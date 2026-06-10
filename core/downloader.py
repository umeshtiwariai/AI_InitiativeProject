"""
Smart WSR – External Portal File Downloader
Supports: direct URLs, Basic Auth, Bearer token, API-key header, custom headers.
"""

import io
import re
from pathlib import Path
from urllib.parse import urlparse, urlencode, urlunparse, parse_qs, urljoin

import requests
import pandas as pd


# ── URL normalisers ──────────────────────────────────────────────────────────

def _normalize_google_sheets(url: str) -> str:
    """
    Convert a Google Sheets browser URL to a direct CSV/XLSX export URL.
    Handles:
      - .../edit#gid=… → export as csv (tab specified by gid)
      - /spreadsheets/d/<ID>/…  → /spreadsheets/d/<ID>/export?format=csv
    """
    if "docs.google.com/spreadsheets" not in url:
        return url
    m = re.search(r"/spreadsheets/d/([^/]+)", url)
    if not m:
        return url
    sheet_id = m.group(1)
    gid_match = re.search(r"gid=(\d+)", url)
    gid = gid_match.group(1) if gid_match else "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def _normalize_sharepoint(url: str) -> str:
    """
    Convert a SharePoint share / view URL to a direct download URL.
    SharePoint share links can be made downloadable by appending &download=1.
    """
    if "sharepoint.com" not in url and "1drv.ms" not in url:
        return url
    # If the URL already looks like a direct file URL, leave it
    if "download=1" in url:
        return url
    # Append download flag
    sep = "&" if "?" in url else "?"
    return url + sep + "download=1"


def normalize_url(url: str) -> str:
    """Apply portal-specific URL normalisations."""
    url = url.strip()
    url = _normalize_google_sheets(url)
    url = _normalize_sharepoint(url)
    return url


# ── Format detection ─────────────────────────────────────────────────────────

def _detect_format(url: str, content_type: str) -> str:
    """Return 'csv', 'xlsx', or 'xls' based on URL path and Content-Type."""
    path = urlparse(url).path.lower()
    if path.endswith(".csv") or "text/csv" in content_type or "format=csv" in url.lower():
        return "csv"
    if path.endswith(".xlsx") or "spreadsheetml" in content_type:
        return "xlsx"
    if path.endswith(".xls") or "ms-excel" in content_type:
        return "xls"
    # Default to xlsx for unknown binary content
    return "xlsx"


def _read_bytes(data: bytes, fmt: str, filename: str = "download") -> pd.DataFrame:
    """Parse raw bytes into a DataFrame based on format hint."""
    buf = io.BytesIO(data)
    if fmt == "csv":
        # Try common encodings
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                buf.seek(0)
                return pd.read_csv(buf, encoding=enc)
            except Exception:
                continue
        raise ValueError("Could not decode CSV with common encodings.")
    else:
        buf.seek(0)
        return pd.read_excel(buf)


# ── Core download function ───────────────────────────────────────────────────

def download_from_url(
    url: str,
    auth_type: str = "none",          # none | basic | bearer | apikey | custom_headers
    username: str = "",
    password: str = "",
    token: str = "",
    api_key: str = "",
    api_key_header: str = "X-API-Key",
    custom_headers: dict | None = None,
    timeout: int = 30,
) -> tuple[pd.DataFrame, str]:
    """
    Download a file from *url* and return (DataFrame, filename).

    auth_type options:
        'none'           – no authentication
        'basic'          – HTTP Basic Auth (username + password)
        'bearer'         – Authorization: Bearer <token>
        'apikey'         – <api_key_header>: <api_key>
        'custom_headers' – arbitrary dict of headers passed via custom_headers

    Raises ValueError / requests.RequestException on failure.
    """
    url = normalize_url(url)

    headers: dict = {}
    auth = None

    if auth_type == "basic" and username:
        auth = (username, password)
    elif auth_type == "bearer" and token:
        headers["Authorization"] = f"Bearer {token}"
    elif auth_type == "apikey" and api_key:
        headers[api_key_header or "X-API-Key"] = api_key
    elif auth_type == "custom_headers" and custom_headers:
        headers.update(custom_headers)

    session = requests.Session()
    session.headers.update({"User-Agent": "SmartWSR-Agent/1.0"})

    resp = session.get(url, headers=headers, auth=auth, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")
    # Try to get a filename from Content-Disposition
    cd = resp.headers.get("Content-Disposition", "")
    m = re.search(r'filename[^;=\n]*=(["\']?)([^"\'\n;]+)\1', cd)
    filename = m.group(2).strip() if m else Path(urlparse(url).path).name or "download"

    fmt = _detect_format(url, content_type)
    df = _read_bytes(resp.content, fmt, filename)
    return df, filename


# ── Chat intent helpers ──────────────────────────────────────────────────────

_URL_PATTERN = re.compile(r'https?://[^\s\'"<>]+', re.IGNORECASE)

def extract_url_from_text(text: str) -> str | None:
    """Return the first HTTP/HTTPS URL found in *text*, or None."""
    m = _URL_PATTERN.search(text)
    return m.group(0).rstrip(".,;)\"'") if m else None


def is_url_download_request(prompt: str) -> bool:
    """
    Return True if the prompt looks like a request to download a file from a URL.

    Examples that match:
        "download from https://..."
        "fetch file from https://..."
        "load data from https://..."
        "use this URL: https://..."
        Any prompt that contains an HTTP URL and a trigger keyword.
    """
    p = prompt.lower()
    has_url = bool(_URL_PATTERN.search(prompt))
    if not has_url:
        return False
    trigger_keywords = [
        "download", "fetch", "load", "import", "get file", "pull",
        "url", "link", "portal", "from http", "use this",
        "grab", "read from"
    ]
    return any(kw in p for kw in trigger_keywords)


# ── Validate URL reachability (lightweight) ──────────────────────────────────

def validate_url(url: str, timeout: int = 10) -> tuple[bool, str]:
    """
    HEAD-check the URL.  Returns (ok: bool, message: str).
    Falls back to GET if HEAD is rejected (405).
    """
    url = normalize_url(url)
    try:
        r = requests.head(url, timeout=timeout, allow_redirects=True,
                          headers={"User-Agent": "SmartWSR-Agent/1.0"})
        if r.status_code == 405:
            # Server doesn't support HEAD – try a byte-range GET
            r = requests.get(url, timeout=timeout, allow_redirects=True,
                             headers={"User-Agent": "SmartWSR-Agent/1.0", "Range": "bytes=0-0"})
        if r.status_code in (200, 206):
            ct = r.headers.get("Content-Type", "unknown")
            cl = r.headers.get("Content-Length", "unknown")
            return True, f"Reachable (Content-Type: {ct}, Size: {cl} bytes)"
        return False, f"Server returned HTTP {r.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to host. Check the URL or network."
    except requests.exceptions.Timeout:
        return False, f"Connection timed out after {timeout}s."
    except Exception as e:
        return False, str(e)

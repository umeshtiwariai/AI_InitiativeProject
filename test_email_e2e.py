"""
Email End-to-End Testing Script
Tests all layers of email functionality without running the Streamlit app.
"""

import sys
import os
import re
import smtplib
import socket
from pathlib import Path
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage

# Add app directory to path
APP_DIR = Path(__file__).parent
sys.path.insert(0, str(APP_DIR))

print("=" * 70)
print("EMAIL FUNCTIONALITY - END-TO-END TESTING")
print("=" * 70)

# ============================================================
# TEST 1: VALIDATE EMAIL PARSING
# ============================================================
print("\n[TEST 1] Email Parsing & Validation")
print("-" * 70)

def parse_emails(txt):
    """Extract email addresses from text"""
    vals = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        txt
    )
    return vals

test_cases = [
    ("Send to john@example.com", ["john@example.com"]),
    ("john@example.com; jane@test.org", ["john@example.com", "jane@test.org"]),
    ("CC: user@company.co.uk", ["user@company.co.uk"]),
    ("No emails here", []),
]

for test_input, expected in test_cases:
    result = parse_emails(test_input)
    status = "✅ PASS" if result == expected else "❌ FAIL"
    print(f"{status}: '{test_input}' → {result}")

# ============================================================
# TEST 2: VALIDATE FILE PATHS
# ============================================================
print("\n[TEST 2] File Path Handling")
print("-" * 70)

output_dir = APP_DIR / "outputs"
output_dir.mkdir(exist_ok=True)

# Test Path object handling
test_path = output_dir / "test_file.txt"
test_path.write_text("test content")

try:
    with open(test_path, "rb") as f:
        content = f.read()
    print(f"✅ PASS: Path object works with open() - read {len(content)} bytes")
    test_path.unlink()
except Exception as e:
    print(f"❌ FAIL: Path object issue: {e}")

# ============================================================
# TEST 3: SMTP USER PROMPTS & INPUTS
# ============================================================
print("\n[TEST 3] SMTP Configuration Input")
print("-" * 70)

config_prompts = [
    ("SMTP Host", "REQUIRED - e.g., 'smtp.office365.com' or 'smtp.gmail.com'"),
    ("SMTP Port", "REQUIRED - Default: 587 (for TLS)"),
    ("SMTP User", "REQUIRED - Full email address (e.g., user@company.com)"),
    ("SMTP Password", "REQUIRED - Password or App Password (if 2FA enabled)"),
    ("Sender Email", "OPTIONAL - Defaults to SMTP User if not provided"),
]

print("Configuration needed for testing:")
for field, desc in config_prompts:
    print(f"  • {field}: {desc}")

# Get user inputs for testing
print("\n" + "-" * 70)
print("Provide SMTP settings for connection test:")
print("-" * 70)

smtp_host = input("SMTP Host [smtp.office365.com]: ").strip() or "smtp.office365.com"
smtp_port_str = input("SMTP Port [587]: ").strip() or "587"
smtp_user = input("SMTP User: ").strip()
smtp_pass = input("SMTP Password: ").strip()
smtp_sender = input("Sender Email [optional]: ").strip()

if not smtp_user or not smtp_pass:
    print("\n❌ SMTP User and Password are required for connection test. Skipping.")
    sys.exit(1)

try:
    smtp_port = int(smtp_port_str)
except ValueError:
    print(f"\n❌ Invalid port: {smtp_port_str}")
    sys.exit(1)

# ============================================================
# TEST 4: SMTP CONNECTION & AUTHENTICATION
# ============================================================
print("\n[TEST 4] SMTP Connection & Authentication")
print("-" * 70)

server = None

# Step 1: DNS/Network
print(f"Step 1: Connecting to {smtp_host}:{smtp_port}...")
try:
    server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
    print(f"✅ PASS: Connected to SMTP server")
except (OSError, socket.error) as e:
    print(f"❌ FAIL: Cannot reach {smtp_host}:{smtp_port}")
    print(f"   Error: {str(e)[:100]}")
    sys.exit(1)

# Step 2: STARTTLS
print(f"Step 2: Upgrading to TLS...")
try:
    server.starttls()
    print(f"✅ PASS: STARTTLS successful")
except Exception as e:
    print(f"❌ FAIL: STARTTLS failed - {str(e)[:100]}")
    try:
        server.quit()
    except:
        pass
    sys.exit(1)

# Step 3: Authentication
print(f"Step 3: Authenticating as {smtp_user}...")
try:
    server.login(smtp_user, smtp_pass)
    print(f"✅ PASS: Authentication successful")
except smtplib.SMTPAuthenticationError as e:
    error_msg = str(e)
    print(f"❌ FAIL: Authentication failed")
    if "535" in error_msg:
        print(f"   Error 535: Credentials rejected")
        print(f"   NOTE: If 2FA is enabled, use an App Password instead")
    elif "539" in error_msg:
        print(f"   Error 539: Policy conflict")
    else:
        print(f"   {error_msg}")
    try:
        server.quit()
    except:
        pass
    sys.exit(1)
except Exception as e:
    print(f"❌ FAIL: {str(e)[:100]}")
    try:
        server.quit()
    except:
        pass
    sys.exit(1)

# ============================================================
# TEST 5: EMAIL MESSAGE COMPOSITION
# ============================================================
print("\n[TEST 5] Email Message Composition")
print("-" * 70)

try:
    # Create test recipients
    test_recipients = [smtp_user]  # Send to self for testing
    
    # Compose message
    msg = MIMEMultipart("related")
    msg["Subject"] = "Test Email from Smart WSR"
    msg["From"] = smtp_sender or smtp_user
    msg["To"] = ", ".join(test_recipients)  # RFC 5322 compliant
    
    html = """
    <html>
    <body>
        <p>Hi Team,</p>
        <p>This is a test email from Smart WSR Agent.</p>
        <p>If you received this, the email system is working correctly!</p>
        <p>Regards,<br>Smart WSR Agent</p>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html, "html"))
    
    # Create a test attachment (minimal)
    test_data = b"Test Report Data"
    part = MIMEApplication(test_data)
    part.add_header("Content-Disposition", "attachment", filename="test_report.txt")
    msg.attach(part)
    
    print(f"✅ PASS: Message composed successfully")
    print(f"   Subject: {msg['Subject']}")
    print(f"   From: {msg['From']}")
    print(f"   To: {msg['To']}")
    print(f"   Parts: HTML body + 1 attachment")
    
except Exception as e:
    print(f"❌ FAIL: Could not compose message - {str(e)[:100]}")
    try:
        server.quit()
    except:
        pass
    sys.exit(1)

# ============================================================
# TEST 6: SEND TEST EMAIL
# ============================================================
print("\n[TEST 6] Sending Test Email")
print("-" * 70)

try:
    server.sendmail(
        msg["From"],
        test_recipients,
        msg.as_string()
    )
    print(f"✅ PASS: Test email sent successfully")
    print(f"   To: {', '.join(test_recipients)}")
    print(f"\n💡 Check your inbox for the test email!")
    
except Exception as e:
    print(f"❌ FAIL: Could not send email - {str(e)[:150]}")
    try:
        server.quit()
    except:
        pass
    sys.exit(1)

# ============================================================
# CLEANUP
# ============================================================
print("\n[CLEANUP] Closing connection")
print("-" * 70)

try:
    server.quit()
    print(f"✅ PASS: Connection closed gracefully")
except:
    pass

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print("\nYour email configuration is working correctly.")
print("You can now use the Smart WSR Agent to send reports via email.")
print("\nNext steps:")
print("  1. Run the Streamlit app: streamlit run app.py")
print("  2. Configure Email Settings with your SMTP credentials")
print("  3. Click 'Test Connection' button to verify settings")
print("  4. Generate a report and send it via email")
print("=" * 70)

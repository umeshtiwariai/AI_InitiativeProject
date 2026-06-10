"""
Test script to verify project search functionality
"""
import re
import pandas as pd

# Test detection function
def is_project_details_request(prompt):
    p = str(prompt).strip().lower()
    
    # Check for intent keywords
    intent_keywords = ["detail", "details", "tell me", "info", "information", "what", "status", "show", "find", "get", "about", "project"]
    
    # Check for any meaningful alphanumeric reference
    has_reference = bool(re.search(r'\b[A-Za-z0-9][A-Za-z0-9\-_\.]*[A-Za-z0-9]\b', p))
    
    # Very permissive: if it has some intent + reference, it's likely a project request
    has_intent = any(k in p for k in intent_keywords)
    
    # If combined with a reference, it's definitely a project request
    if has_intent and has_reference:
        return True
    
    # Also accept queries that are just a reference with project/module keywords
    if has_reference and any(k in p for k in ["project", "module", "id ", " id", "code", "module id"]):
        return True
    
    return False


def extract_query_from_prompt(prompt):
    p = str(prompt).strip()
    lower = p.lower()
    
    # Priority phrases - extract what comes after these
    priority_phrases = [
        ("for", 3),
        ("of", 2),
        ("about", 5),
        ("on", 2),
        ("tell me", 8),
        ("show me", 7),
        ("details", 7),
        ("info", 4),
        ("status", 6),
        ("project", 7),
        ("module", 6),
    ]
    
    for phrase, min_len in priority_phrases:
        idx = lower.find(phrase)
        if idx != -1:
            potential = p[idx + len(phrase):].strip(" :.-,")
            # Extract the first meaningful token
            tokens = re.findall(r'\b[A-Za-z0-9][A-Za-z0-9\-_\.]*[A-Za-z0-9]\b', potential)
            if tokens:
                return tokens[0]
    
    # If no phrase matched, look for the most "project-like" strings
    candidates = re.findall(r'\b([A-Za-z0-9][A-Za-z0-9\-_\.]*[A-Za-z0-9])\b', p)
    
    if candidates:
        # Prefer longer strings
        candidates = [c for c in candidates if len(c) >= 2]
        if candidates:
            return max(candidates, key=len)
    
    return p


# Test cases
test_cases = [
    # Complete project names
    ("Tell me about Project ABC", True, "Project ABC"),
    ("Details for Complete Project Name", True, "Complete Project Name"),
    ("Status of MyProjectXYZ", True, "MyProjectXYZ"),
    
    # Partial/Short names
    ("ABC", True, "ABC"),
    ("XYZ project", True, "project"),
    ("Module 123", True, "Module 123"),
    
    # Module IDs
    ("Details for MOD-001", True, "MOD-001"),
    ("show module M_PROJ_01", True, "M_PROJ_01"),
    ("What about MOD_005", True, "MOD_005"),
    
    # Various phrasings
    ("Tell me about ABC", True, "ABC"),
    ("Info on XYZ", True, "XYZ"),
    ("Project DEF", True, "Project"),
    ("Get details for Code123", True, "Code123"),
    ("Show me status of PROJ_2024", True, "PROJ_2024"),
]

print("=" * 60)
print("TESTING PROJECT SEARCH FUNCTIONS")
print("=" * 60)

for prompt, expected_detect, expected_query in test_cases:
    detected = is_project_details_request(prompt)
    extracted = extract_query_from_prompt(prompt)
    
    detect_status = "✅" if detected == expected_detect else "❌"
    query_status = "✅" if extracted.lower() == expected_query.lower() else "⚠️"
    
    print(f"\n{detect_status} DETECT | {query_status} QUERY")
    print(f"  Prompt: '{prompt}'")
    print(f"  Detected: {detected} (expected: {expected_detect})")
    print(f"  Extracted: '{extracted}' (expected: '{expected_query}')")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)

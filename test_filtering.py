#!/usr/bin/env python3
"""
Test script for project filtering functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import llm_understand_prompt, apply_filters, guess_project_column
import pandas as pd

# Create test data
test_data = {
    'Project Module': ['ABC-123', 'DEF-456', 'GHI-789', 'ABC-999', 'XYZ-000'],
    'Status Code': ['Development', 'UAT', 'Production', 'Development', 'Testing'],
    'Aging': [10, 20, 30, 15, 5]
}

df = pd.DataFrame(test_data)

print("Test Data:")
print(df)
print()

# Test LLM understanding
test_prompts = [
    "show only project ABC",
    "filter by project DEF",
    "show only ABC",
    "project XYZ"
]

for prompt in test_prompts:
    print(f"Testing prompt: '{prompt}'")
    try:
        result = llm_understand_prompt(prompt)
        print(f"LLM Result: {result}")

        # Test filtering
        filtered = apply_filters(df.copy(), result)
        print(f"Filtered rows: {len(filtered)}")
        if len(filtered) > 0:
            print("Filtered data:")
            print(filtered)
        print("-" * 50)
    except Exception as e:
        print(f"Error: {e}")
    print()
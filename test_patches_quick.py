#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick validation of radical AI improvements patches"""

import json
from ai_engine import get_ai

# Load test data
try:
    with open('records_fallback.json', 'r', encoding='utf-8') as f:
        records = json.load(f)
    print(f"✓ Loaded {len(records)} test records\n")
except:
    records = []
    print("✗ Could not load records\n")

# Create AI instance
ai = get_ai()

# Test cases
test_queries = [
    ("MXD", "tail_specific", "Simple tail identifier"),
    ("whats the most crit between the tails?", "statistics", "English statistics"),
    ("qual a falha que menos aparece", "statistics", "Portuguese: least common"),
    ("XA-MXD", "tail_specific", "Full tail format"),
    ("ATA 29", "ata_direct", "Direct ATA reference"),
]

print("="*80)
print("TESTING RADICAL AI IMPROVEMENTS")
print("="*80)

passed = failed = 0

for query, expected_intent, description in test_queries:
    # Test intent detection
    detected_intent = ai._detect_intent(query.lower())
    intent_status = "✓ PASS" if detected_intent == expected_intent else "✗ FAIL"
    
    if detected_intent == expected_intent:
        passed += 1
    else:
        failed += 1
    
    print(f"\n{intent_status} | {description}")
    print(f"     Query:            '{query}'")
    print(f"     Expected Intent:  {expected_intent}")
    print(f"     Detected Intent:  {detected_intent}")
    
    # Test full chat response
    if records:
        response = ai.chat(query, records=records)
        response_type = response.get('type', 'unknown')
        confidence = response.get('confidence', 0)
        print(f"     Response Type:    {response_type} (confidence: {confidence})")
        
        # Show response preview
        resp_preview = str(response.get('response', ''))[:120].replace('\n', ' ')
        print(f"     Response (preview): {resp_preview}...")

print(f"\n{'='*80}")
print(f"RESULTS: {passed} passed, {failed} failed ({100*passed/(passed+failed) if passed+failed > 0 else 0:.0f}%)")

if failed == 0:
    print("\n🎉 ALL INTENT DETECTION TESTS PASSED!")
    print("✅ Radical AI improvements are working correctly")
else:
    print(f"\n⚠️  {failed} test(s) failed - review intent detection")

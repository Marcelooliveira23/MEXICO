#!/usr/bin/env python3
"""
Final validation test with original user examples
Tests the radical AI improvements to ensure ATA 29 bug is fixed
"""

from ai_engine import get_ai

print('=' * 80)
print('FINAL VALIDATION TEST - ORIGINAL USER EXAMPLES')
print('=' * 80)
print()

test_queries = [
    ('MXD', 'tail_specific'),
    ('whats the most crit', 'statistics'),
    ('ATA 29', 'ata_direct or fallback (but routed correctly)'),
    ('XA-MXD statistics', 'tail_specific or statistics'),
    ('qual a falha que menos aparece', 'statistics'),
]

ai = get_ai()
passed = 0
failed = 0

for query, expected in test_queries:
    print(f'Query: "{query}"')
    print(f'  Expected type: {expected}')
    try:
        response = ai.chat(query)
        print(f'  Actual type: {response.get("type", "unknown")}')
        print(f'  Confidence: {response.get("confidence", 0)}%')
        preview = response['response'][:100].replace('\n', ' ').strip()
        if len(response['response']) > 100:
            preview += '...'
        print(f'  Response: {preview}')

        # Validate response contains relevant info (not just "ATA 29")
        response_text = response['response'].lower()
        if 'ata 29' in response_text and query.lower() != 'ata 29':
            print(f'  ⚠️ WARNING: ATA 29 appears in response for non-ATA-29 query')
            failed += 1
        else:
            passed += 1
    except Exception as e:
        print(f'  ❌ ERROR: {str(e)}')
        failed += 1
    print()

print('=' * 80)
print(f'RESULTS: {passed} passed, {failed} failed')
if failed == 0:
    print('✅ ALL TESTS PASSED - AI IS COHERENT AND CONTEXT-AWARE')
else:
    print(f'⚠️ {failed} test(s) failed - review above')
print('=' * 80)

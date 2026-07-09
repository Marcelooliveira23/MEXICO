#!/usr/bin/env python3
"""
Test ATA explicit priority fix - ATA should override statistics queries
"""

from ai_engine import get_ai

ai = get_ai()
print('Test: ATA explicit priority (ATA should override statistics)')
print('=' * 80)
print()

test_cases = [
    ('ATA 24', 'Should return ATA 24 detail (not statistics)'),
    ('ATA 29', 'Should return ATA 29  detail (not statistics)'),
    ('ATA 34', 'Should return ATA 34 detail (not statistics)'),
    ('ATA 29 help', 'Should focus on ATA 29 despite "help" keyword'),
    ('whats wrong with ATA 24', 'Should return ATA 24 detail (not troubleshoot)'),
]

for query, expectation in test_cases:
    response = ai.chat(query, records=[])
    response_type = response.get('type', 'unknown')
    confidence = response.get('confidence', 0)
    
    # Check if response mentions correct ATA
    response_text = response['response'].lower()
    ata_num = query.split('ATA ')[1].split()[0] if 'ATA ' in query else None
    
    mentions_correct_ata = f'ata {ata_num}' in response_text if ata_num else True
    
    status = '✓' if mentions_correct_ata and response_type == 'ata_detail' else '✗'
    print(f'{status} Query: "{query}"')
    print(f'  Expected: {expectation}')
    print(f'  Got type: {response_type} (confidence: {confidence}%)')
    print(f'  Mentions ATA {ata_num}: {mentions_correct_ata}')
    preview = response['response'][:80].replace('\n', ' ').strip()
    print(f'  Preview: {preview}...')
    print()

print('=' * 80)
print('All ATA-explicit queries should return ata_detail type, not statistics.')

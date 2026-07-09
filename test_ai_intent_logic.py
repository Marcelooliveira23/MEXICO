#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste da lógica da IA para identificar o bug de ATA 29
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_engine import get_ai
import re

# Simulação das queries do usuário
test_queries = [
    "MXD",
    "whats the most crit between the tails",
    "whats the most common betwen the tail",
    "whats is the low failure on the fleet",
    "qual a falha que menos aparece na frota",
    "qual a ata com menor numero de falhas",
    "diagnostico MXA",
    "ATA 29 problema",
]

ai = get_ai()

print("=" * 80)
print("TESTE DA LÓGICA DE DETECÇÃO DE INTENT")
print("=" * 80)

for query in test_queries:
    q = query.strip().lower()
    
    # Detectar intent
    intent = ai._detect_intent(q)
    
    # Extrair ATAs
    ata_refs = re.findall(r'\b(\d{2,3})\b', q)
    ata_refs = [a for a in ata_refs if a in ai.kb]
    
    # Keyword match
    matched = ai._keyword_match(q)
    
    print(f"\nQuery: {query}")
    print(f"  Detected Intent: {intent}")
    print(f"  ATA Refs Found: {ata_refs}")
    print(f"  Keyword Matches: {matched}")
    
    # Simular what the chat() function would do
    if ata_refs and intent in ('troubleshoot', 'what_is', 'recommendation', None):
        print(f"  ➜ Would return: ATA {ata_refs[0]} details (direct ATA match)")
    elif intent == 'statistics':
        print(f"  ➜ Would return: statistics (if records provided)")
    elif matched:
        print(f"  ➜ Would return: ATA {matched[0]} details (keyword match)")
    else:
        print(f"  ➜ Would return: fallback (no match)")

print("\n" + "=" * 80)
print("ANÁLISE DO CONHECIMENTO BASE")
print("=" * 80)

print(f"\nTotal de ATAs no KB: {len(ai.kb)}")
print(f"ATAs: {', '.join(sorted(ai.kb.keys()))}")

print("\n" + "=" * 80)
print("ÍNDICE DE PALAVRAS-CHAVE")
print("=" * 80)

# Mostrar keywords para ATA 29
if '29' in ai.kb:
    print(f"\nKeywords para ATA 29:")
    ata_29_keywords = [kw for kw, atas in ai._all_keywords.items() if '29' in atas]
    for kw in sorted(ata_29_keywords)[:20]:
        print(f"  - {kw}")

# Procurar por "mxd" ou "tail" no índice
print(f"\nKeywords contendo 'mxd': {[kw for kw in ai._all_keywords.keys() if 'mxd' in kw.lower()]}")
print(f"Keywords contendo 'tail': {[kw for kw in ai._all_keywords.keys() if 'tail' in kw.lower()]}")
print(f"Keywords contendo 'aircraft': {[kw for kw in ai._all_keywords.keys() if 'aircraft' in kw.lower()]}")

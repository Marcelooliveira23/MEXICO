#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste completo da função _build_copilot_answer com dados reais
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the function we need to test
from routes_analytics import _build_copilot_answer, load_records

# Simular os dados
test_queries = [
    "MXD",
    "whats the most crit between the tails",
    "whats the most common betwen the tail",
]

print("=" * 80)
print("TESTE COMPLETO DE _build_copilot_answer()")
print("=" * 80)

for query in test_queries:
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}\n")
    
    try:
        result = _build_copilot_answer(query=query, scope="global", model_filter="", tail_filter="")
        
        # Mostrar apenas os primeiros 1000 characters da resposta
        response_text = result.get("response", "")[:1500]
        print(f"Response (first 1500 chars):\n{response_text}\n")
        
        print(f"Confidence: {result.get('confidence')}")
        print(f"Type: {result.get('type')}")
        print(f"Related ATAs: {result.get('related_atas')}")
        print(f"Sources - Records: {result.get('sources', {}).get('records')}")
        print(f"Sources - MEL: {result.get('sources', {}).get('mel')}")
        print(f"Sources - AOG: {result.get('sources', {}).get('aog')}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)

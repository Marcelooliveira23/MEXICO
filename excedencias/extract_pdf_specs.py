#!/usr/bin/env python3
"""Extrator de especificações PDF - Hard Landing"""

try:
    import pypdf as PyPDF2
except ImportError:
    import PyPDF2
import sys
import os

os.chdir(r'e:\Projetos\excedencias')
pdf_path = r'Analises de dados de voo\MPP8725_05-50-03-06-1-200-801-A_1763656864090.PDF'

try:
    pdf = PyPDF2.PdfReader(pdf_path)
    print(f"[OK] PDF aberto: {len(pdf.pages)} paginas\n")
    
    # Procurar por conteúdo
    target_keywords = ['607', '608', '609', '614', 'vertical', 'acceleration', 'roll rate', 'pitch rate', 'hard landing']
    
    for i in range(len(pdf.pages)):
        text = pdf.pages[i].extract_text()
        has_keyword = any(k.lower() in text.lower() for k in target_keywords)
        
        if has_keyword or i < 5:  # Primeiras 5 paginas sempre
            print(f"\n{'='*80}")
            print(f"PAGE {i+1} {'(POTENTIALLY RELEVANT)' if has_keyword else '(SAMPLE)'}")
            print('='*80)
            print(text[:600] + ("..." if len(text) > 600 else ""))

except Exception as e:
    print(f"[ERRO] {e}")
    sys.exit(1)

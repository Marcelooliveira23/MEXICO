#!/usr/bin/env python3
"""Mapear familias PDF"""
try:
    import pypdf as PyPDF2
except ImportError:
    import PyPDF2
import os

os.chdir(r'e:\Projetos\excedencias\Analises de dados de voo')

pdf_files = [
    'MPP8725_05-50-03-06-1-200-801-A_1763656864090.PDF',
    'MPP8725_05-50-03-06-1-200-801-A_1763656864090-1.PDF',
]

models = ['E145', 'E135', 'E140', 'E170', 'E175', 'E190', 'E195', 'E190-E2', 'E195-E2']

for pdf_name in pdf_files:
    try:
        print(f"\n{'='*60}")
        print(f"PDF: {pdf_name}")
        print('='*60)
        pdf = PyPDF2.PdfReader(pdf_name)
        
        for model in models:
            pages_found = []
            for i in range(len(pdf.pages)):
                text = pdf.pages[i].extract_text()
                if model in text:
                    pages_found.append(i+1)
            
            if pages_found:
                print(f"  {model:10} -> pages {pages_found}")
    except Exception as e:
        print(f"  [ERROR] {e}")

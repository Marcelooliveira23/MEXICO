#!/usr/bin/env python3
"""Extrair dados COMPLETOS das Figures 605-609"""

try:
    import pypdf as PyPDF2
except ImportError:
    import PyPDF2
import os
import re

os.chdir(r'e:\Projetos\excedencias\Analises de dados de voo')
pdf = PyPDF2.PdfReader('MPP8725_05-50-03-06-1-200-801-A_1763656864090.PDF')

# Páginas confirmadas:
# E190-E2: pages 22-23 (Figures 605-606)
# E195-E2: pages 24-26 (Figures 607-609)

pages_data = {
    'E190-E2_Figure605_Roll<=8': 21,  # Page 22 (0-indexed)
    'E190-E2_Figure606_Roll>8': 22,   # Page 23
    'E195-E2_Figure607_Roll<=2.5': 23,  # Page 24
    'E195-E2_Figure608_Roll2.5-7.5': 24,  # Page 25
    'E195-E2_Figure609_Roll>7.5': 25  # Page 26
}

print("[EXTRACTING COMPLETE TABLE DATA]\n")

for label, page_idx in pages_data.items():
    text = pdf.pages[page_idx].extract_text()
    print(f"\n{'='*80}")
    print(f"{label} (PAGE {page_idx+1})")
    print('='*80)
    
    # Extract all numbers that look like aircraft mass or threshold
    lines = text.split('\n')
    
    # Look for table rows with aircraft mass (34700, 40000, etc) and threshold values
    import_lines = []
    for i, line in enumerate(lines):
        # Lines with numbers like "34700" and "2.30" 
        if any(mass in line for mass in ['34700', '40000', '40900', '47000', '51850', '54000', '61500']):
            print(f"Row {i}: {line}")
        # Alternative: lines with threshold values
        elif re.search(r'\d+\.?\d*\s+[12]\.\d{2}', line):
            print(f"Val {i}: {line}")

print("\n\n[EXTRACTED DATA READY FOR PYTHON CONVERSION]")

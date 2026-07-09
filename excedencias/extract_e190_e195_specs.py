#!/usr/bin/env python3
"""Extrair especificações E190/E195 do PDF"""

try:
    import pypdf as PyPDF2
except ImportError:
    import PyPDF2
import os

os.chdir(r'e:\Projetos\excedencias\Analises de dados de voo')
pdf = PyPDF2.PdfReader('MPP8725_05-50-03-06-1-200-801-A_1763656864090.PDF')

# E195-E2 está em pages 24-26 (visto anteriormente)
# E190 deve estar em páginas anteriores

print("[EXTRACTING E190-E195 SPECIFICATIONS]\n")

# Extrair páginas 20-35 para mapear toda a estrutura
for page_num in range(19, 27):  # Pages 20-27
    text = pdf.pages[page_num].extract_text()
    
    # Check for model indicators
    model = ""
    if "E195-E2" in text:
        model = "E195-E2"
    elif "E195" in text and "E2" not in text:
        model = "E195"
    elif "E190-E2" in text:
        model = "E190-E2"
    elif "E190" in text and "E2" not in text:
        model = "E190"
    
    if model:
        print(f"\n{'='*80}")
        print(f"PAGE {page_num+1}: {model}")
        print('='*80)
        
        # Extract table data
        lines = text.split('\n')
        in_table = False
        for line in lines:
            # Look for table headers and data
            if any(x in line for x in ['AIRCRAFT MASS', 'THRESHOLD', 'DEG/S', 'Figure']):
                print(line)
            elif any(char.isdigit() for char in line[:5]):  # Lines starting with numbers
                if any(x in line for x in ['34700', '40000', '47000', '51850', '54000', '61500']):
                    print(f"  {line}")


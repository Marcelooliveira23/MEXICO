#!/usr/bin/env python3
"""Mapear todos PDFs para eventos"""
try:
    import pypdf as PyPDF2
except ImportError:
    import PyPDF2
import os

os.chdir(r'e:\Projetos\excedencias\Analises de dados de voo')

pdfs = {
    '05-50-03': 'MPP8725_05-50-03-06-1-200-801-A_1763656864090.PDF',
    '05-50-06': 'MPP8725_05-50-06-06-1-200-801-A_1763656910862.PDF',
    '05-50-07': 'MPP8725_05-50-07-06-1-200-801-A_1763656924490.PDF',
    '05-50-09': 'MPP8725_05-50-09-06-1-210-801-A_1763656939441.PDF',
    '05-50-27': 'MPP8725_05-50-27-06-1-200-801-A_1763656989006.PDF'
}

print("[MAPEAMENTO PDF -> EVENTO]")
print("="*80)

for task, filename in pdfs.items():
    try:
        pdf = PyPDF2.PdfReader(filename)
        text = pdf.pages[0].extract_text()
        
        # Extract title/description
        lines = text.split('\n')
        for i, line in enumerate(lines[:20]):
            if 'TASK' in line and '05-50' in line:
                print(f"\n{task} ({pdf.pages.__len__()} pages):")
                # Get next 3 lines after TASK
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip():
                        print(f"  {lines[j][:80]}")
                break
    except Exception as e:
        print(f"\n{task}: ERROR - {e}")

print("\n" + "="*80)

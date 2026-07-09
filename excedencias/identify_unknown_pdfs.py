"""
Identifica eventos desconhecidos extraindo títulos de PDFs AMM
"""

try:
    import pypdf as PyPDF2
except ImportError:
    import PyPDF2
from pathlib import Path

# PDFs desconhecidos por família
unknown_pdfs = {
    "E145": [
        r"E:\Projetos\excedencias\E145\MPP1401_05-50-02-06-1_1765402478057.PDF",
        r"E:\Projetos\excedencias\E145\MPP1401_05-50-04-06-1_1765402455790.PDF",
        r"E:\Projetos\excedencias\E145\MPP1401_05-50-25-06-1_1765402412089.PDF",
    ],
    "E1": [
        r"E:\Projetos\excedencias\E1\MPP3213_05-50-13-06-1-200-801-A_1765401857254.PDF",
        r"E:\Projetos\excedencias\E1\MPP3213_05-50-28-06-1-210-801-A_1765401906957.PDF",
        r"E:\Projetos\excedencias\E1\MPP2558_05-50-28-06-1-210-801-A_1770219153026.PDF",
    ],
    "E170": [
        r"E:\Projetos\excedencias\E170\MPP8492_05-50-13-06-1-200-801-A_1765402098706.PDF",
        r"E:\Projetos\excedencias\E170\MPP8492_05-50-28-06-1-210-801-A_1770219201466.PDF",
    ],
    "E2": [
        r"E:\Projetos\excedencias\E2\MPP8725_05-50-10-06-1-200-801-A_1765401465293.PDF",
    ],
}

def extract_pdf_title(pdf_path: str) -> str:
    """Extrai título/primeiras linhas do PDF"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            if len(reader.pages) > 0:
                # Extrair primeira página
                first_page = reader.pages[0]
                text = first_page.extract_text()
                
                # Pegar primeiras linhas significativas
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                
                # Retornar primeiras 5 linhas não vazias
                return '\n'.join(lines[:5])
    except Exception as e:
        return f"ERRO: {e}"

print("=" * 80)
print("🔍 IDENTIFICAÇÃO DE EVENTOS DESCONHECIDOS")
print("=" * 80)

for family, pdfs in unknown_pdfs.items():
    print(f"\n{'=' * 80}")
    print(f"📁 FAMÍLIA: {family}")
    print('=' * 80)
    
    for pdf_path in pdfs:
        pdf_file = Path(pdf_path)
        amm_task = pdf_file.name.split('_')[1]  # 05-50-XX
        
        print(f"\n📄 AMM {amm_task} - {pdf_file.name}")
        print(f"   Tamanho: {pdf_file.stat().st_size / 1024:.1f} KB")
        print(f"   Título:")
        
        title = extract_pdf_title(pdf_path)
        for line in title.split('\n'):
            print(f"      {line}")

print("\n" + "=" * 80)
print("✅ EXTRAÇÃO COMPLETA")
print("=" * 80)

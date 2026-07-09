"""
Extrai especificações de Over-G, High Load Factor e Bank Angle dos PDFs disponíveis
"""

try:
    import pypdf as PyPDF2
except ImportError:
    import PyPDF2
from pathlib import Path
import re

# PDFs de Hard Landing - podem conter specs de Over-G/High Load
pdfs_to_extract = [
    (r"E:\Projetos\excedencias\E1\MPP3213_05-50-03-06-1-200-801-A_1765401741528.PDF", "E1", "05-50-03"),
    (r"E:\Projetos\excedencias\E170\MPP8492_05-50-03-06-1-200-802-A_1765401993281.PDF", "E170", "05-50-03"),
    (r"E:\Projetos\excedencias\E2\MPP8725_05-50-03-06-1-200-801-A_1765401638290.PDF", "E2", "05-50-03"),
]

def extract_section(pdf_path: str, keywords: list, context_lines: int = 50) -> dict:
    """Extrai seções com keywords específicas"""
    results = {kw: [] for kw in keywords}
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text = page.extract_text()
                
                for kw in keywords:
                    pattern = f'.{{0,{context_lines}}}{re.escape(kw)}.{{0,{context_lines}}}'
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    
                    for match in matches:
                        if match not in [m['text'] for m in results[kw]]:
                            results[kw].append({
                                'page': page_num + 1,
                                'text': match.strip()
                            })
    
    except Exception as e:
        return {"error": str(e)}
    
    return results

print("=" * 100)
print("EXTRACAO DE ESPECIFICACOES: OVER-G, HIGH LOAD FACTOR, BANK ANGLE")
print("=" * 100)

keywords = [
    "high load",
    "load factor",
    "3.5",
    "3.8",
    "+3.5",
    "+3.8",
    "±3.5",
    "±3.8",
    "vertical acceleration",
    "normal acceleration",
    "bank angle",
    "60 degree",
    "67 degree",
    "60°",
    "67°",
]

for pdf_path, family, task in pdfs_to_extract:
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"\n❌ PDF não encontrado: {family} - {task}")
        continue
    
    print(f"\n{'=' * 100}")
    print(f"📁 EXTRAÇÃO: {family} - AMM {task}")
    print('=' * 100)
    
    results = extract_section(pdf_path, keywords, context_lines=100)
    
    if "error" in results:
        print(f"❌ ERRO: {results['error']}")
        continue
    
    # Mostrar resultados significativos
    found_any = False
    for kw, matches in results.items():
        if matches:
            found_any = True
            print(f"\n🔎 '{kw}' - {len(matches)} ocorrência(s):")
            
            for i, match in enumerate(matches[:2], 1):
                print(f"\n   [{i}] Página {match['page']}:")
                print(f"   {match['text'][:200]}...")
            
            if len(matches) > 2:
                print(f"\n   ... e mais {len(matches) - 2} ocorrência(s)")
    
    if not found_any:
        print("❌ Nenhuma especificação encontrada para keywords buscadas")

print("\n" + "=" * 100)
print("✅ EXTRAÇÃO COMPLETA")
print("=" * 100)

"""
Busca especificações de Over-G e Tail Strike nos PDFs de Hard Landing
"""

try:
    import pypdf as PyPDF2
except ImportError:
    import PyPDF2
from pathlib import Path
import re

# PDFs de Hard Landing por família
hard_landing_pdfs = [
    r"E:\Projetos\excedencias\E145\MPP1401_05-50-02-06-1_1765402478057.PDF",
    r"E:\Projetos\excedencias\E1\MPP3213_05-50-03-06-1-200-801-A_1765401741528.PDF",
    r"E:\Projetos\excedencias\E170\MPP8492_05-50-03-06-1-200-802-A_1765401993281.PDF",
    r"E:\Projetos\excedencias\E2\MPP8725_05-50-03-06-1-200-801-A_1765401638290.PDF",
]

search_terms = [
    "tail strike",
    "tail-strike",
    "pitch angle",
    "pitch rate",
    "over-g",
    "high load",
    "load factor",
    "3.5",
    "3.8",
    "±3.5",
    "±3.8",
    "+3.5",
    "+3.8",
    "vertical acceleration",
    "normal acceleration",
]

def search_pdf(pdf_path: str, terms: list) -> dict:
    """Busca termos em todo o PDF"""
    results = {term: [] for term in terms}
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            total_pages = len(reader.pages)
            
            for page_num in range(total_pages):
                page = reader.pages[page_num]
                text = page.extract_text().lower()
                
                for term in terms:
                    if term.lower() in text:
                        # Extrair contexto (50 caracteres antes e depois)
                        pattern = f'.{{0,50}}{re.escape(term.lower())}.{{0,50}}'
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        
                        for match in matches:
                            results[term].append({
                                'page': page_num + 1,
                                'context': match.strip()
                            })
    
    except Exception as e:
        return {"error": str(e)}
    
    return results

print("=" * 100)
print("🔍 BUSCA DE ESPECIFICAÇÕES DE OVER-G E TAIL STRIKE NOS PDFs DE HARD LANDING")
print("=" * 100)

for pdf_path in hard_landing_pdfs:
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"\n❌ PDF não encontrado: {pdf_file.name}")
        continue
    
    family = pdf_file.parent.name
    print(f"\n{'=' * 100}")
    print(f"📁 FAMÍLIA: {family} - {pdf_file.name}")
    print('=' * 100)
    
    results = search_pdf(pdf_path, search_terms)
    
    if "error" in results:
        print(f"❌ ERRO: {results['error']}")
        continue
    
    # Filtrar apenas termos encontrados
    found_terms = {term: matches for term, matches in results.items() if matches}
    
    if not found_terms:
        print("❌ Nenhum termo encontrado")
        continue
    
    for term, matches in found_terms.items():
        print(f"\n🔎 Termo: '{term}' - {len(matches)} ocorrências")
        
        # Mostrar primeiras 3 ocorrências
        for i, match in enumerate(matches[:3], 1):
            print(f"   [{i}] Página {match['page']}: ...{match['context']}...")
        
        if len(matches) > 3:
            print(f"   ... e mais {len(matches) - 3} ocorrências")

print("\n" + "=" * 100)
print("✅ BUSCA COMPLETA")
print("=" * 100)

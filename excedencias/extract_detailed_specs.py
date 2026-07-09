"""
Extrai as páginas completas com especificações de Over-G/High Load Factor
"""

try:
    import pypdf as PyPDF2
except ImportError:
    import PyPDF2
from pathlib import Path

def extract_pages_with_content(pdf_path: str, page_numbers: list, output_file: str):
    """Extrai páginas específicas para análise"""
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            with open(output_file, 'w', encoding='utf-8', errors='ignore') as out:
                out.write(f"PDF: {Path(pdf_path).name}\n")
                out.write("=" * 100 + "\n\n")
                
                for page_num in page_numbers:
                    if page_num <= len(reader.pages):
                        page = reader.pages[page_num - 1]
                        text = page.extract_text()
                        
                        out.write(f"\n{'=' * 100}\n")
                        out.write(f"PAGINA {page_num}\n")
                        out.write(f"{'=' * 100}\n\n")
                        out.write(text)
                        out.write("\n\n")
        
        print(f"Extraido: {output_file}")
    
    except Exception as e:
        print(f"ERRO: {e}")

# E1 PDF - procurar por "high load" nas paginas 9-10, 14-16
print("Extraindo paginas com High Load specs...")

extract_pages_with_content(
    r"E:\Projetos\excedencias\E1\MPP3213_05-50-03-06-1-200-801-A_1765401741528.PDF",
    [9, 10, 14, 15, 16, 46],  # Paginas com "high load" e figuras
    r"E:\Projetos\excedencias\SPECS_E1_HIGH_LOAD.txt"
)

# E170 PDF
extract_pages_with_content(
    r"E:\Projetos\excedencias\E170\MPP8492_05-50-03-06-1-200-802-A_1765401993281.PDF",
    [11, 12, 31, 43],
    r"E:\Projetos\excedencias\SPECS_E170_HIGH_LOAD.txt"
)

# E2 PDF
extract_pages_with_content(
    r"E:\Projetos\excedencias\E2\MPP8725_05-50-03-06-1-200-801-A_1765401638290.PDF",
    [5, 7, 21, 22, 23],
    r"E:\Projetos\excedencias\SPECS_E2_HIGH_LOAD.txt"
)

# E145 PDF
extract_pages_with_content(
    r"E:\Projetos\excedencias\E145\MPP1401_05-50-02-06-1_1765402478057.PDF",
    [3, 4, 5, 6],
    r"E:\Projetos\excedencias\SPECS_E145_HIGH_LOAD.txt"
)

print("\nArquivos de specs gerados com sucesso!")

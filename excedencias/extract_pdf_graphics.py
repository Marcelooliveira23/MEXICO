"""
Script para extrair todos os gráficos/imagens dos PDFs técnicos
e organizá-los por família e categoria de evento
"""
import sys
import io
import os
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.pdf_mapper import PDFMapper
from services.pdf_extractor import PDFExtractor

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    # Diretórios
    base_dir = Path(__file__).parent
    output_dir = base_dir / "assets" / "pdf_images"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("🖼️  EXTRAÇÃO DE GRÁFICOS DOS PDFs TÉCNICOS")
    print("=" * 80)
    print()
    
    # Inicializar mapper e extractor
    mapper = PDFMapper()
    extractor = PDFExtractor()
    
    # Escanear todos os PDFs
    pdfs_by_family = mapper.scan_all_pdfs(base_dir)
    
    total_images = 0
    total_pdfs = 0
    
    # Processar cada família
    for family, pdfs in pdfs_by_family.items():
        print(f"\n{'='*80}")
        print(f"📁 Família: {family}")
        print(f"{'='*80}")
        
        # Criar diretório para a família
        family_dir = output_dir / family
        family_dir.mkdir(exist_ok=True)
        
        family_image_count = 0
        
        for pdf in pdfs:
            total_pdfs += 1
            pdf_name = pdf.filename.replace('.pdf', '')
            
            print(f"\n📄 {pdf.filename}")
            print(f"   Categoria: {pdf.event_category}")
            print(f"   Task: {pdf.task_number}")
            
            # Criar diretório para o PDF
            pdf_dir = family_dir / pdf_name
            pdf_dir.mkdir(exist_ok=True)
            
            try:
                # Extrair imagens
                images = extractor.extract_images(pdf.path, pdf_dir)
                
                if images:
                    print(f"   ✅ Extraídas: {len(images)} imagem(ns)")
                    family_image_count += len(images)
                    total_images += len(images)
                    
                    # Listar imagens extraídas
                    for i, img_path in enumerate(images, 1):
                        size_kb = os.path.getsize(img_path) / 1024
                        print(f"      {i}. {Path(img_path).name} ({size_kb:.1f} KB)")
                else:
                    print(f"   ℹ️  Nenhuma imagem encontrada")
                    
            except Exception as e:
                print(f"   ❌ Erro: {e}")
        
        print(f"\n📊 Total de imagens da família {family}: {family_image_count}")
    
    # Resumo final
    print("\n" + "=" * 80)
    print("📈 RESUMO DA EXTRAÇÃO")
    print("=" * 80)
    print(f"Total de PDFs processados: {total_pdfs}")
    print(f"Total de imagens extraídas: {total_images}")
    print(f"Média de imagens por PDF: {total_images/total_pdfs:.1f}")
    print(f"\nImagens salvas em: {output_dir}")
    print("=" * 80)
    
    # Criar índice de imagens por categoria
    print("\n📑 Criando índice de imagens...")
    create_image_index(pdfs_by_family, output_dir)
    print("✅ Índice criado!")

def create_image_index(pdfs_by_family, output_dir):
    """Cria um arquivo JSON com índice de todas as imagens"""
    import json
    
    index = {
        "families": {},
        "categories": {}
    }
    
    for family, pdfs in pdfs_by_family.items():
        index["families"][family] = {
            "total_pdfs": len(pdfs),
            "pdfs": {}
        }
        
        for pdf in pdfs:
            pdf_name = pdf.filename.replace('.pdf', '')
            pdf_dir = output_dir / family / pdf_name
            
            # Contar imagens
            images = list(pdf_dir.glob("*.jpg")) + list(pdf_dir.glob("*.png"))
            
            pdf_info = {
                "filename": pdf.filename,
                "task": pdf.task_number,
                "category": pdf.event_category,
                "image_count": len(images),
                "images": [img.name for img in images]
            }
            
            index["families"][family]["pdfs"][pdf_name] = pdf_info
            
            # Organizar por categoria
            category = pdf.event_category
            if category not in index["categories"]:
                index["categories"][category] = []
            
            index["categories"][category].append({
                "family": family,
                "filename": pdf.filename,
                "image_count": len(images),
                "path": str(pdf_dir.relative_to(output_dir))
            })
    
    # Salvar índice
    index_file = output_dir / "image_index.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    
    print(f"   Índice salvo em: {index_file}")

if __name__ == "__main__":
    main()

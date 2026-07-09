"""
Script para analisar todos os PDFs e criar resumo
"""

from pathlib import Path
import sys
import os

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services import PDFMapper, PDFExtractor
from utils import AppConfig


def main():
    """Analisa todos os PDFs e gera resumo"""
    print("=" * 80)
    print("ANÁLISE DE DOCUMENTAÇÃO TÉCNICA - PDFs")
    print("=" * 80)
    print()
    
    # Caminho base
    base_path = Path(__file__).parent
    
    # Escanear todos os PDFs
    print("📂 Escaneando PDFs...")
    all_pdfs = PDFMapper.scan_all_pdfs(base_path)
    
    # Resumo geral
    total_pdfs = sum(len(pdfs) for pdfs in all_pdfs.values())
    print(f"\n✅ Total de PDFs encontrados: {total_pdfs}")
    print()
    
    # Por família
    for family, pdfs in all_pdfs.items():
        if not pdfs:
            continue
            
        print("-" * 80)
        print(f"🛩️  FAMÍLIA: {family.upper()}")
        print("-" * 80)
        print(f"Total de documentos: {len(pdfs)}\n")
        
        # Agrupar por categoria de evento
        events = {}
        for pdf in pdfs:
            if pdf.event_category not in events:
                events[pdf.event_category] = []
            events[pdf.event_category].append(pdf)
        
        # Mostrar por categoria
        for event_cat, event_pdfs in sorted(events.items()):
            desc = PDFMapper.EVENT_DESCRIPTIONS.get(event_cat, event_cat)
            print(f"\n📋 {desc}")
            print(f"   Categoria: {event_cat}")
            print(f"   Documentos: {len(event_pdfs)}")
            
            for pdf in event_pdfs:
                # Mapear famílias para diretórios corretos
                if family == 'e145':
                    pdf_path = base_path / 'E145' / pdf.filename
                elif family == 'e170':
                    pdf_path = base_path / 'E170' / pdf.filename
                elif family == 'e1':
                    pdf_path = base_path / 'E1' / pdf.filename
                elif family == 'e2':
                    pdf_path = base_path / 'E2' / pdf.filename
                else:
                    # Fallback: tentar usar o nome da família em uppercase
                    pdf_path = base_path / family.upper() / pdf.filename
                
                print(f"\n   📄 {pdf.filename}")
                print(f"      Task: {pdf.task_number}")
                
                if pdf_path.exists():
                    try:
                        info = PDFExtractor.get_pdf_info(pdf_path)
                        print(f"      Páginas: {info['pages']}")
                        print(f"      Tamanho: {info['size_kb']:.1f} KB")
                        print(f"      Imagens: {'Sim' if info['has_images'] else 'Não'}")
                        print(f"      Tabelas: {'Sim' if info['has_tables'] else 'Não'}")
                    except Exception as e:
                        print(f"      ⚠️ Erro ao analisar: {e}")
        
        print()
    
    # Análise detalhada de um PDF de exemplo
    print("\n" + "=" * 80)
    print("ANÁLISE DETALHADA - EXEMPLO")
    print("=" * 80)
    
    # Pegar primeiro PDF de E145
    if all_pdfs['e145']:
        example_pdf = all_pdfs['e145'][0]
        pdf_path = base_path / 'E145' / example_pdf.filename
        
        print(f"\n📄 Analisando: {example_pdf.filename}")
        print()
        
        try:
            # Criar resumo
            summary = PDFExtractor.create_summary(pdf_path)
            print(summary)
            
            # Extrair regras
            print("\n" + "-" * 80)
            print("REGRAS E LIMITES EXTRAÍDOS")
            print("-" * 80)
            
            rules = PDFExtractor.extract_rules_and_limits(pdf_path)
            
            if rules['limits']:
                print(f"\n📏 Limites encontrados ({len(rules['limits'])}):")
                for key, values in list(rules['limits'].items())[:5]:  # Primeiros 5
                    print(f"   • {key}: {values}")
            
            if rules['tolerances']:
                print(f"\n⚙️ Tolerâncias encontradas ({len(rules['tolerances'])}):")
                for key in list(rules['tolerances'].keys())[:5]:  # Primeiras 5
                    print(f"   • {key}")
            
            if rules['conditions']:
                print(f"\n✅ Condições encontradas ({len(rules['conditions'])}):")
                for cond in rules['conditions'][:5]:  # Primeiras 5
                    print(f"   • {cond}")
            
            if rules['inspection_criteria']:
                print(f"\n🔍 Critérios de inspeção ({len(rules['inspection_criteria'])}):")
                for crit in rules['inspection_criteria'][:5]:  # Primeiros 5
                    print(f"   • {crit}")
            
            # Texto bruto (primeiras linhas)
            print("\n" + "-" * 80)
            print("PREVIEW DO TEXTO EXTRAÍDO")
            print("-" * 80)
            lines = rules['raw_text'].split('\n')[:20]
            for line in lines:
                if line.strip():
                    print(line)
            
        except Exception as e:
            print(f"❌ Erro na análise detalhada: {e}")
    
    print("\n" + "=" * 80)
    print("ANÁLISE CONCLUÍDA")
    print("=" * 80)


if __name__ == "__main__":
    main()

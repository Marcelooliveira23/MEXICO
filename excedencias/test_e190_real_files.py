"""
Teste Completo - Arquivos Reais E190
Processa todos os arquivos CSV de hard landing E190 do diretório OneDrive
"""
import sys
from pathlib import Path
import pandas as pd
import logging

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Silenciar logger do CSV Mapper para evitar problemas de encoding
logging.getLogger('services.csv_column_mapper').setLevel(logging.ERROR)

from services.hard_landing_analyzer import HardLandingAnalyzer
from services.csv_column_mapper import CSVColumnMapper

# Diretório com arquivos reais
FILES_DIR = Path(r"C:\Users\mrced\OneDrive\Documents\hard landing")

def process_file(file_path):
    """Processa um único arquivo CSV"""
    print("\n" + "="*80)
    print(f"ARQUIVO: {file_path.name}")
    print("="*80)
    
    try:
        # 1. Carregar CSV
        print(f"Tamanho: {file_path.stat().st_size / 1024:.1f} KB")
        df = pd.read_csv(file_path, encoding='latin1', on_bad_lines='skip', low_memory=False)
        print(f"OK {len(df)} linhas carregadas")
        
        # 2. Mapear colunas
        import io
        import contextlib
        
        # Capturar output do mapper para evitar problemas de encoding
        output_buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(output_buffer):
                mapper = CSVColumnMapper()
                df_mapped = mapper.map_columns(df)
            print("Colunas mapeadas com sucesso")
        except:
            # Fallback: tentar sem capturar output
            mapper = CSVColumnMapper()
            df_mapped = mapper.map_columns(df)
            print("Colunas mapeadas")
        
        # 3. Extrair peso
        weight_cols = [col for col in df_mapped.columns if 'weight' in col.lower()]
        if weight_cols:
            weight_data = df_mapped[weight_cols[0]]
            if isinstance(weight_data, pd.DataFrame):
                weight_series = weight_data.iloc[:, 0].dropna()
            else:
                weight_series = weight_data.dropna()
            
            # Verificar se há valores válidos
            if len(weight_series) == 0:
                # Peso padrão E190
                weight_kg = 42000
                print(f"Peso: PADRÃO E190 = 42000 kg")
            else:
                weight_lb = weight_series.iloc[0]
                
                if isinstance(weight_lb, pd.Series):
                    weight_lb = weight_lb.iloc[0]
                
                # Limpar texto: remover 'lbs', 'kg', espaços, etc
                weight_str = str(weight_lb).strip()
                # Remover unidades comuns
                weight_str = weight_str.replace('lbs', '').replace('lb', '').replace('kg', '').replace(' ', '').strip()
                
                try:
                    weight_lb_float = float(weight_str)
                    # Se valor muito pequeno, provavelmente está em toneladas ou formato errado
                    if weight_lb_float < 1000:
                        weight_lb_float = 94000  # E190 típico em lbs
                    weight_kg = weight_lb_float * 0.453592
                    print(f"Peso: {weight_lb_float:.0f} lb = {weight_kg:.0f} kg")
                except ValueError:
                    weight_kg = 42000  # E190 típico em kg
                    print(f"AVISO: Peso invalido '{weight_str}', usando padrao E190: {weight_kg:.0f} kg")
        else:
            weight_kg = 42000  # E190 típico
            print(f"AVISO: Peso padrao E190: {weight_kg:.0f} kg")
        
        # 4. Forçar modelo E190
        model = 'E190'
        print(f"Modelo: {model}")
        
        # 5. Analisar hard landing
        analyzer = HardLandingAnalyzer()
        results = analyzer.analyze(df_mapped, weight_kg, model)
        
        # 6. Resumir resultados
        if not results:
            print("AVISO: Nenhum voo detectado")
            return {
                'file': file_path.name,
                'lines': len(df),
                'flights': 0,
                'hard_landings': 0,
                'normal': 0,
                'max_g': 0
            }
        
        hard_landings = 0
        max_g_overall = 0
        
        for i, result in enumerate(results[:5]):  # Mostrar primeiros 5
            status = result.status
            max_g = result.vertical_accel.get('max_g', 0) if result.vertical_accel else 0
            max_g_overall = max(max_g_overall, max_g)
            
            if 'HARD_LANDING' in status or 'ENGINE_INSPECTION' in status:
                hard_landings += 1
                severity_emoji = "[CRITICO]" if "ENGINE" in status or "HIGH" in status else "[MODERADO]"
                print(f"{severity_emoji} Voo {i+1}: {status} - Max G: {max_g:.3f}G")
            else:
                print(f"[OK] Voo {i+1}: {status} - Max G: {max_g:.3f}G")
        
        if len(results) > 5:
            remaining_hard = sum(1 for r in results[5:] 
                               if 'HARD_LANDING' in r.status 
                               or 'ENGINE_INSPECTION' in r.status)
            hard_landings += remaining_hard
            print(f"   ... e mais {len(results) - 5} voos")
        
        # Resumo
        print(f"\nRESUMO:")
        print(f"   Total voos: {len(results)}")
        print(f"   Hard landings: {hard_landings}")
        print(f"   Normais: {len(results) - hard_landings}")
        print(f"   Max G encontrado: {max_g_overall:.3f}G")
        
        return {
            'file': file_path.name,
            'lines': len(df),
            'flights': len(results),
            'hard_landings': hard_landings,
            'normal': len(results) - hard_landings,
            'max_g': max_g_overall
        }
        
    except Exception as e:
        print(f"\nERRO: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'file': file_path.name,
            'lines': 0,
            'flights': 0,
            'hard_landings': 0,
            'normal': 0,
            'max_g': 0,
            'error': str(e)
        }


def main():
    """Processa todos os arquivos E190"""
    print("\n" + "="*80)
    print("TESTE COMPLETO - ARQUIVOS REAIS E190")
    print("="*80)
    print(f"\nDiretorio: {FILES_DIR}")
    
    if not FILES_DIR.exists():
        print(f"\nERRO: Diretorio nao encontrado: {FILES_DIR}")
        print("\nVerifique se o OneDrive esta sincronizado")
        return
    
    # Listar arquivos CSV
    csv_files = list(FILES_DIR.glob("*.csv")) + list(FILES_DIR.glob("*.CSV"))
    csv_files = sorted(set(csv_files))  # Remover duplicatas
    
    print(f"Encontrados {len(csv_files)} arquivos CSV\n")
    
    # Processar cada arquivo
    results = []
    for i, file_path in enumerate(csv_files, 1):
        print(f"\n[{i}/{len(csv_files)}]", end=" ")
        result = process_file(file_path)
        results.append(result)
    
    # Relatório final
    print("\n" + "="*80)
    print("RELATÓRIO FINAL - TODOS OS ARQUIVOS E190")
    print("="*80)
    
    total_files = len(results)
    total_lines = sum(r['lines'] for r in results)
    total_flights = sum(r['flights'] for r in results)
    total_hard_landings = sum(r['hard_landings'] for r in results)
    total_normal = sum(r['normal'] for r in results)
    max_g_all = max((r['max_g'] for r in results), default=0)
    
    print(f"\nESTATISTICAS GERAIS:")
    print(f"   Arquivos processados: {total_files}")
    print(f"   Total de linhas: {total_lines:,}")
    print(f"   Total de voos: {total_flights}")
    print(f"   Hard landings detectados: {total_hard_landings}")
    print(f"   Pousos normais: {total_normal}")
    if total_flights > 0:
        print(f"   Taxa de hard landing: {total_hard_landings/total_flights*100:.1f}%")
    else:
        print(f"   Taxa de hard landing: N/A (nenhum voo detectado)")
    print(f"   Max G em todos arquivos: {max_g_all:.3f}G")
    
    # Top 5 arquivos com mais hard landings
    print(f"\nTOP 5 - Mais Hard Landings:")
    sorted_results = sorted(results, key=lambda x: x['hard_landings'], reverse=True)
    for i, r in enumerate(sorted_results[:5], 1):
        if r['hard_landings'] > 0:
            print(f"   {i}. {r['file']}")
            print(f"      Hard landings: {r['hard_landings']}/{r['flights']} voos ({r['hard_landings']/r['flights']*100:.1f}%)")
            print(f"      Max G: {r['max_g']:.3f}G")
    
    # Arquivos com erros
    errors = [r for r in results if 'error' in r]
    if errors:
        print(f"\nARQUIVOS COM ERROS ({len(errors)}):")
        for r in errors:
            print(f"   - {r['file']}: {r['error']}")
    
    print("\n" + "="*80)
    print("PROCESSAMENTO COMPLETO!")
    print("="*80)
    
    # Salvar relatório
    report_file = Path("relatorio_e190_hard_landings.txt")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("RELATORIO - ANALISE DE HARD LANDING E190\n")
        f.write("="*80 + "\n\n")
        f.write(f"Arquivos processados: {total_files}\n")
        f.write(f"Total de voos: {total_flights}\n")
        f.write(f"Hard landings: {total_hard_landings}\n")
        if total_flights > 0:
            f.write(f"Taxa: {total_hard_landings/total_flights*100:.1f}%\n\n")
        else:
            f.write("Taxa: N/A (nenhum voo detectado)\n\n")
        f.write("Detalhes por arquivo:\n")
        f.write("-"*80 + "\n")
        for r in sorted_results:
            f.write(f"\n{r['file']}\n")
            f.write(f"  Linhas: {r['lines']:,}\n")
            f.write(f"  Voos: {r['flights']}\n")
            f.write(f"  Hard landings: {r['hard_landings']}\n")
            f.write(f"  Max G: {r['max_g']:.3f}G\n")
    
    print(f"\nRelatorio salvo: {report_file}")


if __name__ == "__main__":
    main()

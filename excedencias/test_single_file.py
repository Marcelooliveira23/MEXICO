"""
Teste detalhado de análise de hard landing em arquivo individual
"""
import pandas as pd
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.csv_parser import CSVParser
from services.rules_engine import RulesEngine

def run_file(filepath):
    print(f"\n{'='*80}")
    print(f"TESTANDO: {Path(filepath).name}")
    print(f"{'='*80}\n")
    
    # Configurar parser e engine
    parser = CSVParser()
    engine = RulesEngine()
    
    # Carregar arquivo
    print("1. Carregando arquivo...")
    df = parser.parse_file(Path(filepath))
    
    if df is None:
        print("❌ Erro ao carregar arquivo")
        return
    
    print(f"✅ {len(df)} linhas carregadas\n")
    
    # Mostrar colunas mapeadas
    print("2. Colunas disponíveis (primeiras 10):")
    for i, col in enumerate(df.columns[:10]):
        print(f"   - {col}")
    if len(df.columns) > 10:
        print(f"   ... e mais {len(df.columns) - 10} colunas\n")
    
    # Identificar coluna de aceleração
    accel_cols = [col for col in df.columns if 'accel' in col.lower() or 'normaccel' in col.lower()]
    print(f"3. Colunas de aceleração encontradas: {accel_cols}\n")
    
    # Analisar hard landing
    print("4. Executando análise de Hard Landing...")
    print("-" * 80)
    
    results = engine.analyze(df, event_type='hard_landing', aircraft_family='E1')
    
    print("\n5. RESULTADOS:")
    print("-" * 80)
    
    for result in results:
        print(f"\n📊 Voo #{result.flight_number}")
        print(f"   Status: {result.status}")
        print(f"   Nível: {result.severity}")
        
        if hasattr(result, 'vertical_acceleration') and result.vertical_acceleration:
            vert = result.vertical_acceleration
            print(f"\n   ACELERAÇÃO VERTICAL:")
            print(f"      Max G: {vert.get('max_g', 'N/A')}")
            print(f"      Thresholds:")
            thresholds = vert.get('thresholds', {})
            print(f"         Low: {thresholds.get('low', 'N/A')}")
            print(f"         High: {thresholds.get('high', 'N/A')}")
            print(f"         Engine: {thresholds.get('engine', 'N/A')}")
            print(f"      Status: {vert.get('status', 'N/A')}")
        
        if hasattr(result, 'details') and result.details:
            print(f"\n   Detalhes: {result.details}")
    
    print(f"\n{'='*80}")
    print(f"Total de voos analisados: {len(results)}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    # Testar arquivo com maior G (2.398G)
    run_file(r"E:\Projetos\excedencias\data\XA-ALU _HL_13AGO25_FLT651.CSV")

"""
Teste rápido para verificar detecção de Hard Landing
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.hard_landing_analyzer import HardLandingAnalyzer
from services.csv_parser import CSVParser

def test_detection():
    """Testa detecção com dados reais"""
    
    # Carregar dados de teste
    csv_file = Path("test_data_e175_hard_landing.csv")
    parser = CSVParser()
    df = parser.parse_file(csv_file)
    
    print("=" * 80)
    print("TESTE DE DETECÇÃO DE HARD LANDING")
    print("=" * 80)
    print(f"\nArquivo: {csv_file}")
    print(f"Linhas: {len(df)}")
    print(f"Colunas: {list(df.columns)}")
    
    # Verificar valores máximos
    if 'VERT_ACCEL' in df.columns:
        max_g = df['VERT_ACCEL'].max()
        print(f"\n⚠️  ACELERAÇÃO VERTICAL MÁXIMA: {max_g:.2f} G")
    
    # Executar análise
    analyzer = HardLandingAnalyzer()
    
    # Peso: 75000 lb = 34019 kg
    weight_kg = 34019
    model = 'E175'
    
    print(f"\nModelo: {model}")
    print(f"Peso: {weight_kg:.0f} kg ({weight_kg * 2.20462:.0f} lb)")
    
    results = analyzer.analyze(df, weight_kg, model)
    
    print(f"\n{'=' * 80}")
    print(f"RESULTADOS DA ANÁLISE")
    print(f"{'=' * 80}")
    print(f"\nVoos detectados: {len(results)}")
    
    for i, result in enumerate(results, 1):
        print(f"\n{'─' * 80}")
        print(f"VOO {i}")
        print(f"{'─' * 80}")
        print(f"Status: {result.status}")
        print(f"Severidade: {result.severity}")
        print(f"Mensagem: {result.message}")
        print(f"Monitores críticos: {result.critical_monitors}")
        
        print(f"\n📊 Monitor 1 - Aceleração Vertical:")
        vert = result.vertical_accel
        print(f"   Status: {vert['status']}")
        if 'max_g' in vert:
            print(f"   Max G: {vert['max_g']:.3f}")
        if 'thresholds' in vert:
            th = vert['thresholds']
            print(f"   Limites: Low={th.get('low', 'N/A'):.2f}, "
                  f"High={th.get('high', 'N/A'):.2f}, "
                  f"Engine={th.get('engine', 'N/A'):.2f}")
        
        print(f"\n📊 Monitor 2 - Roll Rate:")
        roll = result.roll_rate
        print(f"   Status: {roll['status']}")
        if 'max_roll_rate' in roll:
            print(f"   Max Rate: {roll['max_roll_rate']:.2f} deg/s")
        
        print(f"\n📊 Monitor 3 - Pitch Rate:")
        pitch = result.pitch_rate
        print(f"   Status: {pitch['status']}")
        if 'min_pitch_rate' in pitch:
            print(f"   Min Rate: {pitch['min_pitch_rate']:.2f} deg/s")
    
    print(f"\n{'=' * 80}")
    
    # Verificação final
    if results and results[0].status != 'NORMAL':
        print("\n✅ DETECÇÃO FUNCIONANDO - Hard Landing identificado!")
    else:
        print("\n❌ PROBLEMA - Hard Landing NÃO foi detectado!")
        print("\n🔍 Investigando motivos:")
        if 'VERT_ACCEL' in df.columns:
            print(f"   - Aceleração máxima: {df['VERT_ACCEL'].max():.2f} G")
            print(f"   - Esperado: > 1.85 G para detecção")

if __name__ == "__main__":
    test_detection()

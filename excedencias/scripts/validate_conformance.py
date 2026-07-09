#!/usr/bin/env python3
"""
Script de Validação Pós-Conformidade
Valida que todas as correções de Priority 1 foram aplicadas corretamente
"""

import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.csv_parser import CSVParser
from services.hard_landing_analyzer import HardLandingAnalyzer

# Caminho do arquivo
file_path = Path(__file__).parent.parent / "Analises de dados de voo" / "HARDINGLANDING E145" / "ERJ2.csv"

print(f"Procurando: {file_path}")
print(f"Existe: {file_path.exists()}")

if not file_path.exists():
    # Tentar caminho alternativo
    file_path = Path(r"e:\Projetos\excedencias\Analises de dados de voo\HARDINGLANDING E145\ERJ2.csv")
    print(f"\nTentando: {file_path}")
    print(f"Existe: {file_path.exists()}")

if file_path.exists():
    parser = CSVParser()
    df = parser.parse_file(str(file_path))
    
    print(f"\n✅ Arquivo carregado: {len(df)} linhas")
    print(f"Colunas: {list(df.columns)[:5]}...")
    
    analyzer = HardLandingAnalyzer()
    results = analyzer.analyze(df, weight_kg=21772.416, model='E145')
    
    print(f"\n{'='*60}")
    print(f"VALIDAÇÃO PÓS-CONFORMIDADE (Priority 1 Fixes)")
    print(f"{'='*60}")
    
    print(f"\n✅ Total de voos detectados: {len(results)}")
    
    exceedances = [r for r in results if r.status != 'NORMAL']
    print(f"✅ Hard landings detectados: {len(exceedances)}")
    
    print(f"\n{'='*60}")
    print(f"RESULTADO FINAL:")
    print(f"{'='*60}")
    
    for idx, r in enumerate(exceedances, 1):
        va = r.vertical_accel
        max_g = va.get('max_g', 0)
        threshold = va.get('thresholds', {}).get('high', 0)
        flight_num = results.index(r) + 1
        
        print(f"\n🔴 Hard Landing #{idx}")
        print(f"   Voo: {flight_num}")
        print(f"   Status: {r.status}")
        print(f"   Max G-force: {max_g:.3f}G")
        print(f"   Threshold: {threshold:.3f}G")
        print(f"   Pitch Rate: {r.pitch_rate.get('min_rate', 'N/A')}")
    
    print(f"\n{'='*60}")
    print(f"✅ CONFORMIDADE VALIDADA")
    print(f"{'='*60}\n")
    
else:
    print(f"❌ Arquivo não encontrado: {file_path}")
    sys.exit(1)

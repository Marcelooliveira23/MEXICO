"""
Análise detalhada do arquivo ALU para debug
"""
import pandas as pd
import sys
sys.path.insert(0, 'src')

from services.csv_parser import CSVParser
from services.csv_column_mapper import CSVColumnMapper
from services.hard_landing_analyzer import HardLandingAnalyzer
from services.rules_engine import RulesEngine

# Arquivo
file_path = r"c:\Users\mrced\OneDrive\Documents\hard landing\XA-ALU _HL_13AGO25_FLT651.CSV"

print("=" * 80)
print("ANÁLISE DETALHADA DO ARQUIVO ALU")
print("=" * 80)

# 1. Leitura RAW
print("\n[1] LEITURA RAW DO CSV")
df_raw = pd.read_csv(file_path, skiprows=1)
print(f"Shape: {df_raw.shape}")
print(f"Colunas: {list(df_raw.columns)}")

# 2. Estatísticas de G
g_col = "G's"
print(f"\n[2] ESTATÍSTICAS DE ACELERAÇÃO VERTICAL (coluna '{g_col}')")
print(df_raw[g_col].describe())
max_g = df_raw[g_col].max()
min_g = df_raw[g_col].min()
print(f"\n*** MÁXIMO G: {max_g:.6f} G ***")
print(f"*** MÍNIMO G: {min_g:.6f} G ***")

# 3. Peso
peso_lbs = df_raw["lbs"].dropna().iloc[0]
peso_kg = peso_lbs * 0.453592
print(f"\n[3] PESO DA AERONAVE")
print(f"Peso: {peso_lbs:.0f} lbs = {peso_kg:.0f} kg")

# 4. Parsear com CSV Parser
print(f"\n[4] PARSEANDO COM CSV PARSER")
parser = CSVParser()
try:
    df_parsed = parser.parse_file(file_path)
    print(f"✅ Parseado com sucesso: {df_parsed.shape}")
    print(f"Colunas parseadas: {list(df_parsed.columns)}")
    
    # 5. Colunas já foram normalizadas pelo parser
    print(f"\n[5] COLUNAS JÁ NORMALIZADAS PELO PARSER")
    print(f"Colunas: {list(df_parsed.columns)}")
    
    # 6. Verificar se temos vertical_acceleration
    if 'vertical_acceleration' in df_parsed.columns:
        print(f"\n✅ Coluna 'vertical_acceleration' encontrada!")
        
        # Converter para numérico
        df_parsed['vertical_acceleration'] = pd.to_numeric(df_parsed['vertical_acceleration'], errors='coerce')
        df_parsed['gross_weight'] = pd.to_numeric(df_parsed['gross_weight'], errors='coerce')
        
        max_g_parsed = df_parsed['vertical_acceleration'].max()
        min_g_parsed = df_parsed['vertical_acceleration'].min()
        
        print(f"Max G (após normalização): {max_g_parsed:.6f}")
        print(f"Min G (após normalização): {min_g_parsed:.6f}")
    else:
        print(f"\n❌ ERRO: Coluna 'vertical_acceleration' NÃO encontrada!")
        print("Colunas disponíveis:", [c for c in df_parsed.columns if c])
    
    # 7. Analisar com Hard Landing Analyzer
    print(f"\n[6] ANÁLISE COM HARD LANDING ANALYZER")
    print(f"Modelo assumido: E175")
    print(f"Peso: {peso_kg:.0f} kg")
    
    # Thresholds esperados para E175 com peso ~40000 kg
    print(f"\nTHRESHOLDS MODO AGRESSIVO E175:")
    print(f"  LOW:    1.800 - 2.200 G")
    print(f"  HIGH:   2.100 - 2.500 G")
    print(f"  SEVERE: 2.400 - 2.800 G (Engine Inspection)")
    
    print(f"\nTHRESHOLDS AMM PADRÃO:")
    print(f"  Limite: 2.600 G")
    
    analyzer = HardLandingAnalyzer()
    result = analyzer.analyze_hard_landing(df_parsed, 'E175', peso_kg)
    
    print(f"\n{'='*80}")
    print(f"RESULTADO DA ANÁLISE:")
    print(f"{'='*80}")
    print(f"Hard Landing Detectado: {result.is_hard_landing}")
    print(f"Severidade: {result.severity_level}")
    print(f"Max Vertical Accel: {result.max_vertical_accel:.6f} G")
    
    if result.is_hard_landing:
        print(f"\n⚠️ EXCEDÊNCIA DETECTADA!")
        print(f"Threshold violado: {result.threshold_type}")
        print(f"Ações recomendadas:")
        for action in result.recommended_actions[:3]:
            print(f"  - {action}")
    else:
        print(f"\n✅ SEM EXCEDÊNCIA")
        print(f"Valor máximo ({max_g:.6f}G) está abaixo do threshold LOW (1.800G)")
    
    # 8. Comparação com regras da web
    print(f"\n{'='*80}")
    print(f"COMPARAÇÃO COM REGRAS (threshold original = 2.6G):")
    print(f"{'='*80}")
    if max_g > 2.6:
        print(f"❌ VIOLAÇÃO AMM PADRÃO: {max_g:.6f}G > 2.600G")
    elif max_g > 1.8:
        print(f"⚠️ VIOLAÇÃO MODO AGRESSIVO: {max_g:.6f}G > 1.800G (LOW)")
    else:
        print(f"✅ SEM VIOLAÇÃO: {max_g:.6f}G < 1.800G")
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

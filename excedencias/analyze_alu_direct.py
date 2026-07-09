"""
Análise DIRETA do arquivo ALU (sem CSV Parser)
"""
import pandas as pd
import sys
sys.path.insert(0, 'src')

from services.hard_landing_analyzer import HardLandingAnalyzer

# Arquivo
file_path = r"c:\Users\mrced\OneDrive\Documents\hard landing\XA-ALU _HL_13AGO25_FLT651.CSV"

print("="*80)
print("ANALISE DO ARQUIVO XA-ALU - Hard Landing Flight 651")
print("="*80)

# Ler CSV pulando a primeira linha (header secundario)
df = pd.read_csv(file_path, skiprows=1)

# Mapear colunas manualmente
column_mapping = {
    'Unnamed: 0': 'sample',
    'Unnamed: 1': 'time',
    'Day': 'day',
    'Text': 'flight_number',
    'lbs': 'gross_weight',
    'Unnamed: 5': 'air_ground_switch',
    'degrees': 'roll',
    'degrees.1': 'pitch',
    "G's": 'vertical_acceleration',
    'Unnamed: 9': 'error'
}

df = df.rename(columns=column_mapping)

# Converter para numérico
df['vertical_acceleration'] = pd.to_numeric(df['vertical_acceleration'], errors='coerce')
df['gross_weight'] = pd.to_numeric(df['gross_weight'], errors='coerce')
df['roll'] = pd.to_numeric(df['roll'], errors='coerce')
df['pitch'] = pd.to_numeric(df['pitch'], errors='coerce')

# Limpar dados
df = df.dropna(subset=['vertical_acceleration'])

# Estatísticas
max_g = df['vertical_acceleration'].max()
min_g = df['vertical_acceleration'].min()
peso_lbs = df['gross_weight'].dropna().iloc[0]
peso_kg = peso_lbs * 0.453592

print(f"\n[DADOS DO VOO]")
print(f"Voo: SLI651 (13 AGO 2025)")
print(f"Aeronave: XA-ALU")
print(f"Peso: {peso_lbs:.0f} lbs = {peso_kg:.0f} kg")
print(f"Total de amostras: {len(df)}")

print(f"\n[ACELERACAO VERTICAL]")
print(f"Maximo G: {max_g:.6f} G")
print(f"Minimo G: {min_g:.6f} G")
print(f"Media: {df['vertical_acceleration'].mean():.6f} G")

# THRESHOLDS
print(f"\n[THRESHOLDS E175 - MODO AGRESSIVO]")
print(f"Peso: {peso_kg:.0f} kg")
print(f"  LOW (Inspecao Visual):    1.800 - 2.200 G")
print(f"  HIGH (Inspecao Detalhada):2.100 - 2.500 G") 
print(f"  SEVERE (Motor):           2.400 - 2.800 G")

# COMPARACAO
print(f"\n[COMPARACAO COM THRESHOLDS]")
if max_g >= 2.4:
    severity = "SEVERE - ENGINE INSPECTION"
    status = "EXCEDENCIA SEVERA"
elif max_g >= 2.1:
    severity = "HIGH"
    status = "EXCEDENCIA ALTA"
elif max_g >= 1.8:
    severity = "LOW"
    status = "EXCEDENCIA LEVE"
else:
    severity = "NONE"
    status = "SEM EXCEDENCIA"

print(f"Valor maximo: {max_g:.6f} G")
print(f"Status: {status}")
print(f"Severidade: {severity}")

# ANALISE COM HARD LANDING ANALYZER
print(f"\n[ANALISE COM HARD LANDING ANALYZER]")
try:
    analyzer = HardLandingAnalyzer()
    results = analyzer.analyze(df, peso_kg, 'E175')  # Retorna LISTA de resultados
    
    print(f"\nVoos analisados: {len(results)}")
    
    hard_landings = [r for r in results if r.is_hard_landing]
    
    if hard_landings:
        print(f"\n*** {len(hard_landings)} HARD LANDING(S) DETECTADO(S) ***")
        for i, result in enumerate(hard_landings, 1):
            print(f"\nVoo #{i}:")
            print(f"  Severidade: {result.severity_level}")
            print(f"  Max Vertical Accel: {result.max_vertical_accel:.6f} G")
            print(f"  Threshold Type: {result.threshold_type if hasattr(result, 'threshold_type') else 'MODO AGRESSIVO'}")
            print(f"  Acoes Recomendadas:")
            for j, action in enumerate(result.recommended_actions[:3], 1):
                print(f"    {j}. {action}")
    else:
        print(f"\n*** NENHUM HARD LANDING DETECTADO ***")
        print(f"Total de voos: {len(results)}")
        if results:
            max_g_found = max([r.max_vertical_accel for r in results])
            print(f"Maior G detectado: {max_g_found:.6f} G")
        
except Exception as e:
    print(f"ERRO na analise: {e}")
    import traceback
    traceback.print_exc()

print(f"\n[CONCLUSAO]")
print("="*80)
if max_g >= 1.8:
    print("EXCEDENCIA DETECTADA!")
    print(f"O valor de {max_g:.3f}G EXCEDE o threshold MODO AGRESSIVO de 1.800G")
    print("Inspecao e necessaria conforme AMM 05-50-03")
else:
    print(f"Sem excedencia. Valor maximo {max_g:.3f}G < 1.800G")
print("="*80)

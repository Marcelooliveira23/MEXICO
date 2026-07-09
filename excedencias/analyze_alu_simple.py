"""
Análise SIMPLES do XA-ALU - Busca excedências diretas
"""
import pandas as pd

file_path = r"c:\Users\mrced\OneDrive\Documents\hard landing\XA-ALU _HL_13AGO25_FLT651.CSV"

print("="*80)
print("ANÁLISE SIMPLIFICADA XA-ALU - Flight 651 (13 AGO 2025)")
print("="*80)

# Ler CSV
df = pd.read_csv(file_path, skiprows=1)

# Mapear colunas
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

# Converter
df['vertical_acceleration'] = pd.to_numeric(df['vertical_acceleration'], errors='coerce')
df['gross_weight'] = pd.to_numeric(df['gross_weight'], errors='coerce')
df = df.dropna(subset=['vertical_acceleration'])

# Estatísticas
max_g = df['vertical_acceleration'].max()
peso_lbs = df['gross_weight'].dropna().iloc[0]
peso_kg = peso_lbs * 0.453592

# Encontrar onde está o pico
max_idx = df['vertical_acceleration'].idxmax()
max_row = df.loc[max_idx]

print(f"\nDADOS DO VOO:")
print(f"   Aeronave: XA-ALU")
print(f"   Voo: SLI651")
print(f"   Data: 13 AGO 2025")
print(f"   Peso: {peso_lbs:.0f} lbs = {peso_kg:.0f} kg")
print(f"   Total amostras: {len(df):,}")

print(f"\nACELERACAO VERTICAL:")
print(f"   Maximo: {max_g:.6f} G")
print(f"   Minimo: {df['vertical_acceleration'].min():.6f} G")
print(f"   Media: {df['vertical_acceleration'].mean():.6f} G")

print(f"\nPICO DE ACELERACAO:")
print(f"   Indice: {max_idx}")
print(f"   Valor: {max_g:.6f} G")
print(f"   Roll: {max_row['roll']:.2f}°")
print(f"   Pitch: {max_row['pitch']:.2f}°")

print(f"\nTHRESHOLDS E175 MODO AGRESSIVO ({peso_kg:.0f} kg):")
print(f"   LOW:    1.800 - 2.200 G -> Inspecao Visual")
print(f"   HIGH:   2.100 - 2.500 G -> Inspecao Detalhada")
print(f"   SEVERE: 2.400 - 2.800 G -> Inspecao Motor")

print(f"\nANALISE:")
if max_g >= 2.4:
    severity = "SEVERE"
    nivel = "SEVERO - INSPECAO DE MOTOR"
    color = "***"
elif max_g >= 2.1:
    severity = "HIGH"
    nivel = "ALTO - INSPECAO DETALHADA"
    color = "**"
elif max_g >= 1.8:
    severity = "LOW"
    nivel = "BAIXO - INSPECAO VISUAL"
    color = "*"
else:
    severity = "NONE"
    nivel = "SEM EXCEDENCIA"
    color = "OK"

print(f"   {color} Severidade: {severity}")
print(f"   {color} Nivel: {nivel}")
print(f"   {color} Valor: {max_g:.6f} G")

# COMPARACAO COM AMM
print(f"\nCOMPARACAO COM AMM 05-50-03:")
print(f"   Threshold AMM Padrao: 2.600 G")
print(f"   Valor detectado: {max_g:.6f} G")
if max_g >= 2.6:
    print(f"   >> AMM PADRAO detectaria (>= 2.6G)")
else:
    print(f"   XX AMM PADRAO NAO detectaria (< 2.6G)")
    print(f"   >> MODO AGRESSIVO detecta ({severity})")

print(f"\n" + "=" * 80)
if max_g >= 1.8:
    print(f"   *** EXCEDENCIA DETECTADA!")
    print(f"   Valor {max_g:.3f}G EXCEDE threshold de 1.800G")
    print(f"   Acao requerida conforme AMM 05-50-03: {nivel}")
else:
    print(f"   OK SEM EXCEDENCIA")
    print(f"   Valor {max_g:.3f}G < 1.800G")
print(f"=" * 80)

"""
Teste completo do fluxo de análise de Hard Landing
"""
import sys
sys.path.insert(0, 'src')

from services.csv_parser import CSVParser
from services.hard_landing_analyzer import HardLandingAnalyzer

print("="*80)
print("TESTE COMPLETO DE FLUXO - HARD LANDING XA-ALU")
print("="*80)

# 1. Parse do arquivo
file_path = r"c:\Users\mrced\OneDrive\Documents\hard landing\XA-ALU _HL_13AGO25_FLT651.CSV"
print(f"\n[1] PARSEANDO ARQUIVO...")
print(f"Arquivo: {file_path}")

parser = CSVParser()
df = parser.parse_file(file_path)

print(f"✅ Shape: {df.shape}")
print(f"✅ Colunas: {list(df.columns)}")

# 2. Extrair peso
print(f"\n[2] EXTRAINDO PESO...")
weight_cols = [col for col in df.columns if 'weight' in col.lower() or 'gross' in col.lower()]
print(f"Colunas de peso encontradas: {weight_cols}")

if weight_cols:
    weight_lb = df[weight_cols[0]].dropna().iloc[0]
    weight_kg = float(weight_lb) * 0.453592
    print(f"✅ Peso: {weight_lb:.0f} lb = {weight_kg:.0f} kg")
else:
    weight_kg = 40000 * 0.453592
    print(f"⚠️  Usando peso padrão: {weight_kg:.0f} kg")

# 3. Detectar modelo pelo peso
print(f"\n[3] DETECTANDO MODELO PELO PESO...")
if weight_kg < 36000:
    model = 'E170'
elif weight_kg < 42000:
    model = 'E175'
elif weight_kg < 51000:
    model = 'E190'
else:
    model = 'E195'
print(f"✅ Modelo detectado: {model}")

# 4. Verificar colunas críticas
print(f"\n[4] VERIFICANDO COLUNAS CRÍTICAS...")
critical_cols = {
    'vertical_acceleration': ['normaccel', 'norm_accel', 'vertical_accel', 'vertical_acceleration', 'nz'],
    'roll': ['roll', 'bank', 'phi'],
    'pitch': ['pitch', 'theta']
}

found_cols = {}
for std_name, variations in critical_cols.items():
    for col in df.columns:
        if col.lower() in [v.lower() for v in variations]:
            found_cols[std_name] = col
            print(f"✅ {std_name}: '{col}' encontrada")
            break
    if std_name not in found_cols:
        print(f"❌ {std_name}: NÃO ENCONTRADA")

# 5. Verificar dados nas colunas
print(f"\n[5] VERIFICANDO DADOS NAS COLUNAS...")
for std_name, col_name in found_cols.items():
    non_null = df[col_name].notna().sum()
    if non_null > 0:
        min_val = df[col_name].min()
        max_val = df[col_name].max()
        print(f"✅ {std_name} ('{col_name}'): {non_null} valores válidos, Range: [{min_val:.3f}, {max_val:.3f}]")
    else:
        print(f"❌ {std_name} ('{col_name}'): SEM DADOS VÁLIDOS")

# 6. Executar análise
print(f"\n[6] EXECUTANDO ANÁLISE COM HARDLANDINGANALYZER...")
analyzer = HardLandingAnalyzer()

print(f"Peso: {weight_kg:.0f} kg")
print(f"Modelo: {model}")
print(f"DataFrame shape: {df.shape}")

results = analyzer.analyze(df, weight_kg, model)

print(f"\n✅ Análise concluída! Resultados: {len(results)} voo(s)")

# 7. Mostrar resultados detalhados
for i, result in enumerate(results, 1):
    print(f"\n{'='*80}")
    print(f"VOO {i}")
    print(f"{'='*80}")
    print(f"Status: {result.status}")
    print(f"Severidade: {result.severity}")
    print(f"Mensagem: {result.message}")
    print(f"Monitores críticos: {result.critical_monitors}")
    
    print(f"\nMonitor 1 - Aceleração Vertical:")
    print(f"  Status: {result.vertical_accel.get('status', 'N/A')}")
    if 'max_g' in result.vertical_accel:
        print(f"  Max G: {result.vertical_accel['max_g']:.3f}")
    if 'thresholds' in result.vertical_accel:
        th = result.vertical_accel['thresholds']
        print(f"  Thresholds: LOW={th.get('low', 'N/A')}, HIGH={th.get('high', 'N/A')}, ENGINE={th.get('engine', 'N/A')}")
    
    print(f"\nMonitor 2 - Roll Rate:")
    print(f"  Status: {result.roll_rate.get('status', 'N/A')}")
    if 'max_rate' in result.roll_rate and result.roll_rate['max_rate']:
        print(f"  Max Rate: {result.roll_rate['max_rate']:.2f} deg/s")
    
    print(f"\nMonitor 3 - Pitch Rate:")
    print(f"  Status: {result.pitch_rate.get('status', 'N/A')}")
    if 'min_rate' in result.pitch_rate and result.pitch_rate['min_rate']:
        print(f"  Min Rate: {result.pitch_rate['min_rate']:.2f} deg/s")

print(f"\n{'='*80}")
print("TESTE COMPLETO FINALIZADO")
print(f"{'='*80}")

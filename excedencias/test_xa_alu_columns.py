"""Teste de mapeamento de colunas para XA-ALU"""
import sys
sys.path.insert(0, 'src')

from services.csv_parser import CSVParser

file_path = r"c:\Users\mrced\OneDrive\Documents\hard landing\XA-ALU _HL_13AGO25_FLT651.CSV"

parser = CSVParser()
df = parser.parse_file(file_path)

print("="*80)
print("TESTE DE MAPEAMENTO DE COLUNAS - XA-ALU")
print("="*80)
print(f"\nShape: {df.shape}")
print(f"\nColunas após mapeamento:")
for i, col in enumerate(df.columns, 1):
    print(f"{i:2d}. {col}")

print(f"\nPrimeiras 3 linhas:")
print(df.head(3))

print(f"\nVerificando colunas críticas:")
critical_cols = ['vertical_acceleration', 'roll', 'pitch', 'gross_weight', 'timestamp']
for col in critical_cols:
    if col in df.columns:
        non_null = df[col].notna().sum()
        print(f"✓ {col}: {non_null} valores não-nulos")
    else:
        print(f"✗ {col}: NÃO ENCONTRADA")

# Verificar valores de aceleração vertical
if 'vertical_acceleration' in df.columns:
    valid_accel = df['vertical_acceleration'].dropna()
    if len(valid_accel) > 0:
        print(f"\nACELERAÇÃO VERTICAL:")
        print(f"  Min: {valid_accel.min():.3f} G")
        print(f"  Max: {valid_accel.max():.3f} G")
        print(f"  Valores válidos: {len(valid_accel)}")
    else:
        print(f"\n✗ vertical_acceleration existe mas está vazia!")

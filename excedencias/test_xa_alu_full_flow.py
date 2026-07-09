"""
Teste completo do fluxo XA-ALU para debugging
Simula exatamente o que a UI faz
"""
import sys
from pathlib import Path
import pandas as pd

# Adicionar src ao path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from services.csv_parser import CSVParser
from services.hard_landing_analyzer import HardLandingAnalyzer
from utils.logger import logger

def detect_model_from_weight(df):
    """Detecta modelo baseado no peso (MESMA LÓGICA EXATA DA UI)"""
    weight_cols = [col for col in df.columns if 'weight' in col.lower() or 'gross' in col.lower()]
    if not weight_cols:
        return None, None
    
    weight_data = df[weight_cols[0]]
    if isinstance(weight_data, pd.DataFrame):
        weight_series = weight_data.iloc[:, 0]
    else:
        weight_series = weight_data
    
    if isinstance(weight_series, pd.DataFrame):
        weight_series = weight_series.iloc[:, 0]
    
    first_weight_val = weight_series.dropna().iloc[0]
    
    # Converter para kg usando MESMA LÓGICA da UI (_weight_to_kg)
    col_name = weight_cols[0].lower()
    
    # Prioridade: identificar unidade pelo nome da coluna
    if "kg" in col_name and "lb" not in col_name:
        weight_kg = first_weight_val
    elif "lb" in col_name or "lbs" in col_name:
        weight_kg = first_weight_val * 0.453592
    # Heurística quando unidade não é clara
    # Valores típicos em kg: 18k-60k | em lb: 40k-140k
    elif first_weight_val > 60000:
        weight_kg = first_weight_val * 0.453592
        print(f"  ⚠ Heurística aplicada: {first_weight_val:.1f} > 60000, assumindo libras")
    else:
        weight_kg = first_weight_val
    
    print(f"\n{'='*80}")
    print(f"DETECÇÃO DE MODELO POR PESO")
    print(f"{'='*80}")
    print(f"Coluna: {weight_cols[0]}")
    print(f"Valor bruto: {first_weight_val}")
    print(f"Peso em kg: {weight_kg:.1f} kg")
    
    # Thresholds da UI
    if weight_kg < 26000:
        model = 'E145'
    elif weight_kg < 33000:
        model = 'E170'
    elif weight_kg < 39000:
        model = 'E175'
    elif weight_kg < 48000:
        model = 'E190'
    else:
        model = 'E195'
    
    print(f"Modelo detectado: {model}")
    print(f"  E145: < 26000 kg")
    print(f"  E170: 26000-33000 kg")
    print(f"  E175: 33000-39000 kg ← ATUAL THRESHOLD")
    print(f"  E190: 39000-48000 kg ← DEVERIA SER ESTE")
    print(f"  E195: >= 48000 kg")
    print(f"{'='*80}\n")
    
    return model, weight_kg

def main():
    # Caminho do arquivo
    csv_file = Path(r"c:\Users\mrced\OneDrive\Documents\hard landing\XA-ALU _HL_13AGO25_FLT651.CSV")
    
    if not csv_file.exists():
        print(f"❌ Arquivo não encontrado: {csv_file}")
        return
    
    print(f"\n{'='*80}")
    print(f"TESTE COMPLETO - FLUXO XA-ALU")
    print(f"{'='*80}")
    print(f"Arquivo: {csv_file.name}")
    print(f"{'='*80}\n")
    
    # ETAPA 1: Parse do CSV
    print("ETAPA 1: Parse CSV")
    parser = CSVParser()
    df = parser.parse_file(csv_file)
    print(f"✓ DataFrame carregado: {len(df)} linhas, {len(df.columns)} colunas")
    print(f"  Colunas: {list(df.columns)}\n")
    
    # ETAPA 2: Verificar coluna de aceleração
    print("ETAPA 2: Verificar mapeamento de colunas")
    if 'vertical_acceleration' in df.columns:
        print(f"✓ Coluna 'vertical_acceleration' encontrada")
        valid_accel = df['vertical_acceleration'].dropna()
        print(f"  Valores válidos: {len(valid_accel)}")
        print(f"  Min: {valid_accel.min():.3f} G")
        print(f"  Max: {valid_accel.max():.3f} G")
    else:
        print(f"❌ Coluna 'vertical_acceleration' NÃO encontrada")
    print()
    
    # ETAPA 3: Detectar modelo por peso
    print("ETAPA 3: Detectar modelo")
    model, weight_kg = detect_model_from_weight(df)
    if not model:
        print("❌ Não foi possível detectar modelo")
        return
    
    # ETAPA 4: Executar análise
    print("ETAPA 4: Executar análise HardLandingAnalyzer")
    print(f"{'='*80}")
    analyzer = HardLandingAnalyzer()
    results = analyzer.analyze(df, weight_kg, model)
    print(f"{'='*80}\n")
    
    # ETAPA 5: Mostrar resultados
    print("ETAPA 5: Resultados")
    print(f"{'='*80}")
    if not results:
        print("❌ Nenhum resultado retornado")
    else:
        for i, result in enumerate(results):
            print(f"\nVoo {i+1}:")
            print(f"  Status geral: {result.status}")
            
            # Vertical Accel
            vert = result.vertical_accel
            if vert:
                print(f"\n  Monitor 1 - Vertical Acceleration:")
                print(f"    Status: {vert.get('status', 'N/A')}")
                print(f"    Max G: {vert.get('max_g', 'N/A')}")
                thresholds = vert.get('thresholds', {})
                if thresholds:
                    print(f"    Thresholds: LOW={thresholds.get('low', 'N/A')}, HIGH={thresholds.get('high', 'N/A')}, ENGINE={thresholds.get('engine', 'N/A')}")
            else:
                print(f"  Monitor 1: NO_DATA")
            
            # Roll Rate
            roll = result.roll_rate
            if roll and roll.get('status') != 'NO_DATA':
                print(f"\n  Monitor 2 - Roll Rate:")
                print(f"    Status: {roll.get('status', 'N/A')}")
                print(f"    Max Rate: {roll.get('max_rate', 'N/A')}")
            else:
                print(f"  Monitor 2: NO_DATA ou não aplicável")
            
            # Pitch Rate
            pitch = result.pitch_rate
            if pitch and pitch.get('status') != 'NO_DATA':
                print(f"\n  Monitor 3 - Pitch Rate:")
                print(f"    Status: {pitch.get('status', 'N/A')}")
                print(f"    Min Rate: {pitch.get('min_rate', 'N/A')}")
            else:
                print(f"  Monitor 3: NO_DATA ou não aplicável")
    
    print(f"\n{'='*80}")
    print("TESTE CONCLUÍDO")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()

"""
Testa EXATAMENTE os mesmos métodos que a UI usa
Importa e chama _extract_weight e _detect_model_from_data da análise_view.py
"""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from services.csv_parser import CSVParser
from services.hard_landing_analyzer import HardLandingAnalyzer
from utils.logger import logger

# Simular o método _weight_to_kg como está na UI
def _weight_to_kg(weight_value, col_name: str = None):
    """Converte peso para kg com heurística de unidade."""
    if weight_value is None:
        return None

    try:
        weight_float = float(weight_value)
    except Exception:
        return None

    col_lower = (col_name or "").lower()

    # Prioridade: identificar unidade pelo nome da coluna
    if "kg" in col_lower and "lb" not in col_lower:
        logger.info(f"Peso detectado em kg via coluna '{col_name}': {weight_float:.1f} kg")
        return weight_float
    if "lb" in col_lower or "lbs" in col_lower:
        weight_kg = weight_float * 0.453592
        logger.info(f"Peso detectado em lb via coluna '{col_name}': {weight_float:.1f} lb = {weight_kg:.1f} kg")
        return weight_kg

    # Heurística quando unidade não é clara
    # Valores típicos em kg: 18k-60k | em lb: 40k-140k
    if weight_float > 60000:
        weight_kg = weight_float * 0.453592
        logger.info(f"Peso presumido em lb (heurística): {weight_float:.1f} lb = {weight_kg:.1f} kg")
        return weight_kg

    logger.info(f"Peso presumido em kg (heurística): {weight_float:.1f} kg")
    return weight_float


# Simular o método _detect_model_from_data como está na UI
def _detect_model_from_data(df):
    """Detecta modelo da aeronave a partir dos dados do arquivo"""
    # Verificar pelo peso (gross_weight típico por modelo)
    weight_cols = [col for col in df.columns if 'weight' in col.lower() or 'gross' in col.lower()]
    if weight_cols:
        try:
            # Se há colunas duplicadas, usar iloc[:, 0]
            weight_data = df[weight_cols[0]]
            if isinstance(weight_data, pd.DataFrame):
                weight_series = weight_data.iloc[:, 0]
            else:
                weight_series = weight_data
            
            # Garantir que temos Series válida
            if isinstance(weight_series, pd.DataFrame):
                weight_series = weight_series.iloc[:, 0]
            
            # Usar primeiro valor válido em vez de média (mais confiável)
            first_weight_val = weight_series.dropna().iloc[0]
            weight_kg = _weight_to_kg(first_weight_val, weight_cols[0])
            if weight_kg is None:
                raise ValueError("Peso inválido para detecção de modelo")
            
            logger.info(f"Detectando modelo por peso: {weight_kg:.1f} kg")
            
            # E145: MLW=21772kg (typical landing: 19-24 ton)
            # E170: MLW=31400kg (typical landing: 28-32 ton)
            # E175: MLW=34019kg (typical landing: 31-38 ton)
            # E190: MLW=44000kg (typical landing: 38-51 ton) ← 94000lb = 42.6 ton
            # E195: MLW=49895kg (typical landing: 45-55 ton)
            # Thresholds ajustados: 26000kg (E145/E170), 33000kg (E170/E175), 39000kg (E175/E190), 48000kg (E190/E195)
            if weight_kg < 26000:
                logger.info(f"Modelo detectado: E145 (peso {weight_kg:.1f} kg < 26000 kg)")
                return 'E145', weight_kg
            elif weight_kg < 33000:
                logger.info(f"Modelo detectado: E170 (peso {weight_kg:.1f} kg < 33000 kg)")
                return 'E170', weight_kg
            elif weight_kg < 39000:  # Separação E175/E190 em 39 ton
                logger.info(f"Modelo detectado: E175 (peso {weight_kg:.1f} kg < 39000 kg)")
                return 'E175', weight_kg
            elif weight_kg < 48000:  # Separação E190/E195 em 48 ton
                logger.info(f"Modelo detectado: E190 (peso {weight_kg:.1f} kg < 48000 kg)")
                return 'E190', weight_kg
            else:
                logger.info(f"Modelo detectado: E195 (peso {weight_kg:.1f} kg >= 48000 kg)")
                return 'E195', weight_kg
        except Exception as e:
            logger.warning(f"Erro na detecção de modelo por peso: {e}")
            pass
    
    return None, None


def main():
    # Caminho do arquivo
    csv_file = Path(r"c:\Users\mrced\OneDrive\Documents\hard landing\XA-ALU _HL_13AGO25_FLT651.CSV")
    
    if not csv_file.exists():
        print(f"❌ Arquivo não encontrado: {csv_file}")
        return
    
    print(f"\n{'='*80}")
    print(f"TESTE UI METHODS - XA-ALU")
    print(f"{'='*80}\n")
    
    # Parse do CSV
    parser = CSVParser()
    df = parser.parse_file(csv_file)
    print(f"✓ DataFrame carregado: {len(df)} linhas\n")
    
    # Chamar método _detect_model_from_data exatamente como a UI faz
    print("Chamando _detect_model_from_data()...")
    print(f"{'='*80}")
    model, weight_kg = _detect_model_from_data(df)
    print(f"{'='*80}\n")
    
    if not model:
        print("❌ Falha na detecção de modelo")
        return
    
    print(f"✓ RESULTADO:")
    print(f"  Modelo: {model}")
    print(f"  Peso: {weight_kg:.1f} kg\n")
    
    # Executar análise
    print("Executando análise com o modelo detectado...")
    analyzer = HardLandingAnalyzer()
    results = analyzer.analyze(df, weight_kg, model)
    
    if results:
        result = results[0]
        print(f"\n✓ Status: {result.status}")
        if result.vertical_accel:
            print(f"  Max G: {result.vertical_accel.get('max_g', 'N/A'):.3f} G")
            thresholds = result.vertical_accel.get('thresholds', {})
            print(f"  Thresholds: LOW={thresholds.get('low', 'N/A'):.3f}, HIGH={thresholds.get('high', 'N/A'):.3f}, ENGINE={thresholds.get('engine', 'N/A'):.3f}")
    
    print(f"\n{'='*80}\n")


if __name__ == '__main__':
    main()

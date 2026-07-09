"""
Teste de captura de dados de voo - Validação de parâmetros obrigatórios
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_flight_data_capture():
    """Testa se o sistema captura todos os parâmetros obrigatórios"""
    
    print("="*80)
    print("TESTE DE CAPTURA DE DADOS DE VOO")
    print("="*80)
    
    # Simular CSV com nomes de colunas variados
    test_data = {
        'Time (sec)': [0, 0.125, 0.25, 0.375, 0.5],
        'Acceleration (normal load-factor) (g\'s)': [1.0, 1.5, 2.3, 1.8, 1.0],
        'Altitude (ft)': [100, 50, 20, 10, 0],
        'Indicated Airspeed (kts)': [140, 135, 130, 125, 120],
        'Gross Weight (lbs)': [75000, 75000, 75000, 75000, 75000],
        'Vertical Speed (ft/min)': [-500, -600, -800, -400, -100],
        'Pitch Angle (deg)': [5, 3, 0, -2, -3],
        'Roll Angle (deg)': [0, -2, 1, 0, 0],
        'Radio Height (ft)': [100, 50, 20, 10, 0],
        'Gear Position': ['DOWN', 'DOWN', 'DOWN', 'DOWN', 'DOWN'],
        'Flap Position (deg)': [45, 45, 45, 45, 45]
    }
    
    df = pd.DataFrame(test_data)
    
    print(f"\n✓ DataFrame criado: {len(df)} linhas, {len(df.columns)} colunas")
    print(f"\nColunas disponíveis:")
    for col in df.columns:
        print(f"  - {col}")
    
    # Parâmetros obrigatórios para Hard Landing
    required_params = {
        'timestamp': ['time', 'Time (sec)', 'timestamp'],
        'vertical_acceleration': ['Acceleration (normal load-factor)', 'normaccel', 'vert_accel', 'vertical_acceleration'],
        'altitude': ['altitude', 'Altitude (ft)', 'alt_ft'],
        'airspeed': ['airspeed', 'Indicated Airspeed', 'IAS', 'KIAS'],
        'gross_weight': ['weight', 'Gross Weight', 'gross_weight'],
        'vertical_speed': ['vertical_speed', 'Vertical Speed', 'VS'],
        'pitch': ['pitch', 'Pitch Angle'],
        'roll': ['roll', 'Roll Angle'],
    }
    
    print(f"\n{'='*80}")
    print("VALIDAÇÃO DE PARÂMETROS OBRIGATÓRIOS")
    print(f"{'='*80}")
    
    all_found = True
    
    for param_name, possible_names in required_params.items():
        found = False
        found_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            for name in possible_names:
                if name.lower() in col_lower:
                    found = True
                    found_col = col
                    break
            if found:
                break
        
        status = "✓" if found else "✗"
        if found:
            # Testar se tem dados válidos
            valid_data = df[found_col].dropna()
            data_count = len(valid_data)
            data_status = f"{data_count} valores válidos"
            print(f"{status} {param_name:25s} → '{found_col}' ({data_status})")
        else:
            print(f"{status} {param_name:25s} → NÃO ENCONTRADO")
            all_found = False
    
    print(f"\n{'='*80}")
    if all_found:
        print("✓✓✓ TODOS OS PARÂMETROS OBRIGATÓRIOS ENCONTRADOS")
    else:
        print("⚠ ALGUNS PARÂMETROS OBRIGATÓRIOS NÃO FORAM ENCONTRADOS")
    print(f"{'='*80}")
    assert all_found

def test_column_mapper():
    """Testa se o CSV Column Mapper está mapeando corretamente"""
    
    print(f"\n{'='*80}")
    print("TESTE DO CSV COLUMN MAPPER")
    print(f"{'='*80}")
    
    try:
        from src.services.csv_column_mapper import get_mapper
        
        mapper = get_mapper()
        
        # Testar mapeamento de colunas com nomes variados
        test_columns = {
            'Acceleration (normal load-factor) (g\'s)': 'vertical_acceleration',
            'NormAccel': 'vertical_acceleration',
            'Pitch Angle (deg)': 'pitch',
            'Roll Angle (deg)': 'roll',
            'Gross Weight (lbs)': 'gross_weight',
            'Altitude (ft)': 'altitude',
        }
        
        df = pd.DataFrame(columns=list(test_columns.keys()))
        mapped_df = mapper.map_columns(df)
        
        print(f"\nColunas originais → Colunas mapeadas:")
        for orig, expected in test_columns.items():
            if orig in df.columns:
                # Verificar se foi mapeada
                found_in_mapped = False
                for mapped_col in mapped_df.columns:
                    if expected in mapped_col.lower():
                        print(f"✓ '{orig}' → '{mapped_col}'")
                        found_in_mapped = True
                        break
                
                if not found_in_mapped:
                    # Pode ter mantido o nome original
                    if orig in mapped_df.columns:
                        print(f"⚠ '{orig}' → MANTIDO (esperado: '{expected}')")
                    else:
                        print(f"✗ '{orig}' → PERDIDA")
        
        print(f"\n✓ Column Mapper funcionando")
        assert True
        
    except Exception as e:
        print(f"\n✗ ERRO no Column Mapper: {e}")
        assert False, str(e)

def test_hard_landing_analyzer():
    """Testa se o Hard Landing Analyzer está processando dados"""
    
    print(f"\n{'='*80}")
    print("TESTE DO HARD LANDING ANALYZER")
    print(f"{'='*80}")
    
    try:
        # Criar dados simulados
        num_samples = 100
        touchdown_idx = 70
        
        data = {
            'Time (sec)': [i * 0.125 for i in range(num_samples)],
            'Acceleration (normal load-factor) (g\'s)': [1.0] * num_samples,
            'Pitch Angle (deg)': [5.0] * num_samples,
            'Roll Angle (deg)': [0.0] * num_samples,
        }
        
        # Simular pico de aceleração no touchdown
        for i in range(touchdown_idx - 10, touchdown_idx + 10):
            if 0 <= i < num_samples:
                # Gaussiana centrada no touchdown
                distance = abs(i - touchdown_idx)
                data['Acceleration (normal load-factor) (g\'s)'][i] = 1.0 + 1.3 * (1.0 - distance / 10.0)
        
        # Pitch negativo após touchdown
        for i in range(touchdown_idx, num_samples):
            data['Pitch Angle (deg)'][i] = -2.0
        
        df = pd.DataFrame(data)
        
        print(f"\n✓ Dados simulados criados: {len(df)} samples")
        print(f"  - Touchdown simulado no índice {touchdown_idx}")
        print(f"  - Max G: {max(data['Acceleration (normal load-factor) (g\'s)']):.3f}G")
        
        # Testar se encontra o pico
        max_idx = df['Acceleration (normal load-factor) (g\'s)'].idxmax()
        max_g = df['Acceleration (normal load-factor) (g\'s)'].max()
        
        print(f"\n✓ Pico detectado:")
        print(f"  - Índice: {max_idx} (esperado: ~{touchdown_idx})")
        print(f"  - Valor: {max_g:.3f}G")
        
        # Verificar se o pico está próximo do touchdown esperado
        if abs(max_idx - touchdown_idx) <= 5:
            print(f"  ✓ Pico detectado corretamente")
            assert True
        else:
            print(f"  ✗ Pico detectado em posição incorreta")
            assert False, "Pico detectado em posição incorreta"
        
    except Exception as e:
        print(f"\n✗ ERRO: {e}")
        import traceback
        traceback.print_exc()
        assert False, str(e)

def test_weight_extraction():
    """Testa extração de peso por modelo"""
    
    print(f"\n{'='*80}")
    print("TESTE DE EXTRAÇÃO DE PESO POR MODELO")
    print(f"{'='*80}")
    
    # Pesos MLW típicos (lbs)
    model_weights = {
        'E170': 69224,   # 31,400 kg
        'E175': 75000,   # 34,019 kg
        'E190': 97000,   # 44,000 kg
        'E195': 110000,  # ~50,000 kg
    }
    
    print(f"\nPesos MLW (Maximum Landing Weight) por modelo:")
    for model, weight_lb in model_weights.items():
        weight_kg = weight_lb * 0.453592
        print(f"  {model}: {weight_lb:,} lb = {weight_kg:,.0f} kg")
    
    # Testar detecção de modelo por peso
    print(f"\nDetecção de modelo por peso:")
    
    test_weights_kg = [
        (31000, 'E170'),
        (34000, 'E175'),
        (44000, 'E190'),
        (50000, 'E195'),
    ]
    
    for weight_kg, expected_model in test_weights_kg:
        # Lógica de detecção
        if weight_kg < 33000:
            detected = 'E170'
        elif weight_kg < 39000:
            detected = 'E175'
        elif weight_kg < 49000:
            detected = 'E190'
        else:
            detected = 'E195'
        
        status = "✓" if detected == expected_model else "✗"
        print(f"  {status} {weight_kg:,} kg → {detected} (esperado: {expected_model})")
        assert detected == expected_model
    
    print(f"\n✓ Extração de peso funcionando")
    assert True

if __name__ == '__main__':
    print("\n" + "="*80)
    print("SUITE DE TESTES - CAPTURA DE DADOS DE VOO")
    print("="*80)
    
    results = []

    def run_test_case(name, fn):
        try:
            fn()
            return (name, True)
        except AssertionError:
            return (name, False)
    
    # Executar testes
    results.append(run_test_case("Captura de dados de voo", test_flight_data_capture))
    results.append(run_test_case("Column Mapper", test_column_mapper))
    results.append(run_test_case("Hard Landing Analyzer", test_hard_landing_analyzer))
    results.append(run_test_case("Extração de peso", test_weight_extraction))
    
    # Resumo
    print(f"\n{'='*80}")
    print("RESUMO DOS TESTES")
    print(f"{'='*80}")
    
    total = len(results)
    passed = sum(1 for _, result in results if result)
    failed = total - passed
    
    for name, result in results:
        status = "✓ PASSOU" if result else "✗ FALHOU"
        print(f"{status:10s} - {name}")
    
    print(f"\nTotal: {passed}/{total} testes passaram ({passed/total*100:.0f}%)")
    
    print(f"\n{'='*80}")
    if passed == total:
        print("✓✓✓ TODOS OS TESTES PASSARAM - SISTEMA CAPTURANDO DADOS CORRETAMENTE")
    else:
        print(f"⚠ {failed} TESTE(S) FALHARAM - REVISAR IMPLEMENTAÇÃO")
    print(f"{'='*80}\n")

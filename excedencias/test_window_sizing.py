"""
Script de teste para validar window sizing dinâmico
Testa detecção de hard landing com arquivos de diferentes tamanhos
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from src.services.hard_landing_analyzer import HardLandingAnalyzer
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_test_data(num_lines: int, max_g: float = 2.3) -> pd.DataFrame:
    """
    Cria dados de teste simulando um voo
    
    Args:
        num_lines: Número total de linhas
        max_g: Aceleração máxima em G (para simular hard landing)
    """
    # Criar índice de tempo
    time = np.arange(num_lines) * 0.125  # 8 samples/sec
    
    # Simular aceleração vertical
    # Valores baixos durante voo, pico no touchdown
    touchdown_idx = int(num_lines * 0.7)  # Touchdown aos 70% do arquivo
    
    accel = np.ones(num_lines) * 1.0  # Voo normal = 1G
    
    # Criar pico no touchdown (janela de 50 samples)
    peak_start = touchdown_idx - 25
    peak_end = touchdown_idx + 25
    peak_indices = np.arange(peak_start, peak_end)
    
    # Gaussiana centrada no touchdown
    gaussian = np.exp(-((peak_indices - touchdown_idx) ** 2) / (2 * 10**2))
    accel[peak_start:peak_end] = 1.0 + (max_g - 1.0) * gaussian
    
    # Simular pitch (degr de -5° a +10°)
    pitch = np.sin(time / 10) * 7.5 + 2.5
    pitch[touchdown_idx:] = -2.0  # Pitch negativo após touchdown
    
    # Simular roll (-10° a +10°)
    roll = np.sin(time / 15) * 10
    
    # Criar DataFrame
    df = pd.DataFrame({
        'Time (sec)': time,
        'Acceleration (normal load-factor) (g\'s)': accel,
        'Pitch Angle (deg)': pitch,
        'Roll Angle (deg)': roll,
        'Altitude (ft)': 0.0  # Já no solo
    })
    
    return df, touchdown_idx

def run_file_size(num_lines: int, max_g: float):
    """Testa análise com arquivo de tamanho específico"""
    print(f"\n{'='*80}")
    print(f"TESTE: {num_lines:,} linhas, Max G = {max_g:.3f}G")
    print(f"{'='*80}")
    
    # Criar dados de teste
    df, expected_touchdown = create_test_data(num_lines, max_g)
    
    # Criar analisador
    analyzer = HardLandingAnalyzer()
    
    # Executar análise
    results = analyzer.analyze(
        df=df,
        weight_kg=42000,  # Peso médio E175
        model='E175'
    )
    
    # Verificar resultados
    if results:
        result = results[0]
        print(f"\n✓ RESULTADO:")
        print(f"  Status: {result.status}")
        print(f"  Max G: {result.max_g:.3f}G")
        print(f"  Monitores críticos: {', '.join(result.critical_monitors) if result.critical_monitors else 'Nenhum'}")
        print(f"  Fase: {result.inspection_phase}")
        
        # Validar detecção
        detected = result.status != 'NORMAL' and result.max_g is not None
        if detected:
            error = abs(result.max_g - max_g)
            accuracy = (1 - error / max_g) * 100
            print(f"  Precisão: {accuracy:.1f}% (erro: {error:.3f}G)")
            
            if accuracy >= 95:
                print(f"  ✓ DETECÇÃO PRECISA")
            elif accuracy >= 85:
                print(f"  ⚠ DETECÇÃO ACEITÁVEL")
            else:
                print(f"  ✗ DETECÇÃO IMPRECISA")
        else:
            print(f"  ✗ FALHA NA DETECÇÃO (esperado {max_g:.3f}G)")
            
        return detected
    else:
        print(f"\n✗ NENHUM RESULTADO RETORNADO")
        return False

def run_tests():
    """Executa bateria completa de testes"""
    print("="*80)
    print("TESTE DE WINDOW SIZING DINÂMICO")
    print("="*80)
    
    test_cases = [
        # (num_lines, max_g, descrição)
        (5000, 2.05, "Arquivo pequeno - Hard Landing LOW"),
        (5000, 2.25, "Arquivo pequeno - Hard Landing HIGH"),
        (25000, 2.05, "Arquivo médio - Hard Landing LOW"),
        (25000, 2.25, "Arquivo médio - Hard Landing HIGH"),
        (55000, 2.05, "Arquivo grande - Hard Landing LOW"),
        (55000, 2.25, "Arquivo grande - Hard Landing HIGH"),
        (70000, 2.40, "Arquivo muito grande - Hard Landing HIGH"),
    ]
    
    results_summary = []
    
    for num_lines, max_g, description in test_cases:
        detected = run_file_size(num_lines, max_g)
        results_summary.append({
            'description': description,
            'lines': num_lines,
            'max_g': max_g,
            'detected': detected
        })
    
    # Resumo final
    print(f"\n{'='*80}")
    print("RESUMO DOS TESTES")
    print(f"{'='*80}")
    
    total = len(results_summary)
    successes = sum(1 for r in results_summary if r['detected'])
    failures = total - successes
    
    print(f"\nTotal de testes: {total}")
    print(f"✓ Sucesso: {successes} ({successes/total*100:.1f}%)")
    print(f"✗ Falha: {failures} ({failures/total*100:.1f}%)")
    
    if failures > 0:
        print(f"\nFALHAS:")
        for r in results_summary:
            if not r['detected']:
                print(f"  - {r['description']}: {r['lines']:,} linhas, {r['max_g']:.3f}G")
    
    print(f"\n{'='*80}")
    if successes == total:
        print("✓ TODOS OS TESTES PASSARAM!")
    elif successes >= total * 0.8:
        print("⚠ MAIORIA DOS TESTES PASSARAM")
    else:
        print("✗ MUITOS TESTES FALHARAM - REVISAR IMPLEMENTAÇÃO")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    run_tests()

"""
Teste rápido para verificar detecção de Over-G
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.over_g_analyzer import OverGAnalyzer

def test_over_g():
    """Testa detecção de Over-G"""
    
    # Criar dados com excedência de G (3.5G > 3.15G threshold)
    df = pd.DataFrame({
        'time': range(100),
        'altitude': list(range(10000, 5000, -50)) + [5000] * 0,
        'vertical_acceleration': [1.0] * 50 + [3.5] + [1.0] * 49,
        'airspeed': [250] * 100
    })
    
    analyzer = OverGAnalyzer()
    
    print("=" * 80)
    print("TESTE DE DETECÇÃO DE OVER-G")
    print("=" * 80)
    
    # Testar E175
    print("\n🔍 Testando E175 com 3.5G (threshold: 3.15G)")
    result = analyzer.analyze_over_g(df, 'E175')
    
    print(f"\nStatus: {'DETECTADO ✅' if result.is_over_g else 'NÃO DETECTADO ❌'}")
    print(f"Max Positive G: {result.max_positive_g:.2f}")
    print(f"Max Negative G: {result.max_negative_g:.2f}")
    print(f"Threshold Positive: {result.positive_threshold:.2f}")
    print(f"Severity: {result.severity_level}")
    print(f"Excedências: {result.exceedance_count}")
    
    if result.recommended_actions:
        print(f"\nAções Recomendadas:")
        for action in result.recommended_actions:
            print(f"  - {action}")
    
    # Testar sem excedência
    print("\n" + "=" * 80)
    print("\n🔍 Testando E175 com 2.5G (normal)")
    df_normal = df.copy()
    df_normal['vertical_acceleration'] = [1.0] * 50 + [2.5] + [1.0] * 49
    
    result_normal = analyzer.analyze_over_g(df_normal, 'E175')
    
    print(f"\nStatus: {'DETECTADO ✅' if result_normal.is_over_g else 'NORMAL ✅'}")
    print(f"Max Positive G: {result_normal.max_positive_g:.2f}")
    print(f"Severity: {result_normal.severity_level}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_over_g()

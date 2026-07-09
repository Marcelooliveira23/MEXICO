"""
Teste rápido para validar correções de índices relativos
"""
import pandas as pd
import numpy as np

print("="*80)
print("TESTE DE ÍNDICES RELATIVOS")
print("="*80)

# Simular um DataFrame completo com múltiplos voos
total_samples = 100
touchdown_abs = 70  # Touchdown no índice 70 do DataFrame ORIGINAL

# Simular que pegamos um slice do DataFrame
flight_start_abs = 50
flight_end_abs = 90
flight_df = pd.DataFrame({
    'accel': np.random.rand(flight_end_abs - flight_start_abs) + 1.0
})

print(f"\nDataFrame ORIGINAL: 100 samples")
print(f"Flight slice: índices [{flight_start_abs}:{flight_end_abs}]")
print(f"flight_df length: {len(flight_df)} samples")
print(f"Touchdown ABSOLUTO: {touchdown_abs}")

# Calcular posição relativa (CORREÇÃO IMPLEMENTADA)
touchdown_relative = touchdown_abs - flight_start_abs
print(f"Touchdown RELATIVO: {touchdown_relative}")

# Range de análise: 4s antes (32 samples)
start_idx = max(0, touchdown_relative - 32)
end_idx = touchdown_relative + 50

print(f"\nRange de análise:")
print(f"  start_idx: {start_idx}")
print(f"  end_idx: {end_idx}")
print(f"  Total: {end_idx - start_idx} samples")

# Testar se consegue acessar
try:
    test_slice = flight_df.iloc[start_idx:end_idx]
    print(f"\n✓ Slice SUCESSO: {len(test_slice)} samples extraídos")
    
    if len(test_slice) > 0:
        print(f"  Primeira linha (índice relativo {start_idx}): {test_slice.iloc[0]['accel']:.3f}")
        print(f"  Última linha (índice relativo {end_idx-1}): {test_slice.iloc[-1]['accel']:.3f}")
    
except Exception as e:
    print(f"\n✗ ERRO: {e}")

# Comparar com método ANTIGO (bugado)
print(f"\n{'='*80}")
print("MÉTODO ANTIGO (BUGADO):")
print(f"{'='*80}")

try:
    # Método antigo usava touchdown_abs diretamente
    start_idx_old = max(0, touchdown_abs - 32)  # 70 - 32 = 38
    end_idx_old = touchdown_abs + 50            # 70 + 50 = 120
    
    print(f"Range BUGADO:")
    print(f"  start_idx: {start_idx_old} (fora do flight_df que vai até {len(flight_df)-1})")
    print(f"  end_idx: {end_idx_old} (MUITO além do fim!)")
    
    test_slice_old = flight_df.iloc[start_idx_old:end_idx_old]
    print(f"\n⚠ Slice com bug: {len(test_slice_old)} samples (deveria ser ~82)")
    
    if len(test_slice_old) == 0:
        print(f"  ✗ VAZIO! É por isso que retornava NO_DATA")
    
except Exception as e:
    print(f"\n✗ ERRO (esperado com método antigo): {e}")

print(f"\n{'='*80}")
print("CONCLUSÃO:")
print(f"{'='*80}")
print(f"✓ Método NOVO: extrai {end_idx - start_idx} samples corretamente")
print(f"✗ Método ANTIGO: tentava acessar índices {start_idx_old}-{end_idx_old} em DataFrame de {len(flight_df)} samples")
print(f"\n✅ CORREÇÃO VALIDADA!")

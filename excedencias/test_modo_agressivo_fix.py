#!/usr/bin/env python3
"""
Teste rápido para validar correção do Modo Agressivo
Verifica se os thresholds foram atualizados para AMM completo
"""

import sys
sys.path.insert(0, 'src')

from services.over_g_analyzer import OverGAnalyzer
from services.high_bank_angle_analyzer import HighBankAngleAnalyzer

def _validate_thresholds() -> bool:
    print("=" * 80)
    print("TESTE: Validação de Thresholds AMM (Modo Agressivo Fix)")
    print("=" * 80)

    # Teste 1: Over-G Thresholds
    print("\n[1] OVER-G THRESHOLDS")
    print("-" * 80)

    over_g = OverGAnalyzer()
    thresholds = over_g.OVER_G_THRESHOLDS

    expected = {
        'E170': {'positive': 3.5, 'negative': -3.5},
        'E175': {'positive': 3.5, 'negative': -3.5},
        'E190': {'positive': 3.5, 'negative': -3.5},
        'E195': {'positive': 3.5, 'negative': -3.5},
        'E175-E2': {'positive': 3.8, 'negative': -3.8},
        'E190-E2': {'positive': 3.8, 'negative': -3.8},
        'E195-E2': {'positive': 3.8, 'negative': -3.8},
    }

    all_correct = True
    for model, expected_vals in expected.items():
        actual_pos = thresholds[model]['positive']
        actual_neg = thresholds[model]['negative']
        expected_pos = expected_vals['positive']
        expected_neg = expected_vals['negative']

        status = "✅ OK" if (actual_pos == expected_pos and actual_neg == expected_neg) else "❌ ERRO"
        print(f"{model:12} | Pos: {actual_pos:5.2f}G (esperado {expected_pos:5.2f}G) | " +
              f"Neg: {actual_neg:5.2f}G (esperado {expected_neg:5.2f}G) | {status}")

        if status == "❌ ERRO":
            all_correct = False

    # Teste 2: High Bank Angle Thresholds
    print("\n[2] HIGH BANK ANGLE THRESHOLDS")
    print("-" * 80)

    hba = HighBankAngleAnalyzer()
    bank_thresholds = hba.BANK_ANGLE_THRESHOLDS

    expected_bank = {
        'E170': {'normal': 60.0, 'emergency': 67.0},
        'E175': {'normal': 60.0, 'emergency': 67.0},
        'E190': {'normal': 60.0, 'emergency': 67.0},
        'E195': {'normal': 60.0, 'emergency': 67.0},
        'E175-E2': {'normal': 60.0, 'emergency': 67.0},
        'E190-E2': {'normal': 60.0, 'emergency': 67.0},
        'E195-E2': {'normal': 60.0, 'emergency': 67.0},
    }

    for model, expected_vals in expected_bank.items():
        actual_norm = bank_thresholds[model]['normal']
        actual_emerg = bank_thresholds[model]['emergency']
        expected_norm = expected_vals['normal']
        expected_emerg = expected_vals['emergency']

        status = "✅ OK" if (actual_norm == expected_norm and actual_emerg == expected_emerg) else "❌ ERRO"
        print(f"{model:12} | Normal: {actual_norm:5.1f}° (esperado {expected_norm:5.1f}°) | " +
              f"Emergency: {actual_emerg:5.1f}° (esperado {expected_emerg:5.1f}°) | {status}")

        if status == "❌ ERRO":
            all_correct = False

    # Teste 3: Verificar que comentários MODO AGRESSIVO foram removidos
    print("\n[3] VERIFICAR REMOÇÃO DE COMENTÁRIOS MODO AGRESSIVO")
    print("-" * 80)

    with open('src/services/over_g_analyzer.py', 'r', encoding='utf-8') as f:
        content_over_g = f.read()
        has_modo_agressivo_over_g = 'MODO AGRESSIVO' in content_over_g
        status_over_g = "❌ ENCONTRADO" if has_modo_agressivo_over_g else "✅ REMOVIDO"
        print(f"over_g_analyzer.py: {status_over_g}")
        if has_modo_agressivo_over_g:
            all_correct = False

    with open('src/services/high_bank_angle_analyzer.py', 'r', encoding='utf-8') as f:
        content_bank = f.read()
        has_modo_agressivo_bank = 'MODO AGRESSIVO' in content_bank
        status_bank = "❌ ENCONTRADO" if has_modo_agressivo_bank else "✅ REMOVIDO"
        print(f"high_bank_angle_analyzer.py: {status_bank}")
        if has_modo_agressivo_bank:
            all_correct = False

    print("\n" + "=" * 80)
    if all_correct:
        print("✅ TODOS OS TESTES PASSARAM - Correção aplicada com sucesso!")
        print("   Thresholds atualizados para AMM 05-50-02 e AMM 05-57-00")
    else:
        print("❌ ALGUNS TESTES FALHARAM - Verifique as mudanças")

    return all_correct


def test_modo_agressivo_fix():
    assert _validate_thresholds() is True


if __name__ == "__main__":
    ok = _validate_thresholds()
    sys.exit(0 if ok else 1)

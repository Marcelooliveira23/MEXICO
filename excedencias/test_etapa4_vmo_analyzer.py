#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETAPA 4 - VMO/MMO Analyzer Tests
Validates VMO/MMO overspeed detection across all aircraft models
Test suite: 5 tests covering model-specific thresholds and exceedance detection
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.vmo_analyzer import VmoAnalyzer, VmoResult
from utils.config import AppConfig


def test_vmo_thresholds_per_model():
    """Test 1: Verify VMO/MMO thresholds are correct per model"""
    print("\n" + "="*80)
    print("TEST 1: VMO/MMO Thresholds Per Model")
    print("="*80)
    
    analyzer = VmoAnalyzer()
    
    # Test E145
    e145_thresh = analyzer.get_vmo_thresholds('e145')
    assert e145_thresh['vmo'] == 280, f"E145 VMO should be 280, got {e145_thresh['vmo']}"
    assert e145_thresh['mmo'] == 0.78, f"E145 MMO should be 0.78, got {e145_thresh['mmo']}"
    print("✓ E145: VMO=280 KIAS, MMO=0.78 Mach")
    
    # Test E170
    e170_thresh = analyzer.get_vmo_thresholds('e170')
    assert e170_thresh['vmo'] == 320, f"E170 VMO should be 320, got {e170_thresh['vmo']}"
    assert e170_thresh['mmo'] == 0.82, f"E170 MMO should be 0.82, got {e170_thresh['mmo']}"
    print("✓ E170: VMO=320 KIAS, MMO=0.82 Mach")
    
    # Test E190
    e190_thresh = analyzer.get_vmo_thresholds('e190')
    assert e190_thresh['vmo'] == 320, f"E190 VMO should be 320, got {e190_thresh['vmo']}"
    assert e190_thresh['mmo'] == 0.82, f"E190 MMO should be 0.82, got {e190_thresh['mmo']}"
    print("✓ E190: VMO=320 KIAS, MMO=0.82 Mach")
    
    # Test E190-E2 (newer generation)
    e190e2_thresh = analyzer.get_vmo_thresholds('e190_e2')
    assert e190e2_thresh['vmo'] == 340, f"E190-E2 VMO should be 340, got {e190e2_thresh['vmo']}"
    assert e190e2_thresh['mmo'] == 0.85, f"E190-E2 MMO should be 0.85, got {e190e2_thresh['mmo']}"
    print("✓ E190-E2: VMO=340 KIAS, MMO=0.85 Mach (E2 generation higher limits)")
    
    print("\n✅ TEST 1 PASSED: All thresholds correct\n")


def test_vmo_normal_flight():
    """Test 2: Verify normal flight (no exceedance) is detected correctly"""
    print("="*80)
    print("TEST 2: Normal Flight - No VMO/MMO Exceedance")
    print("="*80)
    
    analyzer = VmoAnalyzer()
    
    # Create synthetic flight data - all speeds below limits
    df = pd.DataFrame({
        'IAS': [100, 150, 200, 250, 280, 300, 310, 315, 310, 305, 250, 150],
        'MACH': [0.15, 0.20, 0.28, 0.38, 0.45, 0.55, 0.65, 0.75, 0.75, 0.70, 0.55, 0.35],
        'ALT': [1000, 2000, 5000, 8000, 10000, 15000, 18000, 20000, 20000, 15000, 10000, 5000],
        'TIMESTAMP': pd.date_range('2026-01-20 10:00', periods=12, freq='10s')
    })
    
    results = analyzer.analyze(df, weight_kg=56000, model='E190')
    assert len(results) == 1, f"Expected 1 result, got {len(results)}"
    
    result = results[0]
    assert result.status == "NORMAL", f"Expected NORMAL status, got {result.status}"
    assert result.severity == "NORMAL", f"Expected NORMAL severity, got {result.severity}"
    assert result.max_ias < 320, f"Max IAS {result.max_ias} should be < 320"
    assert result.max_mach < 0.82, f"Max Mach {result.max_mach} should be < 0.82"
    
    print(f"✓ Flight data analyzed: Max IAS {result.max_ias:.0f} KIAS, Max Mach {result.max_mach:.3f}")
    print(f"✓ Status: {result.status}")
    print(f"✓ Message: {result.message}")
    
    print("\n✅ TEST 2 PASSED: Normal flight correctly identified\n")


def test_vmo_exceedance():
    """Test 3: Verify VMO exceedance is detected"""
    print("="*80)
    print("TEST 3: VMO Exceedance Detection")
    print("="*80)
    
    analyzer = VmoAnalyzer()
    
    # Create flight data with VMO exceedance
    df = pd.DataFrame({
        'IAS': [150, 200, 250, 300, 320, 330, 340, 335, 310, 250],  # Exceeds 320 (VMO)
        'MACH': [0.20, 0.28, 0.38, 0.50, 0.60, 0.68, 0.75, 0.73, 0.65, 0.50],
        'ALT': [3000, 5000, 8000, 12000, 15000, 18000, 20000, 20000, 15000, 10000],
        'TIMESTAMP': pd.date_range('2026-01-20 10:00', periods=10, freq='10s')
    })
    
    results = analyzer.analyze(df, weight_kg=56000, model='E190')
    result = results[0]
    
    assert result.status == "VMO_EXCEEDED", f"Expected VMO_EXCEEDED, got {result.status}"
    assert result.severity == "HIGH", f"Expected HIGH severity, got {result.severity}"
    assert result.max_ias > 320, f"Max IAS {result.max_ias} should exceed 320"
    assert result.ias_vmo_exceedance > 0, f"VMO exceedance should be > 0"
    
    print(f"✓ VMO Exceedance Detected:")
    print(f"  Max IAS: {result.max_ias:.0f} KIAS")
    print(f"  VMO Limit: 320 KIAS")
    print(f"  Exceedance: {result.ias_vmo_exceedance:.0f} KIAS")
    print(f"  Severity: {result.severity}")
    print(f"  Altitude when exceeded: {result.altitude_ft:.0f} ft")
    
    print("\n✅ TEST 3 PASSED: VMO exceedance correctly detected\n")


def test_mmo_exceedance():
    """Test 4: Verify MMO exceedance is detected (Mach limiting at high altitude)"""
    print("="*80)
    print("TEST 4: MMO Exceedance Detection (High Altitude)")
    print("="*80)
    
    analyzer = VmoAnalyzer()
    
    # Create flight data with MMO exceedance (high altitude cruise)
    df = pd.DataFrame({
        'IAS': [200, 220, 240, 250, 260, 270, 280, 290],  # IAS within limits
        'MACH': [0.40, 0.50, 0.60, 0.70, 0.78, 0.82, 0.85, 0.88],  # Exceeds 0.82 (MMO)
        'ALT': [20000, 25000, 28000, 30000, 33000, 35000, 37000, 39000],
        'TIMESTAMP': pd.date_range('2026-01-20 10:00', periods=8, freq='30s')
    })
    
    results = analyzer.analyze(df, weight_kg=56000, model='E190')
    result = results[0]
    
    assert result.status == "MMO_EXCEEDED", f"Expected MMO_EXCEEDED, got {result.status}"
    assert result.severity == "HIGH", f"Expected HIGH severity, got {result.severity}"
    assert result.max_mach > 0.82, f"Max Mach {result.max_mach} should exceed 0.82"
    assert result.mach_mmo_exceedance > 0, f"MMO exceedance should be > 0"
    
    print(f"✓ MMO Exceedance Detected:")
    print(f"  Max Mach: {result.max_mach:.3f}")
    print(f"  MMO Limit: 0.82 Mach")
    print(f"  Exceedance: {result.mach_mmo_exceedance:.3f} Mach")
    print(f"  Severity: {result.severity}")
    print(f"  Altitude when exceeded: {result.altitude_ft:.0f} ft")
    
    print("\n✅ TEST 4 PASSED: MMO exceedance correctly detected\n")


def test_both_vmo_mmo_exceedance():
    """Test 5: Verify when BOTH VMO and MMO are exceeded"""
    print("="*80)
    print("TEST 5: Both VMO and MMO Exceedance")
    print("="*80)
    
    analyzer = VmoAnalyzer()
    
    # Create flight data with both exceeding
    df = pd.DataFrame({
        'IAS': [200, 250, 300, 330, 340, 350, 345, 330],  # Exceeds 320 VMO
        'MACH': [0.30, 0.40, 0.55, 0.70, 0.83, 0.86, 0.85, 0.80],  # Exceeds 0.82 MMO
        'ALT': [10000, 15000, 20000, 25000, 28000, 30000, 30000, 25000],
        'TIMESTAMP': pd.date_range('2026-01-20 10:00', periods=8, freq='20s')
    })
    
    results = analyzer.analyze(df, weight_kg=56000, model='E190')
    result = results[0]
    
    assert result.status == "BOTH_EXCEEDED", f"Expected BOTH_EXCEEDED, got {result.status}"
    assert result.severity == "CRITICAL", f"Expected CRITICAL severity, got {result.severity}"
    assert result.max_ias > 320, f"Max IAS should exceed VMO"
    assert result.max_mach > 0.82, f"Max Mach should exceed MMO"
    
    print(f"✓ BOTH VMO and MMO Exceeded:")
    print(f"  Max IAS: {result.max_ias:.0f} KIAS (VMO: 320)")
    print(f"  VMO Exceedance: {result.ias_vmo_exceedance:.0f} KIAS")
    print(f"  Max Mach: {result.max_mach:.3f} (MMO: 0.82)")
    print(f"  MMO Exceedance: {result.mach_mmo_exceedance:.3f} Mach")
    print(f"  Severity: {result.severity}")
    
    print("\n✅ TEST 5 PASSED: Both exceedances correctly detected\n")


def test_e145_different_thresholds():
    """Test 6: Verify E145 has different (lower) thresholds than E1"""
    print("="*80)
    print("TEST 6: E145 Lower Thresholds vs E1")
    print("="*80)
    
    analyzer = VmoAnalyzer()
    
    # Create flight data with 300 KIAS and 0.79 Mach
    # Should NOT exceed E145 limits
    # Should NOT exceed E170 limits either
    
    df_e145 = pd.DataFrame({
        'IAS': [100, 150, 200, 250, 275, 285, 280],  # At/above E145 VMO(280)
        'MACH': [0.15, 0.20, 0.28, 0.40, 0.50, 0.65, 0.60],
        'ALT': [1000, 3000, 5000, 8000, 10000, 12000, 10000],
        'TIMESTAMP': pd.date_range('2026-01-20 10:00', periods=7, freq='15s')
    })
    
    result_e145 = analyzer.analyze(df_e145, weight_kg=20000, model='E145')[0]
    
    # 285 KIAS exceeds E145 VMO(280)
    assert result_e145.status == "VMO_EXCEEDED", f"E145 should detect VMO exceedance at 285 KIAS"
    print(f"✓ E145 Analysis (VMO=280):")
    print(f"  Max IAS: {result_e145.max_ias:.0f} KIAS")
    print(f"  Status: {result_e145.status}")
    print(f"  Exceedance: {result_e145.ias_vmo_exceedance:.0f} KIAS")
    
    # Same data with E170 should NOT exceed (E170 VMO=320)
    result_e170 = analyzer.analyze(df_e145, weight_kg=36000, model='E170')[0]
    assert result_e170.status == "NORMAL", f"E170 should NOT exceed at 285 KIAS (VMO=320)"
    print(f"\n✓ E170 Analysis (VMO=320):")
    print(f"  Max IAS: {result_e170.max_ias:.0f} KIAS")
    print(f"  Status: {result_e170.status}")
    print(f"  E145 VMO < E170 VMO: 280 < 320 ✓")
    
    print("\n✅ TEST 6 PASSED: Different thresholds per model correctly applied\n")


def run_all_tests():
    """Execute all ETAPA 4 tests"""
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*20 + "ETAPA 4: VMO/MMO ANALYZER TESTS" + " "*26 + "║")
    print("╚" + "═"*78 + "╝")
    
    tests = [
        ("VMO/MMO Thresholds per Model", test_vmo_thresholds_per_model),
        ("Normal Flight Detection", test_vmo_normal_flight),
        ("VMO Exceedance Detection", test_vmo_exceedance),
        ("MMO Exceedance Detection", test_mmo_exceedance),
        ("Both VMO+MMO Exceedance", test_both_vmo_mmo_exceedance),
        ("E145 vs E1 Thresholds", test_e145_different_thresholds),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}\n")
            failed += 1
        except Exception as e:
            print(f"\n❌ TEST ERROR: {test_name}")
            print(f"   Error: {e}\n")
            failed += 1
    
    # Summary
    print("\n" + "═"*80)
    print("TEST SUMMARY")
    print("═"*80)
    print(f"RESULTADO: {passed} PASSOU, {failed} FALHOU")
    
    if failed == 0:
        print("\n✅ ETAPA 4 VALIDADA COM SUCESSO!")
        print("   VMO/MMO Analyzer funcionando corretamente para todos os modelos")
    else:
        print(f"\n❌ {failed} teste(s) falharam")
    
    print("═"*80 + "\n")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

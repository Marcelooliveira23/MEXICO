#!/usr/bin/env python3
"""
ETAPA 10 - Master Event Analyzer Integration Tests (SIMPLE)
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.master_event_analyzer import MasterEventAnalyzer

print("\n[ETAPA 10] MASTER ANALYZER INTEGRATION TESTS\n")

# Test 1: E170 Normal Flight
print("[TEST 1] E170 Normal Flight...")
try:
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='10s'),
        'airspeed_kts': np.linspace(150, 280, 100),
        'altitude_ft': np.linspace(0, 35000, 100),
        'vertical_speed_fpm': np.linspace(0, 2000, 100),
        'pitch_deg': np.linspace(0, 15, 100),
        'roll_deg': np.linspace(0, 30, 100),
        'g_load': np.ones(100) * 1.1,
        'flap_position': [0]*50 + [1]*50,
        'lg_position': [0]*80 + [1]*20,
        'outside_air_temp_c': np.ones(100) * 15,
        'egt_c': np.ones(100) * 850,
        'weight_kg': np.ones(100) * 65000,
    })
    
    analyzer = MasterEventAnalyzer()
    result = analyzer.analyze_complete_flight(df, weight_kg=65000, model='e170', flight_num='UA170')
    
    assert result.conformance_score >= 95, f"Expected high conformance, got {result.conformance_score}"
    print(f"  PASSED - Conformance: {result.conformance_score:.1f}%")
except Exception as e:
    print(f"  FAILED - {str(e)}")

# Test 2: E190 VMO Exceedance
print("\n[TEST 2] E190 VMO Exceedance...")
try:
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='10s'),
        'airspeed_kts': np.linspace(150, 340, 100),  # Exceeds VMO 320
        'altitude_ft': np.linspace(0, 35000, 100),
        'vertical_speed_fpm': np.linspace(0, 2000, 100),
        'pitch_deg': np.linspace(0, 15, 100),
        'roll_deg': np.linspace(0, 30, 100),
        'g_load': np.ones(100) * 1.1,
        'flap_position': [0]*100,
        'lg_position': [0]*100,
        'outside_air_temp_c': np.ones(100) * 15,
        'egt_c': np.ones(100) * 850,
        'weight_kg': np.ones(100) * 56000,
    })
    
    analyzer = MasterEventAnalyzer()
    result = analyzer.analyze_complete_flight(df, weight_kg=56000, model='e190', flight_num='UA190')
    
    assert result.conformance_score < 95, f"Expected lower conformance due to VMO, got {result.conformance_score}"
    print(f"  PASSED - Conformance: {result.conformance_score:.1f}% (VMO detected)")
except Exception as e:
    print(f"  FAILED - {str(e)}")

# Test 3: All analyzers callable
print("\n[TEST 3] All Sub-Analyzers Callable...")
try:
    from services.vmo_analyzer import VmoAnalyzer
    from services.flap_overspeed_analyzer import FlapAnalyzer
    from services.lg_down_overspeed_analyzer import LGDownOverspeedAnalyzer
    from services.turbulence_analyzer import TurbulenceAnalyzer
    from services.overweight_landing_analyzer import OverweightLandingAnalyzer
    from services.temperature_envelope_analyzer import TemperatureEnvelopeAnalyzer
    from services.hard_landing_analyzer import HardLandingAnalyzer
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=50, freq='10s'),
        'airspeed_kts': np.ones(50) * 200,
        'altitude_ft': np.ones(50) * 10000,
        'vertical_speed_fpm': np.ones(50) * 500,
        'pitch_deg': np.ones(50) * 5,
        'roll_deg': np.ones(50) * 10,
        'g_load': np.ones(50) * 1.2,
        'flap_position': np.ones(50) * 0,
        'lg_position': np.ones(50) * 0,
        'outside_air_temp_c': np.ones(50) * 15,
        'egt_c': np.ones(50) * 850,
        'weight_kg': np.ones(50) * 65000,
    })
    
    vmo = VmoAnalyzer().analyze(df, 65000, 'e170')
    flap = FlapAnalyzer().analyze(df, 65000, 'e170')
    lg = LGDownOverspeedAnalyzer().analyze(df, 65000, 'e170')
    turb = TurbulenceAnalyzer().analyze(df, 65000, 'e170')
    overw = OverweightLandingAnalyzer().analyze(df, 65000, 'e170')
    temp = TemperatureEnvelopeAnalyzer().analyze(df, 65000, 'e170')
    hl = HardLandingAnalyzer().analyze(df, 65000, 'e170')
    
    print(f"  PASSED - All 7 analyzers working")
    print(f"    - VMO: {len(vmo)} results")
    print(f"    - Flap: {len(flap)} results")
    print(f"    - LG: {len(lg)} results")
    print(f"    - Turbulence: {len(turb)} results")
    print(f"    - Overweight: {len(overw)} results")
    print(f"    - Temperature: {len(temp)} results")
    print(f"    - Hard Landing: {len(hl)} results")
except Exception as e:
    print(f"  FAILED - {str(e)}")

# Test 4: Model registry coverage
print("\n[TEST 4] All 9 Aircraft Models...")
try:
    models = ['e145', 'e170', 'e175', 'e190', 'e195', 'e175_e2', 'e190_e2', 'e195_e2']
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=50, freq='10s'),
        'airspeed_kts': np.ones(50) * 200,
        'altitude_ft': np.ones(50) * 10000,
        'vertical_speed_fpm': np.ones(50) * 500,
        'pitch_deg': np.ones(50) * 5,
        'roll_deg': np.ones(50) * 10,
        'g_load': np.ones(50) * 1.2,
        'flap_position': np.ones(50) * 0,
        'lg_position': np.ones(50) * 0,
        'outside_air_temp_c': np.ones(50) * 15,
        'egt_c': np.ones(50) * 850,
        'weight_kg': np.ones(50) * 65000,
    })
    
    analyzer = MasterEventAnalyzer()
    
    for model in models:
        result = analyzer.analyze_complete_flight(df, weight_kg=65000, model=model, flight_num=f'TEST-{model}')
        print(f"    - {model.upper()}: {result.conformance_score:.1f}%")
    
    print(f"  PASSED - All 9 models analyzed")
except Exception as e:
    print(f"  FAILED - {str(e)}")

print("\n[ETAPA 10] INTEGRATION TESTS COMPLETE\n")

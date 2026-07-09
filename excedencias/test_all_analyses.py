"""
Script de Teste Completo - Todas as Análises de Excedências
Baseado nas especificações dos PDFs
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sys
import os

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.universal_graph_generator import UniversalGraphGenerator
from src.services.parameter_validator import ValidationResult
from src.services.all_families_specs import AllFamiliesSpecifications


def _get_model_specs(aircraft_model: str):
    specs = AllFamiliesSpecifications.get_specifications_by_model(aircraft_model)
    if not specs:
        raise ValueError(f"Especificacoes nao encontradas para {aircraft_model}")
    return specs


def _model_label(aircraft_model: str) -> str:
    return aircraft_model.upper().replace("-", "")


def create_hard_landing_data(with_exceedance=True, aircraft_model="e190"):
    """Criar dados simulados para Hard Landing baseado nos PDFs"""
    print("\n=== HARD LANDING ===")

    specs = _get_model_specs(aircraft_model)
    hard_specs = specs["hard_landing"]
    normal_limit = hard_specs["normal_limit"].value
    hard_limit = hard_specs["hard_limit"].value

    rows = 100

    base_low = max(0.9, normal_limit * 0.5)
    base_high = min(1.8, normal_limit * 0.95)
    vertical_accel = np.random.uniform(base_low, base_high, rows)

    ok_margin = max(0.1, normal_limit * 0.05)
    ok_peak = max(normal_limit - ok_margin, normal_limit * 0.8)
    exc_margin = max(0.2, hard_limit * 0.08)
    exc_peak = hard_limit + exc_margin

    if with_exceedance:
        vertical_accel[50:55] = np.linspace(base_high, exc_peak, 5)
        vertical_accel[55:60] = np.linspace(exc_peak, base_low, 5)
        print(
            f"  ✓ COM excedência: Pico de {exc_peak:.2f}g "
            f"(limite: {hard_limit:.2f}g)"
        )
    else:
        vertical_accel[50:55] = np.linspace(base_high, ok_peak, 5)
        vertical_accel[55:60] = np.linspace(ok_peak, base_low, 5)
        print(
            f"  ✓ SEM excedência: Pico de {ok_peak:.2f}g "
            f"(limite: {hard_limit:.2f}g)"
        )
    
    # Pitch angle (graus)
    pitch = np.random.uniform(-2, 5, rows)
    pitch[48:52] = [3, 4, 5, 4]  # Flare
    
    # Roll angle (graus)
    roll = np.random.uniform(-1, 1, rows)
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01 10:00:00', periods=rows, freq='100ms'),
        'vertical_acceleration': vertical_accel,
        'pitch': pitch,
        'roll': roll
    })
    
    validation_results = [
        ValidationResult(
            parameter="Vertical Acceleration",
            value=vertical_accel.max(),
            limit=hard_limit,
            unit=hard_specs["hard_limit"].unit,
            status="CRITICAL" if with_exceedance else "OK",
            exceedance_percent=((vertical_accel.max() - hard_limit) / hard_limit * 100)
            if with_exceedance else 0,
            message=(
                f"Hard landing detected: {vertical_accel.max():.2f}"
                f"{hard_specs['hard_limit'].unit} exceeds limit of {hard_limit:.2f}"
                f"{hard_specs['hard_limit'].unit}"
                if with_exceedance else "Normal landing within limits"
            ),
            manual_reference=hard_specs["hard_limit"].manual_reference
        )
    ]
    
    return df, validation_results


def create_gear_overspeed_data(with_exceedance=True, aircraft_model="e190"):
    """Criar dados para Gear Overspeed - VLE"""
    print("\n=== GEAR OVERSPEED ===")

    specs = _get_model_specs(aircraft_model)
    gear_speeds = specs["gear_speeds"]
    vle_limit = gear_speeds["vle"].value

    rows = 120
    base_low = max(120, vle_limit - 80)
    base_high = vle_limit - 30
    airspeed = np.random.uniform(base_low, base_high, rows)

    exc_margin = max(10, vle_limit * 0.08)
    exc_peak = vle_limit + exc_margin
    ok_peak = vle_limit - max(5, vle_limit * 0.03)

    if with_exceedance:
        airspeed[40:50] = np.linspace(base_high, exc_peak, 10)
        airspeed[50:60] = np.linspace(exc_peak, base_low, 10)
        print(
            f"  ✓ COM excedência: {exc_peak:.0f} {gear_speeds['vle'].unit} "
            f"com gear down (limite: {vle_limit:.0f} {gear_speeds['vle'].unit})"
        )
    else:
        airspeed[40:50] = np.linspace(base_high, ok_peak, 10)
        airspeed[50:60] = np.linspace(ok_peak, base_low, 10)
        print(
            f"  ✓ SEM excedência: {ok_peak:.0f} {gear_speeds['vle'].unit} "
            f"com gear down (dentro do limite)"
        )
    
    # Gear position: 0=up, 1=down
    gear_pos = np.zeros(rows)
    gear_pos[35:] = 1  # Gear down após sample 35
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01 10:05:00', periods=rows, freq='100ms'),
        'airspeed': airspeed,
        'gear_position': gear_pos
    })
    
    validation_results = [
        ValidationResult(
            parameter="Landing Gear Speed (VLE)",
            value=airspeed.max(),
            limit=vle_limit,
            unit=gear_speeds["vle"].unit,
            status="WARNING" if with_exceedance else "OK",
            exceedance_percent=((airspeed.max() - vle_limit) / vle_limit * 100)
            if with_exceedance else 0,
            message=(
                f"Gear overspeed: {airspeed.max():.1f} {gear_speeds['vle'].unit} "
                f"exceeds VLE {vle_limit:.0f} {gear_speeds['vle'].unit}"
                if with_exceedance else "Gear speed within limits"
            ),
            manual_reference=gear_speeds["vle"].manual_reference
        )
    ]
    
    return df, validation_results


def create_temp_envelope_data(with_exceedance=True, aircraft_model="e190"):
    """Criar dados para Temperature Envelope"""
    print("\n=== TEMPERATURE ENVELOPE ===")

    specs = _get_model_specs(aircraft_model)
    temps = specs["temperatures"]
    egt_limit = temps["egt_takeoff"].value
    tat_max = temps["tat_max"].value
    tat_min = temps["tat_min"].value

    rows = 150

    tat = np.random.uniform(max(15, tat_min + 10), min(35, tat_max - 10), rows)
    egt = np.random.uniform(650, egt_limit - 80, rows)

    exc_margin = max(20, egt_limit * 0.04)
    exc_peak = egt_limit + exc_margin
    ok_peak = egt_limit - max(10, egt_limit * 0.03)

    if with_exceedance:
        egt[70:80] = np.linspace(egt_limit - 50, exc_peak, 10)
        egt[80:90] = np.linspace(exc_peak, egt_limit - 80, 10)
        print(
            f"  ✓ COM excedência: EGT {exc_peak:.0f}{temps['egt_takeoff'].unit} "
            f"(limite: {egt_limit:.0f}{temps['egt_takeoff'].unit})"
        )
    else:
        egt[70:80] = np.linspace(egt_limit - 50, ok_peak, 10)
        egt[80:90] = np.linspace(ok_peak, egt_limit - 80, 10)
        print(
            f"  ✓ SEM excedência: EGT {ok_peak:.0f}{temps['egt_takeoff'].unit} "
            f"(dentro do limite)"
        )
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01 10:10:00', periods=rows, freq='100ms'),
        'tat': tat,
        'egt': egt
    })
    
    validation_results = [
        ValidationResult(
            parameter="Total Air Temperature (TAT) - High",
            value=tat.max(),
            limit=tat_max,
            unit=temps["tat_max"].unit,
            status="OK",
            exceedance_percent=0,
            message="TAT within limits",
            manual_reference=temps["tat_max"].manual_reference
        ),
        ValidationResult(
            parameter="Exhaust Gas Temperature (EGT)",
            value=egt.max(),
            limit=egt_limit,
            unit=temps["egt_takeoff"].unit,
            status="CRITICAL" if with_exceedance else "OK",
            exceedance_percent=((egt.max() - egt_limit) / egt_limit * 100)
            if with_exceedance else 0,
            message=(
                f"EGT overheat: {egt.max():.1f}{temps['egt_takeoff'].unit} "
                f"exceeds limit of {egt_limit:.0f}{temps['egt_takeoff'].unit}"
                if with_exceedance else "EGT within limits"
            ),
            manual_reference=temps["egt_takeoff"].manual_reference
        )
    ]
    
    return df, validation_results


def create_max_speed_data(with_exceedance=True, aircraft_model="e190"):
    """Criar dados para Max Speed - VMO/MMO"""
    print("\n=== MAX SPEED ===")

    specs = _get_model_specs(aircraft_model)
    speeds = specs["max_speeds"]
    vmo_limit = speeds["vmo"].value

    rows = 100
    base_low = max(200, vmo_limit - 70)
    base_high = vmo_limit - 30
    ias = np.random.uniform(base_low, base_high, rows)
    mach = ias / 661.5 * 0.01  # Conversao simplificada

    exc_margin = max(10, vmo_limit * 0.05)
    exc_peak = vmo_limit + exc_margin
    ok_peak = vmo_limit - max(5, vmo_limit * 0.03)

    if with_exceedance:
        ias[45:55] = np.linspace(base_high, exc_peak, 10)
        mach[45:55] = ias[45:55] / 661.5 * 0.01
        print(
            f"  ✓ COM excedência: {exc_peak:.0f} {speeds['vmo'].unit} "
            f"(limite VMO: {vmo_limit:.0f} {speeds['vmo'].unit})"
        )
    else:
        ias[45:55] = np.linspace(base_high, ok_peak, 10)
        mach[45:55] = ias[45:55] / 661.5 * 0.01
        print(
            f"  ✓ SEM excedência: {ok_peak:.0f} {speeds['vmo'].unit} "
            f"(dentro do limite)"
        )
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01 10:15:00', periods=rows, freq='100ms'),
        'airspeed': ias,
        'mach': mach
    })
    
    validation_results = [
        ValidationResult(
            parameter="Maximum Operating Speed (VMO)",
            value=ias.max(),
            limit=vmo_limit,
            unit=speeds["vmo"].unit,
            status="WARNING" if with_exceedance else "OK",
            exceedance_percent=((ias.max() - vmo_limit) / vmo_limit * 100)
            if with_exceedance else 0,
            message=(
                f"VMO exceedance: {ias.max():.1f} {speeds['vmo'].unit} "
                f"exceeds limit of {vmo_limit:.0f} {speeds['vmo'].unit}"
                if with_exceedance else "Speed within VMO limits"
            ),
            manual_reference=speeds["vmo"].manual_reference
        )
    ]
    
    return df, validation_results


def create_flap_overspeed_data(with_exceedance=True, aircraft_model="e190"):
    """Criar dados para Flap Overspeed"""
    print("\n=== FLAP OVERSPEED ===")

    specs = _get_model_specs(aircraft_model)
    flap_speeds = specs["flap_speeds"]
    flap_key = "flap_4" if "flap_4" in flap_speeds else "flap_3"
    if flap_key not in flap_speeds:
        flap_key = list(flap_speeds.keys())[0]
    flap_limit = flap_speeds[flap_key].value
    flap_pos_value = {
        "flap_1": 1,
        "flap_2": 2,
        "flap_3": 3,
        "flap_4": 4,
        "flap_full": 5,
    }.get(flap_key, 4)

    rows = 110
    base_low = max(120, flap_limit - 60)
    base_high = flap_limit - 20
    airspeed = np.random.uniform(base_low, base_high, rows)
    flap_pos = np.zeros(rows)

    flap_pos[30:] = flap_pos_value

    exc_margin = max(10, flap_limit * 0.08)
    exc_peak = flap_limit + exc_margin
    ok_peak = flap_limit - max(5, flap_limit * 0.03)
    
    if with_exceedance:
        airspeed[40:50] = np.linspace(base_high, exc_peak, 10)
        airspeed[50:60] = np.linspace(exc_peak, base_low, 10)
        print(
            f"  ✓ COM excedência: {exc_peak:.0f} {flap_speeds[flap_key].unit} "
            f"com Flaps {flap_pos_value} (limite: {flap_limit:.0f} "
            f"{flap_speeds[flap_key].unit})"
        )
    else:
        airspeed[40:50] = np.linspace(base_high, ok_peak, 10)
        airspeed[50:60] = np.linspace(ok_peak, base_low, 10)
        print(
            f"  ✓ SEM excedência: {ok_peak:.0f} {flap_speeds[flap_key].unit} "
            f"com Flaps {flap_pos_value} (dentro do limite)"
        )
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01 10:20:00', periods=rows, freq='100ms'),
        'airspeed': airspeed,
        'flap_position': flap_pos
    })
    
    validation_results = [
        ValidationResult(
            parameter=f"Flap Speed - Flaps {flap_pos_value}",
            value=airspeed[flap_pos == flap_pos_value].max(),
            limit=flap_limit,
            unit=flap_speeds[flap_key].unit,
            status="WARNING" if with_exceedance else "OK",
            exceedance_percent=((airspeed[flap_pos == flap_pos_value].max() - flap_limit)
            / flap_limit * 100) if with_exceedance else 0,
            message=(
                f"Flap overspeed: {airspeed[flap_pos == flap_pos_value].max():.1f} "
                f"{flap_speeds[flap_key].unit} exceeds Flaps {flap_pos_value} "
                f"limit of {flap_limit:.0f} {flap_speeds[flap_key].unit}"
                if with_exceedance else "Flap speed within limits"
            ),
            manual_reference=flap_speeds[flap_key].manual_reference
        )
    ]
    
    return df, validation_results


def create_overweight_landing_data(with_exceedance=True, aircraft_model="e190"):
    """Criar dados para Overweight Landing"""
    print("\n=== OVERWEIGHT LANDING ===")

    specs = _get_model_specs(aircraft_model)
    weights = specs["weights"]
    mlw_limit = weights.mlw

    rows = 90
    base_low = max(50000, mlw_limit - 8000)
    base_high = mlw_limit - 3000
    weight = np.random.uniform(base_low, base_high, rows)

    exc_margin = max(1500, mlw_limit * 0.02)
    exc_peak = mlw_limit + exc_margin
    ok_peak = mlw_limit - max(1000, mlw_limit * 0.01)

    if with_exceedance:
        weight[:] = np.random.uniform(mlw_limit + 500, exc_peak, rows)
        print(
            f"  ✓ COM excedência: {exc_peak:,.0f} lbs "
            f"(limite MLW: {mlw_limit:,.0f} lbs)"
        )
    else:
        weight[:] = np.random.uniform(base_low, ok_peak, rows)
        print(
            f"  ✓ SEM excedência: {ok_peak:,.0f} lbs (dentro do limite)"
        )
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01 10:25:00', periods=rows, freq='100ms'),
        'gross_weight': weight
    })
    
    validation_results = [
        ValidationResult(
            parameter="Landing Weight (MLW)",
            value=weight.max(),
            limit=mlw_limit,
            unit="lbs",
            status="WARNING" if with_exceedance else "OK",
            exceedance_percent=((weight.max() - mlw_limit) / mlw_limit * 100)
            if with_exceedance else 0,
            message=(
                f"Overweight landing: {weight.max():.0f} lbs exceeds MLW of "
                f"{mlw_limit:,.0f} lbs"
                if with_exceedance else "Landing weight within MLW"
            ),
            manual_reference="AMM 08-00-00 - Weight and Balance Limitations"
        )
    ]
    
    return df, validation_results


def run_analysis_test(
    name,
    data_func,
    graph_func_name,
    aircraft_model="e190",
    tail_number="PR-TEST"
):
    """Testar uma análise específica"""
    print(f"\n{'='*70}")
    print(f"TESTANDO: {name} ({_model_label(aircraft_model)})")
    print(f"{'='*70}")

    event_dir = name.lower().replace(" ", "_")
    model_dir = aircraft_model.lower().replace("-", "_")
    output_dir = Path(f"test_outputs/{model_dir}/{event_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    generator = UniversalGraphGenerator(output_dir, dense_mode=False, language="pt")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Teste COM excedência
    print("\n--- Teste 1: COM EXCEDÊNCIA ---")
    df_exc, val_exc = data_func(
        with_exceedance=True,
        aircraft_model=aircraft_model
    )
    
    graph_method = getattr(generator, graph_func_name)
    files_exc = graph_method(df_exc, val_exc, aircraft_model, tail_number, f"{timestamp}_exc")
    
    print(f"\n✓ Gráficos gerados: {len(files_exc)}")
    for f in files_exc:
        print(f"  - {f.name}")
    
    # Teste SEM excedência
    print("\n--- Teste 2: SEM EXCEDÊNCIA ---")
    df_ok, val_ok = data_func(
        with_exceedance=False,
        aircraft_model=aircraft_model
    )
    
    files_ok = graph_method(df_ok, val_ok, aircraft_model, tail_number, f"{timestamp}_ok")
    
    print(f"\n✓ Gráficos gerados: {len(files_ok)}")
    for f in files_ok:
        print(f"  - {f.name}")
    
    # Validar que os arquivos foram criados
    assert all(f.exists() for f in files_exc), f"❌ Arquivos COM excedência não foram criados!"
    assert all(f.exists() for f in files_ok), f"❌ Arquivos SEM excedência não foram criados!"
    
    # Validar que não há mistura (arquivos devem ter nomes diferentes)
    exc_names = {f.name for f in files_exc}
    ok_names = {f.name for f in files_ok}
    assert exc_names.isdisjoint(ok_names), f"❌ Há mistura de nomes entre os testes!"
    
    print(f"\n✅ {name} - TODOS OS TESTES PASSARAM!")
    return True


def main():
    """Executar todos os testes"""
    seed = os.getenv("TEST_SEED")
    if seed:
        try:
            np.random.seed(int(seed))
            print(f"Seed de teste definida: {seed}")
        except ValueError:
            print(f"Seed invalida ignorada: {seed}")
    print("="*70)
    print("TESTE COMPLETO - TODOS OS EVENTOS DE EXCEDÊNCIAS")
    print("Baseado em especificações dos PDFs")
    print("="*70)

    models = [
        "e135",
        "e140",
        "e145",
        "e170",
        "e175",
        "e190",
        "e195",
        "e190-e2",
        "e195-e2",
    ]

    tests = [
        ("Hard Landing", create_hard_landing_data, "generate_hard_landing_specific_graphs"),
        ("Gear Overspeed", create_gear_overspeed_data, "generate_gear_overspeed_specific_graphs"),
        ("Temperature Envelope", create_temp_envelope_data, "generate_temperature_specific_graphs"),
        ("Max Speed", create_max_speed_data, "generate_max_speed_specific_graphs"),
        ("Flap Overspeed", create_flap_overspeed_data, "generate_flap_overspeed_specific_graphs"),
        ("Overweight Landing", create_overweight_landing_data, "generate_overweight_landing_specific_graphs"),
    ]

    results = []
    for aircraft_model in models:
        print("\n" + "=" * 70)
        print(f"MODELO: {_model_label(aircraft_model)}")
        print("=" * 70)

        for name, data_func, graph_func in tests:
            try:
                success = run_analysis_test(
                    name,
                    data_func,
                    graph_func,
                    aircraft_model=aircraft_model,
                    tail_number=f"{_model_label(aircraft_model)}-TEST"
                )
                results.append((aircraft_model, name, success))
            except Exception as e:
                print(f"\n❌ ERRO em {name} ({_model_label(aircraft_model)}): {e}")
                import traceback
                traceback.print_exc()
                results.append((aircraft_model, name, False))
    
    # Sumário final
    print("\n" + "="*70)
    print("SUMÁRIO FINAL")
    print("="*70)
    for aircraft_model, name, success in results:
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"{status} - {name} ({_model_label(aircraft_model)})")
    
    total = len(results)
    passed = sum(1 for _, _, s in results if s)
    print(f"\nTotal: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 TODOS OS TESTES PASSARAM COM SUCESSO! 🎉")
    else:
        print(f"\n⚠️  {total - passed} teste(s) falharam")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

"""
Testes de Validação da ETAPA 1: Infraestrutura de Modelo
Verifica que sistema reconhece corretamente sub-modelos e suas características
"""

import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.config import AppConfig
from models.aircraft_model import AircraftModelRegistry, get_models_for_legacy_family


def test_model_registry_exists():
    """Verificar que registry foi criado"""
    print("✓ Test 1: Model Registry criado")
    models = AircraftModelRegistry.list_all_models()
    assert len(models) == 8, f"Esperava 8 modelos, encontrados {len(models)}"
    print(f"  └─ Modelos encontrados: {models}")


def test_e170_vs_e190_recognition():
    """Verificar que E170 e E190 são reconhecidos como diferentes"""
    print("\n✓ Test 2: E170 vs E190 são diferentes")
    
    e170_spec = AircraftModelRegistry.get_model("e170")
    e190_spec = AircraftModelRegistry.get_model("e190")
    
    # Verificar MTOW
    assert e170_spec.mtow == 79344, f"E170 MTOW errado: {e170_spec.mtow}"
    assert e190_spec.mtow == 123676, f"E190 MTOW errado: {e190_spec.mtow}"
    print(f"  └─ E170 MTOW: {e170_spec.mtow} lbs | E190 MTOW: {e190_spec.mtow} lbs")
    
    # Verificar MLW
    assert e170_spec.mlw == 69224, f"E170 MLW errado: {e170_spec.mlw}"
    assert e190_spec.mlw == 108247, f"E190 MLW errado: {e190_spec.mlw}"
    print(f"  └─ E170 MLW: {e170_spec.mlw} lbs | E190 MLW: {e190_spec.mlw} lbs")
    
    # Verificar PDF
    assert e170_spec.pdf_hard_landing == "801", f"E170 PDF errado: {e170_spec.pdf_hard_landing}"
    assert e190_spec.pdf_hard_landing == "804", f"E190 PDF errado: {e190_spec.pdf_hard_landing}"
    print(f"  └─ E170 PDF: {e170_spec.pdf_hard_landing} | E190 PDF: {e190_spec.pdf_hard_landing}")


def test_e190_vs_e195_weight_difference():
    """Verificar que E195 é mais pesado que E190"""
    print("\n✓ Test 3: E190 vs E195 peso diferente")
    
    e190_spec = AircraftModelRegistry.get_model("e190")
    e195_spec = AircraftModelRegistry.get_model("e195")
    
    # E195 deve ser ~4350 kg (9576 lbs) mais pesado
    weight_diff = e195_spec.mtow - e190_spec.mtow
    print(f"  └─ E190 MTOW: {e190_spec.mtow} lbs ({e190_spec.mtow/2.20462:.0f} kg)")
    print(f"  └─ E195 MTOW: {e195_spec.mtow} lbs ({e195_spec.mtow/2.20462:.0f} kg)")
    print(f"  └─ Diferença: {weight_diff} lbs ({weight_diff/2.20462:.0f} kg)")
    
    assert weight_diff > 9000, f"Diferença de peso E190/E195 incorreta: {weight_diff}"


def test_e170_vs_e175_weight_difference():
    """Verificar que E175 é mais pesado que E170"""
    print("\n✓ Test 4: E170 vs E175 peso diferente")
    
    e170_spec = AircraftModelRegistry.get_model("e170")
    e175_spec = AircraftModelRegistry.get_model("e175")
    
    # E175 deve ser ~2000 kg (4409 lbs) mais pesado
    weight_diff = e175_spec.mtow - e170_spec.mtow
    print(f"  └─ E170 MTOW: {e170_spec.mtow} lbs ({e170_spec.mtow/2.20462:.0f} kg)")
    print(f"  └─ E175 MTOW: {e175_spec.mtow} lbs ({e175_spec.mtow/2.20462:.0f} kg)")
    print(f"  └─ Diferença: {weight_diff} lbs ({weight_diff/2.20462:.0f} kg)")
    
    assert weight_diff > 3000, f"Diferença de peso E170/E175 incorreta: {weight_diff}"


def test_family_to_model_mapping():
    """Verificar que famílias mapeiam corretamente para modelos"""
    print("\n✓ Test 5: Family to Model mapping")
    
    mappings = {
        "e145": ["e145"],
        "e170": ["e170", "e175"],
        "e1": ["e190", "e195"],
        "e2": ["e175_e2", "e190_e2", "e195_e2"],
    }
    
    for family_id, expected_models in mappings.items():
        models = get_models_for_legacy_family(family_id)
        print(f"  └─ Família {family_id.upper()}: {models}")
        assert set(models) == set(expected_models), \
            f"Mapeamento {family_id} errado: esperado {expected_models}, obtido {models}"


def test_app_config_integration():
    """Verificar que AppConfig integra corretamente"""
    print("\n✓ Test 6: AppConfig integration")
    
    # Teste get_model_spec
    e170_spec = AppConfig.get_model_spec("e170")
    assert e170_spec is not None, "E170 spec não encontrado"
    print(f"  └─ E170 spec: {e170_spec.model_name}")
    
    # Teste get_models_for_family
    e170_models = AppConfig.get_models_for_family("e170")
    print(f"  └─ Modelos em 'e170': {[m.model_name for m in e170_models]}")
    assert len(e170_models) == 2, f"Esperava 2 modelos em e170, encontrados {len(e170_models)}"
    
    # Teste get_hard_landing_pdf
    e170_pdf = AppConfig.get_hard_landing_pdf("e170")
    e190_pdf = AppConfig.get_hard_landing_pdf("e190")
    print(f"  └─ E170 Hard Landing PDF: {e170_pdf}")
    print(f"  └─ E190 Hard Landing PDF: {e190_pdf}")
    assert e170_pdf == "801", f"PDF E170 errado: {e170_pdf}"
    assert e190_pdf == "804", f"PDF E190 errado: {e190_pdf}"
    assert e170_pdf != e190_pdf, "E170 e E190 devem usar PDFs diferentes!"


def test_mtow_mlw_access():
    """Verificar acesso a MTOW/MLW via AppConfig"""
    print("\n✓ Test 7: MTOW/MLW access via AppConfig")
    
    e190_mtow = AppConfig.get_model_mtow("e190")
    e190_mlw = AppConfig.get_model_mlw("e190")
    e195_mtow = AppConfig.get_model_mtow("e195")
    e195_mlw = AppConfig.get_model_mlw("e195")
    
    print(f"  └─ E190: MTOW {e190_mtow} lbs, MLW {e190_mlw} lbs")
    print(f"  └─ E195: MTOW {e195_mtow} lbs, MLW {e195_mlw} lbs")
    
    assert e190_mtow == 123676, f"E190 MTOW errado: {e190_mtow}"
    assert e195_mtow == 133289, f"E195 MTOW errado: {e195_mtow}"
    assert e195_mtow > e190_mtow, "E195 deve ser mais pesado que E190"


def test_all_models_listed():
    """Verificar que todos os 8 modelos estão listados"""
    print("\n✓ Test 8: Lista completa de modelos")
    
    all_models = AppConfig.list_all_models()
    print(f"  └─ Total de modelos: {len(all_models)}")
    print(f"  └─ Modelos: {sorted(all_models)}")
    
    expected = {"e145", "e170", "e175", "e190", "e195", "e175_e2", "e190_e2", "e195_e2"}
    assert set(all_models) == expected, f"Modelos não correspondem: {set(all_models) ^ expected}"


def main():
    """Executar todos os testes"""
    print("=" * 80)
    print("ETAPA 1 - TESTES DE INFRAESTRUTURA DE MODELO")
    print("=" * 80)
    
    tests = [
        test_model_registry_exists,
        test_e170_vs_e190_recognition,
        test_e190_vs_e195_weight_difference,
        test_e170_vs_e175_weight_difference,
        test_family_to_model_mapping,
        test_app_config_integration,
        test_mtow_mlw_access,
        test_all_models_listed,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  ✗ FALHA: {str(e)}")
    
    print("\n" + "=" * 80)
    print(f"RESULTADO: {passed} PASSOU, {failed} FALHOU")
    print("=" * 80)
    
    if failed == 0:
        print("\n✅ ETAPA 1 VALIDADA COM SUCESSO!")
        print("Sistema agora reconhece corretamente:")
        print("  • E170 vs E190 como modelos diferentes")
        print("  • E175 vs E170 peso diferente (+2000 kg)")
        print("  • E195 vs E190 peso diferente (+4350 kg)")
        print("  • Hard Landing PDF diferente (801 vs 804)")
        return 0
    else:
        print(f"\n❌ {failed} teste(s) falharam. Corrigir antes de prosseguir.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

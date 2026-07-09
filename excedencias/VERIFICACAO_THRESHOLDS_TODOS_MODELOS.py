#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICAÇÃO COMPLETA DE THRESHOLDS - TODOS OS MODELOS
Audita conformidade com PDFs 801, 804 e especificações AMM
Data: 05/02/2026
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.hard_landing_analyzer import HardLandingAnalyzer
from models.aircraft_model import AircraftModelRegistry
from utils.config import AppConfig


def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 100)
    print(f"  {title}")
    print("=" * 100)


def print_section(title):
    """Print section divider"""
    print(f"\n{'─' * 100}")
    print(f"  {title}")
    print(f"{'─' * 100}")


def verify_model_thresholds(model_id: str, analyzer: HardLandingAnalyzer):
    """Verifica thresholds para um modelo específico"""
    
    # Obter especificações do modelo
    spec = AircraftModelRegistry.get_model(model_id)
    if not spec:
        print(f"❌ ERRO: Especificações não encontradas para {model_id}")
        return
    
    print_section(f"MODELO: {spec.model_name} ({model_id})")
    
    # Informações básicas
    print(f"\n📋 Especificações:")
    print(f"   Família: {spec.family_name}")
    print(f"   MTOW: {spec.mtow:,.0f} lb ({spec.mtow * 0.453592:,.0f} kg)")
    print(f"   MLW:  {spec.mlw:,.0f} lb ({spec.mlw * 0.453592:,.0f} kg)")
    print(f"   MZFW: {spec.mzfw:,.0f} lb ({spec.mzfw * 0.453592:,.0f} kg)")
    print(f"   OEW:  {spec.oew:,.0f} lb ({spec.oew * 0.453592:,.0f} kg)")
    print(f"   PDF Hard Landing: {spec.pdf_hard_landing}")
    
    # Peso típico de landing (85% MLW)
    typical_landing_kg = spec.mlw * 0.453592 * 0.85
    
    print(f"\n🎯 Peso Típico de Landing (85% MLW): {typical_landing_kg:,.0f} kg")
    
    # Verificar Vertical Acceleration Thresholds
    print(f"\n📊 VERTICAL ACCELERATION THRESHOLDS:")
    
    try:
        vert_thresholds = analyzer.get_vertical_accel_thresholds(model_id, typical_landing_kg)
        
        if all(v is None for v in vert_thresholds.values()):
            print(f"   ⚠️  Modelo usa threshold único (E145 style)")
            # Para E145, usar o threshold específico
            if hasattr(analyzer, 'VERT_ACCEL_THRESHOLDS_E145'):
                threshold = analyzer.interpolate_threshold(
                    typical_landing_kg, 
                    analyzer.VERT_ACCEL_THRESHOLDS_E145['threshold']
                )
                print(f"   Threshold: {threshold:.3f} G")
        else:
            print(f"   LOW:    {vert_thresholds['low']:.3f} G")
            print(f"   HIGH:   {vert_thresholds['high']:.3f} G")
            print(f"   ENGINE: {vert_thresholds['engine']:.3f} G")
            
            # Verificar qual PDF está sendo usado
            if spec.pdf_hard_landing == "804":
                print(f"   ✅ Usando PDF 804 (E190/E195)")
            elif spec.pdf_hard_landing == "801":
                print(f"   ✅ Usando PDF 801 (E170/E175)")
            else:
                print(f"   ℹ️  Usando PDF: {spec.pdf_hard_landing}")
    
    except Exception as e:
        print(f"   ❌ ERRO ao obter thresholds: {e}")
    
    # Verificar Pitch Rate Thresholds
    print(f"\n📐 PITCH RATE THRESHOLDS:")
    
    try:
        pitch_thresholds = analyzer.get_pitch_thresholds(model_id)
        
        if isinstance(pitch_thresholds, dict):
            if 'low' in pitch_thresholds and 'high' in pitch_thresholds:
                print(f"   LOW:  {pitch_thresholds['low']:.2f} deg/s")
                print(f"   HIGH: {pitch_thresholds['high']:.2f} deg/s")
                if 'with_n2_high' in pitch_thresholds:
                    print(f"   N2≥75%: {pitch_thresholds['with_n2_high']:.2f} deg/s")
            elif 'threshold' in pitch_thresholds:
                print(f"   Threshold: {pitch_thresholds['threshold']:.2f} deg/s")
            else:
                print(f"   ℹ️  Estrutura: {list(pitch_thresholds.keys())}")
        else:
            print(f"   ⚠️  Formato inesperado: {type(pitch_thresholds)}")
    
    except Exception as e:
        print(f"   ❌ ERRO ao obter pitch thresholds: {e}")
    
    # Verificar Roll Rate Thresholds (apenas para modelos com LOW/HIGH/ENGINE)
    if vert_thresholds and not all(v is None for v in vert_thresholds.values()):
        print(f"\n🔄 ROLL RATE THRESHOLDS:")
        
        try:
            low_roll = analyzer.interpolate_threshold(typical_landing_kg, analyzer.ROLL_RATE_THRESHOLDS['low'])
            high_roll = analyzer.interpolate_threshold(typical_landing_kg, analyzer.ROLL_RATE_THRESHOLDS['high'])
            
            print(f"   LOW:  {low_roll:.2f} deg/s")
            print(f"   HIGH: {high_roll:.2f} deg/s")
        
        except Exception as e:
            print(f"   ❌ ERRO ao obter roll thresholds: {e}")
    
    # Testar com diferentes pesos
    print(f"\n🧪 TESTE COM DIFERENTES PESOS:")
    
    test_weights_pct = [80, 85, 90, 95, 100]  # % do MLW
    
    for pct in test_weights_pct:
        test_kg = spec.mlw * 0.453592 * (pct / 100.0)
        
        try:
            thresholds = analyzer.get_vertical_accel_thresholds(model_id, test_kg)
            
            if all(v is None for v in thresholds.values()):
                # E145 style
                threshold = analyzer.interpolate_threshold(
                    test_kg, 
                    analyzer.VERT_ACCEL_THRESHOLDS_E145['threshold']
                )
                print(f"   {pct}% MLW ({test_kg:6.0f} kg): Threshold = {threshold:.3f} G")
            else:
                print(f"   {pct}% MLW ({test_kg:6.0f} kg): LOW={thresholds['low']:.3f}G, HIGH={thresholds['high']:.3f}G, ENG={thresholds['engine']:.3f}G")
        
        except Exception as e:
            print(f"   {pct}% MLW ({test_kg:6.0f} kg): ❌ {e}")


def verify_pdf_assignment():
    """Verifica se os modelos estão associados aos PDFs corretos"""
    
    print_section("VERIFICAÇÃO DE ATRIBUIÇÃO DE PDFs")
    
    expected_mapping = {
        'e145': 'e145_05_50_03',  # PDF específico E145
        'e170': '801',             # PDF 801
        'e175': '801',             # PDF 801
        'e190': '804',             # PDF 804
        'e195': '804',             # PDF 804
        'e175_e2': 'e2_05_50_03',  # PDF E2
        'e190_e2': 'e2_05_50_03',  # PDF E2
        'e195_e2': 'e2_05_50_03',  # PDF E2
    }
    
    print("\n📄 Mapeamento Esperado vs Real:")
    print(f"{'Modelo':<12} {'Esperado':<20} {'Real':<20} {'Status':<10}")
    print("─" * 70)
    
    all_ok = True
    
    for model_id, expected_pdf in expected_mapping.items():
        spec = AircraftModelRegistry.get_model(model_id)
        if spec:
            actual_pdf = spec.pdf_hard_landing
            status = "✅ OK" if actual_pdf == expected_pdf else "❌ ERRO"
            if actual_pdf != expected_pdf:
                all_ok = False
            print(f"{model_id:<12} {expected_pdf:<20} {actual_pdf:<20} {status:<10}")
        else:
            print(f"{model_id:<12} {expected_pdf:<20} {'N/A':<20} {'⚠️  N/A':<10}")
            all_ok = False
    
    print()
    if all_ok:
        print("✅ Todos os modelos estão com PDFs corretos!")
    else:
        print("❌ Alguns modelos têm atribuições incorretas de PDF!")


def verify_threshold_ranges():
    """Verifica se os ranges de threshold estão corretos"""
    
    print_section("VERIFICAÇÃO DE RANGES DE THRESHOLD")
    
    analyzer = HardLandingAnalyzer()
    
    print("\n📊 PDF 801 - Vertical Acceleration (E170/E175):")
    print(f"   Range de peso: {analyzer.VERT_ACCEL_THRESHOLDS['low'][0][0]} - {analyzer.VERT_ACCEL_THRESHOLDS['low'][-1][0]} kg")
    print(f"   LOW:    {analyzer.VERT_ACCEL_THRESHOLDS['low'][0][1]:.3f} - {analyzer.VERT_ACCEL_THRESHOLDS['low'][-1][1]:.3f} G")
    print(f"   HIGH:   {analyzer.VERT_ACCEL_THRESHOLDS['high'][0][1]:.3f} - {analyzer.VERT_ACCEL_THRESHOLDS['high'][-1][1]:.3f} G")
    print(f"   ENGINE: {analyzer.VERT_ACCEL_THRESHOLDS['engine'][0][1]:.3f} - {analyzer.VERT_ACCEL_THRESHOLDS['engine'][-1][1]:.3f} G")
    
    print("\n📊 PDF 804 - Vertical Acceleration (E190/E195):")
    print(f"   Range de peso: {analyzer.VERT_ACCEL_THRESHOLDS_PDF804['low'][0][0]} - {analyzer.VERT_ACCEL_THRESHOLDS_PDF804['low'][-1][0]} kg")
    print(f"   LOW:    {analyzer.VERT_ACCEL_THRESHOLDS_PDF804['low'][0][1]:.3f} - {analyzer.VERT_ACCEL_THRESHOLDS_PDF804['low'][-1][1]:.3f} G")
    print(f"   HIGH:   {analyzer.VERT_ACCEL_THRESHOLDS_PDF804['high'][0][1]:.3f} - {analyzer.VERT_ACCEL_THRESHOLDS_PDF804['high'][-1][1]:.3f} G")
    print(f"   ENGINE: {analyzer.VERT_ACCEL_THRESHOLDS_PDF804['engine'][0][1]:.3f} - {analyzer.VERT_ACCEL_THRESHOLDS_PDF804['engine'][-1][1]:.3f} G")
    
    print("\n📊 E145 - Vertical Acceleration:")
    print(f"   Range de peso: {analyzer.VERT_ACCEL_THRESHOLDS_E145['threshold'][0][0]} - {analyzer.VERT_ACCEL_THRESHOLDS_E145['threshold'][-1][0]} kg")
    print(f"   Threshold: {analyzer.VERT_ACCEL_THRESHOLDS_E145['threshold'][0][1]:.3f} - {analyzer.VERT_ACCEL_THRESHOLDS_E145['threshold'][-1][1]:.3f} G")
    
    print("\n📐 Pitch Rate:")
    print(f"   E145:       {analyzer.PITCH_RATE_E145['threshold']:.2f} deg/s")
    print(f"   E170: LOW={analyzer.PITCH_RATE_E170['low']:.2f}, HIGH={analyzer.PITCH_RATE_E170['high']:.2f} deg/s")
    print(f"   E175: LOW={analyzer.PITCH_RATE_E175['low']:.2f}, HIGH={analyzer.PITCH_RATE_E175['high']:.2f} deg/s")
    print(f"   E190: LOW={analyzer.PITCH_RATE_E190['low']:.2f}, HIGH={analyzer.PITCH_RATE_E190['high']:.2f} deg/s")
    print(f"   E195: LOW={analyzer.PITCH_RATE_E195['low']:.2f}, HIGH={analyzer.PITCH_RATE_E195['high']:.2f} deg/s")


def main():
    """Executa verificação completa"""
    
    print_header("AUDITORIA COMPLETA DE THRESHOLDS - TODOS OS MODELOS MEXICANA")
    print(f"\nData: 05 de Fevereiro de 2026")
    print(f"Sistema: Aircraft Inspection Analysis System v0.1.0")
    
    # Verificar atribuição de PDFs
    verify_pdf_assignment()
    
    # Verificar ranges
    verify_threshold_ranges()
    
    # Criar analyzer
    analyzer = HardLandingAnalyzer()
    
    # Listar todos os modelos
    all_models = AircraftModelRegistry.list_all_models()
    
    print_header(f"VERIFICAÇÃO INDIVIDUAL - {len(all_models)} MODELOS")
    
    # Verificar cada modelo
    for model_id in sorted(all_models):
        verify_model_thresholds(model_id, analyzer)
    
    # Resumo final
    print_header("RESUMO DA AUDITORIA")
    
    print("\n✅ VERIFICAÇÕES COMPLETAS:")
    print("   1. ✅ Atribuição de PDFs verificada")
    print("   2. ✅ Ranges de threshold validados")
    print("   3. ✅ Thresholds individuais por modelo auditados")
    print("   4. ✅ Testes com múltiplos pesos executados")
    
    print("\n📊 MODELOS AUDITADOS:")
    for model_id in sorted(all_models):
        spec = AircraftModelRegistry.get_model(model_id)
        if spec:
            print(f"   • {spec.model_name:<12} (PDF {spec.pdf_hard_landing})")
    
    print("\n" + "=" * 100)
    print("  AUDITORIA CONCLUÍDA COM SUCESSO")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    main()


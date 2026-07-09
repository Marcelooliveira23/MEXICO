#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análise de Conformidade Hard Landing - E170
Comparação: Código implementado vs. Especificações Mexicana AMM 05-50-03
Data: 2026-01-17
"""

import pandas as pd
import sys
import os
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.hard_landing_analyzer import HardLandingAnalyzer
from services.csv_parser import CSVParser


def analyze_e170_conformance():
    """Analisa conformidade E170 Hard Landing contra especificações"""
    
    print("=" * 80)
    print("ANÁLISE DE CONFORMIDADE - HARD LANDING E170")
    print("=" * 80)
    print()
    
    # Dados do teste
    data_dir = Path("Analises de dados de voo/HARDINGLANDING E170")
    
    if not data_dir.exists():
        print(f"[ERRO] Diretório não encontrado: {data_dir}")
        return
    
    # Listar arquivos CSV
    csv_files = list(data_dir.glob("*.csv"))
    print(f"[INFO] Arquivos encontrados: {len(csv_files)}")
    for f in csv_files:
        print(f"   - {f.name} ({f.stat().st_size / (1024*1024):.2f} MB)")
    print()
    
    if not csv_files:
        print("[ERRO] Nenhum arquivo CSV encontrado")
        return
    
    # Processar primeiro arquivo
    csv_file = csv_files[0]
    print(f"[INFO] Processando: {csv_file.name}")
    print()
    
    try:
        # Carregar dados
        parser = CSVParser()
        df = parser.parse_file(csv_file)
        
        print(f"[OK] Dados carregados: {len(df)} linhas, {len(df.columns)} colunas")
        print(f"   Período: {df.index[0]} a {df.index[-1]}")
        print(f"   Colunas: {', '.join(df.columns.tolist()[:5])}...")
        print()
        
        # Análise com E170 isolada
        analyzer = HardLandingAnalyzer()
        weight_kg = 36000.0  # E170 typical operating weight
        results = analyzer.analyze(df, weight_kg, 'E170')

        print(f"[RESULTADO] Analise completada:")
        print(f"   Total de voos analisados: {len(results)}")

        # Contar hard landings
        hard_landings = [r for r in results if 'HARD_LANDING' in r.status or 'ENGINE_INSPECTION' in r.status]
        print(f"   Hard landings detectados: {len(hard_landings)}")
        print()

        # Identificar colunas disponíveis para info extra
        flight_number_col = None
        timestamp_col = None
        for c in df.columns:
            if c.lower() in ["flight_number", "flight", "flt", "flight_no", "flight_id", "numero_voo", "voo", "flt_num", "flightnum", "flight_nbr", "fltnbr"]:
                flight_number_col = c
            if c.lower() in ["timestamp", "time", "datetime", "date_time", "hora", "data_hora", "data", "horario", "utc", "gmt_time", "local_time"]:
                timestamp_col = c

        if hard_landings:
            print("[EVENTOS] HARD LANDING DETECTADOS:")
            for i, event in enumerate(hard_landings, 1):
                # Tentar obter índice do touchdown relativo ao DataFrame
                touchdown_idx = None
                if event.vertical_accel and 'range' in event.vertical_accel:
                    touchdown_idx = event.vertical_accel['range'][0] + 32  # 32 amostras antes do touchdown
                # Buscar info extra
                flight_number = None
                event_time = None
                if touchdown_idx is not None:
                    if flight_number_col and touchdown_idx < len(df):
                        flight_number = df.iloc[touchdown_idx][flight_number_col]
                    if timestamp_col and touchdown_idx < len(df):
                        event_time = df.iloc[touchdown_idx][timestamp_col]
                print(f"\n   {i}. Status: {event.status}")
                if flight_number is not None:
                    print(f"      Número do Voo: {flight_number}")
                if event_time is not None:
                    print(f"      Data/Hora do Evento: {event_time}")
                print(f"      Peso: {event.weight_kg:.0f} kg")
                print(f"      Vertical Accel: {event.vertical_accel.get('status', 'N/A') if event.vertical_accel else 'N/A'}")
                print(f"      Roll Rate: {event.roll_rate.get('status', 'N/A') if event.roll_rate else 'N/A'}")
                print(f"      Pitch Rate: {event.pitch_rate.get('status', 'N/A') if event.pitch_rate else 'N/A'}")
                print(f"      Severity: {event.severity}")
                if event.message:
                    print(f"      Message: {event.message[:100]}...")

        print()
        print("=" * 80)
        print("[CONFORMIDADE] VERIFICACAO DE CONFORMIDADE")
        print("=" * 80)
        print()

        # Verificar thresholds E170
        print("Thresholds E170 Implementados:")
        print()
        print("  Vertical Acceleration (Generico E1/E2):")
        print("    - Low:    1.800-2.200 G (peso interpolado)")
        print("    - High:   2.100-2.500 G (peso interpolado)")
        print("    - Engine: 2.400-2.800 G (peso interpolado)")
        print()
        print("  Pitch Rate:")
        print("    - Threshold: -5.50 a -6.10 deg/s")
        print()
        print("  Roll Rate:")
        print("    - Low:    10.00-14.00 deg/s (peso interpolado)")
        print("    - High:   16.00-22.40 deg/s (peso interpolado)")
        print()

        # Status
        if hard_landings:
            print("[OK] Hard landings foram detectados com sucesso")
            print("   > Validar se os valores de G estao realistas")
            print("   > Comparar com especificacoes Mexicana nos PDFs")
        else:
            print("[WARN] Nenhum hard landing foi detectado")
            print("   > Verificar se o arquivo contem eventos reais")
            print("   > Revisar thresholds de conformidade")

        print()
        
    except Exception as e:
        print(f"[ERRO] Erro ao processar: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    analyze_e170_conformance()


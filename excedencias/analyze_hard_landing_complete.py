"""
ANALISADOR COMPLETO DE HARD LANDING - E190/E195
Baseado em: AMM TASK 05-50-03-200-801-A (Rev 121)

Monitora:
1. Vertical Acceleration (NormAccel) - Figure 607
2. Roll Rate - Figure 608 + Figure 614 (validação)
3. Pitch Rate - Figure 609

Detecta múltiplos voos e eventos por arquivo
Gera gráficos para todos os eventos (confirmados ou não)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import os
from datetime import datetime

class HardLandingAnalyzer:
    """Analisador de Hard Landing conforme AMM E190"""
    
    # THRESHOLDS E190 - Figure 607 (Vertical Acceleration)
    VERT_ACCEL_THRESHOLDS = {
        'low': [
            (29500, 2.30),   # A
            (44000, 1.85),   # B
            (52290, 1.70)    # C
        ],
        'high': [
            (29500, 2.76),   # D
            (44000, 2.22),   # E
            (52290, 2.04)    # F
        ],
        'engine': [
            (29500, 2.30),   # A
            (52290, 2.30)    # G
        ]
    }
    
    # THRESHOLDS - Figure 608 (Roll Rate)
    ROLL_RATE_THRESHOLDS = {
        'low': [
            (29500, 13.0),   # A
            (52290, 5.3)     # C
        ],
        'high': [
            (29500, 14.3),   # B
            (52290, 5.8)     # D
        ],
        'engine': [
            (29500, 13.0),   # A
            (52290, 13.0)    # E
        ]
    }
    
    # THRESHOLDS - Figure 614 (Roll Rate Validation)
    ROLL_RATE_VALIDATION = [
        (29000, 1.81),
        (52000, 1.345)
    ]
    
    # THRESHOLDS - Figure 609 (Pitch Rate)
    PITCH_RATE_E190 = {
        'low': -6.00,
        'high': -6.60
    }
    
    PITCH_RATE_E195 = {
        'low': -5.50,
        'high': -6.05
    }
    
    def __init__(self, aircraft_model='E190'):
        self.aircraft_model = aircraft_model
        self.pitch_thresholds = self.PITCH_RATE_E190 if aircraft_model == 'E190' else self.PITCH_RATE_E195
        
    def interpolate_threshold(self, weight_kg, threshold_table):
        """Interpola threshold baseado no peso"""
        if weight_kg <= threshold_table[0][0]:
            return threshold_table[0][1]
        if weight_kg >= threshold_table[-1][0]:
            return threshold_table[-1][1]
        
        for i in range(len(threshold_table) - 1):
            w1, t1 = threshold_table[i]
            w2, t2 = threshold_table[i + 1]
            if w1 <= weight_kg <= w2:
                # Interpolação linear
                ratio = (weight_kg - w1) / (w2 - w1)
                return t1 + ratio * (t2 - t1)
        return threshold_table[-1][1]
    
    def detect_flights(self, df, air_ground_col):
        """Detecta múltiplos voos no arquivo"""
        flights = []
        in_flight = False
        flight_start = None
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            status = str(row[air_ground_col]).strip().upper()
            
            if status == 'AIR' and not in_flight:
                in_flight = True
                flight_start = idx
            elif status == 'GROUND' and in_flight and flight_start is not None:
                # Final do voo - touchdown
                flight_end = idx
                flights.append({
                    'start': flight_start,
                    'touchdown': flight_end,
                    'end': min(flight_end + 200, len(df) - 1)  # 200 samples após touchdown
                })
                in_flight = False
                flight_start = None
        
        return flights if flights else [{'start': 0, 'touchdown': 0, 'end': len(df) - 1}]
    
    def analyze_vertical_acceleration(self, df, flight_data, weight_kg, accel_col):
        """
        Análise conforme Figure 602 + Figure 607
        Range: 4 segundos ANTES do primeiro GROUND até pitch <= -0.5°
        """
        touchdown_idx = flight_data['touchdown']
        
        # Range de análise (Figure 606)
        # 4 segundos antes = 4 * 8 samples = 32 samples (8 sps)
        start_idx = max(0, touchdown_idx - 32)
        
        # Até pitch <= -0.5 graus
        end_idx = touchdown_idx + 100  # Padrão se não achar pitch
        if 'Pitch Angle' in df.columns or 'Pitch' in df.columns:
            pitch_col = 'Pitch Angle' if 'Pitch Angle' in df.columns else 'Pitch'
            pitch_data = pd.to_numeric(df[pitch_col], errors='coerce')
            for idx in range(touchdown_idx, min(touchdown_idx + 200, len(df))):
                if pitch_data.iloc[idx] <= -0.5:
                    end_idx = idx
                    break
        
        # Extrair range
        analysis_df = df.iloc[start_idx:end_idx].copy()
        analysis_df[accel_col] = pd.to_numeric(analysis_df[accel_col], errors='coerce')
        clean_df = analysis_df[analysis_df[accel_col].notna()]
        
        if len(clean_df) == 0:
            return None
        
        # Pico máximo
        max_g = float(clean_df[accel_col].max())
        max_idx_raw = clean_df[accel_col].idxmax()
        max_idx = int(max_idx_raw) if not isinstance(max_idx_raw, tuple) else int(max_idx_raw[0])
        
        # Thresholds interpolados
        low_threshold = self.interpolate_threshold(weight_kg, self.VERT_ACCEL_THRESHOLDS['low'])
        high_threshold = self.interpolate_threshold(weight_kg, self.VERT_ACCEL_THRESHOLDS['high'])
        engine_threshold = self.interpolate_threshold(weight_kg, self.VERT_ACCEL_THRESHOLDS['engine'])
        
        # Classificação
        status = 'NORMAL'
        phase = None
        
        if max_g > high_threshold:
            status = 'HIGH LOAD'
            phase = 'Phase-II'
        elif max_g > low_threshold:
            status = 'HARD LANDING'
            phase = 'Phase-I + Phase-II (within 6250 FC or 50 HL events)'
        
        engine_status = 'EXCEEDS ENGINE THRESHOLD' if max_g > engine_threshold else 'OK'
        
        return {
            'monitor': 'Vertical Acceleration',
            'max_value': max_g,
            'max_index': max_idx,
            'weight_kg': weight_kg,
            'low_threshold': low_threshold,
            'high_threshold': high_threshold,
            'engine_threshold': engine_threshold,
            'status': status,
            'phase': phase,
            'engine_status': engine_status,
            'range_start': start_idx,
            'range_end': end_idx,
            'data': clean_df
        }
    
    def analyze_roll_rate(self, df, flight_data, weight_kg, roll_col, accel_col):
        """
        Análise conforme Figure 603 + Figure 608
        Validação: Figure 614 - NormAccel deve exceder threshold mínimo
        Range: 2 segundos ANTES e DEPOIS do pico de vertical accel
        """
        touchdown_idx = flight_data['touchdown']
        
        # Primeiro: validação Figure 614
        start_val = max(0, touchdown_idx - 32)
        end_val = touchdown_idx + 100
        val_df = df.iloc[start_val:end_val].copy()
        val_df[accel_col] = pd.to_numeric(val_df[accel_col], errors='coerce')
        
        if val_df[accel_col].max() <= self.interpolate_threshold(weight_kg, self.ROLL_RATE_VALIDATION):
            return {
                'monitor': 'Roll Rate',
                'status': 'VALIDATION FAILED',
                'message': 'NormAccel below minimum threshold - Roll Rate analysis not applicable (Figure 614)'
            }
        
        # Encontrar pico de vertical accel
        max_accel_loc = val_df[accel_col].idxmax()
        if isinstance(max_accel_loc, tuple):
            max_accel_idx = int(max_accel_loc[0])
        elif isinstance(max_accel_loc, (np.integer, np.floating)):
            max_accel_idx = int(max_accel_loc)
        else:
            max_accel_idx = int(max_accel_loc)
        
        # Range: ±2 segundos (±16 samples @ 8sps)
        start_idx = max(0, int(max_accel_idx) - 16)
        end_idx = min(len(df) - 1, int(max_accel_idx) + 16)
        
        analysis_df = df.iloc[start_idx:end_idx].copy()
        analysis_df[roll_col] = pd.to_numeric(analysis_df[roll_col], errors='coerce')
        clean_df = analysis_df[analysis_df[roll_col].notna()]
        
        if len(clean_df) < 2:
            return None
        
        # Calcular Roll Rate (Figure 608)
        # RR_i = (R_i - R_i-1) / 0.5
        roll_rates = []
        for i in range(1, len(clean_df)):
            roll_diff = clean_df[roll_col].iloc[i] - clean_df[roll_col].iloc[i-1]
            roll_rate = roll_diff / 0.125  # 0.125s interval @ 8sps
            roll_rates.append(abs(roll_rate))  # Absolute value per PDF
        
        max_roll_rate = max(roll_rates) if roll_rates else 0
        
        # Thresholds
        low_threshold = self.interpolate_threshold(weight_kg, self.ROLL_RATE_THRESHOLDS['low'])
        high_threshold = self.interpolate_threshold(weight_kg, self.ROLL_RATE_THRESHOLDS['high'])
        engine_threshold = self.interpolate_threshold(weight_kg, self.ROLL_RATE_THRESHOLDS['engine'])
        
        # Classificação
        status = 'NORMAL'
        phase = None
        
        if max_roll_rate > high_threshold:
            status = 'HIGH LOAD'
            phase = 'Phase-II'
        elif max_roll_rate > low_threshold:
            status = 'HARD LANDING'
            phase = 'Phase-I + Phase-II (within 6250 FC or 50 HL events)'
        
        engine_status = 'EXCEEDS ENGINE THRESHOLD' if max_roll_rate > engine_threshold else 'OK'
        
        return {
            'monitor': 'Roll Rate',
            'max_value': max_roll_rate,
            'weight_kg': weight_kg,
            'low_threshold': low_threshold,
            'high_threshold': high_threshold,
            'engine_threshold': engine_threshold,
            'status': status,
            'phase': phase,
            'engine_status': engine_status,
            'roll_rates': roll_rates,
            'data': clean_df
        }
    
    def analyze_pitch_rate(self, df, flight_data, pitch_col, accel_col):
        """
        Análise conforme Figure 604 + Figure 609
        Range: De pitch < 4.0° até pitch <= -0.5°
        """
        touchdown_idx = flight_data['touchdown']
        
        # Encontrar pico de vertical accel
        start_search = max(0, touchdown_idx - 32)
        end_search = touchdown_idx + 100
        search_df = df.iloc[start_search:end_search].copy()
        search_df[accel_col] = pd.to_numeric(search_df[accel_col], errors='coerce')
        
        # Obter índice máximo como inteiro
        max_accel_loc = search_df[accel_col].idxmax()
        if isinstance(max_accel_loc, tuple):
            max_accel_idx = int(max_accel_loc[0])
        elif isinstance(max_accel_loc, (np.integer, np.floating)):
            max_accel_idx = int(max_accel_loc)
        else:
            max_accel_idx = int(max_accel_loc)
        
        # Range de análise (Figure 606)
        pitch_data = pd.to_numeric(df[pitch_col], errors='coerce')
        
        # Início: primeira amostra com pitch < 4.0° após pico accel
        start_idx = max_accel_idx
        for idx in range(int(max_accel_idx), min(int(max_accel_idx) + 200, len(df))):
            if pd.notna(pitch_data.iloc[idx]) and pitch_data.iloc[idx] < 4.0:
                start_idx = idx
                break
        
        # Fim: primeira amostra com pitch <= -0.5°
        end_idx = start_idx + 100
        for idx in range(int(start_idx), min(int(start_idx) + 200, len(df))):
            if pd.notna(pitch_data.iloc[idx]) and pitch_data.iloc[idx] <= -0.5:
                end_idx = idx
                break
        
        analysis_df = df.iloc[start_idx:end_idx].copy()
        analysis_df[pitch_col] = pd.to_numeric(analysis_df[pitch_col], errors='coerce')
        clean_df = analysis_df[analysis_df[pitch_col].notna()]
        
        if len(clean_df) < 2:
            return None
        
        # Calcular Pitch Rate (Figure 609)
        # THPi = (THi - THi-1) / 0.25
        pitch_rates = []
        for i in range(1, len(clean_df)):
            pitch_diff = clean_df[pitch_col].iloc[i] - clean_df[pitch_col].iloc[i-1]
            pitch_rate = pitch_diff / 0.125  # 0.125s @ 8sps
            pitch_rates.append(pitch_rate)
        
        min_pitch_rate = min(pitch_rates) if pitch_rates else 0
        
        # Thresholds (Figure 609)
        low_threshold = self.pitch_thresholds['low']
        high_threshold = self.pitch_thresholds['high']
        
        # Classificação
        status = 'NORMAL'
        phase = None
        
        if min_pitch_rate < high_threshold:
            status = 'HIGH LOAD'
            phase = 'Phase-II'
        elif min_pitch_rate < low_threshold:
            status = 'HARD LANDING'
            phase = 'Phase-I + Phase-II (within 6250 FC or 50 HL events)'
        
        return {
            'monitor': 'Pitch Rate',
            'min_value': min_pitch_rate,
            'low_threshold': low_threshold,
            'high_threshold': high_threshold,
            'status': status,
            'phase': phase,
            'pitch_rates': pitch_rates,
            'data': clean_df
        }
    
    def plot_results(self, results, filename, output_dir):
        """Gera gráficos dos resultados"""
        num_monitors = len([r for r in results if r is not None and 'data' in r])
        if num_monitors == 0:
            return
        
        fig, axes = plt.subplots(num_monitors, 1, figsize=(12, 4 * num_monitors))
        if num_monitors == 1:
            axes = [axes]
        
        plot_idx = 0
        
        for result in results:
            if result is None or 'data' not in result:
                continue
            
            ax = axes[plot_idx]
            monitor = result['monitor']
            
            if monitor == 'Vertical Acceleration':
                data = result['data'].reset_index(drop=True)
                accel_col = [c for c in data.columns if 'accel' in c.lower() and 'vert' in c.lower() or 'norm' in c.lower()][0]
                
                ax.plot(range(len(data)), data[accel_col], 'b-', linewidth=2, label='Vertical Acceleration')
                ax.axhline(y=result['low_threshold'], color='orange', linestyle='--', label=f'Low Threshold ({result["low_threshold"]:.2f}G)')
                ax.axhline(y=result['high_threshold'], color='red', linestyle='--', label=f'High Load ({result["high_threshold"]:.2f}G)')
                ax.axhline(y=result['engine_threshold'], color='purple', linestyle=':', label=f'Engine ({result["engine_threshold"]:.2f}G)')
                
                max_pos = len(data) // 2  # Aproximação visual
                ax.scatter([max_pos], [result['max_value']], color='red', s=100, zorder=5, label=f'Peak: {result["max_value"]:.3f}G')
                
                ax.set_ylabel('Vertical Accel (G)', fontsize=12, fontweight='bold')
                ax.set_title(f'{monitor} - Status: {result["status"]}', fontsize=14, fontweight='bold')
                ax.legend(loc='best')
                ax.grid(True, alpha=0.3)
                
            elif monitor == 'Roll Rate':
                if 'message' in result:
                    ax.text(0.5, 0.5, result['message'], ha='center', va='center', fontsize=12, transform=ax.transAxes)
                    ax.set_title(f'{monitor} - {result["status"]}', fontsize=14, fontweight='bold')
                else:
                    roll_rates = result['roll_rates']
                    indices = list(range(len(roll_rates)))
                    
                    ax.plot(indices, roll_rates, 'g-', linewidth=2, label='Roll Rate')
                    ax.axhline(y=result['low_threshold'], color='orange', linestyle='--', label=f'Low ({result["low_threshold"]:.1f}°/s)')
                    ax.axhline(y=result['high_threshold'], color='red', linestyle='--', label=f'High Load ({result["high_threshold"]:.1f}°/s)')
                    
                    max_idx = roll_rates.index(max(roll_rates))
                    ax.scatter([max_idx], [result['max_value']], color='red', s=100, zorder=5, label=f'Peak: {result["max_value"]:.1f}°/s')
                    
                    ax.set_ylabel('Roll Rate (°/s)', fontsize=12, fontweight='bold')
                    ax.set_title(f'{monitor} - Status: {result["status"]}', fontsize=14, fontweight='bold')
                    ax.legend(loc='best')
                    ax.grid(True, alpha=0.3)
            
            elif monitor == 'Pitch Rate':
                pitch_rates = result['pitch_rates']
                indices = list(range(len(pitch_rates)))
                
                ax.plot(indices, pitch_rates, 'm-', linewidth=2, label='Pitch Rate')
                ax.axhline(y=result['low_threshold'], color='orange', linestyle='--', label=f'Low ({result["low_threshold"]:.2f}°/s)')
                ax.axhline(y=result['high_threshold'], color='red', linestyle='--', label=f'High Load ({result["high_threshold"]:.2f}°/s)')
                
                min_idx = pitch_rates.index(min(pitch_rates))
                ax.scatter([min_idx], [result['min_value']], color='red', s=100, zorder=5, label=f'Min: {result["min_value"]:.2f}°/s')
                
                ax.set_ylabel('Pitch Rate (°/s)', fontsize=12, fontweight='bold')
                ax.set_title(f'{monitor} - Status: {result["status"]}', fontsize=14, fontweight='bold')
                ax.legend(loc='best')
                ax.grid(True, alpha=0.3)
            
            plot_idx += 1
        
        plt.tight_layout()
        output_path = os.path.join(output_dir, f'{filename}_analysis.png')
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"   📊 Gráfico salvo: {output_path}")


def analyze_file(file_path, output_dir):
    """Analisa um arquivo CSV completo"""
    print(f"\n{'='*100}")
    print(f"📁 ARQUIVO: {os.path.basename(file_path)}")
    print(f"{'='*100}")
    
    # Ler arquivo
    try:
        df = pd.read_csv(file_path, low_memory=False)
        print(f"✅ Carregado: {len(df)} linhas, {len(df.columns)} colunas")
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        return
    
    # Mapear colunas
    col_map = {}
    for col in df.columns:
        col_lower = col.lower()
        if 'normaccel' in col_lower or ('vertical' in col_lower and 'accel' in col_lower) or ('normal' in col_lower and 'load' in col_lower):
            col_map['accel'] = col
        elif 'roll' in col_lower and 'rate' not in col_lower:
            col_map['roll'] = col
        elif 'pitch' in col_lower and 'rate' not in col_lower:
            col_map['pitch'] = col
        elif 'air' in col_lower and 'ground' in col_lower or 'air/gnd' in col_lower:
            col_map['air_ground'] = col
        elif 'grossweight' in col_lower or ('gross' in col_lower and 'weight' in col_lower):
            col_map['weight'] = col
    
    print(f"\n📋 Colunas mapeadas:")
    for key, val in col_map.items():
        print(f"   {key}: '{val}'")
    
    # Verificar colunas essenciais
    if 'accel' not in col_map:
        print("❌ Coluna de aceleração vertical não encontrada!")
        return
    
    # Criar analisador
    analyzer = HardLandingAnalyzer('E190')
    
    # Detectar voos
    flights = analyzer.detect_flights(df, col_map.get('air_ground', df.columns[0]))
    print(f"\n✈️  Voos detectados: {len(flights)}")
    
    # Analisar cada voo
    for flight_num, flight_data in enumerate(flights, 1):
        print(f"\n{'─'*100}")
        print(f"✈️  VOO #{flight_num} - Linha {flight_data['start']} a {flight_data['end']}")
        print(f"{'─'*100}")
        
        # Obter peso
        weight_kg = 44000  # Default
        if 'weight' in col_map:
            weight_col = col_map['weight']
            weight_val = pd.to_numeric(df.iloc[flight_data['touchdown']][weight_col], errors='coerce')
            if pd.notna(weight_val) and weight_val > 1000:
                weight_kg = weight_val if weight_val < 100000 else weight_val * 0.453592  # lb to kg
        
        print(f"   Peso: {weight_kg:.0f} kg ({weight_kg * 2.20462:.0f} lb)")
        
        results = []
        
        # 1. Vertical Acceleration
        print(f"\n   🔍 Monitor 1: VERTICAL ACCELERATION")
        result_va = analyzer.analyze_vertical_acceleration(
            df, flight_data, weight_kg, col_map['accel']
        )
        if result_va:
            print(f"      Pico: {result_va['max_value']:.3f}G")
            print(f"      Low threshold: {result_va['low_threshold']:.3f}G")
            print(f"      High threshold: {result_va['high_threshold']:.3f}G")
            print(f"      Status: {result_va['status']}")
            if result_va['phase']:
                print(f"      ⚠️  Ação: {result_va['phase']}")
            print(f"      Engine: {result_va['engine_status']}")
            results.append(result_va)
        
        # 2. Roll Rate
        if 'roll' in col_map:
            print(f"\n   🔍 Monitor 2: ROLL RATE")
            result_rr = analyzer.analyze_roll_rate(
                df, flight_data, weight_kg, col_map['roll'], col_map['accel']
            )
            if result_rr:
                if 'message' in result_rr:
                    print(f"      {result_rr['message']}")
                else:
                    print(f"      Pico: {result_rr['max_value']:.1f}°/s")
                    print(f"      Low threshold: {result_rr['low_threshold']:.1f}°/s")
                    print(f"      High threshold: {result_rr['high_threshold']:.1f}°/s")
                    print(f"      Status: {result_rr['status']}")
                    if result_rr['phase']:
                        print(f"      ⚠️  Ação: {result_rr['phase']}")
                results.append(result_rr)
        
        # 3. Pitch Rate
        if 'pitch' in col_map:
            print(f"\n   🔍 Monitor 3: PITCH RATE")
            result_pr = analyzer.analyze_pitch_rate(
                df, flight_data, col_map['pitch'], col_map['accel']
            )
            if result_pr:
                print(f"      Mínimo: {result_pr['min_value']:.2f}°/s")
                print(f"      Low threshold: {result_pr['low_threshold']:.2f}°/s")
                print(f"      High threshold: {result_pr['high_threshold']:.2f}°/s")
                print(f"      Status: {result_pr['status']}")
                if result_pr['phase']:
                    print(f"      ⚠️  Ação: {result_pr['phase']}")
                results.append(result_pr)
        
        # Gerar gráficos
        filename = f"{Path(file_path).stem}_flight{flight_num}"
        analyzer.plot_results(results, filename, output_dir)
        
        # Resumo do voo
        any_hard_landing = any(r.get('status') in ['HARD LANDING', 'HIGH LOAD'] for r in results if r and 'status' in r)
        if any_hard_landing:
            print(f"\n   ⚠️  ⚠️  ⚠️  HARD LANDING DETECTADO - INSPEÇÃO NECESSÁRIA ⚠️  ⚠️  ⚠️")
        else:
            print(f"\n   ✅ NORMAL LANDING - Aeronave liberada para serviço")


# MAIN
if __name__ == '__main__':
    # Diretório de saída
    output_dir = r'e:\Projetos\excedencias\analises_hard_landing'
    os.makedirs(output_dir, exist_ok=True)
    
    # Arquivos para analisar
    arquivos = [
        r'c:\Users\mrced\OneDrive\Documents\hard landing\CRC212 20-2-25 Hard landing 1.csv',
        r'c:\Users\mrced\OneDrive\Documents\hard landing\XA-ALU _HL_13AGO25_FLT651.CSV',
        r'c:\Users\mrced\OneDrive\Documents\hard landing\HL XA-ALL AM593 20251026.csv',
        r'c:\Users\mrced\OneDrive\Documents\hard landing\CRC212 20-2-25 Hard landing 2.csv',
        r'c:\Users\mrced\OneDrive\Documents\hard landing\JAC.csv',
        r'c:\Users\mrced\OneDrive\Documents\hard landing\ALL.csv',
    ]
    
    print("="*100)
    print("ANALISADOR DE HARD LANDING - E190/E195")
    print("AMM TASK 05-50-03-200-801-A (Rev 121 - Apr 25/25)")
    print("="*100)
    print(f"\nDiretório de saída: {output_dir}")
    print(f"Total de arquivos: {len(arquivos)}")
    
    for arquivo in arquivos:
        if os.path.exists(arquivo):
            analyze_file(arquivo, output_dir)
        else:
            print(f"\n❌ Arquivo não encontrado: {arquivo}")
    
    print(f"\n{'='*100}")
    print("✅ ANÁLISE COMPLETA")
    print(f"📊 Gráficos salvos em: {output_dir}")
    print(f"{'='*100}")

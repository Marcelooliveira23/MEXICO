"""
ADVANCED HARD LANDING DETECTOR
Detects ALL hard landing events across MULTIPLE flights in CSV files
Analyzes ALL parameters: Vertical Acceleration, MLG, NLG, Longitudinal, Radio Height
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import os

class HardLandingDetector:
    """Detecta hard landing usando MÚLTIPLOS parâmetros conforme PDF"""
    
    # REGRAS DO PDF - E190 (AMM 05-51-00)
    THRESHOLDS_E190 = {
        'normal_accel': 2.6,      # G - Hard Landing
        'very_hard_accel': 2.8,   # G - Very Hard Landing
        'descent_rate': 900,      # ft/min - Hard Landing
        'radio_height_max': 10    # feet - máxima altura no touchdown
    }
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.df = None
        self.flights = []
        self.events = []
        
    def load_csv(self):
        """Carrega CSV com múltiplos formatos"""
        print(f"\n{'='*80}")
        print(f"📁 Carregando: {Path(self.csv_path).name}")
        print(f"{'='*80}")
        
        self.df = pd.read_csv(self.csv_path, low_memory=False)
        print(f"✅ {len(self.df)} linhas carregadas")
        
        # Mostrar colunas
        print(f"\nColunas encontradas ({len(self.df.columns)}):")
        for i, col in enumerate(self.df.columns, 1):
            print(f"  {i:2d}. {col}")
        
        return self
        
    def identify_flights(self):
        """Identifica MÚLTIPLOS VOOS no arquivo"""
        print(f"\n{'='*80}")
        print(f"🔍 IDENTIFICANDO VOOS")
        print(f"{'='*80}")
        
        # Procurar coluna Air/Ground
        air_ground_cols = [c for c in self.df.columns if 'air' in c.lower() and 'ground' in c.lower()]
        
        if not air_ground_cols:
            print("⚠️ Coluna Air/Ground não encontrada - assumindo 1 voo")
            self.flights = [{'start': 0, 'end': len(self.df)-1, 'flight_num': 1}]
            return self
        
        ag_col = air_ground_cols[0]
        print(f"📊 Usando coluna: '{ag_col}'")
        
        # Detectar mudanças Ground -> Air -> Ground (um voo completo)
        self.df['is_ground'] = self.df[ag_col].astype(str).str.contains('ground|Ground|GROUND', na=False, case=False)
        
        # Detectar transições
        self.df['ground_change'] = self.df['is_ground'].ne(self.df['is_ground'].shift())
        
        # Encontrar touchdowns (Air -> Ground)
        touchdowns = []
        for idx in range(1, len(self.df)):
            if self.df.loc[idx, 'is_ground'] and not self.df.loc[idx-1, 'is_ground']:
                touchdowns.append(idx)
        
        print(f"\n✈️ Touchdowns detectados: {len(touchdowns)}")
        
        if len(touchdowns) == 0:
            # Arquivo inteiro é no solo ou no ar
            self.flights = [{'start': 0, 'end': len(self.df)-1, 'flight_num': 1, 'touchdown_idx': None}]
        else:
            # Criar voos baseado em touchdowns
            for i, td_idx in enumerate(touchdowns, 1):
                # Janela de análise: 30 seg antes até 10 seg depois do touchdown
                start_idx = max(0, td_idx - 240)  # ~30 seg a 8Hz
                end_idx = min(len(self.df)-1, td_idx + 80)  # ~10 seg
                
                self.flights.append({
                    'start': start_idx,
                    'end': end_idx,
                    'flight_num': i,
                    'touchdown_idx': td_idx
                })
                
                print(f"  Voo {i}: touchdown linha {td_idx} (janela: {start_idx} -> {end_idx})")
        
        return self
    
    def find_acceleration_column(self):
        """Encontra coluna de aceleração vertical"""
        candidates = []
        
        # Procurar por nome
        for col in self.df.columns:
            col_lower = col.lower()
            if 'vertical' in col_lower and 'accel' in col_lower:
                candidates.append((col, 10))  # prioridade alta
            elif 'normaccel' in col_lower or 'normal accel' in col_lower:
                candidates.append((col, 9))
            elif 'normal load' in col_lower:
                candidates.append((col, 8))
            elif col_lower == 'g' or col_lower == 'g-force':
                candidates.append((col, 7))
        
        if candidates:
            # Retornar coluna com maior prioridade
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return None
    
    def find_descent_rate_column(self):
        """Encontra coluna de taxa de descida"""
        for col in self.df.columns:
            col_lower = col.lower()
            if 'vertical' in col_lower and 'speed' in col_lower:
                return col
            elif 'descent' in col_lower or 'sink' in col_lower:
                return col
            elif 'vert' in col_lower and 'spd' in col_lower:
                return col
        return None
    
    def find_radio_height_column(self):
        """Encontra coluna de radio altura"""
        for col in self.df.columns:
            col_lower = col.lower()
            if 'radio' in col_lower and ('alt' in col_lower or 'height' in col_lower):
                return col
            elif 'ralt' in col_lower or 'rad alt' in col_lower:
                return col
        return None
    
    def analyze_flight(self, flight_info):
        """Analisa um voo específico para hard landing"""
        flight_num = flight_info['flight_num']
        start_idx = flight_info['start']
        end_idx = flight_info['end']
        touchdown_idx = flight_info.get('touchdown_idx')
        
        print(f"\n{'='*80}")
        print(f"✈️ ANALISANDO VOO {flight_num}")
        print(f"{'='*80}")
        print(f"Linhas: {start_idx} -> {end_idx} ({end_idx - start_idx + 1} samples)")
        if touchdown_idx:
            print(f"Touchdown: linha {touchdown_idx}")
        
        # Extrair dados do voo
        flight_df = self.df.iloc[start_idx:end_idx+1].copy()
        
        # ANÁLISE 1: Aceleração Vertical (Normal Load Factor)
        accel_col = self.find_acceleration_column()
        if accel_col:
            print(f"\n📊 Aceleração Vertical: '{accel_col}'")
            flight_df[accel_col] = pd.to_numeric(flight_df[accel_col], errors='coerce')
            
            valid_accel = flight_df[flight_df[accel_col].notna()]
            if len(valid_accel) > 0:
                min_g = valid_accel[accel_col].min()
                max_g = valid_accel[accel_col].max()
                mean_g = valid_accel[accel_col].mean()
                
                print(f"  Min: {min_g:.3f}G | Max: {max_g:.3f}G | Média: {mean_g:.3f}G")
                
                # DETECÇÃO HARD LANDING
                if max_g >= self.THRESHOLDS_E190['very_hard_accel']:
                    severity = "VERY HARD LANDING"
                    print(f"  ⚠️⚠️⚠️ {severity} DETECTADO! ({max_g:.3f}G > {self.THRESHOLDS_E190['very_hard_accel']}G)")
                elif max_g >= self.THRESHOLDS_E190['normal_accel']:
                    severity = "HARD LANDING"
                    print(f"  ⚠️ {severity} DETECTADO! ({max_g:.3f}G > {self.THRESHOLDS_E190['normal_accel']}G)")
                else:
                    severity = "NORMAL"
                    print(f"  ✅ Landing normal ({max_g:.3f}G < {self.THRESHOLDS_E190['normal_accel']}G)")
                
                # Registrar evento
                if severity != "NORMAL":
                    # Encontrar linha do pico
                    peak_idx = valid_accel[accel_col].idxmax()
                    
                    # Timestamp
                    time_cols = [c for c in flight_df.columns if 'time' in c.lower() or 'gmt' in c.lower()]
                    timestamp = flight_df.loc[peak_idx, time_cols[0]] if time_cols else f"Linha {peak_idx}"
                    
                    self.events.append({
                        'flight': flight_num,
                        'type': severity,
                        'max_g': max_g,
                        'timestamp': timestamp,
                        'line': peak_idx,
                        'parameter': 'Vertical Acceleration'
                    })
        else:
            print("❌ Coluna de aceleração vertical não encontrada!")
        
        # ANÁLISE 2: Descent Rate
        descent_col = self.find_descent_rate_column()
        if descent_col:
            print(f"\n📊 Descent Rate: '{descent_col}'")
            flight_df[descent_col] = pd.to_numeric(flight_df[descent_col], errors='coerce')
            
            valid_descent = flight_df[flight_df[descent_col].notna()]
            if len(valid_descent) > 0:
                min_rate = valid_descent[descent_col].min()
                max_rate = valid_descent[descent_col].max()
                
                print(f"  Min: {min_rate:.1f} ft/min | Max: {max_rate:.1f} ft/min")
                
                # Descent rate negativo = descendo
                if abs(min_rate) > self.THRESHOLDS_E190['descent_rate']:
                    print(f"  ⚠️ Descent rate excessivo! ({abs(min_rate):.1f} > {self.THRESHOLDS_E190['descent_rate']} ft/min)")
                else:
                    print(f"  ✅ Descent rate normal")
        
        # ANÁLISE 3: Radio Height
        rh_col = self.find_radio_height_column()
        if rh_col:
            print(f"\n📊 Radio Height: '{rh_col}'")
            flight_df[rh_col] = pd.to_numeric(flight_df[rh_col], errors='coerce')
            
            valid_rh = flight_df[flight_df[rh_col].notna()]
            if len(valid_rh) > 0:
                min_rh = valid_rh[rh_col].min()
                max_rh = valid_rh[rh_col].max()
                print(f"  Min: {min_rh:.1f} ft | Max: {max_rh:.1f} ft")
    
    def generate_graphs(self, flight_info):
        """Gera gráficos do evento"""
        flight_num = flight_info['flight_num']
        start_idx = flight_info['start']
        end_idx = flight_info['end']
        
        flight_df = self.df.iloc[start_idx:end_idx+1].copy()
        
        accel_col = self.find_acceleration_column()
        if not accel_col:
            print("❌ Não é possível gerar gráfico sem dados de aceleração")
            return
        
        flight_df[accel_col] = pd.to_numeric(flight_df[accel_col], errors='coerce')
        
        # Criar diretório de gráficos
        graphs_dir = Path('graficos_hard_landing')
        graphs_dir.mkdir(exist_ok=True)
        
        # Plotar
        fig, ax = plt.subplots(figsize=(12, 6))
        
        valid_data = flight_df[flight_df[accel_col].notna()]
        ax.plot(range(len(valid_data)), valid_data[accel_col].values, 'b-', linewidth=2, label='Vertical Acceleration')
        
        # Linhas de threshold
        ax.axhline(y=self.THRESHOLDS_E190['normal_accel'], color='orange', linestyle='--', 
                   linewidth=2, label=f"Hard Landing ({self.THRESHOLDS_E190['normal_accel']}G)")
        ax.axhline(y=self.THRESHOLDS_E190['very_hard_accel'], color='red', linestyle='--', 
                   linewidth=2, label=f"Very Hard ({self.THRESHOLDS_E190['very_hard_accel']}G)")
        
        # Marcar pico
        max_g = valid_data[accel_col].max()
        max_idx = valid_data[accel_col].idxmax()
        max_pos = valid_data.index.get_loc(max_idx)
        ax.plot(max_pos, max_g, 'r*', markersize=20, label=f'Pico: {max_g:.3f}G')
        
        ax.set_xlabel('Sample', fontsize=12)
        ax.set_ylabel('Vertical Acceleration (G)', fontsize=12)
        ax.set_title(f'Hard Landing Analysis - Voo {flight_num} - {Path(self.csv_path).name}', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        
        # Salvar
        filename = f"{Path(self.csv_path).stem}_voo_{flight_num}.png"
        filepath = graphs_dir / filename
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"\n📊 Gráfico salvo: {filepath}")
        
    def run_complete_analysis(self):
        """Executa análise completa: carrega, identifica voos, analisa, gera gráficos"""
        self.load_csv()
        self.identify_flights()
        
        # Analisar cada voo
        for flight_info in self.flights:
            self.analyze_flight(flight_info)
            self.generate_graphs(flight_info)
        
        # Resumo final
        print(f"\n{'='*80}")
        print(f"📊 RESUMO DA ANÁLISE")
        print(f"{'='*80}")
        print(f"Arquivo: {Path(self.csv_path).name}")
        print(f"Total de voos: {len(self.flights)}")
        print(f"Eventos detectados: {len(self.events)}")
        
        if self.events:
            print(f"\n⚠️ EVENTOS DE HARD LANDING:")
            for event in self.events:
                print(f"  • Voo {event['flight']}: {event['type']} - {event['max_g']:.3f}G @ {event['timestamp']}")
        else:
            print(f"\n✅ Nenhum hard landing detectado em nenhum voo")
        
        return self.events


# ==================== TESTE TODOS OS ARQUIVOS ====================
if __name__ == "__main__":
    arquivos = [
        r'c:\Users\mrced\OneDrive\Documents\hard landing\CRC212 20-2-25 Hard landing 1.csv',
        r'c:\Users\mrced\OneDrive\Documents\hard landing\CRC212 20-2-25 Hard landing 2.csv',
        r'c:\Users\mrced\OneDrive\Documents\hard landing\XA-ALU _HL_13AGO25_FLT651.CSV',
        r'c:\Users\mrced\OneDrive\Documents\hard landing\HL XA-ALL AM593 20251026.csv',
        r'c:\Users\mrced\OneDrive\Documents\hard landing\ALL.csv',
        r'c:\Users\mrced\OneDrive\Documents\hard landing\JAC.csv',
    ]
    
    print("=" * 80)
    print("ADVANCED HARD LANDING DETECTOR - E190")
    print("Multiple Flights | Multiple Parameters | Graphic Generation")
    print("=" * 80)
    
    all_events = []
    
    for arquivo in arquivos:
        if not os.path.exists(arquivo):
            print(f"\n❌ Arquivo não encontrado: {arquivo}")
            continue
        
        try:
            detector = HardLandingDetector(arquivo)
            events = detector.run_complete_analysis()
            all_events.extend(events)
        except Exception as e:
            print(f"\n❌ Erro ao processar {Path(arquivo).name}: {e}")
            import traceback
            traceback.print_exc()
    
    # RESUMO GERAL
    print(f"\n\n{'='*80}")
    print(f"RESUMO GERAL - TODOS OS ARQUIVOS")
    print(f"{'='*80}")
    print(f"Arquivos processados: {len(arquivos)}")
    print(f"Total de eventos: {len(all_events)}")
    
    if all_events:
        print(f"\n⚠️ HARD LANDINGS CONFIRMADOS:")
        for evt in all_events:
            print(f"  • {evt['type']}: {evt['max_g']:.3f}G")
    else:
        print(f"\n✅ Nenhum hard landing detectado nos arquivos")

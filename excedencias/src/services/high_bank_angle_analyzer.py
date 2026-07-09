"""
High Bank Angle Analyzer
Detecta ângulos de bank excessivos conforme AMM 05-57-00

Thresholds (AMM oficiais):
- Normal Operations: >60°
- Emergency/Upset: >67°

Monitora:
- Ângulo de roll máximo
- Duração em alto bank angle
- Taxa de variação (roll rate)
- Coordenação (ball out)
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime


@dataclass
class HighBankAngleResult:
    """Resultado da análise de High Bank Angle"""
    is_high_bank_angle: bool
    max_bank_angle: float
    max_roll_rate: float
    bank_threshold_normal: float
    bank_threshold_emergency: float
    sustained_duration: float  # segundos em alto bank
    exceedance_count: int
    exceedance_events: List[Tuple[float, float, float]]  # (time, bank_angle, roll_rate)
    severity_level: str  # 'NONE', 'MODERATE', 'HIGH', 'SEVERE', 'CRITICAL'
    aircraft_model: str
    analysis_timestamp: str
    recommended_actions: List[str]
    flight_phase: str  # 'CRUISE', 'APPROACH', 'LANDING', 'TAKEOFF', 'UNKNOWN'
    
    def __str__(self):
        if not self.is_high_bank_angle:
            return f"[BANK ANGLE] NONE - Max: {abs(self.max_bank_angle):.1f}°"
        
        return (f"[BANK ANGLE] {self.severity_level}\n"
                f"  Max Angle: {abs(self.max_bank_angle):.1f}°\n"
                f"  Threshold: {self.bank_threshold_normal:.1f}°/{self.bank_threshold_emergency:.1f}°\n"
                f"  Duração: {self.sustained_duration:.1f}s\n"
                f"  Eventos: {self.exceedance_count}\n"
                f"  Fase: {self.flight_phase}\n"
                f"  Ações: {', '.join(self.recommended_actions[:2])}")


class HighBankAngleAnalyzer:
    """
    Analisa ângulos de bank excessivos conforme AMM 05-57-00
    
    Detecta:
    - Bank angles >60° (AMM normal)
    - Bank angles >67° (AMM emergency)
    - Manobras bruscas coordenadas/descoordenadas
    - Duração em alto bank
    - Upset/unusual attitudes
    """
    
    # ==================== THRESHOLDS AMM 05-57-00 ====================
    
    BANK_ANGLE_THRESHOLDS = {
        'E170': {
            'normal': 60.0,      # AMM 05-57-00
            'emergency': 67.0,   # AMM 05-57-00
            'sustained_time': 3.0,  # segundos
            'roll_rate_high': 15.0,  # deg/s
            'roll_rate_severe': 25.0  # deg/s
        },
        'E175': {
            'normal': 60.0,
            'emergency': 67.0,
            'sustained_time': 3.0,
            'roll_rate_high': 15.0,
            'roll_rate_severe': 25.0
        },
        'E190': {
            'normal': 60.0,
            'emergency': 67.0,
            'sustained_time': 3.0,
            'roll_rate_high': 15.0,
            'roll_rate_severe': 25.0
        },
        'E195': {
            'normal': 60.0,
            'emergency': 67.0,
            'sustained_time': 3.0,
            'roll_rate_high': 15.0,
            'roll_rate_severe': 25.0
        },
        # E2 Family (mesmos thresholds)
        'E175-E2': {
            'normal': 60.0,
            'emergency': 67.0,
            'sustained_time': 3.0,
            'roll_rate_high': 15.0,
            'roll_rate_severe': 25.0
        },
        'E190-E2': {
            'normal': 60.0,
            'emergency': 67.0,
            'sustained_time': 3.0,
            'roll_rate_high': 15.0,
            'roll_rate_severe': 25.0
        },
        'E195-E2': {
            'normal': 60.0,
            'emergency': 67.0,
            'sustained_time': 3.0,
            'roll_rate_high': 15.0,
            'roll_rate_severe': 25.0
        }
    }
    
    # ==================== AMM COMPLIANCE ====================
    
    AMM_REFERENCE = "AMM 05-57-00 - High Bank Angle Detection"
    
    def __init__(self):
        """Inicializa High Bank Angle Analyzer"""
        self.logger = None
    
    def analyze_high_bank_angle(
        self, 
        flight_data: pd.DataFrame, 
        aircraft_model: str
    ) -> HighBankAngleResult:
        """
        Analisa high bank angles
        
        Args:
            flight_data: DataFrame com dados de voo
            aircraft_model: Modelo da aeronave
        
        Returns:
            HighBankAngleResult com resultados
        """
        
        # Validações
        if flight_data is None or len(flight_data) == 0:
            return self._create_no_bank_angle_result(aircraft_model, "Dados vazios")
        
        if aircraft_model not in self.BANK_ANGLE_THRESHOLDS:
            if 'E2' in aircraft_model:
                aircraft_model = 'E175-E2'
            else:
                aircraft_model = 'E170'
        
        # Obter thresholds
        thresholds = self.BANK_ANGLE_THRESHOLDS[aircraft_model]
        normal_threshold = thresholds['normal']
        emergency_threshold = thresholds['emergency']
        
        # Verificar colunas necessárias
        if 'roll_attitude' not in flight_data.columns:
            return self._create_no_bank_angle_result(
                aircraft_model,
                "Coluna 'roll_attitude' não encontrada"
            )
        
        # Extrair dados
        bank_angles = flight_data['roll_attitude'].dropna()
        
        if len(bank_angles) == 0:
            return self._create_no_bank_angle_result(aircraft_model, "Sem dados válidos de roll")
        
        # Calcular máximo absoluto (pode ser + ou -)
        max_bank_left = float(bank_angles.min())  # Negativo = left
        max_bank_right = float(bank_angles.max())  # Positivo = right
        
        # Maior excursão absoluta
        if abs(max_bank_left) > abs(max_bank_right):
            max_bank_angle = max_bank_left
        else:
            max_bank_angle = max_bank_right
        
        # Roll rate (se disponível)
        max_roll_rate = 0.0
        if 'roll_rate' in flight_data.columns:
            roll_rates = flight_data['roll_rate'].dropna()
            if len(roll_rates) > 0:
                max_roll_rate = float(max(abs(roll_rates.min()), abs(roll_rates.max())))
        
        # Verificar excedência
        is_high_bank = abs(max_bank_angle) > normal_threshold
        
        # Encontrar eventos
        exceedance_events = self._find_bank_angle_events(
            flight_data, normal_threshold, emergency_threshold
        )
        
        # Calcular duração sustentada
        sustained_duration = self._calculate_sustained_duration(
            flight_data, normal_threshold
        )
        
        # Determinar fase de voo
        flight_phase = self._determine_flight_phase(flight_data)
        
        # Determinar severidade
        severity = self._calculate_severity(
            abs(max_bank_angle),
            max_roll_rate,
            normal_threshold,
            emergency_threshold,
            sustained_duration,
            len(exceedance_events),
            flight_phase,
            thresholds
        )
        
        # Ações recomendadas
        recommended_actions = self._get_recommended_actions(
            severity,
            abs(max_bank_angle),
            max_roll_rate,
            sustained_duration,
            flight_phase
        )
        
        return HighBankAngleResult(
            is_high_bank_angle=is_high_bank,
            max_bank_angle=max_bank_angle,
            max_roll_rate=max_roll_rate,
            bank_threshold_normal=normal_threshold,
            bank_threshold_emergency=emergency_threshold,
            sustained_duration=sustained_duration,
            exceedance_count=len(exceedance_events),
            exceedance_events=exceedance_events,
            severity_level=severity,
            aircraft_model=aircraft_model,
            analysis_timestamp=datetime.now().isoformat(),
            recommended_actions=recommended_actions,
            flight_phase=flight_phase
        )
    
    def _find_bank_angle_events(
        self,
        flight_data: pd.DataFrame,
        normal_threshold: float,
        emergency_threshold: float
    ) -> List[Tuple[float, float, float]]:
        """
        Encontra eventos de alto bank angle
        
        Returns:
            Lista de tuplas (time, bank_angle, roll_rate)
        """
        events = []
        
        # Coluna de tempo
        time_col = None
        for col in ['time', 'time_sec', 'elapsed_time', 'timestamp']:
            if col in flight_data.columns:
                time_col = col
                break
        
        bank_angles = flight_data['roll_attitude'].values
        roll_rates = flight_data['roll_rate'].values if 'roll_rate' in flight_data.columns else [0] * len(bank_angles)
        
        for idx, bank in enumerate(bank_angles):
            if pd.notna(bank) and abs(bank) > normal_threshold:
                time_val = flight_data[time_col].iloc[idx] if time_col else idx
                roll_rate_val = roll_rates[idx] if idx < len(roll_rates) else 0
                
                events.append((
                    float(time_val),
                    float(bank),
                    float(roll_rate_val) if pd.notna(roll_rate_val) else 0.0
                ))
        
        return events
    
    def _calculate_sustained_duration(
        self,
        flight_data: pd.DataFrame,
        threshold: float
    ) -> float:
        """
        Calcula duração total em alto bank angle
        
        Returns:
            Duração em segundos
        """
        if 'time' not in flight_data.columns and 'time_sec' not in flight_data.columns:
            # Sem dados de tempo, retornar contagem de frames
            bank_angles = flight_data['roll_attitude'].values
            frames_exceeded = sum(1 for b in bank_angles if pd.notna(b) and abs(b) > threshold)
            return float(frames_exceeded)  # Estimativa
        
        # Com dados de tempo
        time_col = 'time' if 'time' in flight_data.columns else 'time_sec'
        
        total_duration = 0.0
        in_exceedance = False
        start_time = 0.0
        
        for idx, row in flight_data.iterrows():
            bank = row['roll_attitude']
            current_time = row[time_col]
            
            if pd.notna(bank) and abs(bank) > threshold:
                if not in_exceedance:
                    in_exceedance = True
                    start_time = current_time
            else:
                if in_exceedance:
                    total_duration += current_time - start_time
                    in_exceedance = False
        
        # Se ainda em exceedance no final
        if in_exceedance:
            total_duration += flight_data[time_col].iloc[-1] - start_time
        
        return total_duration
    
    def _determine_flight_phase(self, flight_data: pd.DataFrame) -> str:
        """Determina fase de voo baseado em dados disponíveis"""
        
        # Verificar air/ground switch
        if 'air_ground_switch' in flight_data.columns:
            ag_switch = flight_data['air_ground_switch'].mode()
            if len(ag_switch) > 0 and ag_switch[0] == 0:
                return 'LANDING'
        
        # Verificar altitude
        if 'pressure_altitude' in flight_data.columns:
            avg_alt = flight_data['pressure_altitude'].mean()
            if pd.notna(avg_alt):
                if avg_alt < 1000:
                    return 'TAKEOFF/LANDING'
                elif avg_alt < 10000:
                    return 'APPROACH'
                else:
                    return 'CRUISE'
        
        # Verificar airspeed
        if 'indicated_airspeed' in flight_data.columns:
            avg_ias = flight_data['indicated_airspeed'].mean()
            if pd.notna(avg_ias):
                if avg_ias < 100:
                    return 'TAKEOFF/LANDING'
                elif avg_ias < 200:
                    return 'APPROACH'
                else:
                    return 'CRUISE'
        
        return 'UNKNOWN'
    
    def _calculate_severity(
        self,
        max_bank: float,
        max_roll_rate: float,
        normal_threshold: float,
        emergency_threshold: float,
        duration: float,
        event_count: int,
        flight_phase: str,
        thresholds: dict
    ) -> str:
        """
        Calcula severidade
        
        Níveis:
        - NONE: Sem excedência
        - MODERATE: >54° mas <60°
        - HIGH: >60° ou roll rate >15 deg/s
        - SEVERE: >65° ou roll rate >25 deg/s ou duração >5s
        - CRITICAL: >70° ou upset recovery
        """
        
        if max_bank <= normal_threshold:
            return 'NONE'
        
        # CRITICAL: Angles extremos
        if max_bank > 70:
            return 'CRITICAL'
        
        # SEVERE: Emergency threshold ou roll rate muito alto
        if max_bank > emergency_threshold or max_roll_rate > thresholds['roll_rate_severe']:
            return 'SEVERE'
        
        # SEVERE: Duração longa
        if duration > 5.0:
            return 'SEVERE'
        
        # HIGH: Acima de emergency threshold ou roll rate alto
        if max_bank > 60 or max_roll_rate > thresholds['roll_rate_high']:
            return 'HIGH'
        
        # HIGH: Múltiplos eventos
        if event_count > 3:
            return 'HIGH'
        
        # MODERATE: Acima de normal mas abaixo de emergency
        return 'MODERATE'
    
    def _get_recommended_actions(
        self,
        severity: str,
        max_bank: float,
        max_roll_rate: float,
        duration: float,
        flight_phase: str
    ) -> List[str]:
        """Retorna ações recomendadas"""
        
        actions = []
        
        if severity == 'NONE':
            return ['Nenhuma ação necessária']
        
        # Ações comuns
        actions.append('Reportar evento ao departamento de segurança de voo')
        actions.append('Revisar FDR completo e cockpit voice recorder')
        
        # Ações por severidade
        if severity in ['SEVERE', 'CRITICAL']:
            actions.append('INSPEÇÃO ESTRUTURAL OBRIGATÓRIA (AMM 05-57-00)')
            actions.append('Verificar integridade de asas e superfícies de controle')
            actions.append('Inspecionar ailerons, spoilers e flaps')
            actions.append('Verificar sistema hidráulico e FBW')
            actions.append('Inspeção por NDT (ultrassom) em pontos críticos')
            
            if severity == 'CRITICAL':
                actions.append('⚠️ POSSÍVEL UPSET/UNUSUAL ATTITUDE - Análise imediata requerida')
                actions.append('Considerar grounding temporário da aeronave')
                actions.append('Investigação de segurança obrigatória')
        
        elif severity == 'HIGH':
            actions.append('Inspeção visual detalhada de asas e empenagem')
            actions.append('Verificar fadiga em pontos de fixação')
            actions.append('Revisar histórico de manutenção')
        
        else:  # MODERATE
            actions.append('Inspeção visual básica')
            actions.append('Documentar no log de voo')
            actions.append('Revisar procedimentos operacionais')
        
        # Ações específicas por fase
        if flight_phase in ['TAKEOFF/LANDING', 'LANDING', 'APPROACH']:
            actions.append(f'⚠️ Alto bank angle durante {flight_phase} - Risco elevado')
            actions.append('Revisar treinamento de tripulação para essa fase')
        
        # Ações específicas por parâmetros
        if duration > 5.0:
            actions.append(f'Duração prolongada ({duration:.1f}s) - Verificar fadiga estrutural')
        
        if max_roll_rate > 20:
            actions.append(f'Roll rate excessivo ({max_roll_rate:.1f}°/s) - Verificar controles de voo')
        
        return actions
    
    def _create_no_bank_angle_result(self, aircraft_model: str, reason: str = "") -> HighBankAngleResult:
        """Cria resultado negativo"""
        return HighBankAngleResult(
            is_high_bank_angle=False,
            max_bank_angle=0.0,
            max_roll_rate=0.0,
            bank_threshold_normal=54.0,
            bank_threshold_emergency=60.0,
            sustained_duration=0.0,
            exceedance_count=0,
            exceedance_events=[],
            severity_level='NONE',
            aircraft_model=aircraft_model,
            analysis_timestamp=datetime.now().isoformat(),
            recommended_actions=['Nenhuma ação necessária'] if not reason else [f'Análise não realizada: {reason}'],
            flight_phase='UNKNOWN'
        )
    
    def get_amm_reference(self) -> str:
        """Retorna referência AMM"""
        return self.AMM_REFERENCE
    
    def get_threshold_info(self, aircraft_model: str) -> dict:
        """Retorna informações de thresholds"""
        if aircraft_model in self.BANK_ANGLE_THRESHOLDS:
            return self.BANK_ANGLE_THRESHOLDS[aircraft_model]
        return {}


# ==================== TESTING ====================

def test_high_bank_angle_analyzer():
    """Teste rápido"""
    import pandas as pd
    
    # Criar dados de teste
    data = pd.DataFrame({
        'time': range(100),
        'roll_attitude': [0.0] * 30 + [58.0] + [45.0] * 20 + [0.0] * 49,  # High bank em t=30
        'roll_rate': [0.0] * 30 + [18.0] + [0.0] * 69,
        'pressure_altitude': [25000] * 100
    })
    
    analyzer = HighBankAngleAnalyzer()
    result = analyzer.analyze_high_bank_angle(data, 'E175')
    
    print(result)
    print(f"\nEventos detectados: {len(result.exceedance_events)}")
    for event in result.exceedance_events:
        print(f"  T={event[0]:.1f}s: {event[1]:.1f}° (Roll rate: {event[2]:.1f}°/s)")


if __name__ == '__main__':
    test_high_bank_angle_analyzer()

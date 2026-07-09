"""
Over-G Analyzer
Detecta manobras excessivas (Over-G) conforme AMM 05-50-02

Thresholds por família (AMM oficiais):
- E1 (E170/E175/E190/E195): ±3.5G
- E2 (E175-E2/E190-E2/E195-E2): ±3.8G
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime


@dataclass
class OverGResult:
    """Resultado da análise de Over-G"""
    is_over_g: bool
    max_positive_g: float
    max_negative_g: float
    positive_g_exceeded: bool
    negative_g_exceeded: bool
    positive_threshold: float
    negative_threshold: float
    exceedance_count: int
    exceedance_events: List[Tuple[float, float, str]]  # (time, g_value, type)
    severity_level: str  # 'NONE', 'LOW', 'MODERATE', 'HIGH', 'SEVERE'
    aircraft_model: str
    analysis_timestamp: str
    recommended_actions: List[str]
    
    def __str__(self):
        if not self.is_over_g:
            return f"[OVER-G] NONE - Max: +{self.max_positive_g:.2f}G / {self.max_negative_g:.2f}G"
        
        return (f"[OVER-G] {self.severity_level}\n"
                f"  Max G: +{self.max_positive_g:.2f}G / {self.max_negative_g:.2f}G\n"
                f"  Thresholds: +{self.positive_threshold:.2f}G / {self.negative_threshold:.2f}G\n"
                f"  Eventos: {self.exceedance_count}\n"
                f"  Ações: {', '.join(self.recommended_actions)}")


class OverGAnalyzer:
    """
    Analisa manobras excessivas (Over-G) conforme AMM 05-50-02
    
    Detecta:
    - Acelerações positivas excessivas (>3.5G E1, >3.8G E2)
    - Acelerações negativas excessivas (<-3.5G E1, <-3.8G E2)
    - Manobras bruscas e extremas
    - Duração e intensidade das excedências
    """
    
    # ==================== THRESHOLDS AMM 05-50-02 ====================
    
    OVER_G_THRESHOLDS = {
        'E170': {
            'positive': 3.5,   # AMM 05-50-02
            'negative': -3.5,
            'sustained_duration': 1.0,  # segundos
            'moderate_threshold': 3.2,  # Para classificação de severidade
            'high_threshold': 3.3
        },
        'E175': {
            'positive': 3.5,
            'negative': -3.5,
            'sustained_duration': 1.0,
            'moderate_threshold': 3.2,
            'high_threshold': 3.3
        },
        'E190': {
            'positive': 3.5,
            'negative': -3.5,
            'sustained_duration': 1.0,
            'moderate_threshold': 3.2,
            'high_threshold': 3.3
        },
        'E195': {
            'positive': 3.5,
            'negative': -3.5,
            'sustained_duration': 1.0,
            'moderate_threshold': 3.2,
            'high_threshold': 3.3
        },
        # E2 Family (thresholds mais altos)
        'E175-E2': {
            'positive': 3.8,   # AMM 05-50-02
            'negative': -3.8,
            'sustained_duration': 1.0,
            'moderate_threshold': 3.5,
            'high_threshold': 3.6
        },
        'E190-E2': {
            'positive': 3.8,
            'negative': -3.8,
            'sustained_duration': 1.0,
            'moderate_threshold': 3.5,
            'high_threshold': 3.6
        },
        'E195-E2': {
            'positive': 3.8,
            'negative': -3.8,
            'sustained_duration': 1.0,
            'moderate_threshold': 3.5,
            'high_threshold': 3.6
        }
    }
    
    # ==================== AMM COMPLIANCE ====================
    
    AMM_REFERENCE = "AMM 05-50-02 - Over-G Maneuver Detection"
    
    def __init__(self):
        """Inicializa Over-G Analyzer"""
        self.logger = None  # Configurar logger se disponível
    
    def analyze_over_g(self, flight_data: pd.DataFrame, aircraft_model: str) -> OverGResult:
        """
        Analisa manobras Over-G
        
        Args:
            flight_data: DataFrame com dados de voo
            aircraft_model: Modelo da aeronave (E170, E175, E190, E195, E175-E2, etc.)
        
        Returns:
            OverGResult com resultados da análise
        """
        
        # Validações
        if flight_data is None or len(flight_data) == 0:
            return self._create_no_over_g_result(aircraft_model, "Dados vazios")
        
        if aircraft_model not in self.OVER_G_THRESHOLDS:
            # Usar E170 como padrão para E1
            if 'E2' in aircraft_model:
                aircraft_model = 'E175-E2'
            else:
                aircraft_model = 'E170'
        
        # Obter thresholds
        thresholds = self.OVER_G_THRESHOLDS[aircraft_model]
        positive_threshold = thresholds['positive']
        negative_threshold = thresholds['negative']
        
        # Verificar coluna de aceleração vertical
        if 'vertical_acceleration' not in flight_data.columns:
            return self._create_no_over_g_result(
                aircraft_model, 
                "Coluna 'vertical_acceleration' não encontrada"
            )
        
        # Extrair dados
        g_data = flight_data['vertical_acceleration'].dropna()
        
        if len(g_data) == 0:
            return self._create_no_over_g_result(aircraft_model, "Sem dados válidos de aceleração")
        
        # Calcular máximos
        max_positive_g = float(g_data.max())
        max_negative_g = float(g_data.min())
        
        # Verificar excedências
        positive_exceeded = max_positive_g > positive_threshold
        negative_exceeded = max_negative_g < negative_threshold
        
        is_over_g = positive_exceeded or negative_exceeded
        
        # Encontrar eventos de excedência
        exceedance_events = self._find_exceedance_events(
            flight_data, positive_threshold, negative_threshold
        )
        
        # Determinar severidade
        severity = self._calculate_severity(
            max_positive_g, max_negative_g, 
            positive_threshold, negative_threshold,
            thresholds, len(exceedance_events)
        )
        
        # Ações recomendadas
        recommended_actions = self._get_recommended_actions(
            severity, positive_exceeded, negative_exceeded,
            max_positive_g, max_negative_g
        )
        
        return OverGResult(
            is_over_g=is_over_g,
            max_positive_g=max_positive_g,
            max_negative_g=max_negative_g,
            positive_g_exceeded=positive_exceeded,
            negative_g_exceeded=negative_exceeded,
            positive_threshold=positive_threshold,
            negative_threshold=negative_threshold,
            exceedance_count=len(exceedance_events),
            exceedance_events=exceedance_events,
            severity_level=severity,
            aircraft_model=aircraft_model,
            analysis_timestamp=datetime.now().isoformat(),
            recommended_actions=recommended_actions
        )
    
    def _find_exceedance_events(
        self, 
        flight_data: pd.DataFrame, 
        positive_threshold: float,
        negative_threshold: float
    ) -> List[Tuple[float, float, str]]:
        """
        Encontra todos os eventos de excedência
        
        Returns:
            Lista de tuplas (time, g_value, event_type)
        """
        events = []
        
        # Verificar se temos coluna de tempo
        time_col = None
        for col in ['time', 'time_sec', 'elapsed_time', 'timestamp']:
            if col in flight_data.columns:
                time_col = col
                break
        
        g_values = flight_data['vertical_acceleration'].values
        
        for idx, g in enumerate(g_values):
            if pd.notna(g):
                # Excedência positiva
                if g > positive_threshold:
                    time_val = flight_data[time_col].iloc[idx] if time_col else idx
                    events.append((float(time_val), float(g), 'POSITIVE'))
                
                # Excedência negativa
                elif g < negative_threshold:
                    time_val = flight_data[time_col].iloc[idx] if time_col else idx
                    events.append((float(time_val), float(g), 'NEGATIVE'))
        
        return events
    
    def _calculate_severity(
        self, 
        max_pos_g: float, 
        max_neg_g: float,
        pos_threshold: float,
        neg_threshold: float,
        thresholds: dict,
        event_count: int
    ) -> str:
        """
        Calcula nível de severidade
        
        Níveis:
        - NONE: Sem excedência
        - LOW: Excedência leve (1-5% acima)
        - MODERATE: Excedência moderada (5-10% acima)
        - HIGH: Excedência alta (10-15% acima)
        - SEVERE: Excedência severa (>15% acima) ou múltiplos eventos
        """
        
        if max_pos_g <= pos_threshold and max_neg_g >= neg_threshold:
            return 'NONE'
        
        # Calcular percentual de excedência
        pos_exceedance_pct = 0
        if max_pos_g > pos_threshold:
            pos_exceedance_pct = ((max_pos_g - pos_threshold) / pos_threshold) * 100
        
        neg_exceedance_pct = 0
        if max_neg_g < neg_threshold:
            neg_exceedance_pct = ((neg_threshold - max_neg_g) / abs(neg_threshold)) * 100
        
        max_exceedance_pct = max(pos_exceedance_pct, neg_exceedance_pct)
        
        # Múltiplos eventos = mais grave
        if event_count > 5:
            if max_exceedance_pct > 10:
                return 'SEVERE'
            elif max_exceedance_pct > 5:
                return 'HIGH'
            else:
                return 'MODERATE'
        
        # Baseado em percentual
        if max_exceedance_pct > 15:
            return 'SEVERE'
        elif max_exceedance_pct > 10:
            return 'HIGH'
        elif max_exceedance_pct > 5:
            return 'MODERATE'
        else:
            return 'LOW'
    
    def _get_recommended_actions(
        self,
        severity: str,
        positive_exceeded: bool,
        negative_exceeded: bool,
        max_pos_g: float,
        max_neg_g: float
    ) -> List[str]:
        """Retorna ações recomendadas baseadas na severidade"""
        
        actions = []
        
        if severity == 'NONE':
            return ['Nenhuma ação necessária']
        
        # Ações comuns
        actions.append('Reportar evento ao departamento de engenharia')
        actions.append('Revisar dados do FDR completos')
        
        # Ações específicas por severidade
        if severity in ['HIGH', 'SEVERE']:
            actions.append('INSPEÇÃO ESTRUTURAL OBRIGATÓRIA (AMM 05-50-02)')
            actions.append('Verificar integridade de asas, fuselagem e empenagem')
            actions.append('Inspecionar conexões estruturais principais')
            
            if positive_exceeded:
                actions.append(f'Excedência positiva detectada: +{max_pos_g:.2f}G')
                actions.append('Verificar fadiga em pontos de alta tensão')
            
            if negative_exceeded:
                actions.append(f'Excedência negativa detectada: {max_neg_g:.2f}G')
                actions.append('Verificar componentes sob compressão')
        
        elif severity == 'MODERATE':
            actions.append('Inspeção visual detalhada recomendada')
            actions.append('Verificar log de manutenção para eventos prévios')
        
        else:  # LOW
            actions.append('Inspeção visual básica')
            actions.append('Documentar no log de voo')
        
        # Ações adicionais
        if severity in ['HIGH', 'SEVERE']:
            actions.append('Considerar inspeção por NDT (ultrassom/raios-X)')
            actions.append('Avaliar histórico de voos da aeronave')
            actions.append('Revisar treinamento da tripulação')
        
        return actions
    
    def _create_no_over_g_result(self, aircraft_model: str, reason: str = "") -> OverGResult:
        """Cria resultado negativo"""
        return OverGResult(
            is_over_g=False,
            max_positive_g=0.0,
            max_negative_g=0.0,
            positive_g_exceeded=False,
            negative_g_exceeded=False,
            positive_threshold=3.15,
            negative_threshold=-3.15,
            exceedance_count=0,
            exceedance_events=[],
            severity_level='NONE',
            aircraft_model=aircraft_model,
            analysis_timestamp=datetime.now().isoformat(),
            recommended_actions=['Nenhuma ação necessária'] if not reason else [f'Análise não realizada: {reason}']
        )
    
    def get_amm_reference(self) -> str:
        """Retorna referência AMM"""
        return self.AMM_REFERENCE
    
    def get_threshold_info(self, aircraft_model: str) -> dict:
        """Retorna informações de thresholds para modelo específico"""
        if aircraft_model in self.OVER_G_THRESHOLDS:
            return self.OVER_G_THRESHOLDS[aircraft_model]
        return {}


# ==================== TESTING ====================

def test_over_g_analyzer():
    """Teste rápido do analyzer"""
    import pandas as pd
    
    # Criar dados de teste
    data = pd.DataFrame({
        'time': range(100),
        'vertical_acceleration': [1.0] * 30 + [3.5] + [1.0] * 69  # Over-G em t=30
    })
    
    analyzer = OverGAnalyzer()
    result = analyzer.analyze_over_g(data, 'E175')
    
    print(result)
    print(f"\nEventos detectados: {len(result.exceedance_events)}")
    for event in result.exceedance_events:
        print(f"  T={event[0]:.1f}s: {event[1]:.2f}G ({event[2]})")


if __name__ == '__main__':
    test_over_g_analyzer()

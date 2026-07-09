"""
Advanced Analytics Module - Análise Estatística Avançada
Fornece análise profunda, tendências e previsões inteligentes
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np
from collections import Counter
import json


@dataclass
class TrendAnalysis:
    """Análise de tendências"""
    trend_direction: str  # "INCREASING", "DECREASING", "STABLE"
    change_rate: float  # Taxa de mudança percentual
    confidence: float  # 0-100
    prediction: str
    warning_level: str  # "NONE", "CAUTION", "WARNING", "CRITICAL"
    slope: float
    r_squared: float


@dataclass
class StatisticalSummary:
    """Resumo estatístico completo"""
    mean: float
    median: float
    std_dev: float
    min_value: float
    max_value: float
    percentile_25: float
    percentile_50: float
    percentile_75: float
    percentile_95: float
    percentile_99: float
    outliers_count: int
    coefficient_variation: float


@dataclass
class RiskAssessment:
    """Avaliação de risco"""
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    risk_score: float  # 0-100
    contributing_factors: List[Dict[str, any]]
    mitigation_actions: List[str]
    monitoring_requirements: List[str]


class AdvancedAnalytics:
    """
    Módulo de Análise Avançada
    
    Capacidades:
    - Análise estatística descritiva e inferencial
    - Detecção de tendências com regressão
    - Identificação de padrões e anomalias
    - Avaliação de risco multi-fatorial
    - Previsões baseadas em dados históricos
    - Análise de causa raiz
    """
    
    def __init__(self):
        """Inicializa Advanced Analytics"""
        self.analysis_cache = {}
        self.threshold_configs = {
            'E190': {
                'LOW': 2.0,
                'MEDIUM': 2.18,
                'HIGH': 2.48,
                'CRITICAL': 2.8
            },
            'E195': {
                'LOW': 2.0,
                'MEDIUM': 2.18,
                'HIGH': 2.48,
                'CRITICAL': 2.8
            }
        }
    
    def analyze_trends(
        self, 
        historical_data: List[Dict],
        metric_key: str = 'max_g'
    ) -> TrendAnalysis:
        """
        Analisa tendências ao longo do tempo com regressão linear
        
        Args:
            historical_data: Lista de eventos históricos ordenados por tempo
            metric_key: Chave da métrica a analisar
            
        Returns:
            TrendAnalysis com resultados detalhados
        """
        if len(historical_data) < 3:
            return TrendAnalysis(
                trend_direction="INSUFFICIENT_DATA",
                change_rate=0.0,
                confidence=0.0,
                prediction="Dados insuficientes para análise (mínimo 3 pontos)",
                warning_level="NONE",
                slope=0.0,
                r_squared=0.0
            )
        
        # Extrair valores da métrica
        values = []
        for d in historical_data:
            if metric_key in d and d[metric_key] is not None:
                try:
                    values.append(float(d[metric_key]))
                except (ValueError, TypeError):
                    continue
        
        if len(values) < 3:
            return TrendAnalysis(
                trend_direction="INSUFFICIENT_DATA",
                change_rate=0.0,
                confidence=0.0,
                prediction="Dados válidos insuficientes",
                warning_level="NONE",
                slope=0.0,
                r_squared=0.0
            )
        
        # Regressão linear: y = mx + b
        x = np.arange(len(values))
        coefficients = np.polyfit(x, values, 1)
        slope = coefficients[0]
        intercept = coefficients[1]
        
        # Calcular R² (coeficiente de determinação)
        y_pred = slope * x + intercept
        ss_res = np.sum((values - y_pred) ** 2)
        ss_tot = np.sum((values - np.mean(values)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        confidence = max(0, min(100, r_squared * 100))
        
        # Determinar direção da tendência
        threshold = 0.01  # Threshold para considerar estável
        if abs(slope) < threshold:
            direction = "STABLE"
            warning = "NONE"
        elif slope > 0:
            direction = "INCREASING"
            if slope > 0.1:
                warning = "CRITICAL"
            elif slope > 0.05:
                warning = "WARNING"
            else:
                warning = "CAUTION"
        else:
            direction = "DECREASING"
            warning = "NONE"  # Tendência decrescente é positiva
        
        # Calcular taxa de mudança
        first_value = values[0]
        last_value = values[-1]
        change_rate = ((last_value - first_value) / first_value * 100) if first_value != 0 else 0
        
        # Gerar previsão inteligente
        prediction = self._generate_trend_prediction(
            direction, slope, change_rate, confidence, len(values)
        )
        
        return TrendAnalysis(
            trend_direction=direction,
            change_rate=change_rate,
            confidence=confidence,
            prediction=prediction,
            warning_level=warning,
            slope=slope,
            r_squared=r_squared
        )
    
    def _generate_trend_prediction(
        self,
        direction: str,
        slope: float,
        change_rate: float,
        confidence: float,
        data_points: int
    ) -> str:
        """Gera previsão textual inteligente"""
        
        if direction == "INSUFFICIENT_DATA":
            return "Coletar mais dados para análise de tendência"
        
        confidence_text = "alta" if confidence > 75 else "média" if confidence > 50 else "baixa"
        
        if direction == "INCREASING":
            severity = "crítica" if abs(slope) > 0.1 else "significativa" if abs(slope) > 0.05 else "moderada"
            return (f"Tendência crescente {severity} de {abs(change_rate):.1f}% "
                   f"(confiança {confidence_text}: {confidence:.0f}%). "
                   f"AÇÃO NECESSÁRIA: Investigar causas e implementar medidas corretivas imediatamente.")
        
        elif direction == "DECREASING":
            return (f"Tendência decrescente positiva de {abs(change_rate):.1f}% "
                   f"(confiança {confidence_text}: {confidence:.0f}%). "
                   f"Melhoria observada. Manter práticas atuais e continuar monitoramento.")
        
        else:  # STABLE
            return (f"Valores estáveis ({confidence_text} confiança: {confidence:.0f}%). "
                   f"Continuar monitoramento preventivo e manter padrões operacionais.")
    
    def calculate_comprehensive_statistics(
        self, 
        values: List[float]
    ) -> StatisticalSummary:
        """
        Calcula estatísticas descritivas completas
        
        Args:
            values: Lista de valores numéricos
            
        Returns:
            StatisticalSummary com todas as métricas
        """
        if not values:
            return StatisticalSummary(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        arr = np.array([v for v in values if v is not None])
        
        if len(arr) == 0:
            return StatisticalSummary(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        mean = np.mean(arr)
        std = np.std(arr, ddof=1) if len(arr) > 1 else 0
        
        # Coeficiente de variação
        cv = (std / mean * 100) if mean != 0 else 0
        
        # Detectar outliers usando método IQR
        q1 = np.percentile(arr, 25)
        q3 = np.percentile(arr, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outliers = np.sum((arr < lower_bound) | (arr > upper_bound))
        
        return StatisticalSummary(
            mean=float(mean),
            median=float(np.median(arr)),
            std_dev=float(std),
            min_value=float(np.min(arr)),
            max_value=float(np.max(arr)),
            percentile_25=float(np.percentile(arr, 25)),
            percentile_50=float(np.percentile(arr, 50)),
            percentile_75=float(np.percentile(arr, 75)),
            percentile_95=float(np.percentile(arr, 95)),
            percentile_99=float(np.percentile(arr, 99)),
            outliers_count=int(outliers),
            coefficient_variation=float(cv)
        )
    
    def assess_risk(
        self,
        events: List[Dict],
        aircraft_model: str = 'E190'
    ) -> RiskAssessment:
        """
        Avaliação de risco multi-fatorial
        
        Args:
            events: Lista de eventos
            aircraft_model: Modelo da aeronave
            
        Returns:
            RiskAssessment com nível de risco e ações
        """
        if not events:
            return RiskAssessment(
                risk_level="UNKNOWN",
                risk_score=0,
                contributing_factors=[],
                mitigation_actions=["Coletar dados de voos"],
                monitoring_requirements=["Iniciar monitoramento"]
            )
        
        risk_score = 0
        factors = []
        
        # Fator 1: Frequência de hard landings
        total_events = len(events)
        hard_landings = sum(1 for e in events if e.get('max_g', 0) >= 2.0)
        hl_rate = hard_landings / total_events if total_events > 0 else 0
        
        if hl_rate > 0.7:
            risk_score += 40
            factors.append({
                "factor": "Alta frequência de hard landings",
                "value": f"{hl_rate*100:.1f}%",
                "impact": "CRITICAL",
                "weight": 40
            })
        elif hl_rate > 0.5:
            risk_score += 25
            factors.append({
                "factor": "Frequência moderada de hard landings",
                "value": f"{hl_rate*100:.1f}%",
                "impact": "HIGH",
                "weight": 25
            })
        
        # Fator 2: Severidade máxima
        max_g_values = [e.get('max_g', 0) for e in events]
        max_g = max(max_g_values) if max_g_values else 0
        
        thresholds = self.threshold_configs.get(aircraft_model, self.threshold_configs['E190'])
        
        if max_g >= thresholds['CRITICAL']:
            risk_score += 35
            factors.append({
                "factor": "Evento crítico detectado",
                "value": f"{max_g:.3f}G",
                "impact": "CRITICAL",
                "weight": 35
            })
        elif max_g >= thresholds['HIGH']:
            risk_score += 20
            factors.append({
                "factor": "Evento de alta severidade",
                "value": f"{max_g:.3f}G",
                "impact": "HIGH",
                "weight": 20
            })
        
        # Fator 3: Tendência
        if len(events) >= 5:
            trend = self.analyze_trends(events, 'max_g')
            if trend.trend_direction == "INCREASING":
                if trend.slope > 0.1:
                    risk_score += 25
                    factors.append({
                        "factor": "Tendência crescente crítica",
                        "value": f"+{trend.change_rate:.1f}%",
                        "impact": "CRITICAL",
                        "weight": 25
                    })
                elif trend.slope > 0.05:
                    risk_score += 15
                    factors.append({
                        "factor": "Tendência crescente",
                        "value": f"+{trend.change_rate:.1f}%",
                        "impact": "HIGH",
                        "weight": 15
                    })
        
        # Determinar nível de risco
        if risk_score >= 75:
            risk_level = "CRITICAL"
        elif risk_score >= 50:
            risk_level = "HIGH"
        elif risk_score >= 25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # Gerar ações de mitigação
        mitigation_actions = self._generate_mitigation_actions(risk_level, factors)
        
        # Requisitos de monitoramento
        monitoring_reqs = self._generate_monitoring_requirements(risk_level)
        
        return RiskAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            contributing_factors=factors,
            mitigation_actions=mitigation_actions,
            monitoring_requirements=monitoring_reqs
        )
    
    def _generate_mitigation_actions(
        self,
        risk_level: str,
        factors: List[Dict]
    ) -> List[str]:
        """Gera ações de mitigação específicas"""
        
        actions = []
        
        if risk_level in ["CRITICAL", "HIGH"]:
            actions.append("🔴 AÇÃO IMEDIATA: Suspender operações até inspeção completa")
            actions.append("📋 Executar inspeção Fase III conforme AMM 05-50-03")
            actions.append("🔍 Investigar causa raiz dos eventos severos")
            actions.append("👨‍✈️ Revisar treinamento de tripulação")
            actions.append("⚙️ Verificar sistemas de trem de pouso")
        
        if risk_level == "MEDIUM":
            actions.append("⚠️ Executar inspeção Fase II conforme AMM 05-50-03")
            actions.append("📊 Aumentar frequência de monitoramento")
            actions.append("📝 Documentar todos os pousos para análise")
        
        if risk_level == "LOW":
            actions.append("✅ Manter inspeções preventivas regulares")
            actions.append("📈 Continuar monitoramento de tendências")
        
        # Ações específicas por fator
        for factor in factors:
            if "frequência" in factor['factor'].lower():
                actions.append("🎯 Implementar programa de redução de hard landings")
            if "tendência crescente" in factor['factor'].lower():
                actions.append("📉 Análise de causa raiz da deterioração")
        
        return actions
    
    def _generate_monitoring_requirements(self, risk_level: str) -> List[str]:
        """Gera requisitos de monitoramento"""
        
        reqs = []
        
        if risk_level == "CRITICAL":
            reqs.append("Monitoramento contínuo de TODOS os voos")
            reqs.append("Análise em tempo real dos parâmetros de pouso")
            reqs.append("Inspeção pós-voo obrigatória")
            reqs.append("Relatório diário para gerência")
        
        elif risk_level == "HIGH":
            reqs.append("Monitoramento diário")
            reqs.append("Revisão semanal de tendências")
            reqs.append("Inspeção conforme AMM")
        
        elif risk_level == "MEDIUM":
            reqs.append("Monitoramento semanal")
            reqs.append("Revisão mensal de estatísticas")
        
        else:  # LOW
            reqs.append("Monitoramento mensal")
            reqs.append("Revisão trimestral")
        
        return reqs
    
    def identify_patterns(self, events: List[Dict]) -> Dict[str, any]:
        """
        Identifica padrões complexos nos dados
        
        Args:
            events: Lista de eventos
            
        Returns:
            Dicionário com padrões identificados
        """
        patterns = {
            "severity_distribution": {},
            "temporal_patterns": {},
            "monitor_correlations": [],
            "anomalies": [],
            "clusters": []
        }
        
        if not events:
            return patterns
        
        # Distribuição de severidade
        severities = []
        for e in events:
            g = e.get('max_g', 0)
            if g >= 2.8:
                severities.append("CRITICAL")
            elif g >= 2.48:
                severities.append("HIGH")
            elif g >= 2.18:
                severities.append("MEDIUM")
            elif g >= 2.0:
                severities.append("LOW")
            else:
                severities.append("NORMAL")
        
        patterns['severity_distribution'] = dict(Counter(severities))
        
        # Detectar anomalias estatísticas
        g_values = [e.get('max_g', 0) for e in events if 'max_g' in e]
        if g_values:
            stats = self.calculate_comprehensive_statistics(g_values)
            
            # Eventos acima de 2 desvios padrão
            threshold = stats.mean + 2 * stats.std_dev
            anomalies = [
                {
                    "value": e.get('max_g'),
                    "index": i,
                    "deviation": (e.get('max_g', 0) - stats.mean) / stats.std_dev if stats.std_dev > 0 else 0
                }
                for i, e in enumerate(events)
                if e.get('max_g', 0) > threshold
            ]
            patterns['anomalies'] = anomalies
        
        return patterns
    
    def generate_executive_summary(
        self,
        events: List[Dict],
        aircraft_model: str = 'E190'
    ) -> str:
        """
        Gera resumo executivo completo para gestão
        
        Args:
            events: Lista de eventos
            aircraft_model: Modelo da aeronave
            
        Returns:
            String formatada com resumo executivo profissional
        """
        if not events:
            return "Sem dados para análise"
        
        total_flights = len(events)
        hard_landings = sum(1 for e in events if e.get('max_g', 0) >= 2.0)
        rate = (hard_landings / total_flights * 100) if total_flights > 0 else 0
        
        g_values = [e.get('max_g', 0) for e in events]
        max_g = max(g_values) if g_values else 0
        
        # Análises
        stats = self.calculate_comprehensive_statistics(g_values)
        trend = self.analyze_trends(events, 'max_g')
        risk = self.assess_risk(events, aircraft_model)
        patterns = self.identify_patterns(events)
        
        # Determinar status geral
        status_map = {
            "CRITICAL": ("CRÍTICO", "🔴"),
            "HIGH": ("ALTO RISCO", "🟠"),
            "MEDIUM": ("ATENÇÃO", "🟡"),
            "LOW": ("NORMAL", "🟢")
        }
        status_text, status_icon = status_map.get(risk.risk_level, ("DESCONHECIDO", "⚪"))
        
        summary = f"""
╔════════════════════════════════════════════════════════════════════════════
║ RESUMO EXECUTIVO - ANÁLISE AVANÇADA DE HARD LANDING
║ Aeronave: {aircraft_model} | Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}
╚════════════════════════════════════════════════════════════════════════════

{status_icon} STATUS GERAL: {status_text}
   Nível de Risco: {risk.risk_level} (Score: {risk.risk_score}/100)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 MÉTRICAS PRINCIPAIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Total de Voos Analisados:     {total_flights}
• Hard Landings Detectados:     {hard_landings} ({rate:.1f}%)
• Força G Máxima:                {max_g:.3f}G
• Força G Média:                 {stats.mean:.3f}G ± {stats.std_dev:.3f}G
• Percentil 95:                  {stats.percentile_95:.3f}G
• Percentil 99:                  {stats.percentile_99:.3f}G
• Coeficiente de Variação:       {stats.coefficient_variation:.1f}%
• Anomalias Detectadas:          {stats.outliers_count}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 ANÁLISE DE TENDÊNCIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Direção:           {trend.trend_direction}
• Taxa de Mudança:   {trend.change_rate:+.1f}%
• Confiança (R²):    {trend.confidence:.1f}%
• Nível de Alerta:   {trend.warning_level}

📝 Previsão: {trend.prediction}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 DISTRIBUIÇÃO DE SEVERIDADE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        for severity, count in patterns['severity_distribution'].items():
            icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢", "NORMAL": "⚪"}.get(severity, "•")
            pct = (count / total_flights * 100) if total_flights > 0 else 0
            summary += f"{icon} {severity:10s}: {count:3d} eventos ({pct:5.1f}%)\n"
        
        if risk.contributing_factors:
            summary += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  FATORES DE RISCO IDENTIFICADOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            for factor in risk.contributing_factors:
                summary += f"\n• {factor['factor']}\n"
                summary += f"  Valor: {factor['value']} | Impacto: {factor['impact']} | Peso: {factor['weight']}\n"
        
        summary += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 AÇÕES DE MITIGAÇÃO RECOMENDADAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        for i, action in enumerate(risk.mitigation_actions, 1):
            summary += f"\n{i}. {action}"
        
        summary += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 REQUISITOS DE MONITORAMENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        for req in risk.monitoring_requirements:
            summary += f"\n✓ {req}"
        
        summary += "\n\n" + "="*80 + "\n"
        summary += "Relatório gerado pelo Sistema Avançado de Análise de Hard Landing\n"
        summary += "="*80
        
        return summary

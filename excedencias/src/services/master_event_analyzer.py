"""
Master Event Analyzer Integrator
ETAPA 10: Integrates all 10 event analyzers into unified analysis pipeline
Provides comprehensive validation across all aircraft models and event types
"""

import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from utils.logger import logger

# Import all analyzers
from services.hard_landing_analyzer import HardLandingAnalyzer
from services.vmo_analyzer import VmoAnalyzer
from services.flap_overspeed_analyzer import FlapAnalyzer
from services.lg_down_overspeed_analyzer import LGDownOverspeedAnalyzer
from services.turbulence_analyzer import TurbulenceAnalyzer
from services.overweight_landing_analyzer import OverweightLandingAnalyzer
from services.temperature_envelope_analyzer import TemperatureEnvelopeAnalyzer
from utils.config import AppConfig


@dataclass
class IntegratedAnalysisResult:
    """Resultado da análise integrada"""
    aircraft_model: str
    flight_number: Optional[str]
    timestamp: Optional[str]
    total_events_found: int
    hard_landing_status: str
    vmo_status: str
    flap_status: str
    lg_overspeed_status: str
    turbulence_status: str
    overweight_status: str
    temp_envelope_status: str
    critical_findings: List[str]
    warnings: List[str]
    conformance_score: float  # 0-100%


class MasterEventAnalyzer:
    """
    Master analyzer that integrates all event detection systems
    Provides comprehensive aircraft inspection analysis
    """
    
    EVENTS = [
        ('hard_landing', HardLandingAnalyzer(), 'Hard Landing'),
        ('vmo_mmo', VmoAnalyzer(), 'VMO/MMO Overspeed'),
        ('flap_overspeed', FlapAnalyzer(), 'Flap Overspeed'),
        ('lg_overspeed', LGDownOverspeedAnalyzer(), 'LG Down Overspeed'),
        ('turbulence', TurbulenceAnalyzer(), 'Turbulence'),
        ('overweight', OverweightLandingAnalyzer(), 'Overweight Landing'),
        ('temp_envelope', TemperatureEnvelopeAnalyzer(), 'Temperature Envelope'),
    ]
    
    def __init__(self):
        """Initialize all analyzers"""
        self.analyzers = {event_id: analyzer for event_id, analyzer, _ in self.EVENTS}
        logger.info("[ETAPA 10] Master Event Analyzer initialized with 7 event types")
    
    def analyze_complete_flight(self, df: pd.DataFrame, weight_kg: float, model: str, 
                                flight_num: Optional[str] = None) -> IntegratedAnalysisResult:
        """
        Perform complete analysis of a flight across all event types
        
        Args:
            df: Flight data DataFrame
            weight_kg: Aircraft weight in kg
            model: Aircraft model ID
            flight_num: Optional flight number
            
        Returns:
            IntegratedAnalysisResult with all findings
        """
        logger.info(f"\n[ETAPA 10] === COMPLETE FLIGHT ANALYSIS ===")
        logger.info(f"            Model: {model.upper()}, Weight: {weight_kg:.0f} kg, Flight: {flight_num or 'N/A'}")
        logger.info(f"            Data points: {len(df)}, Columns: {len(df.columns)}")
        
        critical_findings = []
        warnings = []
        status_results = {}
        
        # Run all analyses
        for event_id, analyzer, event_name in self.EVENTS:
            try:
                logger.info(f"\n[ETAPA 10] Running: {event_name}...")
                
                if event_id == 'hard_landing':
                    results = analyzer.analyze(df, weight_kg, model)
                elif event_id == 'turbulence':
                    family_id = (
                        AppConfig.get_aircraft_by_id(model).id
                        if AppConfig.get_aircraft_by_id(model)
                        else 'e170'
                    )
                    results = analyzer.analyze_turbulence(df, family_id, model)
                else:
                    results = analyzer.analyze(df, weight_kg, model)

                if results:
                    result_items = results if isinstance(results, list) else [results]
                    if not result_items:
                        continue

                    result = result_items[0]

                    if event_id == 'turbulence':
                        status = "TURBULENCE_EXCEEDED" if result.is_turbulence else "NORMAL"
                        severity = result.severity_level if result.is_turbulence else "NORMAL"
                        message = "Turbulence exceedance detected" if result.is_turbulence else status
                    else:
                        status = getattr(result, 'status', 'UNKNOWN')
                        severity = getattr(result, 'severity', 'NORMAL')
                        message = getattr(result, 'message', status)

                    status_results[event_id] = status

                    # Categorize findings
                    if severity in ['HIGH', 'CRITICAL', 'SEVERE']:
                        critical_findings.append(f"{event_name}: {message}")
                    elif status not in ['NORMAL', 'None']:
                        warnings.append(f"{event_name}: {status}")

                    logger.info(f"   ✓ {event_name}: {status}")
            
            except Exception as e:
                logger.error(f"   ❌ {event_name} analysis failed: {e}")
                status_results[event_id] = "ERROR"
                warnings.append(f"{event_name}: Analysis error")
        
        # Calculate conformance score
        normal_count = sum(1 for status in status_results.values() if status == 'NORMAL')
        total_events = len(self.EVENTS)
        conformance_score = (normal_count / total_events * 100) if total_events > 0 else 0
        
        logger.info(f"\n[ETAPA 10] === ANALYSIS SUMMARY ===")
        logger.info(f"            Conformance: {conformance_score:.0f}% ({normal_count}/{total_events} events normal)")
        logger.info(f"            Critical Findings: {len(critical_findings)}")
        logger.info(f"            Warnings: {len(warnings)}")
        
        result = IntegratedAnalysisResult(
            aircraft_model=model.upper(),
            flight_number=flight_num,
            timestamp=df['TIMESTAMP'].iloc[0] if 'TIMESTAMP' in df.columns else None,
            total_events_found=len(critical_findings) + len(warnings),
            hard_landing_status=status_results.get('hard_landing', 'UNKNOWN'),
            vmo_status=status_results.get('vmo_mmo', 'UNKNOWN'),
            flap_status=status_results.get('flap_overspeed', 'UNKNOWN'),
            lg_overspeed_status=status_results.get('lg_overspeed', 'UNKNOWN'),
            turbulence_status=status_results.get('turbulence', 'UNKNOWN'),
            overweight_status=status_results.get('overweight', 'UNKNOWN'),
            temp_envelope_status=status_results.get('temp_envelope', 'UNKNOWN'),
            critical_findings=critical_findings,
            warnings=warnings,
            conformance_score=conformance_score
        )
        
        return result
    
    def generate_report(self, result: IntegratedAnalysisResult) -> str:
        """Generate human-readable report"""
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║                  FLIGHT INSPECTION REPORT                     ║
╚════════════════════════════════════════════════════════════════╝

Aircraft Model: {result.aircraft_model}
Flight Number: {result.flight_number or 'N/A'}
Analysis Time: {result.timestamp or 'N/A'}

EVENT ANALYSIS RESULTS:
{'-'*62}
  Hard Landing.........: {result.hard_landing_status}
  VMO/MMO Overspeed....: {result.vmo_status}
  Flap Overspeed.......: {result.flap_status}
  LG Down Overspeed....: {result.lg_overspeed_status}
  Turbulence...........: {result.turbulence_status}
  Overweight Landing...: {result.overweight_status}
  Temperature Envelope.: {result.temp_envelope_status}

OVERALL CONFORMANCE: {result.conformance_score:.0f}%
{'-'*62}

CRITICAL FINDINGS: ({len(result.critical_findings)})
"""
        for finding in result.critical_findings:
            report += f"  ⚠️  {finding}\n"
        
        report += f"\nWARNINGS: ({len(result.warnings)})\n"
        for warning in result.warnings:
            report += f"  ⚡ {warning}\n"
        
        if result.conformance_score == 100:
            report += "\n✅ FLIGHT WITHIN ALL SPECIFICATIONS - NO ACTION REQUIRED\n"
        elif result.conformance_score >= 70:
            report += "\n⚠️  FLIGHT HAS MINOR ISSUES - RECOMMEND REVIEW\n"
        else:
            report += "\n🔴 FLIGHT HAS SIGNIFICANT ISSUES - IMMEDIATE REVIEW REQUIRED\n"
        
        report += "╚════════════════════════════════════════════════════════════════╝\n"
        return report

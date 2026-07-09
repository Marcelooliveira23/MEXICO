"""
AI Assistant for Flight Analysis
Provides intelligent analysis interpretation and recommendations
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
from utils.logger import logger


@dataclass
class AIRecommendation:
    """AI-generated recommendation"""
    priority: str  # "HIGH", "MEDIUM", "LOW"
    category: str  # "MAINTENANCE", "INSPECTION", "DOCUMENTATION", "TRAINING"
    action: str
    rationale: str
    references: List[str]


@dataclass
class AIAnalysis:
    """AI-generated analysis interpretation"""
    summary: str
    risk_level: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    key_findings: List[str]
    recommendations: List[AIRecommendation]
    technical_explanation: str


class AIAssistant:
    """AI Assistant for flight inspection analysis"""
    
    def __init__(self):
        """Initialize AI Assistant"""
        self.model_available = False
        logger.info("AIAssistant initialized (offline mode)")
        
        # Knowledge base for offline recommendations
        self.knowledge_base = {
            "hard_landing": {
                "CRITICAL": {
                    "actions": [
                        "Perform immediate structural inspection per AMM",
                        "Inspect landing gear attachment points",
                        "Check for skin buckling or deformation",
                        "Document all findings in aircraft logbook"
                    ],
                    "references": ["AMM 32-00-00", "AMM 51-00-00", "AMM 53-00-00"]
                },
                "HIGH": {
                    "actions": [
                        "Schedule detailed inspection within 24 hours",
                        "Inspect landing gear components",
                        "Check fuselage underside for damage"
                    ],
                    "references": ["AMM 32-00-00", "SRM 53-10-00"]
                },
                "MEDIUM": {
                    "actions": [
                        "Perform standard post-flight inspection",
                        "Monitor for unusual vibrations or noises",
                        "Record event for trend analysis"
                    ],
                    "references": ["AMM 05-51-00"]
                }
            },
            "gear_overspeed": {
                "CRITICAL": {
                    "actions": [
                        "Do not retract landing gear until inspection",
                        "Inspect gear doors and actuators",
                        "Check hydraulic system for leaks",
                        "Inspect gear bay structure"
                    ],
                    "references": ["AMM 32-10-00", "AMM 32-20-00", "AMM 29-00-00"]
                }
            },
            "temp_envelope": {
                "CRITICAL": {
                    "actions": [
                        "Inspect engine components per manual",
                        "Check turbine blades for heat damage",
                        "Perform borescope inspection",
                        "Review engine parameters history"
                    ],
                    "references": ["AMM 71-00-00", "AMM 72-00-00", "EMM"]
                }
            },
            "max_speed": {
                "CRITICAL": {
                    "actions": [
                        "Inspect airframe for overstress damage",
                        "Check control surfaces attachment",
                        "Inspect wing-fuselage junction",
                        "Review flight recorder data"
                    ],
                    "references": ["AMM 51-00-00", "AMM 53-00-00", "AMM 57-00-00"]
                }
            },
            "flap_overspeed": {
                "CRITICAL": {
                    "actions": [
                        "Inspect flap tracks and hinges",
                        "Check flap actuators for damage",
                        "Examine flap surfaces for deformation",
                        "Test flap operation at low speed"
                    ],
                    "references": ["AMM 27-00-00", "AMM 57-20-00"]
                }
            },
            "overweight": {
                "CRITICAL": {
                    "actions": [
                        "Perform overweight landing inspection",
                        "Inspect main landing gear thoroughly",
                        "Check wing attachment points",
                        "Inspect brake assemblies"
                    ],
                    "references": ["AMM 32-00-00", "AMM 32-40-00", "SRM"]
                }
            }
        }
    
    def analyze_results(
        self,
        aircraft_id: str,
        event_type: str,
        analysis_results: List,
        flight_data: Dict
    ) -> AIAnalysis:
        """
        Generate AI analysis from inspection results
        
        Args:
            aircraft_id: Aircraft family
            event_type: Event type
            analysis_results: List of analysis results
            flight_data: Flight parameters data
            
        Returns:
            AIAnalysis with interpretation and recommendations
        """
        # Determine overall risk level
        risk_level = self._calculate_risk_level(analysis_results)
        
        # Generate summary
        summary = self._generate_summary(aircraft_id, event_type, analysis_results, risk_level)
        
        # Extract key findings
        key_findings = self._extract_key_findings(analysis_results)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            event_type, risk_level, analysis_results
        )
        
        # Technical explanation
        technical_explanation = self._generate_technical_explanation(
            event_type, analysis_results, flight_data
        )
        
        return AIAnalysis(
            summary=summary,
            risk_level=risk_level,
            key_findings=key_findings,
            recommendations=recommendations,
            technical_explanation=technical_explanation
        )
    
    def _calculate_risk_level(self, results: List) -> str:
        """Calculate overall risk level"""
        if not results:
            return "LOW"
        
        severities = [r.severity for r in results]
        
        if "CRITICO" in severities or "CRITICAL" in severities:
            return "CRITICAL"
        elif "ALERTA" in severities or "WARNING" in severities:
            return "HIGH"
        elif any(s in severities for s in ["MEDIUM", "MEDIO"]):
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_summary(
        self, aircraft_id: str, event_type: str, results: List, risk_level: str
    ) -> str:
        """Generate analysis summary"""
        count = len(results)
        event_names = {
            "hard_landing": "Hard Landing",
            "gear_overspeed": "Landing Gear Overspeed",
            "temp_envelope": "Temperature Envelope Exceedance",
            "max_speed": "Maximum Speed Exceedance",
            "flap_overspeed": "Flap Overspeed",
            "overweight": "Overweight Landing"
        }
        
        event_name = event_names.get(event_type, event_type.replace("_", " ").title())
        
        if risk_level == "CRITICAL":
            return f"CRITICAL: {event_name} detected on {aircraft_id.upper()} with {count} parameter(s) exceeding limits. Immediate action required."
        elif risk_level == "HIGH":
            return f"WARNING: {event_name} analysis shows {count} parameter(s) requiring attention on {aircraft_id.upper()}."
        elif risk_level == "MEDIUM":
            return f"ADVISORY: {event_name} detected on {aircraft_id.upper()} with {count} parameter(s) near limits. Monitoring recommended."
        else:
            return f"INFO: {event_name} analysis completed for {aircraft_id.upper()}. All parameters within acceptable ranges."
    
    def _extract_key_findings(self, results: List) -> List[str]:
        """Extract key findings from results"""
        findings = []
        
        for result in results:
            if hasattr(result, 'severity') and result.severity in ["CRITICO", "CRITICAL", "ALERTA", "WARNING"]:
                finding = f"{result.parameter}: {result.value} (limit: {result.limit}) - {result.message}"
                findings.append(finding)
        
        return findings[:5]  # Top 5 findings
    
    def _generate_recommendations(
        self, event_type: str, risk_level: str, results: List
    ) -> List[AIRecommendation]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Get knowledge base recommendations
        kb_data = self.knowledge_base.get(event_type, {}).get(risk_level, {})
        
        if kb_data:
            actions = kb_data.get("actions", [])
            references = kb_data.get("references", [])
            
            for action in actions:
                # Determine category
                category = "MAINTENANCE"
                if "inspect" in action.lower():
                    category = "INSPECTION"
                elif "document" in action.lower() or "record" in action.lower():
                    category = "DOCUMENTATION"
                elif "monitor" in action.lower():
                    category = "MAINTENANCE"
                
                # Determine priority
                priority = "HIGH" if risk_level in ["CRITICAL", "HIGH"] else "MEDIUM"
                if "immediate" in action.lower():
                    priority = "HIGH"
                
                rec = AIRecommendation(
                    priority=priority,
                    category=category,
                    action=action,
                    rationale=f"Based on {event_type.replace('_', ' ').title()} analysis with {risk_level} risk level",
                    references=references
                )
                recommendations.append(rec)
        
        # Add generic recommendations if none found
        if not recommendations:
            recommendations.append(AIRecommendation(
                priority="MEDIUM",
                category="DOCUMENTATION",
                action="Document event in aircraft maintenance log",
                rationale="Standard procedure for all exceedance events",
                references=["AMM 05-51-00"]
            ))
        
        return recommendations
    
    def _generate_technical_explanation(
        self, event_type: str, results: List, flight_data: Dict
    ) -> str:
        """Generate technical explanation"""
        explanations = {
            "hard_landing": (
                "A hard landing occurs when the aircraft touches down with excessive vertical "
                "acceleration or descent rate. This can cause structural stress to the airframe, "
                "particularly at landing gear attachment points and the lower fuselage. "
                "The primary concern is potential fatigue damage to structural components."
            ),
            "gear_overspeed": (
                "Landing gear overspeed occurs when the gear is extended or remains extended "
                "at airspeeds exceeding the maximum allowable speed (VLE/VLO). This can cause "
                "excessive aerodynamic loads on gear doors, actuators, and structural attachments, "
                "potentially leading to deformation or failure."
            ),
            "temp_envelope": (
                "Operating outside the temperature envelope can affect engine performance and "
                "structural integrity. High temperatures can cause thermal stress and accelerated "
                "wear on turbine components, while low temperatures can affect oil viscosity and "
                "increase risk of ice formation."
            ),
            "max_speed": (
                "Exceeding maximum operating speed (VMO/MMO) subjects the airframe to aerodynamic "
                "loads beyond its design limits. This can cause flutter, structural deformation, "
                "or overstress of control surfaces and their attachment points."
            ),
            "flap_overspeed": (
                "Flap overspeed occurs when flaps are extended beyond their maximum speed limits. "
                "The increased aerodynamic loads can damage flap tracks, actuators, and support "
                "structures, potentially affecting flap operation and aircraft controllability."
            ),
            "overweight": (
                "Overweight landing subjects the landing gear and airframe to loads exceeding "
                "normal design limits. This can cause stress to landing gear components, brake "
                "systems, and wing attachment points, requiring thorough inspection."
            )
        }
        
        base_explanation = explanations.get(event_type, "Event requires detailed analysis per maintenance manual.")
        
        # Add specific details from results
        if results:
            details = "\n\nSpecific findings:\n"
            for result in results[:3]:  # Top 3
                details += f"- {result.parameter}: {result.message}\n"
            return base_explanation + details
        
        return base_explanation
    
    def generate_narrative_report(self, ai_analysis: AIAnalysis, flight_info: Dict) -> str:
        """Generate human-readable narrative report"""
        report = f"""
AIRCRAFT INSPECTION ANALYSIS REPORT
{'='*60}

SUMMARY
{ai_analysis.summary}

RISK ASSESSMENT: {ai_analysis.risk_level}

TECHNICAL BACKGROUND
{ai_analysis.technical_explanation}

KEY FINDINGS
"""
        for i, finding in enumerate(ai_analysis.key_findings, 1):
            report += f"{i}. {finding}\n"
        
        report += f"""
RECOMMENDED ACTIONS
{'='*60}
"""
        
        for i, rec in enumerate(ai_analysis.recommendations, 1):
            report += f"""
{i}. [{rec.priority}] {rec.action}
   Category: {rec.category}
   Rationale: {rec.rationale}
   References: {', '.join(rec.references)}
"""
        
        report += f"""
{'='*60}
This analysis was generated using technical data and established
maintenance procedures. Always consult the Aircraft Maintenance
Manual (AMM) for detailed inspection procedures.
"""
        
        return report

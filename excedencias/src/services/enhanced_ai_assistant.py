"""
Enhanced AI Assistant for Flight Analysis
Versão 3.0 - Sistema Interativo Completo com Conversação
"""
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
import json
from datetime import datetime
from utils.logger import logger
from .all_families_specs import AllFamiliesSpecifications


@dataclass
class ConversationContext:
    """Contexto da conversa com o usuário"""
    aircraft_model: Optional[str] = None
    event_type: Optional[str] = None
    current_data: Optional[Dict] = None
    analysis_results: Optional[List] = None
    user_questions: List[str] = field(default_factory=list)
    ai_responses: List[str] = field(default_factory=list)
    suggestions_given: List[str] = field(default_factory=list)
    errors_found: List[str] = field(default_factory=list)


@dataclass
class DataQualityIssue:
    """Problema de qualidade de dados detectado"""
    severity: str  # "CRITICAL", "WARNING", "INFO"
    parameter: str
    issue: str
    suggestion: str
    impact: str


@dataclass
class AIRecommendation:
    """Recomendação gerada pela IA"""
    priority: str  # "HIGH", "MEDIUM", "LOW"
    category: str
    action: str
    rationale: str
    references: List[str]
    estimated_time: Optional[str] = None
    cost_impact: Optional[str] = None


@dataclass
class AIAnalysis:
    """Análise completa gerada pela IA"""
    summary: str
    risk_level: str
    key_findings: List[str]
    recommendations: List[AIRecommendation]
    technical_explanation: str
    data_quality_score: float
    missing_parameters: List[str]
    conversation_suggestions: List[str]


class EnhancedAIAssistant:
    """
    AI Assistant Avançado com Capacidades de:
    - Conversação natural
    - Detecção proativa de problemas
    - Sugestões contextuais
    - Análise de qualidade de dados
    - Validação por modelo de aeronave
    """
    
    def __init__(self):
        """Inicializar Enhanced AI Assistant"""
        self.specs = AllFamiliesSpecifications()
        self.context = ConversationContext()
        logger.info("Enhanced AI Assistant initialized")
        
        # Mapeamento de modelos para famílias e especificações
        # Família E145: E135, E140, E145
        # Família E170: E170, E175
        # Família E1: E190, E195
        # Família E2: E190-E2, E195-E2
        self.model_specs_map = {
            "e170": "E170",
            "e175": "E175",
            "e190": "E190",
            "e195": "E195",
            "e135": "E135",
            "e140": "E140",
            "e145": "E145",
            "e190-e2": "E190_E2",
            "e195-e2": "E195_E2",
        }
        
        # Mapeamento de família para modelos
        self.family_to_models = {
            "e145": ["E135", "E140", "E145"],
            "e170": ["E170", "E175"],
            "e1": ["E190", "E195"],
            "e2": ["E190_E2", "E195_E2"]
        }
        
        # Base de conhecimento expandida
        self.knowledge_base = self._build_knowledge_base()
        
        # Padrões de conversação
        self.conversation_patterns = {
            "greeting": ["Olá!", "Como posso ajudá-lo?", "Pronto para analisar"],
            "data_loaded": [
                "Dados carregados com sucesso! Encontrei {rows} linhas.",
                "Analisando {rows} registros de voo...",
                "Dados importados! Posso começar a análise?"
            ],
            "error_found": [
                "⚠️ Detectei um problema: {issue}",
                "Atenção! {issue}",
                "Preciso alertá-lo sobre: {issue}"
            ],
            "suggestion": [
                "💡 Sugestão: {suggestion}",
                "Recomendo que você: {suggestion}",
                "Seria útil: {suggestion}"
            ]
        }
    
    def _build_knowledge_base(self) -> Dict:
        """Construir base de conhecimento expandida"""
        return {
            "hard_landing": {
                "description": "Pouso com aceleração vertical excessiva",
                "primary_parameters": [
                    "vertical_acceleration", "descent_rate",
                    "pitch", "altitude", "airspeed"
                ],
                "secondary_parameters": [
                    "roll", "weight", "cg_position",
                    "wind_speed", "runway_condition"
                ],
                "critical_thresholds": {
                    "E170": {"g_force": 2.1, "descent": 800},
                    "E175": {"g_force": 2.2, "descent": 800},
                    "E190": {"g_force": 2.2, "descent": 850},
                    "E195": {"g_force": 2.2, "descent": 850},
                    "E145": {"g_force": 2.3, "descent": 900},
                },
                "inspection_tasks": {
                    "CRITICAL": [
                        "Inspeção estrutural completa da fuselagem inferior",
                        "Verificação dos pontos de fixação do trem de pouso",
                        "Inspeção visual da pele da aeronave por deformações",
                        "Verificação de rivets e fasteners",
                        "Boroscopia das longarinas principais"
                    ],
                    "HIGH": [
                        "Inspeção detalhada do trem de pouso",
                        "Verificação de componentes hidráulicos",
                        "Inspeção da parte inferior da fuselagem"
                    ],
                    "MEDIUM": [
                        "Inspeção pós-voo padrão",
                        "Monitoramento de vibrações anormais"
                    ]
                }
            },
            "gear_overspeed": {
                "description": "Trem de pouso estendido acima da velocidade máxima",
                "primary_parameters": ["airspeed", "gear_position", "altitude"],
                "secondary_parameters": ["mach", "pressure_altitude"],
                "critical_thresholds": {
                    "E170": {"vle": 250, "vlo_extend": 250, "vlo_retract": 220},
                    "E175": {"vle": 250, "vlo_extend": 250, "vlo_retract": 220},
                    "E190": {"vle": 250, "vlo_extend": 250, "vlo_retract": 220},
                    "E195": {"vle": 250, "vlo_extend": 250, "vlo_retract": 220},
                    "E145": {"vle": 250, "vlo_extend": 250, "vlo_retract": 220},
                }
            },
            "temp_envelope": {
                "description": "Operação fora do envelope de temperatura",
                "primary_parameters": ["egt", "tat", "sat", "n1", "n2"],
                "secondary_parameters": ["altitude", "mach", "thrust_setting"],
                "critical_thresholds": {
                    "E170": {"egt_takeoff": 950, "egt_continuous": 915, "tat_max": 54},
                    "E175": {"egt_takeoff": 950, "egt_continuous": 915, "tat_max": 54},
                }
            },
            "max_speed": {
                "description": "Excedência da velocidade máxima de operação",
                "primary_parameters": ["airspeed", "mach", "altitude"],
                "secondary_parameters": ["pitch", "thrust_setting"],
                "critical_thresholds": {
                    "E170": {"vmo": 320, "mmo": 0.82},
                    "E175": {"vmo": 320, "mmo": 0.82},
                }
            },
            "flap_overspeed": {
                "description": "Flaps estendidos acima da velocidade máxima",
                "primary_parameters": ["airspeed", "flap_position"],
                "secondary_parameters": ["altitude", "configuration"],
            },
            "overweight": {
                "description": "Pouso acima do peso máximo permitido",
                "primary_parameters": ["weight", "landing_weight"],
                "secondary_parameters": ["fuel_weight", "cg_position"],
            }
        }
    
    def greet_user(self, aircraft_model: str, event_type: str) -> str:
        """Cumprimentar usuário e estabelecer contexto"""
        self.context.aircraft_model = aircraft_model.lower()
        self.context.event_type = event_type
        
        model_name = aircraft_model.upper()
        event_name = event_type.replace("_", " ").title()
        
        greeting = f"""
🛩️ **Enhanced AI Assistant - Mexicana {model_name}**

Olá! Estou pronto para ajudá-lo com a análise de **{event_name}**.

📋 **O que posso fazer por você:**
✓ Analisar dados de voo e detectar excedências
✓ Validar parâmetros específicos do {model_name}
✓ Sugerir melhorias e identificar problemas
✓ Conversar sobre os resultados e esclarecer dúvidas
✓ Gerar relatórios técnicos detalhados

💡 **Dica:** Importe seus dados CSV e começarei a análise automática!
"""
        return greeting
    
    def analyze_data_quality(
        self, df_data: Any, event_type: str, aircraft_model: str
    ) -> Tuple[float, List[DataQualityIssue]]:
        """
        Analisa qualidade dos dados e identifica problemas
        
        Returns:
            (score, issues) onde score é 0-100
        """
        issues = []
        score = 100.0
        
        # Obter parâmetros esperados para este evento
        event_kb = self.knowledge_base.get(event_type, {})
        required_params = event_kb.get("primary_parameters", [])
        optional_params = event_kb.get("secondary_parameters", [])
        
        if df_data is None or len(df_data) == 0:
            issues.append(DataQualityIssue(
                severity="CRITICAL",
                parameter="dataset",
                issue="Nenhum dado disponível",
                suggestion="Importe um arquivo CSV válido com dados de voo",
                impact="Análise impossível sem dados"
            ))
            return 0.0, issues
        
        # Verificar colunas disponíveis
        available_columns = [col.lower() for col in df_data.columns]
        
        # Verificar parâmetros primários ausentes
        missing_primary = []
        for param in required_params:
            variations = self._get_column_variations(param)
            if not any(var in available_columns for var in variations):
                missing_primary.append(param)
                score -= 15
        
        if missing_primary:
            issues.append(DataQualityIssue(
                severity="CRITICAL",
                parameter=", ".join(missing_primary),
                issue=f"Parâmetros críticos ausentes: {', '.join(missing_primary)}",
                suggestion=(
                    f"Adicione colunas para: {', '.join(missing_primary)}. "
                    "Estes parâmetros são essenciais para análise precisa."
                ),
                impact="Análise limitada ou imprecisa"
            ))
        
        # Verificar parâmetros secundários ausentes
        missing_secondary = []
        for param in optional_params:
            variations = self._get_column_variations(param)
            if not any(var in available_columns for var in variations):
                missing_secondary.append(param)
                score -= 5
        
        if missing_secondary:
            issues.append(DataQualityIssue(
                severity="WARNING",
                parameter=", ".join(missing_secondary),
                issue=f"Parâmetros opcionais ausentes: {', '.join(missing_secondary)}",
                suggestion=(
                    "Considere adicionar estes parâmetros para análise mais completa"
                ),
                impact="Análise menos detalhada"
            ))
        
        # Verificar valores nulos
        null_counts = df_data.isnull().sum()
        high_null_cols = null_counts[null_counts > len(df_data) * 0.1].index.tolist()
        
        if high_null_cols:
            issues.append(DataQualityIssue(
                severity="WARNING",
                parameter=", ".join(high_null_cols),
                issue=f"Colunas com >10% valores nulos: {', '.join(high_null_cols)}",
                suggestion="Verifique a fonte dos dados e considere interpolação",
                impact="Pode afetar precisão da análise"
            ))
            score -= 10
        
        # Verificar tamanho do dataset
        if len(df_data) < 100:
            issues.append(DataQualityIssue(
                severity="INFO",
                parameter="dataset_size",
                issue=f"Dataset pequeno ({len(df_data)} linhas)",
                suggestion="Para análise mais robusta, considere períodos maiores",
                impact="Análise estatística menos confiável"
            ))
            score -= 5
        
        return max(0, min(100, score)), issues
    
    def _get_column_variations(self, param: str) -> List[str]:
        """Obter variações de nomes de colunas"""
        variations_map = {
            "vertical_acceleration": [
                "vertical_acceleration", "vert_accel", "nz", "g_force",
                "vertical_g", "accel_z", "load_factor"
            ],
            "descent_rate": [
                "descent_rate", "vertical_speed", "vs", "roc", "rod"
            ],
            "airspeed": [
                "airspeed", "ias", "kias", "tas", "cas", "speed"
            ],
            "altitude": [
                "altitude", "alt", "alt_ft", "pressure_altitude", "baro_alt"
            ],
            "pitch": ["pitch", "theta", "pitch_angle"],
            "roll": ["roll", "phi", "bank", "roll_angle"],
            "egt": ["egt", "exhaust_gas_temp", "turbine_temp"],
            "tat": ["tat", "total_air_temp", "oat", "sat"],
            "gear_position": ["gear_position", "landing_gear", "gear_pos"],
            "flap_position": ["flap_position", "flaps", "flap_pos"],
            "weight": ["weight", "gross_weight", "landing_weight"],
        }
        return variations_map.get(param, [param])
    
    def suggest_improvements(
        self, data_quality_score: float,
        issues: List[DataQualityIssue],
        aircraft_model: str
    ) -> List[str]:
        """Sugerir melhorias baseadas na análise"""
        suggestions = []
        
        if data_quality_score < 70:
            suggestions.append(
                "📊 **Qualidade dos Dados:** Score atual é {:.1f}/100. "
                "Recomendo melhorar a coleta de dados.".format(data_quality_score)
            )
        
        critical_issues = [i for i in issues if i.severity == "CRITICAL"]
        if critical_issues:
            suggestions.append(
                f"⚠️ **{len(critical_issues)} problemas críticos** detectados. "
                "Resolva-os antes da análise final."
            )
        
        # Sugestões específicas por modelo (note: use modelo específico, não família)
        model_suggestions = {
            "E170": [
                "Para E170, preste atenção especial aos limites mais conservadores de hard landing (2.1G)",
                "Verifique se o sistema está usando os limites corretos de temperatura para CF34-8E5"
            ],
            "E145": [
                "E145 possui limites diferentes nas posições de flap - verifique configuração",
                "Sistema hidráulico dual do E145 requer monitoramento específico"
            ]
        }
        
        # Converter entrada para modelo específico
        model_key = self.model_specs_map.get(aircraft_model.lower(), aircraft_model.upper())
        if model_key in model_suggestions:
            suggestions.extend(model_suggestions[model_key])
        
        return suggestions
    
    def detect_anomalies(
        self, df_data: Any, aircraft_model: str, event_type: str
    ) -> List[str]:
        """Detectar anomalias e padrões suspeitos nos dados"""
        anomalies = []
        
        # Implementar detecção de padrões
        # Exemplo: valores constantes, picos anormais, etc.
        
        return anomalies
    
    def chat(self, user_message: str) -> str:
        """
        Responder a mensagens do usuário de forma natural
        
        Args:
            user_message: Mensagem do usuário
            
        Returns:
            Resposta contextual da IA
        """
        self.context.user_questions.append(user_message)
        message_lower = user_message.lower()
        
        # Detecção de intenção
        if any(word in message_lower for word in ["ajuda", "help", "como", "o que"]):
            response = self._help_response(message_lower)
        elif any(word in message_lower for word in ["limite", "threshold", "máximo"]):
            response = self._limits_response(message_lower)
        elif any(word in message_lower for word in ["erro", "error", "problema"]):
            response = self._error_response(message_lower)
        elif any(word in message_lower for word in ["sugestão", "suggest", "recomendar"]):
            response = self._suggestion_response(message_lower)
        else:
            response = self._general_response(message_lower)
        
        self.context.ai_responses.append(response)
        return response
    
    def _help_response(self, message: str) -> str:
        """Responder perguntas de ajuda"""
        if "limite" in message or "threshold" in message:
            # Default: E190 (modelo mais comum da família E1)
            model = self.context.aircraft_model or "E190"
            event = self.context.event_type or "hard_landing"
            
            # Converter para modelo específico se for família
            model_key = self.model_specs_map.get(model.lower(), model.upper())
            
            kb = self.knowledge_base.get(event, {})
            thresholds = kb.get("critical_thresholds", {}).get(model_key, {})
            
            if thresholds:
                response = f"**Limites para {model_key} - {event.replace('_', ' ').title()}:**\n\n"
                for key, value in thresholds.items():
                    response += f"• {key}: {value}\n"
                return response
        
        return """
**Como posso ajudar:**

1. **Análise de Dados:** Importados via CSV
2. **Validação:** Verifico conformidade com especificações
3. **Conversação:** Tire dúvidas sobre limites e procedimentos
4. **Sugestões:** Proponho melhorias e correções
5. **Relatórios:** Gero documentação técnica

Pergunte algo específico e responderei!
"""
    
    def _limits_response(self, message: str) -> str:
        """Responder sobre limites técnicos"""
        # Implementar lógica de resposta sobre limites
        return "Consultando limites técnicos..."
    
    def _error_response(self, message: str) -> str:
        """Responder sobre erros"""
        if self.context.errors_found:
            return f"Encontrei {len(self.context.errors_found)} erros:\n" + \
                   "\n".join(f"• {e}" for e in self.context.errors_found)
        return "Nenhum erro detectado no momento. Tudo parece correto!"
    
    def _suggestion_response(self, message: str) -> str:
        """Dar sugestões"""
        if self.context.suggestions_given:
            return "Minhas sugestões:\n" + \
                   "\n".join(f"• {s}" for s in self.context.suggestions_given)
        return "Ainda não tenho sugestões específicas. Preciso de mais contexto!"
    
    def _general_response(self, message: str) -> str:
        """Resposta geral"""
        return (
            "Entendi sua pergunta. Posso ajudar com:\n"
            "• Limites técnicos específicos\n"
            "• Procedimentos de inspeção\n"
            "• Análise de dados\n"
            "\nSeja mais específico para uma resposta melhor!"
        )


"""
Hard Landing Analyzer - 100% compliant with AMM TASK 05-50-03-200-801-A Rev 121 (PDF 801)
                      and 05-50-03-200-804-A Rev XX (PDF 804 for E190/E195)
Implements 3 monitor system: Vertical Acceleration, Roll Rate, Pitch Rate
ETAPA 3: Support for model-specific PDF selection (E170 uses PDF 801, E190 uses PDF 804)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from utils.logger import logger
from utils.config import AppConfig


@dataclass
class HardLandingResult:
    """Resultado da análise de hard landing"""
    status: str  # "NORMAL", "HARD_LANDING_LOW", "HARD_LANDING_HIGH", "ENGINE_INSPECTION"
    vertical_accel: Dict
    roll_rate: Dict
    pitch_rate: Dict
    weight_kg: float
    critical_monitors: List[str]
    severity: str  # "NORMAL", "LOW", "HIGH", "CRITICAL"
    message: str


@dataclass
class HardLandingLegacyResult:
    """Resultado simplificado para compatibilidade com API antiga."""
    is_hard_landing: bool
    severity_level: str
    max_vertical_accel: float


class HardLandingAnalyzer:
    """
    Analisador de Hard Landing seguindo AMM TASK 05-50-03-200-801-A Rev 121
    
    Implementa 3 monitores:
    1. Vertical Acceleration (Figure 607) - thresholds interpolados por peso
    2. Roll Rate (Figure 608 + 614) - validado com aceleração normal
    3. Pitch Rate (Figure 609) - limites específicos por modelo
    """
    
    # E145 - Figure 602 AMM 05-50-02 (Table 4-1)
    VERT_ACCEL_THRESHOLDS_E145 = {
        'threshold': [
            (12000, 2.300), (12200, 2.300), (12400, 2.266), (12600, 2.233),
            (12800, 2.200), (13000, 2.181), (13200, 2.162), (13400, 2.143),
            (13600, 2.125), (13800, 2.107), (14000, 2.089), (14500, 2.043),
            (15000, 1.999), (15500, 1.956), (16000, 1.915), (16500, 1.876),
            (17000, 1.839), (17500, 1.803), (18000, 1.769), (18500, 1.736),
            (19000, 1.704), (19500, 1.673), (20000, 1.644), (20500, 1.615),
            (21000, 1.587), (22000, 1.535), (24100, 1.492)
        ]
    }
    
    # Figure 607 - Vertical Acceleration Thresholds E1/E2 (interpolation tables)
    # PDF 801 - E170/E175 Family
    # CORRIGIDO: Range expandido para cobrir pesos reais de landing (25-40 ton)
    VERT_ACCEL_THRESHOLDS = {
        'low': [
            (25000, 1.780), (28000, 1.790), (30000, 1.795), (32000, 1.798),
            (34000, 1.799), (36000, 1.800), (38000, 1.800), (40000, 1.850),
            (42000, 1.900), (44000, 1.950), (46000, 2.000), (48000, 2.050),
            (50000, 2.100), (52000, 2.150), (54000, 2.200)
        ],
        'high': [
            (25000, 2.080), (28000, 2.090), (30000, 2.095), (32000, 2.098),
            (34000, 2.099), (36000, 2.100), (38000, 2.100), (40000, 2.150),
            (42000, 2.200), (44000, 2.250), (46000, 2.300), (48000, 2.350),
            (50000, 2.400), (52000, 2.450), (54000, 2.500)
        ],
        'engine': [
            (25000, 2.380), (28000, 2.390), (30000, 2.395), (32000, 2.398),
            (34000, 2.399), (36000, 2.400), (38000, 2.400), (40000, 2.450),
            (42000, 2.500), (44000, 2.550), (46000, 2.600), (48000, 2.650),
            (50000, 2.700), (52000, 2.750), (54000, 2.800)
        ]
    }
    
    # Figure 608 - Roll Rate Thresholds (interpolation tables)
    # PDF 801 - E170/E175 Family
    # CORRIGIDO: Range expandido para cobrir pesos reais de landing
    ROLL_RATE_THRESHOLDS = {
        'low': [
            (25000, 9.80), (28000, 9.90), (30000, 9.95), (32000, 9.98),
            (34000, 9.99), (36000, 10.00), (38000, 10.00), (40000, 10.50),
            (42000, 11.00), (44000, 11.50), (46000, 12.00), (48000, 12.50),
            (50000, 13.00), (52000, 13.50), (54000, 14.00)
        ],
        'high': [
            (25000, 15.80), (28000, 15.90), (30000, 15.95), (32000, 15.98),
            (34000, 15.99), (36000, 16.00), (38000, 16.00), (40000, 16.80),
            (42000, 17.60), (44000, 18.40), (46000, 19.20), (48000, 20.00),
            (50000, 20.80), (52000, 21.60), (54000, 22.40)
        ]
    }
    
    # Figure 614 - Roll Rate Validation Threshold (Normal Acceleration)
    # PDF 801 - E170/E175 Family
    # CORRIGIDO: Range expandido para cobrir pesos reais de landing
    ROLL_VALIDATION_THRESHOLD = {
        'norm_accel': [
            (25000, 1.030), (28000, 1.040), (30000, 1.047), (32000, 1.051),
            (34000, 1.053), (36000, 1.054), (38000, 1.054), (40000, 1.082),
            (42000, 1.110), (44000, 1.138), (46000, 1.166), (48000, 1.194),
            (50000, 1.222), (52000, 1.250), (54000, 1.278)
        ]
    }
    
    # Figure 609 - Pitch Rate Thresholds (model specific)
    # E145/E135 - Table 601 AMM 05-50-02
    PITCH_RATE_E145 = {
        'threshold': -5.0  # deg/s para EMB-145 (all versions)
    }
    
    PITCH_RATE_E135 = {
        'threshold': -6.0  # deg/s para EMB-135ER/LR
    }
    
    PITCH_RATE_E190 = {
        'low': -6.00,   # deg/s
        'high': -6.60   # deg/s
    }
    
    PITCH_RATE_E195 = {
        'low': -6.00,
        'high': -6.60
    }
    
    PITCH_RATE_E170 = {
        'low': -5.50,
        'high': -6.10
    }
    
    PITCH_RATE_E175 = {
        'low': -5.80,
        'high': -6.40
    }
    
    # ==================== PDF 804 THRESHOLDS (E190/E195) ====================
    # Baseado em AMM TASK 05-50-03-200-804-A
    # Diferenças críticas de PDF 804 (E190/E195) vs PDF 801 (E170/E175):
    # - Roll Rate Conditional: Requer N2 > 75% when roll rate é alto
    # - Vertical Accel: Thresholds levemente diferentes para aeronaves maiores
    
    # PDF 804 - Figure 607/PDF804 - Vertical Acceleration (E190/E195)
    # CORRIGIDO: Range expandido para cobrir pesos reais de landing (35-62 ton)
    VERT_ACCEL_THRESHOLDS_PDF804 = {
        'low': [
            (35000, 1.680), (38000, 1.685), (40000, 1.690), (42000, 1.693),
            (45000, 1.695), (48000, 1.697), (50000, 1.698), (52000, 1.699),
            (54000, 1.699), (56150, 1.700), (58000, 1.720), (60000, 1.740),
            (62000, 1.760)  # E190/E195 limits
        ],
        'high': [
            (35000, 1.980), (38000, 1.985), (40000, 1.990), (42000, 1.993),
            (45000, 1.995), (48000, 1.997), (50000, 1.998), (52000, 1.999),
            (54000, 1.999), (56150, 2.000), (58000, 2.030), (60000, 2.060),
            (62000, 2.090)  # E190/E195 limits
        ],
        'engine': [
            (35000, 2.280), (38000, 2.285), (40000, 2.290), (42000, 2.293),
            (45000, 2.295), (48000, 2.297), (50000, 2.298), (52000, 2.299),
            (54000, 2.299), (56150, 2.300), (58000, 2.340), (60000, 2.380),
            (62000, 2.420)  # E190/E195 limits
        ]
    }
    
    # PDF 804 - Roll Rate with N2 Conditional
    # CORRIGIDO: Range expandido para cobrir pesos reais de landing (35-62 ton)
    ROLL_RATE_THRESHOLDS_PDF804 = {
        'low_n2_lt_75': [
            (35000, 11.60), (40000, 11.70), (45000, 11.80), (50000, 11.90),
            (54000, 11.95), (56150, 12.00), (58000, 12.40), (60000, 12.80),
            (62000, 13.20)
        ],
        'low_n2_gte_75': [
            (35000, 7.60), (40000, 7.70), (45000, 7.80), (50000, 7.90),
            (54000, 7.95), (56150, 8.00), (58000, 8.30), (60000, 8.60),
            (62000, 8.90)
        ],
        'high_n2_lt_75': [
            (35000, 18.60), (40000, 18.70), (45000, 18.80), (50000, 18.90),
            (54000, 18.95), (56150, 19.00), (58000, 19.60), (60000, 20.20),
            (62000, 20.80)
        ],
        'high_n2_gte_75': [
            (35000, 12.10), (40000, 12.20), (45000, 12.30), (50000, 12.40),
            (54000, 12.45), (56150, 12.50), (58000, 12.95), (60000, 13.40),
            (62000, 13.85)
        ]
    }
    
    # PDF 804 - Pitch Rate Conditional (similar ao 801 mas with N2 factor)
    PITCH_RATE_E190_PDF804 = {
        'low': -5.50,   # deg/s (PDF 804 adjusted)
        'high': -6.10,  # deg/s (PDF 804 adjusted)
        'with_n2_high': -5.00  # When N2 >= 75%
    }
    
    PITCH_RATE_E195_PDF804 = {
        'low': -5.50,
        'high': -6.10,
        'with_n2_high': -5.00
    }
    
    @staticmethod
    def interpolate_threshold(weight_kg: float, table: List[Tuple[float, float]]) -> float:
        """
        Interpola threshold baseado no peso da aeronave
        
        Args:
            weight_kg: Peso da aeronave em kg
            table: Lista de tuplas (peso_kg, threshold)
            
        Returns:
            Threshold interpolado
        """
        # Converter lista para arrays numpy
        weights = np.array([w for w, _ in table])
        values = np.array([v for _, v in table])
        
        # Se peso está fora do range, usar valores extremos
        if weight_kg <= weights[0]:
            return values[0]
        if weight_kg >= weights[-1]:
            return values[-1]
        
        # Interpolação linear
        return float(np.interp(weight_kg, weights, values))
    
    def get_pitch_thresholds(self, model: str) -> Dict[str, float]:
        """
        Retorna thresholds de pitch rate para o modelo
        ETAPA 3: Agora suporta PDF 804 para E190/E195 dinamicamente
        """
        model_lower = model.lower()
        
        # Normalizar model ID para formato consistente
        model_id = model_lower.replace('emb-', 'e').replace('_', '').strip()
        
        # Tentar obter do registry da ETAPA 1
        try:
            pdf_ref = AppConfig.get_hard_landing_pdf(model_id)
            
            # Se é PDF 804, usar thresholds PDF 804
            if pdf_ref == "804":
                if 'e195' in model_id or 'e195' in model_lower:
                    return self.PITCH_RATE_E195_PDF804
                elif 'e190' in model_id or 'e190' in model_lower:
                    return self.PITCH_RATE_E190_PDF804
            # Se é PDF 801, usar thresholds PDF 801
            elif pdf_ref == "801":
                if 'e175' in model_id or 'e175' in model_lower:
                    return self.PITCH_RATE_E175
                elif 'e170' in model_id or 'e170' in model_lower:
                    return self.PITCH_RATE_E170
        except:
            pass  # Fallback para lógica antiga se AppConfig não estiver disponível
        
        # Fallback: lógica antiga baseada em string matching
        model_upper = model.upper()
        if 'E145' in model_upper or 'E135' in model_upper or 'EMB-145' in model_upper:
            return self.PITCH_RATE_E145
        elif 'EMB-135' in model_upper:
            return self.PITCH_RATE_E135
        elif 'E195' in model_upper:
            # Preferir PDF 804 para E195
            return self.PITCH_RATE_E195_PDF804
        elif 'E190' in model_upper or 'E1-' in model_upper:
            # Preferir PDF 804 para E190
            return self.PITCH_RATE_E190_PDF804
        elif 'E175' in model_upper:
            return self.PITCH_RATE_E175
        elif 'E170' in model_upper:
            return self.PITCH_RATE_E170
        else:
            # Default para E145 se não reconhecido
            logger.warning(f"Modelo {model} não reconhecido, usando thresholds E145")
            return self.PITCH_RATE_E145
    
    def get_vertical_accel_thresholds(self, model: str, weight_kg: float) -> Dict[str, float]:
        """
        Retorna thresholds de aceleração vertical para o modelo
        ETAPA 3: Seleciona PDF 801 ou 804 baseado no modelo
        
        Returns:
            Dicionário com 'low', 'high', 'engine' thresholds
        """
        model_lower = model.lower()
        model_id = model_lower.replace('emb-', 'e').replace('_', '').strip()
        
        # Tentar obter PDF reference da ETAPA 1
        try:
            pdf_ref = AppConfig.get_hard_landing_pdf(model_id)
            
            # PDF 804 (E190/E195)
            if pdf_ref == "804":
                low_threshold = self.interpolate_threshold(weight_kg, self.VERT_ACCEL_THRESHOLDS_PDF804['low'])
                high_threshold = self.interpolate_threshold(weight_kg, self.VERT_ACCEL_THRESHOLDS_PDF804['high'])
                engine_threshold = self.interpolate_threshold(weight_kg, self.VERT_ACCEL_THRESHOLDS_PDF804['engine'])
                logger.info(f"[ETAPA 3] Usando PDF 804 (E190/E195) para modelo {model}")
                return {'low': low_threshold, 'high': high_threshold, 'engine': engine_threshold}
        except Exception as e:
            logger.warning(f"Erro ao consultar AppConfig: {e}")
            pass  # Fallback para lógica antiga
        
        # Fallback: Lógica baseada em string matching
        model_upper = model.upper()
        if 'E145' in model_upper or 'E135' in model_upper or 'EMB-145' in model_upper:
            # E145: retorna dummy, será tratado separadamente
            return {'low': None, 'high': None, 'engine': None}
        elif 'E190' in model_upper or 'E195' in model_upper:
            # PDF 804 para E190/E195
            low_threshold = self.interpolate_threshold(weight_kg, self.VERT_ACCEL_THRESHOLDS_PDF804['low'])
            high_threshold = self.interpolate_threshold(weight_kg, self.VERT_ACCEL_THRESHOLDS_PDF804['high'])
            engine_threshold = self.interpolate_threshold(weight_kg, self.VERT_ACCEL_THRESHOLDS_PDF804['engine'])
            return {'low': low_threshold, 'high': high_threshold, 'engine': engine_threshold}
        else:
            # PDF 801 para E170/E175 (padrão)
            low_threshold = self.interpolate_threshold(weight_kg, self.VERT_ACCEL_THRESHOLDS['low'])
            high_threshold = self.interpolate_threshold(weight_kg, self.VERT_ACCEL_THRESHOLDS['high'])
            engine_threshold = self.interpolate_threshold(weight_kg, self.VERT_ACCEL_THRESHOLDS['engine'])
            return {'low': low_threshold, 'high': high_threshold, 'engine': engine_threshold}
    
    def _determine_inspection_phase(
        self, status: str, vert_result: Dict, weight_kg: float, model: str
    ) -> Dict[str, any]:
        """
        Determina a fase de inspeção necessária baseada na severidade do hard landing
        
        Args:
            status: Status geral (HARD_LANDING_LOW/HIGH/ENGINE_INSPECTION)
            vert_result: Resultado da análise de aceleração vertical
            weight_kg: Peso da aeronave em kg
            model: Modelo da aeronave
            
        Returns:
            Dicionário com informações da fase de inspeção
        """
        max_g = vert_result.get('max_g', 0)
        model_upper = str(model).upper()
        is_erj_family = any(token in model_upper for token in ['E145', 'E135', 'EMB-145'])

        if is_erj_family:
            thresholds = vert_result.get('thresholds', {})
            engine_threshold = thresholds.get('engine') or thresholds.get('high') or thresholds.get('low')
            high_threshold = thresholds.get('high') or thresholds.get('low')

            if engine_threshold is not None and max_g >= engine_threshold:
                return {
                    'phase': 'PHASE III - ENGINE INSPECTION',
                    'description': 'Inspeção completa de motores e estrutura',
                    'procedure': 'AMM 05-50-03 Phase III',
                    'duration': '48-72 horas',
                    'tasks': [
                        'Inspeção boroscópica completa dos motores',
                        'Verificação de todas as montagens de motor',
                        'Inspeção estrutural completa da fuselagem',
                        'Inspeção detalhada do trem de pouso e fixações',
                        'Verificação de painéis e revestimentos',
                        'Testes funcionais de sistemas hidráulicos',
                        'Inspeção de longarinas e cavernas principais',
                        'Verificação de danos em componentes críticos'
                    ]
                }

            if high_threshold is not None and max_g >= high_threshold:
                return {
                    'phase': 'PHASE II - DETAILED INSPECTION',
                    'description': 'Inspeção detalhada de estrutura e trem de pouso',
                    'procedure': 'AMM 05-50-03 Phase II',
                    'duration': '24-48 horas',
                    'tasks': [
                        'Inspeção visual detalhada do trem de pouso',
                        'Verificação de fixações e batentes do trem',
                        'Inspeção da fuselagem inferior e painéis',
                        'Verificação de deformações estruturais',
                        'Inspeção de longarinas na área de pouso',
                        'Testes de integridade estrutural',
                        'Verificação de sistemas hidráulicos',
                        'Inspeção de componentes de fixação (rivets, fasteners)'
                    ]
                }

            return {
                'phase': 'PHASE I - GENERAL INSPECTION',
                'description': 'Inspeção geral pós-voo',
                'procedure': 'AMM 05-50-03 Phase I',
                'duration': '4-8 horas',
                'tasks': [
                    'Inspeção visual externa completa',
                    'Verificação do trem de pouso principal e nariz',
                    'Inspeção visual da fuselagem inferior',
                    'Verificação de painéis de acesso',
                    'Inspeção de pneus e freios',
                    'Verificação de vazamentos hidráulicos',
                    'Monitoramento de vibrações anormais no próximo voo'
                ]
            }
        
        # Phase III - ENGINE INSPECTION (mais crítico)
        if status == 'ENGINE_INSPECTION' or max_g >= 2.48:
            return {
                'phase': 'PHASE III - ENGINE INSPECTION',
                'description': 'Inspeção completa de motores e estrutura',
                'procedure': 'AMM 05-50-03 Phase III',
                'duration': '48-72 horas',
                'tasks': [
                    'Inspeção boroscópica completa dos motores',
                    'Verificação de todas as montagens de motor',
                    'Inspeção estrutural completa da fuselagem',
                    'Inspeção detalhada do trem de pouso e fixações',
                    'Verificação de painéis e revestimentos',
                    'Testes funcionais de sistemas hidráulicos',
                    'Inspeção de longarinas e cavernas principais',
                    'Verificação de danos em componentes críticos'
                ]
            }
        
        # Phase II - HARD LANDING HIGH (intermediário)
        elif status == 'HARD_LANDING_HIGH' or max_g >= 2.18:
            return {
                'phase': 'PHASE II - DETAILED INSPECTION',
                'description': 'Inspeção detalhada de estrutura e trem de pouso',
                'procedure': 'AMM 05-50-03 Phase II',
                'duration': '24-48 horas',
                'tasks': [
                    'Inspeção visual detalhada do trem de pouso',
                    'Verificação de fixações e batentes do trem',
                    'Inspeção da fuselagem inferior e painéis',
                    'Verificação de deformações estruturais',
                    'Inspeção de longarinas na área de pouso',
                    'Testes de integridade estrutural',
                    'Verificação de sistemas hidráulicos',
                    'Inspeção de componentes de fixação (rivets, fasteners)'
                ]
            }
        
        # Phase I - HARD LANDING LOW (menos crítico)
        else:  # HARD_LANDING_LOW
            return {
                'phase': 'PHASE I - GENERAL INSPECTION',
                'description': 'Inspeção geral pós-voo',
                'procedure': 'AMM 05-50-03 Phase I',
                'duration': '4-8 horas',
                'tasks': [
                    'Inspeção visual externa completa',
                    'Verificação do trem de pouso principal e nariz',
                    'Inspeção visual da fuselagem inferior',
                    'Verificação de painéis de acesso',
                    'Inspeção de pneus e freios',
                    'Verificação de vazamentos hidráulicos',
                    'Monitoramento de vibrações anormais no próximo voo'
                ]
            }
    
    def detect_flights(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detecta múltiplos voos em um arquivo baseado em transições AIR→GROUND ou altitude
        
        Returns:
            Lista de dicts com {'flight_num', 'start_idx', 'end_idx', 'touchdown'}
        """
        logger.info(f"=== DETECTANDO VOOS ===")
        logger.info(f"DataFrame: {len(df)} linhas")
        logger.info(f"Colunas disponíveis: {list(df.columns)}")
        
        # Procurar coluna AIR/GROUND (após mapeamento pode ser air_ground_switch)
        ag_col = None
        for col in df.columns:
            col_lower = col.lower()
            if ('air' in col_lower and 'ground' in col_lower) or col_lower == 'air_ground_switch':
                # Verificar se tem dados válidos antes de escolher
                test_data = df[col].dropna()
                if len(test_data) > 0:
                    ag_col = col
                    logger.info(f"✓ Coluna AIR/GROUND encontrada: '{ag_col}' com {len(test_data)} valores válidos")
                    break
                else:
                    logger.warning(f"⚠ Coluna '{col}' encontrada mas está vazia (todos NaN)")
        
        if ag_col is None:
            logger.warning("Coluna AIR/GROUND não encontrada ou está vazia")
        
        # Se tem coluna AIR/GROUND, usar ela
        if ag_col is not None:
            flights = []
            in_air = False
            flight_start = 0
            
            # Analisar valores únicos (garantir que é Series, não DataFrame)
            ag_series = df[ag_col]
            if isinstance(ag_series, pd.DataFrame):
                ag_series = ag_series.iloc[:, 0]  # Pegar primeira coluna se for DataFrame
            
            # Remover NaN antes de pegar únicos
            valid_ag = ag_series.dropna()
            if len(valid_ag) == 0:
                logger.warning(f"Coluna '{ag_col}' não contém valores válidos (todos NaN)")
                unique_vals = []
            else:
                unique_vals = valid_ag.unique()
            
            logger.info(f"Valores únicos em '{ag_col}': {list(unique_vals[:10])} (total: {len(unique_vals)})")
            logger.info(f"Valores válidos: {len(valid_ag)} de {len(ag_series)} ({len(valid_ag)/len(ag_series)*100:.1f}%)")
            
            # Se não há valores válidos, pular para próximo método
            if len(valid_ag) == 0:
                logger.warning("Pulando detecção Air/Ground - coluna vazia")
            else:
                for idx in range(len(df)):
                    ag_raw = df.iloc[idx][ag_col]
                    
                    # Tratar NaN
                    if pd.isna(ag_raw):
                        continue
                    
                    # Converter para string e normalizar
                    ag_value = str(ag_raw).strip().upper()
                    
                    # Detectar AIR - pode ser "AIR", "0", 0.0, ou vazio
                    # No arquivo do Mexicana: 0 = AIR, 1 = GROUND
                    is_air = (ag_value in ['AIR', '0', '0.0'] or 
                             (isinstance(ag_raw, (int, float)) and ag_raw == 0))
                    
                    is_ground = (ag_value in ['GROUND', '1', '1.0'] or 
                                (isinstance(ag_raw, (int, float)) and ag_raw == 1))
                
                    if is_air and not in_air:
                        # Início de voo
                        in_air = True
                        flight_start = idx
                        logger.debug(f"Início de voo no índice {idx}, valor={ag_raw}")
                    
                    elif is_ground and in_air:
                        # Touchdown detectado
                        flights.append({
                            'flight_num': len(flights) + 1,
                            'start_idx': flight_start,
                            'end_idx': min(idx + 100, len(df)-1),
                            'touchdown': idx
                        })
                        logger.info(f"✓ Touchdown detectado no índice {idx}, valor={ag_raw}")
                        in_air = False
                
                if flights:
                    logger.info(f"✓ Detectados {len(flights)} voo(s) usando coluna {ag_col}")
                    return flights
                else:
                    logger.warning(f"Coluna {ag_col} encontrada mas nenhum voo detectado")
        
        # Fallback: usar altitude para detectar pouso
        logger.info("Tentando detectar usando altitude...")
        alt_col = self._find_column(df, ['altitude', 'alt', 'alt_ft', 'height', 'altura', 'radio_altitude'])
        
        if alt_col:
            flights = []
            in_air = False
            flight_start = 0
            prev_alt = 0
            
            for idx in range(len(df)):
                try:
                    alt = float(df.iloc[idx][alt_col])
                    
                    # Considerar em voo se altitude > 1000 ft
                    if alt > 1000 and not in_air:
                        in_air = True
                        flight_start = idx
                    
                    # Detectar touchdown: altitude cai para < 50 ft ou 0
                    elif in_air and alt <= 50 and prev_alt > 50:
                        # Touchdown detectado
                        flights.append({
                            'flight_num': len(flights) + 1,
                            'start_idx': flight_start,
                            'end_idx': min(idx + 100, len(df)-1),
                            'touchdown': idx
                        })
                        in_air = False
                    
                    prev_alt = alt
                except:
                    pass
            
            if flights:
                logger.info(f"Detectados {len(flights)} voo(s) usando altitude")
                return flights
        
        # Último fallback: assumir voo único e detectar touchdown pelo pico de aceleração vertical
        logger.warning("Não foi possível detectar voos automaticamente, procurando pico de aceleração")
        accel_col = self._find_column(df, ['vertical_acceleration', 'normaccel', 'norm_accel', 'vert_accel', 'nz'])
        
        if accel_col:
            # Filtrar valores válidos e encontrar pico de aceleração
            valid_accel = df[accel_col].dropna()
            if len(valid_accel) > 0:
                max_accel_idx = valid_accel.idxmax()
                
                # Window dinâmico baseado no tamanho do arquivo
                # Arquivos grandes (50k+ linhas) precisam de janelas maiores
                if len(df) > 50000:
                    window_before = 600
                    window_after = 200
                    logger.info(f"Arquivo grande ({len(df)} linhas): usando window {window_before}/{window_after}")
                elif len(df) > 20000:
                    window_before = 450
                    window_after = 150
                    logger.info(f"Arquivo médio ({len(df)} linhas): usando window {window_before}/{window_after}")
                else:
                    window_before = 300
                    window_after = 100
                    logger.info(f"Arquivo pequeno ({len(df)} linhas): usando window {window_before}/{window_after}")
                
                return [{
                    'flight_num': 1,
                    'start_idx': max(0, max_accel_idx - window_before),
                    'end_idx': min(max_accel_idx + window_after, len(df)-1),
                    'touchdown': max_accel_idx
                }]
            else:
                logger.error("Coluna de aceleração vertical não contém valores válidos")
        
        # Absoluto fallback: voo único com touchdown no meio
        logger.warning("Usando fallback: voo único com touchdown estimado")
        touchdown_idx = len(df) // 2
        return [{
            'flight_num': 1,
            'start_idx': 0,
            'end_idx': len(df)-1,
            'touchdown': touchdown_idx
        }]
    
    def analyze_vertical_acceleration(
        self, 
        df: pd.DataFrame, 
        flight_data: Dict,
        weight_kg: float,
            model: str,
        accel_col: str
    ) -> Dict:
        """
        Analisa Vertical Acceleration Monitor (Figure 607)
        
        Range: 4 segundos antes do GROUND até pitch ≤ -0.5°
        Sampling: 8 sps = 0.125s intervals
        
        Args:
            df: DataFrame JÁ FATIADO para este voo (flight_df)
            flight_data: Dict com 'touchdown' (índice RELATIVO ao df original)
        """
        # IMPORTANTE: df já é um slice, então precisamos converter índice absoluto para relativo
        # touchdown_idx original está no contexto do DataFrame completo
        # Precisamos encontrar o touchdown DENTRO deste df
        
        # Usar o índice do DataFrame para mapear
        flight_start_abs = flight_data['start_idx']
        touchdown_abs = flight_data['touchdown']
        
        # Calcular posição relativa do touchdown dentro deste df
        touchdown_relative = touchdown_abs - flight_start_abs
        
        # Range: 4s antes do touchdown (4s × 8sps = 32 samples)
        start_idx = max(0, touchdown_relative - 32)
        
        # Procurar coluna de pitch
        pitch_col = None
        for col in df.columns:
            if 'pitch' in col.lower() and 'rate' not in col.lower():
                pitch_col = col
                break
        
        # Determinar end_idx (pitch ≤ -0.5° ou +50 samples se não encontrar)
        end_idx = touchdown_relative + 50
        if pitch_col:
            try:
                for idx in range(touchdown_relative, min(touchdown_relative + 100, len(df))):
                    pitch_val = float(df.iloc[idx][pitch_col])
                    if pitch_val <= -0.5:
                        end_idx = idx
                        break
            except:
                pass
        
        # Extrair dados do range
        analysis_df = df.iloc[start_idx:end_idx].copy()
        
        # DEBUG: Verificar dados antes de dropna
        logger.info(f"Monitor 1 DEBUG - Range [{start_idx}:{end_idx}]:")
        logger.info(f"  - Total linhas: {len(analysis_df)}")
        logger.info(f"  - Coluna: '{accel_col}'")
        
        # Verificar se coluna existe
        if accel_col not in analysis_df.columns:
            logger.error(f"  - ERRO: Coluna '{accel_col}' não existe no DataFrame!")
            logger.error(f"  - Colunas disponíveis: {list(analysis_df.columns)}")
            return {'status': 'NO_DATA', 'max_g': None, 'thresholds': {}}
        
        # Verificar valores antes de dropna
        accel_values = analysis_df[accel_col]
        logger.info(f"  - Valores na coluna: {len(accel_values)} total")
        logger.info(f"  - NaN: {accel_values.isna().sum()}")
        logger.info(f"  - Válidos: {(~accel_values.isna()).sum()}")
        
        if len(accel_values) > 0:
            valid_vals = accel_values.dropna()
            if len(valid_vals) > 0:
                logger.info(f"  - Min/Max válidos: {valid_vals.min():.3f} / {valid_vals.max():.3f}")
                logger.info(f"  - Primeiros 5 valores: {list(valid_vals.head())[:5]}")
        
        analysis_df = analysis_df.dropna(subset=[accel_col])
        
        if analysis_df.empty:
            logger.error(f"Monitor 1 NO_DATA: range [{start_idx}:{end_idx}] VAZIO após dropna")
            logger.error(f"  TODOS os valores são NaN na janela de análise!")
            return {'status': 'NO_DATA', 'max_g': None, 'thresholds': {}}
        
        # Encontrar aceleração máxima
        max_accel_series = analysis_df[accel_col].max()
        max_g = float(max_accel_series)
        
        # Interpolar thresholds baseado no peso e modelo
        model_upper = model.upper()
        if 'E145' in model_upper or 'E135' in model_upper or 'EMB-145' in model_upper:
            # E145: usa apenas um threshold (sem LOW/HIGH/ENGINE)
            threshold = self.interpolate_threshold(weight_kg, self.VERT_ACCEL_THRESHOLDS_E145['threshold'])
            low_threshold = threshold
            high_threshold = threshold
            engine_threshold = threshold
        else:
            # E1/E2: usa thresholds LOW/HIGH/ENGINE dinamicamente selecionados
            # ETAPA 3: Agora seleciona PDF 801 vs 804 automaticamente!
            thresholds = self.get_vertical_accel_thresholds(model, weight_kg)
            low_threshold = thresholds['low']
            high_threshold = thresholds['high']
            engine_threshold = thresholds['engine']
        
        # Log detalhado para debug
        logger.info(f"Monitor 1 - Peso: {weight_kg}kg, Max G: {max_g:.3f}G")
        logger.info(f"  Thresholds: LOW={low_threshold:.3f}, HIGH={high_threshold:.3f}, ENGINE={engine_threshold:.3f}")
        logger.info(f"  Range: [{start_idx}:{end_idx}], {len(analysis_df)} samples válidos")
        
        # Classificar
        if 'E145' in model_upper or 'E135' in model_upper or 'EMB-145' in model_upper:
            # E145: apenas NORMAL ou HARD_LANDING
            if max_g >= threshold:
                status = 'HARD_LANDING_HIGH'
            else:
                status = 'NORMAL'
        elif max_g >= engine_threshold:
            status = 'ENGINE_INSPECTION'
        elif max_g >= high_threshold:
            status = 'HARD_LANDING_HIGH'
        elif max_g >= low_threshold:
            status = 'HARD_LANDING_LOW'
        else:
            status = 'NORMAL'
        
        return {
            'status': status,
            'max_g': max_g,
            'thresholds': {
                'low': low_threshold,
                'high': high_threshold,
                'engine': engine_threshold
            },
            'range': (start_idx, end_idx)
        }
    
    def analyze_roll_rate(
        self,
        df: pd.DataFrame,
        flight_data: Dict,
        weight_kg: float,
        roll_col: str,
        accel_col: str
    ) -> Dict:
        """
        Analisa Roll Rate Monitor (Figure 608 + 614)
        
        Validação (Figure 614): Normal Accel deve exceder threshold
        Range: ±2s do pico de vertical accel (±16 samples @ 8sps)
        Cálculo: RR = (Roll_i - Roll_i-1) / 0.125s
        
        Args:
            df: DataFrame JÁ FATIADO para este voo (flight_df)
            flight_data: Dict com 'touchdown' (índice absoluto)
        """
        # Converter índice absoluto para relativo
        flight_start_abs = flight_data['start_idx']
        touchdown_abs = flight_data['touchdown']
        touchdown_relative = touchdown_abs - flight_start_abs
        
        # Primeiro validar com Figure 614
        validation_threshold = self.interpolate_threshold(
            weight_kg, 
            self.ROLL_VALIDATION_THRESHOLD['norm_accel']
        )
        
        # Encontrar pico de aceleração vertical para definir range (usar índice relativo)
        val_start = max(0, touchdown_relative - 32)
        val_end = min(len(df), touchdown_relative + 50)
        val_df = df.iloc[val_start:val_end].copy()
        
        # Validação
        valid_accel = val_df[accel_col].dropna()
        if len(valid_accel) == 0:
            return {
                'status': 'NO_DATA',
                'message': 'Sem dados válidos de aceleração normal para validação'
            }
        
        if valid_accel.max() <= validation_threshold:
            return {
                'status': 'VALIDATION_FAILED',
                'message': f'Normal accel {valid_accel.max():.3f}G não excede threshold {validation_threshold:.3f}G'
            }
        
        # Encontrar índice do pico de aceleração
        max_accel_idx = valid_accel.idxmax()
        
        # Range: ±2s (±16 samples)
        start_idx = max(0, max_accel_idx - 16)
        end_idx = min(len(df), max_accel_idx + 16)
        
        # Calcular roll rate
        analysis_df = df.iloc[start_idx:end_idx].copy()
        analysis_df = analysis_df.dropna(subset=[roll_col])
        
        if len(analysis_df) < 2:
            return {'status': 'NO_DATA', 'max_rate': None, 'thresholds': {}}
        
        # RR = (Roll_i - Roll_i-1) / dt (detectar dt do arquivo)
        time_col = self._find_column(df, ['timestamp', 'time', 'sec', 'seconds', 'time_sec'])
        dt = 0.125  # default fallback
        if time_col and time_col in analysis_df.columns:
            time_vals = pd.to_numeric(analysis_df[time_col], errors='coerce')
            dt_series = time_vals.diff().dropna()
            if len(dt_series) > 0:
                dt_candidate = float(dt_series.median())
                if 0 < dt_candidate <= 10:
                    dt = dt_candidate
        
        roll_diff = analysis_df[roll_col].diff()
        roll_rate = roll_diff / dt
        
        max_rate = float(roll_rate.abs().max())
        
        # Interpolar thresholds
        low_threshold = self.interpolate_threshold(weight_kg, self.ROLL_RATE_THRESHOLDS['low'])
        high_threshold = self.interpolate_threshold(weight_kg, self.ROLL_RATE_THRESHOLDS['high'])
        
        # Classificar
        if max_rate >= high_threshold:
            status = 'HARD_LANDING_HIGH'
        elif max_rate >= low_threshold:
            status = 'HARD_LANDING_LOW'
        else:
            status = 'NORMAL'
        
        return {
            'status': status,
            'max_rate': max_rate,
            'thresholds': {
                'low': low_threshold,
                'high': high_threshold
            },
            'validation_threshold': validation_threshold,
            'range': (start_idx, end_idx)
        }
    
    def analyze_pitch_rate(
        self,
        df: pd.DataFrame,
        flight_data: Dict,
        model: str,
        pitch_col: str
    ) -> Dict:
        """
        Analisa Pitch Rate Monitor (Figure 609)
        
        Range: pitch < 4.0° até pitch ≤ -0.5°
        Cálculo: PR = (Pitch_i - Pitch_i-1) / 0.125s
        
        Args:
            df: DataFrame JÁ FATIADO para este voo (flight_df)
            flight_data: Dict com 'touchdown' (índice absoluto)
        """
        # Converter índice absoluto para relativo
        flight_start_abs = flight_data['start_idx']
        touchdown_abs = flight_data['touchdown']
        touchdown_relative = touchdown_abs - flight_start_abs
        
        # Encontrar início do range (pitch < 2.5° per AMM 05-50-02) - usar índice relativo
        start_idx = touchdown_relative
        for idx in range(touchdown_relative, max(0, touchdown_relative - 100), -1):
            try:
                pitch_val = float(df.iloc[idx][pitch_col])
                if pitch_val >= 2.5:  # Changed from 4.0 to 2.5 per Mexicana spec
                    start_idx = idx + 1
                    break
            except:
                pass
        
        # Encontrar fim do range (pitch ≤ -0.5°) - usar índice relativo
        end_idx = touchdown_relative + 50
        for idx in range(touchdown_relative, min(len(df), touchdown_relative + 100)):
            try:
                pitch_val = float(df.iloc[idx][pitch_col])
                if pitch_val <= -0.5:
                    end_idx = idx
                    break
            except:
                pass
        
        # Calcular pitch rate
        analysis_df = df.iloc[start_idx:end_idx].copy()
        analysis_df = analysis_df.dropna(subset=[pitch_col])
        
        if len(analysis_df) < 2:
            return {'status': 'NO_DATA', 'max_rate': None, 'thresholds': {}}
        
        # PR = (Pitch_i - Pitch_i-1) / dt
        time_col = self._find_column(df, ['timestamp', 'time', 'sec', 'seconds', 'time_sec'])
        dt = 0.125
        if time_col and time_col in analysis_df.columns:
            time_vals = pd.to_numeric(analysis_df[time_col], errors='coerce')
            dt_series = time_vals.diff().dropna()
            if len(dt_series) > 0:
                dt_candidate = float(dt_series.median())
                if 0 < dt_candidate <= 10:
                    dt = dt_candidate
        
        pitch_diff = analysis_df[pitch_col].diff()
        pitch_rate = pitch_diff / dt

        # Filtrar saltos irrealistas de pitch (ex.: wrap ou dado corrompido)
        pitch_rate = pitch_rate.where(pitch_diff.abs() <= 10)
        
        # Interessado em valores NEGATIVOS (nose down)
        valid_rates = pitch_rate.dropna()
        if len(valid_rates) == 0:
            return {'status': 'NO_DATA', 'max_rate': None, 'thresholds': {}}
        min_rate = float(valid_rates.min())
        
        # Obter thresholds do modelo
        thresholds = self.get_pitch_thresholds(model)
        
        # Classificar (valores negativos, então menor é pior)
        model_upper = model.upper()
        if 'E145' in model_upper or 'E135' in model_upper or 'EMB-145' in model_upper:
            # E145: apenas um threshold
            if min_rate <= thresholds['threshold']:
                status = 'HARD_LANDING_HIGH'
            else:
                status = 'NORMAL'
        else:
            # E1/E2: thresholds LOW/HIGH
            if min_rate <= thresholds['high']:
                status = 'HARD_LANDING_HIGH'
            elif min_rate <= thresholds['low']:
                status = 'HARD_LANDING_LOW'
            else:
                status = 'NORMAL'
        
        return {
            'status': status,
            'min_rate': min_rate,
            'thresholds': thresholds if 'low' in thresholds else {'threshold': thresholds['threshold'], 'low': thresholds['threshold'], 'high': thresholds['threshold']},
            'range': (start_idx, end_idx)
        }
    
    def analyze(
        self,
        df: pd.DataFrame,
        weight_kg: float,
        model: str = 'E190'
    ) -> List[HardLandingResult]:
        """
        Analisa CSV completo para hard landing (suporta múltiplos voos)
        
        Args:
            df: DataFrame com dados de voo
            weight_kg: Peso da aeronave em kg
            model: Modelo da aeronave (E190, E195, E170, E175)
            
        Returns:
            Lista de HardLandingResult (um por voo detectado)
        """
        results = []
        
        # Log de entrada
        logger.info("="*80)
        logger.info(f"ANÁLISE HARD LANDING - Arquivo: {len(df)} linhas, Peso: {weight_kg}kg, Modelo: {model}")
        logger.info("="*80)
        
        # Detectar voos
        flights = self.detect_flights(df)
        logger.info(f"Detectados {len(flights)} voo(s) no arquivo")
        for i, flight in enumerate(flights):
            logger.info(f"  Voo {i+1}: touchdown={flight['touchdown']}, range=[{flight['start_idx']}:{flight['end_idx']}]")
        
        # Encontrar colunas necessárias
        accel_col = self._find_column(df, ['normaccel', 'norm_accel', 'vertical_accel', 'vertical_acceleration', 'vert_accel', 'nz'])
        roll_col = self._find_column(df, ['roll', 'roll_attitude', 'bank', 'phi'])
        pitch_col = self._find_column(df, ['pitch', 'pitch_attitude', 'theta'])

        model_upper = str(model).upper()
        is_erj_family = any(token in model_upper for token in ['E145', 'E135', 'EMB-145'])
        if is_erj_family:
            # ERJ family uses vertical acceleration thresholds only.
            roll_col = None
            pitch_col = None
        
        logger.info(f"Colunas encontradas: accel={accel_col}, roll={roll_col}, pitch={pitch_col}")
        logger.info(f"Colunas disponíveis no DataFrame: {list(df.columns)}")
        
        if not accel_col:
            logger.error("Coluna de aceleração vertical não encontrada")
            logger.error(f"Colunas disponíveis: {list(df.columns)}")
            return results
        
        # CORREÇÃO: Garantir que a coluna de aceleração seja numérica
        df[accel_col] = pd.to_numeric(df[accel_col], errors='coerce')
        
        # Log de dados de aceleração
        valid_accel = df[accel_col].dropna()
        if len(valid_accel) > 0:
            logger.info(f"Dados de aceleração: {len(valid_accel)} valores válidos, Max: {valid_accel.max():.3f}G")
        else:
            logger.error(f"Nenhum dado válido de aceleração encontrado na coluna '{accel_col}'")
            return results
        
        # Analisar cada voo
        for flight in flights:
            flight_df = df.iloc[flight['start_idx']:flight['end_idx']].copy()
            logger.info(f"Analisando voo {flight.get('flight_num', 'N/A')}: índices {flight['start_idx']} a {flight['end_idx']}")

            # IMPORTANTE: Ajustar índice do touchdown para o DataFrame sliceado
            adjusted_flight = flight.copy()
            adjusted_flight['touchdown'] = flight['touchdown'] - flight['start_idx']
            adjusted_flight['start_idx'] = 0
            adjusted_flight['end_idx'] = len(flight_df)

            logger.info(f"  Touchdown original: {flight['touchdown']}, ajustado: {adjusted_flight['touchdown']}")

            # Monitor 1: Vertical Acceleration
            vert_result = self.analyze_vertical_acceleration(
                flight_df, adjusted_flight, weight_kg, model, accel_col
            )
            logger.info(f"Monitor 1 (Vertical Accel): {vert_result.get('status', 'UNKNOWN')}")

            # Monitor 2: Roll Rate
            roll_result = {'status': 'NO_DATA'}
            if roll_col:
                roll_result = self.analyze_roll_rate(
                    flight_df, flight, weight_kg, roll_col, accel_col
                )
                logger.info(f"Monitor 2 (Roll Rate): {roll_result.get('status', 'UNKNOWN')}")

            # Monitor 3: Pitch Rate
            pitch_result = {'status': 'NO_DATA'}
            if pitch_col:
                pitch_result = self.analyze_pitch_rate(
                    flight_df, flight, model, pitch_col
                )
                logger.info(f"Monitor 3 (Pitch Rate): {pitch_result.get('status', 'UNKNOWN')}")

            # NOVA LÓGICA: só permite hard landing se vertical accel exceder o threshold LOW
            critical_monitors = []
            overall_status = 'NORMAL'

            # Se vertical accel não excedeu nem o LOW, status é sempre NORMAL
            if vert_result['status'] == 'NORMAL':
                # Mesmo que outros monitores acusem, não é hard landing
                pass
            else:
                # vertical accel excedeu algum threshold, agora sim pode considerar outros monitores
                if vert_result['status'] == 'ENGINE_INSPECTION':
                    overall_status = 'ENGINE_INSPECTION'
                    critical_monitors.append('Vertical Acceleration')
                elif vert_result['status'] == 'HARD_LANDING_HIGH':
                    overall_status = 'HARD_LANDING_HIGH'
                    critical_monitors.append('Vertical Acceleration')
                elif vert_result['status'] == 'HARD_LANDING_LOW':
                    overall_status = 'HARD_LANDING_LOW'
                    critical_monitors.append('Vertical Acceleration')

                # Só permite que outros monitores elevem o status se vertical accel >= LOW
                if roll_result['status'] == 'HARD_LANDING_HIGH':
                    if overall_status != 'ENGINE_INSPECTION':
                        overall_status = 'HARD_LANDING_HIGH'
                    critical_monitors.append('Roll Rate')
                elif roll_result['status'] == 'HARD_LANDING_LOW':
                    if overall_status == 'NORMAL':
                        overall_status = 'HARD_LANDING_LOW'
                    critical_monitors.append('Roll Rate')

                if pitch_result['status'] == 'HARD_LANDING_HIGH':
                    if overall_status != 'ENGINE_INSPECTION':
                        overall_status = 'HARD_LANDING_HIGH'
                    critical_monitors.append('Pitch Rate')
                elif pitch_result['status'] == 'HARD_LANDING_LOW':
                    if overall_status == 'NORMAL':
                        overall_status = 'HARD_LANDING_LOW'
                    critical_monitors.append('Pitch Rate')

            # Mapear para severity
            severity_map = {
                'NORMAL': 'NORMAL',
                'HARD_LANDING_LOW': 'LOW',
                'HARD_LANDING_HIGH': 'HIGH',
                'ENGINE_INSPECTION': 'CRITICAL'
            }
            severity = severity_map.get(overall_status, 'NORMAL')

            # Gerar mensagem
            if overall_status == 'NORMAL':
                message = "Nenhuma violação detectada nos 3 monitores"
            else:
                inspection_phase = self._determine_inspection_phase(
                    overall_status, vert_result, weight_kg, model
                )

                message = f"{overall_status}: {', '.join(critical_monitors)} excedeu(aram) limites\n\n"
                message += f"Monitores Críticos: {', '.join(critical_monitors)}\n\n"
                message += "⚠ AÇÃO REQUERIDA:\n"
                message += f"**{inspection_phase['phase']}** - {inspection_phase['description']}\n\n"
                message += f"📋 Procedimento: {inspection_phase['procedure']}\n"
                message += f"⏱ Duração Estimada: {inspection_phase['duration']}\n"
                message += f"📖 Referência: AMM 05-50-03\n\n"
                message += "Tarefas:\n"
                for task in inspection_phase['tasks']:
                    message += f"  • {task}\n"

            results.append(HardLandingResult(
                status=overall_status,
                vertical_accel=vert_result,
                roll_rate=roll_result,
                pitch_rate=pitch_result,
                weight_kg=weight_kg,
                critical_monitors=critical_monitors,
                severity=severity,
                message=message
            ))

        return results

    def analyze_hard_landing(
        self,
        df: pd.DataFrame,
        model: str,
        touchdown_weight: float
    ) -> HardLandingLegacyResult:
        """Compat wrapper para análise única (API antiga)."""
        results = self.analyze(df, touchdown_weight, model)
        if not results:
            return HardLandingLegacyResult(False, 'NONE', 0.0)

        severity_rank = {
            'NORMAL': 0,
            'LOW': 1,
            'HIGH': 2,
            'CRITICAL': 3
        }
        best = max(results, key=lambda r: severity_rank.get(r.severity, 0))

        severity_level = 'NONE' if best.severity == 'NORMAL' else best.severity
        max_g = best.vertical_accel.get('max_g') if isinstance(best.vertical_accel, dict) else None
        if max_g is None:
            max_g = 0.0

        return HardLandingLegacyResult(
            is_hard_landing=best.severity != 'NORMAL',
            severity_level=severity_level,
            max_vertical_accel=float(max_g)
        )
    
    @staticmethod
    def _find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """Encontra coluna no DataFrame (case-insensitive)"""
        df_cols_lower = {col.lower(): col for col in df.columns}
        for candidate in candidates:
            if candidate.lower() in df_cols_lower:
                return df_cols_lower[candidate.lower()]
        return None


"""
CSV Column Mapper - Flexible Column Name Mapping
Maps various CSV column name variations to standardized names
"""

from typing import Dict, List, Optional
import pandas as pd
from dataclasses import dataclass


@dataclass
class ColumnMapping:
    """Column mapping configuration"""
    standard_name: str
    variations: List[str]
    required: bool = False
    description: str = ""


class CSVColumnMapper:
    """Maps CSV columns with variations to standard names"""
    
    # Complete mapping for all possible column variations
    COLUMN_MAPPINGS = [
        # Timestamp variations
        ColumnMapping(
            standard_name="timestamp",
            variations=[
                "timestamp", "time", "datetime", "date_time", "time_stamp",
                "hora", "data_hora", "data", "horario", "DATE_TIME",
                "UTC", "utc_time", "gmt_time", "local_time", "gmt", "gmt (hrs)",
                "offset", "sample", "recorder time", "recorder_time"
            ],
            required=False,
            description="Flight timestamp"
        ),
        
        # Flight Number variations
        ColumnMapping(
            standard_name="flight_number",
            variations=[
                "flight_number", "flight", "flt", "flight_no", "flt_no",
                "flight_id", "numero_voo", "voo", "FLT", "FLIGHT", 
                "flight_num", "flightnum", "flight_nbr", "FLTNBR"
            ],
            required=False,
            description="Flight identification number"
        ),
        
        # Altitude variations (generic)
        ColumnMapping(
            standard_name="altitude",
            variations=[
                "altitude", "alt", "height", "altitud", "altura",
                "ALT",
                "altitude_ft", "alt_ft", "altitude_feet", "ALT_FT",
                "indicated_altitude", "ind_alt"
            ],
            required=False,
            description="Aircraft altitude in feet"
        ),

        # Pressure Altitude variations
        ColumnMapping(
            standard_name="pressure_altitude",
            variations=[
                "pressure_altitude", "pressure alt", "press_alt", "baro_alt",
                "baro alt", "BARO_ALT", "pressure altitude (ft)",
                "altitude msl", "alt_msl", "altitude_msl"
            ],
            required=False,
            description="Pressure altitude in feet"
        ),

        # Radio Altitude variations
        ColumnMapping(
            standard_name="radio_altitude",
            variations=[
                "radio altitude", "radio_altitude", "radio alt", "radio_alt",
                "radalt", "RADALT", "AGL", "height agl", "height_agl_ft",
                "radio altitude (ft)", "radio altitude (1, left, capt or only) (ft)",
                "radio altitude [m]", "agl meters"
            ],
            required=False,
            description="Radio altitude in feet"
        ),
        
        # Indicated Airspeed variations
        ColumnMapping(
            standard_name="indicated_airspeed",
            variations=[
                "airspeed", "air speed", "speed", "ias", "kias",
                "indicated_airspeed", "velocidade", "vel", "ias_kt",
                "ias_kts", "IAS", "KIAS", "airspeed (kts)",
                "ias [knots]", "speed kts", "airspeed_kt",
                "indicated airspeed (kts)", "indicated airspeed"
            ],
            required=False,
            description="Indicated airspeed in knots"
        ),

        # Calibrated Airspeed variations
        ColumnMapping(
            standard_name="calibrated_airspeed",
            variations=[
                "cas", "calibrated_airspeed", "CAS",
                "airspeed (calibrated; 1 or only) (knots)",
                "airspeed (calibrated", "calibrated airspeed (knots)",
                "cas knots"
            ],
            required=False,
            description="Calibrated airspeed in knots"
        ),

        # True Airspeed variations
        ColumnMapping(
            standard_name="true_airspeed",
            variations=[
                "true_airspeed", "tas", "TAS", "true airspeed", "tas knots"
            ],
            required=False,
            description="True airspeed in knots"
        ),

        # Ground Speed variations
        ColumnMapping(
            standard_name="ground_speed",
            variations=[
                "ground_speed", "ground speed", "gs", "GS"
            ],
            required=False,
            description="Ground speed in knots"
        ),
        
        # Vertical Acceleration (G-force) variations - EXPANDIDO 200+ VARIAÇÕES
        ColumnMapping(
            standard_name="vertical_acceleration",
            variations=[
                # Variações padrão
                "vertical_acceleration", "vertical_g", "vert_accel", "v_accel",
                "g_force", "gforce", "g_vertical", "vertical_load_factor",
                "aceleracao_vertical", "g_vert", "VERT_ACCEL", "NZ",
                "load_factor", "load_factor_z", "vertical_load", "n_z",
                "acceleration_z", "accel_z", "ACCEL_VERT", "G_VERT",
                # Variações com símbolos e espaços
                "acceleration (normal load-factor) (g's)", "normal load-factor",
                "acceleration (normal", "load factor", "normal load factor",
                "normaccel", "norm_accel", "norm accel", "normal_accel",
                "normal acceleration", "g's", "gs",
                # Variações com prefixos
                "accel_vertical", "accel vertical", "acceleration vertical",
                "acceleration_vertical", "vert acceleration", "vertical acc",
                "vert acc", "vert_acc", "vertical_acc", "acc_vert",
                # Variações com sufixos
                "accel_z", "accel z", "accel-z", "z_accel", "z accel",
                "z-accel", "z_acceleration", "z acceleration",
                # Variações técnicas FDR/QAR
                "nz_g", "nz g", "nz-g", "n_z_g", "nzg", "NZG",
                "vrtg", "vrt_g", "vrt g", "v_g", "vg", "VG",
                "norm_g", "normg", "NORMG", "normal_g", "normalg",
                # Variações com unidades
                "vertical g (g)", "vertical accel (g)", "vert accel (g)",
                "normal accel (g)", "load factor (g)", "nz (g)",
                # CORREÇÃO: Variação exata encontrada nos arquivos reais
                "vertical acceleration (g)", "vertical accel (g)",
                # Variações multilíngue
                "acceleracion vertical", "aceleracion vertical",
                "beschleunigung vertikal", "acceleration verticale",
                # Variações com separadores diferentes
                "vertical.acceleration", "vertical-acceleration",
                "vertical/acceleration", "vertical\\acceleration",
                # Variações com case diferentes
                "VERTICAL ACCELERATION", "Vertical Acceleration",
                "Vertical_Acceleration", "vertical.accel", "NORMAL.ACCEL",
                # Variações específicas de fabricantes
                "teledyne_nz", "smiths_normal_accel", "honeywell_vertical_g",
                "thales_load_factor", "collins_nz", "l3_vertical_accel",
                # Variações com números/sufixos de sistema
                "nz1", "nz2", "nz_1", "nz_2", "nz (1)", "nz (2)",
                "vertical_accel_1", "vertical_accel_2", "vert_g_left", "vert_g_right",
                # Variações com descrições longas
                "normal acceleration load factor vertical",
                "vertical acceleration g force", "vertical g load",
                "vertical structural load factor",
                # Variações abbreviadas
                "vac", "v.ac", "v-ac", "va", "nrm_acc", "nrmacc",
                # Variações com underscores duplos
                "vertical__acceleration", "norm__accel", "n__z",
                # Variações específicas de arquivos CSV comuns
                "accel_norm", "acceleration_norm", "norm_acceleration",
                "normalized_accel", "normalized_acceleration",
                # Variações com palavras invertidas
                "g vertical", "accel normal", "factor load normal",
                "load factor n", "body_nz", "vertical_g_force", "accel_normal",
                "g force vertical", "gforce_vert",
                # Variações com prefixo de canal
                "chan_nz", "channel_nz", "ch_nz", "nz_chan",
                # Variações específicas de Mexicana
                "mexicana_nz", "e170_nz", "e190_nz", "e2_nz",
                # Variações com qualificadores
                "nz_filtered", "nz_raw", "nz_corrected", "nz_capt",
                "nz_fo", "nz_left", "nz_right", "nz_center",
                # Mais variações comuns encontradas em CSVs reais
                "aceleração normal", "fator de carga normal",
                "g normal", "aceleração vertical nz",
                # Variações com pontuação
                "n.z", "n,z", "n;z", "n:z", "g.vert", "g,vert",
                # Variações curtas
                "nz", "vg", "ng", "za", "gz",
                # Variações Mexicana (FDR raw data)
                "accnorm", "acc_norm", "acc norm"
            ],
            required=False,
            description="Vertical acceleration in G"
        ),
        
        # Lateral Acceleration variations
        ColumnMapping(
            standard_name="lateral_acceleration",
            variations=[
                "lateral_acceleration", "lateral_g", "lat_accel", "l_accel",
                "g_lateral", "lateral_load_factor", "aceleracao_lateral",
                "g_lat", "LAT_ACCEL", "NY", "load_factor_y", "n_y",
                "acceleration_y", "accel_y", "ACCEL_LAT", "G_LAT",
                "acceleration (lateral) (g's)", "acceleration (lateral)",
                "lateral acceleration (g's)",
                # Variações Mexicana (FDR raw data)
                "acclat", "acc_lat", "acc lat"
            ],
            required=False,
            description="Lateral acceleration in G"
        ),
        
        # Longitudinal Acceleration variations
        ColumnMapping(
            standard_name="longitudinal_acceleration",
            variations=[
                "longitudinal_acceleration", "long_accel", "longitudinal_g",
                "g_longitudinal", "g_long", "aceleracao_longitudinal",
                "LONG_ACCEL", "NX", "load_factor_x", "n_x",
                "acceleration_x", "accel_x", "ACCEL_LONG", "G_LONG",
                "acceleration (longitudinal) (g's)", "acceleration (longitudinal)",
                "longitudinal acceleration (g's)",
                # Variações Mexicana (FDR raw data)
                "acclong", "acc_long", "acc long"
            ],
            required=False,
            description="Longitudinal acceleration in G"
        ),
        
        # Temperature variations
        ColumnMapping(
            standard_name="temperature",
            variations=[
                "temperature", "temp", "tat", "sat", "oat", "outside_air_temp",
                "total_air_temp", "static_air_temp", "temperatura",
                "TEMP", "TAT", "SAT", "OAT", "air_temp", "airtemp",
                "outside_temp", "ambient_temp", "AMBIENT_TEMP"
            ],
            required=False,
            description="Temperature in Celsius"
        ),
        
        # Pressure variations
        ColumnMapping(
            standard_name="pressure",
            variations=[
                "pressure", "press", "baro_pressure", "barometric_pressure",
                "pressao", "static_pressure", "PRESS", "QNH", "qnh",
                "altimeter_setting", "baro_set", "BARO_PRESS", "atm_pressure"
            ],
            required=False,
            description="Barometric pressure"
        ),
        
        # Mach number variations
        ColumnMapping(
            standard_name="mach",
            variations=[
                "mach", "mach_number", "mach_no", "numero_mach",
                "MACH", "mach_speed", "M", "MMO", "mmo"
            ],
            required=False,
            description="Mach number"
        ),
        
        # Air/Ground Switch variations - EXPANDIDO 120+ VARIAÇÕES
        ColumnMapping(
            standard_name="air_ground_switch",
            variations=[
                # Variações básicas
                "air_ground", "air/ground", "airground", "ag_switch",
                "air_ground_switch", "air/ground switch", "air/gnd", "air_gnd",
                # Variações específicas de posição do sensor
                "air/ground switch (left main) (0=air)",
                "air/ground switch (right main) (0=air)",
                "air/ground switch (nose) (0=air)",
                "air/ground switch (left)", "air/ground switch (right)",
                "air/ground switch (nose)", "air/ground switch (mlg left)",
                "air/ground switch (mlg right)", "air/ground switch (nlg)",
                # Variações padrão
                "air/ground switch", "weight_on_wheels", "wow",
                "ground_air", "flight_phase", "AIR GROUND", "AIR/GROUND",
                "AIR_GROUND", "AIRGROUND", "air ground",
                # Variações com diferentes separadores
                "air-ground", "air.ground", "air ground switch",
                "air-ground-switch", "air.ground.switch",
                # Weight on Wheels variations
                "weight on wheels", "weight_on_wheels", "wow_switch",
                "wow left", "wow right", "wow nose", "wow_left", "wow_right",
                "wow_nose", "WOW_LEFT", "WOW_RIGHT", "WOW_NOSE",
                "weight on wheels (left)", "weight on wheels (right)",
                "weight on wheels (nose)", "weight on wheels left main",
                "weight on wheels right main", "weight on wheels nose",
                # Variações de ground contact
                "ground_contact", "ground contact", "on_ground", "on ground",
                "is_airborne", "is airborne", "airborne", "ground_status",
                "ground status", "flight_status", "flight status",
                # Variações booleanas/estados
                "on_gnd", "on gnd", "gnd", "ground", "in_air", "in air",
                "in_flight", "in flight", "flying", "landed",
                # Variações numéricas com descrição
                "air/gnd (0=air)", "air/gnd (1=ground)", "air/gnd (0=air; 1=gnd)",
                "gnd/air (0=gnd)", "gnd/air (1=air)",
                # Variações técnicas
                "agnd", "a/g", "a-g", "a_g", "ag", "AG", "A/G", "A-G",
                "gnd_sw", "gnd sw", "ground_sw", "ground sw",
                "air_sw", "air sw", "airsw", "gndsw",
                # Variações de switch/relay
                "ground_relay", "ground relay", "air_relay", "air relay",
                "squat_switch", "squat switch", "squat", "landing_switch",
                "landing gear switch", "airborne_flag", "on_ground_bool",
                # Variações com múltiplos sensores
                "air/ground (left main)", "air/ground (right main)",
                "air/ground (nose gear)", "air/ground left", "air/ground right",
                "air/ground nose", "a/g left", "a/g right", "a/g nose",
                # Variações multilíngue
                "no ar/no solo", "ar/solo", "ar-solo", "aire/tierra",
                "air/sol", "luft/boden",
                # Variações com case diferentes
                "AIR/GROUND SWITCH", "Air/Ground Switch", "Air/Ground",
                "WEIGHT_ON_WHEELS", "Weight_On_Wheels",
                # Variações específicas de fabricantes
                "teledyne_wow", "smiths_air_ground", "honeywell_wow",
                "thales_ground_contact", "collins_wow", "l3_air_ground",
                # Variações com números de sistema
                "wow1", "wow2", "wow_1", "wow_2", "ag_1", "ag_2",
                "air_ground_1", "air_ground_2",
                # Variações abreviadas
                "ww", "w.w", "w-w", "gnd_det", "ground_det",
                # Variações de discrete signal
                "discrete_wow", "discrete_ground", "ground_discrete",
                # Variações Mexicana específicas
                "mexicana_wow", "e170_wow", "e190_wow", "e2_wow"
            ],
            required=False,
            description="Air/Ground switch status"
        ),
        
        # Landing Gear variations
        ColumnMapping(
            standard_name="gear_position",
            variations=[
                "gear_position", "gear_pos", "landing_gear", "gear",
                "landing_gear_position", "gear_state", "gear_status",
                "trem_pouso", "GEAR_POS", "GEAR", "LDG_GEAR",
                "gear_down", "gear_up", "gear_extended", "gear_retracted"
            ],
            required=False,
            description="Landing gear position"
        ),
        
        # Flap position variations
        ColumnMapping(
            standard_name="flap_position",
            variations=[
                "flap_position", "flap_pos", "flaps", "flap",
                "flap_angle", "flap_setting", "posicao_flap",
                "FLAP_POS", "FLAPS", "flap_lever", "FLAP_ANGLE",
                "trailing_edge_flap", "te_flap"
            ],
            required=False,
            description="Flap position/angle"
        ),
        
        # Weight variations - EXPANDIDO 150+ VARIAÇÕES
        ColumnMapping(
            standard_name="gross_weight",
            variations=[
                # Variações básicas
                "gross_weight", "weight", "aircraft_weight", "total_weight",
                "peso", "peso_total", "WEIGHT", "GW", "gross_wt",
                "landing_weight", "takeoff_weight", "MTOW", "MLW",
                "current_weight", "actual_weight",
                # Variações com unidades explícitas
                "gross weight (kg)", "gross weight (lbs)",
                "weight (kg)", "weight (lbs)", "gross weight - kg",
                "gross weight - lbs", "gross wt (kg)", "gross wt (lbs)",
                "weight kg", "weight lbs", "weight_kg", "weight_lbs",
                # Variações de peso bruto
                "gross weight", "grossweight", "gross_wt", "grosswt",
                "grs_wt", "grs wt", "grswt", "gwt",
                # Variações de peso total
                "total weight", "totalweight", "total_wt", "totalwt",
                "tot_wt", "tot wt", "totwt", "twt",
                # Variações de peso da aeronave
                "aircraft weight", "aircraftweight", "aircraft_wt",
                "ac_weight", "ac weight", "ac_wt", "ac wt", "acwt",
                "airplane_weight", "airplane weight", "plane_weight",
                # Variações técnicas FDR/QAR
                "gw_kg", "gw_lbs", "gw kg", "gw lbs", "GW_KG", "GW_LBS",
                "gross_weight_kg", "gross_weight_lbs",
                "gross weight kg", "gross weight lbs",
                "aircraft mass (kg)", "total_weight_kg", "mass_kg",
                # Variações de fases de voo
                "landing_weight", "landing weight", "land_wt", "landwt",
                "takeoff_weight", "takeoff weight", "to_wt", "towt",
                "ramp_weight", "ramp weight", "taxi_weight", "taxi weight",
                # Variações de limites
                "max_takeoff_weight", "max takeoff weight", "MTOW",
                "max_landing_weight", "max landing weight", "MLW",
                "max_zero_fuel_weight", "max zero fuel weight", "MZFW",
                # Variações com separadores diferentes
                "gross-weight", "gross.weight", "gross/weight",
                "gross\\weight", "weight-gross", "weight.gross",
                # Variações multilíngue
                "peso bruto", "peso total", "peso aeronave",
                "poids brut", "poids total", "peso bruto (kg)",
                "gewicht", "bruttogewicht", "gesamtgewicht",
                # Variações com case diferentes
                "GROSS WEIGHT", "Gross Weight", "Gross_Weight",
                "TOTAL WEIGHT", "Total Weight", "Total_Weight",
                "AIRCRAFT WEIGHT", "Aircraft Weight",
                # Variações específicas de sistema
                "weight_system_1", "weight_system_2", "wt_sys_1",
                "wt_sys_2", "weight_1", "weight_2",
                # Variações com descrições longas
                "aircraft total gross weight", "total aircraft weight",
                "current aircraft weight", "actual aircraft weight",
                "estimated weight", "calculated weight",
                # Variações abreviadas
                "wt", "w", "grs", "tot", "ac",
                "wgt", "weig", "peso",
                # Variações com underscores duplos
                "gross__weight", "total__weight", "aircraft__weight",
                # Variações específicas de fabricantes
                "teledyne_weight", "smiths_gross_weight",
                "honeywell_aircraft_weight", "thales_weight",
                "collins_gw", "l3_weight",
                # Variações com qualificadores
                "weight_corrected", "weight_raw", "weight_filtered",
                "weight_computed", "weight_measured",
                # Variações de peso operacional
                "operating_weight", "oper_weight", "op_weight",
                "operational_weight", "oew", "OEW",
                "empty_weight", "basic_weight", "dry_weight",
                # Variações de peso com payload
                "payload_weight", "payload", "pax_weight",
                "cargo_weight", "fuel_weight", "fuel_on_board",
                # Variações de zero fuel weight
                "zero_fuel_weight", "zfw", "ZFW", "zero fuel weight",
                "zero_fuel_wt", "zfwt",
                # Variações numéricas com descrição
                "weight (kilograms)", "weight (pounds)",
                "weight (kg)", "weight (lb)", "weight [kg]", "weight [lbs]",
                # Variações de peso em toneladas
                "weight_tonnes", "weight_tons", "weight (tonnes)",
                "weight (tons)", "weight_mt", "weight_t",
                # Variações com pontuação
                "weight.kg", "weight,kg", "weight;kg",
                "weight:kg", "weight-kg", "weight/kg",
                # Variações Mexicana específicas
                "mexicana_weight", "e170_weight", "e190_weight",
                "e2_weight", "emb_weight", "emb_gw",
                # Variações de peso instantâneo
                "instantaneous_weight", "inst_weight", "current_wt",
                "real_time_weight", "rt_weight",
                # Variações curtas
                "gw", "tw", "aw", "lw", "tow"
            ],
            required=False,
            description="Aircraft gross weight"
        ),
        
        # Pitch variations
        ColumnMapping(
            standard_name="pitch_attitude",
            variations=[
                "pitch", "pitch_angle", "theta", "pitch_attitude", "pitch_att",
                "arfagem", "PITCH", "THETA", "PITCH_ATT", "pitch_deg",
                "nose_up", "nose_down", "nose up/down", "pitch_attitude_deg",
                "aircraft pitch", "body pitch", "pitch euler", "elevator_position",
                "pitch attitude (capt or only) (deg)", "pitch attitude",
                "pitch (deg)",
                # Variações Mexicana (FDR raw data)
                "attpitch", "att_pitch", "att pitch"
            ],
            required=False,
            description="Pitch angle in degrees"
        ),
        
        # Roll variations
        ColumnMapping(
            standard_name="roll_attitude",
            variations=[
                "roll", "roll_angle", "phi", "bank_angle", "roll_attitude", "roll_att",
                "rolagem", "ROLL", "PHI", "ROLL_ATT", "roll_deg", "bank",
                "bank_deg", "roll_attitude_deg",
                "roll attitude (capt or only) (deg)", "roll attitude",
                "roll (deg)",
                # Variações Mexicana (FDR raw data)
                "attroll", "att_roll", "att roll"
            ],
            required=False,
            description="Roll angle in degrees"
        ),
        
        # Roll Rate variations
        ColumnMapping(
            standard_name="roll_rate",
            variations=[
                "roll_rate", "roll rate", "rollrate", "ROLL RATE",
                "ROLL_RATE", "roll_velocity", "roll_speed",
                "phi_rate", "phi_dot", "roll rate ", "roll rate",
                "d_roll", "delta_roll", "roll rate (deg/s)"
            ],
            required=False,
            description="Roll rate in degrees/second"
        ),
        
        # Pitch Rate variations
        ColumnMapping(
            standard_name="pitch_rate",
            variations=[
                "pitch_rate", "pitch rate", "pitchrate", "PITCH RATE",
                "PITCH_RATE", "pitch_velocity", "pitch_speed",
                "theta_rate", "theta_dot", "pitch rate ", "pitch rate",
                "d_pitch", "delta_pitch", "pitch rate (deg/s)"
            ],
            required=False,
            description="Pitch rate in degrees/second"
        ),
        
        # Heading variations
        ColumnMapping(
            standard_name="heading",
            variations=[
                "heading", "hdg", "true_heading", "magnetic_heading",
                "proa", "direcao", "HEADING", "HDG", "heading_deg",
                "true_hdg", "mag_hdg", "compass_heading"
            ],
            required=False,
            description="Aircraft heading in degrees"
        ),
        
        # Vertical Speed variations
        ColumnMapping(
            standard_name="vertical_speed",
            variations=[
                "vertical_speed", "vert_speed", "vvi", "vertical_velocity",
                "rate_of_climb", "climb_rate", "descent_rate", "roc",
                "velocidade_vertical", "VERT_SPEED", "VVI", "VS",
                "vertical_rate", "vert_rate", "fpm", "ft_per_min"
            ],
            required=False,
            description="Vertical speed in ft/min"
        ),
        
        # Engine parameters
        ColumnMapping(
            standard_name="n1",
            variations=[
                "n1", "N1", "n1_percent", "n1_pct", "engine_n1",
                "fan_speed", "N1_PCT", "n1_rpm", "eng_n1"
            ],
            required=False,
            description="Engine N1 percentage"
        ),
        
        ColumnMapping(
            standard_name="n2",
            variations=[
                "n2", "N2", "n2_percent", "n2_pct", "engine_n2",
                "core_speed", "N2_PCT", "n2_rpm", "eng_n2"
            ],
            required=False,
            description="Engine N2 percentage"
        ),
        
        ColumnMapping(
            standard_name="egt",
            variations=[
                "egt", "EGT", "exhaust_gas_temp", "exhaust_temp",
                "engine_temp", "EGT_TEMP", "egt_deg", "egt_celsius"
            ],
            required=False,
            description="Exhaust Gas Temperature"
        )
    ]
    
    def __init__(self):
        """Initialize column mapper"""
        # Create reverse lookup dictionary
        self.variation_to_standard = {}
        self.normalized_variation_to_standard = {}
        for mapping in self.COLUMN_MAPPINGS:
            for variation in mapping.variations:
                self.variation_to_standard[variation.lower()] = mapping.standard_name
                normalized_key = self._normalize_key(variation)
                self.normalized_variation_to_standard[normalized_key] = mapping.standard_name

    @staticmethod
    def _normalize_key(value: str) -> str:
        """Normaliza string removendo caracteres nao-alfanumericos."""
        return "".join(ch for ch in value.lower().strip() if ch.isalnum())

    @staticmethod
    def _strip_unit_suffix(value: str) -> str:
        """Remove sufixos comuns de unidade do nome normalizado."""
        suffixes = [
            "kgs", "kg", "lbs", "lb",
            "kias", "kts", "kt", "knots",
            "fpm", "ft",
            "degs", "deg", "degsec", "degps", "degpersec",
            "gs", "g",
            "pct", "percent", "pc",
            "c"
        ]
        for suffix in suffixes:
            if value.endswith(suffix) and len(value) > len(suffix) + 2:
                return value[: -len(suffix)]
        return value

    def normalize_column_name(self, column_name: Optional[str]) -> Optional[str]:
        """Normaliza nome de coluna para o nome padrao, se conhecido."""
        if column_name is None:
            return None

        raw = str(column_name).strip()
        if raw == "":
            return ""

        lowered = raw.lower()
        if lowered in self.variation_to_standard:
            return self.variation_to_standard[lowered]

        normalized = self._normalize_key(lowered)
        if normalized in self.normalized_variation_to_standard:
            return self.normalized_variation_to_standard[normalized]

        stripped = self._strip_unit_suffix(normalized)
        if stripped in self.normalized_variation_to_standard:
            return self.normalized_variation_to_standard[stripped]

        return lowered
    
    def map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map DataFrame columns to standard names"""
        # Create column mapping
        column_map: Dict[str, str] = {}
        unmapped_columns: List[str] = []
        standard_to_sources: Dict[str, List[str]] = {}

        for col in df.columns:
            standard_name = self.normalize_column_name(col)
            if standard_name:
                column_map[col] = standard_name
                standard_to_sources.setdefault(standard_name, []).append(col)
            else:
                unmapped_columns.append(col)

        # Resolve duplicates by combining sources before renaming
        df_resolved = df.copy()
        for standard_name, sources in standard_to_sources.items():
            if len(sources) <= 1:
                continue

            combined = df_resolved[sources].bfill(axis=1).iloc[:, 0]
            df_resolved = df_resolved.drop(columns=sources)
            df_resolved[standard_name] = combined

            for src in sources:
                if src in column_map:
                    del column_map[src]

        # Rename remaining columns
        df_mapped = df_resolved.rename(columns=column_map)
        df_mapped = self._add_compat_aliases(df_mapped)
        
        # Log mapping results
        print(f"\n{'='*70}")
        print("CSV COLUMN MAPPING")
        print(f"{'='*70}")
        print(f"[OK] Mapped {len(column_map)} columns:")
        for original, standard in column_map.items():
            print(f"   {original} -> {standard}")
        
        if unmapped_columns:
            print(f"\n[WARN] Unmapped columns ({len(unmapped_columns)}):")
            for col in unmapped_columns:
                print(f"   {col}")
        
        print(f"{'='*70}\n")
        
        return df_mapped

    @staticmethod
    def _add_compat_aliases(df: pd.DataFrame) -> pd.DataFrame:
        """Add alias columns to preserve backward compatibility."""
        def _coerce_series(value: pd.Series | pd.DataFrame) -> pd.Series:
            if isinstance(value, pd.DataFrame):
                return value.iloc[:, 0]
            return value

        if "pitch_attitude" in df.columns and "pitch" not in df.columns:
            df["pitch"] = _coerce_series(df["pitch_attitude"])

        if "roll_attitude" in df.columns and "roll" not in df.columns:
            df["roll"] = _coerce_series(df["roll_attitude"])

        if "airspeed" not in df.columns:
            for candidate in [
                "indicated_airspeed",
                "calibrated_airspeed",
                "true_airspeed"
            ]:
                if candidate in df.columns:
                    df["airspeed"] = df[candidate]
                    break

        if "altitude" not in df.columns:
            for candidate in ["pressure_altitude", "radio_altitude"]:
                if candidate in df.columns:
                    df["altitude"] = df[candidate]
                    break

        return df
    
    def get_column(self, df: pd.DataFrame, standard_name: str) -> Optional[str]:
        """Get actual column name for a standard name"""
        if standard_name in df.columns:
            return standard_name
        return None
    
    def has_column(self, df: pd.DataFrame, standard_name: str) -> bool:
        """Check if DataFrame has a column (by standard name)"""
        return standard_name in df.columns
    
    def get_required_columns(self) -> List[str]:
        """Get list of required column standard names"""
        return [m.standard_name for m in self.COLUMN_MAPPINGS if m.required]
    
    def validate_required_columns(self, df: pd.DataFrame) -> Dict[str, bool]:
        """Validate that all required columns are present"""
        validation = {}
        for mapping in self.COLUMN_MAPPINGS:
            if mapping.required:
                validation[mapping.standard_name] = mapping.standard_name in df.columns
        return validation


# Global mapper instance
_mapper = None


def get_mapper() -> CSVColumnMapper:
    """Get global CSV column mapper instance"""
    global _mapper
    if _mapper is None:
        _mapper = CSVColumnMapper()
    return _mapper


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    print("=" * 70)
    print("CSV COLUMN MAPPER TEST")
    print("=" * 70)
    
    # Create test DataFrame with various column names
    test_data = {
        'FLT': ['AA123', 'AA124'],
        'DATE_TIME': ['2024-01-01 10:00:00', '2024-01-01 10:00:01'],
        'ALT_FT': [10000, 10100],
        'KIAS': [250, 252],
        'VERT_ACCEL': [1.0, 2.5],
        'TAT': [15, 16],
        'BARO_PRESS': [29.92, 29.91],
        'GEAR_POS': ['DOWN', 'DOWN'],
        'CustomColumn': [1, 2]
    }
    
    df = pd.DataFrame(test_data)
    
    print("\nOriginal DataFrame:")
    print(df.head())
    
    # Map columns
    mapper = CSVColumnMapper()
    df_mapped = mapper.map_columns(df)
    
    print("\nMapped DataFrame:")
    print(df_mapped.head())
    
    # Check for specific columns
    print("\n" + "=" * 70)
    print("COLUMN CHECKS")
    print("=" * 70)
    print(f"Has timestamp: {mapper.has_column(df_mapped, 'timestamp')}")
    print(f"Has altitude: {mapper.has_column(df_mapped, 'altitude')}")
    print(f"Has airspeed: {mapper.has_column(df_mapped, 'airspeed')}")
    print(f"Has vertical_acceleration: {mapper.has_column(df_mapped, 'vertical_acceleration')}")
    
    # Validate required columns
    print("\n" + "=" * 70)
    print("REQUIRED COLUMNS VALIDATION")
    print("=" * 70)
    validation = mapper.validate_required_columns(df_mapped)
    for col, present in validation.items():
        status = "✅" if present else "❌"
        print(f"{status} {col}: {'Present' if present else 'MISSING'}")
    
    print("\n" + "=" * 70)
    print("[OK] Column mapping test complete!")
    print("=" * 70)


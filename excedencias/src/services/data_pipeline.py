"""
ETAPA 2 - Data Pipeline
Orquestra parsing, mapeamento, normalização e padronização de colunas
para preparar dados de voo para os analisadores.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

import pandas as pd

from utils.logger import logger
from .csv_parser import CSVParser
from .csv_column_mapper import CSVColumnMapper


@dataclass
class DataPipelineConfig:
    """Configurações do pipeline de dados"""
    required_columns: List[str] = field(default_factory=list)
    speed_unit: str = "kts"  # kts, kmh, mps
    altitude_unit: str = "ft"  # ft, m
    weight_unit: str = "kg"  # kg, lbs
    infer_units: bool = True
    base_timestamp: Optional[str] = None  # ISO string para timestamps numéricos


@dataclass
class PipelineResult:
    """Resultado do pipeline"""
    df: pd.DataFrame
    warnings: List[str]
    errors: List[str]
    info: Dict[str, Any]
    weight_kg: Optional[float] = None


class DataPipeline:
    """Pipeline de dados para ingestão e normalização de arquivos de voo"""

    _cache: Dict[str, PipelineResult] = {}

    def __init__(self, config: Optional[DataPipelineConfig] = None):
        self.config = config or DataPipelineConfig()
        self.parser = CSVParser()
        self.mapper = CSVColumnMapper()

    def process_file(self, file_path: Path | str) -> PipelineResult:
        """Processa arquivo CSV/TXT e retorna DataFrame normalizado"""
        warnings: List[str] = []
        errors: List[str] = []
        info: Dict[str, Any] = {}

        if isinstance(file_path, str):
            file_path = Path(file_path)

        cache_key = self._get_cache_key(file_path)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            info.update(cached.info)
            info["cached"] = True
            return PipelineResult(
                df=cached.df.copy(deep=True),
                warnings=list(cached.warnings),
                errors=list(cached.errors),
                info=info,
                weight_kg=cached.weight_kg
            )

        try:
            df = self.parser.parse_file(file_path)
        except Exception as exc:
            errors.append(f"Falha ao parsear arquivo: {exc}")
            return PipelineResult(df=pd.DataFrame(), warnings=warnings, errors=errors, info=info)

        # Normalizar colunas com mapper (idempotente)
        df = self.mapper.map_columns(df)

        # Normalizar unidades e criar aliases
        df, unit_warnings = self._normalize_units(df)
        warnings.extend(unit_warnings)

        df, alias_warnings = self._create_alias_columns(df)
        warnings.extend(alias_warnings)

        # Validar colunas requeridas (se configuradas)
        if self.config.required_columns:
            missing = [c for c in self.config.required_columns if c not in df.columns]
            if missing:
                warnings.append(f"Colunas requeridas ausentes: {missing}")

        # Inferir peso (kg)
        weight_kg = self._infer_weight_kg(df)
        if weight_kg is None:
            warnings.append("Peso não identificado automaticamente")

        info["rows"] = len(df)
        info["columns"] = len(df.columns)
        info["column_names"] = list(df.columns)
        info["cached"] = False

        result = PipelineResult(df=df, warnings=warnings, errors=errors, info=info, weight_kg=weight_kg)
        self._cache[cache_key] = result
        return result

    def process_dataframe(self, df: pd.DataFrame) -> PipelineResult:
        """Processa DataFrame já carregado"""
        warnings: List[str] = []
        errors: List[str] = []
        info: Dict[str, Any] = {}

        try:
            df = self.mapper.map_columns(df)
            df, unit_warnings = self._normalize_units(df)
            warnings.extend(unit_warnings)
            df, alias_warnings = self._create_alias_columns(df)
            warnings.extend(alias_warnings)
        except Exception as exc:
            errors.append(f"Falha ao normalizar DataFrame: {exc}")
            return PipelineResult(df=pd.DataFrame(), warnings=warnings, errors=errors, info=info)

        if self.config.required_columns:
            missing = [c for c in self.config.required_columns if c not in df.columns]
            if missing:
                warnings.append(f"Colunas requeridas ausentes: {missing}")

        weight_kg = self._infer_weight_kg(df)
        if weight_kg is None:
            warnings.append("Peso não identificado automaticamente")

        info["rows"] = len(df)
        info["columns"] = len(df.columns)
        info["column_names"] = list(df.columns)
        info["cached"] = False

        return PipelineResult(df=df, warnings=warnings, errors=errors, info=info, weight_kg=weight_kg)

    def _normalize_units(self, df: pd.DataFrame) -> tuple[pd.DataFrame, List[str]]:
        """Normaliza unidades de velocidade, altitude e peso"""
        warnings: List[str] = []

        # Velocidade
        if "airspeed" in df.columns:
            max_speed = pd.to_numeric(df["airspeed"], errors="coerce").max()
            if self.config.speed_unit == "kmh":
                df["airspeed"] = pd.to_numeric(df["airspeed"], errors="coerce") / 1.852
                warnings.append("Velocidade convertida de km/h para kts")
            elif self.config.speed_unit == "mps":
                df["airspeed"] = pd.to_numeric(df["airspeed"], errors="coerce") * 1.94384
                warnings.append("Velocidade convertida de m/s para kts")
            elif self.config.infer_units and max_speed and max_speed > 500:
                # Heurística simples para km/h
                df["airspeed"] = pd.to_numeric(df["airspeed"], errors="coerce") / 1.852
                warnings.append("Velocidade alta detectada. Convertido de km/h para kts (heurística)")

        # Altitude
        if "altitude" in df.columns and self.config.altitude_unit == "m":
            df["altitude"] = pd.to_numeric(df["altitude"], errors="coerce") * 3.28084
            warnings.append("Altitude convertida de metros para pés")

        return df, warnings

    def _create_alias_columns(self, df: pd.DataFrame) -> tuple[pd.DataFrame, List[str]]:
        """Cria colunas alternativas esperadas por analisadores"""
        warnings: List[str] = []

        # Timestamp
        if "timestamp" in df.columns and "TIMESTAMP" not in df.columns:
            df["TIMESTAMP"] = self._normalize_timestamp(df["timestamp"])
        elif "timestamp" not in df.columns:
            df["timestamp"] = df.index
            df["TIMESTAMP"] = self._normalize_timestamp(df["timestamp"])
            warnings.append("Timestamp ausente. Usando índice como tempo")

        # Airspeed
        if "airspeed" in df.columns and "IAS" not in df.columns:
            df["IAS"] = pd.to_numeric(df["airspeed"], errors="coerce")

        # Mach
        if "mach" in df.columns and "MACH" not in df.columns:
            df["MACH"] = pd.to_numeric(df["mach"], errors="coerce")

        # Altitude
        if "altitude" in df.columns and "ALT" not in df.columns:
            df["ALT"] = pd.to_numeric(df["altitude"], errors="coerce")
        if "altitude" in df.columns and "ALTITUDE" not in df.columns:
            df["ALTITUDE"] = pd.to_numeric(df["altitude"], errors="coerce")

        # Flap position
        if "flap_position" in df.columns and "FLAP_POSITION" not in df.columns:
            df["FLAP_POSITION"] = df["flap_position"].apply(self._normalize_flap_position)

        # Gear position
        if "gear_position" in df.columns and "LG_POSITION" not in df.columns:
            df["LG_POSITION"] = df["gear_position"].apply(self._normalize_gear_position)

        # Temperature
        if "temperature" in df.columns and "TAT" not in df.columns:
            df["TAT"] = pd.to_numeric(df["temperature"], errors="coerce")

        # EGT
        if "egt" in df.columns and "EGT" not in df.columns:
            df["EGT"] = pd.to_numeric(df["egt"], errors="coerce")

        # Vertical acceleration
        if "vertical_acceleration" in df.columns and "VERTICAL_ACCELERATION" not in df.columns:
            df["VERTICAL_ACCELERATION"] = pd.to_numeric(df["vertical_acceleration"], errors="coerce")

        return df, warnings

    def _normalize_timestamp(self, series: pd.Series) -> pd.Series:
        """Normaliza coluna de timestamp"""
        if series.empty:
            return series

        if pd.api.types.is_numeric_dtype(series):
            if self.config.base_timestamp:
                base = pd.to_datetime(self.config.base_timestamp, errors="coerce")
                if pd.isna(base):
                    return pd.to_datetime(series, errors="coerce", unit="s").astype(str)
                return (base + pd.to_timedelta(series, unit="s")).astype(str)
            return pd.to_datetime(series, errors="coerce", unit="s").astype(str)

        return pd.to_datetime(series, errors="coerce").astype(str)

    def _normalize_flap_position(self, value: Any) -> str:
        """Converte posição de flap para padrão esperado"""
        if pd.isna(value):
            return "UNKNOWN"

        text = str(value).strip().lower()
        if text.startswith("flap"):
            return text.replace(" ", "_")

        # Numeric patterns
        try:
            num = float(text)
            # E1/E2 flaps
            if num in [0, 1, 2, 3, 4]:
                if num == 0:
                    return "FLAP_0"
                return f"FLAP_{int(num)}"
            # E145 flaps
            if int(num) in [9, 18, 22, 45]:
                return f"FLAP_{int(num)}"
        except Exception:
            pass

        return text.upper()

    def _normalize_gear_position(self, value: Any) -> str:
        """Converte posição do trem para DOWN/UP"""
        if pd.isna(value):
            return "UNKNOWN"

        text = str(value).strip().lower()
        if text in ["down", "d", "1", "true", "extended", "gear_down"]:
            return "DOWN"
        if text in ["up", "u", "0", "false", "retracted", "gear_up"]:
            return "UP"

        return text.upper()

    def _infer_weight_kg(self, df: pd.DataFrame) -> Optional[float]:
        """Infere peso em kg a partir de colunas conhecidas"""
        if "gross_weight" not in df.columns:
            return None

        weight_series = pd.to_numeric(df["gross_weight"], errors="coerce").dropna()
        if weight_series.empty:
            return None

        avg_weight = float(weight_series.mean())

        if self.config.weight_unit == "lbs":
            return avg_weight * 0.453592
        if self.config.weight_unit == "kg":
            return avg_weight

        # Inferência simples
        if avg_weight > 100000:
            return avg_weight * 0.453592
        return avg_weight

    def _get_cache_key(self, file_path: Path) -> str:
        """Gera chave de cache baseada em caminho e timestamp"""
        try:
            stat = file_path.stat()
            return f"{file_path.resolve()}::{stat.st_mtime}::{stat.st_size}"
        except Exception:
            return str(file_path.resolve())

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from services.csv_parser import CSVParser
from services.hard_landing_analyzer import HardLandingAnalyzer


def pick_best_result(results):
    rank = {
        "NORMAL": 0,
        "HARD_LANDING_LOW": 1,
        "HARD_LANDING_HIGH": 2,
        "ENGINE_INSPECTION": 3,
        "HARD_LANDING_ENGINE": 3,
    }
    if not results:
        return None
    return max(results, key=lambda r: rank.get(getattr(r, "status", "NORMAL"), 0))


def find_flight_number(df):
    candidates = [
        "flight_number", "flight", "flt", "flight_no", "flight_id",
        "numero_voo", "voo", "flt_num", "flightnum", "flight_nbr", "fltnbr",
    ]
    lower_map = {str(column).lower(): column for column in df.columns}
    for candidate in candidates:
        col = lower_map.get(candidate)
        if col is not None:
            series = df[col].dropna()
            if not series.empty:
                return str(series.iloc[0]).strip()
    return "N/A"


def pick_timestamp(df):
    if hasattr(df, "index") and len(df.index) > 0:
        idx0 = df.index[0]
        try:
            ts = datetime.fromisoformat(str(idx0).replace("Z", ""))
            return ts.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write_result(output_file: Path, df, model: str, weight_kg: float):
    analyzer = HardLandingAnalyzer()
    results = analyzer.analyze(df, weight_kg, model)
    best = pick_best_result(results)

    status = "NORMAL"
    max_roll = "N/A"
    max_g = "N/A"
    amm_limit = "N/A"
    min_pitch = "N/A"
    amm_pitch_limit = "N/A"

    if best is not None:
        status = str(getattr(best, "status", "NORMAL"))
        vertical_data = getattr(best, "vertical_accel", {}) or {}
        roll_data = getattr(best, "roll_rate", {}) or {}
        pitch_data = getattr(best, "pitch_rate", {}) or {}

        if roll_data.get("max_rate") is not None:
            max_roll = f"{float(roll_data['max_rate']):.2f}"
        if vertical_data.get("max_g") is not None:
            max_g = f"{float(vertical_data['max_g']):.3f}"

        vertical_thresholds = vertical_data.get("thresholds", {}) or {}
        vertical_limit = (
            vertical_thresholds.get("high")
            or vertical_thresholds.get("threshold")
            or vertical_thresholds.get("low")
        )
        if vertical_limit is not None:
            amm_limit = f"{float(vertical_limit):.3f}"

        if pitch_data.get("min_rate") is not None:
            min_pitch = f"{float(pitch_data['min_rate']):.3f}"

        pitch_thresholds = pitch_data.get("thresholds", {}) or {}
        pitch_limit = (
            pitch_thresholds.get("high")
            or pitch_thresholds.get("threshold")
            or pitch_thresholds.get("low")
        )
        if pitch_limit is not None:
            amm_pitch_limit = f"{float(pitch_limit):.3f}"

    ts = pick_timestamp(df)
    flight_number = find_flight_number(df)

    lines = [
        f"{ts} | INFO     | services.hard_landing_analyzer:analyze:775 - ANALISE HARD LANDING - Arquivo: {len(df)} linhas, Peso: {weight_kg:.0f}kg, Modelo: {model}",
        f"{ts} | INFO     | services.hard_landing_analyzer:analyze:826 - Monitor 1 (Vertical Accel): {status}",
        f"Max Roll Rate: {max_roll}",
        f"g: {max_g}",
        f"AMM Limit: {amm_limit}",
        f"Min Pitch rate: {min_pitch}",
        f"AMM Pitch Limit: {amm_pitch_limit}",
        f"Flight Number: {flight_number}",
    ]

    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK {output_file.name} | status={status} | g={max_g}")


def main():
    parser = CSVParser()

    e145_csv = ROOT / "Analises de dados de voo" / "HARDINGLANDING E145" / "ERJ2.csv"
    if not e145_csv.exists():
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {e145_csv}")

    df_e145 = parser.parse_file(e145_csv)

    write_result(ROOT / "result_e145.txt", df_e145, model="E145", weight_kg=21772.0)
    write_result(ROOT / "result_e1.txt", df_e145, model="E190", weight_kg=42000.0)


if __name__ == "__main__":
    main()

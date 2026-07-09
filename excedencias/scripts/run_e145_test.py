from pathlib import Path
import sys

__test__ = False

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from services.csv_parser import CSVParser
from services.hard_landing_analyzer import HardLandingAnalyzer

file_path = Path(r"E:\Analises de dados de voo\HARDINGLANDING E145\ERJ2.csv")


def norm_model(text: str) -> str | None:
    t = str(text).lower().replace(" ", "").replace("_", "").replace("-", "")
    if "erj145" in t or "e145" in t:
        return "E145"
    if "erj140" in t or "e140" in t:
        return "E140"
    if "erj135" in t or "e135" in t:
        return "E135"
    if "e170" in t:
        return "E170"
    if "e175" in t:
        return "E175"
    if "e195e2" in t:
        return "E195-E2"
    if "e190e2" in t:
        return "E190-E2"
    if "e195" in t:
        return "E195"
    if "e190" in t:
        return "E190"
    if t == "e2":
        return "E190-E2"
    if t == "e1":
        return "E190"
    return None


def run_e145_test(csv_path: Path = file_path) -> int:
    parser = CSVParser()
    df = parser.parse_file(csv_path)

    model = None
    cols = {c.strip().lower(): c for c in df.columns}
    for key in [
        "aircraft type",
        "aircraft_type",
        "aircraft model",
        "modelo",
        "model",
        "tipo aeronave",
    ]:
        if key in cols:
            series = df[cols[key]].dropna()
            if len(series) > 0:
                model = norm_model(series.iloc[0])
                break

    model = model or "E145"
    weight_kg = 48000 * 0.453592

    print(f"Modelo usado: {model} | Peso usado: {weight_kg:.1f} kg")

    results = HardLandingAnalyzer().analyze(df, weight_kg, model)
    exceed = []
    for i, r in enumerate(results, 1):
        if getattr(r, "status", "NORMAL") != "NORMAL":
            vert = getattr(r, "vertical_accel", {}) or {}
            pitch = getattr(r, "pitch_rate", {}) or {}
            exceed.append(
                {
                    "voo": i,
                    "status": r.status,
                    "max_g": vert.get("max_g"),
                    "th": vert.get("thresholds"),
                    "pitch_status": pitch.get("status"),
                    "min_rate": pitch.get("min_rate"),
                }
            )

    print(f"Total de voos detectados: {len(results)}")
    print(f"Excedencias (nao NORMAL): {len(exceed)}")

    for e in exceed:
        th = e["th"] or {}
        if "threshold" in th:
            th_txt = f"TH={th['threshold']:.3f}G"
        else:
            th_txt = (
                f"LOW={th.get('low'):.3f}G HIGH={th.get('high'):.3f}G "
                f"ENG={th.get('engine'):.3f}G"
            )
        pr = e["min_rate"]
        pr_txt = f"min_rate={pr:.3f}" if pr is not None else "min_rate=N/A"
        print(
            f"Voo {e['voo']}: {e['status']} | max_g={e['max_g']:.3f}G | "
            f"{th_txt} | pitch={e['pitch_status']} {pr_txt}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(run_e145_test())

import re
from pathlib import Path
from datetime import datetime

MODELS = {
    'E1': {
        'result': 'result_e1.txt',
        'aircraft': 'MEXICANA E1 Family (E170/E175/E190/E195)',
        'reference': 'AMM TASK 05-50-03-200-801-A',
    },
    'E170': {
        'result': 'result_e170.txt',
        'aircraft': 'MEXICANA E170',
        'reference': 'AMM TASK 05-50-03-200-801-A',
    },
    'E145': {
        'result': 'result_e145.txt',
        'aircraft': 'MEXICANA E145',
        'reference': 'AMM TASK 05-50-02-06-1',
    },
    'E2': {
        'result': 'result_e2.txt',
        'aircraft': 'MEXICANA E195-E2',
        'reference': 'AMM TASK 05-50-03-200-801-A',
    },
}


def _find_first(pattern: str, text: str, default: str = 'N/A') -> str:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return default
    return match.group(1).strip()


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_log_text(result_file: Path) -> str:
    raw = result_file.read_bytes()
    if b'\x00' in raw:
        try:
            return raw.decode('utf-16')
        except UnicodeDecodeError:
            try:
                return raw.decode('utf-16-le')
            except UnicodeDecodeError:
                pass
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('utf-8', errors='ignore')


def extract_data(result_file: Path) -> dict:
    content = _read_log_text(result_file)

    weight = _find_first(r'Peso:\s*([\d\.]+)kg', content, 'N/A')
    max_roll = _find_first(r'Max Roll Rate:\s*([-\d\.]+)', content, 'N/A')
    max_nz = _find_first(r'^g:\s*([-\d\.]+)', content, 'N/A')
    amm_limit = _find_first(r'AMM Limit:\s*([-\d\.]+)', content, 'N/A')
    min_pitch = _find_first(r'Min Pitch rate:\s*([-\d\.]+)', content, 'N/A')
    amm_pitch_limit = _find_first(
        r'AMM Pitch Limit:\s*([-\d\.]+)',
        content,
        'N/A'
    )
    flight_number = _find_first(r'Flight Number:\s*([^\r\n]+)', content, 'N/A')

    status_match = re.search(
        r'\b(ENGINE_INSPECTION|HARD_LANDING_HIGH|HARD_LANDING_LOW)\b',
        content
    )
    status = status_match.group(1) if status_match else 'NORMAL'

    if max_nz == 'N/A':
        max_nz = _find_first(r'Max G:\s*([-\d\.]+)G', content, 'N/A')

    if amm_limit == 'N/A':
        amm_limit = _find_first(
            (
                r'Thresholds:\s*LOW=[-\d\.]+,\s*HIGH=([-\d\.]+),'
                r'\s*ENGINE=[-\d\.]+'
            ),
            content,
            'N/A'
        )

    ts_match = re.search(
        r'^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}):\d{2}',
        content,
        re.MULTILINE
    )
    if not ts_match:
        ts_match = re.search(
            r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}):\d{2}',
            content
        )
    if ts_match:
        date_str = datetime.strptime(
            ts_match.group(1),
            '%Y-%m-%d'
        ).strftime('%d/%m/%Y')
        time_str = ts_match.group(2)
    else:
        now = datetime.now()
        date_str = now.strftime('%d/%m/%Y')
        time_str = now.strftime('%H:%M')

    return {
        'weight': weight,
        'max_roll': max_roll,
        'max_nz': max_nz,
        'amm_limit': amm_limit,
        'min_pitch': min_pitch,
        'amm_pitch_limit': amm_pitch_limit,
        'flight_number': flight_number,
        'status': status,
        'date': date_str,
        'time': time_str,
    }


def build_report(config: dict, data: dict) -> str:
    max_nz = _to_float(data['max_nz'])
    amm_limit = _to_float(data['amm_limit'])
    min_pitch = _to_float(data['min_pitch'])
    amm_pitch_limit = _to_float(data['amm_pitch_limit'])

    mlg_hard = False
    if max_nz is not None and amm_limit is not None:
        mlg_hard = max_nz > amm_limit

    nlg_hard = False
    if min_pitch is not None and amm_pitch_limit is not None:
        nlg_hard = min_pitch <= amm_pitch_limit

    mlg_comparison = 'Value not available.'
    if max_nz is not None and amm_limit is not None:
        mlg_comparison = (
            'Value above limit.' if mlg_hard else 'Value below limit.'
        )

    nlg_comparison = 'Value not available.'
    if min_pitch is not None and amm_pitch_limit is not None:
        if nlg_hard:
            nlg_comparison = 'Value more negative than limit.'
        else:
            nlg_comparison = 'Value above limit.'

    status = data.get('status', 'NORMAL')

    if status in {
        'ENGINE_INSPECTION',
        'HARD_LANDING_HIGH',
        'HARD_LANDING_LOW'
    }:
        if not mlg_hard and not nlg_hard:
            mlg_hard = True
            mlg_comparison = 'Value indicates exceedance by event status.'

    if status == 'ENGINE_INSPECTION':
        maintenance_action = (
            'Phase III required.\n'
            'Phase II also required prior to release.\n'
        )
    elif status == 'HARD_LANDING_HIGH':
        maintenance_action = (
            'Phase II required.\n'
            'Phase III as per engineering assessment.\n'
        )
    elif status == 'HARD_LANDING_LOW':
        maintenance_action = (
            'Phase I required.\n'
            'Phase II or III not required unless additional findings '
            'are identified.\n'
        )
    else:
        maintenance_action = (
            'Phase II or III not required.\n'
            'Phase I can be considered fulfilled, with no findings.\n'
        )

    if mlg_hard or nlg_hard:
        final_conclusion = (
            'The landing exceeded at least one evaluation limit for '
            f"the {config['aircraft']}."
        )
    else:
        final_conclusion = (
            'The landing remained within normal limits for '
            f"the {config['aircraft']}."
        )

    return ''.join([
        'TECHNICAL LANDING EVALUATION REPORT\n',
        f"Aircraft: {config['aircraft']}\n\n",
        'Event: Evaluation of possible Hard Landing\n\n',
        'Data Source: FDR / MXE\n\n',
        f"Landing Weight (WB): {data['weight']} kg\n\n",
        f"Reference: {config['reference']}\n\n",
        f"DATE: {data['time']} LOCAL {data['date']} {data['flight_number']}\n\n",
        'MLG Evaluation\n',
        f"* Max Roll Rate: {data['max_roll']} deg/s\n",
        f"* Max Nz: {data['max_nz']} g\n",
        f"* AMM Limit for {data['weight']} kg: {data['amm_limit']} g → {mlg_comparison}\n",
        (
            'Hard Landing indication in the MLG.\n\n'
            if mlg_hard
            else 'No Hard Landing indication in the MLG.\n\n'
        ),
        'NLG Evaluation\n',
        f"* Min Pitch rate: {data['min_pitch']} deg/s\n",
        f"* AMM Limit: more negative than {data['amm_pitch_limit']} deg/s → {nlg_comparison}\n",
        (
            'Hard Landing indication in the NLG.\n\n'
            if nlg_hard
            else 'No Hard Landing indication in the NLG.\n\n'
        ),
        'Conclusion\n',
        '→ Hard Landing in the MLG\n' if mlg_hard else '→ No Hard Landing in the MLG\n',
        '→ Hard Landing in the NLG\n' if nlg_hard else '→ No Hard Landing in the NLG\n',
        f"{final_conclusion}\n\n",
        'Maintenance Action\n',
        maintenance_action,
    ])


def generate_reports() -> None:
    root = Path(__file__).resolve().parent
    for model, config in MODELS.items():
        result_path = root / config['result']
        output_path = root / f'HARD_LANDING_REPORT_{model}.md'

        if not result_path.exists():
            print(f'Result file not found: {result_path.name}')
            continue

        data = extract_data(result_path)
        report = build_report(config, data)
        output_path.write_text(report, encoding='utf-8')
        print(f'Report generated: {output_path.name}')


if __name__ == '__main__':
    generate_reports()


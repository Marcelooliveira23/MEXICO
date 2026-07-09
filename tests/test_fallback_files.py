from pathlib import Path


def test_fallback_json_files_exist() -> None:
    root = Path(__file__).resolve().parent.parent
    expected = [
        'users_fallback.json',
        'records_fallback.json',
        'tails_fallback.json',
        'mel_fallback.json',
        'aog_fallback.json',
        'etd_fallback.json',
    ]
    for name in expected:
        assert (root / name).exists(), f'Missing fallback file: {name}'

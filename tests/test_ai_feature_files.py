from pathlib import Path


def test_ai_feature_files_exist() -> None:
    root = Path(__file__).resolve().parent.parent
    assert (root / 'ai_engine.py').exists()
    assert (root / 'routes_analytics.py').exists()
    assert (root / 'Templates' / 'ai_analysis.html').exists()


def test_ai_menu_integration_present() -> None:
    root = Path(__file__).resolve().parent.parent
    menu_path = root / 'Templates' / 'menu.html'
    content = menu_path.read_text(encoding='utf-8')
    assert 'Offline AI Analysis' in content
    assert 'analytics.ai_analysis_page' in content

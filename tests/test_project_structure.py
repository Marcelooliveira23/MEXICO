from pathlib import Path


def test_main_files_exist() -> None:
    root = Path(__file__).resolve().parent.parent
    assert (root / 'app.py').exists()
    assert (root / 'Templates').exists()
    assert (root / 'static').exists()


def test_container_files_exist() -> None:
    root = Path(__file__).resolve().parent.parent
    assert (root / 'Dockerfile').exists()
    assert (root / 'docker-compose.yml').exists()

from pathlib import Path


def test_fleet_status_report_keeps_operational_report_only() -> None:
    root = Path(__file__).resolve().parent.parent
    content = (root / 'Templates' /
               'fleet_status_report.html').read_text(encoding='utf-8')

    forbidden_tokens = [
        'Fleet Health Distribution',
        'Tail Risk and Utilization Profile',
        'Fleet Prioritization Insight',
        'fleetHealthChart',
        'fleetRiskChart',
        'buildFleetCharts()',
        'Chart Configuration',
        'Chart Parameters Explained',
    ]

    for token in forbidden_tokens:
        assert token not in content


def test_ai_analysis_contains_migrated_fleet_charts_and_analysis() -> None:
    root = Path(__file__).resolve().parent.parent
    content = (root / 'Templates' /
               'ai_analysis.html').read_text(encoding='utf-8')

    required_tokens = [
        'Fleet Health Distribution',
        'Tail Risk and Utilization Profile',
        'Fleet Prioritization Insight',
        'fleetHealthChart',
        'fleetRiskChart',
        "{% include 'fleet_ata_filter_section.html' %}",
    ]

    for token in required_tokens:
        assert token in content


def test_fleet_status_report_avoids_primary_portuguese_ui_labels() -> None:
    root = Path(__file__).resolve().parent.parent
    content = (root / 'Templates' /
               'fleet_status_report.html').read_text(encoding='utf-8').lower()

    forbidden_tokens = [
        'relatório',
        'frota',
        'falhas',
        'manutenção',
        'voltar',
        'próximo',
        'configurações',
    ]

    for token in forbidden_tokens:
        assert token not in content

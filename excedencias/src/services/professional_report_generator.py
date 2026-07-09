"""
Professional Report Generator - Gerador de Relatórios Profissionais
Cria relatórios formatados em HTML e PDF com análise detalhada de hard landing
"""

from datetime import datetime
from pathlib import Path
from typing import List, Dict
import json


class ProfessionalReportGenerator:
    """Gerador de relatórios profissionais para análise de hard landing"""
    
    def __init__(self):
        self.template_path = Path(__file__).parent.parent.parent / "assets" / "templates"
        
    def generate_html_report(
        self, 
        results: List[Dict],
        output_path: Path,
        aircraft_model: str = "E190",
        tail_number: str = "N/A"
    ) -> Path:
        """
        Gera relatório HTML profissional
        
        Args:
            results: Lista de resultados de análise
            output_path: Caminho para salvar o relatório
            aircraft_model: Modelo da aeronave
            tail_number: Número de cauda
            
        Returns:
            Path do arquivo gerado
        """
        
        # Calcular estatísticas
        total_flights = sum(r['flights'] for r in results if 'flights' in r)
        total_hard_landings = sum(r['hard_landings'] for r in results if 'hard_landings' in r)
        max_g_overall = max((r['max_g'] for r in results if 'max_g' in r), default=0)
        
        # Classificar por severidade
        critical = [r for r in results if r.get('max_g', 0) >= 2.48]
        high = [r for r in results if 2.18 <= r.get('max_g', 0) < 2.48]
        low = [r for r in results if 2.0 <= r.get('max_g', 0) < 2.18]
        
        html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Hard Landing - {aircraft_model} {tail_number}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .header .info {{
            margin-top: 20px;
            display: flex;
            justify-content: center;
            gap: 40px;
            flex-wrap: wrap;
        }}
        
        .header .info-item {{
            background: rgba(255,255,255,0.1);
            padding: 10px 20px;
            border-radius: 8px;
            backdrop-filter: blur(10px);
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }}
        
        .stat-card {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        }}
        
        .stat-card .value {{
            font-size: 3em;
            font-weight: bold;
            margin: 15px 0;
        }}
        
        .stat-card .label {{
            color: #666;
            font-size: 1.1em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-card.critical .value {{ color: #dc3545; }}
        .stat-card.high .value {{ color: #fd7e14; }}
        .stat-card.low .value {{ color: #ffc107; }}
        .stat-card.normal .value {{ color: #28a745; }}
        .stat-card.info .value {{ color: #17a2b8; }}
        
        .section {{
            padding: 40px;
        }}
        
        .section h2 {{
            font-size: 2em;
            margin-bottom: 25px;
            color: #1e3c72;
            border-bottom: 3px solid #2a5298;
            padding-bottom: 10px;
        }}
        
        .severity-section {{
            margin-bottom: 40px;
        }}
        
        .severity-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .severity-badge {{
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            color: white;
        }}
        
        .severity-badge.critical {{ background: #dc3545; }}
        .severity-badge.high {{ background: #fd7e14; }}
        .severity-badge.low {{ background: #ffc107; color: #333; }}
        
        .flight-card {{
            background: #f8f9fa;
            border-left: 5px solid #2a5298;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            transition: all 0.3s ease;
        }}
        
        .flight-card:hover {{
            background: #e9ecef;
            transform: translateX(10px);
        }}
        
        .flight-card.critical {{ border-left-color: #dc3545; }}
        .flight-card.high {{ border-left-color: #fd7e14; }}
        .flight-card.low {{ border-left-color: #ffc107; }}
        
        .flight-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        
        .detail-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .detail-label {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }}
        
        .detail-value {{
            font-size: 1.1em;
            font-weight: 600;
        }}
        
        .recommendations {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
        }}
        
        .recommendations h2 {{
            color: white;
            border-bottom-color: rgba(255,255,255,0.3);
        }}
        
        .recommendation-item {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            backdrop-filter: blur(10px);
        }}
        
        .recommendation-item h3 {{
            margin-bottom: 10px;
            font-size: 1.3em;
        }}
        
        .footer {{
            background: #1e3c72;
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .footer p {{
            margin: 5px 0;
            opacity: 0.8;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
            }}
            .stat-card:hover, .flight-card:hover {{
                transform: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>RELATÓRIO DE HARD LANDING</h1>
            <div class="subtitle">Análise Técnica Completa - AMM 05-50-03</div>
            <div class="info">
                <div class="info-item">
                    <strong>Aeronave:</strong> {aircraft_model}
                </div>
                <div class="info-item">
                    <strong>Tail Number:</strong> {tail_number}
                </div>
                <div class="info-item">
                    <strong>Data:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}
                </div>
            </div>
        </div>
        
        <!-- Statistics Grid -->
        <div class="stats-grid">
            <div class="stat-card info">
                <div class="label">Total de Voos</div>
                <div class="value">{total_flights}</div>
            </div>
            <div class="stat-card critical">
                <div class="label">Hard Landings</div>
                <div class="value">{total_hard_landings}</div>
            </div>
            <div class="stat-card high">
                <div class="label">Taxa</div>
                <div class="value">{total_hard_landings/total_flights*100:.1f}%</div>
            </div>
            <div class="stat-card low">
                <div class="label">Max G</div>
                <div class="value">{max_g_overall:.3f}G</div>
            </div>
        </div>
        
        <!-- Critical Events -->
        {self._generate_severity_section("CRÍTICO - ENGINE INSPECTION", critical, "critical") if critical else ""}
        
        <!-- High Severity Events -->
        {self._generate_severity_section("ALTA - DETAILED INSPECTION", high, "high") if high else ""}
        
        <!-- Low Severity Events -->
        {self._generate_severity_section("BAIXA - GENERAL INSPECTION", low, "low") if low else ""}
        
        <!-- Recommendations -->
        <div class="recommendations">
            <h2>RECOMENDAÇÕES TÉCNICAS</h2>
            {self._generate_recommendations(critical, high, low)}
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <p><strong>Sistema de Análise de Hard Landing</strong></p>
            <p>Conforme AMM TASK 05-50-03-200-801-A Rev 121</p>
            <p>Gerado automaticamente em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>"""
        
        # Salvar arquivo
        output_path.write_text(html_content, encoding='utf-8')
        return output_path
    
    def _generate_severity_section(self, title: str, events: List[Dict], severity_class: str) -> str:
        """Gera seção HTML para eventos de uma severidade"""
        if not events:
            return ""
        
        cards_html = ""
        for event in events:
            file_name = event.get('file', 'N/A')
            max_g = event.get('max_g', 0)
            flights = event.get('flights', 0)
            hard_landings = event.get('hard_landings', 0)
            lines = event.get('lines', 0)
            
            cards_html += f"""
            <div class="flight-card {severity_class}">
                <h3>{file_name}</h3>
                <div class="flight-details">
                    <div class="detail-item">
                        <div class="detail-label">Max G Force</div>
                        <div class="detail-value">{max_g:.3f}G</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Voos Detectados</div>
                        <div class="detail-value">{flights}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Hard Landings</div>
                        <div class="detail-value">{hard_landings}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Linhas Analisadas</div>
                        <div class="detail-value">{lines:,}</div>
                    </div>
                </div>
            </div>
            """
        
        return f"""
        <div class="section severity-section">
            <div class="severity-header">
                <span class="severity-badge {severity_class}">{title}</span>
                <h2>{len(events)} Evento(s)</h2>
            </div>
            {cards_html}
        </div>
        """
    
    def _generate_recommendations(self, critical: List, high: List, low: List) -> str:
        """Gera recomendações baseadas nos eventos detectados"""
        recommendations = []
        
        if critical:
            recommendations.append("""
            <div class="recommendation-item">
                <h3>🔴 PRIORIDADE CRÍTICA - ENGINE INSPECTION</h3>
                <p><strong>Ação Imediata Requerida:</strong></p>
                <ul>
                    <li>Inspeção boroscópica completa dos motores</li>
                    <li>Verificação de todas as montagens de motor</li>
                    <li>Inspeção estrutural completa da fuselagem</li>
                    <li>Tempo estimado: 48-72 horas</li>
                    <li>Referência: AMM 05-50-03 Phase III</li>
                </ul>
            </div>
            """)
        
        if high:
            recommendations.append("""
            <div class="recommendation-item">
                <h3>🟠 PRIORIDADE ALTA - DETAILED INSPECTION</h3>
                <p><strong>Inspeção Detalhada Necessária:</strong></p>
                <ul>
                    <li>Inspeção visual detalhada do trem de pouso</li>
                    <li>Verificação de fixações e componentes estruturais</li>
                    <li>Inspeção de painéis e revestimentos</li>
                    <li>Tempo estimado: 24-48 horas</li>
                    <li>Referência: AMM 05-50-03 Phase II</li>
                </ul>
            </div>
            """)
        
        if low:
            recommendations.append("""
            <div class="recommendation-item">
                <h3>🟡 INSPEÇÃO GERAL - GENERAL INSPECTION</h3>
                <p><strong>Inspeção Visual Recomendada:</strong></p>
                <ul>
                    <li>Inspeção visual do trem de pouso</li>
                    <li>Verificação de danos aparentes</li>
                    <li>Registro fotográfico</li>
                    <li>Tempo estimado: 8-12 horas</li>
                    <li>Referência: AMM 05-50-03 Phase I</li>
                </ul>
            </div>
            """)
        
        if not (critical or high or low):
            recommendations.append("""
            <div class="recommendation-item">
                <h3>✅ OPERAÇÃO NORMAL</h3>
                <p>Nenhum hard landing detectado. Aeronave operando dentro dos parâmetros normais.</p>
            </div>
            """)
        
        return "".join(recommendations)


def generate_professional_report(results: List[Dict], output_dir: Path = None) -> Path:
    """
    Função helper para gerar relatório profissional
    
    Args:
        results: Lista de resultados da análise
        output_dir: Diretório de saída (padrão: reports/)
        
    Returns:
        Path do arquivo HTML gerado
    """
    if output_dir is None:
        output_dir = Path("reports")
    
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"hard_landing_report_{timestamp}.html"
    
    generator = ProfessionalReportGenerator()
    return generator.generate_html_report(results, output_file)

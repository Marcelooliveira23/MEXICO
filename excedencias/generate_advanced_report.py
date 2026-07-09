"""
Gerador de Relatório Avançado
Cria relatório HTML profissional com análise estatística completa
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Adicionar src ao path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from services.advanced_analytics import AdvancedAnalytics
from services.csv_parser import CSVParser
from services.hard_landing_analyzer import HardLandingAnalyzer


def main():
    """Gera relatório avançado dos dados reais de E190"""
    
    print("="*80)
    print("GERADOR DE RELATÓRIO AVANÇADO - ANÁLISE DE HARD LANDING")
    print("="*80)
    print()
    
    # Caminho dos arquivos
    data_path = Path(r"C:\Users\mrced\OneDrive\Documents\hard landing")
    
    if not data_path.exists():
        print(f"[ERRO] Caminho não encontrado: {data_path}")
        return
    
    # Buscar todos os arquivos CSV
    csv_files = list(data_path.glob("*.csv"))
    print(f"[INFO] Encontrados {len(csv_files)} arquivos CSV")
    print()
    
    # Processar arquivos
    all_events = []
    parser = CSVParser()
    analyzer = HardLandingAnalyzer()
    
    print("Processando arquivos...")
    for csv_file in csv_files:
        print(f"  • {csv_file.name}...", end="")
        
        try:
            # Parse CSV
            df = parser.parse_file(csv_file)
            
            if df is None or df.empty:
                print(" SKIP (sem dados)")
                continue
            
            # Extrair peso se disponível, ou usar peso padrão E190
            weight_kg = 42000  # Peso padrão
            if 'gross_weight' in df.columns:
                weight_series = df['gross_weight'].dropna()
                if len(weight_series) > 0:
                    try:
                        # Pegar primeiro valor válido
                        first_value = weight_series.iloc[0]
                        # Se for uma Series, pegar o valor
                        if hasattr(first_value, 'iloc'):
                            weight_kg = float(first_value.iloc[0])
                        else:
                            weight_kg = float(first_value)
                    except (ValueError, TypeError, IndexError):
                        weight_kg = 42000
            
            # Analisar hard landing
            analysis_results = analyzer.analyze(
                df,
                weight_kg=weight_kg,
                model='E190'
            )
            
            # Extrair eventos dos resultados
            if analysis_results:
                for result in analysis_results:
                    # Converter HardLandingResult para dict para análise
                    is_hl = result.status != 'NORMAL'
                    
                    # Extrair max_g corretamente (chave é 'max_g', não 'max')
                    max_g_value = 0
                    if result.vertical_accel and isinstance(result.vertical_accel, dict):
                        max_g_value = result.vertical_accel.get('max_g', 0)
                    
                    # Extrair max roll/pitch rate
                    max_roll_value = 0
                    if result.roll_rate and isinstance(result.roll_rate, dict):
                        max_roll_value = result.roll_rate.get('max_rate', result.roll_rate.get('max', 0))
                    
                    max_pitch_value = 0
                    if result.pitch_rate and isinstance(result.pitch_rate, dict):
                        max_pitch_value = result.pitch_rate.get('max_rate', result.pitch_rate.get('max', 0))
                    
                    event = {
                        'file': csv_file.name,
                        'max_g': max_g_value if max_g_value else 0,
                        'max_roll_rate': max_roll_value if max_roll_value else 0,
                        'max_pitch_rate': max_pitch_value if max_pitch_value else 0,
                        'status': result.status,
                        'severity': result.severity,
                        'weight_kg': weight_kg,
                        'is_hard_landing': is_hl
                    }
                    all_events.append(event)
                
                hl_count = sum(1 for r in analysis_results if r.status != 'NORMAL')
                max_g_in_file = max((result.vertical_accel.get('max_g', 0) if result.vertical_accel and isinstance(result.vertical_accel, dict) else 0) for result in analysis_results)
                print(f" OK ({len(analysis_results)} voo(s), {hl_count} HL, Max: {max_g_in_file:.3f}G)")
            else:
                print(" OK (nenhum voo detectado)")
        
        except Exception as e:
            print(f" ERRO: {e}")
            continue
    
    print()
    print(f"[INFO] Total de eventos coletados: {len(all_events)}")
    print()
    
    if not all_events:
        print("[AVISO] Nenhum evento para analisar")
        return
    
    # Criar Advanced Analytics
    analytics = AdvancedAnalytics()
    
    # Análise estatística
    print("="*80)
    print("ANALISE ESTATISTICA")
    print("="*80)
    
    g_values = [e.get('max_g', 0) for e in all_events if 'max_g' in e]
    stats = analytics.calculate_comprehensive_statistics(g_values)
    
    print(f"Media:              {stats.mean:.3f}G")
    print(f"Mediana:            {stats.median:.3f}G")
    print(f"Desvio Padrao:      {stats.std_dev:.3f}G")
    print(f"Minimo:             {stats.min_value:.3f}G")
    print(f"Maximo:             {stats.max_value:.3f}G")
    print(f"Percentil 95:       {stats.percentile_95:.3f}G")
    print(f"Percentil 99:       {stats.percentile_99:.3f}G")
    print(f"Coef. Variacao:     {stats.coefficient_variation:.1f}%")
    print(f"Outliers:           {stats.outliers_count}")
    print()
    
    # Análise de tendências
    print("="*80)
    print("ANALISE DE TENDENCIAS")
    print("="*80)
    
    trend = analytics.analyze_trends(all_events, 'max_g')
    print(f"Direcao:            {trend.trend_direction}")
    print(f"Taxa de Mudanca:    {trend.change_rate:+.2f}%")
    print(f"Confianca (R2):     {trend.confidence:.1f}%")
    print(f"Nivel de Alerta:    {trend.warning_level}")
    print(f"Slope:              {trend.slope:.6f}")
    print(f"\nPrevisao: {trend.prediction}")
    print()
    
    # Avaliação de risco
    print("="*80)
    print("AVALIACAO DE RISCO")
    print("="*80)
    
    risk = analytics.assess_risk(all_events, 'E190')
    print(f"Nivel de Risco:     {risk.risk_level}")
    print(f"Score de Risco:     {risk.risk_score}/100")
    print()
    
    if risk.contributing_factors:
        print("Fatores Contribuintes:")
        for factor in risk.contributing_factors:
            print(f"  - {factor['factor']}")
            print(f"    Valor: {factor['value']} | Impacto: {factor['impact']} | Peso: {factor['weight']}")
        print()
    
    if risk.mitigation_actions:
        print("Acoes de Mitigacao:")
        for i, action in enumerate(risk.mitigation_actions, 1):
            # Remove emojis
            clean_action = action.replace("🔴", "[CRITICO]").replace("📋", "[INSP]").replace("🔍", "[INV]")
            clean_action = clean_action.replace("👨‍✈️", "[TREIN]").replace("⚙️", "[SYS]").replace("⚠️", "[ATENC]")
            clean_action = clean_action.replace("📊", "[MONIT]").replace("📝", "[DOC]").replace("✅", "[OK]")
            clean_action = clean_action.replace("📈", "[TREND]").replace("🎯", "[PROG]").replace("📉", "[ANAL]")
            print(f"  {i}. {clean_action}")
        print()
    
    # Identificar padrões
    print("="*80)
    print("PADROES IDENTIFICADOS")
    print("="*80)
    
    patterns = analytics.identify_patterns(all_events)
    
    print("Distribuicao de Severidade:")
    for severity, count in patterns['severity_distribution'].items():
        pct = (count / len(all_events) * 100) if all_events else 0
        print(f"  - {severity:10s}: {count:3d} ({pct:5.1f}%)")
    print()
    
    if patterns.get('anomalies'):
        print(f"Anomalias Detectadas: {len(patterns['anomalies'])}")
        for anomaly in patterns['anomalies'][:5]:  # Mostrar top 5
            print(f"  - Evento #{anomaly['index']}: {anomaly['value']:.3f}G "
                  f"({anomaly['deviation']:.1f} desvios padrao)")
        print()
    
    # Gerar resumo executivo (sem print - vai direto para arquivo)
    print("="*80)
    print()
    print("[INFO] Gerando resumo executivo...")
    summary = analytics.generate_executive_summary(all_events, 'E190')
    print("[OK] Resumo gerado")
    print()
    
    # Salvar relatório
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"relatorio_avancado_e190_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(summary)
        f.write("\n\n")
        f.write("="*80 + "\n")
        f.write("DETALHAMENTO COMPLETO\n")
        f.write("="*80 + "\n\n")
        
        f.write("ESTATÍSTICAS DESCRITIVAS:\n")
        f.write(f"  Média: {stats.mean:.3f}G\n")
        f.write(f"  Mediana: {stats.median:.3f}G\n")
        f.write(f"  Desvio Padrão: {stats.std_dev:.3f}G\n")
        f.write(f"  Min/Max: {stats.min_value:.3f}G / {stats.max_value:.3f}G\n")
        f.write(f"  P25/P50/P75: {stats.percentile_25:.3f}G / {stats.percentile_50:.3f}G / {stats.percentile_75:.3f}G\n")
        f.write(f"  P95/P99: {stats.percentile_95:.3f}G / {stats.percentile_99:.3f}G\n")
        f.write(f"  Coef. Variação: {stats.coefficient_variation:.1f}%\n")
        f.write(f"  Outliers: {stats.outliers_count}\n\n")
        
        f.write("ANÁLISE DE TENDÊNCIAS:\n")
        f.write(f"  Direção: {trend.trend_direction}\n")
        f.write(f"  Taxa de Mudança: {trend.change_rate:+.2f}%\n")
        f.write(f"  Confiança (R²): {trend.confidence:.1f}%\n")
        f.write(f"  Slope: {trend.slope:.6f}\n")
        f.write(f"  Nível de Alerta: {trend.warning_level}\n")
        f.write(f"  Previsão: {trend.prediction}\n\n")
        
        f.write("AVALIAÇÃO DE RISCO:\n")
        f.write(f"  Nível: {risk.risk_level}\n")
        f.write(f"  Score: {risk.risk_score}/100\n\n")
        
        if risk.contributing_factors:
            f.write("  Fatores Contribuintes:\n")
            for factor in risk.contributing_factors:
                f.write(f"    • {factor['factor']}\n")
                f.write(f"      Valor: {factor['value']} | Impacto: {factor['impact']}\n")
            f.write("\n")
        
        f.write("  Ações de Mitigação:\n")
        for action in risk.mitigation_actions:
            f.write(f"    • {action}\n")
        f.write("\n")
        
        f.write("  Requisitos de Monitoramento:\n")
        for req in risk.monitoring_requirements:
            f.write(f"    • {req}\n")
        f.write("\n")
        
        f.write("PADRÕES IDENTIFICADOS:\n")
        f.write("  Distribuição de Severidade:\n")
        for severity, count in patterns['severity_distribution'].items():
            pct = (count / len(all_events) * 100) if all_events else 0
            f.write(f"    • {severity}: {count} ({pct:.1f}%)\n")
        f.write("\n")
        
        if patterns.get('anomalies'):
            f.write(f"  Anomalias: {len(patterns['anomalies'])}\n")
            for anomaly in patterns['anomalies']:
                f.write(f"    • Evento #{anomaly['index']}: {anomaly['value']:.3f}G "
                       f"({anomaly['deviation']:.1f}σ)\n")
    
    print(f"[OK] Relatório salvo em: {report_file}")
    print()
    print("="*80)


if __name__ == "__main__":
    main()

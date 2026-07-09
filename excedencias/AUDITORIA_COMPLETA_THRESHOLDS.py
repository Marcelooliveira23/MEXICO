"""
AUDITORIA COMPLETA DE THRESHOLDS - TODAS AS ANÁLISES
Gera documentação consolidada com TODOS os parâmetros de TODAS as análises para comparação com manuais AMM

Sistema: Aircraft Inspection Analysis System v0.1.0
Data: 05 de Fevereiro de 2026
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.hard_landing_analyzer import HardLandingAnalyzer
from services.flap_overspeed_analyzer import FlapAnalyzer
from services.lg_down_overspeed_analyzer import LGDownOverspeedAnalyzer
from services.overweight_landing_analyzer import OverweightLandingAnalyzer
from services.vmo_analyzer import VmoAnalyzer
from services.turbulence_analyzer import TurbulenceAnalyzer
from services.over_g_analyzer import OverGAnalyzer
from models.aircraft_model import AircraftModelRegistry


class ThresholdAuditor:
    """Audita e documenta todos os thresholds de todas as análises"""
    
    MODELS = [
        'e145', 'e170', 'e175', 'e190', 'e195',
        'e175_e2', 'e190_e2', 'e195_e2'
    ]
    
    def __init__(self):
        self.hard_landing = HardLandingAnalyzer()
        self.flap = FlapAnalyzer()
        self.lg = LGDownOverspeedAnalyzer()
        self.overweight = OverweightLandingAnalyzer()
        self.vmo = VmoAnalyzer()
        self.turbulence = TurbulenceAnalyzer()
        self.overg = OverGAnalyzer()
    
    def generate_full_report(self) -> str:
        """Gera relatório completo com todos os thresholds"""
        
        report = []
        report.append("=" * 100)
        report.append("  ESPECIFICAÇÕES TÉCNICAS COMPLETAS - TODAS AS ANÁLISES")
        report.append("  Sistema de Inspeção de Aeronaves Mexicana - AIAS v0.1.0")
        report.append("=" * 100)
        report.append("")
        report.append("Data: 05 de Fevereiro de 2026")
        report.append("Modelos Auditados: 8 (E145, E170, E175, E190, E195, E175-E2, E190-E2, E195-E2)")
        report.append("")
        
        for model in self.MODELS:
            report.append("\n" + "=" * 100)
            report.append(f"  MODELO: {model.upper()}")
            report.append("=" * 100)
            
            # Especificações básicas
            report.extend(self._get_basic_specs(model))
            
            # 1. Hard Landing
            report.extend(self._get_hard_landing_specs(model))
            
            # 2. Flap Overspeed
            report.extend(self._get_flap_specs(model))
            
            # 3. Landing Gear Overspeed
            report.extend(self._get_lg_specs(model))
            
            # 4. Overweight Landing
            report.extend(self._get_overweight_specs(model))
            
            # 5. VMO/MMO
            report.extend(self._get_vmo_specs(model))
            
            # 6. Turbulence
            report.extend(self._get_turbulence_specs(model))
            
            # 7. Over-G
            report.extend(self._get_overg_specs(model))
        
        # Resumo comparativo
        report.extend(self._get_comparative_summary())
        
        return "\n".join(report)
    
    def _get_basic_specs(self, model: str) -> list:
        """Especificações básicas do modelo"""
        try:
            specs = AircraftModelRegistry.get_model(model)
            return [
                "",
                "┌─────────────────────────────────────────────────────────────────────────────────┐",
                "│ ESPECIFICAÇÕES BÁSICAS                                                          │",
                "└─────────────────────────────────────────────────────────────────────────────────┘",
                "",
                f"  Família: {specs.family_name}",
                f"  MTOW (Maximum Takeoff Weight):    {specs.mtow:>8.0f} lb  ({specs.mtow/2.20462:>8.0f} kg)",
                f"  MLW  (Maximum Landing Weight):    {specs.mlw:>8.0f} lb  ({specs.mlw/2.20462:>8.0f} kg)",
                f"  MZFW (Maximum Zero Fuel Weight):  {specs.mzfw:>8.0f} lb  ({specs.mzfw/2.20462:>8.0f} kg)",
                f"  OEW  (Operating Empty Weight):    {specs.oew:>8.0f} lb  ({specs.oew/2.20462:>8.0f} kg)",
                f"  PDF Hard Landing: {specs.pdf_hard_landing}",
                ""
            ]
        except Exception as e:
            return [f"  ⚠️  Erro ao obter specs: {e}", ""]
    
    def _get_hard_landing_specs(self, model: str) -> list:
        """Thresholds de Hard Landing"""
        lines = [
            "┌─────────────────────────────────────────────────────────────────────────────────┐",
            "│ 1. HARD LANDING (AMM 05-50-03)                                                 │",
            "└─────────────────────────────────────────────────────────────────────────────────┘",
            ""
        ]
        
        # Peso típico de landing (85% MLW)
        try:
            specs = AircraftModelRegistry.get_model(model)
            weight_kg = (specs.mlw * 0.453592) * 0.85
            
            # Vertical Acceleration
            if model == 'e145':
                # E145 usa threshold único
                threshold_val = self.hard_landing.interpolate_threshold(
                    weight_kg, 
                    self.hard_landing.VERT_ACCEL_THRESHOLDS_E145['threshold']
                )
                lines.append(f"  📊 VERTICAL ACCELERATION (Peso típico: {weight_kg:.0f} kg / 85% MLW):")
                lines.append(f"     Threshold: {threshold_val:.3f} G")
                lines.append(f"     Referência: AMM 05-50-02 Figure 602")
            else:
                vert = self.hard_landing.get_vertical_accel_thresholds(model, weight_kg)
                lines.append(f"  📊 VERTICAL ACCELERATION (Peso típico: {weight_kg:.0f} kg / 85% MLW):")
                lines.append(f"     LOW:    {vert['low']:.3f} G")
                lines.append(f"     HIGH:   {vert['high']:.3f} G")
                lines.append(f"     ENGINE: {vert['engine']:.3f} G")
                lines.append(f"     Referência: AMM 05-50-03 Figure 607")
            
            # Pitch Rate
            pitch = self.hard_landing.get_pitch_thresholds(model)
            lines.append(f"  📐 PITCH RATE:")
            if isinstance(pitch, dict):
                if 'low' in pitch:
                    lines.append(f"     LOW:  {pitch['low']:.2f} deg/s")
                    lines.append(f"     HIGH: {pitch['high']:.2f} deg/s")
                    if 'n2_conditional' in pitch:
                        lines.append(f"     N2≥75%: {pitch['n2_conditional']:.2f} deg/s")
                else:
                    lines.append(f"     Threshold: {pitch['threshold']:.2f} deg/s")
            lines.append(f"     Referência: AMM 05-50-03 Figure 609")
            
            # Roll Rate
            # Roll Rate (não aplicável para E145)
            if model != 'e145':
                try:
                    # Para outros modelos, roll é calculado pelo analyze_roll_rate
                    # mas não temos método específico get_roll_thresholds
                    # então pulamos por enquanto
                    lines.append(f"  🔄 ROLL RATE:")
                    lines.append(f"     (Calculado dinamicamente durante análise)")
                    lines.append(f"     Referência: AMM 05-50-03 Figure 608")
                except:
                    pass
            lines.append("")
            
        except Exception as e:
            lines.append(f"  ⚠️  Erro: {e}")
            lines.append("")
        
        return lines
    
    def _get_flap_specs(self, model: str) -> list:
        """Thresholds de Flap Overspeed"""
        lines = [
            "┌─────────────────────────────────────────────────────────────────────────────────┐",
            "│ 2. FLAP OVERSPEED (AMM 05-50-05 / 05-50-13)                                    │",
            "└─────────────────────────────────────────────────────────────────────────────────┘",
            ""
        ]
        
        flap_speeds = self.flap.get_flap_speeds(model)
        lines.append(f"  ✈️  FLAP SPEED LIMITS (KIAS):")
        
        for key, value in flap_speeds.items():
            if key != 'inspection_threshold':
                lines.append(f"     {key.upper().replace('_', ' ')}: {value} KIAS")
        
        if 'inspection_threshold' in flap_speeds:
            lines.append(f"     ⚠️  Inspection Threshold: {flap_speeds['inspection_threshold']} KIAS")
        
        lines.append(f"     Referência: AMM 05-50-05 / 05-50-13")
        lines.append("")
        
        return lines
    
    def _get_lg_specs(self, model: str) -> list:
        """Thresholds de Landing Gear Overspeed"""
        lines = [
            "┌─────────────────────────────────────────────────────────────────────────────────┐",
            "│ 3. LANDING GEAR OVERSPEED (VLE - Velocity Landing Gear Extended)               │",
            "└─────────────────────────────────────────────────────────────────────────────────┘",
            ""
        ]
        
        vle = self.lg.VLE_LIMITS.get(model, 250)
        lines.append(f"  🛬 VLE (Maximum speed with gear down): {vle} KIAS")
        lines.append(f"     Referência: AFM Limitations Section")
        lines.append("")
        
        return lines
    
    def _get_overweight_specs(self, model: str) -> list:
        """Thresholds de Overweight Landing"""
        lines = [
            "┌─────────────────────────────────────────────────────────────────────────────────┐",
            "│ 4. OVERWEIGHT LANDING (MLW - Maximum Landing Weight)                           │",
            "└─────────────────────────────────────────────────────────────────────────────────┘",
            ""
        ]
        
        mlw = self.overweight.get_mlw_for_model(model)
        lines.append(f"  ⚖️  MLW (Maximum Landing Weight): {mlw:.0f} lb ({mlw/2.20462:.0f} kg)")
        lines.append(f"     Qualquer landing > MLW requer inspeção estrutural")
        lines.append(f"     Referência: AFM Limitations / AMM Weight & Balance")
        lines.append("")
        
        return lines
    
    def _get_vmo_specs(self, model: str) -> list:
        """Thresholds de VMO/MMO"""
        lines = [
            "┌─────────────────────────────────────────────────────────────────────────────────┐",
            "│ 5. VMO/MMO OVERSPEED (Maximum Operating Speed)                                 │",
            "└─────────────────────────────────────────────────────────────────────────────────┘",
            ""
        ]
        
        vmo_data = self.vmo.get_vmo_thresholds(model)
        lines.append(f"  🚀 VMO (Velocity Maximum Operating):  {vmo_data['vmo']} KIAS")
        lines.append(f"  🌐 MMO (Mach Maximum Operating):      {vmo_data['mmo']} Mach")
        lines.append(f"     Inspection Threshold VMO:          {vmo_data['inspection_threshold_vmo']} KIAS")
        lines.append(f"     Inspection Threshold MMO:          {vmo_data['inspection_threshold_mmo']} Mach")
        lines.append(f"     Referência: AMM 05-50-07 / AFM Limitations")
        lines.append("")
        
        return lines
    
    def _get_turbulence_specs(self, model: str) -> list:
        """Thresholds de Turbulence"""
        lines = [
            "┌─────────────────────────────────────────────────────────────────────────────────┐",
            "│ 6. TURBULENCE (G-Load Exceedances)                                             │",
            "└─────────────────────────────────────────────────────────────────────────────────┘",
            ""
        ]
        
        # Converter model para aircraft_id usado no turbulence analyzer
        aircraft_id = 'e145' if model == 'e145' else ('e2' if 'e2' in model else 'e1')
        thresholds = self.turbulence.DEFAULT_THRESHOLDS.get(aircraft_id, {})
        
        max_pos_g = thresholds.get('max_positive_g', 2.5)
        max_neg_g = thresholds.get('max_negative_g', -1.0)
        max_speed = thresholds.get('max_turbulence_speed', 280)
        
        lines.append(f"  🌪️  TURBULENCE G-LOAD LIMITS:")
        lines.append(f"     Max Positive G: +{max_pos_g:.1f} G")
        lines.append(f"     Max Negative G: {max_neg_g:.1f} G")
        if max_speed:
            lines.append(f"     Max Turbulence Penetration Speed: {max_speed} KIAS")
        lines.append(f"     Referência: AMM Structural Inspection")
        lines.append("")
        
        return lines
    
    def _get_overg_specs(self, model: str) -> list:
        """Thresholds de Over-G"""
        lines = [
            "┌─────────────────────────────────────────────────────────────────────────────────┐",
            "│ 7. OVER-G MANEUVER (Excessive Maneuvering Loads)                               │",
            "└─────────────────────────────────────────────────────────────────────────────────┘",
            ""
        ]
        
        # Converter model ID para formato usado no over-g analyzer
        model_key = model.upper().replace('_', '-')
        if model_key == 'E145':
            model_key = 'E170'  # E145 usa mesmo threshold de E170
        
        thresholds = self.overg.OVER_G_THRESHOLDS.get(model_key, {})
        
        if thresholds:
            lines.append(f"  ⚡ OVER-G THRESHOLDS:")
            lines.append(f"     Max Positive G: +{thresholds['positive']:.1f} G")
            lines.append(f"     Max Negative G: {thresholds['negative']:.1f} G")
            lines.append(f"     Sustained Duration: {thresholds['sustained_duration']:.1f} s")
            lines.append(f"     Moderate Threshold: {thresholds['moderate_threshold']:.1f} G")
            lines.append(f"     High Threshold: {thresholds['high_threshold']:.1f} G")
        else:
            lines.append(f"  ⚠️  Thresholds não definidos para {model}")
        
        lines.append(f"     Referência: AMM 05-50-02")
        lines.append("")
        
        return lines
    
    def _get_comparative_summary(self) -> list:
        """Resumo comparativo entre modelos"""
        lines = [
            "\n" + "=" * 100,
            "  RESUMO COMPARATIVO - THRESHOLDS POR FAMÍLIA",
            "=" * 100,
            "",
            "┌────────────────────────────────────────────────────────────────────────────────────────────┐",
            "│ HARD LANDING - VERTICAL ACCELERATION                                                       │",
            "└────────────────────────────────────────────────────────────────────────────────────────────┘",
            "",
            "Modelo      | Peso (kg) | LOW (G) | HIGH (G) | ENGINE (G) | PDF Reference",
            "------------|-----------|---------|----------|------------|------------------"
        ]
        
        for model in self.MODELS:
            try:
                specs = AircraftModelRegistry.get_model(model)
                weight_kg = (specs.mlw * 0.453592) * 0.85
                
                if model == 'e145':
                    threshold_val = self.hard_landing.interpolate_threshold(
                        weight_kg,
                        self.hard_landing.VERT_ACCEL_THRESHOLDS_E145['threshold']
                    )
                    lines.append(f"{model.upper():<11} | {weight_kg:>9.0f} | {threshold_val:>7.3f} | N/A      | N/A        | {specs.pdf_hard_landing}")
                else:
                    vert = self.hard_landing.get_vertical_accel_thresholds(model, weight_kg)
                    lines.append(f"{model.upper():<11} | {weight_kg:>9.0f} | {vert['low']:>7.3f} | {vert['high']:>8.3f} | {vert['engine']:>10.3f} | {specs.pdf_hard_landing}")
            except Exception as e:
                lines.append(f"{model.upper():<11} | ERRO: {e}")
        
        lines.extend([
            "",
            "┌────────────────────────────────────────────────────────────────────────────────────────────┐",
            "│ VMO/MMO - MAXIMUM OPERATING SPEED                                                          │",
            "└────────────────────────────────────────────────────────────────────────────────────────────┘",
            "",
            "Modelo      | VMO (KIAS) | MMO (Mach) | Insp VMO | Insp MMO",
            "------------|------------|------------|----------|----------"
        ])
        
        for model in self.MODELS:
            vmo_data = self.vmo.get_vmo_thresholds(model)
            lines.append(
                f"{model.upper():<11} | {vmo_data['vmo']:>10} | {vmo_data['mmo']:>10.2f} | "
                f"{vmo_data['inspection_threshold_vmo']:>8} | {vmo_data['inspection_threshold_mmo']:>8.2f}"
            )
        
        lines.extend([
            "",
            "┌────────────────────────────────────────────────────────────────────────────────────────────┐",
            "│ MLW - MAXIMUM LANDING WEIGHT                                                               │",
            "└────────────────────────────────────────────────────────────────────────────────────────────┘",
            "",
            "Modelo      | MLW (lb)   | MLW (kg)   | Típico Landing (85% MLW)",
            "------------|------------|------------|---------------------------"
        ])
        
        for model in self.MODELS:
            try:
                specs = AircraftModelRegistry.get_model(model)
                mlw_kg = specs.mlw / 2.20462
                typical_kg = mlw_kg * 0.85
                lines.append(
                    f"{model.upper():<11} | {specs.mlw:>10.0f} | {mlw_kg:>10.0f} | {typical_kg:>10.0f} kg"
                )
            except:
                pass
        
        lines.extend([
            "",
            "=" * 100,
            "  FIM DO RELATÓRIO",
            "=" * 100,
            "",
            "Documento gerado automaticamente pela Auditoria de Thresholds v1.0",
            "Sistema de Inspeção de Aeronaves Mexicana - AIAS v0.1.0",
            "Data: 05 de Fevereiro de 2026",
            ""
        ])
        
        return lines


def main():
    """Executa auditoria e gera relatório"""
    print("=" * 100)
    print("  AUDITORIA COMPLETA DE THRESHOLDS - INICIANDO")
    print("=" * 100)
    print()
    
    auditor = ThresholdAuditor()
    
    print(">> Gerando relatorio completo...")
    report = auditor.generate_full_report()
    
    # Salvar em arquivo TXT
    output_file = Path("ESPECIFICACOES_COMPLETAS_TODAS_ANALISES.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"OK - Relatorio salvo em: {output_file}")
    print(f"Tamanho: {len(report.split(chr(10)))} linhas")
    print()
    print("=" * 100)
    print("  AUDITORIA CONCLUÍDA")
    print("=" * 100)
    
    # Mostrar preview
    print("\nPREVIEW (primeiras 50 linhas):")
    print("-" * 100)
    for line in report.split('\n')[:50]:
        print(line)
    print("-" * 100)
    print(f"... ({len(report.split(chr(10))) - 50} linhas restantes no arquivo)")


if __name__ == '__main__':
    main()


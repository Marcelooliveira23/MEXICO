"""
Professional Hard Landing Analysis Graph Generator
Generates AMM-style professional graphs for Hard Landing inspection analysis
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import numpy as np

from utils.logger import logger

class HardLandingGraphGenerator:
    """Professional AMM-style graph generator for Hard Landing analysis"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize professional graph generator
        
        Args:
            output_dir: Directory to save graphs (default: graficos_hard_landing)
        """
        self.output_dir = output_dir or Path("graficos_hard_landing")
        self.output_dir.mkdir(exist_ok=True)
        
        # Professional graph styling (AMM-like)
        plt.rcParams['figure.facecolor'] = 'white'
        plt.rcParams['axes.facecolor'] = '#F8F9FA'
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.alpha'] = 0.3
        plt.rcParams['grid.linestyle'] = '--'
        plt.rcParams['font.family'] = 'Arial'
        plt.rcParams['font.size'] = 10
        
    def generate_all_graphs(
        self,
        df: pd.DataFrame,
        analysis_results: List,
        aircraft_name: str,
        tail_number: str = "N/A"
    ) -> List[Path]:
        """
        Gera todos os gráficos de Hard Landing
        
        Args:
            df: DataFrame com dados de voo
            analysis_results: Resultados da análise HardLandingAnalyzer
            aircraft_name: Nome da aeronave
            tail_number: Matrícula
            
        Returns:
            Lista de caminhos dos arquivos gerados
        """
        generated_files = []
        
        try:
            # Sanitizar tail_number para nome de arquivo válido
            safe_tail = tail_number.replace('/', '-').replace('\\', '-').replace(':', '-')
            
            # Timestamp para nome dos arquivos
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Verificar se é E145 - gerar gráfico estilo AMM Figure 602
            if 'E145' in aircraft_name or 'E135' in aircraft_name:
                weight_g_file = self.generate_e145_weight_vs_g_graph(
                    df, analysis_results, aircraft_name, safe_tail, timestamp
                )
                if weight_g_file:
                    generated_files.append(weight_g_file)
            
            # 1. Gráfico de aceleração vertical
            accel_file = self.generate_vertical_acceleration_graph(
                df, analysis_results, aircraft_name, safe_tail, timestamp
            )
            if accel_file:
                generated_files.append(accel_file)
            
            # 2. Gráfico de pitch e roll
            attitude_file = self.generate_attitude_graph(
                df, aircraft_name, safe_tail, timestamp
            )
            if attitude_file:
                generated_files.append(attitude_file)
            
            # 3. Gráfico de altitude e velocidade
            alt_speed_file = self.generate_altitude_speed_graph(
                df, aircraft_name, safe_tail, timestamp
            )
            if alt_speed_file:
                generated_files.append(alt_speed_file)
            
            # 4. Gráfico combinado (overview)
            overview_file = self.generate_overview_graph(
                df, aircraft_name, safe_tail, timestamp
            )
            if overview_file:
                generated_files.append(overview_file)
            
            msg = f"Generated {len(generated_files)} graphs"
            logger.info(f"{msg} for Hard Landing analysis")
            
        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating graphs: {e}", exc_info=True)
        
        return generated_files
    
    def generate_vertical_acceleration_graph(
        self,
        df: pd.DataFrame,
        analysis_results: List,
        aircraft_name: str,
        tail_number: str,
        timestamp: str
    ) -> Optional[Path]:
        """Generate professional AMM-style vertical acceleration graph"""
        try:
            # Find vertical acceleration column
            accel_col = self._find_column(
                df, ['vertical_acceleration', 'vert_accel', 'normaccel']
            )
            if not accel_col:
                logger.warning("Vertical acceleration column not found")
                return None
            
            # Create professional figure
            fig, ax = plt.subplots(figsize=(16, 9), facecolor='white')
            
            # Extract data
            time_index = np.arange(len(df))
            accel_data = df[accel_col].values
            
            # Plot main data with professional styling
            ax.plot(
                time_index, accel_data,
                color='#1E88E5', linewidth=1.5,
                label='Normal Acceleration',
                zorder=3
            )
            
            # Fill area under curve for context
            ax.fill_between(
                time_index, 0, accel_data,
                alpha=0.15, color='#1E88E5',
                zorder=1
            )
            
            # Add threshold lines with professional styling
            if analysis_results:
                vert = None
                for result in analysis_results:
                    if hasattr(result, 'vertical_accel') and result.vertical_accel:
                        vert = result.vertical_accel
                        break

                if vert and 'thresholds' in vert:
                    thresholds = vert['thresholds']

                    # Green zone (normal)
                    ax.axhspan(0, thresholds.get('low', 1.8),
                              alpha=0.1, color='green',
                              label='NORMAL OPERATION', zorder=0)

                    # Yellow zone (low threshold)
                    if 'low' in thresholds and 'high' in thresholds:
                        low_val = thresholds['low']
                        high_val = thresholds['high']
                        ax.axhspan(low_val, high_val,
                                  alpha=0.15, color='#FFA500',
                                  label='PHASE I INSPECTION', zorder=0)
                        ax.axhline(low_val, color='#FF8C00',
                                  linestyle='--', linewidth=2.5,
                                  label=f'LOW THRESHOLD: {low_val:.3f}G',
                                  zorder=2)

                    # Red zone (high threshold)
                    if 'high' in thresholds and 'engine' in thresholds:
                        high_val = thresholds['high']
                        eng_val = thresholds['engine']
                        ax.axhspan(high_val, eng_val,
                                  alpha=0.15, color='#FF4444',
                                  label='PHASE II INSPECTION', zorder=0)
                        ax.axhline(high_val, color='#D32F2F',
                                  linestyle='--', linewidth=2.5,
                                  label=f'HIGH THRESHOLD: {high_val:.3f}G',
                                  zorder=2)

                    # Dark red zone (engine inspection)
                    if 'engine' in thresholds:
                        eng_val = thresholds['engine']
                        ax.axhspan(eng_val, ax.get_ylim()[1],
                                  alpha=0.2, color='#8B0000',
                                  label='ENGINE INSPECTION', zorder=0)
                        ax.axhline(eng_val, color='#8B0000',
                                  linestyle='--', linewidth=2.5,
                                  label=f'ENGINE LIMIT: {eng_val:.3f}G',
                                  zorder=2)

                    # Mark peak with professional annotation
                    if 'max_g' in vert and vert['max_g']:
                        valid_data = df[accel_col].dropna()
                        if len(valid_data) > 0:
                            max_idx = valid_data.idxmax()
                            max_val = vert['max_g']

                            # Peak marker
                            ax.plot(max_idx, max_val, 'r*',
                                   markersize=22, markeredgecolor='darkred',
                                   markeredgewidth=2, zorder=5)

                            # Professional annotation box
                            bbox_props = dict(
                                boxstyle='round,pad=0.5',
                                facecolor='#FFE6E6',
                                edgecolor='#D32F2F',
                                linewidth=2
                            )
                            ax.annotate(
                                f'PEAK: {max_val:.3f}G',
                                xy=(max_idx, max_val),
                                xytext=(max_idx + len(df)*0.05, max_val),
                                fontsize=11, fontweight='bold',
                                color='#8B0000',
                                bbox=bbox_props,
                                arrowprops=dict(
                                    arrowstyle='->',
                                    color='#D32F2F',
                                    linewidth=2
                                ),
                                zorder=6
                            )
            
            # Professional labels and title
            ax.set_xlabel('Time Index (samples)', fontsize=13, fontweight='bold')
            ax.set_ylabel('Normal Acceleration (G)', fontsize=13, fontweight='bold')
            
            title = f'HARD LANDING ANALYSIS - VERTICAL ACCELERATION\\n{aircraft_name} | Tail: {tail_number}'
            ax.set_title(title, fontsize=15, fontweight='bold', pad=20)
            
            # Professional legend
            ax.legend(
                loc='center left',
                bbox_to_anchor=(1.02, 0.5),
                fontsize=9,
                framealpha=0.95,
                edgecolor='#666',
                fancybox=True
            )
            
            # Grid styling
            ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
            ax.set_axisbelow(True)
            
            # Add AMM reference note
            fig.text(0.99, 0.01, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")} | AMM 05-50-03',
                    ha='right', fontsize=8, style='italic', color='#666')
            
            # Save with high quality
            filename = f"vertical_accel_{tail_number}_{timestamp}.png"
            filepath = self.output_dir / filename
            fig.tight_layout(rect=[0, 0, 0.78, 1])
            fig.savefig(filepath, dpi=220, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            plt.close(fig)
            
            return filepath
            
        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating vertical acceleration graph: {e}")
            return None
    
    def generate_attitude_graph(
        self,
        df: pd.DataFrame,
        aircraft_name: str,
        tail_number: str,
        timestamp: str
    ) -> Optional[Path]:
        """Gera gráfico de pitch e roll"""
        try:
            pitch_col = self._find_column(df, ['pitch', 'theta'])
            roll_col = self._find_column(df, ['roll', 'phi', 'bank'])
            
            if not pitch_col and not roll_col:
                logger.warning("Colunas de pitch/roll não encontradas")
                return None
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
            time_index = range(len(df))
            
            # Pitch
            if pitch_col:
                ax1.plot(
                    time_index, df[pitch_col], 'g-',
                    linewidth=2, label='Pitch Angle'
                )
                ax1.axhline(
                    y=0, color='k', linestyle='-',
                    linewidth=0.5, alpha=0.5
                )
                ax1.set_ylabel(
                    'Pitch Angle (°)',
                    fontsize=12, fontweight='bold'
                )
                title = f'Pitch Attitude - {aircraft_name} ({tail_number})'
                ax1.set_title(title, fontsize=14, fontweight='bold')
                ax1.legend(loc='best')
                ax1.grid(True, alpha=0.3)
            
            # Roll
            if roll_col:
                ax2.plot(
                    time_index, df[roll_col], 'm-',
                    linewidth=2, label='Roll Angle'
                )
                ax2.axhline(
                    y=0, color='k', linestyle='-',
                    linewidth=0.5, alpha=0.5
                )
                ax2.set_ylabel(
                    'Roll Angle (°)',
                    fontsize=12, fontweight='bold'
                )
                title = f'Roll Attitude - {aircraft_name} ({tail_number})'
                ax2.set_title(title, fontsize=14, fontweight='bold')
                ax2.legend(loc='best')
                ax2.grid(True, alpha=0.3)
            
            ax2.set_xlabel('Sample Index', fontsize=12, fontweight='bold')
            
            # Salvar
            filename = f"attitude_{tail_number}_{timestamp}.png"
            filepath = self.output_dir / filename
            fig.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close(fig)
            
            return filepath
            
        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating attitude graph: {e}")
            return None
    
    def generate_altitude_speed_graph(
        self,
        df: pd.DataFrame,
        aircraft_name: str,
        tail_number: str,
        timestamp: str
    ) -> Optional[Path]:
        """Gera gráfico de altitude e velocidade"""
        try:
            alt_col = self._find_column(df, ['altitude', 'alt', 'alt_ft'])
            speed_col = self._find_column(
                df, ['airspeed', 'ias', 'kias', 'speed']
            )
            
            if not alt_col and not speed_col:
                msg = "Colunas de altitude/velocidade não encontradas"
                logger.warning(msg)
                return None
            
            fig, ax1 = plt.subplots(figsize=(14, 8))
            time_index = range(len(df))
            
            # Altitude no eixo esquerdo
            if alt_col:
                color = 'tab:blue'
                ax1.set_xlabel(
                    'Sample Index', fontsize=12, fontweight='bold'
                )
                ax1.set_ylabel(
                    'Altitude (ft)', color=color,
                    fontsize=12, fontweight='bold'
                )
                ax1.plot(
                    time_index, df[alt_col], color=color,
                    linewidth=2, label='Altitude'
                )
                ax1.tick_params(axis='y', labelcolor=color)
                ax1.grid(True, alpha=0.3)
            
            # Velocidade no eixo direito
            if speed_col:
                ax2 = ax1.twinx()
                color = 'tab:red'
                ax2.set_ylabel(
                    'Airspeed (KIAS)', color=color,
                    fontsize=12, fontweight='bold'
                )
                ax2.plot(
                    time_index, df[speed_col], color=color,
                    linewidth=2, label='Airspeed'
                )
                ax2.tick_params(axis='y', labelcolor=color)
            
            title = f'Altitude and Airspeed - {aircraft_name} ({tail_number})'
            ax1.set_title(title, fontsize=14, fontweight='bold')
            
            # Salvar
            filename = f"alt_speed_{tail_number}_{timestamp}.png"
            filepath = self.output_dir / filename
            fig.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close(fig)
            
            return filepath
            
        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating altitude/speed graph: {e}")
            return None
    
    def generate_overview_graph(
        self,
        df: pd.DataFrame,
        aircraft_name: str,
        tail_number: str,
        timestamp: str
    ) -> Optional[Path]:
        """Gera gráfico combinado com todos os parâmetros principais"""
        try:
            # Encontrar colunas
            accel_col = self._find_column(
                df, ['vertical_acceleration', 'vert_accel']
            )
            pitch_col = self._find_column(df, ['pitch', 'theta'])
            roll_col = self._find_column(df, ['roll', 'phi'])
            alt_col = self._find_column(df, ['altitude', 'alt'])
            
            if not any([accel_col, pitch_col, roll_col, alt_col]):
                logger.warning("Nenhuma coluna encontrada para overview")
                return None
            
            # Criar subplots
            num_plots = sum([
                bool(accel_col), bool(pitch_col),
                bool(roll_col), bool(alt_col)
            ])
            fig, axes = plt.subplots(
                num_plots, 1,
                figsize=(14, 4*num_plots),
                sharex=True
            )
            
            if num_plots == 1:
                axes = [axes]
            
            time_index = range(len(df))
            plot_idx = 0
            
            # Aceleração Vertical
            if accel_col:
                axes[plot_idx].plot(
                    time_index, df[accel_col], 'b-', linewidth=2
                )
                axes[plot_idx].set_ylabel(
                    'Vert. Accel (G)', fontweight='bold'
                )
                axes[plot_idx].grid(True, alpha=0.3)
                axes[plot_idx].set_title(
                    'Vertical Acceleration', fontweight='bold'
                )
                plot_idx += 1
            
            # Pitch
            if pitch_col:
                axes[plot_idx].plot(
                    time_index, df[pitch_col], 'g-', linewidth=2
                )
                axes[plot_idx].axhline(
                    y=0, color='k', linestyle='-',
                    linewidth=0.5, alpha=0.5
                )
                axes[plot_idx].set_ylabel('Pitch (°)', fontweight='bold')
                axes[plot_idx].grid(True, alpha=0.3)
                axes[plot_idx].set_title('Pitch Angle', fontweight='bold')
                plot_idx += 1
            
            # Roll
            if roll_col:
                axes[plot_idx].plot(
                    time_index, df[roll_col], 'm-', linewidth=2
                )
                axes[plot_idx].axhline(
                    y=0, color='k', linestyle='-',
                    linewidth=0.5, alpha=0.5
                )
                axes[plot_idx].set_ylabel('Roll (°)', fontweight='bold')
                axes[plot_idx].grid(True, alpha=0.3)
                axes[plot_idx].set_title('Roll Angle', fontweight='bold')
                plot_idx += 1
            
            # Altitude
            if alt_col:
                axes[plot_idx].plot(time_index, df[alt_col], 'r-', linewidth=2)
                axes[plot_idx].set_ylabel('Altitude (ft)', fontweight='bold')
                axes[plot_idx].grid(True, alpha=0.3)
                axes[plot_idx].set_title('Altitude', fontweight='bold')
                plot_idx += 1
            
            axes[-1].set_xlabel(
                'Sample Index', fontsize=12, fontweight='bold'
            )
            
            fig.suptitle(f'Hard Landing Analysis Overview - {aircraft_name} ({tail_number})', 
                        fontsize=16, fontweight='bold', y=0.995)
            
            plt.tight_layout()
            
            # Salvar
            filename = f"overview_{tail_number}_{timestamp}.png"
            filepath = self.output_dir / filename
            fig.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close(fig)
            
            return filepath
            
        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating overview graph: {e}")
            return None
    
    def generate_e145_weight_vs_g_graph(
        self,
        df: pd.DataFrame,
        analysis_results: List,
        aircraft_name: str,
        tail_number: str,
        timestamp: str
    ) -> Optional[Path]:
        """
        Generate E145 weight vs G-force graph (AMM Figure 602 style)
        Shows threshold curve and actual landing points
        """
        try:
            # E145 thresholds from AMM Table 4-1 (kg, G)
            E145_THRESHOLDS = [
                (12000, 2.300), (12200, 2.300), (12400, 2.266), (12600, 2.233),
                (12800, 2.200), (13000, 2.181), (13200, 2.162), (13400, 2.143),
                (13600, 2.125), (13800, 2.107), (14000, 2.089), (14500, 2.043),
                (15000, 1.999), (15500, 1.956), (16000, 1.915), (16500, 1.876),
                (17000, 1.839), (17500, 1.803), (18000, 1.769), (18500, 1.736),
                (19000, 1.704), (19500, 1.673), (20000, 1.644), (20500, 1.615),
                (21000, 1.587), (22000, 1.535), (24100, 1.492)
            ]
        
            # Create professional figure
            fig, ax = plt.subplots(figsize=(14, 10), facecolor='white')
        
            # Plot threshold curve
            weights = [w for w, g in E145_THRESHOLDS]
            g_forces = [g for w, g in E145_THRESHOLDS]
        
            ax.plot(
                weights, g_forces,
                color='#D32F2F', linewidth=3,
                marker='o', markersize=6,
                label='Hard Landing Threshold',
                zorder=3
            )
        
            # Fill area below threshold (safe zone)
            ax.fill_between(
                weights, 1.0, g_forces,
                alpha=0.15, color='green',
                label='Normal Operation Zone',
                zorder=1
            )
        
            # Fill area above threshold (inspection required)
            ax.fill_between(
                weights, g_forces, 2.5,
                alpha=0.15, color='red',
                label='Hard Landing - Inspection Required',
                zorder=1
            )
        
            # Plot actual landing data points if available
            if analysis_results:
                for idx, result in enumerate(analysis_results):
                    if hasattr(result, 'vertical_accel'):
                        vert = result.vertical_accel
                        max_g = vert.get('max_g', 0)
        
                        # Try to get weight from result or use default
                        weight_kg = 21772  # Default E145 MLW
                        if hasattr(result, 'weight'):
                            weight_kg = result.weight
        
                        # Determine color based on threshold exceedance
                        exceeded = vert.get('exceeded', False)
                        color = '#FF4444' if exceeded else '#4CAF50'
                        marker = 'X' if exceeded else 'o'
                        size = 200 if exceeded else 100
        
                        ax.scatter(
                            weight_kg, max_g,
                            c=color, s=size, marker=marker,
                            edgecolors='black', linewidths=1.5,
                            alpha=0.8, zorder=4
                        )
        
                        # Label the point
                        label_text = f'Flight {idx+1}\n{max_g:.3f}G'
                        ax.annotate(
                            label_text,
                            xy=(weight_kg, max_g),
                            xytext=(10, 10), textcoords='offset points',
                            fontsize=9, fontweight='bold',
                            bbox=dict(
                                boxstyle='round,pad=0.3',
                                facecolor='white',
                                edgecolor=color,
                                alpha=0.9
                            ),
                            zorder=5
                        )
        
            # Professional styling
            ax.set_xlabel('Landing Weight (kg)', fontsize=14, fontweight='bold')
            ax.set_ylabel('Normal Acceleration (G)', fontsize=14, fontweight='bold')
        
            title = (f'E145 HARD LANDING THRESHOLD - AMM Figure 602\n'
                    f'{aircraft_name} | Tail: {tail_number}')
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        
            # Set axis limits with padding
            ax.set_xlim(11500, 24500)
            ax.set_ylim(1.4, 2.4)
        
            # Grid styling
            ax.grid(True, alpha=0.4, linestyle='--', linewidth=0.8, which='major')
            ax.grid(True, alpha=0.2, linestyle=':', linewidth=0.5, which='minor')
            ax.minorticks_on()
            ax.set_axisbelow(True)
        
            # Legend
            ax.legend(loc='upper right', fontsize=11, framealpha=0.95,
                     edgecolor='#666', fancybox=True, shadow=True)
        
            # Add reference notes
            fig.text(0.02, 0.02, 
                    'Reference: AMM 05-50-02 Table 4-1 | E145 Hard Landing Inspection',
                    fontsize=9, style='italic', color='#666')
            fig.text(0.98, 0.02,
                    f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                    ha='right', fontsize=9, style='italic', color='#666')
        
            # Save with high quality
            filename = f"E145_weight_vs_g_{tail_number}_{timestamp}.png"
            filepath = self.output_dir / filename
            fig.savefig(filepath, dpi=200, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            plt.close(fig)
        
            logger.info(f"Generated E145 weight vs G graph: {filepath}")
            return filepath
        
        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating E145 weight vs G graph: {e}")
            return None
    
    @staticmethod
    def _find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """Encontra coluna no DataFrame (case-insensitive)"""
        df_cols_lower = {col.lower(): col for col in df.columns}
        for candidate in candidates:
            if candidate.lower() in df_cols_lower:
                return df_cols_lower[candidate.lower()]
        return None

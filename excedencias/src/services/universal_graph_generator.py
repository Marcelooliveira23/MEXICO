"""
Universal Graph Generator - Gráficos para Todos os Eventos
Versão 2.0 - Sistema Completo de Visualização
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.patches as mpatches  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
import pandas as pd  # noqa: E402
import numpy as np  # noqa: E402
from pathlib import Path  # noqa: E402
from datetime import datetime  # noqa: E402
from typing import Optional, List  # noqa: E402
from .parameter_validator import ValidationResult  # noqa: E402
from utils.logger import logger  # noqa: E402


class UniversalGraphGenerator:
    """
    Gerador universal de gráficos para todos os 6 tipos de eventos:
    1. Hard Landing
    2. Gear Overspeed
    3. Temperature Envelope
    4. Maximum Speed
    5. Flap Overspeed
    6. Overweight Landing
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        dense_mode: bool = False,
        language: str = "pt"
    ):
        """Inicializar gerador de gráficos"""
        self.output_dir = output_dir or Path("graficos_analise")
        self.output_dir.mkdir(exist_ok=True)

        self.dense_mode = dense_mode
        self.language = (language or "pt").lower()

        # Cores para status
        self.colors = {
            "OK": "#2ECC71",        # Verde
            "WARNING": "#F39C12",   # Laranja
            "CRITICAL": "#E74C3C",  # Vermelho
            "limit": "#3498DB",     # Azul
            "background": "#F5F7FA",  # Cinza claro
            "grid": "#D5DCE5",
            "text": "#1F2A37"
        }

        self.output_formats = ["png", "pdf", "svg"]

        self._configure_matplotlib()

        logger.info(
            f"Universal Graph Generator initialized: {self.output_dir}"
        )

    def generate_all_graphs(
        self,
        df: pd.DataFrame,
        validation_results: List[ValidationResult],
        aircraft_model: str,
        event_type: str,
        tail_number: str = "UNKNOWN"
    ) -> List[Path]:
        """
        Gerar todos os gráficos relevantes para um evento

        Args:
            df: DataFrame com dados de voo
            validation_results: Resultados da validação
            aircraft_model: Modelo da aeronave
            event_type: Tipo de evento
            tail_number: Matrícula da aeronave

        Returns:
            Lista de caminhos dos gráficos gerados
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        generated_files = []

        try:
            # Gráfico 1: Parâmetros vs Limites
            params_file = self.generate_parameters_vs_limits_graph(
                df, validation_results, aircraft_model,
                event_type, tail_number, timestamp
            )
            if params_file:
                generated_files.append(params_file)

            # Gráfico 2: Timeline dos parâmetros principais
            timeline_file = self.generate_timeline_graph(
                df, validation_results, aircraft_model,
                event_type, tail_number, timestamp
            )
            if timeline_file:
                generated_files.append(timeline_file)

            # Gráfico 3: Dashboard Overview
            dashboard_file = self.generate_dashboard_overview(
                df, validation_results, aircraft_model,
                event_type, tail_number, timestamp
            )
            if dashboard_file:
                generated_files.append(dashboard_file)

            # Gráficos específicos por tipo de evento
            if event_type == "hard_landing":
                hl_files = self.generate_hard_landing_specific_graphs(
                    df,
                    validation_results,
                    aircraft_model,
                    tail_number,
                    timestamp
                )
                generated_files.extend(hl_files)

            elif event_type == "gear_overspeed":
                gear_files = self.generate_gear_overspeed_specific_graphs(
                    df,
                    validation_results,
                    aircraft_model,
                    tail_number,
                    timestamp
                )
                generated_files.extend(gear_files)

            elif event_type == "temp_envelope":
                temp_files = self.generate_temperature_specific_graphs(
                    df,
                    validation_results,
                    aircraft_model,
                    tail_number,
                    timestamp
                )
                generated_files.extend(temp_files)

            elif event_type == "max_speed":
                speed_files = self.generate_max_speed_specific_graphs(
                    df,
                    validation_results,
                    aircraft_model,
                    tail_number,
                    timestamp
                )
                generated_files.extend(speed_files)
            elif event_type == "flap_overspeed":
                flap_files = self.generate_flap_overspeed_specific_graphs(
                    df,
                    validation_results,
                    aircraft_model,
                    tail_number,
                    timestamp
                )
                generated_files.extend(flap_files)
            elif event_type == "overweight_landing":
                weight_files = (
                    self.generate_overweight_landing_specific_graphs(
                        df,
                        validation_results,
                        aircraft_model,
                        tail_number,
                        timestamp
                    )
                )
                generated_files.extend(weight_files)

            logger.info(
                f"Generated {len(generated_files)} graphs for {event_type}"
            )

        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating graphs: {e}", exc_info=True)

        return generated_files

    def _configure_matplotlib(self) -> None:
        """Configurar estilo visual consistente e limpo"""
        title_size = 11 if self.dense_mode else 12
        label_size = 10 if self.dense_mode else 11
        tick_size = 8 if self.dense_mode else 9

        plt.rcParams.update({
            "figure.facecolor": self.colors["background"],
            "axes.facecolor": "#FFFFFF",
            "axes.edgecolor": "#CBD5E1",
            "axes.labelcolor": self.colors["text"],
            "xtick.color": self.colors["text"],
            "ytick.color": self.colors["text"],
            "text.color": self.colors["text"],
            "axes.titleweight": "bold",
            "axes.titlesize": title_size,
            "axes.labelsize": label_size,
            "legend.frameon": True,
            "legend.framealpha": 0.92,
            "legend.facecolor": "#FFFFFF",
            "legend.edgecolor": "#CBD5E1",
            "grid.color": self.colors["grid"],
            "grid.alpha": 0.55,
            "grid.linestyle": "-",
            "font.family": "DejaVu Sans"
        })

        plt.rcParams["xtick.labelsize"] = tick_size
        plt.rcParams["ytick.labelsize"] = tick_size

    def _apply_axes_style(self, ax: Axes) -> None:
        ax.grid(True, alpha=0.5)
        tick_size = 8 if self.dense_mode else 9
        ax.tick_params(axis="both", labelsize=tick_size)

    def _apply_card_style(self, ax: Axes) -> None:
        ax.set_facecolor("#FFFFFF")
        for spine in ax.spines.values():
            spine.set_visible(False)

        card = mpatches.FancyBboxPatch(
            (0, 0),
            1,
            1,
            transform=ax.transAxes,
            boxstyle="round,pad=0.02,rounding_size=10",
            linewidth=1.0,
            edgecolor="#CBD5E1",
            facecolor="#FFFFFF",
            zorder=-2
        )
        ax.add_patch(card)

    def _save_figure(
        self,
        fig: Figure,
        filename_base: str,
        dpi: int
    ) -> Path:
        if "png" in self.output_formats:
            primary_format = "png"
        else:
            primary_format = self.output_formats[0]

        primary_path = self.output_dir / f"{filename_base}.{primary_format}"

        for fmt in self.output_formats:
            filepath = self.output_dir / f"{filename_base}.{fmt}"
            if fmt == "png":
                fig.savefig(filepath, dpi=dpi, bbox_inches='tight')
            else:
                fig.savefig(filepath, bbox_inches='tight')

        return primary_path

    def _t(self, key: str) -> str:
        translations = {
            "pt": {
                "parameters": "Parametros",
                "value": "Valor",
                "measured_value": "Valor Medido",
                "limit": "Limite Tecnico",
                "timeline": "Analise Temporal",
                "sample_index": "Indice de Amostra",
                "status_distribution": "Distribuicao de Status",
                "exceed_percent": "Percentual de Excedencia",
                "dashboard": "DASHBOARD",
                "summary_title": "Resumo Tecnico dos Parametros",
                "summary_empty": "Sem dados para resumo",
                "insights_title": "Insights Rapidos",
                "overall_status": "Status geral",
                "critical": "Critico",
                "warning": "Atencao",
                "ok": "OK",
                "max_exceed": "Maior excedencia",
                "worst_exceed": "Pior excedencia",
                "max_value": "Maior valor",
                "params_evaluated": "Parametros avaliados",
                "top_param": "Parametro mais critico",
                "samples": "Amostras",
                "max": "Max",
                "exceed": "Exced (%)",
                "limit_label": "Limite",
                "measured": "Medido"
            },
            "en": {
                "parameters": "Parameters",
                "value": "Value",
                "measured_value": "Measured Value",
                "limit": "Technical Limit",
                "timeline": "Timeline Analysis",
                "sample_index": "Sample Index",
                "status_distribution": "Status Distribution",
                "exceed_percent": "Exceedance (%)",
                "dashboard": "DASHBOARD",
                "summary_title": "Technical Parameter Summary",
                "summary_empty": "No data for summary",
                "insights_title": "Quick Insights",
                "overall_status": "Overall status",
                "critical": "Critical",
                "warning": "Warning",
                "ok": "OK",
                "max_exceed": "Max exceedance",
                "worst_exceed": "Worst exceedance",
                "max_value": "Max value",
                "params_evaluated": "Parameters evaluated",
                "top_param": "Most critical parameter",
                "samples": "Samples",
                "max": "Max",
                "exceed": "Exceed (%)",
                "limit_label": "Limit",
                "measured": "Measured"
            }
        }

        lang = "en" if self.language == "en" else "pt"
        return translations[lang].get(key, key)

    def _build_insights_text(
        self,
        validation_results: List[ValidationResult]
    ) -> str:
        if not validation_results:
            return self._t("summary_empty")

        crit_count = sum(
            1
            for r in validation_results
            if r.status == "CRITICAL"
        )
        warn_count = sum(
            1
            for r in validation_results
            if r.status == "WARNING"
        )
        overall = self._t("ok")
        if crit_count > 0:
            overall = self._t("critical")
        elif warn_count > 0:
            overall = self._t("warning")

        top_result = max(
            validation_results,
            key=lambda r: r.exceedance_percent or 0.0
        )
        max_exceed = top_result.exceedance_percent or 0.0

        return (
            f"{self._t('overall_status')}: {overall} | "
            f"{self._t('max_exceed')}: {max_exceed:.1f}%\n"
            f"{self._t('top_param')}: {top_result.parameter}"
        )

    def _dedupe_legend(self, ax: Axes) -> None:
        handles, labels = ax.get_legend_handles_labels()
        if not labels:
            return

        unique = {}
        for handle, label in zip(handles, labels):
            if label not in unique:
                unique[label] = handle

        ax.legend(unique.values(), unique.keys(), loc='best')

    def _build_summary_rows(
        self,
        df: pd.DataFrame,
        validation_results: List[ValidationResult]
    ) -> List[List[str]]:
        rows = []
        for result in validation_results:
            col = self._find_column_for_parameter(df, result.parameter)
            max_value = None
            exceed_samples = 0
            if col and result.limit is not None:
                series = df[col].dropna()
                if not series.empty:
                    max_value = float(series.max())
                    exceed_samples = int((series > result.limit).sum())

            max_text = "-"
            if max_value is not None:
                max_text = f"{max_value:.2f}"

            exceed_text = f"{result.exceedance_percent or 0.0:.1f}%"
            rows.append([
                result.parameter,
                max_text,
                f"{result.limit:.2f}",
                exceed_text,
                str(exceed_samples)
            ])

        return rows

    def _add_kpi_tile(
        self,
        ax: Axes,
        title: str,
        value: str,
        status: str,
        series: Optional[pd.Series]
    ) -> None:
        ax.set_facecolor("#FFFFFF")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color("#CBD5E1")

        status_color = self.colors.get(status, self.colors["limit"])
        ax.text(
            0.04,
            0.78,
            title,
            transform=ax.transAxes,
            fontsize=9,
            fontweight='bold',
            color=self.colors["text"]
        )
        ax.text(
            0.04,
            0.44,
            value,
            transform=ax.transAxes,
            fontsize=16,
            fontweight='bold',
            color=status_color
        )

        if series is not None and len(series) > 1:
            self._add_sparkline(ax, series, status_color)

    def _add_sparkline(
        self,
        ax: Axes,
        series: pd.Series,
        color: str
    ) -> None:
        values = pd.Series(series).dropna().to_numpy()
        if values.size < 2:
            return

        inset = ax.inset_axes((0.04, 0.08, 0.92, 0.26))
        inset.plot(values, color=color, linewidth=1.6)
        inset.fill_between(
            range(len(values)),
            values,
            color=color,
            alpha=0.15
        )
        inset.set_xticks([])
        inset.set_yticks([])
        for spine in inset.spines.values():
            spine.set_visible(False)

    def _find_peak_index(self, series: pd.Series) -> Optional[int]:
        values = pd.Series(series).dropna().to_numpy()
        if values.size == 0:
            return None
        try:
            return int(np.nanargmax(values))
        except (ValueError, TypeError):
            return None

    def _find_recovery_index(
        self,
        series: pd.Series,
        limit: float,
        last_exceed_idx: int
    ) -> Optional[int]:
        if last_exceed_idx >= len(series) - 1:
            return None

        tail = series.iloc[last_exceed_idx + 1:]
        mask = (tail <= limit) & tail.notna()
        if not mask.any():
            return None

        recovery_offset = int(np.where(mask.to_numpy())[0][0])
        return last_exceed_idx + 1 + recovery_offset

    def _add_event_markers(
        self,
        ax: Axes,
        time_index: range,
        series: pd.Series,
        limit: Optional[float],
        status: str,
        include_first: bool = True
    ) -> None:
        peak_idx = self._find_peak_index(series)
        if peak_idx is not None:
            ax.scatter(
                [time_index[peak_idx]],
                [series.iloc[peak_idx]],
                marker='D',
                s=48,
                color=self.colors.get(status, self.colors["limit"]),
                edgecolors='black',
                linewidths=0.5,
                label='Pico'
            )

        if limit is None:
            return

        exceed_idx = self._find_exceedance_indices(series, limit)
        if not exceed_idx:
            return

        if include_first:
            first_idx = exceed_idx[0]
            ax.scatter(
                [time_index[first_idx]],
                [series.iloc[first_idx]],
                marker='x',
                s=90,
                color='black',
                linewidths=1.8,
                label='Primeira excedência'
            )

        recovery_idx = self._find_recovery_index(
            series,
            limit,
            exceed_idx[-1]
        )
        if recovery_idx is not None:
            ax.scatter(
                [time_index[recovery_idx]],
                [series.iloc[recovery_idx]],
                marker='o',
                s=38,
                color='#374151',
                edgecolors='black',
                linewidths=0.5,
                label='Recuperacao'
            )

    def generate_parameters_vs_limits_graph(
        self,
        df: pd.DataFrame,
        validation_results: List[ValidationResult],
        aircraft_model: str,
        event_type: str,
        tail_number: str,
        timestamp: str
    ) -> Optional[Path]:
        """Gráfico de barras: Parâmetros vs Limites"""
        if not validation_results:
            return None

        try:
            fig, ax = plt.subplots(figsize=(12, 8))
            fig.patch.set_facecolor(self.colors["background"])

            parameters = [r.parameter for r in validation_results]
            values = [r.value for r in validation_results]
            limits = [r.limit for r in validation_results]
            statuses = [r.status for r in validation_results]

            x = np.arange(len(parameters))
            width = 0.35

            # Barras de valores reais
            bars_values = ax.bar(
                x - width/2, values, width,
                label=self._t("measured_value"),
                color=[self.colors[s] for s in statuses],
                alpha=0.8
            )

            # Barras de limites
            ax.bar(
                x + width/2, limits, width,
                label=self._t("limit"),
                color=self.colors['limit'],
                alpha=0.6
            )

            # Configurar eixos
            ax.set_xlabel(
                self._t("parameters"),
                fontsize=12,
                fontweight='bold'
            )
            ax.set_ylabel(self._t("value"), fontsize=12, fontweight='bold')
            ax.set_title(
                f'{event_type.replace("_", " ").title()} - '
                f'Parâmetros vs Limites\n'
                f'{aircraft_model} ({tail_number})',
                fontsize=14,
                fontweight='bold'
            )
            ax.set_xticks(x)
            ax.set_xticklabels(parameters, rotation=45, ha='right')
            self._dedupe_legend(ax)
            self._apply_card_style(ax)
            ax.grid(True, alpha=0.35, axis='y')
            self._apply_axes_style(ax)

            # Adicionar valores nas barras
            for bar in bars_values:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom',
                    fontsize=9
                )

            plt.tight_layout()

            # Salvar
            filename_base = f"params_vs_limits_{tail_number}_{timestamp}"
            filepath = self._save_figure(fig, filename_base, dpi=150)
            plt.close(fig)

            return filepath

        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating params vs limits graph: {e}")
            return None

    def generate_timeline_graph(
        self,
        df: pd.DataFrame,
        validation_results: List[ValidationResult],
        aircraft_model: str,
        event_type: str,
        tail_number: str,
        timestamp: str
    ) -> Optional[Path]:
        """Gráfico de linha temporal dos parâmetros"""
        try:
            if not validation_results or df.empty:
                return None

            fig, axes = plt.subplots(
                len(validation_results), 1,
                figsize=(14, 4 * len(validation_results)),
                sharex=True
            )
            fig.patch.set_facecolor(self.colors["background"])

            if len(validation_results) == 1:
                axes = [axes]

            time_index = range(len(df))

            for idx, result in enumerate(validation_results):
                ax = axes[idx]

                # Encontrar coluna correspondente
                col = self._find_column_for_parameter(df, result.parameter)

                if col:
                    # Plotar valores
                    ax.plot(
                        time_index, df[col],
                        linewidth=2,
                        label='Valor Medido',
                        color=self.colors[result.status]
                    )

                    # Linha de limite
                    ax.axhline(
                        y=result.limit,
                        color=self.colors['limit'],
                        linestyle='--',
                        linewidth=2,
                        label=f'Limite: {result.limit} {result.unit}'
                    )

                    # Preencher área de excedência se houver
                    if result.status in ["WARNING", "CRITICAL"]:
                        series_max = df[col].max(skipna=True)
                        if pd.notna(series_max):
                            ax.fill_between(
                                time_index, result.limit, series_max,
                                where=(df[col] > result.limit),
                                color=self.colors[result.status],
                                alpha=0.3,
                                label='Área de Excedência'
                            )

                        exceed_idx = self._find_exceedance_indices(
                            df[col],
                            result.limit
                        )
                        if exceed_idx:
                            exceed_x = [time_index[i] for i in exceed_idx]
                            exceed_y = df[col].iloc[np.array(exceed_idx)]
                            ax.scatter(
                                exceed_x,
                                exceed_y,
                                marker='o',
                                s=22,
                                color=self.colors[result.status],
                                edgecolors='black',
                                linewidths=0.4,
                                label='Excedência'
                            )
                            first_idx = exceed_idx[0]
                            ax.scatter(
                                [time_index[first_idx]],
                                [df[col].iloc[first_idx]],
                                marker='x',
                                s=90,
                                color='black',
                                linewidths=1.8,
                                label='Primeira excedência'
                            )

                    self._add_event_markers(
                        ax,
                        time_index,
                        df[col],
                        result.limit,
                        result.status,
                        include_first=False
                    )

                    ax.set_ylabel(
                        f'{result.parameter}\n({result.unit})',
                        fontweight='bold'
                    )
                    self._dedupe_legend(ax)
                    ax.grid(True, alpha=0.3)
                    self._apply_axes_style(ax)
                    self._apply_card_style(ax)
                    ax.set_title(
                        result.message,
                        fontsize=10,
                        color=self.colors[result.status]
                    )

            axes[-1].set_xlabel(
                self._t("sample_index"),
                fontsize=12,
                fontweight='bold'
            )

            fig.suptitle(
                f'{event_type.replace("_", " ").title()} - '
                f'{self._t("timeline")}\n'
                f'{aircraft_model} ({tail_number})',
                fontsize=14,
                fontweight='bold'
            )

            plt.tight_layout()

            # Salvar
            filename_base = f"timeline_{tail_number}_{timestamp}"
            filepath = self._save_figure(fig, filename_base, dpi=220)
            plt.close(fig)

            return filepath

        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating timeline graph: {e}")
            return None

    def generate_dashboard_overview(
        self,
        df: pd.DataFrame,
        validation_results: List[ValidationResult],
        aircraft_model: str,
        event_type: str,
        tail_number: str,
        timestamp: str
    ) -> Optional[Path]:
        """Dashboard completo com múltiplos painéis"""
        try:
            if not validation_results:
                return None

            fig = plt.figure(figsize=(16, 14))
            gs = fig.add_gridspec(4, 3, hspace=0.38, wspace=0.35)
            fig.patch.set_facecolor(self.colors["background"])

            critical_results = sorted(
                validation_results,
                key=lambda r: r.exceedance_percent,
                reverse=True
            )[:3]

            total_params = len(validation_results)
            warn_count = sum(
                1 for r in validation_results if r.status == "WARNING"
            )
            crit_count = sum(
                1 for r in validation_results if r.status == "CRITICAL"
            )
            overall_status = "OK"
            if crit_count > 0:
                overall_status = "CRITICAL"
            elif warn_count > 0:
                overall_status = "WARNING"

            kpi_grid = gs[0, :].subgridspec(1, 3, wspace=0.25)
            ax_kpi_1 = fig.add_subplot(kpi_grid[0, 0])
            ax_kpi_2 = fig.add_subplot(kpi_grid[0, 1])
            ax_kpi_3 = fig.add_subplot(kpi_grid[0, 2])

            top_result = critical_results[0] if critical_results else None
            top_series = None
            if top_result:
                top_col = self._find_column_for_parameter(
                    df,
                    top_result.parameter
                )
                if top_col:
                    top_series = df[top_col]

            max_exceed = 0.0
            if validation_results:
                max_exceed = max(
                    (r.exceedance_percent or 0.0) for r in validation_results
                )

            self._add_kpi_tile(
                ax_kpi_1,
                self._t("worst_exceed"),
                f"{max_exceed:.1f}%",
                top_result.status if top_result else overall_status,
                top_series
            )
            self._add_kpi_tile(
                ax_kpi_2,
                self._t("max_value"),
                (
                    f"{top_result.value:.1f} {top_result.unit}"
                    if top_result
                    else "0"
                ),
                top_result.status if top_result else overall_status,
                top_series
            )
            self._add_kpi_tile(
                ax_kpi_3,
                self._t("params_evaluated"),
                f"{total_params}",
                overall_status,
                pd.Series([
                    r.exceedance_percent or 0.0 for r in validation_results
                ])
            )

            # Painel 1: Status Summary (pie chart)
            ax1 = fig.add_subplot(gs[1, :2])
            status_counts = {
                "OK": sum(1 for r in validation_results if r.status == "OK"),
                "WARNING": sum(
                    1 for r in validation_results if r.status == "WARNING"
                ),
                "CRITICAL": sum(
                    1 for r in validation_results if r.status == "CRITICAL"
                )
            }

            if sum(status_counts.values()) > 0:
                ax1.pie(
                    [v for v in status_counts.values() if v > 0],
                    labels=[k for k, v in status_counts.items() if v > 0],
                    colors=[
                        self.colors[k]
                        for k, v in status_counts.items()
                        if v > 0
                    ],
                    autopct='%1.1f%%',
                    startangle=90
                )
                ax1.set_title(
                    self._t("status_distribution"), fontweight='bold'
                )
            self._apply_axes_style(ax1)
            self._apply_card_style(ax1)

            # Painel 2: Exceedance Percentages
            ax2 = fig.add_subplot(gs[1, 2])
            params = [r.parameter[:15] for r in validation_results]
            exceedances = [
                r.exceedance_percent or 0.0 for r in validation_results
            ]

            ax2.barh(
                params, exceedances,
                color=[self.colors[r.status] for r in validation_results]
            )
            ax2.set_xlabel(self._t("exceed_percent"), fontweight='bold')
            ax2.set_title(self._t("exceed_percent"), fontweight='bold')
            ax2.grid(True, alpha=0.3, axis='x')
            self._apply_axes_style(ax2)
            self._apply_card_style(ax2)

            # Painéis 3-5: Top 3 parâmetros mais críticos
            for idx, result in enumerate(critical_results):
                ax = fig.add_subplot(gs[2, idx])

                col = self._find_column_for_parameter(df, result.parameter)
                if col:
                    ax.plot(
                        df[col], linewidth=2, color=self.colors[result.status]
                    )
                    ax.axhline(
                        y=result.limit,
                        color=self.colors['limit'],
                        linestyle='--',
                        linewidth=2
                    )
                    ax.set_title(
                        f'{result.parameter}\n'
                        f'Max: {result.value:.1f} {result.unit} / '
                        f'Limit: {result.limit:.1f} {result.unit}',
                        fontsize=9,
                        fontweight='bold'
                    )
                    ax.grid(True, alpha=0.3)
                    self._apply_axes_style(ax)
                    self._apply_card_style(ax)

            summary_ax = fig.add_subplot(gs[3, :])
            summary_ax.axis('off')
            summary_ax.set_title(
                self._t("summary_title"),
                fontweight='bold',
                fontsize=11
            )

            summary_ax.text(
                0.01,
                0.92,
                self._build_insights_text(validation_results),
                ha='left',
                va='top',
                fontsize=9,
                color=self.colors["text"]
            )

            summary_results = sorted(
                validation_results,
                key=lambda r: r.exceedance_percent or 0.0,
                reverse=True
            )[:6]
            summary_rows = self._build_summary_rows(df, summary_results)

            if summary_rows:
                headers = [
                    self._t("parameters"),
                    self._t("max"),
                    self._t("limit_label"),
                    self._t("exceed"),
                    self._t("samples")
                ]
                table = summary_ax.table(
                    cellText=summary_rows,
                    colLabels=headers,
                    loc='center',
                    cellLoc='center'
                )
                table.auto_set_font_size(False)
                table.set_fontsize(8 if self.dense_mode else 9)
                table.scale(1.0, 1.25)
            else:
                summary_ax.text(
                    0.5,
                    0.5,
                    self._t("summary_empty"),
                    ha='center',
                    va='center',
                    fontsize=9
                )

            # Título geral
            fig.suptitle(
                f'{self._t("dashboard")} - '
                f'{event_type.replace("_", " ").upper()}\n'
                f'{aircraft_model} ({tail_number}) - {timestamp}',
                fontsize=16,
                fontweight='bold'
            )

            # Salvar
            filename_base = f"dashboard_{tail_number}_{timestamp}"
            filepath = self._save_figure(fig, filename_base, dpi=220)
            plt.close(fig)

            return filepath

        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating dashboard: {e}")
            return None

    def generate_hard_landing_specific_graphs(
        self,
        df: pd.DataFrame,
        validation_results: List[ValidationResult],
        aircraft_model: str,
        tail_number: str,
        timestamp: str
    ) -> List[Path]:
        """Gráficos específicos para Hard Landing"""
        files = []

        # Gráfico combinado: G-Force + Pitch + Roll
        try:
            fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
            fig.patch.set_facecolor(self.colors["background"])

            # Aceleração vertical
            accel_col = self._find_column(
                df, ['vertical_acceleration', 'vert_accel', 'nz']
            )
            if accel_col:
                axes[0].plot(
                    df[accel_col], 'b-',
                    linewidth=2, label='Vertical G'
                )
                accel_limit = self._get_validation_limit(
                    validation_results, 'Vertical Acceleration', fallback=2.6
                )
                exceed_idx = []
                if accel_limit is not None:
                    axes[0].axhline(
                        y=2.0, color='orange',
                        linestyle='--', label='Normal Limit'
                    )
                    axes[0].axhline(
                        y=accel_limit, color='red',
                        linestyle='--', label='Hard Limit'
                    )

                    exceed_idx = self._find_exceedance_indices(
                        df[accel_col], accel_limit
                    )
                    if exceed_idx:
                        exceed_y = df[accel_col].iloc[np.array(exceed_idx)]
                        axes[0].scatter(
                            exceed_idx,
                            exceed_y,
                            marker='o',
                            s=24,
                            color=self.colors['CRITICAL'],
                            edgecolors='black',
                            linewidths=0.4,
                            label='Excedência'
                        )
                        first_idx = exceed_idx[0]
                        axes[0].scatter(
                            [first_idx],
                            [df[accel_col].iloc[first_idx]],
                            marker='x',
                            s=90,
                            color='black',
                            linewidths=1.8,
                            label='Primeira excedência'
                        )
                axes[0].set_ylabel('G Force', fontweight='bold')
                self._add_event_markers(
                    axes[0],
                    range(len(df)),
                    df[accel_col],
                    accel_limit,
                    "CRITICAL",
                    include_first=False
                )
                self._dedupe_legend(axes[0])
                axes[0].grid(True, alpha=0.3)
                self._apply_axes_style(axes[0])
                self._apply_card_style(axes[0])
                axes[0].set_title('Vertical Acceleration', fontweight='bold')

            # Pitch
            pitch_col = self._find_column(df, ['pitch', 'theta'])
            if pitch_col:
                axes[1].plot(
                    df[pitch_col], 'g-',
                    linewidth=2, label='Pitch Angle'
                )
                axes[1].axhline(y=0, color='k', linestyle='-', linewidth=0.5)
                axes[1].set_ylabel('Pitch (°)', fontweight='bold')
                self._add_event_markers(
                    axes[1],
                    range(len(df)),
                    df[pitch_col],
                    None,
                    "OK",
                    include_first=False
                )
                self._dedupe_legend(axes[1])
                axes[1].grid(True, alpha=0.3)
                self._apply_axes_style(axes[1])
                self._apply_card_style(axes[1])
                axes[1].set_title('Pitch Angle', fontweight='bold')

            # Roll
            roll_col = self._find_column(df, ['roll', 'phi', 'bank'])
            if roll_col:
                axes[2].plot(
                    df[roll_col], 'm-',
                    linewidth=2, label='Roll Angle'
                )
                axes[2].axhline(y=0, color='k', linestyle='-', linewidth=0.5)
                axes[2].set_ylabel('Roll (°)', fontweight='bold')
                axes[2].set_xlabel(
                    self._t("sample_index"),
                    fontweight='bold'
                )
                self._add_event_markers(
                    axes[2],
                    range(len(df)),
                    df[roll_col],
                    None,
                    "OK",
                    include_first=False
                )
                self._dedupe_legend(axes[2])
                axes[2].grid(True, alpha=0.3)
                self._apply_axes_style(axes[2])
                self._apply_card_style(axes[2])
                axes[2].set_title('Roll Angle', fontweight='bold')

            fig.suptitle(
                f'Hard Landing Analysis - {aircraft_model} ({tail_number})',
                fontsize=14,
                fontweight='bold'
            )

            plt.tight_layout()

            filename_base = f"hard_landing_detail_{tail_number}_{timestamp}"
            filepath = self._save_figure(fig, filename_base, dpi=220)
            plt.close(fig)
            files.append(filepath)

        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating hard landing graph: {e}")

        return files

    def generate_gear_overspeed_specific_graphs(
        self,
        df: pd.DataFrame,
        validation_results: List[ValidationResult],
        aircraft_model: str,
        tail_number: str,
        timestamp: str
    ) -> List[Path]:
        """Gráficos específicos para Gear Overspeed"""
        files = []

        try:
            speed_col = self._find_column(df, ['airspeed', 'ias', 'kias'])
            gear_col = self._find_column(
                df, ['gear_position', 'landing_gear', 'gear_pos']
            )
            if not speed_col:
                return files

            fig, ax = plt.subplots(figsize=(14, 8))
            fig.patch.set_facecolor(self.colors["background"])
            time_index = range(len(df))
            ax.plot(
                time_index, df[speed_col],
                linewidth=2, color='#1E88E5', label='Airspeed'
            )

            vle_limit = self._get_validation_limit(
                validation_results,
                'Landing Gear Speed (VLE)',
                fallback=None
            )
            if vle_limit is not None:
                ax.axhline(
                    y=vle_limit,
                    color=self.colors['limit'],
                    linestyle='--',
                    linewidth=2,
                    label=f'VLE {vle_limit:.0f} KIAS'
                )

            if gear_col:
                gear_mask = df[gear_col].astype(str).str.strip(
                ).str.upper().isin(
                    ['1', 'DOWN', 'EXTENDED', 'LOCKED', 'TRUE']
                )
                if gear_mask.any():
                    ax.scatter(
                        [i for i, v in enumerate(gear_mask) if v],
                        df.loc[gear_mask, speed_col],
                        s=12,
                        color='#F39C12',
                        label='Gear Down'
                    )

            self._add_event_markers(
                ax,
                time_index,
                df[speed_col],
                vle_limit,
                "WARNING" if vle_limit is not None else "OK",
                include_first=True
            )

            ax.set_title(
                f'Landing Gear Overspeed - {aircraft_model} '
                f'({tail_number})',
                fontweight='bold'
            )
            ax.set_xlabel(self._t("sample_index"), fontweight='bold')
            ax.set_ylabel('Airspeed (KIAS)', fontweight='bold')
            ax.grid(True, alpha=0.3)
            self._dedupe_legend(ax)
            self._apply_axes_style(ax)
            self._apply_card_style(ax)

            filename_base = f"gear_overspeed_{tail_number}_{timestamp}"
            filepath = self._save_figure(fig, filename_base, dpi=220)
            plt.close(fig)
            files.append(filepath)

        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating gear overspeed graph: {e}")

        return files

    def generate_temperature_specific_graphs(
        self,
        df: pd.DataFrame,
        validation_results: List[ValidationResult],
        aircraft_model: str,
        tail_number: str,
        timestamp: str
    ) -> List[Path]:
        """Gráficos específicos para Temperature Envelope"""
        files = []

        try:
            tat_col = self._find_column(
                df, ['tat', 'total_air_temp', 'oat', 'sat']
            )
            egt_col = self._find_column(
                df, ['egt', 'exhaust_gas_temp', 'turbine_temp']
            )
            if not tat_col and not egt_col:
                return files

            fig, ax = plt.subplots(figsize=(14, 8))
            fig.patch.set_facecolor(self.colors["background"])
            time_index = range(len(df))

            if tat_col:
                ax.plot(
                    time_index, df[tat_col],
                    linewidth=2, color='#1976D2', label='TAT'
                )

            if egt_col:
                ax.plot(
                    time_index, df[egt_col],
                    linewidth=2, color='#E67E22', label='EGT'
                )

            tat_high = self._get_validation_limit(
                validation_results,
                'Total Air Temperature (TAT) - High',
                fallback=None
            )
            tat_low = self._get_validation_limit(
                validation_results,
                'Total Air Temperature (TAT) - Low',
                fallback=None
            )
            egt_limit = self._get_validation_limit(
                validation_results,
                'Exhaust Gas Temperature (EGT)',
                fallback=None
            )

            if tat_high is not None:
                ax.axhline(
                    y=tat_high,
                    color='#1565C0',
                    linestyle='--',
                    linewidth=2,
                    label=f'TAT Max {tat_high:.0f} C'
                )
            if tat_low is not None:
                ax.axhline(
                    y=tat_low,
                    color='#1565C0',
                    linestyle='--',
                    linewidth=2,
                    label=f'TAT Min {tat_low:.0f} C'
                )
            if egt_limit is not None:
                ax.axhline(
                    y=egt_limit,
                    color='#C0392B',
                    linestyle='--',
                    linewidth=2,
                    label=f'EGT Limit {egt_limit:.0f} C'
                )

            if tat_col and tat_high is not None:
                self._add_event_markers(
                    ax,
                    time_index,
                    df[tat_col],
                    tat_high,
                    "WARNING",
                    include_first=True
                )
            if egt_col and egt_limit is not None:
                self._add_event_markers(
                    ax,
                    time_index,
                    df[egt_col],
                    egt_limit,
                    "CRITICAL",
                    include_first=True
                )

            ax.set_title(
                f'Temperature Envelope - {aircraft_model} '
                f'({tail_number})',
                fontweight='bold'
            )
            ax.set_xlabel(self._t("sample_index"), fontweight='bold')
            ax.set_ylabel('Temperature (C)', fontweight='bold')
            ax.grid(True, alpha=0.3)
            self._dedupe_legend(ax)
            self._apply_axes_style(ax)
            self._apply_card_style(ax)

            filename_base = f"temperature_envelope_{tail_number}_{timestamp}"
            filepath = self._save_figure(fig, filename_base, dpi=220)
            plt.close(fig)
            files.append(filepath)

        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating temperature graph: {e}")

        return files

    def generate_max_speed_specific_graphs(
        self,
        df: pd.DataFrame,
        validation_results: List[ValidationResult],
        aircraft_model: str,
        tail_number: str,
        timestamp: str
    ) -> List[Path]:
        """Gráficos específicos para Max Speed"""
        files = []

        try:
            ias_col = self._find_column(df, ['airspeed', 'ias', 'kias'])
            mach_col = self._find_column(df, ['mach', 'mmo'])
            if not ias_col and not mach_col:
                return files

            fig, ax = plt.subplots(figsize=(14, 8))
            fig.patch.set_facecolor(self.colors["background"])
            time_index = range(len(df))

            if ias_col:
                ax.plot(
                    time_index, df[ias_col],
                    linewidth=2, color='#1E88E5', label='IAS (KIAS)'
                )
                vmo_limit = self._get_validation_limit(
                    validation_results,
                    'Maximum Operating Speed (VMO)',
                    fallback=None
                )
                if vmo_limit is not None:
                    ax.axhline(
                        y=vmo_limit,
                        color=self.colors['limit'],
                        linestyle='--',
                        linewidth=2,
                        label=f'VMO {vmo_limit:.0f} KIAS'
                    )
                    self._add_event_markers(
                        ax,
                        time_index,
                        df[ias_col],
                        vmo_limit,
                        "WARNING",
                        include_first=True
                    )

            if mach_col:
                ax2 = ax.twinx()
                ax2.plot(
                    time_index, df[mach_col],
                    linewidth=2, color='#8E44AD', label='Mach'
                )
                mmo_limit = self._get_validation_limit(
                    validation_results,
                    'Maximum Operating Mach (MMO)',
                    fallback=None
                )
                if mmo_limit is not None:
                    ax2.axhline(
                        y=mmo_limit,
                        color='#6A1B9A',
                        linestyle='--',
                        linewidth=2,
                        label=f'MMO {mmo_limit:.2f}'
                    )
                ax2.set_ylabel('Mach', fontweight='bold')

                lines, labels = ax.get_legend_handles_labels()
                lines2, labels2 = ax2.get_legend_handles_labels()
                ax2.legend(lines + lines2, labels + labels2, loc='best')
            else:
                self._dedupe_legend(ax)

            ax.set_title(
                f'Max Speed - {aircraft_model} '
                f'({tail_number})',
                fontweight='bold'
            )
            ax.set_xlabel(self._t("sample_index"), fontweight='bold')
            ax.set_ylabel('Airspeed (KIAS)', fontweight='bold')
            ax.grid(True, alpha=0.3)
            self._apply_axes_style(ax)
            self._apply_card_style(ax)

            filename_base = f"max_speed_{tail_number}_{timestamp}"
            filepath = self._save_figure(fig, filename_base, dpi=220)
            plt.close(fig)
            files.append(filepath)

        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating max speed graph: {e}")

        return files

    def generate_flap_overspeed_specific_graphs(
        self,
        df: pd.DataFrame,
        validation_results: List[ValidationResult],
        aircraft_model: str,
        tail_number: str,
        timestamp: str
    ) -> List[Path]:
        """Gráficos específicos para Flap Overspeed"""
        files = []

        try:
            ias_col = self._find_column(df, ['airspeed', 'ias', 'kias'])
            flap_col = self._find_column(
                df, ['flap_position', 'flap', 'flaps']
            )
            if not ias_col:
                return files

            fig, ax = plt.subplots(figsize=(14, 8))
            fig.patch.set_facecolor(self.colors["background"])
            time_index = range(len(df))
            ax.plot(
                time_index, df[ias_col],
                linewidth=2, color='#1E88E5', label='IAS (KIAS)'
            )

            for result in validation_results:
                if result.parameter.lower().startswith('flap speed'):
                    ax.axhline(
                        y=result.limit,
                        color=self.colors['limit'],
                        linestyle='--',
                        linewidth=2,
                        label=f"{result.parameter}: {result.limit:.0f} KIAS"
                    )

            max_limit = None
            for result in validation_results:
                if result.parameter.lower().startswith('flap speed'):
                    max_limit = result.limit if max_limit is None else max(
                        max_limit, result.limit
                    )

            if max_limit is not None:
                self._add_event_markers(
                    ax,
                    time_index,
                    df[ias_col],
                    max_limit,
                    "WARNING",
                    include_first=True
                )

            if flap_col:
                changes = df[flap_col].astype(str).fillna('')
                for idx in range(1, len(changes)):
                    if changes.iloc[idx] != changes.iloc[idx - 1]:
                        ax.axvline(
                            x=idx, color='#BDBDBD',
                            linestyle=':', linewidth=1
                        )

            ax.set_title(
                f'Flap Overspeed - {aircraft_model} '
                f'({tail_number})',
                fontweight='bold'
            )
            ax.set_xlabel(self._t("sample_index"), fontweight='bold')
            ax.set_ylabel('Airspeed (KIAS)', fontweight='bold')
            ax.grid(True, alpha=0.3)
            self._dedupe_legend(ax)
            self._apply_axes_style(ax)
            self._apply_card_style(ax)

            filename_base = f"flap_overspeed_{tail_number}_{timestamp}"
            filepath = self._save_figure(fig, filename_base, dpi=220)
            plt.close(fig)
            files.append(filepath)

        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating flap overspeed graph: {e}")

        return files

    def generate_overweight_landing_specific_graphs(
        self,
        df: pd.DataFrame,
        validation_results: List[ValidationResult],
        aircraft_model: str,
        tail_number: str,
        timestamp: str
    ) -> List[Path]:
        """Gráficos específicos para Overweight Landing"""
        files = []

        try:
            weight_col = self._find_column(
                df, ['gross_weight', 'weight', 'landing_weight', 'gw']
            )
            if not weight_col:
                return files

            fig, ax = plt.subplots(figsize=(14, 8))
            fig.patch.set_facecolor(self.colors["background"])
            time_index = range(len(df))
            ax.plot(
                time_index, df[weight_col],
                linewidth=2, color='#1E88E5', label='Landing Weight'
            )

            mlw_limit = self._get_validation_limit(
                validation_results,
                'Landing Weight (MLW)',
                fallback=None
            )
            if mlw_limit is not None:
                ax.axhline(
                    y=mlw_limit,
                    color=self.colors['limit'],
                    linestyle='--',
                    linewidth=2,
                    label=f'MLW {mlw_limit:.0f}'
                )
                self._add_event_markers(
                    ax,
                    time_index,
                    df[weight_col],
                    mlw_limit,
                    "WARNING",
                    include_first=True
                )

            ax.set_title(
                f'Overweight Landing - {aircraft_model} '
                f'({tail_number})',
                fontweight='bold'
            )
            ax.set_xlabel(self._t("sample_index"), fontweight='bold')
            ax.set_ylabel('Weight', fontweight='bold')
            ax.grid(True, alpha=0.3)
            self._dedupe_legend(ax)
            self._apply_axes_style(ax)
            self._apply_card_style(ax)

            filename_base = f"overweight_landing_{tail_number}_{timestamp}"
            filepath = self._save_figure(fig, filename_base, dpi=220)
            plt.close(fig)
            files.append(filepath)

        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Error generating overweight landing graph: {e}")

        return files

    def _find_column(
        self, df: pd.DataFrame, candidates: List[str]
    ) -> Optional[str]:
        """Encontrar coluna no DataFrame (case-insensitive)"""
        df_cols_lower = {col.lower(): col for col in df.columns}
        for candidate in candidates:
            if candidate.lower() in df_cols_lower:
                return df_cols_lower[candidate.lower()]
        return None

    def _find_exceedance_indices(
        self, series: pd.Series, limit: float
    ) -> List[int]:
        try:
            mask = (series > limit) & series.notna()
            return list(np.where(mask.to_numpy())[0])
        except Exception:
            return []

    def _get_validation_limit(
        self,
        validation_results: List[ValidationResult],
        parameter_name: str,
        fallback: Optional[float]
    ) -> Optional[float]:
        for result in validation_results:
            if result.parameter.lower() == parameter_name.lower():
                return result.limit
        return fallback

    def _find_column_for_parameter(
        self, df: pd.DataFrame, parameter: str
    ) -> Optional[str]:
        """Mapear nome do parâmetro para coluna do DataFrame"""
        parameter_map = {
            "Vertical Acceleration": [
                'vertical_acceleration', 'vert_accel', 'nz'
            ],
            "Descent Rate": ['descent_rate', 'vertical_speed', 'vs'],
            "Landing Gear Speed": ['airspeed', 'ias', 'kias'],
            "Landing Gear Speed (VLE)": ['airspeed', 'ias', 'kias'],
            "Exhaust Gas Temperature": ['egt', 'exhaust_gas_temp'],
            "Total Air Temperature": ['tat', 'total_air_temp', 'oat'],
            "Maximum Operating Speed": ['airspeed', 'ias', 'kias'],
            "Maximum Operating Mach": ['mach', 'mmo'],
            "Landing Weight": [
                'gross_weight', 'weight', 'landing_weight', 'gw'
            ],
            "Landing Weight (MLW)": [
                'gross_weight', 'weight', 'landing_weight', 'gw'
            ],
        }

        if parameter.lower().startswith("flap speed"):
            return self._find_column(df, ['airspeed', 'ias', 'kias'])

        candidates = parameter_map.get(parameter, [parameter.lower()])
        return self._find_column(df, candidates)

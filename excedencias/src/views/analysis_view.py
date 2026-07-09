"""
Data analysis page
"""

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFileDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QTextEdit,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from pathlib import Path

from utils import AppConfig, AppColors
from utils.logger import logger
from services import CSVParser, RulesEngine, ReportGenerator
from services.parameter_validator import ParameterValidator, ValidationResult
from services.universal_graph_generator import UniversalGraphGenerator
from services.data_pipeline import DataPipeline
from services.analysis_cache import AnalysisCache, CacheEntry
from services.pdf_mapper import PDFMapper
from services.vmo_analyzer import VmoAnalyzer
from services.flap_overspeed_analyzer import FlapAnalyzer
from services.lg_down_overspeed_analyzer import LGDownOverspeedAnalyzer
from services.overweight_landing_analyzer import OverweightLandingAnalyzer
from services.temperature_envelope_analyzer import TemperatureEnvelopeAnalyzer
from services.turbulence_analyzer import TurbulenceAnalyzer
from utils.audit_log import append_audit_log
from services.hard_landing_analyzer import HardLandingAnalyzer
from services.over_g_analyzer import OverGAnalyzer
from utils.model_selection import get_model_name_for_analyzers


class AnalysisView(QWidget):
    """Inspection data analysis screen"""
    
    back_clicked = pyqtSignal()
    view_pdfs_clicked = pyqtSignal(str, str, str, str)  # family_id, family_name, event_id, event_name
    view_graphics_clicked = pyqtSignal(str, str, str, str)  # family_id, family_name, event_id, event_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_aircraft_id = None
        self.current_aircraft_name = None
        self.current_event_id = None
        self.current_event_name = None
        self.current_data = None  # DataFrame with imported data
        self.current_analysis = None  # Last analysis result
        self.current_data_context = None  # (aircraft_id, event_id)
        self.current_file_signature = None
        self.current_analysis_event_id = None
        self.current_analysis_event_name = None
        self.analysis_cache = AnalysisCache(max_size=30)
        self.report_generator = ReportGenerator()  # Report generator
        self.setup_ui()
    
    def setup_ui(self):
        """Configure UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header with back button
        header_layout = QHBoxLayout()
        
        back_button = QPushButton("← Back")
        back_button.setMaximumWidth(180)
        back_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {AppColors.SECONDARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 22px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {AppColors.PRIMARY};
            }}
        """)
        back_button.clicked.connect(self.back_clicked.emit)
        header_layout.addWidget(back_button)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Context information
        self.context_label = QLabel()
        self.context_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(48)
        font.setBold(True)
        self.context_label.setFont(font)
        self.context_label.setStyleSheet(f"color: {AppColors.PRIMARY}; padding: 20px;")
        layout.addWidget(self.context_label)
        
        # Import section
        import_group = QGroupBox("DATA IMPORT & ANALYSIS")
        import_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 24px;
                font-weight: bold;
                border: 3px solid {AppColors.BORDER};
                border-radius: 12px;
                margin-top: 20px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                color: {AppColors.PRIMARY};
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        import_layout = QVBoxLayout(import_group)
        
        import_button_layout = QHBoxLayout()
        import_button_layout.addStretch()
        
        # Action buttons in 3-column grid with blue colors
        buttons_grid = QGridLayout()
        buttons_grid.setSpacing(15)
        
        # Row 1 - Standardized button sizing
        self.import_button = QPushButton("IMPORT")
        self.import_button.setMinimumSize(300, 90)
        self.import_button.setMaximumSize(350, 90)
        self.import_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2196F3,
                    stop:0.5 #1976D2,
                    stop:1 #0D47A1);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 25px;
                font-size: 22px;
                font-weight: bold;
                letter-spacing: 2px;
                border-bottom: 4px solid rgba(0, 0, 0, 0.2);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #42A5F5,
                    stop:0.5 #2196F3,
                    stop:1 #1976D2);
                border-bottom: 5px solid rgba(0, 0, 0, 0.3);
            }
            QPushButton:pressed {
                padding-top: 27px;
                padding-bottom: 23px;
                border-top: 4px solid rgba(0, 0, 0, 0.3);
                border-bottom: 2px solid rgba(0, 0, 0, 0.1);
            }
        """)
        self.import_button.clicked.connect(self.import_file)
        buttons_grid.addWidget(self.import_button, 0, 0)
        
        self.analyze_button = QPushButton("ANALYZE")
        self.analyze_button.setEnabled(False)
        self.analyze_button.setMinimumSize(300, 90)
        self.analyze_button.setMaximumSize(350, 90)
        self.analyze_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1976D2,
                    stop:0.5 #1565C0,
                    stop:1 #0D47A1);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 25px;
                font-size: 22px;
                font-weight: bold;
                letter-spacing: 2px;
                border-bottom: 4px solid rgba(0, 0, 0, 0.2);
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2196F3,
                    stop:0.5 #1976D2,
                    stop:1 #1565C0);
                border-bottom: 5px solid rgba(0, 0, 0, 0.3);
            }}
            QPushButton:pressed {{
                padding-top: 27px;
                padding-bottom: 23px;
                border-top: 4px solid rgba(0, 0, 0, 0.3);
                border-bottom: 2px solid rgba(0, 0, 0, 0.1);
            }}
            QPushButton:disabled {{
                background: {AppColors.BORDER};
                color: {AppColors.TEXT_DISABLED};
                border-bottom: 2px solid rgba(0, 0, 0, 0.1);
            }}
        """)
        self.analyze_button.clicked.connect(self.analyze_data)
        buttons_grid.addWidget(self.analyze_button, 0, 1)
        
        self.export_button = QPushButton("EXPORT")
        self.export_button.setEnabled(False)
        self.export_button.setMinimumSize(300, 90)
        self.export_button.setMaximumSize(350, 90)
        self.export_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1565C0,
                    stop:0.5 #0D47A1,
                    stop:1 #01579B);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 25px;
                font-size: 22px;
                font-weight: bold;
                letter-spacing: 2px;
                border-bottom: 4px solid rgba(0, 0, 0, 0.2);
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1976D2,
                    stop:0.5 #1565C0,
                    stop:1 #0D47A1);
                border-bottom: 5px solid rgba(0, 0, 0, 0.3);
            }}
            QPushButton:pressed {{
                padding-top: 18px;
                padding-bottom: 12px;
                border-top: 4px solid rgba(0, 0, 0, 0.3);
                border-bottom: 2px solid rgba(0, 0, 0, 0.1);
            }}
            QPushButton:disabled {{
                background: {AppColors.BORDER};
                color: {AppColors.TEXT_DISABLED};
                border-bottom: 2px solid rgba(0, 0, 0, 0.1);
            }}
        """)
        self.export_button.clicked.connect(self.export_report)
        buttons_grid.addWidget(self.export_button, 0, 2)

        self.clear_button = QPushButton("CLEAR")
        self.clear_button.setEnabled(False)
        self.clear_button.setMinimumSize(300, 90)
        self.clear_button.setMaximumSize(350, 90)
        self.clear_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #455A64,
                    stop:0.5 #37474F,
                    stop:1 #263238);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 25px;
                font-size: 22px;
                font-weight: bold;
                letter-spacing: 2px;
                border-bottom: 4px solid rgba(0, 0, 0, 0.2);
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #546E7A,
                    stop:0.5 #455A64,
                    stop:1 #37474F);
                border-bottom: 5px solid rgba(0, 0, 0, 0.3);
            }}
            QPushButton:pressed {{
                padding-top: 27px;
                padding-bottom: 23px;
                border-top: 4px solid rgba(0, 0, 0, 0.3);
                border-bottom: 2px solid rgba(0, 0, 0, 0.1);
            }}
            QPushButton:disabled {{
                background: {AppColors.BORDER};
                color: {AppColors.TEXT_DISABLED};
                border-bottom: 2px solid rgba(0, 0, 0, 0.1);
            }}
        """)
        self.clear_button.clicked.connect(self.clear_analysis_state)
        buttons_grid.addWidget(self.clear_button, 0, 3)
        
        # Row 2 - Secondary actions with standardized sizing
        self.view_pdfs_button = QPushButton("DOCS")
        self.view_pdfs_button.setEnabled(False)
        self.view_pdfs_button.setMinimumSize(300, 90)
        self.view_pdfs_button.setMaximumSize(350, 90)
        self.view_pdfs_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0D47A1,
                    stop:0.5 #01579B,
                    stop:1 #003C8F);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 25px;
                font-size: 22px;
                font-weight: bold;
                letter-spacing: 2px;
                border-bottom: 4px solid rgba(0, 0, 0, 0.2);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1565C0,
                    stop:0.5 #0D47A1,
                    stop:1 #01579B);
                border-bottom: 5px solid rgba(0, 0, 0, 0.3);
            }
            QPushButton:pressed {
                padding-top: 27px;
                padding-bottom: 23px;
                border-top: 4px solid rgba(0, 0, 0, 0.3);
                border-bottom: 2px solid rgba(0, 0, 0, 0.1);
            }
        """)
        self.view_pdfs_button.clicked.connect(self.show_pdfs)
        buttons_grid.addWidget(self.view_pdfs_button, 1, 0)
        
        self.graphs_button = QPushButton("GRAPHS")
        self.graphs_button.setMinimumSize(300, 90)
        self.graphs_button.setMaximumSize(350, 90)
        self.graphs_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0277BD,
                    stop:0.5 #01579B,
                    stop:1 #003C8F);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 25px;
                font-size: 22px;
                font-weight: bold;
                letter-spacing: 2px;
                border-bottom: 4px solid rgba(0, 0, 0, 0.2);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0288D1,
                    stop:0.5 #0277BD,
                    stop:1 #01579B);
                border-bottom: 5px solid rgba(0, 0, 0, 0.3);
            }
            QPushButton:pressed {
                padding-top: 22px;
                padding-bottom: 18px;
                border-top: 4px solid rgba(0, 0, 0, 0.3);
                border-bottom: 2px solid rgba(0, 0, 0, 0.1);
            }
        """)
        self.graphs_button.clicked.connect(self.show_graphs)
        buttons_grid.addWidget(self.graphs_button, 1, 1)
        
        self.ai_assistant_button = QPushButton("AI ASSISTANT")
        self.ai_assistant_button.setMinimumSize(300, 90)
        self.ai_assistant_button.setMaximumSize(350, 90)
        self.ai_assistant_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0288D1,
                    stop:0.5 #0277BD,
                    stop:1 #01579B);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 25px;
                font-size: 22px;
                font-weight: bold;
                letter-spacing: 2px;
                border-bottom: 4px solid rgba(0, 0, 0, 0.2);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #03A9F4,
                    stop:0.5 #0288D1,
                    stop:1 #0277BD);
                border-bottom: 5px solid rgba(0, 0, 0, 0.3);
            }
            QPushButton:pressed {
                padding-top: 27px;
                padding-bottom: 23px;
                border-top: 4px solid rgba(0, 0, 0, 0.3);
                border-bottom: 2px solid rgba(0, 0, 0, 0.1);
            }
        """)
        self.ai_assistant_button.clicked.connect(self.show_ai_assistant)
        buttons_grid.addWidget(self.ai_assistant_button, 1, 2)
        
        import_button_layout.addLayout(buttons_grid)
        import_button_layout.addStretch()
        
        import_layout.addLayout(import_button_layout)

        self.file_label = QLabel("NO FILE SELECTED")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        file_font = QFont()
        file_font.setPointSize(14)
        file_font.setBold(True)
        self.file_label.setFont(file_font)
        self.file_label.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY}; padding: 15px;")
        import_layout.addWidget(self.file_label)
        
        layout.addWidget(import_group)
        
        # Flight Parameters Section
        params_group = QGroupBox("FLIGHT PARAMETERS")
        params_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 20px;
                font-weight: bold;
                border: 3px solid {AppColors.BORDER};
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                color: {AppColors.PRIMARY};
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }}
        """)
        params_layout = QGridLayout(params_group)
        
        # Parameter labels with English translation
        param_labels = [
            ("TAIL NUMBER:", "N/A"),
            ("FLIGHT NUMBER:", "N/A"),
            ("DATE/TIME:", "N/A"),
            ("DURATION:", "N/A")
        ]
        
        self.param_value_labels = {}
        for i, (label_text, default_value) in enumerate(param_labels):
            label = QLabel(label_text)
            label_font = QFont()
            label_font.setPointSize(13)
            label_font.setBold(True)
            label.setFont(label_font)
            label.setStyleSheet(f"font-weight: bold; color: {AppColors.TEXT_PRIMARY};")
            value = QLabel(default_value)
            value.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY};")
            
            params_layout.addWidget(label, i, 0)
            params_layout.addWidget(value, i, 1)
            self.param_value_labels[label_text] = value
        
        layout.addWidget(params_group)

        # Rules / PDF reference section
        rules_group = QGroupBox("RULES & PDF REFERENCES")
        rules_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 18px;
                font-weight: bold;
                border: 2px dashed {AppColors.BORDER};
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                color: {AppColors.SECONDARY};
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        rules_layout = QVBoxLayout(rules_group)

        self.rules_label = QLabel("Select family and event to view applicable PDFs.")
        self.rules_label.setWordWrap(True)
        self.rules_label.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY}; font-size: 13px;")
        rules_layout.addWidget(self.rules_label)

        layout.addWidget(rules_group)
        
        # Results section
        results_group = QGroupBox("ANALYSIS RESULTS")
        results_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 20px;
                font-weight: bold;
                border: 3px solid {AppColors.BORDER};
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                color: {AppColors.PRIMARY};
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMinimumHeight(2400)  # Expanded height to minimize scrolling
        self.results_text.setMinimumWidth(1100)
        self.results_text.setPlaceholderText("Import a file to start analysis...")
        self.results_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {AppColors.SURFACE};
                border: 1px solid {AppColors.BORDER};
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }}
        """)
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
        layout.addStretch()
    
    def set_context(self, aircraft_id: str, aircraft_name: str, event_id: str, event_name: str):
        """Define analysis context"""
        self.clear_analysis_state(clear_context=False)
        self.current_aircraft_id = aircraft_id
        self.current_aircraft_name = aircraft_name
        self.current_event_id = event_id
        self.current_event_name = event_name
        
        self._update_context_label()
        self.view_pdfs_button.setEnabled(True)
    
    def import_file(self):
        """Import CSV/TXT file."""
        self.clear_analysis_state(clear_context=False)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Data File",
            "",
            "Data Files (*.csv *.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                # Usar pipeline de dados para padronização
                path = Path(file_path)
                self.current_file_signature = self._get_file_signature(path)
                pipeline = DataPipeline()
                pipeline_result = pipeline.process_file(path)
                if pipeline_result.errors:
                    raise ValueError("; ".join(pipeline_result.errors))

                self.current_data = pipeline_result.df
                self.current_data_context = (self.current_aircraft_id, self.current_event_id)
                
                # Atualizar label do arquivo
                file_info = CSVParser.get_file_info(path)
                self.file_label.setText(
                    f"✓ {path.name} | {file_info['rows']} rows | {file_info['columns']} columns"
                )
                self.file_label.setStyleSheet(f"color: {AppColors.SUCCESS}; padding: 5px; font-weight: bold;")
                
                # Mostrar preview na tabela
                self.display_data_preview(self.current_data)
                
                # Atualizar resultados
                warnings_text = ""
                if pipeline_result.warnings:
                    warnings_text = "\n\n⚠️ Warnings:\n   " + "\n   ".join(pipeline_result.warnings)

                self.results_text.setText(
                    f"✓ File imported successfully!\n\n"
                    f"📊 File information:\n"
                    f"   • Rows: {file_info['rows']}\n"
                    f"   • Columns: {file_info['columns']}\n"
                    f"   • Encoding: {file_info['encoding']}\n"
                    f"   • Size: {file_info['size_bytes'] / 1024:.1f} KB\n\n"
                    f"📋 Columns found:\n"
                    f"   {', '.join(file_info['column_names'])}\n\n"
                    f"⚙ ️Click 'Analyze' to process the data."
                    f"{warnings_text}"
                )
                
                # Enable analysis button
                self.analyze_button.setEnabled(True)
                self.clear_button.setEnabled(True)
                
                # Try to extract basic parameters
                self.extract_flight_params(self.current_data)
                
            except Exception as e:
                # Mostrar erro
                QMessageBox.critical(
                    self,
                    "Import Error",
                    f"Could not import file:\n\n{str(e)}"
                )
                self.file_label.setText("❌ Error importing file")
                self.file_label.setStyleSheet(f"color: {AppColors.ERROR}; padding: 5px;")
    
    def display_data_preview(self, df):
        """Display data preview in table"""
        try:
            # Check if data_table exists
            if not hasattr(self, 'data_table'):
                logger.warning("Preview table is not available in this view")
                return
                
            # Limpar tabela
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
            
            # Configurar colunas
            self.data_table.setColumnCount(len(df.columns))
            self.data_table.setHorizontalHeaderLabels(df.columns.tolist())
            
            # Mostrar primeiras 10 linhas
            preview_df = df.head(10)
            self.data_table.setRowCount(len(preview_df))
            
            # Preencher dados
            for i, row in enumerate(preview_df.itertuples(index=False)):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(str(value))
                    self.data_table.setItem(i, j, item)
            
            # Ajustar largura das colunas
            self.data_table.resizeColumnsToContents()
            
        except Exception as e:
            logger.warning(f"Erro ao exibir preview: {e}")
    
    def extract_flight_params(self, df):
        """Try to extract flight parameters from the DataFrame."""
        try:
            # Procurar colunas comuns (case-insensitive) usando nomes mapeados
            columns_lower = {col.lower(): col for col in df.columns}
            
            # Matrícula/Tail
            for tail_col in ['tail', 'matricula', 'aircraft', 'registration', 'tail_number']:
                if tail_col in columns_lower:
                    tail = df[columns_lower[tail_col]].iloc[0]
                    self.param_value_labels["TAIL NUMBER:"].setText(str(tail))
                    break
            
            # Número do voo - usar nome mapeado flight_number
            for flight_col in ['flight_number', 'flight', 'voo', 'flight_no', 'numero_voo', 'flt']:
                if flight_col in columns_lower:
                    flight = df[columns_lower[flight_col]].iloc[0]
                    self.param_value_labels["FLIGHT NUMBER:"].setText(str(flight))
                    break
            
            # Data/Hora - usar nome mapeado timestamp
            for date_col in ['timestamp', 'datetime', 'date_time', 'date', 'data', 'hora']:
                if date_col in columns_lower:
                    date = df[columns_lower[date_col]].iloc[0]
                    self.param_value_labels["DATE/TIME:"].setText(str(date))
                    break
            
            # Duração (se disponível) - calcular do timestamp
            if 'timestamp' in columns_lower and len(df) > 1:
                try:
                    import pandas as pd
                    ts_col = columns_lower['timestamp']
                    first_time = pd.to_datetime(df[ts_col].iloc[0])
                    last_time = pd.to_datetime(df[ts_col].iloc[-1])
                    duration = last_time - first_time
                    # Formatar duração
                    total_seconds = int(duration.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    self.param_value_labels["DURATION:"].setText(duration_str)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Erro ao extrair parâmetros: {e}")

    def _get_flight_metadata(self, df) -> dict:
        """Extract flight metadata (tail, flight number, event time) from the DataFrame."""
        metadata = {
            "tail_number": None,
            "flight_number": None,
            "event_time": None,
        }

        if df is None or len(df) == 0:
            return metadata

        metadata["tail_number"] = self._extract_value(
            df, ['tail', 'tail_number', 'matricula', 'registration', 'aircraft']
        )
        metadata["flight_number"] = self._extract_value(
            df, ['flight_number', 'flight', 'flight_no', 'numero_voo', 'flt', 'voo']
        )
        metadata["event_time"] = self._extract_value(
            df, ['timestamp', 'datetime', 'date_time', 'date', 'data', 'hora', 'time']
        )
        if metadata["event_time"] is None and "TIMESTAMP" in df.columns:
            try:
                metadata["event_time"] = df["TIMESTAMP"].iloc[0]
            except Exception:
                metadata["event_time"] = None

        return metadata

    @staticmethod
    def _extract_value(df, column_names: list[str]):
        """Extract the first available value from candidate columns (case-insensitive)."""
        try:
            columns_lower = {col.lower(): col for col in df.columns}
            for name in column_names:
                key = name.lower()
                if key in columns_lower:
                    return df[columns_lower[key]].iloc[0]
        except Exception:
            return None
        return None
    
    def analyze_data(self):
        """Analisa os dados importados usando analisadores específicos"""
        self.hard_landing_results = None
        self.analysis_results = None
        self.current_analysis_event_id = None
        self.current_analysis_event_name = None
        if self.current_data is None:
            QMessageBox.warning(
                self,
                "No Data",
                "Please import a data file before running analysis."
            )
            return
        
        if not self.current_aircraft_id or not self.current_event_id:
            QMessageBox.warning(
                self,
                "Contexto Inválido",
                "Analysis context was not set correctly."
            )
            return

        if self.current_data_context and self.current_data_context != (self.current_aircraft_id, self.current_event_id):
            QMessageBox.warning(
                self,
                "Mismatched Context",
                "The imported data belongs to a different event/family. Click CLEAR and import again."
            )
            return
        
        try:
            # Check if DataFrame has valid data
            if len(self.current_data) == 0:
                QMessageBox.warning(
                    self,
                    "Empty Data",
                    "The imported file does not contain valid data for analysis."
                )
                return
            
            # Determinar qual analisador usar baseado no evento
            event_id = self.current_event_id or ""
            self.current_analysis = None
            self.results_text.setText("")

            missing = self._validate_event_columns(event_id, self.current_data)
            if missing:
                QMessageBox.warning(
                    self,
                    "Missing Data",
                    "Required columns are missing for this analysis:\n\n"
                    + "\n".join(missing)
                )
                return

            cache_key = (
                self.current_aircraft_id,
                event_id,
                self.current_file_signature,
                "auto"
            )
            cached = self.analysis_cache.get(cache_key) if self.current_file_signature else None
            if cached:
                self.current_analysis = cached.analysis_obj
                self.results_text.setText(cached.result_text)
                cached_event_id = (cached.metadata or {}).get("event_id", event_id)
                self.current_analysis_event_id = cached_event_id
                self.current_analysis_event_name = self.current_event_name

                if cached_event_id == "hard_landing":
                    self.hard_landing_results = getattr(self.current_analysis, "results", None)
                    self.analysis_results = None
                else:
                    self.analysis_results = getattr(self.current_analysis, "results", None)
                    self.hard_landing_results = None

                self.export_button.setEnabled(True)
                self.clear_button.setEnabled(True)
                return
            
            results_text = ""
            
            analysis_df = self.current_data

            if event_id == "hard_landing":
                # Usar HardLandingAnalyzer
                analyzer = HardLandingAnalyzer()
                
                # Extrair peso do DataFrame
                weight_kg = self._extract_weight(self.current_data, None)
                
                # Determinar modelo (auto-detectar se não houver contexto)
                if self.current_aircraft_id:
                    model = self._get_model_from_aircraft_id(self.current_aircraft_id)
                else:
                    model = self._detect_model_from_data(self.current_data)
                
                logger.info(f"Modelo detectado: {model}, Peso: {weight_kg:.0f} kg")
                logger.info(f"Colunas disponíveis: {list(self.current_data.columns)}")
                
                # Executar análise
                results = analyzer.analyze(analysis_df, weight_kg, model)
                
                # Armazenar resultados para uso pela IA
                self.hard_landing_results = results
                self.analysis_results = None
                self.current_analysis = type('obj', (object,), {'results': results, 'event_type': event_id})()
                self.current_analysis_event_id = event_id
                self.current_analysis_event_name = self.current_event_name
                
                # Exibir resultados
                results_text = self._format_hard_landing_results(results, model, weight_kg)
                
            elif event_id == "over_g":
                # Usar OverGAnalyzer
                analyzer = OverGAnalyzer()
                model = self._get_model_from_aircraft_id(self.current_aircraft_id)
                result = analyzer.analyze_over_g(analysis_df, model)
                results_text = self._format_over_g_results(result)
                self.current_analysis = type('obj', (object,), {'results': [result], 'event_type': event_id})()
                self.current_analysis_event_id = event_id
                self.current_analysis_event_name = self.current_event_name
                self.analysis_results = None
                self.hard_landing_results = None
                
            else:
                # Usar RulesEngine genérico para outros eventos
                analysis = RulesEngine.analyze(analysis_df, self.current_aircraft_id, self.current_event_id)
                self.display_analysis_results(analysis)
                self.current_analysis = analysis
                self.analysis_results = analysis.results
                self.hard_landing_results = None
                self.current_analysis_event_id = event_id
                self.current_analysis_event_name = self.current_event_name
                self.export_button.setEnabled(True)

                cache_key = (
                    self.current_aircraft_id,
                    event_id,
                    self.current_file_signature,
                    "auto"
                )
                if self.current_file_signature:
                    entry = CacheEntry(
                        result_text=self.results_text.toPlainText(),
                        analysis_obj=analysis,
                        metadata={"aircraft_id": self.current_aircraft_id, "event_id": event_id, "manual_model": None}
                    )
                    self.analysis_cache.set(cache_key, entry)

                self._append_audit_log(event_id, "rules_engine")
                return
            
            # Mostrar resultados
            results_text += self._get_pdf_references_text()
            self.results_text.setText(results_text)

            cache_key = (
                self.current_aircraft_id,
                event_id,
                self.current_file_signature,
                "auto"
            )
            if self.current_file_signature:
                entry = CacheEntry(
                    result_text=results_text,
                    analysis_obj=self.current_analysis,
                    metadata={"aircraft_id": self.current_aircraft_id, "event_id": event_id, "manual_model": None}
                )
                self.analysis_cache.set(cache_key, entry)

            self._append_audit_log(event_id, "custom_analyzer")
            
            # Colorir baseado no conteúdo
            if "CRITICAL" in results_text or "ENGINE" in results_text or "SEVERE" in results_text:
                self.results_text.setStyleSheet(f"background-color: #FFEBEE; color: {AppColors.TEXT_PRIMARY}; border: 2px solid {AppColors.ERROR}; border-radius: 6px; padding: 10px; font-family: 'Consolas', 'Courier New', monospace;")
            elif "HIGH" in results_text or "WARNING" in results_text:
                self.results_text.setStyleSheet(f"background-color: #FFF3E0; color: {AppColors.TEXT_PRIMARY}; border: 2px solid {AppColors.WARNING}; border-radius: 6px; padding: 10px; font-family: 'Consolas', 'Courier New', monospace;")
            elif "LOW" in results_text:
                self.results_text.setStyleSheet(f"background-color: #E3F2FD; color: {AppColors.TEXT_PRIMARY}; border: 2px solid {AppColors.PRIMARY}; border-radius: 6px; padding: 10px; font-family: 'Consolas', 'Courier New', monospace;")
            else:
                self.results_text.setStyleSheet(f"background-color: #E8F5E9; color: {AppColors.TEXT_PRIMARY}; border: 2px solid {AppColors.SUCCESS}; border-radius: 6px; padding: 10px; font-family: 'Consolas', 'Courier New', monospace;")
            
            # Habilitar exportação
            self.export_button.setEnabled(True)
            self.clear_button.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Analysis Error",
                f"An error occurred during analysis:\n\n{str(e)}"
            )
            logger.error(f"Erro na análise: {e}", exc_info=True)
    
    def display_analysis_results(self, analysis):
        """Display analysis results in the UI."""
        # Montar texto de resultados
        results_text = f"{'='*60}\n"
        results_text += f"ANALYSIS REPORT\n"
        results_text += f"{'='*60}\n\n"
        
        results_text += f"📋 Flight Information:\n"
        results_text += f"   • Tail Number: {analysis.tail_number or 'N/A'}\n"
        if analysis.flight_number:
            results_text += f"   • Flight Number: {analysis.flight_number}\n"
        results_text += f"   • Aircraft: {self.current_aircraft_name}\n"
        results_text += f"   • Event Type: {self.current_event_name}\n"

        timestamp_value = getattr(analysis, 'timestamp', None)
        if timestamp_value:
            if hasattr(timestamp_value, "strftime"):
                event_time = timestamp_value.strftime('%Y-%m-%d %H:%M:%S')
            else:
                event_time = str(timestamp_value)
        else:
            event_time = "N/A"
        results_text += f"   • Event Time: {event_time}\n"
        results_text += self._get_pdf_references_text(prefix="   • ")
        results_text += "\n"
        
        # Status geral
        status_icons = {
            "OK": "✅",
            "WARNING": "⚠️",
            "VIOLATION": "❌",
            "NO_DATA": "ℹ️",
            "NO_RULES": "⚙️"
        }
        status_icon = status_icons.get(analysis.overall_status, "❓")
        results_text += f"📊 Overall Status: {status_icon} {analysis.overall_status}\n\n"
        
        # Resultados detalhados
        if analysis.results:
            results_text += f"{'='*60}\n"
            results_text += f"ANALYZED PARAMETERS\n"
            results_text += f"{'='*60}\n\n"
            
            for result in analysis.results:
                icon = status_icons.get(result.status, "•")
                results_text += f"{icon} {result.parameter}:\n"
                results_text += f"   Value: {result.value or 'N/A'}\n"
                results_text += f"   Limit: {result.limit or 'N/A'}\n"
                results_text += f"   Status: {result.status or 'N/A'}\n"
                results_text += f"   Severity: {result.severity or 'N/A'}\n"
                results_text += f"   Message: {result.message or 'N/A'}\n\n"
        
        # Recomendações
        if analysis.recommendations:
            results_text += f"{'='*60}\n"
            results_text += f"RECOMMENDATIONS\n"
            results_text += f"{'='*60}\n\n"
            for rec in analysis.recommendations:
                results_text += f"{rec}\n"
        
        # Atualizar texto
        self.results_text.setText(results_text)
        
        # Colorir baseado no status
        if analysis.overall_status == "OK":
            self.results_text.setStyleSheet(f"background-color: #E8F5E9; color: {AppColors.TEXT_PRIMARY}; border: 2px solid {AppColors.SUCCESS}; border-radius: 6px; padding: 10px;")
        elif analysis.overall_status == "WARNING":
            self.results_text.setStyleSheet(f"background-color: #FFF3E0; color: {AppColors.TEXT_PRIMARY}; border: 2px solid {AppColors.WARNING}; border-radius: 6px; padding: 10px;")
        elif analysis.overall_status == "VIOLATION":
            self.results_text.setStyleSheet(f"background-color: #FFEBEE; color: {AppColors.TEXT_PRIMARY}; border: 2px solid {AppColors.ERROR}; border-radius: 6px; padding: 10px;")
        else:
            self.results_text.setStyleSheet(f"background-color: #E3F2FD; color: {AppColors.TEXT_PRIMARY}; border: 2px solid {AppColors.INFO}; border-radius: 6px; padding: 10px;")
    
    def show_pdfs(self):
        """Emit signal to show technical PDFs."""
        if self.current_aircraft_id and self.current_event_id:
            self.view_pdfs_clicked.emit(
                self.current_aircraft_id,
                self.current_aircraft_name,
                self.current_event_id,
                self.current_event_name
            )
        else:
            QMessageBox.warning(
                self,
                "Invalid Context",
                "Select a family and event before opening documents."
            )

    def clear_analysis_state(self, clear_context: bool = True):
        """Clear current analysis data and results."""
        self.current_data = None
        self.current_analysis = None
        self.current_data_context = None
        self.hard_landing_results = None
        self.analysis_results = None
        self.current_tail_number = None
        self.current_analysis_event_id = None
        self.current_analysis_event_name = None

        if clear_context:
            self.current_aircraft_id = None
            self.current_aircraft_name = None
            self.current_event_id = None
            self.current_event_name = None
            self.context_label.setText("")
            self.view_pdfs_button.setEnabled(False)

        self.file_label.setText("NO FILE SELECTED")
        self.file_label.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY}; padding: 15px;")

        self.results_text.clear()
        self.results_text.setPlaceholderText("Import a file to start analysis...")
        self.results_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {AppColors.SURFACE};
                border: 1px solid {AppColors.BORDER};
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }}
        """)

        self.analyze_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.clear_button.setEnabled(False)

        # Reset parameters
        for label in self.param_value_labels.values():
            label.setText("N/A")

        # Clear table preview
        if hasattr(self, 'data_table'):
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
    
    def export_report(self):
        """Export analysis report."""
        if not self.current_analysis or self.current_data is None:
            QMessageBox.warning(
                self,
                "No Analysis",
                "Please run an analysis before exporting."
            )
            return
        
        # Diálogo para escolher formato e local
        default_name = f"analysis_{self.current_aircraft_id}_{self.current_event_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Opções de formato
        file_filter = "Excel (*.xlsx);;PDF (*.pdf);;Text (*.txt)"
        
        output_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Report",
            default_name,
            file_filter
        )
        
        if not output_path:
            return
        
        try:
            # Converter análise para formato compatível
            analysis_results = []
            for result in self.current_analysis.results:
                # Criar objeto compatível com ReportGenerator
                class AnalysisResult:
                    def __init__(self, result):
                        self.severity = result.severity
                        self.message = result.message
                        self.value = result.value
                        self.limit = result.limit
                        self.recommendation = getattr(result, 'recommendation', 'Consult the maintenance manual')
                
                analysis_results.append(AnalysisResult(result))
            
            # Gerar relatório no formato escolhido
            if "Excel" in selected_filter or output_path.endswith('.xlsx'):
                output_file = self.report_generator.generate_excel_report(
                    self.current_data,
                    analysis_results,
                    self.current_aircraft_name,
                    self.current_event_name,
                    output_path
                )
            elif "PDF" in selected_filter or output_path.endswith('.pdf'):
                output_file = self.report_generator.generate_pdf_report(
                    self.current_data,
                    analysis_results,
                    self.current_aircraft_name,
                    self.current_event_name,
                    output_path
                )
            else:  # TXT
                output_file = self.report_generator.generate_txt_report(
                    self.current_data,
                    analysis_results,
                    self.current_aircraft_name,
                    self.current_event_name,
                    output_path
                )
            
            QMessageBox.information(
                self,
                "Export Completed",
                f"Report successfully exported!\n\n{output_file}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Error exporting report:\n{str(e)}"
            )
    
    def show_graphs(self):
        """Generate and display flight data graphs."""
        # Verificar se temos dados e análise
        if self.current_data is None:
            QMessageBox.warning(
                self,
                "No Data",
                "Please import a data file before generating graphs."
            )
            return

        if not self.current_analysis:
            QMessageBox.warning(
                self,
                "No Analysis",
                "Please run an analysis before generating graphs."
            )
            return

        if self.current_analysis_event_id and self.current_event_id:
            if self.current_analysis_event_id != self.current_event_id:
                QMessageBox.warning(
                    self,
                    "Mismatched Analysis",
                    "The current analysis belongs to a different event.\n\n"
                    "Run 'Analyze' again for this event before generating graphs."
                )
                return
        
        # Se for Hard Landing, gerar gráficos específicos
        if self.current_event_id == "hard_landing":
            try:
                # Verificar se há resultados de análise
                if not hasattr(self, 'hard_landing_results') or not self.hard_landing_results:
                    QMessageBox.warning(
                        self,
                        "No Analysis",
                        "Run 'Analyze' first to generate the required results."
                    )
                    return
                
                from services.hard_landing_graph_generator import HardLandingGraphGenerator
                
                # Criar gerador de gráficos
                generator = HardLandingGraphGenerator()
                
                # Gerar gráficos
                tail = getattr(self, 'current_tail_number', 'N/A')
                
                QMessageBox.information(
                    self,
                    "Generating Graphs",
                    "Generating Hard Landing graphs...\n\nThis may take a few seconds."
                )
                
                # Gerar todos os gráficos usando hard_landing_results
                graph_files = generator.generate_all_graphs(
                    self.current_data,
                    self.hard_landing_results,
                    self.current_aircraft_name,
                    tail
                )
                
                if graph_files:
                    # Exibir gráficos em janela do app
                    self._show_graphs_dialog(graph_files)
                else:
                    QMessageBox.warning(
                        self,
                        "No Graphs",
                        "Unable to generate graphs.\n\nCheck that the data contains the required columns."
                    )
                    
            except Exception as e:
                logger.error(f"Erro ao gerar gráficos: {e}", exc_info=True)
                import traceback
                detail = traceback.format_exc()
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Error generating graphs:\n\n{str(e)}\n\nDetails:\n{detail}"
                )
        else:
            # Para outros eventos, gerar gráficos universais
            try:
                validation_results = self._build_validation_results_for_event()
                if not validation_results:
                    QMessageBox.warning(
                        self,
                        "No Graph Data",
                        "Unable to generate graphs for this event.\n\n"
                        "Check that the data contains numeric columns for the analysis results."
                    )
                    return

                generator = UniversalGraphGenerator()
                tail = getattr(self, 'current_tail_number', 'N/A')

                graph_files = generator.generate_all_graphs(
                    self.current_data,
                    validation_results,
                    self.current_aircraft_name or "UNKNOWN",
                    self.current_event_id or "unknown_event",
                    tail
                )

                if graph_files:
                    self._show_graphs_dialog(graph_files)
                else:
                    QMessageBox.warning(
                        self,
                        "No Graphs",
                        "Unable to generate graphs.\n\nCheck the logs for details."
                    )

            except Exception as e:
                logger.error(f"Erro ao gerar gráficos: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Error generating graphs:\n\n{str(e)}"
                )
    
    def _weight_to_kg(self, weight_value, col_name: str | None = None) -> float | None:
        """Converte peso para kg com heurística de unidade."""
        if weight_value is None:
            return None

        try:
            weight_float = float(weight_value)
        except Exception:
            return None

        col_lower = (col_name or "").lower()

        # Prioridade: identificar unidade pelo nome da coluna
        if "kg" in col_lower and "lb" not in col_lower:
            logger.info(f"Peso detectado em kg via coluna '{col_name}': {weight_float:.1f} kg")
            return weight_float
        if "lb" in col_lower or "lbs" in col_lower:
            weight_kg = weight_float * 0.453592
            logger.info(f"Peso detectado em lb via coluna '{col_name}': {weight_float:.1f} lb = {weight_kg:.1f} kg")
            return weight_kg

        # Heurística quando unidade não é clara
        # Valores típicos em kg: 18k-60k | em lb: 40k-140k
        if weight_float > 60000:
            weight_kg = weight_float * 0.453592
            logger.info(f"Peso presumido em lb (heurística): {weight_float:.1f} lb = {weight_kg:.1f} kg")
            return weight_kg

        logger.info(f"Peso presumido em kg (heurística): {weight_float:.1f} kg")
        return weight_float

    def _build_validation_results_for_event(self) -> list[ValidationResult]:
        """Build ValidationResult list aligned with the current event analysis."""
        event_id = self.current_event_id or ""
        if self.current_data is None:
            return []

        validator = ParameterValidator()
        model_id = self._get_model_from_aircraft_id(self.current_aircraft_id)

        try:
            if event_id == "gear_overspeed":
                report = validator.validate_gear_overspeed(self.current_data, model_id)
                return report.validation_results
            if event_id == "temp_envelope":
                report = validator.validate_temperature_envelope(self.current_data, model_id)
                return report.validation_results
            if event_id == "max_speed":
                report = validator.validate_max_speed(self.current_data, model_id)
                return report.validation_results
            if event_id == "flap_overspeed":
                report = validator.validate_flap_overspeed(self.current_data, model_id)
                return report.validation_results
            if event_id == "overweight_landing":
                report = validator.validate_overweight_landing(self.current_data, model_id)
                return report.validation_results
        except Exception as exc:
            logger.warning(f"Validation fallback for graphs: {exc}")

        return self._convert_analysis_to_validation_results()

    def _convert_analysis_to_validation_results(self) -> list[ValidationResult]:
        """Convert current_analysis results to ValidationResult for graphing."""
        results = []
        analysis = getattr(self, "current_analysis", None)
        if not analysis:
            return results

        for result in getattr(analysis, "results", []) or []:
            value_num = self._parse_numeric_value(getattr(result, "value", None))
            limit_num = self._parse_numeric_value(getattr(result, "limit", None))
            if value_num is None or limit_num is None:
                continue

            status = getattr(result, "severity", "LOW")
            status_map = {
                "LOW": "OK",
                "MEDIUM": "WARNING",
                "HIGH": "CRITICAL",
                "CRITICAL": "CRITICAL",
                "OK": "OK",
                "VIOLATION": "CRITICAL",
            }
            normalized_status = status_map.get(status, "OK")

            exceedance_percent = 0.0
            if limit_num != 0:
                exceedance_percent = max(0.0, (value_num - limit_num) / limit_num * 100.0)

            results.append(ValidationResult(
                parameter=getattr(result, "parameter", "Parameter"),
                value=value_num,
                limit=limit_num,
                unit="",
                status=normalized_status,
                exceedance_percent=exceedance_percent,
                message=getattr(result, "message", ""),
                manual_reference=""
            ))

        return results

    @staticmethod
    def _parse_numeric_value(value) -> float | None:
        """Parse the first numeric value from mixed strings like 'IAS=320 KIAS'."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            text = str(value)
        except Exception:
            return None

        import re
        match = re.search(r"-?\d+\.?\d*", text)
        if not match:
            return None
        try:
            return float(match.group(0))
        except Exception:
            return None

    def _extract_weight(self, df, model_hint_override: str | None = None):
        """Extrai peso da aeronave do DataFrame"""
        import pandas as pd  # ✅ Import necessário aqui
        try:
            # Procurar coluna de peso
            weight_cols = [col for col in df.columns if 'weight' in col.lower() or 'gross' in col.lower()]
            if weight_cols:
                col_name = weight_cols[0]
                # Se há colunas duplicadas, iloc[:, 0] garante pegar primeira coluna como Series
                weight_data = df[col_name]
                if isinstance(weight_data, pd.DataFrame):
                    # DataFrame: pegar primeira coluna e primeiro valor válido
                    weight_value = weight_data.iloc[:, 0].dropna().iloc[0]
                else:
                    # Series: pegar primeiro valor válido
                    weight_value = weight_data.dropna().iloc[0]
                
                # Garantir que temos um valor escalar numérico
                if isinstance(weight_value, pd.Series):
                    weight_value = weight_value.iloc[0]

                weight_kg = self._weight_to_kg(weight_value, col_name)
                if weight_kg is not None:
                    return weight_kg
            # Peso padrão se não encontrar - usar MLW por modelo
            model_hint = None
            if model_hint_override:
                model_hint = get_model_name_for_analyzers(model_hint_override) or self._get_model_from_aircraft_id(model_hint_override)
            elif self.current_aircraft_id:
                model_hint = self._get_model_from_aircraft_id(self.current_aircraft_id)
            if not model_hint:
                model_hint = self._detect_model_from_data(df)
            
            default_weights_lb = {
                'E135': 40565,
                'E140': 42329,
                'E145': 48000,
                'E170': 69224,
                'E175': 75000,
                'E190': 97000,
                'E195': 100309,
                'E190-E2': 109127,
                'E195-E2': 115963
            }
            default_lb = default_weights_lb.get(model_hint or 'E190', 97000)
            logger.warning(
                f"Coluna de peso não encontrada no CSV, usando peso padrão {model_hint or 'E190'} ({default_lb:.0f} lb)"
            )
            return default_lb * 0.453592
        except Exception as e:
            logger.error(f"Erro ao extrair peso: {e}")
            return 75000 * 0.453592
    
    def _detect_model_from_data(self, df):
        """Detecta modelo da aeronave a partir dos dados do arquivo"""
        # 1) Tentar identificar pelo tipo de aeronave no CSV
        type_value = self._extract_value(
            df,
            [
                'aircraft type', 'aircraft_type', 'aircraft model',
                'modelo', 'model', 'tipo aeronave'
            ]
        )
        if type_value:
            model_from_type = self._normalize_model_from_text(str(type_value))
            if model_from_type:
                logger.info(f"Modelo detectado por Aircraft Type: {model_from_type}")
                return model_from_type

        # Tentar encontrar coluna de tail number ou flight number
        tail_cols = [col for col in df.columns if 'tail' in col.lower() or 'ac' in col.lower()]
        flt_cols = [col for col in df.columns if 'flt' in col.lower() or 'flight' in col.lower()]
        
        # Verificar pelo peso (gross_weight típico por modelo)
        weight_cols = [col for col in df.columns if 'weight' in col.lower() or 'gross' in col.lower()]
        if weight_cols:
            try:
                # Se há colunas duplicadas, usar iloc[:, 0]
                weight_data = df[weight_cols[0]]
                if isinstance(weight_data, pd.DataFrame):
                    weight_series = weight_data.iloc[:, 0]
                else:
                    weight_series = weight_data
                
                # Garantir que temos Series válida
                if isinstance(weight_series, pd.DataFrame):
                    weight_series = weight_series.iloc[:, 0]
                
                # Usar primeiro valor válido em vez de média (mais confiável)
                first_weight_val = weight_series.dropna().iloc[0]
                weight_kg = self._weight_to_kg(first_weight_val, weight_cols[0])
                if weight_kg is None:
                    raise ValueError("Peso inválido para detecção de modelo")
                
                logger.info(f"Detectando modelo por peso: {weight_kg:.1f} kg")
                
                # E145: MLW=21772kg (typical landing: 19-24 ton)
                # E170: MLW=31400kg (typical landing: 28-32 ton)
                # E175: MLW=34019kg (typical landing: 31-38 ton)
                # E190: MLW=44000kg (typical landing: 38-51 ton) ← 94000lb = 42.6 ton
                # E195: MLW=49895kg (typical landing: 45-55 ton)
                # Thresholds ajustados: 26000kg (E145/E170), 33000kg (E170/E175), 39000kg (E175/E190), 48000kg (E190/E195)
                if weight_kg < 26000:
                    logger.info(f"Modelo detectado: E145 (peso {weight_kg:.1f} kg < 26000 kg)")
                    return 'E145'
                elif weight_kg < 33000:
                    logger.info(f"Modelo detectado: E170 (peso {weight_kg:.1f} kg < 33000 kg)")
                    return 'E170'
                elif weight_kg < 39000:  # Separação E175/E190 em 39 ton
                    logger.info(f"Modelo detectado: E175 (peso {weight_kg:.1f} kg < 39000 kg)")
                    return 'E175'
                elif weight_kg < 48000:  # Separação E190/E195 em 48 ton
                    logger.info(f"Modelo detectado: E190 (peso {weight_kg:.1f} kg < 48000 kg)")
                    return 'E190'
                else:
                    logger.info(f"Modelo detectado: E195 (peso {weight_kg:.1f} kg >= 48000 kg)")
                    return 'E195'
            except Exception as e:
                logger.warning(f"Erro na detecção de modelo por peso: {e}")
                pass
        
        # Default por família selecionada, quando disponível
        if self.current_aircraft_id:
            default_model = self._get_model_from_aircraft_id(self.current_aircraft_id)
            logger.warning(
                f"Não foi possível detectar modelo automaticamente, usando {default_model} como padrão"
            )
            return default_model
        
        logger.warning("Não foi possível detectar modelo automaticamente, usando E190 como padrão")
        return 'E190'
    
    def _get_model_from_aircraft_id(self, aircraft_id):
        """Mapeia aircraft_id para modelo"""
        if not aircraft_id:
            return 'E190'
        model = self._normalize_model_from_text(str(aircraft_id))
        if model:
            return model
        
        mapping = {
            'e145': 'E145',
            'e170': 'E170',
            'e175': 'E175',
            'e190': 'E190',
            'e195': 'E195',
            'e175_e2': 'E175-E2',
            'e1': 'E190',  # Default E1 - Mexicana 190 (AMM 05-50-03)
            'e190_e2': 'E190-E2',
            'e195_e2': 'E195-E2',
            'e2': 'E190-E2'  # Default E2
        }
        return mapping.get(aircraft_id.lower(), 'E190')

    @staticmethod
    def _normalize_model_from_text(text: str) -> str | None:
        """Normaliza texto e tenta extrair o modelo da aeronave"""
        text_lower = text.lower().replace(' ', '').replace('_', '').replace('-', '')
        if 'erj145' in text_lower or 'e145' in text_lower:
            return 'E145'
        if 'erj140' in text_lower or 'e140' in text_lower:
            return 'E140'
        if 'erj135' in text_lower or 'e135' in text_lower:
            return 'E135'
        if 'e170' in text_lower:
            return 'E170'
        if 'e175' in text_lower:
            return 'E175'
        if 'e175e2' in text_lower:
            return 'E175-E2'
        if 'e195e2' in text_lower or 'e195e2' in text_lower:
            return 'E195-E2'
        if 'e190e2' in text_lower or 'e190e2' in text_lower:
            return 'E190-E2'
        if 'e195' in text_lower:
            return 'E195'
        if 'e190' in text_lower:
            return 'E190'
        if text_lower == 'e2':
            return 'E190-E2'
        if text_lower == 'e1':
            return 'E190'
        return None
    
    def _get_file_signature(self, path: Path) -> str:
        """Gera assinatura simples do arquivo para cache"""
        try:
            stat = path.stat()
            return f"{path.resolve()}::{stat.st_mtime}::{stat.st_size}"
        except Exception:
            return str(path.resolve())

    def _get_pdf_references_text(self, prefix: str = "") -> str:
        """Return text with PDFs applied to this analysis."""
        if not self.current_aircraft_id or not self.current_event_id:
            return ""

        base_path = Path(__file__).parent.parent.parent
        pdf_paths = PDFMapper.get_pdfs_for_event(self.current_aircraft_id, self.current_event_id, base_path)
        if not pdf_paths:
            missing = PDFMapper.get_missing_expected_tasks(
                self.current_aircraft_id,
                self.current_event_id,
                base_path
            )
            missing_text = f" Missing expected tasks: {', '.join(missing)}" if missing else ""
            return f"{prefix}• PDFs applied: No documents found.{missing_text}\n"

        pdf_names = ", ".join([p.name for p in pdf_paths])
        missing = PDFMapper.get_missing_expected_tasks(
            self.current_aircraft_id,
            self.current_event_id,
            base_path
        )
        missing_text = f" | Missing expected tasks: {', '.join(missing)}" if missing else ""
        return f"{prefix}• PDFs applied: {pdf_names}{missing_text}\n"

    def _update_context_label(self):
        """Update the context label."""
        if not self.current_aircraft_name or not self.current_event_name:
            self.context_label.setText("")
            return

        base_text = f"{self.current_aircraft_name} - {self.current_event_name}"
        self.context_label.setText(base_text)

    def _validate_event_columns(self, event_id: str, df) -> list[str]:
        """Valida colunas mínimas para cada evento"""
        if df is None or len(df) == 0:
            return ["DataFrame vazio"]

        required_any = {
            "hard_landing": [["vertical_acceleration", "VERTICAL_ACCELERATION", "nz", "g_load"]],
            "gear_overspeed": [["airspeed", "IAS"]],
            "temp_envelope": [["temperature", "TAT", "EGT"]],
            "max_speed": [["airspeed", "IAS"]],
            "flap_overspeed": [["airspeed", "IAS"], ["flap_position", "FLAP_POSITION"]],
            "overweight_landing": [["gross_weight", "weight", "landing_weight", "grossweight"]],
            "turbulence": [["vertical_acceleration", "g_load", "nz"]],
            "over_g": [["vertical_acceleration", "g_load", "nz"]],
            "high_bank_angle": [["roll_attitude", "roll"]],
        }

        groups = required_any.get(event_id, [])
        missing = []
        for group in groups:
            if not any(col in df.columns for col in group):
                missing.append("/".join(group))
        return missing

    def _append_audit_log(self, event_id: str, analyzer: str) -> None:
        """Registra auditoria da análise"""
        try:
            append_audit_log(
                {
                    "aircraft_id": self.current_aircraft_id,
                    "aircraft_name": self.current_aircraft_name,
                    "event_id": event_id,
                    "event_name": self.current_event_name,
                    "analyzer": analyzer,
                    "file_signature": self.current_file_signature,
                    "rows": len(self.current_data) if self.current_data is not None else 0,
                },
                AppConfig.OUTPUT_DIR
            )
        except Exception as exc:
            logger.warning(f"Falha ao registrar auditoria: {exc}")

    def _format_hard_landing_results(self, results, model, weight_kg):
        """Format HardLandingAnalyzer results"""
        if not results:
            return "No flights detected in provided data."

        flight_meta = self._get_flight_metadata(self.current_data)
        event_time = flight_meta.get("event_time")
        event_time_text = str(event_time) if event_time is not None else "N/A"
        
        text = "=" * 80 + "\n"
        text += "HARD LANDING ANALYSIS\n"
        text += "=" * 80 + "\n\n"
        
        text += f"Model: {model or 'N/A'}\n"
        text += f"Tail Number: {flight_meta.get('tail_number') or 'N/A'}\n"
        if flight_meta.get("flight_number"):
            text += f"Flight Number: {flight_meta.get('flight_number')}\n"
        text += f"Event Time: {event_time_text}\n"
        if weight_kg:
            text += f"Weight: {weight_kg:.0f} kg ({weight_kg * 2.20462:.0f} lb)\n"
        else:
            text += "Weight: N/A\n"
        text += f"Flights detected: {len(results)}\n\n"
        
        for i, result in enumerate(results, 1):
            text += "=" * 80 + "\n"
            text += f"FLIGHT {i}\n"
            text += "=" * 80 + "\n\n"
            
            # Status
            status_map = {
                'NORMAL': '✓ NORMAL',
                'HARD_LANDING_LOW': '⚠ HARD LANDING (LOW)',
                'HARD_LANDING_HIGH': '⚠⚠ HARD LANDING (HIGH)',
                'ENGINE_INSPECTION': '🔴 CRITICAL - ENGINE INSPECTION REQUIRED'
            }
            status = getattr(result, 'status', 'UNKNOWN')
            severity = getattr(result, 'severity', 'UNKNOWN')
            text += f"STATUS: {status_map.get(status, status)}\n"
            text += f"SEVERITY: {severity}\n\n"
            
            # Monitor 1: Vertical Acceleration
            text += "─" * 80 + "\n"
            text += "MONITOR 1: VERTICAL ACCELERATION\n"
            text += "─" * 80 + "\n"
            vert = getattr(result, 'vertical_accel', {})
            if isinstance(vert, dict):
                text += f"Status: {vert.get('status', 'N/A')}\n"
                if 'max_g' in vert and vert['max_g'] is not None:
                    text += f"Maximum Acceleration: {vert['max_g']:.3f} G\n"
                if 'thresholds' in vert:
                    th = vert['thresholds']
                    text += f"Thresholds:\n"
                    if 'low' in th and th['low'] is not None:
                        text += f"  - LOW:    {th['low']:.2f} G\n"
                    if 'high' in th and th['high'] is not None:
                        text += f"  - HIGH:   {th['high']:.2f} G\n"
                    if 'engine' in th and th['engine'] is not None:
                        text += f"  - ENGINE: {th['engine']:.2f} G\n"
            text += "\n"
            
            # Monitor 2: Roll Rate
            text += "─" * 80 + "\n"
            text += "MONITOR 2: ROLL RATE\n"
            text += "─" * 80 + "\n"
            roll = getattr(result, 'roll_rate', {})
            if isinstance(roll, dict):
                text += f"Status: {roll.get('status', 'N/A')}\n"
                if 'max_roll_rate' in roll and roll['max_roll_rate'] is not None:
                    text += f"Maximum Roll Rate: {roll['max_roll_rate']:.2f} deg/s\n"
            text += "\n"
            
            # Monitor 3: Pitch Rate
            text += "─" * 80 + "\n"
            text += "MONITOR 3: PITCH RATE\n"
            text += "─" * 80 + "\n"
            pitch = getattr(result, 'pitch_rate', {})
            if isinstance(pitch, dict):
                text += f"Status: {pitch.get('status', 'N/A')}\n"
                if 'min_pitch_rate' in pitch and pitch['min_pitch_rate'] is not None:
                    text += f"Minimum Pitch Rate: {pitch['min_pitch_rate']:.2f} deg/s\n"
            text += "\n"
            
            # Message and recommendations
            text += "=" * 80 + "\n"
            text += "RESULT\n"
            text += "=" * 80 + "\n"
            message = getattr(result, 'message', 'No message')
            text += f"{message}\n"
            
            critical_monitors = getattr(result, 'critical_monitors', [])
            if critical_monitors:
                text += f"\nCritical Monitors: {', '.join(critical_monitors)}\n"
            
            if status != 'NORMAL':
                text += "\n⚠ ACTION REQUIRED:\n"
                text += "Consult AMM 05-50-03 for inspection procedures.\n"
            
            text += "\n"
        
        return text
    
    def _format_over_g_results(self, result):
        """Format OverGAnalyzer results"""
        text = "=" * 80 + "\n"
        text += "OVER-G ANALYSIS\n"
        text += "=" * 80 + "\n\n"

        flight_meta = self._get_flight_metadata(self.current_data)
        event_time = flight_meta.get("event_time")
        event_time_text = str(event_time) if event_time is not None else "N/A"
        text += f"Tail Number: {flight_meta.get('tail_number') or 'N/A'}\n"
        if flight_meta.get("flight_number"):
            text += f"Flight Number: {flight_meta.get('flight_number')}\n"
        text += f"Event Time: {event_time_text}\n\n"
        
        is_over_g = getattr(result, 'is_over_g', False)
        severity = getattr(result, 'severity_level', 'N/A')
        text += f"Status: {'EXCEEDANCE DETECTED' if is_over_g else 'NORMAL'}\n"
        text += f"Severity: {severity}\n\n"
        
        max_pos = getattr(result, 'max_positive_g', 0)
        max_neg = getattr(result, 'max_negative_g', 0)
        pos_thresh = getattr(result, 'positive_threshold', 0)
        neg_thresh = getattr(result, 'negative_threshold', 0)
        
        if max_pos is not None:
            text += f"Maximum Positive Acceleration: +{max_pos:.2f} G\n"
        if max_neg is not None:
            text += f"Maximum Negative Acceleration: {max_neg:.2f} G\n\n"
        
        if pos_thresh is not None:
            text += f"Positive Threshold: +{pos_thresh:.2f} G\n"
        if neg_thresh is not None:
            text += f"Negative Threshold: {neg_thresh:.2f} G\n\n"
        
        if is_over_g:
            exceedance = getattr(result, 'exceedance_count', 0)
            text += f"Exceedance Events: {exceedance}\n\n"
            
            actions = getattr(result, 'recommended_actions', [])
            if actions:
                text += "RECOMMENDED ACTIONS:\n"
                for action in actions:
                    text += f"  • {action}\n"
        
        return text
    
    def show_ai_assistant(self):
        """Show AI assistant dialog with intelligent analysis"""
        try:
            # Verificar se há dados carregados
            if not hasattr(self, 'current_data') or self.current_data is None:
                QMessageBox.information(
                    self,
                    "🤖 AI Assistant",
                    "Please load flight data first.\n\n"
                    "Use 'Import CSV' to load data before requesting AI analysis."
                )
                return
            
            # Verificar se há resultados de análise (aceitar self.current_analysis também)
            has_hard_landing = hasattr(self, 'hard_landing_results') and self.hard_landing_results
            has_analysis = hasattr(self, 'analysis_results') and self.analysis_results
            has_current_analysis = hasattr(self, 'current_analysis') and self.current_analysis is not None
            
            if not has_hard_landing and not has_analysis and not has_current_analysis:
                QMessageBox.information(
                    self,
                    "🤖 AI Assistant",
                    "No analysis results available.\n\n"
                    "Please run 'Analyze' first to generate results for AI interpretation."
                )
                return
            
            from services.ai_assistant import AIAssistant
            import pandas as pd
            from datetime import datetime
            
            # Initialize AI Assistant
            assistant = AIAssistant()
            logger.info("AI Assistant initialized successfully")
            
            # Preparar dados do voo
            analysis_event_id = self.current_analysis_event_id or getattr(self.current_analysis, 'event_type', None)
            if analysis_event_id and self.current_event_id and analysis_event_id != self.current_event_id:
                QMessageBox.information(
                    self,
                    "🤖 AI Assistant",
                    "The AI report is based on a different event analysis.\n\n"
                    "Run 'Analyze' for the current event before requesting AI analysis."
                )
                return

            aircraft_name = getattr(self, 'current_aircraft_name', 'Unknown Aircraft')
            event_name = getattr(self, 'current_event_name', 'Analysis')
            
            flight_data = {
                "aircraft": aircraft_name,
                "event": event_name,
                "tail_number": "N/A",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Gerar relatório baseado nos resultados disponíveis
            report_text = self._generate_ai_report(assistant, flight_data)
            
            # Criar dialog para mostrar análise
            self._show_ai_dialog(report_text)
            
        except Exception as e:
            logger.error(f"Erro no AI Assistant: {e}", exc_info=True)
            error_report = f"Erro ao gerar relatório:\n\n{str(e)}"
            QMessageBox.critical(
                self,
                "AI Assistant Error",
                f"An error occurred while generating AI analysis:\n\n{str(e)}\n\n"
                "Please check the logs for details."
            )
            
            # Create dialog to show AI analysis
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
            
            dialog = QDialog(self)
            dialog.setWindowTitle("🤖 AI Assistant - Analysis Report")
            dialog.resize(700, 600)
            
            layout = QVBoxLayout(dialog)
            
            # Report text
            report_text = QTextEdit()
            report_text.setReadOnly(True)
            report_text.setPlainText(report)
            report_text.setStyleSheet("""
                QTextEdit {
                    background-color: #F5F5F5;
                    border: 2px solid #2196F3;
                    border-radius: 8px;
                    padding: 15px;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 13px;
                }
            """)
            layout.addWidget(report_text)
            
            # Close button
            close_button = QPushButton("Close")
            close_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2196F3, stop:0.5 #1976D2, stop:1 #0D47A1);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-weight: bold;
                    min-height: 40px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #42A5F5, stop:0.5 #2196F3, stop:1 #1976D2);
                }
            """)
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)
            
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Error showing AI dialog: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to display AI analysis:\n{str(e)}"
            )
    
    def _copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        from PyQt6.QtWidgets import QApplication
        
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        QMessageBox.information(
            self,
            "📋 Copied!",
            "AI analysis report copied to clipboard successfully!"
        )
    
    def _generate_ai_report(self, assistant, flight_data):
        """Generate enhanced AI technical analysis report"""
        report_parts = []
        aircraft_name = str(
            flight_data.get('aircraft')
            or self.current_aircraft_name
            or ''
        )

        analysis_event_id = self.current_analysis_event_id or self.current_event_id
        if (
            analysis_event_id == "hard_landing"
            and hasattr(self, 'hard_landing_results')
            and self.hard_landing_results
            and self._is_target_hard_landing_aircraft(aircraft_name)
        ):
            return self._generate_hard_landing_technical_report(flight_data)
        
        # Professional Header
        report_parts.append("="*80)
        report_parts.append("🤖 AI-POWERED TECHNICAL ANALYSIS SYSTEM")
        report_parts.append("   AUTOMATED FLIGHT DATA RECORDER (FDR) ANALYSIS")
        report_parts.append("="*80)
        report_parts.append("")
        report_parts.append(f"AIRCRAFT MODEL    : {flight_data['aircraft']}")
        report_parts.append(f"ANALYSIS TYPE     : {flight_data['event']}")
        report_parts.append(f"ANALYSIS DATE/TIME: {flight_data['timestamp']}")
        report_parts.append(f"TAIL NUMBER       : {flight_data.get('tail_number', 'N/A')}")
        report_parts.append("="*80)
        report_parts.append("")
        
        analysis_event_id = self.current_analysis_event_id or self.current_event_id

        # Hard Landing Analysis Results
        if analysis_event_id == "hard_landing" and hasattr(self, 'hard_landing_results') and self.hard_landing_results:
            report_parts.append("┌" + "─"*78 + "┐")
            report_parts.append("│ 📊 HARD LANDING ANALYSIS - DETAILED TECHNICAL ASSESSMENT" + " "*21 + "│")
            report_parts.append("└" + "─"*78 + "┘")
            report_parts.append("")
            
            for idx, result in enumerate(self.hard_landing_results, 1):
                report_parts.append(f"FLIGHT EVENT #{idx}")
                report_parts.append("-"*80)
                
                # Extract technical parameters
                max_g = None
                thresholds = {}
                if hasattr(result, 'vertical_accel') and result.vertical_accel:
                    max_g = result.vertical_accel.get('max_g')
                    thresholds = result.vertical_accel.get('thresholds', {})
                
                # Status assessment
                severity_color = "🟢" if result.status == "NORMAL" else "🟡" if "LOW" in result.status else "🔴"
                report_parts.append(f"{severity_color} STATUS: {result.status}")
                report_parts.append("")
                
                # Key Parameters
                report_parts.append("KEY PARAMETERS:")
                if max_g:
                    report_parts.append(f"  • Maximum Normal Acceleration: {max_g:.4f} G")
                    report_parts.append(f"  • Threshold Comparison:")
                    if thresholds:
                        report_parts.append(f"    - LOW Threshold  : {thresholds.get('low', 0):.3f}G {' [EXCEEDED]' if max_g > thresholds.get('low', 999) else ''}")
                        report_parts.append(f"    - HIGH Threshold : {thresholds.get('high', 0):.3f}G {' [EXCEEDED]' if max_g > thresholds.get('high', 999) else ''}")
                        report_parts.append(f"    - ENGINE Limit   : {thresholds.get('engine', 0):.3f}G {' [CRITICAL!]' if max_g > thresholds.get('engine', 999) else ''}")
                else:
                    report_parts.append("  • Maximum G-Force: DATA NOT AVAILABLE")
                
                report_parts.append("")
                
                # Critical Monitors
                if result.critical_monitors:
                    report_parts.append(f"⚠️  CRITICAL MONITORS TRIGGERED:")
                    for monitor in result.critical_monitors:
                        report_parts.append(f"  • {monitor}")
                    report_parts.append("")
                
                # Technical Assessment & Required Actions
                if result.status in ['HARD_LANDING_LOW', 'HARD_LANDING_HIGH', 'HARD_LANDING_ENGINE']:
                    report_parts.append("┌" + "─"*78 + "┐")
                    report_parts.append("│ 🔍 MANDATORY INSPECTION REQUIREMENTS" + " "*41 + "│")
                    report_parts.append("└" + "─"*78 + "┘")
                    report_parts.append("")
                    
                    if result.status == 'HARD_LANDING_LOW':
                        report_parts.append("INSPECTION PHASE: I (Basic Visual Inspection)")
                        report_parts.append("ESTIMATED DURATION: 2-4 hours")
                        report_parts.append("PRIORITY LEVEL: MEDIUM")
                        report_parts.append("")
                        report_parts.append("REQUIRED INSPECTIONS:")
                        report_parts.append("  1. Visual inspection of main landing gear assemblies")
                        report_parts.append("  2. Check for hydraulic fluid leaks")
                        report_parts.append("  3. Inspect tire condition and pressure")
                        report_parts.append("  4. Visual check of fuselage belly panels")
                        report_parts.append("  5. Verify landing gear doors operation")
                        
                    elif result.status == 'HARD_LANDING_HIGH':
                        report_parts.append("INSPECTION PHASE: II (Detailed Structural Inspection)")
                        report_parts.append("ESTIMATED DURATION: 8-12 hours")
                        report_parts.append("PRIORITY LEVEL: HIGH")
                        report_parts.append("")
                        report_parts.append("REQUIRED INSPECTIONS:")
                        report_parts.append("  1. DETAILED visual inspection per AMM 05-51-00")
                        report_parts.append("  2. Ultrasonic testing of landing gear components")
                        report_parts.append("  3. Inspection of wing attachment points")
                        report_parts.append("  4. Check fuselage frames for buckling/deformation")
                        report_parts.append("  5. Inspect floor beams and cargo floor panels")
                        report_parts.append("  6. Non-destructive testing (NDT) as per SRM")
                        report_parts.append("  7. Verify structural integrity of keel beam")
                        
                    elif result.status == 'HARD_LANDING_ENGINE':
                        report_parts.append("INSPECTION PHASE: III (Engine & Powerplant Inspection)")
                        report_parts.append("ESTIMATED DURATION: 24-48 hours")
                        report_parts.append("PRIORITY LEVEL: CRITICAL")
                        report_parts.append("")
                        report_parts.append("REQUIRED INSPECTIONS:")
                        report_parts.append("  1. ALL Phase II inspections (listed above)")
                        report_parts.append("  2. ENGINE BORESCOPE INSPECTION (both engines)")
                        report_parts.append("  3. Magnetic particle inspection of engine mounts")
                        report_parts.append("  4. Fan blade and inlet inspection")
                        report_parts.append("  5. Check engine cowling and nacelle structure")
                        report_parts.append("  6. Inspect thrust reverser system")
                        report_parts.append("  7. Verify engine indication parameters")
                        report_parts.append("  8. Ground run test if required")
                    
                    report_parts.append("")
                
                report_parts.append("-"*80)
                report_parts.append("")
        
        # Generic Analysis Summary for other events
        if analysis_event_id != "hard_landing" and getattr(self, "current_analysis", None) is not None:
            report_parts.append("┌" + "─"*78 + "┐")
            report_parts.append("│ 📊 EVENT ANALYSIS SUMMARY" + " "*48 + "│")
            report_parts.append("└" + "─"*78 + "┘")
            report_parts.append("")

            analysis = self.current_analysis
            results = getattr(analysis, "results", [])
            if not results:
                report_parts.append("No analysis results available for this event.")
                report_parts.append("")
            else:
                for result in results:
                    report_parts.append(f"• {result.parameter}: {result.message}")
                report_parts.append("")

        # AI-Enhanced Technical Recommendations
        report_parts.append("┌" + "─"*78 + "┐")
        report_parts.append("│ 💡 AI-ENHANCED RECOMMENDATIONS & PREDICTIVE ANALYSIS" + " "*25 + "│")
        report_parts.append("└" + "─"*78 + "┘")
        report_parts.append("")
        
        if analysis_event_id == "hard_landing" and hasattr(self, 'hard_landing_results') and self.hard_landing_results:
            for result in self.hard_landing_results:
                if result.status in ['HARD_LANDING_HIGH', 'HARD_LANDING_LOW', 'HARD_LANDING_ENGINE']:
                    report_parts.append("🔴 PRIORITY: IMMEDIATE ACTION REQUIRED")
                    report_parts.append("")
                    report_parts.append("IMMEDIATE ACTIONS (within 1 hour):")
                    report_parts.append("  ✓ Aircraft MUST remain grounded - NO DISPATCH until cleared")
                    report_parts.append("  ✓ Notify Chief of Maintenance immediately")
                    report_parts.append("  ✓ Preserve FDR/QAR data - create backup copy")
                    report_parts.append("  ✓ Interview flight crew for additional details")
                    report_parts.append("  ✓ Secure aircraft and prevent unauthorized access")
                    report_parts.append("")
                    report_parts.append("DOCUMENTATION REQUIREMENTS:")
                    report_parts.append("  • Complete Form: Hard Landing Report (per AMM 05-50-03)")
                    report_parts.append("  • Aircraft Technical Log entry with full details")
                    report_parts.append("  • Notify airline operations and dispatch")
                    report_parts.append("  • Report to aviation authority if regulatory threshold exceeded")
                    report_parts.append("  • Update maintenance tracking system")
                    report_parts.append("")
                    report_parts.append("TECHNICAL ANALYSIS:")
                    report_parts.append("  • Retrieve complete FDR data package for engineering review")
                    report_parts.append("  • Calculate actual sink rate at touchdown")
                    report_parts.append("  • Determine aircraft weight and CG at landing")
                    report_parts.append("  • Review weather conditions and runway state")
                    report_parts.append("  • Analyze approach profile and stabilization")
                    report_parts.append("")
                    
                    if result.status in ['HARD_LANDING_HIGH', 'HARD_LANDING_ENGINE']:
                        report_parts.append("ENGINEERING INVOLVEMENT REQUIRED:")
                        report_parts.append("  ⚠️  Contact OEM (Mexicana) Technical Support")
                        report_parts.append("  ⚠️  Structural engineering review mandatory")
                        report_parts.append("  ⚠️  Possible Service Bulletin compliance check")
                        report_parts.append("  ⚠️  Consider fleet-wide inspection if recurring pattern")
                        report_parts.append("")
                    
                    break
        else:
            report_parts.append("✅ AIRCRAFT STATUS: NOMINAL")
            report_parts.append("")
            report_parts.append("No critical events detected based on current analysis.")
            report_parts.append("")
            report_parts.append("RECOMMENDED ACTIONS:")
            report_parts.append("  • Continue normal flight operations")
            report_parts.append("  • Maintain standard inspection intervals")
            report_parts.append("  • Monitor landing parameters on subsequent flights")
            report_parts.append("  • Ensure crew awareness of hard landing thresholds")
            report_parts.append("")
        
        # Technical References
        report_parts.append("="*80)
        report_parts.append("📚 TECHNICAL REFERENCE DOCUMENTATION")
        report_parts.append("-"*80)
        report_parts.append("")
        report_parts.append("PRIMARY REFERENCES:")
        report_parts.append("  • AMM 05-50-03: Hard Landing Inspection Procedures")
        report_parts.append("  • AMM 05-51-00: Landing Gear Visual Inspection")
        report_parts.append("  • SRM 53-00-00: Fuselage Structure Repair")
        report_parts.append("  • SRM 57-00-00: Wing Structure Repair")
        report_parts.append("  • EMM 71-00-00: Engine Powerplant Inspection")
        report_parts.append("")
        report_parts.append("REGULATORY REFERENCES:")
        report_parts.append("  • EASA CS-25 / FAA 14 CFR Part 25 (Airworthiness Standards)")
        report_parts.append("  • AC 25-7D (Flight Test Guide for Certification)")
        report_parts.append("  • ICAO Annex 6 (Operation of Aircraft)")
        report_parts.append("")
        report_parts.append("• Flight Crew Operating Manual (FCOM)")
        report_parts.append("• Engine Manual (EMM) - If engine inspection required")
        report_parts.append("")
        report_parts.append("="*70)
        report_parts.append("")
        report_parts.append("⚠️  DISCLAIMER:")
        report_parts.append("This analysis is AI-generated and for guidance only.")
        report_parts.append("Always consult certified maintenance personnel and")
        report_parts.append("official maintenance manuals for final decisions.")
        report_parts.append("="*70)
        
        return "\n".join(report_parts)

    @staticmethod
    def _is_target_hard_landing_aircraft(aircraft_name: str) -> bool:
        """Check if aircraft should use technical hard-landing report format."""
        normalized = str(aircraft_name).upper()
        return any(
            token in normalized
            for token in [
                'E1',
                'E170',
                'E145',
                'E2',
                'E190-E2',
                'E195-E2',
                'EMB-145',
            ]
        )

    def _generate_hard_landing_technical_report(self, flight_data):
        """Generate concise technical report format for hard landing evaluation."""
        results = getattr(self, 'hard_landing_results', []) or []
        if not results:
            return "No hard landing results available."

        status_rank = {
            'NORMAL': 0,
            'HARD_LANDING_LOW': 1,
            'HARD_LANDING_HIGH': 2,
            'ENGINE_INSPECTION': 3,
            'HARD_LANDING_ENGINE': 3,
        }
        result = max(results, key=lambda item: status_rank.get(getattr(item, 'status', 'NORMAL'), 0))

        aircraft_label = str(flight_data.get('aircraft', 'MEXICANA')).upper()
        if 'E190-E2' in aircraft_label or 'E195-E2' in aircraft_label or 'E2' in aircraft_label:
            aircraft_display = 'MEXICANA E195-E2'
            amm_reference = 'AMM TASK 05-50-03-200-801-A'
        elif 'E145' in aircraft_label or 'EMB-145' in aircraft_label:
            aircraft_display = 'MEXICANA E145'
            amm_reference = 'AMM TASK 05-50-02-06-1'
        elif 'E170' in aircraft_label:
            aircraft_display = 'MEXICANA E170'
            amm_reference = 'AMM TASK 05-50-03-200-801-A'
        else:
            aircraft_display = 'MEXICANA E1 FAMILY'
            amm_reference = 'AMM TASK 05-50-03-200-801-A'

        vertical_data = getattr(result, 'vertical_accel', {}) or {}
        roll_data = getattr(result, 'roll_rate', {}) or {}
        pitch_data = getattr(result, 'pitch_rate', {}) or {}

        weight_kg = float(getattr(result, 'weight_kg', 0.0) or 0.0)
        max_roll = roll_data.get('max_rate')
        max_nz = vertical_data.get('max_g')
        vert_thresholds = vertical_data.get('thresholds', {}) or {}
        mlg_limit = vert_thresholds.get('high') or vert_thresholds.get('low')

        pitch_min = pitch_data.get('min_rate')
        pitch_thresholds = pitch_data.get('thresholds', {}) or {}
        nlg_limit = pitch_thresholds.get('high') or pitch_thresholds.get('low') or pitch_thresholds.get('threshold')

        mlg_hard = str(vertical_data.get('status', 'NORMAL')).startswith('HARD_LANDING')
        nlg_hard = str(pitch_data.get('status', 'NORMAL')).startswith('HARD_LANDING')

        if max_nz is not None and mlg_limit is not None:
            mlg_comparison = 'Value above limit.' if float(max_nz) > float(mlg_limit) else 'Value below limit.'
        else:
            mlg_comparison = 'Value not available.'

        if pitch_min is not None and nlg_limit is not None:
            nlg_comparison = (
                'Value more negative than limit.'
                if float(pitch_min) <= float(nlg_limit)
                else 'Value above limit.'
            )
        else:
            nlg_comparison = 'Value not available.'

        timestamp = str(flight_data.get('timestamp', '')).strip()
        if ' ' in timestamp:
            date_part, time_part = timestamp.split(' ', 1)
            timestamp_line = f"{time_part[:5]} LOCAL {date_part}"
        else:
            timestamp_line = timestamp or 'N/A'

        report_parts = []
        report_parts.append('TECHNICAL LANDING EVALUATION REPORT')
        report_parts.append(f"Aircraft: {aircraft_display}")
        report_parts.append('')
        report_parts.append('Event: Evaluation of possible Hard Landing')
        report_parts.append('')
        report_parts.append('Data Source: FDR / MXE')
        report_parts.append('')
        report_parts.append(
            f"Landing Weight (WB): {weight_kg:.0f} kg" if weight_kg > 0 else 'Landing Weight (WB): N/A'
        )
        report_parts.append('')
        report_parts.append(f"Reference: {amm_reference}")
        report_parts.append('')
        report_parts.append(f"DATE: {timestamp_line}")
        report_parts.append('')
        report_parts.append('MLG Evaluation')
        report_parts.append(
            f"* Max Roll Rate: {float(max_roll):.2f} deg/s" if max_roll is not None else '* Max Roll Rate: N/A'
        )
        report_parts.append(
            f"* Max Nz: {float(max_nz):.2f} g" if max_nz is not None else '* Max Nz: N/A'
        )
        if mlg_limit is not None and weight_kg > 0:
            report_parts.append(
                f"* AMM Limit for {weight_kg:.0f} kg: {float(mlg_limit):.2f} g → {mlg_comparison}"
            )
        else:
            report_parts.append(f"* AMM Limit: N/A → {mlg_comparison}")
        report_parts.append(
            'Hard Landing indication in the MLG.' if mlg_hard else 'No Hard Landing indication in the MLG.'
        )
        report_parts.append('')
        report_parts.append('NLG Evaluation')
        report_parts.append(
            f"* Min Pitch rate: {float(pitch_min):.2f} deg/s" if pitch_min is not None else '* Min Pitch rate: N/A'
        )
        if nlg_limit is not None:
            report_parts.append(
                f"* AMM Limit: more negative than {float(nlg_limit):.2f} deg/s → {nlg_comparison}"
            )
        else:
            report_parts.append(f"* AMM Limit: N/A → {nlg_comparison}")
        report_parts.append(
            'Hard Landing indication in the NLG.' if nlg_hard else 'No Hard Landing indication in the NLG.'
        )
        report_parts.append('')
        report_parts.append('Conclusion')
        report_parts.append(
            '→ Hard Landing in the MLG' if mlg_hard else '→ No Hard Landing in the MLG'
        )
        report_parts.append(
            '→ Hard Landing in the NLG' if nlg_hard else '→ No Hard Landing in the NLG'
        )
        if mlg_hard or nlg_hard:
            report_parts.append(
                f"The landing exceeded at least one evaluation limit for the {aircraft_display}."
            )
        else:
            report_parts.append(
                f"The landing remained within normal limits for the {aircraft_display}."
            )
        report_parts.append('')
        report_parts.append('Maintenance Action')

        status = str(getattr(result, 'status', 'NORMAL'))
        if status in {'ENGINE_INSPECTION', 'HARD_LANDING_ENGINE'}:
            report_parts.append('Phase III required.')
            report_parts.append('Phase II also required prior to release.')
        elif status == 'HARD_LANDING_HIGH':
            report_parts.append('Phase II required.')
            report_parts.append('Phase III as per engineering assessment.')
        elif status == 'HARD_LANDING_LOW':
            report_parts.append('Phase I required.')
            report_parts.append('Phase II or III not required unless additional findings are identified.')
        else:
            report_parts.append('Phase II or III not required.')
            report_parts.append('Phase I can be considered fulfilled, with no findings.')

        return "\n".join(report_parts)
    
    def _show_ai_dialog(self, report_text):
        """Show AI analysis dialog"""
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
            from PyQt6.QtGui import QFont
            
            dialog = QDialog(self)
            dialog.setWindowTitle("🤖 AI Assistant - Intelligent Analysis")
            dialog.resize(1100, 850)  # Aumentado para reduzir scroll
            
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(15)
            
            # Report text
            report_display = QTextEdit()
            report_display.setReadOnly(True)
            report_display.setPlainText(report_text)
            
            # Set monospace font for better readability
            font = QFont("Consolas", 11)
            if not font.exactMatch():
                font = QFont("Courier New", 11)
            report_display.setFont(font)
            
            report_display.setStyleSheet("""
                QTextEdit {
                    background-color: #FAFAFA;
                    border: 2px solid #2196F3;
                    border-radius: 10px;
                    padding: 20px;
                    line-height: 1.6;
                }
            """)
            layout.addWidget(report_display)
            
            # Buttons
            button_layout = QHBoxLayout()
            button_layout.setSpacing(10)
            
            # Copy to Clipboard button
            copy_button = QPushButton("📋 Copy to Clipboard")
            copy_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #66BB6A, stop:0.5 #4CAF50, stop:1 #388E3C);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 12px 24px;
                    font-weight: bold;
                    font-size: 14px;
                    min-height: 45px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #81C784, stop:0.5 #66BB6A, stop:1 #4CAF50);
                }
                QPushButton:pressed {
                    background: #388E3C;
                }
            """)
            copy_button.clicked.connect(lambda: self._copy_to_clipboard(report_text))
            button_layout.addWidget(copy_button)
            
            # Close button
            close_button = QPushButton("✖ Close")
            close_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2196F3, stop:0.5 #1976D2, stop:1 #0D47A1);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 12px 24px;
                    font-weight: bold;
                    font-size: 14px;
                    min-height: 45px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #42A5F5, stop:0.5 #2196F3, stop:1 #1976D2);
                }
                QPushButton:pressed {
                    background: #0D47A1;
                }
            """)
            close_button.clicked.connect(dialog.accept)
            button_layout.addWidget(close_button)
            
            layout.addLayout(button_layout)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "AI Assistant Error",
                f"Error generating AI analysis:\n{str(e)}"
            )
    
    def _show_graphs_dialog(self, graph_files):
        """Exibe gráficos em uma janela do aplicativo"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt
        
        dialog = QDialog(self)
        event_name = self.current_event_name or "Analysis"
        dialog.setWindowTitle(f"{event_name} - Graphs")
        dialog.resize(1200, 900)
        
        layout = QVBoxLayout(dialog)
        
        # Scroll area para os gráficos
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Widget container para gráficos
        container = QWidget()
        container_layout = QVBoxLayout(container)
        
        # Adicionar cada gráfico
        for i, graph_file in enumerate(graph_files, 1):
            # Título do gráfico
            title = QLabel(f"Graph {i}: {graph_file.name}")
            title.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
            container_layout.addWidget(title)
            
            # Imagem do gráfico
            pixmap = QPixmap(str(graph_file))
            if not pixmap.isNull():
                label = QLabel()
                # Redimensionar para caber na janela mantendo proporção
                scaled_pixmap = pixmap.scaled(
                    1150, 600,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                label.setPixmap(scaled_pixmap)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                container_layout.addWidget(label)
            
            # Separador
            if i < len(graph_files):
                separator = QLabel("-" * 150)
                separator.setStyleSheet("color: #CCCCCC; padding: 5px;")
                container_layout.addWidget(separator)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # Botões
        button_layout = QHBoxLayout()
        
        # Botão para abrir pasta
        open_folder_btn = QPushButton("📁 Open Folder")
        open_folder_btn.clicked.connect(lambda: self._open_graphs_folder(graph_files[0].parent))
        button_layout.addWidget(open_folder_btn)
        
        # Botão para imprimir
        print_btn = QPushButton("🖨️ Print")
        print_btn.clicked.connect(lambda: self._print_graphs(graph_files))
        button_layout.addWidget(print_btn)
        
        button_layout.addStretch()
        
        # Botão fechar
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _open_graphs_folder(self, folder_path):
        """Open the graphs folder in Explorer."""
        import os
        try:
            os.startfile(folder_path)
        except Exception as e:
            logger.error(f"Erro ao abrir pasta: {e}")
            QMessageBox.warning(self, "Error", f"Unable to open the folder:\n{e}")
    
    def _print_graphs(self, graph_files):
        """Print graphs."""
        from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
        from PyQt6.QtGui import QPainter, QPixmap
        
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            painter = QPainter(printer)
            
            for i, graph_file in enumerate(graph_files):
                if i > 0:
                    printer.newPage()
                
                pixmap = QPixmap(str(graph_file))
                if not pixmap.isNull():
                    # Escalar para caber na página
                    rect = painter.viewport()
                    scaled = pixmap.scaled(
                        rect.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    painter.drawPixmap(0, 0, scaled)
            
            painter.end()
            QMessageBox.information(self, "Success", "Graphs sent to the printer!")


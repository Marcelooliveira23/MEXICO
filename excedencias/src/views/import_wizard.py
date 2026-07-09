"""
Import Wizard - Multi-step guided data import with column validation
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, 
    QHeaderView, QGroupBox, QScrollArea, QWidget, QMessageBox,
    QProgressBar, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon
from PyQt6.QtCore import QSize

from utils import AppConfig, AppColors
from utils.logger import logger
from services import CSVParser
from services.data_pipeline import DataPipeline


class FileSelectionPage(QWizardPage):
    """Página 1: Seleção de arquivo"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Seleção de Arquivo")
        self.setSubTitle("Selecione o arquivo CSV ou TXT para importar")
        
        layout = QVBoxLayout()
        
        # Info text
        info = QLabel("Clique em 'Procurar' para selecionar um arquivo de dados:")
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {AppColors.TEXT}; font-size: 12px;")
        layout.addWidget(info)
        
        layout.addSpacing(20)
        
        # File selection area
        file_layout = QHBoxLayout()
        self.file_label = QLabel("Nenhum arquivo selecionado")
        self.file_label.setStyleSheet(f"color: {AppColors.SECONDARY}; padding: 10px; font-weight: bold;")
        file_layout.addWidget(self.file_label)
        
        browse_btn = QPushButton("Procurar...")
        browse_btn.setMaximumWidth(150)
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {AppColors.PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {AppColors.SECONDARY};
            }}
        """)
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)
        
        layout.addSpacing(20)
        
        # File info display
        self.info_text = QLabel("")
        self.info_text.setWordWrap(True)
        self.info_text.setStyleSheet(f"color: {AppColors.TEXT}; font-size: 11px; background-color: {AppColors.BG_SECONDARY}; padding: 10px; border-radius: 4px;")
        layout.addWidget(self.info_text)
        
        layout.addStretch()
        self.setLayout(layout)
        self.file_path = None
    
    def browse_file(self):
        """Browse for file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Arquivo de Dados",
            "",
            "Arquivos de Dados (*.csv *.txt);;Todos os Arquivos (*.*)"
        )
        
        if file_path:
            self.file_path = Path(file_path)
            self.file_label.setText(f"✓ {self.file_path.name}")
            self.file_label.setStyleSheet(f"color: {AppColors.SUCCESS}; padding: 10px; font-weight: bold;")
            
            # Show file info
            try:
                file_info = CSVParser.get_file_info(self.file_path)
                self.info_text.setText(
                    f"📊 Informações do arquivo:\n\n"
                    f"• Nome: {self.file_path.name}\n"
                    f"• Linhas: {file_info['rows']}\n"
                    f"• Colunas: {file_info['columns']}\n"
                    f"• Tamanho: {file_info['size_bytes'] / 1024:.1f} KB\n"
                    f"• Encoding: {file_info['encoding']}\n\n"
                    f"Colunas encontradas:\n"
                    f"{', '.join(file_info['column_names'][:5])}"
                    f"{'...' if len(file_info['column_names']) > 5 else ''}"
                )
            except Exception as e:
                self.info_text.setText(f"⚠️ Erro ao ler arquivo: {str(e)}")
            
            self.completeChanged.emit()
    
    def isComplete(self):
        """Check if file is selected"""
        return self.file_path is not None


class ColumnPreviewPage(QWizardPage):
    """Página 2: Preview de colunas com indicadores de mapeamento"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Preview de Colunas")
        self.setSubTitle("Verifique o mapeamento das colunas detectadas")
        
        layout = QVBoxLayout()
        
        # Info
        info = QLabel("As colunas abaixo foram detectadas no seu arquivo.\n"
                      "🟢 = Coluna reconhecida | 🟡 = Possível alias | 🔴 = Desconhecida")
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {AppColors.TEXT}; font-size: 11px;")
        layout.addWidget(info)
        
        layout.addSpacing(10)
        
        # Columns table
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        table_widget = QWidget()
        table_layout = QVBoxLayout()
        table_layout.setSpacing(5)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        self.column_items = []
        self.columns_table = QTableWidget()
        self.columns_table.setColumnCount(3)
        self.columns_table.setHorizontalHeaderLabels(["Status", "Coluna Original", "Mapeamento"])
        self.columns_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.columns_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.columns_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.columns_table.setMaximumHeight(400)
        table_layout.addWidget(self.columns_table)
        table_layout.addStretch()
        
        table_widget.setLayout(table_layout)
        scroll.setWidget(table_widget)
        layout.addWidget(scroll)
        
        layout.addStretch()
        self.setLayout(layout)
        self.mapper = None
    
    def initializePage(self):
        """Initialize when page is shown"""
        # Get file path from previous page
        file_path = self.wizard().page(0).file_path
        if file_path:
            try:
                # Load and map columns
                file_info = CSVParser.get_file_info(file_path)
                self.columns_table.setRowCount(len(file_info['column_names']))
                
                for row, col_name in enumerate(file_info['column_names']):
                    # Status icon
                    status_item = QTableWidgetItem()
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    status_item.setFont(QFont("Arial", 14))
                    
                    # Try to detect mapping using DataPipeline mapper
                    mapped = self._detect_mapping(col_name)
                    if mapped['status'] == 'found':
                        status_item.setText("🟢")
                        mapping_text = f"→ {mapped['standard_name']}"
                        status_item.setBackground(QColor(200, 255, 200))
                    elif mapped['status'] == 'possible':
                        status_item.setText("🟡")
                        mapping_text = f"→ {mapped['standard_name']} (possível alias)"
                        status_item.setBackground(QColor(255, 255, 200))
                    else:
                        status_item.setText("🔴")
                        mapping_text = "Desconhecida"
                        status_item.setBackground(QColor(255, 200, 200))
                    
                    self.columns_table.setItem(row, 0, status_item)
                    self.columns_table.setItem(row, 1, QTableWidgetItem(col_name))
                    self.columns_table.setItem(row, 2, QTableWidgetItem(mapping_text))
            
            except Exception as e:
                logger.error(f"Error in column preview: {str(e)}")
    
    def _detect_mapping(self, column_name: str) -> dict:
        """Detect if column is recognized"""
        from services import CSVColumnMapper
        
        mapper = CSVColumnMapper()
        col_lower = column_name.lower().strip()
        
        # Check for exact match
        for standard_name, aliases in mapper.standard_columns.items():
            if col_lower in [a.lower() for a in aliases]:
                return {'status': 'found', 'standard_name': standard_name}
        
        # Check for partial match (possible alias)
        for standard_name, aliases in mapper.standard_columns.items():
            if any(alias.lower() in col_lower or col_lower in alias.lower() 
                   for alias in aliases):
                return {'status': 'possible', 'standard_name': standard_name}
        
        return {'status': 'unknown', 'standard_name': column_name}


class RequiredColumnsPage(QWizardPage):
    """Página 3: Verificação de colunas obrigatórias"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Validação de Colunas Obrigatórias")
        self.setSubTitle("Verifique se as colunas necessárias para o evento foram encontradas")
        
        layout = QVBoxLayout()
        
        # Info
        info = QLabel("Seu evento requer as seguintes colunas. "
                      "Todas as colunas necessárias foram encontradas?")
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {AppColors.TEXT}; font-size: 11px;")
        layout.addWidget(info)
        
        layout.addSpacing(15)
        
        # Event info
        self.event_label = QLabel("")
        self.event_label.setStyleSheet(f"color: {AppColors.PRIMARY}; font-weight: bold; font-size: 13px;")
        layout.addWidget(self.event_label)
        
        layout.addSpacing(10)
        
        # Required columns display
        self.required_text = QLabel("")
        self.required_text.setWordWrap(True)
        self.required_text.setStyleSheet(f"""
            background-color: {AppColors.BG_SECONDARY};
            padding: 15px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 11px;
        """)
        layout.addWidget(self.required_text)
        
        layout.addSpacing(15)
        
        # Status summary
        self.status_text = QLabel("")
        self.status_text.setWordWrap(True)
        layout.addWidget(self.status_text)
        
        layout.addSpacing(10)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {AppColors.BORDER};
                border-radius: 4px;
                text-align: center;
                background-color: {AppColors.BG_SECONDARY};
            }}
            QProgressBar::chunk {{
                background-color: {AppColors.SUCCESS};
            }}
        """)
        layout.addWidget(self.progress)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Column requirements mapping
        self.required_columns_map = {
            "hard_landing": [["vertical_acceleration", "VERTICAL_ACCELERATION", "nz", "g_load"]],
            "gear_overspeed": [["airspeed", "IAS"], ["gear_position", "LG_POSITION"]],
            "temp_envelope": [["temperature", "TAT", "EGT"]],
            "max_speed": [["airspeed", "IAS", "MACH"]],
            "flap_overspeed": [["airspeed", "IAS"], ["flap_position", "FLAP_POSITION"]],
            "overweight_landing": [["gross_weight"]],
            "turbulence": [["vertical_acceleration", "g_load", "nz"]],
            "over_g": [["vertical_acceleration", "g_load", "nz"]],
        }
        self.all_columns_found = True
    
    def initializePage(self):
        """Initialize when page is shown"""
        import pandas as pd
        
        file_path = self.wizard().page(0).file_path
        event_id = self.wizard().event_id
        event_name = self.wizard().event_name
        
        self.event_label.setText(f"Evento: {event_name} (ID: {event_id})")
        
        try:
            # Load and validate
            pipeline = DataPipeline()
            result = pipeline.process_file(file_path)
            
            if result.errors:
                self.status_text.setText(f"❌ Erros no pipeline: {'; '.join(result.errors)}")
                self.all_columns_found = False
                self.progress.setValue(0)
                return
            
            df = result.df
            required_groups = self.required_columns_map.get(event_id, [])
            
            if not required_groups:
                self.required_text.setText("⚠️ Tipo de evento não reconhecido")
                self.all_columns_found = False
                return
            
            # Check each required group
            found_count = 0
            required_text_lines = []
            
            for group_idx, group in enumerate(required_groups, 1):
                found = False
                found_col = None
                for col_option in group:
                    if col_option in df.columns:
                        found = True
                        found_col = col_option
                        found_count += 1
                        break
                
                status = "🟢" if found else "🔴"
                cols_str = " ou ".join(group)
                found_str = f"✓ ({found_col})" if found else "✗"
                required_text_lines.append(f"{status} {cols_str} {found_str}")
            
            self.required_text.setText("\n".join(required_text_lines))
            
            # Update progress
            total = len(required_groups)
            percentage = int((found_count / total * 100)) if total > 0 else 0
            self.progress.setValue(percentage)
            
            if found_count == total:
                self.status_text.setText(f"✅ Todas as {total} colunas obrigatórias foram encontradas!")
                self.status_text.setStyleSheet(f"color: {AppColors.SUCCESS}; font-weight: bold;")
                self.all_columns_found = True
            else:
                missing = total - found_count
                self.status_text.setText(
                    f"⚠️ {missing} de {total} grupos de colunas faltando.\n"
                    f"Você pode continuar, mas a análise pode não funcionar corretamente."
                )
                self.status_text.setStyleSheet(f"color: {AppColors.WARNING}; font-weight: bold;")
                self.all_columns_found = False
        
        except Exception as e:
            self.status_text.setText(f"❌ Erro na validação: {str(e)}")
            self.all_columns_found = False


class ConfirmationPage(QWizardPage):
    """Página 4: Confirmação e resumo"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Confirmação")
        self.setSubTitle("Revise as informações antes de importar")
        
        layout = QVBoxLayout()
        
        # Summary text
        self.summary_text = QLabel("")
        self.summary_text.setWordWrap(True)
        self.summary_text.setStyleSheet(f"""
            background-color: {AppColors.BG_SECONDARY};
            padding: 15px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 11px;
        """)
        layout.addWidget(self.summary_text)
        
        layout.addSpacing(20)
        
        # Ready indicator
        self.ready_label = QLabel("")
        self.ready_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ready_label.setStyleSheet(f"font-size: 13px; font-weight: bold;")
        layout.addWidget(self.ready_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def initializePage(self):
        """Initialize when page is shown"""
        file_path = self.wizard().page(0).file_path
        event_id = self.wizard().event_id
        event_name = self.wizard().event_name
        
        try:
            file_info = CSVParser.get_file_info(file_path)
            
            summary = f"""
📁 ARQUIVO
   Nome: {file_path.name}
   Linhas: {file_info['rows']}
   Colunas: {file_info['columns']}
   Tamanho: {file_info['size_bytes'] / 1024:.1f} KB

📋 EVENTO
   Nome: {event_name}
   ID: {event_id}

✓ Todos os passos foram concluídos com sucesso!
   Clique em "Terminar" para importar os dados.
            """
            
            self.summary_text.setText(summary.strip())
            self.ready_label.setText("✅ Pronto para importar!")
            self.ready_label.setStyleSheet(f"color: {AppColors.SUCCESS}; font-size: 13px; font-weight: bold;")
            
        except Exception as e:
            self.summary_text.setText(f"❌ Erro: {str(e)}")
            self.ready_label.setText("Erro na preparação")
            self.ready_label.setStyleSheet(f"color: {AppColors.ERROR}; font-size: 13px; font-weight: bold;")


class ImportWizard(QWizard):
    """Wizard for guided data import with validation"""
    
    import_completed = pyqtSignal(Path)  # Signal with file path when import is complete
    
    def __init__(self, aircraft_id: str, event_id: str, event_name: str, parent=None):
        super().__init__(parent)
        
        self.aircraft_id = aircraft_id
        self.event_id = event_id
        self.event_name = event_name
        self.imported_file_path = None
        
        self.setWindowTitle("Import Data Wizard - Guided Data Import")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        self.setStyleSheet(f"""
            QWizard {{
                background-color: {AppColors.BG};
                color: {AppColors.TEXT};
            }}
            QWizard QLabel {{
                color: {AppColors.TEXT};
            }}
            QPushButton {{
                min-height: 32px;
                border-radius: 4px;
                font-weight: bold;
            }}
        """)
        
        # Add pages
        self.page1 = FileSelectionPage()
        self.page2 = ColumnPreviewPage()
        self.page3 = RequiredColumnsPage()
        self.page4 = ConfirmationPage()
        
        self.addPage(self.page1)
        self.addPage(self.page2)
        self.addPage(self.page3)
        self.addPage(self.page4)
        
        # Connect finish button
        self.finished.connect(self.on_wizard_finished)
    
    def on_wizard_finished(self, result):
        """Handle wizard completion"""
        if result == QWizard.DialogCode.Accepted:
            file_path = self.page1.file_path
            if file_path:
                self.imported_file_path = file_path
                self.import_completed.emit(file_path)

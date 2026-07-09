"""
Graphics Viewer
Displays technical diagrams and charts from PDFs
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont
from pathlib import Path
from utils import AppColors
from utils.logger import logger


class GraphicsView(QWidget):
    """Graphics viewer widget"""
    
    back_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_aircraft = None
        self.current_event = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header_layout = QHBoxLayout()
        
        back_button = QPushButton("← Back")
        back_button.setMaximumWidth(180)
        back_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2196F3, stop:0.5 #1976D2, stop:1 #0D47A1);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 22px;
                font-weight: bold;
                border-bottom: 3px solid rgba(0, 0, 0, 0.2);
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #42A5F5, stop:0.5 #2196F3, stop:1 #1976D2);
            }}
        """)
        back_button.clicked.connect(self.back_clicked.emit)
        header_layout.addWidget(back_button)
        
        self.title_label = QLabel("📊 Technical Graphics")
        self.title_label.setFont(QFont("Segoe UI", 42, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {AppColors.PRIMARY};")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.title_label, 1)
        
        header_layout.addSpacing(120)
        
        layout.addLayout(header_layout)
        
        # Context label
        self.context_label = QLabel()
        self.context_label.setFont(QFont("Segoe UI", 20))
        self.context_label.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY}; padding: 5px;")
        self.context_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.context_label)
        
        # Scroll area for graphics
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 2px solid {AppColors.BORDER};
                border-radius: 8px;
                background-color: white;
            }}
        """)
        
        # Graphics container
        self.graphics_container = QWidget()
        self.graphics_layout = QGridLayout(self.graphics_container)
        self.graphics_layout.setSpacing(20)
        
        scroll.setWidget(self.graphics_container)
        layout.addWidget(scroll)
    
    def set_context(self, aircraft_id: str, aircraft_name: str, event_id: str, event_name: str):
        """Set viewing context"""
        self.current_aircraft = aircraft_id
        self.current_event = event_id
        self.context_label.setText(f"{aircraft_name} - {event_name}")
        self.load_graphics()
    
    def load_graphics(self):
        """Load graphics for current context"""
        # Clear existing graphics
        while self.graphics_layout.count():
            child = self.graphics_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Load graphics from assets
        graphics_dir = Path("assets/pdf_graphics") / self.current_aircraft.lower()
        
        if not graphics_dir.exists():
            # Show no graphics message
            no_graphics_label = QLabel("No graphics available for this selection.\n\nGraphics will be extracted from PDFs automatically.")
            no_graphics_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_graphics_label.setStyleSheet(f"""
                color: {AppColors.TEXT_SECONDARY};
                font-size: 14px;
                padding: 50px;
            """)
            self.graphics_layout.addWidget(no_graphics_label, 0, 0, 1, 3)
            return
        
        # Find all PNG images
        image_files = list(graphics_dir.glob("*.png"))
        
        if not image_files:
            # Show no graphics message
            no_graphics_label = QLabel("No graphics extracted yet.\n\nRun graphics extraction to populate this view.")
            no_graphics_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_graphics_label.setStyleSheet(f"""
                color: {AppColors.TEXT_SECONDARY};
                font-size: 14px;
                padding: 50px;
            """)
            self.graphics_layout.addWidget(no_graphics_label, 0, 0, 1, 3)
            return
        
        # Display graphics in grid (3 columns)
        row = 0
        col = 0
        
        for img_file in sorted(image_files):
            try:
                # Create card for image
                card = self.create_image_card(img_file)
                self.graphics_layout.addWidget(card, row, col)
                
                col += 1
                if col >= 3:
                    col = 0
                    row += 1
                    
            except Exception as e:
                logger.error(f"Error loading graphic {img_file}: {e}")
        
        logger.info(f"Loaded {len(image_files)} graphics for {self.current_aircraft}")
    
    def create_image_card(self, image_path: Path) -> QWidget:
        """Create a card widget for an image"""
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: white;
                border: 2px solid {AppColors.BORDER};
                border-radius: 8px;
                padding: 10px;
            }}
            QWidget:hover {{
                border: 2px solid {AppColors.PRIMARY};
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        
        # Image
        pixmap = QPixmap(str(image_path))
        if not pixmap.isNull():
            # Scale image to fit
            scaled_pixmap = pixmap.scaled(
                300, 300,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            image_label = QLabel()
            image_label.setPixmap(scaled_pixmap)
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(image_label)
        
        # Filename
        name_label = QLabel(image_path.name)
        name_label.setStyleSheet(f"""
            color: {AppColors.TEXT_SECONDARY};
            font-size: 10px;
        """)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        # View button
        view_button = QPushButton("🔍 View Full Size")
        view_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2196F3, stop:0.5 #1976D2, stop:1 #0D47A1);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
                border-bottom: 2px solid rgba(0, 0, 0, 0.2);
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #42A5F5, stop:0.5 #2196F3, stop:1 #1976D2);
            }}
        """)
        view_button.clicked.connect(lambda: self.view_full_size(image_path))
        layout.addWidget(view_button)
        
        return card
    
    def view_full_size(self, image_path: Path):
        """View image in full size dialog"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"📊 {image_path.name}")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Scroll area for large image
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        image_label = QLabel()
        pixmap = QPixmap(str(image_path))
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        scroll.setWidget(image_label)
        layout.addWidget(scroll)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.exec()

"""
Aircraft Family Selection Page
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from utils import AppConfig, AircraftColors
from views.components import AircraftButton


class AircraftSelectionView(QWidget):
    """Aircraft family selection screen"""
    
    aircraft_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(30)
        layout.setContentsMargins(40, 40, 40, 40)
        
        title_font_size = 48
        subtitle_font_size = 24

        # Title
        title = QLabel("Select Aircraft Family")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(title_font_size)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet("color: #2E5266; padding: 20px;")
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Choose the aircraft family to begin analysis")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(subtitle_font_size)
        subtitle.setFont(subtitle_font)
        subtitle.setStyleSheet("color: #6C757D; padding-bottom: 20px;")
        layout.addWidget(subtitle)
        
        # Buttons grid
        buttons_layout = QGridLayout()
        buttons_layout.setSpacing(20)
        
        # Create buttons for each family
        families = AppConfig.AIRCRAFT_FAMILIES
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        
        short_labels = {
            "e145": "ERJ145",
            "e170": "EMB170",
            "e1": "EMB190",
            "e2": "E2",
        }

        for family, pos in zip(families, positions):
            display_name = short_labels.get(family.id, family.display_name)
            btn = AircraftButton(
                aircraft_id=family.id,
                display_name=display_name,
                color=family.color
            )
            btn.clicked_with_id.connect(self.on_aircraft_selected)
            buttons_layout.addWidget(btn, pos[0], pos[1], Qt.AlignmentFlag.AlignCenter)
        
        layout.addLayout(buttons_layout)
        layout.addStretch()
        
        # Footer
        footer = QLabel(f"Aircraft Inspection Analysis System v{AppConfig.APP_VERSION}")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #ADB5BD; font-size: 10px; padding: 10px;")
        layout.addWidget(footer)
    
    def on_aircraft_selected(self, aircraft_id: str):
        """Emit signal when aircraft is selected"""
        self.aircraft_selected.emit(aircraft_id)

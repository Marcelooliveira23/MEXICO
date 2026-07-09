"""
Event Category Selection Page
"""

from functools import partial

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGridLayout
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from utils import AppConfig


class EventSelectionView(QWidget):
    """Event category selection screen"""
    
    event_selected = pyqtSignal(str, str)  # event_id, aircraft_id
    back_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_aircraft_id = None
        self.current_aircraft_name = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Header with back button
        header_layout = QHBoxLayout()
        
        back_btn = QPushButton("← Back")
        back_btn.setMaximumWidth(180)
        back_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2196F3, stop:0.5 #1976D2, stop:1 #0D47A1);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 22px;
                font-weight: bold;
                border-bottom: 3px solid rgba(0, 0, 0, 0.2);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #42A5F5, stop:0.5 #2196F3, stop:1 #1976D2);
            }
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(back_btn)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Title
        self.title = QLabel()
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(48)
        font.setBold(True)
        self.title.setFont(font)
        self.title.setStyleSheet("color: #1976D2; padding: 20px;")
        layout.addWidget(self.title)
        
        # Subtitle
        subtitle = QLabel("Select the event type for analysis")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(24)
        subtitle.setFont(subtitle_font)
        subtitle.setStyleSheet("color: #6C757D; padding-bottom: 10px;")
        layout.addWidget(subtitle)
        
        # Grid layout for event buttons (3x3)
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(20)
        grid_layout.setContentsMargins(20, 20, 20, 20)
        
        # Event buttons configuration (semantic IDs) - simplified titles only
        events = [
            ("hard_landing", "Hard Landing"),
            ("gear_overspeed", "LG overspeed"),
            ("temp_envelope", "TEMP Envelope"),
            ("max_speed", "VMO/MMO"),
            ("flap_overspeed", "Flap Overspeed"),
            ("overweight_landing", "Overweight Landing"),
            ("turbulence", "Turbulence")
        ]
        
        # Create buttons in 3x3 grid
        for idx, (event_id, event_name) in enumerate(events):
            row = idx // 3
            col = idx % 3
            
            btn = QPushButton(event_name)
            btn.setFixedSize(300, 90)
            btn.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
            
            # Different blue gradient for each button
            if idx == 0:  # Hard Landing
                gradient = "stop:0 #2196F3, stop:0.5 #1E88E5, stop:1 #1976D2"
            elif idx == 1:  # Gear Overspeed
                gradient = "stop:0 #1E88E5, stop:0.5 #1976D2, stop:1 #1565C0"
            elif idx == 2:  # Temperature
                gradient = "stop:0 #42A5F5, stop:0.5 #2196F3, stop:1 #1E88E5"
            elif idx == 3:  # Max Speed
                gradient = "stop:0 #1976D2, stop:0.5 #1565C0, stop:1 #0D47A1"
            elif idx == 4:  # Flap Overspeed
                gradient = "stop:0 #2196F3, stop:0.5 #1976D2, stop:1 #1565C0"
            elif idx == 5:  # Overweight
                gradient = "stop:0 #1565C0, stop:0.5 #0D47A1, stop:1 #01579B"
            else:  # Turbulence
                gradient = "stop:0 #42A5F5, stop:0.5 #1976D2, stop:1 #0D47A1"
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        {gradient});
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 25px;
                    font-size: 22px;
                    font-weight: bold;
                    letter-spacing: 2px;
                    border-bottom: 3px solid rgba(0, 0, 0, 0.3);
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #42A5F5, stop:0.5 #2196F3, stop:1 #1976D2);
                    border-bottom: 4px solid rgba(0, 0, 0, 0.4);
                }}
                QPushButton:pressed {{
                    padding-top: 28px;
                    padding-bottom: 22px;
                    border-top: 3px solid rgba(0, 0, 0, 0.3);
                    border-bottom: 1px solid rgba(0, 0, 0, 0.2);
                }}
            """)
            
            btn.clicked.connect(partial(self.on_event_selected, event_id))
            grid_layout.addWidget(btn, row, col)
        
        layout.addWidget(grid_widget, 1)
    
    def set_aircraft(self, aircraft_id: str):
        """Set current aircraft"""
        self.current_aircraft_id = aircraft_id
        aircraft = AppConfig.get_aircraft_by_id(aircraft_id)
        if aircraft:
            self.current_aircraft_name = aircraft.display_name
            self.title.setText(f"Analysis - {aircraft.display_name}")
    
    def on_event_selected(self, event_id: str):
        """Emit signal when event is selected"""
        if self.current_aircraft_id:
            self.event_selected.emit(event_id, self.current_aircraft_id)

"""
Language Selector Widget
Widget PyQt6 para seleção de idioma
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox, QLabel
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont

from utils.i18n import get_i18n
from utils.logger import logger


class LanguageSelector(QWidget):
    """
    Widget para seleção de idioma
    Emite sinal quando idioma é alterado
    """
    
    # Sinal emitido quando idioma muda
    language_changed = pyqtSignal(str)  # Emite código do idioma (pt_BR, en_US, etc)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.i18n = get_i18n()
        self._init_ui()
        
        logger.info("LanguageSelector initialized")
    
    def _init_ui(self):
        """Inicializar interface"""
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Label
        label = QLabel("🌍")
        label_font = QFont()
        label_font.setPointSize(12)
        label.setFont(label_font)
        layout.addWidget(label)
        
        # ComboBox
        self.combo = QComboBox()
        self.combo.setMinimumWidth(200)
        
        # Adicionar idiomas
        languages = self.i18n.get_available_languages()
        for lang in languages:
            self.combo.addItem(f"{lang.flag} {lang.name}", lang.code)
        
        # Selecionar idioma atual
        current_lang = self.i18n.get_language()
        for i in range(self.combo.count()):
            if self.combo.itemData(i) == current_lang:
                self.combo.setCurrentIndex(i)
                break
        
        # Conectar sinal
        self.combo.currentIndexChanged.connect(self._on_language_changed)
        
        layout.addWidget(self.combo)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def _on_language_changed(self, index: int):
        """Handler para mudança de idioma"""
        lang_code = self.combo.itemData(index)
        
        if lang_code:
            # Atualizar idioma no i18n
            self.i18n.set_language(lang_code)
            
            # Emitir sinal
            self.language_changed.emit(lang_code)
            
            logger.info(f"Language changed to: {lang_code}")
    
    def get_current_language(self) -> str:
        """Obter idioma atual"""
        return self.combo.currentData()
    
    def set_language(self, lang_code: str):
        """
        Definir idioma programaticamente
        
        Args:
            lang_code: Código do idioma
        """
        for i in range(self.combo.count()):
            if self.combo.itemData(i) == lang_code:
                self.combo.setCurrentIndex(i)
                break

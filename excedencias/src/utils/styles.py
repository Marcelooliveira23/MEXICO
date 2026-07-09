"""
Estilos Qt Style Sheets (QSS) da aplicação
"""

from .colors import AppColors


def get_app_stylesheet() -> str:
    """
    Retorna o stylesheet principal da aplicação
    """
    return f"""
    /* Estilo Global */
    QMainWindow {{
        background-color: #FFFFFF;
    }}
    
    QWidget {{
        font-family: 'Segoe UI', Arial, sans-serif;
        color: {AppColors.TEXT_PRIMARY};
        background-color: #FFFFFF;
    }}
    
    /* Botões Principais */
    QPushButton {{
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 {AppColors.PRIMARY},
                                          stop:0.5 {AppColors.PRIMARY},
                                          stop:1 {AppColors.SECONDARY});
        color: {AppColors.TEXT_ON_PRIMARY};
        border: 2px solid rgba(0, 0, 0, 0.1);
        border-bottom: 4px solid rgba(0, 0, 0, 0.2);
        border-radius: 8px;
        padding: 12px 24px;
        font-size: 14px;
        font-weight: bold;
        min-height: 40px;
    }}
    
    QPushButton:hover {{
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 {AppColors.SECONDARY},
                                          stop:0.5 {AppColors.SECONDARY},
                                          stop:1 {AppColors.PRIMARY});
        border: 2px solid rgba(255, 255, 255, 0.3);
    }}
    
    QPushButton:pressed {{
        background-color: {AppColors.PRIMARY};
        padding-top: 14px;
        padding-bottom: 10px;
    }}
    
    QPushButton:disabled {{
        background-color: {AppColors.BORDER};
        color: {AppColors.TEXT_DISABLED};
    }}
    
    /* Botões Secundários */
    QPushButton[buttonStyle="secondary"] {{
        background-color: {AppColors.SURFACE};
        color: {AppColors.PRIMARY};
        border: 2px solid {AppColors.PRIMARY};
    }}
    
    QPushButton[buttonStyle="secondary"]:hover {{
        background-color: {AppColors.PRIMARY};
        color: {AppColors.TEXT_ON_PRIMARY};
    }}
    
    /* Cards */
    QFrame[frameStyle="card"] {{
        background-color: {AppColors.CARD};
        border: 1px solid {AppColors.BORDER_LIGHT};
        border-radius: 12px;
        padding: 16px;
    }}
    
    /* Labels de Título */
    QLabel[labelStyle="title"] {{
        font-size: 28px;
        font-weight: bold;
        color: {AppColors.PRIMARY};
        padding: 16px 0;
    }}
    
    QLabel[labelStyle="subtitle"] {{
        font-size: 18px;
        font-weight: 600;
        color: {AppColors.SECONDARY};
        padding: 8px 0;
    }}
    
    /* Tabelas */
    QTableWidget {{
        background-color: {AppColors.SURFACE};
        border: 1px solid {AppColors.BORDER};
        border-radius: 8px;
        gridline-color: {AppColors.BORDER_LIGHT};
    }}
    
    QTableWidget::item {{
        padding: 8px;
    }}
    
    QTableWidget::item:selected {{
        background-color: {AppColors.ACCENT};
        color: {AppColors.TEXT_PRIMARY};
    }}
    
    QHeaderView::section {{
        background-color: {AppColors.PRIMARY};
        color: {AppColors.TEXT_ON_PRIMARY};
        padding: 8px;
        border: none;
        font-weight: bold;
    }}
    
    /* Inputs */
    QLineEdit, QTextEdit {{
        background-color: {AppColors.SURFACE};
        border: 2px solid {AppColors.BORDER};
        border-radius: 6px;
        padding: 8px 12px;
        min-height: 36px;
    }}
    
    QLineEdit:focus, QTextEdit:focus {{
        border-color: {AppColors.PRIMARY};
    }}
    
    /* ComboBox */
    QComboBox {{
        background-color: {AppColors.SURFACE};
        border: 2px solid {AppColors.BORDER};
        border-radius: 6px;
        padding: 8px 12px;
        min-height: 36px;
    }}
    
    QComboBox:hover {{
        border-color: {AppColors.SECONDARY};
    }}
    
    QComboBox::drop-down {{
        border: none;
        padding-right: 8px;
    }}
    
    /* Diálogos */
    QDialog {{
        background-color: {AppColors.SURFACE};
    }}
    
    /* Barra de Menu */
    QMenuBar {{
        background-color: {AppColors.SURFACE};
        border-bottom: 1px solid {AppColors.BORDER};
    }}
    
    QMenuBar::item:selected {{
        background-color: {AppColors.ACCENT};
    }}
    
    QMenu {{
        background-color: {AppColors.SURFACE};
        border: 1px solid {AppColors.BORDER};
    }}
    
    QMenu::item:selected {{
        background-color: {AppColors.ACCENT};
    }}
    
    /* Scrollbar */
    QScrollBar:vertical {{
        background-color: {AppColors.BACKGROUND};
        width: 12px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {AppColors.BORDER};
        border-radius: 6px;
        min-height: 30px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {AppColors.SECONDARY};
    }}
    
    /* ProgressBar */
    QProgressBar {{
        border: 2px solid {AppColors.BORDER};
        border-radius: 6px;
        text-align: center;
        background-color: {AppColors.SURFACE};
    }}
    
    QProgressBar::chunk {{
        background-color: {AppColors.SUCCESS};
        border-radius: 4px;
    }}
    """


def get_button_style(variant: str = "primary") -> str:
    """
    Retorna estilo para botão específico
    
    Args:
        variant: "primary", "secondary", "success", "warning", "error"
    """
    colors = {
        "primary": AppColors.PRIMARY,
        "secondary": AppColors.SECONDARY,
        "success": AppColors.SUCCESS,
        "warning": AppColors.WARNING,
        "error": AppColors.ERROR,
    }
    
    color = colors.get(variant, AppColors.PRIMARY)
    
    return f"""
    QPushButton {{
        background-color: {color};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: bold;
        min-height: 40px;
    }}
    
    QPushButton:hover {{
        background-color: {color};
        border: 2px solid white;
    }}
    """

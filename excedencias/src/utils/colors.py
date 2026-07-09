"""
Cores do sistema
"""


class AppColors:
    """Paleta de cores da aplicação"""
    
    # Cores primárias
    PRIMARY = "#2E5266"       # Azul escuro
    SECONDARY = "#6E8898"     # Azul médio
    ACCENT = "#9FB1BC"        # Azul claro
    
    # Cores de estado
    SUCCESS = "#52B788"       # Verde
    WARNING = "#F4A261"       # Laranja
    ERROR = "#E63946"         # Vermelho
    INFO = "#457B9D"          # Azul informação
    
    # Cores de fundo
    BACKGROUND = "#F8F9FA"    # Cinza muito claro
    SURFACE = "#FFFFFF"       # Branco
    CARD = "#FFFFFF"          # Branco para cards
    
    # Cores de texto
    TEXT_PRIMARY = "#212529"   # Preto suave
    TEXT_SECONDARY = "#6C757D" # Cinza
    TEXT_DISABLED = "#ADB5BD"  # Cinza claro
    TEXT_ON_PRIMARY = "#FFFFFF" # Branco
    
    # Cores de borda
    BORDER = "#DEE2E6"
    BORDER_LIGHT = "#E9ECEF"
    
    # Sombras
    SHADOW = "rgba(0, 0, 0, 0.1)"
    SHADOW_STRONG = "rgba(0, 0, 0, 0.2)"


class AircraftColors:
    """Cores específicas para cada família de aeronave"""
    
    E145 = "#1B4965"   # Azul petróleo
    E1 = "#62B6CB"     # Azul céu
    E2 = "#5FA8D3"     # Azul médio
    E170 = "#1A759F"   # Azul profundo

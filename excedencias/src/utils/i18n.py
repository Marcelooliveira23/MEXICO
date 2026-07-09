"""
Internationalization (i18n) System
Sistema completo de tradução e localização
"""

import json
import locale
import os
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from utils.logger import logger


@dataclass
class LanguageInfo:
    """Informações sobre um idioma"""
    code: str           # pt_BR, en_US, es_ES
    name: str           # Português (Brasil)
    flag: str           # 🇧🇷
    direction: str = "ltr"  # ltr ou rtl
    decimal_sep: str = ","
    thousands_sep: str = "."
    date_format: str = "%d/%m/%Y"
    time_format: str = "%H:%M:%S"


class I18nManager:
    """
    Gerenciador de Internacionalização
    Suporta múltiplos idiomas com carregamento dinâmico
    """
    
    # Idiomas suportados
    SUPPORTED_LANGUAGES = {
        "pt_BR": LanguageInfo(
            code="pt_BR",
            name="Português (Brasil)",
            flag="🇧🇷",
            decimal_sep=",",
            thousands_sep=".",
            date_format="%d/%m/%Y",
            time_format="%H:%M:%S"
        ),
        "en_US": LanguageInfo(
            code="en_US",
            name="English (United States)",
            flag="🇺🇸",
            decimal_sep=".",
            thousands_sep=",",
            date_format="%m/%d/%Y",
            time_format="%I:%M:%S %p"
        ),
        "es_ES": LanguageInfo(
            code="es_ES",
            name="Español (España)",
            flag="🇪🇸",
            decimal_sep=",",
            thousands_sep=".",
            date_format="%d/%m/%Y",
            time_format="%H:%M:%S"
        )
    }
    
    def __init__(self, translations_dir: str = "translations"):
        """
        Inicializar gerenciador i18n
        
        Args:
            translations_dir: Diretório com arquivos de tradução
        """
        self.translations_dir = Path(translations_dir)
        self.translations: Dict[str, Dict[str, str]] = {}
        self.current_language = "pt_BR"  # Default
        self.fallback_language = "en_US"
        
        # Criar diretório se não existir
        self.translations_dir.mkdir(exist_ok=True)
        
        # Detectar idioma do sistema
        self._detect_system_language()
        
        # Carregar traduções
        self._load_all_translations()
        
        logger.info(f"I18nManager initialized: {self.current_language}")
    
    def _detect_system_language(self):
        """Detectar idioma do sistema operacional"""
        try:
            system_locale = locale.getlocale()[0]
            if not system_locale:
                locale.setlocale(locale.LC_ALL, '')
                system_locale = locale.getlocale()[0]
            
            # Mapear locale do sistema para nossos códigos
            if system_locale:
                if system_locale.startswith("pt"):
                    self.current_language = "pt_BR"
                elif system_locale.startswith("es"):
                    self.current_language = "es_ES"
                elif system_locale.startswith("en"):
                    self.current_language = "en_US"
                
                logger.info(f"System language detected: {system_locale} -> {self.current_language}")
        
        except Exception as e:
            logger.warning(f"Could not detect system language: {e}")
            self.current_language = "pt_BR"
    
    def _load_all_translations(self):
        """Carregar todos os arquivos de tradução"""
        for lang_code in self.SUPPORTED_LANGUAGES.keys():
            self._load_translation(lang_code)
    
    def _load_translation(self, lang_code: str):
        """
        Carregar arquivo de tradução para um idioma
        
        Args:
            lang_code: Código do idioma (pt_BR, en_US, etc)
        """
        file_path = self.translations_dir / f"{lang_code}.json"
        
        if not file_path.exists():
            logger.warning(f"Translation file not found: {file_path}")
            self.translations[lang_code] = {}
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.translations[lang_code] = json.load(f)
            
            logger.info(f"Loaded {len(self.translations[lang_code])} translations for {lang_code}")
        
        except Exception as e:
            logger.error(f"Error loading translation {lang_code}: {e}")
            self.translations[lang_code] = {}
    
    def set_language(self, lang_code: str):
        """
        Definir idioma atual
        
        Args:
            lang_code: Código do idioma
        """
        if lang_code not in self.SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported language: {lang_code}")
            return
        
        self.current_language = lang_code
        logger.info(f"Language changed to: {lang_code}")
    
    def get_language(self) -> str:
        """Obter idioma atual"""
        return self.current_language
    
    def get_language_info(self) -> LanguageInfo:
        """Obter informações do idioma atual"""
        return self.SUPPORTED_LANGUAGES[self.current_language]
    
    def get_available_languages(self) -> List[LanguageInfo]:
        """Obter lista de idiomas disponíveis"""
        return list(self.SUPPORTED_LANGUAGES.values())
    
    def translate(self, key: str, **kwargs) -> str:
        """
        Traduzir uma chave
        
        Args:
            key: Chave de tradução (ex: "ui.button.save")
            **kwargs: Variáveis para interpolação
            
        Returns:
            Texto traduzido
        """
        # Tentar idioma atual
        text = self._get_translation(self.current_language, key)
        
        # Fallback para inglês
        if text is None:
            text = self._get_translation(self.fallback_language, key)
        
        # Fallback para a própria chave
        if text is None:
            logger.warning(f"Translation not found: {key}")
            text = key
        
        # Interpolação de variáveis
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError as e:
                logger.error(f"Missing variable in translation {key}: {e}")
        
        return text
    
    def _get_translation(self, lang_code: str, key: str) -> Optional[str]:
        """
        Obter tradução específica
        
        Args:
            lang_code: Código do idioma
            key: Chave de tradução
            
        Returns:
            Texto traduzido ou None
        """
        if lang_code not in self.translations:
            return None
        
        # Suportar chaves aninhadas: ui.button.save -> translations['ui']['button']['save']
        keys = key.split('.')
        value = self.translations[lang_code]
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value if isinstance(value, str) else None
    
    def format_number(self, number: float, decimals: int = 2) -> str:
        """
        Formatar número de acordo com locale
        
        Args:
            number: Número para formatar
            decimals: Casas decimais
            
        Returns:
            Número formatado
        """
        lang_info = self.get_language_info()
        
        # Formatar com casas decimais
        formatted = f"{number:.{decimals}f}"
        
        # Substituir separadores
        formatted = formatted.replace('.', 'TEMP')
        formatted = formatted.replace(',', lang_info.thousands_sep)
        formatted = formatted.replace('TEMP', lang_info.decimal_sep)
        
        # Adicionar separador de milhares
        parts = formatted.split(lang_info.decimal_sep)
        integer_part = parts[0]
        
        # Adicionar separadores de milhares
        if len(integer_part) > 3:
            reversed_int = integer_part[::-1]
            grouped = [reversed_int[i:i+3] for i in range(0, len(reversed_int), 3)]
            integer_part = lang_info.thousands_sep.join(grouped)[::-1]
        
        if len(parts) > 1:
            return f"{integer_part}{lang_info.decimal_sep}{parts[1]}"
        else:
            return integer_part
    
    def format_date(self, date: datetime) -> str:
        """
        Formatar data de acordo com locale
        
        Args:
            date: Data para formatar
            
        Returns:
            Data formatada
        """
        lang_info = self.get_language_info()
        return date.strftime(lang_info.date_format)
    
    def format_time(self, time: datetime) -> str:
        """
        Formatar hora de acordo com locale
        
        Args:
            time: Hora para formatar
            
        Returns:
            Hora formatada
        """
        lang_info = self.get_language_info()
        return time.strftime(lang_info.time_format)
    
    def format_datetime(self, dt: datetime) -> str:
        """
        Formatar data e hora
        
        Args:
            dt: Data/hora para formatar
            
        Returns:
            Data/hora formatada
        """
        return f"{self.format_date(dt)} {self.format_time(dt)}"
    
    def export_template(self, lang_code: str, output_file: Optional[str] = None):
        """
        Exportar template de tradução
        
        Args:
            lang_code: Código do idioma
            output_file: Arquivo de saída (opcional)
        """
        if output_file is None:
            output_file = str(self.translations_dir / f"{lang_code}.json")
        
        # Template com todas as chaves necessárias
        template = {
            "app": {
                "name": "Sistema de Análise de Inspeções de Aeronaves",
                "version": "1.0.0"
            },
            "ui": {
                "button": {
                    "save": "Salvar",
                    "cancel": "Cancelar",
                    "close": "Fechar",
                    "import": "Importar",
                    "export": "Exportar",
                    "analyze": "Analisar",
                    "start": "Iniciar",
                    "stop": "Parar",
                    "clear": "Limpar",
                    "confirm": "Confirmar",
                    "delete": "Excluir"
                },
                "menu": {
                    "file": "Arquivo",
                    "edit": "Editar",
                    "view": "Visualizar",
                    "tools": "Ferramentas",
                    "help": "Ajuda"
                },
                "label": {
                    "aircraft": "Aeronave",
                    "flight_id": "ID do Voo",
                    "event_type": "Tipo de Evento",
                    "severity": "Severidade",
                    "status": "Status",
                    "timestamp": "Data/Hora",
                    "details": "Detalhes"
                }
            },
            "analysis": {
                "hard_landing": "Pouso Duro",
                "gear_overspeed": "Velocidade Excessiva do Trem",
                "max_speed": "Velocidade Máxima",
                "flap_overspeed": "Velocidade Excessiva com Flaps",
                "overweight_landing": "Pouso Acima do Peso",
                "temp_envelope": "Envelope de Temperatura"
            },
            "severity": {
                "critical": "Crítico",
                "high": "Alto",
                "medium": "Médio",
                "low": "Baixo",
                "info": "Info"
            },
            "messages": {
                "success": {
                    "saved": "Salvo com sucesso",
                    "imported": "Importado com sucesso",
                    "exported": "Exportado com sucesso",
                    "analyzed": "Análise concluída"
                },
                "error": {
                    "failed_to_save": "Falha ao salvar",
                    "failed_to_import": "Falha ao importar",
                    "failed_to_export": "Falha ao exportar",
                    "failed_to_analyze": "Falha na análise",
                    "invalid_file": "Arquivo inválido",
                    "no_data": "Nenhum dado encontrado"
                },
                "warning": {
                    "unsaved_changes": "Alterações não salvas",
                    "confirm_delete": "Confirmar exclusão?"
                }
            },
            "realtime": {
                "monitoring": "Monitoramento",
                "connections": "Conexões",
                "queue": "Fila",
                "alerts": "Alertas",
                "statistics": "Estatísticas",
                "event_log": "Log de Eventos"
            }
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Translation template exported to: {output_file}")
        
        except Exception as e:
            logger.error(f"Error exporting template: {e}")


# Singleton instance
_i18n_instance: Optional[I18nManager] = None


def get_i18n(translations_dir: str = "translations") -> I18nManager:
    """
    Obter instância singleton do I18nManager
    
    Args:
        translations_dir: Diretório de traduções
        
    Returns:
        Instância do I18nManager
    """
    global _i18n_instance
    
    if _i18n_instance is None:
        _i18n_instance = I18nManager(translations_dir)
    
    return _i18n_instance


# Função de conveniência
def _(key: str, **kwargs) -> str:
    """
    Atalho para tradução
    
    Args:
        key: Chave de tradução
        **kwargs: Variáveis para interpolação
        
    Returns:
        Texto traduzido
    """
    return get_i18n().translate(key, **kwargs)

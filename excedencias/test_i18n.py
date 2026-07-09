"""
Testes para Sistema de Internacionalização (i18n)
Cobertura completa do I18nManager e traduções
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.i18n import I18nManager, LanguageInfo, get_i18n, _


class TestI18nManager:
    """Testes para I18nManager"""
    
    @pytest.fixture
    def temp_translations_dir(self):
        """Criar diretório temporário para traduções"""
        temp_dir = tempfile.mkdtemp()
        
        # Criar arquivos de tradução de teste
        pt_br = {
            "ui": {
                "button": {
                    "save": "Salvar",
                    "cancel": "Cancelar"
                },
                "message": "Olá, {name}!"
            },
            "test": {
                "nested": {
                    "deep": "Valor aninhado"
                }
            }
        }
        
        en_us = {
            "ui": {
                "button": {
                    "save": "Save",
                    "cancel": "Cancel"
                },
                "message": "Hello, {name}!"
            }
        }
        
        with open(Path(temp_dir) / "pt_BR.json", 'w', encoding='utf-8') as f:
            json.dump(pt_br, f, ensure_ascii=False)
        
        with open(Path(temp_dir) / "en_US.json", 'w', encoding='utf-8') as f:
            json.dump(en_us, f, ensure_ascii=False)
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def i18n_manager(self, temp_translations_dir):
        """Fixture para I18nManager"""
        return I18nManager(translations_dir=temp_translations_dir)
    
    def test_initialization(self, i18n_manager):
        """Testar inicialização"""
        assert i18n_manager.current_language in ["pt_BR", "en_US", "es_ES"]
        assert i18n_manager.fallback_language == "en_US"
        assert len(i18n_manager.translations) > 0
    
    def test_supported_languages(self):
        """Testar lista de idiomas suportados"""
        languages = I18nManager.SUPPORTED_LANGUAGES
        
        assert "pt_BR" in languages
        assert "en_US" in languages
        assert "es_ES" in languages
        
        # Verificar estrutura
        pt_br = languages["pt_BR"]
        assert pt_br.code == "pt_BR"
        assert pt_br.name == "Português (Brasil)"
        assert pt_br.flag == "🇧🇷"
        assert pt_br.decimal_sep == ","
        assert pt_br.thousands_sep == "."
    
    def test_set_language(self, i18n_manager):
        """Testar mudança de idioma"""
        i18n_manager.set_language("en_US")
        assert i18n_manager.get_language() == "en_US"
        
        i18n_manager.set_language("pt_BR")
        assert i18n_manager.get_language() == "pt_BR"
    
    def test_set_invalid_language(self, i18n_manager):
        """Testar mudança para idioma inválido"""
        original = i18n_manager.get_language()
        i18n_manager.set_language("invalid_LANG")
        
        # Deve manter o idioma original
        assert i18n_manager.get_language() == original
    
    def test_get_language_info(self, i18n_manager):
        """Testar obtenção de informações do idioma"""
        i18n_manager.set_language("pt_BR")
        info = i18n_manager.get_language_info()
        
        assert isinstance(info, LanguageInfo)
        assert info.code == "pt_BR"
        assert info.decimal_sep == ","
    
    def test_get_available_languages(self, i18n_manager):
        """Testar lista de idiomas disponíveis"""
        languages = i18n_manager.get_available_languages()
        
        assert len(languages) == 3
        assert all(isinstance(lang, LanguageInfo) for lang in languages)
    
    def test_translate_simple(self, i18n_manager):
        """Testar tradução simples"""
        i18n_manager.set_language("pt_BR")
        text = i18n_manager.translate("ui.button.save")
        assert text == "Salvar"
        
        i18n_manager.set_language("en_US")
        text = i18n_manager.translate("ui.button.save")
        assert text == "Save"
    
    def test_translate_nested(self, i18n_manager):
        """Testar tradução com chaves aninhadas"""
        i18n_manager.set_language("pt_BR")
        text = i18n_manager.translate("test.nested.deep")
        assert text == "Valor aninhado"
    
    def test_translate_with_interpolation(self, i18n_manager):
        """Testar tradução com interpolação de variáveis"""
        i18n_manager.set_language("pt_BR")
        text = i18n_manager.translate("ui.message", name="João")
        assert text == "Olá, João!"
        
        i18n_manager.set_language("en_US")
        text = i18n_manager.translate("ui.message", name="John")
        assert text == "Hello, John!"
    
    def test_translate_missing_key(self, i18n_manager):
        """Testar tradução de chave inexistente"""
        text = i18n_manager.translate("non.existent.key")
        
        # Deve retornar a própria chave
        assert text == "non.existent.key"
    
    def test_translate_fallback(self, i18n_manager):
        """Testar fallback para inglês"""
        i18n_manager.set_language("es_ES")
        
        # Chave que só existe em inglês (no nosso teste)
        text = i18n_manager.translate("ui.button.save")
        
        # Deve fazer fallback para en_US
        assert text in ["Save", "Guardar", "Salvar"]
    
    def test_format_number_pt_br(self, i18n_manager):
        """Testar formatação de número em PT-BR"""
        i18n_manager.set_language("pt_BR")
        
        # 1234.56 -> 1.234,56
        formatted = i18n_manager.format_number(1234.56, decimals=2)
        assert "," in formatted  # Separador decimal
        assert "." in formatted or len(formatted.split(",")[0]) <= 4  # Separador de milhares
    
    def test_format_number_en_us(self, i18n_manager):
        """Testar formatação de número em EN-US"""
        i18n_manager.set_language("en_US")
        
        # 1234.56 -> 1,234.56
        formatted = i18n_manager.format_number(1234.56, decimals=2)
        assert "." in formatted  # Separador decimal
    
    def test_format_date_pt_br(self, i18n_manager):
        """Testar formatação de data em PT-BR"""
        i18n_manager.set_language("pt_BR")
        
        date = datetime(2026, 2, 4)
        formatted = i18n_manager.format_date(date)
        
        # Formato: DD/MM/YYYY
        assert formatted == "04/02/2026"
    
    def test_format_date_en_us(self, i18n_manager):
        """Testar formatação de data em EN-US"""
        i18n_manager.set_language("en_US")
        
        date = datetime(2026, 2, 4)
        formatted = i18n_manager.format_date(date)
        
        # Formato: MM/DD/YYYY
        assert formatted == "02/04/2026"
    
    def test_format_time(self, i18n_manager):
        """Testar formatação de hora"""
        time = datetime(2026, 2, 4, 15, 30, 45)
        
        i18n_manager.set_language("pt_BR")
        formatted_pt = i18n_manager.format_time(time)
        assert "15:30:45" in formatted_pt or "15:30" in formatted_pt
        
        i18n_manager.set_language("en_US")
        formatted_en = i18n_manager.format_time(time)
        # EN-US usa 12h format com AM/PM
        assert "PM" in formatted_en or ":" in formatted_en
    
    def test_format_datetime(self, i18n_manager):
        """Testar formatação de data/hora"""
        dt = datetime(2026, 2, 4, 15, 30, 45)
        
        i18n_manager.set_language("pt_BR")
        formatted = i18n_manager.format_datetime(dt)
        
        assert "04/02/2026" in formatted
        assert ":" in formatted  # Tem hora
    
    def test_export_template(self, i18n_manager, tmp_path):
        """Testar exportação de template"""
        output_file = tmp_path / "template.json"
        
        i18n_manager.export_template("pt_BR", str(output_file))
        
        # Verificar que arquivo foi criado
        assert output_file.exists()
        
        # Verificar conteúdo
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert "app" in data
        assert "ui" in data
        assert "button" in data["ui"]
        assert "save" in data["ui"]["button"]
    
    def test_singleton_pattern(self, temp_translations_dir):
        """Testar padrão singleton"""
        # Resetar singleton para teste
        import utils.i18n
        utils.i18n._i18n_instance = None
        
        i18n1 = get_i18n(temp_translations_dir)
        i18n2 = get_i18n(temp_translations_dir)
        
        assert i18n1 is i18n2
    
    def test_translate_shortcut(self, temp_translations_dir):
        """Testar função de atalho _()"""
        # Resetar singleton
        import utils.i18n
        utils.i18n._i18n_instance = I18nManager(temp_translations_dir)
        utils.i18n._i18n_instance.set_language("pt_BR")
        
        text = _("ui.button.save")
        assert text == "Salvar"


class TestRealTranslations:
    """Testes com arquivos de tradução reais"""
    
    @pytest.fixture
    def i18n_real(self):
        """I18n com traduções reais"""
        translations_dir = Path(__file__).parent / "translations"
        if not translations_dir.exists():
            pytest.skip("Translation files not found")
        return I18nManager(str(translations_dir))
    
    def test_real_translations_loaded(self, i18n_real):
        """Testar que traduções reais foram carregadas"""
        # Verificar PT-BR
        i18n_real.set_language("pt_BR")
        assert i18n_real.translate("app.name") != "app.name"
        
        # Verificar EN-US
        i18n_real.set_language("en_US")
        assert i18n_real.translate("app.name") != "app.name"
        
        # Verificar ES-ES
        i18n_real.set_language("es_ES")
        assert i18n_real.translate("app.name") != "app.name"
    
    def test_button_translations(self, i18n_real):
        """Testar traduções de botões"""
        buttons = ["save", "cancel", "close", "import", "export", "analyze"]
        
        for lang in ["pt_BR", "en_US", "es_ES"]:
            i18n_real.set_language(lang)
            
            for button in buttons:
                text = i18n_real.translate(f"ui.button.{button}")
                assert text != f"ui.button.{button}"
                assert len(text) > 0
    
    def test_analysis_types_translations(self, i18n_real):
        """Testar traduções de tipos de análise"""
        analysis_types = [
            "hard_landing",
            "gear_overspeed",
            "max_speed",
            "flap_overspeed",
            "overweight_landing",
            "temp_envelope"
        ]
        
        for lang in ["pt_BR", "en_US", "es_ES"]:
            i18n_real.set_language(lang)
            
            for analysis_type in analysis_types:
                text = i18n_real.translate(f"analysis.{analysis_type}")
                assert text != f"analysis.{analysis_type}"
                assert len(text) > 0
    
    def test_severity_translations(self, i18n_real):
        """Testar traduções de severidade"""
        severities = ["critical", "high", "medium", "low", "info"]
        
        for lang in ["pt_BR", "en_US", "es_ES"]:
            i18n_real.set_language(lang)
            
            for severity in severities:
                text = i18n_real.translate(f"severity.{severity}")
                assert text != f"severity.{severity}"
                assert len(text) > 0
    
    def test_message_translations(self, i18n_real):
        """Testar traduções de mensagens"""
        messages = [
            "messages.success.saved",
            "messages.error.failed_to_save",
            "messages.warning.unsaved_changes",
            "messages.info.processing"
        ]
        
        for lang in ["pt_BR", "en_US", "es_ES"]:
            i18n_real.set_language(lang)
            
            for message in messages:
                text = i18n_real.translate(message)
                assert text != message
                assert len(text) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

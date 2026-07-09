#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML LOCALIZATION HELPER - Traduz conteúdo legacy em inglês para português
Identificação automática de strings chave que precisam tradução
"""

# Dicionário de tradução principal (legacy content → PT-BR)
TRANSLATION_MAP = {
    # Botões comuns
    'Apply': 'Aplicar',
    'Cancel': 'Cancelar',
    'Save': 'Salvar',
    'Delete': 'Deletar',
    'Back': 'Voltar',
    'Next': 'Próximo',
    'Previous': 'Anterior',
    'Submit': 'Enviar',
    'Clear': 'Limpar',
    'Reset': 'Reiniciar',
    'Close': 'Fechar',
    'Search': 'Pesquisar',
    'Filter': 'Filtro',
    'Sort': 'Ordenar',
    'Export': 'Exportar',
    'Import': 'Importar',
    'Download': 'Baixar',
    'Upload': 'Enviar',
    'Add': 'Adicionar',
    'Edit': 'Editar',
    'View': 'Visualizar',
    'Analyze': 'Analisar',
    'Generate': 'Gerar',
    'Configure': 'Configurar',
    'Refresh': 'Atualizar',
    'Reload': 'Recarregar',
    'Create': 'Criar',
    'Remove': 'Remover',
    'Update': 'Atualizar',
    'Execute': 'Executar',
    'Expand': 'Expandir',
    'Collapse': 'Recolher',
    
    # Campos de formulário
    'Operating family': 'Família operacional',
    'Model': 'Modelo',
    'Category': 'Categoria',
    'Description': 'Descrição',
    'Status': 'Situação',
    'Date': 'Data',
    'Time': 'Hora',
    'Notes': 'Observações',
    'Comments': 'Comentários',
    'Tail': 'Cauda',
    'Aircraft': 'Aeronave',
    'ATA': 'ATA',
    'System': 'Sistema',
    'Component': 'Componente',
    'Part Number': 'Número da Peça',
    'Serial Number': 'Número de Série',
    'Flight Hours': 'Horas de Voo',
    'Flight Cycles': 'Ciclos de Voo',
    'Location': 'Localização',
    'Technician': 'Técnico',
    'Duration': 'Duração',
    'Estimated Hours': 'Horas Estimadas',
    'Priority': 'Prioridade',
    'Severity': 'Gravidade',
    'Resolution': 'Resolução',
    'Troubleshooting': 'Solução de Problemas',
    
    # Labels & Headings
    'Fleet Status Report': 'Relatório de Situação da Frota',
    'Aircraft Status': 'Situação da Aeronave',
    'Operational': 'Operacional',
    'Out of Service': 'Fora de Serviço',
    'Health Index': 'Índice de Saúde',
    'Open Issues': 'Questões Abertas',
    'Closed Issues': 'Questões Fechadas',
    'Last 30 Days': 'Últimos 30 Dias',
    'Trend': 'Tendência',
    'Forecast': 'Previsão',
    'Top ATA': 'ATA Principal',
    'Failure Pattern': 'Padrão de Falha',
    'Recurring Issues': 'Problemas Recorrentes',
    'MEL Items': 'Itens MEL',
    'AOG Events': 'Eventos AOG',
    'Maintenance': 'Manutenção',
    'Inspection': 'Inspeção',
    'Preventive': 'Preventiva',
    'Corrective': 'Corretiva',
    'Emergency': 'Emergência',
    'By Aircraft': 'Por Aeronave',
    'By System': 'Por Sistema',
    'By Date': 'Por Data',
    'By Technician': 'Por Técnico',
    
    # Status Messages
    'Loading...': 'Carregando...',
    'No data available': 'Nenhum dado disponível',
    'Please select': 'Por favor, selecione',
    'Required field': 'Campo obrigatório',
    'Invalid input': 'Entrada inválida',
    'Success': 'Sucesso',
    'Error': 'Erro',
    'Warning': 'Aviso',
    'Information': 'Informação',
    'Confirm': 'Confirmar',
    'Are you sure?': 'Você tem certeza?',
    
    # Page titles
    'Logbook': 'Diário de Bordo',
    'Maintenance Events': 'Eventos de'Manutenção',
    'MEL - Minimum Equipment List': 'MEL - Lista Mínima de Equipamentos',
    'LRU Removals': 'Remoções de LRU',
    'User Management': 'Gerenciamento de Usuários',
    'Settings': 'Configurações',
    'Dashboard': 'Painel de Controle',
    'Reports': 'Relatórios',
    'Administration': 'Administração',
    'Help': 'Ajuda',
    'About': 'Sobre',
    'Version': 'Versão',
    
    # AI/Analytics terms
    'Analyze Failure': 'Analisar Falha',
    'Troubleshooting Steps': 'Etapas de Solução de Problemas',
    'Recommended Actions': 'Ações Recomendadas',
    'Similar Cases': 'Casos Semelhantes',
    'Pattern Recognition': 'Reconhecimento de Padrão',
    'Predictive Analysis': 'Análise Preditiva',
    'Risk Assessment': 'Avaliação de Risco',
    'Fleet Intelligence': 'Inteligência da Frota',
    'AI Recommendation': 'Recomendação de IA',
    'Confidence': 'Confiança',
    'Score': 'Pontuação',
}

# Strings mais frequentes que precisam tradução
TOP_TRANSLATIONS_BY_FREQUENCY = [
    ('Filter by', 'Filtrar por'),
    ('Sort by', 'Ordenar por'),
    ('View', 'Visualizar'),
    ('Aircraft', 'Aeronave'),
    ('Status', 'Situação'),
    ('No data', 'Sem dados'),
    ('Loading', 'Carregando'),
    ('Select', 'Selecionar'),
    ('Please', 'Por favor'),
    ('Available', 'Disponível'),
    ('Open', 'Aberto'),
    ('Closed', 'Fechado'),
    ('Active', 'Ativo'),
    ('Inactive', 'Inativo'),
]

def translate_html_file(content: str, translation_dict=None) -> str:
    """
    Traduz conteúdo HTML usando dicionário de tradução.
    Preserva tags HTML e atributos.
    """
    if translation_dict is None:
        translation_dict = TRANSLATION_MAP
    
    # Não traduzir dentro de tags HTML
    import re
    
    # Extract text content (between > and <)
    def replace_in_text(match):
        full = match.group(0)
        tag_start = full.find('>')
        tag_end = full.rfind('<')
        
        if tag_start == -1 or tag_end == -1:
            return full
        
        text = full[tag_start+1:tag_end]
        
        # Try translations
        for en, pt in translation_dict.items():
            if en in text:
                text = text.replace(en, pt)
        
        return full[:tag_start+1] + text + full[tag_end:]
    
    # DO NOT translate attribute values in some cases
    # Only translate button text, labels, placeholders, titles
    
    result = content
    for en, pt in sorted(translation_dict.items(), key=lambda x: -len(x[0])):
        # Translate text nodes (between tags)
        # Translate button text
        result = re.sub(f'(<button[^>]*>)({en})(<\/button>)', 
                       f'\\1{pt}\\3', result)
        # Translate label text
        result = re.sub(f'(<label[^>]*>)({en})(<\/label>)', 
                       f'\\1{pt}\\3', result)
        # Translate span text
        result = re.sub(f'(<span[^>]*>)({en})(<\/span>)', 
                       f'\\1{pt}\\3', result)
        # Translate div text (be careful - only short text)
        result = re.sub(f'(<div[^>]*>)({en})(<\/div>)', 
                       f'\\1{pt}\\3', result)
        # Translate h1-h6
        result = re.sub(f'(<h[1-6][^>]*>)({en})(<\/h[1-6]>)', 
                       f'\\1{pt}\\3', result)
        # Translate td/th
        result = re.sub(f'(<t[dh][^>]*>)({en})(<\/t[dh]>)', 
                       f'\\1{pt}\\3', result)
    
    return result

if __name__ == '__main__':
    # Test the translation
    test_html = '''
    <button>Filter by Model</button>
    <label>Operating family</label>
    <span>No data available</span>
    '''
    
    translated = translate_html_file(test_html)
    print("Original:")
    print(test_html)
    print("\nTranslated:")
    print(translated)

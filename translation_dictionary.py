#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPREHENSIVE TRANSLATION DICTIONARY
Maps all Portuguese/Spanish terms to English equivalents
Used for database migrations, code refactoring, and UI localization
"""

TRANSLATION_MAP = {
    # ===== DATABASE ENTITY NAMES =====
    "Falha": "Failure",
    "Registro de Falha": "Fault Registration",
    "Sistema Inoperante": "Unserviceable System",
    "Aeronave": "Aircraft",
    "Cauda": "Tail",
    "Matrícula": "Registration",
    
    # ===== STATUS FIELDS =====
    "Aberta": "Open",
    "Fechada": "Closed",
    "Emaberto": "In Progress",
    "Resolvida": "Resolved",
    "Em Serviço": "In Service",
    "Fora de Serviço": "Out of Service",
    "Ativa": "Active",
    "Inativa": "Inactive",
    "Aposentada": "Retired",
    
    # ===== MAINTENANCE TERMS =====
    "MEL": "Minimum Equipment List",
    "Itens MEL": "MEL Items",
    "ETD": "Technical Disposition",
    "Disposição Técnica": "Technical Disposition",
    "AOG": "Aircraft on Ground",
    "LRU": "Line Replaceable Unit",
    "Componentes": "Components",
    "Remoção e Instalação": "Removal and Installation",
    "Ação de Manutenção": "Maintenance Action",
    "Ações Executadas": "Executed Actions",
    "Logbook Técnico": "Technical Logbook",
    "Logbook": "Logbook",
    
    # ===== OPERATIONAL TERMS =====
    "Horas de Voo": "Flight Hours",
    "Ciclos": "Cycles",
    "Utilizacao": "Utilization",
    "Tendência": "Trend",
    "Total de Horas": "Total Hours",
    "Total de Ciclos": "Total Cycles",
    "Hora de Fabricação": "Manufactured Date",
    "Data de Aposentadoria": "Retirement Date",
    "Data Aberta": "Open Date",
    "Data Fechada": "Close Date",
    "Data Prevista": "Due Date",
    "Data de Retorno Esperado": "Expected Return Date",
    "Data de Liberação": "Release Date",
    
    # ===== AIRCRAFT MODELS =====
    "E190": "E190",
    "E195": "E195",
    "E190-E2": "E190-E2",
    "E195-E2": "E195-E2",
    "Modelo": "Model",
    "Número de Série": "Serial Number",
    "Status de Registro": "Registration Status",
    
    # ===== ATA CHAPTERS =====
    "Sistemas Elétricos": "Electrical System",
    "Motores": "Engines",
    "Células": "Airframe",
    "Aviónica": "Avionics",
    "Navegação": "Navigation",
    "Comando de Voo": "Flight Controls",
    "Combustível": "Fuel System",
    "Ambiente de Cabine": "Cabin Environment",
    "Equipamentos": "Equipment/Furnishings",
    "Luzes": "Lights",
    "Portas": "Doors",
    "Controle Ambiental": "Environmental Control",
    "Água e Esgoto": "Water/Waste",
    "Assento dos Passageiros": "Passenger Seating",
    "Segurança": "Safety Equipment",
    
    # ===== CATEGORIES =====
    "Categoria": "Category",
    "Crítico": "Critical",
    "Crítica": "Critical",
    
    # ===== USER ROLES =====
    "Administrador": "Administrator",
    "Admin": "Admin",
    "Técnico": "Technician",
    "Piloto": "Pilot",
    "Usuário": "User",
    "Nível de Acesso": "Access Level",
    "Ativo": "Active",
    "Inativo": "Inactive",
    
    # ===== FORM FIELDS & ACTIONS =====
    "Nome de Usuário": "Username",
    "Senha": "Password",
    "Email": "Email",
    "Confirmar Senha": "Confirm Password",
    "Lembrar-me": "Remember Me",
    "Entrar": "Login",
    "Sair": "Logout",
    "Salvar": "Save",
    "Cancelar": "Cancel",
    "Editar": "Edit",
    "Deletar": "Delete",
    "Excluir": "Delete",
    "Adicionar": "Add",
    "Criar": "Create",
    "Atualizar": "Update",
    "Enviar": "Submit",
    "Voltar": "Back",
    "Próximo": "Next",
    "Anterior": "Previous",
    "Filtrar": "Filter",
    "Buscar": "Search",
    "Limpar": "Clear",
    "Aplicar": "Apply",
    "Exportar": "Export",
    "Importar": "Import",
    "Imprimir": "Print",
    "Download": "Download",
    "Upload": "Upload",
    "Fechar": "Close",
    "Abrir": "Open",
    
    # ===== PAGE TITLES =====
    "Menu Principal": "Main Menu",
    "Dashboard": "Dashboard",
    "Relatório": "Report",
    "Relatório de Status da Frota": "Fleet Status Report",
    "Gestão de Usuários": "User Management",
    "Mudança de Senha": "Change Password",
    "Configurações": "Settings",
    "Sobre": "About",
    "Ajuda": "Help",
    
    # ===== ERROR MESSAGES =====
    "Erro": "Error",
    "Erro ao carregar dados": "Error loading data",
    "Falha": "Failure",
    "Verifique sua conexão": "Check your connection",
    "Acesso Negado": "Access Denied",
    "Permissões Insuficientes": "Insufficient Permissions",
    "Não Encontrado": "Not Found",
    "Falha na Autenticação": "Authentication Failed",
    "Senha Incorreta": "Incorrect Password",
    "Usuário não encontrado": "User not found",
    "Campos Obrigatórios": "Required Fields",
    "Por favor, preencha todos os campos": "Please fill all required fields",
    "Credenciais Inválidas": "Invalid Credentials",
    
    # ===== SUCCESS MESSAGES =====
    "Sucesso": "Success",
    "Salvo com Sucesso": "Saved Successfully",
    "Criado com Sucesso": "Created Successfully",
    "Deletado com Sucesso": "Deleted Successfully",
    "Atualizado com Sucesso": "Updated Successfully",
    "Operação Concluída": "Operation Completed",
    
    # ===== NOTIFICATIONS =====
    "Aviso": "Warning",
    "Informação": "Information",
    "Esta ação é irreversível": "This action is irreversible",
    "Tem certeza?": "Are you sure?",
    "Confirme esta ação": "Confirm this action",
    
    # ===== OTHER UI ELEMENTS =====
    "Início": "Home",
    "Página": "Page",
    "Total": "Total",
    "Nenhum Resultado": "No Results",
    "Carregando": "Loading",
    "Aguarde": "Please Wait",
    "Novo": "New",
    "Vazio": "Empty",
    "Selecionado": "Selected",
    "Todos": "All",
    "Nenhum": "None",
}

# ===== SPANISH VARIATIONS =====
TRANSLATION_MAP.update({
    "Fallo": "Failure",
    "Registro de Fallo": "Fault Registration",
    "Sistema Inoperable": "Unserviceable System",
    "Avión": "Aircraft",
    "Matricula": "Registration",
    "Estado": "Status",
    "Servicio": "In Service",
    "Fuera de Servicio": "Out of Service",
    "MEL": "Minimum Equipment List",
    "Artículos MEL": "MEL Items",
    "Horas de Vuelo": "Flight Hours",
    "Ciclos": "Cycles",
    "Acción de Mantenimiento": "Maintenance Action",
    "Libro de Abordo Técnico": "Technical Logbook",
    "Rol": "Role",
    "Administrador": "Administrator",
    "Técnico": "Technician",
    "Piloto": "Pilot",
    "Nombre de Usuario": "Username",
    "Contraseña": "Password",
    "Correo Electrónico": "Email",
    "Guardar": "Save",
    "Cancelar": "Cancel",
    "Atrás": "Back",
    "Siguiente": "Next",
    "Anterior": "Previous",
    "Buscar": "Search",
    "Crear": "Create",
    "Editar": "Edit",
    "Eliminar": "Delete",
    "Actualizar": "Update",
    "Error": "Error",
    "Éxito": "Success",
    "Advertencia": "Warning",
    "Información": "Information",
})

def get_english_term(portuguese_or_spanish: str) -> str:
    """
    Get English equivalent of Portuguese/Spanish term.
    Returns original if not in dictionary.
    """
    return TRANSLATION_MAP.get(portuguese_or_spanish, portuguese_or_spanish)


def translate_text(text: str) -> str:
    """
    Translate Portuguese/Spanish text to English.
    Works with phrases by checking each word.
    """
    if not text:
        return text
    
    words = text.split()
    translated = []
    
    for word in words:
        # Try exact match first
        if word in TRANSLATION_MAP:
            translated.append(TRANSLATION_MAP[word])
        else:
            # Try lowercase match
            lower_word = word.lower()
            found = False
            for pt_es_term, en_term in TRANSLATION_MAP.items():
                if pt_es_term.lower() == lower_word:
                    translated.append(en_term)
                    found = True
                    break
            if not found:
                translated.append(word)
    
    return ' '.join(translated)


# ===== SQL TRANSLATION SCRIPTS =====
SQL_TRANSLATIONS = {
    "database_enum_status": """
    -- Translate status enum values
    UPDATE failures SET status = 'Open' WHERE status = 'Aberta';
    UPDATE failures SET status = 'Closed' WHERE status = 'Fechada';
    UPDATE failures SET status = 'In Progress' WHERE status = 'Emaberto';
    UPDATE failures SET status = 'Resolved' WHERE status = 'Resolvida';
    
    UPDATE aircraft SET registration_status = 'Active' WHERE registration_status = 'Ativa';
    UPDATE aircraft SET registration_status = 'Out of Service' WHERE registration_status = 'Fora de Serviço';
    UPDATE aircraft SET registration_status = 'Grounded' WHERE registration_status = 'Aposentada';
    """,
    
    "database_column_rename": """
    -- Rename columns to English equivalents
    ALTER TABLE failures CHANGE COLUMN `data_abertura` `date_opened` DATE;
    ALTER TABLE failures CHANGE COLUMN `data_fechamento` `date_closed` DATE;
    ALTER TABLE failures CHANGE COLUMN `data_prevista` `due_date` DATE;
    ALTER TABLE failures CHANGE COLUMN `sistema_inoperante` `system_inop` VARCHAR(500);
    ALTER TABLE failures CHANGE COLUMN `acao_manutencao` `maintenance_action` TEXT;
    
    ALTER TABLE aircraft CHANGE COLUMN `numero_serie` `serial_number` VARCHAR(50);
    ALTER TABLE aircraft CHANGE COLUMN `status_registro` `registration_status` VARCHAR(50);
    ALTER TABLE aircraft CHANGE COLUMN `total_horas_voo` `total_flight_hours` FLOAT;
    ALTER TABLE aircraft CHANGE COLUMN `data_fabricacao` `manufactured_date` DATE;
    
    ALTER TABLE users CHANGE COLUMN `nome_usuario` `username` VARCHAR(100);
    ALTER TABLE users CHANGE COLUMN `nivel_acesso` `access_level` VARCHAR(50);
    ALTER TABLE users CHANGE COLUMN `ativo` `is_active` BOOLEAN;
    ALTER TABLE users CHANGE COLUMN `ultimo_login` `last_login` DATETIME;
    """,
    
    "database_label_updates": """
    -- Update data labels to English
    UPDATE failure_categories SET name = 'Navigation' WHERE name = 'Navegação';
    UPDATE failure_categories SET name = 'Electrical System' WHERE name = 'Sistemas Elétricos';
    UPDATE failure_categories SET name = 'Engines' WHERE name = 'Motores';
    UPDATE failure_categories SET name = 'Avionics' WHERE name = 'Aviónica';
    UPDATE failure_categories SET name = 'Flight Controls' WHERE name = 'Comando de Voo';
    UPDATE failure_categories SET name = 'Fuel System' WHERE name = 'Combustível';
    UPDATE failure_categories SET name = 'Environmental Control' WHERE name = 'Controle Ambiental';
    """
}


if __name__ == '__main__':
    # Test translations
    test_terms = [
        "Falha",
        "Registro de Falha",
        "Sistema Inoperante",
        "Horas de Voo",
        "Técnico",
        "Salvar"
    ]
    
    print("📚 Translation Dictionary Test")
    print("=" * 50)
    for term in test_terms:
        english = get_english_term(term)
        print(f"  {term:30} → {english}")
    
    print("\n✅ All translations loaded successfully!")


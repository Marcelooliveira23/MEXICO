# Troubleshooting System - Guia da Ferramenta

Sistema web para suporte a manutencao aeronautica, com foco em registro de falhas, acompanhamento de frota, AOG, MEL, ETD, LRU e analise assistida por IA.

## 1. Visao Geral

A aplicacao foi desenvolvida em Flask e organizada em dois blocos principais:

- Operacao: paginas de cadastro, status e controle de manutencao.
- Inteligencia/Analytics: APIs e telas para analise de falhas, tendencias e risco operacional.

O sistema opera com MySQL como base principal e possui mecanismo de fallback em JSON para manter continuidade quando o banco estiver indisponivel.

## 2. Principais Funcionalidades

- Autenticacao de usuarios (login, logout, troca de senha e administracao de usuarios).
- Registro de falhas tecnicas com status, prioridade, ATA, troubleshooting e solucao.
- Painel de horas e ciclos por aeronave (FH/FC).
- Visao consolidada de status da frota (indicadores operacionais, saude e recorrencia).
- Logbook com filtros e exportacao (Excel, CSV, PDF simples e modo impressao).
- Gestao de AOG (out of service) e retorno operacional.
- Gestao de MEL (itens abertos/fechados, urgencia e rastreio de recorrencia).
- Gestao de ETD com anexos e controle de emissao.
- Gestao de LRU (remocao/instalacao e estatisticas de componentes).
- IA aplicada a troubleshooting e analise de exceedance.

## 3. Paginas da Aplicacao

As paginas principais renderizadas pelo backend sao:

| Rota                      | Template                      | Finalidade                                 |
| ------------------------- | ----------------------------- | ------------------------------------------ |
| /login                    | login.html                    | Autenticacao de usuarios                   |
| /menu                     | menu.html                     | Navegacao central do sistema               |
| /change_password          | change_password.html          | Alteracao de senha                         |
| /user_management          | user_management.html          | Administracao de usuarios                  |
| /cadastro                 | cadastro.html                 | Cadastro de falhas/manutencao              |
| /horas_ciclos             | horas_ciclos.html             | Controle de FH/FC                          |
| /fleet_status_report      | fleet_status_report.html      | Situacao operacional da frota              |
| /logbook_data             | logbook_data.html             | Consulta de registros e exportacao         |
| /out_of_service           | out_of_service.html           | Controle AOG / aeronave fora de servico    |
| /tail_cadastro            | tail_cadastro.html            | Cadastro e consolidacao de tails           |
| /mel_itens                | mel_itens.html                | Gestao de itens MEL                        |
| /etd                      | etd.html                      | Gestao ETD e compliance                    |
| /lru_removal_installation | lru_removal_installation.html | Historico de remocao/instalacao LRU        |
| /ai_analysis              | ai_analysis.html              | Dashboard de analise com IA                |
| /ui/v10                   | ui_v10_professional.html      | Interface profissional de copiloto IA      |
| /exceedance_analysis      | exceedance_analysis.html      | Analise de exceedance com apoio documental |

Paginas auxiliares:

- error_404.html e error_500.html para tratamento de erro.
- logbook_print.html para visualizacao de impressao.

## 4. APIs e Modulo de Analytics

O blueprint de analytics concentra uma camada extensa de APIs (mais de 100 rotas), incluindo:

- IA/Copilot: chat, resumo, explicacoes, feedback, recalibracao e contexto.
- Exceedance: analise, casos abertos, investigacoes, aprovacao e dashboard.
- Missao/Queue: fila de tarefas, priorizacao automatica e atualizacao em lote.
- Telemetria e logs: captura de eventos, resumo e limpeza.
- Qualidade de dados: normalizacao, validacao e metricas de qualidade.
- Frota e manutencao: risco, disponibilidade, backlog e inteligencia ATA.
- Saude do sistema: health, versao, changelog, cache e quality gates.

Exemplos de endpoints:

- /api/ai/chat
- /api/ai/analyze_failure
- /api/ai/exceedance/analyze
- /api/mission/queue
- /api/health
- /api/system/v12_health_gate

## 5. Ferramentas e Tecnologias

Backend e web:

- Python 3.13
- Flask 3
- Werkzeug
- Flask-CORS

Dados e persistencia:

- MySQL 8 (principal)
- PyMySQL
- Arquivos JSON fallback para resiliencia offline

Exportacao e documentos:

- openpyxl (Excel)
- pypdf (leitura de PDF)
- Geracao PDF simples para exportacao textual

Infra e execucao:

- Docker / Docker Compose
- Scripts de inicializacao para Windows (.bat e .ps1)

## 6. Estrutura Tecnica (Arquivos-chave)

- app.py: aplicacao Flask principal, autenticacao, paginas operacionais, uploads e handlers.
- routes_analytics.py: blueprint com analytics, IA, exceedance e APIs de suporte.
- ai_engine.py / ai_engine_v10_advanced.py / ai_engine_v10_utils.py: motores e utilitarios de IA.
- config.py: configuracoes centralizadas (seguranca, banco, upload, limites).
- Templates/: paginas HTML.
- static/: CSS, JS, icones e manifest.

## 7. Execucao Local (Windows)

Opcao 1 (recomendada):

1. Execute start_dev.bat.
2. O script cria venv, instala dependencias e inicia a aplicacao.
3. Acesse http://127.0.0.1:5050/login.

Opcao 2 (manual):

1. python -m venv venv
2. venv\Scripts\activate
3. python -m pip install --upgrade pip
4. pip install -r requirements_fullstack.txt
5. python app.py

## 8. Execucao com Docker

1. Configure variaveis no arquivo .env (opcional, recomendado).
2. Execute docker compose up --build.
3. Ajuste o mapeamento de portas para refletir a porta interna da aplicacao quando necessario.

## 9. Configuracao e Ambiente

Principais variaveis em config.py:

- FLASK_SECRET_KEY / SECRET_KEY
- MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
- FLEET_DB_NAME, MEL_DB_NAME, ETD_DB_NAME
- UPLOAD_FOLDER
- MAX_UPLOAD_MB
- ALLOWED_ATTACH_EXTENSIONS
- APP_LOG_LEVEL

## 10. Modo Fallback (Alta Disponibilidade Operacional)

Quando o MySQL falha ou fica indisponivel, o sistema usa arquivos locais JSON para manter operacao basica:

- users_fallback.json
- records_fallback.json
- tails_fallback.json
- mel_fallback.json
- aog_fallback.json
- etd_fallback.json
- lru_fallback.json

Isso permite continuidade do fluxo operacional, com sincronizacao posterior quando aplicavel.

## 11. Credenciais Iniciais (Fallback)

No modo fallback, usuarios padrao podem ser gerados automaticamente:

- admin / XXXX
- technician / XXXXX

Recomendacao: alterar senhas em ambiente real.

## 12. Observacoes de Seguranca

- Use segredo forte para FLASK_SECRET_KEY em producao.
- Restrinja extensoes de upload e tamanho maximo de arquivo.
- Evite uso de credenciais padrao em ambientes nao-locais.
- Utilize reverso/proxy e HTTPS em deploy produtivo.

---



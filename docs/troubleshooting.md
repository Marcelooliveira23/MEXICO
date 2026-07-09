# Guia de Troubleshooting – MXA

Este guia cobre os problemas mais comuns encontrados no sistema MXA e os passos recomendados para diagnóstico e resolução.

---

## Índice

1. [Falha na autenticação / acesso negado](#1-falha-na-autenticação--acesso-negado)
2. [Inconsistência nos registros de controle](#2-inconsistência-nos-registros-de-controle)
3. [Timeout ou lentidão no sistema](#3-timeout-ou-lentidão-no-sistema)
4. [Erros de integração com sistemas externos](#4-erros-de-integração-com-sistemas-externos)
5. [Falhas no processamento de relatórios](#5-falhas-no-processamento-de-relatórios)
6. [Problemas de sincronização de dados](#6-problemas-de-sincronização-de-dados)
7. [Alertas de auditoria inesperados](#7-alertas-de-auditoria-inesperados)

---

## 1. Falha na autenticação / acesso negado

**Sintomas:**
- Usuário não consegue fazer login no MXA.
- Mensagem "Acesso negado" ou "Credenciais inválidas".

**Diagnóstico:**

| Passo | Ação | Resultado esperado |
|-------|------|--------------------|
| 1 | Verificar se o usuário está ativo no diretório | Usuário com status `ATIVO` |
| 2 | Confirmar que as credenciais não expiraram | Data de expiração futura |
| 3 | Checar grupos e permissões do usuário | Grupo `MXA_USERS` ou superior presente |
| 4 | Analisar logs de autenticação | Sem bloqueio por tentativas repetidas |

**Resolução:**
- Se a conta estiver bloqueada: acionar o administrador de identidades para desbloqueio.
- Se as credenciais expiraram: solicitar reset via portal de autoatendimento.
- Se o grupo estiver ausente: abrir chamado para a equipe de IAM.

---

## 2. Inconsistência nos registros de controle

**Sintomas:**
- Diferença entre dados exibidos no painel e nos relatórios exportados.
- Registros duplicados ou ausentes.

**Diagnóstico:**
1. Confirmar o intervalo de datas utilizado em ambas as consultas.
2. Verificar se há carga de dados em andamento (jobs de ETL ativos).
3. Comparar os registros via consulta direta no banco de dados com o relatório exportado.
4. Checar o log de jobs de sincronização para erros recentes.

**Resolução:**
- Aguardar a conclusão dos jobs de ETL e atualizar a página.
- Se o problema persistir, acionar a equipe de dados para reprocessamento manual do intervalo afetado.
- Registrar a inconsistência no sistema de chamados com evidências (prints, logs).

---

## 3. Timeout ou lentidão no sistema

**Sintomas:**
- Páginas demoram mais de 30 segundos para carregar.
- Operações expiram com mensagem "Request Timeout".

**Diagnóstico:**
1. Verificar o status dos serviços no painel de monitoramento MXA.
2. Checar a utilização de CPU/memória dos servidores de aplicação.
3. Identificar se há consultas lentas no banco de dados (queries acima de 5 s).
4. Verificar se há pico de acessos simultâneos (horário de fechamento, auditorias).

**Resolução:**
- Em caso de pico pontual: orientar os usuários a tentar novamente após 5–10 minutos.
- Consultas lentas: encaminhar para a equipe de DBA para análise de índices.
- Degradação contínua: escalar para a equipe de infraestrutura com os logs de monitoramento.

---

## 4. Erros de integração com sistemas externos

**Sintomas:**
- Dados de sistemas parceiros (ERP, RH, Financeiro) não aparecem no MXA.
- Erros HTTP 4xx/5xx nos logs de integração.

**Diagnóstico:**

| Código | Causa provável | Próximo passo |
|--------|---------------|---------------|
| 401 / 403 | Token de integração expirado ou inválido | Renovar credenciais da integração |
| 404 | Endpoint alterado no sistema parceiro | Atualizar configuração do conector |
| 500 | Falha interna no sistema parceiro | Acionar suporte do sistema parceiro |
| Timeout | Rede ou sistema parceiro indisponível | Verificar conectividade e status do parceiro |

**Resolução:**
- Renovar tokens: acessar **Administração > Integrações > [Nome da integração] > Renovar token**.
- Atualizar endpoints: consultar a documentação da API do parceiro e atualizar em **Administração > Integrações > Configuração**.
- Para erros 500 persistentes: abrir chamado junto ao suporte do sistema parceiro com os logs de integração.

---

## 5. Falhas no processamento de relatórios

**Sintomas:**
- Relatório fica em status "Em processamento" por mais de 15 minutos.
- Relatório gerado com dados incompletos ou formato incorreto.

**Diagnóstico:**
1. Verificar o status do job de relatório em **Relatórios > Histórico**.
2. Checar os logs do serviço de relatórios para erros.
3. Confirmar que os filtros utilizados retornam dados quando testados diretamente.

**Resolução:**
- Cancelar o job travado e reenviar com um intervalo de dados menor.
- Se o formato estiver incorreto: verificar se houve atualização recente nos templates de relatório.
- Acionar a equipe de suporte com o ID do job e os parâmetros utilizados.

---

## 6. Problemas de sincronização de dados

**Sintomas:**
- Dados atualizados em sistemas-fonte não refletem no MXA após o prazo esperado.
- Registros com datas de última atualização desatualizadas.

**Diagnóstico:**
1. Verificar o painel de jobs de sincronização em **Administração > Sincronização**.
2. Checar se o job do período está com status `CONCLUÍDO`, `EM ANDAMENTO` ou `ERRO`.
3. Analisar os logs do job para identificar registros rejeitados.

**Resolução:**
- Job com erro: verificar a causa no log, corrigir os dados na fonte e reexecutar o job.
- Job travado: reiniciar o serviço de sincronização (acionar infraestrutura).
- Rejeição de registros: analisar regras de validação e corrigir os dados na fonte.

---

## 7. Alertas de auditoria inesperados

**Sintomas:**
- O sistema gerou um alerta de auditoria para uma ação que parece legítima.
- Notificações de auditoria enviadas para destinatários incorretos.

**Diagnóstico:**
1. Identificar o ID e o tipo do alerta em **Auditoria > Alertas**.
2. Verificar a regra de auditoria associada ao alerta.
3. Confirmar se a ação que disparou o alerta estava dentro dos parâmetros esperados.

**Resolução:**
- Alerta legítimo mas inesperado: documentar a justificativa no próprio alerta e fechar com status "Justificado".
- Regra muito abrangente: acionar o responsável pelo controle interno para revisão da regra.
- Destinatários incorretos: atualizar a configuração de notificação em **Auditoria > Configuração de Alertas**.

---

## Escalada e Contatos

| Nível | Quando escalar | Canal |
|-------|---------------|-------|
| Suporte N1 | Problemas com usuários, acesso, relatórios simples | Portal de chamados |
| Suporte N2 | Integrações, sincronização, lentidão persistente | Chamado com categoria "MXA – Técnico" |
| Suporte N3 | Corrupção de dados, falhas críticas de segurança | Contato direto com equipe MXA |

---

*Última atualização: 2026-07-09*

# Procedimentos de Controle Interno – MXA

Este documento descreve os procedimentos de controle interno aplicáveis ao sistema MXA, visando garantir a integridade, confiabilidade e conformidade das informações.

---

## Índice

1. [Objetivos do Controle Interno](#1-objetivos-do-controle-interno)
2. [Responsabilidades](#2-responsabilidades)
3. [Controles de Acesso](#3-controles-de-acesso)
4. [Controles de Dados](#4-controles-de-dados)
5. [Controles de Processos](#5-controles-de-processos)
6. [Controles de Auditoria](#6-controles-de-auditoria)
7. [Revisão Periódica dos Controles](#7-revisão-periódica-dos-controles)

---

## 1. Objetivos do Controle Interno

O controle interno do MXA tem como objetivos:

- **Integridade dos dados:** garantir que as informações registradas sejam precisas, completas e não adulteradas.
- **Conformidade:** assegurar que os processos estejam em conformidade com políticas internas e regulamentações aplicáveis.
- **Disponibilidade:** garantir que o sistema esteja disponível para os usuários autorizados conforme acordos de nível de serviço (SLA).
- **Segurança:** proteger os dados contra acessos não autorizados e vazamentos.
- **Rastreabilidade:** manter trilha de auditoria completa para todas as operações críticas.

---

## 2. Responsabilidades

| Papel | Responsabilidade |
|-------|-----------------|
| Gestor de Controle Interno | Definir, revisar e aprovar os controles. Acompanhar indicadores. |
| Administrador do Sistema MXA | Implementar controles técnicos, gerenciar acessos, monitorar logs. |
| Usuários | Utilizar o sistema conforme as políticas e reportar anomalias. |
| Auditoria Interna | Verificar a eficácia dos controles. Conduzir revisões periódicas. |
| TI / Infraestrutura | Garantir disponibilidade, backup e segurança da infraestrutura. |

---

## 3. Controles de Acesso

### 3.1 Princípio do Menor Privilégio

- Cada usuário recebe apenas as permissões necessárias para executar suas funções.
- Perfis de acesso devem ser revisados a cada **6 meses** ou em caso de mudança de função.

### 3.2 Autenticação

- Autenticação multifator (MFA) é **obrigatória** para todos os usuários com acesso ao MXA.
- Senhas devem seguir a política corporativa: mínimo de 12 caracteres, complexidade obrigatória, expiração em 90 dias.

### 3.3 Gestão de Acessos

- Solicitações de acesso devem ser aprovadas pelo gestor do usuário e pelo Administrador do MXA.
- Desligamentos e transferências devem resultar em revogação imediata do acesso (prazo máximo: 24 horas após o comunicado de RH).
- Acessos de emergência ("break glass") devem ser registrados, justificados e revisados em até 48 horas.

### 3.4 Contas de Serviço

- Contas de serviço devem ser documentadas com responsável definido.
- Credenciais de contas de serviço devem ser rotacionadas a cada **90 dias**.
- Contas de serviço não devem ser utilizadas por usuários humanos.

---

## 4. Controles de Dados

### 4.1 Integridade

- Todas as alterações em dados críticos devem ser registradas em log de auditoria com: usuário, data/hora, valor anterior e valor posterior.
- Dados importados de sistemas externos passam por validação de integridade antes de serem incorporados ao MXA.

### 4.2 Backup e Recuperação

- Backups completos são realizados **diariamente**, com retenção de **30 dias**.
- Backups incrementais são realizados a cada **4 horas**.
- Testes de restauração devem ser executados **mensalmente** e documentados.

### 4.3 Retenção de Dados

- Dados transacionais são retidos por **7 anos** conforme exigência regulatória.
- Logs de auditoria são retidos por **5 anos**.
- Dados pessoais são tratados conforme a política de privacidade e LGPD.

---

## 5. Controles de Processos

### 5.1 Segregação de Funções

- As funções de **cadastro**, **aprovação** e **auditoria** devem ser exercidas por usuários distintos.
- Nenhum usuário pode ter simultaneamente permissões de criar e aprovar a mesma transação.

### 5.2 Aprovações e Alçadas

| Tipo de operação | Alçada necessária |
|-----------------|-------------------|
| Cadastro de novo fornecedor | Gestor de área + Compliance |
| Alteração de limite financeiro | Diretor financeiro |
| Exclusão de registros históricos | Gestor de Controle Interno |
| Criação de conta de administrador | TI + Gestor de Controle Interno |

### 5.3 Reconciliação

- Reconciliações entre MXA e sistemas parceiros devem ser executadas **mensalmente**.
- Divergências identificadas devem ser documentadas, investigadas e resolvidas em até **15 dias úteis**.

---

## 6. Controles de Auditoria

### 6.1 Trilha de Auditoria

- O MXA mantém trilha de auditoria automática para todas as operações de criação, edição e exclusão.
- A trilha de auditoria é imutável: nenhum usuário, incluindo administradores, pode alterar ou excluir registros de auditoria.

### 6.2 Monitoramento Contínuo

- Alertas automáticos são configurados para:
  - Acessos fora do horário comercial.
  - Tentativas de acesso a dados sensíveis.
  - Múltiplas falhas de autenticação.
  - Operações em volume acima do padrão histórico.

### 6.3 Revisões de Auditoria

- Revisões de acesso são realizadas **semestralmente** pela Auditoria Interna.
- Revisões de configurações de segurança são realizadas **anualmente**.
- Resultados das revisões são reportados à Diretoria.

---

## 7. Revisão Periódica dos Controles

### 7.1 Calendário de Revisões

| Controle | Frequência | Responsável |
|----------|-----------|-------------|
| Revisão de acessos | Semestral | Administrador MXA + Gestor |
| Teste de backup/recuperação | Mensal | TI / Infraestrutura |
| Reconciliação de dados | Mensal | Gestor de Controle Interno |
| Revisão de regras de auditoria | Anual | Auditoria Interna |
| Atualização desta documentação | Anual ou por mudança relevante | Gestor de Controle Interno |

### 7.2 Indicadores de Desempenho (KPIs)

- **% de acessos revisados no prazo:** meta ≥ 95%.
- **Tempo médio de revogação de acesso:** meta ≤ 24 horas.
- **Divergências de reconciliação resolvidas no prazo:** meta ≥ 90%.
- **Disponibilidade do sistema:** meta ≥ 99,5% mensal.
- **Testes de backup bem-sucedidos:** meta = 100%.

---

*Última atualização: 2026-07-09*

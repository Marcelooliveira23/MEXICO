# Checklists de Verificação – MXA

Use estes checklists durante auditorias, revisões periódicas e troubleshooting do sistema MXA.

---

## Checklist 1 – Revisão de Acessos (Semestral)

**Período de referência:** ___/___/______ a ___/___/______  
**Responsável:** ______________________  
**Data de execução:** ___/___/______

- [ ] Listar todos os usuários ativos no MXA.
- [ ] Confirmar que cada usuário possui gestor responsável identificado.
- [ ] Verificar se usuários com mudança de função tiveram perfis de acesso atualizados.
- [ ] Verificar se ex-funcionários tiveram acesso revogado (prazo máximo 24 h após desligamento).
- [ ] Confirmar que nenhum usuário possui acumulação indevida de privilégios (segregação de funções).
- [ ] Revisar contas de serviço: documentação atualizada e credenciais rotacionadas nos últimos 90 dias.
- [ ] Verificar se contas administrativas possuem MFA ativo.
- [ ] Documentar e justificar exceções encontradas.
- [ ] Encaminhar relatório de revisão para o Gestor de Controle Interno.

**Observações:** ______________________________________________________

---

## Checklist 2 – Teste de Backup e Recuperação (Mensal)

**Mês de referência:** ___/______  
**Responsável:** ______________________  
**Data de execução:** ___/___/______

- [ ] Confirmar que o backup completo do dia anterior foi concluído com sucesso.
- [ ] Verificar logs de backup incremental das últimas 24 horas (sem erros).
- [ ] Selecionar um conjunto de dados para teste de restauração (registros aleatórios).
- [ ] Executar a restauração em ambiente de homologação/isolado.
- [ ] Validar a integridade dos dados restaurados (comparação com dados de origem).
- [ ] Registrar o tempo de restauração.
- [ ] Documentar o resultado (sucesso / falha / parcial) com evidências.
- [ ] Em caso de falha: abrir chamado de prioridade alta para a equipe de infraestrutura.

**Resultado da restauração:** [ ] Sucesso  [ ] Falha  [ ] Parcial  
**Observações:** ______________________________________________________

---

## Checklist 3 – Reconciliação de Dados (Mensal)

**Mês de referência:** ___/______  
**Responsável:** ______________________  
**Data de execução:** ___/___/______

- [ ] Exportar os totais de registros do MXA para o período.
- [ ] Exportar os totais de registros dos sistemas-fonte para o mesmo período.
- [ ] Comparar os totais: MXA vs. sistemas-fonte.
- [ ] Identificar e listar todas as divergências encontradas.
- [ ] Para cada divergência: classificar como (erro de dados / atraso de sincronização / item em disputa).
- [ ] Registrar as divergências no sistema de chamados.
- [ ] Confirmar que divergências do mês anterior foram resolvidas dentro do prazo (15 dias úteis).
- [ ] Encaminhar relatório de reconciliação para o Gestor de Controle Interno.

**Total de divergências encontradas:** ______  
**Total resolvidas no prazo (mês anterior):** ______  
**Observações:** ______________________________________________________

---

## Checklist 4 – Troubleshooting Inicial (Incidente)

**Data/hora do incidente:** ___/___/______ __:____  
**Responsável pelo atendimento:** ______________________  
**Descrição do problema:** ______________________________________________________

### Diagnóstico rápido

- [ ] Identificar o(s) usuário(s) afetado(s).
- [ ] Identificar o módulo/funcionalidade afetada.
- [ ] Verificar se outros usuários estão sendo afetados (problema isolado ou sistêmico).
- [ ] Consultar o painel de monitoramento do MXA para alertas ativos.
- [ ] Verificar logs de aplicação para erros recentes.
- [ ] Verificar se houve atualização ou manutenção recente no sistema.
- [ ] Verificar status dos serviços integrados (ERP, RH, Financeiro).

### Classificação do incidente

- [ ] **Baixo:** afeta um usuário, sem impacto em processos críticos → Suporte N1
- [ ] **Médio:** afeta múltiplos usuários ou processo crítico pontual → Suporte N2
- [ ] **Alto:** indisponibilidade total ou risco à integridade dos dados → Suporte N3 / Gestão

### Ações imediatas

- [ ] Comunicar os usuários afetados com previsão de resolução.
- [ ] Registrar o incidente no sistema de chamados com: descrição, impacto, hora de início.
- [ ] Acionar o nível de suporte adequado conforme classificação acima.
- [ ] Consultar [`docs/troubleshooting.md`](troubleshooting.md) para orientações específicas.

**Número do chamado aberto:** ______________________  
**Observações:** ______________________________________________________

---

## Checklist 5 – Auditoria de Segurança (Anual)

**Ano de referência:** ______  
**Responsável:** ______________________  
**Data de execução:** ___/___/______

### Controles de acesso

- [ ] Revisar e atualizar a matriz de perfis de acesso.
- [ ] Confirmar que MFA está ativo para 100% dos usuários.
- [ ] Verificar se a política de senha está sendo aplicada corretamente.
- [ ] Revisar contas de acesso de emergência ("break glass") e seus registros de uso.

### Configurações de segurança

- [ ] Verificar configurações de timeout de sessão (máximo recomendado: 30 minutos de inatividade).
- [ ] Confirmar que logs de auditoria são imutáveis e estão sendo retidos conforme política (5 anos).
- [ ] Verificar se os alertas de monitoramento contínuo estão ativos e configurados corretamente.
- [ ] Confirmar que comunicações com sistemas externos utilizam criptografia (TLS 1.2+).

### Testes

- [ ] Tentar acessar dados de outro perfil com usuário de perfil inferior (verificar negação de acesso).
- [ ] Tentar alterar registro e confirmar que a trilha de auditoria foi gerada corretamente.
- [ ] Simular tentativas de login com credenciais inválidas e confirmar geração de alerta.

### Documentação

- [ ] Atualizar documentação de controle interno (`docs/controle-interno.md`) se necessário.
- [ ] Registrar exceções identificadas com plano de remediação e prazo.
- [ ] Elaborar relatório final e encaminhar para a Diretoria.

**Observações:** ______________________________________________________

---

*Última atualização: 2026-07-09*

# POP-D05 — Registrar Baixa de Entrega

**Categoria**: D — Operacional: Transporte e Entrega
**Prioridade**: P1 (Alta — fecha ciclo operacional)
**Status**: PARCIAL
**Executor Atual**: Rafael (dependente de parceiros)
**Executor Futuro**: Stephanie
**Versão**: 1.0
**Data**: 2026-02-16
**Autor**: Claude (Agente Logístico)

---

## Objetivo

Registrar a baixa de entregas realizadas, confirmando a entrega ao destinatário ou registrando ocorrências que impedem a conclusão. Este processo fecha o ciclo operacional do CTRC, atualiza o status no sistema SSW e permite faturamento/cobrança.

---

## Trigger

- Retorno do motorista/veículo com comprovantes de entrega
- Notificação do parceiro regional informando entregas realizadas
- Final do dia (REGRA SSW: todos CTRCs de Romaneios do dia anterior devem receber ocorrência)
- Consulta de CTRCs pendentes via Relatório 011 (Atrasados)

---

## Frequência

**Diária**:
- Manhã: Verificar entregas do dia anterior (Relatório 011)
- Tarde: Registrar baixas conforme retorno de motoristas/parceiros
- Fim do dia: Garantir que NENHUM Romaneio do dia anterior reste sem baixa

**Ad-hoc**: Quando parceiro informar entrega concluída

---

## Pré-requisitos

1. **Romaneio de Entrega emitido** (Opção 037) com CTRCs alocados
2. **Acesso ao SSW** com perfil operacional na unidade destinatária (CAR ou parceiro tipo T)
3. **Comprovante de entrega** (assinado pelo recebedor) OU informações da ocorrência (se entrega não concluída)
4. **Tabela de Ocorrências** (Opção 405) configurada com códigos padrão
5. **SSWMobile** (recomendado): parceiro com app instalado para baixa em tempo real

---

## Passo-a-Passo

### ETAPA 1: Acessar Registro de Baixa
1. Logar no SSW com usuário operacional da unidade destinatária
2. Acessar **[Opção 038](../operacional/038-baixa-entregas-ocorrencias.md) — Registrar Baixa de Entregas**
3. Sistema exibe menu com 8 formas de baixa

### ETAPA 2: Escolher Forma de Baixa

**Opção A — Por Romaneio (MAIS COMUM):**
1. Selecionar "1 — Baixa por Romaneio"
2. Informar número do Romaneio de Entrega
3. Sistema exibe lista de CTRCs do Romaneio
4. Selecionar CTRCs entregues (checkbox individual ou "Marcar Todos")

**Opção B — Código de Barras (RECOMENDADO se SSWBar disponível):**
1. Selecionar "3 — Baixa por Código de Barras"
2. Fazer leitura do código de barras no CTRC ou canhoto
3. Sistema localiza CTRC e abre tela de baixa

**Opção C — Digitação Manual:**
1. Selecionar "4 — Digitação de CTRC"
2. Informar Série + Número do CTRC
3. Sistema localiza CTRC e abre tela de baixa

**Opção D — CTRCs Pendentes (ÚTIL para final do dia):**
1. Selecionar "7 — CTRCs Pendentes de Baixa"
2. Sistema exibe CTRCs sem baixa (filtro por data/Romaneio)
3. Selecionar CTRCs e processar baixa em lote

### ETAPA 3: Preencher Dados da Baixa

**Campos Obrigatórios:**
1. **Ocorrência**: Selecionar código da tabela [405](../cadastros/405-tabela-ocorrencias.md)
   - Entrega normal: código padrão "01 — Entregue" (ou similar conforme cadastro CarVia)
   - Entrega com problema: código específico (ex: "10 — Destinatário Ausente", "15 — Recusa", etc.)
2. **Data/Hora da Ocorrência**: Preencher com data/hora real da entrega (ou tentativa)

**Campos Condicionais:**
3. **Odômetro** (se habilitado em 903/Operação): Informar KM do veículo na entrega
4. **Receber Frete** (se CTRC com frete a receber):
   - Valor recebido em espécie
   - Forma de pagamento (dinheiro, cheque, PIX, etc.)
5. **Dados do Recebedor** (se entrega concluída):
   - Nome completo
   - CPF ou RG
   - Assinatura (digitalizada se SSWMobile, ou anexar comprovante físico)

**Campos de Controle de Estadias** (se habilitado em 903/Operação):
6. **Hora Chegada no Cliente**: Hora que veículo chegou no local de entrega
7. **Hora Saída do Cliente**: Hora que veículo deixou o local
8. **Gerar CTRC Complementar**: Se estadia exceder limite, sistema gera CTRC automaticamente

### ETAPA 4: Validar e Confirmar
1. Revisar dados preenchidos (especialmente ocorrência e dados do recebedor)
2. Verificar se CTRC possui MDF-e vinculado (sistema encerra MDF-e automaticamente)
3. Clicar em **Confirmar** ou pressionar **F10**
4. Sistema atualiza status do CTRC:
   - Ocorrência finalizadora (ex: "Entregue") → CTRC baixado, liberado para faturamento
   - Ocorrência não-finalizadora (ex: "Ausente") → CTRC pendente, aguarda instrução (ver POP-D06, [Opção 108](../operacional/108-ocorrencias-entrega.md))

### ETAPA 5: Processar Romaneios Itinerantes (se aplicável)
1. Se Romaneio do tipo **Itinerante** (múltiplas entregas no mesmo veículo):
2. Após baixar TODOS os CTRCs, registrar **Retorno do Veículo** (botão específico na Opção 038)
3. Sistema fecha Romaneio e libera veículo para novo Romaneio

### ETAPA 6: Verificar CTRC de Reentrega Automática (se habilitado)
1. Se configurado em **[Opção 423](../comercial/423-parametros-comerciais-cliente.md) — CTRC Reentrega Automática**:
2. Ao registrar ocorrência não-finalizadora (ex: "Ausente"), sistema gera novo CTRC automaticamente
3. Verificar se CTRC de reentrega foi criado (mesmo remetente/destinatário, nova série)

### ETAPA 7: Estornar Baixa (se necessário)
1. Se baixa foi registrada incorretamente:
2. Acessar **[Opção 138](../comercial/138-estorno-baixa-entrega.md) — Estornar Baixa de Entrega**
3. Informar CTRC e justificativa
4. Sistema reverte status do CTRC para pendente

---

## Contexto CarVia

| Aspecto | Hoje | Futuro (Pós-Implantação POP) |
|---------|------|------------------------------|
| **Executor da Baixa** | **Parceiros regionais** (unidades tipo T no SSW). Rafael atualiza manualmente quando parceiro informa OU parceiro dá baixa direto (se usar SSW). | **Stephanie monitora baixas diariamente**. Cobra parceiros que não baixaram CTRCs no prazo (D+1). Rafael só escala em casos críticos. |
| **Ferramentas** | Manual (Opção 038) ou dependente do sistema do parceiro | **SSWMobile** recomendado para parceiros (baixa em tempo real). Stephanie usa Opção 038 para baixas da própria CarVia (se houver entrega direta). |
| **Monitoramento** | Ad-hoc. Rafael só verifica quando cliente reclama ou parceiro avisa. | **Relatório 011** (CTRCs Atrasados) consultado DIARIAMENTE por Stephanie. Meta: 0 CTRCs > D+2 sem baixa. |
| **Ocorrências Pendentes** | CTRCs com ocorrência não-finalizadora ficam "esquecidos". Sem rotina de cobrança de instrução. | Stephanie usa **[Opção 108](../operacional/108-ocorrencias-entrega.md)** (Instruções para Ocorrências) DIARIAMENTE. Cobra parceiro/cliente por instrução. Escala para Rafael se > 3 dias sem resposta. |
| **Controle de Estadias** | Não habilitado (903/Operação). Sem cobrança de estadia extra. | **Habilitar controle** em 903/Operação. CTRC Complementar automático se estadia > 2h (limite a definir). Receita adicional. |
| **CTRC Reentrega** | Não habilitado ([423](../comercial/423-parametros-comerciais-cliente.md)). Reentregas geram CTRC manual (trabalho dobrado). | **Habilitar [Opção 423](../comercial/423-parametros-comerciais-cliente.md)**. Reentrega automática economiza tempo e reduz erro de digitação. |
| **SLA de Baixa** | Sem SLA. Parceiros baixam quando querem. | **SLA: D+1** (baixa até fim do dia seguinte à entrega). Stephanie cobra parceiros fora do SLA. Indicador mensal: % CTRCs baixados no prazo. |

---

## Erros Comuns e Soluções

| Erro | Causa Provável | Solução |
|------|----------------|---------|
| CTRC não aparece na lista ([Opção 038](../operacional/038-baixa-entregas-ocorrencias.md)) | CTRC não alocado em Romaneio OU baixa já registrada OU unidade incorreta | 1. Verificar se CTRC foi incluído em Romaneio (Opção 037). 2. Consultar histórico do CTRC (Opção 057) para ver status. 3. Validar se usuário logado está na unidade destinatária. |
| Sistema não aceita ocorrência selecionada | Ocorrência bloqueada para envio EDI (configuração 943) OU ocorrência inativa | 1. Verificar **Opção 943** (Liberar Ocorrências Finalizadoras para EDI) — desbloquear se necessário. 2. Consultar **[Opção 405](../cadastros/405-tabela-ocorrencias.md)** (Tabela de Ocorrências) — verificar se código está ativo. |
| Dados do recebedor obrigatórios mas sem informação | CTRC entregue mas recebedor não identificado (portaria, vizinho, etc.) | 1. Solicitar ao motorista/parceiro SEMPRE coletar nome+CPF/RG. 2. Se impossível: registrar "Portaria" ou "Responsável no Local" + observação no campo livre. |
| MDF-e não encerra automaticamente | MDF-e vinculado a Romaneio não baixado completamente OU erro de comunicação SEFAZ | 1. Verificar se TODOS os CTRCs do Romaneio receberam baixa. 2. Se sim e MDF-e não encerrou: acessar **Opção de Gestão MDF-e** (2XX) e encerrar manualmente. |
| Controle de Estadias não gera CTRC Complementar | Controle desabilitado OU limite de tempo não excedido OU configuração incorreta | 1. Habilitar controle em **903/Operação**. 2. Configurar tempo limite (ex: 2h). 3. Preencher corretamente hora chegada/saída. |
| Estorno de baixa não permitido | Período de faturamento fechado OU baixa com integração EDI já enviada | 1. Verificar período contábil (Opção 9XX). 2. Se fechado: solicitar reabertura ao financeiro. 3. Se EDI enviado: contatar suporte SSW para procedimento especial. Use [Opção 138](../comercial/138-estorno-baixa-entrega.md) para estorno. |
| CTRCs pendentes não aparecem (Opção 038-7) | Filtro de data incorreto OU todos CTRCs já baixados | 1. Ajustar filtro de data (ampliar período). 2. Usar **Relatório 011** (Atrasados) como referência — lista CTRCs > X dias sem baixa. |

---

## Verificação Playwright

| ID | Verificação | Seletor/Ação | Resultado Esperado |
|----|-------------|--------------|-------------------|
| V1 | Acessar Opção 038 | `click('text=038')` ou navegação por menu | Tela "Registrar Baixa de Entregas" exibida com 8 formas de baixa |
| V2 | Selecionar baixa por Romaneio | `click('text=1 — Baixa por Romaneio')` | Campo "Número do Romaneio" habilitado |
| V3 | Informar Romaneio (exemplo: 12345) | `fill('input[name="numeroRomaneio"]', '12345')` + Enter | Lista de CTRCs do Romaneio 12345 exibida |
| V4 | Marcar CTRC para baixa (exemplo: primeiro da lista) | `click('table tbody tr:first-child input[type="checkbox"]')` | Checkbox marcado, CTRC selecionado |
| V5 | Preencher ocorrência (exemplo: "01 — Entregue") | `selectOption('select[name="ocorrencia"]', '01')` | Ocorrência "01 — Entregue" selecionada |
| V6 | Preencher data/hora | `fill('input[name="dataHoraOcorrencia"]', '16/02/2026 14:30')` | Data/hora preenchida (formato SSW: DD/MM/YYYY HH:MM) |
| V7 | Preencher nome recebedor | `fill('input[name="nomeRecebedor"]', 'João Silva')` | Nome "João Silva" preenchido |
| V8 | Preencher CPF recebedor | `fill('input[name="cpfRecebedor"]', '123.456.789-00')` | CPF preenchido (validar máscara) |
| V9 | Confirmar baixa | `click('button:has-text("Confirmar")')` ou `press('F10')` | Mensagem "Baixa registrada com sucesso" OU retorno à lista com CTRC removido |
| V10 | Verificar status do CTRC | Consultar Opção 057 e buscar CTRC baixado | Status = "Entregue" ou "Baixado" (conforme ocorrência) |
| V11 | Verificar CTRCs pendentes (Relatório 011) | Acessar Relatório 011 e filtrar por unidade CAR | CTRC baixado NÃO aparece na lista de atrasados |

**Notas de Automação**:
- Validar campos obrigatórios: `expect(page.locator('input[name="ocorrencia"]')).toBeVisible()` e `toBeRequired()`
- Aguardar carregamento de CTRCs após informar Romaneio: `page.waitForSelector('table tbody tr')`
- Capturar mensagens de erro: `page.locator('.mensagem-erro').textContent()` para debug

---

## POPs Relacionados

| POP | Título | Relação |
|-----|--------|---------|
| POP-D03 | Emitir Romaneio de Entrega (Opção 037) | **Pré-requisito**: Romaneio deve ser emitido antes da baixa |
| POP-D04 | Registrar Chegada de Veículo (Opção 030) | **Sequencial**: Após chegada de transferência, CTRCs são entregues e recebem baixa |
| POP-D06 | Registrar Ocorrências | **Condicional**: Se baixa com ocorrência não-finalizadora, seguir POP-D06 para instruções |
| POP-M03 | Consultar CTRCs Atrasados (Relatório 011) | **Suporte**: Usado diariamente para identificar CTRCs sem baixa no prazo |
| POP-F05 | Estornar Baixa (Opção 138) | **Correção**: Usado quando baixa foi registrada incorretamente |
| POP-C09 | Configurar Tabela de Ocorrências (Opção 405) | **Cadastro**: Define códigos de ocorrência usados na baixa |

---

## Histórico de Revisões

| Versão | Data | Autor | Alterações |
|--------|------|-------|------------|
| 1.0 | 2026-02-16 | Claude (Agente Logístico) | Criação inicial do POP. Status: PARCIAL — hoje baixa feita por parceiros sem monitoramento sistemático. Futuro: Stephanie assume monitoramento diário com SLA D+1 e cobrança proativa. |

# POP-F04 — Conciliar Banco

**Categoria**: F — Financeiro: Pagaveis
**Prioridade**: P1 (Alta)
**Status**: A IMPLANTAR
**Executor Atual**: Rafael (fora do SSW)
**Executor Futuro**: Jaqueline
**Data Criacao**: 2026-02-16
**Autor**: Claude (Agente Logistico)

---

## Objetivo

Controlar e validar movimentacoes financeiras comparando saldo do sistema SSW com saldo do extrato bancario, bloqueando alteracoes retroativas em periodos conciliados para garantir integridade contabil. Pre-requisito OBRIGATORIO para uso da contabilidade do SSW pela contabilidade externa.

---

## Trigger

- **Fim do dia util**: Conciliar saldo D+0 (recomendado para controle rigoroso)
- **Fim da semana**: Conciliar saldo da sexta-feira (minimo aceitavel)
- **Fim do mes**: Conciliar saldo do ultimo dia util (OBRIGATORIO para fechamento contabil 559/567)
- **Apos transferencias entre contas**: Conciliar ambas as contas envolvidas
- **Apos liquidacao de cheques**: Conciliar conta emissora
- **Antes de entrega contabil**: Garantir periodo fechado e bloqueado

---

## Frequencia

- **Ideal**: Diaria (ao final do expediente)
- **Minima aceitavel**: Semanal (sextas-feiras)
- **OBRIGATORIA**: Mensal (ultimo dia util do mes, antes do fechamento 559)

**Recomendacao CarVia**: Iniciar com frequencia semanal (sextas) ate ganhar confianca, depois migrar para diaria.

---

## Pre-requisitos

### Sistema
1. **Conta bancaria cadastrada** ([opcao 904](../cadastros/904-bancos-contas-bancarias.md)) com banco/agencia/conta/carteira configurados
2. **Plano de contas configurado** ([opcao 540](../contabilidade/540-plano-de-contas.md)) com sequencias padrao:
   - Seq 11: Banco Conta Movimento (complemento: BANCO+CARTEIRA)
   - Seq 17: Cheques a Pagar
   - Seq 63: Banco Conta Movimento (alternativa seq 11)
   - Seq 82: Adiantamentos/Creditos Nao Identificados
3. **Lancamentos automaticos configurados** ([opcao 541](../contabilidade/541-lancamentos-automaticos.md)) para contabilizacao de:
   - Compensacao de cheques ([456](../financeiro/456-conta-corrente.md))
   - Transferencias entre contas ([456](../financeiro/456-conta-corrente.md))
   - Liquidacoes de cobranca bancaria (444)
   - Despesas extras ([475](../financeiro/475-contas-a-pagar.md))
4. **Movimentacoes conciliadas** via [opcao 456](../financeiro/456-conta-corrente.md) (Extrato Bancario):
   - Cheques compensados
   - Transferencias entre contas
   - Tarifas bancarias
5. **Creditos nao identificados lancados** via [opcao 571](../financeiro/571-acni-adiantamento-credito-nao-identificado.md) (Razao Contabil):
   - Depositos sem origem conhecida (seq 82)

### Operacional
- **Extrato bancario disponivel** (internet banking ou agencia)
- **Todas as movimentacoes do dia lancadas** no SSW (pagamentos, recebimentos, transferencias)
- **Nenhuma pendencia de conferencia** (ex: cheques emitidos mas nao compensados)

### Pessoas
- Jaqueline treinada em opcoes [456](../financeiro/456-conta-corrente.md), [569](../financeiro/569-conciliacao-bancaria.md), [571](../financeiro/571-acni-adiantamento-credito-nao-identificado.md)
- Rafael como backup
- Contato com gerente do banco para esclarecimento de movimentacoes

---

## Passo-a-Passo

### ETAPA 1: Obter Extrato Bancario
1. Acessar internet banking ou solicitar extrato na agencia
2. Baixar extrato do periodo a conciliar (ex: D-1 se conciliacao diaria)
3. Anotar **saldo final** do extrato (este sera o "saldo conciliado")
4. Identificar movimentacoes:
   - **Debitos**: pagamentos, tarifas, transferencias saida, cheques compensados
   - **Creditos**: recebimentos, transferencias entrada, depositos

### ETAPA 2: Conciliar Cheques Compensados (Opcao 456)
**IMPORTANTE**: Fazer ANTES de conciliar saldo via [569](../financeiro/569-conciliacao-bancaria.md)

1. Acessar menu: **Financeiro > Contas a Pagar > Extrato Bancario ([456](../financeiro/456-conta-corrente.md))**
2. Selecionar **banco/agencia/conta/carteira**
3. Informar **periodo** da conciliacao
4. Aba **Cheques**:
   - Marcar cheques que aparecem compensados no extrato bancario
   - Sistema contabiliza automaticamente:
     - **Credito** seq 11 (Banco Conta Movimento)
     - **Debito** seq 17 (Cheques a Pagar)
5. Clicar **Salvar**
6. **CHECKPOINT**: Total de cheques compensados no SSW = Total de cheques no extrato

### ETAPA 3: Conciliar Transferencias Entre Contas (Opcao 456)
**IMPORTANTE**: Fazer ANTES de conciliar saldo via [569](../financeiro/569-conciliacao-bancaria.md)

1. Ainda na [opcao **456**](../financeiro/456-conta-corrente.md) (Extrato Bancario)
2. Aba **Transferencias**:
   - Informar transferencias saida (debito) e entrada (credito)
   - Preencher campos:
     - **Conta origem** / **Conta destino**
     - **Valor**
     - **Data**
     - **Historico** (ex: "Transferencia para conta corrente")
   - Sistema contabiliza automaticamente:
     - Conta origem: **Credito** seq 63/11, **Debito** seq 63/11
     - Conta destino: **Credito** seq 63/11, **Debito** seq 63/11
3. Clicar **Salvar**
4. **CHECKPOINT**: Total transferencias no SSW = Total transferencias no extrato

### ETAPA 4: Conciliar Tarifas Bancarias (Opcao 456)
**IMPORTANTE**: Fazer ANTES de conciliar saldo via [569](../financeiro/569-conciliacao-bancaria.md)

1. Ainda na [opcao **456**](../financeiro/456-conta-corrente.md) (Extrato Bancario)
2. Aba **Tarifas**:
   - Informar tarifas que aparecem no extrato (ex: tarifa manutencao conta, DOC, TED)
   - Preencher campos:
     - **Valor**
     - **Data**
     - **Historico** (ex: "Tarifa manutencao conta")
     - **Sequencia contabil** (ex: seq 63 para debito em Banco Conta Movimento)
3. Clicar **Salvar**
4. **CHECKPOINT**: Total tarifas no SSW = Total tarifas no extrato

### ETAPA 5: Lancar Creditos Nao Identificados (Opcao 571)
**APENAS se houver depositos/creditos sem origem conhecida**

1. Acessar menu: **Contabilidade > Razao Contabil ([571](../financeiro/571-acni-adiantamento-credito-nao-identificado.md))**
2. Clicar **Novo Lancamento**
3. Preencher:
   - **Data**: data do deposito no extrato
   - **Historico**: "Deposito nao identificado — verificar origem"
   - **Credito**: seq 82 (Adiantamentos/Creditos Nao Identificados)
   - **Debito**: seq 63/11 (Banco Conta Movimento)
   - **Valor**: valor exato do deposito
   - **Complemento**: BANCO+CARTEIRA (ex: "001-0001234-5")
4. Clicar **Salvar**
5. **Acao futura**: Investigar origem do deposito e reclassificar (ex: pagamento de cliente)

### ETAPA 6: Calcular Saldo Esperado no SSW
**ANTES de acessar opcao [569](../financeiro/569-conciliacao-bancaria.md)**

1. Anotar saldo anterior conciliado (ultima conciliacao via [569](../financeiro/569-conciliacao-bancaria.md))
2. Somar movimentacoes de credito (recebimentos, depositos, transferencias entrada)
3. Subtrair movimentacoes de debito (pagamentos, tarifas, transferencias saida, cheques compensados)
4. **Saldo esperado SSW** = Saldo anterior + Creditos - Debitos
5. **CHECKPOINT CRITICO**: Saldo esperado SSW = Saldo final extrato bancario
   - **Se divergir**: PARAR e investigar antes de conciliar (ver ETAPA 9)

### ETAPA 7: Executar Conciliacao Bancaria (Opcao 569)
**APENAS se saldo SSW = saldo extrato (checkpoint ETAPA 6 passou)**

1. Acessar menu: **Contabilidade > Conciliacao Bancaria ([569](../financeiro/569-conciliacao-bancaria.md))**
2. Informar:
   - **Banco/Agencia/Conta/Carteira**: selecionar conta a conciliar
   - **Data conciliacao**: data do saldo final do extrato (ex: 2026-02-15)
   - **Saldo conciliado**: saldo final do extrato bancario (valor EXATO)
3. Clicar **Confirmar**
4. Sistema valida:
   - Compara saldo informado com saldo calculado do SSW
   - Se divergir: exibe mensagem de erro e NAO concilia
   - Se bater: concilia e **BLOQUEIA** periodo
5. **Mensagem de sucesso**: "Conciliacao realizada com sucesso. Periodo bloqueado."

### ETAPA 8: Validar Bloqueios Automaticos
**Apos conciliar via [569](../financeiro/569-conciliacao-bancaria.md), testar bloqueios:**

1. Tentar cancelar CTRB/OS em data conciliada (opcao 074):
   - Sistema deve IMPEDIR e exibir mensagem "Periodo conciliado — alteracao bloqueada"
2. Tentar lancar despesa manual em data conciliada ([opcao 558](../contabilidade/558-lancamentos-manuais.md)):
   - Sistema deve IMPEDIR e exibir mensagem "Periodo conciliado — alteracao bloqueada"
3. Tentar alterar despesa em data conciliada ([opcao 475](../financeiro/475-contas-a-pagar.md)):
   - Sistema deve IMPEDIR e exibir mensagem "Periodo conciliado — alteracao bloqueada"

### ETAPA 9: Investigar Divergencias (Se Checkpoint ETAPA 6 Falhou)
**NUNCA conciliar com divergencia — sempre investigar antes**

1. Acessar [opcao **571**](../financeiro/571-acni-adiantamento-credito-nao-identificado.md) (Razao Contabil)
2. Filtrar por conta (seq 11 ou 63) e periodo
3. Comparar lancamentos SSW vs extrato bancario:
   - **Lancamento no SSW mas NAO no extrato**: possivel erro de data, cheque nao compensado, transferencia nao processada
   - **Lancamento no extrato mas NAO no SSW**: possivel tarifa nao lancada, deposito nao identificado, debito automatico nao previsto
4. Corrigir divergencias:
   - Lancar movimentacao faltante ([456](../financeiro/456-conta-corrente.md), [571](../financeiro/571-acni-adiantamento-credito-nao-identificado.md), [475](../financeiro/475-contas-a-pagar.md))
   - Ajustar data de lancamento incorreto
   - Estornar lancamento duplicado
5. Recalcular saldo esperado SSW (ETAPA 6)
6. Repetir ate saldo SSW = saldo extrato

### ETAPA 10: Documentar Conciliacao (Controle Interno)
**Boas praticas para auditoria**

1. Criar planilha de controle (Excel ou Google Sheets):
   - **Data conciliacao**
   - **Banco/Conta**
   - **Saldo extrato**
   - **Saldo SSW**
   - **Divergencia** (se houver)
   - **Ajustes realizados**
   - **Responsavel** (Jaqueline ou Rafael)
2. Anexar copia do extrato bancario (PDF)
3. Anotar observacoes (ex: "Tarifa inesperada R$ 15,00 — verificado com banco")
4. Salvar em pasta compartilhada (ex: Google Drive > Financeiro > Conciliacoes)

---

## Contexto CarVia

| Aspecto | Hoje (2026-02-16) | Futuro (Com Conciliacao SSW) |
|---------|-------------------|------------------------------|
| **Metodo de conciliacao** | Rafael concilia MANUALMENTE fora do SSW | Conciliacao via [opcao 569](../financeiro/569-conciliacao-bancaria.md) dentro do SSW |
| **Controle** | Anotacoes proprias de Rafael (nao sistematizado) | Sistema bloqueia alteracoes retroativas automaticamente |
| **Integridade contabil** | Nenhuma (contabilidade externa nao confia nos dados SSW) | Total (contabilidade externa pode extrair dados via 559/567) |
| **Frequencia** | Irregular (quando Rafael tem tempo) | Semanal (sextas) ou diaria (ideal) |
| **Executor** | Rafael (fora do SSW) | Jaqueline (dentro do SSW) |
| **Pre-requisito critico** | — | Cadastrar conta bancaria ([904](../cadastros/904-bancos-contas-bancarias.md)) — ver PEND-11 |
| **Pre-requisito critico** | — | Configurar plano de contas ([540](../contabilidade/540-plano-de-contas.md)) e lancamentos automaticos ([541](../contabilidade/541-lancamentos-automaticos.md)) |
| **Bloqueio de periodo** | NAO existe (permite alteracoes retroativas) | SIM (impedimentos automaticos apos [569](../financeiro/569-conciliacao-bancaria.md)) |
| **Uso da contabilidade SSW** | IMPOSSIVEL (dados nao confiaveis) | POSSIVEL (pre-requisito atendido) |

**Justificativa da implantacao (P1 — ALTA)**: Sem conciliacao bancaria no SSW, a contabilidade externa NAO consegue usar o modulo contabil do SSW (opcoes [540](../contabilidade/540-plano-de-contas.md)-559-567). Conciliacao garante integridade dos dados e bloqueia alteracoes retroativas que invalidariam balancetes/DREs. Pre-requisito critico para profissionalizacao financeira.

**Ordem de implantacao**:
1. **PEND-11**: Cadastrar conta bancaria ([904](../cadastros/904-bancos-contas-bancarias.md))
2. **PEND-XX**: Configurar plano de contas ([540](../contabilidade/540-plano-de-contas.md)) e lancamentos automaticos ([541](../contabilidade/541-lancamentos-automaticos.md))
3. **POP-F04**: Conciliar mes atual (este POP)
4. **Rotina**: Conciliacao semanal (sextas) ou diaria

---

## Erros Comuns e Solucoes

| Erro | Sintoma | Causa Provavel | Solucao |
|------|---------|----------------|---------|
| **Saldo SSW diverge do extrato** | [Opcao 569](../financeiro/569-conciliacao-bancaria.md) exibe erro "Saldo informado difere do saldo calculado" | Movimentacao nao lancada (tarifa, deposito, cheque) | Investigar via ETAPA 9 — comparar razao contabil ([571](../financeiro/571-acni-adiantamento-credito-nao-identificado.md)) com extrato, lancar faltantes via [456](../financeiro/456-conta-corrente.md)/[571](../financeiro/571-acni-adiantamento-credito-nao-identificado.md) |
| **Cheque compensado mas nao conciliado** | Saldo SSW maior que extrato | Cheque compensado no banco mas nao marcado em [456](../financeiro/456-conta-corrente.md) | Acessar 456, aba Cheques, marcar cheque compensado, salvar |
| **Transferencia duplicada** | Saldo SSW menor que extrato | Transferencia lancada 2x em [456](../financeiro/456-conta-corrente.md) | Acessar [571](../financeiro/571-acni-adiantamento-credito-nao-identificado.md), identificar duplicidade, estornar lancamento |
| **Tarifa bancaria nao lancada** | Saldo SSW maior que extrato | Tarifa debitada pelo banco mas nao informada em [456](../financeiro/456-conta-corrente.md) | Acessar 456, aba Tarifas, lancar tarifa, salvar |
| **Deposito nao identificado** | Saldo extrato maior que SSW | Cliente depositou mas nao informou SSW | Lancar credito seq 82 via [571](../financeiro/571-acni-adiantamento-credito-nao-identificado.md) (ETAPA 5), investigar origem |
| **Periodo ja conciliado nao bloqueia** | Sistema permite alterar data conciliada | Configuracao de bloqueio nao ativada em parametros SSW | Contatar suporte SSW — verificar parametro "Bloquear alteracoes em periodo conciliado" |
| **Conta bancaria nao cadastrada** | [Opcao 569](../financeiro/569-conciliacao-bancaria.md) nao exibe banco/agencia | PEND-11 nao executado | Executar PEND-11 primeiro (cadastrar conta [904](../cadastros/904-bancos-contas-bancarias.md)) |
| **Plano de contas nao configurado** | Lancamentos automaticos ([456](../financeiro/456-conta-corrente.md)) nao contabilizam | Seq 11/17/63/82 nao cadastradas em [540](../contabilidade/540-plano-de-contas.md) | Configurar plano de contas (540) conforme manual SSW |
| **Conciliacao de periodo futuro** | Data conciliacao maior que hoje | Erro de digitacao | Informar data <= hoje — conciliar sempre retroativo |

---

## Verificacao Playwright

| Passo | Acao | Elemento Alvo | Validacao |
|-------|------|---------------|-----------|
| **1. Acessar opcao [456](../financeiro/456-conta-corrente.md)** | `page.goto("/opcao/456")` | Menu "Extrato Bancario" | `expect(page.locator("h1")).to_contain_text("Extrato")` |
| **2. Selecionar banco/conta** | `page.select_option("#banco", "001")` | Dropdown banco/carteira | `expect(page.locator("#banco")).to_have_value("001")` |
| **3. Aba Cheques** | `page.click("a[href='#cheques']")` | Tab "Cheques" | `expect(page.locator("#cheques")).to_be_visible()` |
| **4. Marcar cheque compensado** | `page.check("input[data-cheque='123']")` | Checkbox cheque ID 123 | `expect(page.locator("input[data-cheque='123']")).to_be_checked()` |
| **5. Salvar cheques** | `page.click("button[type=submit]")` | Botao "Salvar" | `expect(page.locator(".alert-success")).to_be_visible()` |
| **6. Aba Transferencias** | `page.click("a[href='#transferencias']")` | Tab "Transferencias" | `expect(page.locator("#transferencias")).to_be_visible()` |
| **7. Informar transferencia** | `page.fill("#valor_transferencia", "1000.00")` | Input valor | `expect(page.locator("#valor_transferencia")).to_have_value("1000.00")` |
| **8. Acessar opcao [569](../financeiro/569-conciliacao-bancaria.md)** | `page.goto("/opcao/569")` | Menu "Conciliacao Bancaria" | `expect(page.locator("h1")).to_contain_text("Conciliacao")` |
| **9. Informar saldo conciliado** | `page.fill("#saldo_conciliado", "15000.00")` | Input saldo | `expect(page.locator("#saldo_conciliado")).to_have_value("15000.00")` |
| **10. Confirmar conciliacao** | `page.click("button[type=submit]")` | Botao "Confirmar" | `expect(page.locator(".alert-success")).to_contain_text("Conciliacao realizada")` |
| **11. Validar bloqueio** | `page.goto("/opcao/074")` | Cancelar CTRB em data conciliada | `expect(page.locator(".alert-danger")).to_contain_text("Periodo conciliado")` |
| **12. Consultar razao contabil** | `page.goto("/opcao/571")` | Menu "Razao Contabil" | `expect(page.locator("table.razao tbody tr").count()).to_be_greater_than(0)` |

---

## POPs Relacionados

| POP | Titulo | Relacao |
|-----|--------|---------|
| **POP-E04** | Emitir Cobranca Bancaria | **DEPENDENTE** — liquidacoes (ocorrencia 006) devem ser conciliadas via [569](../financeiro/569-conciliacao-bancaria.md) |
| **POP-F01** | Pagar Fornecedor (Cheque) | **DEPENDENTE** — cheques compensados devem ser conciliados via [456](../financeiro/456-conta-corrente.md)+[569](../financeiro/569-conciliacao-bancaria.md) |
| **POP-F02** | Pagar Fornecedor (Transferencia) | **DEPENDENTE** — transferencias devem ser conciliadas via [456](../financeiro/456-conta-corrente.md)+[569](../financeiro/569-conciliacao-bancaria.md) |
| **POP-G01** | Fechamento Contabil Mensal | **PRE-REQUISITO** — fechamento 559 requer conciliacao [569](../financeiro/569-conciliacao-bancaria.md) do mes |
| **PEND-11** | Cadastrar Conta Bancaria ([904](../cadastros/904-bancos-contas-bancarias.md)) | **PRE-REQUISITO CRITICO** — conta deve existir para conciliar |
| **PEND-XX** | Configurar Plano de Contas ([540](../contabilidade/540-plano-de-contas.md)) | **PRE-REQUISITO** — seq 11/17/63/82 devem estar cadastradas |
| **PEND-XX** | Configurar Lancamentos Automaticos ([541](../contabilidade/541-lancamentos-automaticos.md)) | **PRE-REQUISITO** — contabilizacao de [456](../financeiro/456-conta-corrente.md)/444/[475](../financeiro/475-contas-a-pagar.md) depende de 541 |

---

## Historico de Revisoes

| Versao | Data | Autor | Alteracoes |
|--------|------|-------|------------|
| **1.0** | 2026-02-16 | Claude (Agente Logistico) | Criacao inicial baseada em doc SSW [opcao 569](../financeiro/569-conciliacao-bancaria.md) + opcoes relacionadas [456](../financeiro/456-conta-corrente.md)/476/[540](../contabilidade/540-plano-de-contas.md)/[541](../contabilidade/541-lancamentos-automaticos.md)/[558](../contabilidade/558-lancamentos-manuais.md)/559/567/[571](../financeiro/571-acni-adiantamento-credito-nao-identificado.md). Contexto CarVia: implantacao critica (P1), Rafael concilia manualmente hoje fora do SSW, pre-requisito para contabilidade externa. Executor futuro: Jaqueline. Fluxo completo: conciliar cheques/transferencias/tarifas via 456, lancar creditos nao identificados via 571, executar conciliacao 569, validar bloqueios. Investigacao de divergencias (ETAPA 9) e documentacao (ETAPA 10). Ordem de implantacao: PEND-11 → configurar 540/541 → conciliar mes atual → rotina semanal/diaria. |

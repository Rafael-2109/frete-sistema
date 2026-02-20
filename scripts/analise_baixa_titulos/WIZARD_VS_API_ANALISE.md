# Wizard Odoo vs API Manual — Analise de Reconciliacao de Extrato

**Data**: 20/02/2026
**Contexto**: Apos implementar o metodo consolidado `preparar_extrato_para_reconciliacao()` com 5 passos manuais (draft → write partner → write name → write account_id → post), documentamos por que NAO usamos o mecanismo nativo do Odoo.

---

## Resumo

Sao **2 operacoes DIFERENTES**. O wizard faz UMA delas. A outra e feita nativamente pelo Odoo na UI (bank reconciliation widget), mas nos replicamos via API com customizacoes.

---

## As 2 Operacoes Distintas

### Operacao 1: Criar Payment + Reconciliar com TITULO

| Aspecto | Descricao |
|---------|-----------|
| **O que faz** | Cria `account.payment`, posta, reconcilia payment↔titulo |
| **Wizard** | `account.payment.register` — faz TUDO automatico (inclusive write-off de juros) |
| **Nosso codigo** | `criar_pagamento_outbound_com_writeoff()` (com juros) ou `criar_pagamento_outbound()` + `reconciliar()` (sem juros) |
| **Status** | JA usamos o wizard onde faz sentido (com juros). Fluxo manual para sem juros tambem funciona. |

**Localizacao no codigo:**
- `baixa_pagamentos_service.py:420-542` — `criar_pagamento_outbound_com_writeoff()` (wizard)
- `baixa_pagamentos_service.py:363-418` — `criar_pagamento_outbound()` (manual)
- `baixa_pagamentos_service.py:599-614` — `reconciliar()`

### Operacao 2: Reconciliar EXTRATO BANCARIO com Payment

| Aspecto | Descricao |
|---------|-----------|
| **O que faz** | Vincula statement_line↔payment via conta PENDENTES, seta `is_reconciled=True` |
| **Wizard** | `account.payment.register` NAO faz isso — o extrato permanece `is_reconciled=False` |
| **Odoo nativo (UI)** | Bank reconciliation widget faz isso automaticamente |
| **Nosso codigo** | `preparar_extrato_para_reconciliacao()` (5 passos) + `reconciliar()` |

**Localizacao no codigo (2 versoes):**
- `baixa_pagamentos_service.py:897-1022` — versao publica, IDs raw (usada por comprovantes)
- `extrato_conciliacao_service.py:1694-1849` — versao privada, ExtratoItem

---

## O Que o Odoo FAZ Nativamente na UI (Evidencia)

No documento `ANALISE_CONCILIACAO_EXTRATO_MULTICOMPANY.md` (dez/2025, mesmo diretorio), secao 4, ha um teste feito via **UI do Odoo** (bank reconciliation widget):

```
O QUE O ODOO FEZ NA CONCILIACAO (via UI):

1. Modificou o move do extrato (428302)
   - Linhas originais (2770009, 2770010) foram SUBSTITUIDAS
   - Novas linhas (2780041, 2780042) foram CRIADAS
   - Linha 2780042 usa conta PAGAMENTOS PENDENTES (26868)

2. Reconciliou as linhas da conta PENDENTES
   - Linha 2734615 (empresa 4 - payment) <-> Linha 2780042 (empresa 1 - extrato)
   - Criou partial_reconcile 33387
   - Criou full_reconcile 27438
```

Isso e EXATAMENTE o que nosso `preparar_extrato_para_reconciliacao()` faz manualmente via API.

---

## Por Que NAO Usamos o Mecanismo Nativo

### Razao 1: Nao E o Wizard — E o Bank Reconciliation Widget

O `account.payment.register` (wizard) so cuida da Operacao 1 (payment↔titulo).
O que faria a Operacao 2 automaticamente e o **bank reconciliation widget** do Odoo 17.

Na UI: o usuario abre Contabilidade → Banco → Reconciliar, arrasta linhas, e o Odoo faz tudo.
Via API: o metodo interno que o widget chama nao esta documentado/exposto para XML-RPC.

### Razao 2: O Mecanismo Nativo NAO Conhece Nossos Dados

Quando o Odoo reconcilia via UI, ele TAMBEM precisa saber:
- **Qual payment** corresponde a qual statement_line
- **Qual partner** associar (boletos nao tem partner automatico)
- **Qual rotulo** usar (payment_ref)

Na UI, o USUARIO informa isso clicando. Via API, NOS informamos via o metodo consolidado.

O matching inteligente (CNPJ, NF, parcela, tolerancia R$ 0.02) e 100% nosso — o Odoo nativo nao faz isso.

### Razao 3: Multi-Company Via API

A analise multicompany (dez/2025) mostra que o Odoo lida com multi-company na UI.
Mas via XML-RPC, nao ha garantia de que o metodo interno do widget funcione cross-company.
Nosso codigo trata os 3 cenarios explicitamente (cenario 1/2/3 da analise).

### Razao 4: Bugs O11/O12

Nosso metodo consolidado foi criado ESPECIFICAMENTE para contornar:
- **O11**: `button_draft` remove reconciliacao existente
- **O12**: Write em statement_line regenera move_lines, revertendo account_id

O mecanismo nativo do Odoo provavelmente nao tem esses problemas porque opera em nivel mais baixo (ORM direto, nao XML-RPC). Mas nos operamos via XML-RPC onde essas limitacoes existem.

---

## Tabela Comparativa

| Necessidade | Wizard (payment.register) | Bank Rec Widget (UI) | Nosso Codigo (API) |
|-------------|---------------------------|---------------------|---------------------|
| Criar payment | SIM (com write-off) | NAO | SIM (manual ou wizard) |
| Postar payment | SIM (automatico) | NAO | SIM (`action_post`) |
| Reconciliar payment↔titulo | SIM (automatico) | NAO | SIM (`reconcile()`) |
| Trocar TRANSITORIA→PENDENTES | NAO | SIM (automatico) | SIM (passo 4 do consolidado) |
| Atualizar partner_id | NAO | SIM (usuario informa) | SIM (passo 2 do consolidado) |
| Atualizar rotulo | NAO | SIM (usuario informa) | SIM (passos 2-3 do consolidado) |
| Reconciliar extrato↔payment | NAO | SIM (automatico) | SIM (`reconcile()` final) |
| Matching inteligente | NAO | NAO (usuario decide) | SIM (CNPJ, NF, parcela, tolerancia) |
| Multi-company | NAO | SIM (via UI) | SIM (3 cenarios) |

---

## Investigacao Futura (Opcional)

### Metodos Potenciais no Odoo 17

| Metodo Potencial | Modelo | Status |
|-----------------|--------|--------|
| `_action_reconcile()` | `account.bank.statement.line` | NAO VERIFICADO — pode nao existir ou ser privado |
| `action_bank_statement_validate()` | `account.bank.statement.line` | NAO VERIFICADO — pode validar todo statement |
| `process_bank_statement_line()` | `account.reconciliation.widget` | DEPRECADO — era do Odoo <= 16, removido no 17 |
| `reconcile_bank_recs()` | ??? | NAO VERIFICADO |

### Pre-requisitos para Testar

1. **Descobrir metodos**: Usar skill `descobrindo-odoo-estrutura` no modelo `account.bank.statement.line`
2. **Testar chamada**: Se existir metodo publico, testar passando `statement_line_id` + `counterpart_line_ids` + `partner_id`
3. **Verificar resultado**: `is_reconciled = True`, conta PENDENTES, partner correto, rotulo atualizado

### Riscos da Abordagem Nativa

- Metodo pode ser `_private` (prefixo `_`) — inacessivel via XML-RPC
- Comportamento cross-company nao garantido
- Pode nao aceitar partner_id como parametro
- Mudancas de versao quebram metodos internos (nao e API publica)

---

## Conclusao e Recomendacao

### O que JA fazemos certo:
1. **Wizard para juros**: Ja usamos `account.payment.register` onde faz sentido
2. **Fluxo manual para pagamentos simples**: Funciona corretamente
3. **Metodo consolidado para extrato**: Resolve O11/O12 de forma robusta

### Recomendacao:
**Manter o sistema atual** (funciona e esta testado). Como melhoria futura opcional, investigar os metodos internos do `account.bank.statement.line` no Odoo 17 para ver se existe alternativa nativa. Isso requer:
1. Sessao de discovery no Odoo (skill `descobrindo-odoo-estrutura`)
2. Teste em ambiente de staging
3. Validacao dos 3 cenarios multi-company

---

## Documentos Relacionados

| Documento | Conteudo |
|-----------|----------|
| `ANALISE_CONCILIACAO_EXTRATO_MULTICOMPANY.md` (mesmo diretorio) | Teste via UI, 3 cenarios multi-company |
| `app/financeiro/CLAUDE.md` (O11, O12) | Gotchas do metodo consolidado |
| `app/financeiro/GOTCHAS.md` (O11, O12) | Versao expandida dos gotchas |
| `.claude/skills/executando-odoo-financeiro/references/fluxo-recebimento.md` | Fluxo completo de conciliacao |

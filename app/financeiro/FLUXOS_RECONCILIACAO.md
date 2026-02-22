# Fluxos de Reconciliacao Financeira

**Atualizado**: 21/02/2026

Documento indice dos 5 caminhos de reconciliacao do modulo financeiro.
NAO duplica gotchas (ver `GOTCHAS.md`) nem campos (ver schemas JSON).

> **Convencoes**: Receber = `asset_receivable` (cliente paga). Pagar = `liability_payable` (nos pagamos).

---

## Tabela Comparativa

| # | Caminho | Trigger | Automacao | Receber | Pagar | Rota Principal |
|---|---------|---------|-----------|---------|-------|----------------|
| 1 | **CNAB Retorno** | Upload `.ret` | Automatico | Sim | Nao | `/cnab400/upload` |
| 2 | **Extrato Bancario** | Import statement Odoo | Semi-auto | Sim | Sim | `/extrato/importar-statement/<id>` |
| 3 | **Comprovante Boleto** | Upload PDF | Semi-auto | Nao | Sim | `/comprovantes/api/upload` |
| 4 | **Baixa Excel** | Upload planilha | Batch manual | Sim | Nao | `/contas-receber/baixas/upload` |
| 5 | **Baixa Pagamentos** | Import extrato saida | Item a item | Nao | Sim | `/contas-pagar/baixas/importar-extrato/<id>` |

---

## Mapa de Entidades Local <-> Odoo

```
LOCAL (PostgreSQL)                              ODOO (XML-RPC)
=================                               ==============

ContasAReceber                                  account.move.line
  .odoo_line_id ─────────────────────────────── .id (asset_receivable, debit > 0)
  .titulo_nf                                    .move_id -> account.move (NF-e)
  .parcela (VARCHAR)                            .l10n_br_cobranca_parcela (int|False)
  .valor_residual = abs(...)                    .amount_residual (positivo)
  .parcela_paga                                 .l10n_br_paga / .reconciled

ContasAPagar                                    account.move.line
  .odoo_line_id ─────────────────────────────── .id (liability_payable, credit > 0)
  .valor_residual = abs(...)                    .amount_residual (NEGATIVO!)

ExtratoItem                                     account.bank.statement.line
  .statement_line_id ────────────────────────── .id
  .move_id ──────────────────────────────────── .move_id -> account.move
  .credit_line_id ───────────────────────────── account.move.line (conta TRANSITORIA 22199)

ExtratoItemTitulo (M:N)                         account.partial.reconcile
  .extrato_item_id -> ExtratoItem               .partial_reconcile_id
  .titulo_receber_id -> ContasAReceber           .full_reconcile_id
  .titulo_pagar_id -> ContasAPagar
  .valor_alocado (Numeric 15,2)
  .payment_id -> account.payment

BaixaTituloItem                                 account.payment (inbound, customer)
  .titulo_odoo_id ───────────────────────────── account.move.line (receivable)
  .payment_odoo_id ──────────────────────────── .id
  .partial_reconcile_id                         account.partial.reconcile

BaixaPagamentoItem                              account.payment (outbound, supplier)
  .titulo_id ────────────────────────────────── account.move.line (payable)
  .payment_id ───────────────────────────────── .id
  .statement_line_id ────────────────────────── account.bank.statement.line

ComprovantePagamentoBoleto                      account.bank.statement.line
  .odoo_statement_line_id ───────────────────── .id
  .odoo_journal_id                              account.journal

LancamentoComprovante                           account.payment (outbound, supplier)
  .odoo_move_line_id ────────────────────────── account.move.line (payable)
  .odoo_payment_id ──────────────────────────── .id
```

### Contas-chave Odoo

| ID | Codigo | Nome | Papel |
|----|--------|------|-------|
| 22199 | 1110100003 | TRANSITORIA | Contrapartida temporaria do extrato |
| 26868 | 1110100004 | PENDENTES | Ponte payment <-> extrato (reconciliacao) |
| 24801 | 1120100001 | CLIENTES NACIONAIS | Receivable (clientes) |

> IDs completos: `.claude/references/odoo/IDS_FIXOS.md`

---

## Fluxo 1: CNAB Retorno

**Escopo**: Contas a receber. Arquivo `.ret` do banco (CNAB 400).

```
Upload .ret ──> Parse CNAB ──> Match titulo ──> Match extrato ──> Baixa auto ──> Reconcilia Odoo
```

| Passo | Acao | Arquivo responsavel |
|-------|------|---------------------|
| 1 | Upload arquivo `.ret`, calcula hash SHA256 (anti-duplicata) | `routes/cnab400.py` |
| 2 | Parse registros tipo 1, extrai NF/Parcela do campo "Seu Numero" | `services/cnab400_parser_service.py` |
| 3 | Cria `CnabRetornoLote` + `CnabRetornoItem` por registro | `services/cnab400_processor_service.py` |
| 4 | Match titulo: busca `ContasAReceber` por empresa+NF+parcela | `services/cnab400_processor_service.py` |
| 5 | Match extrato: busca `ExtratoItem` por data_credito+valor+CNPJ | `services/cnab400_processor_service.py` |
| 6 | Baixa automatica: se titulo E extrato vinculados, processa Odoo | `services/cnab400_processor_service.py` |
| 7 | Reconcilia via `ExtratoConciliacaoService.conciliar_item()` | `services/extrato_conciliacao_service.py` |

**Models**: `CnabRetornoLote`, `CnabRetornoItem`, `ContasAReceber`, `ExtratoItem`
**Worker**: `workers/cnab400_batch_jobs.py`

---

## Fluxo 2: Extrato Bancario

**Escopo**: Receber (entrada) E Pagar (saida). Linhas de `account.bank.statement` do Odoo.

```
Import Odoo ──> Resolver favorecido ──> Matching ──> Aprovacao ──> Conciliacao Odoo
```

| Passo | Acao | Arquivo responsavel |
|-------|------|---------------------|
| 1 | Importa linhas nao-reconciliadas do statement Odoo | `services/extrato_service.py` |
| 2 | Cria `ExtratoLote` (UNIQUE: statement_id + tipo_transacao) e `ExtratoItem` | `services/extrato_service.py` |
| 3 | Resolve favorecido/pagador (CNPJ, nome, categoria) | `services/favorecido_resolver_service.py` ou `services/recebimento_resolver_service.py` |
| 4 | Matching: entrada→`ExtratoMatchingService`, saida→`PagamentoMatchingService` | `services/extrato_matching_service.py` / `services/pagamento_matching_service.py` |
| 5 | Vinculacao M:N via `ExtratoItemTitulo` (valor_alocado por titulo) | `services/extrato_matching_service.py` |
| 6 | Aprovacao manual pelo usuario na tela `/extrato/itens` | `routes/extrato.py` |
| 7 | Conciliacao: prepara extrato (TRANSITORIA→PENDENTES) + reconcilia | `services/extrato_conciliacao_service.py` |

**Models**: `ExtratoLote`, `ExtratoItem`, `ExtratoItemTitulo`, `ContasAReceber`, `ContasAPagar`
**Worker**: `workers/extrato_conciliacao_jobs.py` (ate 100 itens/job)

> **Gotcha critico**: A preparacao do extrato DEVE usar metodo consolidado (`_preparar_extrato_para_reconciliacao`).
> Ver gotchas O11/O12 em `CLAUDE.md`.

---

## Fluxo 3: Comprovante Boleto

**Escopo**: Contas a pagar. Upload de comprovantes PDF (boletos Sicoob).

```
Upload PDF ──> OCR ──> S3 ──> Match fornecedor ──> Confirmacao ──> Lancamento Odoo ──> Reconcilia
```

| Passo | Acao | Arquivo responsavel |
|-------|------|---------------------|
| 1 | Upload PDF(s), hash SHA256, detecta tipo OCR (Sicoob vs generico) | `services/comprovante_service.py` |
| 2 | Extrai dados: numero_agendamento, valor, data, beneficiario, CNPJ | `services/comprovante_service.py` |
| 3 | Armazena PDF no S3, cria `ComprovantePagamentoBoleto` (IMPORTADO) | `services/comprovante_service.py` |
| 4 | Matching: busca faturas candidatas no Odoo (liability_payable) | `services/comprovante_match_service.py` |
| 5 | Parseia NF+parcela do numero_documento, calcula score (85+ = auto) | `services/comprovante_match_service.py` |
| 6 | Cria `LancamentoComprovante` (PENDENTE), usuario confirma (→CONFIRMADO) | `services/comprovante_match_service.py` |
| 7 | Cria `account.payment` outbound, posta, reconcilia titulo+extrato | `services/comprovante_lancamento_service.py` |

**Models**: `ComprovantePagamentoBoleto`, `LancamentoComprovante` (em `models_comprovante.py`)
**Workers**: `workers/comprovante_batch_jobs.py`, `workers/comprovante_match_jobs.py`, `workers/comprovante_lancamento_jobs.py`

---

## Fluxo 4: Baixa Excel (Receber)

**Escopo**: Contas a receber. Planilha com NF+Parcela+Valor+Journal.

```
Download template ──> Preencher ──> Upload ──> Validacao ──> Processamento ──> Payment Odoo
```

| Passo | Acao | Arquivo responsavel |
|-------|------|---------------------|
| 1 | Download template Excel (colunas: NF, PARCELA, VALOR, JOURNAL, DATA, ...) | `routes/baixas.py` |
| 2 | Upload Excel, valida colunas obrigatorias, detecta duplicatas (arquivo+banco) | `routes/baixas.py` |
| 3 | Resolve journal por nome/codigo/ID, cria `BaixaTituloLote` + `BaixaTituloItem` | `routes/baixas.py` |
| 4 | Itens INVALIDO podem ter journal corrigido; itens podem ser ativados/inativados | `routes/baixas.py` |
| 5 | Processamento via worker: busca titulo Odoo por NF+parcela (receivable) | `services/baixa_titulos_service.py` |
| 6 | Cria `account.payment` inbound, posta, reconcilia com titulo | `services/baixa_titulos_service.py` |
| 7 | Processa colunas adicionais: desconto (J886), acordo (J885), devolucao (J879), juros (J1066) | `services/baixa_titulos_service.py` |

**Models**: `BaixaTituloLote`, `BaixaTituloItem` (em `models.py`)
**Worker**: `workers/baixa_titulos_jobs.py` (lock Redis por item_id)

---

## Fluxo 5: Baixa Pagamentos (Pagar)

**Escopo**: Contas a pagar. Linhas de saida do extrato bancario.

```
Import extrato saida ──> Matching CNPJ+valor ──> Aprovacao ──> Processar ──> Payment Odoo
```

| Passo | Acao | Arquivo responsavel |
|-------|------|---------------------|
| 1 | Importa linhas de saida (amount < 0) do extrato Odoo | `routes/pagamentos_baixas.py` |
| 2 | Cria `BaixaPagamentoLote` + `BaixaPagamentoItem` | `routes/pagamentos_baixas.py` |
| 3 | Matching automatico: CNPJ beneficiario + valor (tolerancia R$5) | `routes/pagamentos_baixas.py` |
| 4 | Vinculacao manual para SEM_MATCH; busca titulos por NF/CNPJ | `routes/pagamentos_baixas.py` |
| 5 | Aprovacao (individual ou lote) | `routes/pagamentos_baixas.py` |
| 6 | Cria `account.payment` outbound+supplier, posta | `services/baixa_pagamentos_service.py` |
| 7 | Reconcilia payment com titulo E com extrato; captura snapshots | `services/baixa_pagamentos_service.py` |

**Models**: `BaixaPagamentoLote`, `BaixaPagamentoItem` (em `models.py`)
**Processamento**: Sincrono por item (`processar-item/<id>`) ou assincrono por lote

> **Diferencas vs Receber**: `payment_type='outbound'`, `partner_type='supplier'`,
> titulo tem `credit > 0`, `amount_residual` e NEGATIVO (ver gotcha O3).

---

## Indice Cruzado

| Preciso de... | Documento |
|---------------|-----------|
| Gotchas A1-A10 (armadilhas de codigo) | `app/financeiro/CLAUDE.md` |
| Gotchas O1-O12 (armadilhas Odoo) | `app/financeiro/CLAUDE.md` |
| 80+ gotchas detalhados | `app/financeiro/GOTCHAS.md` |
| Campos de QUALQUER tabela financeira | `.claude/skills/consultando-sql/schemas/tables/{tabela}.json` |
| Codigo para criar payment + reconciliar | `.claude/skills/executando-odoo-financeiro/references/fluxo-recebimento.md` |
| Erros comuns ao executar payments | `.claude/skills/executando-odoo-financeiro/references/erros-comuns.md` |
| IDs de contas de juros por empresa | `.claude/skills/executando-odoo-financeiro/references/contas-por-empresa.md` |
| IDs fixos Odoo (journals, accounts) | `.claude/references/odoo/IDS_FIXOS.md` |
| Wizard vs API (por que NAO usamos bank rec widget) | `scripts/analise_baixa_titulos/WIZARD_VS_API_ANALISE.md` |
| Conciliacao multi-company (titulo CD + extrato FB) | `scripts/analise_baixa_titulos/ANALISE_CONCILIACAO_EXTRATO_MULTICOMPANY.md` |
| Constantes (contas, journals, mapeamentos) | `app/financeiro/constants.py` |
| Regras de negocio contas a receber | `app/financeiro/contas_a_receber.md` |

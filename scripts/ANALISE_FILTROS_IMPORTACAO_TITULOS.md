# Analise Comparativa: Filtros e Criterios de Importacao de Titulos

**Data**: 2026-02-24
**Autor**: Sistema de Fretes

## Contexto

O script `scripts/auditar_icms_st_receber.py` busca titulos a receber no Odoo para detectar faturas sem ICMS-ST. Para entender se os criterios do script estao alinhados (ou divergem) dos servicos de producao, esta analise compara os filtros de 3 componentes:

1. **Sync Contas a Receber** — `app/financeiro/services/sincronizacao_contas_receber_service.py`
2. **Sync Contas a Pagar** — `app/financeiro/services/sincronizacao_contas_pagar_service.py`
3. **Script de Auditoria** — `scripts/auditar_icms_st_receber.py`

---

## 1. Domain Filters no Odoo (account.move.line)

### Comparacao lado a lado

| Criterio | Sync Receber (manual) | Sync Receber (incremental) | Sync Pagar (manual) | Sync Pagar (incremental) | Script Auditoria |
|---|---|---|---|---|---|
| **account_type** | `asset_receivable` | `asset_receivable` | `liability_payable` | `liability_payable` | `asset_receivable` |
| **parent_state** | `posted` | `posted` | `posted` | `posted` | `posted` |
| **Filtro de saldo** | `balance > 0` | **NENHUM** | `amount_residual < 0` | **NENHUM** | **NENHUM** |
| **Filtro de data** | `date >= D-7` | `write_date\|create_date >= D-120min` | `date_maturity >= D-90` | `write_date\|create_date >= D-120min` | **NENHUM** |
| **date_maturity** | `!= False` | `!= False` | — (filtro por >=) | — | — |
| **company_id** | Todas (via map) | Todas (via map) | Todas (via map) | Todas (via map) | `[1, 3, 4]` (explicito) |

### Fontes exatas

- Sync Receber manual: `contas_receber_service.py:88-94`
- Sync Receber incremental: `sincronizacao_contas_receber_service.py:240-247`
- Sync Pagar manual: `sincronizacao_contas_pagar_service.py:407-418`
- Sync Pagar incremental: `sincronizacao_contas_pagar_service.py:297-303`
- Script Auditoria: `auditar_icms_st_receber.py:220-224`

### Observacoes criticas

1. **O script de auditoria NAO filtra por saldo** — inclui titulos pagos e abertos. Isso e **intencional**: precisa detectar write-offs em titulos ja quitados.

2. **O sync incremental do Receber tambem NAO filtra saldo** — para capturar titulos recem-pagos e atualizar `parcela_paga` localmente.

3. **O sync manual do Receber filtra `balance > 0`** — exclui titulos pagos. Titulos com ST faltante que ja foram quitados (com write-off de juros) **podem nao ser reimportados** por este caminho.

4. **Pagar usa `amount_residual < 0`** (negativo por convencao Odoo — Gotcha O3), Receber usa `balance > 0`.

5. **O script nao tem filtro de data** — busca TUDO desde o inicio. Receber filtra por `date` (emissao), Pagar filtra por `date_maturity` (vencimento).

---

## 2. Campos Fetched do Odoo

### Campos comuns (presentes nos 3)

| Campo | Receber | Pagar | Auditoria |
|---|:---:|:---:|:---:|
| `id` | Y | Y | Y |
| `x_studio_nf_e` | Y | Y | Y |
| `l10n_br_cobranca_parcela` | Y | Y | Y |
| `partner_id` | Y | Y | Y |
| `company_id` | Y | Y | Y |
| `date` | Y | Y | Y |
| `date_maturity` | Y | Y | Y |
| `amount_residual` | Y | Y | Y |
| `l10n_br_paga` | Y | Y | Y |
| `parent_state` | Y | Y | — (no filtro) |
| `account_type` | Y | Y | — (no filtro) |

### Campos EXCLUSIVOS de cada servico

| Campo | Receber | Pagar | Auditoria | Motivo |
|---|:---:|:---:|:---:|---|
| `balance` | Y | — | Y | Receber usa balance; Pagar usa credit |
| `credit` | — | Y | — | Pagar: valor original e o credito |
| `desconto_concedido` | Y | — | Y | Receber tem bug de desconto duplo |
| `desconto_concedido_percentual` | Y | — | Y | Idem |
| `payment_provider_id` | Y | — | — | Tipo de titulo (boleto, etc.) |
| `x_studio_status_de_pagamento` | Y | — | — | Status de pagamento (apenas Receber) |
| `move_id` | — | Y | Y | Referencia ao account.move |
| `reconciled` | — | Y | Y | Pagar usa como sinal de pagamento |
| `matched_debit_ids` | — | — | Y | Rastrear reconciliacoes (Fases 4/4b) |
| `matched_credit_ids` | — | — | Y | Idem |
| `name`, `ref` | — | Y | Y | Referencias para diagnostico |
| `write_date` | Y (incr.) | Y (incr.) | — | Filtro incremental |
| `create_date` | Y (incr.) | Y (incr.) | — | Filtro incremental |

### Fontes exatas

- Receber manual: `contas_receber_service.py:30-48`
- Receber incremental: `sincronizacao_contas_receber_service.py:230-238`
- Pagar: `sincronizacao_contas_pagar_service.py:48-67`
- Auditoria: `auditar_icms_st_receber.py:104-113`

### Campos fiscais (APENAS no script de auditoria, via account.move)

| Campo | Descricao | Usado em |
|---|---|---|
| `amount_total` | Valor da fatura como criada | Fase 3 — comparar com NF real |
| `l10n_br_total_nfe` | Valor REAL da NF (inclui ST) | Fase 3 — NF real |
| `l10n_br_icmsst_valor` | Valor do ICMS-ST | Fase 3 — ST faltante |
| `l10n_br_icmsst_base` | Base do ICMS-ST | Fase 3 — contexto |
| `l10n_br_icms_valor` | ICMS normal | Fase 7 — Excel |
| `l10n_br_icms_base` | Base ICMS normal | Fase 7 — Excel |
| `l10n_br_fcp_st_valor` | FCP-ST | Fase 7 — Excel |

**FONTE**: `auditar_icms_st_receber.py:123-133`

**Nota**: Os syncs de producao NAO buscam campos fiscais — nao e responsabilidade deles detectar ST faltante.

---

## 3. Criterios de Exclusao

| Criterio | Receber | Pagar | Auditoria |
|---|:---:|:---:|:---:|
| **NF-e vazia/zero** | Y (regra 2) | Y (linha 498) | Y (Fase 3, linha 456) |
| **Intercompany (CNPJ Nacom)** | **NAO** | Y (CNPJS_RAIZ_GRUPO_PAGAR) | Y (CNPJS_RAIZ_GRUPO) |
| **Empresa nao mapeada (=0)** | Y | Y | N/A (filtra por company_id) |
| **LA FAMIGLIA-LF** | Y (excluida, regra 4) | **NAO** | N/A (company_id=[1,3,4]) |
| **date_maturity < 2000-01-02** | Y (excluida, regra 5) | **NAO** | **NAO** (detecta phantoms 2000) |
| **balance/credit <= 0** | Y (manual, regra 3) | Y (credit=0, linha 524) | **NAO** |
| **Duplicatas (empresa,NF,parcela)** | Y (dedup) | N/A | N/A |
| **Devolucoes (saldo_total <= 0)** | Y (incr., linha 500) | Y (credit=0) | **NAO** |

### Fontes exatas

- Receber regras: `contas_receber_service.py:245-354`
- Receber incremental exclusoes: `sincronizacao_contas_receber_service.py:496-501`
- Pagar exclusoes: `sincronizacao_contas_pagar_service.py:488-526`
- Auditoria exclusoes: `auditar_icms_st_receber.py:449-458`

### Divergencias importantes

1. **Intercompany**: O sync Receber **NAO** exclui intercompany, mas o sync Pagar e o script de auditoria **SIM**. Titulos intercompany a receber sao importados para a tabela local.

2. **Phantoms 2000**: O sync Receber exclui `date_maturity < 2000-01-02`. O script de auditoria **mantem** essas linhas justamente para detecta-las (Fase 5).

3. **LA FAMIGLIA-LF**: Excluida pelo sync Receber (company 5/LF). O script de auditoria resolve isso filtrando por `company_id in [1,3,4]` (que exclui LF por omissao).

---

## 4. Logica de Pagamento (parcela_paga)

| Sinal | Receber | Pagar | Auditoria |
|---|---|---|---|
| `l10n_br_paga = True` | Y | Y | Y (campo `paga`) |
| `amount_residual <= 0` | Y | Y (`>= 0` para payable) | Y (implicito) |
| `reconciled = True` | — | Y | Y (campo `reconciliado`) |
| `status = 'paid'` | Y | — | — |

**Pagar** usa 3 sinais: `l10n_br_paga OR reconciled OR amount_residual >= 0`.
FONTE: `sincronizacao_contas_pagar_service.py:539-541`

**Receber** usa 3 sinais: `l10n_br_paga OR amount_residual <= 0 OR status='paid'`.
FONTE: `sincronizacao_contas_receber_service.py:575-578`

**Auditoria** nao calcula `parcela_paga` — exporta os sinais brutos para analise.
FONTE: `auditar_icms_st_receber.py:520-521`

---

## 5. Tratamento de Valores

| Aspecto | Receber | Pagar | Auditoria |
|---|---|---|---|
| **Campo-base** | `balance` | `credit` | `balance` |
| **Bug desconto duplo** | Y Corrigido | N/A | N/A (compara totais do invoice) |
| **valor_original** | `saldo_total / (1-desc%)` | `credit` direto | `amount_total` do account.move |
| **valor_residual** | `abs(amount_residual)` | `abs(amount_residual)` | `amount_residual` (Gotcha O3) |
| **Sinal** | Positivo (balance > 0) | Negativo (residual < 0) -> abs() | Positivo (balance) |

**Divergencia**: O sync Receber aplica correcao de desconto duplo (Gotcha O7 — `saldo_total = balance + desconto_concedido` e depois recalcula). O Pagar usa `credit` diretamente sem essa correcao.

FONTE correcao desconto: `sincronizacao_contas_receber_service.py:541-573` (comentario extenso)

---

## 6. Partner/Fornecedor Enrichment

| Aspecto | Receber | Pagar | Auditoria |
|---|---|---|---|
| **Modelo** | `res.partner` | `res.partner` | `res.partner` |
| **Campos** | `l10n_br_cnpj`, `l10n_br_razao_social`, `name`, `state_id` | `l10n_br_cnpj`, `l10n_br_razao_social`, `name` | `name`, `l10n_br_cnpj`, `l10n_br_razao_social` |
| **UF** | Y (via state_id -> UF 2 letras) | **NAO** | **NAO** |
| **Batch size** | 500 | sem batch (limit=len) | 500 |
| **Fallback display_name** | Evitado | Evitado | Evitado |

### Fontes exatas

- Receber partner: `sincronizacao_contas_receber_service.py:421-424`
- Pagar partner: `sincronizacao_contas_pagar_service.py:454-458`
- Auditoria partner: `auditar_icms_st_receber.py:117`

---

## 7. Scheduler e Periodicidade

| Config | Receber | Pagar |
|---|---|---|
| **Intervalo** | 30 min | 30 min |
| **Janela** | 120 min | 120 min |
| **Env var** | `JANELA_CONTAS_RECEBER` | `JANELA_CONTAS_PAGAR` |
| **Metodo** | `sincronizar_incremental()` | `sincronizar_incremental()` |
| **Chamada no scheduler** | `sincronizacao_incremental_definitiva.py:702` | `sincronizacao_incremental_definitiva.py:898` |

FONTE env vars: `sincronizacao_incremental_definitiva.py:45-47`
FONTE intervalo: `sincronizacao_incremental_definitiva.py:37`

---

## 8. Resumo de Divergencias Chave

| # | Divergencia | Impacto | Fonte |
|---|---|---|---|
| 1 | **Receber NAO exclui intercompany** — Pagar e Auditoria excluem | Titulos intercompany a receber aparecem na tabela local | Pagar:510, Auditoria:450 |
| 2 | **Receber exclui phantoms 2000** — Auditoria mantem | Script detecta phantoms que o sync descarta | Receber:322, Auditoria:1215 |
| 3 | **Pagar filtra por `date_maturity`** — Receber filtra por `date` (emissao) | Janelas temporais diferentes para cada tipo | Receber:89, Pagar:410 |
| 4 | **Receber tem bug fix desconto duplo** — Pagar nao aplica | Pagar usa `credit` direto (nao precisa corrigir) | Receber:541-573 |
| 5 | **Auditoria nao filtra por saldo nem data** | Escopo total para auditoria completa | Auditoria:220-224 |
| 6 | **Auditoria busca campos fiscais (l10n_br_*)** | Exclusivo — syncs nao verificam ST | Auditoria:123-133 |
| 7 | **Auditoria busca matched_debit/credit_ids** | Exclusivo — rastreamento de reconciliacoes | Auditoria:111 |
| 8 | **Pagar usa `credit`, Receber usa `balance`** | Campos diferentes para valor original | Pagar:519, Receber:287 |
| 9 | **x_studio_status_de_pagamento** apenas no Receber | Pagar usa `reconciled` em vez de `status` | Receber:235, Pagar:62 |

---

## Fontes

| Arquivo | Linhas-chave |
|---|---|
| `app/financeiro/services/contas_receber_service.py` | Domain: 88-94, Fields: 30-48, Regras: 245-354 |
| `app/financeiro/services/sincronizacao_contas_receber_service.py` | Domain incr.: 240-247, Fields: 230-238, Create: 537-605 |
| `app/financeiro/services/sincronizacao_contas_pagar_service.py` | Domain: 407-418, Domain incr.: 297-303, Fields: 48-67, Exclusoes: 488-526 |
| `scripts/auditar_icms_st_receber.py` | Domain: 220-224, Fields: 104-113, Fiscais: 123-133, Exclusoes: 449-458 |
| `app/scheduler/sincronizacao_incremental_definitiva.py` | Receber: 702, Pagar: 898, Intervalo: 37, Env vars: 45-47 |

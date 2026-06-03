<!-- doc:meta
tipo: reference
camada: L2
sot_de: —
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# IDs Fixos por Empresa - Odoo

> **Papel:** IDs Fixos por Empresa - Odoo.

## Indice

- [Companies (CNPJ → Company ID)](#companies-cnpj-company-id)
- [Locais "Indisponivel" por Empresa](#locais-indisponivel-por-empresa)
- [Picking Types por Company](#picking-types-por-company)
- [Operacoes de TRANSPORTE/CTe (l10n_br_operacao_id)](#operacoes-de-transportecte-l10n_br_operacao_id)
  - [Mapeamento De-Para Operacoes](#mapeamento-de-para-operacoes)
- [IDs do Frete/CTe](#ids-do-fretecte)
- [Journals Financeiros](#journals-financeiros)
  - [Journals Especiais (Hardcoded)](#journals-especiais-hardcoded)
  - [Top 10 Journals por Frequencia](#top-10-journals-por-frequencia)
- [Tolerancias de Validacao NF x PO](#tolerancias-de-validacao-nf-x-po)
- [IDs de UI Odoo (Navegacao Web)](#ids-de-ui-odoo-navegacao-web)
  - [URLs de Invoice](#urls-de-invoice)
  - [Gotcha: networkidle vs domcontentloaded](#gotcha-networkidle-vs-domcontentloaded)
- [Como Usar](#como-usar)

**Ultima verificacao:** 31/Janeiro/2026 (product_id corrigido: 35→29993)
**Fonte:** `app/fretes/services/lancamento_odoo_service.py`, `app/financeiro/routes/baixas.py`

---

## Companies (CNPJ → Company ID)

| CNPJ | Company ID | Nome | Codigo |
|------|------------|------|--------|
| 61724241000178 | 1 | NACOM GOYA - FB | FB |
| 61724241000259 | 3 | NACOM GOYA - SC | SC |
| 61724241000330 | 4 | NACOM GOYA - CD | CD |
| 18467441000163 | 5 | LA FAMIGLIA - LF | LF |

```python
CNPJS_GRUPO = [
    '61724241000178',  # FB
    '61724241000259',  # SC
    '61724241000330',  # CD
    '18467441000163',  # LF
]
# Usar para excluir NFs internas de validacao NF x PO
```

---

## Locais "Indisponivel" por Empresa

> **Criados 2026-05-19** (sessao inventario). Filhos do `view_location_id` (FORA do `lot_stock_id`), `usage='internal'`, `active=True`.
> Como nao sao descendentes de `WH/Estoque`, as `stock.rule` existentes (venda/producao/replenish) NAO os enxergam — saldo fica isolado de qualquer reserva automatica.

| Company | location_id | complete_name | Parent (view_location_id) |
|---------|-------------|---------------|---------------------------|
| 1 (FB) | **31088** | `FB/Indisponivel` | 7 (FB) |
| 3 (SC) | **31089** | `SC/Indisponivel` | 21 (SC) |
| 4 (CD) | **31090** | `CD/Indisponivel` | 31 (CD) |
| 5 (LF) | **31091** | `LF/Indisponivel` | 41 (LF) |

```python
LOCAIS_INDISPONIVEL = {
    1: 31088,  # FB/Indisponivel
    3: 31089,  # SC/Indisponivel
    4: 31090,  # CD/Indisponivel
    5: 31091,  # LF/Indisponivel
}
```

**Uso (regra inventario 2026-05 — D011):**
- **Ajuste negativo CD/FB**: estoque sai de `{emp}/Estoque` (lote real) → entra em `{emp}/Indisponivel` (lote `MIGRACAO`)
- **Ajuste positivo**: estoque sai de `{emp}/Indisponivel` → entra em `{emp}/Estoque` no lote especificado

Ver `docs/inventario-2026-05/00-decisoes/D011-locais-indisponivel-por-empresa.md`.

---

## Picking Types por Company

> **Atualizado 2026-05-17** apos audit (`scripts/inventario_2026_05/00b_investigar_gotchas.py`).
> Anterior afirmava LF=16, mas id=16 e' "Conferencia (CD)" inativo da CD, nao LF.

| Company | picking_type_id (Recebimento principal) | Outros incoming |
|---------|----------------------------------------|------------------|
| FB (1) | **1** Recebimento (FB) | 52 Recebimentos Industrializacao; 54 Recebimentos Entre Filiais; 6 Devolucoes |
| SC (3) | **8** Recebimento (SC) | (nao auditado nesta fase) |
| CD (4) | **13** Recebimento (CD) | 50 Recebimentos Entre Filiais; 18 Devolucoes |
| LF (5) | **19** Recebimento (LF) | 64 Recebimentos Industrializacao; 24 Devolucoes |

---

## Operacoes de TRANSPORTE/CTe (l10n_br_operacao_id)

> **ATENCAO:** Estes IDs sao EXCLUSIVOS para lancamento de FRETE/CTe, NAO para compras genericas!

| Company | Interna Normal | Interestadual Normal | Interna Simples | Interestadual Simples |
|---------|----------------|----------------------|-----------------|----------------------|
| FB (1) | 2022 | 3041 | 2738 | 3040 |
| CD (4) | 2632 | 3038 | 2739 | 3037 |

### Mapeamento De-Para Operacoes

```python
OPERACAO_DE_PARA = {
    # FB → CD
    2022: {4: 2632},   # Interna Regime Normal
    3041: {4: 3038},   # Interestadual Regime Normal
    2738: {4: 2739},   # Interna Simples Nacional
    3040: {4: 3037},   # Interestadual Simples Nacional
    # CD → FB (inverso)
    2632: {1: 2022},
    3038: {1: 3041},
    2739: {1: 2738},
    3037: {1: 3040},
}

def _obter_operacao_correta(operacao_atual_id, company_destino_id):
    """Retorna operacao correta para a empresa destino"""
    mapa = OPERACAO_DE_PARA.get(operacao_atual_id, {})
    return mapa.get(company_destino_id)
```

---

## IDs do Frete/CTe

| Campo | Valor | Uso |
|-------|-------|-----|
| team_id | 119 | Sales Team (Frete) |
| payment_provider_id | 30 | Payment Provider padrao |
| product_id (FRETE) | 29993 | Produto FRETE - SERVICO (PRODUTO_SERVICO_FRETE_ID) |
| product_tmpl_id (FRETE) | 34 (antigo) | **VERIFICAR** - pode ter mudado junto com product_id |
| PAYMENT_TERM_A_VISTA | 2791 | account.payment.term "A VISTA" |

---

## Journals Financeiros

> Fonte completa: `app/financeiro/routes/baixas.py:JOURNALS_DISPONIVEIS` (57 journals)

### Journals Especiais (Hardcoded)

| ID | Code | Nome | Uso |
|----|------|------|-----|
| 886 | DESCO | DESCONTO CONCEDIDO | Desconto sobre titulos (limitado ao saldo) |
| 885 | ACORD | ACORDO COMERCIAL | Acordos comerciais (limitado ao saldo) |
| 879 | DEVOL | DEVOLUCAO | Devolucao de valores (limitado ao saldo) |
| 1066 | JUROS | JUROS RECEBIDOS | Juros (pode ultrapassar saldo) |
| 883 | GRAFENO | GRAFENO | Banco principal - fallback CNAB |

### Top 10 Journals por Frequencia

| ID | Code | Nome | Tipo | Freq |
|----|------|------|------|------|
| 883 | GRA1 | GRAFENO | bank | 3473 |
| 985 | AGIS | AGIS | cash | 798 |
| 879 | DEVOL | DEVOLUCAO | cash | 556 |
| 902 | BNK1 | Atacadao | cash | 470 |
| 10 | SIC | SICOOB | bank | 422 |
| 980 | SENDA | SENDAS(ASSAI) | cash | 307 |
| 885 | ACORD | ACORDO COMERCIAL | cash | 242 |
| 388 | BRAD | BRADESCO | bank | 222 |
| 966 | WMS | WMS | cash | 202 |
| 886 | DESCO | DESCONTO CONCEDIDO | cash | 161 |

---

## Tolerancias de Validacao NF x PO

| Tipo | Percentual | Constante |
|------|------------|-----------|
| Quantidade | 10% | `TOLERANCIA_QTD_PERCENTUAL = 10` |
| Preco | 0% (exato) | `TOLERANCIA_PRECO_PERCENTUAL = 0` |
| Data entrega | -5 a +15 dias | Configuravel |

---

## IDs de UI Odoo (Navegacao Web)

> **ATENCAO:** Estes IDs sao da instancia Nacom Goya e podem mudar se o Odoo for atualizado/reinstalado.
> Preferir URLs sem `menu_id`/`action` quando possivel (Odoo 17 resolve pelo `model` + `view_type`).

| ID | Tipo | Valor | Uso | Fragil? |
|----|------|-------|-----|---------|
| `cids` | Company IDs | `1-3-4` | Multi-company (FB=1, SC=3, CD=4) | Medio — muda se companies forem adicionadas |
| `menu_id` | Menu Faturamento | `124` | Necessario para breadcrumb correto | **Alto** — muda se Odoo reinstalar |
| `action` | Action Invoices | `243` | Necessario para resolucao de view | **Alto** — muda se Odoo reinstalar |

### URLs de Invoice

```python
# URL minima (PREFERIR — sem IDs frageis):
f"{ODOO_URL}/web#id={invoice_id}&cids=1-3-4&model=account.move&view_type=form"

# URL completa (fallback — com menu/action para resolucao correta):
f"{ODOO_URL}/web#id={invoice_id}&cids=1-3-4&menu_id=124&action=243&model=account.move&view_type=form"
```

### Gotcha: networkidle vs domcontentloaded

Odoo SPA mantem long-polling/WebSocket aberto. `networkidle` **NUNCA** resolve.
Sempre usar `wait_until='domcontentloaded'` + `wait_for_selector('.o_form_view')`.

**Fonte:** `app/recebimento/services/playwright_nfe_transmissao.py`, `scripts/remediar_nfe_93549_playwright.py`

---

## Como Usar

```python
# Buscar picking_type_id pela company
# CORRECAO 2026-05-17: LF e' 19, NAO 16 (id=16 e' "Conferencia (CD)" inativo da CD).
# Audit em scripts/inventario_2026_05/00b_investigar_gotchas.py. Ver tabela "Picking Types por Company" acima.
PICKING_TYPES = {
    1: 1,   # FB
    3: 8,   # SC
    4: 13,  # CD
    5: 19,  # LF (era 16, corrigido em 2026-05-17)
}
picking_type_id = PICKING_TYPES.get(company_id)

# Buscar company_id pelo CNPJ
COMPANY_IDS = {
    '61724241000178': 1,  # FB
    '61724241000259': 3,  # SC
    '61724241000330': 4,  # CD
    '18467441000163': 5,  # LF
}
company_id = COMPANY_IDS.get(cnpj_limpo)
```

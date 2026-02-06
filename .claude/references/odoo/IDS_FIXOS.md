# IDs Fixos por Empresa - Odoo

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

## Picking Types por Company

| Company | picking_type_id | Nome |
|---------|-----------------|------|
| FB (1) | 1 | Recebimento (FB) | ✅ Configurado em CONFIG_POR_EMPRESA |
| SC (3) | 8 | Recebimento (SC) | ⚠️ ID correto mas NAO configurado em CONFIG_POR_EMPRESA |
| CD (4) | 13 | Recebimento (CD) | ✅ Configurado em CONFIG_POR_EMPRESA |
| LF (5) | 16 | Recebimento (LF) | ⚠️ ID correto mas NAO configurado em CONFIG_POR_EMPRESA |

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
| product_tmpl_id (FRETE) | ~~34~~ | **VERIFICAR** - pode ter mudado junto com product_id |
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

## Como Usar

```python
# Buscar picking_type_id pela company
PICKING_TYPES = {
    1: 1,   # FB
    3: 8,   # SC
    4: 13,  # CD
    5: 16,  # LF
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

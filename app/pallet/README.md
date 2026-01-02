# Módulo de Pallet - NF de Remessa de Vasilhame

Módulo para emissão de NF de Pallet (Remessa de Vasilhame) no Odoo.

## Descobertas do Estudo (02/01/2026)

### Rastreamento: NF de Pallet ID 460182 (VAS/2025/02093)

#### Documentos/Tabelas Criados

| # | Modelo | Descrição |
|---|--------|-----------|
| 1 | `stock.picking` | Picking de expedição de vasilhame |
| 2 | `stock.move` | Movimento de estoque |
| 3 | `stock.move.line` | Linha detalhada do movimento |
| 4 | `account.move` | Fatura/NF-e |
| 5 | `account.move.line` | Linhas contábeis da fatura |

#### Conclusões Importantes

1. **NÃO precisa de Pedido de Vendas (sale.order)**
   - `sale_id` do picking: `false`
   - `invoice_origin` da fatura: `false`
   - `sale_order_count`: `0`

2. **SIM, precisa de Picking (stock.picking)**
   - Picking é OBRIGATÓRIO e criado PRIMEIRO
   - Fatura é vinculada ao picking via campo `picking_ids`
   - Tipo de operação específico para cada empresa

3. **CFOP utilizado**: 5920 (Remessa de vasilhame ou sacaria)

---

## Fluxo Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUXO NF DE PALLET                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. CREATE stock.picking                                       │
│     ├── picking_type_id: Expedição Pallet/Vasilhame           │
│     ├── partner_id: Cliente                                    │
│     ├── carrier_id: Transportadora                             │
│     └── move_ids: [(0, 0, {...})] com produto PALLET          │
│                        ↓                                        │
│  2. action_confirm (picking)                                   │
│     └── state: confirmed                                       │
│                        ↓                                        │
│  3. action_assign (picking)                                    │
│     └── state: assigned                                        │
│                        ↓                                        │
│  4. Preencher qty_done nas stock.move.line                     │
│                        ↓                                        │
│  5. button_validate (picking)                                  │
│     └── state: done                                            │
│                        ↓                                        │
│  6. CREATE account.move                                        │
│     ├── move_type: out_invoice                                 │
│     ├── journal_id: REMESSA DE VASILHAME                       │
│     ├── fiscal_position_id: REMESSA DE VASILHAME               │
│     ├── picking_ids: [(6, 0, [picking_id])]                    │
│     └── invoice_line_ids: [(0, 0, {...})]                      │
│                        ↓                                        │
│  7. action_post (account.move)                                 │
│     └── Emite NF-e (CFOP 5920)                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Vinculação entre Documentos

```
account.move (NF) ──── picking_ids ────→ stock.picking
                                              │
stock.picking ────── move_ids ─────→ stock.move
                                              │
stock.move ──── move_line_ids ──→ stock.move.line
```

---

## Configuração por Empresa

### NACOM GOYA - CD (company_id: 4)

| Campo | ID | Nome |
|-------|-----|------|
| picking_type_id | 84 | Expedição Pallet (CD) |
| sequence_code | - | CD/PALLET |
| location_id | 32 | CD/Estoque |
| location_dest_id | 5 | Parceiros/Clientes |
| journal_id | 831 | REMESSA DE VASILHAME |
| fiscal_position_id | 46 | REMESSA DE VASILHAME |

### NACOM GOYA - FB (company_id: 1)

| Campo | ID | Nome |
|-------|-----|------|
| picking_type_id | 93 | Expedição Vasilhame (FB) |
| sequence_code | - | FB/SAI/VAS |
| location_id | 8 | FB/Estoque |
| location_dest_id | 5 | Parceiros/Clientes |
| journal_id | 390 | REMESSA DE VASILHAME |
| fiscal_position_id | 17 | REMESSA DE VASILHAME |

### NACOM GOYA - SC (company_id: 3)

| Campo | ID | Nome |
|-------|-----|------|
| picking_type_id | 90 | Expedição Vasilhame (SC) |
| sequence_code | - | SC/SAI/VAS |
| location_id | 22 | SC/Estoque |
| location_dest_id | 5 | Parceiros/Clientes |
| journal_id | 810 | REMESSA DE VASILHAME |
| fiscal_position_id | 37 | REMESSA DE VASILHAME |

---

## Produto PALLET

| Campo | Valor |
|-------|-------|
| product_id | 28108 |
| Código | 208000012 |
| Nome | PALLET |
| Preço unitário | R$ 35,00 |
| account_id | 26846 (1150100012 FATURAMENTO FISICO FISCAL) |
| NCM | 44152000 |

---

## Condição de Pagamento

| Campo | Valor |
|-------|-------|
| invoice_payment_term_id | 2800 |
| Nome | A VISTA |

---

## Timeline de Exemplo (CD/CD/PALLET/03841)

| Horário | Documento | Ação |
|---------|-----------|------|
| 19:04:51 | stock.picking | Criado |
| 19:04:51 | stock.move | Criado |
| 19:04:57 | stock.move | done |
| 19:04:59 | stock.picking | done (validado) |
| 19:06:40 | account.move | Criado |
| 19:06:40 | account.move | posted (NF-e emitida) |

**Tempo total**: ~2 minutos

---

## Uso do Serviço

```python
from app.pallet.services import emitir_nf_pallet

# Emitir NF de 17 pallets
resultado = emitir_nf_pallet(
    empresa='CD',
    cliente_id=88586,           # ATACADAO 341
    transportadora_id=1208,     # Cazan Transportes
    quantidade=17,
    dry_run=False               # True para simular
)

if resultado['sucesso']:
    print(f"Picking: {resultado['picking']['name']}")
    print(f"NF-e: {resultado['fatura']['l10n_br_numero_nota_fiscal']}")
else:
    print(f"Erro: {resultado['erro']}")
```

---

## Campos Importantes da NF de Pallet

### account.move (Fatura)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| move_type | char | `out_invoice` (fatura de saída) |
| journal_id | many2one | Diário REMESSA DE VASILHAME |
| fiscal_position_id | many2one | Posição fiscal REMESSA DE VASILHAME |
| picking_ids | many2many | Pickings vinculados |
| l10n_br_carrier_id | many2one | Transportadora para NF-e |
| l10n_br_numero_nota_fiscal | char | Número da NF-e emitida |
| l10n_br_chave_nf | char | Chave de acesso da NF-e |
| l10n_br_situacao_nf | char | Situação (autorizado, cancelado, etc) |

### stock.picking (Picking)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| picking_type_id | many2one | Tipo de operação (Expedição Pallet) |
| location_id | many2one | Local de origem (Estoque) |
| location_dest_id | many2one | Local de destino (Clientes) |
| partner_id | many2one | Cliente |
| carrier_id | many2one | Transportadora |
| sale_id | many2one | **SEMPRE FALSE** para pallet |
| origin | char | **SEMPRE FALSE** para pallet |

---

## Estrutura do Módulo

```
app/pallet/
├── __init__.py
├── README.md                          # Esta documentação
└── services/
    ├── __init__.py
    └── emissao_nf_pallet.py          # Serviço principal
```

---

## Referências

- NF de Pallet rastreada: ID 460182 (VAS/2025/02093)
- Picking rastreado: ID 295040 (CD/CD/PALLET/03828)
- Estudo realizado em: 02/01/2026

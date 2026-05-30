# T21 — PILOTO E2E DIRETO (4870112, 10 cx) — em andamento

**Status**: 🟡 in_progress (PO + SO confirmadas; aguardando criação MO LF manual conforme D20)
**Sessão**: 2026-05-29
**Executor**: Claude via XML-RPC (PO e SO) + Rafael (autorização) + PCP LF (MO manual pendente)

---

## Sequência executada nesta sessão

### Pré-requisitos extras descobertos / corrigidos

| Achado | Ação |
|---|---|
| `res.company.warehouse_id` False em FB e LF (config inter-company incompleta — T01 não cobriu) | ✅ Write FB.warehouse_id=1, LF.warehouse_id=4 (autorizado Rafael) |
| Operação 1917 está restrita ao partner 35 LF, mapeia CFOP intra-estadual 1124 (id=11) | ✅ Setada na linha da PO |
| CFOP da linha não populou automaticamente via onchange XML-RPC | ✅ Setado manualmente id=11 (CFOP 1124) |
| `res.company.warehouse_id` faltava → button_confirm da PO falhou primeira tentativa | ✅ Resolvido |

### PO 42659 (C2619775) em cmp=FB ✅

```
partner_id                     = [35, 'LA FAMIGLIA - LF']
company_id                     = [1, 'NACOM GOYA - FB']
picking_type_id                = [52, 'FB: Recebimentos Industrialização (FB)']  ← correção do problema histórico (pt=1)
l10n_br_tipo_pedido            = serv-industrializacao
l10n_br_operacao_id            = [1917, 'Industrialização efetuada por outra empresa (ICMS 51)']
state                          = purchase
amount_total                   = R$ 350,00
date_order                     = 2026-05-29 07:08:04
```

Linha 129222:
```
product_id        = [27834, '[4870112] MOLHO SHOYU - PET 12X1,01 L - CAMPO BELO']
product_qty       = 10 CAIXAS
price_unit        = R$ 35,00
l10n_br_cfop_id   = [11, '1124 - Industrialização efetuada por outra empresa']
l10n_br_operacao_id = [1917, ...]
```

### Picking RECEB/FB/IND/00018 em FB ✅

```
picking_type      = pt=52 RECEB/FB/IND ← CORREÇÃO HISTÓRICA confirmada
state             = assigned
origin            = C2619775
location_id       = Parceiros/Estoque LF
location_dest_id  = FB/Estoque
```

Move 1170392: qty=10 cx do PA 4870112, state=assigned, esperando o produto chegar da LF.

### SO 73424 (VLF2600001) em cmp=LF ✅ (inter-company DISPAROU)

```
company_id         = [5, 'LA FAMIGLIA - LF']
partner_id         = [1, 'NACOM GOYA - FB']
client_order_ref   = C2619775                  ← referência à PO de origem (FB)
warehouse_id       = [4, 'LF']
amount_total       = R$ 350,00
state              = sale
user_id            = False (criado por OdooBot via sale_purchase_inter_company_rules)
```

⚠ **l10n_br_operacao_id, l10n_br_tipo_pedido**: o módulo inter-company NÃO propagou esses campos do PO para a SO (criou SO com `tipo_pedido=venda` genérico, `operacao=False`, CFOP da linha=False). Vai precisar ser ajustado antes da NF retorno (T25).

Linha 520956: produto 27834, qty=10, price=35, `route_id=False`.

### Picking LF/OUT/00020 em LF ⏸️

```
picking_type      = LF: Ordens de Entrega
state             = confirmed (aguardando saldo em LF/Estoque)
origin            = VLF2600001
location_id       = LF/Estoque
location_dest_id  = Parceiros/Clientes
```

Move 1170394: qty=10 PA, **procure_method=make_to_stock** (rota MTO chain não disparou em LF). Conforme D20, MO será criada manualmente.

---

## Validações cruzadas (testes do roadmap)

| Item | Esperado | Real | Status |
|---|---|---|---|
| SO em LF criada via inter-company | sim | sim (id=73424) | ✅ |
| Picking RES (pt=75) em FB | sim | **NÃO** (não foi gerado pelo subcontract) | ⚠️ |
| Stock.rules criadas auto na rota 162 (D16) | sim | **NÃO** (caminho A do D16 falhou) | ❌ — confirma fallback |
| Picking em FB recebe com pt=52 (não pt=1) | sim | **SIM** ✓ (RECEB/FB/IND/00018) | ✅ — CORREÇÃO HISTÓRICA |
| MO disparada via MTO em LF | sim | **NÃO** (rota MTO global sem rules em LF) | ❌ → D20 caminho concorrente |

---

## Achado crítico: T11 escolheu rota errada

O produto 27834 tem `route_ids=[134, 1]`. A rota 1 (MTO global) tem 46 rules **todas em cmp=FB**, zero em cmp=LF.

A rota que faria MTO funcionar em LF é a **132 "Reabastecer no Pedido (PSE) - LF"** (rules 20/35/36 com procure=`mts_else_mto`), `product_selectable=True`, e **0/19 PAs LF amostrados a têm**. Histórico confirma: MOs em LF são manuais (PCP LF / Edilane).

T11 anterior (testes/T11-resultado.md): adicionou rota 1 global ao produto. Para automatização real do procurement MTO em LF, deveria ter sido a rota 132. Não bloqueia o piloto (D20 caminho concorrente), mas vale registrar como dívida técnica do rollout futuro.

---

## Próximo passo

**T21b — Criar MO LF manualmente** (D20):

Especificação:
```
product_id      = 27834 ([4870112] MOLHO SHOYU - PET 12X1,01 L)
product_qty     = 10
bom_id          = 3695 (LF normal hierárquica, consumption=strict pós-T10)
company_id      = 5 (LF)
origin          = "C2619775 / VLF2600001"  (rastreabilidade até PO/SO)
```

Quem cria:
- **Opção A**: Claude via XML-RPC (mantém automação, gera MO em state=draft, depois confirm)
- **Opção B**: Rafael/PCP LF via UI Odoo (pattern histórico Edilane)

A MO produzirá BATELADA DE SHOYU como sub-MO (BoM 3646 filha) consumindo os 9 químicos + 1 MP shoyu_tradicional + ÁGUA (insumo LF). Resultado: 10 cx do PA em LF/Estoque, que destrava o picking LF/OUT/00020 para reservar e ser validado.

---

## Próximas validações pendentes (pós-MO)

1. MO LF produz 10 cx → entra LF/Estoque
2. Picking LF/OUT/00020 reserva (state=assigned)
3. Rafael valida picking OUT → 10 cx saem LF/Estoque
4. Rafael emite NF retorno LF→FB via CIEL IT (CFOP 5124 PA + 17 linhas 5902 + sobras 5903) — T25
5. DFe chega em FB → CIEL IT mapeia para picking RECEB/FB/IND/00018 (pt=52!) — T26
6. Validação dos saldos (`Q1-Q5` — T29)

---

## Anotações para retomada / sessões futuras

- IDs criados: PO=42659, SO=73424, picking_in_FB=322039 (RECEB/FB/IND/00018), picking_out_LF=322041 (LF/OUT/00020)
- l10n_br fields da SO LF ficaram False — pode precisar ajuste antes de T25 (CIEL IT pode reclamar)
- A operação 1917 está restrita ao partner 35 — funcionou bem para PO. Em LF, o equivalente seria operação de SAÍDA (CFOP 5124) — a verificar
- D20 resolve A05 (PA → LF/Estoque); LF/PA de Terceiros (31093) fica reservada para uso futuro
- Não foi gerado picking RES (pt=75) — confirma que o módulo subcontract NÃO disparou para esse fluxo (era esperado para D16 mas falhou)

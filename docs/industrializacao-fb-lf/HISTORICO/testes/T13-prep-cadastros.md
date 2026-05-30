# T13 — Preparação de cadastros (diagnóstico exaustivo)

**Status**: ✅ S0 completo e validado (2026-05-28)
**Executor**: Claude (read-only XML-RPC + 2 writes autorizados)

## Objetivo

Antes de Rafael abrir T13, validar exaustivamente que tudo o que T13 precisa está cadastrado e consistente. Documentar achados.

---

## 1) Picking types relevantes

| ID | Sequence | Code | Cmp | Src | Dst | Status |
|---|---|---|---|---|---|---|
| 1 | RECEB/FB | incoming | FB | — | FB/Estoque | ✅ |
| 52 | RECEB/FB/IND | incoming | FB | Em Transito Industrialização | FB/Estoque | ✅ |
| 53 | FB/SAI/IND | outgoing | FB | FB/Estoque | Em Transito Industrialização | ✅ |
| 64 | LF/RECEB/IND | incoming | LF | Em Transito Industrialização | LF/Estoque | ✅ |
| 74 | SBC | mrp_operation | FB | Local de subcontratação | Estoque Virtual/Produção | ✅ (T05) |
| 75 | RES | outgoing | FB | FB/Estoque | Local de subcontratação | ✅ |
| 80 | SBC | mrp_operation | LF | Local de subcontratação | Estoque Virtual/Produção | ✅ (T06) |

## 2) Routes

| ID | Nome | Active | Stock.rules | Status |
|---|---|---|---|---|
| 1 | MTO | True | 46 | ✅ (T11 adicionou ao produto) |
| 134 | Fabricar | True | 2 | ✅ (já no produto) |
| **162** | FB: Reposição para subcontratação | **True** | 0 | ✅ ativada nesta sessão |
| 166 | LF: Reposição para subcontratação | False | 0 | ⛔ T09 skipped |

**Importante**: WH FB (id=1) tem `subcontracting_to_resupply=True` e `subcontracting_route=[162]`. Ao primeiro PO inter-company que disparar fluxo subcontract, o módulo `mrp_subcontracting` vai consultar essa rota — agora ativa.

## 3) Locations

| ID | Complete Name | Cmp | Usage | Active |
|---|---|---|---|---|
| 8 | FB/Estoque | FB | internal | ✅ |
| 41 | LF | LF | view | ✅ |
| 42 | LF/Estoque | LF | internal | ✅ |
| 31088 | FB/Indisponivel | FB | internal | ✅ |
| 31091 | LF/Indisponivel | LF | internal | ✅ |
| **31092** | LF/Materiais de Terceiros | LF | internal | ✅ (T02) |
| **31093** | LF/PA de Terceiros | LF | internal | ✅ (T03) |
| 26489 | Estoque Virtual/Em Trânsito Industrialização | — | transit | ✅ |
| 30713 | Locais Fisicos/Local de subcontratação | FB | internal | ✅ |

## 4) Companies (inter-company)

| ID | Nome | rule_type | intercompany_user |
|---|---|---|---|
| 1 | NACOM GOYA - FB | **sale_purchase** | OdooBot | ✅ (T01) |
| 5 | LA FAMIGLIA - LF | **sale_purchase** | OdooBot | ✅ (T01) |

## 5) Partner LF (id=35) em cmp=FB

- `property_stock_subcontractor` = LF/Materiais de Terceiros (31092) ✅ (T04)

## 6) Produto piloto 4870112 (id=27834)

- `active` = True
- `type` = product (storable)
- `weight` = 13.00 kg
- `barcode` = 7898075644167 (GTIN válido — Schema 225 OK)
- `route_ids` = [134 Fabricar LF, 1 MTO global] ✅ (T11)
- `categ` = TODOS / PRODUTO ACABADO / MOLHOS / LIQUIDOS / PET 1,01 LT (id=193)
- `purchase_ok` = False, `sale_ok` = True

## 7) BoMs ativas do produto piloto e BATELADA

| ID | Produto | Type | Cmp | Cons | Status |
|---|---|---|---|---|---|
| **3695** | [4870112] PA MOLHO SHOYU | normal | LF | **strict** | ✅ (T10) |
| **3646** | [3800018] BATELADA DE SHOYU | normal | LF | **strict** | ✅ (T10b) |
| ~~14833~~ | [4870112] PA (subcontract antigo) | subcontract | FB | warning | **⛔ desativada nesta sessão (T33 antecipada)** |

BoMs antigas (14411, 14583, 14632, 13691): todas `active=False` (legado).

## 8) Supplierinfo 6319 (PA inter-company subcontract)

```
partner_id      = [35, 'LA FAMIGLIA - LF']
price           = 35.00 BRL ✅ (D03)
product_tmpl_id = [42282, '[4870112] MOLHO SHOYU - PET 12X1,01 L - CAMPO BELO']
company_id      = [1, 'NACOM GOYA - FB']
is_subcontractor = True ✅
min_qty         = 1.0
```

---

## 9) Cadastro fiscal dos 17 componentes + PA

| Código | Nome | Weight | Barcode | NCM | Origem |
|---|---|---:|---|---|---:|
| 4870112 | MOLHO SHOYU - PET 12X1,01 L (PA) | 13.00 | 7898075644167 | 21031090 | 0 |
| 210030322 | ROTULO MOLHO SHOYU PET 1,01 L | 0.01 | — | 48211000 | 0 |
| 210030110 | TAMPA PLASTICA VERMELHA | 1.00 | — | 39235000 | 0 |
| 210030203 | CAIXA DE PAPELAO | 0.30 | — | 48191000 | 0 |
| 207210014 | ETIQUETA BRANCA | 0.01 | — | 48211000 | 0 |
| 208000008 | FILME STRECH | 1.00 | — | 39201099 | 0 |
| 208000010 | FITA ADESIVA | 0.01 | — | 39191090 | 0 |
| 210030010 | FRASCO INCOLOR 1,01 L | 1.00 | — | 39233090 | 0 |
| 104000004 | BENZOATO DE SODIO | 1.00 | — | 29163110 | 2 |
| 104000007 | CORANTE CARAMELO | 1.00 | — | 17029000 | 2 |
| 104000015 | SAL SEM IODO | 1.00 | — | 25010090 | 0 |
| 104000018 | SORBATO DE POTASSIO | 1.00 | — | 29161911 | 0 |
| 104000002 | **ACIDO CITRICO** | **0.00** ⚠ | — | 29181400 | 2 |
| 105000023 | ANTIESPUMANTE AFE 1520 | 1.00 | — | 34029029 | 0 |
| 105000024 | ACUCAR CRISTAL | 1.00 | — | 17019900 | 0 |
| 105000039 | AROMA SHOYU ST 2175 | 1.00 | — | 33021000 | 0 |
| 104000017 | **AGUA** (insumo LF) | **0.00** ⚠ | — | 22011000 | 0 |
| 105000022 | MOLHO SHOYU TRADICIONAL | 1.00 | — | 21031090 | 0 |

**Resumo fiscal**:
- ✅ NCM presente em todos
- ✅ Origem presente em todos
- ⚠ **2 produtos com weight=0**: ACIDO CITRICO (vai na remessa) e ÁGUA (NÃO vai na remessa)
- ✅ Barcode não conflita com default_code (Schema 225 G035 OK)

**Implicação T22**: corrigir weight do ACIDO CITRICO antes de emitir a NF de remessa (ou aceitar que CIEL IT/SEFAZ pode reclamar). Adicionar como pequena task derivada.

---

## 10) Estoque FB/Estoque (livre) vs demanda 10 cx do PA

| Código | Need (10 cx) | FB DISP | OK? |
|---|---:|---:|---:|
| 207210014 ETIQUETA BRANCA | 10 un | 341.554 un | ✅ |
| 208000008 FILME STRECH | 0.12 kg | 1.262 kg | ✅ |
| 208000010 FITA ADESIVA | 8.60 m | 58.267 m | ✅ |
| 210030010 FRASCO INCOLOR | 120 un | 7.392 un | ✅ |
| **210030110 TAMPA PLASTICA** | **120 un** | **0 (tudo reservado)** | ❌ |
| 210030203 CAIXA DE PAPELAO | 10 un | 616 un | ✅ |
| 210030322 ROTULO | 120 un | 7.392 un | ✅ |
| 104000002 ACIDO CITRICO | 0.13 kg | 2.324 kg | ✅ |
| 104000004 BENZOATO | 0.13 kg | 658 kg | ✅ |
| 104000007 CORANTE | 1.92 kg | 135 kg | ✅ |
| 104000015 SAL SEM IODO | 5.34 kg | 8.581 kg | ✅ |
| 104000018 SORBATO | 0.13 kg | 331 kg | ✅ |
| **105000023 ANTIESPUMANTE** | **0.03 kg** | **0 (tudo reservado)** | ❌ |
| 105000024 ACUCAR CRISTAL | 1.28 kg | 1.880 kg | ✅ |
| **105000039 AROMA SHOYU** | **0.58 kg** | **0 (tudo reservado)** | ❌ |
| 105000022 SHOYU TRADICIONAL | 24.64 L | 1.711 L | ✅ |

**Resumo estoque**: 13/16 OK em FB/Estoque livre. 3 totalmente reservados (mas com saldo em outras locations):

| Componente faltante em FB livre | Onde tem saldo |
|---|---|
| 210030110 TAMPA | LF/Estoque (73.148 un), FB/Indisponivel (1.379.033 un) |
| 105000023 ANTIESPUMANTE | LF/Estoque (38.58 kg) |
| 105000039 AROMA | LF/Estoque (489.74 kg), FB/Indisponivel (4.208 kg) |

**Não bloqueia T13** (que usa produto qualquer, não 4870112). **Bloqueia T21** (piloto real com 10 cx do 4870112). Caminhos para T21:
- (a) Liberar reservas dos 3 em FB/Estoque (cancelar/postergar outras MOs)
- (b) Transferir saldo de LF/Estoque ou FB/Indisponivel para FB/Estoque livre
- (c) Reduzir piloto para qty menor que ative limite (mas D08 fixou 10 cx)

Decidir antes de T21 — não bloqueia T13.

---

## 11) Confronto BoM 14833 antiga vs Opção 2 — DESATIVADA preventivamente

Antes desta sessão:
- 14833 ATIVA (subcontract, FB, sub=[35 LF], sequence=25)
- 3695 ATIVA (normal, LF, sequence=61)

Quando PO FB→LF for criada, o Odoo precisa escolher entre subcontract path (14833) e inter-company path (3695). Risco de escolher o caminho errado.

**Verificação CHK1**:
- 0 MOs ativas usando 14833
- 0 MOs done recentes usando 14833 (últimas 5 = 0)
- 0 pickings ativos pt=74 FB Subcontratação

**Desativação segura confirmada**. Executada nesta sessão (T33 antecipada conforme decisão Rafael).

---

## Resumo final S0

✅ **Pronto para T13**. Todos os pré-requisitos técnicos satisfeitos.

⏸️ Bloqueio humano restante: **A03 — janela do piloto** (Rafael decide).

⚠️ Tasks derivadas opcionais (não bloqueiam T13):
- Corrigir weight=0 do 104000002 ACIDO CITRICO antes de T22
- Resolver disponibilidade dos 3 componentes para T21 (post-T13)

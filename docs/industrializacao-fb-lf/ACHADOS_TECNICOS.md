# ACHADOS TÉCNICOS — Industrialização FB↔LF (Odoo / CIEL IT)

> Fatos **verificados ao vivo** (PROD, 2026-05-29) que fundamentam a `DIRETRIZ.md`. Tudo aqui é o "como o Odoo/CIEL IT realmente decide", não suposição.

---

## 1. Como a contabilização é determinada (as duas camadas)

Com **AVCO + valoração Tempo Real** (`product.category.property_valuation='real_time'`, `cost_method='average'`), **cada `stock.move` gera um `account.move` automático**. Para um material entrando/saindo há **dois** documentos contábeis distintos:

### (1) FATURA (NF) — `account.move` fiscal → **CONFIGURÁVEL**
As contas vêm de uma cadeia, **não** da categoria:
- **Operação fiscal** (`l10n_br_ciel_it_account.operacao`) define CFOP + impostos + `tipo_pedido` + `movimento_estoque`. **NÃO tem campo de conta GL** (enumerados todos os ~130 campos).
- **CFOP → posição fiscal**, e a **posição fiscal remapeia contas** (`account.fiscal.position.account`: `account_src → account_dest`). Ex. real: fp **86** mapeia `3201000002 VARIAÇÕES POSITIVAS → 1150100011 RECEBIMENTO FÍSICO FISCAL`.
- **tipo_pedido → journal** (modelo `l10n_br_ciel_it_account.tipo.pedido.diario`), e o **journal carrega contas**: `default_account_id` + `account_no_payment_id`. Ex. real: journal **998** (ENTRADA-RETRABALHO) tem `account_no_payment_id = 1150200002`.

### (2) VALORAÇÃO DE ESTOQUE (SVL) — `account.move` no diário ESTOQUE → **CONFIGURÁVEL (por empresa)**
A conta vem **exclusivamente da categoria do produto**, e essas contas são **company-dependent (`ir.property`)**:

| Campo da `product.category` | Papel |
|---|---|
| `property_stock_valuation_account_id` | conta de ativo (valoração) |
| `property_stock_account_input_categ_id` | contrapartida na ENTRADA |
| `property_stock_account_output_categ_id` | contrapartida na SAÍDA |
| `property_stock_account_production_cost_id` | conta de produção/elaboração |

**Prova de que é por empresa** — mesma categoria (314 GALAO), contas diferentes:

| Empresa | Valoração | Entrada | Saída |
|---|---|---|---|
| FB | 1150100007 PRODUTO-ACABADO | 1150100011 RECEB. FÍSICO FISCAL | 1150100012 FATUR. FÍSICO FISCAL |
| **LF** | 1150100007 PRODUTO-ACABADO | **3201000002 VARIAÇÕES POSITIVAS** | **3201000003 VARIAÇÕES NEGATIVAS** |
| CD | … | 3201000002 | 3201000003 |

→ É **por aqui** (contas de categoria no contexto da LF, via `ir.property`) que se altera a contabilização de estoque da LF, **sem afetar FB/CD/SC**. Isso explica o lançamento que víamos na entrada da LF: `D MATÉRIA-PRIMA / C 3201000002 VARIAÇÕES POSITIVAS` — o crédito é a **conta de entrada da categoria NA LF**.

### Onde a valoração de estoque **NÃO** se configura (verificado por exaustão)
- `stock.location.valuation_in/out_account_id`: **sem efeito para locations `internal`** (texto oficial do Odoo); e **nenhuma** location no grupo tem esses campos setados.
- `res.company.account_estoque_{tipo}_id` (89 contas CIEL IT por tipo de produto): **vazias na LF** → LF usa a categoria.
- `stock.rule`, `stock.picking.type`: **sem campo de conta**.
- `base.automation`: só 1 (arquivar CT-e), nada de estoque.
- Operação fiscal/CFOP: sem campo de conta de valoração.

---

## 2. Mecanismo NACOM já existente: "Transferir TERCEIROS"

Existe um mecanismo NACOM para movimentar material de terceiros com contabilização própria (referência — **não** é o caminho da diretriz, mas comprova que terceiros é tratável):
- **Server action 1899 "Transferir TERCEIROS"** (botão em `stock.picking`) → chama o método `action_movimentar_estoque_terceiro()`.
- Cria um **picking-companheiro** (campo `picking_terceiro_id`) que movimenta para/da árvore de locations **`Parceiros/Estoques em poder de terceiros/{CNPJ}`** (ex.: id 30720 = estoque em poder da LF).
- Já roda em pickings de **entrada e saída** (FB/IN, LF/IN têm companheiro). O método (Python no servidor) é quem compõe o lançamento em `1150200002`.

> A `DIRETRIZ` prefere a via de **configuração das contas de categoria por-empresa** (mais simples, sem depender do método/botão), justamente porque a LF não tem estoque próprio.

---

## 3. Incidente `rule_type` (gotcha — não repetir)

`res.company.rule_type='sale_purchase'` (módulo `sale_purchase_inter_company_rules`) é **company-wide** e dispara SO espelho em **toda** PO inter-company cuja contraparte/fornecedor é FB ou LF — **inclusive transferências CD↔FB**. Valores do campo: `not_synchronize / invoice_and_refund / sale / purchase / sale_purchase`. **Estado correto = `not_synchronize`** (FB e LF). Detalhe na memória do Claude Code `gotcha-rule-type-intercompany-company-wide`.

---

## 4. Quirks CIEL IT relevantes

- **`action_gerar_po_dfe` herda a company do USER autenticado** (não do DFe). Rafael (uid=42, company principal=FB) → PO sai em FB. Forçar `allowed_company_ids=[5]` ou autenticar como user com company principal=LF.
- **`action_liberar_faturamento`** dispara o robô CIEL IT que **cria a invoice em ~90s**.
- **Pré-condições para liberar faturamento** no picking de saída: `incoterm=6` (CIF) + `carrier_id=996` + operação na linha + CFOP na linha + `res.company.warehouse_id` setado.
- `amount_total=0` quando ICMS CST=51 (suspenso): a NF de remessa carrega valor em `amount_untaxed` (ex.: 725676 = R$ 2.797,85), mas total a pagar = 0. **NF saída SEFAZ-autorizada NÃO cancela via XML-RPC** (evento formal, janela ~24h).
- `l10n_br_operacao_id` / `l10n_br_tipo_pedido` **NÃO propagam** para SO criada via inter-company (ficam False).

---

## 5. Mapa de IDs

### Empresas / parceiros / armazéns
- Empresas: **FB=1** (CNPJ 61.724.241/0001-78, encomendante), **LF=5** (CNPJ 18.467.441/0001-63, industrializadora), SC=3, CD=4.
- Partners: FB=1 (global), CD=34, **LF=35** (LF em cmp=FB).
- `res.company.warehouse_id`: FB=1, LF=4. Armazéns: WH FB=1, WH LF=4.

### Locations
| id | nome | papel |
|---|---|---|
| 8 | FB/Estoque | estoque FB |
| 42 | LF/Estoque | estoque LF |
| 26489 | Em Trânsito Industrialização (virtual, cmp 0) | **par-chave: deve zerar a cada ciclo** |
| 31092 | LF/Materiais de Terceiros (criada T02, internal, cmp 5) | destino dos insumos remetidos |
| 31093 | LF/PA de Terceiros (criada T03, internal, cmp 5) | onde o PA da MO LF cai |
| 53 | LF/Pré-Produção | origem dos componentes da MO |

### Picking types
| id | nome | papel |
|---|---|---|
| 53 | FB/SAI/IND | remessa FB→LF (correto) |
| 64 | LF/RECEB/IND | recebimento da remessa em LF (ocioso desde ago/2024) |
| 98 | LF/SAI/IND/RET (criada T07: src=31093, dst=26489, return=64) | saída do retorno LF→FB |
| 52 | RECEB/FB/IND (src=26489) | recebimento do retorno em FB (**correto**; hoje usam o genérico **pt=1**, errado) |

### Produto / BoM
- PA piloto **4870112** (product.product 27834, template 42282, categ 193). BoM hierárquica: **3695** (PA, normal LF, strict) → **3646** (BATELADA DE SHOYU, semi 3800018, strict). BoM subcontract antiga **14833** = desativada.
- Remessa = **16 componentes** (7 embalagens + 8 químicos + 1 MP shoyu_tradicional 105000022). 8 químicos: BENZOATO, CORANTE, SAL, SORBATO, ÁC. CÍTRICO, ANTIESPUMANTE, AÇÚCAR, AROMA. **ÁGUA (104000017)** = único insumo próprio LF (tipo `consu`). Valor agregado **R$ 35/cx** (supplierinfo 6319).

### Fiscal
- CFOPs: **5901/1901** (remessa/entrada), **5124** (PA), **5902** (insumos consumidos), **5903** (insumos não aplicados/sobra) — e entradas 1124/1902/1903.
- Posições fiscais: FB **25** (REMESSA P/ INDUSTRIALIZAÇÃO), LF **131** (ENTRADA REMESSA IND. LF), **91** (SAÍDA-PERDAS/5903), **97** (ENTRADA RETORNO NÃO APLICADO/1903).
- Operações: 1917 (PO FB, ICMS 51), 2686 (PO LF entrada, serv-industrializacao). CFOP ids: 11=1124, 101=1901, 307=5124, 391=5901.

### Contas (account.account)
| code | nome | contexto |
|---|---|---|
| 1150100001 | MATÉRIA-PRIMA | valoração MP (próprio) |
| 1150100002 | MATERIAL DE EMBALAGEM | valoração embalagem (próprio) |
| 1150100007 | PRODUTO-ACABADO | valoração PA (próprio) |
| 1150100004 | PRODUTO EM ELABORAÇÃO | produção |
| 1150100011 | RECEBIMENTO FÍSICO FISCAL | transitória entrada |
| 1150100012 | FATURAMENTO FÍSICO FISCAL | transitória saída |
| **1150200001** | **MATERIAL EM TERCEIROS** | **alvo (valoração terceiros LF); hoje saldo R$ 0** |
| **1150200002** | **( − ) MATERIAL DE TERCEIROS** | **contrapartida terceiros (net-zero)** |
| 3201000002 / 3201000003 | VARIAÇÕES POSITIVAS / NEGATIVAS DE ESTOQUE | contrapartidas atuais (erradas) da categoria na LF |

### Sintomas contábeis na FB (28/05/2026, postados)
- 1150100002 MAT. EMBALAGEM = R$ 21.938.384,94
- 1150100011 RECEB. FÍSICO FISCAL = R$ −1.488.150.962,96 (histórico, vários fluxos)
- 1150200001 MATERIAL EM TERCEIROS = **R$ 0,00** (confirma que remessas 5901 nunca foram contabilizadas como industrialização)
- Passivo medido só do MOLHO SHOYU PET: **R$ 785.569,62** (1.057 stock.moves de componentes somados indevidamente ao Ativo Estoque FB).

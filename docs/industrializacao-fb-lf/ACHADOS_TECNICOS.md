# ACHADOS TÉCNICOS — Industrialização FB↔LF (Odoo / CIEL IT)

> **Papel deste doc:** mecanismo Odoo/CIEL IT + **IDs/constantes** (contas, operações, journals, locations, picking types). Desenho-alvo e decisões = `SOT_OPERACOES.md`. Índice geral: `README.md`.
> Fatos **verificados ao vivo** (PROD) — "como o Odoo/CIEL IT realmente decide", não suposição. (A `DIRETRIZ.md` original foi para `HISTORICO/`.)

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
- **Criar remessa pt53 via XML-RPC (2026-06-01, validado E2E):** o picking **DEVE** ter `partner_id=35` (LF) — senão `button_validate` falha ao auto-criar o picking-companheiro **"Transferir TERCEIROS"** (server action 1899, ver §2) com `Field Destination Location (location_dest_id) not set`. Demais gotchas (UoM rounding, cap no saldo, lote pinado, `skip_backorder`) em `RUNBOOK_PILOTO_4870112.md §0.6` (G-REM-1..4).
- **Transmissão SEFAZ** = `transmitir_nfe_via_playwright(invoice_id, odoo, logger)` (`app/recebimento/services/playwright_nfe_transmissao.py`) — XML-RPC puro falha (campos `l10n_br` stale → SEFAZ 225); Playwright força recompute via UI.

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
- 1150200001 MATERIAL EM TERCEIROS = **R$ 0,00** (NÃO é "remessas nunca contabilizadas" — ver ACHADO 2026-05-30 abaixo: o sistema usa `5101010001`, não esta conta)
- Passivo medido só do MOLHO SHOYU PET: **R$ 785.569,62** (1.057 stock.moves de componentes somados indevidamente ao Ativo Estoque FB).

---

## ACHADO 2026-05-30 — A saída da FB ESTÁ correta (usa conta de compensação `5101010001`)

> **Correção de premissa.** Verificado ao vivo em remessas pt53 reais (FB/SAI/IND/01606=piloto, 01607, 01608) + NFs fiscais RPI/2026/00242-244. Scripts: `scripts/e2e_saida_fb_etapa1.py`, `scripts/teste_lever_saida_fb.py`.

A remessa FB→LF (Etapa 1, CFOP 5901) gera **DUAS camadas** que, combinadas, lançam **NET**:
- **SVL (valoração):** `D 1150100012 FATUR. FÍSICO FISCAL / C 1150100002 MAT. EMBALAGEM`
- **NF fiscal (fp 25 / journal 17 REMESSA P/ INDUSTRIALIZAÇÃO):** `D 5101010001 REMESSA INDUSTRIALIZAÇÃO (ATIVA) / C 1150100012`
- **NET:** `D 5101010001 REMESSA INDUSTRIALIZAÇÃO (ATIVA) / C 1150100002` → a transitória `1150100012` **zera**.

**`5101010001` é `asset_current`** (Ativo Circulante) — conta de **compensação** de uma família completa: `51010xx` (ATIVA) ↔ `51020xx` (PASSIVA) para remessa industrialização, retorno, comodato, conserto, consignação, exposição, demonstração, armazenagem, transf. entre empresas, retrabalho, etc.

→ **A saída da FB reclassifica corretamente** o material de estoque físico (`1150100002`) para o controle de remessa (`5101010001`). FB continua dona. **NÃO usa `1150200001`** — a `DIRETRIZ` mirou a conta errada; o sistema já tem a família `51010xx` funcionando.

→ **O destino é definido pela NF (fp 25 / journal 17), NÃO pela categoria nem pela location.** Teste empírico (2026-05-30): setar `valuation_in/out` da location de trânsito 26489 **NÃO** alterou o lançamento (continuou via output da categoria → fechado pela NF). Lever da location **refutado**.

### O problema NÃO está na saída — está no RETORNO (Etapa 5)
- `5101010001` (FB, posted): saldo **R$ 60.818.109,76** · **D=R$ 61.009.250,65 / C=R$ 191.140,89** (1.946 lançs).
- O crédito (baixa no retorno) é **~0,3% do débito** → as remessas entram no controle mas **quase nunca são baixadas no retorno**. O ciclo não fecha na Etapa 5, somado à re-inflação do estoque físico (R$ 785k).
- **Implicação p/ o projeto:** rever a `DIRETRIZ` — em vez de migrar tudo para `1150200001`, possivelmente **fechar o ciclo da família `51010xx`** existente (creditar `5101010001` no retorno). Decisão Contador.

> Resíduo imaterial do teste (2026-05-30): R$ 0,95 nas transitórias `1150100011/012` (par forward+reverse de internal sem NF). Estoque ROTULO restaurado (120), location 26489 `in/out=False`, pickings de teste cancelados/done.

---

## ACHADO 2026-06-01 — roteamento G4/G5a verificado ao vivo + confirmação da Contadora

> Grounding ao vivo (PROD) para fechar a config do retorno. Scripts efêmeros: `inv_cfg_g4_g5a`, `inv_entsi`, `inv_roteamento_completo`, `inv_etapa4_*`, `inv_pergunta_contadora`. Detalhe e spec: `PROPOSTA_CONFIG_RETORNO.md`.

### Confirmação da Contadora (Etapas 4-5 + Opção A)
- **Etapas 4 e 5 validadas.** Custo dos insumos no retorno = **Ativo→Ativo** (`D 1150100007 PA / C 5101010001`), **CPV só na venda final** do PA. **Não há CPV no retorno** (Opção A).
- Ground-truth que confirma: a entrada FB real `ENTSI/2026/05/0126` lança **tudo no Ativo** (D 1150100007 PA + D 1150100001 MP + D 1150100002 EMB), **zero CPV**.

### Roteamento `tipo_pedido(_entrada) → tipo.pedido.diario(empresa) → journal → no_payment`
- **FB entrada (j1001 ENTSI):** `tipo_pedido_entrada=industrializacao → j1001` com **`account_no_payment_id` VAZIO** → **não baixa 5101010001** (causa raiz G5a). `tipo_pedido_entrada=retorno → j1007` (no_payment=**5101020002 PASSIVA RETORNO**, conta errada p/ encomendante).
- **LF saída:** `dev-industrializacao` (5902) e `perda` (5903) **NÃO têm registro** no `tipo.pedido.diario` da LF → caem em default/PERDAS (j1003, no_payment=5101010001 ATIVA, +R$ 8,67M). `venda-industrializacao` (5124) → **j847 VENDA DE PRODUÇÃO** ✅.
- **Referência a espelhar:** remessa FB `industrializacao → j17` (sale, no_payment=5101010001 ATIVA → `D 5101010001`); entrada LF `serv-industrializacao → j1047` (purchase, no_payment=5101020001 PASSIVA → `C 5101020001`).

### Double-count confirmado ao vivo (G5b)
- A entrada FB de retorno **re-infla o estoque próprio**: na `ENTSI/2026/05/0126`, o picking `FB/IN/13403` (22 moves) gera `D 1150100002 MAT. EMBALAGEM` (~R$ 2.660) + `D 1150100001 MATÉRIA-PRIMA` (~R$ 4.296) — os insumos consumidos re-entram. A operação da linha 1902 está com `movimento_estoque=True`. Fix = op **3252** (`movimento_estoque=False`).

### Lado físico FB da remessa (dreno 26489)
- O companheiro nativo "Transferir TERCEIROS" (server action **1899** sobre `stock.picking`, método `action_movimentar_estoque_terceiro`) cria um picking **pt5 `26489→30720`** (Parceiros/Estoques em poder de terceiros/LF, usage=**customer**). No fluxo real ele nasce **`assigned` e NUNCA é validado** (191 assigned, 0 done recentes) → por isso 26489 nunca zera.
- **Mover `26489→30720` é PURAMENTE FÍSICO: 0 SVL, 0 account.move** (verificado: 10 moves done históricos geraram 0 SVL; 26489 transit cmp=False + 30720 customer cmp=False = nenhuma é valued p/ a FB; contas 1150200001/002 têm 0 lançamentos na FB). Driver dry-run-first: `scripts/e2e_drenar_transito_26489.py`.
- ✅ **EXECUTADO 2026-06-01:** picking pt5 manual `FB/INT/08128` (id 322875) **done** — POS-CHECK ao vivo: 26489 (lote PILOTO-3105) = **0**, 30720 = **42,28994948** (16 quants), **0 SVL** gerados pelos moves do dreno. Confirma empiricamente o "0 contábil".
- **G-DRENO-1 (gotcha do driver, corrigido):** o pt5 reserva `at confirm` → `action_confirm` dispara `action_assign` automático criando `stock.move.line` SEM-LOTE; somadas às manuais pinadas davam 32 mls (qty dobrada) → guard abortava (deixou órfão 322852). **Fix:** `do_unreserve` + unlink de residuais após `action_confirm` (antes das manuais) + idempotência que cancela órfãos de execuções anteriores (origin `DRENO-PILOTO%`).

### IDs-chave (config retorno)
- Contas: 5101010001 FB=**22800**/LF=26652 (ATIVA); 5101020001 FB=22815/LF=**26667** (PASSIVA); 5101010002 FB=22801/LF=26653; 5101020002 FB=22816/LF=26668.
- Operações retorno: 5124→**849/2702**; 5902→**850**; 5903→**2711**; 1902 simbólica→**3252**; 1124→3064/3134; 1903→838/3120.
- pt98 (LF saída retorno, 31093→26489, ativo, 0 usos); pt52 (FB entrada retorno, src=26489); pt5 (FB transf. internas, dreno 26489→30720).

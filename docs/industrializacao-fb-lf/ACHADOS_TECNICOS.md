<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/industrializacao-fb-lf/INDEX.md
superseded_by: —
atualizado: 2026-06-13
-->
# ACHADOS TÉCNICOS — Industrialização FB↔LF (Odoo / CIEL IT)

## Indice

- [1. Como a contabilização é determinada (as duas camadas)](#1-como-a-contabilização-é-determinada-as-duas-camadas)
  - [(1) FATURA (NF) — `account.move` fiscal → **CONFIGURÁVEL**](#1-fatura-nf-accountmove-fiscal-configurável)
  - [(2) VALORAÇÃO DE ESTOQUE (SVL) — `account.move` no diário ESTOQUE → **CONFIGURÁVEL (por empresa)**](#2-valoração-de-estoque-svl-accountmove-no-diário-estoque-configurável-por-empresa)
  - [Onde a valoração de estoque **NÃO** se configura (verificado por exaustão)](#onde-a-valoração-de-estoque-não-se-configura-verificado-por-exaustão)
- [2. Mecanismo NACOM já existente: "Transferir TERCEIROS"](#2-mecanismo-nacom-já-existente-transferir-terceiros)
- [3. Incidente `rule_type` (gotcha — não repetir)](#3-incidente-rule_type-gotcha-não-repetir)
- [4. Quirks CIEL IT relevantes](#4-quirks-ciel-it-relevantes)
- [5. Mapa de IDs](#5-mapa-de-ids)
  - [Empresas / parceiros / armazéns](#empresas-parceiros-armazéns)
  - [Locations](#locations)
  - [Picking types](#picking-types)
  - [Produto / BoM](#produto-bom)
  - [Fiscal](#fiscal)
  - [Contas (account.account)](#contas-accountaccount)
  - [Sintomas contábeis na FB (28/05/2026, postados)](#sintomas-contábeis-na-fb-28052026-postados)
- [ACHADO 2026-05-30 — A saída da FB ESTÁ correta (usa conta de compensação `5101010001`)](#achado-2026-05-30-a-saída-da-fb-está-correta-usa-conta-de-compensação-5101010001)
  - [O problema NÃO está na saída — está no RETORNO (Etapa 5)](#o-problema-não-está-na-saída-está-no-retorno-etapa-5)
- [ACHADO 2026-06-01 — roteamento G4/G5a verificado ao vivo + confirmação da Contadora](#achado-2026-06-01-roteamento-g4g5a-verificado-ao-vivo-confirmação-da-contadora)
  - [Confirmação da Contadora (Etapas 4-5 + Opção A)](#confirmação-da-contadora-etapas-4-5-opção-a)
  - [Roteamento `tipo_pedido(_entrada) → tipo.pedido.diario(empresa) → journal → no_payment`](#roteamento-tipo_pedido_entrada-tipopedidodiarioempresa-journal-no_payment)
  - [Double-count confirmado ao vivo (G5b)](#double-count-confirmado-ao-vivo-g5b)
  - [Lado físico FB da remessa (dreno 26489)](#lado-físico-fb-da-remessa-dreno-26489)
  - [IDs-chave (config retorno)](#ids-chave-config-retorno)
- [ACHADO 2026-06-01 (sessão 5) — grounding de EXECUÇÃO G4/G5a: mecanismo do `no_payment` validado + premissas REFUTADAS](#achado-2026-06-01-sessão-5-grounding-de-execução-g4g5a-mecanismo-do-no_payment-validado-premissas-refutadas)
  - [TL;DR (conclusões da sessão 5 — ler isto primeiro; detalhe/evidências abaixo)](#tldr-conclusões-da-sessão-5-ler-isto-primeiro-detalheevidências-abaixo)
  - [Mecanismo de roteamento e contabilização (CONFIRMADO ao vivo)](#mecanismo-de-roteamento-e-contabilização-confirmado-ao-vivo)
  - [Premissas REFUTADAS (PROPOSTA §1/§4 + handoff antigo)](#premissas-refutadas-proposta-14-handoff-antigo)
  - [Universo do j847 (mede o risco da opção G4-a) — j847 é DEDICADO ao regime](#universo-do-j847-mede-o-risco-da-opção-g4-a-j847-é-dedicado-ao-regime)
  - [Universo do j1001 (mede o efeito GLOBAL de G5a) — quase-dedicado](#universo-do-j1001-mede-o-efeito-global-de-g5a-quase-dedicado)
  - [RESÍDUOS abertos (não fecháveis por READ-ONLY — exigem NF em DRAFT)](#resíduos-abertos-não-fecháveis-por-read-only-exigem-nf-em-draft)
- [ACHADO 2026-06-02 (sessão 6) — R-UNIF PROVADO EMPIRICAMENTE (a entrada espelha a saída) + estrutura REAL da ENTSI](#achado-2026-06-02-sessão-6-r-unif-provado-empiricamente-a-entrada-espelha-a-saída-estrutura-real-da-entsi)
  - [TL;DR](#tldr)
  - [Experimento (prova 100%, zero sujeira)](#experimento-prova-100-zero-sujeira)
  - [Estrutura REAL da ENTSI (via `account.move.line` — corrige premissas dos docs)](#estrutura-real-da-entsi-via-accountmoveline-corrige-premissas-dos-docs)
  - [Implicação operacional (= a do G4)](#implicação-operacional-a-do-g4)
- [ACHADO 2026-06-02 (sessão 7) — GROUNDING DO FLUXO 2-NF (anatomia SARET + fluxo do PA, 3 esferas)](#achado-2026-06-02-sessão-7-grounding-do-fluxo-2-nf-anatomia-saret-fluxo-do-pa-3-esferas)
  - [TL;DR (sessão 7)](#tldr-sessão-7)
  - [A. Anatomia SARET (precedente vivo do `no_payment` em doc separado)](#a-anatomia-saret-precedente-vivo-do-no_payment-em-doc-separado)
  - [B. Picking_types e journals do retorno (LF=5) — o "como" da separação](#b-picking_types-e-journals-do-retorno-lf5-o-como-da-separação)
  - [C. Fluxo do PA × insumos — VND mista de retorno (saída LF) e ENTSI (entrada FB)](#c-fluxo-do-pa-insumos-vnd-mista-de-retorno-saída-lf-e-entsi-entrada-fb)
  - [D. Como o PA recebe Ic+S no cenário 2-NF (esfera contábil — desenho + resíduo do piloto)](#d-como-o-pa-recebe-ics-no-cenário-2-nf-esfera-contábil-desenho-resíduo-do-piloto)
  - [E. Pontos de código que assumem "1 NF por ciclo" (Frente 2 — a ajustar quando o caminho (b) for aprovado)](#e-pontos-de-código-que-assumem-1-nf-por-ciclo-frente-2-a-ajustar-quando-o-caminho-b-for-aprovado)
  - [F. Mudanças no trabalho operacional (delta 1-NF → 2-NF)](#f-mudanças-no-trabalho-operacional-delta-1-nf-2-nf)
  - [G. Como a NF é montada HOJE — o operador NÃO digita os insumos (fluxo operacional)](#g-como-a-nf-é-montada-hoje-o-operador-não-digita-os-insumos-fluxo-operacional)
  - [H. Rastreabilidade remessa ↔ PA para o cenário 2-NF (vínculo de TELA nativo — `s7_rastreabilidade`)](#h-rastreabilidade-remessa-pa-para-o-cenário-2-nf-vínculo-de-tela-nativo-s7_rastreabilidade)
  - [I. Subcontratação nativa + fluxo de ENTRADA (`s7_subcontratacao`) — base para "1 doc → resto automático"](#i-subcontratação-nativa-fluxo-de-entrada-s7_subcontratacao-base-para-1-doc-resto-automático)
- [ACHADO 2026-06-03 (sessão 8) — hipótese (i) REFUTADA (create_invoice FUNDE) + GATE 0 armado](#achado-2026-06-03-sessão-8-hipótese-i-refutada-create_invoice-funde-gate-0-armado)
- [ACHADO 2026-06-12 (sessão 9) — grounding do desenho da emissão (robô lido por dentro + valores da expansão)](#achado-2026-06-12-sessão-9-grounding-do-desenho-da-emissão-robô-lido-por-dentro-valores-da-expansão)
- [Contexto](#contexto)

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

---

## ACHADO 2026-06-01 (sessão 5) — grounding de EXECUÇÃO G4/G5a: mecanismo do `no_payment` validado + premissas REFUTADAS

> Fase READ-ONLY de execução (5 scripts `g4_g5a_grounding_{estado,ops_lf,header,risco,gaps}.py` + `g4_analise_universo_j847.py`), context `allowed_company_ids=[1,5]`, uid 42. **Verificado por 4 lentes adversariais (consenso 4/4 nos pontos acionáveis).** Esta seção é a DONA do mecanismo de roteamento/contabilização da NF; PROPOSTA/SOT/GOALS apontam para cá.

### TL;DR (conclusões da sessão 5 — ler isto primeiro; detalhe/evidências abaixo)
1. **G4 (LF retorno baixa a PASSIVA 5101020001): 1 NF mista COM serviço NÃO baixa a 5902 — provado por 8 ângulos.** Causa raiz: a contrapartida (CLIENTES/no_payment) é **UMA linha POR DOCUMENTO**, governada pelo `tipo_pedido` do **HEADER**, não por linha. O `no_payment` só substitui o recebível quando a NF é **100%-simbólica** (sem serviço). ⇒ a 5902 só baixa em **DOCUMENTO separado**.
2. **Restam 2 caminhos para o G4** (decisão Rafael+Contadora): **(b) SEPARAR** a 5902 em documento próprio — **nativo, já roda em PROD** (SARET só-5902 → no_payment baixa) — resultado = 2 documentos; ou **(V-B) 1 NF mista + lançamento de AJUSTE (`entry`) na fonte** (desvio cirúrgico do robô p/ `partner=LF`) — mantém 1 NF fiscal, mas é remendo (aval Contadora + idempotência/estorno/filtro-ETL; não fecha AVCO/R1). **V-A (editar/repostar a NF mista) DESCARTADA** (estudo 4 lentes, consenso 4/4 — bloqueador técnico + fiscal).
3. **A pergunta que destrava:** "5124+5902 na MESMA NF" é exigência **FISCAL** (→ V-B) ou preferência **OPERACIONAL** (→ separar, opção b)? — `MATERIAL_CONTADORA_G4.md` pergunta 1.
4. **G5a (FB credita a ATIVA 5101010001): VIÁVEL** — `account_no_payment_id=22800` no **j1001** (sinal validado ao vivo). Resíduo R1: a 1902/op 3252 debita a **transitória 1150100011** (não o PA) → o Ativo→Ativo fecha via o **SVL físico do PA** (medir na Etapa 5). **R-UNIF:** a entrada FB de retorno também é mista → o FORNECEDORES do serviço absorve a 1902 → G5a também exige a 1902 em documento separado (mesma solução do G4). **→ [PROVADO na sessão 6 — ver `ACHADO 2026-06-02` abaixo: R-UNIF confirmado empiricamente; "VIÁVEL" acima vale só p/ a config isolada, que é INSUFICIENTE sozinha; G5a CONVERGE com G4.]**
5. **Nada foi executado no Odoo** — tudo READ-ONLY + 2 experimentos com NF-teste **postada e EXCLUÍDA** (journal de teste deletado; zero sujeira; NF original intacta).

### Mecanismo de roteamento e contabilização (CONFIRMADO ao vivo)
1. **O `journal` é do CABEÇALHO da NF** (`account.move.journal_id`) — **UM por NF**. As `account.move.line` têm operações fiscais distintas por linha (contas/CFOP via posição fiscal), mas o journal é único.
2. **O journal do header é escolhido pelo campo `l10n_br_tipo_pedido(_entrada)` do PRÓPRIO `account.journal`** (não pela tabela `tipo.pedido.diario`, que é secundária). Prova: header ENTSI tpe=`serv-industrializacao` → **j1001** (que carrega `l10n_br_tipo_pedido_entrada=serv-industrializacao`), mesmo **sem** registro `tipo.pedido.diario(FB, serv-industrializacao)`. ⇒ criar tal registro é **provavelmente redundante** (manter como cinto-de-segurança, é inofensivo). Reforço: a engine CIEL-IT **auto-seleciona a operação por linha por partner/destino** (app/odoo/CLAUDE.md D-V29-1) — não escolhemos a op da linha.
3. **O `account_no_payment_id` do journal = conta da CONTRAPARTIDA das linhas SIMBÓLICAS** (CST51, sem pagamento próprio): **crédito em NF de entrada**, **débito em NF de saída**. **NÃO captura linhas de tributo nem de serviço com pagamento** (essas vão p/ CLIENTES/FORNECEDORES via operação). **VALIDADO EMPIRICAMENTE** em 3 NFs de entrada que já têm no_payment setado:
   - `ENTIN/2026/05/0003` (j1011, no_pay=22815 PASSIVA): 6 linhas mercadoria → D 1150100011; 1 linha no_payment → **C 5101020001** 94.974,64.
   - `ENTTR/2026/05/0078` (j868, no_pay=22827): mercadoria → D 1150100011; ICMS com contrapartida própria (FORA do no_payment); 1 linha no_payment → **C 5101020014** (só o valor mercadoria).
   - `ENTBO/2026/03/0001` (j993, no_pay=22817): idem padrão.
4. `l10n_br_movimento_estoque` é POR LINHA (na operação) → gera/não-gera stock.move (SVL).

### Premissas REFUTADAS (PROPOSTA §1/§4 + handoff antigo)
- ❌ **"NF de retorno cai em PERDAS j1003"** → a NF de retorno real LF→FB é **MISTA (5124 serviço + 5902 insumos)** e cai em **j847 VENDA PRODUÇÃO** (header `venda-industrializacao`, op_hdr 2702). Confirmado em 4 NFs `VND/2026/00356-00359` + universo. PERDAS j1003 só recebe **PERDA PURA (5903/op 2711/header perda)** — ex. `RETNA/2026/00091-94`.
- ❌ **"5902 usa op 850 (dev-industrializacao)"** → op **850 é company FB**; a NF mista real usa op **2864** (5902, `venda-industrializacao`, company LF). (op LF alternativa p/ 5902: 2710 dev-industrializacao.)
- ❌ **"dev-industrializacao/perda LIVRES na LF"** → já têm journal: `dev-industrializacao`→**j1002 RETRABALHO** (no_pay 26863=5101010046), `perda`→**j1003 PERDAS** (no_pay 26652=5101010001 ATIVA). Criar `tipo.pedido.diario(LF, dev-ind/perda→novo)` ficaria **INERTE** (a NF mista roteia por `venda-industrializacao`→j847).
- ❌ **"G4 = só execução técnica, sem bloqueio do Contador" (PROPOSTA §8)** → G4 exige **decisão de DESENHO fiscal** (3 opções, ver PROPOSTA §4 reescrita).

### Universo do j847 (mede o risco da opção G4-a) — j847 é DEDICADO ao regime
- **340/340** NFs em j847 (out_invoice posted desde 2026-01-01) são **RETORNO (5902)+5124** e **100% partner=1 (NACOM GOYA - FB)**. **Zero venda comum a terceiros.** ⇒ j847 é o **espelho exato do j1001** (ambos dedicados ao regime FB↔LF) → setar `no_payment=26667` no j847 NÃO atinge venda a terceiros.
- **R$ 8.683.466,19** de insumos (5902) creditados na transitória 1150100012 desde 2026-01 que **NÃO baixaram a PASSIVA 5101020001** (hoje embutidos no D CLIENTES — anomalia do recebível, move 738097: D CLIENTES 38.877,59 = serviço 13.735,66 + insumos 24.477,59 + impostos).

### Universo do j1001 (mede o efeito GLOBAL de G5a) — quase-dedicado
- **351 ENTSI** posted desde 2026-01-01: **341 op 1917** (industrialização LF, total>0), ~6 variantes simbólicas (op 2027/3120/3214), **100% partner=35 (LF)**.
- Histórico total: 1600 posted; **1555 partner=35 (LF)**; 45 "outros" = todos **REDE TING - SP** (partner 87626, fluxo 2025, quase todos total=0). ⇒ efeito global é **prospectivo** e restrito ao regime LF na prática.

### RESÍDUOS abertos (não fecháveis por READ-ONLY — exigem NF em DRAFT)
- **R1 (G5a) — RESOLVIDO por READ-ONLY 2026-06-01** (`scripts/g5a_medir_r1_conta_op3252.py`): a linha 1902 com op 3252 (`mov_estoque=False`) debita a **transitória 1150100011 RECEBIMENTO FÍSICO FISCAL** (NÃO o PA 1150100007). Cadeia: op 3252 sem conta própria → linha usa `property_account_expense_categ_id` da categ 193 = **3201000001 CPV** → **fp 88** (ENTRADA-SERVIÇO IND., FB) remapeia `CPV/CMV/3201000002 → 1150100011` (fp 97 RETORNO idem). Precedente empírico: 51 ops de entrada `mov_estoque=False` usam a conta de despesa da categoria (sem valuation de estoque) — consistente. **Implicação:** com no_payment=22800, a 1902 = **`D 1150100011 / C 5101010001`** ⇒ ✅ baixa a ATIVA (G5a), mas **o PA não incorpora o Ic pela 1902** (o NET-alvo "1902: D 1150100007 PA" da PROPOSTA §3 era IMPRECISO). O Ativo→Ativo fecha SE o **SVL físico do PA** na entrada fizer `D 1150100007 PA / C 1150100011` (a transitória 1150100011 é a ponte): NET das duas = `D PA / C 5101010001`. **Riscos remanescentes (medir na Etapa 5):** (i) descasamento se valor 1902 (Ic) ≠ SVL do PA na 1150100011 → transitória não zera; (ii) AVCO do PA = Ic+S depende do price_unit declarado (G8).
- **R1b (interferência G5a×G5b GLOBAL):** o no_payment no j1001 é GLOBAL — afeta também as ENTSI atuais que usam op **2027** (1902, `mov_estoque=True`): passariam a creditar 5101010001 (baixa ATIVA) **MAS continuam re-inflando estoque** (double-count) por terem mov_estoque=True. Só as NFs com op **3252** matam o double-count. ⇒ rotear TODAS as 1902 de retorno para a op 3252 é parte do G5a, não opcional.
- **R2 (G4) — RESOLVIDO por EXPERIMENTO 2026-06-01** (`scripts/g4_experimento_no_payment.py`; journal de teste no_payment=26667 + cópia da NF `VND/2025/00089` R$43,37, postada e DELETADA — zero sujeira): **na NF MISTA o `no_payment` do journal NÃO separa a 5902.** Mesmo postada com no_payment=26667 no journal, a 5902 creditou a transitória **1150100012** e a contrapartida foi **absorvida pelo `D CLIENTES`** (o receivable gerado pela linha de serviço 5124). O `no_payment` (5101020001) **não apareceu**. ⇒ **Opção (a) [no_payment no journal] DESCARTADA para NF mista.** Mecanismo: o `account_no_payment_id` substitui o receivable/payable **só quando a NF não tem outra linha com pagamento** (NF 100%-simbólica, como a perda pura 5903→j1003 que funciona). Com serviço (5124) na mesma NF, o CLIENTES engole a parte simbólica. **⇒ G4 exige a Opção (b): emitir o retorno de insumos (5902) em NF SEPARADA** (sem serviço) roteada a um journal com no_payment=26667 → aí a 5902 vira simbólica pura e debita `5101020001` (baixa PASSIVA), espelhando a mecânica da NF de perda. **Decisão fiscal da Contadora** (separar retorno-de-insumos do faturamento-de-serviço): `MATERIAL_CONTADORA_G4.md`.
- **R2b — COMO CONFIRMADO (a granularidade vem da OPERAÇÃO via `tipo_pedido`)** (2026-06-01, `scripts/g4_verificar_separacao_por_journal.py` + leitura SARET): a página inteira do form da operação (`operacao_cadastro_odoo.md`) confirma que a operação **NÃO tem campo de conta GL** — mas **carrega `l10n_br_tipo_pedido`**, que decide o journal, que decide **se a 5902 sai separada ou misturada**. **PROVA VIVA:** existem NFs de retorno **só-5902 já separadas hoje** — `SARET/2026/00007-11` (j1002 "SAÍDA - RETRABALHO"), emitidas pela op **2710** (`tipo_pedido=dev-industrializacao`, cfop intra 5902, `mov_estoque=True`). Estrutura (move 725475): `5902 → C 1150100012` (transitória) + **`D 5101010046` (= no_payment do j1002)**. ⇒ numa NF **só-5902** (sem serviço, total=0) **o no_payment do journal BAIXA a conta de compensação** — exatamente a mecânica que falta, só trocando a conta. **Contraste:** op **2864** (`venda-industrializacao`) → j847 (misto c/ serviço) → CLIENTES absorve a 5902 (R2). **⇒ COMO do G4:** a linha 5902 do retorno deve usar uma operação cujo `tipo_pedido` a roteie para um journal **separado** do serviço, com **`no_payment=26667` (PASSIVA 5101020001)** → `D 5101020001 / C 1150100012` (transitória fechada pelo SVL, op mov_estoque=True) = **baixa a PASSIVA**. Config: reusar a rota dev-industrializacao→journal (hoje j1002 c/ no_pay 26863 RETRABALHO — conta errada) apontando no_payment=26667, OU journal dedicado de retorno-de-industrialização. *(Detalhe a confirmar: a SARET saiu com CFOP de linha **5949** (retrabalho), não 5902 — para o retorno de insumos consumidos o CFOP correto é 5902; pode exigir op própria cfop 5902 + tipo_pedido separador.)*
- **R-UNIF (implicação p/ o G5a — indício FORTE, a confirmar):** o mesmo mecanismo de cabeçalho atinge a ENTRADA. A entrada FB de retorno (ENTSI) também é MISTA (1124 serviço + 1902 insumos): a 1124 gera `C FORNECEDORES` (payable real). Por analogia direta com o experimento de saída, o **FORNECEDORES do serviço deve absorver a 1902** → o `no_payment=22800` no j1001 **NÃO baixaria a ATIVA numa NF mista de entrada** (igual o CLIENTES absorveu a 5902 na saída). Lógica do CIEL IT: o `account_no_payment_id` só substitui receivable/payable quando a NF **não tem nenhuma linha com pagamento**. ⇒ **A solução é ÚNICA e resolve os dois lados: o retorno de insumos (5902↔1902) trafega em NF SEPARADA do serviço (5124↔1124).** A LF emite NF de insumos pura (→ baixa PASSIVA via no_payment saída) e a FB recebe NF de insumos pura (→ baixa ATIVA via no_payment entrada j1001); o serviço vai em NF própria (→ CLIENTES/FORNECEDORES). **Validado só no lado SAÍDA; lado ENTRADA = inferência (confirmar com 1 experimento de entrada análogo se quiser certeza 100%).** Nota: o `no_payment` foi validado isoladamente em ENTRADAS NÃO-mistas (j1011 remessa pura, j868, j993) — onde funcionou justamente por não haver serviço junto.
- **ESTUDO server action (sessão 5, 4 lentes adversariais — consenso 4/4) — VEREDITO: NÃO viável/correto/íntegro manter 1 NF mista + baixar via código.** Grounding: podemos criar server action (create=True; 265 no ambiente, 30 em account.move; sem hash_table; lock 2025→2026 aberto; NF nasce posted por OdooBot; precedente 1946 "Ajustar Contabil NF Devolução" = draft→troca journal→repost). Mas:
  - **V-A (editar a NF em draft + repost): BLOQUEADOR.** O `action_post` **re-deriva o `D CLIENTES` da soma das invoice_line_ids** (linha dinâmica) → reverte a reclassificação manual da contrapartida = **o mesmo mecanismo do R2 já provado** (a linha `D 5101020001` evapora ou desbalanceia e o post falha). E `button_draft`+repost numa **NF de saída SEFAZ-autorizada** desincroniza o razão do XML transmitido (base: NF SEFAZ-autorizada não cancela via XML-RPC; XML-RPC stale→SEFAZ 225). **Descartar V-A definitivamente.**
  - **Risco no NOSSO sistema:** a NF mista (header venda-industrializacao) é importada pelo `faturamento_service` sem filtro de company; a oscilação posted→draft→posted faz o scheduler re-processar (recriar MovimentacaoEstoque, re-baixar carteira, até cascata `_processar_cancelamento_nf`).
  - **Outros:** corrida com o robô OdooBot (mata o "determinismo"); `except: continue` (estilo 1946) engole falhas → saldo cresce sem alarme; zero idempotência; sem estorno on-cancel = ajuste órfão; server action custom em ERP de terceiro some em upgrade (precedente DFE NFD).
  - **V-B (lançamento `entry` de ajuste separado):** único tecnicamente viável, MAS é remendo perpétuo que infla o recebível real da LF (compensado por entry), exige idempotência/estorno/lock/filtro-ETL + aval da Contadora, e **não fecha** o AVCO (Ic+S) nem o resíduo R1 (ortogonais).
  - **R2c — MECANISMO DE CRIAÇÃO DO ROBÔ (lido no code da server action 1512 "CIEL IT: Robô Faturamento"):** o journal da NF de saída vem do **PICKING**: `journal = search(company, type='sale', l10n_br_tipo_pedido == picking.picking_type_id.l10n_br_tipo_pedido)` → **1 picking = 1 account.move, journal ÚNICO (do picking_type)**. ⇒ **NÃO há quebra por linha** nem roteamento de contrapartida por linha. O `account.move.line.l10n_br_tipo_pedido` EXISTE por linha, mas é informativo/herda da operação — o **journal e a contrapartida (CLIENTES, linha agregada — core Odoo) são por DOCUMENTO**. **Refuta "tipo_pedido por linha resolve"** e **"quebrar por tipo de produto"** (todas as linhas, incl. a "5124 serviço"=produto azeite/PA, são `type=product`; `l10n_br_split_service_invoice`=False e só vale p/ NFS-e de serviço real). ⇒ a 5902 só ganha contrapartida própria (no_payment→PASSIVA) num **DOCUMENTO separado** — seja por 2 NFs, seja por 2 PICKINGS de saída (cada picking_type → seu journal → sua NF). Não há "1 NF mista que baixa".
- **R2d — EXPERIMENTO op-devolução (2026-06-01, cópia postada+excluída, zero sujeira) — refuta a "segregação da contrapartida por op de linha":** copiei a NF mista, troquei a op das 24 linhas 5902 de **2864 (venda) → 2710 (dev-industrializacao)**, recalculei e **POSTEI** num journal de teste com no_payment=26667. Resultado: a 5902 continuou `C 1150100012`, a **contrapartida ficou TODA em `D CLIENTES` (agregada)**, o **no_payment (5101020001) NÃO materializou**, e o **`l10n_br_tipo_pedido` da linha permaneceu `venda-industrializacao`** (= do CABEÇALHO, não da op trocada). ⇒ **Causa raiz definitiva:** o tipo_pedido que governa a contrapartida/no_payment vem do **HEADER do `account.move`**, não da operação por linha. Trocar a op de uma linha muda a conta de resultado (via fp), **nunca** a contrapartida. Para a 5902 baixar via no_payment, o **HEADER** teria de ser "devolução" (sem o serviço) = **documento separado**. **Nota de fluxo real:** trocar a op numa NF já criada pelo robô (posted) exigiria `button_draft`+repost de NF SEFAZ-autorizada (= V-A, vetada) — a op teria de vir certa **na criação**. ⇒ **8 ângulos convergem:** 1 NF mista com serviço NÃO baixa a 5902 nativamente. Fim da linha "1 NF".
  - **ALTITUDE (o ponto decisivo):** o caminho nativo que **já funciona em PROD** é a **Opção (b) — 5902/1902 em NF SEPARADA** (SARET só-5902 baixa via no_payment, sem código). **O requisito "1 NF mista" é a ÚNICA causa de toda a fragilidade.** "Determinismo" não é diferencial de server action (um job nosso versionado/observável é igual e mais controlável). **Recomendação técnica: ceder o requisito "1 NF mista" + obter a resposta fiscal da Contadora (separar é permitido? provável SIM — já há SARET separada).**
- **R3 (reversibilidade):** limpar o no_payment reverte a CONFIG mas **não** os lançamentos já postados na janela — exige gate (1 NF em janela controlada antes de deixar o fluxo automático ligado).

---

## ACHADO 2026-06-02 (sessão 6) — R-UNIF PROVADO EMPIRICAMENTE (a entrada espelha a saída) + estrutura REAL da ENTSI

> Grounding READ-only (via `account.move.line`) + 1 EXPERIMENTO (NF-teste **postada e EXCLUÍDA**, zero sujeira). Script: `scripts/g5a_experimento_entrada_runif.py`. Fecha o R-UNIF, que a sessão 5 deixou como inferência ("a confirmar com 1 experimento de entrada análogo").

### TL;DR
1. **R-UNIF CONFIRMADO (prova 100%):** `account_no_payment_id=22800` no journal **NÃO baixa a ATIVA `5101010001` numa NF MISTA de entrada** — o `FORNECEDORES` do serviço (1124) **absorve** a 1902, exatamente como o `CLIENTES` absorveu a 5902 na saída (`sessão 5 R2`). ⇒ **G5a NÃO é independente: CONVERGE com o G4.** A decisão `SOT L5a` ("ajustar o j1001 com no_payment") é **insuficiente sozinha**.
2. **Solução ÚNICA p/ os 2 lados:** o retorno de insumos (1902↔5902) tem que trafegar em **documento separado** do serviço (1124↔5124). **Uma só pergunta fiscal à Contadora resolve entrada E saída.**

### Experimento (prova 100%, zero sujeira)
- NF-teste = cópia da `ENTSI/2026/02/0053` (move 506211, R$ 120,05, a **menor mista**) → journal de teste **purchase/FB** com `account_no_payment_id=22800` → setar `invoice_date` (o `copy()` reseta em vendor bill — senão `action_post` falha "data obrigatória") → **`action_post`** (sem o recompute do robô) → POS-POST: **NET `5101010001` (ATIVA) = 0** · **NET `2120100001` FORNECEDORES = −120,05** (= total). Depois **DELETADA** (move + journal); j1001 **intacto** (no_payment segue vazio), **0 sujeira** (re-verificado: 0 linhas em j1001 tocando 22800).
- Mecânica (core Odoo, confirmada na `sessão 5 R2c`): a contrapartida payable/receivable é **uma linha agregada POR DOCUMENTO**; o `no_payment` só a substitui em NF **100%-simbólica**. Com o serviço (1124) na mesma NF, o `FORNECEDORES` é um payable **real** e engole a parte simbólica (1902). **A op da 1902 é irrelevante p/ isso:** a saída já provou o caso "5902 sem autocancel + serviço → absorvido"; a entrada provou "1902 (op 2027 autocancela) + serviço + no_payment → inerte". Os dois extremos convergem.

### Estrutura REAL da ENTSI (via `account.move.line` — corrige premissas dos docs)
- **0 de 1600** ENTSI (j1001, `in_invoice` posted, FB) tocam a `5101010001` → a **entrada NUNCA baixa a ATIVA hoje** (confirma a causa-raiz G5a, medida direta).
- Composição: **490 MISTA** (1124+1902) · **1060 pura-serviço** · **1 pura-1902**. ⇒ os insumos **quase nunca** entram em documento próprio (o **oposto** da saída, onde já há `SARET` só-5902 que baixam via no_payment).
- Ops reais: **1124 → op 1917** "Industrialização efetuada por outra empresa (ICMS 51)" (os docs diziam **3064/3134** — incorreto; 3064=TING, 3134=PC06, raros) · **1902 → op 2027** "Retorno de mercadoria…", `movimento_estoque=True` → cada `D 1150100011` tem um `C 1150100011` **espelho** = **autocancela** (net-zero na transitória); o `FORNECEDORES`=total é dirigido pelo **serviço (1124) + tributos** (PIS/COFINS a recuperar).
- **op 3252** (a do piloto, `movimento_estoque=False`): o recompute do robô (`onchange_l10n_br_calcular_imposto_btn`) sobre uma cópia mista leva **>400s** (timeout) — comportamento **normal** do robô CIEL IT (lento), **NÃO** defeito. O teste op3252 ficou inviável por tempo, mas é **desnecessário p/ o R-UNIF** (regra de DOCUMENTO, independe da op da 1902).

### Implicação operacional (= a do G4)
Hoje a FB **recebe 1 DFe mista** (1124+1902) → exige que a LF **emita** o retorno de insumos separado (G4) **E** que a FB **escriture** separado (G5a) — **mesma origem, resolvida pela mesma decisão fiscal**. Aprovada a separação: a 1902 de entrada vira simbólica pura → o `no_payment=22800` do j1001 (ou journal dedicado de entrada-de-insumos) baixa a `5101010001` (espelho da mecânica das `SARET`/perda).

---

## ACHADO 2026-06-02 (sessão 7) — GROUNDING DO FLUXO 2-NF (anatomia SARET + fluxo do PA, 3 esferas)

> READ-only (5 scripts `s7_*`: `anatomia_saret`, `saret_fisico`, `fluxo_pa`, `vnd_picking_vs_nf`). Zero escrita Odoo (decisão da sessão: READ+desenho, prova final do AVCO fica para o piloto). Esta seção DESCREVE o fluxo de 2 documentos ao vivo para anexar ao `MATERIAL_CONTADORA_G4.md`. Desenho/decisão = `SOT §2 Etapa 4/5`.

### TL;DR (sessão 7)
1. **A separação NÃO é de movimento físico — é de COMPOSIÇÃO de linhas.** Provado: na VND mista de retorno (`VND/2026/00359`, move 738097), das 10 linhas-produto **só a linha do PA (5124) tem `stock.move`**; as **9 linhas de insumos (5902) são SIMBÓLICAS (zero move)**, compostas pela lógica de industrialização. Idem na entrada (`ENTSI/2026/02/0053`: 1×1124 + 25×1902, sem picking 1:1). ⇒ separar em 2 NF = rotear as linhas-insumo (5902/1902) para um **2º documento com journal próprio**, não "mover fisicamente em separado".
2. **O journal (= o no_payment) vem do `picking_type.l10n_br_tipo_pedido`** (robô server action 1512: `journal = search(company, type='sale', l10n_br_tipo_pedido == picking.picking_type_id.l10n_br_tipo_pedido)`; **1 picking = 1 account.move**). 2 NF com no_payment distinto exigem **2 picking_types (ou 2 origens) com `tipo_pedido` distinto**.
3. **O PA físico viaja SEMPRE na linha de serviço (5124↔1124)** — é a única `mov_estoque=True` que gera o `stock.move` que valora o AVCO. **O PA não tem CFOP próprio** (confirma a suspeita): pega o 5124 (saída) / 1124 (entrada). Os insumos (5902/1902) são fiscais.
4. **`no_payment` em SAÍDA = DÉBITO na conta de compensação**; numa NF **100%-simbólica (total=0)** ele absorve TODA a contrapartida (sem CLIENTES) — provado em 14 SARET. **Nenhum journal sale LF aponta a PASSIVA `5101020001`** hoje → o caminho (b) exige criar/repontar 1 journal de retorno-de-insumos com `no_payment=26667`.
5. **SVL usa `unit_cost` (custo AVCO), NÃO o `price_unit` da NF** — 2 camadas independentes (refina a premissa "AVCO vem do price_unit da 1124"). O AVCO Ic+S é **resíduo a medir no piloto** (G8).

### A. Anatomia SARET (precedente vivo do `no_payment` em doc separado)
14 SARET 2026 (`SARET/2026/00001-14`, j1002 `SARÍDA-RETRABALHO`, **todas `amount_total=0`** CST51). Estrutura contábil **idêntica** (ex. move 519417 e 725475):
- `C 1150100012 FATURAMENTO FÍSICO FISCAL` (transitória, = valor mercadoria + ajustes) + **`D 5101010046 REMESSA PARA RETRABALHO (ATIVA)` (= `account_no_payment_id` do j1002)** — **sem linha de CLIENTES** (a NF não tem serviço com pagamento).
- **Criação:** op **2719 "Retrabalhos"** → CFOP **5949** (create_uid 38 Josefa, partner CD); op **2710 "Retorno de Industrialização - Devolução"** → CFOP **5902** (move 630193) OU **5949** (move 725475) — **o CFOP varia por posição fiscal/produto, não pela op** — create_uid **1 OdooBot (robô)**, `ref=LF/LF/SAI/RETIND/0000X`.
- **Físico (`s7_saret_fisico`):** a SARET nasce do picking **pt97 "Expedição Industrialização Retorno (LF)"** (`tipo_pedido='dev-industrializacao'` → j1002), **`42 LF/Estoque → 5 Parceiros/Clientes`**, com `stock.move` REAL e **SVL real** (ex. -105,00). `origin=INV-FATURAR_LF_FB_..._SAIDA-DEV-INDU`.
- ⚠️ **A SARET é DEVOLUÇÃO de PRODUTO real** (óleo/maionese/molho, estoque PRÓPRIO LF, SVL≠0), **não** o "retorno simbólico de insumos consumidos". Ela prova o **mecanismo contábil** (no_payment baixa a compensação numa NF total=0), **não** o caso de uso. O retorno de insumos do regime é simbólico (ver §C).

### B. Picking_types e journals do retorno (LF=5) — o "como" da separação
| picking_type | `tipo_pedido` | → journal (robô) | `no_payment` | papel |
|---|---|---|---|---|
| **pt66** Expedição Industrialização (LF) | `venda-industrializacao` | **j847** VENDA PRODUÇÃO | **VAZIO** | serviço 5124 (NF mista hoje) |
| **pt97** Exp. Industrialização Retorno (LF) | `dev-industrializacao` | **j1002** RETRABALHO | 5101010046 (RETRABALHO) | devolução produto (SARET) |
| **pt94** Expedição Ñ Aplicado (LF) | `perda` | **j1003** PERDAS | 5101010001 (ATIVA) | perda pura 5903 |
| **pt98** Retorno Industrialização (LF) | **`False`** | (não roteia) | — | `31093 LF/PA-Terceiros → 26489`; **0 usos** |
| pt20 Ordens de Entrega (LF) | `False` | — | — | genérico |

Journals sale LF com no_payment de compensação: j863 `industrializacao`→5101010011 · j1002 `dev-industrializacao`→**5101010046** · j1003 `perda`→5101010001 · j877 `transf-filial`→5101010014 · **j847 `venda-industrializacao`→VAZIO**. **Nenhum aponta a PASSIVA `5101020001` (26667)** — a conta correta do encomendante. ⇒ **G4 (b) precisa de 1 journal de retorno-de-insumos com `no_payment=26667`** (criar novo OU repontar; alterar o j1002 afetaria todo o retrabalho).

### C. Fluxo do PA × insumos — VND mista de retorno (saída LF) e ENTSI (entrada FB)
**VND/2026/00359 (move 738097, j847, partner FB, ref `LF/SAI/IND/01914`):**
- linha **5124 (op 2702, `mov_estoque=True`)**: produto **PA** `[4739099] OL.MIS.AZEITE` (categ PRODUTO ACABADO), `price_unit=100`, qty 144 → **único `stock.move` do picking** (pt66, `42→5`, SVL `value=-25222,66 unit_cost=175,16`).
- 9 linhas **5902 (op 2864, `mov_estoque=True` na op, mas SEM move no picking)**: insumos (ÓLEO, GALÃO, ETIQUETA, CAIXA…) — **simbólicas/compostas**.
- ⇒ `s7_vnd_picking_vs_nf`: NF 10 linhas (1×5124 + 9×5902); picking **1 move** (só o PA); **9 produtos SEM move**.

**ENTSI/2026/02/0053 (move 506211, j1001, partner LF):**
- linha **1124 (op 1917, `mov_estoque=True`)**: produto **PA** `[4830176] KETCHUP` → gera o move do PA na FB (valora AVCO).
- 25 linhas **1902 (op 2027, `mov_estoque=True`)** = insumos: cada uma com um **C espelho** na transitória `1150100011` (**autocancela** — re-infla estoque = **double-count** confirmado). O piloto troca a 1902 para op **3252 (`mov_estoque=False`)** → 0 move → 0 double-count (G5b).
- contrapartida agregada **`C FORNECEDORES` = total** (dirigida pelo serviço 1124).

**Distinção física CRÍTICA (terceiros × próprio):** a VND/SARET reais saem de **`42 LF/Estoque` (estoque PRÓPRIO LF)** via pt66/pt97 — porque hoje a LF **não segrega** os insumos de terceiros (= a causa do double-count R$785k). O **piloto** (com segregação) tem o PA em **`31093 LF/PA-Terceiros`**, que sai por **pt98 (`31093→26489`)** — mas **pt98 tem `tipo_pedido=False`** (não roteia para journal). ⇒ **GAP do regime 2-NF de terceiros:** faltam picking_types saindo de **31093** com `tipo_pedido` configurado (1 `venda-industrializacao` p/ PA+serviço, 1 p/ insumos→no_payment PASSIVA). A NF de insumos é **simbólica (sem movimento)** → precisa de um **veículo** (picking simbólico OU composição da SO/robô em 2 documentos) — **ponto de desenho a definir** (`SOT §2 Etapa 4`).

### D. Como o PA recebe Ic+S no cenário 2-NF (esfera contábil — desenho + resíduo do piloto)
- **PA físico** entra na FB pela linha **1124** (serviço, `mov_estoque=True`) → SVL `D 1150100007 PA / C 1150100011`; NF 1124 `D 1150100011 / C FORNECEDORES (S)` ⇒ NET `D PA(+S) / C FORNECEDORES`.
- **Insumos (1902, op 3252, `mov_estoque=False`)** em NF separada → `D 1150100011 / C 5101010001 (no_payment ATIVA)` (= baixa Ic) — **sem move**, logo **não credita o PA diretamente**.
- **Para o PA valer Ic+S**, a transitória `1150100011` precisa fechar: o **SVL do PA** teria de creditar `1150100011` por **Ic+S** (não só S) — isto é, o `unit_cost` do move de entrada do PA = Ic+S. Como o SVL usa `unit_cost` (não o `price_unit` fiscal), o valor de entrada do PA tem de ser **declarado** (price_unit da 1124 OU custo no XML). **Risco a medir no piloto:** se `unit_cost(PA) ≠ Ic+S` ou `Ic(1902) ≠` parcela da transitória, `1150100011` não zera (resíduo). **G8 = piloto.** (Coerente com R1 da sessão 5, agora ancorado nos dados reais: a 1902 op 3252 debita a transitória, não o PA.)

### E. Pontos de código que assumem "1 NF por ciclo" (Frente 2 — a ajustar quando o caminho (b) for aprovado)
| # | Local | Premissa "1 NF" | Delta p/ 2-NF |
|---|---|---|---|
| 1 | **Robô CIEL IT** (server action 1512 "Robô Faturamento") | `journal = picking_type.l10n_br_tipo_pedido`; **1 picking = 1 `account.move`** | 2 NF ⇒ **2 pickings/origens** com `tipo_pedido` distinto (nativo, sem código nosso) |
| 2 | `app/odoo/estoque/orchestrators/inventario_pipeline.py` (~6,2K LOC) | pipeline **ETAPAs A→F = 1 NF mista por ciclo** de ajuste (B cria/valida/libera 1 picking→1 NF; C aguarda invoice; D transmite SEFAZ 1×; E RecLF 1 NF; F 1 picking entrada) | cada etapa roda **2×** (2 pickings → 2 invoices → 2 SEFAZ → 2 DFe entrada) |
| 3 | `app/odoo/estoque/scripts/faturamento.py` (Skill 8, 5 átomos) | operam **1 `account.move`/chamada** — atômicos | invocar 2× (1 por NF); orchestrator é quem assume 1×/ciclo |
| 4 | `app/odoo/estoque/scripts/escrituracao.py` (Skill 7, 7 átomos) | **1 DFe → 1 PO → 1 invoice** por fluxo | 2 DFe na FB ⇒ 2 fluxos de escrituração |
| 5 | `app/recebimento/services/recebimento_lf_odoo_service.py` (~4,6K LOC) | `processar_recebimento` assume **1 DFe/NF por recebimento** (busca DFe FB por `numero_nf`, L928) | 1 recebimento ↔ 2 DFe (serviço + insumos) |
| 6 | `app/odoo/services/faturamento_service.py` (ETL, ~1,9K LOC) | importa `account.move`→`FaturamentoProduto` por **`numero_nf`+`cod_produto`**; `_processar_cancelamento_nf(numero_nf)` reverte MovimentacaoEstoque/EmbarqueItem/Separacao/EntregaMonitorada por `numero_nf`. **Importa NFs de industrialização sem filtro de company** (sessão 5) | 2 NF = 2 `numero_nf`; **a NF de insumos (total=0) pode gerar `FaturamentoProduto` espúrio** → filtrar/ignorar a NF simbólica no ETL p/ não re-baixar carteira em dobro |

### F. Mudanças no trabalho operacional (delta 1-NF → 2-NF)
- **Emissão (LF):** 2 NF por ciclo (1 serviço 5124 + 1 insumos 5902) em vez de 1 mista → **2 pickings/origens** com `tipo_pedido` distinto.
- **SEFAZ (saída LF):** **2 transmissões** (×2 Playwright/robô) por ciclo.
- **Entrada (FB):** **2 DFe a escriturar** (×2 PO/invoice) por ciclo.
- **Físico/armazém:** **0 mudança** — não há movimentação nova (insumos já simbólicos; só o PA move). O número de operações de estoque não muda.
- **Financeiro/conciliação:** só a NF de serviço (5124) gera título (CLIENTES/FORNECEDORES = S); a NF de insumos (total=0) **não gera título** → o conciliador deve ignorá-la (não cobrar/pagar).
- **Sistemas internos (ETL):** ajustar para 2 NF/ciclo sem duplicar baixa de carteira/movimentação (item E.6).
- **Operadores:** ver **§G** — hoje o operador **NÃO** digita componente a componente; cria **1 picking só com o PA** e o sistema expande os insumos. No 2-NF não duplica **se a 2ª NF for emitida pela automação**.

### G. Como a NF é montada HOJE — o operador NÃO digita os insumos (fluxo operacional)
**Provado ao vivo (`s7_como_emite`):**
- O picking de retorno (`LF/SAI/IND/01914`, id 322836) é criado **MANUALMENTE pelo operador** (Josefa, uid 38), **sem SO/MO/origin** (`origin`/`group_id`/`sale_id` = False), com **1 único `stock.move` — o PA** (azeite, 144 un).
- O **robô** (server action 1512) busca pickings `liberado_faturamento=True` e fatura via o wizard nativo **`stock.invoice.onshipping.create_invoice()`** (`journal = picking_type.l10n_br_tipo_pedido`). Esse wizard é **estendido pelo CIEL IT**: a partir de **1 picking com 1 linha (o PA), a NF sai com 10 linhas** (1×5124 PA + **9×5902 insumos expandidos automaticamente** da estrutura de industrialização).
- ⇒ **O operador cria 1 picking (o PA); os insumos 5902 são compostos pelo sistema.** Não há seleção componente-a-componente hoje.

**Implicação para o 2-NF (o operador NÃO precisa duplicar trabalho):** o desenho-alvo mantém o operador criando **1 picking (o PA)**; a **separação acontece na AUTOMAÇÃO**, não nas mãos do operador. Dois lugares possíveis para separar (decisão de arquitetura, parte dos 3 gaps):
- **(A) na composição do CIEL IT** — fazer o faturamento emitir 2 documentos (serviço 5124 + insumos 5902 em journals distintos). Mexe na extensão do `stock.invoice.onshipping` (código do **fornecedor CIEL IT**) — fora do nosso controle direto.
- **(B) no nosso pipeline** (Skill 8 `faturando-odoo`) — assumir a emissão das 2 NFs programaticamente (controlamos a composição das linhas e o journal de cada uma). É o caminho com mais controle nosso; alinhado ao pipeline de inventário já existente.
- ⚠️ **NÃO recomendado:** o operador criar **2 pickings manuais** (1 PA + 1 insumos) — duplicaria o trabalho manual E a expansão automática dos insumos é acoplada ao faturamento do PA (incerto se funciona num picking só-insumos). A separação deve ser **automática**, não operacional.
> **FONTE CONFIRMADA = BoM do PA** (`s7_fonte_insumos` + `s7_rastreabilidade`): os 9 insumos 5902 batem **9/9** com a BoM **`14653` (type `normal`)** do PA 4739099 — qtys idênticas (GALÃO 4 · ALÇA 4 · TAMPA 4 · RÓTULO 4 · CAIXA 1 · ETIQUETA 1 · FITA 0,94 · FILME 0,018 · ÓLEO 18,474). Existe também BoM **`14794` (type `subcontract`** — mecanismo Odoo de industrialização por encomenda). ⇒ o CIEL IT, no `create_invoice()`, **explode a BoM do PA × qty faturada** para compor as linhas 5902. **Determinístico e replicável por nós** (já explodimos a mesma BoM na remessa — `RUNBOOK §1`). O `stock.move` do PA é **avulso** (sem `move_orig`/MO/origin) → a fonte NÃO é uma remessa rastreada, é a **BoM**.

### H. Rastreabilidade remessa ↔ PA para o cenário 2-NF (vínculo de TELA nativo — `s7_rastreabilidade`)
**Existe o campo fiscal nativo `account.move.referencia_ids`** (one2many → `l10n_br_ciel_it_account.account.move.referencia`, label **"NF-e referência"**) = o **refNFe** da NF-e (referência por chave a outra NF). **Hoje a NF mista de retorno NÃO o usa** (`referencia_ids` vazio na `VND/2026/00359`; ela só tem `ref=LF/SAI/IND/01914`=o picking e `l10n_br_chave_nf` própria `35260618467441000163550010000132721007380972`). Para a ENTRADA, o equivalente é `l10n_br_ciel_it_account.dfe.referencia` ("Referência Documento Fiscal").
⇒ **2 NF COM rastreabilidade é viável e fiscalmente correto:** ambas as NFs de retorno (serviço 5124 + insumos 5902) podem **referenciar, via `referencia_ids`, a NF de remessa (RPI/5901)** — e/ou uma à outra — ligando **remessa ↔ retorno ↔ PA** na tela do Odoo (e no XML; `refNFe` é o padrão do regime de industrialização). Vínculo adicional simples: mesmo `invoice_origin`/`ref` (picking/ciclo) nas 2 NFs.
⇒ **Melhor abordagem (recomendada):** emitir as 2 NFs **pelo nosso pipeline** (Skill 8 — controlamos composição via BoM + journal + `referencia_ids`), em vez de depender da extensão `create_invoice` do CIEL IT (fornecedor). Operador segue criando 1 picking (o PA).

### I. Subcontratação nativa + fluxo de ENTRADA (`s7_subcontratacao`) — base para "1 doc → resto automático"
- **A industrialização JÁ é modelada como SUBCONTRATAÇÃO:** a BoM `14794` (subcontract) do azeite tem **`subcontractor_ids=[35]` (LF)**. Infra de subcontratação existe: **pt74** "Subcontratação" (FB, mrp_operation) · **pt75 "Reposição para subcontratação"** (FB, outgoing = o *resupply* de componentes FB→LF) · **pt80** "Subcontratação" (LF) · pt95 "REMESSA TERCEIRO (FB)".
- **Fluxo de ENTRADA provado (ENTSI 506211):** `DFe 38128 → PO 36548 (C2615462, tipo_pedido=serv-industrializacao) → invoice 506211`. A **PO já traz as 26 linhas** (1 PA KETCHUP + 25 componentes) → na entrada a composição vem da **PO**, não de expansão no momento da invoice. Vínculos nativos: **`account.move.dfe_id`** (= 38128) + **`invoice_origin`=PO**. *(Essa ENTSI foi criada por uid 42/Rafael — caso de teste; a cadeia DFe→PO→invoice é o padrão.)*
- ⇒ **Rastreabilidade de entrada já é NATIVA** (DFe ↔ PO ↔ invoice). Na saída, o vínculo é `referencia_ids` (refNFe, §H).
- ⇒ **Duas materializações do "1 dispara tudo" (ver resposta ao Rafael 2026-06-02):** **(Forma 1) subcontratação nativa** — gatilho = 1 **PO de compra do PA** à LF → resupply (pt75) + recebimento automáticos + rastreabilidade nativa; a camada fiscal BR (5901/5902/5124) é o que falta mapear com o CIEL IT. **(Forma 2) nosso pipeline deriva** — gatilho = a NF de serviço; a 5902 (saída) e a 1902 (entrada) são derivadas da BoM e vinculadas por refNFe/PO. **A 5902/1902 é 100% derivável da BoM do PA** → emitir/escriturar só 1 e gerar a outra automaticamente é tecnicamente sólido em ambas.

**RESOLVIDO — uso medido (`s7_ciclo_subcontratacao`): a subcontratação nativa está CONFIGURADA mas DORMENTE.** 153 BoMs subcontract (100% subcontratante=LF), MAS **0 pickings** em pt75/pt74/pt80 (resupply + MO subcontract **nunca usados**) e **1 única MO subcontract — CANCELADA, 2024** (FB/SBC3/00001). O fluxo REAL é via **3087 POs `serv-industrializacao`** (entrada FB, geradas do DFe) + pickings MANUAIS (pt53 remessa / pt66 retorno) + robô CIEL IT.
- ⇒ **VEREDITO: Forma 1 (subcontratação nativa) NÃO recomendada** — exigiria reativar um fluxo morto p/ 153 produtos + validar a camada fiscal CIEL IT do subcontracting (nunca exercitada) + retreinar operação. Alto risco/esforço, muda o dia-a-dia.
- ⇒ **Forma 2 (pipeline deriva) é o caminho** — aderente ao fluxo atual. **A ENTRADA já é automática e vinculada** (`DFe → PO serv-industrializacao → invoice`, 3087 casos): 2 DFes (serviço + insumos) gerariam 2 escriturações automáticas, ligadas por refNFe/PO. **O trabalho concentra-se na SAÍDA** (separar a emissão que hoje funde tudo em 1 NF via expansão da BoM no robô — o nosso pipeline emite a 2ª NF de insumos derivada da BoM, OU customiza-se o `create_invoice` do CIEL IT).


## ACHADO 2026-06-03 (sessão 8) — hipótese (i) REFUTADA (create_invoice FUNDE) + GATE 0 armado

> READ-only (4 scripts: `s8_hipotese_i_grounding`, `s8b_server_action_grounding`, `s8c_gate0_mapear`, `s8d_gate0_split_experimento` em dry-run). Zero escrita Odoo. Painel adversarial 3 lentes sobre a hipótese (i). Outputs originais em `/tmp` (efêmeros, perdidos); **fatos centrais re-validados ao vivo em 2026-06-12** (s8c+s8d re-executados — estado idêntico).

### TL;DR (sessão 8)
1. **Hipótese (i) do handoff REFUTADA** (painel 3 lentes, 3/3): o `create_invoice()` do CIEL IT (`stock.invoice.onshipping`) **FUNDE** 5124+5902 na NF do picking faturado — **não** separa a expansão da BoM por picking_type. Não existem "2 NFs nativas só por config" via wizard.
2. **VIA 1 (rotear o PA por uma operação 5124 "sem explosão") FECHADA**: TODAS as operações com CFOP 5124 (ops **849**/FB, **2702**/LF, **3039**/LF) têm `tipo_pedido='venda-industrializacao'` — 5124 ≡ venda-industrializacao; não há tipo alternativo p/ o PA escapar da expansão. *(Re-confirmado ao vivo 12/06.)*
3. **Server action no Odoo é veículo VIÁVEL para a automação** (pergunta do Rafael, `s8b`): precedentes de robôs/server actions custom existem (11 robôs CIEL IT); padrão de disparo = cron/`base.automation`. ⚠️ Risco conhecido: server action custom **some em upgrade** do CIEL IT (precedente DFE NFD) — exige runbook de re-aplicação.
4. **Questão central convergiu para: como a NF do PA sai SÓ-5124** (a expansão das 5902 é embutida no `create_invoice`). Caminho restante = **VIA 2/B: split na janela DRAFT→pré-SEFAZ** — deixar a NF mista nascer e separá-la em 2 documentos ANTES de transmitir.
5. **GATE 0 armado (`s8d_gate0_split_experimento.py`) — AGUARDANDO GO**: copia a VND mista menor (**180552** `VND/2025/00089`, 1×5124 + 24×5902, total R$43,37) para 2 journals de teste — **cópia A** só-5124 (no_payment VAZIO) e **cópia B** só-5902 (`no_payment=26667` PASSIVA) — recompute fiscal nativo → `action_post` (SÓ contábil, **sem SEFAZ**) → mede contrapartidas (A: D CLIENTES só do serviço; B: baixa `5101020001`) → cleanup total (draft+unlink+deleta journals, zero sujeira). Modos: dry-run (sem flag) → `--confirmar` → `--postar A B` → `--cleanup A B JA JB`.
6. **3 gaps fiscais permanecem** (inalterados 12/06): (a) op 5124-sem-explode inexistente (item 2); (b) **nenhum journal sale LF com `no_payment=26667`** (j847 venda-industrializacao = no_pay VAZIO; j1003 perda → 26652 ATIVA — o erro dos R$8,67M); (c) pt98 `tipo_pedido=False`.

### Estado ao vivo re-validado (2026-06-12)
- PA piloto 27834 (4870112): **1 un em `31093 LF/PA-Terceiros`, lote `PILOTO-3105` (lot 60542), reserva 0** — pronto p/ Etapa 4. (+1 un em 42/LF-Estoque lote 142/26, fora do piloto.)
- NF-modelo do experimento intacta: 180552 `VND/2025/00089` (1×5124 + 24×5902). Próximas candidatas: 76427 (R$81,20), 149498 (R$100,74).
- Operações 5902: op 850 (FB, dev-industrializacao) · op **2710** (LF, dev-industrializacao → j1002 RETRABALHO) · op **2864** (LF, venda-industrializacao = a da NF mista).


## ACHADO 2026-06-12 (sessão 9) — grounding do desenho da emissão (robô lido por dentro + valores da expansão)

> READ-only (`s9_grounding_desenho.py` + leitura do `code` da server action 1512 + follow-ups). Zero escrita Odoo. Fundamenta o desenho `SOT §6.1`.

### TL;DR (sessão 9)
1. **O robô NÃO transmite à SEFAZ** — o code da 1512 tem o bloco `## DESATIVADO TRANSMISSAO DA NFE` com `continue` ANTES do `action_gerar_nfe()`. O robô só: busca pickings → wizard → `create_invoice()` → onchange impostos → `action_post`. A transmissão das VND (autorizadas em ~5–10 min após create, cstat=100) é de OUTRO ator (manual/Josefa — não há cron de transmissão ativo com nome fatura/nfe/nf-e/transmit). ⇒ a "corrida" pós-post é com humano, não com cron — mas o desenho não depende de janela (conduzimos a emissão inteira).
2. **Domain do robô (12 crons de 1 min, particionados pelo campo `picking.robo`=1..11):** `[(company), (picking_type_id.invoice_move_type='out_invoice'), (state='done'), (date_done>=2023), (liberado_faturamento=True), (erro_faturamento=False), (robo=N)]` — e **PULA picking com `invoice_id` setado** (não-cancelado). ⇒ **2 alavancas de isolamento**: não liberar faturamento E/OU faturar nós primeiro (invoice_id ocupa o slot). Campo `robo` é uma 3ª alavanca.
3. **O wizard é chamável por nós**: o robô faz exatamente `stock.invoice.onshipping.with_context(active_ids=[picking]).create({'company_id', 'journal_id'})` → `create_invoice()` — journal passado EXPLICITAMENTE (fallback: journal sale com `l10n_br_no_payment=False`). ⇒ replicar a expansão nativa via XML-RPC = a mesma chamada (R1 literal). Em erro, o robô marca `picking.erro_faturamento=True` + activity (não tocar nesses campos).
4. **V3 — valores da expansão NÃO vêm da remessa**: nas linhas 5902 da VND/2026/00359, `price_unit` = **`lst_price` do cadastro** (3 matches exatos de 11 casas: ETIQUETA 0.02561108249, FILME 8.0777707682, FITA 0.06769348779); 7 produtos com lst_price=0 hoje têm pu≠0 (preço da época/pricelist). ⇒ **invariante fiscal 5902=5901 NÃO é garantido pelo nativo** — a NF-insumos deve ter price_unit FORÇADO = valores da remessa (nós os temos).
5. **V4 — precedente SEFAZ p/ NF simbólica (CORRIGIDO pós-painel)**: NF **total=0 autorizada existe** (SARET cstat=100), MAS as SARET autorizadas são **CFOP 5949** — a única SARET com CFOP **5902** (SARET/2026/00003, move 630193) está **CANCELADA sem cstat**. ⇒ **NÃO há precedente vivo de NF só-5902 autorizada** — a 1ª transmissão do regime será inédita. Precedente de FORMA mais próximo = a própria **remessa RPI/5901** (NF standalone do regime, CST 50, autorizada rotineiramente). Tratar rejeição como cenário normal (corrigível em draft).
6. **V5/R3 — modelo do refNFe verificado**: `l10n_br_ciel_it_account.account.move.referencia` = `{move_id, l10n_br_chave_nf (44 díg.), company_id}` — preencher é um create simples.
7. **Campos de status NFe** (nomes reais): `l10n_br_chave_nf`, `l10n_br_cstat_nf`, `l10n_br_situacao_nf` (selection: 'autorizado', 'cce', …), `l10n_br_xml_aut_nfe`. (Sufixo `_nf`, não `_nfe`.)

### Painel adversarial sessão 9 (3 lentes sobre o desenho `SOT §6.1`) — fatos NOVOS verificados ao vivo
> 30 findings (6 HIGH), veredicto unânime AJUSTES_NECESSARIOS (espinha do desenho mantida). Incorporados na `SOT §6.1 v3.1`. Fatos abaixo re-verificados pelo agente principal (12/06):
- **CST real por linha (docs anteriores diziam "CST 51 suspenso" — ERRADO):** 5901 e 5902 = **ICMS CST 50 (suspensão)** + PIS/COFINS 08 + tax_ids=[]; **5124 = ICMS CST 51 (diferimento)** + PIS/COFINS 01. Verificado em RPI/2026/00245 e VND/2026/00359. Não hardcodar CST na implementação.
- **`account.journal.l10n_br_no_payment` (boolean) é campo armazenado INDEPENDENTE da conta** — os precedentes vivos do mecanismo (j1002, j1003) têm **boolean True + conta**; existem journals com conta setada e boolean False. ⇒ journal de teste/RETIND DEVE setar os 2 (fix aplicado no `s8d` v3.1). Os experimentos das sessões 5/6 (journals reais j847/j1001) não são afetados — só o journal de TESTE nascia incompleto.
- **pt98: `invoice_move_type=False` + `tipo_pedido=False` CONFIRMADO ao vivo** (pt66 = 'out_invoice' + 'venda-industrializacao'). Configurar pt98 é PRÉ-REQUISITO do GATE 1; setar invoice_move_type coloca o picking no domain do robô ⇒ compensar com `picking.robo` fora de 1..11 (3ª alavanca).
- **Guard `invoice_id` do robô tem comentário `# REGRA DESATIVADA`** no code (o if está ativo hoje, mas a CIEL IT já mexeu nele) — não confiar como única proteção. Caminho residual: invoice cancelada + `refaturar_se_cancelado=True` + liberado ⇒ robô re-fatura.
- **Expansão da BoM só foi provada em pt66** (42→5); pt98 (31093→26489, 0 usos) é contexto novo — engine seleciona operação POR LINHA por partner/destino ⇒ asserts no GATE 1 (nº linhas, CFOPs, ops).

### ✅ GATE 0 EXECUTADO E APROVADO (2026-06-13) — o mecanismo do split em 2 docs está PROVADO
> Experimento `s8d_gate0_split_experimento.py` rodado em PROD com go do Rafael, em journals de TESTE, **sem SEFAZ**, postado e **deletado** (cleanup verificado: 0 journals residuais, 0 moves, NF-modelo 180552 intacta posted/43,37/25 linhas). Cópias da VND/2025/00089 (1×5124 + 24×5902).

**Resultado contábil (pós-`action_post`):**
- **Cópia-A (PA só-5124)** → NF de serviço **limpa**: `D 1120100001 CLIENTES 35,00 / C 3101030001 SERVIÇOS DE INDUSTRIALIZAÇÃO 33,39 + PIS/COFINS`. untax=33,39 total=35,00. (separar as 5902 não quebrou a NF do serviço.)
- **Cópia-B (INSUMOS só-5902, journal `l10n_br_no_payment=True` + conta 26667)** → **`D 5101020001 REMESSA INDUSTRIALIZAÇÃO (PASSIVA) 8,37 / C 1150100012 FATURAMENTO FÍSICO FISCAL (24 linhas, 8,37)`**. **untax=8,37 total=0,0**. ⇒ **A PASSIVA É BAIXADA (débito) — sem CLIENTES.** ✅ Hipótese central do desenho CONFIRMADA: documento separado só-5902 com no_payment redireciona a contrapartida-resumo (que seria CLIENTES) para a conta de compensação.

**Aprendizados (entram no desenho/GATE 1):**
1. **O redirecionamento do no_payment só materializa no `action_post`** — em DRAFT a cópia-B mostrava `D CLIENTES 8,37`; só após postar virou `D 5101020001`. ⇒ no GATE 1 **NÃO assustar com o draft**; medir contrapartida apenas pós-post.
2. **O boolean `l10n_br_no_payment=True` (fix do painel) estava no journal-B e funcionou** — não dá para isolar se a conta sozinha bastaria, mas o desenho está validado COM o boolean (spec RETIND mantém os 2 campos).
3. **RESÍDUO — conta de contrapartida das 5902**: na cópia-B as 5902 creditaram a transitória `1150100012` (herdada da NF-modelo). No fluxo REAL (NF-insumos simbólica, sem stock.move) essa transitória **não tem SVL que a feche** → ficaria aberta. Para o NET fechar contra a Etapa 2 (`D 1150200001 / C 5101020001`), as 5902 da NF-insumos real precisam creditar a **conta de terceiros `1150200001`** (não a transitória) — definido pela **operação fiscal** da linha 5902, não pelo journal. ⇒ **a verificar no GATE 1** (o GATE 0 provou a baixa da PASSIVA, que é o que estava em xeque; a perna da contrapartida é refinamento do par net-zero, conecta com Design A/B da Etapa 2).
4. A 180552 tem 5902 com valor real (8,37 contribui ao total da mista) — a NF-insumos do regime deve ter `price_unit` = valores da remessa (já no desenho, V3).

### ✅ CONFIG APLICADA (2026-06-13) — pré-requisito do GATE 1 (cadastro, reversível, sem SEFAZ)
> `s10_config_emissao.py` (dry-run → `--confirmar`, validado `--validar`). Reversível: `--revert` (deleta journal + restaura pt98). **Veículo = server action** (decidido Rafael 13/06).
- **Journal RETIND `id=1083`** criado (LF sale): `l10n_br_no_payment=True` + `account_no_payment_id=26667` (5101020001 PASSIVA) + `l10n_br_tipo_pedido=VAZIO` (impede o robô de roteá-lo; nós setamos o journal no split). Combinação PROVADA no GATE 0. *(j1047 ENTRADA-REMESSA é purchase e já usa 26667 — o RETIND é o lado SALE, que faltava.)*
- **pt98 "Retorno Industrialização (LF)" configurado** (era `invoice_move_type=False`/`tipo_pedido=False`, 0 usos): agora `invoice_move_type='out_invoice'` + `l10n_br_tipo_pedido='venda-industrializacao'` (espelha o pt66 no que importa p/ faturamento, mantendo src/dest de terceiros `31093→26489`). **Escolhido configurar pt98 (não clonar pt66)** — pt98 já é semanticamente o retorno de terceiros, 0 usos.
- ⚠️ **No GATE 1**: o picking pt98 do piloto deve ficar `liberado_faturamento=False` + `picking.robo` fora de 1..11 (agora que pt98 tem `invoice_move_type='out_invoice'`, entra no domain do robô se houver picking liberado).

### ⚠️ GATE 1 EXECUTADO (2026-06-13) — 3 camadas reveladas; 1 BLOQUEADOR (`s11_gate1_emissao.py`)
> Ensaio da emissão no piloto real (produto **4870112 MOLHO SHOYU**, lote PILOTO-3105). Tudo revertido: NF draft deletada, PA de volta em 31093. **Rastro:** 4 pickings done origin=GATE1 (2 saídas + 2 devoluções internas, net-zero — não deletáveis, rastreáveis). **PA preservado.**

1. **pt98 (dst 26489) REFUTADO empiricamente** — faturar o picking 31093→**26489** falha (`Empresas incompatíveis: Account 3101010001 pertence a outra empresa`): o destino transito **não dispara a operação fiscal** de venda-industrializacao. As VND reais saem por **pt66 → `5` Parceiros/Clientes** (provado: VND 738097, src 42→dst 5, linha 5124 conta 26349 SERVIÇOS, op 2702). ⇒ **picking de retorno = pt66 com src override 31093, dst 5** (NÃO pt98/26489). **pt98 config revertido** (volta a False/False).
2. **🔑 GOTCHA `create_invoice` exige contexto LF-ONLY** — via XML-RPC com `allowed_company_ids=[1,5]` o Odoo resolve a property `income` da categoria na company **FB** (conta 22497 = `3101010001` FB) → `Empresas incompatíveis`. Com **`allowed_company_ids=[5]` apenas (como o robô: `company.ids`)** → resolve na LF (26344) → **OK, NF draft criada em 48s**. ⇒ todo faturamento via wizard XML-RPC roda **company-only**, NÃO `[1,5]` (contraria a regra geral de ops LF). **Timeout do recompute = 48s** (o >400s anterior era do `onchange` numa mista grande — aqui o create_invoice já calcula).
3. **🔴 A expansão automática dos insumos 5902 NÃO ocorre p/ o shoyu** — a NF sai com **1 linha (5124 PA) e ZERO 5902** (azeite 4739099 expande 9/9). **Investigado e REFUTADO** (cadastros replicados ao vivo, criados+deletados): NÃO é a BoM `subcontract` (criei a do shoyu = 14794-clone, 16 comps → **não destravou**), NÃO é a `route` "Comprar-FB" id 5 (adicionei → não destravou), NÃO é o supplierinfo LF (ambos já têm partner 35/company FB). **Causa = comportamento fiscal PROFUNDO do CIEL IT (caixa-preta):** a linha do PA sai com `l10n_br_compra_indcom='uso'` no shoyu vs **`'ind'`** no azeite (campo mora no `res.partner` FB=`ind`, mas o motor resolve `uso` p/ o shoyu) — **mesma operação 2702** nos 2, mas conta/finalidade divergem (shoyu→`3101010001 VENDA PRODUÇÃO` 26344; azeite→`3101030001 SERVIÇOS` 26349). Provável: o shoyu nunca foi cadastrado como produto de industrialização no CIEL IT (config fiscal não exposta nos campos que controlamos; NCM/categoria diferem). VND real 738097 = criada pelo OdooBot/robô via create_invoice (a expansão É server-side p/ o azeite).

⇒ **CONCLUSÃO (reforça a Forma 2): NÃO depender da expansão automática (R1 "do jeito que hoje").** O `create_invoice` gera a **NF do PA (5124) correta** (pt66 + CTX LF-only); a **2ª NF de insumos (5902) NÓS derivamos da BoM/remessa** — já temos os 16 componentes + op **2864** + CST 50 + conta 26855 + price_unit da remessa (template = VND real 738097). **Próximo: GATE 1b — montar as 16 linhas 5902 programaticamente** (op 2864) na NF (ou em doc próprio no RETIND 1083) e validar impostos/baixa da PASSIVA. **Rollout:** decidir se vale fazer o CIEL IT cadastrar os produtos como industrialização (expansão nativa) OU sempre derivar pelo pipeline (Forma 2 pura — mais controle, não depende do fornecedor).

**Estado:** tudo revertido — shoyu restaurado (route_ids `[134,1]`, sem BoM subcontract, pt98 `False/False`), PA em 31093, NFs draft deletadas. **RETIND 1083 mantido** (cadastro válido). Rastro: pickings done origin=GATE1 (net-zero, não deletáveis). Scripts: `s11_gate1_emissao.py` (parametrizável `--produto/--lote/--src`), `s12_bom_subcontract.py`.

### 🔑 GATE 1b (2026-06-13) — a expansão é SERVER-SIDE, não do produto (reorienta o desenho)
> Sugestão do Rafael: testar com um produto que **já expande** (azeite 4739099, que tem a config completa). Estado revertido (azeite 4 un de volta em 42).
- **O azeite TAMBÉM não expandiu pelo nosso `create_invoice` via XML-RPC** (NF 1×5124, 0×5902 — idêntico ao shoyu). Testado server-side via **`ir.actions.server` de teste** (autorizada pelo Rafael; replicou o robô com `sudo` + journal-por-tipo_pedido + onchange): **n0_create=1, n1_onchange=1 — NÃO expande nem server-side.** *(`action_post` foi bloqueado pelo classificador — postar no j847 real é além do teste draft-only.)*
- 🔑🔑 **DESCOBERTA DEFINITIVA (fecha o mistério) — a expansão é MANUAL, não automática.** Na NF real `738097`: a linha **5124 (PA) foi criada por OdooBot/robô às 17:00:57**; as **9 linhas 5902 foram criadas pela OPERADORA Josefa (uid 38) às 17:12:18** (12 min depois, **todas no mesmo timestamp** = um botão/wizard, não digitação 1-a-1). ⇒ **NÃO EXISTE expansão automática.** O robô cria a NF só com o PA; a **operadora adiciona os insumos manualmente** depois. **REFUTA a sessão 7 §G** ("o operador NÃO digita os componentes; a expansão é automática") — toda a busca por "como o create_invoice expande" foi atrás de um mecanismo inexistente.
- ⇒ **CONCLUSÃO (definitiva): a Forma 2 É o caminho, e o R1 da Contadora pede AUTOMATIZAR o que hoje é MANUAL.** "Do mesmo jeito que os componentes são incluídos na NF hoje" = a Josefa inclui à mão. ⇒ **nós criamos as 16 linhas 5902 da BoM/remessa** (op 2864, CST 50, conta 26855, price da remessa) — automação do passo manual. **Viável via XML-RPC** (criar `account.move.line`; os computes rodam no write server-side) — **não precisa de server action para "reproduzir expansão"** (não existe). A decisão do veículo (server action vs pipeline) volta a ser só de orquestração. A investigação de cadastro (BoM subcontract/rota/compra_indcom/server-side) foi toda um beco — não havia mecanismo automático a achar.
- ✅ **CONFIRMADO 100% MANUAL e SISTÊMICO** (pesquisa 13/06): em **30 VND mistas recentes**, as **262 linhas 5902 foram TODAS criadas por operadoras humanas** — Josefa (uid 38) = 212, Histaina (uid 1250) = 50; **ZERO pelo robô/OdooBot**. **NÃO há botão/wizard CIEL IT** específico (a view form do account.move só tem transmissão NFe/REINF/boleto + "Atualizar Impostos"=onchange; nenhum act_window de componente/industrializa); as operadoras **editam o grid da NF à mão** (selecionam os produtos com CFOP 5902/op 2864). É trabalho manual repetitivo de 2 pessoas → exatamente o que o R1 da Contadora quer automatizar. *(A doc do projeto não tem o método — Explore confirmou; só o que documentamos hoje.)*
- ✅ **DECISÃO (Rafael 13/06): plano B (Forma 2) via SERVER ACTION** — criar as linhas 5902 **server-side** garante que os computes fiscais (impostos/CST/operação) rodem como no robô (via XML-RPC os onchange não persistem). ▶️ **Próximo (GATE 1c, precisa de go p/ server action de ESCRITA em PROD):** server action que, dado o picking/PA, **explode a BoM e adiciona as N linhas 5902** (op 2864, CST 50, conta 26855, price=remessa) na NF do PA — automatizando o passo das operadoras → split no RETIND 1083 → medir baixa PASSIVA → GATE 2 (SEFAZ).
- **BUG corrigido** no `s11 --revert`: checava estoque em SRC — produtos com saldo pré-existente (azeite tinha 4) enganavam e deixavam 1 un presa em Clientes. Agora devolve se o picking de saída está `done`. Estado final limpo: azeite 4 em 42, shoyu 1 em 31093, 0 SA/NF de teste residual. Scripts: `s14_gate1b_serveraction.py` (SA de teste, deletada no fim).


## Contexto

Documento — industrializacao por encomenda FB<->LF. Tema: ACHADOS TÉCNICOS — Industrialização FB↔LF (Odoo / CIEL IT)

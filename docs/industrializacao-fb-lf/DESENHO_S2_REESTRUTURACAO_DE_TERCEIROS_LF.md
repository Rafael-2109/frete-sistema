<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/industrializacao-fb-lf/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# DESENHO S2 — Execução wired da reestruturação do estoque LF → "De Terceiros" (31092/31093)

> **Papel:** plano de execução wired (entregável da Sessão 2) da reestruturação do estoque LF para "De Terceiros" (31092/31093), com a investigação ampla ao vivo que o fundamenta. **Abra quando:** for revisar/decidir o GATE da S2 ou iniciar a S3.

> **🔴 SESSÃO 2 (de 4) — DESENHO + investigação ampla. NÃO implementar.** Entregável = este plano de execução wired, costurado ponta a ponta. **GATE:** Rafael aprova/decide ANTES de iniciar a S3 (implementação Odoo). Companheiro do `MACRO_REESTRUTURACAO_DE_TERCEIROS_LF.md` (S1). Toda afirmação de As-Is foi verificada AO VIVO no Odoo (READ-only) — fontes nos scripts `s72`–`s78` (`docs/industrializacao-fb-lf/scripts/`).

## Indice
- [0. Sumário executivo](#0-sumário-executivo)
- [1. As-Is confirmado ao vivo (evidências)](#1-as-is-confirmado-ao-vivo-evidências)
- [2. Três descobertas que ALTERAM o desenho do MACRO](#2-três-descobertas-que-alteram-o-desenho-do-macro)
- [3. Plano wired — estado-alvo](#3-plano-wired--estado-alvo)
- [4. Migração do saldo (mecanismo)](#4-migração-do-saldo-mecanismo)
- [5. Exceções e pré-condições](#5-exceções-e-pré-condições)
- [6. Ordem de execução da S3 + validações + reversibilidade](#6-ordem-de-execução-da-s3--validações--reversibilidade)
- [7. Decisões pendentes (GATE Rafael)](#7-decisões-pendentes-gate-rafael)
- [Contexto](#contexto)

---

## 0. Sumário executivo

A LF é industrializadora por encomenda — **100% do material é da FB (terceiros)** — mas hoje todo o estoque gira em `42 LF/Estoque` como se fosse próprio. O alvo é segregar em `31092 LF/Materiais de Terceiros` (MP+EMB) e `31093 LF/PA de Terceiros` (PA), refletindo a propriedade **fisicamente** e alinhando a **automação G1** (que já lê de `31092`).

**A investigação ao vivo refutou 2 premissas do MACRO e propõe uma abordagem mais limpa:**

1. **Contábil não é por location** — a valoração vem da `product.category` (todas apontam para contas de estoque PRÓPRIO LF; campos de conta da location estão vazios). Mover entre locations internal é **contabilmente neutro** (provado: 2000 moves internal→internal = 0 SVL). ⇒ a reestruturação física **não** torna o estoque "terceiros contábil" sozinha; isso é a alavanca de categoria (L1), **decisão separada** (§7-D1).
2. **Roteamento por rule/picking_type não separa PA de material** — os picking_types misturam os dois (pt66 majoritariamente PA; pt94/pt20 majoritariamente material; pt34 material). A separação correta é **por categoria de produto** ⇒ **put-away rule**, não edição de src/dst em 15 rules.
3. **`31092`/`31093` são IRMÃS de `42`** (todas filhas de `41 LF` view), e o warehouse tem **`lot_stock_id=42`**. Mover o saldo p/ irmãs o tira do escopo do lot_stock (quebra on-hand/MRP e a reserva das saídas `src=42`). ⇒ é preciso **reparentar 31092/31093 sob 42** (recomendado) ou mudar o lot_stock (§7-D2).

**Abordagem DECIDIDA (Rafael, 2026-06-15 — GATE S2):**
1. **Reparent `31092`/`31093` sob `42`** (D2) — `lot_stock` segue 42 (internal); on-hand passa a vê-las; saídas `src=42` reservam delas; entradas `dst=42` + put-away separam. (Decisão "lot_stock→41" foi **refutada**: `lot_stock_id` exige `usage=internal` e 41 é `view` — `s79`.)
2. **Put-away por categoria** (PA→31093; fallback→31092) — separa no depósito, em qualquer fluxo de entrada.
3. **Migração** do saldo existente 42→31092/31093 por categoria, **exceto o açúcar reservado** (D3).
4. **Repoint contábil de terceiros (L1)** (D1) — categorias LF passam a valorar em conta de terceiros (`1150200001`) + reclassificação do saldo existente. **Ponto mais delicado** — ancorar no L1 já validado na Etapa 2 (§3.4).

Com (1)+(2)+(3), **quase nenhuma rule precisa mudar** (entradas continuam dst=42 e a put-away redireciona; saídas continuam src=42 e reservam das filhas). (4) é a camada contábil sobre essa base física.

---

## 1. As-Is confirmado ao vivo (evidências)

### 1.1 Locations-chave (fonte: `s72`/`s74`)
| ID | usage | parent | nome | papel |
|---|---|---|---|---|
| 41 | view | 1 Locais Fisicos | LF | raiz da empresa LF |
| **42** | internal | **41** | LF/Estoque | **HUB atual** (lot_stock do WH) |
| 53 | internal | 41 | LF/Pré-Produção | componentes p/ MO |
| 54 | internal | 41 | LF/Pós-Produção | PA recém-produzido |
| 30710 | internal | 53 | LF/Pré-Produção/Intermediário | semi |
| 28835 | internal | 42 | LF/Estoque/PREPARAÇÃO | (única filha real de 42 hoje) |
| **31092** | internal | **41** | LF/Materiais de Terceiros | **ALVO MP+EMB** (vazio) |
| **31093** | internal | **41** | LF/PA de Terceiros | **ALVO PA** (vazio) |
| 26489 | transit | 3 Estoque Virtual | Em Transito (Industrialização) | trânsito FB↔LF |
| 30716 | internal | 1 | Local de subcontratação (LF) | dormente |

### 1.2 Warehouse LF (fonte: `s73`/`s78`)
`[4] LF` — **`lot_stock_id=42`** · `reception_steps=one_step` · `delivery_steps=ship_only` · `manufacture_steps=pbm_sam` (pick-components→manufacture→store) · `manufacture_to_resupply=True`. Features **ativas**: `group_stock_multi_locations`, `group_stock_storage_categories`, `group_adv_location` ⇒ **put-away rules disponíveis**. **0 put-away rules hoje.**

### 1.3 Rules ativas que tocam o foco (42/31092/31093/53/54) (fonte: `s73`)
| rule | rota | action | src → dst | pt | obs |
|---|---|---|---|---|---|
| 130 | Comprar - LF | buy | — → **42** | 19 | compra (heterogêneo MP+EMB+PA) |
| 131 | Fabricar P.A - LF | manufacture | — → 54 | 36 | PA produzido → Pós-Produção |
| 135 | Fabricar P.A - LF | pull | 54 → **42** | 35 | armazenar PA |
| 136 | Fabricar P.I - LF | manufacture | — → 53 | 36 | intermediário |
| 132 | 3 passos | pull | **42** → 53 | 34 | abastece produção (componentes) |
| 134 | 3 passos | push | 54 → **42** | 35 | armazenar PA |
| 138 | 3 passos | pull | 53 → 39 | 36 | consumo na produção |
| 17 | Entregar 1 etapa | pull | **42** → 5 Clientes | 20 | entrega |
| 20 | PSE - LF | pull | **42** → 5 Clientes | 20 | entrega MTS/MTO |
| 35 | PSE - LF | pull | **42** → 39 Produção | 36 | consumo |
| 36 | PSE - LF | pull | **42** → 53 | 34 | abastece produção |
| 67 | PSE - LF | pull | **42** → 4021 Subcontr. | 48 (**OFF**) | dormente |
| 151 | PSE - LF | pull | **42** → 26483 Subcontr. | 63 (**OFF**) | dormente |
| 65/66 | **Fabrico (rota INATIVA)** | — | — | — | ignorar |

### 1.4 Picking types relevantes (fonte: `s73`)
`pt19` Recebimento (→42) · `pt20` Ordens de Entrega (42→) · `pt23` Transferências Internas (42→42) · `pt24` Devoluções (→42) · `pt34` Escolha Componentes (42→39, rule sobrescreve p/ 53) · `pt35` Armazenar PA (54→42) · `pt64` Recebimentos Industrialização (26489→42) · `pt66` Expedição Industrialização (42→5, `tipo_pedido=venda-industrializacao`) · `pt94` Expedição Ñ Aplicado (42→5, `perda`) · `pt97` Expedição Industrialização Retorno (42→5, `dev-industrializacao`) · **`pt98` Retorno Industrialização (31093→26489, JÁ em 31093)** · `pt48`/`pt63` Subcontratação (**OFF**).

### 1.5 Histórico real de stock.move (done, 365d, fonte: `s74`)
**Entradas em 42:** compras `pt19` (1338, src Fornecedores) · armazenar PA `pt35` (975, src 54) · industrialização `pt64` (273, src **Clientes**) · ajustes (1986, src 38). **Saídas de 42:** componentes→produção `pt34` (17915 → dest 53; **maior fluxo**) · Clientes (1754: pt66/pt94/pt97/pt20) · ajustes (1318 → 38) · 32 → 26489 (retornos antigos, hoje via pt98 de 31093). **Nenhum fluxo real de subcontratação.**

### 1.6 Conteúdo PA vs material das saídas (fonte: `s77`) — por que put-away
| pt | total | composição |
|---|---|---|
| pt34 (componentes) | 4000 | 2112 MP · 1734 EMB · 152 desp · ~PA 0 → **material** |
| pt66 (Exp Ind.) | 990 | 957 **PA** · 20 MP · 13 EMB |
| pt97 (Exp Ret.) | 85 | 82 **PA** · 3 EMB |
| pt94 (perda) | 695 | 413 EMB · 218 MP · 54 SEMI · 8 PA → **material** |
| pt20 (entrega) | 26 | 24 EMB · 1 MP · 1 PA → **material** |
⇒ o mesmo pt carrega PA **e** material ⇒ separar por **categoria** (put-away), não por src/dst fixo.

### 1.7 Contábil (fonte: `s72`/`s75`/`s76`/`s80`/`s81`)
- Valoração por **`product.category`** (`real_time`/`average`), company-specific via `ir.property` — **não por location** (`valuation_in/out_account_id` de 42/31092/31093/54/53/26489 = **vazios**).
- ⚠️ **Correção (`s80`/`s81`):** a leitura do `s72` resolveu a conta pela company errada (mostrou "tudo próprio"). O `ir.property` direto da company 5 mostra **14 categorias já em terceiros `1150200001`** (piloto shoyu) e ~159 em próprio (`1150100001/002/007`, IDs LF 26132/26133/26138). Saldos: `1150200001`=-69k, `1150200002`=-11,96M, `1150100001`=-21,3M, `1150100002`=-5,3M, `5101010001`=+8,67M, `5101020001`=-5,87M.
- **Cruzamento saldo×classe (`s81`):** 443 quants em 42 → **318 já terceiros / 125 próprio** ⇒ L1 ~72% feito (base de A5, §3.4).
- **Prova de neutralidade:** 2000 moves internal→internal (c5/365d) = **0 SVL**; `pt35` (54→42) = 0 SVL; `pt64` (Clientes→42) = 273 SVL (entrada valorada — só muda a location interna de destino se redirecionada).

### 1.8 Universo de migração + reservas/MOs (fonte: `s72`/`s75`)
- **443 quants (qty≠0) em `42` direto** (NÃO nas sublocations MOLHO/etc) · 5,66M un · 311 produtos.
- **442 livres + 1 reservado** (açúcar). **440 com lote** · 3 sem lote. **PA ≈ 10 produtos** (óleos/molhos/conservas) · MP+EMB ≈ 301.
- Lotes especiais: **82 quants lote `P-15/05`** + **5 quants lote `MIGRAÇÃO`/`migração`** (migram normal — são lotes válidos).
- **Única reserva aberta em 42:** ML 217666132 → picking **`321794 LF/LF/SAI/RNA/00103`** (ACUCAR CRISTAL, lote 230326, 999 un, 42→Clientes, sem MO) = a "saída FB pendente" do MACRO.
- **Única MO ativa:** `20797 LF/MO/03575` (KETCHUP, confirmed), abastecida de **53** — **0 raws reservando em 42**. ⇒ migração não colide com produção.

---

## 2. Três descobertas que ALTERAM o desenho do MACRO

1. **D-CONT — "conta de terceiros por location" não existe no Odoo aqui.** O MACRO item 5 ("definir conta de valoração de 31092/31093 terceiros vs 42") parte de premissa incorreta: a conta vem da **categoria**, não da location, e os campos de conta da location estão vazios. A reestruturação física é **neutra**. Tornar "terceiros contábil" exige a alavanca **L1 (repoint de categoria)** — que afeta **todo** o estoque LF da categoria, em qualquer location → **§7-D1**.
2. **D-PUT — separar PA/MP pede put-away por categoria.** Editar src/dst nas 15 rules (Abordagem B do MACRO) não separa corretamente porque os picking_types são heterogêneos. Put-away por categoria (feature ativa, 0 regras hoje) faz a separação no momento do depósito, qualquer que seja o fluxo de entrada.
3. **D-PARENT — `31092`/`31093` fora do lot_stock.** São irmãs de 42; com `lot_stock_id=42`, mover o saldo p/ elas quebra on-hand/MRP e a reserva das saídas `src=42`. **`lot_stock_id` exige `usage=internal`** (`s79`) ⇒ apontar p/ `41` (view) é **inviável**. **Solução: reparentar 31092/31093 sob 42** (D2 decidido) — `lot_stock` segue 42 (internal), passa a vê-las, sem trazer 53/54 (produção) ao on-hand.

---

## 3. Plano wired — estado-alvo

### 3.1 Passos decididos (reparent + put-away + migração + repoint L1)
| # | Mudança | Objeto Odoo | Efeito |
|---|---|---|---|
| A1 | **Reparent** `31092.location_id = 42` e `31093.location_id = 42` | `stock.location` | viram filhas de 42 → entram no lot_stock; saídas `src=42` reservam delas; on-hand intacto. (Muda `complete_name` p/ `LF/Estoque/...` — cosmético.) |
| A2 | **Put-away** categoria **`6` PRODUTO ACABADO** → **31093** | `stock.putaway.rule` (location_in=42) | todo PA (cat 6 + descendentes OLEOS/MOLHOS/CONSERVAS/…) depositado em 42 vai p/ 31093 |
| A3 | **Put-away** categoria **`1` TODOS** (raiz, fallback) → **31092** | `stock.putaway.rule` (location_in=42) | MP/EMB/PALLET/etc vão p/ 31092 |
| A4 | **Migrar saldo** atual 42→31092/31093 por categoria (§4), **exceto açúcar reservado** | picking interno pt23 | move neutro (0 SVL); separa o legado |
| A5 | **Repoint contábil L1** (terceiros) + reclassificação do saldo | `product.category` (contexto LF) + lançamento | valoração LF passa a conta de terceiros `1150200001` (§3.4) |

Com A1–A4, os fluxos passam a terminar/originar nas locations corretas **sem editar rules**:
- **Entradas** (pt19 compra, pt35 armazenar PA, pt64 industrialização, ajustes) → dst=42 → **put-away redireciona** p/ 31092/31093 por categoria.
- **Abastecimento produção** (pt34/rules 132/36/35: src=42→53/39) → reserva de **31092** (filha).
- **Saídas** (pt20/66/94/97, rules 17/20: src=42→Clientes) → reservam da filha correta (PA de 31093, material de 31092).
- **Retorno industrialização** (pt98: 31093→26489) → **já correto**.
- **Automação G1** → passa a ver entradas/saldo reais em 31092 (hoje só o piloto forçava).

### 3.2 Alternativa descartada (registrada por completude)
Editar src/dst nas 15 rules manualmente **+ mudar `lot_stock_id`**: descartada — (a) os picking_types são heterogêneos (não separam PA/MP); (b) **`lot_stock_id` exige `internal`** (`s79`), logo "lot_stock→41 (view)" é **inviável**. O reparent (A1) resolve a ancoragem sem mexer no warehouse.

### 3.3 O que NÃO muda
Rules de produção interna (131/136/138), pt98 (retorno já em 31093), pt23 (veículo da migração), rotas inativas (Fabrico) e subcontratação dormente (pt48/63 OFF) — **sem ação**.

**Consumidores de código (read) do `42` — varredura `app/` (2026-06-16):** além da automação G1 (§4 Nota crítica / §7.1-D4), só há referências de **baixo/nenhum risco**: (a) `consulta_quant.py:164` `only_principal=True` filtra `location_id in [42]` **exato** → pós-reparent **perderia** as filhas 31092/31093 — mas tem **zero callers** em `app/` (parâmetro dormante, default `False`); gotcha **latente**: se um dia for usado p/ LF, trocar p/ `child_of 42`. (b) `constants/locations.py` `COMPANY_LOCATIONS[5]=42` (e cópias em `transfer.py`/`inventario_pipeline.py`) segue **válido** — 42 continua a raiz/`lot_stock`; transferências `src=42` reservam das filhas por `child_of`. ⚠️ pós-reparent, **evitar criar quant direto em 42** (inventário) — deixar a put-away (A2/A3) rotear. Nenhum desses bloqueia A1–A5.

### 3.4 Camada contábil L1 (A5) — terceiros (D1) — PONTO MAIS DELICADO
Decisão Rafael (D1): o estoque LF deve valorar como **terceiros** (`1150200001`). **A investigação ao vivo (`s80`/`s81`) mostrou que o L1 já está PARCIALMENTE aplicado** — a doc (ACHADOS "1150200001=R$0") está **desatualizada**:
- **Estado real (`s80`/`s81`):** o `ir.property` da company 5 já aponta **14 categorias** para `1150200001` (terceiros) — as do **piloto shoyu** (FRASCO/TAMPA/CAIXA/ETIQ/FILME/FITA/ROTULO · AROMAS/AÇUCARES/CORANTE/SAIS/SHOYU · PA PET 1,01 · SEMI BATELADAS). As demais (~159 categorias) seguem em conta **própria**. Saldos vivos: `1150200001`=**-69k** (566 lançs), `1150200002`=**-11,96M** (1743), `1150100001`=-21,3M, `1150100002`=-5,3M.
- **Cruzamento com o saldo a migrar (`s81`):** dos **443 quants em 42, 318 já estão em categoria-terceiros**; **só 125 em próprio**. ⇒ **D1 já está ~72% feito**; A5 = **completar** o repoint das categorias próprias que contêm material LF + reclassificar **esses 125** — NÃO refazer do zero.
- **Mecânica (ancorar no L1 da Etapa 2, `SOT §"Etapa 2" Design A`):** (1) repoint `ir.property` (company 5) das categorias próprias restantes → `1150200001`; (2) **reclassificação** do saldo desses 125 `D 1150200001 / C 1150100001/002/007`. **Medir pelo CICLO.**
- ⚠️ **Decisão de Contador (registrada em `ACHADOS §"ACHADO 2026-05-30"`):** "migrar tudo p/ `1150200001`" **vs** "fechar o ciclo `51010xx` existente". Como o L1 já anda em terceiros (14 cat), a direção está dada, mas **os valores da reclassificação (milhões) exigem validação do Contador** antes do go. A S3 deve detalhar/medir A5 **separadamente**, com go próprio. ⚠️ Repoint de categoria afeta **toda** a categoria na LF (não só industrialização) — consistente pois a LF é 100% industrializadora.

---

## 4. Migração do saldo (mecanismo)

**Universo:** 443 quants em 42 (442 livres + 1 reservado=açúcar). **Veículo recomendado:** 1 (ou 2) **picking interno** `pt23 Transferências Internas (LF)` agrupando todos os move.lines, classificando o destino por categoria do produto:
- categoria descendente de `6 PRODUTO ACABADO` → **31093**
- demais → **31092**

**✅ Validado em dry-run pelo builder `s82` (`--plano`, READ):** dos 442 livres → **431 quants p/ 31092** (5.655.181,0 un) + **11 quants p/ 31093** (978,7 un); o reservado (açúcar lote `230326`, 3.157,6 un) fica de fora (D3). **Invariante OK:** `Σ destinos (5.656.159,653) == Σ a migrar`; `total 5.659.317,3 = migrar + açúcar`. Plano linha-a-linha em `/tmp/s2_s82_migracao_plan.json`. Os 5 quants de açúcar **livres** (lotes ≠ 230326) migram normal p/ 31092.

**Por que picking interno (vs skill `transferindo-interno-odoo`):** rastreável (1-2 docs), reversível por estorno, preserva lote, **0 SVL (neutro)**. ⚠️ **Descoberta (verificação do átomo):** a skill `transferindo-interno-odoo` usa `StockInternalTransferService.transferir_entre_locations`, que faz **inventory adjustment 2× (ajusta quant)** — isso **GERA SVL** (saída+entrada, net-zero se mesma conta), **violando a promessa "0 SVL"**. ⇒ **NÃO usar o átomo para a migração**; usar `stock.move`/picking de verdade.
**Veículo correto (reuso testado):** `app/odoo/estoque/scripts/picking.py` `PickingService`: `criar_transferencia(5,5,42,dst,linhas,pt=23, incoterm=None, carrier=None, partner=None, origin=...)` → `confirmar_e_reservar` → **`consolidar_move_lines(pid, linhas_esperadas=[{product_id,lot_name,quantity}])`** (G023 — trata **multi-lote por produto**; `preencher_qty_done` faz match só por produto, **não serve** p/ produtos com vários lotes) → `validar(pid, linhas_esperadas)` (button_validate com guards G019/G023). **2 pickings:** 42→31092 (431 linhas) e 42→31093 (11 linhas). 🔶 **Primeiro go = CANARY** (1-3 produtos, incluindo 1 multi-lote) p/ validar o fluxo antes dos 442. **Excluir** o açúcar reservado (lote 230326 / picking 321794) até a saída FB ser resolvida (§5).

> **⚠️ Nota crítica (automação G1/G2 — verificado na fonte 2026-06-16):** a descoberta da NF-2 (`descoberta_industrializacao.py` + `SA_BODY_G1` em `sa_retorno_industrializacao.py`) usa `31092` **EXATO** em **dois** filtros:
> - **F1 — genealogia:** `move_raw.location_id == 31092` (`descoberta:157` / `SA_BODY_G1:126`) decide se o componente consumido é "de terceiros". Falhar = componente **descartado da NF-2** (não é só preço — some da nota).
> - **F2 — entrada:** `location_dest_id == 31092` (`descoberta:81` / `SA_BODY_G1:132`) acha o SVL (preço, `descoberta:90`) e **vota a remessa** (chave R3, `descoberta:116` / `SA_BODY_G1:148`).
>
> Duas consequências da reestruturação:
> 1. **Janela de transição:** lote remetido/produzido **antes** da migração (move com `location_id`/`location_dest_id` = **42**) e **retornado depois** → F1 descarta o componente e F2 perde SVL + remessa → NF-2 incompleta / sem R3 (fiscalmente errada). A data-de-corte da G1 é a do **retorno**, não a da remessa — logo **não protege**.
> 2. **Poluição do voto:** o picking de migração A4 (42→31092, `done`, **0 SVL**) casa o domain de F2 e **conta voto** de remessa (o voto não exige SVL) → pode vencer a votação e apontar remessa errada.
>
> ⇒ **Pré-condição de S4** (habilitar o cron G1), **não** bloqueia A4 — o cron G1 ainda está em **canary/OFF** (`SA_BODY_G1` marca "🔴 CANARY REQUIRED ... ANTES de habilitar o cron G1"). **Endurecer a descoberta antes de ligar o cron** → **§7.1-D4**.

---

## 5. Exceções e pré-condições

| Item | Estado (ao vivo) | Tratamento |
|---|---|---|
| **Açúcar reservado** | picking `321794 SAI/RNA/00103`, 999 un lote 230326, 42→Clientes | resolver a saída FB **antes** OU excluir esse quant da migração e migrar depois |
| Açúcar livre (5 quants) | sem reserva | migram normal p/ 31092 (são terceiros) |
| Lotes `P-15/05` (82) e `MIGRAÇÃO` (5) | quants válidos livres | migram normal (preservar lote) |
| "4 produtos sem PO" (MACRO) | não bloqueia migração física | confirmar na S3 ao classificar (sem efeito no roteamento) |
| MO 20797 (ketchup) | abastecida de 53, 0 raws em 42 | sem ação |
| Subcontratação | pt48/63 OFF, 0 moves reais | sem ação |
| **Reservas** | só 1 (açúcar) | re-checar imediatamente antes da migração |
| **Janela de transição (automação G1)** | descoberta G1 usa `31092` exato (F1/F2); lotes pré-migração entram/consomem em 42 | **pré-condição de S4, não de A4** (cron G1 em canary/OFF): endurecer F1/F2 + excluir picking de migração do voto **antes de ligar o cron G1** → §7.1-D4 |

**Pré-condições da S3:** (1) reservas LF/Estoque limpas (feito na S1, exceto açúcar); (2) janela sem produção iniciando que reserve 42; (3) decisões §7 resolvidas; (4) go fresco do Rafael por escrita.
**Pré-condição da S4 (registrada aqui pois A4 a origina):** descoberta G1 endurecida (§7.1-D4) **antes** de habilitar o cron G1 — enquanto G1 ficar em canary/OFF, A1–A5 são seguros.

---

## 6. Ordem de execução da S3 + validações + reversibilidade

**Builder + validador prontos:** `s82_exec_reestruturacao.py` (A1–A4 dry-run-first, escrita só com `--confirmar`; A4 reusa `StockPickingService`) + `s83_validador_reestruturacao.py` (gates). `--plano` validado em dry; baseline pré-go já capturado (`s83 --baseline` → `/tmp/s2_baseline.json`).

**Comandos do go (1 por passo, cada um após dry + go fresco):**
```
# (baseline já capturado: s83 --baseline)
s82 --reparent --confirmar                 # A1
s82 --migrar --canary-n 3 --confirmar      # A4 canary (validar fluxo)
s82 --migrar --confirmar                   # A4 restante
s82 --putaway --confirmar                  # A2/A3
s83 --validar                              # gates pós-go
# A5 (repoint L1): só após validação do Contador (CSV /tmp/s2_mapa_a5_...csv)
```

**Sequência (cada passo = dry-run → medir → go fresco do Rafael → executar → validar):** *ordem importa* — **A1 antes de A4** (senão o saldo migrado fica fora do `lot_stock` até o reparent); **A4 antes de A2/A3** (migração usa `dst` explícito 31092/31093, então não é redirecionada pela put-away; ativar put-away depois evita qualquer interação e só vale p/ fluxos futuros).
1. **A1 reparent** 31092/31093 sob 42 (`s82 --reparent`) → validar: `child_of(42)` inclui ambas; on-hand do WH inalterado.
2. **A4 migração** dos 442 livres (`s82 --migrar`, picking pt23, `dst` explícito por categoria, **excluindo açúcar lote 230326**) → validar: 31092 recebe 431 (5.655.181 un) / 31093 recebe 11 (978,7 un), 42 zera (exceto açúcar), lotes preservados, **0 SVL**, saldo por produto inalterado.
3. **A2/A3 put-away** (`s82 --putaway`: cat 6 PA→31093; cat 1 TODOS→31092) → validar com 1 recebimento-teste de cada categoria (dry) que o destino redireciona.
4. **Smoke dos fluxos** (sem postar): abastecimento (reserva de 31092), entrega (reserva de 31093), entrada industrialização (put-away→31092), armazenar PA (put-away→31093).
5. **Validação de neutralidade física:** nenhuma conta de estoque mudou pela migração A4 (move interno = 0 SVL).
6. **A5 repoint contábil L1 (terceiros)** — passo SEPARADO, go próprio: completar repoint das 37 categorias próprias (`/tmp/s2_mapa_a5_categorias_repoint.csv`) + lançamento de reclassificação dos 125 quants → `1150200001`. **Valores = validação Contador.** **Medir pelo CICLO.** (§3.4)
7. **Açúcar (D3):** após a saída FB do picking 321794 ser resolvida, migrar o quant remanescente.
8. Atualizar `MACRO` (status S3) + banner do `PROMPT_PROXIMA_SESSAO`.

**Reversibilidade:** A1 (reparent) e A4 (picking interno) reversíveis por write/estorno; A2/A3 (put-away) por unlink; A5 (lançamento) por estorno. Nada toca SEFAZ.

**Dependência p/ S4 (não p/ S3):** habilitar o **cron G1** exige antes endurecer a descoberta (§7.1-D4) — A4 cria a janela de transição **e** o picking que polui o voto de remessa. Enquanto G1 ficar em **canary/OFF**, A1–A5 são seguros; o canary G1 (READ + oráculo `saida_retorno_industrializacao validar`) detectaria qualquer NF-2 errada **antes** de postar. Sequenciar: A1–A4 → (S4) endurecer F1/F2 + excluir migração do voto → canary G1 → habilitar cron.

**Validações automatizáveis (gates da S3):** saldo por (produto,lote) idêntico pré/pós; `Σ quants 31092+31093 == Σ quants 42 antigo (−açúcar)`; `Δ` contas de estoque pela migração A4 = 0; reserva da MO 20797 intacta; pós-A5, lançamento de reclassificação fecha pelo ciclo.

---

## 7. Decisões do GATE (Rafael, 2026-06-15)

| # | Decisão | Implicação no plano |
|---|---|---|
| **D1** | **Terceiros TAMBÉM contábil** (repoint categoria L1) | + passo **A5** (§3.4). **Já ~72% feito** (`s81`: 318/443 quants terceiros; 14 categorias). A5 = **completar** repoint das categorias próprias restantes (125 quants) + reclassificar `1150100001/002/007→1150200001`. **Valores (milhões) = decisão de Contador** antes do go. Alcance: toda categoria na LF. |
| **D2** | **Reparent 31092/31093 sob 42** | passo **A1**. (A opção "lot_stock→41" foi **refutada** — `lot_stock_id` exige `internal`, 41 é `view`, `s79`.) lot_stock segue 42; on-hand passa a ver 31092/31093 sem trazer 53/54. |
| **D3** | **Migrar livres agora; açúcar depois** | A4 exclui o quant do açúcar reservado (picking 321794); passo **7** migra após a saída FB ser resolvida. |

**Status S2:** desenho concluído + decisões D1–D3 tomadas ⇒ **DoD da S2 cumprida**. A investigação ampla da S2 (escopo "contábil + exceções") **descobriu** uma pré-condição de S4 (D4, abaixo) que **não** altera o plano físico A1–A5. Próximo = **S3 (implementação Odoo)** — não iniciar sem o "go por escrita" do Rafael (cada passo dry-run-first).

### 7.1 Decisão ABERTA (descoberta 2026-06-16, verificada na fonte)

| # | Decisão (pendente Rafael) | Implicação no plano |
|---|---|---|
| **D4** | **Endurecer a descoberta G1 antes de ligar o cron (S4)** | **Pré-condição de S4** — A4 abre a janela de transição + o picking que polui o voto (ver §4 Nota crítica + §5). **Não** bloqueia A1–A5 (cron G1 em canary/OFF). Correção recomendada (aplicar em `descoberta_industrializacao.py` **e** `SA_BODY_G1`): **F1** `move_raw.location_id` `child_of 42` (em vez de `== 31092`) — pós-reparent, todo estoque LF sob 42 é terceiros; **F2** `location_dest_id` `child_of 42` **E** restringir `entrada` aos moves **com SVL `unit_cost`** (exclui o move de migração 0-SVL do **preço e do voto**). Remessas legítimas (ENTIN/compra) sempre têm SVL. Re-deploy da server action exige **canary READ + oráculo** (`saida_retorno_industrializacao validar`) antes do cron. **Decisão/validação Rafael + Contador (preço).** |

---

## Contexto

Documento — industrialização por encomenda FB↔LF. Entregável da **Sessão 2** (desenho detalhado), companheiro do `MACRO_REESTRUTURACAO_DE_TERCEIROS_LF.md` (S1). Investigação ao vivo (READ-only) nos scripts `s72`–`s81`. Norte: `SOT_OPERACOES.md §"OBJETIVO FINAL"` (critério #4 estoque correto + #5 contabilização pelo ciclo). **Achado D4 (§7.1) verificado na fonte 2026-06-16** (`descoberta_industrializacao.py` 81/157 + `SA_BODY_G1` 126/132). Próximo: aprovação Rafael (GATE) → **S3 implementação Odoo**. Relacionado: `app/odoo/estoque/fluxos/1.1.4` (automação G1/G2), `app/odoo/estoque/scripts/descoberta_industrializacao.py` + `app/odoo/estoque/provisioning/sa_retorno_industrializacao.py` (leem `31092`).

Documento — industrialização por encomenda FB↔LF. Entregável da **Sessão 2** (desenho detalhado), companheiro do `MACRO_REESTRUTURACAO_DE_TERCEIROS_LF.md` (S1). Investigação ao vivo (READ-only) nos scripts `s72`–`s78`. Norte: `SOT_OPERACOES.md §"OBJETIVO FINAL"` (critério #4 estoque correto + #5 contabilização pelo ciclo). Próximo: aprovação Rafael (GATE) → **S3 implementação Odoo**. Relacionado: `app/odoo/estoque/fluxos/1.1.4` (automação G1/G2), `app/odoo/estoque/provisioning/sa_retorno_industrializacao.py` (lê `31092`).

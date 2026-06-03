<!-- doc:meta
tipo: how-to
camada: L2
sot_de: —
hub: docs/industrializacao-fb-lf/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# RUNBOOK — Piloto E2E 4870112 (Industrialização FB↔LF)

## Indice

- [0. Visão da sequência (5 etapas) e onde os levers entram](#0-visão-da-sequência-5-etapas-e-onde-os-levers-entram)
- [0.5 — PLANO DO TESTE CONTROLADO (1 caixa, lote dedicado) — A0→K](#05-plano-do-teste-controlado-1-caixa-lote-dedicado-a0k)
- [0.6 — CHECKPOINT 2026-06-01 (Etapa 1 EXECUTADA em PROD) + GOTCHAS de criação de remessa](#06-checkpoint-2026-06-01-etapa-1-executada-em-prod-gotchas-de-criação-de-remessa)
- [0.7 — CHECKPOINT 2026-06-01 (Passo C / Entrada LF INICIADO — Model A) + GOTCHAS de entrada](#07-checkpoint-2026-06-01-passo-c-entrada-lf-iniciado-model-a-gotchas-de-entrada)
  - [Execução 2026-06-01 (após "go" do Rafael) — estado e BLOQUEIO do picking](#execução-2026-06-01-após-go-do-rafael-estado-e-bloqueio-do-picking)
  - [Continuação — A' (picking manual vinculado à PO) + BLOQUEIO lote inter-company (G-ENT-6)](#continuação-a-picking-manual-vinculado-à-po-bloqueio-lote-inter-company-g-ent-6)
  - [EXECUÇÃO B1 (Model B) — entrada LF CONCLUÍDA (faltando só post) ✅](#execução-b1-model-b-entrada-lf-concluída-faltando-só-post)
  - [Tarefa 2 (MO Etapa E) — ✅ CORRIGIDA E VALIDADA (2026-06-01, fix G-ENT-10)](#tarefa-2-mo-etapa-e-corrigida-e-validada-2026-06-01-fix-g-ent-10)
  - [GOTCHA do dreno físico FB (G-DRENO-1, 2026-06-01)](#gotcha-do-dreno-físico-fb-g-dreno-1-2026-06-01)
  - [GOTCHAS B1 novos (G-ENT-7..10)](#gotchas-b1-novos-g-ent-710)
- [1. RECEITA — 16 componentes remetidos (1 caixa) ✅ validado ao vivo](#1-receita-16-componentes-remetidos-1-caixa-validado-ao-vivo)
- [2. Lotes + disponibilidade em FB/Estoque(8) — ✅ validado · 🔴 1 bloqueador](#2-lotes-disponibilidade-em-fbestoque8-validado-1-bloqueador)
- [3. Picking type de criação + locations ✅](#3-picking-type-de-criação-locations)
- [4. Operação / CFOP 5901 por-linha ✅ resolvido ao vivo](#4-operação-cfop-5901-por-linha-resolvido-ao-vivo)
- [5. Checklist pré-condições `action_liberar_faturamento` (ACHADOS §4, campos v17)](#5-checklist-pré-condições-action_liberar_faturamento-achados-4-campos-v17)
- [6. Reaproveitar vs criar NOVA remessa — ✅ decisão: **NOVA**](#6-reaproveitar-vs-criar-nova-remessa-decisão-nova)
- [7. Números do piloto ✅](#7-números-do-piloto)
- [8. Sequência de execução (Etapa 1) — com gates](#8-sequência-de-execução-etapa-1-com-gates)
- [9. Métrica de sucesso da Etapa 1 (G0) — **medir por LOTE/cadeia do piloto** (GOALS §B)](#9-métrica-de-sucesso-da-etapa-1-g0-medir-por-lotecadeia-do-piloto-goals-b)
- [10. Etapa 5 (G5b) — aplicação da op 3252 ✅ script validado](#10-etapa-5-g5b-aplicação-da-op-3252-script-validado)
- [11. Pendências](#11-pendências)

> **Batch do piloto = 1 CAIXA de 4870112** (MOLHO SHOYU PET 12×1,01 L = 12 frascos). Unidade mínima.
> **Papel deste doc:** procedimento de execução do piloto + **gotchas** (G-ENT/G-REM/G-DRENO) + drivers. Desenho-alvo e decisões = `SOT_OPERACOES.md §2`; índice = `README.md`.
> **Gates invioláveis:** toda escrita Odoo com dry-run + aprovação do Rafael; **NF SEFAZ (Etapas 1 e 4) = IRREVERSÍVEL → só com "go" explícito**.
> **Validado ao vivo 2026-05-30** (Odoo PROD v17): op 3252 ✓ · L1 ✓ · receita/Ic ✓ · preview e g5b rodando. Sondas: `/tmp/ind_fb_lf_validar_estado.py`, `scripts/e2e_remessa_etapa1_dryrun.py`, `scripts/g5b_aplicar_op3252_na_linha.py`.
> **Gotcha Odoo 17:** linhas de produto da fatura têm `display_type='product'` (não `False`); CFOP usa `codigo_cfop`; incoterm em `stock.picking` é o campo **`incoterm`** (não `incoterm_id`).

---

## 0. Visão da sequência (5 etapas) e onde os levers entram

| Etapa | O quê | pt | NF/CFOP | Lever | Métrica (Δ ciclo, por LOTE do piloto) |
|---|---|---|---|---|---|
| **1. Remessa FB→LF** | 16 insumos saem FB→Em Trânsito | **53** (8→26489) | NF **5901** CST51 | — (já correto) | `D 5101010001 +I / C 1150100002 −I`; 1150100012=0 |
| 2. LF recebe | DFe 1901; entra em Materiais de Terceiros | **64** (26489→**31092**)¹ | 1901 | **L1** (val→1150200001) | SVL `D 1150200001 / C 1150100011`; **Δ1150100011(LF)=0** |
| 3. MO LF | BoM 3695→3646; PA em PA-Terceiros | interno | — | — | net-zero terceiros; PA em 31093 |
| 4. LF retorno | NF mista | **98** (31093→26489) | **5902+5903+5124** CST51, s/ICMS | L4 | **Δ5101020001(LF)=0**; 0 em "SAÍDA-PERDAS" |
| 5. FB recebe | DFe; **op 3252 na linha 1902** | **52** (26489→8) | 1902+1903+1124 | **G5b** (op 3252) | **G5b: 0 SVL de componentes** (estoque FB não infla) |

¹ pt64 hoje aponta `dst=42` (LF/Estoque), **não** 31092 → exige override na Etapa 2 (lever L2).
**⚠️ Distinção G5b × G5a (não confundir):** o **piloto valida só G5b** (op 3252 → componentes não re-entram no estoque). **`Δ5101010001(FB)=0` é G5a** (creditar a ATIVA no retorno). **DESENHO ANTIGO REVOGADO (v2.3/v2.4):** G5a **NÃO** depende de journal novo — é **AJUSTAR o j1001** existente setando `account_no_payment_id=22800` (5101010001), comprovado pelo grounding sessão 5 (entrada → C 5101010001). G5a **não** é alcançável pela op 3252 sozinha (op 3252 = G5b, só mata o double-count) — precisa do no_payment no j1001 **+** medir resíduo R1 (conta que a op 3252 debita). Detalhe: `ACHADOS §"ACHADO 2026-06-01 (sessão 5)"`.

---

## 0.5 — PLANO DO TESTE CONTROLADO (1 caixa, lote dedicado) — A0→K

> Estratégia: **clean-slate** (zerar componentes na FB + adicionar quantidade controlada num **lote dedicado**, ex. `PILOTO-3105`) → rodar o ciclo **validando após cada etapa** para *recortar a etapa duvidosa*. Toda medição é **por lote/cadeia do piloto** (não saldo absoluto). 🔴 = gate SEFAZ irreversível · ⚠️ = etapa duvidosa (onde L1/G5b são testados).

| Passo | Ação | Ferramenta | Critério |
|---|---|---|---|
| **A0** ✅ | Snapshot baseline (contábil + físico por lote) | `e2e_piloto_validar.py --modo baseline --lote PILOTO-3105 --out base.json` | **FEITO** — `/tmp/piloto_base.json` (⚠️ efêmero) |
| **A** ✅ | 16 quants criados no lote `PILOTO-3105` @ FB/Estoque(8) | `ajustar_quant.py --cod C --empresa FB --local 8 --lote PILOTO-3105 --delta X --criar-se-faltar --confirmar` (16×) | **FEITO** — qty exata de 1 caixa, Ic R$279,24 |
| **B** ✅🔴 | Remessa FB→LF (pt53, NF 5901) — **lote pinado** | `e2e_remessa_criar.py --lote PILOTO-3105` → `--execute` → `--liberar` + Playwright SEFAZ | **FEITO** — picking 01612(322399) done; **NF RPI/2026/00245(735679) AUTORIZADA** chave `…0946041007356795`; NET `D 5101010001 +279,23 / C estoque`; 1150100012 resíduo R$0,05 |
| **C** ⚠️ ⬅️ **PRÓXIMO** | Entrada LF — **pré-flight pt64/pt19 dst** | `--modo preflight-lf` antes; *receb LF*; dst=**31092** | material em **31092** (não 42) |
| **D** | Valida B+C (Δ computado) | `e2e_piloto_validar.py --modo remessa` / `--modo entrada-lf --base base.json` | `Δ1150100011(LF)=0`; 26489 do lote=0 |
| **E** ✅ | 2 MOs (BATELADA + PA), origem 31092 → PA em 31093 | `e2e_mo_lf_criar.py --modo batelada/pa --execute` (fix G-ENT-10) | **FEITO** — 20252+20254; net-zero terceiros; PA em 31093 |
| **F** ✅ | Valida E | `e2e_piloto_validar.py --modo mo --mo 20252 --mo2 20254 --lote PILOTO-3105 --base base.json` | **PASS** — consumo 31092, PA 31093, loc 42 inalt. |
| **G** 🔴 | Retorno LF→FB (pt98, NF mista 5902+5124) | *retorno fiscal* | debita 5101020001; PA price=Ic+S |
| **H** | Entrada FB (pt52) + **op 3252 na 1902 em DRAFT** | `g5b_aplicar_op3252_na_linha.py --move-id <draft>` | 1902 com op 3252 |
| **I** ⚠️ | Valida entrada FB | `e2e_piloto_validar.py --modo entrada-fb --nf <id>` | **G5b**: 0 SVL comps. **G5a**: C 5101010001 (com no_payment=22800 no j1001) — medir R1 (conta debitada pela op 3252) |
| **J** | Ajuste/conferência do PA produzido (AVCO=Ic+S; cleanup) | *manual + validar* | AVCO PA = Ic+S |
| **K** 🔴 | Rollout p/ todos LF | **GATE CONTADOR** (G5a + 3 pernas + regularização) | — |

---

## 0.6 — CHECKPOINT 2026-06-01 (Etapa 1 EXECUTADA em PROD) + GOTCHAS de criação de remessa

**Feito nesta sessão (A0→B):** A0 baseline · A 16 quants no lote `PILOTO-3105` · B remessa **autorizada no SEFAZ** (picking `FB/SAI/IND/01612` id 322399; NF `RPI/2026/00245` id 735679; chave `35260661724241000178550010000946041007356795`). G0 atingido (resíduo R$0,05 imaterial). Rastro: 3 pickings cancelados 01609/10/11 (iterações de fix).

**Caminho correto de criação+transmissão (provado E2E):**
1. `e2e_remessa_criar.py --lote PILOTO-3105 --execute` → cria+valida picking pt53 (reversível).
2. `e2e_remessa_criar.py --picking <id> --liberar` → `action_liberar_faturamento` → robô CIEL IT cria a NF em ~90s (situacao_nf=`rascunho`).
3. `transmitir_nfe_via_playwright(invoice_id, odoo, logger)` (`app/recebimento/services/playwright_nfe_transmissao.py`) → SEFAZ autoriza (força recompute l10n_br via UI → evita SEFAZ 225). IRREVERSÍVEL.

**GOTCHAS de criação de remessa via XML-RPC (codificados no `e2e_remessa_criar.py`):**
- **G-REM-1 (partner_id):** o picking pt53 **DEVE** ter `partner_id=35` (LF). Sem ele, `button_validate` falha ao auto-criar o picking-companheiro "Transferir TERCEIROS" (server action 1899) → `Field Destination Location (location_dest_id) not set`.
- **G-REM-2 (UoM rounding):** a qty do move.line deve respeitar o `uom.rounding` do produto (Litros/Latas/m=1e-06, kg=1e-08). Explodir BoM em precisão total (9 casas) → `button_validate` rejeita ("não respeita a precisão de arredondamento").
- **G-REM-3 (cap no saldo):** nunca remeter > saldo do quant (mismatch quant 6dp × explosão 8dp gera estoque negativo). Fix: `q_remit = min(explosão, free)`.
- **G-REM-4 (lote pinado):** criar a move.line manualmente com `lot_id` fixo (sem `action_assign`/FIFO) + gravar `quantity` E `qty_done` juntos + `button_validate` com `skip_backorder` (sem `stock.immediate.transfer`, removido no v17).

---

## 0.7 — CHECKPOINT 2026-06-01 (Passo C / Entrada LF INICIADO — Model A) + GOTCHAS de entrada

**Modelo confirmado (Rafael):** **Model A** — a entrada DRENA o trânsito `26489 → 31092` (terceiros LF). O companheiro nativo "Transferir TERCEIROS" (`26489 → 30720`) é **cancelado** antes. Driver: `scripts/e2e_entrada_lf_criar.py` (caminho A / FLUXO L3 1.2.1, compõe átomos Skill 7 + Skill 5 + override L2). Constants: `tipo_dfe=tipo_po='serv-industrializacao'` (escriturar_dfe **rejeita** 'compra'; canary 42868 usou serv-industr), pt64, team143, pterm2791, provider38, fp derivada (131).

**Estado em PROD (parcial — entrada NÃO concluída):**
- ✅ **Gate 1**: companheiro `322400` (FB/INT/08121, era `assigned`) **cancelado** (contexto FB company=1). 26489 mantém 42,29 un do lote PILOTO-3105.
- ⚠️ **Gate 2**: `escriturar_dfe`(43776, serv-industr) OK → `gerar_po_from_dfe` criou **PO `42741` (C2619828) VAZIA** (0 order_line, 0 picking, 0 invoice) → preencher/confirmar `state=purchase`. **Causa: DFe 43776 é resumo SEFAZ** (`l10n_br_status=06`, `situacao_manifesto=nenhum`, `l10n_br_xml_dfe` VAZIO, **0 dfe.line**) — `action_gerar_po_dfe` sem linhas para mapear.
- 🔧 **Recuperação pronta (NÃO executada — aguardava aprovação)**: `--modo completar-dfe` → cancela PO 42741 vazia + limpa `dfe.purchase_fiscal_id` + escreve `l10n_br_xml_dfe`=XML autorizado da NF 735679 (24KB, 16 linhas) + `action_processar_arquivo_manual` + `alinhar_dfe_lines_company`(43776,5) → depois `--modo escriturar` re-gera PO **com linhas**.

**GOTCHAS de entrada (novos, descobertos nesta sessão):**
- **G-ENT-1 (companheiro é FB):** o picking "Transferir TERCEIROS" (`picking_terceiro_id` da remessa) é **company FB=1**. Cancelar/ler exige contexto FB (`allowed_company_ids=[1]`), não LF — senão "sem acesso leitura a stock.picking".
- **G-ENT-2 (DFe resumo sem linhas):** o DFe que chega via SEFAZ para `INDUSTRIALIZACAO_FB_LF` pode ser **só resumo** (`l10n_br_status=06`, XML/linhas vazios). `action_gerar_po_dfe` então cria **PO vazia**. Fix = popular o DFe com o XML autorizado da nossa NF de saída (`l10n_br_xml_aut_nfe`) + `action_processar_arquivo_manual` (= caminho B aplicado ao DFe existente). A idempotência de `criar_dfe_a_partir_do_invoice_saida` (linha 1107) **devolve o DFe vazio** — por isso o fix preenche o existente em vez de chamar o átomo.
- **G-ENT-3 (escriturar_dfe rejeita 'compra'):** a whitelist do átomo `escriturar_dfe` (escrituracao.py:1306) **não** inclui `'compra'` (apesar do mapping `L10N_BR_TIPO_PEDIDO_POR_ACAO[dfe]='compra'`). Usar `'serv-industrializacao'` no DFe (canary-provado).
- **G-ENT-4 (company context na leitura da PO):** PO gerada é company LF=5; ler `picking_ids`/`order_line` exige contexto LF — em contexto FB vem vazio (falso "sem picking").

### Execução 2026-06-01 (após "go" do Rafael) — estado e BLOQUEIO do picking
- ✅ `cancelar-comp` (322400) · ✅ `completar-dfe` (DFe 43776 resumo → escrito XML autorizado da NF 735679 + `action_processar_arquivo_manual` → **16 dfe.lines** + `alinhar_dfe_lines_company` idempotente) · ✅ `escriturar` → PO **42743** (C2619830) company LF, tipo serv-industr, **16 linhas fiscais corretas**, state=purchase.
- 🔴 **BLOQUEIO (G-ENT-5):** o **picking de recebimento NÃO auto-gera** (`group_id=False`, 0 `move_ids`, `picking_ids=[]`) — diferente do canary PO 42122 (PEPINO) que gerou `group=60114`+picking 320393. **Causa provável:** os 16 produtos têm rotas com **conflito de regra `buy`**: route **5** "Comprar - FB" (rule 116 buy → pt1 FB company=1, dst=FB/Estoque 8) + route **133** "Comprar" LF (rule 130 buy → pt19 LF, dst=42) + route 167 "Pegar Embalagem" + 1 MTO. O canary (routes `[5,168,1]`, **sem 133/167**) não tinha o conflito. Possível co-fator: DFe manualmente completado (vs SEFAZ-sync) pode não disparar o auto-picking do CIEL IT.
- **NF ENTIN acoplada ao picking:** `criar_invoice_from_po` precisa `qty_received>0` → exige picking validado.
- **FORK pendente (decisão Rafael):** (A) criar picking manual `26489→31092` vinculado à PO 42743 + validar + invoice + post (tampão Skill 5 v15a, deprecado mas é o caso de uso dele) — isolado/reversível; OU (B) ajustar cadastro de rotas dos 16 produtos (remover conflito buy FB×LF) — limpo mas global/arriscado.
- PO/DFe canceladas no caminho (rastro): 42741 (vazia, DFe sem linhas), 42742 (pt64 não gerou picking).

### Continuação — A' (picking manual vinculado à PO) + BLOQUEIO lote inter-company (G-ENT-6)
- Decisão: como o picking não auto-gera, criar **picking manual `26489→31092` vinculado à PO** (moves com `purchase_line_id`→PO line) p/ atualizar `qty_received` (necessário p/ ENTIN). Driver: `--modo criar-picking --po <id>` (+ `validar-picking`, `compartilhar-lotes`).
- ✅ **Picking 322401 (LF/IN/01789) CRIADO**: 16 moves `26489→31092` `assigned`, lotes PILOTO-3105 pinados, `purchase_line_id` vinculado à PO 42743. pt19 (location override no create).
- 🔴 **BLOQUEIO (G-ENT-6 — lote inter-company):** `button_validate` falha com **"Empresas incompatíveis: produto LF vs lote PILOTO-3105 de outra empresa (FB)"**. Os 16 lotes PILOTO-3105 (ids 60496-60511) são **company FB=1** (criados na remessa em ctx FB). A LF (cmp 5) **não consome estoque sob lote FB**. ALÉM: `button_validate` em ctx `[5]`-só falha antes com "sem acesso leitura a stock.lot" → exige ctx `[1,5]`.
- **FIX TENTADO E BLOQUEADO PELO ODOO:** `--modo compartilhar-lotes` (write `company_id=False` nos 16 lotes) → `<Fault 2: 'Alterar a empresa deste registro é proibido neste ponto, você deve arquivá-lo e criar um novo.'>`. **Lote com estoque/movimento tem company IMUTÁVEL.** → **Model A (drenar trânsito FB-lote direto p/ LF) é INVIÁVEL** sem re-lotar.
- **Lição (G-ENT-6):** lotes de trânsito inter-company DEVEM nascer **compartilhados (`company_id=False`)** — corrigir `e2e_remessa_criar.py` p/ criar/usar lote shared na remessa (senão o retorno/entrada LF trava). Company de lote só muda antes de ter estoque.
- **FORK pós-Model-A-inviável (decisão Rafael):**
  - **(B1) Model B nativo** — cancelar picking 322401; LF recebe **fresco Vendors→31092** c/ **lotes LF novos** (mesmo nome, company LF) → valida limpo + SVL Design A + `qty_received` → ENTIN; re-fazer companheiro **26489→30720** (FB) p/ drenar trânsito. Padrão inter-company nativo, robusto. **RECOMENDADO.**
  - **(A-relot)** — via Skill 1: zerar quant FB-lote em 26489 + recriar sob lote compartilhado (net-zero) → picking 322401 passa a consumir. Preserva "26489→31092 direto", mas + escritas/risco.

### EXECUÇÃO B1 (Model B) — entrada LF CONCLUÍDA (faltando só post) ✅
Rafael escolheu **B1**. Driver `--modo criar-picking-b1` (cancela Model-A 322401 + cria 16 lotes LF + receipt **Vendors(4)→31092** vinculado à PO + valida):
- ✅ Picking **322451 (LF/IN/01790) DONE**: 16 moves Vendors→31092, lotes LF PILOTO-3105 (company 5). 16 quants em 31092. `qty_received` atualizou.
- ✅ **SVL Design A**: `D 1150200001 / C 1150100011 = 278,56` (16 SVLs, via L1).
- ✅ **ENTIN 737062** (`--modo nf`): `action_create_invoice` em ctx [1,5] (atomo usa ctx FB → "sem acesso account.account LF"). Precisou 2 fixes pré-invoice: **(a) B-V23-2** alinhar `PO.line.account_id` FB→LF (code 3202010001); **(b) limpar `taxes_id` FB** (empresas incompatíveis; IBS/CBS "a recuperar" = refinamento). Invoice saiu como **compra comum** (`D 3202010001 CMV / C 2120100001 Fornecedores`) porque a **operação fiscal não propagou** (op=False). **Fix `fix_entin.py`**: setar **operação 2686** + conta **1150100011** + cfop **1901** nas 16 linhas + payable→**5101020001** (espelha canary ENTIN 688686, journal 1047 ENTRADA-REMESSA, fp 131). Resultado draft: **`D 1150100011 / C 5101020001 = 278,56`** ✓.
- **NET = `D 1150200001 / C 5101020001`** → Δ1150100011 = 0 (transitória fecha) = **Design A completo**.
- ✅ **ENTIN 737062 POSTED** (go Rafael). **Validador oficial `--modo entrada-lf --picking 322451 --nf 737062`: Δ1150100011(LF)=0.0 PASS, dst=31092 PASS, material 31092 PASS, SVL Design A ✓, ENTIN D 1150100011/C 5101020001 ✓.** TAREFA 1 COMPLETA.
- ✅ **Tarefa 1 — dreno 26489 EXECUTADO (2026-06-01)**: picking pt5 manual `FB/INT/08128` (id 322875) done; 26489→0, 30720=42,28994948 (16 quants), **0 SVL** (físico puro). Driver `e2e_drenar_transito_26489.py --execute` (gotcha G-DRENO-1 corrigido — ver §0.7 abaixo). Validador `--modo entrada-lf` deixa de dar FAIL em "26489 zera".

### Tarefa 2 (MO Etapa E) — ✅ CORRIGIDA E VALIDADA (2026-06-01, fix G-ENT-10)
Script `scripts/e2e_mo_lf_criar.py` (BoM 3695 PA→3646 BATELADA semi; src=31092 dst=31093; ÁGUA 104000017 consu).

**G-ENT-10 (causa raiz CONFIRMADA + fix VALIDADO):** o `action_assign` cria `stock.move.line` com `quantity=reservado` mas **`picked=False`**. O `button_mark_done` cai no wizard `mrp.consumption.warning` (rounding demanda-BoM > estoque), cujo `action_confirm` re-dispara `button_mark_done(skip_consumption=True)` — que, com `picked=False`, interpreta "nada apontado" e **cancela os raws** (produção fantasma). Ground-truth: MO boa **LF/MO/03510 (20216)** consome com raws `picked=True`+`quantity>0`+lote. **Não há método de apontamento próprio do CIEL IT.**
- **FIX:** após `action_assign` + `qty_producing`, **setar `picked=True` nas `stock.move.line` (e no `stock.move`) dos raws ANTES do `button_mark_done`**. Codificado em `e2e_mo_lf_criar.py:79+` com **POS-CHECK anti-falso-sucesso** (aborta-alerta se algum raw ficar `state=cancel`).

**Limpeza dos fantasmas (Skill 1 `ajustando-quant-odoo`):** as 4 MOs 20235/36/38/39 ficam como **rastro `done`** (NÃO removíveis: `action_cancel` → `FALHA_STATE_NAO_CANCELAVEL`; `unbuild` re-adicionaria os 16 comps = inflaria; 2 do 1º try já tinham outputs zerados → bagunça). Zerado o estoque fantasma: semi `3800018`@31092 (quant 267291, −12,818→0) + PA `4870112`@31093 (quant 267293, −1,0→0), ambos `EXECUTADO`, SVL `value=0` **sem account.move** (confirmado igual ao 1º try — a baixa consome a camada de custo-zero do quant, não o AVCO).

**Redo correto (PROD):**
- BATELADA **20252** (LF/MO/03519): POS-CHECK **10/10 raws consumidos, 0 cancelados** → semi 3800018 (12,818) em 31092.
- PA **20254** (LF/MO/03521): POS-CHECK **8/8 raws consumidos, 0 cancelados** → PA 4870112 (1,0) em 31093.
- **Contábil (G3 net-zero terceiros ✓):** ambas `1150100004`(produção) bal=0 + `1150200001`(terceiros) bal=0; **NÃO tocou estoque próprio LF** (1150100001/002/007 ausentes → o double-count R$785k NÃO se repetiu). AVCO do PA na LF = **R$188,62** (custo LF dos comps; FRASCO na LF ~14,76/un vs 22,23 FB) — **transitório de terceiros**, NÃO é o valor final (PA na FB = Ic+S=R$314,24 via `price_unit` da NF de retorno, §7).
- **Validador** `e2e_piloto_validar.py --modo mo --mo 20252 --mo2 20254 --lote PILOTO-3105 --base /tmp/piloto_base.json`: consumo 31092 ✓, PA 31093 ✓, **loc 42 inalterado PASS**. (⚠️ exige `--lote PILOTO-3105`; sem ele compara todos os lotes de loc 42 → falso-FAIL.)
- Resíduo imaterial: poeira de rounding ~1e-5 un em 5 químicos (31092, `value≈0`, esperado G-REM-2).
- ✅ **Dreno trânsito 26489 EXECUTADO (2026-06-01):** picking pt5 `FB/INT/08128` (322875) done; 26489→0, 30720=42,29 (16 quants), 0 SVL. Ver G-DRENO-1 abaixo.

### GOTCHA do dreno físico FB (G-DRENO-1, 2026-06-01)
- **Sintoma:** `e2e_drenar_transito_26489.py --execute` criou o picking pt5 mas abortou no guard `[ABORT] 16 move.line com lote != PILOTO-3105` (deixando órfão 322852, `assigned`).
- **Causa raiz:** o pt5 ("FB: Transferências Internas") reserva `at confirm` → `action_confirm` dispara `action_assign` automático que cria 16 `stock.move.line` SEM-LOTE (`qty_done=0`). Somadas às 16 manuais pinadas do loop → 32 mls no picking (`move.quantity` dobrado). O guard varre todas e barra as 16 automáticas (defesa correta — não validou qty dobrada).
- **Fix (codificado no driver):** após `action_confirm`, chamar `stock.picking.do_unreserve` + unlink de move.lines residuais ANTES de criar as manuais pinadas; + idempotência `achar_orfaos()` que detecta/cancela pickings pt5 de dreno não-finalizados (origin `DRENO-PILOTO%`) antes de recriar. Re-execução: cancelou 322852 → criou 322875 limpo → done. **Impacto contábil sempre ZERO** (transit→customer não gera SVL).

### GOTCHAS B1 novos (G-ENT-7..10)
- **G-ENT-7 (account/taxes multi-company na fatura):** `action_create_invoice` de PO LF rejeita PO.line com account/taxes da FB. Pré-alinhar `account_id` (resolver code na company destino) + limpar/alinhar `taxes_id` ANTES.
- **G-ENT-8 (operação fiscal não propaga → compra comum):** sem `l10n_br_operacao_id` na linha, a fatura cai em CMV/Fornecedores. A entrada industrialização exige **op 2686** (cfop 1901) → conta 1150100011 + payable 5101020001 (journal 1047 no_payment). Setar op 2686 NÃO recomputa account via XML-RPC → setar account_id+cfop manual também.
- **G-ENT-9 (Model B = lotes LF próprios):** no Model B a LF recebe de Vendors com **lotes LF novos** (mesmo nome PILOTO-3105, company 5) — NÃO consome o 26489 FB-lote. 26489 drena separado pelo companheiro (lado FB).
- **G-ENT-10 (MO via XML-RPC produz sem consumir) ✅ RESOLVIDO:** `action_assign` deixa as `stock.move.line` dos raws com `picked=False`; o `button_mark_done`→wizard `mrp.consumption.warning.action_confirm`→`button_mark_done(skip_consumption=True)` interpreta `picked=False` como "nada apontado" e **cancela os raws**. **Fix: setar `picked=True` nas move.lines (e no move) dos raws ANTES do `mark_done`** + POS-CHECK. NÃO há método de apontamento próprio do CIEL IT (a MO boa só difere por `picked=True`). Validado em 20252/20254. Corolário: MO `state=done` NÃO é cancelável (`action_cancel` falha) nem deletável; `unbuild` reverte o físico mas re-adiciona a BoM (infla) e mantém a MO `done`.

---

## 1. RECEITA — 16 componentes remetidos (1 caixa) ✅ validado ao vivo

> Explosão BoM **3695** (PA, rende 1 caixa) + **3646** (BATELADA semi, ×12,818 un/caixa), dividindo pelo rendimento de cada BoM. Validado: `scripts/e2e_remessa_etapa1_dryrun.py` → **16 componentes**, `Ic` ao vivo.

| # | cód | componente | qty / caixa | std_price (FB) | valor | via |
|---|---|---|---:|---:|---:|---|
| 1 | 210030010 | FRASCO INCOLOR 1,01 L | 12,000000 | 22,2310 | **266,77** | BoM 3695 |
| 2 | 105000022 | MOLHO SHOYU TRADICIONAL (MP) | 2,464427 | 2,3481 | 5,79 | BATELADA |
| 3 | 210030322 | RÓTULO MOLHO SHOYU PET 1,01 L | 12,000000 | 0,0954 | 1,14 | BoM 3695 |
| 4 | 210030203 | CAIXA DE PAPELÃO 320X240X267 | 1,000000 | 1,1462 | 1,15 | BoM 3695 |
| 5 | 104000007 | CORANTE CARAMELO III | 0,192270 | 6,2914 | 1,21 | BATELADA |
| 6 | 210030110 | TAMPA PLÁSTICA VERMELHA PET 1,01 | 12,000000 | 0,0932 | 1,12 | BoM 3695 |
| 7 | 105000039 | AROMA SHOYU ST 2175 | 0,058450 | 9,5688 | 0,56 | BATELADA |
| 8 | 104000018 | SORBATO DE POTÁSSIO | 0,012818 | 26,8879 | 0,34 | BATELADA |
| 9 | 105000024 | AÇÚCAR CRISTAL | 0,128180 | 3,1231 | 0,40 | BATELADA |
| 10 | 105000023 | ANTIESPUMANTE AFE 1520 | 0,002564 | 64,5125 | 0,17 | BATELADA |
| 11 | 104000015 | SAL SEM IODO | 0,533998 | 0,2975 | 0,16 | BATELADA |
| 12 | 104000004 | BENZOATO DE SÓDIO | 0,012818 | 9,7107 | 0,12 | BATELADA |
| 13 | 208000008 | FILME STRECH PRE ESTIRADO | 0,011607 | 10,2199 | 0,12 | BoM 3695 |
| 14 | 104000002 | ÁCIDO CÍTRICO | 0,012818 | 8,0546 | 0,10 | BATELADA |
| 15 | 208000010 | FITA ADESIVA TRANSP. 48X1200 | 0,860000 | 0,0622 | 0,05 | BoM 3695 |
| 16 | 207210014 | ETIQUETA BRANCA 104X50 | 1,000000 | 0,0325 | 0,03 | BoM 3695 |
| | | **Ic (valor da remessa, AVCO FB)** | | | **R$ 279,24** | |

**NÃO remetidos:** `104000017` ÁGUA (consu, 9,40/caixa — própria LF) · `3800018` BATELADA semi (produzido na MO LF).
> O **FRASCO** (vidro) é 95,5% do Ic (R$266,77). Custo dominante do batch.

---

## 2. Lotes + disponibilidade em FB/Estoque(8) — ✅ validado · 🔴 1 bloqueador

> O preview **lista** lotes com saldo livre (FIFO por `in_date`); o **operador escolhe/confirma** o lote por componente. Disponibilidade ao vivo 2026-05-30:

- **15/16 componentes têm saldo livre folgado** em FB/Estoque (ex.: FRASCO 120 un livre lote 85127; ROTULO 120 lote 251041; SAL 9.422; ETIQUETA 309.782).
- 🔴 **BLOQUEADOR — `210030203` CAIXA DE PAPELÃO 320X240X267: saldo livre em FB/Estoque = 0** (50 quants do produto existem, mas em Produção/Fornecedores/MIGRAÇÃO/Ajuste — **nenhum em loc 8**). **Repor/transferir ≥1 un de CAIXA para FB/Estoque ANTES da remessa.** (Em 29/05 havia 10 un; foram consumidas.)

> Rodar `e2e_remessa_etapa1_dryrun.py --caixas 1` na hora da remessa para revalidar saldos/lotes (mudam com a operação diária).

---

## 3. Picking type de criação + locations ✅

- **pt 53** "Expedição Industrialização (FB)" · code=outgoing · **src=8 (FB/Estoque) → dst=26489 (Em Trânsito Industrialização)** · wh=FB.
- 26489 é virtual/trânsito (cmp 0) — **deve zerar** no par remessa↔retorno **para o lote do piloto** (ver §9; 26489 carrega ruído histórico de outros ciclos).

---

## 4. Operação / CFOP 5901 por-linha ✅ resolvido ao vivo
- Operação da linha de remessa = **op 80** "Remessa p/ Industrialização" · CFOP **391** (`codigo_cfop`='5901') → journal 17 → `account_no_payment_id=5101010001`.
- Confirmado em remessas reais RPI/2026/00243-244 (e na cancelada 00242). O fluxo CIEL IT auto-seleciona ao criar a remessa pelo mesmo caminho de 01607/01608.

---

## 5. Checklist pré-condições `action_liberar_faturamento` (ACHADOS §4, campos v17)

**AMBIENTE (já satisfeito):**
- [x] `res.company(FB=1).warehouse_id = 1` ✅

**POR-PICKING (setar na remessa antes de liberar):**
- [ ] `stock.picking.incoterm = 6` (CIF) — **campo `incoterm`, não `incoterm_id`** (confirmado em 01607/01608)
- [ ] `stock.picking.carrier_id = 996` (NACOM GOYA) ✅ existe
- [ ] **operação 80 (5901) + CFOP 391 na(s) linha(s)** — `l10n_br_operacao_id != False` (GATE bloqueante: sem isso o robô não gera a NF)
- [ ] picking **validado** (componentes em 26489) antes de `action_liberar_faturamento`

Após `action_liberar_faturamento`: **robô CIEL IT cria a invoice em ~90s** (polling). Conferir 5901 (CST51, `amount_total=0`, `amount_untaxed=I≈R$279,24`) **antes** de transmitir.

---

## 6. Reaproveitar vs criar NOVA remessa — ✅ decisão: **NOVA**
- Rastro 29/05 confirmado ao vivo: picking **322049** (FB/SAI/IND/01606) `done`; NF **725676** (RPI/2026/00242) `cancel` (`amount_untaxed`=R$2.797,85 = **10 caixas**); **reversão física completa via `FB/DEV/00658`** (26489→8, `done`, "Devolução de FB/SAI/IND/01606", quantidades ×10).
- **NF SEFAZ cancelada não se reabre** + picking done + devolução feita = **criar remessa NOVA** com lotes frescos. (Não reaproveitar.)

---

## 7. Números do piloto ✅

| Símbolo | Significado | Valor |
|---|---|---|
| **I** | valor remessa (16 remetidos, AVCO FB) = `Ic+Is` | **R$ 279,24** (1 caixa) — *anchor histórico NF725676 R$2.797,85 era **10 caixas** → /10 ≈ R$279,78, bate* |
| **Ic** | insumos consumidos | = I (cenário **sem sobra**) |
| **Is** | sobra | **0** (sem sobra) → SEM linha 5903/1903 |
| **S** | valor agregado LF (serviço) | **R$ 35,00 / caixa** × 1 = **R$ 35,00** (supplierinfo 6319) |
| **PA** | valoração do PA na FB (AVCO-alvo) | **Ic + S = R$ 314,24** |

**Cenário recomendado: SEM SOBRA** (remeter exatamente a BoM → Is=0 → NF retorno só 5902+5124; entrada FB só 1902+1124). Simplifica a prova (`SOT §3`).

> ⚠️ **Risco aberto — AVCO do PA com 1902 simbólica (3 pernas):** com a op 3252 (`movimento_estoque=False`), a linha 1902 **não gera stock.move** → o `Ic` **não** entra no AVCO via 1902. Para o PA valer `Ic+S`, a **NF de retorno da LF deve declarar `price_unit` do PA = Ic+S na linha que gera o stock.move (1124)** (`SOT §76`). **Pós-piloto, conferir `standard_price`/AVCO do 4870112 na FB.** Como exatamente o `Ic` compõe o custo do PA = item "3 pernas" do **Contador** (`PROPOSTA §3 PERNAS`).

---

## 8. Sequência de execução (Etapa 1) — com gates

0. **GATE 0 (pré-flight):** confirmar (a) reversão do 322049 feita ✅ (FB/DEV/00658 done); (b) **repor CAIXA 210030203 em FB/Estoque** (§2 bloqueador); (c) 26489 sem resíduo do lote do piloto (snapshot baseline — §9).
1. **Preview (read-only):** `python docs/industrializacao-fb-lf/scripts/e2e_remessa_etapa1_dryrun.py --caixas 1` → confere receita, lotes, Ic, pré-condições. **Apresentar ao Rafael.**
2. *(go)* **Criar picking pt53** (16 moves, src=8→dst=26489, lotes do passo 1). **Meio:** criar `e2e_remessa_criar.py` (dry-run-first) replicando o padrão de `teste_lever_saida_fb.do_transfer` **OU** passo-a-passo na UI Odoo. *(script de criação ainda NÃO existe — próximo entregável após este runbook ser aprovado.)*
3. Setar `incoterm=6`, `carrier_id=996`, operação 80 + CFOP 5901 na(s) linha(s); `button_validate` (componentes → 26489).
4. `action_liberar_faturamento` → aguardar robô CIEL IT (~90s) → ler a NF 5901 → conferir `D 5101010001 +I / C 1150100002 −I` + transitória 1150100012=0 (métrica G0, **filtrando pela cadeia do piloto** — §9).
5. **⛔ GATE SEFAZ:** transmitir a NF 5901 **só com "go" explícito do Rafael** (IRREVERSÍVEL).

---

## 9. Métrica de sucesso da Etapa 1 (G0) — **medir por LOTE/cadeia do piloto** (GOALS §B)
> Saldos absolutos têm histórico (5101010001=R$60,8M; 26489 tem 50 quants negativos de outros ciclos). **Medir o Δ do ciclo, não o saldo absoluto.**
- **Snapshot baseline ANTES da remessa:** quants de 26489 + saldo 1150100012 dos componentes (subtrair depois).
- **Contábil:** Δ(débito−crédito) das `account.move.line` cujo `move` pertence à **cadeia documental do piloto** (NF 5901 + ref/origin do picking) = `D 5101010001 +I / C 1150100002 −I`; transitória `1150100012` da cadeia = 0.
- **Físico:** `stock.move.line` filtradas por **produto + lote do piloto** → componentes saem de FB/Estoque(8) e entram em 26489; 26489 do lote do piloto zera só após o retorno (Etapa 5).

---

## 10. Etapa 5 (G5b) — aplicação da op 3252 ✅ script validado
`scripts/g5b_aplicar_op3252_na_linha.py --move-id <NF entrada FB> [--execute]` — seta `l10n_br_operacao_manual=True` + `l10n_br_operacao_id=3252` **só nas linhas 1902** (insumos consumidos), preservando 1124/1903. Dry-run default; resolve CFOP 1902 ao vivo (`codigo_cfop`); guard de op (ativa, `movimento_estoque=False`), de estado e **anti-falso-sucesso** (aborta se 0 linhas 1902 mas há linhas de produto).
- **⏱️ JANELA OBRIGATÓRIA:** aplicar a op **enquanto o `account.move` está em `draft`** — antes de validar/postar e antes do robô gerar o picking. Aplicar pós-posted = no-op (o stock.move do double-count já foi gerado).
- **Confirmar no piloto:** a NF mista gera picking só das linhas `movimento_estoque=True` (1124/1903), pulando a 1902.

---

## 11. Pendências
**Resolvidas ao vivo (2026-05-30):** Ic por componente (R$279,24) · lotes/saldo · reversão 322049 · warehouse_id(FB)=1 · operação 5901 (op 80) · campos v17.

**Operacional (antes do piloto):**
1. 🔴 Repor **CAIXA 210030203** em FB/Estoque (§2).
2. Criar `e2e_remessa_criar.py` (dry-run-first) OU runbook UI da criação do pt53 (§8 passo 2).
3. Snapshot baseline de 26489 + 1150100012 (§9).

**Contador / desenho (não bloqueiam o piloto G5b; destravam o fechamento do ciclo):**
4. **G5a — CONVERGE com G4 (PROVADO sessão 6):** setar `account_no_payment_id=22800` no **j1001** é **necessário mas INSUFICIENTE sozinho** — experimento provou que numa NF de entrada mista o no_payment NÃO baixa a ATIVA (o FORNECEDORES do serviço absorve a 1902). ⇒ a 1902 de entrada precisa vir em **NF separada** do serviço (mesma decisão fiscal do G4). 🔴 **G4 = G5a = aprovação FISCAL da Contadora** — emitir a 5902 (saída) E escriturar a 1902 (entrada) em NF SEPARADA do serviço (`PROPOSTA §4` opção b; `MATERIAL_CONTADORA_G4.md`; `ACHADOS §sessão 6`).
5. **3 pernas**: como `Ic` entra no AVCO do PA com a 1902 simbólica (§7).
6. Conta valoração SVL-LF (`1150200001` × server action 1899) · conta PRODUÇÃO `1150100004` (L3).
7. Regularização dos acumulados (5101010001 R$60,8M FB + R$8,67M LF; double-count R$785k; 1150100011 −R$1,49bi).

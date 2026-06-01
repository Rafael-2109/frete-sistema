# PROMPT — Próxima sessão (Industrialização FB↔LF)

> **Reescrito 2026-06-01 (2 sessões).** Estado: **Etapa 1 (Remessa) + Etapa 2 (Entrada LF) + Etapa E (MO) EXECUTADAS e VALIDADAS em PROD.** Pendente: **dreno do trânsito 26489** (companheiro FB→30720) + **Etapas 4-5 (retorno LF→FB + entrada FB)** — G5a depende do Contador.

## Como começar
Leia nesta ordem (CANÔNICO): **`README.md` → `GOALS.md` → `SOT_OPERACOES.md` (v2.1) → `RUNBOOK_PILOTO_4870112.md`** — em especial **§0.7** (checkpoint completo desta sessão: Model A inviável → Model B, gotchas **G-ENT-1..10**) + §0.5/§0.6. Depois `ACHADOS_TECNICOS.md` + `PROPOSTA_CONFIG_RETORNO.md`.
**IGNORE** (histórico): `DIRETRIZ.md`, `PLANO_EXECUCAO.md`, `HISTORICO/`.

## Decisões fechadas (não reabrir)
- Conta fiscal = família **`51010xx (ATIVA)` / `51020xx (PASSIVA)`**; SEM ICMS (CST51); tudo CONFIG por-linha.
- **Model B** (escolha do Rafael, porque Model A é INVIÁVEL — `company_id` de lote com estoque é IMUTÁVEL no Odoo, G-ENT-6): a LF recebe **fresco de Vendors→31092 com lotes LF próprios** (mesmo nome PILOTO-3105, company 5); o trânsito 26489 (FB-lote) drena pelo **companheiro FB→30720** (lado FB, separado).
- Entrada LF é **caminho B-ish**: DFe que chega via SEFAZ pode ser **resumo sem linhas** (G-ENT-2) → popular com o XML autorizado da NF de saída.

## ESTADO em PROD (teste controlado 1 caixa — lote PILOTO-3105)
**Etapa 1 (Remessa) ✅:** picking `FB/SAI/IND/01612` (322399), NF `RPI/2026/00245` (735679) SEFAZ-autorizada, NET `D 5101010001 +279,23`.
**Etapa 2 (Entrada LF) ✅ COMPLETA — Model B:**
- DFe **43776** completado (16 linhas, via upload do XML de 735679 + `action_processar_arquivo_manual` + `alinhar_dfe_lines_company`).
- PO **42743** (C2619830, company LF=5, 16 linhas fiscais).
- Picking **322451** (`LF/IN/01790`) **DONE**: Vendors(4)→**31092**, 16 lotes LF PILOTO-3105.
- **SVL Design A**: `D 1150200001 / C 1150100011 = 278,56` (via L1 vivo na categ 193).
- **ENTIN 737062** **POSTED**: `D 1150100011 / C 5101020001 (PASSIVA) = 278,56`, cfop 1901, **op 2686**, journal 1047 (ENTRADA-REMESSA), fp 131.
- **Validador `e2e_piloto_validar.py --modo entrada-lf --picking 322451 --nf 737062 --lote PILOTO-3105`: Δ1150100011(LF)=0.0 PASS, dst=31092 PASS, material 31092 PASS.**
- Rastro cancelado (ignorar): POs 42741 (vazia)/42742 (pt64 não gera picking); picking 322401 (Model A).

**Etapa E (MO) ✅ COMPLETA E VALIDADA (2026-06-01, fix G-ENT-10):**
- **Fix G-ENT-10 RESOLVIDO** (não há método CIEL IT especial): após `action_assign`, **setar `picked=True` nas `stock.move.line` dos raws ANTES do `button_mark_done`** (ground-truth = MO boa LF/MO/03510 (20216), que consome com `picked=True`+`quantity>0`+lote). Sem isso, o wizard `mrp.consumption.warning.action_confirm` dispara `button_mark_done(skip_consumption=True)` que, com `picked=False`, cancela os raws. Codificado em `e2e_mo_lf_criar.py` + POS-CHECK anti-falso-sucesso.
- **MOs novas (boas):** BATELADA **20252** (LF/MO/03519, POS-CHECK 10/10 consumidos) → semi 3800018 (12,818) em 31092; PA **20254** (LF/MO/03521, POS-CHECK 8/8) → PA 4870112 (1,0) em 31093.
- **MOs fantasma 20235/36/38/39 = rastro `done`** (NÃO canceláveis: `action_cancel` falha em done; `unbuild` inflaria os 16 comps). Estoque fantasma (semi+PA) zerado via Skill 1 (`value=0`, sem account.move).
- **Contábil (G3 net-zero terceiros ✓):** ambas as MOs `1150100004`(produção) bal=0 + `1150200001`(terceiros) bal=0; **NÃO tocou estoque próprio LF** (1150100001/002/007). AVCO do PA na LF = **R$188,62** (custo LF dos comps, transitório de terceiros — NÃO é o valor final; PA na FB = Ic+S=R$314,24 vem do `price_unit` da NF de retorno, SOT §7).
- **Validador** `e2e_piloto_validar.py --modo mo --mo 20252 --mo2 20254 --lote PILOTO-3105 --base /tmp/piloto_base.json`: consumo 31092 ✓, PA 31093 ✓, loc 42 inalterado PASS. (⚠️ passar `--lote PILOTO-3105`, senão loc 42 dá falso-FAIL.)
- Resíduo imaterial: poeira de rounding ~1e-5 un em 5 químicos (31092, `value≈0`, esperado G-REM-2).

## PRÓXIMO (pendente go Rafael)
1. **Drenar trânsito 26489** (companheiro FB→30720, lado FB — NÃO drena pela LF no Model B). Decidir/refazer com Rafael.
2. **Etapas 4-5** (retorno LF→FB NF mista 5902+5124 + entrada FB com op 3252 na 1902). **G5a depende do Contador** (journal que credita 5101010001 não existe). Ver `GOALS §B`, `SOT §2 Etapas 4-5`.

## Pendências Etapa 2 (separadas, não bloqueiam a MO)
- **Drenar 26489**: o trânsito ainda tem os 16 comps FB-lote (Model B não drena pela LF). Refazer o companheiro **26489→30720** (lado FB) OU decidir com Rafael.
- **Taxes IBS/CBS**: foram LIMPAS na ENTIN (eram da FB, "empresas incompatíveis"). Refinamento: alinhar à LF (a recuperar).

## Scripts (`docs/industrializacao-fb-lf/scripts/`)
- `e2e_entrada_lf_criar.py` — driver da entrada LF (modos: dry-run, cancelar-comp, completar-dfe, limpar-po, escriturar, **criar-picking-b1** [Model B], validar-picking, **nf** [com B-V23-2 + op-2686 fix inline], post). **Battle-tested nesta sessão.**
- `e2e_mo_lf_criar.py` — driver da MO (modos: dry-run, batelada, pa). **✅ FIX G-ENT-10 aplicado e validado** (picked=True nas move.lines dos raws antes do mark_done + POS-CHECK). Battle-tested 20252/20254.
- `/tmp/fix_entin.py` — fix fiscal da ENTIN (op 2686 + conta 1150100011 + cfop 1901 + payable 5101020001). **Encodar no driver `--modo nf` se reusar.**
- `e2e_piloto_validar.py` — validador read-only (baseline/remessa/entrada-lf/mo/...).

## IDs/constantes-chave
Empresas FB=1/LF=5 · partner LF=35 · Vendors=4 · trânsito=26489 · **31092** (LF/Mat.Terceiros) · **31093** (LF/PA Terceiros) · 30720 (FB customer terceiros) · pt19 (LF receb) · pt36 (LF produção) · op fiscal entrada **2686** · journal **1047** · fp **131** · contas LF: 1150200001(terceiros)/1150100011(transitória)/5101020001(PASSIVA). Lotes: FB PILOTO-3105 ids 60496-60511 (company 1, IMUTÁVEL); LF PILOTO-3105 (company 5, criados no Model B).

## Regras invioláveis
- **dry-run + aprovação do Rafael em TODA escrita Odoo.** O classificador exige "go" FRESCO **depois** da dry-run apresentada (não antes). NF SEFAZ (retorno, Etapa 4) só com "go" explícito.
- **NUNCA** `action_apply_inventory` cru (infla quant negativo) → usar Skill 1 `ajustando-quant-odoo`.
- `action_create_invoice`/`action_gerar_po_dfe` etc. para PO LF: rodar em **contexto `allowed_company_ids=[1,5]`** (senão "sem acesso a account.account/stock.lot LF" ou "empresas incompatíveis"). Ver G-ENT-1/4/7/8.
- Classificador bloqueia bash complexo + skill WRITE → invocação canônica simples (1 comando/escrita).

## Pendente Contador (paralelo)
G5a (journal entrada FB→5101010001, Etapa 5) · 3 pernas (Ic no AVCO do PA) · regularização dos acumulados. NÃO bloqueia a MO nem o dreno.

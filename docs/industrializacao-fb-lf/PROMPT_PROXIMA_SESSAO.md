# PROMPT — Próxima sessão (Industrialização FB↔LF)

> **Atualizado 2026-06-01 (3ª sessão).** Estado: **Etapa 1 (Remessa) + Etapa 2 (Entrada LF) + Etapa E (MO) EXECUTADAS e VALIDADAS em PROD.** **Etapas 4-5 DESBLOQUEADAS**: a **Contadora confirmou o desenho + Opção A (Ativo→Ativo, CPV só na venda)**; roteamento G4/G5a mapeado ao vivo, **spec dos 2 journals em `PROPOSTA_CONFIG_RETORNO.md`** (falta criar via dry-run). ~~Pendente lateral: dreno do trânsito 26489→30720~~ → **✅ DRENO EXECUTADO 2026-06-01** (picking `FB/INT/08128` id 322875 done; 26489 zerado, 30720=42,29 un, **0 SVL/contábil**).

## Como começar
Leia nesta ordem (CANÔNICO): **`README.md` → `GOALS.md` → `SOT_OPERACOES.md` (v2.2) → `RUNBOOK_PILOTO_4870112.md`** — em especial **§0.7** (Model A inviável → Model B, gotchas **G-ENT-1..10**) + §0.5/§0.6. Depois **`PROPOSTA_CONFIG_RETORNO.md`** (spec G4+G5a, é o entregável atual) + `ACHADOS_TECNICOS.md` (§ACHADO 2026-06-01 = roteamento verificado).
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
1. **Implementar a config G4+G5a** (Contadora já confirmou Opção A) — **spec completa em `PROPOSTA_CONFIG_RETORNO.md`**:
   - **G5a (FB)**: criar journal `ENTRADA - RETORNO DE INDUSTRIALIZAÇÃO` (purchase, no_payment=**5101010001**/id22800, espelho inverso de j17) + registro `tipo.pedido.diario(FB, serv-industrializacao)` → esse journal; op **3252** na 1902 (mata double-count).
   - **G4 (LF)**: criar journal `SAÍDA - RETORNO DE INDUSTRIALIZAÇÃO` (sale, no_payment=**5101020001**/id26667, espelho inverso de j1047) + registros `tipo.pedido.diario(LF, dev-industrializacao/perda)`; tirar do journal PERDAS (j1003).
   - **SEM bloqueio do Contador** (ele já deu Opção A + desenho + perna REMESSA + PA=Ic+S). O resto é técnico/piloto: apontar a conta da 1902 via posição fiscal (`PROPOSTA §5`), medir o AVCO no piloto (`PROPOSTA §6`). **dry-run + go Rafael em TODA escrita.**
2. ~~Drenar trânsito 26489→30720~~ — **✅ EXECUTADO 2026-06-01** (picking `FB/INT/08128` id 322875 done). Ver "Pendências Etapa 2" abaixo.

## Pendências Etapa 2 (separadas, não bloqueiam a MO)
- **Drenar 26489 — ✅ EXECUTADO 2026-06-01:** o trânsito tinha os 16 comps FB-lote PILOTO-3105 (lots `60496-60511`, company 1), soma `42,28994948` un. **Drenado → 30720** (`Parceiros/Estoques em poder de terceiros/…LF`, usage=customer, cmp=False) via **picking manual pt5 `FB/INT/08128` (id 322875) done**. POS-CHECK: **26489=0, 30720=42,28994948 (16 quants), 0 SVL** (físico puro, 0 contábil, confirmado ao vivo). Fecha o lado físico FB da remessa (zera junto com 30720 quando o retorno entrar na Etapa 5).
  - **Método (validado):** picking manual pt5 `26489→30720` (replica o companheiro nativo cancelado `322400` FB/INT/08121) — **NÃO** re-disparar a server action 1899 (não-determinística). Driver: **`scripts/e2e_drenar_transito_26489.py`** (`--execute` cancela órfãos + cria pt5 + `do_unreserve` + 16 lots pinados + valida + POS-CHECK).
  - **GOTCHA do driver (G-DRENO-1, corrigido):** o pt5 reserva `at confirm` → `action_confirm` dispara `action_assign` automático criando 16 `move.line` SEM-LOTE que se somam às 16 manuais (32 mls, qty dobrada). A 1ª execução abortou no guard (correto) e deixou órfão `322852` (cancelado na re-execução). **Fix:** `do_unreserve` + unlink de residuais logo após `action_confirm`, antes de criar as move.lines manuais pinadas; + idempotência que cancela órfãos de execuções anteriores. (os 30 quants negativos em 26489 = contrapartida virtual de ajustes de OUTROS lotes, NÃO-físico, ignorar.)
- **Taxes IBS/CBS**: foram LIMPAS na ENTIN (eram da FB, "empresas incompatíveis"). Refinamento: alinhar à LF (a recuperar).

## Scripts (`docs/industrializacao-fb-lf/scripts/`)
- `e2e_entrada_lf_criar.py` — driver da entrada LF (modos: dry-run, cancelar-comp, completar-dfe, limpar-po, escriturar, **criar-picking-b1** [Model B], validar-picking, **nf** [com B-V23-2 + op-2686 fix inline], post). **Battle-tested nesta sessão.**
- `e2e_mo_lf_criar.py` — driver da MO (modos: dry-run, batelada, pa). **✅ FIX G-ENT-10 aplicado e validado** (picked=True nas move.lines dos raws antes do mark_done + POS-CHECK). Battle-tested 20252/20254.
- `/tmp/fix_entin.py` — fix fiscal da ENTIN (op 2686 + conta 1150100011 + cfop 1901 + payable 5101020001). **Encodar no driver `--modo nf` se reusar.**
- `e2e_piloto_validar.py` — validador read-only (baseline/remessa/entrada-lf/mo/...).
- `e2e_drenar_transito_26489.py` — **NOVO (2026-06-01)** dreno físico FB `26489→30720` (pt5, lotes pinados, POS-CHECK). dry-run-first; `--execute` só com go. 0 contábil.

## IDs/constantes-chave
Empresas FB=1/LF=5 · partner LF=35 · Vendors=4 · trânsito=26489 · **31092** (LF/Mat.Terceiros) · **31093** (LF/PA Terceiros) · 30720 (FB customer terceiros) · pt19 (LF receb) · pt36 (LF produção) · op fiscal entrada **2686** · journal **1047** · fp **131** · contas LF: 1150200001(terceiros)/1150100011(transitória)/5101020001(PASSIVA). Lotes: FB PILOTO-3105 ids 60496-60511 (company 1, IMUTÁVEL); LF PILOTO-3105 (company 5, criados no Model B).

## Regras invioláveis
- **dry-run + aprovação do Rafael em TODA escrita Odoo.** O classificador exige "go" FRESCO **depois** da dry-run apresentada (não antes). NF SEFAZ (retorno, Etapa 4) só com "go" explícito.
- **NUNCA** `action_apply_inventory` cru (infla quant negativo) → usar Skill 1 `ajustando-quant-odoo`.
- `action_create_invoice`/`action_gerar_po_dfe` etc. para PO LF: rodar em **contexto `allowed_company_ids=[1,5]`** (senão "sem acesso a account.account/stock.lot LF" ou "empresas incompatíveis"). Ver G-ENT-1/4/7/8.
- Classificador bloqueia bash complexo + skill WRITE → invocação canônica simples (1 comando/escrita).

## Dúvidas técnicas em aberto (resolver na implementação, com dry-run — NÃO bloqueiam o conceito)
- **Roteamento da 1902 (G5a)**: usar `tipo_pedido_entrada=serv-industrializacao` criando registro novo no `tipo.pedido.diario(FB)` (recomendado, isolado) **vs** repontar o j1001 ENTSI (global). `tipo_pedido_entrada` é SELECTION → não dá p/ criar valor novo sem DEV. `PROPOSTA §3b`.
- **Linha 1124 serviço (FB entrada)**: `serv-industrializacao` **não tem registro** no `tipo.pedido.diario(FB)` → cai em journal default — **confirmar qual** antes de escriturar.
- **pt98 nunca usado** (0 pickings): o piloto será o **1º uso real** (31093→26489) — validar comportamento.
- **Criar `account.journal` via XML-RPC**: confirmar se é possível por XML-RPC ou exige UI (DDL de journal).
- **AVCO subvalorizado (G8)**: PA na FB hoje = R$ 35,37/cx (só S) — a NF de retorno precisa declarar `price_unit = Ic+S` (ligado às 3 pernas).

## Contador — JÁ deu o essencial (não bloqueia a implementação)
✅ **Contadora confirmou (2026-06-01): Etapas 4-5 + Opção A (Ativo→Ativo, CPV só na venda) + perna REMESSA direto (5101010001/5101020001) + PA vale Ic+S.** Com isso, **G4/G5a não dependem de mais nenhuma decisão contábil** — o que resta é execução técnica (criar journals, apontar conta da 1902 via posição fiscal, medir AVCO no piloto). **Único re-escalonamento possível**: SE o piloto revelar descasamento AVCO×razão na 1902 simbólica (`PROPOSTA §6`). Separado e sem prazo: regularização dos acumulados (5101010001 R$60,8M etc — `GOALS G9`).

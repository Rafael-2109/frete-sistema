# PROMPT — Próxima sessão (Industrialização FB↔LF)

> **Reescrito 2026-06-01.** Substitui a versão de 30/05. Estado: **Etapa 1 (Remessa) EXECUTADA em PROD** (SEFAZ autorizado). Próximo = **Etapa 2 / passo C — Entrada LF**.

## Como começar
Leia nesta ordem (CANÔNICO): **`README.md` → `GOALS.md` → `SOT_OPERACOES.md` (v2.1) → `CICLO_COMPLETO_MAPA.md` → `ACHADOS_TECNICOS.md` → `RUNBOOK_PILOTO_4870112.md`** (§0.5 plano A0-K + §0.6 checkpoint+gotchas) + `PROPOSTA_CONFIG_RETORNO.md`.
**IGNORE** (histórico): `DIRETRIZ.md`, `PLANO_EXECUCAO.md`, `HISTORICO/`.

## Decisões fechadas (não reabrir)
- Conta fiscal = família **`51010xx` (ATIVA) / `51020xx` (PASSIVA)**; **NÃO** `1150200001` (= só valoração SVL-LF).
- Saída FB (5901) já correta; o problema é o **RETORNO** (Etapa 5). **SEM ICMS** (CST51). Tudo é **CONFIG** (operação por-linha + `movimento_estoque`).
- **G5b ≠ G5a**: piloto valida G5b (op 3252, sem double-count). `Δ5101010001(FB)=0` é G5a → journal de entrada novo (**Contador**, ainda inexistente).

## Estado em PROD (teste controlado 1 caixa — lote `PILOTO-3105`)
- **A0** baseline salvo em `/tmp/piloto_base.json` ⚠️ **efêmero — re-gerar se /tmp foi limpo** (`e2e_piloto_validar.py --modo baseline --lote PILOTO-3105 --out /tmp/piloto_base.json`).
- **A** ✅ 16 quants criados no lote `PILOTO-3105` @ FB/Estoque(8) (qty exata 1 caixa, Ic R$279,24).
- **B** ✅ **Remessa SEFAZ-autorizada**: picking `FB/SAI/IND/01612` (id **322399**) done → 16 comps em **26489** lote PILOTO-3105; NF **`RPI/2026/00245`** (id **735679**) AUTORIZADA, chave `35260661724241000178550010000946041007356795`; G0 atingido (NET `D 5101010001 +279,23 / C estoque`; transitória 1150100012 resíduo R$0,05 imaterial).
- Pickings cancelados 01609/10/11 = rastro das iterações (ignorar).

## PRÓXIMO: Etapa 2 / passo C — Entrada LF (⚠️ etapa duvidosa #1)
Os 16 componentes estão em **26489**. A LF precisa **receber** o DFe da RPI/2026/00245. Objetivos:
1. **Pré-flight** (read-only): `e2e_piloto_validar.py --modo preflight-lf` — confere `default_location_dest_id` de pt64/pt19 (deve ser **31092** "Materiais de Terceiros", não 42).
2. **Receber** (escriturar o DFe no LF): caminho via Skill 7 `escriturando-odoo` (FLUXO L3 1.2.x) OU picking pt64 — **decidir e apresentar dry-run ANTES de escrever**. `action_gerar_po_dfe` herda company do user → forçar `allowed_company_ids=[5]`.
3. **Levers a testar:** **L2** (material entra em **31092**, não 42) + **L1 Design A** (SVL `D 1150200001 / C 1150100011`; NF ENTIN `D 1150100011 / C 5101020001`).
4. **Validar** (D): `e2e_piloto_validar.py --modo entrada-lf --picking <pt64> --nf <entin> --lote PILOTO-3105` → **Δ1150100011(LF)=0** (Design A fecha a transitória) + **26489 do lote zera** + material em 31092. Se 1150100011 não fechar → reavaliar A vs B (Contador).

## Scripts (`docs/industrializacao-fb-lf/scripts/`)
- `e2e_piloto_validar.py` — multi-modo (baseline/diff/preflight-lf/remessa/entrada-lf/mo/entrada-fb), métricas computadas PASS/FAIL.
- `e2e_remessa_criar.py` — passo B (battle-tested; gotchas G-REM-1..4 no RUNBOOK §0.6).
- `g5b_aplicar_op3252_na_linha.py` — passo H (op 3252 na linha 1902, em DRAFT).
- `e2e_remessa_etapa1_dryrun.py` — preview disponibilidade.

## Regras invioláveis
- **NF SEFAZ** (Etapas 1 e 4) = IRREVERSÍVEL → só com "go" explícito; **dry-run + apresentar antes de qualquer escrita Odoo**.
- Odoo PROD via XML-RPC. **Gotchas:** v17 (`display_type='product'`, `codigo_cfop`, `stock.picking.incoterm`) · G-REM-1 partner_id companheiro · transmissão SEFAZ só via `transmitir_nfe_via_playwright`. Ver ACHADOS §4 + RUNBOOK §0.6.
- Classificador bloqueia comandos Bash complexos com skills WRITE → usar **invocação canônica simples** (1 comando por escrita).

## Pendente Contador (paralelo; destrava fechamento do ciclo, não bloqueia C)
G5a (journal entrada→5101010001) · 3 pernas (Ic no AVCO do PA) · conta valoração SVL-LF · regularização dos acumulados.

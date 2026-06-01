# Industrialização FB↔LF

Industrialização por encomenda dentro do grupo: **FB** (encomendante) remete insumos → **LF** (industrializadora) produz e devolve o PA. Objetivo: **acertar fluxo físico + contábil** para os insumos de terceiros **não inflarem o estoque** (passivo medido: **R$ 785k** só no MOLHO SHOYU PET; `5101010001` FB acumulado **R$ 60,8M**).

> **Estado: 2026-05-30** — desenho mapeado e verificado; 2 escritas config aplicadas (op 3252 + L1, reversíveis); **piloto E2E NÃO iniciado** (aguarda go p/ a remessa). Ver `ESTADO_ATUAL` abaixo e `PROMPT_PROXIMA_SESSAO.md`.

---

## Leia nesta ordem (CANÔNICO)

| # | Doc | O que é |
|---|---|---|
| 1 | **`GOALS.md`** | **COMECE AQUI.** Plano objetivo: fluxo atual×correto×mudança por operação + 10 goals com **métrica de sucesso** + levers + ordem de ataque. |
| 2 | **`SOT_OPERACOES.md`** (v2.2) | Fonte única do **desenho-alvo** por operação (CFOP/contábil/estoque), prova de fechamento do ciclo, decisões do Contador. |
| 2b | **`PROPOSTA_CONFIG_RETORNO.md`** | **Spec G4+G5a** (entregável atual): 2 journals + roteamento, com IDs; status das decisões (Contadora já confirmou Opção A). |
| 3 | **`CICLO_COMPLETO_MAPA.md`** | Os **fatos verificados**: como o ciclo é hoje, por que não fecha, os 3 saldos que acumulam. |
| 4 | **`ACHADOS_TECNICOS.md`** | **Mecanismo Odoo/CIEL IT** + IDs (contas, ops, journals, locations) + os achados 2026-05-30 (5101010001, granularidade por-linha, movimento_estoque). |
| 5 | **`PROPOSTA_CONFIG_RETORNO.md`** | Proposta concreta de operações+journals do retorno (G5a/G5b) — o que criar/ajustar. |
| — | **`T-*-resultado.md`** | Log de execução: `T-PASSO0-TESTE` (G5b wiring LF ✅), `T-G5B-OP` (op 3252 ✅). |

## ESTADO_ATUAL (checkpoint 2026-06-01 — piloto 4870112 1 caixa, lote PILOTO-3105)
**Config base (reversível):** ✅ Op 3252 (`movimento_estoque=False`, lever G5b) · ✅ **L1 aplicado** (14 categorias LF → valoração `1150200001`/input `1150100011`/output `1150100012`, Design A — **VIVO e validado**).
**Piloto E2E (ver `RUNBOOK §0.7` + `PROMPT_PROXIMA_SESSAO.md`):**
- ✅ **Etapa 1 (Remessa)**: NF `RPI/2026/00245` SEFAZ-OK; `D 5101010001 +279,23`.
- ✅ **Etapa 2 (Entrada LF) COMPLETA — Model B**: picking `LF/IN/01790` (322451) Vendors→**31092** (lotes LF); SVL Design A `D 1150200001 / C 1150100011`; **ENTIN 737062 POSTED** `D 1150100011 / C 5101020001 (PASSIVA)`; **validador Δ1150100011=0 PASS**. (Model A inviável — lote com estoque tem company imutável, G-ENT-6.)
- ✅ **Etapa E (MO) COMPLETA — fix G-ENT-10**: MOs **20252** (BATELADA) + **20254** (PA) consumiram 31092 → PA em 31093; **net-zero terceiros** (`1150100004`/`1150200001` bal=0), estoque próprio LF intacto (G3 ✅). Fantasmas (20235/36/38/39) = rastro `done`, estoque zerado via Skill 1. Fix: `picked=True` nas move.lines dos raws antes do `mark_done`.
- ✅ **Etapas 4-5 (retorno) — DESBLOQUEADAS (2026-06-01)**: a **Contadora confirmou** o desenho + **Opção A (Ativo→Ativo, CPV só na venda)**. Roteamento G4 (LF saída baixar PASSIVA 5101020001) + G5a (FB entrada baixar ATIVA 5101010001) **mapeado ao vivo**; spec dos 2 journals + `tipo.pedido.diario` em **`PROPOSTA_CONFIG_RETORNO.md`** (falta criar via dry-run; pendente Contador: 3 pernas + perna REMESSA×RETORNO + resíduo NF mista).
- ⏳ **Pendente lateral**: drenar trânsito 26489→30720 (físico, **0 contábil**, driver `scripts/e2e_drenar_transito_26489.py` dry-run pronto — não bloqueia Etapas 4-5).

## Decisão de base (resolvida nesta sessão)
- **Conta**: usar a família de compensação existente **`51010xx` (ATIVA) / `51020xx` (PASSIVA)** — **NÃO** `1150200001` como conta fiscal (a `DIRETRIZ` errou). `1150200001` é só a conta de **valoração SVL** da LF (camada distinta).
- **Saída FB (remessa) JÁ está correta** (`D 5101010001 / C 1150100002`). O problema é o **RETORNO** não fechar.
- **Sem ICMS** em nenhuma etapa (CST51 + CBS/IBS/PIS/COFINS). Não mexer em imposto.
- **Tudo é CONFIG** (operação por-linha + `movimento_estoque`), não DEV.

## Contador — JÁ confirmou o essencial (2026-06-01)
✅ Opção A (Ativo→Ativo, CPV só na venda) · perna REMESSA direto · PA vale Ic+S · Design A da SVL-LF (vivo na Etapa 2) · conta PRODUÇÃO 1150100004 (validada net-zero na MO). **G4/G5a não dependem de mais decisão contábil** — resta execução técnica (`PROPOSTA §5/§6/§8`).
- 🟡 Único re-escalonamento possível: SE o piloto revelar descasamento AVCO×razão na 1902 simbólica (3 pernas — `PROPOSTA §6`).
- ⏳ Separado/sem prazo: **regularização dos acumulados** (`5101010001` R$60,8M FB + R$8,67M LF; double-count R$785k; `1150100011` −R$1,49bi) — `GOALS G9`.

## ⚠️ SUPERSEDED (referência histórica — NÃO seguir como verdade atual)
- `DIRETRIZ.md` — propunha migrar tudo p/ `1150200001`. **Superado por `SOT_OPERACOES.md`** (adota 51010xx).
- `PLANO_EXECUCAO.md` / `00_FLUXO_ATUAL_VS_IDEAL.md §3` — plano/ideal preliminares. **Superados por `GOALS.md` + `SOT`**. (`00_FLUXO §1-2` ainda vale como enunciado do problema.)
- `PASSO0_LEVANTAMENTO.md` — levantamento das categorias LF (válido); a parte de conta foi superada pelo SOT.
- `HISTORICO/` — execução "Opção 2 / inter-company" **abandonada**. IDs válidos, fluxo NÃO.

## Scripts (`scripts/`, todos READ-ONLY exceto onde dito)
Probes Passo 0 (`passo0_*`), ciclo (`ciclo_*`), G5b (`g5b_*`), E2E (`e2e_*`). **WRITE**: `teste_controlado_repoint.py` (LF wiring, auto-restaura), `teste_lever_saida_fb.py` (lever FB, refutado), `g5b_piloto_criar_operacao.py` (op 3252), `e2e_l1_repoint_lf.py` (L1, `--revert`).

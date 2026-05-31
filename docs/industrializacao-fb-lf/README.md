# Industrialização FB↔LF

Industrialização por encomenda dentro do grupo: **FB** (encomendante) remete insumos → **LF** (industrializadora) produz e devolve o PA. Objetivo: **acertar fluxo físico + contábil** para os insumos de terceiros **não inflarem o estoque** (passivo medido: **R$ 785k** só no MOLHO SHOYU PET; `5101010001` FB acumulado **R$ 60,8M**).

> **Estado: 2026-05-30** — desenho mapeado e verificado; 2 escritas config aplicadas (op 3252 + L1, reversíveis); **piloto E2E NÃO iniciado** (aguarda go p/ a remessa). Ver `ESTADO_ATUAL` abaixo e `PROMPT_PROXIMA_SESSAO.md`.

---

## Leia nesta ordem (CANÔNICO)

| # | Doc | O que é |
|---|---|---|
| 1 | **`GOALS.md`** | **COMECE AQUI.** Plano objetivo: fluxo atual×correto×mudança por operação + 10 goals com **métrica de sucesso** + levers + ordem de ataque. |
| 2 | **`SOT_OPERACOES.md`** (v2.1) | Fonte única do **desenho-alvo** por operação (CFOP/contábil/estoque), prova de fechamento do ciclo, decisões do Contador. |
| 3 | **`CICLO_COMPLETO_MAPA.md`** | Os **fatos verificados**: como o ciclo é hoje, por que não fecha, os 3 saldos que acumulam. |
| 4 | **`ACHADOS_TECNICOS.md`** | **Mecanismo Odoo/CIEL IT** + IDs (contas, ops, journals, locations) + os achados 2026-05-30 (5101010001, granularidade por-linha, movimento_estoque). |
| 5 | **`PROPOSTA_CONFIG_RETORNO.md`** | Proposta concreta de operações+journals do retorno (G5a/G5b) — o que criar/ajustar. |
| — | **`T-*-resultado.md`** | Log de execução: `T-PASSO0-TESTE` (G5b wiring LF ✅), `T-G5B-OP` (op 3252 ✅). |

## ESTADO_ATUAL (checkpoint 2026-05-30)
**Mapeamento completo + 2 escritas reversíveis aplicadas no Odoo PROD:**
- ✅ **Op 3252** criada (cópia da 2027, `movimento_estoque=False`, isolada/sem cfop_orig) — o lever G5b. *(reversível: desativar op)*
- ✅ **L1 aplicado**: 14 categorias LF repointadas → valoração `1150200001` / input `1150100011` / output `1150100012`. *(reversível: `e2e_l1_repoint_lf.py --revert`, snapshot `/tmp/e2e_l1_snapshot.json` — ⚠️ snapshot em /tmp some no reboot)*
- ⬜ **Piloto E2E NÃO iniciado** — próximo = Etapa 1 (remessa NF 5901 SEFAZ). Runbook em `PROMPT_PROXIMA_SESSAO.md` + `GOALS.md §C` + `PROPOSTA_CONFIG_RETORNO.md §Sequência`. (`GOALS §A` é só o design por-operação.)

## Decisão de base (resolvida nesta sessão)
- **Conta**: usar a família de compensação existente **`51010xx` (ATIVA) / `51020xx` (PASSIVA)** — **NÃO** `1150200001` como conta fiscal (a `DIRETRIZ` errou). `1150200001` é só a conta de **valoração SVL** da LF (camada distinta).
- **Saída FB (remessa) JÁ está correta** (`D 5101010001 / C 1150100002`). O problema é o **RETORNO** não fechar.
- **Sem ICMS** em nenhuma etapa (CST51 + CBS/IBS/PIS/COFINS). Não mexer em imposto.
- **Tudo é CONFIG** (operação por-linha + `movimento_estoque`), não DEV.

## Pendente (Contador) — destrava o restante
1. Design A vs B da valoração SVL-LF (fechar `1150100011`) + colisão de `1150200001` com server action 1899.
2. Composição "3 pernas" (custo dos insumos `Ic` no valor do PA).
3. Regularização dos acumulados (`5101010001` R$60,8M FB + R$8,67M LF; double-count R$785k; `1150100011` −R$1,49bi).
4. Conta de PRODUÇÃO `1150100004` (transitória vs terceiros).

## ⚠️ SUPERSEDED (referência histórica — NÃO seguir como verdade atual)
- `DIRETRIZ.md` — propunha migrar tudo p/ `1150200001`. **Superado por `SOT_OPERACOES.md`** (adota 51010xx).
- `PLANO_EXECUCAO.md` / `00_FLUXO_ATUAL_VS_IDEAL.md §3` — plano/ideal preliminares. **Superados por `GOALS.md` + `SOT`**. (`00_FLUXO §1-2` ainda vale como enunciado do problema.)
- `PASSO0_LEVANTAMENTO.md` — levantamento das categorias LF (válido); a parte de conta foi superada pelo SOT.
- `HISTORICO/` — execução "Opção 2 / inter-company" **abandonada**. IDs válidos, fluxo NÃO.

## Scripts (`scripts/`, todos READ-ONLY exceto onde dito)
Probes Passo 0 (`passo0_*`), ciclo (`ciclo_*`), G5b (`g5b_*`), E2E (`e2e_*`). **WRITE**: `teste_controlado_repoint.py` (LF wiring, auto-restaura), `teste_lever_saida_fb.py` (lever FB, refutado), `g5b_piloto_criar_operacao.py` (op 3252), `e2e_l1_repoint_lf.py` (L1, `--revert`).

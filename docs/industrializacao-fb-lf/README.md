# Industrialização FB↔LF — Índice

Industrialização por encomenda no grupo: **FB** (encomendante) remete insumos → **LF** (industrializadora) produz e devolve o PA. Objetivo: fechar o fluxo físico+contábil para os insumos de terceiros **não inflarem o estoque** (passivo medido R$ 785k só no MOLHO SHOYU PET; `5101010001` FB acumulado R$ 60,8M).

> **Este README é o ÍNDICE** — só ponteiros. Cada assunto tem **um dono**; a informação mora num lugar só (não é replicada entre docs). Progressive disclosure: abra o doc do tema quando precisar do detalhe.

## Mapa dos documentos (cada um = 1 tema)

| Camada | Doc | Dono de | Abra quando |
|---|---|---|---|
| índice | **`README.md`** (este) | índice + ESTADO atual | ponto de entrada |
| handoff | **`PROMPT_PROXIMA_SESSAO.md`** | próximo passo da sessão | retomar o trabalho |
| desenho ⭐ | **`SOT_OPERACOES.md`** | desenho-alvo + **DECISÕES** (CFOP/contábil/estoque por etapa) | entender "o que deve ser" / qualquer decisão |
| metas | **`GOALS.md`** | metas + critério de sucesso por goal | medir se uma etapa fechou |
| mecanismo | **`ACHADOS_TECNICOS.md`** | como o Odoo/CIEL IT decide + IDs/constantes | precisar de um ID ou do mecanismo |
| execução config | **`PROPOSTA_CONFIG_RETORNO.md`** | **COMO** executar a config G4/G5a (IDs, roteamento, dry-run) | criar/ajustar journals do retorno |
| procedimento | **`RUNBOOK_PILOTO_4870112.md`** | passos do piloto + gotchas (G-ENT/G-REM/G-DRENO) + drivers | executar uma etapa no Odoo |
| histórico | **`HISTORICO/`** | superseded (DIRETRIZ, PLANO_EXECUCAO, 00_FLUXO, PASSO0, CICLO, T-*) | arqueologia — **NÃO seguir** |

⭐ fonte única. **Em conflito, a SOT vence**; os demais apontam para ela, não copiam.

## ESTADO (checkpoint 2026-06-01 — piloto 4870112, 1 caixa, lote PILOTO-3105)

Config base (reversível): ✅ op 3252 (`movimento_estoque=False`) · ✅ L1 (categorias LF, Design A).

| Etapa | Estado |
|---|---|
| 1 — Remessa FB→LF | ✅ NF `RPI/2026/00245` SEFAZ-OK; `D 5101010001 +279,23` |
| Dreno físico FB `26489→30720` | ✅ EXECUTADO — picking `FB/INT/08128` (322875); 26489→0, 30720=42,29, **0 SVL** |
| 2 — Entrada LF (Model B) | ✅ picking 322451→31092; ENTIN 737062 posted; Δ1150100011=0 |
| E — MO | ✅ MOs 20252+20254; net-zero terceiros; PA em 31093 |
| 4 — Retorno LF→FB (faturar) | ⏳ pendente — depende da config **G4** |
| 5 — Entrada FB (escriturar) | ⏳ pendente — depende da config **G5a** |

**Próximo:** config do retorno (G4+G5a). Passo → `PROMPT_PROXIMA_SESSAO.md`. Decisão+execução → `SOT §2 L5a` + `PROPOSTA §3`.

## Decisões fechadas (detalhe e porquê na `SOT`)
- Conta de compensação = família **`51010xx` ATIVA / `51020xx` PASSIVA** (NÃO `1150200001`, que é só valoração SVL-LF).
- **Opção A** (Ativo→Ativo, CPV só na venda) — Contadora confirmou 2026-06-01.
- **G5a = AJUSTAR o journal `j1001` existente** (`account_no_payment_id`=5101010001), **não** criar journal novo. **G4 = criar journal LF de saída** (no_payment=5101020001) + tirar de PERDAS.
- Compensação 51010xx vem do `account_no_payment_id` do **journal** (não da posição fiscal).
- Sem ICMS em nenhuma etapa (CST51 + CBS/IBS/PIS/COFINS).
> Fonte: `SOT_OPERACOES.md` (§0 princípio · §2 por etapa · §5 decisões · §histórico v2.3).

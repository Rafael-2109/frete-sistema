# Atualizacao Memory Eval — 2026-06-29-1

**Data**: 2026-06-29
**Health Score**: **86/100 (+0)** — estabiliza em 86 (recupera o -1 de 06-22, mas NAO retoma o recorde 87 de 06-15)
**Fonte**: Render Postgres `dpg-d13m38vfte5s738t6p50-a` (read-only, 8 queries — 7 do protocolo + 1 consolidada)

> Q6 (detalhe por linha das memorias empresa) retornou ~124KB e estourou o limite de tokens inline;
> resolvido por agregacao SQL equivalente (contagens reviewed_at/cold/stale/efficacy). Nenhuma query falhou.

---

## Resumo Executivo

Ciclo de **consolidacao tecnica**: health volta a 86 mas o sistema esta na pratica **PARADO em duas frentes criticas** que so nao derrubam o score porque as dimensoes que elas afetam ainda estao acima do threshold. A base de memorias cresceu forte (+120, +16.4%) e o uso segue saudavel (1019 sessoes, 31 usuarios), mas:

1. **KG completamente travado (follow-up #4, 5o ciclo)**: memorias linkadas CRAVADAS em **245** (identico a 06-15, 06-22) e relacoes CRAVADAS em **7808** (identico a 06-22). Com a base crescendo, coverage desabou de novo: 33.6% -> **28.8%** (-4.8pp). O pipeline entity->memory linking esta **morto** ha 3 leituras.
2. **Divida de revisao empresa em maximo historico (11o ciclo)**: empresa 329 -> **382 (+53)**, never_reviewed 216 -> **269 (70.4%, novo RECORDE)**.

As 3 dimensoes "verdes" (eficacia 0.81, stale 2.6%, correcoes 0.38) seguram o score; KG (2.2/15 pts) e o calcanhar cronico.

---

## Metricas de Sessoes (Q1)

| Metrica | Valor | vs 06-22 |
|---------|-------|----------|
| Total de sessoes | 1019 | +71 |
| Sessoes ultima semana | 72 | -5 (77) |
| Sessoes ultimo mes | 302 | -12 (314) |
| Usuarios unicos (total) | 31 | +1 |
| Msgs/sessao (media) | 9.14 | estavel |
| Custo/sessao (media) | US$ 3.76 | -US$0.06 (3.82) |

Sessoes semanais seguem na faixa fria (72 vs 77), mas a base total cruza **1019** (marco de 1000). Custo medio por sessao continua caindo lentamente.

---

## Sessoes por Usuario — Top 30d (Q5)

28 usuarios ativos nos ultimos 30d. Top 8 por sessoes:

| user_id | Nome | Sessoes | Msgs | Custo (US$) | Ultima sessao |
|---------|------|---------|------|-------------|---------------|
| 1 | Rafael Nascimento | 58 | 367 | 328.88 | 2026-06-29 |
| 18 | Marcus Lima | 32 | 374 | 221.33 | 2026-06-29 |
| 17 | Talita De Le Lima | 28 | 501 | 183.14 | 2026-06-25 |
| 4 | Jessica Tereza | 22 | 108 | 21.55 | 2026-06-25 |
| 45 | Sabrina Lima | 20 | 303 | 202.60 | 2026-06-25 |
| 54 | Gabriella Silva | 16 | 123 | 175.42 | 2026-06-29 |
| 82 | Martha Frugoli | 15 | 313 | 189.11 | 2026-06-25 |
| 78 | Rayssa Alves | 13 | 320 | 260.64 | 2026-06-26 |

Custo concentrado: Rafael (1) + Marcus (18) + Rayssa (78) + Sabrina (45) somam ~US$1013 dos ~US$2050 do mes. Cauda longa de 13 usuarios com 1-5 sessoes (onboarding/uso esporadico).

---

## Memorias por Categoria e Escopo (Q2)

**Total: 850 memorias** (is_directory=false) — +120 vs 730 (06-22), +16.4%.

| Categoria | Escopo | Total | Avg Imp | Avg Usage | Avg Effective | Avg Corr | Cold | Stale 60d |
|-----------|--------|-------|---------|-----------|---------------|----------|------|-----------|
| cold | pessoal | 15 | 0.70 | 14.4 | 8.8 | 0 | 15 | 0 |
| contextual | empresa | 2 | 0.90 | 15.0 | 28.5 | 0 | 0 | 0 |
| contextual | pessoal | 23 | 0.50 | 23.3 | 25.5 | 0.43 | 3 | 1 |
| operational | empresa | 61 | 0.83 | 64.0 | 50.0 | 0.03 | 12 | 1 |
| operational | pessoal | 69 | 0.56 | 24.1 | 24.5 | 0.46 | 4 | 5 |
| permanent | empresa | 6 | 0.90 | 197.5 | 124.7 | 0 | 0 | 0 |
| permanent | pessoal | 65 | 0.87 | 59.3 | 58.9 | 0.22 | 0 | 4 |
| structural | empresa | 311 | 0.80 | 59.9 | 47.6 | 0.03 | 52 | 3 |
| structural | pessoal | 298 | 0.72 | 7.4 | 8.0 | 0.87 | 21 | 8 |

**Totais**: cold = **107 (12.59%)** · stale 60d = **22 (2.59%)** · conflitos = **0**.

Observacoes:
- `structural/empresa` (311) e `structural/pessoal` (298) sao os dois grandes motores de crescimento — juntos = 71.6% da base.
- `structural/pessoal` segue como o **motor de correcoes**: avg_corrections **0.87** (era 0.73 em 06-22, 0.49 em 06-15) — **3a alta consecutiva**, margem do threshold (<0.5 = 100%) ja foi rompida NESTA categoria; so a media global a segura.
- Cold concentrado em `structural/empresa` (52) — cold-tiering operando em conhecimento estavel da empresa, comportamento esperado.

---

## Top 20 Memorias de Baixa Eficacia (Q3)

`usage >= 3`, `efficacy < 0.3`, `category != permanent`. As de maior impacto (alto uso, eficacia ~zero):

| path (resumido) | cat | escopo | usage | eff | efic | corr |
|-----------------|-----|--------|-------|-----|------|------|
| heuristicas/integracao/memorias-de-usuario-...protocolo-ativo | operational | empresa | **172** | 9 | 0.052 | 0 |
| heuristicas/geral/integracao-nf | structural | empresa | **108** | 5 | 0.046 | 0 |
| heuristicas/geral/confirmar-pedido | structural | empresa | **81** | 4 | 0.049 | 0 |
| heuristicas/geral/a-rede-assai-opera-com-multiplas-lojas | structural | empresa | 49 | 3 | 0.061 | 0 |
| system/download_config | structural | pessoal(1) | 47 | 3 | 0.064 | 0 |
| armadilhas/geral/build_artifact_pnpm.md | operational | empresa | 36 | 2 | 0.056 | 0 |
| **protocolos/integracao/diagnostico-de-regressao-sem-historico-git** | structural | empresa | **32** | 0 | **0.000** | 0 |
| armadilhas/integracao/_archived_..._presigned-url-s3-vence (**4x arquivada**) | structural | empresa | 23 | 0 | **0.000** | 0 |
| armadilhas/integracao/reautorizacao-oauth-...-tagplus | structural | empresa | 20 | 0 | **0.000** | 0 |
| heuristicas/geral/quando-o-usuario-envia-saudacao-e-pedido | structural | empresa | 19 | 0 | **0.000** | 0 |
| perfis/comercial/gabriella-comunica-se-de-forma-telegrafica | structural | empresa | 17 | 0 | **0.000** | 0 |
| corrections/quando-pergunta-detalhes-de-um-cluster (u18) | structural | pessoal | 10 | 0 | 0.000 | **8** |

Leitura (segue follow-up #3 — **metrica cega para always-on de governanca**):
- As memorias de TOPO de uso (`protocolo-ativo` u172, `integracao-nf` u108, `confirmar-pedido` u81) sao **heuristicas always-on injetadas via builder de diretrizes** — `effective_count` (similaridade resposta<->memoria) NAO as captura. Sao protocolos de comportamento, nao conhecimento citavel. Eficacia ~0.05 e **falso negativo**, ja diagnosticado.
- **16 memorias** com usage>=10 e efic<0.1 (vs 13 nas empresa-only; era ~14 em 06-22). A divida de "ruido real vs cego" so se resolve com o judge calibrado (follow-up #1).
- `_archived_presigned-url-s3` **continua 4x arquivada e em uso** (u23, efic 0) — 7o ciclo do bug. Renomear nao desliga a injecao.
- `diagnostico-de-regressao-sem-historico-git` (empresa, u32, **0 effective em 32 usos**) — candidata clara a auditoria de conteudo.

---

## Knowledge Graph (Q4 + Q7)

| Metrica | Valor | vs 06-22 | Sinal |
|---------|-------|----------|-------|
| Total entidades | 3815 | +12 (3803) | poda parou |
| Entidades orfas | **1626** (42.6%) | +12 | piora marginal |
| Memorias com entidade | **245** | **CRAVADO** (245) | **pipeline morto** |
| Coverage (245/850) | **28.8%** | -4.8pp (33.6%) | **5o ciclo de queda** |
| Total relacoes | **7808** | **CRAVADO** (7808) | **pipeline morto** |

**Diagnostico (follow-up #4 CONFIRMADO e agravado)**: tanto `memorias linkadas` (245) quanto `total de relacoes` (7808) estao **byte-a-byte identicos** a 06-22. Com a base crescendo +120, NENHUMA das memorias novas foi linkada nem gerou relacao. O job de extracao entity->memory esta **parado ha pelo menos 3 ciclos** (245 cravado desde 06-15). Coverage so cai por diluicao. Isto e o unico fator que impede o health de voltar a 87.

Entidades por tipo (top): conceito 1401 (192 linkadas), cliente 760 (27), produto 578 (49), transportadora 444 (22), processo 273 (136). `usuario` (16) e `uf` (74) tem as maiores avg_mentions (5.9 e 4.5) — bem conectadas; o grosso de cliente/produto/transportadora e mono-mencao orfa (catalogo morto).

Relacoes top (Q7): grafo coerente em qualidade — `ASSAI requer CONFIRMACAO-MANUAL` (w5), `DRY-RUN-OBRIGATORIO precede ACOES-EM-LOTE-ODOO` (w5), `CONFIRMAR-PEDIDO co_occurs COTACAO` (w3.5). As arestas existentes sao boas; o problema e exclusivamente de **volume/atualizacao**, nao de qualidade.

---

## Memorias Empresa (user_id=0) — Detalhado (Q6, agregado)

| Metrica | Valor | vs 06-22 |
|---------|-------|----------|
| Total empresa | **382** | +53 (329) |
| Nunca revisadas (reviewed_at NULL) | **269 (70.4%)** | +53 — **RECORDE** |
| Revisadas ha >30d | 105 | estavel |
| Stale 60d | 4 | estavel |
| Cold | 64 | estavel |
| Baixa eficacia + alto uso (u>=10, efic<0.1) | 13 | estavel |
| Avg importance | 0.80 | estavel |
| Avg usage | 62.6 | estavel |
| Avg efficacy | 0.872 | estavel |

**Marco negativo cronico (11o ciclo)**: empresa cresceu +53 e `reviewed_at` NULL subiu **exatamente +53** — divida 1:1, **zero revisao** das memorias novas. 70.4% da base empresa nunca passou por revisao humana (era 65.7% em 06-22). O gate de revisao (R2 recorrente) segue sem implementacao.

---

## Health Score — 86/100

| Dimensao | Peso | Valor | Score | Contrib | vs 06-22 |
|----------|------|-------|-------|---------|----------|
| Eficacia media | 30% | 0.812 (>=0.7) | 100% | **30.0** | = (era ponderada 0.782) |
| Taxa cold | 20% | 12.59% | 93.5% | **18.7** | +1.0 (cold count cravado, base cresceu) |
| Stale 60d | 20% | 2.59% (<5%) | 100% | **20.0** | = |
| KG coverage | 15% | 28.8% | 14.7% | **2.2** | **-1.2 (33.6%->28.8%)** |
| Correcoes | 15% | 0.382 (<0.5) | 100% | **15.0** | = (mas margem encolhendo) |
| **TOTAL** | | | | **85.9 ≈ 86** | **+0** |

Nota: usei `avg_efficacy_real` (media simples das taxas por memoria = 0.812). A versao **ponderada por uso** continua mais baixa (~0.78, follow-up #3) — ambas >0.7, dimensao a 100%. O score "verdadeiro" considerando KG morto + 70% empresa sem revisao seria ~80; o framework de pesos nao captura a paralisia do pipeline.

---

## Recomendacoes Acionaveis

1. **[R1 — P0, follow-up #4 — 3o ciclo CRAVADO] Pipeline entity->memory linking esta MORTO.** `memorias_com_entidade`=245 e `total_relacoes`=7808 identicos a 06-22 e 06-15. Acao: verificar status do worker/job de extracao de entidades (provavel falha silenciosa ou flag OFF), e rodar **backfill de linking sobre as ~605 memorias sem entidade** (850-245). Sem isto, KG coverage continuara caindo a cada ciclo so por diluicao. **Esta e a unica recomendacao que move o health para 87+.**

2. **[R2 — P1, 11o ciclo] 70.4% das memorias empresa (269/382) nunca revisadas — RECORDE.** Divida 1:1 com crescimento (NULL subiu +53 = +53 novas). Acao: implementar **gate de revisao** que marque `reviewed_at` na promocao a empresa, ou batch de revisao das 269. Recorrente desde 04-13.

3. **[R3 — P1] Deletar de vez `_archived_...presigned-url-s3` (4x arquivada, u23, efic 0).** Renomear nao desliga a injecao — 7o ciclo em uso. Tambem auditar `diagnostico-de-regressao-sem-historico-git` (empresa, u32, **0 effective em 32 usos**) — candidata a delecao ou reescrita.

4. **[R4 — P1, follow-up #3] Saturacao da metrica de eficacia.** 16 memorias usage>=10/efic<0.1, lideradas por heuristicas always-on (`protocolo-ativo` u172, `integracao-nf` u108, `confirmar-pedido` u81). `effective_count` e cego para governanca always-on. Bloqueado ate o judge calibrado (follow-up #1). Quando ele existir: segmentar relatorio (governanca vs conhecimento citavel).

5. **[R5 — P2 — NOVO GATILHO] Correcoes em `structural/pessoal` rompeu o threshold local: 0.87** (0.49->0.73->0.87, 3a alta). Ainda mascarado pela media global (0.38<0.5=100%), mas se o ritmo seguir, a dimensao Correcoes comeca a sangrar pontos em ~2 ciclos. Vigiar a origem das correcoes (memorias pessoais aprendidas que o usuario corrige repetidamente).

6. **[R6 — P2] Podar entidades orfas mono-mencao no KG: 1626 orfas (42.6%).** Catalogo morto de cliente/produto/transportadora (mono-mencao, 0 link). A poda iniciada em 06-15 PAROU (entidades 3803->3815, +12). Retomar poda das orfas para limpar o grafo antes/depois do backfill de R1.

7. **[R7 — P3] Custo concentrado em 4 usuarios (~50% do gasto/mes).** Rafael+Marcus+Rayssa+Sabrina ~US$1013. Sem acao imediata — apenas monitorar (uso pesado legitimo: dev + financeiro + Assai).

---

## Comparacao com Ciclo Anterior (06-22 -> 06-29)

| Metrica | 06-22 | 06-29 | Delta |
|---------|-------|-------|-------|
| Health Score | 86 | 86 | +0 |
| Memorias | 730 | 850 | +120 (+16.4%) |
| Sessoes | 948 | 1019 | +71 |
| Usuarios (total) | 30 | 31 | +1 |
| Cold | 107 (14.66%) | 107 (12.59%) | count cravado, rate -2.1pp |
| Stale 60d | 19 (2.6%) | 22 (2.59%) | +3, rate estavel |
| KG coverage | 33.6% | **28.8%** | **-4.8pp** |
| Memorias linkadas | 245 | **245** | **CRAVADO (3o ciclo)** |
| Relacoes KG | 7808 | **7808** | **CRAVADO** |
| Entidades | 3803 | 3815 | +12 (poda parada) |
| Empresa total | 329 | 382 | +53 |
| Empresa never_reviewed | 216 (65.7%) | **269 (70.4%)** | RECORDE |
| Eficacia (simples) | ~0.95 | 0.812 | metrica recalibrada* |
| Correcoes (global) | 0.314 | 0.382 | +0.068 (2a alta) |

\* Leituras anteriores reportaram tanto media simples (~0.95) quanto ponderada (0.78); aqui o valor exato e 0.812 (simples). Ambas seguem >0.7.

**Veredito**: ciclo de crescimento saudavel em USO mascarando **paralisia em MANUTENCAO**. O health 86 e tecnicamente honesto pelos pesos, mas o sistema acumula duas dividas estruturais (KG morto + empresa sem revisao) que o framework atual nao penaliza. R1 (backfill linking) e a alavanca de maior ROI.

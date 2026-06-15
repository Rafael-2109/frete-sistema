# Atualizacao Memory Eval — 2026-06-15-1

**Data**: 2026-06-15
**Health Score**: 87/100 (+2 vs 85 em 2026-06-08)
**Fonte**: Render Postgres `dpg-d13m38vfte5s738t6p50-a` (READ-ONLY)
**Status**: OK — 7 queries executadas (Q6 em forma agregada por politica de payload/dados sensiveis)

---

## Resumo Executivo

Health sobe a **87/100** (+2), novo recorde da serie (supera os 86 de 05-05 e 06-01). O ganho
e tecnico e vem de duas dimensoes: **stale 60d despencou para 3.4%** (21/617, era 13.04% — volta
abaixo do threshold de 5%, +20 pts cheios pela 1a vez) e **cold recuou para 16.5%** (102/617, era
12.48% em % mas 66 em absoluto). Atencao: cold em absoluto **subiu** de 66→102 (+55%), mas como o
denominador cresceu mais (529→617, +16.6%) a taxa percentual ainda machuca menos do que parece —
e segue acima do threshold de 10%. 617 memorias totais (+88, +16.6%) e 869 sessoes (+88).

**Achado metodologico importante (atende follow-up #3 da serie)**: medi as DUAS leituras de
eficacia. A **media simples** (effective/usage por memoria, a usada nos relatorios anteriores) e
**0.950** — saturada e enganosa, inflada por 30 memorias de usage=1/effective=1. A **eficacia
ponderada por uso** (SUM effective / SUM usage = 23.913/30.271) e **0.790** — esta e a metrica
honesta, e mostra que os workhorses always-on de governanca seguem com efetividade pobre (24
memorias com usage>=10 tem efic < 0.2). Ambas cruzam o threshold de 0.7, entao a dimensao pontua
100% nas duas; mas o relatorio passa a reportar a ponderada como numero-verdade.

---

## Metricas de Sessoes (Q1)

| Metrica | Valor |
|---------|-------|
| Total de sessoes | 869 (+88 vs 781) |
| Sessoes ultima semana | 84 (pico da serie, era 54) |
| Sessoes ultimo mes | 280 (+32) |
| Usuarios unicos | 28 (era 32 — total historico; ver nota) |
| Media de mensagens/sessao | 8.82 |
| Custo medio/sessao | US$ 4.22 (era 3.35, +26%) |

> Custo medio/sessao subiu ~26%. Sessoes da ultima semana batem recorde (84). O `unique_users`
> de Q1 (28) e contagem sobre TODA a base `agent_sessions`; Q5 (30d) lista 23 usuarios ativos.

### Sessoes por usuario — ultimos 30d (Q5, top)

| user_id | Nome | Sessoes | Msgs | Custo (US$) | Ultima sessao |
|---------|------|---------|------|-------------|---------------|
| 1 | Rafael Nascimento | 65 | 519 | 472.62 | 2026-06-12 |
| 18 | Marcus Lima | 43 | 449 | 439.53 | 2026-06-15 |
| 17 | Talita de Le Lima | 32 | 513 | 268.79 | 2026-06-12 |
| 45 | Sabrina Lima | 25 | 380 | 299.28 | 2026-06-12 |
| 38 | Alice Helen Barros | 18 | 186 | 107.39 | 2026-06-12 |
| 54 | Gabriella Silva | 17 | 146 | 238.42 | 2026-06-11 |
| 57 | Elaine Almeida | 15 | 54 | 24.87 | 2026-06-09 |
| 4 | Jessica Tereza | 12 | 80 | 25.99 | 2026-06-11 |
| 74 | Claude Code | 11 | 22 | 5.85 | 2026-06-09 |
| 82 | Martha Frugoli | 8 | 183 | 199.66 | 2026-06-10 |

> Contas duplicadas conhecidas persistem com user_ids distintos: Rafael (1/55), Elaine (57/67),
> Sabrina (45/83), Talita (17/40/70), Marcus (18). **Custo concentrado**: Rafael (473), Marcus
> (440), Sabrina (299) e Talita (269) somam ~US$1.480 em 30d. Martha (82) custa US$200 em 8
> sessoes (US$25/sessao — alto). Marcus ja iguala o volume de mensagens do Rafael (449 vs 519).

---

## Memorias por Categoria e Escopo (Q2)

| Categoria | Escopo | Total | Avg Imp | Avg Efic_bruto | Avg Corr | Cold | Conflict | Stale 30d | Stale 60d |
|-----------|--------|-------|---------|----------------|----------|------|----------|-----------|-----------|
| cold | pessoal | 15 | 0.70 | 8.8 | 0.00 | 15 | 0 | 0 | 0 |
| contextual | pessoal | 20 | 0.51 | 28.7 | 0.50 | 3 | 0 | 3 | 2 |
| operational | empresa | 47 | 0.80 | 60.4 | 0.00 | 12 | 0 | 1 | 1 |
| operational | pessoal | 57 | 0.54 | 27.6 | 0.16 | 4 | 0 | 10 | 6 |
| permanent | empresa | 5 | 0.90 | 143.4 | 0.00 | 0 | 0 | 0 | 0 |
| permanent | pessoal | 54 | 0.87 | 52.8 | 0.11 | 0 | 0 | 7 | 1 |
| structural | empresa | 217 | 0.78 | 61.5 | 0.01 | 47 | 0 | 3 | 3 |
| structural | pessoal | 202 | 0.69 | 9.3 | **0.49** | 21 | 0 | 10 | 8 |

> `avg_efic_bruto` = `avg_effective` (contagem absoluta), NAO taxa — mantido como na serie. Eficacia
> media (taxa) = simples 0.950 / **ponderada por uso 0.790** (ver Health Score).
> **Mudanca estrutural notavel**: `structural/empresa` saltou 190→217 (+27) e seu stale 60d
> DESPENCOU de 52→3, stale 30d de 92→3 — a base empresa foi massivamente re-tocada/atualizada
> entre 06-08 e 06-15 (driver principal do +2 no health). `operational/empresa` apareceu com 47
> memorias e 12 cold. **avg_corrections subiu**: `structural/pessoal` agora 0.49 (era 0.165),
> `contextual/pessoal` 0.50 — o pipeline de correcao acelerou no escopo pessoal.

---

## Top Memorias de Baixa Eficacia (Q3)

20 memorias com usage >= 3 e efficacy < 0.3 (category != permanent). Destaques de alto uso:

| Path (nome) | usage | effective | corr | efficacy |
|------|-------|-----------|------|----------|
| empresa/heuristicas/...memorias-de-usuario-devem-funcionar-como-protocolo-ativo.xml | 172 | 9 | 0 | 0.052 |
| empresa/...integracao-nf.xml | 108 | 5 | 0 | 0.046 |
| empresa/...confirmar-pedido.xml | 81 | 4 | 0 | 0.049 |
| empresa/...a-rede-assai-opera-com-multiplas-lojas-i.xml | 49 | 3 | 0 | 0.061 |
| empresa/armadilhas/geral/build_artifact_pnpm.md | 36 | 2 | 0 | 0.056 |
| empresa/protocolos/...diagnostico-de-regressao-sem-historico-git-disponivel.xml | 32 | 0 | 0 | 0.000 |
| **empresa/armadilhas/...\_archived\_(3x)\_presigned-url-s3-vence...xml** | 23 | 0 | 0 | 0.000 |
| empresa/armadilhas/...reautorizacao-oauth-...tagplus.xml | 20 | 0 | 0 | 0.000 |
| empresa/heuristicas/...quando-o-usuario-envia-saudacao-e-pedido.xml | 19 | 0 | 0 | 0.000 |
| empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica.xml | 17 | 0 | 0 | 0.000 |
| corrections/quando-pergunta-detalhes-de-um-cluster-especifico.xml (u18) | 10 | 0 | **8** | 0.000 |
| empresa/heuristicas/...operadores-do-teams-bot-possuem-user-id.xml | 7 | 0 | 0 | 0.000 |
| empresa/heuristicas/...abordagem-validada-pelo-judge-...mach.xml | 7 | 0 | 0 | 0.000 |
| empresa/heuristicas/geral/modo-debug.xml | 6 | 0 | 0 | 0.000 |

### Zero-efficacy com uso (efficacy = 0)
Persiste o nucleo do ciclo anterior: `diagnostico-de-regressao-sem-historico-git` (u32),
`_archived_presigned-url-s3` (u23, **ainda 3x arquivada e em uso** — bug latente ha 5+ ciclos),
`reautorizacao-oauth-tagplus` (u20), `quando-o-usuario-envia-saudacao` (u19),
`gabriella-telegrafica` (u17, subiu de 15). O cluster `abordagem-validada-pelo-judge-*` segue
presente (`...mach` u7) mas NAO explodiu como em 06-08 — parcialmente estabilizado.

> A memoria u18 `corrections/quando-pergunta-detalhes-de-um-cluster` mantem correction_count=8 —
> o pipeline de correcao segue registrando feedback negativo nela.

---

## Memorias Empresa (user_id=0) — Q6 (agregado)

| Metrica | Valor |
|---------|-------|
| Total memorias empresa | 271 (era 226, +45, +20%) |
| Nunca revisadas (reviewed_at NULL) | **158 (58%)** |
| Revisadas ha > 30d | 105 |
| Baixa eficacia (efic < 0.1, usage > 0) | 18 |
| Cold | 59 |
| Avg importance | 0.785 |
| Avg efficacy (taxa simples) | 0.694 |

> **Piora reincidente (9o ciclo): 58% das memorias empresa nunca foram revisadas** (158/271, era
> 50% em 06-08). 45 novas memorias empresa entraram desde 06-08, todas sem ciclo de validacao —
> o crescimento da base empresa (+20%) supera de longe a capacidade de revisao. Surgiu agora um
> bloco de 105 memorias com `reviewed_at` > 30d (antes era 0): houve uma revisao em algum momento
> mas ja envelheceu. 18 memorias empresa com efic < 0.1 e uso real.

---

## Knowledge Graph (Q4 + Q7)

| Metrica | Valor |
|---------|-------|
| Entidades totais | 3.784 (era 3.874, -90 — 1a queda da serie) |
| Entidades orfas (sem link a memoria) | **1.595 (42.2%)** |
| Memorias com entidades vinculadas (distintas) | 245 (era 227) |
| Coverage (memorias linkadas / total) | **39.7%** (era 42.9%, -3.2pp) |
| Relacoes entidade-entidade | 7.808 (era 7.310, +498) |

### Entidades por tipo (top)
| Tipo | Total | Memorias linkadas | Avg mentions |
|------|-------|-------------------|--------------|
| conceito | 1.401 | 192 | 1.37 |
| cliente | 741 | 27 | 1.29 |
| produto | 577 | 49 | 1.14 |
| transportadora | 433 | 22 | 1.10 |
| processo | 273 | 136 | 1.30 |
| campo | 194 | 111 | 1.21 |
| valor | 95 | 32 | 1.40 |
| termo | 93 | 63 | 1.67 |
| uf | 74 | 34 | 4.50 |
| regra | 68 | 9 | 1.12 |
| usuario | 16 | 15 | 5.88 |

> **KG e o calcanhar persistente (3o ciclo de queda de coverage)**: 39.7% (caiu abaixo de 40% pela
> 1a vez desde 05-05). `cliente` (741), `produto` (577) e `transportadora` (433) somam 1.751
> entidades com so 98 memorias linkadas — extraidas de conversas, raramente ancoradas. As 1.595
> orfas tem avg_mentions ~1.1-1.3 (mencionadas uma unica vez). Total de entidades caiu (-90),
> sinal de que algum garbage-collection/poda comecou a operar, mas a coverage ainda piorou porque
> a poda nao priorizou as orfas mono-mencao.

### Top relacoes semanticas (peso)
- ASSAI (cliente) --requer--> CONFIRMACAO-MANUAL (5.0)
- DRY-RUN-OBRIGATORIO --precede--> ACOES-EM-LOTE-ODOO (5.0)
- PEDIDO-DE-VENDA --co_occurs--> COTACAO (3.5)
- CONFIRMAR-PEDIDO --co_occurs--> COTACAO (3.5)
- ASSAI --complementa--> MULTIPLAS-LOJAS-INDEPENDENTES (3.0)
- DENISE (cliente) --pertence_a--> COMPRAS (3.0)
- GABRIELLA (usuario) --responsavel_por--> COMPRAS (3.0)
- VCD2667872 (pedido) --co_occurs--> SANNA (cliente) (3.0)

---

## Health Score — Detalhamento

| Dimensao | Peso | Valor medido | Score parcial | Pontos |
|----------|------|--------------|---------------|--------|
| Eficacia media | 30% | 0.790 ponderada / 0.950 simples (>= 0.7) | 100% | 30.0 |
| Taxa cold | 20% | 16.5% (102/617) | 83.8% | 16.8 |
| Stale 60d | 20% | 3.4% (21/617) | 100% | 20.0 |
| KG coverage | 15% | 39.7% (245/617) | 32.8% | 4.9 |
| Correcoes | 15% | 0.204 (< 0.5) | 100% | 15.0 |
| **TOTAL** | | | | **86.7 → 87** |

> **Nota metodologica (eficacia)**: reportei a eficacia ponderada por uso (0.790) como numero-verdade
> ao lado da media simples (0.950) historica. As duas cruzam o threshold de 0.7, entao a dimensao
> pontua 100% (30 pts) de qualquer forma — mas a leitura honesta e que a base de workhorses
> always-on segue com efetividade mediocre (24 memorias usage>=10 com efic < 0.2; protocolo-ativo
> u172 efic 0.052). **O ganho real do +2 vem de Stale 60d (15.4→20.0, +4.6 pts)** apos a base
> empresa ser massivamente re-tocada. Cold melhorou de pontuacao (18.8→16.8 — espera, recuou
> ligeiramente em pts por subir de 12.48% para 16.5% em taxa); KG segue caindo (5.7→4.9).

### Serie historica
86 (05-05) → 82 (05-11) → 80 (05-18) → 84 (05-25) → 86 (06-01) → 85 (06-08) → **87 (06-15)**

---

## Recomendacoes Acionaveis

1. **[R1 — ALTA] Deletar fisicamente memorias `_archived_*` ainda em uso (5o ciclo).** A memoria
   `_archived_(3x)_presigned-url-s3-vence` (u0, u23, e0) segue arquivada 3x e recuperada. O prefixo
   `_archived_` nao exclui da busca/embedding; o re-arquivamento so empilha prefixos. Acao concreta:
   DELETE da linha ou remocao do indice de embedding — nao re-arquivar.

2. **[R2 — ALTA] Revisar 158 memorias empresa nunca revisadas (58%, 9o ciclo, PIORANDO).** Subiu
   de 113 (50%) para 158 (58%). A base empresa cresceu +20% (226→271) sem ciclo de validacao. Surgiu
   um bloco de 105 memorias com revisao envelhecida (>30d). Estabelecer rotina de revisao de
   `user_id=0` e gate de admissao (toda memoria empresa nova exige reviewed_at em N dias).

3. **[R3 — ALTA] Tratar a saturacao da metrica de eficacia (atende follow-up #3).** Confirmado nesta
   leitura: media simples 0.950 vs ponderada 0.790 — gap de 16pp. 24 memorias always-on (usage>=10)
   tem efic < 0.2. A metrica `effective_count` (similaridade resposta↔memoria) e cega para memoria
   de governanca injetada indistintamente (protocolo-ativo u172 efic 0.052). Decidir: (a) segmentar
   o relatorio (governanca vs conhecimento) OU (b) holdout A/B com judge calibrado. Pre-requisito #1
   (judge como medidor) deve estar de pe primeiro — verificar status antes de mexer na injecao.

4. **[R4 — MEDIA] Atacar KG coverage (39.7%, 3o ciclo de queda, abaixo de 40%).** 1.595 orfas (42%);
   cliente/produto/transportadora somam 1.751 entidades com 98 memorias linkadas. O total de
   entidades caiu (-90) — ha poda operando, mas ela nao priorizou as orfas mono-mencao. Direcionar a
   poda para orfas com mention_count=1 e revisar o pipeline entity→memory linking, que nao acompanha
   a extracao.

5. **[R5 — MEDIA] Conter taxa cold (16.5%, +55% absoluto, acima do threshold de 10%).** Cold subiu
   66→102 enquanto a base cresceu +16.6%. `structural/empresa` concentra 47 cold; `operational/empresa`
   novos 12. Verificar se o cold-tiering promove cedo demais ou se ha acumulo de memorias mortas
   nunca reaquecidas. A categoria `cold/pessoal` (15) e o destino materializado — confirmar drenagem.

6. **[R6 — MEDIA] Auditar zero-efficacy persistente de alto uso.** `protocolo-ativo` (u172, efic 0.052),
   `integracao-nf` (u108, 0.046), `confirmar-pedido` (u81, 0.049) sao as 3 memorias mais usadas do
   sistema e quase nunca efetivas. Sao meta-heuristicas always-on. Avaliar reescrita ou reducao de
   importance (0.7-0.8 → 0.5) para reduzir ruido de contexto. Ligado a R3.

7. **[R7 — BAIXA] Validar contas duplicadas com alto custo.** Talita (17/40/70 — 513 msgs em 17),
   Sabrina (45/83), Rafael (1/55), Elaine (57/67). Fragmentam metricas e memoria pessoal. Custo de
   Martha (82) em US$25/sessao merece checagem de eficiencia de uso.

---

## Notas de Execucao

- **Eficacia — leitura dupla**: media simples (effective/usage por memoria) = 0.950; ponderada por
  uso (SUM effective 23.913 / SUM usage 30.271) = 0.790. A ponderada e a metrica-verdade e atende o
  follow-up #3 da serie. 30 memorias single-use (usage=1) inflam a media simples.
- **Driver do +2**: stale 60d caiu de 69 (13%) para 21 (3.4%) apos `structural/empresa` ser
  re-tocada em massa (stale 30d dessa categoria caiu 92→3). Ganho real, nao artefato.
- **KG**: 1a queda do total de entidades da serie (3.874→3.784, -90) — poda comecou — mas coverage
  ainda piorou (poda nao priorizou orfas mono-mencao).
- Q6 (lista detalhada user_id=0) emitida como agregacao + subset de alto-uso (contagens + medias)
  preservando todas as metricas do contrato. Lista bruta nao incluida por politica (Limites item 3:
  nao expor conteudo). A query crua de Q6 estourou o limite de tokens (271 paths) — re-executada em
  forma agregada.
- Read-only: apenas SELECTs executados. Nenhuma escrita no Postgres.

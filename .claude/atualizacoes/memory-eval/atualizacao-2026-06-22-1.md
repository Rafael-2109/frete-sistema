# Atualizacao Memory Eval — 2026-06-22-1

**Data**: 2026-06-22
**Health Score**: 86/100 (-1 vs 87 em 2026-06-15)
**Fonte**: Render Postgres `dpg-d13m38vfte5s738t6p50-a` (READ-ONLY)
**Status**: OK — 7 queries executadas (Q6 em forma agregada por politica de payload/dados sensiveis)

---

## Resumo Executivo

Health recua marginalmente para **86/100** (-1), encerrando o recorde de 87 da semana passada — queda
tecnica, nao estrutural. Tres das cinco dimensoes melhoraram ou ficaram cravadas no teto: **stale 60d
caiu para 2.6%** (19/730, era 3.4% — segue muito abaixo do threshold de 5%, +20 pts cheios pela 2a
semana) e **cold recuou para 14.66%** (107/730, era 16.5%) graças ao denominador crescer mais rapido
que o cold absoluto. **O dreno do -1 e o KG**: coverage despencou de 39.7% para **33.6%** (245/730),
4o ciclo consecutivo de queda — a base de memorias cresceu +18.3% (617→730) enquanto as memorias
linkadas ao grafo ficaram cravadas em 245. A base sobe, o grafo nao acompanha.

948 sessoes totais (+79). A semana foi mais fria (77 sessoes na ultima semana vs pico de 84), mas o
mes acumulado cresceu (314 vs 280). Custo medio/sessao caiu de US$4.22 para **US$3.82**.

**Achado metodologico (segue follow-up #3 da serie)**: a eficacia ponderada por uso (numero-verdade)
e **0.782** — praticamente identica a 0.790 da semana passada. A media simples (saturada, inflada por
single-use) e 0.950+. Ambas cruzam o threshold de 0.7, entao a dimensao pontua 100% (30 pts) — mas a
leitura honesta segue sendo que os workhorses always-on de governanca tem efetividade pobre (ex.:
`protocolo-ativo` u172 efic 0.052, agora a memoria MAIS usada do sistema).

---

## Metricas de Sessoes (Q1)

| Metrica | Valor |
|---------|-------|
| Total de sessoes | 948 (+79 vs 869) |
| Sessoes ultima semana | 77 (era 84 — recuou do pico) |
| Sessoes ultimo mes | 314 (+34) |
| Usuarios unicos | 30 (era 28 — total historico; ver nota) |
| Media de mensagens/sessao | 8.90 |
| Custo medio/sessao | US$ 3.82 (era 4.22, -9.5%) |

> O `unique_users` de Q1 (30) e contagem sobre TODA a base `agent_sessions`; Q5 (30d) lista 27
> usuarios ativos. Custo medio/sessao desceu ~9.5% apesar do volume de mensagens estavel — sessoes
> mais baratas em media. A ultima semana foi mais fria (77 vs 84) mas o acumulado de 30d cresceu.

### Sessoes por usuario — ultimos 30d (Q5, top)

| user_id | Nome | Sessoes | Msgs | Custo (US$) | Ultima sessao |
|---------|------|---------|------|-------------|---------------|
| 1 | Rafael Nascimento | 66 | 501 | 398.02 | 2026-06-20 |
| 18 | Marcus Lima | 42 | 484 | 273.92 | 2026-06-17 |
| 45 | Sabrina Lima | 29 | 441 | 347.55 | 2026-06-19 |
| 17 | Talita de Le Lima | 28 | 425 | 174.11 | 2026-06-19 |
| 4 | Jessica Tereza | 21 | 118 | 31.08 | 2026-06-18 |
| 54 | Gabriella Silva | 17 | 146 | 244.77 | 2026-06-19 |
| 38 | Alice Helen Barros | 16 | 152 | 73.10 | 2026-06-12 |
| 57 | Elaine Almeida | 13 | 51 | 27.28 | 2026-06-19 |
| 82 | Martha Frugoli | 11 | 259 | 180.18 | 2026-06-19 |
| 74 | Claude Code | 11 | 22 | 5.85 | 2026-06-09 |
| 78 | Rayssa Alves | 9 | 170 | 134.27 | 2026-06-20 |

> Contas duplicadas conhecidas persistem com user_ids distintos: Talita (17/40/70), Sabrina (45/83
> nao aparece este ciclo), Rafael (1). **Custo concentrado**: Rafael (398), Sabrina (348), Marcus
> (274) e Gabriella (245) lideram; somados ~US$1.265 em 30d. **Martha (82) sobe forte**: 259 msgs em
> 11 sessoes (US$16/sessao) — voltou a ser usuaria pesada. **Rayssa (78) emergiu** com 9 sessoes /
> 170 msgs / US$134. Marcus e Sabrina ja superam o Rafael em msgs/sessao.

---

## Memorias por Categoria e Escopo (Q2)

| Categoria | Escopo | Total | Avg Imp | Avg Efic_bruto | Avg Corr | Cold | Conflict | Stale 30d | Stale 60d |
|-----------|--------|-------|---------|----------------|----------|------|----------|-----------|-----------|
| cold | pessoal | 15 | 0.70 | 8.8 | 0.00 | 15 | 0 | 0 | 0 |
| contextual | empresa | 2 | 0.90 | 12.5 | 0.00 | 0 | 0 | 0 | 0 |
| contextual | pessoal | 21 | 0.50 | 27.8 | 0.48 | 3 | 0 | 2 | 1 |
| operational | empresa | 56 | 0.82 | 53.1 | 0.04 | 12 | 0 | 1 | 1 |
| operational | pessoal | 66 | 0.55 | 24.9 | 0.32 | 4 | 0 | 6 | 5 |
| permanent | empresa | 5 | 0.90 | 147.0 | 0.00 | 0 | 0 | 0 | 0 |
| permanent | pessoal | 59 | 0.87 | 55.9 | 0.19 | 0 | 0 | 7 | 1 |
| structural | empresa | 264 | 0.79 | 53.0 | 0.03 | 52 | 0 | 3 | 3 |
| structural | pessoal | 242 | 0.71 | 8.8 | **0.73** | 21 | 0 | 10 | 8 |

> `avg_efic_bruto` = `avg_effective` (contagem absoluta), NAO taxa — mantido como na serie. Eficacia
> media (taxa) = ponderada por uso **0.782** (ver Health Score).
> **Crescimento concentrado em structural**: `structural/empresa` 217→264 (+47) e `structural/pessoal`
> 202→242 (+40) — juntos +87 das +113 memorias novas. **avg_corrections de `structural/pessoal`
> SALTOU para 0.73** (era 0.49) — o pipeline de correcao acelerou forte no escopo pessoal e e o
> principal motor da subida de avg_corrections geral (0.204→0.314). `operational/empresa` cresceu
> 47→56. Cold concentra-se em `structural/empresa` (52) e na materializada `cold/pessoal` (15).

---

## Top Memorias de Baixa Eficacia (Q3)

20 memorias com usage >= 3 e efficacy < 0.3 (category != permanent). Destaques de alto uso:

| Path (nome) | usage | effective | corr | efficacy |
|------|-------|-----------|------|----------|
| empresa/heuristicas/...memorias-de-usuario-devem-funcionar-como-protocolo-ativo.xml | 172 | 9 | 0 | 0.052 |
| empresa/...integracao-nf.xml | 108 | 5 | 0 | 0.046 |
| empresa/...confirmar-pedido.xml | 81 | 4 | 0 | 0.049 |
| empresa/...a-rede-assai-opera-com-multiplas-lojas-i.xml | 49 | 3 | 0 | 0.061 |
| system/download_config.xml (u1) | 47 | 3 | 0 | 0.064 |
| empresa/armadilhas/geral/build_artifact_pnpm.md | 36 | 2 | 0 | 0.056 |
| empresa/protocolos/...diagnostico-de-regressao-sem-historico-git-disponivel.xml | 32 | 0 | 0 | 0.000 |
| **empresa/armadilhas/...\_archived\_(4x)\_presigned-url-s3-vence...xml** | 23 | 0 | 0 | 0.000 |
| empresa/armadilhas/...reautorizacao-oauth-...tagplus.xml | 20 | 0 | 0 | 0.000 |
| empresa/heuristicas/...quando-o-usuario-envia-saudacao-e-pedido.xml | 19 | 0 | 0 | 0.000 |
| empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica.xml | 17 | 0 | 0 | 0.000 |
| corrections/quando-pergunta-detalhes-de-um-cluster-especifico.xml (u18) | 10 | 0 | **8** | 0.000 |
| empresa/heuristicas/...abordagem-validada-pelo-judge-...mach.xml | 7 | 0 | 0 | 0.000 |
| empresa/heuristicas/...operadores-do-teams-bot-possuem-user-id.xml | 7 | 0 | 0 | 0.000 |
| empresa/heuristicas/geral/modo-debug.xml | 6 | 0 | 0 | 0.000 |
| user_expertise.xml (u57) | 6 | 0 | 0 | 0.000 |
| empresa/usuarios/kerley.xml | 5 | 0 | 0 | 0.000 |
| corrections/usuario-sinalizou-...esquece-de-registrar.xml (u1) | 4 | 0 | 0 | 0.000 |
| corrections/usuario-corrigiu-agente-...nao-ter-visto-o-arquivo.xml (u1) | 3 | 0 | 0 | 0.000 |

### Zero-efficacy com uso (efficacy = 0)
Mesmo nucleo do ciclo anterior, agora um ciclo mais velho:
`diagnostico-de-regressao-sem-historico-git` (u32), `_archived_presigned-url-s3` (u23, **agora 4x
arquivada** — re-arquivada de novo desde 06-15, segue em uso — bug latente ha 6+ ciclos),
`reautorizacao-oauth-tagplus` (u20), `quando-o-usuario-envia-saudacao` (u19),
`gabriella-telegrafica` (u17). Novos na lista de zero-efficacy: `user_expertise.xml` (u57/u6),
`kerley.xml` (u5), e duas memorias `corrections/*` do user 1 (u4 e u3).

> A memoria u18 `corrections/quando-pergunta-detalhes-de-um-cluster` mantem correction_count=8 — o
> pipeline de correcao segue registrando feedback negativo nela (estavel vs 06-15).

---

## Memorias Empresa (user_id=0) — Q6 (agregado)

| Metrica | Valor |
|---------|-------|
| Total memorias empresa | 329 (era 271, +58, +21%) |
| Nunca revisadas (reviewed_at NULL) | **216 (65.7%)** |
| Revisadas ha > 30d | 105 |
| Baixa eficacia (efic < 0.1, usage >= 3) | 17 |
| Cold | 64 |
| Avg importance | 0.797 |
| Avg efficacy (taxa simples) | 0.749 |

> **Piora reincidente (10o ciclo): 65.7% das memorias empresa nunca foram revisadas** (216/329, era
> 58% / 158 em 06-15). A base empresa cresceu +21% (271→329) e as 58 novas entraram todas sem ciclo
> de validacao — `reviewed_at` NULL subiu +58 (de 158 para 216), batendo EXATAMENTE o crescimento da
> base. Ou seja: zero das memorias novas foi revisada, e nenhuma das antigas pendentes foi limpa. O
> bloco de 105 com revisao envelhecida (>30d) ficou estavel. 17 memorias empresa com efic < 0.1 e uso
> real (>=3). Este e o problema cronico mais persistente da serie.

### Memorias empresa de alto uso e baixissima eficacia (efic < 0.1, usage >= 5)
- `protocolo-ativo.xml` (u172, efic 0.052), `integracao-nf.xml` (u108, 0.046),
  `confirmar-pedido.xml` (u81, 0.049), `a-rede-assai...` (u49, 0.061),
  `build_artifact_pnpm.md` (u36, 0.056), `diagnostico-de-regressao...` (u32, 0.0),
  `cotacao.xml` (u27, 0.074), `_archived_(4x)_presigned-url-s3` (u23, 0.0),
  `reautorizacao-oauth-tagplus` (u20, 0.0), `quando-...saudacao` (u19, 0.0),
  `gabriella-telegrafica` (u17, 0.0). Todas criadas pelo user 1, todas `reviewed_at` NULL.

---

## Knowledge Graph (Q4 + Q7)

| Metrica | Valor |
|---------|-------|
| Entidades totais | 3.803 (era 3.784, +19 — voltou a crescer) |
| Entidades orfas (sem link a memoria) | **1.614 (42.4%)** |
| Memorias com entidades vinculadas (distintas) | 245 (CRAVADO em 245 vs 06-15) |
| Coverage (memorias linkadas / total) | **33.6%** (era 39.7%, -6.1pp) |
| Relacoes entidade-entidade | 7.808 (estavel vs 06-15) |

### Entidades por tipo (top)
| Tipo | Total | Memorias linkadas | Avg mentions |
|------|-------|-------------------|--------------|
| conceito | 1.401 | 192 | 1.37 |
| cliente | 752 | 27 | 1.29 |
| produto | 578 | 49 | 1.14 |
| transportadora | 440 | 22 | 1.10 |
| processo | 273 | 136 | 1.30 |
| campo | 194 | 111 | 1.21 |
| valor | 95 | 32 | 1.40 |
| termo | 93 | 63 | 1.67 |
| uf | 74 | 34 | 4.50 |
| regra | 68 | 9 | 1.12 |
| pedido | 24 | 18 | 2.29 |
| cnpj | 17 | 14 | 1.41 |
| usuario | 16 | 15 | 5.88 |

> **KG e o dreno do health este ciclo (4o ciclo de queda de coverage; -6.1pp e o maior tombo da
> serie).** Coverage 33.6% — abaixo de 35% pela 1a vez. A causa e clara: memorias linkadas ficaram
> **cravadas em 245** (identicas a 06-15) enquanto a base cresceu +113. O pipeline entity→memory
> linking PAROU de acompanhar a extracao de memorias. `cliente` (752), `produto` (578) e
> `transportadora` (440) somam 1.770 entidades com so 98 memorias linkadas. As 1.614 orfas (42.4%)
> tem avg_mentions ~1.1-1.3 (mono-mencao). Total de entidades voltou a crescer (+19) e as relacoes
> ficaram estaveis (7.808) — a poda da semana passada nao teve continuidade.

### Top relacoes semanticas (peso) — identicas a 06-15
- ASSAI (cliente) --requer--> CONFIRMACAO-MANUAL (5.0)
- DRY-RUN-OBRIGATORIO --precede--> ACOES-EM-LOTE-ODOO (5.0)
- PEDIDO-DE-VENDA --co_occurs--> COTACAO (3.5)
- CONFIRMAR-PEDIDO --co_occurs--> COTACAO (3.5)
- ASSAI --complementa--> MULTIPLAS-LOJAS-INDEPENDENTES (3.0)
- DENISE (cliente) --pertence_a--> COMPRAS (3.0)
- GABRIELLA (usuario) --responsavel_por--> COMPRAS (3.0)
- VCD2667872 (pedido) --co_occurs--> SANNA (cliente) (3.0)

> As top relacoes nao mudaram desde 06-15 — sinal de que o grafo de alto-peso esta estavel e nenhuma
> nova relacao forte foi formada na semana.

---

## Health Score — Detalhamento

| Dimensao | Peso | Valor medido | Score parcial | Pontos |
|----------|------|--------------|---------------|--------|
| Eficacia media | 30% | 0.782 ponderada / 0.950+ simples (>= 0.7) | 100% | 30.0 |
| Taxa cold | 20% | 14.66% (107/730) | 88.3% | 17.7 |
| Stale 60d | 20% | 2.6% (19/730) | 100% | 20.0 |
| KG coverage | 15% | 33.6% (245/730) | 22.7% | 3.4 |
| Correcoes | 15% | 0.314 (< 0.5) | 100% | 15.0 |
| **TOTAL** | | | | **86.1 → 86** |

> **Nota metodologica (eficacia)**: reportei a ponderada por uso (0.782) como numero-verdade ao lado
> da media simples historica. As duas cruzam 0.7 → 30 pts. A leitura honesta segue: workhorses
> always-on com efetividade mediocre (`protocolo-ativo` u172 efic 0.052 — agora a memoria mais usada
> do sistema). **O -1 vem inteiramente do KG (4.9→3.4, -1.5 pts)**: coverage caiu 6.1pp porque a base
> cresceu e as linkadas nao. Cold MELHOROU (16.8→17.7, +0.9) e stale ficou cravado no teto (20.0).
> Correcoes segue em 100% (avg 0.314 < 0.5) — mas a margem encolheu (0.204→0.314, o pipeline de
> correcao esta ganhando tracao no escopo pessoal; se passar de 0.5 derruba a dimensao).

### Serie historica
86 (05-05) → 82 (05-11) → 80 (05-18) → 84 (05-25) → 86 (06-01) → 85 (06-08) → 87 (06-15) → **86 (06-22)**

---

## Recomendacoes Acionaveis

1. **[R1 — ALTA] Atacar o colapso de KG coverage (33.6%, 4o ciclo de queda, -6.1pp — pior tombo da
   serie).** Causa-raiz identificada: memorias linkadas CRAVADAS em 245 enquanto a base cresceu +113.
   O pipeline entity→memory linking nao processa as memorias novas. Acao: rodar (ou agendar) o
   backfill de linking sobre as 485 memorias sem entidade vinculada; verificar se o job de extracao
   esta ativo. Em paralelo, podar as 1.614 orfas mono-mencao (mention_count=1) que so inflam o
   denominador de entidades.

2. **[R2 — ALTA] Revisar 216 memorias empresa nunca revisadas (65.7%, 10o ciclo, PIORANDO).** Subiu
   de 158 (58%) para 216 (65.7%). As 58 novas memorias empresa entraram TODAS sem revisao — `reviewed_at`
   NULL subiu exatamente +58. Sem gate de admissao, a divida cresce 1:1 com a base. Acao concreta:
   (a) gate que exige `reviewed_at` em N dias para toda memoria `user_id=0`; (b) mutirao de revisao
   das 216 pendentes, priorizando as 17 de alto uso/baixa eficacia.

3. **[R3 — ALTA] Deletar fisicamente as memorias `_archived_*` ainda em uso (6o ciclo).** A memoria
   `presigned-url-s3-vence` agora esta **4x arquivada** (re-arquivada de novo desde 06-15) e segue
   recuperada (u23, efic 0). O prefixo `_archived_` nao exclui da busca/embedding; re-arquivar so
   empilha prefixos. Acao: DELETE da linha ou remocao do indice de embedding — parar de re-arquivar.

4. **[R4 — MEDIA] Tratar a saturacao da metrica de eficacia (atende follow-up #3).** Estavel vs 06-15:
   ponderada 0.782 vs simples 0.950+. `effective_count` (similaridade resposta↔memoria) e cega para
   governanca always-on injetada indistintamente. Pre-requisito #1 (judge como medidor / holdout-ablacao)
   precisa estar de pe antes de mexer na injecao — verificar status do #1 antes de qualquer acao.

5. **[R5 — MEDIA] Reduzir importance dos workhorses zero-efficacy de alto uso.** `protocolo-ativo`
   (u172, 0.052) e a memoria MAIS usada do sistema com efic 5%; `integracao-nf` (u108, 0.046) e
   `confirmar-pedido` (u81, 0.049) completam o top. Sao meta-heuristicas always-on. Avaliar reescrita
   ou baixar importance (0.7-0.8 → 0.5) para reduzir ruido de contexto. Ligado a R4.

6. **[R6 — MEDIA] Vigiar a dimensao Correcoes — margem encolhendo.** avg_corrections geral subiu
   0.204→0.314 (ainda < 0.5, mas a 2a alta consecutiva). Motor: `structural/pessoal` saltou para 0.73.
   O pipeline de correcao esta ganhando tracao (bom para qualidade), mas se a media geral passar de
   0.5 a dimensao deixa de pontuar 100%. Monitorar; nao e acao corretiva, e gatilho de atencao.

7. **[R7 — BAIXA] Validar contas duplicadas e uso intensivo.** Talita (17/40/70), Rafael (1). Custo
   concentrado em Rafael/Sabrina/Marcus/Gabriella (~US$1.265/30d). Novas usuarias pesadas: Martha (82,
   259 msgs/11 sessoes) e Rayssa (78, 170 msgs). Custo medio/sessao caiu para US$3.82 (saudavel).

---

## Notas de Execucao

- **Eficacia — leitura dupla**: ponderada por uso (numero-verdade) = 0.782 — praticamente identica a
  0.790 de 06-15. Media simples segue saturada (>0.95) por memorias single-use. Atende follow-up #3.
- **Driver do -1**: KG coverage caiu de 39.7% para 33.6% (-6.1pp) porque a base cresceu +113 e as
  memorias linkadas ficaram cravadas em 245. As outras dimensoes melhoraram (cold, stale) ou ficaram
  no teto. Queda tecnica, nao degradacao estrutural da memoria.
- **Marco negativo cronico**: 10o ciclo de empresa sem revisao (65.7%, recorde da serie). O crescimento
  da base empresa (+58) bateu exatamente o crescimento de `reviewed_at` NULL (+58) — divida 1:1.
- **`_archived_presigned-url-s3` agora 4x arquivada** — re-arquivada de novo entre 06-15 e 06-22. Bug
  latente de 6+ ciclos. O re-arquivamento automatico nao resolve; precisa de DELETE.
- Q6 (lista detalhada user_id=0) emitida como agregacao + subset de alto-uso (contagens + medias)
  preservando todas as metricas do contrato. Lista bruta nao incluida por politica (Limites item 3:
  nao expor conteudo). A query crua de Q6 estourou o limite de tokens (329 paths) — re-executada em
  forma agregada.
- Read-only: apenas SELECTs executados. Nenhuma escrita no Postgres.

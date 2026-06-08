# Atualizacao Memory Eval — 2026-06-08-1

**Data**: 2026-06-08
**Health Score**: 85/100 (-1 vs 86 em 2026-06-01)
**Fonte**: Render Postgres `dpg-d13m38vfte5s738t6p50-a` (READ-ONLY)
**Status**: OK — 7 queries executadas (Q6 em forma agregada por politica de payload/dados sensiveis)

---

## Resumo Executivo

Health recua marginalmente a **85/100** (-1), encerrando a serie de duas leituras em 86
(05-05 e 06-01). A queda e tecnica, nao estrutural: **eficacia media segue saturada a 100%**
(0.895, era 0.812) e **a dimensao Correcoes deixou de ser ruido** — `correction_count` agora
incrementa de verdade (avg 0.055 geral; `structural/pessoal` 0.165; uma memoria u18 com 8
correcoes). O ponto que custa pontos: **cold sobe para 12.48%** (66/529, acima do threshold de
10% — primeira vez desde 05-18) e **KG coverage volta a cair para 42.9%** (era 44.6%), com
**1.590 entidades orfas (41%)**. 529 memorias totais (+36, +7.3%) e 781 sessoes (+57).

**Mudanca de schema observada**: surgiu a categoria `cold` como categoria distinta (15 memorias
em `cold/pessoal`), separada da flag `is_cold`. O tier frio agora parece materializar-se tambem
como categoria propria — sinal de que o cold-tiering passou a operar (ver Notas).

---

## Metricas de Sessoes (Q1)

| Metrica | Valor |
|---------|-------|
| Total de sessoes | 781 (+57 vs 724) |
| Sessoes ultima semana | 54 |
| Sessoes ultimo mes | 248 |
| Usuarios unicos | 32 (+1) |
| Media de mensagens/sessao | 8.78 |
| Custo medio/sessao | US$ 3.35 |

### Sessoes por usuario — ultimos 30d (Q5, top)

| user_id | Nome | Sessoes | Msgs | Custo (US$) | Ultima sessao |
|---------|------|---------|------|-------------|---------------|
| 1 | Rafael Nascimento | 64 | 485 | 293.97 | 2026-06-05 |
| 18 | Marcus Lima | 35 | 219 | 104.61 | 2026-06-08 |
| 17 | Talita de Le Lima | 25 | 391 | 178.57 | 2026-06-01 |
| 69 | Gabriella Silva | 16 | 156 | 189.99 | 2026-06-05 |
| 83 | Sabrina Lima | 16 | 292 | 180.56 | 2026-06-05 |
| 38 | Alice Helen Barros | 12 | 152 | 60.27 | 2026-06-02 |
| 67 | Elaine Almeida | 12 | 50 | 22.99 | 2026-06-08 |
| 4 | Jessica Tereza | 11 | 78 | 25.79 | 2026-06-03 |
| 55 | Rafael Nascimento (alt) | 10 | 92 | 79.60 | 2026-06-05 |

> Contas duplicadas conhecidas convivem com user_ids distintos: Rafael (1/55), Elaine (67/57),
> Sabrina (83/45), Talita (17/58/70), Marcus (18/56). Ja registrado na memoria do projeto.
> Novidade: Alice (38) e Jessica (4) entram no top de atividade. Martha (82) custa US$155 em 5 sessoes.

---

## Memorias por Categoria e Escopo (Q2)

| Categoria | Escopo | Total | Avg Imp | Avg Efic* | Avg Corr | Cold | Conflict | Stale 30d | Stale 60d |
|-----------|--------|-------|---------|-----------|----------|------|----------|-----------|-----------|
| cold | pessoal | 15 | 0.70 | — | 0.00 | 15 | 0 | 0 | 0 |
| contextual | pessoal | 18 | 0.48 | — | 0.00 | 3 | 1 | 3 | 0 |
| operational | empresa | 30 | 0.81 | — | 0.00 | 2 | 0 | 14 | 8 |
| operational | pessoal | 51 | 0.54 | — | 0.00 | 3 | 0 | 13 | 6 |
| permanent | empresa | 4 | 0.90 | — | 0.00 | 0 | 0 | 0 | 0 |
| permanent | pessoal | 45 | 0.88 | — | 0.00 | 0 | 0 | 4 | 0 |
| structural | empresa | 190 | 0.77 | — | 0.00 | 28 | 0 | 92 | 52 |
| structural | pessoal | 176 | 0.68 | — | **0.165** | 15 | 0 | 41 | 3 |

> *Avg Efic por linha nao reportada (Q2 usa avg_effective bruto, nao a taxa). Eficacia media
> geral (taxa effective/usage) = **0.895** — ver Health Score.
> `structural/empresa` (190) segue concentrando o problema: 28 de 66 cold (42%) e 52 de 69 stale
> 60d (75%). **avg_corrections deixou de ser 0**: `structural/pessoal` registra 0.165 — o pipeline
> de correcao comecou a gravar (ver categoria `corrections/*` na Q3 com correction_count=8).

---

## Top Memorias de Baixa Eficacia (Q3)

20 memorias com usage >= 3 e efficacy < 0.3 (category != permanent). Destaques de alto uso:

| Path | usage | effective | corr | efficacy |
|------|-------|-----------|------|----------|
| empresa/heuristicas/integracao/memorias-de-usuario-devem-funcionar-como-protocolo-ativo.xml | 172 | 9 | 0 | 0.052 |
| empresa/termos/integracao-nf.xml | 108 | 5 | 0 | 0.046 |
| empresa/termos/confirmar-pedido.xml | 81 | 4 | 0 | 0.049 |
| empresa/regras/a-rede-assai-opera-com-multiplas-lojas-i.xml | 49 | 3 | 0 | 0.061 |
| empresa/correcoes/build_artifact_pnpm.md | 36 | 2 | 0 | 0.056 |
| empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel.xml | 32 | 0 | 0 | 0.000 |
| **empresa/armadilhas/integracao/_archived_..._archived_..._archived_presigned-url-s3-vence...xml** | 23 | 0 | 0 | 0.000 |
| empresa/armadilhas/integracao/reautorizacao-oauth-...tagplus.xml | 20 | 0 | 0 | 0.000 |
| empresa/regras/quando-o-usuario-envia-saudacao-e-pedido.xml | 19 | 0 | 0 | 0.000 |
| empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica.xml | 15 | 0 | 0 | 0.000 |
| **empresa/heuristicas/abordagem-validada-pelo-judge-bom-dia.xml** | 11 | 0 | 0 | 0.000 |
| corrections/quando-pergunta-detalhes-de-um-cluster-especifico.xml (u18) | 10 | 0 | **8** | 0.000 |

### Zero-efficacy com uso (efficacy = 0)
**21 memorias** com effective_count = 0 apesar de usage_count > 0 (era 12 em 06-01, **+9, +75%**).
A piora vem de um novo cluster emergente: memorias `empresa/heuristicas/abordagem-validada-pelo-judge-*`
(`bom-dia` u11, `estou-enviando-2-arquivos...mach` u6, `ola` u5) — todas criadas em 2026-06-06,
recuperadas mas nunca marcadas efetivas. Padrao de ruido novo (heuristicas geradas pelo judge que
nao convertem). Persistem do ciclo anterior: `diagnostico-de-regressao-sem-historico-git` (u32),
`_archived_presigned-url-s3` (u23, **agora 3x arquivada**, ainda em uso), `reautorizacao-oauth-tagplus`
(u20), `quando-o-usuario-envia-saudacao` (u19), `gabriella-telegrafica` (u15).

> Nota positiva: a memoria u18 `corrections/quando-pergunta-detalhes-de-um-cluster` tem
> correction_count=8 — o pipeline de correcao esta registrando feedback negativo nela.

---

## Memorias Empresa (user_id=0) — Q6 (agregado)

| Metrica | Valor |
|---------|-------|
| Total memorias empresa | 226 (era 211, +15) |
| Nunca revisadas (reviewed_at NULL) | **113 (50%)** |
| Revisadas ha > 30d | 0 |
| Baixa eficacia (efic < 0.3, usage >= 3) | 33 (era 31) |
| Zero-efficacy (effective=0, usage>0) | 12 |
| Cold | 30 |
| Stale 60d | 60 |
| Avg importance | 0.78 |
| Avg efficacy (taxa) | 0.70 |
| Avg corrections | 0.00 |

> Metade das memorias empresa segue nunca revisada (`reviewed_at` NULL) — padrao reincidente ha
> 8+ ciclos. 15 novas memorias empresa entraram desde 06-01, todas sem ciclo de validacao.
> `correction_count` permanece 0 no escopo empresa — o feedback de correcao so opera no escopo pessoal.

---

## Knowledge Graph (Q4 + Q7)

| Metrica | Valor |
|---------|-------|
| Entidades totais | 3.874 (+273 vs 3.601) |
| Entidades orfas (sem link a memoria) | **1.590 (41.0%)** |
| Memorias com entidades vinculadas (distintas) | 227 |
| Coverage (memorias linkadas / total) | **42.9%** (era 44.6%, -1.7pp) |
| Links entidade-memoria | 2.284 |
| Relacoes entidade-entidade | 7.310 (+123) |

### Entidades por tipo (top)
| Tipo | Total | Memorias linkadas | Avg mentions |
|------|-------|-------------------|--------------|
| conceito | 1.343 | 178 | 1.38 |
| cliente | 737 | 26 | 1.30 |
| produto | 578 | 48 | 1.14 |
| transportadora | 429 | 21 | 1.10 |
| processo | 241 | 121 | 1.34 |
| campo | 179 | 98 | 1.21 |
| termo | 85 | 58 | 1.71 |
| valor | 82 | 29 | 1.23 |
| uf | 69 | 31 | 4.36 |
| regra | 68 | 9 | 1.12 |
| usuario | 16 | 15 | 5.88 |

> `cliente` (737), `produto` (578) e `transportadora` (429) seguem como os grandes geradores de
> orfas: juntos sao 1.744 entidades mas so 95 memorias linkadas. Sao extraidas de conversas mas
> raramente ancoradas a memoria persistente. Coverage caiu pelo 2o ciclo — extracao continua
> crescendo mais rapido que a ancoragem (entity->memory linking).

### Top relacoes semanticas (peso)
- ASSAI (cliente) --requer--> CONFIRMACAO-MANUAL (5.0)
- DRY-RUN-OBRIGATORIO --precede--> ACOES-EM-LOTE-ODOO (5.0)
- PEDIDO-DE-VENDA --co_occurs--> COTACAO (3.5)
- CONFIRMAR-PEDIDO --co_occurs--> COTACAO (3.5)
- VCD --complementa--> PEDIDO (3.0)
- DENISE (cliente) --pertence_a--> COMPRAS (3.0)
- GABRIELLA (usuario) --responsavel_por--> COMPRAS (3.0)
- VCD2667872 (pedido) --co_occurs--> SANNA (cliente) (3.0)

---

## Health Score — Detalhamento

| Dimensao | Peso | Valor medido | Score parcial | Pontos |
|----------|------|--------------|---------------|--------|
| Eficacia media | 30% | 0.895 (>= 0.7) | 100% | 30.0 |
| Taxa cold | 20% | 12.48% (66/529) | 93.8% | 18.8 |
| Stale 60d | 20% | 13.04% (69/529) | 77.0% | 15.4 |
| KG coverage | 15% | 42.9% (227/529) | 38.2% | 5.7 |
| Correcoes | 15% | 0.055 (< 0.5) | 100% | 15.0 |
| **TOTAL** | | | | **84.9 → 85** |

> **Mudanca metodologica relevante**: a dimensao Correcoes deixou de ser artificial. Em ciclos
> anteriores `correction_count` era 0 em 100% das memorias e os 15 pts eram ruido. Agora o campo
> incrementa (avg 0.055 geral; uma memoria com 8 correcoes). Como o valor real (0.055) ainda esta
> bem abaixo do threshold de 0.5, a dimensao legitimamente pontua 100% — mas agora porque o sistema
> esta saudavel em correcoes, nao porque o campo esta morto. **O health 85 e mais confiavel que os
> 86 anteriores.** A dimensao KG (5.7/15) e a unica genuinamente fraca; cold subiu ao threshold.

### Serie historica
86 (05-05) → 82 (05-11) → 80 (05-18) → 84 (05-25) → 86 (06-01) → **85 (06-08)**

---

## Recomendacoes Acionaveis

1. **[R1 — ALTA] Deletar fisicamente memorias `_archived_*` ainda em uso.** A memoria
   `_archived_..._archived_..._archived_presigned-url-s3-vence` (u23, e0) ja foi arquivada **3 vezes**
   (timestamps 20260521, 20260528, 20260603 no path) e continua sendo recuperada. Bug latente ha
   4+ ciclos: o prefixo `_archived_` nao exclui da busca. O re-arquivamento so empilha prefixos.
   Excluir do indice/embedding ou deletar a linha.

2. **[R2 — ALTA] Investigar novo cluster `heuristicas/abordagem-validada-pelo-judge-*`.** Tres
   memorias criadas em 2026-06-06 (`bom-dia` u11, `...mach` u6, `ola` u5) ja entraram zero-efficacy.
   O judge esta gerando heuristicas a partir de saudacoes/uploads triviais que sao recuperadas mas
   nunca convertem. Driver do salto de zero-efficacy 12→21 (+75%). Avaliar filtro de geracao do
   judge (nao memorizar abordagem para inputs triviais) ou rebaixar importance dessas heuristicas.

3. **[R3 — ALTA] Revisar 113 memorias empresa nunca revisadas (50%).** Zero memorias empresa tem
   `reviewed_at` (0 em <30d, 113 NULL, de 226). Padrao reincidente ha 8 ciclos. Estabelecer rotina
   de revisao de `user_id=0`. `correction_count` tambem nao opera no escopo empresa (so pessoal).

4. **[R4 — MEDIA] Atacar KG coverage (42.9%, 2o ciclo de queda).** 1.590 entidades orfas (41%);
   cliente/produto/transportadora somam 1.744 entidades com so 95 memorias linkadas. Podar orfas
   com mention_count = 1 (a maioria: avg_mentions ~1.1-1.3 nesses tipos) e revisar o pipeline de
   entity→memory linking, que nao acompanha o ritmo de extracao.

5. **[R5 — MEDIA] Mover para cold tier as 52 stale 60d de `structural/empresa`.** Concentram 75%
   do stale 60d total e 42% do cold. Candidatas a tier frio (>60d sem update). A categoria `cold`
   ja existe como destino (15 memorias hoje) — usar o pipeline de cold-tiering para drena-las.

6. **[R6 — MEDIA] Conter taxa cold (12.48%, acima do threshold de 10%).** 66 memorias cold de 529;
   o crescimento de cold (44→66, +50%) superou o de memorias totais (+7%). Verificar se o
   cold-tiering esta promovendo memorias cedo demais ou se ha acumulo de memorias mortas nunca
   reaquecidas.

7. **[R7 — BAIXA] Rebaixar `heuristicas/.../protocolo-ativo.xml` (u172, efic 0.052).** Memoria mais
   usada do sistema (172 usos) e quase nunca efetiva — meta-heuristica que sempre carrega mas
   raramente ajuda. Persiste no topo da lista de baixa eficacia ha multiplos ciclos. Avaliar
   reescrita ou reducao de importance (0.8 → 0.5).

8. **[R8 — BAIXA] Validar conta duplicada de Talita (17/58/70) com US$178/391msgs em 17.** Tres
   user_ids para a mesma pessoa fragmentam metricas e memorias pessoais. Consolidar perfil
   reduziria ruido de memoria pessoal (ja conhecido, mas o volume de 17 cresceu).

---

## Notas de Execucao

- **Schema**: surgiu a categoria `cold` na Q2 (15 memorias `cold/pessoal`) — distinta da flag
  booleana `is_cold`. Indica que o cold-tiering passou a materializar memorias como categoria
  propria. As 15 estao 100% marcadas `is_cold=true` e fora de stale (recem-movidas). Sinal de que
  o pipeline de cold-tier comecou a operar entre 06-01 e 06-08.
- **Correcoes**: `correction_count` deixou de ser 0 universal — primeiro ciclo com o campo vivo
  (avg geral 0.055; `structural/pessoal` 0.165; memoria u18 com 8). Health 85 e metodologicamente
  mais solido que os 86 anteriores (que infavam +15 pts artificiais).
- Q6 (lista detalhada user_id=0) emitida como agregacao (contagens + medias) preservando todas as
  metricas do contrato. Lista bruta nao incluida por politica (Limites item 3: nao expor conteudo).
- Read-only: apenas SELECTs executados. Nenhuma escrita no Postgres.

# Atualizacao Memory Eval — 2026-06-01-1

**Data**: 2026-06-01
**Health Score**: 86/100 (+2 vs 84 em 2026-05-25)
**Fonte**: Render Postgres `dpg-d13m38vfte5s738t6p50-a` (READ-ONLY)
**Status**: OK — 7 queries executadas (Q6 re-emitida em forma agregada por estouro de payload)

---

## Resumo Executivo

Health sobe a **86/100**, igualando o recorde da serie (05-05) e quebrando definitivamente
o vale 80-82-84 de abril/maio. Eficacia media geral salta para **0.812** (era 0.656 em 05-25,
+15.6pp) — melhor leitura ja registrada — puxando a dimensao Eficacia a 100%. Cold cai abaixo
do threshold (8.93% < 10%). **KG continua sendo o calcanhar**: coverage 44.6% (15% do peso,
so 6.15 pts dos 15) e **1.582 entidades orfas** (44% do grafo). Stale 60d sobe para 13.99%
(69 memorias). 493 memorias totais (+68, +16%) e 724 sessoes (+80).

---

## Metricas de Sessoes (Q1)

| Metrica | Valor |
|---------|-------|
| Total de sessoes | 724 (+80 vs 644) |
| Sessoes ultima semana | 80 (recorde semanal) |
| Sessoes ultimo mes | 231 |
| Usuarios unicos | 31 (+2) |
| Media de mensagens/sessao | 8.72 |
| Custo medio/sessao | US$ 2.90 |

### Sessoes por usuario — ultimos 30d (Q5, top)

| user_id | Nome | Sessoes | Msgs | Custo (US$) | Ultima sessao |
|---------|------|---------|------|-------------|---------------|
| 1 | Rafael Nascimento | 67 | 480 | 232.87 | 2026-05-31 |
| 18 | Marcus Lima | 37 | 300 | 85.22 | 2026-05-30 |
| 17 | Talita de Le Lima | 23 | 293 | 60.50 | 2026-06-01 |
| 69 | Gabriella Silva | 18 | 180 | 173.65 | 2026-05-29 |
| 67 | Elaine Almeida | 11 | 50 | 24.03 | 2026-05-27 |
| 83 | Sabrina Lima | 11 | 226 | 121.04 | 2026-05-29 |
| 55 | Rafael Nascimento (alt) | 10 | 90 | 80.74 | 2026-05-29 |

> Contas duplicadas observadas: Rafael (1/55), Elaine (67/57), Sabrina (83/45), Talita (17/58/70),
> Marcus (18/56) — convivem com user_ids distintos (ja conhecido na memoria do projeto).

---

## Memorias por Categoria e Escopo (Q2)

| Categoria | Escopo | Total | Avg Imp | Avg Efic | Cold | Conflict | Stale 30d | Stale 60d |
|-----------|--------|-------|---------|----------|------|----------|-----------|-----------|
| contextual | pessoal | 18 | 0.47 | 1.02 | 3 | 1 | 3 | 0 |
| operational | empresa | 20 | 0.85 | 0.70 | 2 | 0 | 13 | 7 |
| operational | pessoal | 46 | 0.54 | 0.89 | 2 | 0 | 14 | 6 |
| permanent | empresa | 4 | 0.90 | 0.58 | 0 | 0 | 4 | 4 |
| permanent | pessoal | 42 | 0.87 | 0.81 | 0 | 0 | 10 | 5 |
| structural | empresa | 185 | 0.77 | 0.68 | 27 | 0 | 90 | 45 |
| structural | pessoal | 178 | 0.67 | 0.83 | 10 | 0 | 94 | 2 |

> `structural/empresa` (185) concentra o problema: 27 de 44 cold (61%) e 45 de 69 stale 60d (65%).
> avg_corrections = 0 em TODAS as categorias (correcoes nao estao sendo contabilizadas — campo
> permanece zerado ciclo apos ciclo; contribui artificialmente +15 pts para o health score).

---

## Top Memorias de Baixa Eficacia (Q3)

20 memorias com usage >= 3 e efficacy < 0.3 (category != permanent). Destaques de alto uso:

| Path | usage | effective | efficacy |
|------|-------|-----------|----------|
| empresa/heuristicas/integracao/memorias-de-usuario-devem-funcionar-como-protocolo-ativo.xml | 172 | 9 | 0.052 |
| empresa/termos/integracao-nf.xml | 108 | 5 | 0.046 |
| empresa/termos/confirmar-pedido.xml | 81 | 4 | 0.049 |
| empresa/regras/a-rede-assai-opera-com-multiplas-lojas-i.xml | 49 | 3 | 0.061 |
| system/download_config.xml (u1) | 47 | 3 | 0.064 |
| empresa/correcoes/build_artifact_pnpm.md | 36 | 2 | 0.056 |
| empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel.xml | 32 | 0 | 0.000 |
| empresa/termos/cotacao.xml | 27 | 2 | 0.074 |
| **empresa/armadilhas/integracao/_archived_...presigned-url-s3-vence...xml** | 23 | 0 | 0.000 |
| empresa/armadilhas/integracao/reautorizacao-oauth-...tagplus.xml | 20 | 0 | 0.000 |

### Zero-efficacy com uso (efficacy = 0)
12 memorias com effective_count = 0 apesar de usage_count > 0 (era 12 em 05-25, estavel):
- usage 32: `diagnostico-de-regressao-sem-historico-git-disponivel.xml`
- usage 23: `_archived_...presigned-url-s3-vence-antes-do-usuario-baixar.xml` **(arquivada, ainda em uso)**
- usage 20: `reautorizacao-oauth-obrigatoria-para-novos-scopes-tagplus.xml`
- usage 19: `quando-o-usuario-envia-saudacao-e-pedido.xml`
- usage 15: `gabriella-comunica-se-de-forma-telegrafica...xml`
- usage 15: `_archived_..._archived_sessao-teams-reinicia-antes-de-subagente-concluir.xml` **(2x arquivada, ainda em uso)**
- + 6 com usage 3-9 (corrections/* u1/u18/u57, kerley.xml, modo-debug.xml, operadores-teams-bot)

---

## Memorias Empresa (user_id=0) — Q6 (agregado)

| Metrica | Valor |
|---------|-------|
| Total memorias empresa | 211 (era 192, +19) |
| Nunca revisadas (reviewed_at NULL) | **106 (50%)** |
| Revisadas ha > 30d | 0 |
| Baixa eficacia (efic < 0.3) | 31 (era 29) |
| Cold | 29 |
| Stale 60d | 56 |
| Avg importance | 0.78 |
| Avg efficacy | 0.66 |

> Metade das memorias empresa nunca passou por revisao (`reviewed_at` NULL). Padrao persistente
> ha 7+ ciclos: novas memorias empresa entram sem ciclo de validacao.

---

## Knowledge Graph (Q4 + Q7)

| Metrica | Valor |
|---------|-------|
| Entidades totais | 3.601 (+1.820 vs 1.781) |
| Entidades orfas (sem link a memoria) | **1.582 (43.9%)** |
| Memorias com entidades vinculadas | 220 |
| Coverage (memorias linkadas / total) | **44.6%** (era 47.5%, -2.9pp) |
| Relacoes entidade-entidade | 7.187 (+820) |

### Entidades por tipo (top)
| Tipo | Total | Memorias linkadas | Avg mentions |
|------|-------|-------------------|--------------|
| conceito | 1.332 | 174 | 1.38 |
| cliente | 731 | 26 | 1.30 |
| produto | 577 | 47 | 1.14 |
| transportadora | 427 | 21 | 1.10 |
| processo | 233 | 117 | 1.35 |
| campo | 175 | 96 | 1.21 |
| uf | 68 | 30 | 4.41 |
| usuario | 16 | 15 | 5.88 |

> `cliente` (731), `produto` (577) e `transportadora` (427) sao os grandes geradores de orfas:
> entidades extraidas de conversas mas raramente ancoradas a memoria persistente. O KG dobrou de
> tamanho mas a coverage caiu — crescimento desbalanceado (extracao >> ancoragem).

### Top relacoes semanticas (peso)
- ASSAI --requer--> CONFIRMACAO-MANUAL (5.0)
- DRY-RUN-OBRIGATORIO --precede--> ACOES-EM-LOTE-ODOO (5.0)
- PEDIDO-DE-VENDA --co_occurs--> COTACAO (3.5)
- CONFIRMAR-PEDIDO --co_occurs--> COTACAO (3.5)
- GABRIELLA --responsavel_por--> COMPRAS (3.0)

---

## Health Score — Detalhamento

| Dimensao | Peso | Valor medido | Score parcial | Pontos |
|----------|------|--------------|---------------|--------|
| Eficacia media | 30% | 0.812 (>= 0.7) | 100% | 30.0 |
| Taxa cold | 20% | 8.93% (44/493, < 10%) | 100% | 20.0 |
| Stale 60d | 20% | 13.99% (69/493) | 74.3% | 14.9 |
| KG coverage | 15% | 44.6% (220/493) | 41.0% | 6.2 |
| Correcoes | 15% | 0.0 (< 0.5) | 100% | 15.0 |
| **TOTAL** | | | | **86.0** |

> Ressalva: dimensao Correcoes (15 pts) e ARTIFICIAL — `correction_count` esta zerado em todas
> as memorias ha multiplos ciclos. Excluindo-a, o health "real" seria ~71/100. A dimensao KG
> (6.2/15) e a unica genuinamente fraca.

### Serie historica
86 (05-05) -> 82 (05-11) -> 80 (05-18) -> 84 (05-25) -> **86 (06-01)**

---

## Recomendacoes Acionaveis

1. **[R1 — ALTA] Remover memorias `_archived_*` ainda em uso.** Duas memorias arquivadas
   (`_archived_...presigned-url-s3-vence` u23, `_archived_..._archived_sessao-teams-reinicia` u15)
   continuam sendo recuperadas com effective_count baixo/zero. Bug latente ha 3+ ciclos: o
   prefixo `_archived_` nao exclui da busca. Mover para cold tier ou deletar fisicamente.

2. **[R2 — ALTA] Auditar 12 memorias zero-efficacy de alto uso.** `diagnostico-de-regressao-sem-historico-git`
   (u32, e0), `reautorizacao-oauth-tagplus` (u20, e0), `quando-o-usuario-envia-saudacao-e-pedido`
   (u19, e0). Sao recuperadas mas nunca marcadas efetivas — provavel mismatch de relevancia
   (recall alto, precision zero). Revisar conteudo/embedding ou rebaixar importance.

3. **[R3 — ALTA] Revisar 106 memorias empresa nunca revisadas (50%).** Nenhuma memoria empresa
   tem `reviewed_at` recente (0 revisadas em <30d, 106 NULL). Estabelecer rotina de revisao de
   memorias `user_id=0` — padrao reincidente ha 7 ciclos.

4. **[R4 — MEDIA] Atacar KG coverage (44.6%, unica dimensao real fraca).** 1.582 entidades orfas
   (cliente/produto/transportadora dominam). O grafo dobrou mas a ancoragem caiu. Avaliar:
   (a) podar entidades orfas com mention_count = 1; (b) revisar pipeline de linking entity->memory.

5. **[R5 — MEDIA] Mover para cold tier as 45 stale 60d de `structural/empresa`.** Concentram 65%
   do stale 60d e 61% do cold. Candidatas a tier frio (>60d sem update, baixa eficacia).

6. **[R6 — BAIXA] Investigar `correction_count` zerado.** O campo nunca incrementa, inflando o
   health em 15 pts. Verificar se o pipeline de feedback grava correcoes — sem ele, a dimensao
   e ruido. Sem correcao, considerar repesar o health score.

7. **[R7 — BAIXA] Rebaixar `heuristicas/.../protocolo-ativo.xml` (u172, efic 0.052).** Memoria
   mais usada do sistema e quase nunca efetiva — meta-heuristica que sempre carrega mas raramente
   ajuda. Avaliar reescrita ou reducao de importance (0.8 -> 0.5).

---

## Notas de Execucao

- Q6 (lista detalhada user_id=0) excedeu o limite de payload do MCP (69.557 chars). Re-emitida
  como agregacao (contagens + medias) preservando todas as metricas exigidas pelo contrato.
  Lista bruta nao incluida no relatorio por politica (item 3 dos Limites: nao expor conteudo).
- Read-only: apenas SELECTs executados. Nenhuma escrita no Postgres.

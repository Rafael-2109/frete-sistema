<!-- doc:meta
tipo: relatorio
camada: L3
sot_de: —
hub: docs/superpowers/plans/2026-06-09-arquitetura-contexto-boot-agente.md
superseded_by: —
atualizado: 2026-06-10
-->
# Precision@k baseline — Tier 2 de memorias (F5 PAD-CTX)

> **Papel:** medicao de baseline do retrieval de memorias do Agente Web (mandato do
> ponteiro de retomada da F5: medir ANTES de codar a 5.4) + A/B voyage-4-lite vs
> voyage-4-large. Anexo do plano `2026-06-09-arquitetura-contexto-boot-agente.md`.

## Metodo

- **20 turnos reais** de PROD (05-09/06/2026, 9 usuarios: 1, 18, 27, 38, 43, 49, 67,
  69, 83; fontes: `agent_sessions.title`/`last_message`). Dominios: expedicao,
  estoque/producao, financeiro, CarVia, Odoo.
- **3 bracos** por turno:
  1. `fallback` — as 4 memorias que PROD REALMENTE injetava via fallback de recencia
     (observadas nos logs `[MEMORY_INJECT_PATHS]` de 09/06 — semantic=0 em 100% dos
     turnos por threshold 0.55 acima da distribuicao).
  2. `lite` — top-4 do indice PROD real (`agent_memory_embeddings`, voyage-4-lite,
     queries re-embedadas com o prompt do turno; SQL identica a
     `_search_pgvector_memories`).
  3. `large` — top-4 de re-embed local do MESMO corpus (361 memorias ativas baixadas
     read-only) com voyage-4-large, mesmas queries, mesmo filtro `user_id IN (uid,0)`.
- **Julgamento**: 20 judges Sonnet ceticos (1/turno; workflow `precision-at-k-memorias`),
  criterio "util = muda concretamente a resposta DESTE turno"; ~12 memorias julgadas
  por turno. Agregacao por posicao com gates pos-hoc de similarity.
- Artefatos: `/tmp/f5_baseline/` (dataset, judge_input, verdicts, precision_report.json)
  + `/tmp/f5_braco_b/` (corpus, ab_rankings). Scripts reexecutaveis nos mesmos paths.

## Resultados

| Braco | Gate | Injetadas | Uteis | Precision@4 | Cobertura (turnos) | Uteis/turno |
|---|---|---:|---:|---:|---:|---:|
| Fallback recencia (PROD hoje) | — | 80 | 1 | **0.013** | 20/20 | 0.05 |
| Lite (indice PROD) | >=0.55 | 18 | 11 | 0.611 | 9/20 | 0.55 |
| Lite (indice PROD) | >=0.45 | 52 | 29 | **0.558** | 15/20 | 1.45 |
| Lite (indice PROD) | >=0.40 | 67 | 30 | 0.448 | 18/20 | 1.50 |
| Large (re-embed local) | >=0.55 | 9 | 9 | 1.000 | 6/20 | 0.45 |
| Large (re-embed local) | >=0.45 | 38 | 32 | **0.842** | 15/20 | 1.60 |
| Large (re-embed local) | >=0.40 | 55 | 37 | **0.673** | 18/20 | 1.85 |
| Large (re-embed local) | sem gate | 80 | 43 | 0.537 | 20/20 | 2.15 |

Distribuicao de similarity (top-1 mediano): lite 0.5482 / large 0.5032 — **escala NAO
transfere entre modelos** (mesma licao do bug do 0.55).

## Conclusoes

1. **O baseline de PROD e ruido**: 1 memoria util em 80 injetadas (precision 0.013).
   Qualquer semantica funcional e ordens de magnitude melhor.
2. **Threshold 0.55 (env PROD) mata o retrieval**: cobre so 9/20 turnos no lite.
   Para o lite vigente, **0.45** e o equilibrio (0.558 de precisao, 15/20).
3. **voyage-4-large rankeia muito melhor que o lite** no MESMO corpus e queries:
   +51% de precisao relativa @0.45 (0.842 vs 0.558) e +50% @0.40 (0.673 vs 0.448).
   Recall bruto por gate empata; a diferenca esta na ORDENACAO (uteis no topo).
4. **2 turnos sao irrecuperaveis por embedding** (anafora "as 4.840" sem contexto;
   pergunta factual de skill SSW) — teto pratico de cobertura ~18/20 nesta amostra.
5. Memorias `_archived_*` poluiam o top-10 do indice PROD (3/10 num turno) — corrigido
   na F5.4 (filtro is_cold no SQL da busca).

## Recomendacoes (decisao do Rafael)

- **Imediato (sem deploy)**: mudar env `AGENT_MEMORY_MIN_SIMILARITY` em PROD de
  `0.55` para `0.45` (ou remover — default do codigo ja e 0.45). So isso tira o
  Tier 2 de precision 0.013 (fallback) para 0.558 em 15/20 turnos.
- **Migracao para voyage-4-large** (custo irrisorio, ganho +50% de precisao):
  1. Reindexar `agent_memory_embeddings` com large (361 ativas; manter dim 1024 —
     sem DDL); 2. `VOYAGE_DEFAULT_MODEL=voyage-4-large` (afeta TODOS os dominios que
     usam o default — sessoes/templates exigem reindex tambem, ou isolar via env
     dedicada p/ memorias); 3. threshold recalibrado para **0.40** (cobertura 18/20,
     precision 0.673, ~1.85 uteis/turno) ou 0.45 conservador; 4. validar com este
     mesmo harness (reexecutavel).
- **Fallback de recencia**: manteve-se como rede com caps F4 (4x300c) — dado novo
  (precision 0.013) sugere no futuro desligar a parte EMPRESA do fallback; nao
  mudado agora (exigiria nova validacao comportamental).

## Fontes

- FONTE: logs Render `[MEMORY_INJECT]`/`[MEMORY_INJECT_PATHS]` srv-d13m38vfte5s738t6p60 (2026-06-09).
- FONTE: `agent_memory_embeddings`/`agent_memories` PROD via MCP Render (read-only).
- FONTE: workflow `precision-at-k-memorias` (20 judges Sonnet, 2026-06-10).
- FONTE: `docs/superpowers/plans/2026-06-09-arquitetura-contexto-boot-agente.md` (FASE 5).

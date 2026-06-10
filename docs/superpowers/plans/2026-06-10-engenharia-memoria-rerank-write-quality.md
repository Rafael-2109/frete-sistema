<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano das 2 frentes de engenharia de memoria pos-PAD-CTX (reranker no retrieval + qualidade na escrita)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-10
-->
# Engenharia de Memoria — Reranker no retrieval + Qualidade na escrita

> **Papel:** continuidade direta da F5/F6 do plano PAD-CTX
> (`2026-06-09-arquitetura-contexto-boot-agente.md`) — os itens 3 e 4 do topico D
> da conversa de 2026-06-10 com o Rafael ("a engenharia de prompt e memoria
> poderiam ser aprimoradas?"). **Abra quando:** for executar/retomar qualquer
> das 2 frentes. Metodo INVIOLAVEL (licao F5/F6): medir ANTES de codar →
> TDD red-first → validar com o harness → aceite em PROD com logs.

> 🔵 **PROXIMA SESSAO — COMECAR AQUI:** FRENTE 1 CONCLUIDA (rerank medido
> vencedor, flag ON, latencia validada em PROD 320ms). FRENTE 2 com codigo
> COMPLETO (parser+validacao+backfill script) — **PENDE SO a aplicacao do
> backfill em PROD, que exige autorizacao explicita do Rafael** (escrita
> direta DATABASE_URL_PROD — regra da memoria do projeto):
> `DATABASE_URL="$DATABASE_URL_PROD" python scripts/migrations/2026_06_10_backfill_meta_when_do.py --confirmar`
> (dry-run ja revisado: parser=102, haiku~58 com 11 nao-operativas recusadas).
> Depois: validar 2.5 (% meta.do >= 90% das operativas) + re-rodar ablacao.
> PRE-REQUISITO de leitura: Rastreamento abaixo + `rerank_ab_2026-06-10.md`.

## Evidencia (verificada 2026-06-10 — nao re-descobrir)

- **Retrieval atual** (pos-F5): voyage-4-large@0.40, precision@4 = 0.673 com
  cobertura 18/20 (harness de 20 turnos reais + judges Sonnet). O A/B mostrou
  que RANKING e onde o large ganha (+50% vs lite) — reranker e o proximo
  degrau natural da mesma alavanca.
- **Rerank JA EXISTE no repo** para regras SPED: `app/embeddings/sped_rules_search.py`
  (~:125-210) — flag de uso, pool maior de candidatos no cosine
  (`SPED_RULES_RERANK_CANDIDATES`), `client.rerank(...)` Voyage, fallback se
  falhar. A busca de MEMORIAS (`app/embeddings/memory_search.py::buscar_memorias_semantica`)
  NAO tem rerank; o `rerank_score` lido em
  `app/agente/sdk/memory_injection.py` (`r.get('rerank_score', similarity)`)
  e placeholder que nunca e populado.
  **⚠ CORRECAO (2026-06-10, execucao F1): os 2 ultimos pontos estavam ERRADOS.**
  `buscar_memorias_semantica` JA tinha rerank completo (over-fetch 40 +
  rerank-2.5-lite + fallback) com `MEMORY_RERANKING_ENABLED` default `true`
  desde 2026-03-03, e o `rerank_score` JA era populado/consumido. O log era
  `debug` (invisivel em PROD) — dai a impressao de inexistente. Detalhe:
  `relatorios/estudo_contexto_boot_2026-06-09/rerank_ab_2026-06-10.md`.
- **Escrita sem formato operativo**: 359 memorias de conhecimento ativas em
  PROD (excluidos perfis/context/system); **146 (40%) sem `meta.do`**, das
  quais **109 sao longas (>300c)** → caem no truncate burro do destilado
  Tier 2 (`_distill_tier2_content` prefere meta WHEN/DO; sem meta, corta o
  content a 300c). O destilado operativo e o que sustentou tier1 a 95% de
  utilidade na ablacao — memoria sem WHEN/DO desperdica o retrieval consertado.
- Consumidores do meta WHEN/DO hoje: destilado Tier 2 (300c), destilado de
  rules (`_distill_rule_content`), operational_directives (legado flag-off),
  routing traps. `save_memory` (memory_mcp_tool, Enhanced v2.1.0) JA popula
  meta para formatos reconhecidos (serializador canonico 2026-06-08, 92%
  PROD) — o gap e conteudo LIVRE sem WHEN/DO que o parser nao extrai.

## FRENTE 1 — Reranker no retrieval de memorias

| # | Acao | Onde |
|---|------|------|
| 1.1 | MEDIR ANTES (ja existe baseline 0.673 — conferir que o harness reexecuta; artefatos `/tmp/f5_*` sao volateis, regenerar se preciso) | harness precision@k |
| 1.2 | Portar o padrao SPED: `buscar_memorias_semantica` ganha rerank opt-in — cosine pesca pool maior (ex: 30-40 candidatos em vez de 20), `client.rerank` Voyage (modelo a confirmar na doc Voyage; SPED usa o que esta na config) reordena, top-N final. Flag `MEMORY_SEARCH_RERANK` default OFF ate medir. Fallback silencioso p/ cosine se a API falhar (mesmo pattern SPED) | `app/embeddings/memory_search.py` + `app/embeddings/config.py` |
| 1.3 | Popular `rerank_score` de verdade no retorno (o placeholder em `memory_injection.py` passa a receber valor real — conferir que o composite nao quebra com a nova escala; escala de rerank != escala cosine, NAO comparar com threshold 0.40 que e do cosine) | `memory_search.py` (retorno) |
| 1.4 | A/B com o harness: 20 turnos reais, braco cosine-only vs braco rerank. ACEITE: precision@4 > 0.673 SEM perder cobertura (>=18/20). Se nao superar: flag fica OFF, registrar resultado e fechar a frente (decisao por medida, nao por gosto) | harness + relatorio anexo |
| 1.5 | Se aceite: flag ON em PROD + validar logs [MEMORY_INJECT] (latencia do turno nao degrada — rerank adiciona 1 chamada de API; medir tempo no log) | PROD |

**Cuidados**: rerank NAO toca o dedup (decisao A/B 2026-06-10: dedup permanece
lite, gate binario). Cache de injecao por sessao (TTL 30min) amortiza o custo.
Superficies: Web+Teams (mesmo client); subagentes nao recebem o hook.

## FRENTE 2 — Qualidade na escrita (formato operativo na criacao)

| # | Acao | Onde |
|---|------|------|
| 2.1 | MEDIR/CLASSIFICAR as 146 sem meta.do: quantas sao geradas pelo AGENTE (save_memory livre) vs daemons (pattern_analyzer, session_summarizer)? Por kind/path? Define onde atacar | SQL PROD + amostra |
| 2.2 | Validacao INSTRUTIVA no `save_memory`: kinds operativos (heuristica/armadilha/protocolo/correcao/regra) sem WHEN/DO extraivel → tool retorna erro instrutivo pedindo o formato (self-healing: o agente reescreve na hora; padrao ja usado em outros guards). NAO bloquear kinds narrativos (caso/episodica) | `app/agente/tools/memory_mcp_tool.py` |
| 2.3 | Reforco de 1-2 linhas no MEMORY_PROTOCOL.md + description da tool (orcamento do listing! conferir `skills_listing_audit` — description de tool MCP nao conta no listing de skills, mas conferir limites proprios) | `MEMORY_PROTOCOL.md` + tool |
| 2.4 | BACKFILL das 109 longas sem meta.do: derivacao WHEN/DO via Haiku (barato), gravacao no meta JSONB (content INTACTO — so meta), dry-run + amostra revisada antes do lote. Embeddings: content nao muda → indice intacto | script `scripts/migrations/` (data-fix Python) |
| 2.5 | Validar: % com meta.do (alvo >=90% das operativas); re-rodar ablacao (payloads reexecutaveis) — destilados Tier 2 devem aparecer como WHEN/DO em vez de truncate | SQL + harness ablacao |

**Cuidados**: daemons pos-sessao tambem criam memoria — se 2.1 mostrar que a
maioria vem deles, o fix certo e no PROMPT do daemon (pattern_analyzer), nao
no tool. Backfill NUNCA altera content (so meta) — zero risco de perda;
`update_memory` normal gravaria versao, mas data-fix direto em meta nao
precisa (content intacto).

## Fora de escopo (registrado, nao esquecido)

- `preferred_skills` por uso real = F7.5 do plano PAD-CTX (evidencia: 2 riscos
  na ablacao). Few-shot em skills top = F7.3. Ambos vivem LA, nao aqui.
- Qualquer mudanca de threshold/modelo de embedding (fechado na F5).

## Rastreamento de execucao (append-only)

- 2026-06-10 — Plano criado (sessao F6). Evidencias verificadas no codigo e
  em PROD na mesma sessao. Nenhuma frente iniciada.
- 2026-06-10 (noite) — **FRENTE 1 CONCLUIDA.** Premissa corrigida (rerank ja
  rodava em PROD desde marco sem medida — ver ⚠ na Evidencia). A/B executado
  (dataset 20 turnos regenerado, mesmos 9 usuarios; 19 judges Sonnet, 92
  memorias): **rerank 0.463 vs cosine 0.388 precision@4 (+19%), cobertura
  igual 19/20, 4 turnos melhores / 0 piores** → decisao por medida: flag
  `MEMORY_RERANKING_ENABLED` PERMANECE ON. Latencia rerank 292-693ms
  (mediana 441ms) — ok pre-stream. Achado colateral corrigido com TDD: gate
  few-shot F5.5 recebia rerank_score (escala incomparavel: 60% vs 27%
  passam 0.55) → `_build_similarity_maps` separa sim_map/cosine_map
  (`memory_injection.py` + `tests/agente/sdk/test_rerank_scale_gates.py`,
  6 testes). Observabilidade 1.5: log rerank debug→INFO com latencia
  (`memory_search.py`). Suite sdk+embeddings: 342 passed. Relatorio:
  `relatorios/estudo_contexto_boot_2026-06-09/rerank_ab_2026-06-10.md`.
  PENDENTE 1.5: validar latencia no log `[memory_search] rerank` em PROD
  pos-deploy.
- 2026-06-10 (noite, cont.) — **1.5 VALIDADO em PROD**: deploy `e816deb9a`
  live 20:40Z; turno real 21:04Z logou `[memory_search] rerank: 40
  candidatos -> 20 em 320ms user_id=69` — dentro da faixa do harness.
  **FRENTE 2 executada (codigo completo)**:
  - 2.1 CLASSIFICADO: 144 sem meta.do (109 longas). Origem do fluxo vivo =
    AGENTE via save_memory (created_by 1/18/55 + session_id), NAO daemons.
    Causa raiz: o agente grava `<armadilha>`/`<protocolo>`/pseudo-ns/XML
    escapado com WHEN/DO DENTRO do content e o parse_memory nao tinha
    parser para esses formatos → caia em raw, descartando o que ja existia
    (80/144 tinham when/do no content).
  - 2.2a (novo, decidido pelo 2.1): parser `_parse_xml_operativo`
    (armadilha/protocolo + pseudo-namespace + <tag> bracket + wrapper
    <memoria> delegado) + retry de XML escapado + fix kind heuristica
    tipo-exotico. `memory_format.py` + 6 fixtures REAIS de PROD (ids 910,
    914, 916, 917, 926, 344). 38 testes do serializador verdes. Ganho
    medido contra PROD: 86/144 (60%) recuperam DO sem LLM.
  - 2.2b: validacao INSTRUTIVA no save_memory (`_formato_operativo_error`):
    path operativo sem DO extraivel → erro com template sentinela
    (self-healing). + gap colateral corrigido: update_memory deixava meta
    STALE pos-replace (`_rederive_meta_after_content_change`). 5 testes.
  - 2.3: description da tool + MEMORY_PROTOCOL.md (secao Formato Canonico).
  - 2.4: script `scripts/migrations/2026_06_10_backfill_meta_when_do.py`
    (2 fases: parser → Haiku; content INTACTO, so meta; dry-run default).
    Dry-run revisado contra PROD: fase parser = 102 memorias ganham meta;
    fase haiku = ~58 derivadas + 11 nao-operativas recusadas (~$0.08).
    **APLICACAO EM PROD BLOQUEADA por autorizacao** (escrita direta
    DATABASE_URL_PROD exige OK explicito do Rafael — classifier negou e a
    regra da memoria do projeto confirma). Comando no ponteiro 🔵.
  - 2.5 PENDENTE (depende do backfill aplicado): % meta.do >= 90% das
    operativas + re-rodar ablacao (destilados WHEN/DO em vez de truncate).

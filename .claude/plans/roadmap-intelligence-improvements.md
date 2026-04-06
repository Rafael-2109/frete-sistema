# Roadmap: Melhorias de Inteligencia do Agente

**Gerado**: 2026-04-05 | **Para executar em**: 1 sessao limpa
**Prerequisito**: commit `34e39e61` (4 melhorias ja implementadas)

---

## Contexto

Auditoria profunda revelou 6 problemas reais e 6 gaps de valor no pipeline de inteligencia do agente (12 services, 7 tiers de injecao, 3 paths de busca). As 4 melhorias de maior impacto ja foram implementadas. Este roadmap cobre os itens restantes.

**Ja implementado** (sessao anterior):
- [x] Surfacar conflitos de memoria no briefing (pessoal + empresa + paths)
- [x] KG Hop 2 weight boost (factor 0.3->0.5, cap 0.5->0.7)
- [x] KG Query Tool (13a tool MCP, v2.2.0)
- [x] Empresa memory consolidation (30 files / 12K chars)
- [x] Fix insights routing 500 (cast para JSON column)
- [x] Fix correction_count sempre 0 (incluir user_id=0)
- [x] Fix resolves_to sempre 0 (detectar routing por conteudo)

---

## Fase 1: Quick Wins (< 5 min cada, zero risco)

### 1.1 Habilitar IMPROVEMENT_DIALOGUE

**O que**: Ligar o D8 (dialogo Agent SDK <-> Claude Code) em producao.
**Por que**: Feature completa, wiring 100% funcional, custo ~$0.01/dia. Unica feature deliberadamente off.
**Como**: Setar env var `AGENT_IMPROVEMENT_DIALOGUE=true` no Render (Web Service + Worker).
**Verificacao**: Logs `[IMPROVEMENT]` devem aparecer nos horarios 07:00 e 10:00 UTC.
**Nota**: `register_improvement` MCP tool JA funciona independente do flag — ja pode haver rows na tabela.

### 1.2 Remover dead code `_build_operational_context`

**O que**: Apagar funcao deprecated (~130 LOC) + cache associado.
**Arquivo**: `app/agente/sdk/memory_injection.py` linhas 27-158
**Por que**: Marcada como "desconectada do pipeline desde 2026-03". Conflict surfacing foi reimplementado no briefing. Zero callers.
**Como**:
1. Deletar linhas 27-158 (funcao `_build_operational_context` + `_op_context_cache`)
2. Verificar que nenhum import referencia a funcao (grep `_build_operational_context` — 0 callers)
**Verificacao**: `python -c "from app.agente.sdk.memory_injection import inject_memories_into_prompt"` sem erro.

### 1.3 Remover dead schema `reviewed_at`

**O que**: Coluna `reviewed_at` em `AgentMemory` nunca escrita por nenhum code path.
**Arquivo**: `app/agente/models.py` linha 488
**Por que**: Schema morto — existe no modelo mas nenhum write path a popula.
**Como**:
1. Criar migration `scripts/migrations/drop_reviewed_at.sql`:
   ```sql
   ALTER TABLE agent_memories DROP COLUMN IF EXISTS reviewed_at;
   ```
2. Criar migration `scripts/migrations/drop_reviewed_at.py` (padrao do projeto)
3. Remover `reviewed_at = db.Column(...)` de `models.py`
4. Grep para confirmar: 0 referencias alem da definicao
**Verificacao**: Migration roda sem erro, modelo importa sem erro.

---

## Fase 2: Correcoes Pontuais (15-30 min cada)

### 2.1 Fix `log_system_pitfall` — salvar empresa, nao pessoal

**O que**: Pitfalls do sistema sao conhecimento organizacional, devem ser empresa (user_id=0).
**Arquivo**: `app/agente/tools/memory_mcp_tool.py` — funcao `log_system_pitfall`
**Por que**: Hoje salva em `/memories/system/pitfalls.json` com user_id do caller. A extracao pos-sessao salva armadilhas em `/memories/empresa/armadilhas/`. Dois stores paralelos desconectados.
**Como**:
1. No `log_system_pitfall`, mudar o path de `/memories/system/pitfalls.json` para `/memories/empresa/armadilhas/system-pitfalls.json`
2. Usar `user_id=0` (empresa) em vez do user_id do caller
3. Setar `escopo='empresa'` e `created_by=user_id` (quem originou)
4. Manter backward-compat: se `/memories/system/pitfalls.json` existir, migrar conteudo para o novo path
**Verificacao**: `log_system_pitfall` salva com user_id=0, visivel para todos os usuarios.

### 2.2 Add recommendations para memory health

**O que**: O `recommendations_engine.py` recebe `memory_health` do insights mas nao gera recomendacoes.
**Arquivo**: `app/agente/services/recommendations_engine.py`
**Por que**: Dashboard mostra dados de saude de memoria mas nao sugere acoes. 7 regras existem, faltam 2-3 para memoria.
**Como**: Adicionar regras:
1. `conflicting_memories > 0` → warning "Existem N memorias com conflito pendente — revisar"
2. `cold_ratio > 0.3` → info "30%+ das memorias estao no tier frio — considerar limpeza"
3. `ineffective_ratio > 0.2` → warning "20%+ das memorias nao sao efetivas — consolidacao recomendada"
**Reusar**: Pattern das 7 regras existentes (`_generate_recommendations`, cada regra = dict com `severity`, `message`, `action`).
**Verificacao**: Dashboard insights mostra recomendacoes de memoria quando thresholds sao excedidos.

### 2.3 Fix `clear_all_for_user` cascade

**O que**: `AgentMemory.delete_all_for_user()` usa `.delete(synchronize_session=False)` que NAO dispara cascade.
**Arquivo**: `app/agente/models.py` — metodo `delete_all_for_user` (~linha 638)
**Por que**: Orphana embeddings em `agent_memory_embeddings` e links em `agent_memory_entity_links`. CLAUDE.md do modulo ja alerta sobre isso.
**Como**: Antes do `DELETE FROM agent_memories`, adicionar:
```python
db.session.execute(text("DELETE FROM agent_memory_embeddings WHERE memory_id IN (SELECT id FROM agent_memories WHERE user_id = :uid)"), {"uid": user_id})
db.session.execute(text("DELETE FROM agent_memory_entity_links WHERE memory_id IN (SELECT id FROM agent_memories WHERE user_id = :uid)"), {"uid": user_id})
```
**Verificacao**: `clear_memories` MCP tool nao deixa orphans nas tabelas dependentes.

---

## Fase 3: Melhorias de Qualidade (30-60 min cada)

### 3.1 Sentimento cross-turn (historico)

**O que**: `sentiment_detector.py` processa cada mensagem isoladamente. Sequencias de msgs curtas nao acumulam frustracao.
**Arquivo**: `app/agente/services/sentiment_detector.py`
**Por que**: Um usuario que envia 3 mensagens curtas seguidas sem erro detectado nao e flagado, mesmo que o padrao indique frustracao crescente.
**Como**:
1. Adicionar parametro `recent_scores: list[int] = None` a `detect_frustration()`
2. Se `len(recent_scores) >= 2` e `all(s >= 1 for s in recent_scores[-2:])`, adicionar +2 ao score (trend crescente)
3. No caller (`routes/chat.py:332`), manter um `response_state['sentiment_scores']` (lista dos ultimos 3 scores) e passar ao detector
4. Reset na troca de sessao
**Reusar**: Pattern existente de `response_state` dict que ja e mantido durante o stream.
**Verificacao**: 3 mensagens curtas consecutivas apos erro detectam frustracao (score >= 3).

### 3.2 Deduplicate JSON parsing

**O que**: 4 services tem implementacoes identicas de `_parse_json_response()` (direct parse + regex fallback).
**Arquivos**: `pattern_analyzer.py`, `session_summarizer.py`, `suggestion_generator.py`, `improvement_suggester.py`
**Por que**: Codigo duplicado — risco de divergencia ao corrigir bug em 1 mas nao nos outros.
**Como**:
1. Criar `app/agente/services/_utils.py` com funcao `parse_llm_json_response(text: str) -> dict`
2. Implementacao: try `json.loads(text)`, fallback regex `r'\{[\s\S]*\}'`, fallback `{}`
3. Substituir nos 4 services
**Verificacao**: Todos os 4 services importam de `_utils.py`, funcionalidade identica.

### 3.3 Routes search text fallback

**O que**: `routes_search_tool.py` retorna vazio se embeddings indisponiveis. Outros tools (session_search) tem fallback ILIKE.
**Arquivo**: `app/agente/tools/routes_search_tool.py`
**Por que**: Se pgvector falhar, agente perde capacidade de buscar rotas.
**Como**:
1. Se `search_routes()` retornar vazio ou levantar excecao, fallback para ILIKE em `route_template_embeddings.content`
2. Ou query simples em `url` e `description` das rotas indexadas
**Reusar**: Pattern de fallback de `session_search_tool.py:_search_sessions_ilike()`.
**Verificacao**: Com `EMBEDDINGS_ENABLED=false`, busca de rotas ainda retorna resultados por texto.

---

## Fase 4: Feature Maior (1-2h)

### 4.1 Feedback de sugestoes (track cliques)

**O que**: `suggestion_generator.py` custa ~$0.003/resposta mas nao ha dados sobre quais sugestoes sao uteis.
**Arquivos**: `app/agente/routes/chat.py`, `app/static/agente/js/chat.js`, `app/agente/models.py`
**Por que**: Sem feedback, impossivel otimizar. O agente pode estar gerando sugestoes inuteis sem saber.
**Como**:
1. **Backend**: Nova rota `POST /agente/api/suggestion-feedback` que recebe `{session_id, suggestion_text, clicked: bool}`
2. **Frontend**: No `chat.js`, ao clicar numa sugestao, POST para a rota (best-effort, nao bloqueia)
3. **Storage**: Nova coluna `suggestion_clicks` (JSONB) em `AgentSession`, ou tabela separada `agent_suggestion_feedback`
4. **Insights**: Agregar click-through rate no `insights_service.py` (metricas de suggestions)
**Verificacao**: Clicar numa sugestao registra feedback; insights mostra taxa de cliques.

---

## Ordem de Execucao Recomendada

```
Fase 1 (15 min total):
  1.1 IMPROVEMENT_DIALOGUE=true     [env var]
  1.2 Remover _build_operational_context  [1 arquivo]
  1.3 Remover reviewed_at           [modelo + migration]

Fase 2 (1h total):
  2.1 Fix log_system_pitfall        [1 arquivo]
  2.2 Recommendations memory health [1 arquivo]
  2.3 Fix clear_all_for_user cascade [1 arquivo]

Fase 3 (1.5h total):
  3.1 Sentimento cross-turn         [2 arquivos]
  3.2 Dedup JSON parsing            [5 arquivos]
  3.3 Routes search fallback        [1 arquivo]

Fase 4 (1.5h):
  4.1 Suggestion feedback loop      [4 arquivos + migration]

Total estimado: ~4.5h
```

## Nao incluido neste roadmap (escopo futuro)

- **Hybrid vector+text search** (tsvector) — requer mudanca de infraestrutura pgvector, alto risco
- **Tier 1.5/1.6 string matching** — funciona, apenas fragil. Fix requer reestruturar formato XML de memorias
- **Extracao pos-sessao redundante** — design intencional (ultima execucao captura tudo), custo baixo
- **Render logs agregacao** — requer nova tool MCP ou endpoint de analytics
- **Python fallback scale** — aceitavel no volume atual (<1K records), monitorar

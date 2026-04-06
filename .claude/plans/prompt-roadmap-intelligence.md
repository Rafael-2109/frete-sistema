# Prompt para sessao: Roadmap Intelligence Improvements

Copiar o bloco abaixo e colar como primeiro prompt numa sessao limpa.

---

```
/ralph-wiggum

Implementar o roadmap completo de melhorias de inteligencia do agente.
O plano detalhado esta em: `.claude/plans/roadmap-intelligence-improvements.md`

Leia o roadmap COMPLETO antes de comecar. Siga a ordem de execucao recomendada (Fase 1 → 4).

## Instrucoes especificas por item:

### Fase 1 — Quick Wins
- 1.1: Setar `AGENT_IMPROVEMENT_DIALOGUE=true` no Render via MCP (`mcp__render__update_environment_variables`). Aplicar em AMBOS: Web Service (`srv-d13m38vfte5s738t6p60`) e Worker (`srv-d2muidggjchc73d4segg`). IDs estao em `.claude/references/INFRAESTRUTURA.md`.
- 1.2: Remover `_build_operational_context` + `_op_context_cache` de `app/agente/sdk/memory_injection.py`. Confirmar 0 callers via grep ANTES de deletar.
- 1.3: Remover `reviewed_at` de `app/agente/models.py`. Criar DOIS artefatos de migration (regra CLAUDE.md): `.py` + `.sql`. Grep para confirmar 0 usos.

### Fase 2 — Correcoes
- 2.1: Em `log_system_pitfall` (`memory_mcp_tool.py`), mudar path para `/memories/empresa/armadilhas/system-pitfalls.json`, user_id=0, escopo='empresa'. Manter backward-compat migrando conteudo se path antigo existir.
- 2.2: Em `recommendations_engine.py`, adicionar 3 regras de memory health. O parametro `memory_health` ja e passado pelo insights — verificar a assinatura de `_generate_recommendations` para confirmar.
- 2.3: Em `models.py:delete_all_for_user`, adicionar DELETEs nas tabelas dependentes ANTES do delete principal.

### Fase 3 — Qualidade
- 3.1: Sentimento cross-turn: adicionar `recent_scores` param ao detector + manter scores no `response_state` do caller em `routes/chat.py`.
- 3.2: Criar `app/agente/services/_utils.py` com `parse_llm_json_response()`. Substituir nos 4 services. Manter assinatura compativel.
- 3.3: Em `routes_search_tool.py`, adicionar fallback ILIKE quando pgvector retorna vazio. Seguir pattern de `session_search_tool.py`.

### Fase 4 — Feature
- 4.1: Suggestion feedback. Backend: rota POST em `routes/feedback.py` (ja tem feedback route). Frontend: `chat.js` POST ao clicar sugestao. Storage: JSONB em AgentSession ou tabela nova. Insights: agregar click rate.

## Regras:
- Commitar ao final de CADA fase (4 commits separados)
- Verificar syntax de cada arquivo modificado (`python -c "import ast; ast.parse(open('arquivo').read())"`)
- NAO pular a fase de verificacao de cada item
- Se encontrar ambiguidade: ler o codigo existente antes de assumir
- Migrations: SEMPRE dois artefatos (.py + .sql) — regra do CLAUDE.md
```

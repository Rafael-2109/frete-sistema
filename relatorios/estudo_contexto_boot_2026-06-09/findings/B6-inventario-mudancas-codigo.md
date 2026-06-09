---
name: B6-inventario-mudancas-codigo
description: Inventario completo de pontos de mudanca no codigo implicados pelas decisoes em discussao no estudo de contexto de boot do Agente Web
type: reference
---

# B6 — Inventario de Mudancas de Codigo

**Missao**: mapear arquivo:linha, tipo de mudanca, risco, testes existentes e migracoes de dados para cada das 9 areas de mudanca identificadas nas avaliacoes de Rafael (R-1..R-9) e nos findings A1-A5.

Repo base: `/home/rafaelnascimento/projetos/frete_sistema`

---

## AREA 1: Remocao de skill_hints + world_model

**Decisao: JA TOMADA PELO RAFAEL** (R-1 + confirmacao em A1/A3)

### 1a. Opcao minima (zero codigo — recomendada)
Remover as duas env vars do painel Render:
- `AGENT_SKILL_RAG=true` → remover (default do codigo e `false`)
- `AGENT_WORLD_MODEL_INJECT=true` → remover (default do codigo e `false`)

**Efeito imediato**: os blocos `<skill_hints>` e `<world_model>` param de ser injetados. O codigo permanece intacto para rollback.

### 1b. Remocao completa do codigo

**Geradores (2 funcoes):**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/sdk/context_enrichment.py` | 55-115 | Remover `rank_skills_for_query()` |
| `app/agente/sdk/context_enrichment.py` | 122-155 | Remover `build_skill_hints_block()` |
| `app/agente/sdk/context_enrichment.py` | 162-283 | Remover `build_world_model_block()` + `_resolve_entity_types_for_query()` + `_DOMAIN_ENTITY_TYPES` |
| `app/agente/sdk/context_enrichment.py` | 44 | Remover import `capability_registry` (nivel modulo) |
| `app/agente/sdk/context_enrichment.py` | 48 | Remover import `query_ontology_entities` |

**Feature flags (2 constantes):**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/config/feature_flags.py` | 1005-1017 | Remover bloco `USE_AGENT_SKILL_RAG` |
| `app/agente/config/feature_flags.py` | 1019-1031 | Remover bloco `USE_AGENT_WORLD_MODEL_INJECT` |

**Call sites no hook (2 blocos):**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/sdk/hooks.py` | 1440-1452 | Remover bloco F4/F5 skill_hints (variavel + try/except) |
| `app/agente/sdk/hooks.py` | 1454-1468 | Remover bloco D5 world_model (variavel + try/except) |
| `app/agente/sdk/hooks.py` | 1470 | Simplificar condicional `if session_context or ... skill_hints_context or world_model_context` |
| `app/agente/sdk/hooks.py` | 1471 | Remover `skill_hints_context + world_model_context` da concatenacao `full_context` |
| `app/agente/sdk/hooks.py` | 1478-1480 | Remover linhas de log `skill_hints_chars` e `world_model_chars` do CONTEXT_BUDGET |

**Testes existentes (22 testes — DELETAR ou adaptar):**
| Arquivo | Acao |
|---------|------|
| `tests/agente/sdk/test_context_enrichment.py` | DELETAR inteiro (22 testes: 6 TestRankSkills + 4 TestBuildSkillHints + 5 TestBuildWorldModel + 4 TestFlagsOff + 3 TestHookBestEffort) |

**Documentacao (atualizar, nao deletar):**
| Arquivo | Acao |
|---------|------|
| `docs/blueprint-agente/EXECUCAO.md` | Marcar F4/F5 e D5 como CANCELADOS com justificativa |
| `docs/blueprint-agente/BLUEPRINT_MESTRE.md` | Linha 135: atualizar ONDA 4, remover skill-RAG e world_model |
| `docs/blueprint-agente/VALIDACAO.md` | Linhas 34-35, 78-79, 123-124, 871-903: marcar como cancelados |
| `docs/blueprint-agente/ROADMAP.md` | Linha 132: cancelar O7.4 |
| `docs/blueprint-agente/critica/D-ontologia.md` | Linhas 45, 69: atualizar referencia a world_model |

**Skill gerindo-agente (atualizar registro de flags):**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `.claude/skills/gerindo-agente/scripts/infra.py` | 78-79 | Remover entradas `USE_AGENT_SKILL_RAG` e `USE_AGENT_WORLD_MODEL_INJECT` da tabela de flags |

**Risco**: BAIXO para opcao 1a. MEDIO para 1b (23 pontos de toque mas todos isolados). O modulo `context_enrichment.py` inteiro pode ser deletado — NAO e importado por nenhum outro arquivo alem de `hooks.py`.

**Observacao**: o `capability_registry.py` e usado por outros fluxos (Skill isolation tests, `_collect_principal_skills()`) — NAO deletar.

---

## AREA 2: Filtro de skills por superficie (whitelist web sem dev-only)

**Decisao**: R-3 (Rafael) + R-7 (preferir skills web-only). Baseado em A3 e A5.

### 2a. Adicionar skills com bug na deny-list (CRITICO — bug confirmado A3)

As skills `carregando-motos-assai` e `consultando-venda-loja` estao no listing do principal por omissao — nao aparecem em nenhum grupo de `SKILLS_DELEGADAS_SUBAGENTE`.

| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/config/skills_whitelist.py` | 54-61 | Adicionar `'carregando-motos-assai'` ao `SKILLS_DOMINIO_ASSAI` |
| `app/agente/config/skills_whitelist.py` | 42-48 | Adicionar `'consultando-venda-loja'` ao `SKILLS_DOMINIO_HORA` |

**Testes afetados:**
| Arquivo | Acao |
|---------|------|
| `tests/agente/config/test_skills_whitelist_consolidation.py` | Verificar se os nomes estao cobertos; adicionar assertions |

### 2b. Adicionar skills dev-only a deny-list (R-3 confirmado por A5)

Confirmar que `diagnosticando-banco`, `padronizando-docs` (zero uso em 90 dias), `gerindo-agente` (1 uso — admin) e `consultando-sentry` (2 usos — ambos admins) saem do listing do principal.

**Opcao B1 — Deny-list simples (sem perfil):**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/config/skills_whitelist.py` | 95-104 | Criar novo grupo `SKILLS_DEV_ONLY: Set[str]` com as 4 skills |
| `app/agente/config/skills_whitelist.py` | 99-104 | Adicionar `SKILLS_DEV_ONLY` ao `frozenset(... | SKILLS_DEV_ONLY)` |

**Opcao B2 — Gating por perfil admin (mais granular, mais complexo):**
Nao existe hoje nenhum mecanismo de gating de listing por user_id no `_discover_skills_from_project()` (`client.py:83`). O SDK recebe `skills=` no `connect()` — uma lista fixa por processo. Para gating por usuario seria necessario `set_skills()` por turno (NAO existe no SDK atual). PORTANTO: a opcao viavel hoje e a deny-list simples (B1) ou instrucao no system_prompt para nao usar as 4 skills com usuarios nao-admins.

**Risco**: BAIXO — deny-list nao afeta subagentes (cada um tem seu proprio listing via frontmatter).

---

## AREA 3: Proveniencia de memoria (campo source_session_id)

**Decisao**: RP-2 (Rafael) + achado A2 (BUG por omissao: AgentMemory NAO tem campo session_id de origem).

**Estado atual**: A tabela `agent_memories` NAO tem `source_session_id`. O campo `origem` e texto livre em `meta` JSONB (nao coluna). Apenas `AgentKnowledgeNode` tem `source_session_ids: ARRAY(Text)` (linha 1223 de models.py). O `save_memory` em `memory_mcp_tool.py` captura `get_current_session_id()` mas APENAS para o KG (gateado por `USE_AGENT_ONTOLOGY`, OFF — linhas 2099-2120).

### 3a. Adicionar coluna `source_session_id` a `agent_memories`

**Migration (2 artefatos obrigatorios por regra DEV CLAUDE.md):**
```
scripts/migrations/YYYY_MM_DD_agent_memories_source_session_id.py  — Python + create_app + verify
scripts/migrations/YYYY_MM_DD_agent_memories_source_session_id.sql — SQL idempotente IF NOT EXISTS
```
DDL: `ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS source_session_id TEXT;`
Indice: `CREATE INDEX IF NOT EXISTS idx_agent_memories_source_session_id ON agent_memories(source_session_id);`
Sem FK (conforme pattern existente na linha 1444 de models.py: "Sem FK para agent_sessions.session_id porque sessoes podem ser deletadas").

**Model (1 linha):**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/models.py` | ~610 (apos `created_at`/`updated_at`) | Adicionar `source_session_id = db.Column(db.Text, nullable=True, index=True)` |

**Populacao no save_memory:**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/tools/memory_mcp_tool.py` | ~1990 (criacao do `mem`) | Adicionar `mem.source_session_id = get_current_session_id()` |
| `app/agente/tools/memory_mcp_tool.py` | ~1955 (update do `existing`) | Nao alterar existing.source_session_id (manter a origem original) |

**Exibicao na injecao (opcional):**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/sdk/memory_injection.py` | ~1350-1365 (montagem tier2_texts) | Adicionar `session_id="{mem.source_session_id or ''}"` como atributo no tag `<memory>` |

**Testes afetados:**
| Arquivo | Acao |
|---------|------|
| `tests/agente/services/test_memory_format.py` | Adicionar caso com source_session_id |
| `tests/agente/tools/test_memory_mcp_session_guard.py` | Verificar se source_session_id e populado |

**Migracao de dados**: dados historicos ficam com `source_session_id = NULL`. NAO ha backfill necessario — a informacao nao existe retroativamente.

**Risco**: BAIXO. Coluna nullable, sem FK, zero impacto em queries existentes.

---

## AREA 4: Dedup user_rules vs user_memories

**Bug confirmado em A2**: memorias `priority='mandatory'` entram DUAS vezes no payload — uma como `<rule>` em `<user_rules>` (via `_build_user_rules`, linhas 880-898) e outra como `<memory>` em `<user_memories>` (via Tier 2 semantico, linha 1033: `if r['memory_id'] not in protected_ids`). A causa: `protected_ids` exclui apenas as 3 paths fixos do Tier 1 (`/memories/user.xml`, etc.), NAO os IDs das rules do L1.

### Fix (1 ponto de toque — low risco)

| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/sdk/memory_injection.py` | ~888-898 (bloco L1 user_rules) | Apos construir `rules_block`, popular `protected_ids` com os IDs das rules: `protected_ids.update(r.id for r in rules)` |

**Detalhe**: a query de rules em `memory_injection_rules.py:33-42` retorna objetos `AgentMemory` com `.id`. O bloco L1 precisa retornar esses IDs alem do texto. Opcoes:
- A) `_build_user_rules` retorna `(str, list[int])` em vez de `Optional[str]` (BREAKING — 1 caller)
- B) Fazer a query de rules diretamente no `_load()` de `memory_injection.py` (duplica codigo)
- C) Chamar a query de rules duas vezes — uma para protected_ids, outra para o bloco (ineficiente mas simples)

Opcao A e a mais limpa. Cuida: o unico caller de `_build_user_rules` e `memory_injection.py:887` — mudanca contida.

**Testes afetados:**
| Arquivo | Acao |
|---------|------|
| `tests/agente/test_memory_injection_fase3.py` | Adicionar caso: memoria mandatory NAO aparece duas vezes no payload resultante |
| `tests/agente/test_memory_injection_rules.py` | Verificar que _build_user_rules retorna IDs (se mudar assinatura) |

**Risco**: BAIXO. Impacto: reducao de payload (elimina duplicatas) — melhoria de qualidade.

---

## AREA 5: Gates deterministicos debug_mode / sql_admin

**Status atual** (verificado em hooks.py:1298-1381): ambos os blocos JA sao condicionais — injetados apenas quando user_id esta na lista correta. NAO ha problema de gating.

**O que resta (questao arquitetural):** os textos dos blocos sao longos (330 chars para debug_mode, 380 chars para sql_admin) e poderiam ser mais concisos. Mas isso e optimizacao de conteudo, nao mudanca de codigo estrutural.

**Opcao de encolher texto** (R-1 "reduzir ruido"):
| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/sdk/hooks.py` | 1318-1345 | Reduzir `debug_mode_context` de 8 linhas para 3-4 linhas com pontos chave |
| `app/agente/sdk/hooks.py` | 1361-1374 | Reduzir `sql_admin_context` de 7 linhas para 3-4 linhas |

**Mover para tool description** (alternativa mais radical): NAO recomendado — a tool description e estatica e nao sabe quem e o usuario. O hook e o lugar correto.

**Risco**: BAIXO para encolher texto. ZERO para nao fazer nada (status quo funciona).

---

## AREA 6: Relocacao de stale_empresa / improvement_responses para view gerindo-agente

**Status atual** (verificado em `intersession_briefing.py:73-87`):
- `stale_empresa`: injetada SEMPRE no briefing se count > 20 (linha 410-411)
- `improvement_responses`: injetada APENAS se `AGENT_IMPROVEMENT_DIALOGUE=true` (linha 83-87)

**O problema** (A4/Rafael): esses blocos sao administrativos — "Memorias empresa sem revisao ha 60+ dias" e "respostas do Claude Code ao dialogo de melhoria" — informacoes direcionadas ao Rafael/admin, nao a usuarios finais operacionais.

### Relocacao (2 pontos de toque no briefing + ampliar gerindo-agente)

**No briefing (remover das partes injetadas a todos):**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/services/intersession_briefing.py` | 72-75 | Remover bloco stale_empresa da funcao principal (manter `_check_stale_empresa_memories` como funcao utilitaria) |
| `app/agente/services/intersession_briefing.py` | 82-87 | Remover bloco improvement_responses (a flag ja isola parcialmente, mas o bloco deve sair do path operacional) |

**Na skill gerindo-agente (expor como consulta sob demanda):**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `.claude/skills/gerindo-agente/scripts/diagnostico.py` | Final | Adicionar funcao que chama `_check_stale_empresa_memories()` e `_check_improvement_responses()` |
| `.claude/skills/gerindo-agente/SKILL.md` | Secao de triggers | Adicionar: "memorias empresa sem revisao", "respostas dialogo melhoria" |

**Alternativa menos invasiva**: manter no briefing MAS condicionar por `user_id in ADMIN_IDS` (Rafael=1, Danilo=55, Nara=62). Requer importar `USUARIOS_SQL_ADMIN` no briefing (ja importado em hooks.py).

**Testes afetados:**
| Arquivo | Acao |
|---------|------|
| `tests/agente/` | Nenhum teste direto de intersession_briefing encontrado — verificar se ha cobertura antes de alterar |

**Migracao de dados**: nenhuma.

**Risco**: MEDIO — se removido do briefing e Rafael depende dessas informacoes no boot de sessao, pode haver perda de contexto. Discutir com Rafael antes de executar.

---

## AREA 7: Orcamento/ordenacao de blocos do hook

**Estado atual** (verificado em hooks.py:1470-1471): a concatenacao dos 8 blocos e hardcoded na linha 1471:
```python
full_context = resume_fallback_context + session_context + (additional_context or "") + correction_hint + debug_context + sql_admin_context + skill_hints_context + world_model_context
```

**O que pode mudar**: com a remocao de skill_hints e world_model (Area 1), a linha simplifica para 6 blocos. Com a relocacao de stale_empresa/improvement_responses (Area 6), o `additional_context` (memorias) diminui.

**Orcamento explicitamente controlado**: o budget ja e adaptativo por modelo em `memory_injection.py` (Opus=ilimitado, Sonnet=6000 chars, Haiku=3000 chars, linha 1190-1203). A ordenacao e semanticamente correta: session_context (cache-safe) precede memorias (dinamic).

**Mudanca de ordenacao se necessaria:**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/sdk/hooks.py` | 1471 | Reordenar concatenacao (ex: session_context PRIMEIRO, depois user_rules, depois memories, depois correction_hint, depois debug/admin) |

**Implementacao alternativa via intersession_briefing.py**: a funcao `get_intersession_briefing()` poderia receber um parametro `user_id` e aplicar filtros de admin vs operacional antes de montar o briefing. Isso centraliza a logica de orcamento no lugar certo (o briefing) em vez de no hook.

**Risco**: BAIXO para reordenacao de blocos. MEDIO para refatorar budget no intersession_briefing.

---

## AREA 8: Fonte unica de subagentes (gerar tabela de agents/*.md para prompt e CLAUDE.md)

**Problema identificado em A4/A3**: o `gestor-estoque-odoo` aparece no CLAUDE.md raiz (secao SUBAGENTES) mas NAO na lista `<subagents>` do `system_prompt.md` (verificado: grep retornou vazios). A tabela em CLAUDE.md raiz e mantida manualmente, causando inconsistencia.

**Estado verificado**:
- `system_prompt.md`: tem 13 `<agent name="...">` (linhas 673-724): analista-carteira, especialista-odoo, raio-x-pedido, gestor-carvia, gestor-ssw, auditor-financeiro, controlador-custo-frete, gestor-recebimento, gestor-devolucoes, gestor-estoque-producao, analista-performance-logistica, gestor-motos-assai
- CLAUDE.md raiz (secao SUBAGENTES): lista 14 agentes incluindo `gestor-estoque-odoo` (ausente do system_prompt)
- `.claude/agents/` tem 16 arquivos de agente

**Discrepancias**:
1. `gestor-estoque-odoo.md` existe em `.claude/agents/` e no CLAUDE.md mas NAO no system_prompt `<subagents>`
2. `desenvolvedor-integracao-odoo.md` existe em `.claude/agents/` e no CLAUDE.md com nota "dev-only, nao exposto ao agente web" — correto omitir do system_prompt
3. `orientador-loja.md` existe em `.claude/agents/` mas NAO no CLAUDE.md nem no system_prompt

**Opcoes para fonte unica**:
- **Opcao A (recomendada — zero codigo)**: adicionar `gestor-estoque-odoo` ao system_prompt `<subagents>` (1 bloco `<agent>`) e ao CLAUDE.md, manter atualizacao manual via pre-commit lint
- **Opcao B (automatizacao)**: criar script `scripts/audits/check_agents_consistency.py` que verifica se todo `.claude/agents/*.md` marcado como `exposed_to_principal: true` aparece no system_prompt. Plugar em pre-commit.

**Para adicionar gestor-estoque-odoo ao system_prompt:**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/prompts/system_prompt.md` | ~724 (apos gestor-motos-assai) | Adicionar bloco `<agent name="gestor-estoque-odoo">` com delegate_when e capabilities |

**Cuidado**: adicionar ao system_prompt AUMENTA tokens. Pre-commit `prompt_size_audit.py --check-delta` bloqueara o commit se nao rodar `--update-baseline` junto.

**Testes afetados**: nenhum direto. O `test_system_prompt_p4.py` pode ter assertions sobre o numero de agentes.

**Risco**: BAIXO para adicionar ao system_prompt. MEDIO para automatizar (novo script).

---

## AREA 9: Unificacao lendo-arquivos / lendo-documentos

**Premissa**: A5 mostra ratio 2.8:1 de uso (lendo-arquivos=28 invocacoes vs lendo-documentos=10). Ambas ativas. Rafael nao sinalizou decisao de unificar — esta e uma opcao, nao decisao tomada.

**Escopo tecnico** (se a unificacao for decidida):

**Pontos de toque identificados:**

**1. Skill files (4 arquivos):**
| Arquivo | Acao |
|---------|------|
| `.claude/skills/lendo-arquivos/SKILL.md` | Expandir description para incluir Word/CNAB/OFX |
| `.claude/skills/lendo-arquivos/scripts/ler.py` | Mesclar logica de `ler_doc.py` |
| `.claude/skills/lendo-documentos/SKILL.md` | Deletar (ou manter como alias com redirect) |
| `.claude/skills/lendo-documentos/scripts/ler_doc.py` | Deletar (logica movida para ler.py) |
| `.claude/skills/lendo-documentos/references/formatos-bancarios.md` | Mover para `.claude/skills/lendo-arquivos/references/` |

**2. Deny-list (se `lendo-documentos` for removida do listing):**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/config/skills_whitelist.py` | 99-104 | Adicionar `'lendo-documentos'` ao grupo deprecado/delegado se for unificar |

**3. tool_skill_mapper.py:**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/services/tool_skill_mapper.py` | 108-109 | Remover entrada `'lendo-documentos': 'Importacao de Dados'` |

**4. ROUTING_SKILLS.md (1 referencia):**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `.claude/references/ROUTING_SKILLS.md` | 49 | Remover linha `LER DOCUMENTOS...` ou unificar com linha 48 |
| `.claude/references/ROUTING_SKILLS.md` | 236 | Remover `lendo-documentos` da lista |

**5. Evals/testes (3 arquivos):**
| Arquivo | Acao |
|---------|------|
| `.claude/skills/lendo-arquivos/evals/evals.json` | Adicionar casos Word/CNAB/OFX |
| `.claude/skills/lendo-arquivos/evals/trigger_eval_set.json` | Adicionar triggers de documentos |
| `.claude/skills/lendo-documentos/evals/evals.json` | Deletar (ou migrar casos) |
| `tests/agente/test_agente_files_root_consistency.py` | Linhas 21-22: remover `ler_doc` da lista PATHS (mantendo apenas `ler`) |

**6. Referencia em chat.py:**
| Arquivo | Linha | Acao |
|---------|-------|------|
| `app/agente/routes/chat.py` | 2269 | Comentario `# PDF maior cai para skill lendo-documentos ou metadata` → atualizar para `lendo-arquivos` |

**SCRIPTS.md das duas skills**: atualizar documentacao.

**Risco**: MEDIO — ha usuarios que invocam lendo-documentos (3 usuarios, 10 invocacoes). Garantir que todos os formatos estejam cobertos na skill unificada antes de remover.

---

## Tabela Resumo de Riscos e Dependencias

| Area | Arquivos principais | Tipo | Risco | Pre-requisito |
|------|--------------------|----- |-------|---------------|
| 1a (env vars only) | Render dashboard | config | BAIXO | nenhum |
| 1b (remocao codigo) | context_enrichment.py, hooks.py, feature_flags.py, 22 testes | deletar | BAIXO | 1a validado |
| 2a (bug deny-list) | skills_whitelist.py | editar | BAIXO | nenhum |
| 2b (dev-only fora) | skills_whitelist.py | editar | BAIXO | 2a |
| 3 (source_session_id) | models.py, memory_mcp_tool.py, 2 migrations | criar/editar | BAIXO | migration deployada antes do codigo |
| 4 (dedup rules) | memory_injection.py, memory_injection_rules.py | editar | BAIXO | nenhum |
| 5 (debug/sql text) | hooks.py | editar | BAIXO | opcional |
| 6 (stale_empresa) | intersession_briefing.py, gerindo-agente scripts | editar/criar | MEDIO | conversa com Rafael |
| 7 (ordenacao hook) | hooks.py | editar | BAIXO | areas 1+6 |
| 8 (subagentes SOT) | system_prompt.md | editar | BAIXO | baseline update |
| 9 (unificacao lendo) | 6+ arquivos de skill + 3 testes | editar/deletar | MEDIO | decisao Rafael |

---

## Ordem Recomendada de Execucao

**Fase 0 (imediata, zero codigo)**: Area 1a — remover env vars Render.
**Fase 1 (baixo risco, alta ROI)**: Areas 2a + 2b + 4 + 8 — todas sao `editar` isolado em 1-2 arquivos.
**Fase 2 (media complexidade)**: Area 3 — requer migration + codigo + testes.
**Fase 3 (apos validacao)**: Area 1b — remocao completa do codigo (so apos confirmar que Area 1a esta estavel).
**Fase 4 (decisao separada)**: Areas 6 + 9 — requerem alinhamento com Rafael primeiro.
**Fase 5 (refinamento)**: Areas 5 + 7 — otimizacoes de texto e ordenacao.

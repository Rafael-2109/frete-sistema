---
name: gerindo-agente
description: Esta skill deve ser usada quando o usuario precisa gerenciar o Agente Web — memorias persistentes, sessoes anteriores, padroes aprendidos, perfil comportamental, knowledge graph, diagnosticos de saude, analise de friccao, briefing intersessao ou manutencao do sistema. Exemplos que trigam: "memorias do usuario 5", "sessoes anteriores", "historico de conversas", "padroes aprendidos", "pitfalls do sistema", "knowledge graph", "entidades do grafo", "saude do agente", "health score", "metricas do agente", "memorias nao efetivas", "consolidar memorias", "reindexar embeddings", "cleanup do agente", "memorias empresa", "tier frio", "versoes de memoria", "pendencia resolvida", "conflitos de memoria", "cobertura de embeddings", "sumarizar sessao", "analise de friccao", "sinais de frustracao", "briefing entre sessoes", "briefing do agente", "sessoes do Teams", "modelo usado nas sessoes", "perfil comportamental", "perfil do usuario", "user.xml", "gerar perfil". NAO usar para: consultas SQL ou dados de negocio (usar consultando-sql), lembrar preferencias do PROPRIO Claude Code (usar auto-memory), cotacao de frete (usar cotando-frete), operacoes SSW (usar operando-ssw), Odoo (usar skills Odoo).
allowed-tools: Read, Bash, Glob, Grep
---

# gerindo-agente

Gestao completa do Agente Web: memorias, sessoes, padroes, knowledge graph, diagnosticos e manutencao.

**Substitui**: `memoria-usuario` (deprecated).

## REGRAS CRITICAS

### R1: user_id OBRIGATORIO
TODOS os scripts requerem `--user-id`. Se o usuario nao informar, perguntar antes de executar.

### R2: Operacoes Destrutivas
`delete`, `clear` e `delete` de sessao EXIGEM `--confirm`. SEMPRE avisar o usuario do impacto antes.

### R3: Operacoes com Custo API
`analyze`, `extract`, `summarize` e `consolidate` chamam Sonnet (~$0.003-0.006 por execucao). Avisar o usuario.

### R4: Escopo Empresa
Memorias em `/memories/empresa/*` pertencem a `user_id=0` (Sistema). O script `empresa` do dominio Padrao ja trata isso.

### R5: Formato de Saida
Todos os scripts suportam `--json` para saida JSON. Usar quando o resultado precisa ser processado.

### R6: Limite de Resultados
`--limit` controla o numero de resultados (default 20). Aumentar quando necessario.

## ANTI-ALUCINACAO
- NUNCA inventar user_id — perguntar ao usuario
- NUNCA assumir que uma operacao destrutiva e segura — pedir confirmacao
- Se o script retornar erro, reportar o erro EXATO ao usuario

## DECISION TREE

```
O que o usuario quer?
|
|-- Memorias (CRUD, versoes, cold, pendencias, pitfalls)
|   -> scripts/memoria.py
|   |-- "ver memoria"           -> view --path /memories/...
|   |-- "salvar memoria"        -> save --path ... --content "..."
|   |-- "atualizar memoria"     -> update --path ... --old "..." --new "..."
|   |-- "deletar memoria"       -> delete --path ... --confirm
|   |-- "listar memorias"       -> list [--include-cold] [--category ...]
|   |-- "limpar todas"          -> clear --confirm
|   |-- "buscar no tier frio"   -> search-cold --query "..."
|   |-- "versoes de memoria"    -> versions --path ...
|   |-- "restaurar versao"      -> restore --path ... --version N
|   |-- "resolver pendencia"    -> resolve-pendencia --description "..."
|   |-- "registrar pitfall"     -> log-pitfall --area ... --description "..."
|   |-- "stats de memorias"     -> stats
|
|-- Sessoes (listar, buscar, ver, resumo)
|   -> scripts/sessao.py
|   |-- "sessoes recentes"      -> list [--channel teams|web]
|   |-- "buscar em sessoes"     -> search --query "..."
|   |-- "busca semantica"       -> semantic --query "..."
|   |-- "ver sessao"            -> view --session-id ...
|   |-- "resumo da sessao"      -> summary --session-id ...
|   |-- "usuarios com sessoes"  -> users
|   |-- "deletar sessao"        -> delete --session-id ... --confirm
|
|-- Padroes (patterns, pitfalls, analise, empresa, perfil)
|   -> scripts/padrao.py
|   |-- "padroes aprendidos"    -> patterns
|   |-- "pitfalls do sistema"   -> pitfalls
|   |-- "analisar padroes"      -> analyze
|   |-- "extrair conhecimento"  -> extract --session-id ...
|   |-- "memorias empresa"      -> empresa
|   |-- "perfil comportamental" -> profile
|   |-- "gerar perfil"          -> profile --generate
|
|-- Knowledge Graph (query, entidades, links, relacoes)
|   -> scripts/grafo.py
|   |-- "query no grafo"        -> query --prompt "..."
|   |-- "entidades do grafo"    -> entities [--type ...]
|   |-- "links da entidade"     -> links --entity-id N
|   |-- "relacoes"              -> relations [--entity-name "..."]
|   |-- "stats do grafo"        -> stats
|
|-- Diagnosticos (insights, metricas, saude, efetividade, friccao, briefing)
|   -> scripts/diagnostico.py
|   |-- "insights do agente"    -> insights [--days N]
|   |-- "metricas de memoria"   -> memory-metrics [--days N]
|   |-- "saude do agente"       -> health [--days N]
|   |-- "memorias efetivas"     -> effectiveness
|   |-- "candidatas a cold"     -> cold-candidates
|   |-- "conflitos"             -> conflicts
|   |-- "cobertura embeddings"  -> embedding-coverage
|   |-- "analise de friccao"    -> friction [--days N]
|   |-- "briefing intersessao"  -> briefing
|
|-- Manutencao (consolidar, cold, reindexar, cleanup)
|   -> scripts/manutencao.py
|   |-- "consolidar memorias"   -> consolidate
|   |-- "mover para cold"       -> cold-move
|   |-- "sumarizar sessao"      -> summarize --session-id ...
|   |-- "reindexar memorias"    -> reindex-memories [--reindex]
|   |-- "reindexar sessoes"     -> reindex-sessions [--reindex]
|   |-- "cleanup orfaos"        -> cleanup-orphans
```

## REFERENCIA RAPIDA

### Comando Base
```bash
source .venv/bin/activate && python .claude/skills/gerindo-agente/scripts/{SCRIPT}.py {SUBCOMANDO} --user-id {UID} [--json] [--limit N]
```

### Scripts e Subcomandos

| Script | Subcomandos | Dominio |
|--------|-------------|---------|
| `memoria.py` | view, save, update, delete, list, clear, search-cold, versions, restore, resolve-pendencia, log-pitfall, stats | Memoria |
| `sessao.py` | list, search, semantic, view, summary, users, delete | Sessoes |
| `padrao.py` | patterns, pitfalls, analyze, extract, empresa, profile | Padroes |
| `grafo.py` | query, entities, links, relations, stats | Knowledge Graph |
| `diagnostico.py` | insights, memory-metrics, health, effectiveness, cold-candidates, conflicts, embedding-coverage, friction, briefing | Diagnosticos |
| `manutencao.py` | consolidate, cold-move, summarize, reindex-memories, reindex-sessions, cleanup-orphans | Manutencao |

## TRATAMENTO DE ERROS

| Erro | Causa | Solucao |
|------|-------|---------|
| `Usuario com ID=X nao encontrado` | user_id invalido | Verificar ID correto |
| `Memoria nao encontrada: /path` | Path inexistente | Verificar path com `list` |
| `Texto nao encontrado` | old_string nao existe no update | Verificar conteudo com `view` |
| `Texto encontrado N vezes` | Match nao unico no update | Usar trecho mais longo |
| `Use --confirm para confirmar` | Operacao destrutiva sem flag | Adicionar --confirm |
| `Limite de 20 pitfalls` | Muitos pitfalls | Remover antigos primeiro |
| `Modulo de embeddings nao disponivel` | voyageai nao instalado | Reindexacao indisponivel |
| `Busca semantica falhou` | API key ou embeddings ausentes | Usa fallback textual |

## FEATURE FLAGS RELEVANTES

| Flag | Default | Funcao |
|------|---------|--------|
| `AGENT_AUTO_MEMORY_INJECTION` | true | Injeta memorias automaticamente |
| `AGENT_MEMORY_CONSOLIDATION` | true | Consolidacao automatica |
| `AGENT_PATTERN_LEARNING` | true | Analise de padroes |
| `AGENT_SESSION_SUMMARY` | true | Sumarizacao de sessoes |
| `MEMORY_SEMANTIC_SEARCH` | true | Busca semantica memorias |
| `MEMORY_KNOWLEDGE_GRAPH` | true | Knowledge graph |
| `SESSION_SEMANTIC_SEARCH` | true | Busca semantica sessoes |
| `MEMORY_SEMANTIC_SEARCH` | true | Busca semantica memorias |
| `AGENT_BEHAVIORAL_PROFILE` | true | Gera user.xml (Tier 1) com perfil comportamental |
| `AGENT_BEHAVIORAL_PROFILE_THRESHOLD` | 5 | Threshold de sessoes para geracao de perfil |
| `USE_FRICTION_ANALYSIS` | true | Analise de friccao (5 sinais) |
| `USE_INTERSESSION_BRIEFING` | true | Briefing entre sessoes |
| `USE_SENTIMENT_DETECTION` | true | Deteccao de frustracao (inline) |
| `USE_POST_SESSION_EXTRACTION` | true | Extracao pos-sessao de padroes |
| `POST_SESSION_EXTRACTION_MIN_MESSAGES` | 3 | Threshold minimo de msgs para extract |
| `USE_SESSION_TURN_EMBEDDING` | true | Embedding inline de turnos |
| `USE_DEBUG_MODE` | true | Features admin (target_user_id) |
| `TEAMS_DEFAULT_MODEL` | claude-opus-4-6 | Modelo default do Teams bot |
| `TEAMS_ASYNC_MODE` | true | Modo async do Teams |
| `TEAMS_PROGRESSIVE_STREAMING` | true | Streaming progressivo Teams |

## NOTA: AGENTE TEAMS

O Agente Web tambem opera via Microsoft Teams (bot async). Diferencas arquiteturais:

| Aspecto | Teams | Web |
|---------|-------|-----|
| Session ID | `teams_<hash>` | `<uuid>` |
| Usuario | Auto-cadastrado (`teams_{hash}@teams.nacomgoya.local`) | Existente |
| Modelo | Opus (default: `TEAMS_DEFAULT_MODEL`) | Sonnet |
| AskUser timeout | 120s | 55s |
| Streaming | Progressivo a DB | SSE direto |
| Thread | Non-daemon (async) | Sincrono |
| Max concurrent | 1 por conversation_id | Sem limite |

**Uso na skill**:
- `sessao.py list --channel teams` — filtra sessoes Teams
- `sessao.py list/view` — coluna Modelo mostra qual modelo processou
- Flags Teams: `TEAMS_DEFAULT_MODEL`, `TEAMS_ASYNC_MODE`, `TEAMS_PROGRESSIVE_STREAMING`
- Para debugging de `TeamsTask`: usar `consultando-sql` direto na tabela `teams_tasks`

## EXEMPLOS

```bash
# Listar memorias do usuario 5
source .venv/bin/activate && python .claude/skills/gerindo-agente/scripts/memoria.py list --user-id 5

# Ver padroes aprendidos
source .venv/bin/activate && python .claude/skills/gerindo-agente/scripts/padrao.py patterns --user-id 5

# Health score dos ultimos 7 dias
source .venv/bin/activate && python .claude/skills/gerindo-agente/scripts/diagnostico.py health --user-id 5 --days 7

# Buscar sessoes sobre frete
source .venv/bin/activate && python .claude/skills/gerindo-agente/scripts/sessao.py search --user-id 5 --query "frete"

# Sessoes do Teams
source .venv/bin/activate && python .claude/skills/gerindo-agente/scripts/sessao.py list --user-id 5 --channel teams

# Analise de friccao dos ultimos 7 dias
source .venv/bin/activate && python .claude/skills/gerindo-agente/scripts/diagnostico.py friction --user-id 5 --days 7

# Briefing intersessao
source .venv/bin/activate && python .claude/skills/gerindo-agente/scripts/diagnostico.py briefing --user-id 5

# Ver perfil comportamental
source .venv/bin/activate && python .claude/skills/gerindo-agente/scripts/padrao.py profile --user-id 5

# Gerar/atualizar perfil comportamental (chama Sonnet, ~$0.006)
source .venv/bin/activate && python .claude/skills/gerindo-agente/scripts/padrao.py profile --user-id 5 --generate

# Query no knowledge graph
source .venv/bin/activate && python .claude/skills/gerindo-agente/scripts/grafo.py query --user-id 5 --prompt "transportadora para Manaus"

# Consolidar memorias redundantes
source .venv/bin/activate && python .claude/skills/gerindo-agente/scripts/manutencao.py consolidate --user-id 5
```

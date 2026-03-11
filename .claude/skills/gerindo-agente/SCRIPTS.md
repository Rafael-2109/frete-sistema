# SCRIPTS.md — Referencia Unificada de Parametros

## Argumentos Comuns (todos os scripts)

| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--user-id` | int | Sim | — | ID do usuario no banco |
| `--json` | flag | Nao | false | Saida em formato JSON |
| `--limit` | int | Nao | 20 | Limite de resultados |

---

## memoria.py

### view
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--path` | str | Nao | /memories | Path da memoria |

### save
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--path` | str | Sim | — | Path da memoria |
| `--content` | str | Sim | — | Conteudo da memoria |
| `--skip-dedup` | flag | Nao | false | Pular verificacao de duplicata |

Apos salvar, executa best-effort: dedup check (warning se duplicata), embedding Voyage AI, e pitfall hint detection. Paridade com MCP tool `save_memory`.

### update
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--path` | str | Sim | — | Path da memoria |
| `--old` | str | Sim | — | Texto a substituir (match unico) |
| `--new` | str | Sim | — | Texto novo |

### delete
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--path` | str | Sim | — | Path da memoria |
| `--confirm` | flag | Sim | false | Confirmar exclusao |

### list
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--include-cold` | flag | Nao | false | Incluir tier frio |
| `--category` | str | Nao | None | Filtrar por categoria |

### clear
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--confirm` | flag | Sim | false | Confirmar limpeza total |

### search-cold
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--query` | str | Sim | — | Termo de busca |

### versions
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--path` | str | Sim | — | Path da memoria |

### restore
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--path` | str | Sim | — | Path da memoria |
| `--version` | int | Sim | — | Numero da versao |

### resolve-pendencia
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--description` | str | Sim | — | Descricao da pendencia |

### log-pitfall
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--area` | str | Sim | — | Area (odoo, ssw, banco, api, deploy, sistema) |
| `--description` | str | Sim | — | Descricao do pitfall |

### stats
Sem argumentos adicionais.

---

## sessao.py

### list
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--channel` | str | Nao | None | Filtrar: teams ou web |

### search
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--query` | str | Sim | — | Termo de busca |
| `--channel` | str | Nao | None | Filtrar: teams ou web |

### semantic
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--query` | str | Sim | — | Consulta semantica |

### view
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--session-id` | str | Sim | — | ID da sessao |

### summary
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--session-id` | str | Sim | — | ID da sessao |

### users
Sem argumentos adicionais (admin).

### delete
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--session-id` | str | Sim | — | ID da sessao |
| `--confirm` | flag | Sim | false | Confirmar exclusao |

---

## padrao.py

### patterns
Sem argumentos adicionais.

### pitfalls
Sem argumentos adicionais.

### analyze
Sem argumentos adicionais. Chama Sonnet (~$0.006).

### extract
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--session-id` | str | Sim | — | ID da sessao |

### empresa
Sem argumentos adicionais. Lista memorias com user_id=0.

---

## grafo.py

### query
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--prompt` | str | Sim | — | Consulta em linguagem natural |

### entities
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--type` | str | Nao | None | Tipo de entidade |

### links
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--entity-id` | int | Sim | — | ID da entidade |

### relations
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--entity-name` | str | Nao | None | Filtrar por nome |

### stats
Sem argumentos adicionais.

---

## diagnostico.py

### insights
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Periodo em dias |

### memory-metrics
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Periodo em dias |

### health
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Periodo em dias |

### effectiveness
Sem argumentos adicionais.

### cold-candidates
Sem argumentos adicionais.

### conflicts
Sem argumentos adicionais.

### embedding-coverage
Sem argumentos adicionais.

### friction
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--days` | int | Nao | 30 | Periodo em dias |

Mostra 5 sinais de friccao: queries repetidas, sessoes abandonadas, sinais de frustracao, sessoes sem tools, e score geral (0-100). Controlado pela flag `USE_FRICTION_ANALYSIS`.

### briefing
Sem argumentos adicionais.

Mostra o briefing intersessao atual (XML): erros Odoo, falhas de importacao, alertas de memoria, commits recentes e ultimo intent. Controlado pela flag `USE_INTERSESSION_BRIEFING`.

---

## manutencao.py

### consolidate
Sem argumentos adicionais. Chama Sonnet (~$0.006).

### cold-move
Sem argumentos adicionais.

### summarize
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--session-id` | str | Sim | — | ID da sessao |

### reindex-memories
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--reindex` | flag | Nao | false | Forcar reindexacao total |

### reindex-sessions
| Argumento | Tipo | Obrigatorio | Default | Descricao |
|-----------|------|-------------|---------|-----------|
| `--reindex` | flag | Nao | false | Forcar reindexacao total |

### cleanup-orphans
Sem argumentos adicionais.

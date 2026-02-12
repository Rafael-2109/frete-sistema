# Scripts — Diagnosticando Banco (Detalhes)

Referencia detalhada de parametros, retornos esperados e exemplos de uso.

---

## 1. health_check_banco.py

Executa diagnosticos de saude do banco PostgreSQL.

```bash
source .venv/bin/activate && python .claude/skills/diagnosticando-banco/scripts/health_check_banco.py [opcoes]
```

**Parametros:**

| Param | Obrig | Descricao |
|-------|-------|-----------|
| `--all` / `-a` | * | Executar TODOS os 9 checks |
| `--check` / `-c` | * | Checks especificos (lista separada por espaco) |
| `--limit` / `-l` | Nao | Limite de resultados por check (default: 20) |
| `--resumo` / `-r` | Nao | Apenas resumo executivo (sem dados detalhados) |

\* Pelo menos um obrigatorio (`--all` ou `--check`)

**Checks disponiveis:**

| Check | Descricao | Requer |
|-------|-----------|--------|
| `unused_indexes` | Indices com 0 scans (candidatos a remocao) | — |
| `duplicate_indexes` | Indices com mesma definicao na mesma tabela | — |
| `top_queries` | Top N queries por tempo total de execucao | pg_stat_statements |
| `cache_hit_rate` | Taxa de acerto do buffer cache | — |
| `connections` | Conexoes ativas por estado | — |
| `index_bloat` | Maiores indices com analise de eficiencia | — |
| `table_sizes` | Maiores tabelas por tamanho total | — |
| `vacuum_stats` | Tabelas com dead tuples (candidatas a VACUUM) | — |
| `sequence_capacity` | Uso % das sequences (risco de overflow) | — |

---

## Retorno JSON

### Sucesso (--all --resumo)
```json
{
  "sucesso": true,
  "timestamp": "2026-02-12T13:44:29.392870+00:00",
  "checks_executados": 9,
  "resumo_executivo": {
    "saude_geral": "BOM (com observacoes)",
    "total_problemas": 2,
    "problemas": [
      "20 indices nao usados (22.0 MB desperdicado)",
      "3 tabelas precisam de VACUUM (dead_ratio > 10%)"
    ],
    "destaques": [
      "Cache hit rate: 99.7% (EXCELENTE)",
      "Conexoes: 15/100 (15.0%)",
      "Top tabelas: 223.7 MB"
    ]
  },
  "resultados": {
    "unused_indexes": { "...": "dados resumidos" },
    "cache_hit_rate": { "...": "dados resumidos" }
  }
}
```

### Sucesso (check especifico)
```json
{
  "sucesso": true,
  "timestamp": "2026-02-12T13:44:29+00:00",
  "checks_executados": 1,
  "resultados": {
    "cache_hit_rate": {
      "check": "cache_hit_rate",
      "descricao": "Taxa de acerto do buffer cache (shared_buffers)",
      "status": "EXCELENTE",
      "heap": {
        "hit_rate_pct": 99.72,
        "blocos_cache": 15234567,
        "blocos_disco": 42890
      },
      "index": {
        "hit_rate_pct": 99.85,
        "blocos_cache": 8765432,
        "blocos_disco": 13210
      },
      "acao_sugerida": "Hit rate < 95% indica shared_buffers insuficiente"
    }
  }
}
```

### Check indisponivel (pg_stat_statements)
```json
{
  "resultados": {
    "top_queries": {
      "check": "top_queries",
      "disponivel": false,
      "aviso": "pg_stat_statements nao esta habilitado. Execute: CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
    }
  }
}
```

---

## Exemplos de Uso

### Cenario 1: Visao geral rapida
```
Pergunta: "como esta a saude do banco?"
Comando: health_check_banco.py --all --resumo
```

### Cenario 2: Investigar indices
```
Pergunta: "quais indices nao estao sendo usados?"
Comando: health_check_banco.py --check unused_indexes duplicate_indexes --limit 30
```

### Cenario 3: Performance
```
Pergunta: "quais queries estao mais lentas?"
Comando: health_check_banco.py --check top_queries --limit 15
```

### Cenario 4: Capacidade
```
Pergunta: "tem alguma sequence proxima do limite?"
Comando: health_check_banco.py --check sequence_capacity
```

### Cenario 5: Manutencao
```
Pergunta: "alguma tabela precisa de vacuum?"
Comando: health_check_banco.py --check vacuum_stats table_sizes
```

### Cenario 6: Producao via Render MCP
```
Pergunta: "cache hit rate em producao?"
Acao: Usar mcp__render__query_render_postgres com SQL da SKILL.md
```

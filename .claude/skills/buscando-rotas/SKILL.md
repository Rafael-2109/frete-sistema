---
name: buscando-rotas
description: >-
  Busca semantica de rotas, telas e APIs do sistema por linguagem natural.
  Use quando precisar encontrar "onde fica a tela de X?", "qual URL de Y?",
  "quais APIs existem para Z?", "como acesso a pagina de W?".
  Retorna URL, menu, template, permissao e metadados de ~300 rotas indexadas.
  Nao usar para consultar dados no banco (usar consultando-sql), navegar no
  SSW (usar acessando-ssw), ou monitorar entregas (usar monitorando-entregas).
allowed-tools: Read, Bash, Glob, Grep
---

# Buscando Rotas - Busca Semantica de Rotas e Templates

Skill para **localizar rotas, telas e APIs** do sistema via busca semantica (embeddings).

> **ESCOPO:** Esta skill encontra ONDE algo esta no sistema (URL, menu, template).
> Para consultar DADOS, use `consultando-sql`.
> Para operar no SSW, use `acessando-ssw` ou `operando-ssw`.

## Quando Usar

```
USE buscando-rotas:
├── Localizar tela
│   "Onde fica contas a pagar?"
│   "Qual a URL do dashboard de BI?"
│   "Como acesso a carteira de pedidos?"
│
├── Encontrar API
│   "Quais APIs existem para fretes?"
│   "Endpoint de filtro de separacoes"
│   "API de exportacao financeiro"
│
├── Descobrir menu
│   "Em que menu esta o recebimento?"
│   "Onde acho relatorios de frete?"
│
└── Mapear modulo
    "Todas as telas do financeiro"
    "Rotas do modulo de carteira"
```

## Mapeamento Rapido

Antes de executar o script, tente estes atalhos:

| Modulo | Prefixo de URL | Blueprint |
|--------|---------------|-----------|
| Financeiro | `/financeiro/` | `financeiro` |
| Carteira | `/carteira/` | `carteira` |
| Fretes | `/fretes/` | `fretes` |
| Recebimento | `/recebimento/` | `recebimento` |
| Embarque | `/embarque/` | `embarque` |
| BI/Analytics | `/bi/` | `bi` |
| Pallet | `/pallet/` | `pallet` |

## Scripts

### `buscar_rotas.py` — Busca semantica principal

```bash
source .venv/bin/activate
python .claude/skills/buscando-rotas/scripts/buscar_rotas.py "contas a pagar"
```

**Parametros:**
| Param | Tipo | Default | Descricao |
|-------|------|---------|-----------|
| `query` | str (posicional) | obrigatorio | Texto de busca em linguagem natural |
| `--tipo` | str | None | Filtro: `rota_template` (telas) ou `rota_api` (APIs) |
| `--limit` | int | 10 | Maximo de resultados |

**Retorno JSON:**
```json
{
  "sucesso": true,
  "query": "contas a pagar",
  "total": 3,
  "resultados": [
    {
      "tipo": "rota_template",
      "blueprint_name": "financeiro",
      "function_name": "contas_pagar",
      "url_path": "/financeiro/contas-pagar/",
      "http_methods": "GET",
      "template_path": "financeiro/contas_pagar.html",
      "menu_path": "Financeiro > Contas a Pagar",
      "permission_decorator": "@login_required",
      "source_file": "app/financeiro/routes/contas_pagar_routes.py",
      "similarity": 0.92
    }
  ]
}
```

## Exemplos

```bash
# Buscar tela por nome
python .claude/skills/buscando-rotas/scripts/buscar_rotas.py "contas a pagar"

# Apenas APIs
python .claude/skills/buscando-rotas/scripts/buscar_rotas.py "fretes" --tipo rota_api

# Apenas telas, top 3
python .claude/skills/buscando-rotas/scripts/buscar_rotas.py "dashboard" --tipo rota_template --limit 3

# Buscar por conceito
python .claude/skills/buscando-rotas/scripts/buscar_rotas.py "onde vejo entregas pendentes"
```

## Pre-requisitos

1. Tabela `route_template_embeddings` criada (migration existente)
2. Indexer executado: `python -m app.embeddings.indexers.route_template_indexer`
3. Feature flag `ROUTE_TEMPLATE_SEMANTIC_SEARCH` habilitada (default: `true`)
4. Voyage AI configurado (`VOYAGE_API_KEY` em `.env`)

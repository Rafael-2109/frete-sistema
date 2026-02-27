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

## Mapeamento Rapido de Modulos

**ANTES de executar o script**, tente estes atalhos — cobrem 90% das buscas:

| Modulo | Prefixo de URL | Blueprint | Telas principais |
|--------|---------------|-----------|------------------|
| Financeiro | `/financeiro/` | `financeiro` | contas-pagar, contas-receber, extratos, dashboard |
| Carteira | `/carteira/` | `carteira` | principal, separacoes, agendamentos |
| Fretes | `/fretes/` | `fretes` | fretes, cotacao, tabelas |
| Recebimento | `/recebimento/` | `recebimento` | nf, validacao, conferencia |
| Embarque | `/embarque/` | `embarque` | embarques, romaneios |
| BI/Analytics | `/bi/` | `bi` | dashboard, relatorios |
| Pallet | `/pallet/` | `pallet` | controle, movimentacao |
| CarVia | `/carvia/` | `carvia` | operacoes, subcontratos, faturas |
| Devolucao | `/devolucao/` | `devolucao` | lista, detalhe |
| Custeio | `/custeio/` | `custeio` | dashboard, analise |
| Comercial | `/comercial/` | `comercial` | clientes, propostas |

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

## Diagnostico: Script Retorna 0 Resultados

**ATENCAO:** O script retorna `sucesso: true, total: 0` em dois cenarios:

1. **Tabela `route_template_embeddings` nao existe** — indexador nunca foi executado
2. **Feature flag `ROUTE_TEMPLATE_SEMANTIC_SEARCH` desabilitada**

### Fallback Obrigatorio (quando script retorna 0 resultados)

Se o script retornar `total: 0`, **NAO diga "nao encontrei"**. Use o fallback:

```bash
# Fallback 1: Grep direto nas rotas
grep -rn "def " app/*/routes/*.py | grep -i "TERMO_BUSCA"

# Fallback 2: Buscar blueprint registration
grep -rn "Blueprint\|register_blueprint" app/*/routes/*.py app/*/__init__.py | grep -i "MODULO"

# Fallback 3: Buscar URLs nos templates
grep -rn "url_for\|href=" app/templates/**/*.html | grep -i "TERMO_BUSCA"

# Fallback 4: Listar todas as rotas de um blueprint
grep -rn "@.*\.route\|@.*\.get\|@.*\.post" app/MODULO/routes/*.py
```

**SEMPRE informe ao usuario que a busca semantica esta indisponivel e esta usando busca textual.**

## Regras de Fidelidade

### NUNCA:
- Inventar URLs que nao aparecem no output do script ou no grep
- Assumir template_path sem verificar (pode ser None para APIs)
- Omitir o campo `tipo` (rota_template vs rota_api)
- Apresentar similarity score sem que o script o tenha retornado
- Confundir menu_path (hierarquia no menu) com url_path (URL HTTP)

### SEMPRE:
- Citar url_path EXATAMENTE como o script retornou
- Informar o tipo de rota (tela vs API) ao usuario
- Mencionar blueprint_name para contexto de modulo
- Se retornou 0 resultados, executar fallback com Grep/Glob
- Se o fallback tambem nao encontrou, dizer claramente que nao existe

## Pre-requisitos

1. Tabela `route_template_embeddings` criada (migration existente)
2. Indexer executado: `python -m app.embeddings.indexers.route_template_indexer`
3. Feature flag `ROUTE_TEMPLATE_SEMANTIC_SEARCH` habilitada (default: `true`)
4. Voyage AI configurado (`VOYAGE_API_KEY` em `.env`)

**Se pre-requisitos nao estiverem atendidos:** skill degrada graciosamente para fallback textual.

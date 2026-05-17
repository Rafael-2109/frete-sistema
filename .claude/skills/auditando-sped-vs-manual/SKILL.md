---
name: auditando-sped-vs-manual
description: >-
  Skill EXCLUSIVA do subagente auditor-sped-ecd. Valida SPED parseado
  contra Manual ECD Leiaute 9 em duas dimensoes: (1) DSL formal via
  YAML por registro (tipo, tamanho, obrigatoriedade, valores validos);
  (2) busca semantica em embeddings das regras normativas (util para
  erros PVA em linguagem natural). Use apos parseando-sped-ecd.
allowed-tools: Read, Bash
---

# auditando-sped-vs-manual — Compliance vs Manual ECD

## Quando usar

Apos `parseando-sped-ecd`. Cobre o que `auditando-sped-contabil` nao
cobre: validacoes formais de campo + busca semantica em regras.

## Modo 1: DSL Formal (YAML)

Validacao de campos por registro contra regras em
`.claude/skills/auditando-sped-vs-manual/regras/*.yaml`.

```bash
source .venv/bin/activate
python .claude/skills/auditando-sped-vs-manual/scripts/dsl_engine.py \
    /tmp/sped-parsed-v21.json
```

**Cobertura atual** (5 YAMLs, todos ativos): `I050`, `I155`, `I250`,
`J100`, `J150`. Parser SPED alinhado ao Manual Leiaute 9 desde 2026-05-17
(fix de 13 registros em `parse_sped.py`). DSL engine ainda respeita o
flag `parser_status: misaligned_blocked` em YAMLs caso necessario bloquear
algum por divergencia futura. Adicionar novos blocos via YAML — sem
alterar codigo Python.

**Findings por tipo**:
- `campo_obrigatorio_ausente` — BLOQUEANTE
- `tipo_invalido` — BLOQUEANTE (C vs N)
- `tamanho_invalido` — BLOQUEANTE
- `valor_nao_listado` — BLOQUEANTE

## Modo 2: Busca Hibrida (Exato + Semantico)

`buscar_regras_semantico()` faz busca em **2 camadas**:

1. **Exato** — se a query contem `REGRA_X` ou codigo de registro (`I050`, `J930` etc),
   busca por `regra_name = X` direto. Resultados com `similarity=1.0` + `match_type="exact"`.
2. **Semantico** — vector cosine para o restante (descricao em linguagem natural).
   Exclui chunks ja retornados pelo exato.

### Exemplos de uso

**Lookup por codigo da regra** (mais preciso que cosine):
```python
from app.embeddings.sped_rules_search import buscar_regras_semantico

# Erro do PVA cita REGRA_X → exato vem com similarity=1.0
results = buscar_regras_semantico(
    "REGRA_HIERARQUIA_ARQUIVO falhou no upload",
    limit=5,
)
# results[0]["match_type"] == "exact", regra_name == "REGRA_HIERARQUIA_ARQUIVO"
```

**Busca por linguagem natural** (cosine puro):
```python
results = buscar_regras_semantico(
    "conta sem natureza definida",
    limit=5,
    chunk_type="regra",
)
# results[0]["match_type"] == "semantic", similarity > 0.45
```

**Filtro por registro** (autodetectado se query contem codigo):
```python
# Query "I050 codigo duplicado" -> registro='I050' filtrado automaticamente
results = buscar_regras_semantico("I050 codigo duplicado", limit=10)
```

### Parametros

| Parametro | Default | O que faz |
|-----------|---------|-----------|
| `query` | obrigatorio | Texto livre (cosine) E/OU contendo REGRA_X/codigo registro (exato) |
| `limit` | 10 | Top-K total — exato + semantico combinados |
| `chunk_type` | None | Filtra por tipo (ver tabela abaixo) |
| `bloco` | None | `0`, `C`, `I`, `J`, `K`, `9` |
| `registro` | None (autodetecta de query) | Codigo do registro (sobrepoe deteccao) |
| `min_similarity` | `THRESHOLD_SPED_RULES=0.45` | Corte minimo do cosine |

### Tipos de chunk indexados

| `chunk_type` | Origem | O que e | Quando filtrar |
|--------------|--------|---------|----------------|
| `registro` | `manual_ecd/bloco_*.md` | Definicao completa de 1 registro (I050, J930…) | Lookup geral por registro |
| `regra` | `manual_ecd/bloco_*.md` | `REGRA_X` nomeada com descricao curta | Compliance check de regra especifica |
| `regra_pva` | `manual_ecd/04_regras_validacao.md` | Regras nivel 1/2 (REGRA_HIERARQUIA_ARQUIVO etc) | Erros estruturais que o PVA bloqueia |
| `manual_capitulo` | `manual_ecd/01_*.md`, `02_*.md`, `INDEX.md` | Sections normativas (prazos, hash, encoding) | Pergunta conceitual sobre o leiaute |
| `plano_iteracao` | `SPED_ECD_PLANO.md` (HISTORICO) | Mudanca aplicada em uma versao (V21, V31 PVA…) | "Ja resolvemos isso? Em qual versao?" |
| `categoria_erro` | `SPED_ECD_PLANO.md` (CATEGORIAS) | Diagnostico de erro PVA classificado (CAT 1-25) | Erro PVA reincidente |
| `gotcha` | CLAUDE.md secao GOTCHAS | Armadilhas conhecidas (PVA exige X intercalado…) | "Por que isso quebra?" |
| `decisao` | CLAUDE.md HISTORICO DE VERSOES | Decisoes arquiteturais e motivacao | "Por que escolhemos X em V20?" |
| `procedimento` | CLAUDE.md PROTOCOLO / FLUXO | Passo-a-passo (gerar nova versao, fluxo de fix) | "Como faco para iterar?" |
| `arquitetura` | CLAUDE.md TECH STACK / ARQUITETURA / etc | Referencia estrutural (services, constantes, rotas) | "Onde fica X no codigo?" |
| `referencia` | CLAUDE.md REFERENCIAS | Links / indice | Localizar outras fontes |
| `contexto` | CLAUDE.md CONTEXTO CRITICO | Onboarding para nova sessao | Setup inicial de sessao |

**Pre-requisito**: indexer rodado a cada deploy (ja esta no `build.sh`).
Para forçar reindex local: `python -m app.embeddings.indexers.sped_ecd_rules_indexer`.

## Como adicionar nova regra YAML

Exemplo `I250.yaml`:

```yaml
registro: I250
descricao: Partidas do lancamento
campos:
  - {pos: 2, nome: COD_CTA, tipo: C, tamanho: null, obrigatorio: S}
  - {pos: 3, nome: COD_CCUS, tipo: C, tamanho: null, obrigatorio: N}
  - {pos: 4, nome: VL_DC, tipo: N, tamanho: null, obrigatorio: S, decimal: 2}
  - {pos: 5, nome: IND_DC, tipo: C, tamanho: 1, obrigatorio: S, valores: [D, C]}
```

Engine carrega automaticamente — sem alterar codigo Python.
Usar `tamanho: null` (nao `"-"`) para campos de tamanho variavel.

## NAO usar quando

- Validacao matematica (usar `auditando-sped-contabil`)
- Diff com ground truth (usar `comparando-sped-ground-truth`)
- Pre-upload check inline (usar `sped_ecd_validator.py` interno)

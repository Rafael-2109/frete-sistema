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

**Cobertura inicial**: apenas `I050.yaml`. Adicionar novos blocos
incrementalmente via YAML (sem alterar codigo).

**Findings por tipo**:
- `campo_obrigatorio_ausente` — BLOQUEANTE
- `tipo_invalido` — BLOQUEANTE (C vs N)
- `tamanho_invalido` — BLOQUEANTE
- `valor_nao_listado` — BLOQUEANTE

## Modo 2: Busca Semantica

Quando PVA reporta erro em linguagem natural (ex: "conta sem natureza"),
buscar a regra normativa correspondente:

```python
from app.embeddings.sped_rules_search import buscar_regras_semantico

results = buscar_regras_semantico(
    "conta sem natureza definida",
    limit=5,
    chunk_type="regra"  # filtra so REGRA_X nomeadas
)
for r in results:
    print(f"[{r['similarity']:.2f}] {r['regra_name']}: {r['content']}")
```

**Pre-requisito**: indexer rodado: `python -m app.embeddings.indexers.sped_ecd_rules_indexer`.

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

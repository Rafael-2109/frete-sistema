---
name: comparando-sped-ground-truth
description: >-
  Skill EXCLUSIVA do subagente auditor-sped-ecd. Compara SPED nosso vs
  SPED da contadora (aprovado pela RFB). Detecta: registros ausentes,
  campos sistemicamente vazios. Usar para calibracao com ground truth
  conhecido. NAO compara valores (datas/montantes) — periodo eh
  diferente. Foco em estrutura.
allowed-tools: Read, Bash
---

# comparando-sped-ground-truth — Diff vs SPED Contadora Aprovado RFB

## Quando usar

Apos `parseando-sped-ecd`. Especialmente util para identificar gaps de
cobertura conhecidos do nosso gerador (ex: J932 ausente, J150 sem
hierarquia COD_AGL_SUP populada).

## Como usar

```bash
source .venv/bin/activate

# Pre-requisito: SPED da contadora parseado
python .claude/skills/parseando-sped-ecd/scripts/parse_sped.py \
    ~/Downloads/SpedContabil-61724241000178_*.txt \
    /tmp/sped-ground-truth.json

# Diff
python .claude/skills/comparando-sped-ground-truth/scripts/diff_truth.py \
    /tmp/sped-parsed-v21.json \
    /tmp/sped-ground-truth.json
```

## Categorias de finding

| Tipo | Severidade | Quando |
|---|---|---|
| `registro_ausente_nosso` | BLOQUEANTE/WARNING/INFO | Ground tem, nosso nao tem |
| `registro_extra_nosso` | WARNING | Nosso tem, ground nao tem |
| `campo_vazio_nosso` | WARNING | Campo preenchido no ground, vazio no nosso |

Severidade de `registro_ausente_nosso` depende do registro:
- BLOQUEANTE se obrigatorio (`REGISTROS_OBRIGATORIOS` no script: 21 registros)
- WARNING se condicional (J932, I020, I052, I100, 0150, 0180)
- INFO se opcional

## Limitacoes

- Compara PRIMEIRA ocorrencia de cada registro (eh suficiente para gaps
  sistemicos; nao detecta inconsistencias por linha).
- NAO compara valores (CNPJ, datas, montantes) — periodos diferentes.

## Findings esperados na auditoria V21 (referencia)

Ja documentado em `app/relatorios_fiscais/CLAUDE.md:286-297`:
- J932 ausente (substituicao ECD — se aplicavel)
- I030 formato pode diferir (12 campos completos vs reducao)
- J150 sem hierarquia COD_AGL_SUP

## NAO usar quando

- Auditoria de regras formais (usar `auditando-sped-vs-manual`)
- Validacao matematica (usar `auditando-sped-contabil`)
- SPED da contadora ainda nao disponivel (sem ground truth ainda)

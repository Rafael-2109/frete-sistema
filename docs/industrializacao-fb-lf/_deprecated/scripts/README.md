# Scripts — Industrialização FB↔LF

## Convenção

- Cada script versionado tem prefixo T{NN}_ correspondente à task no `ROADMAP_TASKS.md`.
- Scripts multi-task: `setup_s0.py` (T02–T12 e T33).
- Todos têm modo dry-run por default; só executam com `--execute`.

## Lista

| Script | Tasks cobertas | Tipo |
|---|---|---|
| `T01_validate_intercompany.py` | T01 | Read-only |
| `setup_s0.py` | T02–T12, T33 | Read + Write |

## Como executar (template)

```bash
# 1. Ativar ambiente
source .venv/bin/activate

# 2. Dry-run (mostra o que faria)
python docs/industrializacao-fb-lf/scripts/setup_s0.py --task T02 --dry-run

# 3. Revisar output. Se OK:
python docs/industrializacao-fb-lf/scripts/setup_s0.py --task T02 --execute

# 4. Documentar resultado
cp resultado.txt docs/industrializacao-fb-lf/testes/T02-resultado.md
# Atualizar STATUS.md marcando T02 como ✅ done
```

## IDs constantes

Todos os scripts importam constantes nominais (não hardcoded em queries SQL).
Constantes verificadas em 2026-05-28. Se alguma mudar no Odoo, atualizar no script e em `../CONTEXTO.md`.

## Validação de resultado

Após executar uma task, validar no Odoo via UI ou via query SQL.
Documentar a validação em `../testes/T{NN}-resultado.md` com:
- IDs gerados
- Screenshot ou query de evidência
- Quem executou + timestamp

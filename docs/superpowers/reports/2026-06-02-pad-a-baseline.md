<!-- doc:meta
tipo: state
camada: L1
sot_de: inventario de divida documental/scripts (baseline Onda 0)
hub: docs/superpowers/reports/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# PAD-A — Baseline Onda 0 (2026-06-02)

## Atualizado

2026-06-02. Gerado via:

```
python3 scripts/audits/doc_audit.py --report-only --skip-dup
python3 scripts/audits/script_audit.py --report-only
```

Tempos: doc_audit 0.85s, script_audit 0.33s.

## Estado atual

### Documentos gerenciados — 745 achados (todos bloqueantes)

| Codigo | Qtd | Descricao resumida |
|--------|-----|--------------------|
| C1     | 645 | header `doc:meta` ausente (legado sem migrar) |
| C6     |  40 | arquivo >100 linhas sem TOC |
| C7     |  36 | link morto (link-rot) |
| D3     |  23 | token DB-model nao existe no schema |
| C5     |   1 | secao obrigatoria ausente p/ tipo |
| **Total** | **745** | |

### Scripts operacionais — 209 achados (todos bloqueantes)

| Codigo | Qtd | Descricao resumida |
|--------|-----|--------------------|
| SC-ORFAO  | 101 | script nao indexado em nenhum INDEX/MAPA da zona |
| SC-HEADER | 101 | header de script ausente (`# etapa / # doc-dono / # hub`) |
| SC-ID     |   7 | identificador de script invalido ou ausente |
| **Total** | **209** | |

### Near-duplicate: DEFERIDO por perf

O passo `checks_dup.compare_blocks` e O(n²) sobre todos os pares de docs.
O diagnostico original (workflows `wf_ba978431` e `wf_f1b6c258`, 2026-06-01) ja
quantificou **9 clusters de duplicacao**. O baseline acima foi rodado com
`--skip-dup` para evitar timeout na varredura full de ~684 docs gerenciados.
A analise hub-scoped de near-dup esta planejada para uma onda futura.

## Pendencias

Implicacoes para as Ondas 1-4:

- **Onda 1 (C1 em massa):** migrar header `doc:meta` nos 645 docs legados.
  Foco inicial: `.claude/references/` (22 docs) e `app/*/CLAUDE.md` em massa.
- **Onda 2 (SC-HEADER + SC-ORFAO):** adicionar header e indexar os 101 scripts
  em `scripts/inventario_2026_05/` e `app/odoo/estoque/scripts/`.
- **Onda 3 (C6 + C7 + D3):** TOC em 40 docs grandes; reparar 36 links mortos;
  corrigir 23 tokens DB-model obsoletos em `.claude/references/modelos/`.
- **Onda 4 (near-dup hub-scoped):** rodar `checks_dup` restrito por zona/hub
  para identificar e consolidar os 9 clusters ja quantificados.

# Scripts — Inventário 2026-05

Scripts datados consumidos pela operação de ajuste de inventário da NACOM Goya (FB, CD) + LA FAMIGLIA, decorrente da contagem física de 16/05/2026.

## Ordem de execução

| # | Script | Fase | Reversível? |
|---|--------|------|-------------|
| 00 | `00_audit_odoo_realidade.py` | F0 — descoberta | sim (read-only) |
| 01 | `01_extrair_estoque_odoo.py` | F1 | sim (read-only) |
| 02 | `02_carregar_inventario_xlsx.py` | F1 | sim (gera JSON local) |
| 03 | `03_confrontar_inv_vs_odoo.py` | F2 | sim |
| 04 | `04_propor_ajustes.py` | F3 | sim (INSERT em DB local) |
| 05 | `05_canary_estoque_staging.py` | F4a | sim (reverte no `finally`) |
| 06 | `06_canary_nfs_referencia.py` | F4b | sim (read-only) |
| 07 | `07_executar_onda1_lf_fb.py` | F5 — O1 | **NÃO** (NF emitida = SEFAZ) |
| 08 | `08_executar_onda2_cd_fb.py` | F5 — O2 | **NÃO** |
| 09 | `09_executar_onda3_indisponibilizacao.py` | F5 — O3 | sim (active=True reverte) |
| 10 | `10_reconciliar_pos_ajuste.py` | F6 | sim |

Cada script é idempotente e suporta `--dry-run`. Resultados em `docs/inventario-2026-05/07-relatorios/`.

## Hooks determinísticos

`hooks/` contém regras invioláveis aplicadas pelos services novos em `app/odoo/services/`:

- `pre_execute_nf.py` — bloqueia NF se status ≠ APROVADO, custo divergente >20%, ou valor > teto
- `pos_execute_nf.py` — gera doc atômico em `docs/inventario-2026-05/04-movimentacoes/`
- `pre_lote_rename.py` — bloqueia rename se há `stock.move` em picking não-done
- `pre_execute_indisponibilizacao.py` — exige `canary_passou=True`
- `pre_commit_docs.sh` — bloqueia commit de doc sem frontmatter mínimo

## Spec e plano

- Spec: `docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md`
- Plano: `docs/superpowers/plans/2026-05-17-ajuste-inventario-nacom-lf.md`

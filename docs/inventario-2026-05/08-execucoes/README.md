<!-- doc:meta
tipo: index
camada: L1
sot_de: —
hub: docs/inventario-2026-05/08-execucoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Execuções operacionais — Inventário 2026-05

> **Papel:** Execuções operacionais — Inventário 2026-05.

Esta pasta agrupa **relatórios pós-execução** de operações pontuais realizadas durante o ciclo de inventário 2026-05.

Diferença vs `07-relatorios/`:
- `07-relatorios/` = artefatos gerados por scripts automatizados (Excels, audit_fiscal_LF.md gerado por `09_executar_onda1_bulk.py --modo audit_fiscal`).
- `08-execucoes/` = registros narrativos de operações executadas pelo operador (Rafael ou Claude Code) com decisões manuais — útil para audit trail forense.

---

## Conteúdo

| Arquivo | Data | O que registra |
|---|---|---|
| `EXECUCAO_CADASTRO_NCM_WEIGHT_2026_05_18.md` | 2026-05-18 08:19 | Cadastro de NCM em 3 produtos LF + weight em 2 — descoberta do modelo CIEL IT customizado `l10n_br_ciel_it_account.ncm` |
| `EXECUCAO_ENTRADA_LF_NF627348_2026_05_18.md` | 2026-05-18 08:39 | Entrada manual LF da NF 627348 (PEPINO 168.108 un industrialização) — picking 317316 LF/IN/01734, gotcha company_id no move |
| `EXECUCAO_PRE_ETAPA_CD_2026_05_18.md` | 2026-05-18 03:04-15:00 | Execução pré-etapa CD onda 5 (D007) — 6.746/6.897 ajustes executados, 4 bugs descobertos e fixados (dry-run modificava DB, VARCHAR(20), arredondamento, paralelização) |

---

## Para que servem

Quando precisar:
- Auditar uma operação específica do ciclo (data, operador, IDs Odoo, diferenças vs proposta)
- Reproduzir um padrão (ex: entrada manual de NF FB→LF replicada em sessão futura)
- Investigar gotcha em código que veio de descoberta em execução real

**Ordem de leitura sugerida**: este README → arquivo da operação específica → gotcha relacionado em `02-gotchas/`.

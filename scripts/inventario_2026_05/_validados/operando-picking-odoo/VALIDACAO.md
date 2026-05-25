# `_validados/operando-picking-odoo/` — scripts SUPERADOS pela skill `operando-picking-odoo`

> Mantidos aqui como **museum vivo** após validação cobertura. `sys.path` corrigido (`parents[2]→parents[4]`) e header de arquivado adicionado. Ainda executáveis para retomadas em caso extremo, mas a forma canônica de operar é via skill.

**Skill destino**: [`.claude/skills/operando-picking-odoo/`](../../../../.claude/skills/operando-picking-odoo/)
**Service base**: [`app/odoo/estoque/scripts/picking.py`](../../../../app/odoo/estoque/scripts/picking.py) (StockPickingService)
**Fluxo associado**: [`app/odoo/estoque/fluxos/2.5-cancelar-validar-devolver-picking.md`](../../../../app/odoo/estoque/fluxos/2.5-cancelar-validar-devolver-picking.md)

---

## Scripts arquivados

### 1. `16_cancelar_pickings_fantasmas.py`

**Operação original (PROD 2026-05-18)**: cancelou 854 pickings em `state=assigned/draft` com idade ≥ 7 dias e origin antiga (C24xxxxx) ou sem origin, reservando saldo de lotes alvos da planilha `transf para MIGRACAO.xlsx`.

**Equivalência na skill**:
```bash
python .claude/skills/operando-picking-odoo/scripts/operar_picking.py \
    --modo cancelar \
    --json /tmp/pickings_reservadores_15.json \
    --idade-min 7 \
    --motivo "fantasma >7d" \
    --confirmar
```

**Validação (dry-run vs script-fonte)**:
- Filtro idade (`(hoje - create_date).days >= idade_min`): IDÊNTICO entre script e skill (`operar_picking.carregar_pickings_json`).
- Chamada `svc.cancelar(picking_id, motivo)`: IDÊNTICO (script importa `StockPickingService` via shim; skill importa direto de `app/odoo/estoque/scripts/picking.py`).
- Output JSON com `total/contagem_status/resultados`: skill expõe equivalente em `cancelar_batch()`.
- Idempotência state=cancel: NOOP em ambos.

**Diferenças**:
- Script-fonte salva log em `auditoria/log_16_*.json` automaticamente; skill imprime no stdout (caller redireciona).
- Script-fonte tem `--limite N` para canary; skill também.
- Script-fonte é standalone (1 modo); skill aceita `--modo cancelar/validar/devolver` (mais versátil).

---

## Status C7-C10

- **C7**: `gestor-estoque-odoo` lista `operando-picking-odoo` (skills:); ROUTING_SKILLS amplia triggers; tool_skill_mapper mapeia `'operando-picking-odoo': 'Estoque Odoo (Write)'`; CLAUDE.md raiz atualizada.
- **C8**: fluxo [2.5-cancelar-validar-devolver-picking.md](../../../../app/odoo/estoque/fluxos/2.5-cancelar-validar-devolver-picking.md) criado com 3 sub-casos (a/b/c) cobrindo 100% dos átomos.
- **C9**: 1 script SUPERADO movido (`16_cancelar_pickings_fantasmas`). Scripts COM-BUG ou pipeline-only (executar_fluxo_b_vivas, teste_210030325_lf, fat_lf_05_executar_clean, 09_executar_onda1_bulk, fat_lf_cleanup) permanecem VIVOS — são fluxos compostos cross-skill, não átomos isolados. `substituir_lote_205030410_fb` permanece VIVO — é fluxo cross-skill (Skill 2.4 unreserve + Skill 2 transfer + reassign), não átomo da Skill 5.
- **C10**: MAPA_SCRIPTS atualizado (seção `scripts/picking.py` + `16_cancelar_pickings_fantasmas` SUPERADO).

## Histórico de execução (script-fonte original)

**2026-05-18 ~12h**: rodado em PROD com 854 pickings → `CANCELED` em todos. Liberou reservas dos lotes alvos para transferência MIGRAÇÃO. Detalhes em `docs/inventario-2026-05/02-gotchas/` (G021/G022 dependeram dessa liberação).

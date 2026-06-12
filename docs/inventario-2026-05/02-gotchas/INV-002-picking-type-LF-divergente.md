<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-12
-->
# INV-002 — Divergência picking_type_id da LF

> **Papel:** INV-002 — Divergência picking_type_id da LF.

> **Nota:** Renomeado de G002 em 2026-06-12 (T1.3) — colisao com a serie G0xx do dominio estoque `app/odoo/estoque/`.

**Descoberto em:** 2026-05-17 (audit F0)
**Severidade:** MÉDIA — afeta consumidor de `.claude/references/odoo/IDS_FIXOS.md`

## Contexto

`.claude/references/odoo/IDS_FIXOS.md:36` documenta:

```
| LF (5)    | 16  | Recebimento (LF)  | ⚠️ ID correto mas NAO configurado em CONFIG_POR_EMPRESA |
```

## Achado do audit

Em `company_id=5` (LF), audit listou 3 picking types `code='incoming'`:

- `id=19` — **Recebimento (LF)**
- `id=24` — Devoluções (LF)
- `id=64` — Recebimentos Industrialização (LF)

**Nenhum tem `id=16`** entre os incoming da company 5.

## Hipóteses

1. ID 16 está em outro `code` (talvez `internal` ou `outgoing`)? Verificar com search sem filtro `code`
2. ID 16 foi reconfigurado/migrado e `IDS_FIXOS.md` não foi atualizado
3. ID 16 pertence a outra company

## Ação proposta

1. Buscar `stock.picking.type` com `id=16` para confirmar qual é
2. Atualizar `.claude/references/odoo/IDS_FIXOS.md` com o ID correto (19 ou outro confirmado)
3. Atualizar `app/recebimento/services/recebimento_lf_odoo_service.py` se referenciar 16 diretamente

---
## Resultado da investigação

- `stock.picking.type id=16` existe e tem características:
  - `id`: 16
  - `name`: Conferência (CD)
  - `code`: internal
  - `company_id`: [4, 'NACOM GOYA - CD']
  - `sequence_code`: CD/PACK
  - `default_location_src_id`: [36, 'CD/Pré-separação']
  - `default_location_dest_id`: [36, 'CD/Pré-separação']
  - `active`: False

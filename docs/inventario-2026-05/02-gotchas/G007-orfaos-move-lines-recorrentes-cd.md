# G007 — Orfaos de `stock.move.line` recorrentes no CD

**Data**: 2026-05-18
**Descoberto durante**: execucao pre-etapa CD (D007)
**Impacto**: 825 orfaos no CD acumulados em 18 meses, **continua sendo criado**

---

## Sintoma

`stock.move.line` no Odoo CIEL IT do CD (company_id=4) com:
- `move_id = False` (sem stock.move pai)
- `picking_id = False` (sem stock.picking pai)
- `state = False` (sem estado proprio)
- `reference = False`, `origin = False`
- `quantity > 0` (segura reserva no quant)

**Consequencia**: o `stock.quant.reserved_quantity` soma essas linhas
fantasma e bloqueia operacoes futuras (transferencias, vendas) com mensagem
"reservadas em pickings ativos" — mesmo nao havendo picking algum.

---

## Volumetria descoberta

**Snapshot 18/05/2026**:
- **825 orfaos** no CD (apos limpeza de 526 da pre-etapa, sobraram 299 fora do escopo Cat 2)
- Distribuicao temporal (continua sendo criado!):

| Mes | Qtd | Mes | Qtd |
|---|---|---|---|
| 2024-08 | 17 | 2025-09 | 6 |
| 2024-09 | 9 | 2025-10 | 69 |
| 2024-10 | 64 | **2025-11** | **138** ← pico |
| 2024-11 | 6 | 2025-12 | 12 |
| 2024-12 | 18 | 2026-01 | 7 |
| **2025-02** | **80** | **2026-02** | **96** |
| **2025-03** | **82** | 2026-03 | 61 |
| 2025-05 | 9 | **2026-04** | **123** ← recente |
| 2025-06 | 16 | | |
| 2025-07 | 5 | | |
| 2025-08 | 7 | | |

- Por destino: 743 (90%) → "CD/Estoque" (auto-referencia), 72 (9%) → "Em Transito Filiais", 10 (1%) → "CD/Saida"

---

## Causa provavel

Sao **residuos de operacoes canceladas ou batches que crasharam** no Odoo:
- Operador abre inventory adjustment, edita, fecha aba sem confirmar/cancelar
- Batches de redistribuicao interna que travaram em meio a operacao
- Reservas de pickings deletados sem limpar move_lines

Picos coincidem com **fins de mes** (rotinas de fechamento) — sugere batch
mensal.

---

## Limpeza segura

Filtro estrito (operacao testada em 526 unlinks com 0 falhas):
```python
domain = [
    ['company_id', '=', 4],
    ['move_id', '=', False],
    ['picking_id', '=', False],
    ['state', '=', False],
    ['quantity', '>', 0],
]
ids = odoo.execute_kw('stock.move.line', 'search', [domain])
odoo.execute_kw('stock.move.line', 'unlink', [ids])
```

**ATENCAO**: somente unlink nao basta — recompute manual de
`reserved_quantity` e' obrigatorio. Ver **G006**.

---

## Recomendacao operacional

- 299 orfaos remanescentes no CD (apos limpeza pre-etapa D007) — limpar
  pontualmente caso bloqueiem operacao futura, usando os scripts
  `/tmp/delete_orphan_movelines.py` + `/tmp/fix_reserved_quantity.py`

---

## Script de limpeza (template)

```python
# /tmp/delete_orphans_b_minimo.py (versao Cat 2)
# /tmp/delete_orphan_movelines.py (versao geral)
# /tmp/fix_reserved_quantity.py (recompute reservas)

# Workflow:
# 1. dry-run para listar volume
# 2. backup JSON dos IDs
# 3. unlink em batches de 100
# 4. fix_reserved_quantity para recompute
# 5. validacao
```

Ver scripts em `/tmp/` (sessao 2026-05-18). Os 3 funcionam em conjunto.

---

## Referencias

- D007: `00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md`
- G006: `02-gotchas/G006-reserved-quantity-nao-recompute-apos-unlink.md`
- Backup orfaos limpos: `/tmp/backup_inventario_2026_05/orfaos_b_min_cd_20260518_060842.json`
- Relatorio execucao: `EXECUCAO_PRE_ETAPA_CD_2026_05_18.md`

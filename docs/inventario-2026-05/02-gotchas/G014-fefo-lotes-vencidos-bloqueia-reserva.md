# G014 — FEFO bloqueia auto-reserva em lotes vencidos (PEPINO IND)

**Descoberta**: 2026-05-18 sub-piloto bulk (apos fix L18-L21)
**Severidade**: HIGH (estoque "fantasma" — 73k kg parecem livres mas nao reservam)
**Status**: PRECISA TRATAMENTO MANUAL (config Odoo CIEL IT, nao bug de codigo)

---

## Sintoma

`action_assign` retorna OK mas `move_lines=[]`. Picking continua em `state=confirmed`
apesar de estoque agregado abundante no Odoo.

Para PEPINO IND (103000011) em FB/Estoque (location_id=8):
```
TOTAL agregado FB: 151.809 kg (em 22 quants)
TOTAL FB/Estoque livre: 72.893 kg (em 4 lotes)
TOTAL livre em lotes VALIDOS (nao vencidos): 0.00 kg
```

Demand do picking 317312: 149.976 kg → reserva 0.

## Causa raiz

Odoo CIEL IT tem regra FEFO (First Expired First Out) habilitada:
- `action_assign` NAO reserva automaticamente quants em lotes VENCIDOS
  (lot.expiration_date < hoje)
- Estoque livre em lotes vencidos aparece nos `stock.quant` mas e' invisivel
  para a logica de reserva

PEPINO IND tem TODOS os lotes nao-vencidos JA reservados por outros pickings:
| lote | qty | reservado | livre | exp |
|---|---|---|---|---|
| 032/24-25 | 42917 | 0 | 42917 | 2026-01-15 (VENCIDO) |
| 15/01/2025 | 14325 | 0 | 14325 | 2026-02-12 (VENCIDO) |
| 0308/24 | 9000 | 0 | 9000 | 2025-08-03 (VENCIDO) |
| 0110/24 | 6650 | 0 | 6650 | 2025-10-01 (VENCIDO) |
| 0208/24 | 15200 | 15200 | 0 | 2025-08-02 (VENCIDO) |
| 0909 | 362.52 | 362.52 | 0 | 2026-09-09 (OK, reservado) |
| 28/10 | 306.34 | 306.34 | 0 | 2026-10-29 (OK, reservado) |
| ... | ... | ... | 0 | ... (todos OK reservados) |

Sub-piloto historico (picking 317297, 2026-05-18 06:00) tambem teve PEPINO IND
move 1078359 cancelado pelo mesmo motivo (apenas ALHO GRANULADO passou).

## Solucoes possiveis

### A. Cancelar ajuste + tratar manualmente (recomendado para sub-piloto)

```sql
UPDATE ajuste_estoque_inventario
SET status='REJEITADO',
    fase_pipeline=NULL,
    erro_msg='G014: PEPINO IND sem lote valido livre em FB. Lotes vencidos: 72k livres mas Odoo FEFO bloqueia auto-reserva. Tratar via UI com forcar lote vencido OU producao nova.'
WHERE id IN (162425, 170143);
```

E cancelar picking 317312 no Odoo.

### B. Forcar via UI (manual)

Abrir picking 317312 no UI Odoo, manualmente selecionar lote vencido na
move_line + qty_done + validar. Odoo emite aviso "lote vencido" mas permite.

### C. Refator estrutural (LF completa)

Para evitar esse bloqueio em massa quando rodar bulk de 660 produtos:

1. Em `etapa_b_pickings`, ao consultar quants do produto na origem:
   - Filtrar APENAS lotes nao vencidos (`expiration_date >= hoje OR expiration_date IS NULL`)
   - Se demand > soma_livre_validos: criar ajuste compensatorio em vez de
     incluir no picking

2. Adicionar audit pre-execucao:
```sql
-- Identificar produtos com 0 estoque livre em lotes validos
-- (vai falhar action_assign mesmo tendo quants agregados)
```

3. Para casos LF→FB (PERDA), o problema NAO afeta (estoque LF nao tem
   essas restricoes). Afeta apenas FB→LF/CD (INDUSTRIALIZACAO_FB_LF,
   TRANSFERIR_FB_CD).

## Como identificar produtos afetados antes de rodar bulk

```python
# Para cada produto com acao INDUSTRIALIZACAO_FB_LF na fila:
# verificar se ha pelo menos 1 lote NAO VENCIDO com qty > 0 livre
from datetime import datetime
HOJE = datetime.utcnow()

quants = odoo.search_read('stock.quant',
    [['product_id', '=', pid], ['location_id', '=', LOC_FB_ESTOQUE],
     ['quantity', '>', 0]],
    ['lot_id', 'quantity', 'reserved_quantity'])

livre_validos = 0
for q in quants:
    if not q['lot_id']: continue
    lot = odoo.read('stock.lot', [q['lot_id'][0]], ['expiration_date'])[0]
    exp = lot.get('expiration_date')
    if exp:
        exp_dt = datetime.strptime(exp.split(' ')[0], '%Y-%m-%d')
        if exp_dt < HOJE: continue  # SKIP vencido
    livre = q['quantity'] - (q.get('reserved_quantity') or 0)
    livre_validos += max(0, livre)

if livre_validos < demand:
    # MARCAR ajuste para tratamento manual
    pass
```

## Ref

- Sub-piloto historico picking 317297 (mesma falha 2026-05-18 06:00)
- Sub-piloto atual picking 317312 (mesma falha 2026-05-18 08:33)
- D006 secao a ser adicionada

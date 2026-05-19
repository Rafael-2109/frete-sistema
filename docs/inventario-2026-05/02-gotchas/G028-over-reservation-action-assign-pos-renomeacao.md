# G028 — Over-reservation em action_assign após renomeação de lote

**Descoberta**: 2026-05-18 sessao 3 tarde (batch 30 e 15 prods LF)
**Severidade**: CRITICAL (bloqueava 70-100% dos pickings PERDA em batches LF)
**Status**: ✅ **FIX IMPLEMENTADO** (`StockPickingService.consolidar_move_lines`)

---

## Sintoma

Após ETAPA A renomear lotes (`action_apply_inventory`), a ETAPA B subsequente
sofre over-reservation extrema no `action_assign`:

```
prod=ACIDO ASCORBICO  demand=0.22    reserved=100.44   ratio=459.66x ⚠️
prod=ACIDO CITRICO    demand=2426.22 reserved=5472.58  ratio=2.26x
prod=ACUCAR           demand=250.00  reserved=812.00   ratio=3.25x
prod=BENZOATO         demand=1563.97 reserved=3355.12  ratio=2.14x
prod=VINAGRE          demand=2530.58 reserved=129061.15 ratio=51.00x ⚠️
prod=SACARINA         demand=3.95    reserved=107.90   ratio=27.31x ⚠️
```

`button_validate` rejeita com `Fault 2: "estoque negativo"` em batches PERDA.

## Causa raiz

Quando `stock.quant.action_apply_inventory` renomeia um lote (move saldo
do lote velho para o lote novo), **reservas órfãs no lote velho não são
liberadas automaticamente**.

Quando `action_assign` do picking PERDA subsequente roda para o mesmo
produto, ele reserva em **AMBOS**:
- Lote velho (onde reservas órfãs permanecem fantasmas)
- Lote novo (que recebeu o saldo via G014/RENOMEAR)

Resultado: `sum(move_line.quantity)` >> `move.product_uom_qty` (demand).

**NÃO é problema de location** — investigado em 2026-05-18: LF tem 683
sub-locations, mas saldo dos produtos do batch fica direto em LF/Estoque(42).
`child_of=42` retorna idêntico a `=42`.

**NÃO é problema de timing** — testado com sleep 90s entre A e B, e sleep
5s entre pickings em B. Reservas órfãs permanecem mesmo com pausas longas.

## Fix implementado

`StockPickingService.consolidar_move_lines(picking_id, linhas_esperadas)`
(linha ~143).

**Algoritmo**:
1. Caller passa `linhas_esperadas` = [{product_id, lot_name, quantity}, ...]
   derivado dos `AjusteEstoqueInventario` (lote_origem + qtd_ajuste exatos).
2. Para cada `(product_id, lot_name)` esperado:
   - Encontrar `stock.move.line` correspondente
   - Setar `quantity=qty_esperada, qty_done=qty_esperada`
3. Para cada `move.move_line_ids` **NÃO** em linhas_esperadas:
   - Zerar `quantity=0, qty_done=0` (libera reserva órfã)

**Chamado** em `StockPickingService.validar(picking_id, linhas_esperadas)`
ANTES de `button_validate`. Aqui os campos computed do `stock.move` já
foram atualizados pelos writes de `preencher_qty_done` e
`ajustar_qty_done_pelo_disponivel`.

## Padrão herdado de

`RecebimentoLfOdooService.processar_recebimento` em
`app/recebimento/services/recebimento_lf_odoo_service.py:2336-2395`:

```python
# IMPORTANTE: O Odoo auto-cria move_lines via action_assign,
# potencialmente uma por lote/quant. Precisamos consolidar:
# preencher APENAS a primeira move_line de cada produto e zerar extras.
for extra_line in product_lines[1:]:
    odoo.write('stock.move.line', extra_line['id'], {
        'qty_done': 0, 'quantity': 0
    })
```

## Resultado em batches LF (validação 2026-05-18)

| Batch | Sem G028 | Com G028 v4 |
|-------|----------|-------------|
| 50 prods (10/picking) | 1/6 done (17%) | n/a |
| 30 prods (5/picking) | 1/6 done (17%) | n/a |
| 15 prods (5/picking) — primeira tentativa | 0/3 done | n/a |
| **15 prods (5/picking) — G028 v4 ativo** | n/a | **2/3 done (67%)** ✅ |

Aumento de taxa de sucesso PERDA de 17% → 67% (3.9x).

Picking que ainda falhou no batch v4 foi por outro motivo (ajuste com
`lote_origem=NULL` em produto com `tracking=lot` — fix separado, ver
"resolver lote antes do picking" em `09_executar_onda1_bulk.py`).

## Refatoração paralela em `09_executar_onda1_bulk.py`

Substituiu FIFO automático de quants por **`lote_origem` + `qtd_ajuste`
EXATOS dos ajustes**:

```python
# G023: respeitar lote_origem dos AJUSTES em vez de FIFO automatico de quants
ajustes_com_lote = [(aj, aj.lote_origem, abs(aj.qtd_ajuste)) for aj in ajs if aj.lote_origem]
ajustes_sem_lote = [(aj, abs(aj.qtd_ajuste)) for aj in ajs if not aj.lote_origem]

# Linhas para ajustes COM lote: 1:1
for aj, lote, qty in ajustes_com_lote:
    linhas.append({'lot_name': lote, 'quantity': qty, ...})

# Ajustes SEM lote: resolver via FIFO de quants_validos (G014-aware)
if ajustes_sem_lote:
    qty_a_distribuir = sum(q for _, q in ajustes_sem_lote)
    for q in quants_validos:
        livre = quant - reservas_de_terceiros - ja_alocado
        ...
```

## Ref

- `app/odoo/services/stock_picking_service.py:142-265` (consolidar_move_lines)
- `app/odoo/services/stock_picking_service.py:425-451` (chamada em validar)
- `app/odoo/services/inventario_pipeline_service.py:704-707` (passar linhas_esperadas)
- `scripts/inventario_2026_05/09_executar_onda1_bulk.py:919-985` (geração linhas baseada em ajustes)
- G021 (race A↔B) e G022 (revalidar saldo) — explicam o cenário
- `app/recebimento/services/recebimento_lf_odoo_service.py:2336-2395` (padrão herdado)

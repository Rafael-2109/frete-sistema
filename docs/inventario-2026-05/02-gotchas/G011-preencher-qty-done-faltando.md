# G011 — preencher_qty_done faltando no pipeline (cascateia L20/L21)

**Descoberta**: 2026-05-18 sub-piloto bulk (re-execucao apos G010 fix)
**Severidade**: CRITICAL (raiz de L19/L20/L21 — bloqueia ANY picking do pipeline)
**Status**: corrigido em `inventario_pipeline_service.py` f5b_validar_pickings + `09_executar_onda1_bulk.py` etapa_b_pickings

---

## Sintoma

Picking criado, action_assign passa, mas:
- Moves ficam com `move_line_ids=[]` (sem move_lines)
- `ajustar_qty_done_pelo_disponivel` reduz `product_uom_qty` (demand) para 0
- `button_validate` falha: "Nao e possivel validar uma transferencia se nao
  houver quantidades reservadas. Para forcar a transferencia, codifique as
  quantidades."
- Em cascata: `action_liberar_faturamento` falha:
  - "Voce deve informar o Peso Liquido para liberar o faturamento" (G012)
  - "Voce deve informar a Quantidade de Volumes para liberar o faturamento" (G013)

## Causa raiz

Fluxo `f5b_validar_pickings` faltava 1 etapa critica:

```
1. criar_transferencia    -> cria picking + moves (SEM lot_name/lot_id)
2. action_confirm         -> draft -> confirmed
3. action_assign          -> cria move_lines com qty_done=0
4. ajustar_qty_done       -> reduz demand para sum(qty_done)=0  ❌ BUG
5. button_validate        -> falha (sem reserva)
```

`action_assign` cria move_lines com `quantity` (qty a separar) mas `qty_done=0`.
O `qty_done` precisa ser preenchido APOS para o picking funcionar.

`ajustar_qty_done_pelo_disponivel` interpretou `qty_done=0` como
"reservou 0" (em vez de "ainda nao preenchido") e reduziu `demand` a 0.

Consequencia: peso/volumes computados via `@api.depends('move_ids.qty_done')`
no CIEL IT ficam 0 → action_liberar_faturamento falha (G012/G013).

## Solucao

Inserir `preencher_qty_done` entre `action_assign` e `ajustar_qty_done`:

```
1. criar_transferencia
2. action_confirm
3. action_assign
4. preencher_qty_done(pid, linhas)   ✅ NOVO — qty_done = quantity
5. ajustar_qty_done                  → so reduz se realmente sobra
6. button_validate                   ✅
```

Implementacao:

### inventario_pipeline_service.py

```python
def f5b_validar_pickings(
    self, ajustes: List, executado_por: str = 'sistema',
    linhas_por_picking: Optional[Dict[int, List[Dict]]] = None,
) -> Dict[int, bool]:
    """Para cada picking distinto: confirmar_e_reservar + preencher + validar."""
    ...
    def _io(pid):
        ...
        self.picking_svc.confirmar_e_reservar(pid)
        # L19 fix: popular qty_done DEPOIS de action_assign
        linhas = linhas_por_picking.get(pid)
        if linhas:
            try:
                self.picking_svc.preencher_qty_done(pid, linhas)
            except Exception as e:
                logger.warning(...)
        # ajustar_qty_done agora opera com qty_done correto
        try:
            self.picking_svc.ajustar_qty_done_pelo_disponivel(pid)
        ...
        self.picking_svc.validar(pid)
```

### 09_executar_onda1_bulk.py

```python
# Passar linhas para f5b:
pipeline_svc.f5b_validar_pickings(
    ajustes_chunk, executado_por=executado_por,
    linhas_por_picking={picking_id: linhas},
)
```

## Validacao

Picking 317295 (sub-piloto anterior OK):
- 3 moves, state=done
- peso_liquido=742.76, volumes=108 ✓
- Tudo computou corretamente APOS preencher qty_done

Pickings 317309/317310 (FALHARAM antes do fix):
- 5 moves cada, peso_liquido=0, volumes=0
- Cancelados (apenas draft/confirmed, sem invoice)

## Ref

- G012 (L20 peso_liquido consequencia)
- G013 (L21 quantidade_volumes consequencia)
- D006 secao L19 (a ser adicionada)
- `app/odoo/services/stock_picking_service.py` linha 137 `preencher_qty_done`

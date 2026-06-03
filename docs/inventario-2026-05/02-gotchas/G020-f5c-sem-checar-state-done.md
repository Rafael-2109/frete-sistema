<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# G020 — f5c liberar_faturamento NÃO checa pre-condicao state=done

> **Papel:** G020 — f5c liberar_faturamento NÃO checa pre-condicao state=done.

**Descoberta**: 2026-05-18 sessao 2 manha (teste 100 produtos LF)
**Severidade**: MED (cascateia G019; robo CIEL IT nunca cria invoice)
**Status**: ✅ IMPLEMENTADO (atualizado 2026-05-24 v3 — fix esta em `app/odoo/estoque/scripts/picking.py` linhas 500-525, capinado de `app/odoo/services/`; cobertura 3 testes pytest em `test_stock_picking_service.py`: `test_liberar_faturamento_chama_action`, `test_liberar_faturamento_state_nao_done_raises`, `test_liberar_faturamento_propaga_erro_negocio`). Note que `liberar_faturamento` NAO e exposto na skill `operando-picking-odoo` (so saida via Skill 8 `faturando-odoo`); o invariante esta no service e tras a garantia para o pipeline.

---

## Sintoma

`f5c_liberar_faturamento` chama `action_liberar_faturamento` em pickings
que ainda estao em `state=assigned` (porque G019 false-positive marcou
F5b_VALIDADO no DB local). O Odoo ACEITA a chamada sem erro mas o robo
CIEL IT nao cria invoice para picking nao-done.

Resultado: ajustes marcam `fase=F5c_LIBERADO` mas o picking continua em
assigned e nenhuma invoice e' jamais criada.

## Root cause

`StockPickingService.liberar_faturamento()` em
`stock_picking_service.py:290-314`:

```python
def liberar_faturamento(self, picking_id: int) -> None:
    """action_liberar_faturamento — sinaliza para o robo CIEL IT criar
    a invoice.

    Pre-condicao: picking em state='done' e liberacao_para_faturamento
    configurada no picking_type.
    """
    self.odoo.execute_kw(
        'stock.picking', 'action_liberar_faturamento', [[picking_id]]
    )
```

Pre-condicao mencionada na docstring mas **nao verificada em runtime**.

## Solucao proposta

```python
def liberar_faturamento(self, picking_id: int) -> None:
    # ✅ FIX G020: validar pre-condicao state=done
    p = self.odoo.read('stock.picking', [picking_id], ['state'])
    if not p:
        raise RuntimeError(f'Picking {picking_id} nao existe no Odoo')
    if p[0]['state'] != 'done':
        raise RuntimeError(
            f'Picking {picking_id} state={p[0]["state"]} '
            '(esperado "done" para liberar_faturamento). '
            'Re-validar (button_validate) antes — provavelmente F5b '
            'teve false-positive (G019).'
        )
    self.odoo.execute_kw(
        'stock.picking', 'action_liberar_faturamento', [[picking_id]]
    )
```

## Recovery (estado atual)

`f5c_liberar_faturamento` esta usando o helper `_io` em paralelo. Quando
o fix lancar RuntimeError para picking-nao-done, o caller (ETAPA B do
script bulk) registra falha e o ajuste fica em `F5c_FALHA`. Isso facilita
identificar e retry posterior.

Para os 4 pickings que ja' tiveram f5c chamado em estado assigned (foram
cancelados em 2026-05-18 ~12:25): nenhuma acao Odoo adicional necessaria
(cancel ja' descartou estado).

## Ref

- G019 (f5b false-positive — bug raiz que cascateia aqui)
- `app/odoo/estoque/scripts/picking.py:500-525` (`liberar_faturamento()` — capinado de `services/` em 2026-05-24 v3; shim em `services/stock_picking_service.py` re-exporta)
- `app/odoo/services/inventario_pipeline_service.py:768-862` (f5c)

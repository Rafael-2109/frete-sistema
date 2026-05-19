# G019 — f5b validar() engole erro e marca F5b_VALIDADO sem picking estar done

**Descoberta**: 2026-05-18 sessao 2 manha (teste 100 produtos LF)
**Severidade**: CRITICAL (cascateia em G020 + invoice nunca criada pelo robo)
**Status**: PROPOSTO (fix pendente)

---

## Sintoma

ETAPA B reporta `pickings criados=5 validados=5 liberados=5 ajustes_falha=0`
mas inspecao posterior mostra 4 dos 5 pickings em `state=assigned` (nao done).

Ajustes locais marcados `fase_pipeline=F5b_VALIDADO` mas picking real em
state assigned no Odoo. Quando ETAPA C tenta polling F5d, robo CIEL IT
nunca cria invoice porque picking nao esta done.

## Root cause

`StockPickingService.validar()` em `stock_picking_service.py:249-279`:

```python
try:
    self.odoo.execute_kw(
        'stock.picking', 'button_validate', [[picking_id]],
        {'context': {'skip_backorder': True,
                     'picking_ids_not_to_backorder': [picking_id]}},
    )
    return True
except Exception as e:
    if 'cannot marshal None' in str(e):
        return True  # ← FALSE POSITIVE possivel
    raise
```

Quando o Odoo nao consegue validar (e.g., estoque negativo), pode retornar:
- Erro com mensagem clara → exception → propagado OK
- Wizard de confirmacao → XML-RPC tenta serializar None → erro 'cannot marshal None'
- → tratado como sucesso, MAS picking continua em assigned

Caso real descoberto:
- Picking 317342 estoque insuficiente para confirmar (drift Cat 2)
- button_validate retornou wizard XML-RPC pode ter retornado None
- Odoo manteve picking em `assigned` mas script marcou F5b_VALIDADO

## Sintoma confirmado

Tentativa manual de `button_validate` no picking 317342 (~2h apos f5b):

```
Erro: <Fault 2: "Nao pode validar esta operacao de stock porque o nivel
de stock do produto '%s'%s tornar-se-ia negativo (%s) na localizacao '%s'
e um stock negativo nao e' permitido para este produto e/ou local.">
```

Mensagem com `%s` literais — bug CIEL IT na formatacao, mas o erro real e'
estoque negativo. f5b nao detectou isso.

## Solucao proposta

Modificar `StockPickingService.validar()` para CHECAR state apos chamada:

```python
def validar(self, picking_id: int) -> bool:
    try:
        self.odoo.execute_kw(
            'stock.picking', 'button_validate', [[picking_id]],
            {'context': {'skip_backorder': True,
                         'picking_ids_not_to_backorder': [picking_id]}},
        )
        # ✅ FIX G019: verificar state real apos chamada
        p = self.odoo.read('stock.picking', [picking_id], ['state'])
        if p and p[0]['state'] == 'done':
            return True
        raise RuntimeError(
            f'Picking {picking_id} state={p[0]["state"] if p else "unknown"} '
            'apos button_validate (esperado "done")'
        )
    except Exception as e:
        if 'cannot marshal None' in str(e):
            # Mesmo com 'marshal None', verificar state
            p = self.odoo.read('stock.picking', [picking_id], ['state'])
            if p and p[0]['state'] == 'done':
                logger.info(
                    f'Picking {picking_id}: button_validate retornou None '
                    '(state=done — sucesso)'
                )
                return True
            raise RuntimeError(
                f'Picking {picking_id}: button_validate retornou marshal None '
                f'MAS state={p[0]["state"] if p else "unknown"} '
                '(NAO done — provavelmente estoque negativo ou wizard pendente)'
            )
        raise
```

## Recovery (estado atual)

Para os 4 pickings que ficaram em assigned (cancelados em 2026-05-18 ~12:25):
- `action_cancel` funciona em state=assigned → libera reservas
- Ajustes locais resetados para PROPOSTO

## Ref

- G020 (f5c sem pre-cond — bug em cascata)
- G016 (SSL resilience — ainda nao cobre f5d, descoberto no mesmo teste)
- `app/odoo/services/stock_picking_service.py:249-279`
- `app/odoo/services/inventario_pipeline_service.py:663-762` (f5b)

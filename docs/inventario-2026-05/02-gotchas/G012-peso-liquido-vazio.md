# G012 — peso_liquido vazio em picking (consequencia de G011)

**Descoberta**: 2026-05-18 sub-piloto bulk (apos G010 fix)
**Severidade**: MED (bloqueia F5c action_liberar_faturamento)
**Status**: corrigido pela cadeia G011 (preencher_qty_done apos action_assign)

---

## Sintoma

```
ERROR app.odoo.utils.connection ❌ Erro na execucao de stock.picking.action_liberar_faturamento:
<Fault 2: 'Voce deve informar o Peso Liquido para liberar o faturamento.'>
```

Picking criado, action_confirm + action_assign OK, mas peso_liquido=0.

## Causa raiz

Campos calculados no CIEL IT (`@api.depends('move_ids.qty_done')`?):
- `l10n_br_peso_liquido` = SUM(move.qty_done * product.weight)
- `l10n_br_peso_bruto` = SUM(move.qty_done * product.weight) [ou product.gross_weight]

Se `qty_done=0` em todas as moves (G011), peso_liquido=0 → action_liberar_faturamento
recusa.

## Comparacao

Picking 317295 (OK historico, state=done):
- 3 moves PIMENTA BIQUINHO+PIMENTA BIQ B+CEBOLINHA
- product.weight = 1.0 (todos)
- soma qty_done = 60.440 + 672.320 + 10 = **742.76**
- l10n_br_peso_liquido = **742.76** ✓
- action_liberar_faturamento OK

Picking 317309 (FALHOU pre-fix, state=cancel):
- 5 moves COGUMELO + AZEITONA PRETA + AZEITONAS TRIT + PEPINO + ALHO EM PO
- product.weight = 1.0 (todos)
- soma qty_done = 0 (G011 raiz)
- l10n_br_peso_liquido = **0.0** ❌
- action_liberar_faturamento: "Voce deve informar o Peso Liquido"

## Solucao

Resolvida pela cadeia G011 — preencher qty_done DEPOIS de action_assign.

Validacao defensiva opcional (recomendada para detectar produto sem weight):

```python
# Antes de criar picking, validar weight > 0
prods = odoo.read('product.product', pids, ['default_code', 'weight'])
sem_peso = [p['default_code'] for p in prods if not p['weight'] or p['weight'] <= 0]
if sem_peso:
    raise RuntimeError(
        f"Produtos sem peso liquido cadastrado no Odoo: {sem_peso}. "
        "Atualizar product.weight antes de rodar bulk."
    )
```

Referencia: `recebimento_lf_odoo_service.py:1910` (`_validar_peso_liquido_produtos`).

## Quando esse problema voltar

Mesmo apos fix G011, se algum `product.weight == 0`:
- soma qty_done * weight = 0
- peso_liquido = 0
- action_liberar_faturamento falha

Validar `weight > 0` em TODOS os produtos do batch antes de criar picking.
Auditoria SQL recomendada para LF completa:

```sql
-- Identificar produtos da onda 1 LF com weight zerado no Odoo
-- (consultar via XML-RPC ja que weight nao esta no DB local)
SELECT cod_produto FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05' AND company_id=5 AND status='PROPOSTO'
GROUP BY cod_produto;
-- Para cada cod -> ler product.product.weight no Odoo
```

## Ref

- G011 (preencher_qty_done — raiz)
- G013 (volumes vazios — mesma cadeia)
- D006 secao L20 (a ser adicionada)

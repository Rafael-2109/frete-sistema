<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# G013 — quantidade_volumes vazio em picking (consequencia de G011)

> **Papel:** G013 — quantidade_volumes vazio em picking (consequencia de G011).

**Descoberta**: 2026-05-18 sub-piloto bulk (apos G010 fix)
**Severidade**: MED (bloqueia F5c action_liberar_faturamento em pickings FB)
**Status**: corrigido pela cadeia G011 (preencher_qty_done apos action_assign)

---

## Sintoma

```
ERROR app.odoo.utils.connection ❌ Erro na execucao de stock.picking.action_liberar_faturamento:
<Fault 2: 'Voce deve informar a Quantidade de Volumes para liberar o faturamento.'>
```

Picking FB criado (industrializacao FB->LF), action_confirm + action_assign,
mas `l10n_br_volumes=0`.

## Causa raiz

Campo `l10n_br_volumes` (stock.picking) e' computado pelo CIEL IT como:
- Some via stock.move por algum criterio (qty_done, UoM, embalagem) → quando
  `qty_done=0` em todas as moves (G011), volumes=0.

## Comparacao

Picking 317295 (OK historico):
- 3 moves com qty_done > 0
- l10n_br_volumes = **108** ✓

Picking 317310 (FALHOU pre-fix):
- 1 move PEPINO IND com qty_done=0
- l10n_br_volumes = **0** ❌

## Solucao

Resolvida pela cadeia G011 — preencher qty_done DEPOIS de action_assign.

Quando G011 estiver OK e ainda assim volumes=0, investigar:
- product.l10n_br_unidade_volume (caso exista — CIEL IT pode ter campo diferente)
- product.weight vs product.volume
- Embalagem padrao do produto (`product.packaging_ids`)

## Diferenca LF vs FB

- LF (perda LF→FB): primeiro reclamado pelo SEFAZ via `l10n_br_peso_liquido` (G012)
- FB (industrializacao FB→LF): primeiro reclamado por `l10n_br_volumes` (G013)

Mesma raiz (G011) mas mensagem de erro diferente conforme tipo do picking.

## Ref

- G011 (preencher_qty_done — raiz)
- G012 (peso_liquido vazio — mesma cadeia, LF)
- D006 secao L21 (a ser adicionada)

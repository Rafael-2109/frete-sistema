<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# G018 — weight=0 no produto bloqueia F5c liberar_faturamento

> **Papel:** G018 — weight=0 no produto bloqueia F5c liberar_faturamento.

## Indice

- [Sintoma](#sintoma)
- [Causa raiz](#causa-raiz)
- [Caso real (sub-piloto sessao 2)](#caso-real-sub-piloto-sessao-2)
- [Solucao IMPLEMENTADA](#solucao-implementada)
- [Por que nao usar G015 (price_unit=0) approach?](#por-que-nao-usar-g015-price_unit0-approach)
- [Trade-off fiscal](#trade-off-fiscal)
- [Comparacao com gotchas relacionados](#comparacao-com-gotchas-relacionados)
- [Ref](#ref)

**Descoberta**: 2026-05-18 sessao 2 manha (audit fiscal LF 455 produtos)
**Severidade**: HIGH (bloqueia F5c para 109 produtos da onda 1 LF)
**Status**: ✅ **FIX IMPLEMENTADO** (2026-05-18 sessao 2 manha) em
`scripts/inventario_2026_05/09_executar_onda1_bulk.py`. Funcao
`corrigir_weight_zero` + flag CLI `--auto-fix-weight`.

---

## Sintoma

```
ERROR app.odoo.utils.connection ❌ Erro na execucao de stock.picking.action_liberar_faturamento:
<Fault 2: 'Voce deve informar o Peso Liquido para liberar o faturamento.'>
```

ou (em pickings FB):

```
<Fault 2: 'Voce deve informar a Quantidade de Volumes para liberar o faturamento.'>
```

## Causa raiz

CIEL IT computa `l10n_br_peso_liquido` e `l10n_br_volumes` no stock.picking
como `SUM(move.qty_done * product.weight)`. Se `product.weight = 0`, ambos
ficam = 0 e `action_liberar_faturamento` rejeita.

**G011 (preencher qty_done apos action_assign) NAO resolve isto** —
mesmo com qty_done correto, se `product.weight=0`, o produto vezes weight
ainda da' 0.

## Caso real (sub-piloto sessao 2)

Audit em 2026-05-18 revelou **110 produtos com `weight=0` no Odoo** no
escopo onda 1 LF (455 produtos PROPOSTO), dos quais **109 com acao de
picking** (PERDA_LF_FB + INDUSTRIALIZACAO_FB_LF):

| Familia | Qtd | Exemplo |
|---|---|---|
| 104xxx ingredientes | 12 | OREGANO, MANJERICAO, NOZ MOSCADA |
| 105xxx aromas/condimentos | 10 | AROMA FUMACA, TOMILHO, SUCRALOSE |
| 109xxx oleos | 1 | AZEITE EXT VIRG LT |
| 201-203xxx embalagens vidro/balde | 4 | CAIXA PAPELAO, BALDE 2L, TAMPA |
| 207-208-209xxx rotulos/sacos/tampas | 8 | ROTULO AZ PI VD 200G |
| 210010xxx rotulos ST ISABEL | 30 | ROTULO MOLHO DE SALADA |
| 210030xxx rotulos CAMPO BELO + caixas | 23 | ROTULO MAIONESE |
| 301xxx insumos quimicos | 1 | SALMOURA HIDRATACAO |
| 38xxxxx bateladas | 11 | BATELADA DE ALHO |
| **Total** | **109** | |

Cadastrar manualmente 109 produtos via UI Odoo bloquearia LF completo.

## Solucao IMPLEMENTADA

Funcao `corrigir_weight_zero(odoo, pids_map, peso_fallback=0.001)` em
`09_executar_onda1_bulk.py:206-265`:

```python
def corrigir_weight_zero(odoo, pids_map, peso_fallback=0.001):
    """G018: corrige product.weight=0 -> peso_fallback no Odoo."""
    pids_validos = [pid for pid in pids_map.values() if pid]
    prods = odoo.read('product.product', pids_validos,
        ['default_code', 'name', 'weight'])
    a_corrigir = [p for p in prods if float(p.get('weight') or 0) <= 0]
    if a_corrigir:
        pids_corrigir = [p['id'] for p in a_corrigir]
        odoo.write('product.product', pids_corrigir,
            {'weight': peso_fallback})
    return a_corrigir
```

Chamada em `etapa_b_pickings` ANTES de `validar_cadastro_fiscal`:

```python
if auto_fix_weight > 0:
    corrigir_weight_zero(odoo, prod_cache, peso_fallback=auto_fix_weight)
validar_cadastro_fiscal(odoo, prod_cache, modo=modo_validacao_fiscal)
```

Flag CLI:
```bash
# Default (0.001kg = 1g)
python 09_executar_onda1_bulk.py --confirmar

# Desabilitar fix (validacao fiscal strict vai bloquear)
python 09_executar_onda1_bulk.py --auto-fix-weight=0 --validacao-fiscal=strict

# Override com outro fallback (ex: 0.01kg = 10g)
python 09_executar_onda1_bulk.py --auto-fix-weight=0.01
```

## Por que nao usar G015 (price_unit=0) approach?

G015 corrige `aj.custo_medio` no DB local + `linhas[].price_unit` no payload
do picking. NAO toca master data Odoo.

**G018 PRECISA modificar `product.product.weight` no Odoo** porque
`l10n_br_peso_liquido` no stock.picking e' campo `compute='_compute_*'`
(somente leitura via XML-RPC, recalculado a partir de move.qty_done *
product.weight). Tentar setar `peso_liquido` diretamente no picking
seria sobrescrito no proximo recompute.

## Trade-off fiscal

- **Rotulos/embalagens** (a maioria, ~70%): 0.001 = realista (peso real
  e' mesmo desprezivel).
- **Ingredientes/aromas/oleos** (~25%): 0.001 e' fiscal-compromise.
  Peso real seria 0.5-1kg/un. Como o SEFAZ aceita >0, NF passa, mas
  XML fica com peso fiscalmente impreciso.
- **Bateladas/insumos quimicos** (~5%): mesmo trade-off.

**Recomendacao operacional**: usar 0.001 como fallback para destravar
LF completo. Cadastrar weight correto via UI Odoo apos inventario
(tarefa de manutencao master data).

## Comparacao com gotchas relacionados

| Gotcha | Campo | Master data? | Fix |
|---|---|---|---|
| G011 | move.qty_done | Nao (campo writable do picking) | preencher apos action_assign |
| G012 | picking.l10n_br_peso_liquido | Nao (computed) | corrigir product.weight (este G018) |
| G013 | picking.l10n_br_volumes | Nao (computed) | corrigir product.weight (este G018) |
| G015 | aj.custo_medio + linhas[].price_unit | Nao | aplicar standard_price ou 0.01 |
| G017 | product.l10n_br_ncm_id | Sim | cadastrar manualmente |
| **G018** | **product.weight** | **Sim (modificado pelo fix)** | **product.write {weight: 0.001}** |

## Ref

- G011 (preencher qty_done — pre-requisito)
- G012/G013 (peso_liquido/volumes vazios — sintoma)
- G015 (price_unit=0 — fix analogo no escopo local, nao Odoo)
- G017 (NCM=False — fix analogo strict, sem auto-fix)
- `docs/inventario-2026-05/07-relatorios/audit_fiscal_LF.md` (snapshot)

# T04 — Configurar property_stock_subcontractor da LF

**Status final**: ✅ done
**Executado em**: 2026-05-28
**Executor**: Claude (`setup_s0.py`) com autorização Rafael
**Modo**: dry-run → execute

## Comando

```bash
python docs/industrializacao-fb-lf/scripts/setup_s0.py --task T04 --execute
```

## Output execute

```
[EXEC] T04 — Alterar property_stock_subcontractor da LF
[EXEC]   nova location: LF/Materiais de Terceiros (id=31092)
[EXEC]   atual: Locais Fisicos/Local de subcontratação
[EXEC] write res.partner id=35: {'property_stock_subcontractor': 31092}
✅ Task T04 OK (result=True)
```

## Antes / depois

| | Antes | Depois |
|---|---|---|
| `res.partner.property_stock_subcontractor` da LF (id=35) | Locais Fisicos/Local de subcontratação (id=30713) | **LF/Materiais de Terceiros (id=31092)** |

## Validação pós-execução (XML-RPC)

```
res.partner id=35 LA FAMIGLIA - LF
  property_stock_subcontractor = [31092, 'LF/Materiais de Terceiros']
```

## Significado operacional

A partir de agora, quando um stock.move de subcontratação envolver o partner LF (id=35) como subcontratante, os componentes enviados pela FB **deixam o estoque FB** e entram em **LF/Materiais de Terceiros (31092)**, em vez do antigo `Locais Fisicos/Local de subcontratação` (30713, sem visibilidade gerencial em cmp=LF).

Esta é a "ponte de localização" que dá ao PCP LF visibilidade em cmp=LF dos materiais que estão fisicamente na LF mas pertencem contabilmente à FB.

## Próxima task destravada

- T13 (teste end-to-end) — agora pode validar que `picking_type=75 RES` move componentes FB→LF/Materiais de Terceiros corretamente.

## Idempotência

Re-executar `--execute` agora mostraria:
```
[EXEC]   atual: LF/Materiais de Terceiros
  já configurado (skip)
```

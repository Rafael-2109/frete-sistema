# T10b — Alterar BoM 3646 (filha BATELADA): consumption='strict'

**Status final**: ✅ done
**Executado em**: 2026-05-28
**Executor**: Claude (write XML-RPC direto) com autorização Rafael
**Modo**: write direto (1 linha)

## Comando

```python
conn.write('mrp.bom', 3646, {'consumption': 'strict'})
```

## Antes / depois

| Campo | Antes | Depois |
|---|---|---|
| `mrp.bom` id=3646 BATELADA DE SHOYU `consumption` | warning | **strict** |

## Validação pós-execução

```
mrp.bom id=3646 [3800018] BATELADA DE SHOYU
  consumption = strict
  active = True
  type = normal
  company_id = [5, LF]
```

## Origem

Decisão D17 — A BoM real do piloto é hierárquica (3695 PA + 3646 filha BATELADA). Para que D05 (Opção B strict) funcione efetivamente na MO LF, ambos os níveis precisam ter `consumption='strict'`. T10 cobriu 3695, T10b cobre 3646.

## Rollback

```python
conn.write('mrp.bom', 3646, {'consumption': 'warning'})
```

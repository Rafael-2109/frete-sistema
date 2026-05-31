# T03 — Criar location LF/PA de Terceiros

**Status final**: ✅ done
**Executado em**: 2026-05-28
**Executor**: Claude (`setup_s0.py`) com autorização Rafael
**Modo**: dry-run → execute

## Comando

```bash
python docs/industrializacao-fb-lf/scripts/setup_s0.py --task T03 --execute
```

## Output execute

```
[EXEC] T03 — Criar location LF/PA de Terceiros
[EXEC] create stock.location: {'name': 'PA de Terceiros', 'location_id': 41, 'usage': 'internal', 'company_id': 5, 'active': True}
[EXEC]   resultado: location id=31093
✅ Task T03 OK (result=31093)
```

## Validação pós-execução (XML-RPC)

| Campo | Valor |
|---|---|
| id | **31093** |
| name | PA de Terceiros |
| complete_name | LF/PA de Terceiros |
| location_id (parent) | [41, 'LF'] |
| usage | internal |
| company_id | [5, 'LA FAMIGLIA - LF'] |
| active | True |

## Constante nova para o projeto

```
LOC_LF_PA_TERCEIROS = 31093
```

## Próxima task destravada

- T07 (criar `picking_type LF/SAI/IND/RET` com `default_location_src_id=31093`)

## A05 ainda em aberto

`LF/PA de Terceiros` foi criada, mas a decisão A05 (PA da MO LF cai aqui ou em LF/Estoque) só será resolvida em T13. Por padrão, sem stock.rule customizada, MO LF produz em LF/Estoque (id=42). Se for necessário direcionar para 31093, customizar regra da rota Fabricar (134) — tarefa T-OPC-01.

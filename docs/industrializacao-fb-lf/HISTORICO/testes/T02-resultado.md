# T02 — Criar location LF/Materiais de Terceiros

**Status final**: ✅ done
**Executado em**: 2026-05-28
**Executor**: Claude (script `setup_s0.py`) com autorização Rafael
**Modo**: dry-run → execute

## Comando

```bash
source .venv/bin/activate
python docs/industrializacao-fb-lf/scripts/setup_s0.py --task T02            # dry-run
python docs/industrializacao-fb-lf/scripts/setup_s0.py --task T02 --execute  # apply
```

## Output execute

```
[EXEC] T02 — Criar location LF/Materiais de Terceiros
[EXEC]   parent location: LF (id=41)
[EXEC] create stock.location: {'name': 'Materiais de Terceiros', 'location_id': 41, 'usage': 'internal', 'company_id': 5, 'active': True}
[EXEC]   resultado: location id=31092
✅ Task T02 OK (result=31092)
```

## Validação pós-execução (XML-RPC)

```python
conn.search_read('stock.location', [('id','=',31092)],
    ['id','name','complete_name','location_id','usage','company_id','active'])
```

| Campo | Valor |
|---|---|
| id | **31092** |
| name | Materiais de Terceiros |
| complete_name | LF/Materiais de Terceiros |
| location_id (parent) | [41, 'LF'] |
| usage | internal |
| company_id | [5, 'LA FAMIGLIA - LF'] |
| active | True |

## Constante nova para o projeto

```
LOC_LF_MATERIAIS_TERCEIROS = 31092
```

Adicionar em CONTEXTO.md (tabela "Locations Odoo") e referenciar nos scripts subsequentes (T04, T08).

## Próxima task

- T04 (depende de T02 done) — alterar `res.partner.property_stock_subcontractor` da LF (id=35) para apontar para 31092.
- T08 (depende de T05 + T02) — criar `stock.rule` na rota 162 com `location_dest_id=31092`.
- T03 (sem pré-req) — criar LF/PA de Terceiros — pode rodar em paralelo.

## Observações

- Idempotência: re-executar `--execute` agora retornaria `já existe id=31092 (skip)`.
- Sem efeitos colaterais. Location vazia (`quant_ids=[]`).

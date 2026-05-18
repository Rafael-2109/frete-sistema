# G006 — Picking inter-company exige location virtual destino

**Descoberta**: 2026-05-18 sub-piloto bulk 10 produtos
**Severidade**: HIGH (bloqueia validacao do picking)
**Status**: corrigido em `inventario_pipeline_service.py:74-148`

---

## Sintoma

```
<Fault 2: "Empresas incompativeis nos registros:
- 'FB/SAI/IND/01553' pertence a empresa 'NACOM GOYA - FB' e
  'Destination Location' (location_dest_id: 'LF/Estoque') pertence a outra empresa.">
```

Ao chamar `action_confirm` em picking criado com:
- `company_id = 1 (FB)`
- `location_id = 8 (FB/Estoque)` — OK, mesma empresa
- `location_dest_id = 42 (LF/Estoque)` — **ERRO**, outra empresa

## Causa raiz

Odoo exige que **pickings inter-company** usem location virtual no destino
(com `company_id=False`), nao a location interna da empresa destino.

`resolver_location_destino(tipo_op, company_destino)` antigo retornava
`COMPANY_LOCATIONS[destino]` (= 8 para FB, 42 para LF, 32 para CD) —
todas internas com `company_id` definido.

## Solucao

Mapeamento canonico por `(company_origem, tipo_op) → location virtual`:

| Origem | Tipo Op | Location destino | Nome |
|---|---|---|---|
| 5 (LF) | perda | **5** | Parceiros/Clientes |
| 1 (FB) | industrializacao | **26489** | Em Transito Industrializacao |
| 5 (LF) | industrializacao | **5** | Parceiros/Clientes (LF retorno) |
| 1 (FB) | transf-filial | **6** | Em Transito Filiais |
| 4 (CD) | transf-filial | **6** | Em Transito Filiais |
| 5 (LF) | dev-industrializacao | **5** | Parceiros/Clientes |
| 4 (CD) | dev-industrializacao | **26489** | Em Transito Industrializacao |
| 1 (FB) | dev-industrializacao | **26489** | Em Transito Industrializacao |

Todas com `company_id=False` (compartilhadas) — Odoo aceita.

## Codigo

```python
def resolver_location_destino(tipo_op, company_destino, company_origem=None):
    if company_origem is not None:
        key = (company_origem, tipo_op)
        if key in LOCATION_DESTINO_POR_DIRECAO:
            return LOCATION_DESTINO_POR_DIRECAO[key]
    # Fallback...
```

## Validacao

Validado contra `default_location_dest_id` dos picking_types:
- pt 51 FB Exp Entre Filiais: 6 ✓
- pt 53 FB Exp Industrializacao: 26489 ✓
- pt 55 CD Exp Entre Filiais: 6 ✓
- pt 66 LF Exp Industrializacao: 5 ✓
- pt 94 LF Exp N Aplicado: 5 ✓
- pt 96 CD Retrabalho: 26489 ✓

## Para a LF completa

Atencao especial a casos onde `company_origem`/`tipo_op` nao esta em
`LOCATION_DESTINO_POR_DIRECAO`. Adicionar antes de rodar bulk LF
(quando criar novas combinacoes).

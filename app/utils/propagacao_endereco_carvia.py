"""Propaga cidade/UF do cadastro de endereço CarVia para os destinos EXTERNOS
ao CarVia: `embarque_itens` (item CarVia) e `entregas_monitoradas` (origem CARVIA).

Mora em app/utils (zona neutra) porque o CarVia não pode importar app/embarques
nem app/monitoramento (R1). Espelha app/utils/propagacao_local_cd.py:
- Idempotente; UPDATE filtra status/entregue.
- Sem commit (UPDATE em massa synchronize_session=False); o caller commita.
- EmbarqueItem: separacao_lote_id LIKE 'CARVIA-%' E (nota_fiscal IN numeros_nf
  OU carvia_cotacao_id IN cot_ids), status 'ativo'. NUNCA toca itens Nacom.
- EntregaMonitorada: numero_nf IN numeros_nf, origem='CARVIA', entregue=False.
"""


def propagar_cidade_uf_carvia(numeros_nf, cot_ids, cidade, uf):
    numeros_nf = [n for n in (numeros_nf or []) if n]
    cot_ids = [c for c in (cot_ids or []) if c]
    if (not numeros_nf and not cot_ids) or (cidade is None and uf is None):
        return {'embarque_itens': 0, 'entregas': 0}

    from app import db
    from app.embarques.models import EmbarqueItem
    from app.monitoramento.models import EntregaMonitorada

    valores = {}
    if cidade is not None:
        valores['cidade_destino'] = cidade
    if uf is not None:
        valores['uf_destino'] = uf

    cond_match = []
    if numeros_nf:
        cond_match.append(EmbarqueItem.nota_fiscal.in_(numeros_nf))
    if cot_ids:
        cond_match.append(EmbarqueItem.carvia_cotacao_id.in_(cot_ids))

    n_itens = (
        EmbarqueItem.query
        .filter(
            EmbarqueItem.separacao_lote_id.ilike('CARVIA-%'),
            db.or_(*cond_match),
            EmbarqueItem.status == 'ativo',
        )
        .update(valores, synchronize_session=False)
    )

    n_entregas = 0
    if numeros_nf:
        valores_e = {}
        if cidade is not None:
            valores_e['municipio'] = cidade
        if uf is not None:
            valores_e['uf'] = uf
        n_entregas = (
            EntregaMonitorada.query
            .filter(
                EntregaMonitorada.numero_nf.in_(numeros_nf),
                EntregaMonitorada.origem == 'CARVIA',
                EntregaMonitorada.entregue.is_(False),
            )
            .update(valores_e, synchronize_session=False)
        )

    return {'embarque_itens': n_itens, 'entregas': n_entregas}

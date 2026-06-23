"""Valida as queries do filtro de embarque da listagem de NF Venda CarVia.

A rota `listar_nfs` usa `db.session.query(...).paginate()`, que NAO roda sob a
TestingSession do conftest (sem `query_cls` do Flask-SQLAlchemy; so' `Model.query`
tem `.paginate`). Entao em vez de bater no endpoint, este teste reconstroi e
EXECUTA as subqueries do filtro `emb_pendente` e da via-frete do badge — pegando
erro de montagem SQL (em especial o EXISTS correlacionado + alias da via frete,
que ignora NF com EmbarqueItem CARVIA). O COMPORTAMENTO (NF com EI cancelado fica
pendente; NF sem EI mas com frete sai) foi validado em producao via Render MCP.
"""


def test_subqueries_filtro_embarque_executam(db):
    from app import db as _db
    from app.carvia.models import CarviaNf, CarviaOperacaoNf, CarviaFrete
    from app.embarques.models import Embarque, EmbarqueItem

    # "saiu da portaria" via embarque_itens CARVIA-* ativo (numero_nf)
    saiu_ei_notas = _db.session.query(EmbarqueItem.nota_fiscal).join(
        Embarque, Embarque.id == EmbarqueItem.embarque_id
    ).filter(
        EmbarqueItem.separacao_lote_id.like('CARVIA-%'),
        EmbarqueItem.status == 'ativo',
        EmbarqueItem.nota_fiscal.isnot(None),
        Embarque.data_embarque.isnot(None),
    )

    # "saiu da portaria" via frete — so se a NF NAO tem EmbarqueItem CARVIA
    # (EXISTS correlacionado + alias para nao colidir com o CarviaNf externo)
    CarviaNfFrete = _db.aliased(CarviaNf)
    saiu_frete_nf_ids = _db.session.query(CarviaOperacaoNf.nf_id).join(
        CarviaFrete, CarviaFrete.operacao_id == CarviaOperacaoNf.operacao_id
    ).join(
        Embarque, Embarque.id == CarviaFrete.embarque_id
    ).join(
        CarviaNfFrete, CarviaNfFrete.id == CarviaOperacaoNf.nf_id
    ).filter(
        CarviaFrete.status != 'CANCELADO',
        Embarque.data_embarque.isnot(None),
        ~_db.session.query(EmbarqueItem.id).filter(
            EmbarqueItem.nota_fiscal == CarviaNfFrete.numero_nf,
            EmbarqueItem.separacao_lote_id.like('CARVIA-%'),
        ).exists(),
    )

    # filtro completo (como na rota): NFs que NAO sairam por nenhuma via
    q = _db.session.query(CarviaNf).filter(
        CarviaNf.numero_nf.notin_(saiu_ei_notas),
        CarviaNf.id.notin_(saiu_frete_nf_ids),
    )
    # executa de fato — se o SQL nao montar (alias/EXISTS), levanta aqui
    assert isinstance(q.count(), int)
    assert isinstance(saiu_ei_notas.count(), int)
    assert isinstance(saiu_frete_nf_ids.count(), int)

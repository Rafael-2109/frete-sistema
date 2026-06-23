import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import text


def _criar_operacao(db, cte_numero, cte_valor):
    from app.carvia.models import CarviaOperacao
    op = CarviaOperacao(
        cte_numero=cte_numero, cte_valor=Decimal(str(cte_valor)),
        cte_data_emissao=datetime(2026, 1, 5).date(),
        cnpj_cliente='12345678000100', nome_cliente='C',
        uf_origem='SP', cidade_origem='SAO PAULO',
        uf_destino='RJ', cidade_destino='RIO DE JANEIRO',
        status='RASCUNHO', tipo_entrada='IMPORTADO', criado_por='test',
    )
    db.session.add(op); db.session.flush()
    return op


def _criar_nf(db, numero):
    from app.carvia.models import CarviaNf
    nf = CarviaNf(
        numero_nf=numero, cnpj_emitente='11111111000111', nome_emitente='E',
        cnpj_destinatario='22222222000122', nome_destinatario='D',
        data_emissao=datetime(2026, 1, 5).date(), valor_total=Decimal('500'),
        status='ATIVA', tipo_fonte='MANUAL', criado_por='test',
    )
    db.session.add(nf); db.session.flush()
    return nf


def test_receita_por_lote_nf_usa_cte(db):
    from app.carvia.models import CarviaOperacaoNf
    from app.carvia.services.financeiro.viabilidade_service import receita_carvia_por_lotes
    op = _criar_operacao(db, 'CTe-V1', 1200.0)
    nf = _criar_nf(db, '70001')
    db.session.add(CarviaOperacaoNf(operacao_id=op.id, nf_id=nf.id)); db.session.flush()

    res = receita_carvia_por_lotes([f'CARVIA-NF-{nf.id}'])
    assert res['total'] == 1200.0
    assert res['por_lote'][f'CARVIA-NF-{nf.id}']['fonte'] == 'CTE'


def test_lote_nacom_e_zero(db):
    from app.carvia.services.financeiro.viabilidade_service import receita_carvia_por_lotes
    res = receita_carvia_por_lotes(['LOTE_NACOM_123'])
    assert res['total'] == 0.0
    assert res['por_lote']['LOTE_NACOM_123']['fonte'] == 'SEM'


def test_receita_por_lotes_soma_multiplos(db):
    from app.carvia.models import CarviaOperacaoNf
    from app.carvia.services.financeiro.viabilidade_service import receita_carvia_por_lotes
    op1 = _criar_operacao(db, 'CTe-V2', 300.0); nf1 = _criar_nf(db, '70010')
    op2 = _criar_operacao(db, 'CTe-V3', 700.0); nf2 = _criar_nf(db, '70011')
    db.session.add(CarviaOperacaoNf(operacao_id=op1.id, nf_id=nf1.id))
    db.session.add(CarviaOperacaoNf(operacao_id=op2.id, nf_id=nf2.id))
    db.session.flush()
    res = receita_carvia_por_lotes([f'CARVIA-NF-{nf1.id}', f'CARVIA-NF-{nf2.id}', 'LOTE_X'])
    assert res['total'] == 1000.0


def _criar_cot_ped(db, numero_nf=None, valor_aprovado=None):
    """Cria cliente+endereco+cotacao (com valor_final_aprovado) + pedido (+item com NF)."""
    suf = uuid.uuid4().hex[:6]
    cli = db.session.execute(text(
        "INSERT INTO carvia_clientes (nome_comercial, criado_por) "
        "VALUES (:n, 'test') RETURNING id"
    ), {'n': f'C{suf}'}).scalar()
    end = db.session.execute(text(
        "INSERT INTO carvia_cliente_enderecos (cliente_id, tipo, criado_por) "
        "VALUES (:c, 'ORIGEM', 'test') RETURNING id"
    ), {'c': cli}).scalar()
    cot = db.session.execute(text(
        "INSERT INTO carvia_cotacoes (numero_cotacao, cliente_id, endereco_origem_id, "
        "endereco_destino_id, tipo_material, criado_por, local_cd, valor_final_aprovado) "
        "VALUES (:num, :cli, :e, :e, 'MOTO', 'test', 'VICTORIO_MARCHEZINE', :v) RETURNING id"
    ), {'num': f'COT-{suf}', 'cli': cli, 'e': end, 'v': valor_aprovado}).scalar()
    ped = db.session.execute(text(
        "INSERT INTO carvia_pedidos (numero_pedido, cotacao_id, filial, tipo_separacao, "
        "criado_por, local_cd) "
        "VALUES (:n, :c, 'SP', 'ESTOQUE', 'test', 'VICTORIO_MARCHEZINE') RETURNING id"
    ), {'n': f'P-{suf}', 'c': cot}).scalar()
    if numero_nf:
        db.session.execute(text(
            "INSERT INTO carvia_pedido_itens (pedido_id, quantidade, numero_nf) "
            "VALUES (:p, 1, :nf)"
        ), {'p': ped, 'nf': numero_nf})
    db.session.flush()
    return cot, ped


def _emb_com_itens(db, itens):
    """itens: lista de (lote, cot_id, nota_fiscal). Cria 1 embarque ativo com os EmbarqueItem."""
    from app.embarques.models import Embarque, EmbarqueItem
    emb = Embarque(numero=int(uuid.uuid4().int % 9_000_000) + 1_000_000, status='ativo')
    db.session.add(emb)
    db.session.flush()
    for lote, cot_id, nf in itens:
        db.session.add(EmbarqueItem(
            embarque_id=emb.id, separacao_lote_id=lote, pedido='P', cliente='X',
            status='ativo', uf_destino='SP', cidade_destino='X',
            local_cd='VICTORIO_MARCHEZINE', carvia_cotacao_id=cot_id, nota_fiscal=nf,
        ))
    db.session.flush()
    return emb


def test_receita_embarque_cte_vence_cotado(db):
    """Pedido cuja NF tem CTe (operacao): usa cte_valor (vence o cotado), tem_cte=True."""
    from app.carvia.models import CarviaOperacaoNf
    cot, ped = _criar_cot_ped(db, numero_nf='80001', valor_aprovado=Decimal('999'))
    op = _criar_operacao(db, 'CTe-EMB', 2500.0)
    nf = _criar_nf(db, '80001')
    db.session.add(CarviaOperacaoNf(operacao_id=op.id, nf_id=nf.id))
    db.session.flush()
    emb = _emb_com_itens(db, [(f'CARVIA-PED-{ped}', cot, '80001')])

    res = emb.receita_carvia()
    assert res['total'] == 2500.0
    assert res['tem_cte'] is True


def test_receita_embarque_usa_cotado_sem_cte(db):
    """Pedido sem CTe/frete: usa o valor cotado. Era o caso que ficava R$ 0 ate a portaria."""
    cot, ped = _criar_cot_ped(db, numero_nf=None, valor_aprovado=Decimal('900'))
    emb = _emb_com_itens(db, [(f'CARVIA-PED-{ped}', cot, None)])

    res = emb.receita_carvia()
    assert res['total'] == 900.0
    assert res['tem_cte'] is False


def test_receita_embarque_dedup_por_cotacao(db):
    """2 itens da MESMA cotacao (split/provisorio+NF) sem CTe contam o cotado 1x, nao 2x."""
    cot, ped = _criar_cot_ped(db, numero_nf=None, valor_aprovado=Decimal('900'))
    emb = _emb_com_itens(db, [
        (f'CARVIA-PED-{ped}', cot, None),
        ('CARVIA-NF-99999', cot, None),
    ])

    res = emb.receita_carvia()
    assert res['total'] == 900.0


def test_receita_embarque_sem_itens_carvia_e_zero(db):
    """Embarque so com item Nacom: receita CarVia = 0 (nao toca itens nao-CARVIA)."""
    from app.embarques.models import Embarque, EmbarqueItem
    emb = Embarque(numero=int(uuid.uuid4().int % 9_000_000) + 1_000_000, status='ativo')
    db.session.add(emb)
    db.session.flush()
    db.session.add(EmbarqueItem(
        embarque_id=emb.id, separacao_lote_id='LOTE_NACOM', pedido='P', cliente='X',
        status='ativo', local_cd='VICTORIO_MARCHEZINE', uf_destino='SP', cidade_destino='X',
    ))
    db.session.flush()

    res = emb.receita_carvia()
    assert res['total'] == 0.0
    assert res['tem_cte'] is False

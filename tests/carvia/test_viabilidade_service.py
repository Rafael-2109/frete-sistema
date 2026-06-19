from datetime import datetime
from decimal import Decimal


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

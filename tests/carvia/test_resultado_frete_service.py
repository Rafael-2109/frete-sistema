from datetime import date
from decimal import Decimal


def _op(db, cte_numero, cte_valor):
    from app.carvia.models import CarviaOperacao
    o = CarviaOperacao(
        cte_numero=cte_numero, cte_valor=Decimal(str(cte_valor)),
        cte_data_emissao=date(2026, 1, 10),
        cnpj_cliente='12345678000100', nome_cliente='C',
        uf_origem='SP', cidade_origem='SAO PAULO',
        uf_destino='SP', cidade_destino='PIRACICABA',
        status='RASCUNHO', tipo_entrada='IMPORTADO', criado_por='test',
    )
    db.session.add(o); db.session.flush()
    return o


def _nf_motos(db, numero, motos, cidade='PIRACICABA', uf='SP', peso='100.000'):
    """NF + `motos` veiculos (chassi) -> contagem GREATEST = motos."""
    from app.carvia.models import CarviaNf, CarviaNfVeiculo
    nf = CarviaNf(
        numero_nf=numero, cnpj_emitente='11111111000111', nome_emitente='E',
        cnpj_destinatario='22222222000122', nome_destinatario='D',
        uf_destinatario=uf, cidade_destinatario=cidade,
        data_emissao=date(2026, 1, 10), valor_total=Decimal('500'),
        peso_bruto=Decimal(peso), status='ATIVA', tipo_fonte='MANUAL', criado_por='test',
    )
    db.session.add(nf); db.session.flush()
    for i in range(motos):
        db.session.add(CarviaNfVeiculo(nf_id=nf.id, chassi=f'CH{numero}{i:03d}'))
    db.session.flush()
    return nf


def _link(db, op_id, nf_id):
    from app.carvia.models import CarviaOperacaoNf
    db.session.add(CarviaOperacaoNf(operacao_id=op_id, nf_id=nf_id)); db.session.flush()


def test_receita_rateada_por_motos(db):
    from app.carvia.services.financeiro.resultado_frete_service import ResultadoFreteService
    op = _op(db, 'CTe-R1', 1440.0)
    for n in range(3):
        nf = _nf_motos(db, f'8000{n}', 2)
        _link(db, op.id, nf.id)
    det = ResultadoFreteService().detalhe_por_nf(date(2026, 1, 1), date(2026, 12, 31))
    rows = [d for d in det if d['operacao_id'] == op.id]
    assert len(rows) == 3
    for d in rows:
        assert d['motos'] == 2
        assert round(d['receita'], 2) == 480.0
        assert round(d['resultado'], 2) == 480.0
        assert round(d['resultado_moto'], 2) == 240.0


def test_custo_subcontrato_gera_prejuizo(db):
    from app.carvia.models import CarviaSubcontrato
    from app.transportadoras.models import Transportadora
    from app.carvia.services.financeiro.resultado_frete_service import ResultadoFreteService
    op = _op(db, 'CTe-R2', 4000.0)
    nf = _nf_motos(db, '81000', 16)
    _link(db, op.id, nf.id)
    transp = Transportadora(razao_social='T2', cnpj='44444444000144', cidade='SP', uf='SP')
    db.session.add(transp); db.session.flush()
    db.session.add(CarviaSubcontrato(
        operacao_id=op.id, transportadora_id=transp.id,
        cte_valor=Decimal('4309.39'), status='CONFIRMADO', criado_por='test',
    )); db.session.flush()
    det = ResultadoFreteService().detalhe_por_nf(date(2026, 1, 1), date(2026, 12, 31))
    rows = [d for d in det if d['operacao_id'] == op.id]
    assert len(rows) == 1
    d = rows[0]
    assert round(d['custo_sub'], 2) == 4309.39
    assert d['custo_sub_flag'] == 'REAL'
    assert round(d['resultado'], 2) == round(4000.0 - 4309.39, 2)  # prejuizo


def test_resumo_por_cte_agrega(db):
    from app.carvia.services.financeiro.resultado_frete_service import ResultadoFreteService
    op = _op(db, 'CTe-R3', 1000.0)
    nf = _nf_motos(db, '82000', 4)
    _link(db, op.id, nf.id)
    res = ResultadoFreteService().resumo('cte', date(2026, 1, 1), date(2026, 12, 31))
    rows = [r for r in res if r['label'] == op.cte_numero]
    assert len(rows) == 1
    assert round(rows[0]['receita'], 2) == 1000.0
    assert rows[0]['motos'] == 4
    assert round(rows[0]['receita_moto'], 2) == 250.0

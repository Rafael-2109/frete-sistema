import uuid
from decimal import Decimal
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo,
    PENDENCIA_CATEGORIA_FALTA_PECA, PENDENCIA_ORIGEM_GALPAO,
    PENDENCIA_TRATATIVA_USAR_ESTOQUE,
)
from app.motos_assai.services.peca_service import criar_peca
from app.motos_assai.services.movimento_service import registrar_entrada
from app.motos_assai.services.pendencia_service import abrir_pendencia, detalhe_pendencia
from app.motos_assai.services.resolucao_service import resolver_com_tratativa


def _moto(chassi, admin_user):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()


def test_detalhe_traz_ficha_movimentos_e_custo(app, admin_user):
    with app.app_context():
        chassi = f'TSTDET{uuid.uuid4().hex[:6].upper()}'
        _moto(chassi, admin_user)
        p = criar_peca(nome=f'PZ{uuid.uuid4().hex[:6].upper()}', operador_id=admin_user.id)
        registrar_entrada(peca_id=p.id, quantidade=3, custo_unitario='10.00', operador_id=admin_user.id)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='falta',
                            operador_id=admin_user.id)
        resolver_com_tratativa(pendencia_id=f.id, tratativa=PENDENCIA_TRATATIVA_USAR_ESTOQUE,
                               resolucao_descricao='ok', operador_id=admin_user.id,
                               peca_id=p.id, quantidade=1)
        db.session.flush()
        d = detalhe_pendencia(f.id)
        assert d is not None
        assert d['ficha']['categoria'] == PENDENCIA_CATEGORIA_FALTA_PECA
        assert len(d['movimentos']) == 1
        assert d['movimentos'][0]['tipo'] == 'CONSUMO'
        assert d['custo_total'] == Decimal('10.00')
        assert detalhe_pendencia(999999999) is None
        db.session.rollback()

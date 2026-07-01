import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo,
    PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_CATEGORIA_AVARIA,
    PENDENCIA_ORIGEM_GALPAO, PENDENCIA_ORIGEM_POS_VENDA_LOJA,
)
from app.motos_assai.services.pendencia_service import (
    abrir_pendencia, reclassificar, PendenciaError,
)


def _moto(chassi, admin_user):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()


def _uid(): return f'TSTX{uuid.uuid4().hex[:6].upper()}'


def test_reclassificar_categoria(app, admin_user):
    with app.app_context():
        chassi = _uid(); _moto(chassi, admin_user)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='defeito',
                            operador_id=admin_user.id)
        reclassificar(pendencia_id=f.id, categoria=PENDENCIA_CATEGORIA_AVARIA,
                      origem=PENDENCIA_ORIGEM_GALPAO, operador_id=admin_user.id)
        db.session.refresh(f)
        assert f.categoria == PENDENCIA_CATEGORIA_AVARIA
        assert f.detalhes.get('reclassificacao') is not None
        db.session.rollback()


def test_reclassificar_nao_pode_destravar_moto_via_origem(app, admin_user):
    with app.app_context():
        chassi = _uid(); _moto(chassi, admin_user)
        # ficha fisica (GALPAO) => emitiu PENDENTE (evento_pendente_id set)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='defeito',
                            operador_id=admin_user.id)
        assert f.evento_pendente_id is not None
        with pytest.raises(PendenciaError, match='fisica|trava|nao-fisica'):
            reclassificar(pendencia_id=f.id, categoria=PENDENCIA_CATEGORIA_AVARIA,
                          origem=PENDENCIA_ORIGEM_POS_VENDA_LOJA, operador_id=admin_user.id)
        db.session.rollback()

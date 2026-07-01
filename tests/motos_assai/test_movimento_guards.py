# tests/motos_assai/test_movimento_guards.py
import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiPendencia,
    PENDENCIA_CATEGORIA_FALTA_PECA, PENDENCIA_ORIGEM_GALPAO,
)
from app.motos_assai.services.peca_service import criar_peca
from app.motos_assai.services.pendencia_service import abrir_pendencia
from app.motos_assai.services.movimento_service import consumir, canibalizar, EstoqueError


def _peca(admin_user):
    return criar_peca(nome=f'PZ_{uuid.uuid4().hex[:8].upper()}', operador_id=admin_user.id)


def _moto(chassi, admin_user):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()


def _ficha(chassi, admin_user, categoria=PENDENCIA_CATEGORIA_FALTA_PECA):
    return abrir_pendencia(
        chassi=chassi, categoria=categoria, origem=PENDENCIA_ORIGEM_GALPAO,
        descricao='defeito', operador_id=admin_user.id,
    )


def test_consumir_peca_inexistente_erro_claro(app, admin_user):
    with app.app_context():
        chassi = f'TSTG{uuid.uuid4().hex[:6].upper()}'
        _moto(chassi, admin_user)
        f = _ficha(chassi, admin_user)
        with pytest.raises(EstoqueError, match='peca'):
            consumir(peca_id=999999999, quantidade=1, pendencia_id=f.id,
                     chassi_destino=chassi, operador_id=admin_user.id)
        db.session.rollback()


def test_canibalizar_peca_inexistente_erro_claro(app, admin_user):
    with app.app_context():
        recep = f'TSTR{uuid.uuid4().hex[:6].upper()}'
        doad = f'TSTD{uuid.uuid4().hex[:6].upper()}'
        _moto(recep, admin_user); _moto(doad, admin_user)
        f = _ficha(recep, admin_user)
        with pytest.raises(EstoqueError, match='peca'):
            canibalizar(peca_id=999999999, quantidade=1, chassi_origem=doad,
                        chassi_destino=recep, pendencia_id=f.id, operador_id=admin_user.id)
        db.session.rollback()


def test_canibalizar_doador_inexistente_erro(app, admin_user):
    with app.app_context():
        recep = f'TSTR{uuid.uuid4().hex[:6].upper()}'
        _moto(recep, admin_user)
        p = _peca(admin_user); f = _ficha(recep, admin_user)
        with pytest.raises(EstoqueError, match='[Dd]oador'):
            canibalizar(peca_id=p.id, quantidade=1, chassi_origem='NAOEXISTE999',
                        chassi_destino=recep, pendencia_id=f.id, operador_id=admin_user.id)
        db.session.rollback()


def test_canibalizar_anti_cascata_doador_ja_em_falta_da_peca(app, admin_user):
    with app.app_context():
        recep = f'TSTR{uuid.uuid4().hex[:6].upper()}'
        doad = f'TSTD{uuid.uuid4().hex[:6].upper()}'
        _moto(recep, admin_user); _moto(doad, admin_user)
        p = _peca(admin_user); f = _ficha(recep, admin_user)
        # doador ja tem FALTA_PECA aberta DA MESMA peca
        abrir_pendencia(chassi=doad, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                        origem=PENDENCIA_ORIGEM_GALPAO, descricao='ja falta',
                        peca_id=p.id, operador_id=admin_user.id)
        with pytest.raises(EstoqueError, match='[Cc]ascata|[Ff]alta'):
            canibalizar(peca_id=p.id, quantidade=1, chassi_origem=doad,
                        chassi_destino=recep, pendencia_id=f.id, operador_id=admin_user.id)
        db.session.rollback()

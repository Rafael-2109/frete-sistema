import uuid
from decimal import Decimal

import pytest
from app import db
from app.motos_assai.models import AssaiModelo, AssaiPeca, AssaiPecaModelo
from app.motos_assai.services.peca_service import (
    criar_peca, editar_peca, vincular_modelo, desvincular_modelo,
    listar_compativeis, listar, PecaError,
)


def _nome():
    return f'PECA_{uuid.uuid4().hex[:8].upper()}'


def test_criar_peca_simples(app, admin_user):
    with app.app_context():
        p = criar_peca(nome=_nome(), codigo='C-1', custo_referencia='12.50',
                       operador_id=admin_user.id)
        assert p.id is not None
        assert p.ativo is True
        assert p.custo_referencia == Decimal('12.50')
        db.session.rollback()


def test_criar_peca_com_modelos(app, admin_user):
    with app.app_context():
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        p = criar_peca(nome=_nome(), modelo_ids=[modelo.id], operador_id=admin_user.id)
        compat = listar_compativeis(modelo.id)
        assert p.id in [x.id for x in compat]
        db.session.rollback()


def test_vincular_desvincular_idempotente(app, admin_user):
    with app.app_context():
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        p = criar_peca(nome=_nome(), operador_id=admin_user.id)
        vincular_modelo(peca_id=p.id, modelo_id=modelo.id)
        vincular_modelo(peca_id=p.id, modelo_id=modelo.id)  # idempotente
        assert AssaiPecaModelo.query.filter_by(peca_id=p.id, modelo_id=modelo.id).count() == 1
        desvincular_modelo(peca_id=p.id, modelo_id=modelo.id)
        assert AssaiPecaModelo.query.filter_by(peca_id=p.id, modelo_id=modelo.id).count() == 0
        db.session.rollback()


def test_editar_peca(app, admin_user):
    with app.app_context():
        p = criar_peca(nome=_nome(), operador_id=admin_user.id)
        editar_peca(peca_id=p.id, nome='NOVO NOME', ativo=False)
        assert p.nome == 'NOVO NOME'
        assert p.ativo is False
        db.session.rollback()


def test_criar_peca_sem_nome_falha(app, admin_user):
    with app.app_context():
        with pytest.raises(PecaError):
            criar_peca(nome='  ', operador_id=admin_user.id)
        db.session.rollback()


def test_listar_filtra_inativos_e_busca(app, admin_user):
    with app.app_context():
        nome = _nome()
        p = criar_peca(nome=nome, operador_id=admin_user.id)
        assert p.id in [x.id for x in listar(busca=nome)]
        editar_peca(peca_id=p.id, ativo=False)
        assert p.id not in [x.id for x in listar(ativo=True, busca=nome)]
        assert p.id in [x.id for x in listar(ativo=False, busca=nome)]
        db.session.rollback()

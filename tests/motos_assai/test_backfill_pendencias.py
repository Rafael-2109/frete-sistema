import uuid
import importlib.util
import os
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiMotoEvento, AssaiPendencia,
    EVENTO_ESTOQUE, EVENTO_PENDENTE,
    PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_ORIGEM_GALPAO,
    PENDENCIA_CATEGORIA_REVISAO, PENDENCIA_ORIGEM_DEVOLUCAO,
)
from app.motos_assai.services.moto_evento_service import emitir_evento

_SPEC = importlib.util.spec_from_file_location(
    'motos_assai_35_backfill_pendencias',
    os.path.join(
        os.path.dirname(__file__), '..', '..',
        'scripts', 'migrations', 'motos_assai_35_backfill_pendencias.py',
    ),
)
backfill_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(backfill_mod)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _moto_pendente_legacy(chassi, admin_user):
    """Simula chassi legado: PENDENTE direto via evento, SEM ficha."""
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
    ev = emitir_evento(
        chassi, EVENTO_PENDENTE, admin_user.id,
        observacao='Defeito legado', dados_extras={'descricao': 'Defeito legado'},
    )
    db.session.commit()
    return ev


def _moto_devolucao_legacy(chassi, admin_user):
    """Simula chassi legado de devolucao: PENDENTE com origem devolucao_nfd, SEM ficha."""
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
    ev = emitir_evento(
        chassi, EVENTO_PENDENTE, admin_user.id,
        observacao='Moto devolvida pelo cliente',
        dados_extras={'origem': 'devolucao_nfd', 'descricao': 'Moto devolvida pelo cliente'},
    )
    db.session.commit()
    return ev


def test_backfill_cria_ficha_indeterminada(app, admin_user):
    with app.app_context():
        chassi = f'TST_BF_{_uid()}'
        ev = _moto_pendente_legacy(chassi, admin_user)
        try:
            assert AssaiPendencia.query.filter_by(chassi=chassi).count() == 0
            res = backfill_mod.backfill(confirmar=True)
            assert res['criadas'] >= 1
            f = AssaiPendencia.query.filter_by(chassi=chassi).first()
            assert f is not None
            assert f.categoria == PENDENCIA_CATEGORIA_INDETERMINADA
            assert f.origem == PENDENCIA_ORIGEM_GALPAO
            assert f.evento_pendente_id == ev.id
            assert f.descricao == 'Defeito legado'
            assert (f.detalhes or {}).get('legacy_backfill') is True
            # Garante que NAO emitiu 2o PENDENTE
            n_pendentes = AssaiMotoEvento.query.filter_by(
                chassi=chassi, tipo=EVENTO_PENDENTE
            ).count()
            assert n_pendentes == 1
        finally:
            AssaiPendencia.query.filter_by(chassi=chassi).delete()
            db.session.commit()


def test_backfill_cria_ficha_devolucao(app, admin_user):
    """Chassi legado de devolucao (dados_extras['origem']=='devolucao_nfd')
    deve gerar ficha REVISAO/DEVOLUCAO."""
    with app.app_context():
        chassi = f'TST_BF_{_uid()}'
        ev = _moto_devolucao_legacy(chassi, admin_user)
        try:
            assert AssaiPendencia.query.filter_by(chassi=chassi).count() == 0
            res = backfill_mod.backfill(confirmar=True)
            assert res['criadas'] >= 1
            f = AssaiPendencia.query.filter_by(chassi=chassi).first()
            assert f is not None
            assert f.categoria == PENDENCIA_CATEGORIA_REVISAO
            assert f.origem == PENDENCIA_ORIGEM_DEVOLUCAO
            assert f.evento_pendente_id == ev.id
            assert (f.detalhes or {}).get('legacy_backfill') is True
            # Garante que NAO emitiu 2o PENDENTE
            n_pendentes = AssaiMotoEvento.query.filter_by(
                chassi=chassi, tipo=EVENTO_PENDENTE
            ).count()
            assert n_pendentes == 1
        finally:
            AssaiPendencia.query.filter_by(chassi=chassi).delete()
            db.session.commit()


def test_backfill_idempotente(app, admin_user):
    with app.app_context():
        chassi = f'TST_BF_{_uid()}'
        _moto_pendente_legacy(chassi, admin_user)
        try:
            backfill_mod.backfill(confirmar=True)
            n1 = AssaiPendencia.query.filter_by(chassi=chassi).count()
            backfill_mod.backfill(confirmar=True)
            n2 = AssaiPendencia.query.filter_by(chassi=chassi).count()
            assert n1 == 1 and n2 == 1
        finally:
            AssaiPendencia.query.filter_by(chassi=chassi).delete()
            db.session.commit()


def test_dry_run_nao_grava(app, admin_user):
    with app.app_context():
        chassi = f'TST_BF_{_uid()}'
        _moto_pendente_legacy(chassi, admin_user)
        try:
            res = backfill_mod.backfill(confirmar=False)
            assert res['plano'] >= 1
            assert AssaiPendencia.query.filter_by(chassi=chassi).count() == 0
        finally:
            AssaiPendencia.query.filter(
                AssaiPendencia.chassi == chassi).delete()
            db.session.commit()


def test_verificar_detecta_gap(app, admin_user):
    """`verificar()` retorna >= 1 quando ha chassi PENDENTE sem ficha."""
    with app.app_context():
        chassi = f'TST_BF_{_uid()}'
        _moto_pendente_legacy(chassi, admin_user)
        try:
            n = backfill_mod.verificar()
            assert n >= 1
        finally:
            # cleanup (sem ficha pra deletar aqui)
            db.session.commit()

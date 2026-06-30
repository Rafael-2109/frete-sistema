"""Task 9: verifica que as 5 funcoes de LEITURA leem assai_pendencia, nao eventos.

Cria fichas via abrir_pendencia/resolver_pendencia e checa que
listar_abertas/listar_historico_resolvidas/contar/operadores/modelos refletem
as fichas — nao os eventos da assai_moto_evento.
"""
import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiPendencia,
    EVENTO_ESTOQUE,
    PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_ORIGEM_GALPAO,
)
from app.motos_assai.services import pendencia_service
from app.motos_assai.services.moto_evento_service import emitir_evento


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _moto_estoque(chassi, admin_user):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
    db.session.commit()


def test_listar_abertas_le_a_tabela(app, admin_user):
    with app.app_context():
        chassi = f'TST_PR_{_uid()}'
        _moto_estoque(chassi, admin_user)
        ficha = pendencia_service.abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Bateria com defeito',
            operador_id=admin_user.id,
        )
        db.session.commit()
        try:
            abertas = pendencia_service.listar_abertas()
            achou = [a for a in abertas if a['chassi'] == chassi]
            assert len(achou) == 1
            assert achou[0]['observacao'] == 'Bateria com defeito'
            assert achou[0]['modelo_codigo'] == 'DOT'
            assert pendencia_service.contar_pendencias_abertas() >= 1
        finally:
            AssaiPendencia.query.filter_by(id=ficha.id).delete()
            db.session.commit()


def test_historico_le_resolucao_da_ficha(app, admin_user):
    with app.app_context():
        chassi = f'TST_PR_{_uid()}'
        _moto_estoque(chassi, admin_user)
        ficha = pendencia_service.abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta parafuso',
            operador_id=admin_user.id,
        )
        db.session.commit()
        pendencia_service.resolver_pendencia(
            pendencia_id=ficha.id, tratativa='CONSERTAR',
            resolucao_descricao='Parafuso colocado', operador_id=admin_user.id,
        )
        db.session.commit()
        try:
            hist = pendencia_service.listar_historico_resolvidas()
            achou = [h for h in hist if h['chassi'] == chassi]
            assert len(achou) == 1
            assert achou[0]['descricao_resolucao'] == 'Parafuso colocado'
            assert achou[0]['observacao_pendencia'] == 'Falta parafuso'
            assert pendencia_service.listar_abertas() is not None
            assert chassi not in [a['chassi'] for a in pendencia_service.listar_abertas()]
        finally:
            AssaiPendencia.query.filter_by(id=ficha.id).delete()
            db.session.commit()


def test_contar_pendencias_abertas_le_tabela(app, admin_user):
    """contar_pendencias_abertas conta fichas abertas na tabela, nao eventos."""
    with app.app_context():
        chassi = f'TST_PR_{_uid()}'
        _moto_estoque(chassi, admin_user)
        antes = pendencia_service.contar_pendencias_abertas()
        ficha = pendencia_service.abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Defeito no motor',
            operador_id=admin_user.id,
        )
        db.session.commit()
        try:
            depois = pendencia_service.contar_pendencias_abertas()
            assert depois == antes + 1
        finally:
            AssaiPendencia.query.filter_by(id=ficha.id).delete()
            db.session.commit()


def test_operadores_que_registraram_pendencia_le_tabela(app, admin_user):
    """operadores_que_registraram_pendencia retorna lista de dicts {id, nome, email}."""
    with app.app_context():
        chassi = f'TST_PR_{_uid()}'
        _moto_estoque(chassi, admin_user)
        ficha = pendencia_service.abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Teste operadores',
            operador_id=admin_user.id,
        )
        db.session.commit()
        try:
            ops = pendencia_service.operadores_que_registraram_pendencia()
            assert isinstance(ops, list)
            ids = [o['id'] for o in ops]
            assert admin_user.id in ids
            # verifica shape do dict
            for o in ops:
                assert 'id' in o
                assert 'nome' in o
                assert 'email' in o
        finally:
            AssaiPendencia.query.filter_by(id=ficha.id).delete()
            db.session.commit()


def test_modelos_com_pendencias_le_tabela(app, admin_user):
    """modelos_com_pendencias retorna lista de dicts {id, codigo, nome}."""
    with app.app_context():
        chassi = f'TST_PR_{_uid()}'
        _moto_estoque(chassi, admin_user)
        ficha = pendencia_service.abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Teste modelos',
            operador_id=admin_user.id,
        )
        db.session.commit()
        try:
            modelos = pendencia_service.modelos_com_pendencias()
            assert isinstance(modelos, list)
            codigos = [m['codigo'] for m in modelos]
            assert 'DOT' in codigos
            for m in modelos:
                assert 'id' in m
                assert 'codigo' in m
                assert 'nome' in m
        finally:
            AssaiPendencia.query.filter_by(id=ficha.id).delete()
            db.session.commit()

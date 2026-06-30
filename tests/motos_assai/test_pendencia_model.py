import uuid

from app import db
from app.motos_assai.models import (
    AssaiPendencia,
    PENDENCIA_CATEGORIA_REVISAO, PENDENCIA_CATEGORIA_AVARIA,
    PENDENCIA_ORIGEM_GALPAO, PENDENCIA_ORIGEM_DEVOLUCAO,
    PENDENCIA_CATEGORIAS_VALIDAS, PENDENCIA_ORIGENS_VALIDAS, ORIGENS_FISICAS,
    PENDENCIA_FASES_VALIDAS, PENDENCIA_TRATATIVAS_VALIDAS,
)


def _chassi():
    return f'TST_{uuid.uuid4().hex[:8].upper()}'


def test_sets_de_taxonomia():
    assert PENDENCIA_CATEGORIAS_VALIDAS == {
        'AVARIA', 'FALTA_PECA', 'REVISAO', 'VENDA', 'INDETERMINADA'}
    assert PENDENCIA_ORIGENS_VALIDAS == {
        'GALPAO', 'TRANSPORTE', 'POS_VENDA_CLIENTE', 'POS_VENDA_LOJA', 'DEVOLUCAO'}
    assert ORIGENS_FISICAS == {'GALPAO', 'TRANSPORTE', 'DEVOLUCAO'}
    assert PENDENCIA_FASES_VALIDAS == {'ABERTA', 'EM_TRATATIVA', 'AGUARDANDO_PECA'}
    assert PENDENCIA_TRATATIVAS_VALIDAS == {
        'USAR_ESTOQUE', 'USAR_OUTRA_MOTO', 'CONSERTAR', 'REVISAR'}


def test_criar_ficha_defaults(app, admin_user):
    with app.app_context():
        p = AssaiPendencia(
            chassi=_chassi(), categoria=PENDENCIA_CATEGORIA_AVARIA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Fio solto',
            aberta_por_id=admin_user.id,
        )
        db.session.add(p)
        db.session.flush()
        assert p.id is not None
        assert p.fase == 'ABERTA'
        assert p.retorno_fisico is False
        assert p.esta_aberta is True
        db.session.rollback()


def test_status_derivado(app, admin_user):
    with app.app_context():
        from app.utils.timezone import agora_brasil_naive
        p = AssaiPendencia(
            chassi=_chassi(), categoria=PENDENCIA_CATEGORIA_AVARIA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='X', aberta_por_id=admin_user.id,
        )
        db.session.add(p)
        db.session.flush()
        assert p.esta_aberta is True
        p.resolvida_em = agora_brasil_naive()
        db.session.flush()
        assert p.esta_aberta is False
        db.session.rollback()


def test_auto_relacao_pai_filhas(app, admin_user):
    with app.app_context():
        ch = _chassi()
        mae = AssaiPendencia(
            chassi=ch, categoria=PENDENCIA_CATEGORIA_REVISAO,
            origem=PENDENCIA_ORIGEM_DEVOLUCAO, descricao='Revisao devolucao',
            aberta_por_id=admin_user.id,
        )
        db.session.add(mae)
        db.session.flush()
        filha = AssaiPendencia(
            chassi=ch, categoria=PENDENCIA_CATEGORIA_AVARIA,
            origem=PENDENCIA_ORIGEM_DEVOLUCAO, descricao='Avaria achada na revisao',
            pendencia_pai_id=mae.id, aberta_por_id=admin_user.id,
        )
        db.session.add(filha)
        db.session.flush()
        db.session.refresh(mae)
        assert filha.pai.id == mae.id
        assert filha.id in [f.id for f in mae.filhas]
        db.session.rollback()

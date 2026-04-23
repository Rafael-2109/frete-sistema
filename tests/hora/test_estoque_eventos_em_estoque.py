"""Valida ajustes em EVENTOS_EM_ESTOQUE e novo helper listar_em_transito."""
from app.hora.services import estoque_service
from app.hora.services.moto_service import registrar_evento


def test_cancelada_esta_em_eventos_em_estoque():
    """Moto com ultimo evento CANCELADA deve ser visivel (voltou origem)."""
    assert 'CANCELADA' in estoque_service.EVENTOS_EM_ESTOQUE


def test_em_transito_nao_esta_em_eventos_em_estoque():
    """Moto em transito esta em limbo — nao conta como estoque."""
    assert 'EM_TRANSITO' not in estoque_service.EVENTOS_EM_ESTOQUE


def test_listar_em_transito_retorna_moto_recem_emitida(
    db, chassi_em_estoque, loja_destino,
):
    from app import db as _db
    registrar_evento(
        numero_chassi=chassi_em_estoque, tipo='EM_TRANSITO',
        loja_id=loja_destino.id, operador='teste',
    )
    _db.session.flush()
    em_transito = estoque_service.listar_em_transito(
        lojas_permitidas_ids=[loja_destino.id],
    )
    chassis = [m['numero_chassi'] for m in em_transito]
    assert chassi_em_estoque in chassis


def test_listar_em_transito_filtrado_por_loja_permitida(
    db, chassi_em_estoque, loja_destino,
):
    from app import db as _db
    registrar_evento(
        numero_chassi=chassi_em_estoque, tipo='EM_TRANSITO',
        loja_id=loja_destino.id, operador='teste',
    )
    _db.session.flush()
    em_transito = estoque_service.listar_em_transito(
        lojas_permitidas_ids=[999999],
    )
    assert all(m['numero_chassi'] != chassi_em_estoque for m in em_transito)

"""Valida ajustes em EVENTOS_EM_ESTOQUE e novo helper listar_em_transito."""
from app.hora.services import estoque_service, transferencia_service


def test_cancelada_esta_em_eventos_em_estoque():
    """Moto com ultimo evento CANCELADA deve ser visivel (voltou origem)."""
    assert 'CANCELADA' in estoque_service.EVENTOS_EM_ESTOQUE


def test_em_transito_nao_esta_em_eventos_em_estoque():
    """Moto em transito esta em limbo — nao conta como estoque."""
    assert 'EM_TRANSITO' not in estoque_service.EVENTOS_EM_ESTOQUE


def test_listar_em_transito_visivel_pelo_destino(
    db, chassi_em_estoque, loja_origem, loja_destino,
):
    transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id,
        loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque],
        usuario='emissor',
    )
    em_transito = estoque_service.listar_em_transito(
        lojas_permitidas_ids=[loja_destino.id],
    )
    chassis = [m['numero_chassi'] for m in em_transito]
    assert chassi_em_estoque in chassis


def test_listar_em_transito_visivel_pela_origem(
    db, chassi_em_estoque, loja_origem, loja_destino,
):
    """Origem tambem deve ver motos que acabou de enviar."""
    transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id,
        loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque],
        usuario='emissor',
    )
    em_transito = estoque_service.listar_em_transito(
        lojas_permitidas_ids=[loja_origem.id],
    )
    chassis = [m['numero_chassi'] for m in em_transito]
    assert chassi_em_estoque in chassis


def test_listar_em_transito_filtrado_por_loja_permitida(
    db, chassi_em_estoque, loja_origem, loja_destino,
):
    transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id,
        loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque],
        usuario='emissor',
    )
    em_transito = estoque_service.listar_em_transito(
        lojas_permitidas_ids=[999999],
    )
    assert all(m['numero_chassi'] != chassi_em_estoque for m in em_transito)

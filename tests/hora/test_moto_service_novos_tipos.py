"""Valida que EM_TRANSITO e CANCELADA estao em TIPOS_VALIDOS."""
import pytest

from app.hora.services.moto_service import registrar_evento


def test_em_transito_e_tipo_valido(chassi_em_estoque, loja_destino):
    ev = registrar_evento(
        numero_chassi=chassi_em_estoque,
        tipo='EM_TRANSITO',
        loja_id=loja_destino.id,
        operador='teste',
    )
    assert ev.tipo == 'EM_TRANSITO'


def test_cancelada_e_tipo_valido(chassi_em_estoque, loja_origem):
    ev = registrar_evento(
        numero_chassi=chassi_em_estoque,
        tipo='CANCELADA',
        loja_id=loja_origem.id,
        operador='teste',
    )
    assert ev.tipo == 'CANCELADA'


def test_tipo_invalido_falha(chassi_em_estoque, loja_origem):
    with pytest.raises(ValueError, match="Tipo de evento inválido"):
        registrar_evento(
            numero_chassi=chassi_em_estoque,
            tipo='INEXISTENTE',
            loja_id=loja_origem.id,
            operador='teste',
        )

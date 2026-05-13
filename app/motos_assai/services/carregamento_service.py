"""Service de Carregamento (Fase 2 + 3).

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md
"""
from app import db
from app.motos_assai.models import (
    AssaiCarregamento,
    AssaiPedidoVenda, AssaiLoja,
    CARREGAMENTO_STATUS_EM_CARREGAMENTO,
)
from app.utils.timezone import agora_brasil_naive


# ============================================================
# Exceptions
# ============================================================

class CarregamentoError(Exception):
    """Erro base de carregamento_service."""


class CarregamentoValidationError(CarregamentoError):
    """Validacao de input falhou (pedido/loja inexistente, etc.)."""


class CarregamentoConflictError(CarregamentoError):
    """Race condition (chassi ja em outro carregamento, etc.) — retorna HTTP 409."""


class CarregamentoStateError(CarregamentoError):
    """Operacao invalida no estado atual (ex: cancelar carregamento ja FINALIZADO sem motivo)."""


class CarregamentoExcedenteError(CarregamentoError):
    """Finalizar carregamento excederia qtd do pedido — operador deve resolver (S14=a)."""

    def __init__(self, msg, *, qtd_excedente=None, seps_bloqueadas=None):
        super().__init__(msg)
        self.qtd_excedente = qtd_excedente
        self.seps_bloqueadas = seps_bloqueadas or []  # lista de sep_ids CARREGADA/FATURADA


# ============================================================
# CRUD basico
# ============================================================

def criar_carregamento(pedido_id, loja_id, operador_id):
    """Cria novo Carregamento em status EM_CARREGAMENTO.

    A2: NAO ha UNIQUE em (pedido, loja, EM_CARREGAMENTO) — N carregamentos
    paralelos sao permitidos.

    Args:
        pedido_id: ID do AssaiPedidoVenda (deve existir)
        loja_id: ID da AssaiLoja (deve existir)
        operador_id: ID do usuario que iniciou

    Returns:
        AssaiCarregamento criado (status EM_CARREGAMENTO).

    Raises:
        CarregamentoValidationError: pedido ou loja nao existem.
    """
    pedido = AssaiPedidoVenda.query.get(pedido_id)
    if not pedido:
        raise CarregamentoValidationError(f'Pedido {pedido_id} nao encontrado')

    loja = AssaiLoja.query.get(loja_id)
    if not loja:
        raise CarregamentoValidationError(f'Loja {loja_id} nao encontrada')

    car = AssaiCarregamento(
        pedido_id=pedido_id,
        loja_id=loja_id,
        status=CARREGAMENTO_STATUS_EM_CARREGAMENTO,
        iniciado_em=agora_brasil_naive(),
        iniciado_por_id=operador_id,
    )
    db.session.add(car)
    db.session.flush()  # garante car.id disponivel; commit fica para o caller
    return car

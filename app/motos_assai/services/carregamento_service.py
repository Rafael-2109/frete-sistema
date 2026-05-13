"""Service de Carregamento (Fase 2 + 3).

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md
"""
from app import db
from app.motos_assai.models import (
    AssaiCarregamento, AssaiCarregamentoItem, AssaiSeparacao, AssaiSeparacaoItem,
    AssaiSeparacaoSaldoModelo,
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiLoja, AssaiMoto,
    CARREGAMENTO_STATUS_EM_CARREGAMENTO,
    CARREGAMENTO_STATUS_FINALIZADO, CARREGAMENTO_STATUS_CANCELADO,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_CARREGADA,
)
from app.motos_assai.services.moto_evento_service import emitir_evento
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


def escanear_carregamento_item(carregamento_id, chassi, operador_id):
    """Adiciona chassi ao carregamento ativo.

    S3=c: lock pessimista em assai_moto + valida que chassi NAO esta em outro
    carregamento ativo (EM_CARREGAMENTO).

    A1: NAO emite evento (estado muda apenas no finalize).

    Args:
        carregamento_id: ID do carregamento (deve estar EM_CARREGAMENTO)
        chassi: chassi a adicionar
        operador_id: usuario que escaneou

    Returns:
        AssaiCarregamentoItem criado.

    Raises:
        CarregamentoValidationError: chassi inexistente em assai_moto
        CarregamentoStateError: carregamento nao esta EM_CARREGAMENTO
        CarregamentoConflictError: chassi ja em outro carregamento ativo
    """
    car = AssaiCarregamento.query.get(carregamento_id)
    if not car:
        raise CarregamentoValidationError(f'Carregamento {carregamento_id} nao encontrado')
    if car.status != CARREGAMENTO_STATUS_EM_CARREGAMENTO:
        raise CarregamentoStateError(
            f'Carregamento {carregamento_id} esta {car.status} '
            f'(esperado EM_CARREGAMENTO)'
        )

    # Lock pessimista no chassi (S3=c)
    moto = (AssaiMoto.query
            .filter_by(chassi=chassi)
            .with_for_update()
            .first())
    if not moto:
        raise CarregamentoValidationError(f'Chassi {chassi} nao cadastrado em assai_moto')

    # Validar chassi NAO esta em outro carregamento ativo
    item_em_outro = (AssaiCarregamentoItem.query
                     .join(AssaiCarregamento)
                     .filter(
                         AssaiCarregamentoItem.chassi == chassi,
                         AssaiCarregamento.status == CARREGAMENTO_STATUS_EM_CARREGAMENTO,
                         AssaiCarregamento.id != carregamento_id,
                     )
                     .first())
    if item_em_outro:
        raise CarregamentoConflictError(
            f'Chassi {chassi} ja esta no Carregamento #{item_em_outro.carregamento_id} '
            f'(EM_CARREGAMENTO). Cancele ou finalize o outro antes.'
        )

    # Validar chassi nao ja escaneado no MESMO carregamento (idempotencia)
    ja_escaneado = AssaiCarregamentoItem.query.filter_by(
        carregamento_id=carregamento_id, chassi=chassi,
    ).first()
    if ja_escaneado:
        raise CarregamentoConflictError(
            f'Chassi {chassi} ja foi escaneado neste Carregamento (item #{ja_escaneado.id})'
        )

    item = AssaiCarregamentoItem(
        carregamento_id=carregamento_id,
        chassi=chassi,
        modelo_id=moto.modelo_id,
        escaneado_em=agora_brasil_naive(),
        escaneado_por_id=operador_id,
    )
    db.session.add(item)
    db.session.flush()
    return item


# ============================================================
# Alterar (S6=a reabre)
# ============================================================

def alterar_carregamento(carregamento_id, operador_id):
    """Reabre Carregamento FINALIZADO para edicao (S6=a).

    Status: FINALIZADO -> EM_CARREGAMENTO.
    Reset campos: finalizado_em, finalizado_por_id.
    Items existentes (assai_carregamento_item) NAO sao tocados — operador
    pode adicionar/remover via escanear_carregamento_item / cancelar_carregamento_item.

    Quando re-finalizar, executa Fase 2-6 do algoritmo §6 novamente
    (sep alvo pode mudar; chassis recalculados; Excel regenerado).

    H3 fix — regredir Sep vinculada (CARREGADA -> FECHADA) para manter
    invariante "Sep CARREGADA <-> Carregamento FINALIZADO". Sep mantem chassis
    (re-finalizar vai re-ajustar via algoritmo §6 Fase 2). Mantem
    car.separacao_id (vinculo FK preservado para que finalize re-use a mesma sep).

    Args:
        carregamento_id: ID do carregamento (deve estar FINALIZADO).
        operador_id: usuario que solicitou a alteracao.

    Raises:
        CarregamentoValidationError: carregamento nao existe.
        CarregamentoStateError: nao esta FINALIZADO (ja EM_CARREGAMENTO ou CANCELADO).
    """
    car = AssaiCarregamento.query.get(carregamento_id)
    if not car:
        raise CarregamentoValidationError(
            f'Carregamento {carregamento_id} nao encontrado'
        )

    if car.status == CARREGAMENTO_STATUS_EM_CARREGAMENTO:
        raise CarregamentoStateError(
            f'Carregamento {carregamento_id} ja EM_CARREGAMENTO — nao precisa alterar'
        )
    if car.status == CARREGAMENTO_STATUS_CANCELADO:
        raise CarregamentoStateError(
            f'Carregamento {carregamento_id} esta CANCELADO — nao pode ser reaberto. '
            f'Inicie um novo carregamento.'
        )

    # FINALIZADO -> EM_CARREGAMENTO
    car.status = CARREGAMENTO_STATUS_EM_CARREGAMENTO
    car.finalizado_em = None
    car.finalizado_por_id = None

    # H3 fix — regredir Sep vinculada (CARREGADA -> FECHADA) para manter invariante
    # "Sep CARREGADA <-> Carregamento FINALIZADO". Sep mantem chassis (re-finalizar
    # vai re-ajustar via algoritmo §6 Fase 2). Mantem car.separacao_id (vinculo
    # FK preservado para que finalize re-use a mesma sep).
    if car.separacao_id:
        sep = AssaiSeparacao.query.get(car.separacao_id)
        if sep and sep.status == SEPARACAO_STATUS_CARREGADA:
            sep.status = SEPARACAO_STATUS_FECHADA
            # Sep volta a estado "pronta para Carregamento". Chassis nao mudam de evento
            # (ja estao com evento CARREGADA — proximo finalize pode mudar).

    db.session.flush()


# ============================================================
# Helpers para finalize
# ============================================================

def _calcular_count_em_comum(sep, chassis):
    """Helper: conta chassis em comum entre uma sep e lista de chassis."""
    chassis_sep = {it.chassi for it in sep.itens}
    return len(chassis_sep & set(chassis))


def _saldo_pendente_modelo(sep_id, modelo_id):
    """Helper: qtd_planejada - qtd_separada para um modelo na sep.

    Retorna 0 se nao ha saldo planejado para o modelo.
    """
    saldo_obj = (db.session.query(AssaiSeparacaoSaldoModelo)
                 .filter_by(separacao_id=sep_id, modelo_id=modelo_id)
                 .first())
    if not saldo_obj:
        return 0

    qtd_separada = (db.session.query(db.func.count(AssaiSeparacaoItem.id))
                    .filter_by(separacao_id=sep_id, modelo_id=modelo_id)
                    .scalar() or 0)
    return max(0, saldo_obj.qtd_planejada - qtd_separada)


def _resolver_valor_unitario(car, modelo_id):
    """Helper: pega valor_unitario do AssaiPedidoVendaItem para esse modelo no pedido."""
    item_pedido = (AssaiPedidoVendaItem.query
                   .filter_by(pedido_id=car.pedido_id, loja_id=car.loja_id, modelo_id=modelo_id)
                   .first())
    return float(item_pedido.valor_unitario) if item_pedido else 0.0


# ============================================================
# Algoritmo finalizar_carregamento (8 fases)
# ============================================================

def finalizar_carregamento(carregamento_id, operador_id):
    """Finaliza Carregamento - algoritmo §6 (8 fases).

    Tasks 5-12 implementam fases 1-8 incrementalmente.
    Esta versao (Task 5) implementa apenas Fase 1.

    Args:
        carregamento_id: ID do carregamento (deve estar EM_CARREGAMENTO)
        operador_id: usuario que finalizou

    Returns:
        AssaiSeparacao alvo (criada ou ajustada).

    Raises:
        CarregamentoValidationError: carregamento nao existe
        CarregamentoStateError: carregamento nao esta EM_CARREGAMENTO
        CarregamentoExcedenteError: Fase 3 - excederia pedido (Task 7)
    """
    car = AssaiCarregamento.query.get(carregamento_id)
    if not car:
        raise CarregamentoValidationError(f'Carregamento {carregamento_id} nao encontrado')
    if car.status != CARREGAMENTO_STATUS_EM_CARREGAMENTO:
        raise CarregamentoStateError(
            f'Carregamento {carregamento_id} esta {car.status} (esperado EM_CARREGAMENTO)'
        )

    chassis_car = [item.chassi for item in car.itens]
    if not chassis_car:
        raise CarregamentoValidationError(
            f'Carregamento {carregamento_id} esta vazio - nao pode ser finalizado'
        )

    # === FASE 1: identificar ou criar Sep alvo ===
    # S18=b/A2: Sep CARREGADA/FATURADA NAO entra no match (1:1).
    seps_ativas = (AssaiSeparacao.query
                   .filter_by(pedido_id=car.pedido_id, loja_id=car.loja_id)
                   .filter(AssaiSeparacao.status.in_([
                       SEPARACAO_STATUS_EM_SEPARACAO,
                       SEPARACAO_STATUS_FECHADA,
                   ]))
                   .all())

    if not seps_ativas:
        # Q4/Q6: criar Sep automaticamente em CARREGADA
        # A9: fechada_em + fechada_por_id usam operador_id
        sep_alvo = AssaiSeparacao(
            pedido_id=car.pedido_id, loja_id=car.loja_id,
            status=SEPARACAO_STATUS_CARREGADA,  # pula EM_SEPARACAO + FECHADA
            iniciada_em=agora_brasil_naive(),
            fechada_em=agora_brasil_naive(),
            fechada_por_id=operador_id,  # A9
        )
        db.session.add(sep_alvo)
        db.session.flush()
    else:
        # Q5: match por chassis em comum (mais matches = sep alvo)
        sep_alvo = max(seps_ativas, key=lambda s: _calcular_count_em_comum(s, chassis_car))
        # NOTA: status final atribuido na Fase 4

    # === FASES 2-8: implementadas em Tasks 6-12 ===
    # Por ora, marcar sep como CARREGADA + finalizar carregamento (esqueleto)
    sep_alvo.status = SEPARACAO_STATUS_CARREGADA
    car.separacao_id = sep_alvo.id
    car.status = CARREGAMENTO_STATUS_FINALIZADO
    car.finalizado_em = agora_brasil_naive()
    car.finalizado_por_id = operador_id
    db.session.flush()

    return sep_alvo

"""Service de Carregamento (Fase 2 + 3).

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md
"""
from sqlalchemy.exc import IntegrityError

from app import db
from app.motos_assai.models import (
    AssaiCarregamento, AssaiCarregamentoItem, AssaiSeparacao, AssaiSeparacaoItem,
    AssaiSeparacaoSaldoModelo,
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiLoja, AssaiMoto,
    AssaiPedidoExcel,
    AssaiNfQpa,
    CARREGAMENTO_STATUS_EM_CARREGAMENTO,
    CARREGAMENTO_STATUS_FINALIZADO, CARREGAMENTO_STATUS_CANCELADO,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_CARREGADA, SEPARACAO_STATUS_FATURADA,
    SEPARACAO_STATUS_CANCELADA,
    EVENTO_SEPARADA, EVENTO_DISPONIVEL, EVENTO_CARREGADA,
    NF_STATUS_BATEU, NF_STATUS_DIVERGENTE, NF_STATUS_CANCELADA,
    DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO,
    DIVERGENCIA_TIPO_CARREGAMENTO_CHASSI_FORA_NF,
)
from app.motos_assai.services.moto_evento_service import emitir_evento
from app.motos_assai.services.faturamento_service import gerar_excel_qpa
from app.motos_assai.services.pedido_status_service import recalcular_status_pedido
from app.motos_assai.services.separacao_mirror_service import sincronizar_espelho_com_separacao
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


def cancelar_carregamento_item(item_id, operador_id):
    """Remove item do carregamento (apenas durante EM_CARREGAMENTO).

    A1: NAO emite evento (estado nunca mudou).

    Args:
        item_id: ID do AssaiCarregamentoItem
        operador_id: usuario que cancelou (para audit log futuro)

    Raises:
        CarregamentoValidationError: item nao existe
        CarregamentoStateError: carregamento ja FINALIZADO ou CANCELADO
    """
    item = AssaiCarregamentoItem.query.get(item_id)
    if not item:
        raise CarregamentoValidationError(f'Item {item_id} nao encontrado')

    car = item.carregamento
    if car.status != CARREGAMENTO_STATUS_EM_CARREGAMENTO:
        raise CarregamentoStateError(
            f'Carregamento {car.id} esta {car.status} — nao e possivel cancelar item. '
            f'Use alterar_carregamento (S6=a) para reabrir.'
        )

    db.session.delete(item)
    db.session.flush()


def cancelar_carregamento(carregamento_id, motivo, operador_id):
    """Cancela carregamento. Comportamento DEPENDE do status (S5).

    - EM_CARREGAMENTO: items deletam (cascata FK), chassis voltam ao estado anterior
      (sem mudanca de evento — A1).
    - FINALIZADO: chassis mantem SEPARADA na sep alvo (S5=b — nao desfaz adicoes).
      Apenas marca carregamento como CANCELADO. Sep pode ser cancelada separadamente.

    Args:
        carregamento_id: ID do carregamento
        motivo: justificativa (obrigatorio, min 3 chars)
        operador_id: usuario que cancelou

    Raises:
        CarregamentoValidationError: carregamento nao existe ou motivo vazio
        CarregamentoStateError: ja CANCELADO
    """
    if not motivo or len(motivo.strip()) < 3:
        raise CarregamentoValidationError('Motivo obrigatorio (min 3 chars)')

    car = AssaiCarregamento.query.get(carregamento_id)
    if not car:
        raise CarregamentoValidationError(f'Carregamento {carregamento_id} nao encontrado')
    if car.status == CARREGAMENTO_STATUS_CANCELADO:
        raise CarregamentoStateError(f'Carregamento {carregamento_id} ja CANCELADO')

    # S5: comportamento depende do status atual
    if car.status == CARREGAMENTO_STATUS_EM_CARREGAMENTO:
        # Cascata FK ON DELETE CASCADE remove items automaticamente.
        # A1: nenhum evento foi emitido durante escaneio, entao nao ha o que reverter.
        AssaiCarregamentoItem.query.filter_by(carregamento_id=car.id).delete()
    elif car.status == CARREGAMENTO_STATUS_FINALIZADO:
        # S5=b: chassis MANTEM SEPARADA na sep alvo. Nao desfaz adicoes.
        # Sep nao e tocada (pode ser cancelada separadamente via cancelar_separacao).
        pass

    car.status = CARREGAMENTO_STATUS_CANCELADO
    car.cancelado_em = agora_brasil_naive()
    car.cancelado_por_id = operador_id
    car.motivo_cancelamento = motivo
    db.session.flush()


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

    # === FASE 2: sobrescrever sep alvo (Q10) ===
    items_atuais = AssaiSeparacaoItem.query.filter_by(separacao_id=sep_alvo.id).all()
    chassis_atuais = {it.chassi for it in items_atuais}
    chassis_novos = set(chassis_car)

    # 2A — Chassis a remover (na sep mas nao no carregamento)
    chassis_remover = chassis_atuais - chassis_novos
    for chassi in chassis_remover:
        item = next(it for it in items_atuais if it.chassi == chassi)
        valor_unit_remover = item.valor_unitario_qpa
        db.session.delete(item)

        # S2=b: tentar realocar em outra sep com saldo
        moto = AssaiMoto.query.filter_by(chassi=chassi).first()
        outras_seps = (AssaiSeparacao.query
                       .filter(
                           AssaiSeparacao.pedido_id == car.pedido_id,
                           AssaiSeparacao.loja_id == car.loja_id,
                           AssaiSeparacao.id != sep_alvo.id,
                           AssaiSeparacao.status.in_([SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA]),
                       )
                       .all())

        sep_destino = None
        for sep_cand in outras_seps:
            saldo = _saldo_pendente_modelo(sep_cand.id, moto.modelo_id)
            if saldo > 0:
                sep_destino = sep_cand
                break

        if sep_destino:
            db.session.add(AssaiSeparacaoItem(
                separacao_id=sep_destino.id, chassi=chassi,
                modelo_id=moto.modelo_id,
                valor_unitario_qpa=valor_unit_remover,
            ))
            emitir_evento(chassi, EVENTO_SEPARADA, operador_id=operador_id,
                          observacao=f'realocado pelo Carregamento {car.id} (S2=b)')
        else:
            # R1.1 fallback: vai DISPONIVEL
            emitir_evento(chassi, EVENTO_DISPONIVEL, operador_id=operador_id,
                          observacao=f'expulso pelo Carregamento {car.id} (sem sep destino)')

    # 2B — Chassis a adicionar (no carregamento mas nao na sep)
    chassis_adicionar = chassis_novos - chassis_atuais
    for chassi in chassis_adicionar:
        moto = AssaiMoto.query.filter_by(chassi=chassi).first()
        # CR-6: emite SEPARADA agora; CARREGADA emitido na Fase 4 (loop unico).
        # Resultado: chassis adicionados pegam (SEPARADA, CARREGADA);
        # chassis que ja estavam na sep pegam apenas CARREGADA.
        db.session.add(AssaiSeparacaoItem(
            separacao_id=sep_alvo.id, chassi=chassi,
            modelo_id=moto.modelo_id,
            valor_unitario_qpa=_resolver_valor_unitario(car, modelo_id=moto.modelo_id),
        ))
        emitir_evento(chassi, EVENTO_SEPARADA, operador_id=operador_id,
                      observacao=f'adicionado pelo Carregamento {car.id}')

    # === FASE 3: respeitar limite do pedido (R1.2 + S14=a) ===
    qtd_pedida_total = (db.session.query(db.func.coalesce(db.func.sum(AssaiPedidoVendaItem.qtd_pedida), 0))
                        .filter(AssaiPedidoVendaItem.pedido_id == car.pedido_id)
                        .scalar() or 0)

    qtd_separada_total = (db.session.query(db.func.count(AssaiSeparacaoItem.id))
                          .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
                          .filter(
                              AssaiSeparacao.pedido_id == car.pedido_id,
                              AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
                          )
                          .scalar() or 0)

    if qtd_separada_total > qtd_pedida_total:
        excedente = qtd_separada_total - qtd_pedida_total

        # S14=a: restringir a (EM_SEPARACAO, FECHADA). NAO mexer em CARREGADA/FATURADA.
        candidatos = (AssaiSeparacaoItem.query
                      .join(AssaiSeparacao)
                      .filter(
                          AssaiSeparacao.pedido_id == car.pedido_id,
                          AssaiSeparacao.loja_id == car.loja_id,
                          AssaiSeparacao.id != sep_alvo.id,
                          AssaiSeparacao.status.in_([SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA]),
                      )
                      .order_by(AssaiSeparacaoItem.id.desc())  # LIFO (mais recentes primeiro)
                      .limit(excedente)
                      .all())

        if len(candidatos) < excedente:
            # Escalar: nao tem candidatos suficientes em (EM_SEPARACAO, FECHADA)
            seps_bloqueadas = [
                s.id for s in AssaiSeparacao.query.filter(
                    AssaiSeparacao.pedido_id == car.pedido_id,
                    AssaiSeparacao.loja_id == car.loja_id,
                    AssaiSeparacao.id != sep_alvo.id,
                    AssaiSeparacao.status.in_([SEPARACAO_STATUS_CARREGADA, SEPARACAO_STATUS_FATURADA]),
                ).all()
            ]
            # N-B5 fix: NAO chamar db.session.rollback() — caller (route) faz isso ao capturar a excecao.
            # Rollback aqui invalida transacao multi-fase, perdendo Fases 1-2.
            raise CarregamentoExcedenteError(
                f'Pedido excedido em {excedente} chassis mas apenas {len(candidatos)} '
                f'podem ser removidos automaticamente. Seps CARREGADA/FATURADA bloqueando: {seps_bloqueadas}',
                qtd_excedente=excedente,
                seps_bloqueadas=seps_bloqueadas,
            )

        for it in candidatos:
            chassi = it.chassi
            db.session.delete(it)
            emitir_evento(chassi, EVENTO_DISPONIVEL, operador_id=operador_id,
                          observacao=f'removido por excedente pedido (LIFO) - Carregamento {car.id}')

    # === FASE 4: Sep alvo CARREGADA + emitir evento CARREGADA ===
    sep_alvo.status = SEPARACAO_STATUS_CARREGADA
    car.separacao_id = sep_alvo.id
    car.status = CARREGAMENTO_STATUS_FINALIZADO
    car.finalizado_em = agora_brasil_naive()
    car.finalizado_por_id = operador_id

    # Emite CARREGADA para TODOS chassis do carregamento (chassis adicionados na Fase 2
    # ja receberam SEPARADA antes — agora pegam CARREGADA. Chassis que ja estavam na sep
    # pegam apenas CARREGADA.)
    for chassi in chassis_car:
        emitir_evento(chassi, EVENTO_CARREGADA, operador_id=operador_id,
                      observacao=f'Carregamento {car.id} finalizado',
                      dados_extras={'carregamento_id': car.id, 'sep_id': sep_alvo.id})

    db.session.flush()

    # === FASE 5: regenerar Excel Q.P.A. (D-C + S13=a + CR-9/CR-12 race fix) ===
    # CR-12: lock pessimista na sep para serializar regeneracoes concorrentes.
    AssaiSeparacao.query.filter_by(id=sep_alvo.id).with_for_update().first()

    excel_anterior = AssaiPedidoExcel.query.filter_by(
        separacao_id=sep_alvo.id, ativo=True,
    ).first()
    if excel_anterior:
        excel_anterior.ativo = False  # mantem historico

    nova_versao = (excel_anterior.versao + 1) if excel_anterior else 1

    # gerar_excel_qpa retorna (bytes, s3_key) - service existente em faturamento_service
    bytes_xlsx, s3_key = gerar_excel_qpa(sep_alvo.id, operador_id)

    # CR-9 + N-B6 fix: retry defensivo via SAVEPOINT (begin_nested) em vez de rollback completo.
    # Rollback completo desfaz Fases 1-4 inteiras. Savepoint isola apenas o INSERT do Excel.
    try:
        with db.session.begin_nested():
            db.session.add(AssaiPedidoExcel(
                pedido_id=car.pedido_id, separacao_id=sep_alvo.id,
                s3_key=s3_key, versao=nova_versao, ativo=True,
                motivo_regeneracao=f'Carregamento {car.id} finalizado',
                gerado_por_id=operador_id,
            ))
    except IntegrityError:
        # Savepoint reverteu o INSERT. Recalcula MAX e tenta de novo.
        max_versao = (db.session.query(db.func.coalesce(db.func.max(AssaiPedidoExcel.versao), 0))
                      .filter_by(separacao_id=sep_alvo.id)
                      .scalar() or 0)
        nova_versao = max_versao + 1
        db.session.add(AssaiPedidoExcel(
            pedido_id=car.pedido_id, separacao_id=sep_alvo.id,
            s3_key=s3_key, versao=nova_versao, ativo=True,
            motivo_regeneracao=f'Carregamento {car.id} finalizado (retry)',
            gerado_por_id=operador_id,
        ))
        db.session.flush()

    # === FASE 6: atualizar mirror Nacom (D-B + S12=a) ===
    # S12=a: mirror agora aceita FECHADA + CARREGADA + FATURADA na guarda
    # (atualizado em Task 15 — separacao_mirror_service.py).
    sincronizar_espelho_com_separacao(sep_alvo.id)

    # === FASE 7: detectar divergencia se NF ja existe e bateu ===
    # A3: filtra status_match != CANCELADA
    # S22=a: ignora NFs nao-BATEU
    # N-B3 fix: lazy import — divergencia_service so e criado no Plano 3 (Fase 4).
    # No Plano 2, criamos um stub minimo do divergencia_service.py para Fase 7
    # funcionar antes do Plano 3 estar completo.
    from app.motos_assai.services.divergencia_service import criar_divergencia

    nf = (AssaiNfQpa.query
          .filter_by(separacao_id=sep_alvo.id)
          .filter(AssaiNfQpa.status_match != NF_STATUS_CANCELADA)
          .first())
    if nf and nf.status_match == NF_STATUS_BATEU:
        chassis_nf = {it.chassi for it in nf.itens}
        chassis_so_car = set(chassis_car) - chassis_nf
        chassis_so_nf = chassis_nf - set(chassis_car)
        houve_divergencia = False

        for c in chassis_so_car:
            criar_divergencia(
                tipo=DIVERGENCIA_TIPO_CARREGAMENTO_CHASSI_FORA_NF,
                chassi=c, sep_id=sep_alvo.id, car_id=car.id, nf_id=nf.id,
                detalhes={'origem': 'finalizar_carregamento_fase7'},
            )
            houve_divergencia = True

        for c in chassis_so_nf:
            criar_divergencia(
                tipo=DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO,
                chassi=c, sep_id=sep_alvo.id, car_id=car.id, nf_id=nf.id,
                detalhes={'origem': 'finalizar_carregamento_fase7'},
            )
            houve_divergencia = True

        # A4: NF.status_match volta de BATEU -> DIVERGENTE quando Carregamento gera divergencia
        if houve_divergencia:
            nf.status_match = NF_STATUS_DIVERGENTE

    # === FASE 8: recalcular status pedido (A13 — defensivo) ===
    # Carregamento por si nao muda qtd_faturada (so NF muda).
    # Mas se logica futura mudar (ex: sep nasce FATURADA via A11), pode precisar.
    # Custo zero (idempotente), beneficio: cobertura defensiva.
    recalcular_status_pedido(car.pedido_id)

    db.session.flush()
    return sep_alvo

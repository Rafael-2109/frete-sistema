"""Separação por (pedido × loja). Fungível por modelo.

Estados:
- EM_SEPARACAO: criada e aceita novos chassis
- FECHADA: operador clicou Finalizar (saldo zero ou parcial)
- FATURADA: NF Q.P.A. importada e bateu
- CANCELADA: cancelada pelo operador (chassis devolvidos via novo evento DISPONIVEL)
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from app import db
from app.motos_assai.models import (
    AssaiSeparacao, AssaiSeparacaoItem, AssaiPedidoVenda, AssaiPedidoVendaItem,
    AssaiMoto, AssaiModelo,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_CANCELADA, SEPARACAO_STATUS_FATURADA,
    PEDIDO_STATUS_EM_PRODUCAO, PEDIDO_STATUS_SEPARANDO,
    EVENTO_DISPONIVEL, EVENTO_SEPARADA, EVENTO_FATURADA,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo


class SeparacaoConflictError(Exception):
    """Race ao reservar chassi (UNIQUE parcial)."""


class SeparacaoValidationError(Exception):
    pass


def get_ou_criar_separacao(pedido_id: int, loja_id: int, operador_id: int) -> AssaiSeparacao:
    """Retorna separação ativa ou cria. UNIQUE parcial garante 1 ativa por (pedido, loja)."""
    sep = (
        AssaiSeparacao.query
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.loja_id == loja_id,
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
        )
        .first()
    )
    if sep:
        return sep

    sep = AssaiSeparacao(
        pedido_id=pedido_id, loja_id=loja_id,
        status=SEPARACAO_STATUS_EM_SEPARACAO,
    )
    db.session.add(sep)
    db.session.flush()
    return sep


def saldo_pendente_por_modelo(pedido_id: int, loja_id: int) -> List[Dict[str, Any]]:
    """Retorna [{modelo_id, codigo, nome, qtd_pedida, qtd_separada, qtd_pendente, valor_unitario}]."""
    rows = (
        db.session.query(
            AssaiPedidoVendaItem.modelo_id,
            AssaiModelo.codigo,
            AssaiModelo.nome,
            AssaiPedidoVendaItem.qtd_pedida,
            AssaiPedidoVendaItem.valor_unitario,
        )
        .join(AssaiModelo, AssaiModelo.id == AssaiPedidoVendaItem.modelo_id)
        .filter(
            AssaiPedidoVendaItem.pedido_id == pedido_id,
            AssaiPedidoVendaItem.loja_id == loja_id,
        )
        .order_by(AssaiModelo.codigo)
        .all()
    )

    # SUM já separado por (modelo) nesta separação ativa
    sep = (
        AssaiSeparacao.query
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.loja_id == loja_id,
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
        ).first()
    )

    qtd_separada_por_modelo: Dict[int, int] = {}
    if sep:
        sums = (
            db.session.query(
                AssaiSeparacaoItem.modelo_id, func.count(AssaiSeparacaoItem.id)
            )
            .filter(AssaiSeparacaoItem.separacao_id == sep.id)
            .group_by(AssaiSeparacaoItem.modelo_id).all()
        )
        qtd_separada_por_modelo = {mid: int(n) for mid, n in sums}

    result = []
    for r in rows:
        sep_qtd = qtd_separada_por_modelo.get(r.modelo_id, 0)
        result.append({
            'modelo_id': r.modelo_id,
            'codigo': r.codigo,
            'nome': r.nome,
            'qtd_pedida': r.qtd_pedida,
            'qtd_separada': sep_qtd,
            'qtd_pendente': max(0, r.qtd_pedida - sep_qtd),
            'valor_unitario': r.valor_unitario,
        })
    return result


def registrar_chassi(
    pedido_id: int, loja_id: int, chassi: str, registrada_por_id: int,
) -> Dict[str, Any]:
    """Vincula chassi à separação. Validações:

    1. Status da moto = DISPONIVEL
    2. Modelo da moto bate com algum saldo > 0 do pedido para essa loja
    3. UNIQUE chassi via UNIQUE parcial — race retorna 409
    """
    chassi_norm = chassi.strip().upper()

    moto = AssaiMoto.query.filter_by(chassi=chassi_norm).with_for_update(of=AssaiMoto).first()
    if not moto:
        raise SeparacaoValidationError(f'Chassi {chassi_norm} não cadastrado')

    status = status_efetivo(chassi_norm)
    if status != EVENTO_DISPONIVEL:
        raise SeparacaoValidationError(
            f'Chassi {chassi_norm} está em {status}, esperado DISPONIVEL'
        )

    # Saldo: encontrar item do pedido com modelo bate
    saldos = saldo_pendente_por_modelo(pedido_id, loja_id)
    saldo_modelo = next(
        (s for s in saldos if s['modelo_id'] == moto.modelo_id and s['qtd_pendente'] > 0),
        None,
    )
    if not saldo_modelo:
        raise SeparacaoValidationError(
            f'Modelo {moto.modelo.codigo} sem saldo pendente para esta loja '
            '(ou modelo não pertence ao pedido)'
        )

    sep = get_ou_criar_separacao(pedido_id, loja_id, registrada_por_id)

    try:
        item = AssaiSeparacaoItem(
            separacao_id=sep.id,
            chassi=chassi_norm,
            modelo_id=moto.modelo_id,
            valor_unitario_qpa=Decimal(str(saldo_modelo['valor_unitario'])),
            registrada_por_id=registrada_por_id,
        )
        db.session.add(item)
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        raise SeparacaoConflictError(
            f'Chassi {chassi_norm} já em outra separação ativa'
        )

    emitir_evento(
        chassi_norm, EVENTO_SEPARADA,
        operador_id=registrada_por_id,
        dados_extras={
            'separacao_id': sep.id, 'pedido_id': pedido_id, 'loja_id': loja_id,
        },
    )

    # Pedido -> SEPARANDO
    pedido = AssaiPedidoVenda.query.get(pedido_id)
    if pedido and pedido.status == PEDIDO_STATUS_EM_PRODUCAO:
        pedido.status = PEDIDO_STATUS_SEPARANDO

    db.session.commit()
    return {
        'separacao_id': sep.id,
        'item_id': item.id,
        'chassi': chassi_norm,
        'modelo_codigo': moto.modelo.codigo,
        'cor': moto.cor,
    }


def desfazer_chassi(separacao_item_id: int, operador_id: int) -> Dict[str, Any]:
    """Remove chassi da separação ativa. Emite DISPONIVEL para o chassi voltar."""
    item = AssaiSeparacaoItem.query.get_or_404(separacao_item_id)
    sep = AssaiSeparacao.query.get(item.separacao_id)
    if sep and sep.status != SEPARACAO_STATUS_EM_SEPARACAO:
        raise SeparacaoValidationError(
            f'Separação {sep.id} está {sep.status}, não permite desfazer'
        )

    chassi = item.chassi
    db.session.delete(item)
    emitir_evento(
        chassi, EVENTO_DISPONIVEL,
        operador_id=operador_id,
        observacao='desfeito da separação',
        dados_extras={'separacao_id': sep.id if sep else None},
    )
    db.session.commit()
    return {'chassi': chassi}


def finalizar_separacao(separacao_id: int, operador_id: int) -> AssaiSeparacao:
    sep = AssaiSeparacao.query.get_or_404(separacao_id)
    if sep.status != SEPARACAO_STATUS_EM_SEPARACAO:
        raise SeparacaoValidationError(f'Status atual: {sep.status}')

    from app.utils.timezone import agora_brasil_naive
    sep.status = SEPARACAO_STATUS_FECHADA
    sep.fechada_em = agora_brasil_naive()
    sep.fechada_por_id = operador_id

    # Espelhar para `separacao` Nacom — aparece em lista_pedidos.html via
    # VIEW pedidos Parte 1, permite Cotacao + Embarque + Frete (origem=OP_ASSAI).
    # Idempotente: skip se ja espelhada.
    #
    # CRITICAL (code review 2026-05-11):
    # - MirrorRaceError: outra transacao venceu — espelho ja existe.
    #   Tratamos como sucesso (idempotencia) e re-aplicamos o status FECHADA
    #   em transacao nova.
    # - Demais excecoes: rollback + re-raise como SeparacaoValidationError
    #   para o operador. Sem isso, FECHADA persistiria sem espelho e a
    #   separacao sumiria de lista_pedidos.html.
    try:
        from app.motos_assai.services.separacao_mirror_service import (
            mirror_assai_to_separacao, MirrorRaceError,
        )
        mirror_assai_to_separacao(sep.id)
    except MirrorRaceError:
        # Espelho ja criado por concorrencia — re-buscar a separacao
        # (sessao foi rollbackada) e re-aplicar status FECHADA.
        import logging
        logging.getLogger(__name__).info(
            'finalizar_separacao: race detectada para AssaiSeparacao %s — '
            'espelho ja existe, re-aplicando FECHADA', sep.id,
        )
        sep = AssaiSeparacao.query.get_or_404(separacao_id)
        if sep.status == SEPARACAO_STATUS_EM_SEPARACAO:
            sep.status = SEPARACAO_STATUS_FECHADA
            sep.fechada_em = agora_brasil_naive()
            sep.fechada_por_id = operador_id
        # else: outra transacao ja persistiu — idempotencia OK
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(
            'mirror_assai_to_separacao FALHOU para AssaiSeparacao %s: %s '
            '— transacao revertida',
            sep.id, e, exc_info=True,
        )
        raise SeparacaoValidationError(
            f'Falha ao espelhar separacao em Nacom: {e}. '
            'Status nao foi alterado — tente novamente. Se persistir, '
            'verifique cadastro de peso dos modelos.'
        )

    db.session.commit()
    return sep


def cancelar_separacao(separacao_id: int, motivo: str, operador_id: int) -> AssaiSeparacao:
    """Cancela. Para cada item: emite DISPONIVEL para devolver chassi ao estoque.

    Regras:
    - FATURADA: não pode cancelar (NF já emitida)
    - CANCELADA: já cancelada, idempotente erro
    - FECHADA ou EM_SEPARACAO: pode cancelar
    """
    if not motivo or len(motivo.strip()) < 3:
        raise SeparacaoValidationError('Motivo obrigatório (≥3 chars)')

    sep = AssaiSeparacao.query.get_or_404(separacao_id)
    if sep.status in (SEPARACAO_STATUS_CANCELADA, SEPARACAO_STATUS_FATURADA):
        raise SeparacaoValidationError(
            f'Não é possível cancelar separação com status {sep.status}'
        )

    items = AssaiSeparacaoItem.query.filter_by(separacao_id=sep.id).all()
    for it in items:
        # H6: skip chassis já faturados — não reverter para DISPONIVEL
        if status_efetivo(it.chassi) == EVENTO_FATURADA:
            continue
        emitir_evento(
            it.chassi, EVENTO_DISPONIVEL,
            operador_id=operador_id,
            observacao='separacao_cancelada',
            dados_extras={'separacao_id': sep.id, 'motivo': motivo.strip()},
        )

    sep.status = SEPARACAO_STATUS_CANCELADA
    sep.motivo_cancelamento = motivo.strip()

    # Remover espelho em separacao Nacom (se existir). Se ja tem NF no
    # espelho (raro — separacao FATURADA ja foi bloqueada acima), o
    # service nega e cancelar_separacao falha — operador deve cancelar
    # a NF primeiro.
    try:
        from app.motos_assai.services.separacao_mirror_service import (
            unmirror_assai_separacao,
        )
        unmirror_assai_separacao(sep.id)
    except ValueError as e:
        # Bloqueio explicito (NF preenchida no espelho) — propaga como
        # erro de validacao para o operador
        raise SeparacaoValidationError(str(e))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(
            'Falha ao remover espelho de AssaiSeparacao %s: %s',
            sep.id, e, exc_info=True,
        )
        # Nao bloqueia o cancelamento — limpeza manual via SQL se necessario

    db.session.commit()
    return sep


def listar_pares_separaveis() -> List[Dict[str, Any]]:
    """Lista pares (pedido, loja) com saldo pendente de chassis a separar.

    Retorna: [{pedido_id, pedido_numero, pedido_status,
               loja_id, loja_numero, loja_nome, loja_cidade, loja_uf,
               qtd_pedida_total, qtd_separada_total, qtd_pendente_total,
               separacao_ativa_id, separacao_ativa_status,
               modelos: [{codigo, nome, qtd_pedida, qtd_separada, qtd_pendente}]}]

    Considera apenas pedidos NAO FATURADOS / NAO CANCELADOS.
    Mostra pares que tem AO MENOS 1 modelo com qtd_pendente > 0,
    ou que ja tem separacao ATIVA (EM_SEPARACAO ou FECHADA mas nao FATURADA).
    """
    from app.motos_assai.models import AssaiLoja
    pedidos = (
        AssaiPedidoVenda.query
        .filter(AssaiPedidoVenda.status.notin_([
            'FATURADO', 'CANCELADO',
        ]))
        .order_by(AssaiPedidoVenda.criado_em.desc())
        .all()
    )
    if not pedidos:
        return []
    pedido_ids = [p.id for p in pedidos]

    itens = (
        db.session.query(
            AssaiPedidoVendaItem.pedido_id,
            AssaiPedidoVendaItem.loja_id,
            AssaiPedidoVendaItem.modelo_id,
            AssaiPedidoVendaItem.qtd_pedida,
            AssaiModelo.codigo,
            AssaiModelo.nome,
        )
        .join(AssaiModelo, AssaiModelo.id == AssaiPedidoVendaItem.modelo_id)
        .filter(AssaiPedidoVendaItem.pedido_id.in_(pedido_ids))
        .order_by(AssaiModelo.codigo)
        .all()
    )

    # Qtd ja em separacao (qualquer status != CANCELADA - CANCELADA devolve chassi)
    sep_items = (
        db.session.query(
            AssaiSeparacao.pedido_id,
            AssaiSeparacao.loja_id,
            AssaiSeparacaoItem.modelo_id,
            func.count(AssaiSeparacaoItem.id).label('qtd'),
        )
        .join(AssaiSeparacaoItem, AssaiSeparacaoItem.separacao_id == AssaiSeparacao.id)
        .filter(
            AssaiSeparacao.pedido_id.in_(pedido_ids),
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
        )
        .group_by(AssaiSeparacao.pedido_id, AssaiSeparacao.loja_id, AssaiSeparacaoItem.modelo_id)
        .all()
    )
    sep_map = {(r.pedido_id, r.loja_id, r.modelo_id): int(r.qtd) for r in sep_items}

    sep_ativas = (
        AssaiSeparacao.query
        .filter(
            AssaiSeparacao.pedido_id.in_(pedido_ids),
            AssaiSeparacao.status.in_([
                SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
            ]),
        )
        .all()
    )
    ativa_map = {(s.pedido_id, s.loja_id): s for s in sep_ativas}

    lojas = AssaiLoja.query.all()
    loja_por_id = {l.id: l for l in lojas}
    pedido_por_id = {p.id: p for p in pedidos}

    pares: Dict[tuple, Dict[str, Any]] = {}
    for it in itens:
        key = (it.pedido_id, it.loja_id)
        qtd_pedida = int(it.qtd_pedida)
        qtd_sep = sep_map.get((it.pedido_id, it.loja_id, it.modelo_id), 0)
        qtd_pend = max(0, qtd_pedida - qtd_sep)
        bucket = pares.setdefault(key, {
            'pedido_id': it.pedido_id,
            'loja_id': it.loja_id,
            'qtd_pedida_total': 0,
            'qtd_separada_total': 0,
            'qtd_pendente_total': 0,
            'modelos': [],
        })
        bucket['qtd_pedida_total'] += qtd_pedida
        bucket['qtd_separada_total'] += qtd_sep
        bucket['qtd_pendente_total'] += qtd_pend
        bucket['modelos'].append({
            'codigo': it.codigo,
            'nome': it.nome,
            'qtd_pedida': qtd_pedida,
            'qtd_separada': qtd_sep,
            'qtd_pendente': qtd_pend,
        })

    result = []
    for (pid, lid), bucket in pares.items():
        sep_ativa = ativa_map.get((pid, lid))
        if bucket['qtd_pendente_total'] <= 0 and not sep_ativa:
            continue
        pedido = pedido_por_id.get(pid)
        loja = loja_por_id.get(lid)
        result.append({
            **bucket,
            'pedido_numero': pedido.numero if pedido else '-',
            'pedido_status': pedido.status if pedido else '-',
            'loja_numero': loja.numero if loja else '-',
            'loja_nome': loja.nome if loja else '-',
            'loja_cidade': (loja.cidade if loja else None) or '-',
            'loja_uf': (loja.uf if loja else None) or '-',
            'separacao_ativa_id': sep_ativa.id if sep_ativa else None,
            'separacao_ativa_status': sep_ativa.status if sep_ativa else None,
        })

    result.sort(key=lambda r: (
        0 if r['separacao_ativa_id'] else 1,
        r['pedido_numero'],
        r['loja_numero'],
    ))
    return result

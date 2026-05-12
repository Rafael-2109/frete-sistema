"""Resumo por modelo x status efetivo.

Status efetivo = tipo do ultimo evento (ocorrido_em DESC, id DESC) por chassi.

Funcoes:
- resumo_por_modelo() -> lista agregada por modelo, com counts por status e qtd em pedidos
- detalhe_estoque(modelo_id) -> chassis em ESTOQUE com cor + data_recebimento
- detalhe_pendente(modelo_id) -> chassis em PENDENTE com observacao do evento
- detalhe_montada(modelo_id) -> chassis em MONTADA efetivo (inclui PENDENCIA_RESOLVIDA->MONTADA)
                                com operador + data/hora do ultimo MONTADA
- detalhe_disponivel(modelo_id) -> chassis em DISPONIVEL com montagem + disponibilidade
- detalhe_em_pedido(modelo_id) -> lojas com qtd pendente por loja (pedido nao faturado)

Status considerados "MONTADA efetivo": ultimo evento = MONTADA OU
REVERTIDA_PARA_MONTADA (semanticamente moto montada de novo).
"""

from __future__ import annotations

from typing import List, Dict, Any

from sqlalchemy import func

from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiMotoEvento, AssaiModelo, AssaiLoja,
    AssaiPedidoVenda, AssaiPedidoVendaItem,
    AssaiSeparacao, AssaiSeparacaoItem,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE,
    EVENTO_DISPONIVEL, EVENTO_REVERTIDA_PARA_MONTADA,
    PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
    SEPARACAO_STATUS_CANCELADA,
)


# Status MONTADA "efetivo" - aceita ambos
STATUS_MONTADA_EFETIVO = (EVENTO_MONTADA, EVENTO_REVERTIDA_PARA_MONTADA)


def _ultimo_evento_subquery():
    """Subquery: (chassi, ultimo_id) - ultimo evento por chassi por id DESC."""
    return (
        db.session.query(
            AssaiMotoEvento.chassi.label('chassi'),
            func.max(AssaiMotoEvento.id).label('ultimo_id'),
        )
        .group_by(AssaiMotoEvento.chassi)
        .subquery()
    )


def resumo_por_modelo() -> List[Dict[str, Any]]:
    """Retorna lista [{modelo_id, codigo, nome, estoque, pendente, montada,
    disponivel, em_pedido}].

    em_pedido = somatorio de qtd_pedida nos pedidos NAO faturados/cancelados
                menos chassis ja FATURADOS desse modelo desses pedidos.
    """
    sub = _ultimo_evento_subquery()

    # Agrupa por (modelo, status) usando ultimo evento
    rows = (
        db.session.query(
            AssaiModelo.id.label('modelo_id'),
            AssaiModelo.codigo.label('codigo'),
            AssaiModelo.nome.label('nome'),
            AssaiMotoEvento.tipo.label('tipo'),
            func.count(AssaiMoto.id).label('qtd'),
        )
        .select_from(AssaiModelo)
        .join(AssaiMoto, AssaiMoto.modelo_id == AssaiModelo.id)
        .join(sub, sub.c.chassi == AssaiMoto.chassi)
        .join(AssaiMotoEvento, AssaiMotoEvento.id == sub.c.ultimo_id)
        .filter(AssaiModelo.ativo.is_(True))
        .group_by(AssaiModelo.id, AssaiModelo.codigo, AssaiModelo.nome, AssaiMotoEvento.tipo)
        .all()
    )

    # Indexa por modelo
    por_modelo: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        bucket = por_modelo.setdefault(r.modelo_id, {
            'modelo_id': r.modelo_id,
            'codigo': r.codigo,
            'nome': r.nome,
            'estoque': 0,
            'pendente': 0,
            'montada': 0,
            'disponivel': 0,
            'em_pedido': 0,
        })
        if r.tipo == EVENTO_ESTOQUE:
            bucket['estoque'] = int(r.qtd)
        elif r.tipo == EVENTO_PENDENTE:
            bucket['pendente'] = int(r.qtd)
        elif r.tipo in STATUS_MONTADA_EFETIVO:
            bucket['montada'] += int(r.qtd)
        elif r.tipo == EVENTO_DISPONIVEL:
            bucket['disponivel'] = int(r.qtd)

    # Garante modelos sem nenhum chassi (ativos)
    for m in AssaiModelo.query.filter_by(ativo=True).all():
        por_modelo.setdefault(m.id, {
            'modelo_id': m.id, 'codigo': m.codigo, 'nome': m.nome,
            'estoque': 0, 'pendente': 0, 'montada': 0, 'disponivel': 0,
            'em_pedido': 0,
        })

    # Qtd em pedidos NAO faturados / NAO cancelados
    # Para cada (pedido, loja, modelo) com qtd_pedida: qtd_pendente = qtd_pedida - qtd_faturada
    # qtd_faturada = chassis em separacao_item da separacao FATURADA do pedido x loja x modelo
    em_pedido_rows = (
        db.session.query(
            AssaiPedidoVendaItem.modelo_id.label('modelo_id'),
            func.sum(AssaiPedidoVendaItem.qtd_pedida).label('qtd_pedida_total'),
        )
        .join(AssaiPedidoVenda, AssaiPedidoVenda.id == AssaiPedidoVendaItem.pedido_id)
        .filter(AssaiPedidoVenda.status.notin_([
            PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
        ]))
        .group_by(AssaiPedidoVendaItem.modelo_id)
        .all()
    )
    qtd_pedida_por_modelo = {r.modelo_id: int(r.qtd_pedida_total or 0) for r in em_pedido_rows}

    # Qtd ja consumida pelo pedido = chassis em separacao NAO CANCELADA
    # (EM_SEPARACAO + FECHADA + FATURADA). Apenas CANCELADA devolve chassis para
    # o pool. Antes contava so FATURADA, o que double-countava chassis em FECHADA.
    qtd_consumida_rows = (
        db.session.query(
            AssaiSeparacaoItem.modelo_id.label('modelo_id'),
            func.count(AssaiSeparacaoItem.id).label('qtd'),
        )
        .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
        .join(AssaiPedidoVenda, AssaiPedidoVenda.id == AssaiSeparacao.pedido_id)
        .filter(
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
            AssaiPedidoVenda.status.notin_([
                PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
            ]),
        )
        .group_by(AssaiSeparacaoItem.modelo_id)
        .all()
    )
    qtd_consumida_por_modelo = {r.modelo_id: int(r.qtd or 0) for r in qtd_consumida_rows}

    for mid, bucket in por_modelo.items():
        pedida = qtd_pedida_por_modelo.get(mid, 0)
        consumida = qtd_consumida_por_modelo.get(mid, 0)
        bucket['em_pedido'] = max(0, pedida - consumida)

    return sorted(por_modelo.values(), key=lambda b: b['codigo'])


def _chassis_modelo_status(modelo_id: int, status_tipos) -> List[str]:
    """Lista chassis cujo modelo=modelo_id e ultimo evento.tipo IN status_tipos."""
    if isinstance(status_tipos, str):
        status_tipos = (status_tipos,)
    sub = _ultimo_evento_subquery()
    rows = (
        db.session.query(AssaiMoto.chassi)
        .join(sub, sub.c.chassi == AssaiMoto.chassi)
        .join(AssaiMotoEvento, AssaiMotoEvento.id == sub.c.ultimo_id)
        .filter(
            AssaiMoto.modelo_id == modelo_id,
            AssaiMotoEvento.tipo.in_(list(status_tipos)),
        )
        .all()
    )
    return [r.chassi for r in rows]


def detalhe_estoque(modelo_id: int) -> List[Dict[str, Any]]:
    """Chassis com status atual = ESTOQUE.

    Retorna: [{chassi, cor, data_recebimento}]
    data_recebimento = ocorrido_em do evento ESTOQUE (criado no recebimento).
    """
    chassis = _chassis_modelo_status(modelo_id, EVENTO_ESTOQUE)
    if not chassis:
        return []

    # Para cada chassi, pega ultimo evento ESTOQUE (deve ser o unico ativo)
    eventos = (
        db.session.query(
            AssaiMotoEvento.chassi, AssaiMotoEvento.ocorrido_em,
        )
        .filter(
            AssaiMotoEvento.chassi.in_(chassis),
            AssaiMotoEvento.tipo == EVENTO_ESTOQUE,
        )
        .order_by(AssaiMotoEvento.chassi, AssaiMotoEvento.ocorrido_em.desc())
        .all()
    )
    data_por_chassi: Dict[str, Any] = {}
    for ev in eventos:
        if ev.chassi not in data_por_chassi:
            data_por_chassi[ev.chassi] = ev.ocorrido_em

    motos = AssaiMoto.query.filter(AssaiMoto.chassi.in_(chassis)).all()
    result = []
    for m in motos:
        dt = data_por_chassi.get(m.chassi)
        result.append({
            'chassi': m.chassi,
            'cor': m.cor or '-',
            'data_recebimento': dt.strftime('%d/%m/%Y %H:%M') if dt else '-',
        })
    return sorted(result, key=lambda r: r['chassi'])


def detalhe_pendente(modelo_id: int) -> List[Dict[str, Any]]:
    """Chassis com status atual = PENDENTE.

    Retorna: [{chassi, cor, observacao, data_pendencia, operador}]
    observacao = AssaiMotoEvento.observacao OR dados_extras['descricao']
    """
    chassis = _chassis_modelo_status(modelo_id, EVENTO_PENDENTE)
    if not chassis:
        return []

    # Para cada chassi, o ultimo evento PENDENTE
    eventos = (
        AssaiMotoEvento.query
        .filter(
            AssaiMotoEvento.chassi.in_(chassis),
            AssaiMotoEvento.tipo == EVENTO_PENDENTE,
        )
        .order_by(AssaiMotoEvento.chassi, AssaiMotoEvento.id.desc())
        .all()
    )
    info_por_chassi: Dict[str, AssaiMotoEvento] = {}
    for ev in eventos:
        if ev.chassi not in info_por_chassi:
            info_por_chassi[ev.chassi] = ev

    motos = AssaiMoto.query.filter(AssaiMoto.chassi.in_(chassis)).all()
    result = []
    for m in motos:
        ev = info_por_chassi.get(m.chassi)
        obs = None
        if ev:
            obs = ev.observacao
            if not obs and isinstance(ev.dados_extras, dict):
                obs = ev.dados_extras.get('descricao')
        result.append({
            'chassi': m.chassi,
            'cor': m.cor or '-',
            'observacao': obs or '(sem observacao)',
            'data_pendencia': ev.ocorrido_em.strftime('%d/%m/%Y %H:%M') if ev and ev.ocorrido_em else '-',
            'operador': ev.operador.nome if ev and ev.operador else '-',
        })
    return sorted(result, key=lambda r: r['chassi'])


def detalhe_montada(modelo_id: int) -> List[Dict[str, Any]]:
    """Chassis MONTADA efetivo (MONTADA ou REVERTIDA_PARA_MONTADA).

    Retorna: [{chassi, cor, operador, data_hora}] - dados do evento que
    deixou o chassi neste estado.

    Fallback: prefere ultimo MONTADA; se nao existir (sequencia
    .. -> MONTADA -> DISPONIVEL -> REVERTIDA_PARA_MONTADA tem MONTADA antigo,
    mas REVERTIDA mais recente), usa o ultimo evento entre MONTADA OU
    REVERTIDA_PARA_MONTADA.
    """
    chassis = _chassis_modelo_status(modelo_id, STATUS_MONTADA_EFETIVO)
    if not chassis:
        return []

    # Bulk fetch: TODOS os eventos MONTADA + REVERTIDA_PARA_MONTADA dos chassis,
    # ordenados por id DESC. Tomamos o mais recente por chassi (que e o que
    # explica o estado atual).
    eventos = (
        AssaiMotoEvento.query
        .filter(
            AssaiMotoEvento.chassi.in_(chassis),
            AssaiMotoEvento.tipo.in_(list(STATUS_MONTADA_EFETIVO)),
        )
        .order_by(AssaiMotoEvento.chassi, AssaiMotoEvento.id.desc())
        .all()
    )
    info_por_chassi: Dict[str, AssaiMotoEvento] = {}
    for ev in eventos:
        if ev.chassi not in info_por_chassi:
            info_por_chassi[ev.chassi] = ev

    motos = AssaiMoto.query.filter(AssaiMoto.chassi.in_(chassis)).all()
    result = []
    for m in motos:
        ev = info_por_chassi.get(m.chassi)
        # Label do tipo para o operador entender se foi MONTADA ou REVERTIDA
        tipo_label = ev.tipo if ev else '-'
        result.append({
            'chassi': m.chassi,
            'cor': m.cor or '-',
            'operador': ev.operador.nome if ev and ev.operador else '-',
            'data_hora': ev.ocorrido_em.strftime('%d/%m/%Y %H:%M') if ev and ev.ocorrido_em else '-',
            'tipo': tipo_label,
        })
    return sorted(result, key=lambda r: r['chassi'])


def detalhe_disponivel(modelo_id: int) -> List[Dict[str, Any]]:
    """Chassis DISPONIVEL.

    Retorna: [{chassi, cor, montagem_operador, montagem_data,
               disp_operador, disp_data}]
    """
    chassis = _chassis_modelo_status(modelo_id, EVENTO_DISPONIVEL)
    if not chassis:
        return []

    # ultimo MONTADA por chassi
    montadas = (
        AssaiMotoEvento.query
        .filter(
            AssaiMotoEvento.chassi.in_(chassis),
            AssaiMotoEvento.tipo == EVENTO_MONTADA,
        )
        .order_by(AssaiMotoEvento.chassi, AssaiMotoEvento.id.desc())
        .all()
    )
    montagem_por_chassi: Dict[str, AssaiMotoEvento] = {}
    for ev in montadas:
        if ev.chassi not in montagem_por_chassi:
            montagem_por_chassi[ev.chassi] = ev

    # ultimo DISPONIVEL por chassi
    disps = (
        AssaiMotoEvento.query
        .filter(
            AssaiMotoEvento.chassi.in_(chassis),
            AssaiMotoEvento.tipo == EVENTO_DISPONIVEL,
        )
        .order_by(AssaiMotoEvento.chassi, AssaiMotoEvento.id.desc())
        .all()
    )
    disp_por_chassi: Dict[str, AssaiMotoEvento] = {}
    for ev in disps:
        if ev.chassi not in disp_por_chassi:
            disp_por_chassi[ev.chassi] = ev

    motos = AssaiMoto.query.filter(AssaiMoto.chassi.in_(chassis)).all()
    result = []
    for m in motos:
        m_ev = montagem_por_chassi.get(m.chassi)
        d_ev = disp_por_chassi.get(m.chassi)
        result.append({
            'chassi': m.chassi,
            'cor': m.cor or '-',
            'montagem_operador': m_ev.operador.nome if m_ev and m_ev.operador else '-',
            'montagem_data': m_ev.ocorrido_em.strftime('%d/%m/%Y %H:%M') if m_ev and m_ev.ocorrido_em else '-',
            'disp_operador': d_ev.operador.nome if d_ev and d_ev.operador else '-',
            'disp_data': d_ev.ocorrido_em.strftime('%d/%m/%Y %H:%M') if d_ev and d_ev.ocorrido_em else '-',
        })
    return sorted(result, key=lambda r: r['chassi'])


def detalhe_em_pedido(modelo_id: int) -> List[Dict[str, Any]]:
    """Lojas com saldo PENDENTE de faturamento para o modelo.

    Retorna: [{loja_id, loja_numero, loja_nome, pedido_numero,
               qtd_pedida, qtd_faturada, qtd_pendente}]

    Considera apenas pedidos NAO FATURADOS e NAO CANCELADOS.
    qtd_faturada = chassis em separacao FATURADA do (pedido, loja, modelo).
    """
    rows = (
        db.session.query(
            AssaiPedidoVendaItem.id.label('item_id'),
            AssaiPedidoVendaItem.qtd_pedida.label('qtd_pedida'),
            AssaiPedidoVendaItem.loja_id.label('loja_id'),
            AssaiPedidoVendaItem.pedido_id.label('pedido_id'),
            AssaiLoja.numero.label('loja_numero'),
            AssaiLoja.nome.label('loja_nome'),
            AssaiLoja.cidade.label('loja_cidade'),
            AssaiLoja.uf.label('loja_uf'),
            AssaiPedidoVenda.numero.label('pedido_numero'),
            AssaiPedidoVenda.status.label('pedido_status'),
        )
        .join(AssaiPedidoVenda, AssaiPedidoVenda.id == AssaiPedidoVendaItem.pedido_id)
        .join(AssaiLoja, AssaiLoja.id == AssaiPedidoVendaItem.loja_id)
        .filter(
            AssaiPedidoVendaItem.modelo_id == modelo_id,
            AssaiPedidoVenda.status.notin_([
                PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
            ]),
        )
        .order_by(AssaiPedidoVenda.numero, AssaiLoja.numero)
        .all()
    )
    if not rows:
        return []

    # qtd ja consumida por separacao NAO cancelada (EM_SEPARACAO + FECHADA + FATURADA)
    # Inclui FECHADA para nao double-contar chassis ja separados aguardando NF.
    consumida_rows = (
        db.session.query(
            AssaiSeparacao.pedido_id.label('pedido_id'),
            AssaiSeparacao.loja_id.label('loja_id'),
            func.count(AssaiSeparacaoItem.id).label('qtd'),
        )
        .join(AssaiSeparacaoItem, AssaiSeparacaoItem.separacao_id == AssaiSeparacao.id)
        .filter(
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
            AssaiSeparacaoItem.modelo_id == modelo_id,
        )
        .group_by(AssaiSeparacao.pedido_id, AssaiSeparacao.loja_id)
        .all()
    )
    consumida_map = {(r.pedido_id, r.loja_id): int(r.qtd) for r in consumida_rows}

    result = []
    for r in rows:
        consumida = consumida_map.get((r.pedido_id, r.loja_id), 0)
        pend = max(0, int(r.qtd_pedida) - consumida)
        if pend <= 0:
            continue
        result.append({
            'loja_id': r.loja_id,
            'loja_numero': r.loja_numero,
            'loja_nome': r.loja_nome,
            'loja_cidade': r.loja_cidade or '-',
            'loja_uf': r.loja_uf or '-',
            'pedido_numero': r.pedido_numero,
            'pedido_status': r.pedido_status,
            'qtd_pedida': int(r.qtd_pedida),
            'qtd_faturada': consumida,
            'qtd_pendente': pend,
        })
    return result

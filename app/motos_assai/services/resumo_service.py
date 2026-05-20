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
from sqlalchemy.orm import joinedload

from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiMotoEvento, AssaiModelo, AssaiLoja,
    AssaiPedidoVenda, AssaiPedidoVendaItem,
    AssaiSeparacao, AssaiSeparacaoItem,
    AssaiCarregamento, AssaiCarregamentoItem,
    AssaiNfQpa, AssaiNfQpaItem,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE,
    EVENTO_DISPONIVEL, EVENTO_REVERTIDA_PARA_MONTADA,
    EVENTO_SEPARADA, EVENTO_CARREGADA, EVENTO_FATURADA,
    PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
    SEPARACAO_STATUS_CANCELADA,
    CARREGAMENTO_STATUS_CANCELADO,
    NF_STATUS_CANCELADA,
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
            'separada': 0,
            'carregada': 0,
            'faturada': 0,
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
        elif r.tipo == EVENTO_SEPARADA:
            bucket['separada'] = int(r.qtd)
        elif r.tipo == EVENTO_CARREGADA:
            bucket['carregada'] = int(r.qtd)
        elif r.tipo == EVENTO_FATURADA:
            bucket['faturada'] = int(r.qtd)

    # Garante modelos sem nenhum chassi (ativos)
    for m in AssaiModelo.query.filter_by(ativo=True).all():
        por_modelo.setdefault(m.id, {
            'modelo_id': m.id, 'codigo': m.codigo, 'nome': m.nome,
            'estoque': 0, 'pendente': 0, 'montada': 0, 'disponivel': 0,
            'separada': 0, 'carregada': 0, 'faturada': 0,
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


def detalhe_separada(modelo_id: int) -> List[Dict[str, Any]]:
    """Chassis com status atual = SEPARADA.

    Retorna: [{chassi, cor, sep_id, pedido_numero, loja_numero, loja_nome,
               data_hora, operador}]
    Enriquecido com a separacao NAO-cancelada que contem o chassi (pedido/loja).
    """
    chassis = _chassis_modelo_status(modelo_id, EVENTO_SEPARADA)
    if not chassis:
        return []

    # Ultimo evento SEPARADA por chassi (data + operador)
    eventos = (
        AssaiMotoEvento.query
        .options(joinedload(AssaiMotoEvento.operador))
        .filter(
            AssaiMotoEvento.chassi.in_(chassis),
            AssaiMotoEvento.tipo == EVENTO_SEPARADA,
        )
        .order_by(AssaiMotoEvento.chassi, AssaiMotoEvento.id.desc())
        .all()
    )
    ev_por_chassi: Dict[str, AssaiMotoEvento] = {}
    for ev in eventos:
        ev_por_chassi.setdefault(ev.chassi, ev)

    # Separacao nao-cancelada que contem o chassi -> pedido/loja
    sep_rows = (
        db.session.query(
            AssaiSeparacaoItem.chassi.label('chassi'),
            AssaiSeparacao.id.label('sep_id'),
            AssaiPedidoVenda.numero.label('pedido_numero'),
            AssaiLoja.numero.label('loja_numero'),
            AssaiLoja.nome.label('loja_nome'),
        )
        .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
        .join(AssaiPedidoVenda, AssaiPedidoVenda.id == AssaiSeparacao.pedido_id)
        .join(AssaiLoja, AssaiLoja.id == AssaiSeparacao.loja_id)
        .filter(
            AssaiSeparacaoItem.chassi.in_(chassis),
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
        )
        .all()
    )
    sep_por_chassi: Dict[str, Any] = {}
    for r in sep_rows:
        sep_por_chassi.setdefault(r.chassi, r)

    motos = AssaiMoto.query.filter(AssaiMoto.chassi.in_(chassis)).all()
    result = []
    for m in motos:
        ev = ev_por_chassi.get(m.chassi)
        sp = sep_por_chassi.get(m.chassi)
        result.append({
            'chassi': m.chassi,
            'cor': m.cor or '-',
            'sep_id': sp.sep_id if sp else None,
            'pedido_numero': sp.pedido_numero if sp else '-',
            'loja_numero': sp.loja_numero if sp else '-',
            'loja_nome': sp.loja_nome if sp else '-',
            'data_hora': ev.ocorrido_em.strftime('%d/%m/%Y %H:%M') if ev and ev.ocorrido_em else '-',
            'operador': ev.operador.nome if ev and ev.operador else '-',
        })
    return sorted(result, key=lambda r: r['chassi'])


def detalhe_carregada(modelo_id: int) -> List[Dict[str, Any]]:
    """Chassis com status atual = CARREGADA.

    Retorna: [{chassi, cor, carregamento_id, pedido_numero, loja_numero,
               loja_nome, data_hora, operador}]
    Enriquecido com o carregamento NAO-cancelado que contem o chassi.
    """
    chassis = _chassis_modelo_status(modelo_id, EVENTO_CARREGADA)
    if not chassis:
        return []

    eventos = (
        AssaiMotoEvento.query
        .options(joinedload(AssaiMotoEvento.operador))
        .filter(
            AssaiMotoEvento.chassi.in_(chassis),
            AssaiMotoEvento.tipo == EVENTO_CARREGADA,
        )
        .order_by(AssaiMotoEvento.chassi, AssaiMotoEvento.id.desc())
        .all()
    )
    ev_por_chassi: Dict[str, AssaiMotoEvento] = {}
    for ev in eventos:
        ev_por_chassi.setdefault(ev.chassi, ev)

    car_rows = (
        db.session.query(
            AssaiCarregamentoItem.chassi.label('chassi'),
            AssaiCarregamento.id.label('carregamento_id'),
            AssaiPedidoVenda.numero.label('pedido_numero'),
            AssaiLoja.numero.label('loja_numero'),
            AssaiLoja.nome.label('loja_nome'),
        )
        .join(AssaiCarregamento, AssaiCarregamento.id == AssaiCarregamentoItem.carregamento_id)
        .join(AssaiPedidoVenda, AssaiPedidoVenda.id == AssaiCarregamento.pedido_id)
        .join(AssaiLoja, AssaiLoja.id == AssaiCarregamento.loja_id)
        .filter(
            AssaiCarregamentoItem.chassi.in_(chassis),
            AssaiCarregamento.status != CARREGAMENTO_STATUS_CANCELADO,
        )
        .all()
    )
    car_por_chassi: Dict[str, Any] = {}
    for r in car_rows:
        car_por_chassi.setdefault(r.chassi, r)

    motos = AssaiMoto.query.filter(AssaiMoto.chassi.in_(chassis)).all()
    result = []
    for m in motos:
        ev = ev_por_chassi.get(m.chassi)
        cr = car_por_chassi.get(m.chassi)
        result.append({
            'chassi': m.chassi,
            'cor': m.cor or '-',
            'carregamento_id': cr.carregamento_id if cr else None,
            'pedido_numero': cr.pedido_numero if cr else '-',
            'loja_numero': cr.loja_numero if cr else '-',
            'loja_nome': cr.loja_nome if cr else '-',
            'data_hora': ev.ocorrido_em.strftime('%d/%m/%Y %H:%M') if ev and ev.ocorrido_em else '-',
            'operador': ev.operador.nome if ev and ev.operador else '-',
        })
    return sorted(result, key=lambda r: r['chassi'])


def detalhe_faturada(modelo_id: int) -> List[Dict[str, Any]]:
    """Chassis com status atual = FATURADA.

    Retorna: [{chassi, cor, nf_numero, loja_numero, loja_nome, data_emissao,
               data_hora, operador}]
    Enriquecido com a NF Q.P.A. NAO-cancelada que contem o chassi.
    """
    chassis = _chassis_modelo_status(modelo_id, EVENTO_FATURADA)
    if not chassis:
        return []

    eventos = (
        AssaiMotoEvento.query
        .options(joinedload(AssaiMotoEvento.operador))
        .filter(
            AssaiMotoEvento.chassi.in_(chassis),
            AssaiMotoEvento.tipo == EVENTO_FATURADA,
        )
        .order_by(AssaiMotoEvento.chassi, AssaiMotoEvento.id.desc())
        .all()
    )
    ev_por_chassi: Dict[str, AssaiMotoEvento] = {}
    for ev in eventos:
        ev_por_chassi.setdefault(ev.chassi, ev)

    nf_rows = (
        db.session.query(
            AssaiNfQpaItem.chassi.label('chassi'),
            AssaiNfQpa.numero.label('nf_numero'),
            AssaiNfQpa.data_emissao.label('data_emissao'),
            AssaiLoja.numero.label('loja_numero'),
            AssaiLoja.nome.label('loja_nome'),
        )
        .join(AssaiNfQpa, AssaiNfQpa.id == AssaiNfQpaItem.nf_id)
        .outerjoin(AssaiLoja, AssaiLoja.id == AssaiNfQpa.loja_id)
        .filter(
            AssaiNfQpaItem.chassi.in_(chassis),
            AssaiNfQpa.status_match != NF_STATUS_CANCELADA,
        )
        .all()
    )
    nf_por_chassi: Dict[str, Any] = {}
    for r in nf_rows:
        nf_por_chassi.setdefault(r.chassi, r)

    motos = AssaiMoto.query.filter(AssaiMoto.chassi.in_(chassis)).all()
    result = []
    for m in motos:
        ev = ev_por_chassi.get(m.chassi)
        nf = nf_por_chassi.get(m.chassi)
        result.append({
            'chassi': m.chassi,
            'cor': m.cor or '-',
            'nf_numero': (nf.nf_numero if nf else None) or '-',
            'loja_numero': nf.loja_numero if nf else '-',
            'loja_nome': nf.loja_nome if nf else '-',
            'data_emissao': nf.data_emissao.strftime('%d/%m/%Y') if nf and nf.data_emissao else '-',
            'data_hora': ev.ocorrido_em.strftime('%d/%m/%Y %H:%M') if ev and ev.ocorrido_em else '-',
            'operador': ev.operador.nome if ev and ev.operador else '-',
        })
    return sorted(result, key=lambda r: r['chassi'])


# =====================================================================
# Listagens agrupadas por modelo (Item 1 - exibições por tela)
# =====================================================================
# Diferentemente de detalhe_*(modelo_id), estas funcoes trazem TODAS as
# motos de TODOS os modelos cujo ultimo evento esta em `tipos`, em UMA
# unica query (evita N+1 quando o template lista varios modelos).
#
# Cada moto inclui: chassi, cor, ocorrido_em (timestamp), operador_nome, tipo.
# O caller decide se quer agrupar por modelo no template (ex.: dict.items()).


def _listar_motos_por_tipos(tipos, filtros=None) -> List[Dict[str, Any]]:
    """Lista motos cujo ULTIMO evento.tipo esta em `tipos`, com dados do
    evento (data, operador, tipo). UMA unica query — agrupa no caller.

    Args:
        tipos: tipo (str) ou iteravel de tipos de evento.
        filtros: dict opcional com 'chassi' (ilike) e 'modelo_id' (==).

    Returns:
        [{'modelo_id', 'modelo_codigo', 'modelo_nome', 'chassi', 'cor',
          'ocorrido_em' (datetime), 'operador_nome', 'tipo'}]
        Ordenado por modelo_codigo, ocorrido_em DESC.
    """
    if isinstance(tipos, str):
        tipos = (tipos,)
    tipos = list(tipos)

    sub = _ultimo_evento_subquery()

    # Importacao tardia para evitar circular (Usuario fora deste modulo).
    # Tabela 'usuarios' (Usuario) e importada onde necessario nos services
    # via app.auth.models — segue padrao do MontagemEvento etc.
    from app.auth.models import Usuario

    q = (
        db.session.query(
            AssaiMoto.modelo_id.label('modelo_id'),
            AssaiModelo.codigo.label('modelo_codigo'),
            AssaiModelo.nome.label('modelo_nome'),
            AssaiMoto.chassi.label('chassi'),
            AssaiMoto.cor.label('cor'),
            AssaiMotoEvento.tipo.label('tipo'),
            AssaiMotoEvento.ocorrido_em.label('ocorrido_em'),
            Usuario.nome.label('operador_nome'),
        )
        .select_from(AssaiMoto)
        .join(AssaiModelo, AssaiModelo.id == AssaiMoto.modelo_id)
        .join(sub, sub.c.chassi == AssaiMoto.chassi)
        .join(AssaiMotoEvento, AssaiMotoEvento.id == sub.c.ultimo_id)
        .outerjoin(Usuario, Usuario.id == AssaiMotoEvento.operador_id)
        .filter(AssaiMotoEvento.tipo.in_(tipos))
    )

    if filtros:
        chassi = (filtros.get('chassi') or '').strip().upper()
        if chassi:
            q = q.filter(AssaiMoto.chassi.ilike(f'%{chassi}%'))
        modelo_id = filtros.get('modelo_id')
        if modelo_id:
            q = q.filter(AssaiMoto.modelo_id == modelo_id)

    rows = (
        q.order_by(AssaiModelo.codigo, AssaiMotoEvento.ocorrido_em.desc())
        .all()
    )

    return [
        {
            'modelo_id': r.modelo_id,
            'modelo_codigo': r.modelo_codigo,
            'modelo_nome': r.modelo_nome,
            'chassi': r.chassi,
            'cor': r.cor or '-',
            'ocorrido_em': r.ocorrido_em,
            'operador_nome': r.operador_nome or '-',
            'tipo': r.tipo,
        }
        for r in rows
    ]


def _agrupar_por_modelo(motos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Agrupa lista de motos por modelo. Retorna {'total', 'modelos': [...]}.

    Estrutura retornada:
        {
            'total': int,
            'modelos': [
                {
                    'modelo_id', 'codigo', 'nome', 'qtd',
                    'motos': [{chassi, cor, ocorrido_em, operador_nome, tipo}, ...],
                },
                ...
            ]
        }
    Ordenado por modelo_codigo.
    """
    por_modelo: Dict[int, Dict[str, Any]] = {}
    for m in motos:
        bucket = por_modelo.setdefault(m['modelo_id'], {
            'modelo_id': m['modelo_id'],
            'codigo': m['modelo_codigo'],
            'nome': m['modelo_nome'],
            'qtd': 0,
            'motos': [],
        })
        bucket['qtd'] += 1
        bucket['motos'].append({
            'chassi': m['chassi'],
            'cor': m['cor'],
            'ocorrido_em': m['ocorrido_em'],
            'operador_nome': m['operador_nome'],
            'tipo': m['tipo'],
        })
    modelos = sorted(por_modelo.values(), key=lambda b: b['codigo'])
    total = sum(b['qtd'] for b in modelos)
    return {'total': total, 'modelos': modelos}


def listar_motos_montadas_agrupadas(filtros=None) -> Dict[str, Any]:
    """Motos em status MONTADA efetivo (MONTADA ou REVERTIDA_PARA_MONTADA)
    agrupadas por modelo. Usado pela tela /motos-assai/montagem.

    filtros: dict opcional com 'chassi' (ilike) e 'modelo_id' (==).
    """
    motos = _listar_motos_por_tipos(STATUS_MONTADA_EFETIVO, filtros=filtros)
    return _agrupar_por_modelo(motos)


def listar_motos_disponiveis_agrupadas(filtros=None) -> Dict[str, Any]:
    """Motos em status DISPONIVEL agrupadas por modelo.
    Usado pela tela /motos-assai/disponibilizar.

    filtros: dict opcional com 'chassi' (ilike) e 'modelo_id' (==).
    """
    motos = _listar_motos_por_tipos(EVENTO_DISPONIVEL, filtros=filtros)
    return _agrupar_por_modelo(motos)


# =====================================================================
# Metricas por pedido / pedido x loja (Item 2 - resumos nas linhas)
# =====================================================================
# Cinco metricas por entidade:
#   - total:     SUM(qtd_pedida) do(s) item(ns)
#   - separado:  COUNT(AssaiSeparacaoItem) em seps != CANCELADA
#   - faturado:  COUNT(AssaiSeparacaoItem) em seps FATURADA
#   - entregue:  COUNT de chassis cujas NFs Q.P.A. estao em EntregaMonitorada
#                origem='OP_ASSAI' com entregue=True
#   - pendente:  total - separado
#
# Implementacao batch (uma query por metrica) para evitar N+1 quando a UI
# precisa de varios pedidos (lista de pedidos).


def metricas_por_pedido(pedido_ids: List[int]) -> Dict[int, Dict[str, int]]:
    """Calcula 5 metricas (total/separado/faturado/entregue/pendente) por pedido.

    Args:
        pedido_ids: lista de ids de AssaiPedidoVenda.

    Returns:
        {pedido_id: {'total', 'separado', 'faturado', 'entregue', 'pendente'}}.
        Pedidos sem itens vem com zero em tudo.
    """
    from app.motos_assai.models import (
        AssaiNfQpa, AssaiNfQpaItem, NF_STATUS_BATEU,
        SEPARACAO_STATUS_FATURADA,
    )
    from app.monitoramento.models import EntregaMonitorada

    if not pedido_ids:
        return {}

    # Total: SUM qtd_pedida por pedido
    totais = dict(
        db.session.query(
            AssaiPedidoVendaItem.pedido_id,
            func.sum(AssaiPedidoVendaItem.qtd_pedida),
        )
        .filter(AssaiPedidoVendaItem.pedido_id.in_(pedido_ids))
        .group_by(AssaiPedidoVendaItem.pedido_id)
        .all()
    )
    totais = {pid: int(v or 0) for pid, v in totais.items()}

    # Separado: COUNT items em seps != CANCELADA por pedido
    separados = dict(
        db.session.query(
            AssaiSeparacao.pedido_id,
            func.count(AssaiSeparacaoItem.id),
        )
        .join(AssaiSeparacaoItem, AssaiSeparacaoItem.separacao_id == AssaiSeparacao.id)
        .filter(
            AssaiSeparacao.pedido_id.in_(pedido_ids),
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
        )
        .group_by(AssaiSeparacao.pedido_id)
        .all()
    )
    separados = {pid: int(v or 0) for pid, v in separados.items()}

    # Faturado: COUNT items em seps FATURADA por pedido
    faturados = dict(
        db.session.query(
            AssaiSeparacao.pedido_id,
            func.count(AssaiSeparacaoItem.id),
        )
        .join(AssaiSeparacaoItem, AssaiSeparacaoItem.separacao_id == AssaiSeparacao.id)
        .filter(
            AssaiSeparacao.pedido_id.in_(pedido_ids),
            AssaiSeparacao.status == SEPARACAO_STATUS_FATURADA,
        )
        .group_by(AssaiSeparacao.pedido_id)
        .all()
    )
    faturados = {pid: int(v or 0) for pid, v in faturados.items()}

    # Entregue: COUNT DISTINCT de chassis de seps FATURADA cujos NFs estao em
    # EntregaMonitorada(OP_ASSAI, entregue=True). Cada AssaiSeparacao->1 NF
    # via assai_nf_qpa.separacao_id. Cada NF tem N items (chassis).
    # Conta NfQpaItem da NF cuja entrega esta entregue=True.
    #
    # DISTINCT (code review fix 2026-05-12): EntregaMonitorada.numero_nf NAO
    # tem UNIQUE constraint — duplicatas (mesmo numero_nf + origem='OP_ASSAI'
    # + entregue=True) duplicariam a contagem via JOIN. DISTINCT em
    # AssaiNfQpaItem.id garante 1 chassi = 1 contagem.
    entregues_rows = (
        db.session.query(
            AssaiSeparacao.pedido_id,
            func.count(AssaiNfQpaItem.id.distinct()),
        )
        .join(AssaiNfQpa, AssaiNfQpa.separacao_id == AssaiSeparacao.id)
        .join(AssaiNfQpaItem, AssaiNfQpaItem.nf_id == AssaiNfQpa.id)
        .join(
            EntregaMonitorada,
            db.and_(
                EntregaMonitorada.numero_nf == AssaiNfQpa.numero,
                EntregaMonitorada.origem == 'OP_ASSAI',
                EntregaMonitorada.entregue == True,  # noqa: E712
            ),
        )
        .filter(
            AssaiSeparacao.pedido_id.in_(pedido_ids),
            AssaiNfQpa.status_match == NF_STATUS_BATEU,
        )
        .group_by(AssaiSeparacao.pedido_id)
        .all()
    )
    entregues = {pid: int(v or 0) for pid, v in entregues_rows}

    # Monta resultado
    result: Dict[int, Dict[str, int]] = {}
    for pid in pedido_ids:
        total = totais.get(pid, 0)
        separado = separados.get(pid, 0)
        result[pid] = {
            'total': total,
            'separado': separado,
            'faturado': faturados.get(pid, 0),
            'entregue': entregues.get(pid, 0),
            'pendente': max(0, total - separado),
        }
    return result


def metricas_por_pedido_loja(pedido_id: int) -> Dict[int, Dict[str, int]]:
    """5 metricas por (pedido_id, loja_id). Igual a metricas_por_pedido mas
    granularidade por loja. Usado em pedidos/detalhe.html (header accordion).

    Returns:
        {loja_id: {'total', 'separado', 'faturado', 'entregue', 'pendente'}}.
    """
    from app.motos_assai.models import (
        AssaiNfQpa, AssaiNfQpaItem, NF_STATUS_BATEU,
        SEPARACAO_STATUS_FATURADA,
    )
    from app.monitoramento.models import EntregaMonitorada

    # Total por loja
    totais = dict(
        db.session.query(
            AssaiPedidoVendaItem.loja_id,
            func.sum(AssaiPedidoVendaItem.qtd_pedida),
        )
        .filter(AssaiPedidoVendaItem.pedido_id == pedido_id)
        .group_by(AssaiPedidoVendaItem.loja_id)
        .all()
    )
    totais = {lid: int(v or 0) for lid, v in totais.items()}

    # Separado por loja
    separados = dict(
        db.session.query(
            AssaiSeparacao.loja_id,
            func.count(AssaiSeparacaoItem.id),
        )
        .join(AssaiSeparacaoItem, AssaiSeparacaoItem.separacao_id == AssaiSeparacao.id)
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
        )
        .group_by(AssaiSeparacao.loja_id)
        .all()
    )
    separados = {lid: int(v or 0) for lid, v in separados.items()}

    # Faturado por loja
    faturados = dict(
        db.session.query(
            AssaiSeparacao.loja_id,
            func.count(AssaiSeparacaoItem.id),
        )
        .join(AssaiSeparacaoItem, AssaiSeparacaoItem.separacao_id == AssaiSeparacao.id)
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.status == SEPARACAO_STATUS_FATURADA,
        )
        .group_by(AssaiSeparacao.loja_id)
        .all()
    )
    faturados = {lid: int(v or 0) for lid, v in faturados.items()}

    # Entregue por loja
    entregues_rows = (
        db.session.query(
            AssaiSeparacao.loja_id,
            func.count(AssaiNfQpaItem.id),
        )
        .join(AssaiNfQpa, AssaiNfQpa.separacao_id == AssaiSeparacao.id)
        .join(AssaiNfQpaItem, AssaiNfQpaItem.nf_id == AssaiNfQpa.id)
        .join(
            EntregaMonitorada,
            db.and_(
                EntregaMonitorada.numero_nf == AssaiNfQpa.numero,
                EntregaMonitorada.origem == 'OP_ASSAI',
                EntregaMonitorada.entregue == True,  # noqa: E712
            ),
        )
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiNfQpa.status_match == NF_STATUS_BATEU,
        )
        .group_by(AssaiSeparacao.loja_id)
        .all()
    )
    entregues = {lid: int(v or 0) for lid, v in entregues_rows}

    # Lojas: union de todas que aparecem em qualquer metrica (garante presenca
    # mesmo de lojas com 0 separado e total > 0)
    todas_lojas = set(totais.keys()) | set(separados.keys()) | set(faturados.keys()) | set(entregues.keys())
    result: Dict[int, Dict[str, int]] = {}
    for lid in todas_lojas:
        total = totais.get(lid, 0)
        separado = separados.get(lid, 0)
        result[lid] = {
            'total': total,
            'separado': separado,
            'faturado': faturados.get(lid, 0),
            'entregue': entregues.get(lid, 0),
            'pendente': max(0, total - separado),
        }
    return result

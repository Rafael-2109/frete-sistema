"""Estoque HORA: calcula estoque por loja a partir do ultimo evento de cada moto.

Regra (invariante 4): estado atual = ultimo HoraMotoEvento por chassi.
"Em estoque" = chassi cujo ultimo evento esta em `EVENTOS_EM_ESTOQUE` e a loja
do evento e a loja onde a moto esta.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import and_, func

from app import db
from app.hora.models import (
    HoraLoja,
    HoraModelo,
    HoraMoto,
    HoraMotoEvento,
)


# Eventos que significam "moto esta no estoque da loja do evento"
EVENTOS_EM_ESTOQUE = (
    'RECEBIDA', 'CONFERIDA', 'TRANSFERIDA',
    'CANCELADA',  # transferencia cancelada — moto voltou a origem
    'AVARIADA', 'FALTANDO_PECA',
)
# Eventos que tiram a moto do estoque
EVENTOS_FORA_ESTOQUE = ('VENDIDA', 'DEVOLVIDA')
# Eventos "em limbo" — nao estao no estoque de nenhuma loja
EVENTOS_EM_TRANSITO = ('EM_TRANSITO',)


def _subquery_ultimo_evento_id():
    """Subquery: para cada chassi, o id do evento mais recente."""
    return (
        db.session.query(
            HoraMotoEvento.numero_chassi.label('chassi'),
            func.max(HoraMotoEvento.id).label('max_id'),
        )
        .group_by(HoraMotoEvento.numero_chassi)
        .subquery()
    )


def _nf_recebimento_por_chassi(chassis: List[str]) -> Dict[str, dict]:
    """Para cada chassi, retorna {nf_id, nf_numero, nf_serie, recebimento_id}
    do recebimento/conferencia de entrada mais recente. Silenciosamente omite
    chassis sem conferencia.
    """
    if not chassis:
        return {}
    from app.hora.models import HoraNfEntrada, HoraRecebimento, HoraRecebimentoConferencia

    chassis_norm = [c.strip().upper() for c in chassis]
    # Pega a conferencia ativa mais recente por chassi.
    sub = (
        db.session.query(
            HoraRecebimentoConferencia.numero_chassi.label('chassi'),
            func.max(HoraRecebimentoConferencia.id).label('max_id'),
        )
        .filter(
            HoraRecebimentoConferencia.numero_chassi.in_(chassis_norm),
            HoraRecebimentoConferencia.substituida.is_(False),
        )
        .group_by(HoraRecebimentoConferencia.numero_chassi)
        .subquery()
    )
    rows = (
        db.session.query(
            HoraRecebimentoConferencia.numero_chassi,
            HoraRecebimento.id.label('recebimento_id'),
            HoraNfEntrada.id.label('nf_id'),
            HoraNfEntrada.numero_nf.label('nf_numero'),
            HoraNfEntrada.serie_nf.label('nf_serie'),
        )
        .join(sub, HoraRecebimentoConferencia.id == sub.c.max_id)
        .join(HoraRecebimento, HoraRecebimento.id == HoraRecebimentoConferencia.recebimento_id)
        .join(HoraNfEntrada, HoraNfEntrada.id == HoraRecebimento.nf_id)
        .all()
    )
    return {
        r.numero_chassi: {
            'nf_id': r.nf_id,
            'nf_numero': r.nf_numero,
            'nf_serie': r.nf_serie,
            'recebimento_id': r.recebimento_id,
        }
        for r in rows
    }


def _pecas_abertas_por_chassi(chassis: List[str]) -> Dict[str, int]:
    """Count de pecas faltando ABERTA por chassi."""
    if not chassis:
        return {}
    from app.hora.models import HoraPecaFaltando

    chassis_norm = [c.strip().upper() for c in chassis]
    rows = (
        db.session.query(
            HoraPecaFaltando.numero_chassi,
            func.count(HoraPecaFaltando.id),
        )
        .filter(
            HoraPecaFaltando.numero_chassi.in_(chassis_norm),
            HoraPecaFaltando.status == 'ABERTA',
        )
        .group_by(HoraPecaFaltando.numero_chassi)
        .all()
    )
    return {chassi: count for chassi, count in rows}


def _transferencias_em_transito_por_chassi(chassis: List[str]) -> Dict[str, int]:
    """Count de transferencias cujo item aponta para chassi e ainda nao
    foi confirmado no destino (conferido_destino_em IS NULL).
    Conta apenas transferencias com status EM_TRANSITO.
    """
    if not chassis:
        return {}
    from app.hora.models import HoraTransferencia, HoraTransferenciaItem

    chassis_norm = [c.strip().upper() for c in chassis]
    rows = (
        db.session.query(
            HoraTransferenciaItem.numero_chassi,
            func.count(HoraTransferenciaItem.id),
        )
        .join(HoraTransferencia, HoraTransferencia.id == HoraTransferenciaItem.transferencia_id)
        .filter(
            HoraTransferenciaItem.numero_chassi.in_(chassis_norm),
            HoraTransferencia.status == 'EM_TRANSITO',
            HoraTransferenciaItem.conferido_destino_em.is_(None),
        )
        .group_by(HoraTransferenciaItem.numero_chassi)
        .all()
    )
    return {chassi: count for chassi, count in rows}


def listar_estoque(
    loja_id: Optional[int] = None,
    modelo_id: Optional[int] = None,
    cor: Optional[str] = None,
    incluir_avariadas: bool = True,
    incluir_faltando_peca: bool = True,
    incluir_fora_estoque: bool = False,
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> List[dict]:
    """Lista motos chassi-a-chassi.

    Quando `incluir_fora_estoque=False` (default): somente motos cujo ultimo
    evento esta em EVENTOS_EM_ESTOQUE.
    Quando `incluir_fora_estoque=True`: TODAS as motos cadastradas (inclusive
    VENDIDA, DEVOLVIDA, EM_TRANSITO), com o flag `moto_disponivel`.

    Retorna dicts com: chassi, modelo_*, cor, loja_*, ultimo_evento, ...,
    nf_id, nf_numero, nf_serie, recebimento_id, avarias_abertas,
    pecas_faltando_abertas, transferencias_em_transito, moto_disponivel.
    """
    if incluir_fora_estoque:
        tipos = None  # sem filtro de tipo
    else:
        tipos = list(EVENTOS_EM_ESTOQUE)
        if not incluir_avariadas:
            tipos = [t for t in tipos if t != 'AVARIADA']
        if not incluir_faltando_peca:
            tipos = [t for t in tipos if t != 'FALTANDO_PECA']

    sub = _subquery_ultimo_evento_id()
    q = (
        db.session.query(HoraMotoEvento, HoraMoto, HoraModelo, HoraLoja)
        .join(
            sub,
            and_(
                HoraMotoEvento.numero_chassi == sub.c.chassi,
                HoraMotoEvento.id == sub.c.max_id,
            ),
        )
        .join(HoraMoto, HoraMotoEvento.numero_chassi == HoraMoto.numero_chassi)
        .join(HoraModelo, HoraMoto.modelo_id == HoraModelo.id)
        .outerjoin(HoraLoja, HoraMotoEvento.loja_id == HoraLoja.id)
    )
    if tipos is not None:
        q = q.filter(HoraMotoEvento.tipo.in_(tipos))

    if loja_id:
        q = q.filter(HoraMotoEvento.loja_id == loja_id)
    if modelo_id:
        q = q.filter(HoraMoto.modelo_id == modelo_id)
    if cor:
        q = q.filter(HoraMoto.cor == cor.strip().upper())
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        if incluir_fora_estoque:
            # Para "fora de estoque": ultimo evento pode ter loja_id NULL
            # (ex.: VENDIDA). Garantir autorizacao via subquery que exige
            # que ESTE chassi ja teve ao menos 1 evento em loja permitida.
            chassis_permitidos = (
                db.session.query(HoraMotoEvento.numero_chassi)
                .filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))
                .distinct()
                .subquery()
            )
            q = q.filter(HoraMotoEvento.numero_chassi.in_(chassis_permitidos))
        else:
            q = q.filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))

    q = q.order_by(HoraMotoEvento.timestamp.desc())

    resultado = []
    for ev, moto, modelo, loja in q.all():
        resultado.append({
            'chassi': moto.numero_chassi,
            'modelo_id': modelo.id,
            'modelo_nome': modelo.nome_modelo,
            'cor': moto.cor,
            'motor': moto.numero_motor,
            'ano_modelo': moto.ano_modelo,
            'loja_id': loja.id if loja else None,
            'loja_nome': loja.rotulo_display if loja else None,
            'ultimo_evento': ev.tipo,
            'ultimo_evento_em': ev.timestamp,
            'ultimo_evento_detalhe': ev.detalhe,
            'moto_disponivel': ev.tipo in EVENTOS_EM_ESTOQUE,
        })

    if not resultado:
        return resultado

    chassis = [r['chassi'] for r in resultado]

    # Enriquecimento: NF de entrada + recebimento
    nf_map = _nf_recebimento_por_chassi(chassis)
    # Avarias abertas
    from app.hora.services.avaria_service import avarias_abertas_por_chassi
    avarias_map = avarias_abertas_por_chassi(chassis)
    # Pecas faltando abertas
    pecas_map = _pecas_abertas_por_chassi(chassis)
    # Transferencias em transito (nao confirmadas no destino)
    transf_map = _transferencias_em_transito_por_chassi(chassis)

    for r in resultado:
        nf = nf_map.get(r['chassi']) or {}
        r['nf_id'] = nf.get('nf_id')
        r['nf_numero'] = nf.get('nf_numero')
        r['nf_serie'] = nf.get('nf_serie')
        r['recebimento_id'] = nf.get('recebimento_id')
        r['avarias_abertas'] = avarias_map.get(r['chassi'], 0)
        r['pecas_faltando_abertas'] = pecas_map.get(r['chassi'], 0)
        r['transferencias_em_transito'] = transf_map.get(r['chassi'], 0)

    return resultado


def opcoes_filtro_estoque(
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> dict:
    """Retorna opcoes para SELECTs de filtro: apenas modelos/cores que
    atualmente tem ao menos 1 moto em EVENTOS_EM_ESTOQUE nas lojas permitidas.

    Returns:
        {
            'modelos': [{'id': int, 'nome_modelo': str}, ...],
            'cores': [str, ...],
        }
    """
    sub = _subquery_ultimo_evento_id()
    q_base = (
        db.session.query(
            HoraModelo.id,
            HoraModelo.nome_modelo,
            HoraMoto.cor,
        )
        .join(HoraMoto, HoraMoto.modelo_id == HoraModelo.id)
        .join(sub, HoraMoto.numero_chassi == sub.c.chassi)
        .join(HoraMotoEvento, HoraMotoEvento.id == sub.c.max_id)
        .filter(HoraMotoEvento.tipo.in_(EVENTOS_EM_ESTOQUE))
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return {'modelos': [], 'cores': []}
        q_base = q_base.filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))

    modelos_dict: Dict[int, str] = {}
    cores_set = set()
    for mid, mnome, cor in q_base.distinct().all():
        modelos_dict[mid] = mnome
        if cor:
            cores_set.add(cor)

    modelos = [
        {'id': mid, 'nome_modelo': nome}
        for mid, nome in sorted(modelos_dict.items(), key=lambda x: x[1] or '')
    ]
    cores = sorted(cores_set)
    return {'modelos': modelos, 'cores': cores}


def kpis_estoque_por_loja(
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> List[dict]:
    """Agrupa estoque por loja (contagem total + avariadas + faltando_peca)."""
    sub = _subquery_ultimo_evento_id()
    q = (
        db.session.query(
            HoraLoja.id.label('loja_id'),
            HoraLoja.apelido,
            HoraLoja.nome,
            HoraLoja.nome_fantasia,
            HoraMotoEvento.tipo,
            func.count().label('total'),
        )
        .join(
            sub,
            and_(
                HoraMotoEvento.numero_chassi == sub.c.chassi,
                HoraMotoEvento.id == sub.c.max_id,
            ),
        )
        .join(HoraLoja, HoraMotoEvento.loja_id == HoraLoja.id)
        .filter(HoraMotoEvento.tipo.in_(EVENTOS_EM_ESTOQUE))
        .group_by(HoraLoja.id, HoraLoja.apelido, HoraLoja.nome,
                  HoraLoja.nome_fantasia, HoraMotoEvento.tipo)
    )
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraLoja.id.in_(lojas_permitidas_ids))

    acum = {}
    for row in q.all():
        k = row.loja_id
        if k not in acum:
            acum[k] = {
                'loja_id': row.loja_id,
                'loja_nome': row.apelido or row.nome_fantasia or row.nome,
                'total': 0,
                'disponivel': 0,
                'avariada': 0,
                'faltando_peca': 0,
            }
        acum[k]['total'] += row.total
        if row.tipo == 'AVARIADA':
            acum[k]['avariada'] += row.total
        elif row.tipo == 'FALTANDO_PECA':
            acum[k]['faltando_peca'] += row.total
        else:
            acum[k]['disponivel'] += row.total

    return sorted(acum.values(), key=lambda x: x['loja_nome'] or '')


def kpis_estoque_por_modelo(
    loja_id: Optional[int] = None,
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> List[dict]:
    """Agrupa estoque por modelo (contagem total)."""
    sub = _subquery_ultimo_evento_id()
    q = (
        db.session.query(
            HoraModelo.id,
            HoraModelo.nome_modelo,
            HoraMoto.cor,
            func.count().label('total'),
        )
        .join(HoraMoto, HoraMoto.modelo_id == HoraModelo.id)
        .join(
            sub,
            HoraMoto.numero_chassi == sub.c.chassi,
        )
        .join(HoraMotoEvento, HoraMotoEvento.id == sub.c.max_id)
        .filter(HoraMotoEvento.tipo.in_(EVENTOS_EM_ESTOQUE))
        .group_by(HoraModelo.id, HoraModelo.nome_modelo, HoraMoto.cor)
        .order_by(HoraModelo.nome_modelo, HoraMoto.cor)
    )
    if loja_id:
        q = q.filter(HoraMotoEvento.loja_id == loja_id)
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))

    return [
        {
            'modelo_id': r.id,
            'modelo_nome': r.nome_modelo,
            'cor': r.cor,
            'total': r.total,
        }
        for r in q.all()
    ]


def historico_chassi(numero_chassi: str) -> List[dict]:
    """Retorna todos os eventos de um chassi, mais recentes primeiro.

    Mantido por compatibilidade com quem ainda consome. A tela de detalhe
    usa agora `rastreamento_completo` (mais rico).
    """
    chassi = numero_chassi.strip().upper()
    eventos = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraMotoEvento.timestamp.desc())
        .all()
    )
    return [
        {
            'id': e.id,
            'tipo': e.tipo,
            'timestamp': e.timestamp,
            'loja_id': e.loja_id,
            'loja_nome': e.loja.rotulo_display if e.loja else None,
            'operador': e.operador,
            'detalhe': e.detalhe,
            'origem_tabela': e.origem_tabela,
            'origem_id': e.origem_id,
        }
        for e in eventos
    ]


def rastreamento_completo(numero_chassi: str) -> dict:
    """Cruza dados de TODAS as entidades que tocam o chassi, gerando o
    "raio-x" usado na tela de detalhe. Sem eventos crus — entidades reais.

    Returns dict com chaves: pedido, nf, nf_item, recebimento, conferencia,
    conferencia_divergencias, transferencias, avarias, pecas_faltando, venda,
    devolucoes, ultimo_evento, moto_disponivel.
    Campos ausentes vem como None (ou [] para coleções).
    """
    from app.hora.models import (
        HoraAvaria, HoraDevolucaoFornecedor, HoraDevolucaoFornecedorItem,
        HoraNfEntradaItem, HoraPecaFaltando, HoraPedido,
        HoraPedidoItem, HoraRecebimento, HoraRecebimentoConferencia,
        HoraTransferencia, HoraTransferenciaItem, HoraVendaItem,
    )

    chassi = numero_chassi.strip().upper()
    resultado = {
        'pedido': None,
        'nf': None,
        'nf_item': None,
        'recebimento': None,
        'conferencia': None,
        'conferencia_divergencias': [],
        'transferencias': [],
        'avarias': [],
        'pecas_faltando': [],
        'venda': None,
        'venda_item': None,
        'devolucoes': [],
        'ultimo_evento': None,
        'moto_disponivel': False,
    }

    # NF item + NF + Pedido
    nf_item = (
        HoraNfEntradaItem.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraNfEntradaItem.id.desc())
        .first()
    )
    if nf_item:
        resultado['nf_item'] = nf_item
        resultado['nf'] = nf_item.nf
        if nf_item.nf and nf_item.nf.pedido_id:
            resultado['pedido'] = HoraPedido.query.get(nf_item.nf.pedido_id)
        else:
            # Fallback: pedido diretamente pelo chassi no item de pedido.
            item_pedido = (
                HoraPedidoItem.query
                .filter_by(numero_chassi=chassi)
                .order_by(HoraPedidoItem.id.desc())
                .first()
            )
            if item_pedido:
                resultado['pedido'] = item_pedido.pedido
    else:
        # Sem NF mas possivelmente com pedido com chassi atribuido.
        item_pedido = (
            HoraPedidoItem.query
            .filter_by(numero_chassi=chassi)
            .order_by(HoraPedidoItem.id.desc())
            .first()
        )
        if item_pedido:
            resultado['pedido'] = item_pedido.pedido

    # Recebimento + Conferencia (ativa mais recente)
    conf = (
        HoraRecebimentoConferencia.query
        .filter_by(numero_chassi=chassi, substituida=False)
        .order_by(HoraRecebimentoConferencia.id.desc())
        .first()
    )
    if conf:
        resultado['conferencia'] = conf
        resultado['conferencia_divergencias'] = list(conf.divergencias)
        resultado['recebimento'] = HoraRecebimento.query.get(conf.recebimento_id)

    # Transferencias
    resultado['transferencias'] = (
        HoraTransferencia.query
        .join(HoraTransferenciaItem,
              HoraTransferenciaItem.transferencia_id == HoraTransferencia.id)
        .filter(HoraTransferenciaItem.numero_chassi == chassi)
        .distinct()
        .order_by(HoraTransferencia.emitida_em.desc())
        .all()
    )

    # Avarias
    resultado['avarias'] = (
        HoraAvaria.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraAvaria.criado_em.desc())
        .all()
    )

    # Pecas faltando
    resultado['pecas_faltando'] = (
        HoraPecaFaltando.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraPecaFaltando.criado_em.desc())
        .all()
    )

    # Venda
    venda_item = (
        HoraVendaItem.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraVendaItem.id.desc())
        .first()
    )
    if venda_item:
        resultado['venda_item'] = venda_item
        resultado['venda'] = venda_item.venda

    # Devolucoes (ao fornecedor)
    resultado['devolucoes'] = (
        HoraDevolucaoFornecedor.query
        .join(HoraDevolucaoFornecedorItem,
              HoraDevolucaoFornecedorItem.devolucao_id == HoraDevolucaoFornecedor.id)
        .filter(HoraDevolucaoFornecedorItem.numero_chassi == chassi)
        .distinct()
        .order_by(HoraDevolucaoFornecedor.criado_em.desc())
        .all()
    )

    # Ultimo evento para status geral
    ult = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraMotoEvento.timestamp.desc())
        .first()
    )
    if ult:
        resultado['ultimo_evento'] = {
            'tipo': ult.tipo,
            'timestamp': ult.timestamp,
            'loja_id': ult.loja_id,
            'loja_nome': ult.loja.rotulo_display if ult.loja else None,
            'detalhe': ult.detalhe,
        }
        resultado['moto_disponivel'] = ult.tipo in EVENTOS_EM_ESTOQUE

    return resultado


def listar_em_transito(
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> List[dict]:
    """Motos com ultimo evento EM_TRANSITO, visiveis para origem OU destino.

    Interpretacao: evento EM_TRANSITO e emitido com loja_id=destino. Para que
    a loja origem tambem enxergue o que saiu, fazemos JOIN com
    hora_transferencia_item -> hora_transferencia e filtramos onde
    loja_origem_id ou loja_destino_id esta em lojas_permitidas_ids.
    """
    from app.hora.models import HoraTransferencia, HoraTransferenciaItem
    from sqlalchemy import or_

    sub = _subquery_ultimo_evento_id()
    q = (
        db.session.query(
            HoraMotoEvento, HoraMoto, HoraModelo,
            HoraTransferencia, HoraLoja,
        )
        .join(
            sub,
            and_(
                HoraMotoEvento.numero_chassi == sub.c.chassi,
                HoraMotoEvento.id == sub.c.max_id,
            ),
        )
        .join(HoraMoto, HoraMotoEvento.numero_chassi == HoraMoto.numero_chassi)
        .join(HoraModelo, HoraMoto.modelo_id == HoraModelo.id)
        .outerjoin(HoraLoja, HoraMotoEvento.loja_id == HoraLoja.id)
        .join(
            HoraTransferenciaItem,
            and_(
                HoraTransferenciaItem.id == HoraMotoEvento.origem_id,
                HoraMotoEvento.origem_tabela == 'hora_transferencia_item',
            ),
        )
        .join(
            HoraTransferencia,
            HoraTransferencia.id == HoraTransferenciaItem.transferencia_id,
        )
        .filter(HoraMotoEvento.tipo == 'EM_TRANSITO')
    )

    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(or_(
            HoraTransferencia.loja_origem_id.in_(lojas_permitidas_ids),
            HoraTransferencia.loja_destino_id.in_(lojas_permitidas_ids),
        ))

    q = q.order_by(HoraMotoEvento.timestamp.desc())

    return [
        {
            'numero_chassi': moto.numero_chassi,
            'modelo_id': modelo.id,
            'modelo_nome': modelo.nome_modelo,
            'cor': moto.cor,
            'loja_destino_id': loja.id if loja else None,
            'loja_destino_nome': loja.rotulo_display if loja else None,
            'loja_origem_id': transferencia.loja_origem_id,
            'transferencia_id': transferencia.id,
            'emitido_em': ev.timestamp,
            'detalhe': ev.detalhe,
        }
        for ev, moto, modelo, transferencia, loja in q.all()
    ]

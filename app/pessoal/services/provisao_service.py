"""CRUD de PessoalProvisao (forecast manual) e sync com orcamento datado.

Vertente FLUXO DE CAIXA. Permite usuario cadastrar lancamentos FUTUROS esperados
(pro-labore, reembolsos, aluguel, etc.) que aparecem como linhas provisionadas
na tela de fluxo de caixa.

Tambem materializa orcamento em provisoes (cada categoria do orcamento com data
de vencimento vira uma provisao de saida).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from app import db
from app.pessoal.models import (
    PessoalCategoria, PessoalOrcamento, PessoalProvisao, PessoalTransacao,
)
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


# =============================================================================
# CRUD
# =============================================================================
def criar_provisao(
    tipo: str,
    data_prevista: date,
    valor: float,
    descricao: str,
    categoria_id: Optional[int] = None,
    membro_id: Optional[int] = None,
    conta_id: Optional[int] = None,
    orcamento_id: Optional[int] = None,
    recorrente: bool = False,
    recorrencia_tipo: Optional[str] = None,
    recorrencia_ate: Optional[date] = None,
    observacao: Optional[str] = None,
    criado_por: Optional[str] = None,
    commit: bool = True,
) -> PessoalProvisao:
    """Cria uma provisao.

    Se recorrente=True e recorrencia_tipo='mensal' (ou outro), expande para
    copias mensais ate recorrencia_ate (ou 12 meses se nao informado).
    A PRIMEIRA provisao retornada e a 'mae'; as demais sao criadas com recorrente=False
    (para evitar replicacao em cascata).
    """
    if tipo not in ('entrada', 'saida'):
        raise ValueError(f"tipo invalido: {tipo!r} (esperado 'entrada' ou 'saida')")
    if float(valor) <= 0:
        raise ValueError('valor deve ser > 0')
    if recorrente and recorrencia_tipo not in ('mensal', 'semanal', 'anual'):
        raise ValueError(
            f"recorrencia_tipo invalido: {recorrencia_tipo!r} "
            '(esperado mensal, semanal ou anual)'
        )

    # Idempotencia: evita insert duplicado se usuario clicar 2x (double-submit).
    # Considera duplicata: mesma (tipo, data_prevista, valor, descricao) ativa.
    duplicata = PessoalProvisao.query.filter(
        PessoalProvisao.tipo == tipo,
        PessoalProvisao.data_prevista == data_prevista,
        PessoalProvisao.valor == Decimal(str(valor)),
        PessoalProvisao.descricao == descricao,
        PessoalProvisao.status.in_(['PROVISIONADA', 'REALIZADA']),
    ).first()
    if duplicata:
        logger.info(
            'provisao_criada_duplicada_ignorada id=%d tipo=%s data=%s valor=%.2f',
            duplicata.id, tipo, data_prevista, float(valor),
        )
        return duplicata

    prov = PessoalProvisao(
        tipo=tipo,
        data_prevista=data_prevista,
        valor=Decimal(str(valor)),
        descricao=descricao,
        categoria_id=categoria_id,
        membro_id=membro_id,
        conta_id=conta_id,
        orcamento_id=orcamento_id,
        status='PROVISIONADA',
        recorrente=recorrente,
        recorrencia_tipo=recorrencia_tipo if recorrente else None,
        recorrencia_ate=recorrencia_ate if recorrente else None,
        observacao=observacao,
        criado_por=criado_por,
    )
    db.session.add(prov)
    db.session.flush()

    # Expande recorrencia
    criadas_extras = 0
    if recorrente and recorrencia_tipo:
        limite = recorrencia_ate or _adicionar_meses(data_prevista, 12)
        d_atual = _proxima_data(data_prevista, recorrencia_tipo)
        while d_atual <= limite:
            extra = PessoalProvisao(
                tipo=tipo,
                data_prevista=d_atual,
                valor=Decimal(str(valor)),
                descricao=descricao,
                categoria_id=categoria_id,
                membro_id=membro_id,
                conta_id=conta_id,
                orcamento_id=orcamento_id,
                status='PROVISIONADA',
                recorrente=False,  # as copias nao se replicam
                observacao=(
                    f'Recorrencia de provisao #{prov.id}'
                    if not observacao else
                    f'{observacao} | Recorrencia de #{prov.id}'
                ),
                criado_por=criado_por,
            )
            db.session.add(extra)
            criadas_extras += 1
            d_atual = _proxima_data(d_atual, recorrencia_tipo)

    logger.info(
        'provisao_criada id=%d tipo=%s data=%s valor=%.2f recorrencia=%s extras=%d',
        prov.id, tipo, data_prevista, float(valor),
        recorrencia_tipo or '-', criadas_extras,
    )

    if commit:
        db.session.commit()
    return prov


def atualizar_provisao(
    provisao_id: int,
    **campos,
) -> PessoalProvisao:
    """Atualiza campos de uma provisao existente. Nao toca recorrencia."""
    prov = db.session.get(PessoalProvisao, provisao_id)
    if not prov:
        raise ValueError(f'Provisao id={provisao_id} nao encontrada')
    if prov.status == 'REALIZADA':
        raise ValueError(
            f'Provisao id={provisao_id} esta REALIZADA, nao pode ser editada. '
            'Use reverter_realizacao() primeiro.'
        )

    editaveis = {
        'tipo', 'data_prevista', 'valor', 'descricao', 'categoria_id',
        'membro_id', 'conta_id', 'orcamento_id', 'observacao',
    }
    for k, v in campos.items():
        if k in editaveis:
            if k == 'valor':
                v = Decimal(str(v))
            setattr(prov, k, v)

    prov.atualizado_em = agora_utc_naive()
    db.session.commit()
    return prov


def cancelar_provisao(provisao_id: int) -> PessoalProvisao:
    """Marca provisao como CANCELADA (nao entra no fluxo)."""
    prov = db.session.get(PessoalProvisao, provisao_id)
    if not prov:
        raise ValueError(f'Provisao id={provisao_id} nao encontrada')
    prov.status = 'CANCELADA'
    prov.atualizado_em = agora_utc_naive()
    db.session.commit()
    logger.info('provisao_cancelada id=%d', provisao_id)
    return prov


def realizar_provisao(
    provisao_id: int,
    transacao_id: Optional[int] = None,
) -> PessoalProvisao:
    """Marca provisao como REALIZADA, opcionalmente vinculando a uma transacao.

    Se transacao_id for fornecido: vincula para rastreabilidade.
    """
    prov = db.session.get(PessoalProvisao, provisao_id)
    if not prov:
        raise ValueError(f'Provisao id={provisao_id} nao encontrada')
    if prov.status == 'CANCELADA':
        raise ValueError('Provisao cancelada nao pode ser realizada. Edite-a primeiro.')

    prov.status = 'REALIZADA'
    prov.realizado_em = agora_utc_naive()
    if transacao_id:
        t = db.session.get(PessoalTransacao, transacao_id)
        if not t:
            raise ValueError(f'Transacao id={transacao_id} nao encontrada')
        prov.transacao_id = transacao_id
    db.session.commit()
    logger.info(
        'provisao_realizada id=%d transacao_id=%s',
        provisao_id, transacao_id or '-',
    )
    return prov


def reverter_realizacao(provisao_id: int) -> PessoalProvisao:
    """Volta status REALIZADA para PROVISIONADA (permite editar de novo)."""
    prov = db.session.get(PessoalProvisao, provisao_id)
    if not prov:
        raise ValueError(f'Provisao id={provisao_id} nao encontrada')
    if prov.status != 'REALIZADA':
        raise ValueError(
            f'Provisao id={provisao_id} nao esta REALIZADA (status={prov.status})'
        )
    prov.status = 'PROVISIONADA'
    prov.realizado_em = None
    prov.transacao_id = None
    db.session.commit()
    return prov


def excluir_provisao(provisao_id: int) -> None:
    """DELETE fisico. Use com cuidado."""
    prov = db.session.get(PessoalProvisao, provisao_id)
    if not prov:
        raise ValueError(f'Provisao id={provisao_id} nao encontrada')
    db.session.delete(prov)
    db.session.commit()
    logger.info('provisao_excluida id=%d', provisao_id)


# =============================================================================
# LISTAGEM / FILTROS
# =============================================================================
def listar_provisoes(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    tipo: Optional[str] = None,
    status: Optional[str] = None,
    categoria_id: Optional[int] = None,
    membro_id: Optional[int] = None,
    conta_id: Optional[int] = None,
    incluir_canceladas: bool = False,
    limit: int = 500,
) -> list[dict]:
    """Lista provisoes com filtros."""
    q = PessoalProvisao.query
    if data_inicio:
        q = q.filter(PessoalProvisao.data_prevista >= data_inicio)
    if data_fim:
        q = q.filter(PessoalProvisao.data_prevista <= data_fim)
    if tipo:
        q = q.filter(PessoalProvisao.tipo == tipo)
    if status:
        q = q.filter(PessoalProvisao.status == status)
    elif not incluir_canceladas:
        q = q.filter(PessoalProvisao.status != 'CANCELADA')
    if categoria_id:
        q = q.filter(PessoalProvisao.categoria_id == categoria_id)
    if membro_id:
        q = q.filter(PessoalProvisao.membro_id == membro_id)
    if conta_id:
        q = q.filter(PessoalProvisao.conta_id == conta_id)
    return [
        p.to_dict() for p in q.order_by(
            PessoalProvisao.data_prevista.asc(), PessoalProvisao.id.asc(),
        ).limit(limit).all()
    ]


# =============================================================================
# ORCAMENTO -> PROVISOES (materializa orcamento datado)
# =============================================================================
def materializar_orcamento(
    ano: int,
    mes: int,
    dia_vencimento_default: int = 10,
    mapa_vencimento_por_categoria: Optional[dict[int, int]] = None,
    criado_por: Optional[str] = None,
) -> dict:
    """Cria provisoes de SAIDA a partir dos orcamentos do mes.

    Cada orcamento com categoria_id != NULL vira 1 provisao de saida na
    data de vencimento configurada.

    Args:
        ano/mes: mes do orcamento a materializar
        dia_vencimento_default: dia do mes para lancamento quando nao ha override
        mapa_vencimento_por_categoria: {categoria_id: dia} para override
        criado_por: usuario para auditoria

    Returns:
        dict com 'criadas', 'ignoradas' (ja existiam), 'detalhes'
    """
    mapa = mapa_vencimento_por_categoria or {}
    inicio = date(ano, mes, 1)

    # Busca orcamentos por categoria do mes
    orcamentos = PessoalOrcamento.query.filter(
        PessoalOrcamento.ano_mes == inicio,
        PessoalOrcamento.categoria_id.isnot(None),
    ).all()

    criadas = 0
    ignoradas = 0
    detalhes = []

    for orc in orcamentos:
        # Ja existe provisao ligada a este orcamento e ainda nao cancelada?
        ja_existe = PessoalProvisao.query.filter(
            PessoalProvisao.orcamento_id == orc.id,
            PessoalProvisao.status != 'CANCELADA',
        ).first()
        if ja_existe:
            ignoradas += 1
            continue

        dia = mapa.get(orc.categoria_id, dia_vencimento_default)
        # Clamp dia ao max do mes (evita 31/fev)
        ultimo_dia = _ultimo_dia_do_mes(ano, mes)
        dia_real = min(dia, ultimo_dia)
        d_prev = date(ano, mes, dia_real)

        cat = db.session.get(PessoalCategoria, orc.categoria_id)
        nome_cat = cat.nome if cat else f'Categoria #{orc.categoria_id}'

        prov = PessoalProvisao(
            tipo='saida',
            data_prevista=d_prev,
            valor=orc.valor_limite,
            descricao=f'Orcamento: {nome_cat}',
            categoria_id=orc.categoria_id,
            orcamento_id=orc.id,
            status='PROVISIONADA',
            criado_por=criado_por,
            observacao=f'Gerado automaticamente de orcamento id={orc.id}',
        )
        db.session.add(prov)
        criadas += 1
        detalhes.append({
            'orcamento_id': orc.id,
            'categoria_id': orc.categoria_id,
            'categoria_nome': nome_cat,
            'valor': float(orc.valor_limite),
            'data_prevista': d_prev.isoformat(),
        })

    db.session.commit()
    logger.info(
        'materializar_orcamento ano=%d mes=%d criadas=%d ignoradas=%d',
        ano, mes, criadas, ignoradas,
    )
    return {
        'ano': ano,
        'mes': mes,
        'criadas': criadas,
        'ignoradas': ignoradas,
        'detalhes': detalhes,
    }


def desmaterializar_orcamento(ano: int, mes: int) -> int:
    """Cancela todas as provisoes vindas de orcamento no mes (status=PROVISIONADA).

    Usa status=CANCELADA (nao DELETE) para preservar historico.
    """
    inicio = date(ano, mes, 1)
    if mes == 12:
        proximo = date(ano + 1, 1, 1)
    else:
        proximo = date(ano, mes + 1, 1)

    q = PessoalProvisao.query.filter(
        PessoalProvisao.orcamento_id.isnot(None),
        PessoalProvisao.status == 'PROVISIONADA',
        PessoalProvisao.data_prevista >= inicio,
        PessoalProvisao.data_prevista < proximo,
    )
    n = q.count()
    for prov in q.all():
        prov.status = 'CANCELADA'
        prov.atualizado_em = agora_utc_naive()
    db.session.commit()
    logger.info('desmaterializar_orcamento ano=%d mes=%d canceladas=%d', ano, mes, n)
    return n


# =============================================================================
# HELPERS DE DATAS
# =============================================================================
def _adicionar_meses(d: date, n: int) -> date:
    """Soma n meses a uma data, ajustando dia se necessario (fim de mes)."""
    mes = d.month - 1 + n
    ano = d.year + mes // 12
    mes = mes % 12 + 1
    dia = min(d.day, _ultimo_dia_do_mes(ano, mes))
    return date(ano, mes, dia)


def _proxima_data(d: date, tipo: str) -> date:
    if tipo == 'mensal':
        return _adicionar_meses(d, 1)
    if tipo == 'semanal':
        return d + timedelta(days=7)
    if tipo == 'anual':
        return _adicionar_meses(d, 12)
    raise ValueError(f'recorrencia_tipo invalido: {tipo!r}')


def _ultimo_dia_do_mes(ano: int, mes: int) -> int:
    import calendar
    return calendar.monthrange(ano, mes)[1]

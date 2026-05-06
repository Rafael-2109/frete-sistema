"""Helpers de autorização e filtragem por loja para queries do módulo HORA.

Usar em CADA listagem/dashboard que exiba dados de múltiplas lojas. Admin e
usuários com `loja_hora_id IS NULL` veem tudo; demais veem só sua loja.
"""
from __future__ import annotations

from typing import List, Optional, Set

from flask_login import current_user


def lojas_permitidas_ids() -> Optional[List[int]]:
    """Retorna lista de loja_id permitidas para o usuário atual.

    - None = acesso irrestrito (admin ou sem loja específica).
    - [id] = restrito a uma loja.
    """
    if not current_user.is_authenticated:
        return None
    return current_user.lojas_hora_ids_permitidas()


def cnpjs_lojas_permitidas() -> Optional[Set[str]]:
    """Retorna set de CNPJs das lojas permitidas.

    Usado em queries que filtram por `cnpj_destino` ou `cnpj_destinatario`
    (pedidos e NFs de entrada — que referenciam lojas por CNPJ, não por id).

    - None = acesso irrestrito.
    - set() vazio = usuário tem loja_hora_id mas loja não existe/inativa (bloqueia tudo).
    - {cnpj, ...} = restrito a esses CNPJs.
    """
    ids = lojas_permitidas_ids()
    if ids is None:
        return None

    from app.hora.models import HoraLoja
    lojas = HoraLoja.query.filter(HoraLoja.id.in_(ids)).all()
    return {l.cnpj for l in lojas}


def usuario_tem_acesso_a_loja(loja_id: int) -> bool:
    """Checa se usuário atual pode ver dados da loja_id informada."""
    ids = lojas_permitidas_ids()
    if ids is None:
        return True
    return loja_id in ids


def loja_origem_permitida_para_transferencia() -> Optional[int]:
    """Retorna loja_id obrigatoria como origem para o usuario atual.

    Returns:
        None se user e admin ou sem loja atribuida (pode escolher qualquer origem).
        int (loja_hora_id) se user e escopado a 1 loja.
    """
    if not current_user.is_authenticated:
        return None
    perfil = getattr(current_user, 'perfil', None)
    if perfil == 'administrador':
        return None
    return getattr(current_user, 'loja_hora_id', None)


# ---------------------------------------------------------------------------
# Autorizacao de chassi via documentos (pedido / NF entrada / venda)
#
# Motivacao: por design, a criacao de pedido com chassi insere em hora_moto
# (get_or_create_moto) mas NAO emite evento — o primeiro evento (RECEBIDA) so
# nasce na NF/recebimento. Para usuarios escopados conseguirem rastrear esses
# chassis "puros" (apenas em pedido/NF/venda, sem evento ainda), expandimos a
# autorizacao para considerar tambem a loja registrada nos documentos.
# ---------------------------------------------------------------------------


def chassis_acessiveis_subquery(lojas_permitidas: Optional[List[int]]):
    """Subquery dos chassis acessiveis ao usuario, considerando 4 fontes:

    1. HoraMotoEvento.loja_id (estado fisico na loja)
    2. HoraPedidoItem -> HoraPedido.loja_destino_id (chassi prometido)
    3. HoraNfEntradaItem -> HoraNfEntrada.loja_destino_id (chassi faturado)
    4. HoraVendaItem -> HoraVenda.loja_id (chassi vendido — pode ser NULL)

    Returns:
        None se admin (sem filtro — caller deve pular o `.in_(subq)`).
        Subquery sempre-vazia se permitidas=[] (bloqueia tudo).
        Subquery com chassis acessiveis caso contrario.

    Uso:
        subq = chassis_acessiveis_subquery(lojas_permitidas)
        if subq is not None:
            query = query.filter(HoraMoto.numero_chassi.in_(subq))
    """
    if lojas_permitidas is None:
        return None

    from app import db
    from app.hora.models import (
        HoraMotoEvento, HoraNfEntrada, HoraNfEntradaItem,
        HoraPedido, HoraPedidoItem, HoraVenda, HoraVendaItem,
    )

    if not lojas_permitidas:
        # Subquery sempre vazia (filtra tudo fora). Reusa a mesma coluna
        # (numero_chassi) que o caller usa em `.in_()` para evitar mismatch
        # de tipo. Filtro `id == -1` nunca matcha (id e PK > 0).
        return db.session.query(HoraMotoEvento.numero_chassi).filter(
            HoraMotoEvento.id == -1,
        ).subquery()

    chassis_evento = db.session.query(HoraMotoEvento.numero_chassi).filter(
        HoraMotoEvento.loja_id.in_(lojas_permitidas),
    )
    chassis_pedido = (
        db.session.query(HoraPedidoItem.numero_chassi)
        .join(HoraPedido, HoraPedidoItem.pedido_id == HoraPedido.id)
        .filter(
            HoraPedido.loja_destino_id.in_(lojas_permitidas),
            HoraPedidoItem.numero_chassi.isnot(None),
        )
    )
    chassis_nf = (
        db.session.query(HoraNfEntradaItem.numero_chassi)
        .join(HoraNfEntrada, HoraNfEntradaItem.nf_id == HoraNfEntrada.id)
        .filter(
            HoraNfEntrada.loja_destino_id.in_(lojas_permitidas),
            HoraNfEntradaItem.numero_chassi.isnot(None),
        )
    )
    chassis_venda = (
        db.session.query(HoraVendaItem.numero_chassi)
        .join(HoraVenda, HoraVendaItem.venda_id == HoraVenda.id)
        .filter(
            HoraVenda.loja_id.in_(lojas_permitidas),
            HoraVendaItem.numero_chassi.isnot(None),
        )
    )
    return chassis_evento.union(
        chassis_pedido, chassis_nf, chassis_venda,
    ).subquery()


def chassi_acessivel(numero_chassi: str, lojas_permitidas: List[int]) -> bool:
    """Versao pontual (1 chassi) — para uso em rotas de detalhe.

    Retorna True se o chassi tem evento OU pedido/NF entrada/venda em alguma
    loja permitida. Para listagens (N chassis) use `chassis_acessiveis_subquery`.

    Pre-condicao: caller deve ter checado que `lojas_permitidas is not None`
    (admin nao chama este helper).
    """
    if not lojas_permitidas:
        return False

    from app import db
    from app.hora.models import (
        HoraMotoEvento, HoraNfEntrada, HoraNfEntradaItem,
        HoraPedido, HoraPedidoItem, HoraVenda, HoraVendaItem,
    )

    chassi = numero_chassi.strip().upper()

    if db.session.query(HoraMotoEvento.id).filter(
        HoraMotoEvento.numero_chassi == chassi,
        HoraMotoEvento.loja_id.in_(lojas_permitidas),
    ).first():
        return True

    if db.session.query(HoraPedidoItem.id).join(
        HoraPedido, HoraPedidoItem.pedido_id == HoraPedido.id,
    ).filter(
        HoraPedidoItem.numero_chassi == chassi,
        HoraPedido.loja_destino_id.in_(lojas_permitidas),
    ).first():
        return True

    if db.session.query(HoraNfEntradaItem.id).join(
        HoraNfEntrada, HoraNfEntradaItem.nf_id == HoraNfEntrada.id,
    ).filter(
        HoraNfEntradaItem.numero_chassi == chassi,
        HoraNfEntrada.loja_destino_id.in_(lojas_permitidas),
    ).first():
        return True

    if db.session.query(HoraVendaItem.id).join(
        HoraVenda, HoraVendaItem.venda_id == HoraVenda.id,
    ).filter(
        HoraVendaItem.numero_chassi == chassi,
        HoraVenda.loja_id.in_(lojas_permitidas),
    ).first():
        return True

    return False

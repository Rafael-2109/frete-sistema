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

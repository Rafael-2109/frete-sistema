# app/integracoes/tagplus/services/notificacao_whatsapp_service.py
"""Serviço de notificação WhatsApp para pedido/NF do TagPlus.

Processamento assíncrono em Thread(daemon=False), espelhando o padrão do
WhatsApp bot (app/whatsapp/services.py: R1 thread non-daemon, R2 commit retry,
R3 re-fetch, R5 cleanup no finally). Best-effort: falhas degradam e ficam no
registro tagplus_notificacao_whatsapp.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import func, or_

logger = logging.getLogger(__name__)

DELAYS_BUSCA = [1, 3, 5]


def _resolver_vendedor(nome: Optional[str]):
    """Resolve o nome do vendedor (TagPlus) -> Usuario autorizado no WhatsApp.

    Match case-insensitive por `vendedor_vinculado` OU `nome`, exigindo
    `whatsapp_autorizado=True`, `status='ativo'` e `telefone` preenchido.
    Retorna o Usuario ou None (fallback só-grupo).
    """
    if not nome or not nome.strip():
        return None
    from app.auth.models import Usuario

    alvo = nome.strip().lower()
    return (
        Usuario.query
        .filter(Usuario.whatsapp_autorizado.is_(True))
        .filter(Usuario.status == 'ativo')
        .filter(Usuario.telefone.isnot(None))
        .filter(or_(
            func.lower(Usuario.vendedor_vinculado) == alvo,
            func.lower(Usuario.nome) == alvo,
        ))
        .first()
    )

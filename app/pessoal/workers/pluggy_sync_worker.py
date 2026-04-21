"""Worker RQ para sync assincrono Pluggy.

Funcoes chamadas via enqueue_job():
    - processar_item_criado(pluggy_item_id, client_user_id) — pos-webhook/onSuccess
    - sync_diario_todos_items() — cron diario 06:00
"""
from __future__ import annotations

import logging

from app import create_app
from app.pessoal.services.pluggy_sync_service import (
    sincronizar_item,
    sync_all_active_items,
)

logger = logging.getLogger(__name__)


def _com_app_context(func, *args, **kwargs):
    """Worker RQ roda fora de Flask app context. Encapsula manualmente."""
    app = create_app()
    with app.app_context():
        return func(*args, **kwargs)


def processar_item_criado(pluggy_item_id: str, client_user_id: str) -> dict:
    """Job: chamado apos onSuccess do widget ou webhook item/created.

    Aguarda sync inicial completar (ALERTA 7) e popula stg.
    """
    logger.info(f"[worker] processar_item_criado {pluggy_item_id} user={client_user_id}")
    return _com_app_context(
        sincronizar_item, pluggy_item_id, client_user_id=client_user_id, aguardar=True,
    )


def processar_item_atualizado(pluggy_item_id: str) -> dict:
    """Job: chamado apos webhook item/updated. Sync sem polling (dados ja prontos)."""
    logger.info(f"[worker] processar_item_atualizado {pluggy_item_id}")
    return _com_app_context(sincronizar_item, pluggy_item_id, aguardar=False)


def sync_diario_todos_items() -> dict:
    """Job: cron diario que sincroniza todos os items ativos."""
    logger.info("[worker] sync_diario_todos_items start")
    return _com_app_context(sync_all_active_items)

"""Sync service Pluggy — popula tabelas staging (Fase 1, sem tocar PessoalTransacao).

Fluxo:
    1. sincronizar_item(pluggy_item_id) — poll /items/{id} ate status=UPDATED
    2. Lista /accounts?itemId=X e upsert em pessoal_pluggy_accounts
    3. Para cada account, itera /transactions com janela de 12 meses
    4. Upsert em pessoal_pluggy_transacoes_stg via pluggy_transaction_id UNIQUE

Nao converte formato. Nao cria PessoalTransacao. Trabalho do adapter (Fase 3).

ALERTA 7 (webhook dispara antes dos dados): retry com backoff quando
execution_status=UPDATING.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import db
from app.pessoal.models import (
    PessoalPluggyAccount,
    PessoalPluggyItem,
    PessoalPluggyTransacaoStg,
)
from app.pessoal.services.pluggy_client import PluggyClientError, get_pluggy_client
from app.utils.json_helpers import sanitize_for_json
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


POLL_INTERVAL_SEC = 5
POLL_MAX_ATTEMPTS = 24       # 24 * 5s = 2 min total
HISTORICO_MESES = 12         # max suportado pelo Pluggy


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _parse_iso(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            v = value.rstrip("Z")
            return datetime.fromisoformat(v)
        except ValueError:
            return None
    return None


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


# ----------------------------------------------------------------------
# Item
# ----------------------------------------------------------------------
def criar_ou_atualizar_item(
    pluggy_item_id: str,
    client_user_id: str,
    payload: Optional[dict] = None,
) -> PessoalPluggyItem:
    """Upsert em pessoal_pluggy_items. Usa payload da API se fornecido."""
    item = PessoalPluggyItem.query.filter_by(pluggy_item_id=pluggy_item_id).first()

    if payload is None:
        client = get_pluggy_client()
        payload = client.get_item(pluggy_item_id)

    connector = payload.get("connector") or {}
    campos = {
        "client_user_id": client_user_id,
        "connector_id": connector.get("id") or 0,
        "connector_name": connector.get("name"),
        "status": payload.get("status") or "UPDATING",
        "execution_status": payload.get("executionStatus"),
        "consent_expires_at": _parse_iso(payload.get("consentExpiresAt")),
        "payload_raw": sanitize_for_json(payload),
    }

    if item is None:
        item = PessoalPluggyItem(pluggy_item_id=pluggy_item_id, **campos)
        db.session.add(item)
        logger.info(f"Criado PessoalPluggyItem {pluggy_item_id} user={client_user_id}")
    else:
        for k, v in campos.items():
            setattr(item, k, v)

    db.session.commit()
    return item


def aguardar_item_pronto(
    pluggy_item_id: str, max_attempts: int = POLL_MAX_ATTEMPTS,
) -> dict:
    """Polla /items/{id} ate status != UPDATING. Retorna payload final."""
    client = get_pluggy_client()
    for attempt in range(1, max_attempts + 1):
        payload = client.get_item(pluggy_item_id)
        status = payload.get("status")
        exec_status = payload.get("executionStatus")
        logger.info(
            f"[poll {attempt}/{max_attempts}] item={pluggy_item_id} "
            f"status={status} exec={exec_status}"
        )
        if status and status != "UPDATING":
            return payload
        time.sleep(POLL_INTERVAL_SEC)
    logger.warning(f"Timeout aguardando item {pluggy_item_id} ficar pronto.")
    return client.get_item(pluggy_item_id)


# ----------------------------------------------------------------------
# Accounts
# ----------------------------------------------------------------------
def upsert_account(item_pk: int, account_payload: dict) -> PessoalPluggyAccount:
    pluggy_account_id = account_payload["id"]
    account = PessoalPluggyAccount.query.filter_by(
        pluggy_account_id=pluggy_account_id
    ).first()

    campos = {
        "pluggy_item_pk": item_pk,
        "type": account_payload.get("type"),
        "subtype": account_payload.get("subtype"),
        "number": account_payload.get("number"),
        "name": account_payload.get("name"),
        "marketing_name": account_payload.get("marketingName"),
        "owner_name": account_payload.get("owner"),
        "tax_number": account_payload.get("taxNumber"),
        "balance": _to_decimal(account_payload.get("balance")),
        "currency_code": account_payload.get("currencyCode") or "BRL",
        "bank_data": sanitize_for_json(account_payload.get("bankData")),
        "credit_data": sanitize_for_json(account_payload.get("creditData")),
        "payload_raw": sanitize_for_json(account_payload),
    }

    if account is None:
        account = PessoalPluggyAccount(pluggy_account_id=pluggy_account_id, **campos)
        db.session.add(account)
    else:
        for k, v in campos.items():
            setattr(account, k, v)

    db.session.flush()
    return account


# ----------------------------------------------------------------------
# Transactions
# ----------------------------------------------------------------------
def upsert_transacao_stg(account_pk: int, tx_payload: dict) -> bool:
    """Upsert de transacao stg por pluggy_transaction_id UNIQUE.

    Retorna True se inseriu nova, False se atualizou existente.
    """
    tx_id = tx_payload["id"]
    visto_em = agora_utc_naive()

    valores = {
        "pluggy_account_pk": account_pk,
        "pluggy_transaction_id": tx_id,
        "date": _parse_iso(tx_payload.get("date")) or agora_utc_naive(),
        "description": tx_payload.get("description"),
        "description_raw": tx_payload.get("descriptionRaw"),
        "amount": _to_decimal(tx_payload.get("amount")) or Decimal("0"),
        "amount_in_account_currency": _to_decimal(
            tx_payload.get("amountInAccountCurrency")
        ),
        "currency_code": tx_payload.get("currencyCode"),
        "balance": _to_decimal(tx_payload.get("balance")),
        "category": tx_payload.get("category"),
        "category_id": tx_payload.get("categoryId"),
        "category_translated": tx_payload.get("categoryTranslated"),
        "provider_code": tx_payload.get("providerCode"),
        "provider_id": tx_payload.get("providerId"),
        "type": tx_payload.get("type"),
        "status": tx_payload.get("status"),
        "operation_type": tx_payload.get("operationType"),
        "payment_data": sanitize_for_json(tx_payload.get("paymentData")),
        "credit_card_metadata": sanitize_for_json(tx_payload.get("creditCardMetadata")),
        "merchant": sanitize_for_json(tx_payload.get("merchant")),
        "payload_raw": sanitize_for_json(tx_payload),
        "visto_em_sync_em": visto_em,
        "atualizado_em": visto_em,
    }

    stmt = pg_insert(PessoalPluggyTransacaoStg.__table__).values(**valores)
    # Ao re-sincronizar, atualizamos status/balance/description_raw pois Pluggy
    # pode enriquecer dados (PENDING -> POSTED).
    update_dict = {
        k: stmt.excluded[k] for k in (
            "description", "description_raw", "amount", "balance",
            "category", "category_id", "category_translated", "provider_code",
            "provider_id", "type", "status", "operation_type",
            "payment_data", "credit_card_metadata", "merchant",
            "payload_raw", "visto_em_sync_em", "atualizado_em",
        )
    }
    # Campo de controle status_processamento NAO e tocado no update.
    stmt = stmt.on_conflict_do_update(
        index_elements=["pluggy_transaction_id"],
        set_=update_dict,
    )
    db.session.execute(stmt)
    return True


def sincronizar_transacoes_conta(
    account: PessoalPluggyAccount,
    meses_historico: int = HISTORICO_MESES,
) -> dict[str, int]:
    """Sincroniza todas as transacoes de uma conta dentro da janela."""
    client = get_pluggy_client()
    hoje = datetime.utcnow().date()
    from_date = (hoje - timedelta(days=30 * meses_historico)).isoformat()
    to_date = hoje.isoformat()

    total = 0
    logger.info(
        f"Sync transacoes account_id={account.pluggy_account_id} "
        f"from={from_date} to={to_date}"
    )

    try:
        for tx in client.iter_transactions(
            account.pluggy_account_id,
            from_date=from_date,
            to_date=to_date,
        ):
            upsert_transacao_stg(account.id, tx)
            total += 1
            # Commit em lotes de 200
            if total % 200 == 0:
                db.session.commit()
                logger.info(f"  ... {total} transacoes commited")
    except PluggyClientError as exc:
        logger.error(f"Erro ao sincronizar account {account.pluggy_account_id}: {exc}")
        db.session.rollback()
        raise

    db.session.commit()
    logger.info(f"Sync account {account.pluggy_account_id} concluido: {total} transacoes")
    return {"account_id": account.pluggy_account_id, "total": total}


def sincronizar_item(
    pluggy_item_id: str,
    client_user_id: Optional[str] = None,
    aguardar: bool = True,
) -> dict:
    """Sincronizacao completa de um item: polling + accounts + transactions.

    Args:
        pluggy_item_id: UUID Pluggy do item
        client_user_id: usado apenas em primeira sincronizacao (criacao do Item local)
        aguardar: se True, polla /items/{id} ate ficar UPDATED (ALERTA 7)
    """
    logger.info(f"Iniciando sync item {pluggy_item_id} user={client_user_id} aguardar={aguardar}")

    # 1. Garantir Item local
    item = PessoalPluggyItem.query.filter_by(pluggy_item_id=pluggy_item_id).first()
    if item is None and client_user_id:
        item = criar_ou_atualizar_item(pluggy_item_id, client_user_id)
    elif item is None:
        raise ValueError(
            f"Item {pluggy_item_id} nao existe localmente e client_user_id nao foi fornecido."
        )

    # 2. Aguardar item ficar UPDATED (ALERTA 7)
    payload = aguardar_item_pronto(pluggy_item_id) if aguardar else get_pluggy_client().get_item(pluggy_item_id)

    # 3. Atualizar estado local
    item = criar_ou_atualizar_item(
        pluggy_item_id, item.client_user_id, payload=payload,
    )
    if payload.get("status") == "LOGIN_ERROR":
        item.erro_mensagem = str(payload.get("error") or "LOGIN_ERROR")
        db.session.commit()
        logger.error(f"Item {pluggy_item_id} em LOGIN_ERROR — abortando sync")
        return {"item_id": pluggy_item_id, "status": "LOGIN_ERROR",
                "accounts": 0, "transactions": 0}

    # 4. Accounts
    client = get_pluggy_client()
    accounts_payload = client.list_accounts(pluggy_item_id)
    accounts_criadas = []
    for acc_payload in accounts_payload:
        account = upsert_account(item.id, acc_payload)
        accounts_criadas.append(account)
    db.session.commit()
    logger.info(f"Item {pluggy_item_id}: {len(accounts_criadas)} accounts sincronizadas")

    # 5. Transacoes por account
    total_tx = 0
    resultado_por_account = []
    for account in accounts_criadas:
        r = sincronizar_transacoes_conta(account)
        total_tx += r["total"]
        resultado_por_account.append(r)

    # 6. Marcar ultimo_sync
    item.ultimo_sync = agora_utc_naive()
    db.session.commit()

    return {
        "item_id": pluggy_item_id,
        "status": item.status,
        "accounts": len(accounts_criadas),
        "transactions": total_tx,
        "per_account": resultado_por_account,
    }


# ----------------------------------------------------------------------
# Entry points (worker)
# ----------------------------------------------------------------------
def sync_all_active_items() -> dict:
    """Job RQ diario: sincroniza todos os items ativos (UPDATED/OUTDATED)."""
    items = PessoalPluggyItem.query.filter(
        PessoalPluggyItem.status.in_(["UPDATED", "OUTDATED"])
    ).all()

    resultados = []
    for item in items:
        try:
            r = sincronizar_item(item.pluggy_item_id, aguardar=False)
            resultados.append(r)
        except Exception as exc:
            logger.exception(f"Falha no sync item {item.pluggy_item_id}: {exc}")
            resultados.append({"item_id": item.pluggy_item_id, "erro": str(exc)})

    return {"total_items": len(items), "resultados": resultados}

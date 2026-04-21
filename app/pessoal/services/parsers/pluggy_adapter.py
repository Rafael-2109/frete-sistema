"""Adapter Pluggy → TransacaoRaw.

Converte linhas de pessoal_pluggy_transacoes_stg para TransacaoRaw (estrutura
compartilhada com parsers CSV/OFX). Implementa os ALERTAS 1-6 da pesquisa:

ALERTA 1: sinal de amount em CREDIT_CARD e INVERSO (positivo=compra).
ALERTA 2: pagamento de fatura aparece 2x (BANK + CREDIT) — flaga eh_pagamento_cartao.
ALERTA 3: dedup via pluggy_transaction_id (PENDING→POSTED mantem mesmo id).
ALERTA 4: historico = descriptionRaw (compat regras CSV); descricao = description.
ALERTA 5: CPF/CNPJ ja vem estruturado em paymentData — so normaliza digitos.
ALERTA 6: categoryId nao mapeia 1:1 — envia sugestao, categorizacao manual decide.

O adapter NAO grava em PessoalTransacao. Retorna TransacaoRaw + metadata extra
(`pluggy_transaction_id`, `categoria_pluggy_id`, `operation_type`, `merchant_nome`).
Fase 4 consome essa estrutura para montar a transacao real.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from app.pessoal.models import PessoalPluggyAccount, PessoalPluggyTransacaoStg
from app.pessoal.services.parsers.base_parser import (
    TransacaoRaw, normalizar_historico,
)

logger = logging.getLogger(__name__)


# Padroes para identificar pagamento de fatura de cartao (ALERTA 2)
PADROES_PAGAMENTO_FATURA_BRADESCO = [
    r"PAGTO.*FATURA",
    r"PAGAMENTO.*CARTAO",
    r"PGTO.*CARTAO",
    r"BRADESCARD",
]


@dataclass
class TransacaoPluggyConvertida:
    """TransacaoRaw + metadata Pluggy adicional."""
    raw: TransacaoRaw
    # Metadata que nao cabe em TransacaoRaw original:
    pluggy_transaction_id: str = ""
    pluggy_account_id: str = ""
    categoria_pluggy_id: Optional[str] = None
    categoria_pluggy_descricao: Optional[str] = None  # PT se disponivel
    operation_type: Optional[str] = None
    merchant_nome: Optional[str] = None
    merchant_cnpj: Optional[str] = None
    # Status Pluggy original (POSTED|PENDING)
    status_pluggy: Optional[str] = None
    # Alertas detectados
    alertas: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _so_digitos(texto: Optional[str]) -> Optional[str]:
    """Remove tudo que nao e digito. Retorna None se resultado vazio."""
    if not texto:
        return None
    digitos = re.sub(r"\D", "", str(texto))
    if not digitos:
        return None
    # Validar tamanho CPF (11) ou CNPJ (14)
    if len(digitos) not in (11, 14):
        return None
    # Evitar sequencias repetidas (000..., 111...)
    if len(set(digitos)) == 1:
        return None
    return digitos


def _extrair_cpf_cnpj_payment_data(payment_data: Optional[dict]) -> Optional[str]:
    """Extrai CPF/CNPJ de paymentData.receiver ou .payer. Prioriza receiver."""
    if not payment_data or not isinstance(payment_data, dict):
        return None
    for chave in ("receiver", "payer"):
        parte = payment_data.get(chave)
        if not parte or not isinstance(parte, dict):
            continue
        doc = parte.get("documentNumber")
        if isinstance(doc, dict):
            val = _so_digitos(doc.get("value"))
            if val:
                return val
        elif isinstance(doc, str):
            val = _so_digitos(doc)
            if val:
                return val
    return None


def _split_agencia_conta(number: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Separa "0001/12345-0" em ("0001", "12345-0")."""
    if not number:
        return None, None
    if "/" in number:
        partes = number.split("/", 1)
        return partes[0].strip(), partes[1].strip()
    return None, number


def _eh_pagamento_fatura(historico: str, descricao: Optional[str]) -> bool:
    fonte = ((historico or "") + " " + (descricao or "")).upper()
    return any(re.search(p, fonte) for p in PADROES_PAGAMENTO_FATURA_BRADESCO)


def _to_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            v = value.rstrip("Z")
            return datetime.fromisoformat(v).date()
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
# Adapter principal
# ----------------------------------------------------------------------
def stg_to_transacao(
    stg: PessoalPluggyTransacaoStg,
    account: Optional[PessoalPluggyAccount] = None,
) -> TransacaoPluggyConvertida:
    """Converte 1 linha stg para TransacaoPluggyConvertida.

    Args:
        stg: registro staging
        account: opcional; se nao passado, busca via stg.account (relationship)

    Returns:
        TransacaoPluggyConvertida com TransacaoRaw e metadata Pluggy.
    """
    if account is None:
        account = stg.account
    if account is None:
        raise ValueError(f"Account nao encontrado para stg id={stg.id}")

    alertas: list[str] = []

    # -------------------------------------------------
    # ALERTA 4: historico = description_raw (compat regras)
    # -------------------------------------------------
    historico = stg.description_raw or stg.description or "(sem descricao)"
    descricao = stg.description if stg.description != historico else None

    # -------------------------------------------------
    # ALERTA 1: sinal de amount conforme tipo de conta
    # -------------------------------------------------
    amount = stg.amount or Decimal("0")
    valor_abs = abs(amount)

    if account.type == "BANK":
        # BANK: amount signed — positivo=entrada, negativo=saida
        # Pluggy tambem retorna campo type="CREDIT"/"DEBIT" que confirma
        tipo = "credito" if amount > 0 else "debito"
        # Cross-check com stg.type Pluggy
        if stg.type:
            esperado = "credito" if stg.type == "CREDIT" else "debito"
            if tipo != esperado:
                alertas.append(
                    f"BANK: sinal amount ({tipo}) diverge de type Pluggy "
                    f"({stg.type}). Prioriza sinal do amount."
                )
    elif account.type == "CREDIT":
        # CREDIT_CARD: INVERSO — positivo=compra(debito), negativo=estorno/pagamento(credito)
        tipo = "debito" if amount > 0 else "credito"
        alertas.append("CREDIT_CARD: sinal invertido aplicado (+amount=debito).")
    else:
        tipo = "debito"
        alertas.append(f"Account type desconhecido: {account.type}")

    # -------------------------------------------------
    # Saldo — BANK usa balance; CREDIT_CARD = NULL (decisao 5)
    # -------------------------------------------------
    if account.type == "BANK":
        saldo = stg.balance
    else:
        saldo = None

    # -------------------------------------------------
    # Parcelamento (cartao)
    # -------------------------------------------------
    parcela_atual = None
    parcela_total = None
    identificador_parcela = None
    valor_dolar = None
    if stg.credit_card_metadata and isinstance(stg.credit_card_metadata, dict):
        ccm = stg.credit_card_metadata
        parcela_atual = ccm.get("installmentNumber")
        parcela_total = ccm.get("totalInstallments")
        bill_id = ccm.get("billId")
        total_amount = ccm.get("totalAmount")
        if parcela_total and parcela_total > 1:
            # Identificador estavel baseado em billId + description + total
            identificador_parcela = (
                f"pluggy|{bill_id or 'nobill'}|{historico[:60]}|{total_amount or ''}"
            )

    # -------------------------------------------------
    # ALERTA 5: CPF/CNPJ estruturado
    # -------------------------------------------------
    cpf_cnpj = _extrair_cpf_cnpj_payment_data(stg.payment_data)
    if not cpf_cnpj and stg.merchant and isinstance(stg.merchant, dict):
        cpf_cnpj = _so_digitos(stg.merchant.get("cnpj"))

    # -------------------------------------------------
    # Merchant / operation_type
    # -------------------------------------------------
    merchant_nome = None
    merchant_cnpj = None
    if stg.merchant and isinstance(stg.merchant, dict):
        merchant_nome = stg.merchant.get("businessName") or stg.merchant.get("name")
        merchant_cnpj = _so_digitos(stg.merchant.get("cnpj"))

    # -------------------------------------------------
    # historico_completo enriquecido
    # -------------------------------------------------
    partes_hist = [normalizar_historico(historico)]
    if descricao:
        partes_hist.append(normalizar_historico(descricao))
    if merchant_nome:
        partes_hist.append(normalizar_historico(merchant_nome))
    if stg.payment_data and isinstance(stg.payment_data, dict):
        receiver = stg.payment_data.get("receiver") or {}
        nome_receiver = receiver.get("name")
        if nome_receiver and nome_receiver not in historico:
            partes_hist.append(normalizar_historico(nome_receiver))
    historico_completo = " | ".join(p for p in partes_hist if p)

    # -------------------------------------------------
    # Cartao: titular + digitos
    # -------------------------------------------------
    titular_cartao = None
    ultimos_digitos_cartao = None
    if account.type == "CREDIT":
        titular_cartao = account.owner_name
        ultimos_digitos_cartao = account.number

    # -------------------------------------------------
    # Data
    # -------------------------------------------------
    data_transacao = _to_date(stg.date) or date.today()

    # -------------------------------------------------
    # TransacaoRaw
    # -------------------------------------------------
    raw = TransacaoRaw(
        data=data_transacao,
        historico=historico,
        descricao=descricao,
        historico_completo=historico_completo,
        documento=stg.provider_code,
        valor=valor_abs,
        tipo=tipo,
        saldo=saldo,
        valor_dolar=valor_dolar,
        parcela_atual=parcela_atual,
        parcela_total=parcela_total,
        identificador_parcela=identificador_parcela,
        titular_cartao=titular_cartao,
        ultimos_digitos_cartao=ultimos_digitos_cartao,
        eh_provisoria=(stg.status == "PENDING"),
    )

    # -------------------------------------------------
    # ALERTA 2: pagamento de fatura (heuristica)
    # -------------------------------------------------
    if account.type == "BANK" and _eh_pagamento_fatura(historico, descricao):
        alertas.append("BANK: detectado pagamento de fatura de cartao (heuristica).")

    # -------------------------------------------------
    # CPF/CNPJ gotcha — o campo esta em TransacaoRaw? Nao, mas e salvo em
    # PessoalTransacao.cpf_cnpj_parte no merge (Fase 4). Por ora so incluir
    # na metadata para dry-run.
    # -------------------------------------------------
    convertida = TransacaoPluggyConvertida(
        raw=raw,
        pluggy_transaction_id=stg.pluggy_transaction_id,
        pluggy_account_id=account.pluggy_account_id,
        categoria_pluggy_id=stg.category_id,
        categoria_pluggy_descricao=stg.category_translated or stg.category,
        operation_type=stg.operation_type,
        merchant_nome=merchant_nome,
        merchant_cnpj=merchant_cnpj,
        status_pluggy=stg.status,
        alertas=alertas,
    )

    # Guardar CPF/CNPJ como atributo dinamico (nao quebra TransacaoRaw)
    convertida.cpf_cnpj = cpf_cnpj  # type: ignore[attr-defined]
    return convertida

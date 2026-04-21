"""Merge service — converte stg APROVADAS em PessoalTransacao reais.

Fluxo:
    1. Vincula PessoalPluggyAccount -> PessoalConta (auto-match ou cria nova)
    2. Para cada stg com status_processamento='APROVADO':
       - Converte via adapter
       - Tenta dedup: primeiro por pluggy_transaction_id, depois por hash_transacao
       - Cria/atualiza PessoalTransacao com origem_import='pluggy'
       - Aplica categorizacao (reusa categorizacao_service)
       - Marca stg como MIGRADO

Nao reprocessa stg ja MIGRADO. Nao toca stg REPROVADO/IGNORAR.
"""
from __future__ import annotations

import logging
from typing import Optional

from app import db
from app.pessoal.models import (
    PessoalConta,
    PessoalPluggyAccount,
    PessoalPluggyItem,
    PessoalPluggyTransacaoStg,
    PessoalTransacao,
)
from app.pessoal.services.categorizacao_service import (
    atribuir_membro, categorizar_transacao,
)
from app.pessoal.services.parsers.base_parser import gerar_hash_transacao
from app.pessoal.services.parsers.pluggy_adapter import (
    _split_agencia_conta, stg_to_transacao,
)
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Vinculo PluggyAccount <-> PessoalConta
# ----------------------------------------------------------------------
def vincular_account_em_conta(
    pluggy_account: PessoalPluggyAccount,
    conta_pessoal: Optional[PessoalConta] = None,
    auto_criar: bool = True,
) -> PessoalConta:
    """Vincula PessoalPluggyAccount a PessoalConta.

    Se `conta_pessoal` fornecida: vincula direto.
    Se nao: tenta match automatico por agencia/conta (BANK) ou digitos (CREDIT).
    Se auto_criar=True e nao achar: cria nova PessoalConta.
    """
    # Ja vinculada?
    if pluggy_account.conta_pessoal_id and not conta_pessoal:
        existente = db.session.get(PessoalConta, pluggy_account.conta_pessoal_id)
        if existente:
            return existente

    if conta_pessoal:
        pluggy_account.conta_pessoal_id = conta_pessoal.id
        pluggy_account.conta_vinculada_em = agora_utc_naive()
        conta_pessoal.pluggy_account_id = pluggy_account.pluggy_account_id
        conta_pessoal.pluggy_item_pk = pluggy_account.pluggy_item_pk
        db.session.commit()
        return conta_pessoal

    # Auto-match
    if pluggy_account.type == "BANK":
        agencia, numero_conta = _split_agencia_conta(pluggy_account.number)
        q = PessoalConta.query.filter_by(tipo="conta_corrente", banco="bradesco")
        if agencia:
            q = q.filter_by(agencia=agencia)
        if numero_conta:
            q = q.filter_by(numero_conta=numero_conta)
        candidato = q.first()
    elif pluggy_account.type == "CREDIT":
        candidato = (
            PessoalConta.query
            .filter_by(tipo="cartao_credito",
                       ultimos_digitos_cartao=pluggy_account.number)
            .first()
        )
    else:
        candidato = None

    if candidato:
        candidato.pluggy_account_id = pluggy_account.pluggy_account_id
        candidato.pluggy_item_pk = pluggy_account.pluggy_item_pk
        pluggy_account.conta_pessoal_id = candidato.id
        pluggy_account.conta_vinculada_em = agora_utc_naive()
        db.session.commit()
        logger.info(
            f"PluggyAccount {pluggy_account.pluggy_account_id} vinculada automaticamente "
            f"a PessoalConta #{candidato.id} ({candidato.nome})"
        )
        return candidato

    if not auto_criar:
        raise ValueError(
            f"Nenhuma PessoalConta encontrada para PluggyAccount "
            f"{pluggy_account.pluggy_account_id} e auto_criar=False"
        )

    # Criar nova
    if pluggy_account.type == "BANK":
        agencia, numero_conta = _split_agencia_conta(pluggy_account.number)
        nova = PessoalConta(
            nome=pluggy_account.marketing_name or pluggy_account.name or "Conta Bradesco",
            tipo="conta_corrente",
            banco="bradesco",
            agencia=agencia,
            numero_conta=numero_conta,
            pluggy_account_id=pluggy_account.pluggy_account_id,
            pluggy_item_pk=pluggy_account.pluggy_item_pk,
        )
    else:
        nova = PessoalConta(
            nome=pluggy_account.marketing_name or pluggy_account.name or "Cartao Bradesco",
            tipo="cartao_credito",
            banco="bradesco",
            ultimos_digitos_cartao=pluggy_account.number,
            pluggy_account_id=pluggy_account.pluggy_account_id,
            pluggy_item_pk=pluggy_account.pluggy_item_pk,
        )

    db.session.add(nova)
    db.session.flush()
    pluggy_account.conta_pessoal_id = nova.id
    pluggy_account.conta_vinculada_em = agora_utc_naive()
    db.session.commit()
    logger.info(f"PessoalConta criada automaticamente #{nova.id} ({nova.nome})")
    return nova


# ----------------------------------------------------------------------
# Merge individual
# ----------------------------------------------------------------------
def _buscar_existente_por_pluggy_id(pluggy_tx_id: str) -> Optional[PessoalTransacao]:
    return PessoalTransacao.query.filter_by(pluggy_transaction_id=pluggy_tx_id).first()


def _buscar_existente_por_hash(hash_t: str) -> Optional[PessoalTransacao]:
    return PessoalTransacao.query.filter_by(hash_transacao=hash_t).first()


def migrar_stg_para_transacao(
    stg: PessoalPluggyTransacaoStg,
) -> tuple[Optional[PessoalTransacao], str]:
    """Migra 1 stg para PessoalTransacao.

    Returns:
        (transacao, acao): acao in {'criada', 'atualizada', 'duplicada_skip', 'erro'}
    """
    if stg.status_processamento != "APROVADO":
        return None, f"status={stg.status_processamento} (nao migra)"

    account = stg.account
    if account is None or account.conta_pessoal_id is None:
        return None, "account nao vinculada a PessoalConta"

    conta_pessoal = db.session.get(PessoalConta, account.conta_pessoal_id)
    if conta_pessoal is None:
        return None, "conta_pessoal nao encontrada"

    # 1. Dedup por pluggy_transaction_id
    existente = _buscar_existente_por_pluggy_id(stg.pluggy_transaction_id)

    # 2. Adapter
    try:
        convertida = stg_to_transacao(stg, account=account)
    except Exception as exc:
        logger.exception(f"Erro adapter stg={stg.id}: {exc}")
        return None, f"adapter_erro: {exc}"

    raw = convertida.raw

    # 3. Hash (dedup cross-source com CSV)
    hash_t = gerar_hash_transacao(
        conta_pessoal.id, raw.data, raw.historico, raw.valor,
        raw.tipo, raw.documento or "", sequencia=0,
    )

    if existente is None:
        # Tentar dedup por hash (pode ja ter sido importada via CSV)
        existente = _buscar_existente_por_hash(hash_t)
        if existente:
            # Atualiza metadados Pluggy na transacao ja existente (CSV)
            existente.pluggy_transaction_id = stg.pluggy_transaction_id
            existente.origem_import = "pluggy"
            existente.operation_type = convertida.operation_type
            existente.merchant_nome = convertida.merchant_nome
            existente.merchant_cnpj = convertida.merchant_cnpj
            existente.categoria_pluggy_id = convertida.categoria_pluggy_id
            existente.categoria_pluggy_sugerida = convertida.categoria_pluggy_descricao
            stg.transacao_pessoal_id = existente.id
            stg.status_processamento = "MIGRADO"
            stg.migrado_em = agora_utc_naive()
            stg.observacao_migracao = "vinculada a transacao existente (CSV) via hash"
            db.session.commit()
            return existente, "atualizada"

    if existente is not None:
        # Atualizar dados dinamicos (status PENDING->POSTED, saldo, etc)
        existente.saldo = raw.saldo
        existente.operation_type = convertida.operation_type
        existente.merchant_nome = convertida.merchant_nome
        existente.merchant_cnpj = convertida.merchant_cnpj
        existente.categoria_pluggy_id = convertida.categoria_pluggy_id
        existente.categoria_pluggy_sugerida = convertida.categoria_pluggy_descricao
        stg.transacao_pessoal_id = existente.id
        stg.status_processamento = "MIGRADO"
        stg.migrado_em = agora_utc_naive()
        stg.observacao_migracao = "atualizada (dedup por pluggy_transaction_id)"
        db.session.commit()
        return existente, "atualizada"

    # 4. Criar nova PessoalTransacao
    transacao = PessoalTransacao(
        importacao_id=None,  # Sem importacao CSV associada
        conta_id=conta_pessoal.id,
        data=raw.data,
        historico=raw.historico,
        descricao=raw.descricao,
        historico_completo=raw.historico_completo,
        documento=raw.documento,
        valor=raw.valor,
        tipo=raw.tipo,
        saldo=raw.saldo,
        valor_dolar=raw.valor_dolar,
        parcela_atual=raw.parcela_atual,
        parcela_total=raw.parcela_total,
        identificador_parcela=raw.identificador_parcela,
        cpf_cnpj_parte=getattr(convertida, "cpf_cnpj", None),
        hash_transacao=hash_t,
        pluggy_transaction_id=stg.pluggy_transaction_id,
        origem_import="pluggy",
        operation_type=convertida.operation_type,
        merchant_nome=convertida.merchant_nome,
        merchant_cnpj=convertida.merchant_cnpj,
        categoria_pluggy_id=convertida.categoria_pluggy_id,
        categoria_pluggy_sugerida=convertida.categoria_pluggy_descricao,
    )

    # PessoalTransacao.importacao_id NOT NULL — precisamos criar ou reutilizar
    # um registro de importacao "virtual" Pluggy. Reutiliza por item+account.
    importacao = _obter_ou_criar_importacao_pluggy(account)
    transacao.importacao_id = importacao.id

    db.session.add(transacao)
    db.session.flush()

    # 5. Categorizar usando pipeline existente
    try:
        resultado_cat = categorizar_transacao(transacao)
        transacao.categoria_id = resultado_cat.categoria_id
        transacao.regra_id = resultado_cat.regra_id
        transacao.categorizacao_auto = resultado_cat.categorizacao_auto
        transacao.categorizacao_confianca = resultado_cat.categorizacao_confianca
        transacao.excluir_relatorio = resultado_cat.excluir_relatorio
        transacao.eh_pagamento_cartao = resultado_cat.eh_pagamento_cartao
        transacao.eh_transferencia_propria = resultado_cat.eh_transferencia_propria
        transacao.status = resultado_cat.status

        # Heuristica ALERTA 2: se BANK e historico identifica pagamento de fatura
        if account.type == "BANK" and any(
            "pagamento de fatura" in a for a in convertida.alertas
        ):
            transacao.eh_pagamento_cartao = True

        # Atribuir membro (cartao: titular; CC: fuzzy)
        membro_id, membro_auto = atribuir_membro(
            transacao,
            titular_cartao=raw.titular_cartao,
            ultimos_digitos=raw.ultimos_digitos_cartao,
        )
        transacao.membro_id = membro_id
        transacao.membro_auto = membro_auto
    except Exception as exc:
        logger.exception(f"Erro categorizando tx={transacao.id}: {exc}")
        transacao.status = "PENDENTE"

    # 6. Marcar stg como MIGRADO
    stg.transacao_pessoal_id = transacao.id
    stg.status_processamento = "MIGRADO"
    stg.migrado_em = agora_utc_naive()
    stg.observacao_migracao = "criada via merge Pluggy"

    # Incrementar contador da importacao Pluggy
    importacao.linhas_importadas = (importacao.linhas_importadas or 0) + 1

    db.session.commit()
    return transacao, "criada"


def _obter_ou_criar_importacao_pluggy(account: PessoalPluggyAccount):
    """Cria registro agregador PessoalImportacao para conjunto de tx Pluggy.

    Uma importacao por dia de sync por conta (permite rastrear no historico).
    """
    from app.pessoal.models import PessoalImportacao
    hoje = agora_utc_naive().date()
    nome = f"Pluggy {account.pluggy_account_id[:8]} {hoje.isoformat()}"
    existente = (
        PessoalImportacao.query
        .filter_by(conta_id=account.conta_pessoal_id, nome_arquivo=nome)
        .first()
    )
    if existente:
        return existente
    tipo = "extrato_cc" if account.type == "BANK" else "fatura_cartao"
    nova = PessoalImportacao(
        conta_id=account.conta_pessoal_id,
        nome_arquivo=nome,
        tipo_arquivo=tipo,
        total_linhas=0,
        linhas_importadas=0,
        status="IMPORTADO",
        criado_por="pluggy_merge",
    )
    db.session.add(nova)
    db.session.flush()
    return nova


# ----------------------------------------------------------------------
# Merge em lote
# ----------------------------------------------------------------------
def merge_item(pluggy_item_pk: int, auto_vincular: bool = True) -> dict:
    """Migra todas as stg APROVADAS de um item para PessoalTransacao."""
    item = db.session.get(PessoalPluggyItem, pluggy_item_pk)
    if item is None:
        raise ValueError(f"Item nao encontrado: {pluggy_item_pk}")

    accounts = PessoalPluggyAccount.query.filter_by(
        pluggy_item_pk=pluggy_item_pk
    ).all()

    # 1. Vincular accounts -> PessoalConta
    if auto_vincular:
        for acc in accounts:
            if acc.conta_pessoal_id is None:
                try:
                    vincular_account_em_conta(acc, auto_criar=True)
                except Exception as exc:
                    logger.exception(
                        f"Erro vinculando account {acc.pluggy_account_id}: {exc}"
                    )

    # 2. Migrar stg APROVADAS
    criadas = 0
    atualizadas = 0
    erros = 0
    skips = 0

    for acc in accounts:
        stgs = (
            PessoalPluggyTransacaoStg.query
            .filter_by(pluggy_account_pk=acc.id, status_processamento="APROVADO")
            .order_by(PessoalPluggyTransacaoStg.date)
            .all()
        )
        for stg in stgs:
            try:
                _, acao = migrar_stg_para_transacao(stg)
                if acao == "criada":
                    criadas += 1
                elif acao == "atualizada":
                    atualizadas += 1
                else:
                    skips += 1
            except Exception as exc:
                logger.exception(f"Erro migrando stg={stg.id}: {exc}")
                erros += 1

    return {
        "item_id": item.pluggy_item_id,
        "accounts": len(accounts),
        "criadas": criadas,
        "atualizadas": atualizadas,
        "skips": skips,
        "erros": erros,
    }

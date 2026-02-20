# -*- coding: utf-8 -*-
"""
Serviço de Sincronização Bidirecional - Comprovantes ↔ Extrato
================================================================

Quando um comprovante de boleto é LANÇADO no Odoo, sincroniza o ExtratoItem
correspondente (via statement_line_id) para CONCILIADO.

Quando um ExtratoItem de SAIDA é CONCILIADO, sincroniza o ComprovantePagamentoBoleto
correspondente (via statement_line_id) como reconciliado.

REGRA: Sync é NÃO-BLOQUEANTE — falha no sync NÃO impede a operação principal.

Chave de ligação:
    ExtratoItem.statement_line_id == ComprovantePagamentoBoleto.odoo_statement_line_id

Autor: Sistema de Fretes
Data: 2026-02-08
"""

import logging
from typing import Optional

from app import db
from app.financeiro.parcela_utils import parcela_to_str
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


class ConciliacaoSyncService:
    """
    Sincroniza status de conciliação entre Comprovantes e Extrato.

    Ambos os métodos são idempotentes:
    - Se o destino já está no estado esperado, faz skip silencioso
    - Se o destino não existe (sem statement_line_id ou sem registro), faz skip silencioso
    """

    def sync_comprovante_para_extrato(self, comprovante_id: int) -> Optional[dict]:
        """
        Após comprovante LANÇADO → marca ExtratoItem correspondente como CONCILIADO.

        Busca ExtratoItem pelo statement_line_id compartilhado com o comprovante.
        Se encontrar e ainda não estiver CONCILIADO, atualiza status e metadados.

        Args:
            comprovante_id: ID do ComprovantePagamentoBoleto

        Returns:
            Dict com resultado ou None se nada a fazer
        """
        from app.financeiro.models_comprovante import (
            ComprovantePagamentoBoleto,
            LancamentoComprovante,
        )
        from app.financeiro.models import ExtratoItem

        comp = db.session.get(ComprovantePagamentoBoleto, comprovante_id)
        if not comp:
            logger.debug(f"[Sync] Comprovante {comprovante_id} não encontrado")
            return None

        if not comp.odoo_statement_line_id:
            logger.debug(
                f"[Sync] Comprovante {comprovante_id} sem odoo_statement_line_id — skip"
            )
            return None

        # Buscar ExtratoItem pelo statement_line_id
        extrato_item = ExtratoItem.query.filter_by(
            statement_line_id=comp.odoo_statement_line_id
        ).first()

        if not extrato_item:
            logger.info(
                f"[Sync] Nenhum ExtratoItem com statement_line_id="
                f"{comp.odoo_statement_line_id} — tentando criar sob demanda"
            )
            extrato_item = self._criar_extrato_item_sob_demanda(
                comp.odoo_statement_line_id, comp
            )
            if not extrato_item:
                logger.warning(
                    f"[Sync] Não foi possível criar ExtratoItem sob demanda "
                    f"para statement_line_id={comp.odoo_statement_line_id}"
                )
                return None

        if extrato_item.status == 'CONCILIADO':
            logger.debug(
                f"[Sync] ExtratoItem {extrato_item.id} já está CONCILIADO — skip"
            )
            return {'action': 'skip', 'reason': 'already_conciliado'}

        # Buscar lançamento LANCADO mais recente do comprovante para extrair IDs
        lanc = LancamentoComprovante.query.filter_by(
            comprovante_id=comprovante_id,
            status='LANCADO',
        ).order_by(LancamentoComprovante.lancado_em.desc()).first()

        # Atualizar ExtratoItem — CONCILIADO implica aprovado=True (invariante)
        extrato_item.status = 'CONCILIADO'
        extrato_item.aprovado = True
        extrato_item.aprovado_em = agora_utc_naive()
        extrato_item.aprovado_por = 'SYNC_COMPROVANTE'
        extrato_item.processado_em = agora_utc_naive()
        extrato_item.mensagem = f"Conciliado via comprovante #{comp.id}"

        if lanc:
            # Propagar IDs de reconciliação se disponíveis
            if lanc.odoo_full_reconcile_id and not extrato_item.full_reconcile_id:
                extrato_item.partial_reconcile_id = lanc.odoo_full_reconcile_id

            if lanc.odoo_full_reconcile_extrato_id and not extrato_item.full_reconcile_id:
                extrato_item.full_reconcile_id = lanc.odoo_full_reconcile_extrato_id

        # Atualizar titulo_pagar_id se disponível e ainda não preenchido
        if lanc and not extrato_item.titulo_pagar_id and not extrato_item.titulo_receber_id:
            # Tentar vincular o título do lançamento
            # NOTA: contas_a_pagar.parcela é varchar(10), lanc.parcela é integer
            from app.financeiro.models import ContasAPagar
            parcela_str = parcela_to_str(lanc.parcela)
            titulo_local = ContasAPagar.query.filter_by(
                titulo_nf=lanc.nf_numero,
                parcela=parcela_str,
            ).first() if lanc.nf_numero else None

            if titulo_local:
                extrato_item.titulo_pagar_id = titulo_local.id
                extrato_item.titulo_nf = lanc.nf_numero
                extrato_item.titulo_parcela = lanc.parcela
                # Preencher campos cache para exibição no template
                extrato_item.titulo_valor = titulo_local.valor_residual
                extrato_item.titulo_vencimento = titulo_local.vencimento
                extrato_item.titulo_cliente = titulo_local.raz_social_red or titulo_local.raz_social
                extrato_item.titulo_cnpj = titulo_local.cnpj

        # Backfill: preencher cache para itens que já têm FK mas cache vazio
        if extrato_item.titulo_pagar_id and not extrato_item.titulo_valor:
            from app.financeiro.models import ContasAPagar
            titulo_existente = db.session.get(ContasAPagar, extrato_item.titulo_pagar_id)
            if titulo_existente:
                extrato_item.titulo_valor = titulo_existente.valor_residual
                extrato_item.titulo_vencimento = titulo_existente.vencimento
                extrato_item.titulo_cliente = titulo_existente.raz_social_red or titulo_existente.raz_social
                extrato_item.titulo_cnpj = titulo_existente.cnpj

        # Atualizar estatísticas do lote (se existir)
        self._atualizar_estatisticas_lote(extrato_item.lote_id)

        # NÃO fazemos commit aqui — o caller (ComprovanteLancamentoService)
        # já faz commit após o lançamento completo
        db.session.flush()

        logger.info(
            f"[Sync] Comprovante {comprovante_id} → ExtratoItem {extrato_item.id} "
            f"marcado como CONCILIADO (statement_line={comp.odoo_statement_line_id})"
        )

        return {
            'action': 'synced',
            'extrato_item_id': extrato_item.id,
            'statement_line_id': comp.odoo_statement_line_id,
        }

    def sync_extrato_para_comprovante(self, extrato_item_id: int) -> Optional[dict]:
        """
        Após ExtratoItem CONCILIADO → marca ComprovantePagamentoBoleto como reconciliado.

        Busca ComprovantePagamentoBoleto pelo statement_line_id compartilhado.
        Se encontrar e ainda não estiver reconciliado, atualiza odoo_is_reconciled.

        Também verifica LancamentoComprovante associados e os sincroniza
        se o título no Odoo já estiver quitado.

        Args:
            extrato_item_id: ID do ExtratoItem

        Returns:
            Dict com resultado ou None se nada a fazer
        """
        from app.financeiro.models import ExtratoItem
        from app.financeiro.models_comprovante import (
            ComprovantePagamentoBoleto,
            LancamentoComprovante,
        )

        item = db.session.get(ExtratoItem, extrato_item_id)
        if not item:
            logger.debug(f"[Sync] ExtratoItem {extrato_item_id} não encontrado")
            return None

        if not item.statement_line_id:
            logger.debug(
                f"[Sync] ExtratoItem {extrato_item_id} sem statement_line_id — skip"
            )
            return None

        # Buscar comprovante pelo statement_line_id
        comp = ComprovantePagamentoBoleto.query.filter_by(
            odoo_statement_line_id=item.statement_line_id
        ).first()

        if not comp:
            logger.debug(
                f"[Sync] Nenhum comprovante com odoo_statement_line_id="
                f"{item.statement_line_id} — skip"
            )
            return None

        resultado = {
            'action': 'synced',
            'comprovante_id': comp.id,
            'statement_line_id': item.statement_line_id,
            'lancamentos_atualizados': 0,
        }

        # Marcar comprovante como reconciliado
        if not comp.odoo_is_reconciled:
            comp.odoo_is_reconciled = True
            logger.info(
                f"[Sync] ExtratoItem {extrato_item_id} → Comprovante {comp.id} "
                f"marcado como odoo_is_reconciled=True"
            )
        else:
            logger.debug(
                f"[Sync] Comprovante {comp.id} já estava odoo_is_reconciled=True"
            )

        # Verificar lançamentos do comprovante que ainda não foram LANCADOS
        lancamentos_pendentes = LancamentoComprovante.query.filter(
            LancamentoComprovante.comprovante_id == comp.id,
            LancamentoComprovante.status.in_(['PENDENTE', 'CONFIRMADO']),
        ).all()

        if lancamentos_pendentes:
            logger.info(
                f"[Sync] {len(lancamentos_pendentes)} lançamentos pendentes "
                f"no comprovante {comp.id} — verificando títulos no Odoo"
            )
            # Nota: NÃO tentamos lançar automaticamente.
            # Apenas logamos para visibilidade. O lançamento requer ação
            # explícita do usuário via ComprovanteLancamentoService.

        # NÃO fazemos commit aqui — o caller (ExtratoConciliacaoService)
        # já faz commit após conciliar o lote
        db.session.flush()

        return resultado

    def _atualizar_estatisticas_lote(self, lote_id: int) -> None:
        """
        Atualiza contadores do lote após sync.

        Recalcula linhas_conciliadas e linhas_erro baseado nos itens atuais.
        """
        if not lote_id:
            return

        from app.financeiro.models import ExtratoLote, ExtratoItem

        lote = db.session.get(ExtratoLote, lote_id)
        if not lote:
            return

        conciliados = ExtratoItem.query.filter_by(
            lote_id=lote_id, status='CONCILIADO'
        ).count()

        erros = ExtratoItem.query.filter_by(
            lote_id=lote_id, status='ERRO'
        ).count()

        lote.linhas_conciliadas = conciliados
        lote.linhas_erro = erros

    def _criar_extrato_item_sob_demanda(self, statement_line_id: int, comprovante):
        """
        Cria ExtratoItem sob demanda quando o auto-import não importou a linha.

        Busca dados da statement_line no Odoo, encontra ou cria um lote
        "Sync sob demanda", e cria o ExtratoItem com status PENDENTE
        (será marcado CONCILIADO pelo fluxo normal de sync_comprovante_para_extrato).

        Isso resolve o cenário onde pagamentos (amount < 0) não eram importados
        pelo scheduler automático (que importava apenas amount > 0 / entrada).

        REGRA: NÃO-BLOQUEANTE — falha aqui NÃO impede o lançamento do comprovante.

        Args:
            statement_line_id: ID da statement line no Odoo
            comprovante: ComprovantePagamentoBoleto associado

        Returns:
            ExtratoItem criado ou None se falhar
        """
        from datetime import datetime as dt
        from app.financeiro.models import ExtratoLote, ExtratoItem

        try:
            from app.odoo.utils.connection import get_odoo_connection
            conn = get_odoo_connection()
            if not conn.authenticate():
                logger.warning("[Sync] Falha ao autenticar Odoo para criar ExtratoItem sob demanda")
                return None

            # Buscar statement_line no Odoo
            linhas = conn.search_read(
                'account.bank.statement.line',
                [['id', '=', statement_line_id]],
                fields=[
                    'id', 'date', 'payment_ref', 'amount',
                    'journal_id', 'move_id', 'partner_id', 'partner_name',
                    'is_reconciled',
                ],
                limit=1,
            )

            if not linhas:
                logger.warning(f"[Sync] Statement line {statement_line_id} não encontrada no Odoo")
                return None

            linha = linhas[0]
            amount = linha.get('amount', 0)
            tipo_transacao = 'saida' if amount < 0 else 'entrada'

            # Extrair journal
            journal_raw = linha.get('journal_id')
            journal_id = journal_raw[0] if isinstance(journal_raw, (list, tuple)) else journal_raw
            journal_name = journal_raw[1] if isinstance(journal_raw, (list, tuple)) and len(journal_raw) > 1 else None

            # Buscar journal_code
            journal_code = None
            if journal_id:
                journals = conn.search_read(
                    'account.journal',
                    [['id', '=', journal_id]],
                    fields=['code', 'name'],
                    limit=1,
                )
                if journals:
                    journal_code = journals[0]['code']
                    journal_name = journals[0]['name']

            # Converter data
            data_transacao = linha.get('date')
            if isinstance(data_transacao, str):
                data_transacao = dt.strptime(data_transacao, '%Y-%m-%d').date()

            # Encontrar ou criar lote "sync sob demanda"
            mes_ano = agora_utc_naive().strftime('%Y-%m')
            nome_lote = f"Sync sob demanda {journal_code or 'N/A'} ({tipo_transacao}) {mes_ano}"

            lote = ExtratoLote.query.filter_by(nome=nome_lote).first()
            if not lote:
                lote = ExtratoLote(
                    nome=nome_lote,
                    journal_code=journal_code,
                    journal_id=journal_id,
                    tipo_transacao=tipo_transacao,
                    status='IMPORTADO',
                    criado_por='SYNC_SOB_DEMANDA',
                )
                db.session.add(lote)
                db.session.flush()

            # Extrair dados do payment_ref via ExtratoService
            from app.financeiro.services.extrato_service import ExtratoService
            extrato_svc = ExtratoService(connection=conn)
            payment_ref = linha.get('payment_ref', '') or ''
            tipo_trans, nome_pagador, cnpj_pagador = extrato_svc._extrair_dados_payment_ref(payment_ref)

            # Extrair move_id
            move_raw = linha.get('move_id')
            move_id = move_raw[0] if isinstance(move_raw, (list, tuple)) else move_raw
            move_name = move_raw[1] if isinstance(move_raw, (list, tuple)) and len(move_raw) > 1 else None

            # Extrair partner
            partner_raw = linha.get('partner_id')
            odoo_partner_id = partner_raw[0] if isinstance(partner_raw, (list, tuple)) else None
            odoo_partner_name = (
                partner_raw[1]
                if isinstance(partner_raw, (list, tuple)) and len(partner_raw) > 1
                else linha.get('partner_name')
            )

            # Criar ExtratoItem como PENDENTE (sync normal marcará CONCILIADO)
            item = ExtratoItem(
                lote_id=lote.id,
                statement_line_id=statement_line_id,
                move_id=move_id,
                move_name=move_name,
                data_transacao=data_transacao,
                valor=amount,
                payment_ref=payment_ref,
                tipo_transacao=tipo_trans,
                nome_pagador=nome_pagador,
                cnpj_pagador=cnpj_pagador,
                odoo_partner_id=odoo_partner_id,
                odoo_partner_name=odoo_partner_name,
                journal_id=journal_id,
                journal_code=journal_code,
                journal_name=journal_name,
                status_match='PENDENTE',
                status='PENDENTE',  # Será marcado CONCILIADO pelo fluxo normal em sync_comprovante_para_extrato
                mensagem=f'Criado sob demanda via comprovante #{comprovante.id}',
            )
            db.session.add(item)

            # Atualizar estatísticas do lote (item começa PENDENTE, será atualizado
            # para CONCILIADO pelo fluxo normal que chama _atualizar_estatisticas_lote)
            lote.total_linhas = (lote.total_linhas or 0) + 1
            lote.valor_total = (lote.valor_total or 0) + abs(amount)

            db.session.flush()

            logger.info(
                f"[Sync] ExtratoItem {item.id} criado sob demanda "
                f"(statement_line={statement_line_id}, valor={amount}, "
                f"journal={journal_code})"
            )

            return item

        except Exception as e:
            logger.error(
                f"[Sync] Erro ao criar ExtratoItem sob demanda para "
                f"statement_line {statement_line_id}: {e}",
                exc_info=True,
            )
            return None

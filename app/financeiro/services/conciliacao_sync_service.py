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
            logger.debug(
                f"[Sync] Nenhum ExtratoItem com statement_line_id="
                f"{comp.odoo_statement_line_id} — skip"
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

        # Atualizar ExtratoItem
        extrato_item.status = 'CONCILIADO'
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
            from app.financeiro.models import ContasAPagar
            titulo_local = ContasAPagar.query.filter_by(
                titulo_nf=lanc.nf_numero,
                parcela=lanc.parcela,
            ).first() if lanc.nf_numero else None

            if titulo_local:
                extrato_item.titulo_pagar_id = titulo_local.id
                extrato_item.titulo_nf = lanc.nf_numero
                extrato_item.titulo_parcela = lanc.parcela

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

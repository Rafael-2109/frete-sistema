# -*- coding: utf-8 -*-
"""
Serviço de Lançamento de Comprovantes no Odoo
==============================================

Implementa o fluxo CONFIRMADO → LANCADO:
1. Buscar LancamentoComprovante confirmado
2. Criar account.payment outbound no Odoo
3. Postar payment (action_post)
4. Reconciliar payment com título (account.move.line payable)
5. Reconciliar payment com extrato (account.bank.statement.line)
6. Atualizar status para LANCADO

Utiliza BaixaPagamentosService para as operações no Odoo.

Journal Sicoob:
- journal_id=10  → company_id=1 (NACOM GOYA - FB)
- journal_id=386 → company_id=5 (LA FAMIGLIA - LF)
- Regra: usar comprovante.odoo_journal_id (vem do match com statement_line)

Autor: Sistema de Fretes
Data: 2026-01-30
"""

import logging
from typing import Callable, Dict, List, Optional

from app import db
from app.financeiro.models_comprovante import (
    ComprovantePagamentoBoleto,
    LancamentoComprovante,
)
from app.utils.timezone import agora_brasil

logger = logging.getLogger(__name__)

# Fallback: journal Sicoob por company_id
# Usar apenas se comprovante.odoo_journal_id não estiver preenchido
SICOOB_JOURNAL_POR_COMPANY = {
    1: 10,    # NACOM GOYA - FB
    5: 386,   # LA FAMIGLIA - LF
}


class ComprovanteLancamentoService:
    """
    Serviço para lançar pagamentos no Odoo a partir de comprovantes confirmados.
    """

    def __init__(self):
        self._baixa_service = None
        self.estatisticas = {
            'total': 0,
            'sucesso': 0,
            'erros': 0,
        }

    @property
    def baixa_service(self):
        """Lazy init do BaixaPagamentosService."""
        if self._baixa_service is None:
            from app.financeiro.services.baixa_pagamentos_service import BaixaPagamentosService
            self._baixa_service = BaixaPagamentosService()
        return self._baixa_service

    # =========================================================================
    # LANÇAMENTO INDIVIDUAL (SÍNCRONO)
    # =========================================================================

    def lancar_no_odoo(self, lancamento_id: int, usuario: str) -> Dict:
        """
        Lança um comprovante confirmado no Odoo.

        Fluxo:
        1. Validar LancamentoComprovante (status=CONFIRMADO)
        2. Buscar ComprovantePagamentoBoleto associado
        3. Determinar journal_id
        4. Criar account.payment outbound
        5. Postar payment
        6. Buscar linhas do payment
        7. Reconciliar com título
        8. Reconciliar com extrato (se disponível)
        9. Atualizar status → LANCADO

        Args:
            lancamento_id: ID do LancamentoComprovante
            usuario: Nome do usuário que executou

        Returns:
            Dict com resultado da operação
        """
        lanc = db.session.get(LancamentoComprovante, lancamento_id)
        if not lanc:
            return {'sucesso': False, 'erro': f'Lançamento {lancamento_id} não encontrado'}

        if lanc.status != 'CONFIRMADO':
            return {
                'sucesso': False,
                'erro': f'Status inválido: {lanc.status}. Esperado: CONFIRMADO',
            }

        comp = lanc.comprovante
        if not comp:
            return {'sucesso': False, 'erro': 'Comprovante associado não encontrado'}

        # Validações obrigatórias
        erros_validacao = self._validar_dados(lanc, comp)
        if erros_validacao:
            return {'sucesso': False, 'erro': '; '.join(erros_validacao)}

        # Determinar journal_id
        journal_id = self._determinar_journal(comp, lanc)
        if not journal_id:
            return {
                'sucesso': False,
                'erro': (
                    f'Não foi possível determinar journal_id. '
                    f'comprovante.odoo_journal_id={comp.odoo_journal_id}, '
                    f'lancamento.odoo_company_id={lanc.odoo_company_id}'
                ),
            }

        logger.info(
            f"[Lancamento] Iniciando: lanc_id={lancamento_id}, "
            f"comp_id={comp.id}, partner_id={lanc.odoo_partner_id}, "
            f"journal_id={journal_id}, valor={comp.valor_pago}"
        )

        try:
            # 1. Criar payment outbound
            payment_id, payment_name = self.baixa_service.criar_pagamento_outbound(
                partner_id=lanc.odoo_partner_id,
                valor=float(comp.valor_pago),
                journal_id=journal_id,
                ref=lanc.odoo_move_name or f'NF {lanc.nf_numero}',
                data=comp.data_pagamento,
                company_id=lanc.odoo_company_id,
            )
            logger.info(f"  Payment criado: {payment_name} (ID: {payment_id})")

            lanc.odoo_payment_id = payment_id
            lanc.odoo_payment_name = payment_name

            # 2. Postar payment
            self.baixa_service.postar_pagamento(payment_id)
            logger.info("  Payment postado")

            # 3. Buscar linhas do payment
            linhas_payment = self.baixa_service.buscar_linhas_payment(payment_id)
            debit_line_id = linhas_payment.get('debit_line_id')
            credit_line_id = linhas_payment.get('credit_line_id')

            lanc.odoo_debit_line_id = debit_line_id
            lanc.odoo_credit_line_id = credit_line_id
            logger.info(f"  Linhas payment: debit={debit_line_id}, credit={credit_line_id}")

            # 4. Reconciliar payment com título
            if debit_line_id and lanc.odoo_move_line_id:
                self.baixa_service.reconciliar(debit_line_id, lanc.odoo_move_line_id)
                logger.info("  Reconciliado: payment ↔ título")

                # Buscar full_reconcile_id
                titulo_atualizado = self.baixa_service.buscar_titulo_por_id(lanc.odoo_move_line_id)
                if titulo_atualizado:
                    full_rec = titulo_atualizado.get('full_reconcile_id')
                    if full_rec:
                        lanc.odoo_full_reconcile_id = (
                            full_rec[0] if isinstance(full_rec, (list, tuple)) else full_rec
                        )

            # 5. Reconciliar payment com extrato (se comprovante tem vínculo Odoo)
            if credit_line_id and comp.odoo_statement_line_id and comp.odoo_move_id:
                debit_line_extrato = self.baixa_service.buscar_linha_debito_extrato(
                    comp.odoo_move_id
                )
                if debit_line_extrato:
                    self.baixa_service.reconciliar(credit_line_id, debit_line_extrato)
                    logger.info("  Reconciliado: payment ↔ extrato")

                    # Buscar full_reconcile_id do extrato
                    linha_extrato = self.baixa_service.connection.search_read(
                        'account.move.line',
                        [['id', '=', debit_line_extrato]],
                        fields=['full_reconcile_id'],
                        limit=1,
                    )
                    if linha_extrato and linha_extrato[0].get('full_reconcile_id'):
                        full_rec = linha_extrato[0]['full_reconcile_id']
                        lanc.odoo_full_reconcile_extrato_id = (
                            full_rec[0] if isinstance(full_rec, (list, tuple)) else full_rec
                        )
                else:
                    logger.warning(
                        f"  Linha de débito do extrato não encontrada para "
                        f"move_id={comp.odoo_move_id}. Reconciliação com extrato pulada."
                    )

            # 6. Atualizar status
            lanc.status = 'LANCADO'
            lanc.lancado_em = agora_brasil()
            lanc.lancado_por = usuario
            lanc.erro_lancamento = None

            # 7. Marcar comprovante como reconciliado
            comp.odoo_is_reconciled = True

            db.session.commit()

            logger.info(
                f"  ✅ Lançamento {lancamento_id} concluído! "
                f"Payment: {payment_name}, Reconcile: {lanc.odoo_full_reconcile_id}"
            )

            return {
                'sucesso': True,
                'lancamento_id': lancamento_id,
                'payment_id': payment_id,
                'payment_name': payment_name,
                'full_reconcile_id': lanc.odoo_full_reconcile_id,
                'full_reconcile_extrato_id': lanc.odoo_full_reconcile_extrato_id,
            }

        except Exception as e:
            logger.error(f"  ❌ Erro no lançamento {lancamento_id}: {e}", exc_info=True)

            # Salvar erro sem reverter status
            lanc.erro_lancamento = str(e)[:1000]
            db.session.commit()

            return {
                'sucesso': False,
                'lancamento_id': lancamento_id,
                'erro': str(e),
            }

    # =========================================================================
    # LANÇAMENTO BATCH
    # =========================================================================

    def lancar_batch(
        self,
        lancamento_ids: Optional[List[int]] = None,
        usuario: str = 'sistema',
        callback_progresso: Optional[Callable] = None,
    ) -> Dict:
        """
        Lança múltiplos comprovantes confirmados no Odoo.

        Args:
            lancamento_ids: IDs específicos ou None para todos CONFIRMADOS
            usuario: Nome do usuário
            callback_progresso: Callback(processados, total, ultimo_resultado)

        Returns:
            Dict com estatísticas consolidadas
        """
        # Buscar lançamentos confirmados
        if lancamento_ids:
            lancamentos = LancamentoComprovante.query.filter(
                LancamentoComprovante.id.in_(lancamento_ids),
                LancamentoComprovante.status == 'CONFIRMADO',
            ).all()
        else:
            lancamentos = LancamentoComprovante.query.filter_by(
                status='CONFIRMADO'
            ).all()

        total = len(lancamentos)
        self.estatisticas = {'total': total, 'sucesso': 0, 'erros': 0}

        logger.info(f"[Lancamento Batch] {total} lançamento(s) CONFIRMADO(s) a processar")

        detalhes = []

        for idx, lanc in enumerate(lancamentos, 1):
            resultado = self.lancar_no_odoo(lanc.id, usuario)

            if resultado.get('sucesso'):
                self.estatisticas['sucesso'] += 1
            else:
                self.estatisticas['erros'] += 1

            detalhes.append({
                'lancamento_id': lanc.id,
                'sucesso': resultado.get('sucesso', False),
                'payment_name': resultado.get('payment_name'),
                'erro': resultado.get('erro'),
            })

            if callback_progresso:
                callback_progresso(idx, total, resultado)

        logger.info(
            f"[Lancamento Batch] Concluído: "
            f"{self.estatisticas['sucesso']}/{total} sucesso, "
            f"{self.estatisticas['erros']} erros"
        )

        return {
            'sucesso': True,
            'estatisticas': self.estatisticas,
            'detalhes': detalhes,
        }

    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================

    def _validar_dados(
        self, lanc: LancamentoComprovante, comp: ComprovantePagamentoBoleto
    ) -> List[str]:
        """Valida dados necessários para o lançamento."""
        erros = []

        if not lanc.odoo_move_line_id:
            erros.append('Lançamento sem odoo_move_line_id (título não identificado)')

        if not lanc.odoo_partner_id:
            erros.append('Lançamento sem odoo_partner_id (fornecedor não identificado)')

        if not lanc.odoo_company_id:
            erros.append('Lançamento sem odoo_company_id (empresa não identificada)')

        if not comp.valor_pago:
            erros.append('Comprovante sem valor_pago')

        if not comp.data_pagamento:
            erros.append('Comprovante sem data_pagamento')

        return erros

    def _determinar_journal(
        self, comp: ComprovantePagamentoBoleto, lanc: LancamentoComprovante
    ) -> Optional[int]:
        """
        Determina o journal_id para o payment.

        Prioridade:
        1. comprovante.odoo_journal_id (vem do match com statement_line — mais confiável)
        2. Fallback: SICOOB_JOURNAL_POR_COMPANY[lancamento.odoo_company_id]
        """
        if comp.odoo_journal_id:
            return comp.odoo_journal_id

        return SICOOB_JOURNAL_POR_COMPANY.get(lanc.odoo_company_id)

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
from app.utils.timezone import agora_utc_naive

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
            # 0. Verificar se o título ainda tem saldo a pagar no Odoo
            titulo_check = self.baixa_service.buscar_titulo_por_id(lanc.odoo_move_line_id)
            if not titulo_check:
                return {
                    'sucesso': False,
                    'erro': f'Título {lanc.odoo_move_line_id} não encontrado no Odoo',
                }

            titulo_reconciliado = titulo_check.get('reconciled', False)
            titulo_residual = abs(float(titulo_check.get('amount_residual', 0)))

            if titulo_reconciliado or titulo_residual < 0.01:
                logger.info(
                    f"  Título {lanc.odoo_move_line_id} já quitado no Odoo "
                    f"(reconciled={titulo_reconciliado}, residual={titulo_residual:.2f}). "
                    f"Sincronizando sem criar payment."
                )
                return self._sincronizar_titulo_ja_quitado(lanc, comp, titulo_check, usuario)

            # 1. Determinar se há juros (valor_pago > valor do título)
            valor_pago = float(comp.valor_pago)
            valor_titulo = abs(float(lanc.odoo_valor_residual or lanc.odoo_valor_original or 0))
            juros = round(valor_pago - valor_titulo, 2) if valor_pago > valor_titulo + 0.01 else 0
            usou_writeoff = False

            if juros > 0:
                # 1a. COM JUROS: usar wizard com write-off
                logger.info(
                    f"  Juros detectado: valor_pago={valor_pago:.2f}, "
                    f"valor_titulo={valor_titulo:.2f}, juros={juros:.2f}"
                )
                payment_id, payment_name = self.baixa_service.criar_pagamento_outbound_com_writeoff(
                    titulo_id=lanc.odoo_move_line_id,
                    partner_id=lanc.odoo_partner_id,
                    valor_titulo=valor_titulo,
                    valor_juros=juros,
                    journal_id=journal_id,
                    ref=lanc.odoo_move_name or f'NF {lanc.nf_numero}',
                    data=comp.data_pagamento,
                    company_id=lanc.odoo_company_id,
                )
                usou_writeoff = True
                logger.info(f"  Payment com Write-Off criado: {payment_name} (ID: {payment_id})")
            else:
                # 1b. SEM JUROS: fluxo original (payment outbound simples)
                payment_id, payment_name = self.baixa_service.criar_pagamento_outbound(
                    partner_id=lanc.odoo_partner_id,
                    valor=valor_pago,
                    journal_id=journal_id,
                    ref=lanc.odoo_move_name or f'NF {lanc.nf_numero}',
                    data=comp.data_pagamento,
                    company_id=lanc.odoo_company_id,
                )
                logger.info(f"  Payment criado: {payment_name} (ID: {payment_id})")

            lanc.odoo_payment_id = payment_id
            lanc.odoo_payment_name = payment_name

            if not usou_writeoff:
                # 2. Postar payment (wizard já posta automaticamente)
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
                # Validar empresa: payment e título devem ser da mesma empresa
                titulo_company = titulo_check.get('company_id')
                titulo_company_id = (
                    titulo_company[0] if isinstance(titulo_company, (list, tuple))
                    else titulo_company
                )

                if titulo_company_id != lanc.odoo_company_id:
                    logger.warning(
                        f"  CONFLITO DE EMPRESA: payment na empresa {lanc.odoo_company_id}, "
                        f"título na empresa {titulo_company_id}. Reconciliação título ignorada "
                        f"(será reconciliado via conciliação de extrato)."
                    )
                elif usou_writeoff:
                    # Wizard já reconciliou o título automaticamente
                    logger.info("  Write-Off: reconciliação título feita pelo wizard")
                else:
                    # Fluxo normal: reconciliar manualmente
                    self.baixa_service.reconciliar(debit_line_id, lanc.odoo_move_line_id)
                    logger.info("  Reconciliado: payment ↔ título")

                # Buscar full_reconcile_id (funciona em ambos os casos)
                titulo_atualizado = self.baixa_service.buscar_titulo_por_id(lanc.odoo_move_line_id)
                if titulo_atualizado:
                    full_rec = titulo_atualizado.get('full_reconcile_id')
                    if full_rec:
                        lanc.odoo_full_reconcile_id = (
                            full_rec[0] if isinstance(full_rec, (list, tuple)) else full_rec
                        )

            # 5. Reconciliar payment com extrato (se comprovante tem vínculo Odoo)
            if credit_line_id and comp.odoo_statement_line_id and comp.odoo_move_id:
                # 5a. Preparar extrato: TODAS as escritas em UM ciclo draft→write→post
                # (conta, partner, rótulo — consolidados para evitar bug O11/O12)
                from app.financeiro.services.baixa_pagamentos_service import BaixaPagamentosService
                rotulo = BaixaPagamentosService.formatar_rotulo_pagamento(
                    valor=float(comp.valor_pago),
                    nome_fornecedor=lanc.odoo_partner_name or '',
                    data_pagamento=comp.data_pagamento,
                )
                self.baixa_service.preparar_extrato_para_reconciliacao(
                    move_id=comp.odoo_move_id,
                    statement_line_id=comp.odoo_statement_line_id,
                    partner_id=lanc.odoo_partner_id,
                    rotulo=rotulo,
                )

                # 5b. Buscar linha de débito do extrato (agora na conta PENDENTES)
                debit_line_extrato = self.baixa_service.buscar_linha_debito_extrato(
                    comp.odoo_move_id
                )
                if debit_line_extrato:
                    # 5c. Reconciliar payment com extrato (POR ÚLTIMO)
                    self.baixa_service.reconciliar(credit_line_id, debit_line_extrato)
                    logger.info("  Reconciliado: payment ↔ extrato")

                    # 5d. Buscar full_reconcile_id do extrato
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
            lanc.lancado_em = agora_utc_naive()
            lanc.lancado_por = usuario
            lanc.erro_lancamento = None

            # 7. Marcar comprovante como reconciliado
            comp.odoo_is_reconciled = True

            # FIX G2/G3: Atualizar ContasAPagar local imediato
            try:
                if lanc.odoo_move_line_id:
                    from app.financeiro.models import ContasAPagar
                    titulo_local = ContasAPagar.query.filter_by(
                        odoo_line_id=lanc.odoo_move_line_id
                    ).first()
                    if titulo_local and not titulo_local.parcela_paga:
                        titulo_local.parcela_paga = True
                        titulo_local.reconciliado = True
                        titulo_local.metodo_baixa = 'COMPROVANTE'
                        if titulo_local.status_sistema == 'PENDENTE':
                            titulo_local.status_sistema = 'PAGO'
                        logger.info(
                            f"  [G2/G3] ContasAPagar #{titulo_local.id} marcada paga "
                            f"(metodo_baixa=COMPROVANTE)"
                        )
                    elif titulo_local and titulo_local.parcela_paga and not titulo_local.metodo_baixa:
                        titulo_local.metodo_baixa = 'COMPROVANTE'
            except Exception as e_g2:
                logger.warning(f"  [G2/G3] Falha ao atualizar titulo local: {e_g2}")

            # 8. Sincronizar com extrato (se existir) — NÃO-BLOQUEANTE
            try:
                from app.financeiro.services.conciliacao_sync_service import ConciliacaoSyncService
                sync_service = ConciliacaoSyncService()
                sync_service.sync_comprovante_para_extrato(comp.id)
            except Exception as sync_err:
                logger.warning(f"  Sync com extrato falhou (não-bloqueante): {sync_err}")

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
    # LANÇAMENTO GRUPO (MULTI-NF)
    # =========================================================================

    def lancar_grupo_no_odoo(self, comprovante_id: int, usuario: str) -> Dict:
        """
        Lança grupo de N lançamentos CONFIRMADOS do mesmo comprovante no Odoo.

        Cenário Multi-NF: 1 comprovante → N títulos, cada um com valor_alocado.
        Cria 1 payment outbound POR título, usando valor_alocado como valor.

        Se apenas 1 lançamento CONFIRMADO, delega para lancar_no_odoo() (backward compatible).

        Fluxo por título:
        1. Verificar saldo no Odoo
        2. Calcular juros proporcionais (se houver)
        3. Criar payment outbound com valor_alocado
        4. Postar payment
        5. Reconciliar payment com título
        6. Atualizar status → LANCADO

        Após todos os payments:
        7. Reconciliar TODOS os payments com o statement line (se disponível)
        8. Marcar comprovante como reconciliado

        Tratamento de erro: se qualquer payment falhar, os anteriores já lançados
        ficam como LANCADO (operações Odoo não são revertidas), e os pendentes
        ficam como CONFIRMADO com erro.

        Args:
            comprovante_id: ID do ComprovantePagamentoBoleto
            usuario: Nome do usuário que executou

        Returns:
            Dict com resultado da operação
        """
        comp = ComprovantePagamentoBoleto.query.get(comprovante_id)
        if not comp:
            return {'sucesso': False, 'erro': f'Comprovante {comprovante_id} não encontrado'}

        # Buscar todos os lançamentos CONFIRMADOS deste comprovante
        lancamentos = LancamentoComprovante.query.filter(
            LancamentoComprovante.comprovante_id == comprovante_id,
            LancamentoComprovante.status == 'CONFIRMADO',
        ).order_by(LancamentoComprovante.id).all()

        if not lancamentos:
            return {'sucesso': False, 'erro': 'Nenhum lançamento CONFIRMADO encontrado'}

        # Se apenas 1 → delegar para fluxo existente (backward compatible)
        if len(lancamentos) == 1:
            return self.lancar_no_odoo(lancamentos[0].id, usuario)

        # Validar que todos têm valor_alocado
        for lanc in lancamentos:
            if not lanc.valor_alocado or float(lanc.valor_alocado) <= 0:
                return {
                    'sucesso': False,
                    'erro': (
                        f'Lançamento {lanc.id} sem valor_alocado. '
                        f'Multi-NF requer valor_alocado em todos os lançamentos.'
                    ),
                }

        valor_pago = float(comp.valor_pago or 0)
        soma_alocado = sum(float(l.valor_alocado) for l in lancamentos)

        # Tolerância de R$ 0.01
        if abs(soma_alocado - valor_pago) > 0.01:
            return {
                'sucesso': False,
                'erro': (
                    f'Soma dos valores alocados (R$ {soma_alocado:.2f}) '
                    f'difere do valor pago (R$ {valor_pago:.2f})'
                ),
            }

        # Determinar journal_id (mesmo para todos — mesmo comprovante)
        journal_id = self._determinar_journal(comp, lancamentos[0])
        if not journal_id:
            return {
                'sucesso': False,
                'erro': (
                    f'Não foi possível determinar journal_id. '
                    f'comprovante.odoo_journal_id={comp.odoo_journal_id}'
                ),
            }

        # Calcular juros proporcionais
        juros_por_lancamento = self._distribuir_juros(comp, lancamentos)

        logger.info(
            f"[Lancamento Grupo] Iniciando: comp_id={comprovante_id}, "
            f"{len(lancamentos)} títulos, soma_alocado=R$ {soma_alocado:.2f}, "
            f"journal_id={journal_id}, usuario={usuario}"
        )

        resultados = []
        credit_line_ids = []  # Para reconciliação com extrato depois

        for lanc in lancamentos:
            lanc_resultado = self._lancar_titulo_individual(
                lanc=lanc,
                comp=comp,
                journal_id=journal_id,
                juros=juros_por_lancamento.get(lanc.id, 0),
                usuario=usuario,
            )
            resultados.append(lanc_resultado)

            if lanc_resultado.get('sucesso') and lanc_resultado.get('credit_line_id'):
                credit_line_ids.append(lanc_resultado['credit_line_id'])

        # Reconciliar payments com extrato (se disponível e todos OK)
        reconciliacao_extrato = None
        if credit_line_ids and comp.odoo_statement_line_id and comp.odoo_move_id:
            reconciliacao_extrato = self._reconciliar_grupo_com_extrato(
                comp=comp,
                lancamentos=[l for l, r in zip(lancamentos, resultados) if r.get('sucesso')],
                credit_line_ids=credit_line_ids,
            )

        # Marcar comprovante como reconciliado se todos lançados com sucesso
        todos_sucesso = all(r.get('sucesso') for r in resultados)
        if todos_sucesso:
            comp.odoo_is_reconciled = True

        # Sincronizar com extrato (se existir) — NÃO-BLOQUEANTE
        try:
            from app.financeiro.services.conciliacao_sync_service import ConciliacaoSyncService
            sync_service = ConciliacaoSyncService()
            sync_service.sync_comprovante_para_extrato(comp.id)
        except Exception as sync_err:
            logger.warning(f"  Sync grupo com extrato falhou (não-bloqueante): {sync_err}")

        db.session.commit()

        total_sucesso = sum(1 for r in resultados if r.get('sucesso'))
        total_erros = sum(1 for r in resultados if not r.get('sucesso'))

        logger.info(
            f"[Lancamento Grupo] Concluído: comp={comprovante_id}, "
            f"{total_sucesso}/{len(lancamentos)} sucesso, {total_erros} erros"
        )

        return {
            'sucesso': todos_sucesso,
            'multi_nf': True,
            'comprovante_id': comprovante_id,
            'total_titulos': len(lancamentos),
            'total_sucesso': total_sucesso,
            'total_erros': total_erros,
            'reconciliacao_extrato': reconciliacao_extrato,
            'detalhes': resultados,
        }

    def _distribuir_juros(
        self,
        comp: ComprovantePagamentoBoleto,
        lancamentos: list,
    ) -> Dict[int, float]:
        """
        Distribui juros/multa proporcionalmente entre os títulos.

        Fórmula: juros_titulo_i = total_juros * (valor_titulo_i / soma_titulos)
        Ajusta centavo residual no maior título.

        Returns:
            Dict {lancamento_id: juros_float}
        """
        total_juros = float(comp.valor_juros_multa or 0)
        if total_juros <= 0:
            return {l.id: 0 for l in lancamentos}

        # Soma dos valores dos títulos (residual ou original)
        valores_titulo = {}
        for lanc in lancamentos:
            valor = float(lanc.odoo_valor_residual or lanc.odoo_valor_original or lanc.valor_alocado or 0)
            valores_titulo[lanc.id] = valor

        soma_titulos = sum(valores_titulo.values())
        if soma_titulos <= 0:
            # Distribuir igualmente como fallback
            juros_cada = round(total_juros / len(lancamentos), 2)
            resultado = {l.id: juros_cada for l in lancamentos}
            # Ajustar residual no primeiro
            soma = sum(resultado.values())
            diff = round(total_juros - soma, 2)
            if abs(diff) > 0 and lancamentos:
                resultado[lancamentos[0].id] = round(resultado[lancamentos[0].id] + diff, 2)
            return resultado

        # Distribuição proporcional
        resultado = {}
        for lanc in lancamentos:
            proporcao = valores_titulo[lanc.id] / soma_titulos
            resultado[lanc.id] = round(total_juros * proporcao, 2)

        # Ajustar centavo residual no maior título
        soma_distribuida = sum(resultado.values())
        diff = round(total_juros - soma_distribuida, 2)
        if abs(diff) > 0:
            # Encontrar o maior título
            maior_id = max(valores_titulo, key=valores_titulo.get)
            resultado[maior_id] = round(resultado[maior_id] + diff, 2)

        return resultado

    def _lancar_titulo_individual(
        self,
        lanc: LancamentoComprovante,
        comp: ComprovantePagamentoBoleto,
        journal_id: int,
        juros: float,
        usuario: str,
    ) -> Dict:
        """
        Lança 1 título individual dentro de um grupo Multi-NF.

        Usa valor_alocado (não comp.valor_pago) como valor do payment.
        NÃO reconcilia com extrato — isso é feito em lote depois.

        Returns:
            Dict com sucesso, payment_id, credit_line_id, etc.
        """
        erros_validacao = self._validar_dados(lanc, comp)
        if erros_validacao:
            lanc.erro_lancamento = '; '.join(erros_validacao)
            db.session.flush()
            return {'sucesso': False, 'lancamento_id': lanc.id, 'erro': '; '.join(erros_validacao)}

        valor_alocado = float(lanc.valor_alocado)

        logger.info(
            f"  [Multi-NF] Título {lanc.id}: move_line={lanc.odoo_move_line_id}, "
            f"NF={lanc.nf_numero}/{lanc.parcela}, valor_alocado=R$ {valor_alocado:.2f}, "
            f"juros=R$ {juros:.2f}"
        )

        try:
            # 0. Verificar saldo no Odoo
            titulo_check = self.baixa_service.buscar_titulo_por_id(lanc.odoo_move_line_id)
            if not titulo_check:
                erro = f'Título {lanc.odoo_move_line_id} não encontrado no Odoo'
                lanc.erro_lancamento = erro
                db.session.flush()
                return {'sucesso': False, 'lancamento_id': lanc.id, 'erro': erro}

            titulo_reconciliado = titulo_check.get('reconciled', False)
            titulo_residual = abs(float(titulo_check.get('amount_residual', 0)))

            if titulo_reconciliado or titulo_residual < 0.01:
                logger.info(
                    f"    Título {lanc.odoo_move_line_id} já quitado. Sincronizando."
                )
                result = self._sincronizar_titulo_ja_quitado(lanc, comp, titulo_check, usuario)
                return {**result, 'credit_line_id': None}

            # 1. Determinar valor do payment e juros
            # No Multi-NF, juros já vem distribuído proporcionalmente
            valor_titulo = valor_alocado - juros  # valor líquido do título
            usou_writeoff = False

            if juros > 0.01:
                # COM JUROS: usar wizard com write-off
                logger.info(
                    f"    Juros: valor_alocado={valor_alocado:.2f}, "
                    f"valor_titulo={valor_titulo:.2f}, juros={juros:.2f}"
                )
                payment_id, payment_name = self.baixa_service.criar_pagamento_outbound_com_writeoff(
                    titulo_id=lanc.odoo_move_line_id,
                    partner_id=lanc.odoo_partner_id,
                    valor_titulo=valor_titulo,
                    valor_juros=juros,
                    journal_id=journal_id,
                    ref=lanc.odoo_move_name or f'NF {lanc.nf_numero}',
                    data=comp.data_pagamento,
                    company_id=lanc.odoo_company_id,
                )
                usou_writeoff = True
                logger.info(f"    Payment Write-Off: {payment_name} (ID: {payment_id})")
            else:
                # SEM JUROS: payment outbound simples
                payment_id, payment_name = self.baixa_service.criar_pagamento_outbound(
                    partner_id=lanc.odoo_partner_id,
                    valor=valor_alocado,
                    journal_id=journal_id,
                    ref=lanc.odoo_move_name or f'NF {lanc.nf_numero}',
                    data=comp.data_pagamento,
                    company_id=lanc.odoo_company_id,
                )
                logger.info(f"    Payment: {payment_name} (ID: {payment_id})")

            lanc.odoo_payment_id = payment_id
            lanc.odoo_payment_name = payment_name

            if not usou_writeoff:
                # 2. Postar payment
                self.baixa_service.postar_pagamento(payment_id)

            # 3. Buscar linhas do payment
            linhas_payment = self.baixa_service.buscar_linhas_payment(payment_id)
            debit_line_id = linhas_payment.get('debit_line_id')
            credit_line_id = linhas_payment.get('credit_line_id')

            lanc.odoo_debit_line_id = debit_line_id
            lanc.odoo_credit_line_id = credit_line_id

            # 4. Reconciliar payment com título
            if debit_line_id and lanc.odoo_move_line_id:
                if usou_writeoff:
                    logger.info("    Write-Off: reconciliação título feita pelo wizard")
                else:
                    self.baixa_service.reconciliar(debit_line_id, lanc.odoo_move_line_id)
                    logger.info("    Reconciliado: payment ↔ título")

                titulo_atualizado = self.baixa_service.buscar_titulo_por_id(lanc.odoo_move_line_id)
                if titulo_atualizado:
                    full_rec = titulo_atualizado.get('full_reconcile_id')
                    if full_rec:
                        lanc.odoo_full_reconcile_id = (
                            full_rec[0] if isinstance(full_rec, (list, tuple)) else full_rec
                        )

            # 5. Atualizar status
            lanc.status = 'LANCADO'
            lanc.lancado_em = agora_utc_naive()
            lanc.lancado_por = usuario
            lanc.erro_lancamento = None

            # FIX G2/G3: Atualizar ContasAPagar local imediato
            try:
                if lanc.odoo_move_line_id:
                    from app.financeiro.models import ContasAPagar
                    titulo_local = ContasAPagar.query.filter_by(
                        odoo_line_id=lanc.odoo_move_line_id
                    ).first()
                    if titulo_local and not titulo_local.parcela_paga:
                        titulo_local.parcela_paga = True
                        titulo_local.reconciliado = True
                        titulo_local.metodo_baixa = 'COMPROVANTE'
                        if titulo_local.status_sistema == 'PENDENTE':
                            titulo_local.status_sistema = 'PAGO'
                    elif titulo_local and titulo_local.parcela_paga and not titulo_local.metodo_baixa:
                        titulo_local.metodo_baixa = 'COMPROVANTE'
            except Exception as e_g2:
                logger.warning(f"  [G2/G3] Falha titulo local (non-blocking): {e_g2}")

            db.session.flush()

            logger.info(
                f"    Título {lanc.id} LANCADO: payment={payment_name}, "
                f"reconcile={lanc.odoo_full_reconcile_id}"
            )

            return {
                'sucesso': True,
                'lancamento_id': lanc.id,
                'payment_id': payment_id,
                'payment_name': payment_name,
                'credit_line_id': credit_line_id,
                'full_reconcile_id': lanc.odoo_full_reconcile_id,
            }

        except Exception as e:
            logger.error(f"    Erro título {lanc.id}: {e}", exc_info=True)
            lanc.erro_lancamento = str(e)[:1000]
            db.session.flush()
            return {
                'sucesso': False,
                'lancamento_id': lanc.id,
                'erro': str(e),
            }

    def _reconciliar_grupo_com_extrato(
        self,
        comp: ComprovantePagamentoBoleto,
        lancamentos: list,
        credit_line_ids: List[int],
    ) -> Optional[Dict]:
        """
        Reconcilia N payments com 1 statement line do extrato.

        O Odoo suporta reconciliação parcial nativamente:
        cada credit_line é reconciliada com a debit_line do extrato.
        A última reconciliação fecha o extrato completamente.

        Args:
            comp: Comprovante com odoo_statement_line_id e odoo_move_id
            lancamentos: Lista de LancamentoComprovante já LANCADOS
            credit_line_ids: IDs das credit lines dos payments criados

        Returns:
            Dict com resultado ou None se falhar
        """
        if not comp.odoo_statement_line_id or not comp.odoo_move_id:
            return None

        try:
            # 1-4. Preparar extrato: TODAS as escritas em UM ciclo draft→write→post
            # (conta, partner, rótulo — consolidados para evitar bug O11/O12)
            from app.financeiro.services.baixa_pagamentos_service import BaixaPagamentosService
            nfs_lista = ', '.join(
                f'NF {l.nf_numero}/{l.parcela}' for l in lancamentos
                if l.nf_numero
            )
            rotulo = BaixaPagamentosService.formatar_rotulo_pagamento(
                valor=float(comp.valor_pago),
                nome_fornecedor=lancamentos[0].odoo_partner_name or '',
                data_pagamento=comp.data_pagamento,
            )
            if nfs_lista:
                rotulo = f"{rotulo} [{nfs_lista}]"

            partner_id = lancamentos[0].odoo_partner_id if lancamentos else None
            self.baixa_service.preparar_extrato_para_reconciliacao(
                move_id=comp.odoo_move_id,
                statement_line_id=comp.odoo_statement_line_id,
                partner_id=partner_id,
                rotulo=rotulo,
            )

            # 5. Buscar linha de débito do extrato (agora na conta PENDENTES)
            debit_line_extrato = self.baixa_service.buscar_linha_debito_extrato(
                comp.odoo_move_id
            )
            if not debit_line_extrato:
                logger.warning(
                    f"  Linha débito extrato não encontrada para move_id={comp.odoo_move_id}"
                )
                return {'sucesso': False, 'erro': 'Linha débito extrato não encontrada'}

            # 6. Reconciliar cada credit_line com o débito do extrato
            # O Odoo faz reconciliação parcial automaticamente quando o valor
            # da credit_line é menor que o débito. Apenas a última fecha totalmente.
            for i, credit_line_id in enumerate(credit_line_ids):
                try:
                    self.baixa_service.reconciliar(credit_line_id, debit_line_extrato)
                    logger.info(
                        f"  Reconciliado extrato: credit_line={credit_line_id} "
                        f"↔ debit_extrato={debit_line_extrato} ({i+1}/{len(credit_line_ids)})"
                    )
                except Exception as e:
                    logger.warning(
                        f"  Falha reconciliar extrato credit_line={credit_line_id}: {e}"
                    )

            # 7. Buscar full_reconcile_id do extrato (da última reconciliação)
            linha_extrato = self.baixa_service.connection.search_read(
                'account.move.line',
                [['id', '=', debit_line_extrato]],
                fields=['full_reconcile_id'],
                limit=1,
            )
            full_rec_extrato = None
            if linha_extrato and linha_extrato[0].get('full_reconcile_id'):
                full_rec = linha_extrato[0]['full_reconcile_id']
                full_rec_extrato = full_rec[0] if isinstance(full_rec, (list, tuple)) else full_rec

            # Atualizar full_reconcile_extrato_id em todos os lançamentos
            for lanc in lancamentos:
                if full_rec_extrato:
                    lanc.odoo_full_reconcile_extrato_id = full_rec_extrato

            logger.info(
                f"  Reconciliação extrato grupo: {len(credit_line_ids)} payments "
                f"↔ statement_line={comp.odoo_statement_line_id}, "
                f"full_reconcile={full_rec_extrato}"
            )

            return {
                'sucesso': True,
                'full_reconcile_extrato_id': full_rec_extrato,
                'credit_lines_reconciliadas': len(credit_line_ids),
            }

        except Exception as e:
            logger.error(f"  Erro reconciliar grupo com extrato: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e)}

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

    def _sincronizar_titulo_ja_quitado(
        self,
        lanc: LancamentoComprovante,
        comp: ComprovantePagamentoBoleto,
        titulo_check: Dict,
        usuario: str,
    ) -> Dict:
        """
        Quando o título já foi quitado no Odoo (manualmente),
        sincronizar os dados e marcar como LANCADO.

        Evita criar payment "fantasma" no Odoo quando o título
        já foi pago por outro meio.

        Args:
            lanc: LancamentoComprovante a ser atualizado
            comp: ComprovantePagamentoBoleto associado
            titulo_check: Dados do título retornados por buscar_titulo_por_id
            usuario: Nome do usuário

        Returns:
            Dict com resultado da operação
        """
        # Extrair full_reconcile_id do título
        full_rec = titulo_check.get('full_reconcile_id')
        if full_rec:
            lanc.odoo_full_reconcile_id = (
                full_rec[0] if isinstance(full_rec, (list, tuple)) else full_rec
            )

        # Verificar se o extrato também já está reconciliado
        if comp.odoo_statement_line_id and comp.odoo_move_id:
            try:
                linhas_extrato = self.baixa_service.connection.search_read(
                    'account.move.line',
                    [
                        ['move_id', '=', comp.odoo_move_id],
                        ['credit', '>', 0],
                    ],
                    fields=['id', 'reconciled', 'full_reconcile_id'],
                    limit=1,
                )
                if linhas_extrato and linhas_extrato[0].get('reconciled'):
                    ext_full_rec = linhas_extrato[0].get('full_reconcile_id')
                    if ext_full_rec:
                        lanc.odoo_full_reconcile_extrato_id = (
                            ext_full_rec[0] if isinstance(ext_full_rec, (list, tuple)) else ext_full_rec
                        )
                    logger.info(
                        f"  Extrato também já reconciliado no Odoo "
                        f"(full_reconcile_extrato={lanc.odoo_full_reconcile_extrato_id})"
                    )
            except Exception as e:
                logger.warning(f"  Falha ao verificar extrato reconciliado: {e}")

        lanc.status = 'LANCADO'
        lanc.lancado_em = agora_utc_naive()
        lanc.lancado_por = usuario
        lanc.erro_lancamento = None
        comp.odoo_is_reconciled = True

        # FIX G2/G3: Atualizar ContasAPagar local imediato
        try:
            if lanc.odoo_move_line_id:
                from app.financeiro.models import ContasAPagar
                titulo_local = ContasAPagar.query.filter_by(
                    odoo_line_id=lanc.odoo_move_line_id
                ).first()
                if titulo_local and not titulo_local.parcela_paga:
                    titulo_local.parcela_paga = True
                    titulo_local.reconciliado = True
                    titulo_local.metodo_baixa = 'COMPROVANTE'
                    if titulo_local.status_sistema == 'PENDENTE':
                        titulo_local.status_sistema = 'PAGO'
                elif titulo_local and titulo_local.parcela_paga and not titulo_local.metodo_baixa:
                    titulo_local.metodo_baixa = 'COMPROVANTE'
        except Exception as e_g2:
            logger.warning(f"  [G2/G3] Falha titulo local (non-blocking): {e_g2}")

        # Sincronizar com extrato (se existir) — NÃO-BLOQUEANTE
        try:
            from app.financeiro.services.conciliacao_sync_service import ConciliacaoSyncService
            sync_service = ConciliacaoSyncService()
            sync_service.sync_comprovante_para_extrato(comp.id)
        except Exception as sync_err:
            logger.warning(f"  Sync título quitado com extrato falhou (não-bloqueante): {sync_err}")

        db.session.commit()

        logger.info(
            f"  ✅ Lançamento {lanc.id} sincronizado (título já quitado no Odoo). "
            f"full_reconcile={lanc.odoo_full_reconcile_id}"
        )
        return {
            'sucesso': True,
            'lancamento_id': lanc.id,
            'full_reconcile_id': lanc.odoo_full_reconcile_id,
            'full_reconcile_extrato_id': lanc.odoo_full_reconcile_extrato_id,
            'sincronizado': True,
        }

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

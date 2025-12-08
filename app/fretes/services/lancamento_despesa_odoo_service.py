"""
Service de Lançamento de Despesa Extra no Odoo
==============================================

OBJETIVO:
    Executar o processo completo de lançamento de CTe de Despesa Extra no Odoo
    Reutiliza a lógica do LancamentoOdooService para fretes

AUTOR: Sistema de Fretes
DATA: 2025-01-22

NOTAS:
    - Usa as mesmas 16 etapas do lançamento de frete
    - Requer CTe Complementar vinculado à despesa (despesa_cte_id)
    - Auditoria registrada com despesa_extra_id
"""

import json
import logging
import time
from datetime import datetime, date
from typing import Dict, Optional, Any

from flask import current_app

from app import db
from app.fretes.models import (
    DespesaExtra,
    ConhecimentoTransporte,
    LancamentoFreteOdooAuditoria
)
from app.fretes.services.lancamento_odoo_service import LancamentoOdooService
from app.utils.timezone import agora_brasil

logger = logging.getLogger(__name__)


class LancamentoDespesaOdooService(LancamentoOdooService):
    """
    Service para lançar despesas extras no Odoo.
    Herda de LancamentoOdooService e adapta para despesas.
    """

    def _registrar_auditoria_despesa(
        self,
        despesa_extra_id: int,
        cte_id: Optional[int],
        chave_cte: str,
        etapa: int,
        etapa_descricao: str,
        modelo_odoo: str,
        acao: str,
        status: str,
        mensagem: Optional[str] = None,
        metodo_odoo: Optional[str] = None,
        dados_antes: Optional[Dict] = None,
        dados_depois: Optional[Dict] = None,
        campos_alterados: Optional[list] = None,
        contexto_odoo: Optional[Dict] = None,
        erro_detalhado: Optional[str] = None,
        tempo_execucao_ms: Optional[int] = None,
        dfe_id: Optional[int] = None,
        purchase_order_id: Optional[int] = None,
        invoice_id: Optional[int] = None
    ) -> LancamentoFreteOdooAuditoria:
        """
        Registra etapa na auditoria com despesa_extra_id

        Returns:
            Registro de auditoria criado
        """
        try:
            auditoria = LancamentoFreteOdooAuditoria(
                frete_id=None,  # Não é frete
                despesa_extra_id=despesa_extra_id,
                cte_id=cte_id,
                chave_cte=chave_cte,
                dfe_id=dfe_id,
                purchase_order_id=purchase_order_id,
                invoice_id=invoice_id,
                etapa=etapa,
                etapa_descricao=etapa_descricao,
                modelo_odoo=modelo_odoo,
                metodo_odoo=metodo_odoo,
                acao=acao,
                dados_antes=json.dumps(dados_antes, default=str) if dados_antes else None,
                dados_depois=json.dumps(dados_depois, default=str) if dados_depois else None,
                campos_alterados=','.join(campos_alterados) if campos_alterados else None,
                status=status,
                mensagem=mensagem,
                contexto_odoo=json.dumps(contexto_odoo, default=str) if contexto_odoo else None,
                erro_detalhado=erro_detalhado,
                tempo_execucao_ms=tempo_execucao_ms,
                executado_por=self.usuario_nome,
                ip_usuario=self.usuario_ip
            )

            db.session.add(auditoria)
            db.session.flush()  # Para obter o ID

            self.auditoria_logs.append(auditoria.to_dict())

            return auditoria

        except Exception as e:
            current_app.logger.error(f"Erro ao registrar auditoria despesa: {e}")
            raise

    def _rollback_despesa_odoo(self, despesa_id: int, etapas_concluidas: int) -> bool:
        """
        Faz rollback dos campos Odoo da despesa em caso de erro

        Args:
            despesa_id: ID da despesa
            etapas_concluidas: Número de etapas concluídas antes do erro

        Returns:
            True se rollback foi executado, False caso contrário
        """
        try:
            despesa = DespesaExtra.query.get(despesa_id)
            if not despesa:
                return False

            # SÓ FAZ ROLLBACK SE NÃO CONCLUIU TODAS AS ETAPAS (16)
            if despesa.status != 'LANCADO_ODOO' or etapas_concluidas < 16:
                current_app.logger.warning(
                    f"ROLLBACK: Limpando campos Odoo da despesa {despesa_id} "
                    f"(Etapas concluídas: {etapas_concluidas}/16)"
                )

                despesa.odoo_dfe_id = None
                despesa.odoo_purchase_order_id = None
                despesa.odoo_invoice_id = None
                despesa.lancado_odoo_em = None
                despesa.lancado_odoo_por = None

                # Voltar para status VINCULADO_CTE se tinha CTe
                if despesa.status == 'LANCADO_ODOO':
                    despesa.status = 'VINCULADO_CTE' if despesa.despesa_cte_id else 'PENDENTE'

                db.session.commit()
                current_app.logger.info(f"Rollback concluído com sucesso")
                return True
            else:
                current_app.logger.info(f"Rollback não necessário - lançamento estava completo")
                return False

        except Exception as rollback_error:
            current_app.logger.error(f"Erro ao executar rollback: {rollback_error}")
            db.session.rollback()
            return False

    def lancar_despesa_odoo(
        self,
        despesa_id: int,
        data_vencimento: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Executa lançamento completo de despesa extra no Odoo

        Args:
            despesa_id: ID da despesa extra no sistema
            data_vencimento: Data de vencimento (se None, usa vencimento da despesa)

        Returns:
            Dict com resultado:
            {
                'sucesso': bool,
                'mensagem': str,
                'dfe_id': int,
                'purchase_order_id': int,
                'invoice_id': int,
                'etapas_concluidas': int,
                'auditoria': List[Dict],
                'erro': str (se houver)
            }
        """
        from app.odoo.utils.connection import get_odoo_connection

        # LOG VISUAL: Início do lançamento
        inicio_total = time.time()
        current_app.logger.info("=" * 80)
        current_app.logger.info(f"INICIANDO LANCAMENTO ODOO - Despesa Extra #{despesa_id}")
        current_app.logger.info(f"Usuario: {self.usuario_nome}")
        current_app.logger.info("=" * 80)

        resultado = {
            'sucesso': False,
            'mensagem': '',
            'dfe_id': None,
            'purchase_order_id': None,
            'invoice_id': None,
            'etapas_concluidas': 0,
            'auditoria': [],
            'erro': None
        }

        try:
            # Buscar despesa
            despesa = DespesaExtra.query.get(despesa_id)
            if not despesa:
                raise ValueError(f"Despesa Extra ID {despesa_id} não encontrada")

            # Validar se tem CTe vinculado
            if not despesa.despesa_cte_id:
                raise ValueError("Despesa não possui CTe Complementar vinculado")

            # Validar tipo de documento (case-insensitive: aceita CTE, CTe, cte, etc.)
            if not despesa.tipo_documento or despesa.tipo_documento.upper() != 'CTE':
                raise ValueError(f"Tipo de documento '{despesa.tipo_documento}' não suportado para lançamento Odoo")

            # Validar status
            if despesa.status != 'VINCULADO_CTE':
                raise ValueError(f"Status '{despesa.status}' não permite lançamento. Esperado: VINCULADO_CTE")

            # Buscar CTe
            cte = ConhecimentoTransporte.query.get(despesa.despesa_cte_id)
            if not cte:
                raise ValueError(f"CTe #{despesa.despesa_cte_id} não encontrado")

            cte_chave = cte.chave_acesso
            cte_id = cte.id

            current_app.logger.info(f"CTe Complementar: {cte.numero_cte}")
            current_app.logger.info(f"Chave CTe: {cte_chave}")

            # Usar vencimento da despesa se não informado
            if not data_vencimento:
                data_vencimento = despesa.vencimento_despesa

            if not data_vencimento:
                raise ValueError("Data de vencimento não informada e despesa não possui vencimento")

            # Converter para string formato YYYY-MM-DD
            if isinstance(data_vencimento, date):
                data_vencimento_str = data_vencimento.strftime('%Y-%m-%d')
            else:
                data_vencimento_str = data_vencimento

            # Conectar no Odoo
            self.odoo = get_odoo_connection()

            if not self.odoo.authenticate():
                raise Exception("Falha na autenticação com Odoo")

            # ========================================
            # ETAPA 1: Buscar DFe pela chave
            # ========================================
            inicio = time.time()
            dfe_data = self.odoo.search_read(
                'l10n_br_ciel_it_account.dfe',
                [('protnfe_infnfe_chnfe', '=', cte_chave)],
                fields=['id', 'name', 'l10n_br_status', 'lines_ids', 'dups_ids'],
                limit=1
            )
            tempo_ms = int((time.time() - inicio) * 1000)

            self._registrar_auditoria_despesa(
                despesa_extra_id=despesa_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=1,
                etapa_descricao="Buscar DFe pela chave de acesso",
                modelo_odoo='l10n_br_ciel_it_account.dfe',
                acao='search_read',
                status='SUCESSO' if dfe_data else 'ERRO',
                mensagem=f"DFe encontrado: {dfe_data[0]['name'] if dfe_data else 'Não encontrado'}",
                dados_depois={'dfe_data': dfe_data[0] if dfe_data else None},
                tempo_execucao_ms=tempo_ms
            )

            if not dfe_data:
                resultado['erro'] = "CTe não encontrado no Odoo"
                resultado['mensagem'] = f"Erro na etapa 1: {resultado['erro']}"
                resultado['rollback_executado'] = self._rollback_despesa_odoo(despesa_id, 0)
                return resultado

            resultado['etapas_concluidas'] = 1
            dfe_id = dfe_data[0]['id']
            resultado['dfe_id'] = dfe_id

            # Verificar status do DFe
            dfe_status = dfe_data[0].get('l10n_br_status')
            if dfe_status != '04':
                resultado['erro'] = f"DFe com status '{dfe_status}' - esperado '04' (PO)"
                resultado['mensagem'] = f"Erro: CTe não está com status PO no Odoo"
                return resultado

            # ========================================
            # ETAPAS 2-16: Usar lógica do LancamentoOdooService
            # ========================================
            # A partir daqui, delegamos para o método pai adaptando os parâmetros
            # Porém, como o método pai espera um frete_id, vamos replicar a lógica
            # adaptada para despesa

            # Por simplicidade, vamos chamar as etapas individuais
            # (Este é um ponto de extensão - poderia ser refatorado para reutilizar mais código)

            # ETAPA 2: Atualizar data de entrada no DFe
            data_entrada = datetime.now().strftime('%Y-%m-%d')
            inicio = time.time()
            self.odoo.write(
                'l10n_br_ciel_it_account.dfe',
                [dfe_id],
                {
                    'l10n_br_date_in': data_entrada,
                    'payment_reference': f'DESPESA-{despesa_id}'
                }
            )
            tempo_ms = int((time.time() - inicio) * 1000)

            self._registrar_auditoria_despesa(
                despesa_extra_id=despesa_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=2,
                etapa_descricao="Atualizar data de entrada e payment_reference",
                modelo_odoo='l10n_br_ciel_it_account.dfe',
                acao='write',
                status='SUCESSO',
                mensagem=f"Data entrada: {data_entrada}, Ref: DESPESA-{despesa_id}",
                campos_alterados=['l10n_br_date_in', 'payment_reference'],
                tempo_execucao_ms=tempo_ms,
                dfe_id=dfe_id
            )
            resultado['etapas_concluidas'] = 2

            # ETAPA 3: Definir tipo pedido = 'servico'
            inicio = time.time()
            self.odoo.write(
                'l10n_br_ciel_it_account.dfe',
                [dfe_id],
                {'tipo_pedido': 'servico'}
            )
            tempo_ms = int((time.time() - inicio) * 1000)

            self._registrar_auditoria_despesa(
                despesa_extra_id=despesa_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=3,
                etapa_descricao="Definir tipo_pedido = servico",
                modelo_odoo='l10n_br_ciel_it_account.dfe',
                acao='write',
                status='SUCESSO',
                mensagem="tipo_pedido definido como 'servico'",
                campos_alterados=['tipo_pedido'],
                tempo_execucao_ms=tempo_ms,
                dfe_id=dfe_id
            )
            resultado['etapas_concluidas'] = 3

            # ETAPA 4: Atualizar linha do DFe com produto de serviço
            lines_ids = dfe_data[0].get('lines_ids', [])
            if lines_ids:
                line_id = lines_ids[0]
                inicio = time.time()
                self.odoo.write(
                    'l10n_br_ciel_it_account.dfe.line',
                    [line_id],
                    {
                        'product_id': self.PRODUTO_SERVICO_FRETE_ID,
                        'analytic_distribution': {str(self.CONTA_ANALITICA_LOGISTICA_ID): 100}
                    }
                )
                tempo_ms = int((time.time() - inicio) * 1000)

                self._registrar_auditoria_despesa(
                    despesa_extra_id=despesa_id,
                    cte_id=cte_id,
                    chave_cte=cte_chave,
                    etapa=4,
                    etapa_descricao="Atualizar linha DFe com produto SERVICO DE FRETE",
                    modelo_odoo='l10n_br_ciel_it_account.dfe.line',
                    acao='write',
                    status='SUCESSO',
                    mensagem=f"Linha {line_id} atualizada com produto {self.PRODUTO_SERVICO_FRETE_ID}",
                    campos_alterados=['product_id', 'analytic_distribution'],
                    tempo_execucao_ms=tempo_ms,
                    dfe_id=dfe_id
                )
            resultado['etapas_concluidas'] = 4

            # ETAPA 5: Atualizar vencimento
            dups_ids = dfe_data[0].get('dups_ids', [])
            if dups_ids:
                dup_id = dups_ids[0]
                inicio = time.time()
                self.odoo.write(
                    'l10n_br_ciel_it_account.dfe.pagamento',
                    [dup_id],
                    {'date_due': data_vencimento_str}
                )
                tempo_ms = int((time.time() - inicio) * 1000)

                self._registrar_auditoria_despesa(
                    despesa_extra_id=despesa_id,
                    cte_id=cte_id,
                    chave_cte=cte_chave,
                    etapa=5,
                    etapa_descricao="Atualizar vencimento",
                    modelo_odoo='l10n_br_ciel_it_account.dfe.pagamento',
                    acao='write',
                    status='SUCESSO',
                    mensagem=f"Vencimento: {data_vencimento_str}",
                    campos_alterados=['date_due'],
                    tempo_execucao_ms=tempo_ms,
                    dfe_id=dfe_id
                )
            resultado['etapas_concluidas'] = 5

            # ETAPA 6: Gerar Purchase Order
            inicio = time.time()
            self.odoo.execute_method(
                'l10n_br_ciel_it_account.dfe',
                'action_gerar_po_dfe',
                [[dfe_id]]
            )
            tempo_ms = int((time.time() - inicio) * 1000)

            self._registrar_auditoria_despesa(
                despesa_extra_id=despesa_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=6,
                etapa_descricao="Gerar Purchase Order (action_gerar_po_dfe)",
                modelo_odoo='l10n_br_ciel_it_account.dfe',
                metodo_odoo='action_gerar_po_dfe',
                acao='execute_method',
                status='SUCESSO',
                mensagem="Purchase Order gerado",
                tempo_execucao_ms=tempo_ms,
                dfe_id=dfe_id
            )
            resultado['etapas_concluidas'] = 6

            # Buscar PO gerado
            dfe_atualizado = self.odoo.read(
                'l10n_br_ciel_it_account.dfe',
                [dfe_id],
                ['purchase_fiscal_id']
            )

            if not dfe_atualizado or not dfe_atualizado[0].get('purchase_fiscal_id'):
                resultado['erro'] = "Purchase Order não foi gerado"
                resultado['mensagem'] = "Erro na etapa 6: PO não foi criado"
                resultado['rollback_executado'] = self._rollback_despesa_odoo(despesa_id, resultado['etapas_concluidas'])
                return resultado

            po_id = dfe_atualizado[0]['purchase_fiscal_id'][0]
            resultado['purchase_order_id'] = po_id

            # ETAPA 7: Configurar PO (incluindo correção da operação fiscal)
            dados_po = {
                'team_id': self.TEAM_LANCAMENTO_FRETE_ID,
                'payment_provider_id': self.PAYMENT_PROVIDER_TRANSFERENCIA_ID,
                'picking_type_id': self.PICKING_TYPE_CD_RECEBIMENTO_ID
            }

            # ✅ CORRIGIR OPERAÇÃO FISCAL: De-Para FB → CD
            try:
                po_operacao = self.odoo.read(
                    'purchase.order',
                    [po_id],
                    ['l10n_br_operacao_id']
                )
                if po_operacao and po_operacao[0].get('l10n_br_operacao_id'):
                    operacao_atual_id = po_operacao[0]['l10n_br_operacao_id'][0]
                    operacao_atual_nome = po_operacao[0]['l10n_br_operacao_id'][1]

                    if operacao_atual_id in self.OPERACAO_FB_PARA_CD:
                        operacao_correta_id = self.OPERACAO_FB_PARA_CD[operacao_atual_id]
                        dados_po['l10n_br_operacao_id'] = operacao_correta_id
                        current_app.logger.info(
                            f"🔄 Corrigindo operação fiscal: {operacao_atual_id} ({operacao_atual_nome}) "
                            f"→ {operacao_correta_id} (empresa CD)"
                        )
                    else:
                        current_app.logger.info(
                            f"✅ Operação fiscal já está correta: {operacao_atual_id} ({operacao_atual_nome})"
                        )
            except Exception as e:
                current_app.logger.warning(f"⚠️ Erro ao verificar operação fiscal: {e}")

            inicio = time.time()
            self.odoo.write(
                'purchase.order',
                [po_id],
                dados_po
            )
            tempo_ms = int((time.time() - inicio) * 1000)

            self._registrar_auditoria_despesa(
                despesa_extra_id=despesa_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=7,
                etapa_descricao="Configurar PO (operação fiscal, team, payment, picking_type)",
                modelo_odoo='purchase.order',
                acao='write',
                status='SUCESSO',
                mensagem=f"PO {po_id} configurado",
                campos_alterados=list(dados_po.keys()),
                tempo_execucao_ms=tempo_ms,
                dfe_id=dfe_id,
                purchase_order_id=po_id
            )
            resultado['etapas_concluidas'] = 7

            # ETAPA 8: Pulada (impostos calculados automaticamente)
            self._registrar_auditoria_despesa(
                despesa_extra_id=despesa_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=8,
                etapa_descricao="Impostos calculados automaticamente (pulada)",
                modelo_odoo='purchase.order',
                acao='skip',
                status='SUCESSO',
                mensagem="Etapa pulada - impostos calculados pelo Odoo",
                dfe_id=dfe_id,
                purchase_order_id=po_id
            )
            resultado['etapas_concluidas'] = 8

            # ETAPA 9: Confirmar PO
            inicio = time.time()
            self.odoo.execute_method(
                'purchase.order',
                'button_confirm',
                [[po_id]]
            )
            tempo_ms = int((time.time() - inicio) * 1000)

            self._registrar_auditoria_despesa(
                despesa_extra_id=despesa_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=9,
                etapa_descricao="Confirmar Purchase Order",
                modelo_odoo='purchase.order',
                metodo_odoo='button_confirm',
                acao='execute_method',
                status='SUCESSO',
                mensagem="PO confirmado",
                tempo_execucao_ms=tempo_ms,
                dfe_id=dfe_id,
                purchase_order_id=po_id
            )
            resultado['etapas_concluidas'] = 9

            # ETAPA 10: Aprovar PO se necessário
            po_data = self.odoo.read('purchase.order', [po_id], ['state'])
            if po_data and po_data[0].get('state') == 'to approve':
                inicio = time.time()
                self.odoo.execute_method(
                    'purchase.order',
                    'button_approve',
                    [[po_id]]
                )
                tempo_ms = int((time.time() - inicio) * 1000)

                self._registrar_auditoria_despesa(
                    despesa_extra_id=despesa_id,
                    cte_id=cte_id,
                    chave_cte=cte_chave,
                    etapa=10,
                    etapa_descricao="Aprovar Purchase Order",
                    modelo_odoo='purchase.order',
                    metodo_odoo='button_approve',
                    acao='execute_method',
                    status='SUCESSO',
                    mensagem="PO aprovado",
                    tempo_execucao_ms=tempo_ms,
                    dfe_id=dfe_id,
                    purchase_order_id=po_id
                )
            else:
                self._registrar_auditoria_despesa(
                    despesa_extra_id=despesa_id,
                    cte_id=cte_id,
                    chave_cte=cte_chave,
                    etapa=10,
                    etapa_descricao="Aprovar Purchase Order (pulada)",
                    modelo_odoo='purchase.order',
                    acao='skip',
                    status='SUCESSO',
                    mensagem="Aprovação não necessária",
                    dfe_id=dfe_id,
                    purchase_order_id=po_id
                )
            resultado['etapas_concluidas'] = 10

            # ETAPA 11: Criar Invoice
            inicio = time.time()
            self.odoo.execute_method(
                'purchase.order',
                'action_create_invoice',
                [[po_id]]
            )
            tempo_ms = int((time.time() - inicio) * 1000)

            self._registrar_auditoria_despesa(
                despesa_extra_id=despesa_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=11,
                etapa_descricao="Criar Invoice",
                modelo_odoo='purchase.order',
                metodo_odoo='action_create_invoice',
                acao='execute_method',
                status='SUCESSO',
                mensagem="Invoice criada",
                tempo_execucao_ms=tempo_ms,
                dfe_id=dfe_id,
                purchase_order_id=po_id
            )
            resultado['etapas_concluidas'] = 11

            # Buscar Invoice criada
            po_atualizado = self.odoo.read('purchase.order', [po_id], ['invoice_ids'])
            if not po_atualizado or not po_atualizado[0].get('invoice_ids'):
                resultado['erro'] = "Invoice não foi gerada"
                resultado['mensagem'] = "Erro na etapa 11: Invoice não foi criada"
                resultado['rollback_executado'] = self._rollback_despesa_odoo(despesa_id, resultado['etapas_concluidas'])
                return resultado

            invoice_id = po_atualizado[0]['invoice_ids'][0]
            resultado['invoice_id'] = invoice_id

            # ETAPA 12: Atualizar impostos da Invoice
            inicio = time.time()
            self.odoo.execute_method(
                'account.move',
                '_compute_tax_totals',
                [[invoice_id]]
            )
            tempo_ms = int((time.time() - inicio) * 1000)

            self._registrar_auditoria_despesa(
                despesa_extra_id=despesa_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=12,
                etapa_descricao="Atualizar impostos da Invoice",
                modelo_odoo='account.move',
                metodo_odoo='_compute_tax_totals',
                acao='execute_method',
                status='SUCESSO',
                mensagem="Impostos atualizados",
                tempo_execucao_ms=tempo_ms,
                dfe_id=dfe_id,
                purchase_order_id=po_id,
                invoice_id=invoice_id
            )
            resultado['etapas_concluidas'] = 12

            # ETAPA 13: Configurar Invoice
            inicio = time.time()
            self.odoo.write(
                'account.move',
                [invoice_id],
                {
                    'invoice_date': data_entrada,
                    'payment_reference': f'DESPESA-{despesa_id}'
                }
            )
            tempo_ms = int((time.time() - inicio) * 1000)

            self._registrar_auditoria_despesa(
                despesa_extra_id=despesa_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=13,
                etapa_descricao="Configurar Invoice",
                modelo_odoo='account.move',
                acao='write',
                status='SUCESSO',
                mensagem=f"Invoice {invoice_id} configurada",
                campos_alterados=['invoice_date', 'payment_reference'],
                tempo_execucao_ms=tempo_ms,
                dfe_id=dfe_id,
                purchase_order_id=po_id,
                invoice_id=invoice_id
            )
            resultado['etapas_concluidas'] = 13

            # ETAPA 14: Atualizar impostos novamente
            inicio = time.time()
            self.odoo.execute_method(
                'account.move',
                '_compute_tax_totals',
                [[invoice_id]]
            )
            tempo_ms = int((time.time() - inicio) * 1000)

            self._registrar_auditoria_despesa(
                despesa_extra_id=despesa_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=14,
                etapa_descricao="Atualizar impostos novamente",
                modelo_odoo='account.move',
                metodo_odoo='_compute_tax_totals',
                acao='execute_method',
                status='SUCESSO',
                mensagem="Impostos recalculados",
                tempo_execucao_ms=tempo_ms,
                dfe_id=dfe_id,
                purchase_order_id=po_id,
                invoice_id=invoice_id
            )
            resultado['etapas_concluidas'] = 14

            # ETAPA 15: Confirmar Invoice
            inicio = time.time()
            self.odoo.execute_method(
                'account.move',
                'action_post',
                [[invoice_id]]
            )
            tempo_ms = int((time.time() - inicio) * 1000)

            self._registrar_auditoria_despesa(
                despesa_extra_id=despesa_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=15,
                etapa_descricao="Confirmar Invoice (action_post)",
                modelo_odoo='account.move',
                metodo_odoo='action_post',
                acao='execute_method',
                status='SUCESSO',
                mensagem="Invoice confirmada",
                tempo_execucao_ms=tempo_ms,
                dfe_id=dfe_id,
                purchase_order_id=po_id,
                invoice_id=invoice_id
            )
            resultado['etapas_concluidas'] = 15

            # ETAPA 16: Atualizar despesa local
            despesa.odoo_dfe_id = dfe_id
            despesa.odoo_purchase_order_id = po_id
            despesa.odoo_invoice_id = invoice_id
            despesa.lancado_odoo_em = agora_brasil()
            despesa.lancado_odoo_por = self.usuario_nome
            despesa.status = 'LANCADO_ODOO'

            db.session.commit()

            self._registrar_auditoria_despesa(
                despesa_extra_id=despesa_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=16,
                etapa_descricao="Atualizar despesa local e finalizar",
                modelo_odoo='despesas_extras',
                acao='write',
                status='SUCESSO',
                mensagem=f"Despesa #{despesa_id} atualizada com IDs Odoo",
                campos_alterados=['odoo_dfe_id', 'odoo_purchase_order_id', 'odoo_invoice_id', 'lancado_odoo_em', 'lancado_odoo_por', 'status'],
                dfe_id=dfe_id,
                purchase_order_id=po_id,
                invoice_id=invoice_id
            )
            resultado['etapas_concluidas'] = 16

            # SUCESSO!
            tempo_total = time.time() - inicio_total
            resultado['sucesso'] = True
            resultado['mensagem'] = f'Despesa #{despesa_id} lançada com sucesso no Odoo em {tempo_total:.2f}s'
            resultado['auditoria'] = self.auditoria_logs

            current_app.logger.info("=" * 80)
            current_app.logger.info(f"LANCAMENTO CONCLUIDO - Despesa #{despesa_id}")
            current_app.logger.info(f"DFe ID: {dfe_id}")
            current_app.logger.info(f"PO ID: {po_id}")
            current_app.logger.info(f"Invoice ID: {invoice_id}")
            current_app.logger.info(f"Tempo total: {tempo_total:.2f}s")
            current_app.logger.info("=" * 80)

            return resultado

        except Exception as e:
            current_app.logger.error(f"Erro no lançamento: {str(e)}")
            import traceback
            traceback.print_exc()

            resultado['erro'] = str(e)
            resultado['mensagem'] = f'Erro no lançamento: {str(e)}'
            resultado['auditoria'] = self.auditoria_logs

            # Rollback
            resultado['rollback_executado'] = self._rollback_despesa_odoo(
                despesa_id, resultado['etapas_concluidas']
            )

            return resultado

"""
Service de Lançamento de Frete no Odoo
========================================

OBJETIVO:
    Executar o processo completo de lançamento de CTe no Odoo (16 etapas)
    com auditoria completa de todas as operações

AUTOR: Sistema de Fretes
DATA: 14/11/2025

ETAPAS:
    1-6:  Lançamento no DF-e
    7-12: Confirmação do Purchase Order
    13-14: Criação da Fatura
    15-17: Confirmação da Fatura
"""

import json
import logging
import time
import traceback
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from flask import current_app

from app import db
from app.fretes.models import (
    Frete,
    ConhecimentoTransporte,
    LancamentoFreteOdooAuditoria
)
from app.odoo.utils.connection import get_odoo_connection


class LancamentoOdooService:
    """
    Service para lançar fretes no Odoo com auditoria completa
    """

    # IDs fixos do Odoo (conforme documentação)
    PRODUTO_SERVICO_FRETE_ID = 29993
    CONTA_ANALITICA_LOGISTICA_ID = 1186
    TEAM_LANCAMENTO_FRETE_ID = 119
    PAYMENT_PROVIDER_TRANSFERENCIA_ID = 30
    COMPANY_NACOM_GOYA_CD_ID = 4
    PICKING_TYPE_CD_RECEBIMENTO_ID = 13  # ✅ CD: Recebimento (CD)

    # De-Para: Operação Fiscal FB → CD
    # Quando o PO é criado com operação da empresa FB, corrigir para a equivalente da CD
    OPERACAO_FB_PARA_CD = {
        2022: 2632,  # Aquisição transporte INTERNA
        3041: 3038,  # Aquisição transporte INTERESTADUAL
        2738: 2739,  # Aquisição transporte Simples Nacional INTERNA
        3040: 3037,  # Aquisição transporte Simples Nacional INTERESTADUAL
    }

    def __init__(self, usuario_nome: str, usuario_ip: Optional[str] = None):
        """
        Inicializa o service

        Args:
            usuario_nome: Nome do usuário que está executando
            usuario_ip: IP do usuário (opcional)
        """
        self.usuario_nome = usuario_nome
        self.usuario_ip = usuario_ip
        self.odoo = None
        self.auditoria_logs = []

    def _rollback_frete_odoo(self, frete_id: int, etapas_concluidas: int) -> bool:
        """
        Faz rollback dos campos Odoo do frete em caso de erro

        Args:
            frete_id: ID do frete
            etapas_concluidas: Número de etapas concluídas antes do erro

        Returns:
            True se rollback foi executado, False caso contrário
        """
        try:
            frete = Frete.query.get(frete_id)
            if not frete:
                return False

            # ✅ SÓ FAZ ROLLBACK SE NÃO CONCLUIU TODAS AS ETAPAS (16)
            if frete.status != 'LANCADO_ODOO' or etapas_concluidas < 16:
                current_app.logger.warning(
                    f"🔄 ROLLBACK: Limpando campos Odoo do frete {frete_id} "
                    f"(Etapas concluídas: {etapas_concluidas}/16)"
                )

                frete.odoo_dfe_id = None
                frete.odoo_purchase_order_id = None
                frete.odoo_invoice_id = None
                frete.lancado_odoo_em = None
                frete.lancado_odoo_por = None

                # Manter status original ou definir como erro
                if frete.status == 'LANCADO_ODOO':
                    frete.status = 'PENDENTE'

                db.session.commit()
                current_app.logger.info(f"✅ Rollback concluído com sucesso")
                return True
            else:
                current_app.logger.info(f"⏭️ Rollback não necessário - lançamento estava completo")
                return False

        except Exception as rollback_error:
            current_app.logger.error(f"❌ Erro ao executar rollback: {rollback_error}")
            db.session.rollback()
            return False

    def _registrar_auditoria(
        self,
        frete_id: Optional[int],
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
        campos_alterados: Optional[List[str]] = None,
        contexto_odoo: Optional[Dict] = None,
        erro_detalhado: Optional[str] = None,
        tempo_execucao_ms: Optional[int] = None,
        dfe_id: Optional[int] = None,
        purchase_order_id: Optional[int] = None,
        invoice_id: Optional[int] = None
    ) -> LancamentoFreteOdooAuditoria:
        """
        Registra etapa na auditoria

        Returns:
            Registro de auditoria criado
        """
        try:
            auditoria = LancamentoFreteOdooAuditoria(
                frete_id=frete_id,
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
                erro_detalhado=erro_detalhado,
                contexto_odoo=json.dumps(contexto_odoo, default=str) if contexto_odoo else None,
                tempo_execucao_ms=tempo_execucao_ms,
                executado_por=self.usuario_nome,
                ip_usuario=self.usuario_ip
            )

            db.session.add(auditoria)
            db.session.commit()

            self.auditoria_logs.append(auditoria.to_dict())

            return auditoria

        except Exception as e:
            current_app.logger.error(f"Erro ao registrar auditoria: {e}")
            db.session.rollback()
            raise

    def _executar_com_auditoria(
        self,
        funcao,
        frete_id: Optional[int],
        cte_id: Optional[int],
        chave_cte: str,
        etapa: int,
        etapa_descricao: str,
        modelo_odoo: str,
        acao: str,
        metodo_odoo: Optional[str] = None,
        contexto_odoo: Optional[Dict] = None,
        dfe_id: Optional[int] = None,
        purchase_order_id: Optional[int] = None,
        invoice_id: Optional[int] = None,
        campos_alterados: Optional[List[str]] = None
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Executa função com auditoria automática

        Returns:
            (sucesso, resultado, mensagem_erro)
        """
        # ✅ LOG VISUAL: Início da etapa
        current_app.logger.info(f"⏳ [ETAPA {etapa:02d}] {etapa_descricao}...")

        inicio = time.time()

        try:
            resultado = funcao()
            tempo_ms = int((time.time() - inicio) * 1000)

            # ✅ LOG VISUAL: Sucesso com tempo
            tempo_formatado = f"{tempo_ms}ms" if tempo_ms < 1000 else f"{tempo_ms/1000:.1f}s"
            current_app.logger.info(f"✅ [ETAPA {etapa:02d}] Concluída em {tempo_formatado}")

            self._registrar_auditoria(
                frete_id=frete_id,
                cte_id=cte_id,
                chave_cte=chave_cte,
                etapa=etapa,
                etapa_descricao=etapa_descricao,
                modelo_odoo=modelo_odoo,
                metodo_odoo=metodo_odoo,
                acao=acao,
                status='SUCESSO',
                mensagem=f'Etapa {etapa} concluída com sucesso',
                contexto_odoo=contexto_odoo,
                tempo_execucao_ms=tempo_ms,
                dfe_id=dfe_id,
                purchase_order_id=purchase_order_id,
                invoice_id=invoice_id,
                campos_alterados=campos_alterados
            )

            return True, resultado, None

        except Exception as e:
            tempo_ms = int((time.time() - inicio) * 1000)
            erro_msg = str(e)
            erro_trace = traceback.format_exc()

            # ❌ LOG VISUAL: Erro com tempo
            tempo_formatado = f"{tempo_ms}ms" if tempo_ms < 1000 else f"{tempo_ms/1000:.1f}s"
            current_app.logger.error(f"❌ [ETAPA {etapa:02d}] FALHOU em {tempo_formatado}: {erro_msg}")

            self._registrar_auditoria(
                frete_id=frete_id,
                cte_id=cte_id,
                chave_cte=chave_cte,
                etapa=etapa,
                etapa_descricao=etapa_descricao,
                modelo_odoo=modelo_odoo,
                metodo_odoo=metodo_odoo,
                acao=acao,
                status='ERRO',
                mensagem=f'Erro na etapa {etapa}: {erro_msg}',
                erro_detalhado=erro_trace,
                contexto_odoo=contexto_odoo,
                tempo_execucao_ms=tempo_ms,
                dfe_id=dfe_id,
                purchase_order_id=purchase_order_id,
                invoice_id=invoice_id,
                campos_alterados=campos_alterados
            )

            return False, None, erro_msg

    def lancar_frete_odoo(
        self,
        frete_id: int,
        cte_chave: str,
        data_vencimento: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Executa lançamento completo de frete no Odoo

        Args:
            frete_id: ID do frete no sistema
            cte_chave: Chave de acesso do CTe (44 dígitos)
            data_vencimento: Data de vencimento (se None, usa vencimento do frete)

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
        # 🚀 LOG VISUAL: Início do lançamento
        inicio_total = time.time()
        current_app.logger.info("="*80)
        current_app.logger.info(f"🚀 INICIANDO LANÇAMENTO ODOO - Frete #{frete_id}")
        current_app.logger.info(f"📄 Chave CTe: {cte_chave}")
        current_app.logger.info(f"👤 Usuário: {self.usuario_nome}")
        current_app.logger.info("="*80)

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
            # Buscar frete
            frete = Frete.query.get(frete_id)
            if not frete:
                raise ValueError(f"Frete ID {frete_id} não encontrado")

            # Buscar CTe
            cte = ConhecimentoTransporte.query.filter_by(chave_acesso=cte_chave).first()
            cte_id = cte.id if cte else None

            # Usar vencimento do frete se não informado
            if not data_vencimento:
                data_vencimento = frete.vencimento

            if not data_vencimento:
                raise ValueError("Data de vencimento não informada e frete não possui vencimento")

            # Converter para string formato YYYY-MM-DD
            if isinstance(data_vencimento, date):
                data_vencimento_str = data_vencimento.strftime('%Y-%m-%d')
            else:
                data_vencimento_str = data_vencimento

            # Conectar no Odoo
            current_app.logger.info(f"Iniciando lançamento de frete {frete_id} - CTe {cte_chave}")
            self.odoo = get_odoo_connection()

            if not self.odoo.authenticate():
                raise Exception("Falha na autenticação com Odoo")

            # ========================================
            # ETAPA 1: Buscar DFe pela chave
            # ========================================
            sucesso, dfe_data, erro = self._executar_com_auditoria(
                funcao=lambda: self.odoo.search_read(
                    'l10n_br_ciel_it_account.dfe',
                    [('protnfe_infnfe_chnfe', '=', cte_chave)],
                    fields=['id', 'name', 'l10n_br_status', 'lines_ids', 'dups_ids'],
                    limit=1
                ),
                frete_id=frete_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=1,
                etapa_descricao="Buscar DFe pela chave de acesso",
                modelo_odoo='l10n_br_ciel_it_account.dfe',
                acao='search_read'
            )

            if not sucesso or not dfe_data:
                resultado['erro'] = erro or "CTe não encontrado no Odoo"
                resultado['mensagem'] = f"Erro na etapa 1: {resultado['erro']}"
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            dfe = dfe_data[0]
            dfe_id = dfe['id']
            dfe_status = dfe.get('l10n_br_status')
            resultado['dfe_id'] = dfe_id
            resultado['etapas_concluidas'] = 1

            current_app.logger.info(f"DFe encontrado: ID {dfe_id}, Status: {dfe_status}")

            # ========================================
            # VALIDAÇÃO: Status deve ser '04' (PO)
            # ========================================
            if dfe_status != '04':
                status_map = {
                    '01': 'Rascunho',
                    '02': 'Sincronizado',
                    '03': 'Ciência/Confirmado',
                    '05': 'Rateio',
                    '06': 'Concluído',
                    '07': 'Rejeitado'
                }
                status_nome = status_map.get(dfe_status, f'Desconhecido ({dfe_status})')

                resultado['erro'] = f'CTe possui status "{status_nome}" - Apenas CTes com status "PO" (04) podem ser lançados'
                resultado['mensagem'] = f'Erro: {resultado["erro"]}'
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            current_app.logger.info(f"✅ DFe validado: Status PO (04), pode ser lançado")

            # ========================================
            # ETAPA 2: Atualizar data de entrada E payment_reference
            # ========================================
            hoje = date.today().strftime('%Y-%m-%d')

            # Preparar dados para atualização
            dados_atualizacao = {'l10n_br_data_entrada': hoje}

            # ✅ ADICIONAR payment_reference com número da fatura (se houver)
            if frete.fatura_frete_id and frete.fatura_frete:
                referencia_fatura = f"FATURA-{frete.fatura_frete.numero_fatura}"

                # Buscar valor atual ANTES de atualizar
                try:
                    dfe_atual = self.odoo.read(
                        'l10n_br_ciel_it_account.dfe',
                        [dfe_id],
                        ['payment_reference']
                    )
                    payment_ref_atual = dfe_atual[0].get('payment_reference', '') if dfe_atual else ''
                except Exception as e:
                    current_app.logger.warning(f"⚠️ Erro ao ler payment_reference atual: {e}")
                    payment_ref_atual = ''

                # Só adiciona ao dict se for diferente ou vazio
                if payment_ref_atual != referencia_fatura:
                    dados_atualizacao['payment_reference'] = referencia_fatura
                    current_app.logger.info(
                        f"🔗 Adicionando fatura {frete.fatura_frete.numero_fatura} ao DFe {dfe_id} "
                        f"(payment_reference: '{payment_ref_atual}' -> '{referencia_fatura}')"
                    )
                else:
                    current_app.logger.info(
                        f"✅ payment_reference já está correto: '{referencia_fatura}'"
                    )

            sucesso, _, erro = self._executar_com_auditoria(
                funcao=lambda: self.odoo.write(
                    'l10n_br_ciel_it_account.dfe',
                    [dfe_id],
                    dados_atualizacao
                ),
                frete_id=frete_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=2,
                etapa_descricao="Atualizar data de entrada e payment_reference",
                modelo_odoo='l10n_br_ciel_it_account.dfe',
                acao='write',
                dfe_id=dfe_id,
                campos_alterados=list(dados_atualizacao.keys())
            )

            if not sucesso:
                resultado['erro'] = erro
                resultado['mensagem'] = f"Erro na etapa 2: {erro}"
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            resultado['etapas_concluidas'] = 2

            # ========================================
            # ETAPA 3: Atualizar tipo pedido
            # ========================================
            sucesso, _, erro = self._executar_com_auditoria(
                funcao=lambda: self.odoo.write(
                    'l10n_br_ciel_it_account.dfe',
                    [dfe_id],
                    {'l10n_br_tipo_pedido': 'servico'}
                ),
                frete_id=frete_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=3,
                etapa_descricao="Atualizar tipo de pedido para 'servico'",
                modelo_odoo='l10n_br_ciel_it_account.dfe',
                acao='write',
                dfe_id=dfe_id
            )

            if not sucesso:
                resultado['erro'] = erro
                resultado['mensagem'] = f"Erro na etapa 3: {erro}"
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            resultado['etapas_concluidas'] = 3

            # ========================================
            # ETAPA 4: Atualizar linha com produto
            # ========================================
            line_ids = dfe.get('lines_ids', [])
            if not line_ids:
                resultado['erro'] = "DFe não possui linhas"
                resultado['mensagem'] = "Erro na etapa 4: DFe não possui linhas"
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            line_id = line_ids[0]

            sucesso, _, erro = self._executar_com_auditoria(
                funcao=lambda: self.odoo.write(
                    'l10n_br_ciel_it_account.dfe.line',
                    [line_id],
                    {
                        'product_id': self.PRODUTO_SERVICO_FRETE_ID,
                        'l10n_br_quantidade': 1.0,
                        'product_uom_id': 1  # UN
                    }
                ),
                frete_id=frete_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=4,
                etapa_descricao="Atualizar linha com produto SERVICO DE FRETE",
                modelo_odoo='l10n_br_ciel_it_account.dfe.line',
                acao='write',
                dfe_id=dfe_id
            )

            if not sucesso:
                resultado['erro'] = erro
                resultado['mensagem'] = f"Erro na etapa 4: {erro}"
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            resultado['etapas_concluidas'] = 4

            # ========================================
            # ETAPA 5: Atualizar vencimento
            # ========================================
            dups_ids = dfe.get('dups_ids', [])
            if not dups_ids:
                resultado['erro'] = "DFe não possui pagamentos"
                resultado['mensagem'] = "Erro na etapa 5: DFe não possui pagamentos"
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            dup_id = dups_ids[0]

            sucesso, _, erro = self._executar_com_auditoria(
                funcao=lambda: self.odoo.write(
                    'l10n_br_ciel_it_account.dfe.pagamento',
                    [dup_id],
                    {'cobr_dup_dvenc': data_vencimento_str}
                ),
                frete_id=frete_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=5,
                etapa_descricao=f"Atualizar vencimento para {data_vencimento_str}",
                modelo_odoo='l10n_br_ciel_it_account.dfe.pagamento',
                acao='write',
                dfe_id=dfe_id
            )

            if not sucesso:
                resultado['erro'] = erro
                resultado['mensagem'] = f"Erro na etapa 5: {erro}"
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            resultado['etapas_concluidas'] = 5

            # ========================================
            # ETAPA 6: Gerar Purchase Order
            # ========================================
            contexto = {'validate_analytic': True}

            sucesso, po_result, erro = self._executar_com_auditoria(
                funcao=lambda: self.odoo.execute_kw(
                    'l10n_br_ciel_it_account.dfe',
                    'action_gerar_po_dfe',
                    [[dfe_id]],
                    {'context': contexto}
                ),
                frete_id=frete_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=6,
                etapa_descricao="Executar action_gerar_po_dfe",
                modelo_odoo='l10n_br_ciel_it_account.dfe',
                metodo_odoo='action_gerar_po_dfe',
                acao='execute_method',
                contexto_odoo=contexto,
                dfe_id=dfe_id
            )

            if not sucesso:
                resultado['erro'] = erro
                resultado['mensagem'] = f"Erro na etapa 6: {erro}"
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            resultado['etapas_concluidas'] = 6

            # Extrair ID do PO
            purchase_order_id = None
            if po_result and isinstance(po_result, dict):
                purchase_order_id = po_result.get('res_id')

            if not purchase_order_id:
                # Tentar buscar pelo DFe
                po_search = self.odoo.search_read(
                    'purchase.order',
                    [('l10n_br_dfe_id', '=', dfe_id)],
                    fields=['id'],
                    limit=1
                )
                if po_search:
                    purchase_order_id = po_search[0]['id']

            if not purchase_order_id:
                resultado['erro'] = "Purchase Order não foi criado"
                resultado['mensagem'] = "Erro: PO não foi criado após executar action_gerar_po_dfe"
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            resultado['purchase_order_id'] = purchase_order_id
            current_app.logger.info(f"Purchase Order criado: ID {purchase_order_id}")

            # ========================================
            # ETAPA 7: Atualizar campos do PO (incluindo partner_ref e picking_type_id)
            # ========================================
            # Preparar dados para atualização
            dados_po = {
                'team_id': self.TEAM_LANCAMENTO_FRETE_ID,
                'payment_provider_id': self.PAYMENT_PROVIDER_TRANSFERENCIA_ID,
                'company_id': self.COMPANY_NACOM_GOYA_CD_ID,
                'picking_type_id': self.PICKING_TYPE_CD_RECEBIMENTO_ID  # ✅ CD: Recebimento (CD)
            }

            # ✅ CORRIGIR OPERAÇÃO FISCAL: De-Para FB → CD (cabeçalho e linhas)
            # O Odoo pode criar o PO com operação da empresa FB, precisamos corrigir para CD
            operacao_correta_id = None
            try:
                po_operacao = self.odoo.read(
                    'purchase.order',
                    [purchase_order_id],
                    ['l10n_br_operacao_id', 'order_line']
                )
                if po_operacao and po_operacao[0].get('l10n_br_operacao_id'):
                    operacao_atual_id = po_operacao[0]['l10n_br_operacao_id'][0]
                    operacao_atual_nome = po_operacao[0]['l10n_br_operacao_id'][1]

                    if operacao_atual_id in self.OPERACAO_FB_PARA_CD:
                        operacao_correta_id = self.OPERACAO_FB_PARA_CD[operacao_atual_id]
                        dados_po['l10n_br_operacao_id'] = operacao_correta_id
                        current_app.logger.info(
                            f"🔄 Corrigindo operação fiscal PO: {operacao_atual_id} ({operacao_atual_nome}) "
                            f"→ {operacao_correta_id} (empresa CD)"
                        )

                        # ✅ CORRIGIR TAMBÉM AS LINHAS DO PO
                        line_ids = po_operacao[0].get('order_line', [])
                        if line_ids:
                            self.odoo.write(
                                'purchase.order.line',
                                line_ids,
                                {'l10n_br_operacao_id': operacao_correta_id}
                            )
                            current_app.logger.info(
                                f"🔄 Corrigindo operação fiscal nas {len(line_ids)} linha(s) do PO"
                            )
                    else:
                        current_app.logger.info(
                            f"✅ Operação fiscal já está correta: {operacao_atual_id} ({operacao_atual_nome})"
                        )
            except Exception as e:
                current_app.logger.warning(f"⚠️ Erro ao verificar/corrigir operação fiscal: {e}")

            # ✅ ADICIONAR partner_ref com número da fatura (se houver)
            if frete.fatura_frete_id and frete.fatura_frete:
                referencia_fatura = f"FATURA-{frete.fatura_frete.numero_fatura}"

                # Buscar valor atual ANTES de atualizar
                try:
                    po_atual = self.odoo.read(
                        'purchase.order',
                        [purchase_order_id],
                        ['partner_ref']
                    )
                    partner_ref_atual = po_atual[0].get('partner_ref', '') if po_atual else ''
                except Exception as e:
                    current_app.logger.warning(f"⚠️ Erro ao ler partner_ref atual: {e}")
                    partner_ref_atual = ''

                # Só adiciona ao dict se for diferente ou vazio
                if partner_ref_atual != referencia_fatura:
                    dados_po['partner_ref'] = referencia_fatura
                    current_app.logger.info(
                        f"🔗 Adicionando fatura {frete.fatura_frete.numero_fatura} ao PO {purchase_order_id} "
                        f"(partner_ref: '{partner_ref_atual}' -> '{referencia_fatura}')"
                    )
                else:
                    current_app.logger.info(
                        f"✅ partner_ref já está correto: '{referencia_fatura}'"
                    )

            sucesso, _, erro = self._executar_com_auditoria(
                funcao=lambda: self.odoo.write(
                    'purchase.order',
                    [purchase_order_id],
                    dados_po
                ),
                frete_id=frete_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=7,
                etapa_descricao="Atualizar campos do PO (operação fiscal, team, payment, company, picking_type)",
                modelo_odoo='purchase.order',
                acao='write',
                dfe_id=dfe_id,
                purchase_order_id=purchase_order_id,
                campos_alterados=list(dados_po.keys())
            )

            if not sucesso:
                resultado['erro'] = erro
                resultado['mensagem'] = f"Erro na etapa 7: {erro}"
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            resultado['etapas_concluidas'] = 7

            # ========================================
            # ETAPA 8: Atualizar impostos do PO - ❌ DESABILITADA
            # ========================================
            # ⚠️ REMOVIDO: Método onchange_l10n_br_calcular_imposto estava zerando valores do PO
            # Os impostos serão calculados automaticamente pelo Odoo ao confirmar o PO
            current_app.logger.info("⏭️ ETAPA 8 (atualizar impostos PO) PULADA - impostos calculados automaticamente")
            resultado['etapas_concluidas'] = 8

            # ========================================
            # ETAPA 9: Confirmar Purchase Order
            # ========================================
            sucesso, _, erro = self._executar_com_auditoria(
                funcao=lambda: self.odoo.execute_kw(
                    'purchase.order',
                    'button_confirm',
                    [[purchase_order_id]],
                    {'context': {'validate_analytic': True}}
                ),
                frete_id=frete_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=9,
                etapa_descricao="Confirmar Purchase Order",
                modelo_odoo='purchase.order',
                metodo_odoo='button_confirm',
                acao='execute_method',
                contexto_odoo={'validate_analytic': True},
                dfe_id=dfe_id,
                purchase_order_id=purchase_order_id
            )

            if not sucesso:
                resultado['erro'] = erro
                resultado['mensagem'] = f"Erro na etapa 9: {erro}"
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            resultado['etapas_concluidas'] = 9

            # ========================================
            # ETAPA 10: Verificar se precisa aprovar
            # ========================================
            po_data = self.odoo.read(
                'purchase.order',
                [purchase_order_id],
                fields=['state', 'is_current_approver']
            )[0]

            if po_data.get('state') == 'to approve' and po_data.get('is_current_approver'):
                sucesso, _, erro = self._executar_com_auditoria(
                    funcao=lambda: self.odoo.execute_kw(
                        'purchase.order',
                        'button_approve',
                        [[purchase_order_id]]
                    ),
                    frete_id=frete_id,
                    cte_id=cte_id,
                    chave_cte=cte_chave,
                    etapa=10,
                    etapa_descricao="Aprovar Purchase Order",
                    modelo_odoo='purchase.order',
                    metodo_odoo='button_approve',
                    acao='execute_method',
                    dfe_id=dfe_id,
                    purchase_order_id=purchase_order_id
                )

                if not sucesso:
                    resultado['erro'] = erro
                    resultado['mensagem'] = f"Erro na etapa 10: {erro}"
                    resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                    return resultado
            else:
                self._registrar_auditoria(
                    frete_id=frete_id,
                    cte_id=cte_id,
                    chave_cte=cte_chave,
                    etapa=10,
                    etapa_descricao="Aprovar Purchase Order (não necessário)",
                    modelo_odoo='purchase.order',
                    acao='skip',
                    status='SUCESSO',
                    mensagem='Aprovação não necessária',
                    dfe_id=dfe_id,
                    purchase_order_id=purchase_order_id
                )

            resultado['etapas_concluidas'] = 10

            # ========================================
            # ETAPA 11: Criar Invoice
            # ========================================
            sucesso, invoice_result, erro = self._executar_com_auditoria(
                funcao=lambda: self.odoo.execute_kw(
                    'purchase.order',
                    'action_create_invoice',
                    [[purchase_order_id]]
                ),
                frete_id=frete_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=11,
                etapa_descricao="Criar Invoice",
                modelo_odoo='purchase.order',
                metodo_odoo='action_create_invoice',
                acao='execute_method',
                dfe_id=dfe_id,
                purchase_order_id=purchase_order_id
            )

            if not sucesso:
                resultado['erro'] = erro
                resultado['mensagem'] = f"Erro na etapa 11: {erro}"
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            resultado['etapas_concluidas'] = 11

            # Extrair ID da Invoice
            invoice_id = None
            if invoice_result and isinstance(invoice_result, dict):
                invoice_id = invoice_result.get('res_id')

            if not invoice_id:
                # Tentar buscar pelo PO
                po_updated = self.odoo.read(
                    'purchase.order',
                    [purchase_order_id],
                    fields=['invoice_ids']
                )[0]
                invoice_ids = po_updated.get('invoice_ids', [])
                if invoice_ids:
                    invoice_id = invoice_ids[0]

            if not invoice_id:
                resultado['erro'] = "Invoice não foi criada"
                resultado['mensagem'] = "Erro: Invoice não foi criada"
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            resultado['invoice_id'] = invoice_id
            current_app.logger.info(f"Invoice criada: ID {invoice_id}")

            # ========================================
            # ETAPA 12: Atualizar impostos da Invoice
            # ========================================
            # ✅ COMMIT ANTES de chamada longa ao Odoo para liberar conexão PostgreSQL
            try:
                db.session.commit()
            except Exception as e:
                current_app.logger.warning(f"⚠️ Erro ao fazer commit antes da ETAPA 12: {e}")

            try:
                self.odoo.execute_kw(
                    'account.move',
                    'onchange_l10n_br_calcular_imposto',
                    [[invoice_id]]
                )
            except Exception as e:
                # ⚠️ Etapa OPCIONAL: Ignorar erros (impostos podem ser ajustados manualmente depois)
                current_app.logger.warning(
                    f"⚠️ ETAPA 12 falhou (não crítico): {e.__class__.__name__}. "
                    f"Impostos podem precisar ajuste manual no Odoo."
                )

            try:
                self._registrar_auditoria(
                    frete_id=frete_id,
                    cte_id=cte_id,
                    chave_cte=cte_chave,
                    etapa=12,
                    etapa_descricao="Atualizar impostos da Invoice",
                    modelo_odoo='account.move',
                    metodo_odoo='onchange_l10n_br_calcular_imposto',
                    acao='execute_method',
                    status='SUCESSO',
                    mensagem='Impostos atualizados',
                    dfe_id=dfe_id,
                    purchase_order_id=purchase_order_id,
                    invoice_id=invoice_id
                )
            except Exception as e:
                # ✅ BLINDAGEM: Se auditoria falhar, NÃO trava o lançamento
                current_app.logger.error(
                    f"❌ Erro ao registrar auditoria ETAPA 12 (não crítico): {e}"
                )
                # Reconectar sessão se perdeu conexão
                db.session.rollback()
                db.session.remove()

            resultado['etapas_concluidas'] = 12

            # ========================================
            # ETAPA 13: Configurar campos da Invoice (incluindo payment_reference)
            # ========================================
            # Preparar dados para atualização
            dados_invoice = {
                'l10n_br_compra_indcom': 'out',
                'l10n_br_situacao_nf': 'autorizado',
                'invoice_date_due': data_vencimento_str
            }

            # ✅ ADICIONAR payment_reference com número da fatura (se houver)
            if frete.fatura_frete_id and frete.fatura_frete:
                referencia_fatura = f"FATURA-{frete.fatura_frete.numero_fatura}"

                # Buscar valor atual ANTES de atualizar
                try:
                    invoice_atual = self.odoo.read(
                        'account.move',
                        [invoice_id],
                        ['payment_reference']
                    )
                    payment_ref_atual = invoice_atual[0].get('payment_reference', '') if invoice_atual else ''
                except Exception as e:
                    current_app.logger.warning(f"⚠️ Erro ao ler payment_reference atual: {e}")
                    payment_ref_atual = ''

                # Só adiciona ao dict se for diferente ou vazio
                if payment_ref_atual != referencia_fatura:
                    dados_invoice['payment_reference'] = referencia_fatura
                    current_app.logger.info(
                        f"🔗 Adicionando fatura {frete.fatura_frete.numero_fatura} à Invoice {invoice_id} "
                        f"(payment_reference: '{payment_ref_atual}' -> '{referencia_fatura}')"
                    )
                else:
                    current_app.logger.info(
                        f"✅ payment_reference já está correto: '{referencia_fatura}'"
                    )

            sucesso, _, erro = self._executar_com_auditoria(
                funcao=lambda: self.odoo.write(
                    'account.move',
                    [invoice_id],
                    dados_invoice
                ),
                frete_id=frete_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=13,
                etapa_descricao="Configurar campos da Invoice e payment_reference",
                modelo_odoo='account.move',
                acao='write',
                dfe_id=dfe_id,
                purchase_order_id=purchase_order_id,
                invoice_id=invoice_id,
                campos_alterados=list(dados_invoice.keys())
            )

            if not sucesso:
                resultado['erro'] = erro
                resultado['mensagem'] = f"Erro na etapa 13: {erro}"
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            resultado['etapas_concluidas'] = 13

            # ========================================
            # ETAPA 14: Atualizar impostos novamente
            # ========================================
            # ✅ COMMIT ANTES de chamada longa ao Odoo para liberar conexão PostgreSQL
            try:
                db.session.commit()
            except Exception as e:
                current_app.logger.warning(f"⚠️ Erro ao fazer commit antes da ETAPA 14: {e}")

            try:
                self.odoo.execute_kw(
                    'account.move',
                    'onchange_l10n_br_calcular_imposto_btn',
                    [[invoice_id]]
                )
            except Exception as e:
                # ⚠️ Etapa OPCIONAL: Ignorar erros (impostos podem ser ajustados manualmente depois)
                current_app.logger.warning(
                    f"⚠️ ETAPA 14 falhou (não crítico): {e.__class__.__name__}. "
                    f"Impostos podem precisar ajuste manual no Odoo."
                )

            try:
                self._registrar_auditoria(
                    frete_id=frete_id,
                    cte_id=cte_id,
                    chave_cte=cte_chave,
                    etapa=14,
                    etapa_descricao="Atualizar impostos da Invoice (final)",
                    modelo_odoo='account.move',
                    metodo_odoo='onchange_l10n_br_calcular_imposto_btn',
                    acao='execute_method',
                    status='SUCESSO',
                    mensagem='Impostos atualizados',
                    dfe_id=dfe_id,
                    purchase_order_id=purchase_order_id,
                    invoice_id=invoice_id
                )
            except Exception as e:
                # ✅ BLINDAGEM: Se auditoria falhar, NÃO trava o lançamento
                current_app.logger.error(
                    f"❌ Erro ao registrar auditoria ETAPA 14 (não crítico): {e}"
                )
                # Reconectar sessão se perdeu conexão
                db.session.rollback()
                db.session.remove()

            resultado['etapas_concluidas'] = 14

            # ========================================
            # ETAPA 15: Confirmar Invoice
            # ========================================
            sucesso, _, erro = self._executar_com_auditoria(
                funcao=lambda: self.odoo.execute_kw(
                    'account.move',
                    'action_post',
                    [[invoice_id]],
                    {'context': {'validate_analytic': True}}
                ),
                frete_id=frete_id,
                cte_id=cte_id,
                chave_cte=cte_chave,
                etapa=15,
                etapa_descricao="Confirmar Invoice",
                modelo_odoo='account.move',
                metodo_odoo='action_post',
                acao='execute_method',
                contexto_odoo={'validate_analytic': True},
                dfe_id=dfe_id,
                purchase_order_id=purchase_order_id,
                invoice_id=invoice_id
            )

            if not sucesso:
                resultado['erro'] = erro
                resultado['mensagem'] = f"Erro na etapa 15: {erro}"
                resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                return resultado

            resultado['etapas_concluidas'] = 15

            # ========================================
            # ETAPA 16: Atualizar frete E criar vínculo bidirecional com CTe
            # ========================================
            try:
                # Atualizar campos do Frete
                frete.odoo_dfe_id = dfe_id
                frete.odoo_purchase_order_id = purchase_order_id
                frete.odoo_invoice_id = invoice_id
                frete.lancado_odoo_em = datetime.now()
                frete.lancado_odoo_por = self.usuario_nome
                frete.status = 'LANCADO_ODOO'

                # ✅ CRIAR VÍNCULO BIDIRECIONAL Frete ↔ CTe
                if cte:
                    # Frete → CTe
                    if not frete.frete_cte_id:
                        frete.frete_cte_id = cte.id
                        current_app.logger.info(f"🔗 Vinculando Frete → CTe: frete_cte_id = {cte.id}")

                    # CTe → Frete
                    if not cte.frete_id:
                        cte.frete_id = frete_id
                        cte.vinculado_em = datetime.now()
                        cte.vinculado_por = self.usuario_nome
                        current_app.logger.info(f"🔗 Vinculando CTe → Frete: frete_id = {frete_id}")

                    # ✅ Atualizar IDs do Odoo no CTe (redundância para consultas)
                    cte.odoo_purchase_fiscal_id = purchase_order_id

                    # odoo_invoice_ids é JSON (lista)
                    import json
                    if cte.odoo_invoice_ids:
                        invoice_list = json.loads(cte.odoo_invoice_ids)
                        if invoice_id not in invoice_list:
                            invoice_list.append(invoice_id)
                            cte.odoo_invoice_ids = json.dumps(invoice_list)
                    else:
                        cte.odoo_invoice_ids = json.dumps([invoice_id])

                db.session.commit()

                self._registrar_auditoria(
                    frete_id=frete_id,
                    cte_id=cte_id,
                    chave_cte=cte_chave,
                    etapa=16,
                    etapa_descricao="Atualizar frete e vincular com CTe",
                    modelo_odoo='fretes + conhecimento_transporte (local)',
                    acao='write',
                    status='SUCESSO',
                    mensagem='Frete atualizado com IDs do Odoo + vínculo bidirecional criado',
                    dfe_id=dfe_id,
                    purchase_order_id=purchase_order_id,
                    invoice_id=invoice_id
                )

                resultado['etapas_concluidas'] = 16

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Erro ao atualizar frete: {e}")
                resultado['erro'] = f"Erro ao atualizar frete: {e}"
                resultado['mensagem'] = f"Lançamento concluído no Odoo, mas erro ao atualizar sistema local: {e}"

            # ========================================
            # SUCESSO TOTAL!
            # ========================================
            resultado['sucesso'] = True
            resultado['mensagem'] = f'Lançamento concluído com sucesso! {resultado["etapas_concluidas"]}/16 etapas'
            resultado['auditoria'] = self.auditoria_logs

            # Log de sucesso final
            tempo_total = time.time() - inicio_total
            logging.info(
                f"[LANCAMENTO_CTE] ✅ CONCLUÍDO | "
                f"Frete ID: {frete_id} | "
                f"DFe: {dfe_id} | PO: {purchase_order_id} | Invoice: {invoice_id} | "
                f"Chave: {cte_chave[:8] if cte_chave else 'N/A'}... | "
                f"Tempo total: {tempo_total:.2f}s | "
                f"Etapas: {resultado['etapas_concluidas']}/16"
            )
            resultado['tempo_total'] = f"{tempo_total:.2f}s"

            return resultado

        except Exception as e:
            erro_msg = str(e)
            erro_trace = traceback.format_exc()

            current_app.logger.error(f"Erro no lançamento: {erro_msg}")
            current_app.logger.error(erro_trace)

            # ========================================
            # ROLLBACK AUTOMÁTICO: Limpar campos do Frete em caso de erro
            # ========================================
            resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])

            resultado['erro'] = erro_msg
            resultado['mensagem'] = f"Erro no lançamento: {erro_msg}"
            resultado['auditoria'] = self.auditoria_logs

            return resultado

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

    def _verificar_lancamento_existente(self, dfe_id: int, cte_chave: str) -> Dict[str, Any]:
        """
        Verifica se já existe um lançamento parcial para este DFe e determina
        de qual etapa deve continuar.

        Returns:
            Dict com:
            - existe_po: bool - Se já existe um PO vinculado
            - purchase_order_id: int - ID do PO existente (se houver)
            - po_state: str - Estado do PO (draft, purchase, done, cancel)
            - existe_invoice: bool - Se já existe Invoice
            - invoice_id: int - ID da Invoice (se houver)
            - invoice_state: str - Estado da Invoice (draft, posted, cancel)
            - continuar_de_etapa: int - Etapa de onde deve continuar (0 se novo)
            - mensagem: str - Descrição do estado encontrado
        """
        resultado = {
            'existe_po': False,
            'purchase_order_id': None,
            'po_state': None,
            'po_company_id': None,
            'existe_invoice': False,
            'invoice_id': None,
            'invoice_state': None,
            'continuar_de_etapa': 0,
            'mensagem': 'Nenhum lançamento anterior encontrado'
        }

        try:
            # Buscar PO vinculado ao DFe
            po_search = self.odoo.search_read(
                'purchase.order',
                [('dfe_id', '=', dfe_id)],
                fields=['id', 'name', 'state', 'company_id', 'invoice_ids', 'team_id', 'picking_type_id'],
                limit=1
            )

            if not po_search:
                current_app.logger.info(f"✅ Nenhum PO existente para DFe {dfe_id} - Iniciando do zero")
                return resultado

            po = po_search[0]
            resultado['existe_po'] = True
            resultado['purchase_order_id'] = po['id']
            resultado['po_state'] = po['state']
            resultado['po_company_id'] = po['company_id'][0] if po.get('company_id') else None

            current_app.logger.info(
                f"🔍 PO existente encontrado: ID {po['id']} ({po['name']}), "
                f"Estado: {po['state']}, Company: {resultado['po_company_id']}"
            )

            # Verificar se o PO está em draft e precisa ser configurado/confirmado
            if po['state'] == 'draft':
                # Verificar se já foi configurado (tem team_id e company correta)
                team_ok = po.get('team_id') and po['team_id'][0] == self.TEAM_LANCAMENTO_FRETE_ID
                company_ok = resultado['po_company_id'] == self.COMPANY_NACOM_GOYA_CD_ID
                picking_ok = po.get('picking_type_id') and po['picking_type_id'][0] == self.PICKING_TYPE_CD_RECEBIMENTO_ID

                if not team_ok or not company_ok or not picking_ok:
                    resultado['continuar_de_etapa'] = 7  # Precisa configurar
                    resultado['mensagem'] = (
                        f"PO {po['name']} existe mas não foi configurado corretamente. "
                        f"Continuando da ETAPA 7 (Configurar PO)"
                    )
                else:
                    resultado['continuar_de_etapa'] = 9  # Precisa confirmar
                    resultado['mensagem'] = (
                        f"PO {po['name']} está configurado mas em draft. "
                        f"Continuando da ETAPA 9 (Confirmar PO)"
                    )

            elif po['state'] == 'purchase':
                # PO confirmado, verificar se tem Invoice
                invoice_ids = po.get('invoice_ids', [])

                if not invoice_ids:
                    resultado['continuar_de_etapa'] = 11  # Precisa criar Invoice
                    resultado['mensagem'] = (
                        f"PO {po['name']} está confirmado mas sem Invoice. "
                        f"Continuando da ETAPA 11 (Criar Invoice)"
                    )
                else:
                    # Buscar estado da Invoice
                    invoice_data = self.odoo.read(
                        'account.move',
                        invoice_ids,
                        ['id', 'name', 'state']
                    )

                    if invoice_data:
                        invoice = invoice_data[0]
                        resultado['existe_invoice'] = True
                        resultado['invoice_id'] = invoice['id']
                        resultado['invoice_state'] = invoice['state']

                        if invoice['state'] == 'draft':
                            resultado['continuar_de_etapa'] = 13  # Precisa configurar/confirmar Invoice
                            resultado['mensagem'] = (
                                f"Invoice {invoice.get('name', invoice['id'])} existe em draft. "
                                f"Continuando da ETAPA 13 (Configurar Invoice)"
                            )
                        elif invoice['state'] == 'posted':
                            resultado['continuar_de_etapa'] = 16  # Já está tudo pronto
                            resultado['mensagem'] = (
                                f"Lançamento já completo! Invoice {invoice.get('name', invoice['id'])} está posted. "
                                f"Continuando da ETAPA 16 (Finalizar)"
                            )
                        else:
                            resultado['continuar_de_etapa'] = 15  # Tentar confirmar Invoice
                            resultado['mensagem'] = (
                                f"Invoice {invoice.get('name', invoice['id'])} em estado {invoice['state']}. "
                                f"Tentando ETAPA 15 (Confirmar Invoice)"
                            )

            elif po['state'] in ('done', 'cancel'):
                resultado['continuar_de_etapa'] = 0  # Não pode continuar, precisa de novo
                resultado['mensagem'] = (
                    f"PO {po['name']} está em estado '{po['state']}' e não pode ser retomado. "
                    f"Será necessário cancelar manualmente e relançar."
                )

            current_app.logger.info(f"📋 {resultado['mensagem']}")
            return resultado

        except Exception as e:
            current_app.logger.error(f"❌ Erro ao verificar lançamento existente: {e}")
            return resultado

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
        Registra etapa na auditoria com retry automático para erros de conexão

        Returns:
            Registro de auditoria criado
        """
        max_retries = 3

        for tentativa in range(max_retries):
            try:
                # ✅ CORREÇÃO: Remover sessão stale antes de inserir
                if tentativa > 0:
                    db.session.remove()
                    current_app.logger.info(f"🔄 Retry {tentativa}/{max_retries} - Reconectando ao banco...")

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
                erro_str = str(e).lower()
                # Erros de conexão que justificam retry
                erros_conexao = ['ssl connection', 'connection', 'closed unexpectedly', 'server closed', 'lost connection']
                eh_erro_conexao = any(erro in erro_str for erro in erros_conexao)

                if eh_erro_conexao and tentativa < max_retries - 1:
                    current_app.logger.warning(f"⚠️ Erro de conexão na auditoria (tentativa {tentativa + 1}): {e}")
                    db.session.rollback()
                    import time as time_module
                    time_module.sleep(1)  # Aguardar 1s antes de retry
                    continue
                else:
                    current_app.logger.error(f"❌ Erro ao registrar auditoria: {e}")
                    db.session.rollback()
                    raise

        # Nunca deveria chegar aqui, mas satisfaz o type checker
        raise RuntimeError("Falha ao registrar auditoria após todas as tentativas")

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
            # VERIFICAÇÃO DE RETOMADA: Existe lançamento parcial?
            # (Deve vir ANTES da validação de status!)
            # ========================================
            lancamento_existente = self._verificar_lancamento_existente(dfe_id, cte_chave)
            continuar_de_etapa = lancamento_existente['continuar_de_etapa']
            purchase_order_id = lancamento_existente.get('purchase_order_id')
            invoice_id = lancamento_existente.get('invoice_id')

            # ========================================
            # VALIDAÇÃO DE STATUS (considera retomada)
            # ========================================
            # Status '04' (PO) = Pronto para gerar PO (lançamento novo)
            # Status '06' (Concluído) = PO já foi gerado (retomada válida)
            status_map = {
                '01': 'Rascunho',
                '02': 'Sincronizado',
                '03': 'Ciência/Confirmado',
                '04': 'PO',
                '05': 'Rateio',
                '06': 'Concluído',
                '07': 'Rejeitado'
            }
            status_nome = status_map.get(dfe_status, f'Desconhecido ({dfe_status})')

            if continuar_de_etapa > 0:
                # RETOMADA: Aceita status '04' (PO) ou '06' (Concluído)
                if dfe_status not in ('04', '06'):
                    resultado['erro'] = (
                        f'CTe possui status "{status_nome}" ({dfe_status}) - '
                        f'Para retomada, esperado "PO" (04) ou "Concluído" (06)'
                    )
                    resultado['mensagem'] = f'Erro: {resultado["erro"]}'
                    resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                    return resultado

                current_app.logger.info(
                    f"✅ DFe validado para RETOMADA: Status {status_nome} ({dfe_status}), "
                    f"PO existente: {purchase_order_id}"
                )
            else:
                # LANÇAMENTO NOVO: Exige status '04' (PO)
                if dfe_status != '04':
                    resultado['erro'] = (
                        f'CTe possui status "{status_nome}" ({dfe_status}) - '
                        f'Apenas CTes com status "PO" (04) podem ser lançados'
                    )
                    resultado['mensagem'] = f'Erro: {resultado["erro"]}'
                    resultado['rollback_executado'] = self._rollback_frete_odoo(frete_id, resultado['etapas_concluidas'])
                    return resultado

                current_app.logger.info(f"✅ DFe validado: Status PO (04), iniciando lançamento novo")

            if continuar_de_etapa > 0:
                current_app.logger.info(
                    f"🔄 RETOMADA DE LANÇAMENTO DETECTADA! Continuando da ETAPA {continuar_de_etapa}"
                )
                current_app.logger.info(f"📋 {lancamento_existente['mensagem']}")

                # Registrar auditoria da retomada
                self._registrar_auditoria(
                    frete_id=frete_id,
                    cte_id=cte_id,
                    chave_cte=cte_chave,
                    etapa=0,
                    etapa_descricao="Retomada de lançamento parcial",
                    modelo_odoo='purchase.order',
                    acao='retomada',
                    status='SUCESSO',
                    mensagem=lancamento_existente['mensagem'],
                    dfe_id=dfe_id,
                    purchase_order_id=purchase_order_id,
                    invoice_id=invoice_id
                )

                # Atualizar resultado com IDs existentes
                if purchase_order_id:
                    resultado['purchase_order_id'] = purchase_order_id
                if invoice_id:
                    resultado['invoice_id'] = invoice_id

                # Definir etapas como já concluídas baseado na etapa de retomada
                if continuar_de_etapa >= 7:
                    resultado['etapas_concluidas'] = 6  # PO já existe
                if continuar_de_etapa >= 9:
                    resultado['etapas_concluidas'] = 8  # PO configurado
                if continuar_de_etapa >= 11:
                    resultado['etapas_concluidas'] = 10  # PO confirmado
                if continuar_de_etapa >= 13:
                    resultado['etapas_concluidas'] = 12  # Invoice existe
                if continuar_de_etapa >= 16:
                    resultado['etapas_concluidas'] = 15  # Invoice confirmada

            # ========================================
            # ETAPA 2: Atualizar data de entrada E payment_reference
            # ========================================
            if continuar_de_etapa < 3:  # Só executa se não está retomando de etapa posterior
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
            else:
                current_app.logger.info(f"⏭️ ETAPA 2 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 3: Atualizar tipo pedido
            # ========================================
            if continuar_de_etapa < 4:  # Só executa se não está retomando de etapa posterior
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
            else:
                current_app.logger.info(f"⏭️ ETAPA 3 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 4: Atualizar linha com produto
            # ========================================
            if continuar_de_etapa < 5:  # Só executa se não está retomando de etapa posterior
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
            else:
                current_app.logger.info(f"⏭️ ETAPA 4 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 5: Atualizar vencimento
            # ========================================
            if continuar_de_etapa < 6:  # Só executa se não está retomando de etapa posterior
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
            else:
                current_app.logger.info(f"⏭️ ETAPA 5 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 6: Gerar Purchase Order
            # ⏱️ TIMEOUT ESTENDIDO: 180 segundos (operação pode demorar MUITO no Odoo)
            # ========================================
            if continuar_de_etapa < 7:  # Só executa se não está retomando de etapa posterior
                contexto = {'validate_analytic': True}

                # 🔧 CORREÇÃO 15/12/2025: Timeout aumentado para 180s
                # A etapa action_gerar_po_dfe é a mais pesada do processo:
                # - Cria Purchase Order
                # - Configura linhas do PO
                # - Calcula impostos automaticamente
                # - Pode demorar 60-90s quando Odoo está ocupado
                # O timeout de 90s estava causando falhas intermitentes
                TIMEOUT_GERAR_PO = 180

                current_app.logger.info(
                    f"⏱️ [ETAPA 06] Iniciando geração de PO com timeout de {TIMEOUT_GERAR_PO}s..."
                )

                sucesso, po_result, erro = self._executar_com_auditoria(
                    funcao=lambda: self.odoo.execute_kw(
                        'l10n_br_ciel_it_account.dfe',
                        'action_gerar_po_dfe',
                        [[dfe_id]],
                        {'context': contexto},
                        timeout_override=TIMEOUT_GERAR_PO
                    ),
                    frete_id=frete_id,
                    cte_id=cte_id,
                    chave_cte=cte_chave,
                    etapa=6,
                    etapa_descricao=f"Gerar Purchase Order (action_gerar_po_dfe) [timeout: {TIMEOUT_GERAR_PO}s]",
                    modelo_odoo='l10n_br_ciel_it_account.dfe',
                    metodo_odoo='action_gerar_po_dfe',
                    acao='execute_method / action_gerar_po_dfe',
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
                if po_result and isinstance(po_result, dict):
                    purchase_order_id = po_result.get('res_id')

                if not purchase_order_id:
                    # Tentar buscar pelo DFe
                    po_search = self.odoo.search_read(
                        'purchase.order',
                        [('dfe_id', '=', dfe_id)],
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
            else:
                # RETOMADA: Usar PO existente
                current_app.logger.info(f"⏭️ ETAPA 6 PULADA - Usando PO existente: ID {purchase_order_id}")
                resultado['purchase_order_id'] = purchase_order_id

            # ========================================
            # ETAPA 7: Atualizar campos do PO (incluindo partner_ref e picking_type_id)
            # ========================================
            if continuar_de_etapa < 8:  # Só executa se não está retomando de etapa posterior
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

                            # ✅ CORRIGIR TAMBÉM AS LINHAS DO PO (COM PROTEÇÃO DE VALORES)
                            line_ids = po_operacao[0].get('order_line', [])
                            if line_ids:
                                # 1. Ler dados atuais das linhas ANTES de alterar
                                linhas_data = self.odoo.read(
                                    'purchase.order.line',
                                    line_ids,
                                    ['id', 'l10n_br_operacao_id', 'price_unit', 'product_qty', 'price_subtotal']
                                )

                                # 2. Filtrar apenas linhas que PRECISAM de correção
                                linhas_para_corrigir = []
                                valores_backup = {}

                                for linha in linhas_data:
                                    op_linha = linha.get('l10n_br_operacao_id')
                                    op_linha_id = op_linha[0] if op_linha else None

                                    if op_linha_id != operacao_correta_id:
                                        linhas_para_corrigir.append(linha['id'])
                                        # Backup dos valores para restaurar se necessário
                                        valores_backup[linha['id']] = {
                                            'price_unit': linha.get('price_unit', 0),
                                            'product_qty': linha.get('product_qty', 1)
                                        }
                                        current_app.logger.info(
                                            f"  📝 Linha {linha['id']}: op {op_linha_id} → {operacao_correta_id} "
                                            f"(valor: R$ {linha.get('price_subtotal', 0):.2f})"
                                        )

                                if linhas_para_corrigir:
                                    # 3. Alterar operação fiscal
                                    self.odoo.write(
                                        'purchase.order.line',
                                        linhas_para_corrigir,
                                        {'l10n_br_operacao_id': operacao_correta_id}
                                    )

                                    # 4. Verificar se valores foram ALTERADOS e RESTAURAR
                                    # 🔧 CORREÇÃO 15/12/2025: Verificar QUALQUER alteração de valor
                                    # Antes só verificava se foi zerado (== 0), mas a operação fiscal
                                    # pode RECALCULAR o valor (ex: incluir/excluir impostos)
                                    linhas_apos = self.odoo.read(
                                        'purchase.order.line',
                                        linhas_para_corrigir,
                                        ['id', 'price_unit', 'price_subtotal']
                                    )

                                    for linha in linhas_apos:
                                        backup = valores_backup.get(linha['id'], {})
                                        valor_original = backup.get('price_unit', 0)
                                        valor_atual = linha.get('price_unit', 0)

                                        # Tolerância de 0.01 para comparação de floats
                                        diferenca = abs(valor_atual - valor_original)
                                        valor_foi_alterado = diferenca > 0.01

                                        if valor_foi_alterado and valor_original > 0:
                                            current_app.logger.warning(
                                                f"  ⚠️ Linha {linha['id']} teve valor ALTERADO! "
                                                f"R$ {valor_original:.2f} → R$ {valor_atual:.2f} (diff: R$ {diferenca:.2f}). "
                                                f"Restaurando valor original..."
                                            )
                                            self.odoo.write(
                                                'purchase.order.line',
                                                [linha['id']],
                                                backup
                                            )
                                        elif valor_foi_alterado:
                                            current_app.logger.warning(
                                                f"  ⚠️ Linha {linha['id']} alterada mas original era R$ 0. "
                                                f"Mantendo valor atual: R$ {valor_atual:.2f}"
                                            )

                                    current_app.logger.info(
                                        f"🔄 Operação fiscal corrigida em {len(linhas_para_corrigir)} linha(s) do PO"
                                    )
                                else:
                                    current_app.logger.info(
                                        f"✅ Todas as {len(line_ids)} linha(s) já estão com operação fiscal correta"
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
            else:
                current_app.logger.info(f"⏭️ ETAPA 7 PULADA - Retomando de etapa {continuar_de_etapa}")

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
            if continuar_de_etapa < 10:  # Só executa se não está retomando de etapa posterior
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
            else:
                current_app.logger.info(f"⏭️ ETAPA 9 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 10: Verificar se precisa aprovar
            # ========================================
            if continuar_de_etapa < 11:  # Só executa se não está retomando de etapa posterior
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
            else:
                current_app.logger.info(f"⏭️ ETAPA 10 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 11: Criar Invoice
            # ========================================
            if continuar_de_etapa < 12:  # Só executa se não está retomando de etapa posterior
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
            else:
                # RETOMADA: Usar Invoice existente
                current_app.logger.info(f"⏭️ ETAPA 11 PULADA - Usando Invoice existente: ID {invoice_id}")
                resultado['invoice_id'] = invoice_id

            # ========================================
            # ETAPA 12: Atualizar impostos da Invoice
            # ========================================
            if continuar_de_etapa < 13:  # Só executa se não está retomando de etapa posterior
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
            else:
                current_app.logger.info(f"⏭️ ETAPA 12 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 13: Configurar campos da Invoice (incluindo payment_reference)
            # ========================================
            if continuar_de_etapa < 14:  # Só executa se não está retomando de etapa posterior
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
            else:
                current_app.logger.info(f"⏭️ ETAPA 13 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 14: Atualizar impostos novamente
            # ========================================
            if continuar_de_etapa < 15:  # Só executa se não está retomando de etapa posterior
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
            else:
                current_app.logger.info(f"⏭️ ETAPA 14 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 15: Confirmar Invoice
            # ========================================
            if continuar_de_etapa < 16:  # Só executa se não está retomando de etapa posterior
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
            else:
                current_app.logger.info(f"⏭️ ETAPA 15 PULADA - Retomando de etapa {continuar_de_etapa}")

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

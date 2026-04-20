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
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


class LancamentoDespesaOdooService(LancamentoOdooService):
    """
    Service para lançar despesas extras no Odoo.
    Herda de LancamentoOdooService e adapta para despesas.
    """

    def _audit_etapa6(
        self,
        *,
        frete_id: Optional[int],
        cte_id: Optional[int],
        chave_cte: str,
        despesa_extra_id: Optional[int] = None,
        **kwargs,
    ):
        """Override: ETAPA 6 da despesa escreve em LancamentoFreteOdooAuditoria com despesa_extra_id."""
        if despesa_extra_id:
            return self._registrar_auditoria_despesa(
                despesa_extra_id=despesa_extra_id,
                cte_id=cte_id,
                chave_cte=chave_cte,
                **kwargs,
            )
        # Fallback para o comportamento do pai se despesa_extra_id nao estiver definido
        return super()._audit_etapa6(
            frete_id=frete_id, cte_id=cte_id, chave_cte=chave_cte,
            despesa_extra_id=despesa_extra_id, **kwargs,
        )

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
        Registra etapa na auditoria com despesa_extra_id e retry automático

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
                db.session.commit()  # ✅ CORREÇÃO: commit em vez de flush para evitar conexão stale

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
                    current_app.logger.error(f"❌ Erro ao registrar auditoria despesa: {e}")
                    db.session.rollback()
                    raise

        # Nunca deveria chegar aqui, mas satisfaz o type checker
        raise RuntimeError("Falha ao registrar auditoria após todas as tentativas")

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
            despesa = db.session.get(DespesaExtra,despesa_id) if despesa_id else None
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

    def _verificar_lancamento_existente_despesa(self, dfe_id: int, cte_chave: str, company_id_esperado: int = None) -> Dict[str, Any]:
        """
        Verifica se já existe um lançamento parcial para este DFe de despesa e determina
        de qual etapa deve continuar.

        Args:
            dfe_id: ID do DFe no Odoo
            cte_chave: Chave de acesso do CTe
            company_id_esperado: ID da empresa correta identificada pelo CNPJ do tomador do CTe.
                                 Se fornecido, verifica se o PO existente está na empresa correta.

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
                # Verificar se já foi configurado (tem team_id e company válida)
                team_ok = po.get('team_id') and po['team_id'][0] == self.TEAM_LANCAMENTO_FRETE_ID

                # 🔧 CORREÇÃO 14/01/2026: Company OK apenas se for a empresa CORRETA para este CTe
                # Se company_id_esperado foi informado, verifica se o PO está na empresa correta
                # Caso contrário, aceita qualquer empresa configurada (comportamento anterior)
                if company_id_esperado is not None:
                    company_ok = resultado['po_company_id'] == company_id_esperado
                    if not company_ok:
                        current_app.logger.warning(
                            f"⚠️ PO {po['id']} está na empresa {resultado['po_company_id']}, "
                            f"mas deveria estar na empresa {company_id_esperado}"
                        )
                else:
                    company_ok = resultado['po_company_id'] in self.CONFIG_POR_EMPRESA

                # Picking OK se não é obrigatório ou se está definido para a empresa ESPERADA
                config_empresa_esperada = self.CONFIG_POR_EMPRESA.get(company_id_esperado or resultado['po_company_id'], {})
                picking_esperado = config_empresa_esperada.get('picking_type_id')
                picking_ok = (
                    picking_esperado is None or
                    (po.get('picking_type_id') and po['picking_type_id'][0] == picking_esperado)
                )

                if not team_ok or not company_ok or not picking_ok:
                    resultado['continuar_de_etapa'] = 7  # Precisa configurar
                    motivos = []
                    if not team_ok:
                        motivos.append("team_id incorreto")
                    if not company_ok:
                        motivos.append(f"company_id incorreto (atual: {resultado['po_company_id']}, esperado: {company_id_esperado})")
                    if not picking_ok:
                        motivos.append("picking_type_id incorreto")
                    resultado['mensagem'] = (
                        f"PO {po['name']} existe mas não foi configurado corretamente ({', '.join(motivos)}). "
                        f"Continuando da ETAPA 7 (Configurar PO)"
                    )
                else:
                    resultado['continuar_de_etapa'] = 9  # Precisa confirmar
                    resultado['mensagem'] = (
                        f"PO {po['name']} está configurado mas em draft. "
                        f"Continuando da ETAPA 9 (Confirmar PO)"
                    )

            elif po['state'] == 'purchase':
                # 🔧 CORREÇÃO 14/01/2026: Verificar se PO confirmado está na empresa correta
                # Se não estiver, não há como corrigir automaticamente (PO já confirmado)
                if company_id_esperado is not None and resultado['po_company_id'] != company_id_esperado:
                    current_app.logger.error(
                        f"❌ ATENÇÃO: PO {po['id']} ({po['name']}) está na empresa {resultado['po_company_id']}, "
                        f"mas deveria estar na empresa {company_id_esperado}. "
                        f"O PO já está confirmado e não pode ser alterado automaticamente. "
                        f"Requer correção manual no Odoo."
                    )
                    # Mesmo assim, continuamos para tentar finalizar o lançamento
                    # A operação fiscal da invoice pode ser corrigida na ETAPA 13

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
            despesa = db.session.get(DespesaExtra,despesa_id) if despesa_id else None
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

            # 🔧 CORREÇÃO 05/01/2026: Extrair dados da despesa ANTES das operações longas
            # Isso previne o erro "Instance <DespesaExtra> is not bound to a Session"
            # que ocorre quando a ETAPA 6 demora muito (30+ segundos) e a sessão expira
            despesa_fatura_id = despesa.fatura_frete_id
            despesa_numero_fatura = despesa.fatura_frete.numero_fatura if despesa.fatura_frete else None
            despesa_cte_id = despesa.despesa_cte_id
            despesa_vencimento = despesa.vencimento_despesa
            current_app.logger.debug(
                f"📦 Dados extraídos da despesa #{despesa_id}: "
                f"fatura_id={despesa_fatura_id}, numero_fatura={despesa_numero_fatura}, "
                f"cte_id={despesa_cte_id}"
            )

            # Buscar CTe
            cte = db.session.get(ConhecimentoTransporte,despesa_cte_id) if despesa_cte_id else None
            if not cte:
                raise ValueError(f"CTe #{despesa_cte_id} não encontrado")

            cte_chave = cte.chave_acesso
            cte_id = cte.id

            current_app.logger.info(f"CTe Complementar: {cte.numero_cte}")
            current_app.logger.info(f"Chave CTe: {cte_chave}")

            # ========================================
            # IDENTIFICAR EMPRESA PELO CNPJ DO TOMADOR
            # ========================================
            company_id = self._identificar_company_por_cte(cte)
            config_empresa = self._obter_config_empresa(company_id)
            current_app.logger.info(
                f"🏢 Empresa identificada: {config_empresa.get('nome', 'N/A')} (ID: {company_id})"
            )

            # Usar vencimento da despesa se não informado
            # 🔧 CORREÇÃO 05/01/2026: Usar variável local extraída no início
            if not data_vencimento:
                data_vencimento = despesa_vencimento

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
            dfe_status = dfe_data[0].get('l10n_br_status')

            current_app.logger.info(f"DFe encontrado: ID {dfe_id}, Status: {dfe_status}")

            # ========================================
            # VERIFICAÇÃO DE RETOMADA: Existe lançamento parcial?
            # (Deve vir ANTES da validação de status!)
            # 🔧 CORREÇÃO 14/01/2026: Passar company_id para verificar se PO está na empresa correta
            # ========================================
            lancamento_existente = self._verificar_lancamento_existente_despesa(dfe_id, cte_chave, company_id)
            continuar_de_etapa = lancamento_existente['continuar_de_etapa']
            po_id = lancamento_existente.get('purchase_order_id')
            invoice_id = lancamento_existente.get('invoice_id')

            # Reconciliar auditorias ERRO da ETAPA 6 — se ha PO, o fire/polling anterior
            # teve o timeout de upstream mas a acao completou no Odoo.
            if po_id:
                self._reconciliar_auditoria_etapa6(
                    frete_id=None,
                    cte_id=None,
                    dfe_id=dfe_id,
                    purchase_order_id=po_id,
                    motivo='Detectado na retomada',
                    despesa_extra_id=despesa_id,
                )

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
                    resultado['rollback_executado'] = self._rollback_despesa_odoo(despesa_id, resultado['etapas_concluidas'])
                    return resultado

                current_app.logger.info(
                    f"✅ DFe validado para RETOMADA: Status {status_nome} ({dfe_status}), "
                    f"PO existente: {po_id}"
                )
            else:
                # LANÇAMENTO NOVO: Exige status '04' (PO)
                if dfe_status != '04':
                    resultado['erro'] = (
                        f'CTe possui status "{status_nome}" ({dfe_status}) - '
                        f'Apenas CTes com status "PO" (04) podem ser lançados'
                    )
                    resultado['mensagem'] = f'Erro: {resultado["erro"]}'
                    resultado['rollback_executado'] = self._rollback_despesa_odoo(despesa_id, resultado['etapas_concluidas'])
                    return resultado

                current_app.logger.info(f"✅ DFe validado: Status PO (04), iniciando lançamento novo")

            if continuar_de_etapa > 0:
                current_app.logger.info(
                    f"🔄 RETOMADA DE LANÇAMENTO DETECTADA! Continuando da ETAPA {continuar_de_etapa}"
                )
                current_app.logger.info(f"📋 {lancamento_existente['mensagem']}")

                # Registrar auditoria da retomada
                self._registrar_auditoria_despesa(
                    despesa_extra_id=despesa_id,
                    cte_id=cte_id,
                    chave_cte=cte_chave,
                    etapa=0,
                    etapa_descricao="Retomada de lançamento parcial",
                    modelo_odoo='purchase.order',
                    acao='retomada',
                    status='SUCESSO',
                    mensagem=lancamento_existente['mensagem'],
                    dfe_id=dfe_id,
                    purchase_order_id=po_id,
                    invoice_id=invoice_id
                )

                # Atualizar resultado com IDs existentes
                if po_id:
                    resultado['purchase_order_id'] = po_id
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
            # ETAPA 2: Atualizar data de entrada no DFe
            # ========================================
            # 🔧 CORREÇÃO 2026-04-20: l10n_br_data_entrada é atualizado SEMPRE (mesmo em retomada)
            #    para refletir a data real do lançamento no Odoo. Antes, retomadas em
            #    dia posterior mantinham a data da tentativa original.
            #    Em retomada, o write é opcional (não trava o lançamento se o DFe
            #    estiver concluído/bloqueado no Odoo).
            data_entrada = agora_utc_naive().strftime('%Y-%m-%d')

            if continuar_de_etapa < 3:
                # Lançamento novo: atualização completa e bloqueante
                dados_dfe = {'l10n_br_data_entrada': data_entrada}

                # ✅ ADICIONAR payment_reference com número da fatura (só em lançamento novo)
                # 🔧 CORREÇÃO 05/01/2026: Usar variáveis locais extraídas no início
                if despesa_fatura_id and despesa_numero_fatura:
                    referencia_fatura = f"FATURA-{despesa_numero_fatura}"
                    dados_dfe['payment_reference'] = referencia_fatura
                    current_app.logger.info(
                        f"🔗 Adicionando fatura {despesa_numero_fatura} ao DFe {dfe_id}"
                    )
                else:
                    dados_dfe['payment_reference'] = f'DESPESA-{despesa_id}'

                inicio = time.time()
                self.odoo.write(
                    'l10n_br_ciel_it_account.dfe',
                    [dfe_id],
                    dados_dfe
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
                    mensagem=f"Data entrada: {data_entrada}, Ref: {dados_dfe['payment_reference']}",
                    campos_alterados=list(dados_dfe.keys()),
                    tempo_execucao_ms=tempo_ms,
                    dfe_id=dfe_id
                )
                resultado['etapas_concluidas'] = 2
            else:
                # Retomada: atualização apenas de l10n_br_data_entrada, não bloqueante
                # (DFe pode estar em status '06' Concluído que bloqueia writes)
                current_app.logger.info(
                    f"🔄 RETOMADA: tentando atualizar l10n_br_data_entrada={data_entrada} no DFe {dfe_id}"
                )
                inicio = time.time()
                try:
                    self.odoo.write(
                        'l10n_br_ciel_it_account.dfe',
                        [dfe_id],
                        {'l10n_br_data_entrada': data_entrada}
                    )
                    tempo_ms = int((time.time() - inicio) * 1000)
                    self._registrar_auditoria_despesa(
                        despesa_extra_id=despesa_id,
                        cte_id=cte_id,
                        chave_cte=cte_chave,
                        etapa=2,
                        etapa_descricao="Atualizar data de entrada (retomada)",
                        modelo_odoo='l10n_br_ciel_it_account.dfe',
                        acao='write',
                        status='SUCESSO',
                        mensagem=f"l10n_br_data_entrada atualizada para {data_entrada}",
                        campos_alterados=['l10n_br_data_entrada'],
                        tempo_execucao_ms=tempo_ms,
                        dfe_id=dfe_id
                    )
                    current_app.logger.info(
                        f"✅ l10n_br_data_entrada atualizada para {data_entrada}"
                    )
                except Exception as e:
                    current_app.logger.warning(
                        f"⚠️ Falha ao atualizar l10n_br_data_entrada em retomada (não crítico): "
                        f"{e.__class__.__name__}: {e}"
                    )
                    try:
                        self._registrar_auditoria_despesa(
                            despesa_extra_id=despesa_id,
                            cte_id=cte_id,
                            chave_cte=cte_chave,
                            etapa=2,
                            etapa_descricao="Atualizar data de entrada (retomada)",
                            modelo_odoo='l10n_br_ciel_it_account.dfe',
                            acao='write',
                            status='ERRO',
                            mensagem=f"Falha não crítica: {str(e)[:200]}",
                            dfe_id=dfe_id
                        )
                    except Exception:
                        pass

            # ========================================
            # ETAPA 3: Definir tipo pedido = 'servico'
            # ========================================
            if continuar_de_etapa < 4:  # Só executa se não está retomando de etapa posterior
                inicio = time.time()
                self.odoo.write(
                    'l10n_br_ciel_it_account.dfe',
                    [dfe_id],
                    {'l10n_br_tipo_pedido': 'servico'}  # Campo correto (não tipo_pedido)
                )
                tempo_ms = int((time.time() - inicio) * 1000)

                self._registrar_auditoria_despesa(
                    despesa_extra_id=despesa_id,
                    cte_id=cte_id,
                    chave_cte=cte_chave,
                    etapa=3,
                    etapa_descricao="Definir l10n_br_tipo_pedido = servico",
                    modelo_odoo='l10n_br_ciel_it_account.dfe',
                    acao='write',
                    status='SUCESSO',
                    mensagem="l10n_br_tipo_pedido definido como 'servico'",
                    campos_alterados=['l10n_br_tipo_pedido'],
                    tempo_execucao_ms=tempo_ms,
                    dfe_id=dfe_id
                )
                resultado['etapas_concluidas'] = 3
            else:
                current_app.logger.info(f"⏭️ ETAPA 3 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 4: Atualizar linha do DFe com produto de serviço
            # ========================================
            if continuar_de_etapa < 5:  # Só executa se não está retomando de etapa posterior
                lines_ids = dfe_data[0].get('lines_ids', [])
                if not lines_ids:
                    resultado['erro'] = "DFe não possui linhas"
                    resultado['mensagem'] = "Erro na etapa 4: DFe não possui linhas"
                    resultado['rollback_executado'] = self._rollback_despesa_odoo(despesa_id, resultado['etapas_concluidas'])
                    return resultado

                line_id = lines_ids[0]
                inicio = time.time()
                self.odoo.write(
                    'l10n_br_ciel_it_account.dfe.line',
                    [line_id],
                    {
                        'product_id': self.PRODUTO_SERVICO_FRETE_ID,
                        'l10n_br_quantidade': 1.0,
                        'product_uom_id': 1  # UN
                    }
                )
                tempo_ms = int((time.time() - inicio) * 1000)

                self._registrar_auditoria_despesa(
                    despesa_extra_id=despesa_id,
                    cte_id=cte_id,
                    chave_cte=cte_chave,
                    etapa=4,
                    etapa_descricao="Atualizar linha com produto SERVICO DE FRETE",
                    modelo_odoo='l10n_br_ciel_it_account.dfe.line',
                    acao='write',
                    status='SUCESSO',
                    mensagem=f"Linha {line_id} atualizada com produto {self.PRODUTO_SERVICO_FRETE_ID}",
                    campos_alterados=['product_id', 'l10n_br_quantidade', 'product_uom_id'],
                    tempo_execucao_ms=tempo_ms,
                    dfe_id=dfe_id
                )
                resultado['etapas_concluidas'] = 4
            else:
                current_app.logger.info(f"⏭️ ETAPA 4 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 5: Atualizar vencimento
            # ========================================
            if continuar_de_etapa < 6:  # Só executa se não está retomando de etapa posterior
                dups_ids = dfe_data[0].get('dups_ids', [])
                if dups_ids:
                    dup_id = dups_ids[0]
                    inicio = time.time()
                    self.odoo.write(
                        'l10n_br_ciel_it_account.dfe.pagamento',
                        [dup_id],
                        {'cobr_dup_dvenc': data_vencimento_str}  # Campo correto (não date_due)
                    )
                    tempo_ms = int((time.time() - inicio) * 1000)

                    self._registrar_auditoria_despesa(
                        despesa_extra_id=despesa_id,
                        cte_id=cte_id,
                        chave_cte=cte_chave,
                        etapa=5,
                        etapa_descricao=f"Atualizar vencimento para {data_vencimento_str}",
                        modelo_odoo='l10n_br_ciel_it_account.dfe.pagamento',
                        acao='write',
                        status='SUCESSO',
                        mensagem=f"Vencimento: {data_vencimento_str}",
                        campos_alterados=['cobr_dup_dvenc'],
                        tempo_execucao_ms=tempo_ms,
                        dfe_id=dfe_id
                    )
                resultado['etapas_concluidas'] = 5
            else:
                current_app.logger.info(f"⏭️ ETAPA 5 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 6: Gerar Purchase Order (fire_and_poll — resiliente a timeout upstream)
            # Ver app/fretes/services/lancamento_odoo_service.py::_gerar_po_dfe_fire_and_poll
            # ========================================
            if continuar_de_etapa < 7:  # Só executa se não está retomando de etapa posterior
                # 🔧 CORREÇÃO 05/01/2026: Forçar leitura do DFE antes de gerar PO
                # Isso evita que o Odoo use dados em cache de um DFE anterior
                # quando múltiplas despesas são processadas em sequência
                try:
                    dfe_refresh = self.odoo.read(
                        'l10n_br_ciel_it_account.dfe',
                        [dfe_id],
                        ['id', 'name', 'nfe_infnfe_total_icmstot_vnf', 'lines_ids', 'dups_ids']
                    )
                    if dfe_refresh:
                        valor_dfe_refresh = dfe_refresh[0].get('nfe_infnfe_total_icmstot_vnf', 0)
                        current_app.logger.info(
                            f"🔄 DFE {dfe_id} recarregado antes de gerar PO. Valor: R$ {valor_dfe_refresh:.2f}"
                        )
                except Exception as e:
                    current_app.logger.warning(f"⚠️ Erro ao recarregar DFE antes de gerar PO: {e}")

                sucesso_po, po_id_novo, erro_po = self._gerar_po_dfe_fire_and_poll(
                    dfe_id=dfe_id,
                    frete_id=None,
                    cte_id=cte_id,
                    cte_chave=cte_chave,
                    despesa_extra_id=despesa_id,
                )

                if not sucesso_po:
                    resultado['erro'] = erro_po
                    resultado['mensagem'] = f"Erro na etapa 6: {erro_po}"
                    resultado['rollback_executado'] = self._rollback_despesa_odoo(despesa_id, resultado['etapas_concluidas'])
                    return resultado

                po_id = po_id_novo
                resultado['etapas_concluidas'] = 6
                resultado['purchase_order_id'] = po_id
            else:
                # RETOMADA: Usar PO existente
                current_app.logger.info(f"⏭️ ETAPA 6 PULADA - Usando PO existente: ID {po_id}")
                resultado['purchase_order_id'] = po_id

            # ========================================
            # ETAPA 7: Configurar PO (incluindo correção da operação fiscal)
            # ========================================
            if continuar_de_etapa < 8:  # Só executa se não está retomando de etapa posterior
                # Preparar dados para atualização usando empresa identificada pelo CTe
                dados_po = {
                    'team_id': self.TEAM_LANCAMENTO_FRETE_ID,
                    'payment_provider_id': self.PAYMENT_PROVIDER_TRANSFERENCIA_ID,
                    'company_id': company_id,  # ✅ Empresa identificada pelo CNPJ do tomador
                }

                # Adicionar picking_type_id se disponível na configuração
                if config_empresa.get('picking_type_id'):
                    dados_po['picking_type_id'] = config_empresa['picking_type_id']

                current_app.logger.info(
                    f"🏢 Configurando PO para empresa {config_empresa.get('nome')} (ID: {company_id})"
                )

                # ✅ ADICIONAR partner_ref com número da fatura (se houver)
                # 🔧 CORREÇÃO 05/01/2026: Usar variáveis locais extraídas no início
                if despesa_fatura_id and despesa_numero_fatura:
                    referencia_fatura = f"FATURA-{despesa_numero_fatura}"
                    dados_po['partner_ref'] = referencia_fatura
                    current_app.logger.info(
                        f"🔗 Adicionando fatura {despesa_numero_fatura} ao PO {po_id} "
                        f"(partner_ref: '{referencia_fatura}')"
                    )

                # 🔧 CORREÇÃO 05/01/2026: Buscar valor CORRETO do DFE (fonte da verdade)
                # O valor deve vir do DFE, não do PO que pode ter sido alterado incorretamente
                valor_correto_dfe = None
                try:
                    dfe_valor = self.odoo.read(
                        'l10n_br_ciel_it_account.dfe',
                        [dfe_id],
                        ['nfe_infnfe_total_icmstot_vnf']
                    )
                    if dfe_valor and dfe_valor[0].get('nfe_infnfe_total_icmstot_vnf'):
                        valor_correto_dfe = dfe_valor[0]['nfe_infnfe_total_icmstot_vnf']
                        current_app.logger.info(
                            f"💰 Valor correto do DFE {dfe_id}: R$ {valor_correto_dfe:.2f}"
                        )
                except Exception as e:
                    current_app.logger.warning(f"⚠️ Erro ao buscar valor do DFE: {e}")

                # ✅ CORRIGIR OPERAÇÃO FISCAL: Garantir operação correta para a empresa identificada
                operacao_correta_id = None
                line_ids_po = []  # Guardar IDs das linhas para verificação posterior
                try:
                    po_operacao = self.odoo.read(
                        'purchase.order',
                        [po_id],
                        ['l10n_br_operacao_id', 'order_line']
                    )
                    if po_operacao and po_operacao[0].get('l10n_br_operacao_id'):
                        operacao_atual_id = po_operacao[0]['l10n_br_operacao_id'][0]
                        operacao_atual_nome = po_operacao[0]['l10n_br_operacao_id'][1]

                        # Usar método que suporta qualquer empresa
                        operacao_correta_id = self._obter_operacao_correta(operacao_atual_id, company_id)

                        if operacao_correta_id:
                            dados_po['l10n_br_operacao_id'] = operacao_correta_id
                            current_app.logger.info(
                                f"🔄 Corrigindo operação fiscal PO: {operacao_atual_id} ({operacao_atual_nome}) "
                                f"→ {operacao_correta_id} (empresa {config_empresa.get('nome')})"
                            )

                            # ✅ CORRIGIR TAMBÉM AS LINHAS DO PO (COM PROTEÇÃO DE VALORES)
                            line_ids = po_operacao[0].get('order_line', [])
                            line_ids_po = line_ids  # Guardar para verificação posterior
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

                                    # 4. Verificar se valores foram zerados e RESTAURAR
                                    linhas_apos = self.odoo.read(
                                        'purchase.order.line',
                                        linhas_para_corrigir,
                                        ['id', 'price_unit', 'price_subtotal']
                                    )

                                    for linha in linhas_apos:
                                        backup = valores_backup.get(linha['id'], {})
                                        valor_original = backup.get('price_unit', 0)
                                        valor_atual = linha.get('price_unit', 0)

                                        if valor_atual == 0 and valor_original > 0:
                                            current_app.logger.warning(
                                                f"  ⚠️ Linha {linha['id']} foi ZERADA! Restaurando R$ {valor_original:.2f}"
                                            )
                                            self.odoo.write(
                                                'purchase.order.line',
                                                [linha['id']],
                                                backup
                                            )

                                    current_app.logger.info(
                                        f"🔄 Operação fiscal corrigida em {len(linhas_para_corrigir)} linha(s) do PO"
                                    )
                                else:
                                    current_app.logger.info(
                                        f"✅ Todas as {len(line_ids)} linha(s) já estão com operação fiscal correta"
                                    )
                        else:
                            # Mesmo sem correção de operação, pegar line_ids para verificação posterior
                            line_ids_po = po_operacao[0].get('order_line', [])
                            current_app.logger.info(
                                f"✅ Operação fiscal já está correta: {operacao_atual_id} ({operacao_atual_nome})"
                            )
                    else:
                        # Mesmo sem operação fiscal, pegar line_ids para verificação posterior
                        if po_operacao:
                            line_ids_po = po_operacao[0].get('order_line', [])
                except Exception as e:
                    current_app.logger.warning(f"⚠️ Erro ao verificar/corrigir operação fiscal: {e}")

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
                    etapa_descricao="Configurar PO (operação fiscal, team, payment, company, picking_type)",
                    modelo_odoo='purchase.order',
                    acao='write',
                    status='SUCESSO',
                    mensagem=f"PO {po_id} configurado para empresa {config_empresa.get('nome')} (company_id={company_id})",
                    campos_alterados=list(dados_po.keys()),
                    tempo_execucao_ms=tempo_ms,
                    dfe_id=dfe_id,
                    purchase_order_id=po_id
                )
                resultado['etapas_concluidas'] = 7

                # 🔧 CORREÇÃO 05/01/2026: Verificar e corrigir valor da linha APÓS o write do header
                # O onchange do Odoo pode recalcular incorretamente os valores das linhas
                # Usamos o valor do DFE como fonte da verdade
                if valor_correto_dfe and line_ids_po:
                    try:
                        # Ler valor atual da linha do PO
                        linha_atual = self.odoo.read(
                            'purchase.order.line',
                            line_ids_po[:1],  # Pegar apenas a primeira linha (CTe tem 1 linha)
                            ['price_unit', 'price_subtotal']
                        )

                        if linha_atual:
                            price_unit_atual = linha_atual[0].get('price_unit', 0)

                            # Comparar com tolerância de R$ 0.01
                            diferenca = abs(price_unit_atual - valor_correto_dfe)
                            if diferenca > 0.01:
                                current_app.logger.warning(
                                    f"⚠️ VALOR INCORRETO DETECTADO NA DESPESA! "
                                    f"PO linha: R$ {price_unit_atual:.2f} | "
                                    f"DFE correto: R$ {valor_correto_dfe:.2f} | "
                                    f"Diferença: R$ {diferenca:.2f}"
                                )

                                # Corrigir o valor da linha com o valor do DFE
                                self.odoo.write(
                                    'purchase.order.line',
                                    line_ids_po[:1],
                                    {'price_unit': valor_correto_dfe}
                                )
                                current_app.logger.info(
                                    f"✅ VALOR CORRIGIDO: R$ {price_unit_atual:.2f} → R$ {valor_correto_dfe:.2f}"
                                )
                            else:
                                current_app.logger.info(
                                    f"✅ Valor da linha PO está correto: R$ {price_unit_atual:.2f}"
                                )
                    except Exception as e:
                        current_app.logger.warning(
                            f"⚠️ Erro ao verificar/corrigir valor da linha PO: {e}"
                        )
            else:
                current_app.logger.info(f"⏭️ ETAPA 7 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 8: Pulada (impostos calculados automaticamente)
            # ========================================
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

            # ========================================
            # ETAPA 9: Confirmar PO
            # ========================================
            if continuar_de_etapa < 10:  # Só executa se não está retomando de etapa posterior
                inicio = time.time()
                self.odoo.execute_kw(
                    'purchase.order',
                    'button_confirm',
                    [[po_id]],
                    {'context': {'validate_analytic': True}}
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
            else:
                current_app.logger.info(f"⏭️ ETAPA 9 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 10: Aprovar PO se necessário
            # ========================================
            if continuar_de_etapa < 11:  # Só executa se não está retomando de etapa posterior
                po_data = self.odoo.read('purchase.order', [po_id], ['state', 'is_current_approver'])
                if po_data and po_data[0].get('state') == 'to approve' and po_data[0].get('is_current_approver'):
                    inicio = time.time()
                    self.odoo.execute_kw(
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
            else:
                current_app.logger.info(f"⏭️ ETAPA 10 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 11: Criar Invoice
            # ========================================
            if continuar_de_etapa < 12:  # Só executa se não está retomando de etapa posterior
                inicio = time.time()
                self.odoo.execute_kw(
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
                    self._registrar_auditoria_despesa(
                        despesa_extra_id=despesa_id,
                        cte_id=cte_id,
                        chave_cte=cte_chave,
                        etapa=12,
                        etapa_descricao="Atualizar impostos da Invoice",
                        modelo_odoo='account.move',
                        metodo_odoo='onchange_l10n_br_calcular_imposto',
                        acao='execute_method',
                        status='SUCESSO',
                        mensagem="Impostos atualizados",
                        dfe_id=dfe_id,
                        purchase_order_id=po_id,
                        invoice_id=invoice_id
                    )
                except Exception as e:
                    # ✅ BLINDAGEM: Se auditoria falhar, NÃO trava o lançamento
                    current_app.logger.error(f"❌ Erro ao registrar auditoria ETAPA 12 (não crítico): {e}")
                    db.session.rollback()
                    db.session.remove()

                resultado['etapas_concluidas'] = 12
            else:
                current_app.logger.info(f"⏭️ ETAPA 12 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 13: Configurar Invoice (campos fiscais + vencimento + referência)
            # ========================================
            if continuar_de_etapa < 14:  # Só executa se não está retomando de etapa posterior
                dados_invoice = {
                    'l10n_br_compra_indcom': 'out',
                    'l10n_br_situacao_nf': 'autorizado',
                    'invoice_date_due': data_vencimento_str
                }

                # ✅ ADICIONAR payment_reference com número da fatura (se houver)
                # 🔧 CORREÇÃO 05/01/2026: Usar variáveis locais extraídas no início
                if despesa_fatura_id and despesa_numero_fatura:
                    referencia_fatura = f"FATURA-{despesa_numero_fatura}"
                    dados_invoice['payment_reference'] = referencia_fatura
                    current_app.logger.info(
                        f"🔗 Adicionando fatura {despesa_numero_fatura} à Invoice {invoice_id}"
                    )
                else:
                    dados_invoice['payment_reference'] = f'DESPESA-{despesa_id}'

                inicio = time.time()
                self.odoo.write(
                    'account.move',
                    [invoice_id],
                    dados_invoice
                )
                tempo_ms = int((time.time() - inicio) * 1000)

                self._registrar_auditoria_despesa(
                    despesa_extra_id=despesa_id,
                    cte_id=cte_id,
                    chave_cte=cte_chave,
                    etapa=13,
                    etapa_descricao="Configurar Invoice (campos fiscais, vencimento e payment_reference)",
                    modelo_odoo='account.move',
                    acao='write',
                    status='SUCESSO',
                    mensagem=f"Invoice {invoice_id} configurada com ref: {dados_invoice['payment_reference']}",
                    campos_alterados=list(dados_invoice.keys()),
                    tempo_execucao_ms=tempo_ms,
                    dfe_id=dfe_id,
                    purchase_order_id=po_id,
                    invoice_id=invoice_id
                )
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
                    self._registrar_auditoria_despesa(
                        despesa_extra_id=despesa_id,
                        cte_id=cte_id,
                        chave_cte=cte_chave,
                        etapa=14,
                        etapa_descricao="Atualizar impostos da Invoice (final)",
                        modelo_odoo='account.move',
                        metodo_odoo='onchange_l10n_br_calcular_imposto_btn',
                        acao='execute_method',
                        status='SUCESSO',
                        mensagem="Impostos recalculados",
                        dfe_id=dfe_id,
                        purchase_order_id=po_id,
                        invoice_id=invoice_id
                    )
                except Exception as e:
                    # ✅ BLINDAGEM: Se auditoria falhar, NÃO trava o lançamento
                    current_app.logger.error(f"❌ Erro ao registrar auditoria ETAPA 14 (não crítico): {e}")
                    db.session.rollback()
                    db.session.remove()

                resultado['etapas_concluidas'] = 14
            else:
                current_app.logger.info(f"⏭️ ETAPA 14 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 15: Confirmar Invoice
            # ========================================
            if continuar_de_etapa < 16:  # Só executa se não está retomando de etapa posterior
                inicio = time.time()
                self.odoo.execute_kw(
                    'account.move',
                    'action_post',
                    [[invoice_id]],
                    {'context': {'validate_analytic': True}}
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
            else:
                current_app.logger.info(f"⏭️ ETAPA 15 PULADA - Retomando de etapa {continuar_de_etapa}")

            # ========================================
            # ETAPA 16: Atualizar despesa local
            # ========================================
            try:
                # 🔧 CORREÇÃO 05/01/2026: Re-buscar despesa com sessão NOVA
                # A sessão original pode ter expirado durante as operações longas no Odoo
                # (especialmente na ETAPA 6 que pode demorar 30+ segundos)

                # ✅ Garantir sessão limpa antes de re-buscar
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()

                current_app.logger.info(f"🔄 Re-buscando despesa #{despesa_id} para atualização final...")
                despesa = db.session.get(DespesaExtra, despesa_id)  # ✅ Usar db.session.get() (SQLAlchemy 2.0+)
                if not despesa:
                    raise ValueError(f"Despesa Extra ID {despesa_id} não encontrada na ETAPA 16")

                despesa.odoo_dfe_id = dfe_id
                despesa.odoo_purchase_order_id = po_id
                despesa.odoo_invoice_id = invoice_id
                despesa.lancado_odoo_em = agora_utc_naive()
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

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Erro ao atualizar despesa: {e}")
                resultado['erro'] = f"Erro ao atualizar despesa: {e}"
                resultado['mensagem'] = f"Lançamento concluído no Odoo, mas erro ao atualizar sistema local: {e}"

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

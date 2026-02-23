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
from datetime import date
from typing import Dict, List, Optional, Tuple, Any
from flask import current_app

from app import db
from app.fretes.models import (
    Frete,
    ConhecimentoTransporte,
    LancamentoFreteOdooAuditoria
)
from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_utc_naive


class LancamentoOdooService:
    """
    Service para lançar fretes no Odoo com auditoria completa
    """

    # IDs fixos do Odoo (conforme documentação)
    PRODUTO_SERVICO_FRETE_ID = 29993
    CONTA_ANALITICA_LOGISTICA_ID = 1186
    TEAM_LANCAMENTO_FRETE_ID = 119
    PAYMENT_PROVIDER_TRANSFERENCIA_ID = 30

    # ========================================
    # MAPEAMENTO DE EMPRESAS POR CNPJ
    # ========================================
    # Usado para identificar qual empresa é o tomador do frete
    CNPJ_PARA_COMPANY = {
        '61724241000178': 1,   # FB - Fábrica
        '61724241000259': 3,   # SC - Santa Catarina
        '61724241000330': 4,   # CD - Centro de Distribuição
        '18467441000163': 5,   # LF - La Famiglia
    }

    # ========================================
    # CONFIGURAÇÃO POR EMPRESA
    # ========================================
    # Cada empresa possui suas próprias configurações de IDs no Odoo
    CONFIG_POR_EMPRESA = {
        1: {  # FB - Fábrica
            'company_id': 1,
            'picking_type_id': 1,  # FB: Recebimento (FB) - CORRIGIDO 14/01/2026
            'nome': 'NACOM GOYA - FB'
        },
        4: {  # CD - Centro de Distribuição
            'company_id': 4,
            'picking_type_id': 13,  # CD: Recebimento (CD)
            'nome': 'NACOM GOYA - CD'
        },
    }

    # Empresa padrão quando não for possível identificar
    COMPANY_PADRAO_ID = 4  # CD

    # ========================================
    # OPERAÇÕES FISCAIS DE TRANSPORTE POR EMPRESA
    # ========================================
    # Estrutura: {company_id: {(destino, regime): operacao_id}}
    # destino: 1=Interna, 2=Interestadual
    # regime: 1=Simples Nacional, 3=Regime Normal (LR/LP)
    OPERACOES_TRANSPORTE = {
        1: {  # FB - Fábrica
            (1, 3): 2022,  # Interna + Regime Normal
            (2, 3): 3041,  # Interestadual + Regime Normal
            (1, 1): 2738,  # Interna + Simples Nacional
            (2, 1): 3040,  # Interestadual + Simples Nacional
        },
        4: {  # CD - Centro de Distribuição
            (1, 3): 2632,  # Interna + Regime Normal
            (2, 3): 3038,  # Interestadual + Regime Normal
            (1, 1): 2739,  # Interna + Simples Nacional
            (2, 1): 3037,  # Interestadual + Simples Nacional
        },
    }

    # Lista de TODAS as operações de transporte válidas (para validação)
    OPERACOES_TRANSPORTE_VALIDAS = {
        # FB
        2022, 3041, 2738, 3040,
        # CD
        2632, 3038, 2739, 3037,
    }

    # De-Para: Operação Fiscal entre empresas
    # Usado quando o Odoo seleciona operação errada automaticamente
    # Formato: {operacao_origem: {company_destino: operacao_correta}}
    OPERACAO_DE_PARA = {
        # FB → CD
        2022: {4: 2632},   # Interna Regime Normal
        3041: {4: 3038},   # Interestadual Regime Normal
        2738: {4: 2739},   # Interna Simples Nacional
        3040: {4: 3037},   # Interestadual Simples Nacional
        # CD → FB
        2632: {1: 2022},   # Interna Regime Normal
        3038: {1: 3041},   # Interestadual Regime Normal
        2739: {1: 2738},   # Interna Simples Nacional
        3037: {1: 3040},   # Interestadual Simples Nacional
    }

    # Mapeamento legado (mantido para compatibilidade)
    # DEPRECATED: Usar OPERACAO_DE_PARA
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

    # ========================================
    # MÉTODOS DE IDENTIFICAÇÃO DE EMPRESA
    # ========================================

    def _identificar_company_por_cnpj(self, cnpj: str) -> int:
        """
        Identifica o ID da empresa Odoo pelo CNPJ

        Args:
            cnpj: CNPJ com ou sem formatação

        Returns:
            Company ID correspondente ou COMPANY_PADRAO_ID se não encontrado
        """
        if not cnpj:
            return self.COMPANY_PADRAO_ID

        # Limpar CNPJ (remover pontuação)
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))[:14]

        # Buscar no mapeamento
        company_id = self.CNPJ_PARA_COMPANY.get(cnpj_limpo)

        if company_id:
            try:
                current_app.logger.debug(f"🏢 CNPJ {cnpj_limpo} → Company ID {company_id}")
            except RuntimeError:
                pass  # Fora do contexto de aplicação
            return company_id

        try:
            current_app.logger.warning(
                f"⚠️ CNPJ {cnpj_limpo} não encontrado no mapeamento. Usando padrão: {self.COMPANY_PADRAO_ID}"
            )
        except RuntimeError:
            pass  # Fora do contexto de aplicação
        return self.COMPANY_PADRAO_ID

    def _identificar_company_por_cte(self, cte: 'ConhecimentoTransporte') -> int:
        """
        Identifica o ID da empresa Odoo pelo CTe (CNPJ do tomador)

        Args:
            cte: Objeto ConhecimentoTransporte

        Returns:
            Company ID correspondente ao tomador do frete
        """
        if not cte:
            return self.COMPANY_PADRAO_ID

        # Identificar CNPJ do tomador baseado no campo 'tomador'
        # 0, 1 = Remetente
        # 3, 4 = Destinatário
        cnpj_tomador = None
        if cte.tomador in ['0', '1']:
            cnpj_tomador = cte.cnpj_remetente
        elif cte.tomador in ['3', '4']:
            cnpj_tomador = cte.cnpj_destinatario
        else:
            # Fallback: tentar usar destinatário se tomador não estiver definido
            cnpj_tomador = cte.cnpj_destinatario

        return self._identificar_company_por_cnpj(cnpj_tomador)

    def _obter_config_empresa(self, company_id: int) -> Dict[str, Any]:
        """
        Obtém a configuração da empresa para lançamento

        Args:
            company_id: ID da empresa no Odoo

        Returns:
            Dict com configurações (company_id, picking_type_id, nome)
        """
        config = self.CONFIG_POR_EMPRESA.get(company_id)

        if config:
            return config

        # Se não tiver configuração específica, retornar config da empresa padrão
        try:
            current_app.logger.warning(
                f"⚠️ Company ID {company_id} não possui configuração específica. "
                f"Usando configuração padrão (Company ID {self.COMPANY_PADRAO_ID})"
            )
        except RuntimeError:
            pass  # Fora do contexto de aplicação
        return self.CONFIG_POR_EMPRESA.get(self.COMPANY_PADRAO_ID, {
            'company_id': self.COMPANY_PADRAO_ID,
            'picking_type_id': 13,
            'nome': 'Padrão'
        })

    def _obter_operacao_correta(
        self,
        operacao_atual_id: int,
        company_destino_id: int,
        purchase_order_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Obtém a operação fiscal correta para a empresa de destino

        Args:
            operacao_atual_id: ID da operação fiscal atual
            company_destino_id: ID da empresa de destino
            purchase_order_id: ID do Purchase Order (usado para determinar operação
                             de transporte quando a operação atual não é de transporte)

        Returns:
            ID da operação correta ou None se não precisar corrigir
        """
        # Verificar se a operação atual precisa de correção (de-para entre empresas)
        if operacao_atual_id in self.OPERACAO_DE_PARA:
            mapeamento = self.OPERACAO_DE_PARA[operacao_atual_id]
            operacao_correta = mapeamento.get(company_destino_id)

            if operacao_correta:
                return operacao_correta

        # Verificar se a operação atual já é válida (é de transporte)
        if operacao_atual_id in self.OPERACOES_TRANSPORTE_VALIDAS:
            # Verificar se pertence à empresa correta
            for company_id, operacoes in self.OPERACOES_TRANSPORTE.items():
                if operacao_atual_id in operacoes.values():
                    if company_id == company_destino_id:
                        return None  # Já está correto
                    else:
                        # Precisa trocar para a empresa correta
                        # Encontrar operação equivalente
                        for (destino, regime), op_id in operacoes.items():
                            if op_id == operacao_atual_id:
                                # Buscar mesma combinação na empresa destino
                                operacoes_destino = self.OPERACOES_TRANSPORTE.get(company_destino_id, {})
                                return operacoes_destino.get((destino, regime))

        # Operação NÃO é de transporte (ex: "Aquisição de Serviços sem Retenção")
        # Isso ocorre quando o Odoo atribui uma operação genérica default ao PO,
        # geralmente porque o partner (transportadora) não tem operação fiscal configurada.
        # Devemos SEMPRE substituir por uma operação de transporte correta.
        if operacao_atual_id not in self.OPERACOES_TRANSPORTE_VALIDAS:
            operacao_transporte = self._determinar_operacao_transporte(
                company_destino_id, purchase_order_id
            )
            if operacao_transporte:
                return operacao_transporte

        return None

    def _determinar_operacao_transporte(
        self,
        company_id: int,
        purchase_order_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Determina a operação fiscal de transporte correta para a empresa,
        consultando dados do parceiro (transportadora) no PO.

        Critérios:
        - destino: UF do partner (transportadora) — SP=Interna(1), outro=Interestadual(2)
        - regime: l10n_br_fiscal_type do partner — '1'=Simples(1), outro=Normal(3)

        Fallback: Interestadual + Regime Normal (caso mais comum para transportadoras)

        Args:
            company_id: ID da empresa no Odoo
            purchase_order_id: ID do Purchase Order para buscar dados do parceiro

        Returns:
            ID da operação de transporte correta ou None se empresa não tem mapeamento
        """
        destino = 2  # Default: Interestadual
        regime = 3   # Default: Regime Normal

        if purchase_order_id and self.odoo:
            try:
                po_data = self.odoo.read('purchase.order', [purchase_order_id], ['partner_id'])
                if po_data and po_data[0].get('partner_id'):
                    partner_id = po_data[0]['partner_id'][0]
                    partner_data = self.odoo.read(
                        'res.partner', [partner_id], ['state_id', 'l10n_br_fiscal_type']
                    )
                    if partner_data:
                        partner = partner_data[0]

                        # Destino: UF da transportadora
                        state_id = partner.get('state_id')
                        if state_id and isinstance(state_id, (list, tuple)):
                            state_name = str(state_id[1])
                            if 'São Paulo' in state_name or state_name.strip().upper() == 'SP':
                                destino = 1  # Interna

                        # Regime fiscal da transportadora
                        fiscal_type = partner.get('l10n_br_fiscal_type')
                        if fiscal_type == '1':
                            regime = 1  # Simples Nacional
            except Exception as e:
                try:
                    current_app.logger.warning(
                        f"⚠️ Erro ao ler dados do parceiro para operação fiscal: {e}. "
                        f"Usando fallback: Interestadual + Regime Normal"
                    )
                except RuntimeError:
                    pass

        operacoes = self.OPERACOES_TRANSPORTE.get(company_id, {})
        operacao = operacoes.get((destino, regime))

        if not operacao:
            # Fallback: Interestadual + Regime Normal (o mais comum)
            operacao = operacoes.get((2, 3))

        return operacao

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
            frete = db.session.get(Frete,frete_id) if frete_id else None
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

    def _verificar_lancamento_existente(self, dfe_id: int, cte_chave: str, company_id_esperado: int = None) -> Dict[str, Any]:
        """
        Verifica se já existe um lançamento parcial para este DFe e determina
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
            frete = db.session.get(Frete,frete_id) if frete_id else None
            if not frete:
                raise ValueError(f"Frete ID {frete_id} não encontrado")

            # 🔧 CORREÇÃO 17/12/2025: Extrair dados do frete ANTES das operações longas
            # Isso previne o erro "Instance <Frete> is not bound to a Session"
            # que ocorre quando a ETAPA 6 demora muito (60+ segundos) e a sessão expira
            frete_fatura_id = frete.fatura_frete_id
            frete_numero_fatura = frete.fatura_frete.numero_fatura if frete.fatura_frete else None
            frete_cte_id_atual = frete.frete_cte_id  # Para verificar vínculo na ETAPA 16
            current_app.logger.debug(
                f"📦 Dados extraídos do frete #{frete_id}: "
                f"fatura_id={frete_fatura_id}, numero_fatura={frete_numero_fatura}"
            )

            # Buscar CTe
            cte = db.session.query(ConhecimentoTransporte).filter_by(chave_acesso=cte_chave).first()
            cte_id = cte.id if cte else None

            # ========================================
            # IDENTIFICAR EMPRESA PELO CNPJ DO TOMADOR
            # ========================================
            company_id = self._identificar_company_por_cte(cte)
            config_empresa = self._obter_config_empresa(company_id)
            current_app.logger.info(
                f"🏢 Empresa identificada: {config_empresa.get('nome', 'N/A')} (ID: {company_id})"
            )

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
            # 🔧 CORREÇÃO 14/01/2026: Passar company_id para verificar se PO está na empresa correta
            # ========================================
            lancamento_existente = self._verificar_lancamento_existente(dfe_id, cte_chave, company_id)
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
                # 🔧 CORREÇÃO 17/12/2025: Usar variáveis locais extraídas no início
                if frete_fatura_id and frete_numero_fatura:
                    referencia_fatura = f"FATURA-{frete_numero_fatura}"

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
                            f"🔗 Adicionando fatura {frete_numero_fatura} ao DFe {dfe_id} "
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

                # 🔧 CORREÇÃO 17/12/2025: Buscar valor CORRETO do DFE (fonte da verdade)
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
                # O Odoo pode criar o PO com operação de outra empresa, precisamos corrigir
                operacao_correta_id = None
                line_ids_po = []  # Guardar IDs das linhas para verificação posterior
                try:
                    po_operacao = self.odoo.read(
                        'purchase.order',
                        [purchase_order_id],
                        ['l10n_br_operacao_id', 'order_line']
                    )
                    if po_operacao and po_operacao[0].get('l10n_br_operacao_id'):
                        operacao_atual_id = po_operacao[0]['l10n_br_operacao_id'][0]
                        operacao_atual_nome = po_operacao[0]['l10n_br_operacao_id'][1]
                        line_ids_po = po_operacao[0].get('order_line', [])

                        # Usar novo método que suporta qualquer empresa
                        operacao_correta_id = self._obter_operacao_correta(
                            operacao_atual_id, company_id, purchase_order_id
                        )

                        if operacao_correta_id:
                            dados_po['l10n_br_operacao_id'] = operacao_correta_id
                            if operacao_atual_id in self.OPERACOES_TRANSPORTE_VALIDAS:
                                current_app.logger.info(
                                    f"🔄 Corrigindo operação fiscal (de-para transporte): "
                                    f"{operacao_atual_id} ({operacao_atual_nome}) → {operacao_correta_id} "
                                    f"(empresa {config_empresa.get('nome')})"
                                )
                            else:
                                current_app.logger.warning(
                                    f"⚠️ Substituindo operação fiscal genérica por transporte: "
                                    f"{operacao_atual_id} ({operacao_atual_nome}) → {operacao_correta_id} "
                                    f"(empresa {config_empresa.get('nome')})"
                                )

                            # Corrigir operação fiscal das linhas
                            if line_ids_po:
                                linhas_data = self.odoo.read(
                                    'purchase.order.line',
                                    line_ids_po,
                                    ['id', 'l10n_br_operacao_id']
                                )

                                linhas_para_corrigir = []
                                for linha in linhas_data:
                                    op_linha = linha.get('l10n_br_operacao_id')
                                    op_linha_id = op_linha[0] if op_linha else None
                                    if op_linha_id != operacao_correta_id:
                                        linhas_para_corrigir.append(linha['id'])

                                if linhas_para_corrigir:
                                    self.odoo.write(
                                        'purchase.order.line',
                                        linhas_para_corrigir,
                                        {'l10n_br_operacao_id': operacao_correta_id}
                                    )
                                    current_app.logger.info(
                                        f"🔄 Operação fiscal corrigida em {len(linhas_para_corrigir)} linha(s) do PO"
                                    )
                                else:
                                    current_app.logger.info(
                                        f"✅ Todas as {len(line_ids_po)} linha(s) já estão com operação fiscal correta"
                                    )
                        else:
                            current_app.logger.info(
                                f"✅ Operação fiscal de transporte já está correta: "
                                f"{operacao_atual_id} ({operacao_atual_nome})"
                            )
                    else:
                        # Mesmo sem operação fiscal, pegar line_ids para verificação posterior
                        if po_operacao:
                            line_ids_po = po_operacao[0].get('order_line', [])
                except Exception as e:
                    current_app.logger.warning(f"⚠️ Erro ao verificar/corrigir operação fiscal: {e}")

                # ✅ ADICIONAR partner_ref com número da fatura (se houver)
                # 🔧 CORREÇÃO 17/12/2025: Usar variáveis locais extraídas no início
                if frete_fatura_id and frete_numero_fatura:
                    referencia_fatura = f"FATURA-{frete_numero_fatura}"

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
                            f"🔗 Adicionando fatura {frete_numero_fatura} ao PO {purchase_order_id} "
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

                # 🔧 CORREÇÃO 17/12/2025: Verificar e corrigir valor da linha APÓS o write do header
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
                                    f"⚠️ VALOR INCORRETO DETECTADO! "
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
                # 🔧 CORREÇÃO 17/12/2025: Usar variáveis locais extraídas no início
                if frete_fatura_id and frete_numero_fatura:
                    referencia_fatura = f"FATURA-{frete_numero_fatura}"

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
                            f"🔗 Adicionando fatura {frete_numero_fatura} à Invoice {invoice_id} "
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
                # 🔧 CORREÇÃO 17/12/2025: Re-buscar frete e CTe com sessão NOVA
                # A sessão original pode ter expirado durante as operações longas no Odoo
                current_app.logger.info(f"🔄 Re-buscando frete #{frete_id} para atualização final...")
                frete = db.session.get(Frete,frete_id) if frete_id else None
                if not frete:
                    raise ValueError(f"Frete ID {frete_id} não encontrado na ETAPA 16")

                # Re-buscar CTe também se existia
                if cte_id:
                    cte = db.session.get(ConhecimentoTransporte,cte_id) if cte_id else None
                    current_app.logger.debug(f"🔄 CTe #{cte_id} re-buscado: {'encontrado' if cte else 'não encontrado'}")

                # Atualizar campos do Frete
                frete.odoo_dfe_id = dfe_id
                frete.odoo_purchase_order_id = purchase_order_id
                frete.odoo_invoice_id = invoice_id
                frete.lancado_odoo_em = agora_utc_naive()
                frete.lancado_odoo_por = self.usuario_nome
                frete.status = 'LANCADO_ODOO'

                # ✅ CRIAR VÍNCULO BIDIRECIONAL Frete ↔ CTe
                if cte:
                    # Frete → CTe (usar variável extraída no início para verificação)
                    if not frete_cte_id_atual:
                        frete.frete_cte_id = cte.id
                        current_app.logger.info(f"🔗 Vinculando Frete → CTe: frete_cte_id = {cte.id}")

                    # CTe → Frete
                    if not cte.frete_id:
                        cte.frete_id = frete_id
                        cte.vinculado_em = agora_utc_naive()
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

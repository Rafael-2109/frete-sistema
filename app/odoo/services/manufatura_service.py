"""
Serviço de Integração Manufatura com Odoo
==========================================

Integração do módulo de Manufatura/PCP com o Odoo ERP.
Importa requisições, pedidos de compra e sincroniza produção.
Usa ManufaturaMapper para mapeamento otimizado de campos.

Autor: Sistema de Fretes
Data: 2025-08-10
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal

from app import db
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.manufatura_mapper import ManufaturaMapper
from app.manufatura.models import (
    RequisicaoCompras, PedidoCompras, OrdemProducao,
    LogIntegracao, HistoricoPedidos
)
from app.estoque.models import MovimentacaoEstoque

logger = logging.getLogger(__name__)


class ManufaturaOdooService:
    """Serviço de integração Manufatura com Odoo"""
    
    def __init__(self):
        """Inicializa serviço com configuração e mapper"""
        self.logger = logging.getLogger(__name__)
        self.connection = get_odoo_connection()
        self.mapper = ManufaturaMapper()
        
    def importar_requisicoes_compras(self) -> Dict[str, Any]:
        """
        Importa requisições de compras do Odoo
        
        Returns:
            Dict com resultado da importação
        """
        inicio = datetime.now()
        registros_processados = 0
        registros_erro = 0
        mensagens_erro = []
        
        try:
            # Conectar ao Odoo
            uid = self.connection.authenticate()
            if not uid:
                raise Exception("Falha na autenticação com Odoo")
            
            # Buscar requisições no Odoo
            requisicoes = self.connection.search_read(
                'purchase.requisition',
                [['state', 'in', ['confirmed', 'done']]],
                ['name', 'product_id', 'product_qty', 'schedule_date', 
                 'user_id', 'create_date']
            )
            
            for req_odoo in requisicoes:
                try:
                    # Verificar se já foi importada
                    existe = RequisicaoCompras.query.filter_by(
                        odoo_id=str(req_odoo['id'])
                    ).first()
                    
                    if not existe:
                        # Processar datas
                        data_criacao = datetime.now().date()
                        if req_odoo.get('create_date'):
                            try:
                                data_criacao = datetime.strptime(
                                    req_odoo['create_date'], '%Y-%m-%d %H:%M:%S'
                                ).date()
                            except Exception as e:
                                logger.error(f"Erro ao processar data de criação: {e}")
                                pass
                        
                        data_necessidade = None
                        if req_odoo.get('schedule_date'):
                            try:
                                data_necessidade = datetime.strptime(
                                    req_odoo['schedule_date'], '%Y-%m-%d'
                                ).date()
                            except Exception as e:
                                logger.error(f"Erro ao processar data de necessidade: {e}")
                                pass
                        
                        # Criar requisição
                        requisicao = RequisicaoCompras(
                            num_requisicao=req_odoo.get('name', f"REQ-{req_odoo['id']}"),
                            data_requisicao_criacao=data_criacao,
                            usuario_requisicao_criacao=req_odoo['user_id'][1] if req_odoo.get('user_id') else 'Odoo',
                            cod_produto=str(req_odoo['product_id'][0]) if req_odoo.get('product_id') else None,
                            nome_produto=req_odoo['product_id'][1] if req_odoo.get('product_id') else None,
                            qtd_produto_requisicao=Decimal(str(req_odoo.get('product_qty', 0))),
                            data_requisicao_solicitada=data_necessidade,
                            data_necessidade=data_necessidade,
                            status='Requisitada',
                            importado_odoo=True,
                            odoo_id=str(req_odoo['id'])
                        )
                        
                        db.session.add(requisicao)
                        registros_processados += 1
                        logger.info(f"Requisição {requisicao.num_requisicao} importada")
                        
                except Exception as e:
                    registros_erro += 1
                    erro_msg = f"Erro ao processar requisição {req_odoo.get('name')}: {str(e)}"
                    mensagens_erro.append(erro_msg)
                    logger.error(erro_msg)
            
            # Commit das alterações
            if registros_processados > 0:
                db.session.commit()
            
            # Registrar log
            tempo_execucao = (datetime.now() - inicio).total_seconds()
            self._registrar_log(
                'importar_requisicoes',
                'sucesso' if registros_erro == 0 else 'parcial',
                f'{registros_processados} requisições importadas, {registros_erro} erros',
                registros_processados,
                registros_erro,
                tempo_execucao,
                {'erros': mensagens_erro} if mensagens_erro else None
            )
            
            return {
                'sucesso': True,
                'processados': registros_processados,
                'erros': registros_erro,
                'mensagem': f'{registros_processados} requisições importadas'
            }
            
        except Exception as e:
            db.session.rollback()
            erro_msg = f"Erro geral na importação: {str(e)}"
            logger.error(erro_msg)
            
            self._registrar_log(
                'importar_requisicoes',
                'erro',
                erro_msg,
                registros_processados,
                registros_erro
            )
            
            return {
                'sucesso': False,
                'erro': erro_msg,
                'processados': registros_processados,
                'erros': registros_erro
            }
    
    def importar_pedidos_compras(self) -> Dict[str, Any]:
        """
        Importa pedidos de compras confirmados do Odoo
        
        Returns:
            Dict com resultado da importação
        """
        inicio = datetime.now()
        registros_processados = 0
        registros_erro = 0
        mensagens_erro = []
        
        try:
            # Conectar ao Odoo
            uid = self.connection.authenticate()
            if not uid:
                raise Exception("Falha na autenticação com Odoo")
            
            # Buscar pedidos no Odoo
            pedidos = self.connection.search_read(
                'purchase.order',
                [['state', 'in', ['purchase', 'done']]],
                ['name', 'partner_id', 'date_order', 'date_planned', 
                 'user_id', 'invoice_ids']
            )
            
            for ped_odoo in pedidos:
                try:
                    # Verificar se já foi importado
                    existe = PedidoCompras.query.filter_by(
                        odoo_id=str(ped_odoo['id'])
                    ).first()
                    
                    if not existe:
                        # Buscar linhas do pedido
                        linhas = self.connection.search_read(
                            'purchase.order.line',
                            [['order_id', '=', ped_odoo['id']]],
                            ['product_id', 'product_qty', 'price_unit', 
                             'price_tax', 'price_total']
                        )
                        
                        # Processar cada linha
                        for linha in linhas:
                            # Processar datas
                            data_pedido = datetime.now().date()
                            if ped_odoo.get('date_order'):
                                try:
                                    data_pedido = datetime.strptime(
                                        ped_odoo['date_order'], '%Y-%m-%d %H:%M:%S'
                                    ).date()
                                except Exception as e:
                                    self.logger.error(f"Erro ao processar data de pedido: {e}")
                                    pass
                            
                            data_prevista = None
                            if ped_odoo.get('date_planned'):
                                try:
                                    data_prevista = datetime.strptime(
                                        ped_odoo['date_planned'], '%Y-%m-%d %H:%M:%S'
                                    ).date()
                                except Exception as e:
                                    self.logger.error(f"Erro ao processar data prevista: {e}")
                                    pass
                            
                            # Buscar NF se existir
                            numero_nf = None
                            if ped_odoo.get('invoice_ids'):
                                try:
                                    invoice = self.connection.search_read(
                                        'account.move',
                                        [['id', 'in', ped_odoo['invoice_ids']]],
                                        ['name'],
                                        limit=1
                                    )
                                    if invoice:
                                        numero_nf = invoice[0].get('name')
                                except Exception as e:
                                    self.logger.error(f"Erro ao buscar NF: {e}")
                                    pass
                            
                            # Verificar se pedido já existe
                            num_pedido = ped_odoo.get('name', f"PO-{ped_odoo['id']}")
                            cod_produto = str(linha['product_id'][0]) if linha.get('product_id') else None
                            
                            pedido_existente = PedidoCompras.query.filter_by(
                                num_pedido=num_pedido,
                                cod_produto=cod_produto
                            ).first()
                            
                            if pedido_existente:
                                # Atualizar pedido existente
                                pedido_existente.numero_nf = numero_nf
                                pedido_existente.data_pedido_previsao = data_prevista
                                pedido_existente.qtd_produto_pedido = Decimal(str(linha.get('product_qty', 0)))
                                pedido_existente.preco_produto_pedido = Decimal(str(linha.get('price_unit', 0)))
                                pedido_existente.atualizado_em = datetime.now()
                                logger.info(f"Pedido {num_pedido} produto {cod_produto} atualizado")
                            else:
                                # Criar novo pedido
                                pedido = PedidoCompras(
                                    num_pedido=num_pedido,
                                    cnpj_fornecedor=str(ped_odoo['partner_id'][0]) if ped_odoo.get('partner_id') else None,
                                    raz_social=ped_odoo['partner_id'][1] if ped_odoo.get('partner_id') else None,
                                    numero_nf=numero_nf,
                                    data_pedido_criacao=data_pedido,
                                    usuario_pedido_criacao=ped_odoo['user_id'][1] if ped_odoo.get('user_id') else 'Odoo',
                                    data_pedido_previsao=data_prevista,
                                    cod_produto=cod_produto,
                                    nome_produto=linha['product_id'][1] if linha.get('product_id') else None,
                                    qtd_produto_pedido=Decimal(str(linha.get('product_qty', 0))),
                                    preco_produto_pedido=Decimal(str(linha.get('price_unit', 0))),
                                    confirmacao_pedido=True,
                                    importado_odoo=True,
                                    odoo_id=str(ped_odoo['id'])
                                )
                                db.session.add(pedido)
                                logger.info(f"Novo pedido {num_pedido} produto {cod_produto} criado")
                            
                            registros_processados += 1
                            
                except Exception as e:
                    registros_erro += 1
                    erro_msg = f"Erro ao processar pedido {ped_odoo.get('name')}: {str(e)}"
                    mensagens_erro.append(erro_msg)
                    logger.error(erro_msg)
                    # Fazer rollback para limpar erros de sessão
                    db.session.rollback()
            
            # Commit das alterações
            if registros_processados > 0:
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Erro ao fazer commit: {e}")
            
            # Registrar log
            tempo_execucao = (datetime.now() - inicio).total_seconds()
            self._registrar_log(
                'importar_pedidos',
                'sucesso' if registros_erro == 0 else 'parcial',
                f'{registros_processados} pedidos importados, {registros_erro} erros',
                registros_processados,
                registros_erro,
                tempo_execucao,
                {'erros': mensagens_erro} if mensagens_erro else None
            )
            
            return {
                'sucesso': True,
                'processados': registros_processados,
                'erros': registros_erro,
                'mensagem': f'{registros_processados} pedidos importados'
            }
            
        except Exception as e:
            db.session.rollback()
            erro_msg = f"Erro geral na importação: {str(e)}"
            logger.error(erro_msg)
            
            self._registrar_log(
                'importar_pedidos',
                'erro',
                erro_msg,
                registros_processados,
                registros_erro
            )
            
            return {
                'sucesso': False,
                'erro': erro_msg,
                'processados': registros_processados,
                'erros': registros_erro
            }
    
    def sincronizar_producao(self) -> Dict[str, Any]:
        """
        Sincroniza ordens de produção com Odoo
        
        Returns:
            Dict com resultado da sincronização
        """
        inicio = datetime.now()
        registros_processados = 0
        registros_erro = 0
        mensagens_erro = []
        
        try:
            # Conectar ao Odoo
            uid = self.connection.authenticate()
            if not uid:
                raise Exception("Falha na autenticação com Odoo")
            
            # Buscar ordens de produção no Odoo
            ordens = self.connection.search_read(
                'mrp.production',
                [['state', 'in', ['confirmed', 'progress', 'to_close', 'done']]],
                ['name', 'product_id', 'product_qty', 'qty_producing', 
                 'qty_produced', 'state', 'date_planned_start', 'date_finished']
            )
            
            for ordem_odoo in ordens:
                try:
                    # Buscar ordem local pelo número
                    ordem_local = OrdemProducao.query.filter_by(
                        numero_ordem=ordem_odoo.get('name')
                    ).first()
                    
                    if ordem_local:
                        # Atualizar quantidade produzida
                        qtd_produzida = Decimal(str(ordem_odoo.get('qty_produced', 0)))
                        if qtd_produzida > 0:
                            ordem_local.qtd_produzida = qtd_produzida
                        
                        # Atualizar status baseado no estado do Odoo
                        estado_odoo = ordem_odoo.get('state')
                        if estado_odoo == 'done':
                            ordem_local.status = 'Concluída'
                            if ordem_odoo.get('date_finished'):
                                try:
                                    ordem_local.data_fim_real = datetime.strptime(
                                        ordem_odoo['date_finished'], '%Y-%m-%d %H:%M:%S'
                                    ).date()
                                except Exception as e:
                                    self.logger.error(f"Erro ao processar data de fim: {e}")
                                    ordem_local.data_fim_real = datetime.now().date()
                        elif estado_odoo in ['progress', 'to_close']:
                            ordem_local.status = 'Em Produção'
                            if not ordem_local.data_inicio_real:
                                ordem_local.data_inicio_real = datetime.now().date()
                        elif estado_odoo == 'confirmed':
                            ordem_local.status = 'Liberada'
                        
                        ordem_local.atualizado_em = datetime.now()
                        registros_processados += 1
                        
                        # Registrar movimentação de estoque se concluída
                        if estado_odoo == 'done' and qtd_produzida > 0:
                            self._registrar_producao_estoque(
                                ordem_local.cod_produto,
                                qtd_produzida,
                                ordem_local.id,
                                ordem_local.numero_ordem
                            )
                        
                        logger.info(f"Ordem {ordem_local.numero_ordem} sincronizada")
                        
                except Exception as e:
                    registros_erro += 1
                    erro_msg = f"Erro ao processar ordem {ordem_odoo.get('name')}: {str(e)}"
                    mensagens_erro.append(erro_msg)
                    logger.error(erro_msg)
            
            # Commit das alterações
            if registros_processados > 0:
                db.session.commit()
            
            # Registrar log
            tempo_execucao = (datetime.now() - inicio).total_seconds()
            self._registrar_log(
                'sincronizar_producao',
                'sucesso' if registros_erro == 0 else 'parcial',
                f'{registros_processados} ordens sincronizadas, {registros_erro} erros',
                registros_processados,
                registros_erro,
                tempo_execucao,
                {'erros': mensagens_erro} if mensagens_erro else None
            )
            
            return {
                'sucesso': True,
                'processados': registros_processados,
                'erros': registros_erro,
                'mensagem': f'{registros_processados} ordens sincronizadas'
            }
            
        except Exception as e:
            db.session.rollback()
            erro_msg = f"Erro geral na sincronização: {str(e)}"
            logger.error(erro_msg)
            
            self._registrar_log(
                'sincronizar_producao',
                'erro',
                erro_msg,
                registros_processados,
                registros_erro
            )
            
            return {
                'sucesso': False,
                'erro': erro_msg,
                'processados': registros_processados,
                'erros': registros_erro
            }
    
    def importar_historico_pedidos(self, mes: int = None, ano: int = None) -> Dict[str, Any]:
        """
        Importa histórico de pedidos do Odoo para análise
        
        Args:
            mes: Mês específico (opcional)
            ano: Ano específico (opcional)
            
        Returns:
            Dict com resultado da importação
        """
        inicio = datetime.now()
        registros_processados = 0
        registros_erro = 0
        
        try:
            # Conectar ao Odoo
            uid = self.connection.authenticate()
            if not uid:
                raise Exception("Falha na autenticação com Odoo")
            
            # Montar filtros
            filtros = [['state', 'in', ['sale', 'done']]]
            if mes and ano:
                data_inicio = f"{ano}-{mes:02d}-01"
                data_fim = f"{ano}-{mes:02d}-31"
                filtros.append(['date_order', '>=', data_inicio])
                filtros.append(['date_order', '<=', data_fim])
            
            # Buscar pedidos de venda no Odoo
            pedidos = self.connection.search_read(
                'sale.order',
                filtros,
                ['name', 'partner_id', 'date_order', 'user_id', 'team_id']
            )
            
            for ped_odoo in pedidos:
                try:
                    # Buscar linhas do pedido
                    linhas = self.connection.search_read(
                        'sale.order.line',
                        [['order_id', '=', ped_odoo['id']]],
                        ['product_id', 'product_uom_qty', 'price_unit', 
                         'price_total', 'tax_id']
                    )
                    
                    # Processar cada linha
                    for linha in linhas:
                        # Verificar se já existe
                        existe = HistoricoPedidos.query.filter_by(
                            num_pedido=ped_odoo.get('name'),
                            cod_produto=str(linha['product_id'][0]) if linha.get('product_id') else None
                        ).first()
                        
                        if not existe:
                            # Processar data
                            data_pedido = datetime.now().date()
                            if ped_odoo.get('date_order'):
                                try:
                                    data_pedido = datetime.strptime(
                                        ped_odoo['date_order'], '%Y-%m-%d %H:%M:%S'
                                    ).date()
                                except Exception as e:
                                    self.logger.error(f"Erro ao processar data de pedido: {e}")
                                    pass
                            
                            # Criar histórico
                            historico = HistoricoPedidos(
                                num_pedido=ped_odoo.get('name'),
                                data_pedido=data_pedido,
                                cnpj_cliente=str(ped_odoo['partner_id'][0]) if ped_odoo.get('partner_id') else None,
                                raz_social_red=ped_odoo['partner_id'][1] if ped_odoo.get('partner_id') else None,
                                vendedor=ped_odoo['user_id'][1] if ped_odoo.get('user_id') else None,
                                equipe_vendas=ped_odoo['team_id'][1] if ped_odoo.get('team_id') else None,
                                cod_produto=str(linha['product_id'][0]) if linha.get('product_id') else None,
                                nome_produto=linha['product_id'][1] if linha.get('product_id') else None,
                                qtd_produto_pedido=Decimal(str(linha.get('product_uom_qty', 0))),
                                preco_produto_pedido=Decimal(str(linha.get('price_unit', 0))),
                                valor_produto_pedido=Decimal(str(linha.get('price_total', 0)))
                            )
                            
                            db.session.add(historico)
                            registros_processados += 1
                            
                except Exception as e:
                    registros_erro += 1
                    logger.error(f"Erro ao processar pedido histórico {ped_odoo.get('name')}: {e}")
            
            # Commit das alterações
            if registros_processados > 0:
                db.session.commit()
            
            # Registrar log
            tempo_execucao = (datetime.now() - inicio).total_seconds()
            self._registrar_log(
                'importar_historico',
                'sucesso' if registros_erro == 0 else 'parcial',
                f'{registros_processados} registros históricos importados',
                registros_processados,
                registros_erro,
                tempo_execucao
            )
            
            return {
                'sucesso': True,
                'processados': registros_processados,
                'erros': registros_erro,
                'mensagem': f'{registros_processados} registros históricos importados'
            }
            
        except Exception as e:
            db.session.rollback()
            erro_msg = f"Erro na importação de histórico: {str(e)}"
            logger.error(erro_msg)
            
            return {
                'sucesso': False,
                'erro': erro_msg,
                'processados': registros_processados,
                'erros': registros_erro
            }
    
    def _registrar_producao_estoque(self, cod_produto: str, quantidade: Decimal, 
                                   ordem_id: int, numero_ordem: str):
        """
        Registra produção no estoque
        
        Args:
            cod_produto: Código do produto
            quantidade: Quantidade produzida
            ordem_id: ID da ordem de produção
            numero_ordem: Número da ordem
        """
        try:
            # Verificar se já foi registrada
            existe = MovimentacaoEstoque.query.filter_by(
                ordem_producao_id=ordem_id,
                tipo_movimentacao='PRODUCAO'
            ).first()
            
            if not existe:
                movimentacao = MovimentacaoEstoque(
                    cod_produto=cod_produto,
                    qtd_movimentacao=quantidade,
                    tipo_movimentacao='PRODUCAO',
                    data_movimentacao=datetime.now(),
                    ordem_producao_id=ordem_id,
                    observacao=f'Produção da ordem {numero_ordem}'
                )
                db.session.add(movimentacao)
                logger.info(f"Movimentação de estoque registrada para ordem {numero_ordem}")
                
        except Exception as e:
            logger.error(f"Erro ao registrar movimentação de estoque: {e}")
    
    def _registrar_log(self, tipo: str, status: str, mensagem: str, 
                      processados: int = 0, erros: int = 0, 
                      tempo: float = None, detalhes: Dict = None):
        """
        Registra log de integração
        
        Args:
            tipo: Tipo de integração
            status: Status da operação
            mensagem: Mensagem descritiva
            processados: Quantidade de registros processados
            erros: Quantidade de erros
            tempo: Tempo de execução em segundos
            detalhes: Detalhes adicionais em JSON
        """
        try:
            log = LogIntegracao(
                tipo_integracao=f"odoo_{tipo}",
                status=status,
                mensagem=mensagem,
                registros_processados=processados,
                registros_erro=erros,
                tempo_execucao=tempo,
                detalhes=detalhes
            )
            db.session.add(log)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Erro ao registrar log: {e}")
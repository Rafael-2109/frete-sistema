"""
Serviço de Faturamento - Integração Odoo Correta
===============================================

Este serviço implementa a integração correta com o Odoo usando múltiplas consultas
ao invés de campos com "/" que não funcionam.

Baseado na descoberta realizada em 2025-07-14.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import sessionmaker

from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.campo_mapper import CampoMapper
from app import db

logger = logging.getLogger(__name__)

class FaturamentoService:
    """
    Serviço para integração de faturamento com Odoo
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mapper = CampoMapper()
    
    def importar_faturamento_odoo(self, filtros: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Importa dados de faturamento do Odoo usando a abordagem correta
        
        Args:
            filtros: Filtros para aplicar na consulta
            
        Returns:
            Resultado da importação
        """
        try:
            self.logger.info("Iniciando importação de faturamento do Odoo")
            
            # Conectar ao Odoo
            connection = get_odoo_connection()
            if not connection:
                raise Exception("Não foi possível conectar ao Odoo")
            
            # Aplicar filtros padrão se não fornecidos
            if filtros is None:
                filtros = {
                    'state': 'sale',  # Apenas pedidos confirmados
                    'data_inicio': datetime.now().strftime('%Y-%m-01'),  # Primeiro dia do mês atual
                }
            
            # Buscar dados do Odoo
            self.logger.info(f"Buscando dados do Odoo com filtros: {filtros}")
            dados_odoo = self.mapper.buscar_dados_completos(connection, filtros)
            
            if not dados_odoo:
                return {
                    'success': False,
                    'message': 'Nenhum dado encontrado no Odoo',
                    'total_importado': 0,
                    'total_processado': 0
                }
            
            # Mapear para formato de faturamento
            self.logger.info("Mapeando dados para formato de faturamento")
            dados_faturamento = self.mapper.mapear_para_faturamento(dados_odoo)
            
            # Processar dados
            resultado_processamento = self._processar_dados_faturamento(dados_faturamento)
            
            # Consolidar para RelatorioFaturamentoImportado
            resultado_consolidacao = self._consolidar_faturamento(dados_faturamento)
            
            self.logger.info("Importação de faturamento concluída com sucesso")
            
            return {
                'success': True,
                'message': 'Dados importados com sucesso',
                'total_importado': len(dados_odoo),
                'total_processado': resultado_processamento['total_processado'],
                'total_consolidado': resultado_consolidacao['total_consolidado'],
                'total_faturamento_produto': resultado_processamento['total_faturamento_produto'],
                'total_relatorio_importado': resultado_consolidacao['total_relatorio_importado'],
                'filtros_aplicados': filtros,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Erro na importação de faturamento: {e}")
            return {
                'success': False,
                'message': f'Erro na importação: {str(e)}',
                'total_importado': 0,
                'total_processado': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    def _processar_dados_faturamento(self, dados_faturamento: List[Dict]) -> Dict[str, Any]:
        """
        Processa dados de faturamento e salva na tabela FaturamentoProduto
        """
        try:
            self.logger.info(f"Processando {len(dados_faturamento)} registros de faturamento")
            
            total_processado = 0
            total_faturamento_produto = 0
            
            for dado in dados_faturamento:
                try:
                    # Verificar se já existe para evitar duplicatas
                    existe = db.session.query(FaturamentoProduto).filter_by(
                        numero_nf=dado.get('nome_pedido'),
                        cod_produto=dado.get('codigo_produto')
                    ).first()
                    
                    if not existe:
                        # Criar novo registro de FaturamentoProduto
                        faturamento_produto = FaturamentoProduto()
                        
                        # Dados da NF
                        faturamento_produto.numero_nf = dado.get('nome_pedido')
                        data_pedido = self._parse_date(dado.get('data_pedido'))
                        faturamento_produto.data_fatura = data_pedido.date() if data_pedido else None
                        
                        # Dados do cliente
                        faturamento_produto.cnpj_cliente = dado.get('cnpj_cliente')
                        faturamento_produto.nome_cliente = dado.get('nome_cliente')
                        faturamento_produto.municipio = dado.get('municipio_cliente')
                        faturamento_produto.estado = dado.get('estado_cliente')
                        
                        # Dados do vendedor
                        faturamento_produto.vendedor = dado.get('vendedor')
                        faturamento_produto.incoterm = dado.get('incoterm')
                        
                        # Dados do produto
                        faturamento_produto.cod_produto = dado.get('codigo_produto')
                        faturamento_produto.nome_produto = dado.get('nome_produto')
                        faturamento_produto.qtd_produto_faturado = dado.get('quantidade_produto')
                        faturamento_produto.preco_produto_faturado = dado.get('preco_unitario')
                        faturamento_produto.valor_produto_faturado = dado.get('total_nfe_br')
                        faturamento_produto.peso_unitario_produto = dado.get('peso_produto')
                        faturamento_produto.peso_total = (dado.get('peso_produto') or 0) * (dado.get('quantidade_produto') or 0)
                        
                        # Origem
                        faturamento_produto.origem = dado.get('pedido_compra')
                        
                        # Status
                        faturamento_produto.status_nf = self._mapear_status(dado.get('status_pedido'))
                        
                        # Auditoria
                        faturamento_produto.created_by = 'odoo_integracao_correta'
                        
                        db.session.add(faturamento_produto)
                        total_faturamento_produto += 1
                    else:
                        # Atualizar registro existente
                        data_pedido = self._parse_date(dado.get('data_pedido'))
                        existe.data_fatura = data_pedido.date() if data_pedido else None
                        existe.cnpj_cliente = dado.get('cnpj_cliente')
                        existe.nome_cliente = dado.get('nome_cliente')
                        existe.municipio = dado.get('municipio_cliente')
                        existe.estado = dado.get('estado_cliente')
                        existe.vendedor = dado.get('vendedor')
                        existe.incoterm = dado.get('incoterm')
                        existe.nome_produto = dado.get('nome_produto')
                        existe.qtd_produto_faturado = dado.get('quantidade_produto')
                        existe.preco_produto_faturado = dado.get('preco_unitario')
                        existe.valor_produto_faturado = dado.get('total_nfe_br')
                        existe.peso_unitario_produto = dado.get('peso_produto')
                        existe.peso_total = (dado.get('peso_produto') or 0) * (dado.get('quantidade_produto') or 0)
                        existe.origem = dado.get('pedido_compra')
                        existe.status_nf = self._mapear_status(dado.get('status_pedido'))
                        existe.updated_by = 'odoo_integracao_correta'
                    
                    total_processado += 1
                    
                    # Commit a cada 100 registros para otimizar performance
                    if total_processado % 100 == 0:
                        db.session.commit()
                        self.logger.info(f"Processados {total_processado} registros")
                
                except Exception as e:
                    self.logger.error(f"Erro ao processar registro {dado.get('nome_pedido', 'desconhecido')}: {e}")
                    db.session.rollback()
                    continue
            
            # Commit final
            db.session.commit()
            
            self.logger.info(f"Processamento concluído: {total_processado} registros processados, {total_faturamento_produto} novos registros")
            
            return {
                'total_processado': total_processado,
                'total_faturamento_produto': total_faturamento_produto
            }
            
        except Exception as e:
            self.logger.error(f"Erro no processamento de faturamento: {e}")
            db.session.rollback()
            return {
                'total_processado': 0,
                'total_faturamento_produto': 0
            }
    
    def _mapear_status(self, status_odoo: Optional[str]) -> str:
        """
        Mapeia status do Odoo para status do sistema
        """
        if not status_odoo:
            return 'ATIVO'
        
        status_map = {
            'draft': 'RASCUNHO',
            'sent': 'ENVIADO',
            'sale': 'ATIVO',
            'done': 'ATIVO',
            'cancel': 'CANCELADO'
        }
        
        return status_map.get(status_odoo.lower(), 'ATIVO')
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Converte string de data para datetime
        """
        if not date_str:
            return None
        
        try:
            # Formato do Odoo: 2025-07-14 20:19:52
            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            return dt  # Retorna datetime para compatibilidade
        except ValueError:
            try:
                # Formato de data apenas: 2025-07-14
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                return dt  # Retorna datetime para compatibilidade
            except ValueError:
                self.logger.warning(f"Formato de data inválido: {date_str}")
                return None
    
    def _consolidar_faturamento(self, dados_faturamento: List[Dict]) -> Dict[str, Any]:
        """
        Consolida dados de faturamento para RelatorioFaturamentoImportado
        """
        try:
            self.logger.info("Consolidando dados para RelatorioFaturamentoImportado")
            
            total_consolidado = 0
            total_relatorio_importado = 0
            
            # Agrupar por pedido para consolidação
            pedidos_consolidados = {}
            
            for dado in dados_faturamento:
                pedido_key = f"{dado.get('id_pedido')}_{dado.get('nome_pedido')}"
                
                if pedido_key not in pedidos_consolidados:
                    pedidos_consolidados[pedido_key] = {
                        'id_pedido_odoo': dado.get('id_pedido'),
                        'nome_pedido': dado.get('nome_pedido'),
                        'pedido_compra': dado.get('pedido_compra'),
                        'nome_cliente': dado.get('nome_cliente'),
                        'cnpj_cliente': dado.get('cnpj_cliente'),
                        'data_fatura': dado.get('data_pedido'),
                        'valor_total': 0,
                        'origem': dado.get('pedido_compra'),  # Campo origem = número do pedido
                        'incoterm': dado.get('incoterm'),
                        'status_pedido': dado.get('status_pedido'),
                        'vendedor': dado.get('vendedor'),
                        'time_vendas': dado.get('time_vendas'),
                        'municipio_cliente': dado.get('municipio_cliente'),
                        'estado_cliente': dado.get('estado_cliente'),
                        'data_criacao': dado.get('data_criacao'),
                        'itens': []
                    }
                
                # Adicionar valor do item ao total
                pedidos_consolidados[pedido_key]['valor_total'] += (dado.get('total') or 0)
                
                # Adicionar item
                pedidos_consolidados[pedido_key]['itens'].append({
                    'codigo_produto': dado.get('codigo_produto'),
                    'nome_produto': dado.get('nome_produto'),
                    'quantidade': dado.get('quantidade_produto'),
                    'preco_unitario': dado.get('preco_unitario'),
                    'valor_total': dado.get('total')
                })
                
                total_consolidado += 1
            
            # Salvar dados consolidados
            for pedido_key, dados_pedido in pedidos_consolidados.items():
                try:
                    # Verificar se já existe
                    existe = db.session.query(RelatorioFaturamentoImportado).filter_by(
                        origem=dados_pedido['origem'],
                        nome_cliente=dados_pedido['nome_cliente']
                    ).first()
                    
                    if not existe:
                        relatorio = RelatorioFaturamentoImportado()
                        relatorio.nome_cliente = dados_pedido['nome_cliente']
                        relatorio.cnpj_cliente = dados_pedido['cnpj_cliente']
                        relatorio.numero_nf = dados_pedido['nome_pedido']
                        data_fatura = self._parse_date(dados_pedido['data_fatura'])
                        relatorio.data_fatura = data_fatura.date() if data_fatura else None
                        relatorio.valor_total = dados_pedido['valor_total']
                        relatorio.origem = dados_pedido['origem']
                        relatorio.incoterm = dados_pedido['incoterm']
                        relatorio.vendedor = dados_pedido['vendedor']
                        relatorio.municipio = dados_pedido['municipio_cliente']
                        relatorio.estado = dados_pedido['estado_cliente']
                        
                        db.session.add(relatorio)
                        total_relatorio_importado += 1
                    else:
                        # Atualizar registro existente
                        existe.valor_total = dados_pedido['valor_total']
                        existe.status_faturamento = dados_pedido['status_pedido']
                        existe.data_importacao = datetime.now()
                        existe.origem_importacao = 'odoo_integracao_correta'
                
                except Exception as e:
                    self.logger.error(f"Erro ao consolidar pedido {pedido_key}: {e}")
                    continue
            
            # Commit final
            db.session.commit()
            
            self.logger.info(f"Consolidação concluída: {total_consolidado} itens processados, {total_relatorio_importado} relatórios criados")
            
            return {
                'total_consolidado': total_consolidado,
                'total_relatorio_importado': total_relatorio_importado
            }
            
        except Exception as e:
            self.logger.error(f"Erro na consolidação: {e}")
            db.session.rollback()
            return {
                'total_consolidado': 0,
                'total_relatorio_importado': 0
            }
    
    def buscar_faturamento_por_filtro(self, filtro: str) -> List[Dict]:
        """
        Busca dados de faturamento com filtros específicos
        """
        try:
            self.logger.info(f"Buscando faturamento com filtro: {filtro}")
            
            # Conectar ao Odoo
            connection = get_odoo_connection()
            if not connection:
                return []
            
            # Definir filtros baseados no parâmetro
            filtros = {}
            
            if filtro.lower() == 'faturamento_pendente':
                filtros = {
                    'state': 'sale',
                    'invoice_status': 'to invoice'
                }
            elif filtro.lower() == 'faturamento_parcial':
                filtros = {
                    'state': 'sale',
                    'invoice_status': 'partial'
                }
            elif filtro.lower() == 'faturamento_completo':
                filtros = {
                    'state': 'sale',
                    'invoice_status': 'invoiced'
                }
            else:
                # Filtro personalizado
                filtros = {'state': 'sale'}
            
            # Buscar dados
            dados_odoo = self.mapper.buscar_dados_completos(connection, filtros)
            
            # Mapear para faturamento
            dados_faturamento = self.mapper.mapear_para_faturamento(dados_odoo)
            
            return dados_faturamento
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar faturamento por filtro: {e}")
            return []
    
    def sincronizar_faturamento_completo(self) -> Dict[str, Any]:
        """
        Sincroniza faturamento completo do Odoo
        """
        try:
            self.logger.info("Iniciando sincronização completa de faturamento")
            
            # Buscar dados do mês atual
            resultado = self.importar_faturamento_odoo()
            
            if resultado['success']:
                # Buscar dados históricos (últimos 3 meses)
                for mes_offset in range(1, 4):
                    data_inicio = datetime.now().replace(day=1)
                    if mes_offset == 1:
                        data_inicio = data_inicio.replace(month=data_inicio.month - 1)
                    elif mes_offset == 2:
                        data_inicio = data_inicio.replace(month=data_inicio.month - 2)
                    elif mes_offset == 3:
                        data_inicio = data_inicio.replace(month=data_inicio.month - 3)
                    
                    filtros_historico = {
                        'state': 'sale',
                        'data_inicio': data_inicio.strftime('%Y-%m-%d')
                    }
                    
                    resultado_historico = self.importar_faturamento_odoo(filtros_historico)
                    
                    if resultado_historico['success']:
                        resultado['total_importado'] += resultado_historico['total_importado']
                        resultado['total_processado'] += resultado_historico['total_processado']
                
                resultado['message'] = 'Sincronização completa realizada com sucesso'
            
            return resultado
            
        except Exception as e:
            self.logger.error(f"Erro na sincronização completa: {e}")
            return {
                'success': False,
                'message': f'Erro na sincronização: {str(e)}',
                'total_importado': 0,
                'total_processado': 0
            } 
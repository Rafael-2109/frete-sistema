"""
Serviço de Carteira Odoo
========================

Serviço responsável por gerenciar a importação de dados de carteira de pedidos
do Odoo ERP usando o mapeamento CORRETO.

ATUALIZADO: Usa CampoMapper com múltiplas consultas ao invés de campos com "/"

Funcionalidades:
- Importação de carteira pendente
- Filtro por período e pedidos específicos
- Estatísticas básicas

Autor: Sistema de Fretes
Data: 2025-07-14
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from decimal import Decimal

from app.odoo.utils.connection import get_odoo_connection
from app.odoo.utils.campo_mapper import CampoMapper

logger = logging.getLogger(__name__)

class CarteiraService:
    """Serviço para gerenciar carteira de pedidos do Odoo usando mapeamento correto"""
    
    def __init__(self):
        self.connection = get_odoo_connection()
        self.mapper = CampoMapper()  # Usar novo CampoMapper
    
    def obter_carteira_pendente(self, data_inicio=None, data_fim=None, pedidos_especificos=None):
        """
        Obter carteira pendente do Odoo com campos corretos
        """
        logger.info("Buscando carteira pendente do Odoo...")
        
        try:
            # Conectar ao Odoo
            if not self.connection:
                return {
                    'sucesso': False,
                    'erro': 'Conexão com Odoo não disponível',
                    'dados': []
                }
            
            # Usar filtros para carteira pendente
            filtros_carteira = {
                'modelo': 'carteira',
                'carteira_pendente': True
            }
            
            # Adicionar filtros opcionais
            if data_inicio:
                filtros_carteira['data_inicio'] = data_inicio
            if data_fim:
                filtros_carteira['data_fim'] = data_fim
            if pedidos_especificos:
                filtros_carteira['pedidos_especificos'] = pedidos_especificos
            
            # Usar novo método do CampoMapper
            logger.info("Usando buscar_carteira_odoo com múltiplas consultas...")
            dados_carteira = self.mapper.buscar_carteira_odoo(self.connection, filtros_carteira)
            
            if dados_carteira:
                logger.info(f"✅ SUCESSO: {len(dados_carteira)} registros encontrados")
                
                # Processar dados para formato esperado
                dados_processados = self._processar_dados_carteira(dados_carteira)
                
                return {
                    'sucesso': True,
                    'dados': dados_processados,
                    'total_registros': len(dados_processados),
                    'mensagem': f'✅ {len(dados_processados)} registros processados com campos corretos'
                }
            else:
                logger.warning("Nenhum dado de carteira pendente encontrado")
                return {
                    'sucesso': True,
                    'dados': [],
                    'total_registros': 0,
                    'mensagem': 'Nenhuma carteira pendente encontrada'
                }
            
        except Exception as e:
            logger.error(f"❌ ERRO: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'dados': [],
                'mensagem': 'Erro ao buscar carteira pendente'
            }
    
    def _processar_dados_carteira(self, dados_carteira: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processa dados de carteira
        """
        dados_processados = []
        
        for item in dados_carteira:
            try:
                # Processar cada item da carteira com campos corretos
                item_processado = {
                    # Campos principais (mapeamento correto)
                    'pedido_compra_cliente': item.get('pedido_compra_cliente'),
                    'referencia_pedido': item.get('referencia_pedido'),
                    'data_criacao': self._format_date(item.get('data_criacao')),
                    'data_pedido': self._format_date(item.get('data_pedido')),
                    
                    # Cliente (campos brasileiros corretos)
                    'cnpj_cliente': item.get('cnpj_cliente'),
                    'razao_social': item.get('razao_social'),
                    'nome_cliente': item.get('nome_cliente'),
                    'municipio_cliente': item.get('municipio_cliente'),
                    'estado_cliente': item.get('estado_cliente'),
                    
                    # Vendedor e Equipe
                    'vendedor': item.get('vendedor'),
                    'equipe_vendas': item.get('equipe_vendas'),
                    
                    # Produto
                    'codigo_produto': item.get('referencia_interna'),
                    'nome_produto': item.get('nome_produto'),
                    'unidade_medida': item.get('unidade_medida'),
                    
                    # Quantidades (campos corretos)
                    'quantidade': self._format_decimal(item.get('quantidade')),
                    'quantidade_a_faturar': self._format_decimal(item.get('quantidade_a_faturar')),
                    'saldo': self._format_decimal(item.get('saldo')),
                    'cancelado': self._format_decimal(item.get('cancelado')),
                    'quantidade_faturada': self._format_decimal(item.get('quantidade_faturada')),
                    'quantidade_entregue': self._format_decimal(item.get('quantidade_entregue')),
                    
                    # Valores
                    'preco_unitario': self._format_decimal(item.get('preco_unitario')),
                    'valor_produto': self._format_decimal(item.get('valor_produto')),
                    'valor_item_pedido': self._format_decimal(item.get('valor_item_pedido')),
                    
                    # Status
                    'status': item.get('status_pedido'),
                    
                    # Categoria do produto
                    'categoria_produto': item.get('categoria_produto'),
                    'categoria_primaria': item.get('categoria_primaria'),
                    'categoria_primaria_pai': item.get('categoria_primaria_pai'),
                    
                    # Pagamento e Entrega
                    'condicoes_pagamento': item.get('condicoes_pagamento'),
                    'forma_pagamento': item.get('forma_pagamento'),
                    'notas_expedicao': item.get('notas_expedicao'),
                    'incoterm': item.get('incoterm'),
                    'metodo_entrega': item.get('metodo_entrega'),
                    'data_entrega': self._format_date(item.get('data_entrega')),
                    'agendamento_cliente': item.get('agendamento_cliente'),
                    
                    # Endereço de entrega (todos os campos brasileiros)
                    'cnpj_endereco_entrega': item.get('cnpj_endereco_entrega'),
                    'proprio_endereco': item.get('proprio_endereco'),
                    'cep_entrega': item.get('cep_entrega'),
                    'estado_entrega': item.get('estado_entrega'),
                    'municipio_entrega': item.get('municipio_entrega'),
                    'bairro_entrega': item.get('bairro_entrega'),
                    'endereco_entrega': item.get('endereco_entrega'),
                    'numero_entrega': item.get('numero_entrega'),
                    'telefone_entrega': item.get('telefone_entrega')
                }
                
                # Adicionar apenas se tem dados válidos e saldo > 0
                if (item_processado['referencia_pedido'] and 
                    item_processado['saldo'] and 
                    item_processado['saldo'] > 0):
                    dados_processados.append(item_processado)
                    
            except Exception as e:
                logger.error(f"Erro ao processar item da carteira: {e}")
                continue
        
        return dados_processados
    
    def _format_date(self, date_value) -> str:
        """Formata data para string"""
        if not date_value:
            return ''
        
        if isinstance(date_value, str):
            try:
                dt = datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S')
                return dt.strftime('%d/%m/%Y')
            except ValueError:
                try:
                    dt = datetime.strptime(date_value, '%Y-%m-%d')
                    return dt.strftime('%d/%m/%Y')
                except ValueError:
                    return str(date_value)
        return str(date_value)
    
    def _format_decimal(self, value) -> float:
        """Formata valor decimal"""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _calcular_estatisticas(self, dados: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula estatísticas básicas da carteira"""
        if not dados:
            return {
                'total_itens': 0,
                'total_pedidos': 0,
                'valor_total': 0.0,
                'quantidade_total': 0.0,
                'saldo_total': 0.0
            }
        
        # Calcular estatísticas
        total_itens = len(dados)
        pedidos_unicos = len(set(item['referencia_pedido'] for item in dados if item['referencia_pedido']))
        valor_total = sum(item['valor_item_pedido'] for item in dados if item['valor_item_pedido'])
        quantidade_total = sum(item['quantidade'] for item in dados if item['quantidade'])
        saldo_total = sum(item['saldo'] for item in dados if item['saldo'])
        
        return {
            'total_itens': total_itens,
            'total_pedidos': pedidos_unicos,
            'valor_total': valor_total,
            'quantidade_total': quantidade_total,
            'saldo_total': saldo_total
        }

def sincronizar_carteira_odoo(usar_filtro_pendente=True):
    """
    Sincroniza carteira do Odoo por substituição completa da CarteiraPrincipal
    ATUALIZADO: Usa novo CampoMapper
    
    Args:
        usar_filtro_pendente (bool): Se deve usar filtro 'Carteira Pendente' (qty_saldo > 0)
    
    Returns:
        dict: Estatísticas da sincronização
    """
    try:
        from app.carteira.models import CarteiraPrincipal
        from app import db
        from flask_login import current_user
        from datetime import datetime
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Criar instância do serviço ATUALIZADO
        service = CarteiraService()
        
        # Buscar dados do Odoo usando método correto
        resultado_busca = service.obter_carteira_pendente()
        
        if not resultado_busca['sucesso']:
            return {
                'sucesso': False,
                'erro': resultado_busca.get('erro', 'Nenhum dado encontrado no Odoo'),
                'registros_importados': 0,
                'registros_removidos': 0
            }
        
        dados_odoo = resultado_busca['dados']
        
        if not dados_odoo:
            return {
                'sucesso': False,
                'erro': 'Nenhum dado de carteira encontrado',
                'registros_importados': 0,
                'registros_removidos': 0
            }
        
        # Aplicar filtro pendente se solicitado
        if usar_filtro_pendente:
            dados_filtrados = [
                item for item in dados_odoo
                if item.get('saldo', 0) > 0
            ]
        else:
            dados_filtrados = dados_odoo
        
        # SUBSTITUIÇÃO COMPLETA: Remover todos os registros existentes
        registros_removidos = CarteiraPrincipal.query.count()
        CarteiraPrincipal.query.delete()
        
        registros_importados = 0
        erros = []
        
        # Processar cada item da carteira
        for item in dados_filtrados:
            try:
                # Validar campos obrigatórios
                referencia_pedido = item.get('referencia_pedido')
                codigo_produto = item.get('codigo_produto')
                
                if not referencia_pedido or not codigo_produto:
                    continue
                
                # Processar datas
                data_pedido = None
                if item.get('data_pedido'):
                    try:
                        data_pedido_str = item.get('data_pedido')
                        if isinstance(data_pedido_str, str) and data_pedido_str:
                            # Converter formato DD/MM/YYYY para date
                            if '/' in data_pedido_str:
                                data_pedido = datetime.strptime(data_pedido_str, '%d/%m/%Y').date()
                            else:
                                data_pedido = datetime.strptime(data_pedido_str, '%Y-%m-%d').date()
                    except Exception as e:
                        logger.warning(f"Erro ao processar data_pedido: {e}")
                
                # Processar valores
                quantidade = float(item.get('quantidade', 0)) or 0
                quantidade_faturada = float(item.get('quantidade_faturada', 0)) or 0
                saldo = float(item.get('saldo', 0)) or 0
                preco_unitario = float(item.get('preco_unitario', 0)) or 0
                valor_item_pedido = float(item.get('valor_item_pedido', 0)) or 0
                
                # Criar novo registro na CarteiraPrincipal
                novo_registro = CarteiraPrincipal()
                novo_registro.pedido_id = str(referencia_pedido)
                novo_registro.data_pedido = data_pedido
                novo_registro.data_prevista = data_pedido  # Usar mesma data se não houver data_entrega
                novo_registro.cnpj_cliente = str(item.get('cnpj_cliente', '')).strip()
                novo_registro.nome_cliente = str(item.get('nome_cliente', '')).strip()
                novo_registro.cod_produto = str(codigo_produto).strip()
                novo_registro.nome_produto = str(item.get('nome_produto', '')).strip()
                novo_registro.qtd_pedido = quantidade
                novo_registro.qtd_faturado = quantidade_faturada
                novo_registro.qtd_saldo = saldo
                novo_registro.valor_unitario = preco_unitario
                novo_registro.valor_total = valor_item_pedido
                novo_registro.vendedor = str(item.get('vendedor', '')).strip()
                novo_registro.incoterm = str(item.get('incoterm', '')).strip()
                novo_registro.municipio = str(item.get('municipio_cliente', '')).strip()
                novo_registro.estado = str(item.get('estado_cliente', '')).strip()
                novo_registro.endereco_entrega = str(item.get('endereco_entrega', '')).strip()
                novo_registro.bairro_entrega = str(item.get('bairro_entrega', '')).strip()
                novo_registro.cep_entrega = str(item.get('cep_entrega', '')).strip()
                novo_registro.municipio_entrega = str(item.get('municipio_entrega', '')).strip()
                novo_registro.estado_entrega = str(item.get('estado_entrega', '')).strip()
                novo_registro.observacoes = str(item.get('notas_expedicao', '')).strip()
                novo_registro.peso_bruto = float(item.get('peso_bruto', 0)) or 0
                novo_registro.peso_liquido = float(item.get('peso_liquido', 0)) or 0
                novo_registro.volume = float(item.get('volume', 0)) or 0
                novo_registro.created_by = current_user.nome if current_user else 'Sistema'
                
                db.session.add(novo_registro)
                registros_importados += 1
                
            except Exception as e:
                erros.append(f"Erro ao processar pedido {referencia_pedido}: {str(e)}")
                logger.error(f"Erro sincronização carteira: {e}")
                continue
        
        # Commit das alterações
        db.session.commit()
        
        resultado = {
            'sucesso': True,
            'registros_importados': registros_importados,
            'registros_removidos': registros_removidos,
            'erros': erros[:5]  # Primeiros 5 erros
        }
        
        logger.info(f"Sincronização carteira concluída: {resultado}")
        return resultado
        
    except Exception as e:
        logger.error(f"Erro na sincronização da carteira: {e}")
        db.session.rollback()
        return {
            'sucesso': False,
            'erro': str(e),
            'registros_importados': 0,
            'registros_removidos': 0
        } 
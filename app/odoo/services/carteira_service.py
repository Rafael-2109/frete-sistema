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
            
            # Usar novo método do CampoMapper com múltiplas queries
            logger.info("Usando sistema de múltiplas queries para carteira...")
            
            # Primeiro buscar dados brutos do Odoo
            domain = [('qty_saldo', '>', 0)]  # Carteira pendente
            campos_basicos = ['id', 'order_id', 'product_id', 'product_uom_qty', 'qty_saldo', 'qty_cancelado', 'price_unit']
            
            dados_odoo_brutos = self.connection.search_read('sale.order.line', domain, campos_basicos, limit=100)
            
            if dados_odoo_brutos:
                logger.info(f"✅ SUCESSO: {len(dados_odoo_brutos)} registros encontrados")
                
                # Processar dados usando mapeamento completo com múltiplas queries
                dados_processados = self._processar_dados_carteira_com_multiplas_queries(dados_odoo_brutos)
                
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
        Processa dados de carteira usando campos EXATOS do modelo CarteiraPrincipal
        
        Baseado em: projeto_carteira/mapeamento_carteira.csv
        """
        dados_processados = []
        
        for item in dados_carteira:
            try:
                # Processar usando EXATAMENTE os nomes do modelo CarteiraPrincipal
                item_processado = {
                    # 🆔 CHAVES PRIMÁRIAS DE NEGÓCIO
                    'num_pedido': item.get('num_pedido', ''),
                    'cod_produto': item.get('cod_produto', ''),
                    
                    # 📋 DADOS DO PEDIDO
                    'pedido_cliente': item.get('pedido_cliente', ''),
                    'data_pedido': self._format_date(item.get('data_pedido')),
                    'data_atual_pedido': self._format_date(item.get('data_atual_pedido')),
                    'status_pedido': item.get('status_pedido', ''),
                    
                    # 👥 DADOS DO CLIENTE
                    'cnpj_cpf': item.get('cnpj_cpf', ''),
                    'raz_social': item.get('raz_social', ''),
                    'raz_social_red': item.get('raz_social_red', ''),
                    'municipio': item.get('municipio', ''),
                    'estado': item.get('estado', ''),
                    'vendedor': item.get('vendedor', ''),
                    'equipe_vendas': item.get('equipe_vendas', ''),
                    
                    # 📦 DADOS DO PRODUTO
                    'nome_produto': item.get('nome_produto', ''),
                    'unid_medida_produto': item.get('unid_medida_produto', ''),
                    'embalagem_produto': item.get('embalagem_produto', ''),
                    'materia_prima_produto': item.get('materia_prima_produto', ''),
                    'categoria_produto': item.get('categoria_produto', ''),
                    
                    # 📊 QUANTIDADES E VALORES
                    'qtd_produto_pedido': self._format_decimal(item.get('qtd_produto_pedido', 0)),
                    'qtd_saldo_produto_pedido': self._format_decimal(item.get('qtd_saldo_produto_pedido', 0)),
                    'qtd_cancelada_produto_pedido': self._format_decimal(item.get('qtd_cancelada_produto_pedido', 0)),
                    'preco_produto_pedido': self._format_decimal(item.get('preco_produto_pedido', 0)),
                    
                    # 💳 CONDIÇÕES COMERCIAIS
                    'cond_pgto_pedido': item.get('cond_pgto_pedido', ''),
                    'forma_pgto_pedido': item.get('forma_pgto_pedido', ''),
                    'incoterm': item.get('incoterm', ''),
                    'metodo_entrega_pedido': item.get('metodo_entrega_pedido', ''),
                    'data_entrega_pedido': self._format_date(item.get('data_entrega_pedido')),
                    'cliente_nec_agendamento': item.get('cliente_nec_agendamento', ''),
                    'observ_ped_1': item.get('observ_ped_1', ''),
                    
                    # 🏠 ENDEREÇO DE ENTREGA COMPLETO
                    'cnpj_endereco_ent': item.get('cnpj_endereco_ent', ''),
                    'empresa_endereco_ent': item.get('empresa_endereco_ent', ''),
                    'cep_endereco_ent': item.get('cep_endereco_ent', ''),
                    'nome_cidade': item.get('nome_cidade', ''),
                    'cod_uf': item.get('cod_uf', ''),
                    'bairro_endereco_ent': item.get('bairro_endereco_ent', ''),
                    'rua_endereco_ent': item.get('rua_endereco_ent', ''),
                    'endereco_ent': item.get('endereco_ent', ''),
                    'telefone_endereco_ent': item.get('telefone_endereco_ent', ''),
                    
                    # Dados gerados automaticamente (timestamp, usuário)
                    'data_importacao': datetime.now(),
                    'usuario_importacao': 'Sistema Odoo'
                }
                
                dados_processados.append(item_processado)
                
            except Exception as e:
                self.logger.warning(f"Erro ao processar item da carteira: {e}")
                continue
        
        self.logger.info(f"✅ {len(dados_processados)} itens processados com campos exatos")
        return dados_processados
    
    def _processar_dados_carteira_com_multiplas_queries(self, dados_odoo_brutos: List[Dict]) -> List[Dict]:
        """
        Processa dados da carteira usando o sistema completo de múltiplas queries
        Resolve os 11 campos complexos que precisam de consultas relacionadas
        """
        try:
            logger.info("Processando carteira com sistema de múltiplas queries...")
            
            # Usar o mapeamento completo que suporta múltiplas queries
            dados_mapeados = self.mapper.mapear_para_carteira_completo(dados_odoo_brutos, self.connection)
            
            # Mostrar estatísticas do mapeamento
            stats = self.mapper.obter_estatisticas_mapeamento()
            logger.info(f"📊 Estatísticas do mapeamento:")
            logger.info(f"   Total de campos: {stats['total_campos']}")
            logger.info(f"   Campos simples: {stats['campos_simples']} ({stats['percentual_simples']:.1f}%)")
            logger.info(f"   Campos complexos: {stats['campos_complexos']} ({stats['percentual_complexos']:.1f}%)")
            
            # Contar campos resolvidos vs não resolvidos
            campos_resolvidos = 0
            campos_nulos = 0
            
            for item in dados_mapeados:
                for campo, valor in item.items():
                    if valor is not None and valor != '':
                        campos_resolvidos += 1
                    else:
                        campos_nulos += 1
            
            taxa_resolucao = (campos_resolvidos / (campos_resolvidos + campos_nulos) * 100) if (campos_resolvidos + campos_nulos) > 0 else 0
            
            logger.info(f"🎯 Taxa de resolução de campos: {taxa_resolucao:.1f}%")
            logger.info(f"   Campos resolvidos: {campos_resolvidos}")
            logger.info(f"   Campos nulos: {campos_nulos}")
            
            return dados_mapeados
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento com múltiplas queries: {e}")
            return []

    def _format_date(self, data_str: Any) -> Optional[date]:
        """Formata string de data para objeto date"""
        if not data_str:
            return None
        try:
            if isinstance(data_str, str):
                # Tenta diferentes formatos
                for formato in ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']:
                    try:
                        return datetime.strptime(data_str, formato).date()
                    except ValueError:
                        continue
            return None
        except Exception as e:
            self.logger.warning(f"Erro ao formatar data: {data_str} - {e}")
            return None

    def _format_decimal(self, valor: Any) -> Optional[float]:
        """Formata valor para decimal"""
        try:
            return float(valor) if valor is not None else 0.0
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

    def sincronizar_carteira_odoo(self, usar_filtro_pendente=True):
        """
        Sincroniza carteira do Odoo por substituição completa da CarteiraPrincipal
        ATUALIZADO: Usa novo CampoMapper com campos EXATOS
        
        Args:
            usar_filtro_pendente (bool): Se deve usar filtro 'Carteira Pendente' (qty_saldo > 0)
        
        Returns:
            dict: Estatísticas da sincronização
        """
        try:
            from app.carteira.models import CarteiraPrincipal
            from app import db
            
            self.logger.info("Iniciando sincronização completa da carteira com Odoo")
            
            # Buscar dados do Odoo usando novo mapper
            from app.odoo.utils.connection import get_odoo_connection
            connection = get_odoo_connection()
            if not connection:
                return {
                    'sucesso': False,
                    'erro': 'Não foi possível conectar ao Odoo',
                    'estatisticas': {}
                }
            
            dados_carteira = self.mapper.buscar_carteira_odoo(connection)
            
            if not dados_carteira:
                return {
                    'sucesso': False,
                    'erro': 'Nenhum dado encontrado no Odoo',
                    'estatisticas': {}
                }
            
            # Filtrar por saldo pendente se solicitado
            if usar_filtro_pendente:
                dados_filtrados = [
                    item for item in dados_carteira 
                    if item.get('qtd_saldo_produto_pedido', 0) > 0
                ]
            else:
                dados_filtrados = dados_carteira
            
            # Limpar tabela CarteiraPrincipal completamente
            self.logger.info("🧹 Limpando tabela CarteiraPrincipal...")
            db.session.query(CarteiraPrincipal).delete()
            
            # Inserir novos dados usando campos EXATOS
            contador_inseridos = 0
            
            for item_mapeado in dados_filtrados:
                try:
                    # Criar registro usando campos exatos do modelo
                    novo_registro = CarteiraPrincipal(**item_mapeado)
                    db.session.add(novo_registro)
                    contador_inseridos += 1
                    
                except Exception as e:
                    self.logger.error(f"Erro ao inserir item: {e}")
                    continue
            
            # Commit das alterações
            db.session.commit()
            
            # Estatísticas finais
            estatisticas = {
                'registros_inseridos': contador_inseridos,
                'total_encontrados': len(dados_carteira),
                'registros_filtrados': len(dados_filtrados),
                'taxa_sucesso': f"{(contador_inseridos/len(dados_filtrados)*100):.1f}%" if dados_filtrados else "0%"
            }
            
            self.logger.info(f"✅ SINCRONIZAÇÃO CONCLUÍDA: {estatisticas}")
            
            return {
                'sucesso': True,
                'estatisticas': estatisticas,
                'mensagem': f'Carteira sincronizada com {contador_inseridos} registros'
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"❌ ERRO na sincronização: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'estatisticas': {}
            } 
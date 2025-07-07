"""
📦 PEDIDOS MAPPER - Mapeamentos para Modelo Pedido
=================================================

Mapper especializado para o modelo Pedido, contendo todos os campos
específicos e seus termos naturais correspondentes.

Campos mapeados:
- Identificação: num_pedido, codigo_pedido
- Localização: cep, cidade, uf, endereco
- Datas: data_pedido, data_prevista_entrega
- Valores: valor_total, peso_total, volumes
- Status: status_calculado, agendado, reagendar
- Relacionamentos: separacao_lote_id, cliente_id
"""

from typing import Dict, Any
from .base_mapper import BaseMapper

class PedidosMapper(BaseMapper):
    """
    Mapper específico para o modelo Pedido.
    
    Responsável por mapear termos naturais para campos
    da tabela 'pedidos' no banco de dados.
    """
    
    def __init__(self):
        super().__init__('Pedido')
    
    def _criar_mapeamentos(self) -> Dict[str, Dict[str, Any]]:
        """
        Cria mapeamentos específicos para o modelo Pedido.
        
        Returns:
            Dict com mapeamentos de campos do Pedido
        """
        return {
            # 🔢 IDENTIFICAÇÃO
            'num_pedido': {
                'campo_principal': 'num_pedido',
                'termos_naturais': [
                    'pedido', 'número do pedido', 'numero do pedido', 
                    'num pedido', 'nº pedido', 'pedido número',
                    'pedido numero', 'código do pedido', 'id do pedido',
                    'número de pedido', 'numero de pedido', 'pdd'
                ],
                'tipo': 'string',
                'observacao': 'Campo principal de identificação do pedido'
            },
            
            'codigo_pedido': {
                'campo_principal': 'codigo_pedido',
                'termos_naturais': [
                    'codigo do pedido', 'código do pedido', 
                    'codigo pedido', 'código pedido',
                    'id pedido', 'identificador do pedido'
                ],
                'tipo': 'string',
                'observacao': 'Código alternativo do pedido'
            },
            
            # 🏠 LOCALIZAÇÃO
            'cep': {
                'campo_principal': 'cep',
                'termos_naturais': [
                    'cep', 'código postal', 'codigo postal',
                    'cep destino', 'cep de entrega', 'cep do cliente'
                ],
                'tipo': 'string',
                'observacao': 'CEP de destino do pedido'
            },
            
            'cidade': {
                'campo_principal': 'cidade',
                'termos_naturais': [
                    'cidade', 'cidade destino', 'cidade de entrega',
                    'municipio', 'município', 'localidade'
                ],
                'tipo': 'string',
                'observacao': 'Cidade de destino do pedido'
            },
            
            'uf': {
                'campo_principal': 'uf',
                'termos_naturais': [
                    'uf', 'estado', 'uf destino', 'estado destino',
                    'uf de entrega', 'estado de entrega', 'sigla do estado'
                ],
                'tipo': 'string',
                'observacao': 'Estado de destino do pedido'
            },
            
            'endereco': {
                'campo_principal': 'endereco',
                'termos_naturais': [
                    'endereco', 'endereço', 'endereco de entrega',
                    'endereço de entrega', 'rua', 'logradouro'
                ],
                'tipo': 'string',
                'observacao': 'Endereço completo de entrega'
            },
            
            # 📅 DATAS
            'data_pedido': {
                'campo_principal': 'data_pedido',
                'termos_naturais': [
                    'data do pedido', 'data pedido', 'quando foi pedido',
                    'data de criação', 'data de criacao', 'criado em'
                ],
                'tipo': 'datetime',
                'observacao': 'Data de criação do pedido'
            },
            
            'data_prevista_entrega': {
                'campo_principal': 'data_prevista_entrega',
                'termos_naturais': [
                    'data prevista', 'data prevista de entrega',
                    'data prevista entrega', 'previsão de entrega',
                    'previsao de entrega', 'quando vai entregar',
                    'data de entrega', 'prazo de entrega'
                ],
                'tipo': 'datetime',
                'observacao': 'Data prevista para entrega do pedido'
            },
            
            # 💰 VALORES
            'valor_total': {
                'campo_principal': 'valor_total',
                'termos_naturais': [
                    'valor total', 'valor do pedido', 'valor total do pedido',
                    'preço total', 'preco total', 'montante',
                    'valor da nota', 'valor nf'
                ],
                'tipo': 'decimal',
                'observacao': 'Valor total em reais do pedido'
            },
            
            'peso_total': {
                'campo_principal': 'peso_total',
                'termos_naturais': [
                    'peso total', 'peso do pedido', 'peso total do pedido',
                    'peso bruto', 'peso líquido', 'peso liquido',
                    'quantos kg', 'quilos', 'quilogramas'
                ],
                'tipo': 'decimal',
                'observacao': 'Peso total em quilogramas do pedido'
            },
            
            'volumes': {
                'campo_principal': 'volumes',
                'termos_naturais': [
                    'volumes', 'quantidade de volumes', 'qtd volumes',
                    'número de volumes', 'numero de volumes',
                    'quantos volumes', 'qtd de itens', 'quantidade de itens'
                ],
                'tipo': 'integer',
                'observacao': 'Quantidade de volumes do pedido'
            },
            
            # 📊 STATUS
            'status_calculado': {
                'campo_principal': 'status_calculado',
                'termos_naturais': [
                    'status', 'status do pedido', 'situação',
                    'situacao', 'situação do pedido', 'estado do pedido',
                    'como está', 'como esta', 'status atual'
                ],
                'tipo': 'string',
                'observacao': 'Status calculado do pedido (ABERTO, COTADO, FATURADO, EMBARCADO)'
            },
            
            'agendado': {
                'campo_principal': 'agendado',
                'termos_naturais': [
                    'agendado', 'tem agendamento', 'foi agendado',
                    'agendamento', 'com agendamento', 'já agendado'
                ],
                'tipo': 'boolean',
                'observacao': 'Indica se o pedido possui agendamento'
            },
            
            'reagendar': {
                'campo_principal': 'reagendar',
                'termos_naturais': [
                    'reagendar', 'precisa reagendar', 'para reagendar',
                    'reagendamento', 'reagendar entrega', 'novo agendamento'
                ],
                'tipo': 'boolean',
                'observacao': 'Indica se o pedido precisa ser reagendado'
            },
            
            # 🔗 RELACIONAMENTOS
            'separacao_lote_id': {
                'campo_principal': 'separacao_lote_id',
                'termos_naturais': [
                    'lote de separação', 'lote separacao', 'separação lote',
                    'separacao lote', 'lote', 'id do lote',
                    'numero do lote', 'número do lote'
                ],
                'tipo': 'string',
                'observacao': 'ID do lote de separação (relacionamento crítico)'
            },
            
            'cliente_id': {
                'campo_principal': 'cliente_id',
                'termos_naturais': [
                    'cliente', 'id do cliente', 'código do cliente',
                    'codigo do cliente', 'identificador do cliente'
                ],
                'tipo': 'integer',
                'observacao': 'ID do cliente (relacionamento com tabela clientes)'
            },
            
            # 🏢 INFORMAÇÕES DO CLIENTE
            'nome_cliente': {
                'campo_principal': 'nome_cliente',
                'termos_naturais': [
                    'nome do cliente', 'nome cliente', 'cliente nome',
                    'razão social', 'razao social', 'empresa'
                ],
                'tipo': 'string',
                'observacao': 'Nome/Razão social do cliente'
            },
            
            'cnpj_cliente': {
                'campo_principal': 'cnpj_cliente',
                'termos_naturais': [
                    'cnpj', 'cnpj do cliente', 'cnpj cliente',
                    'documento', 'documento do cliente'
                ],
                'tipo': 'string',
                'observacao': 'CNPJ do cliente'
            },
            
            # 🎯 CAMPOS ESPECÍFICOS
            'observacoes': {
                'campo_principal': 'observacoes',
                'termos_naturais': [
                    'observações', 'observacoes', 'obs', 'comentários',
                    'comentarios', 'notas', 'anotações', 'anotacoes'
                ],
                'tipo': 'string',
                'observacao': 'Observações e comentários do pedido'
            },
            
            'vendedor_codigo': {
                'campo_principal': 'vendedor_codigo',
                'termos_naturais': [
                    'vendedor', 'código do vendedor', 'codigo do vendedor',
                    'id do vendedor', 'vendedor responsável',
                    'vendedor responsavel'
                ],
                'tipo': 'string',
                'observacao': 'Código do vendedor responsável'
            },
            
            'prazo_entrega': {
                'campo_principal': 'prazo_entrega',
                'termos_naturais': [
                    'prazo de entrega', 'prazo entrega', 'lead time',
                    'tempo de entrega', 'dias para entrega',
                    'quantos dias', 'prazo'
                ],
                'tipo': 'integer',
                'observacao': 'Prazo em dias para entrega'
            },
            
            'urgente': {
                'campo_principal': 'urgente',
                'termos_naturais': [
                    'urgente', 'prioridade', 'prioritário',
                    'prioritario', 'alta prioridade', 'express'
                ],
                'tipo': 'boolean',
                'observacao': 'Indica se o pedido é urgente'
            }
        } 
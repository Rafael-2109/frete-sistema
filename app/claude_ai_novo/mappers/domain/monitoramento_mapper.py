"""
📊 MONITORAMENTO MAPPER - Mapeamentos para Modelo EntregaMonitorada
==================================================================

Mapper especializado para o modelo EntregaMonitorada, usado para
rastrear e monitorar entregas em tempo real.

Campos mapeados:
- Identificação: numero_nf, numero_embarque
- Status: entregue, status_finalizacao, data_entrega_realizada
- Rastreamento: tracking_code, tentativas_entrega
- Logística: transportadora, motorista
"""

from typing import Dict, Any
from .base_mapper import BaseMapper

class MonitoramentoMapper(BaseMapper):
    """
    Mapper específico para o modelo EntregaMonitorada.
    
    Responsável por mapear termos naturais para campos
    da tabela 'entregas_monitoradas' no banco de dados.
    """
    
    def __init__(self):
        super().__init__('EntregaMonitorada')
    
    def _criar_mapeamentos(self) -> Dict[str, Dict[str, Any]]:
        """
        Cria mapeamentos específicos para o modelo EntregaMonitorada.
        
        Returns:
            Dict com mapeamentos de campos de EntregaMonitorada
        """
        return {
            # 🔢 IDENTIFICAÇÃO
            'numero_nf': {
                'campo_principal': 'numero_nf',
                'termos_naturais': [
                    'nf', 'nota fiscal', 'numero da nf', 'número da nf',
                    'numero da nota', 'número da nota', 'nota',
                    'nf número', 'nf numero', 'numero nf'
                ],
                'tipo': 'string',
                'observacao': 'Número da nota fiscal sendo monitorada'
            },
            
            'numero_embarque': {
                'campo_principal': 'numero_embarque',
                'termos_naturais': [
                    'embarque', 'número do embarque', 'numero do embarque',
                    'num embarque', 'nº embarque', 'embarque número',
                    'embarque numero', 'id do embarque'
                ],
                'tipo': 'integer',
                'observacao': 'Número do embarque vinculado'
            },
            
            # 📊 STATUS DE ENTREGA
            'entregue': {
                'campo_principal': 'entregue',
                'termos_naturais': [
                    'entregue', 'foi entregue', 'já entregue',
                    'entrega realizada', 'entrega feita', 'entregou',
                    'status entregue', 'está entregue', 'esta entregue'
                ],
                'tipo': 'boolean',
                'observacao': 'Indica se a entrega foi realizada'
            },
            
            'status_finalizacao': {
                'campo_principal': 'status_finalizacao',
                'termos_naturais': [
                    'status', 'status da entrega', 'situação da entrega',
                    'situacao da entrega', 'como está a entrega',
                    'como esta a entrega', 'status final', 'finalização',
                    'finalizacao', 'status de finalização'
                ],
                'tipo': 'string',
                'observacao': 'Status final da entrega (ENTREGUE, PENDENTE, etc.)'
            },
            
            'data_entrega_realizada': {
                'campo_principal': 'data_entrega_realizada',
                'termos_naturais': [
                    'data da entrega', 'data entrega', 'quando entregou',
                    'data de entrega', 'entregue em', 'data realizada',
                    'data da entrega realizada', 'quando foi entregue'
                ],
                'tipo': 'datetime',
                'observacao': 'Data em que a entrega foi realizada'
            },
            
            # 🚛 RASTREAMENTO
            'tracking_code': {
                'campo_principal': 'tracking_code',
                'termos_naturais': [
                    'tracking', 'código de rastreamento', 'codigo de rastreamento',
                    'rastreamento', 'código tracking', 'codigo tracking',
                    'track', 'rastreio', 'código rastreio', 'codigo rastreio'
                ],
                'tipo': 'string',
                'observacao': 'Código de rastreamento da entrega'
            },
            
            'tentativas_entrega': {
                'campo_principal': 'tentativas_entrega',
                'termos_naturais': [
                    'tentativas', 'tentativas de entrega', 'quantas tentativas',
                    'número de tentativas', 'numero de tentativas',
                    'tentou quantas vezes', 'tentou entregar'
                ],
                'tipo': 'integer',
                'observacao': 'Número de tentativas de entrega realizadas'
            },
            
            # 🏢 LOGÍSTICA
            'transportadora': {
                'campo_principal': 'transportadora',
                'termos_naturais': [
                    'transportadora', 'nome da transportadora',
                    'empresa transportadora', 'quem entregou',
                    'responsável pela entrega', 'responsavel pela entrega'
                ],
                'tipo': 'string',
                'observacao': 'Nome da transportadora responsável'
            },
            
            'motorista': {
                'campo_principal': 'motorista',
                'termos_naturais': [
                    'motorista', 'nome do motorista', 'quem dirigiu',
                    'condutor', 'entregador', 'quem entregou'
                ],
                'tipo': 'string',
                'observacao': 'Nome do motorista responsável'
            },
            
            # 📅 DATAS
            'data_embarque': {
                'campo_principal': 'data_embarque',
                'termos_naturais': [
                    'data do embarque', 'data embarque', 'quando embarcou',
                    'data de saída', 'data de saida', 'saiu em'
                ],
                'tipo': 'datetime',
                'observacao': 'Data de embarque da entrega'
            },
            
            'data_prevista_entrega': {
                'campo_principal': 'data_prevista_entrega',
                'termos_naturais': [
                    'data prevista', 'data prevista de entrega',
                    'data prevista entrega', 'previsão de entrega',
                    'previsao de entrega', 'quando vai chegar',
                    'prazo de entrega', 'prazo'
                ],
                'tipo': 'datetime',
                'observacao': 'Data prevista para entrega'
            },
            
            # 🏠 LOCALIZAÇÃO
            'cidade': {
                'campo_principal': 'cidade',
                'termos_naturais': [
                    'cidade', 'cidade destino', 'cidade de entrega',
                    'municipio', 'município', 'localidade'
                ],
                'tipo': 'string',
                'observacao': 'Cidade de destino da entrega'
            },
            
            'uf': {
                'campo_principal': 'uf',
                'termos_naturais': [
                    'uf', 'estado', 'uf destino', 'estado destino',
                    'uf de entrega', 'estado de entrega'
                ],
                'tipo': 'string',
                'observacao': 'Estado de destino da entrega'
            },
            
            'cliente': {
                'campo_principal': 'cliente',
                'termos_naturais': [
                    'cliente', 'nome do cliente', 'cliente nome',
                    'razão social', 'razao social', 'empresa'
                ],
                'tipo': 'string',
                'observacao': 'Nome do cliente destinatário'
            },
            
            # 💰 VALORES
            'valor_nf': {
                'campo_principal': 'valor_nf',
                'termos_naturais': [
                    'valor da nf', 'valor da nota', 'valor nota fiscal',
                    'valor da nota fiscal', 'valor total', 'preço',
                    'preco', 'montante da nota'
                ],
                'tipo': 'decimal',
                'observacao': 'Valor da nota fiscal em reais'
            },
            
            'peso': {
                'campo_principal': 'peso',
                'termos_naturais': [
                    'peso', 'peso da entrega', 'peso da nota',
                    'peso bruto', 'peso líquido', 'peso liquido',
                    'quantos kg', 'quilos', 'quilogramas'
                ],
                'tipo': 'decimal',
                'observacao': 'Peso da entrega em quilogramas'
            },
            
            # 🎯 CAMPOS ESPECÍFICOS
            'observacoes': {
                'campo_principal': 'observacoes',
                'termos_naturais': [
                    'observações', 'observacoes', 'obs', 'comentários',
                    'comentarios', 'notas', 'anotações', 'anotacoes'
                ],
                'tipo': 'string',
                'observacao': 'Observações sobre a entrega'
            },
            
            'urgente': {
                'campo_principal': 'urgente',
                'termos_naturais': [
                    'urgente', 'prioridade', 'prioritário',
                    'prioritario', 'alta prioridade', 'express'
                ],
                'tipo': 'boolean',
                'observacao': 'Indica se a entrega é urgente'
            },
            
            'lead_time': {
                'campo_principal': 'lead_time',
                'termos_naturais': [
                    'lead time', 'prazo de entrega', 'tempo de entrega',
                    'dias para entrega', 'quantos dias', 'prazo'
                ],
                'tipo': 'integer',
                'observacao': 'Prazo em dias para entrega'
            }
        } 
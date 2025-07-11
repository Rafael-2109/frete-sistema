"""
🚛 EMBARQUES MAPPER - Mapeamentos para Modelo Embarque
=====================================================

Mapper especializado para os modelos Embarque e EmbarqueItem, 
contendo todos os campos específicos de embarques e itens.

Campos mapeados:
- Identificação: numero, codigo_embarque
- Logística: tipo_carga, modalidade, transportadora
- Datas: data_embarque, data_prevista_entrega
- Valores: valor_total, peso_total, volumes
- Status: status, cancelado, motivo_cancelamento
- Localização: origem, destino, rota
"""

from typing import Dict, Any
from .base_mapper import BaseMapper

class EmbarquesMapper(BaseMapper):
    """
    Mapper específico para os modelos Embarque e EmbarqueItem.
    
    Responsável por mapear termos naturais para campos
    das tabelas 'embarques' e 'embarque_itens' no banco de dados.
    """
    
    def __init__(self):
        super().__init__('Embarque')
    
    def _criar_mapeamentos(self) -> Dict[str, Dict[str, Any]]:
        """
        Cria mapeamentos específicos para os modelos Embarque e EmbarqueItem.
        
        Returns:
            Dict com mapeamentos de campos dos Embarques
        """
        return {
            # 🔢 IDENTIFICAÇÃO
            'numero': {
                'campo_principal': 'numero',
                'termos_naturais': [
                    'embarque', 'número do embarque', 'numero do embarque',
                    'num embarque', 'nº embarque', 'embarque número',
                    'embarque numero', 'código do embarque', 'id do embarque',
                    'número de embarque', 'numero de embarque'
                ],
                'tipo': 'integer',
                'observacao': 'Número sequencial único do embarque'
            },
            
            'codigo_embarque': {
                'campo_principal': 'codigo_embarque',
                'termos_naturais': [
                    'código do embarque', 'codigo do embarque',
                    'código embarque', 'codigo embarque',
                    'identificador do embarque'
                ],
                'tipo': 'string',
                'observacao': 'Código alternativo do embarque'
            },
            
            # 🚚 LOGÍSTICA
            'tipo_carga': {
                'campo_principal': 'tipo_carga',
                'termos_naturais': [
                    'tipo de carga', 'tipo carga', 'modalidade de carga',
                    'carga direta', 'carga fracionada', 'tipo do frete',
                    'modalidade do frete', 'tipo de frete'
                ],
                'tipo': 'string',
                'observacao': 'Tipo de carga (DIRETA, FRACIONADA, etc.)'
            },
            
            'modalidade': {
                'campo_principal': 'modalidade',
                'termos_naturais': [
                    'modalidade', 'tipo de transporte', 'meio de transporte',
                    'como vai', 'forma de transporte', 'modal'
                ],
                'tipo': 'string',
                'observacao': 'Modalidade de transporte'
            },
            
            'transportadora': {
                'campo_principal': 'transportadora',
                'termos_naturais': [
                    'transportadora', 'nome da transportadora',
                    'empresa transportadora', 'quem vai entregar',
                    'responsável pela entrega', 'responsavel pela entrega'
                ],
                'tipo': 'string',
                'observacao': 'Nome da transportadora responsável'
            },
            
            'transportadora_id': {
                'campo_principal': 'transportadora_id',
                'termos_naturais': [
                    'id da transportadora', 'código da transportadora',
                    'codigo da transportadora', 'id transportadora'
                ],
                'tipo': 'integer',
                'observacao': 'ID da transportadora (relacionamento)'
            },
            
            # 📅 DATAS
            'data_embarque': {
                'campo_principal': 'data_embarque',
                'termos_naturais': [
                    'data do embarque', 'data embarque', 'quando embarcou',
                    'data de saída', 'data de saida', 'saiu em',
                    'data de expedição', 'data de expedicao'
                ],
                'tipo': 'datetime',
                'observacao': 'Data de saída do embarque'
            },
            
            'data_prevista_entrega': {
                'campo_principal': 'data_prevista_entrega',
                'termos_naturais': [
                    'data prevista', 'data prevista de entrega',
                    'data prevista entrega', 'previsão de entrega',
                    'previsao de entrega', 'quando vai chegar',
                    'data de chegada', 'prazo de entrega'
                ],
                'tipo': 'datetime',
                'observacao': 'Data prevista para entrega do embarque'
            },
            
            # 💰 VALORES
            'valor_total': {
                'campo_principal': 'valor_total',
                'termos_naturais': [
                    'valor total', 'valor do embarque', 'valor total do embarque',
                    'preço total', 'preco total', 'montante',
                    'valor da carga', 'valor das notas'
                ],
                'tipo': 'decimal',
                'observacao': 'Valor total em reais do embarque'
            },
            
            'peso_total': {
                'campo_principal': 'peso_total',
                'termos_naturais': [
                    'peso total', 'peso do embarque', 'peso total do embarque',
                    'peso bruto', 'peso líquido', 'peso liquido',
                    'quantos kg', 'quilos', 'quilogramas'
                ],
                'tipo': 'decimal',
                'observacao': 'Peso total em quilogramas do embarque'
            },
            
            'volumes': {
                'campo_principal': 'volumes',
                'termos_naturais': [
                    'volumes', 'quantidade de volumes', 'qtd volumes',
                    'número de volumes', 'numero de volumes',
                    'quantos volumes', 'qtd de itens', 'quantidade de itens'
                ],
                'tipo': 'integer',
                'observacao': 'Quantidade total de volumes do embarque'
            },
            
            # 📊 STATUS
            'status': {
                'campo_principal': 'status',
                'termos_naturais': [
                    'status', 'status do embarque', 'situação',
                    'situacao', 'situação do embarque', 'estado do embarque',
                    'como está', 'como esta', 'status atual'
                ],
                'tipo': 'string',
                'observacao': 'Status do embarque (ATIVO, CANCELADO, etc.)'
            },
            
            'cancelado': {
                'campo_principal': 'cancelado',
                'termos_naturais': [
                    'cancelado', 'foi cancelado', 'cancelamento',
                    'está cancelado', 'esta cancelado'
                ],
                'tipo': 'boolean',
                'observacao': 'Indica se o embarque foi cancelado'
            },
            
            'motivo_cancelamento': {
                'campo_principal': 'motivo_cancelamento',
                'termos_naturais': [
                    'motivo do cancelamento', 'motivo cancelamento',
                    'por que cancelou', 'razão do cancelamento',
                    'razao do cancelamento', 'porque cancelou'
                ],
                'tipo': 'string',
                'observacao': 'Motivo do cancelamento do embarque'
            },
            
            # 🗺️ LOCALIZAÇÃO
            'origem': {
                'campo_principal': 'origem',
                'termos_naturais': [
                    'origem', 'de onde', 'origem do embarque',
                    'local de origem', 'ponto de origem',
                    'saiu de onde', 'partiu de'
                ],
                'tipo': 'string',
                'observacao': 'Local de origem do embarque'
            },
            
            'destino': {
                'campo_principal': 'destino',
                'termos_naturais': [
                    'destino', 'para onde', 'destino do embarque',
                    'local de destino', 'ponto de destino',
                    'vai para onde', 'vai para'
                ],
                'tipo': 'string',
                'observacao': 'Local de destino do embarque'
            },
            
            'rota': {
                'campo_principal': 'rota',
                'termos_naturais': [
                    'rota', 'rota do embarque', 'caminho',
                    'trajeto', 'percurso', 'itinerário',
                    'itinerario'
                ],
                'tipo': 'string',
                'observacao': 'Rota/trajeto do embarque'
            },
            
            # 🚛 VEÍCULO
            'placa_veiculo': {
                'campo_principal': 'placa_veiculo',
                'termos_naturais': [
                    'placa', 'placa do veículo', 'placa do veiculo',
                    'placa do caminhão', 'placa do caminhao',
                    'número da placa', 'numero da placa'
                ],
                'tipo': 'string',
                'observacao': 'Placa do veículo usado no embarque'
            },
            
            'tipo_veiculo': {
                'campo_principal': 'tipo_veiculo',
                'termos_naturais': [
                    'tipo de veículo', 'tipo de veiculo',
                    'tipo de caminhão', 'tipo de caminhao',
                    'modelo do veículo', 'modelo do veiculo'
                ],
                'tipo': 'string',
                'observacao': 'Tipo/modelo do veículo'
            },
            
            # 🎯 CAMPOS ESPECÍFICOS
            'observacoes': {
                'campo_principal': 'observacoes',
                'termos_naturais': [
                    'observações', 'observacoes', 'obs', 'comentários',
                    'comentarios', 'notas', 'anotações', 'anotacoes'
                ],
                'tipo': 'string',
                'observacao': 'Observações e comentários do embarque'
            },
            
            'urgente': {
                'campo_principal': 'urgente',
                'termos_naturais': [
                    'urgente', 'prioridade', 'prioritário',
                    'prioritario', 'alta prioridade', 'express'
                ],
                'tipo': 'boolean',
                'observacao': 'Indica se o embarque é urgente'
            },
            
            'criado_por': {
                'campo_principal': 'criado_por',
                'termos_naturais': [
                    'criado por', 'quem criou', 'responsável',
                    'responsavel', 'criador', 'usuário criador',
                    'usuario criador'
                ],
                'tipo': 'string',
                'observacao': 'Usuário que criou o embarque'
            }
        } 
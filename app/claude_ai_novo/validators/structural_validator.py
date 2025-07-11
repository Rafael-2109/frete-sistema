#!/usr/bin/env python3
"""
🏗️ SISTEMA DE IA ESTRUTURAL
IA que entende estrutura e fluxos de negócio do sistema de fretes
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class StructuralAI:
    """IA que entende estrutura e fluxos de negócio"""
    
    def __init__(self):
        self.business_flows = self._load_business_flows()
        self.data_relationships = self._load_data_relationships()
        
    def _load_business_flows(self) -> Dict[str, Any]:
        """Carrega fluxos de negócio conhecidos"""
        
        return {
            'pedido_completo': [
                'pedido_criado',
                'cotacao_solicitada', 
                'frete_cotado',
                'pedido_separado',
                'embarque_criado',
                'transportadora_definida',
                'mercadoria_embarcada',
                'entrega_agendada',
                'entrega_realizada',
                'faturamento_gerado'
            ],
            'entrega_padrao': [
                'embarque_saiu',
                'agendamento_realizado',
                'entrega_tentativa',
                'entrega_confirmada',
                'canhoto_coletado'
            ],
            'processo_financeiro': [
                'frete_aprovado',
                'cte_emitido',
                'pagamento_processado',
                'despesas_lancadas'
            ]
        }
    
    def _load_data_relationships(self) -> Dict[str, Any]:
        """Carrega relacionamentos estruturais entre dados"""
        
        return {
            'pedido_entrega': 'Pedido.nf = EntregaMonitorada.numero_nf',
            'embarque_item': 'Embarque.id = EmbarqueItem.embarque_id',
            'entrega_agendamento': 'EntregaMonitorada.id = AgendamentoEntrega.entrega_id',
            'frete_embarque': 'Frete.embarque_id = Embarque.id'
        }
    
    def validate_business_logic(self, data_context: Dict[str, Any]) -> Dict[str, Any]:
        """Valida lógica de negócio nos dados"""
        
        validations = {
            'structural_consistency': True,
            'business_flow_violations': [],
            'data_anomalies': [],
            'recommendations': []
        }
        
        # Validar consistência temporal
        temporal_issues = self._validate_temporal_consistency(data_context)
        if temporal_issues:
            validations['business_flow_violations'].extend(temporal_issues)
            validations['structural_consistency'] = False
        
        # Validar relacionamentos de dados
        relationship_issues = self._validate_data_relationships(data_context)
        if relationship_issues:
            validations['data_anomalies'].extend(relationship_issues)
        
        # Gerar recomendações
        if not validations['structural_consistency']:
            validations['recommendations'].append("Revisar fluxo de dados e corrigir inconsistências temporais")
        
        return validations
    
    def _validate_temporal_consistency(self, data_context: Dict[str, Any]) -> List[str]:
        """Valida consistência temporal nos dados"""
        
        issues = []
        
        # Exemplo: Data de embarque deve ser <= Data de entrega prevista
        if 'data_embarque' in data_context and 'data_entrega_prevista' in data_context:
            try:
                if data_context['data_embarque'] > data_context['data_entrega_prevista']:
                    issues.append("Data de embarque posterior à data de entrega prevista")
            except (TypeError, ValueError):
                pass  # Ignorar erros de conversão de data
        
        return issues
    
    def _validate_data_relationships(self, data_context: Dict[str, Any]) -> List[str]:
        """Valida relacionamentos entre dados"""
        
        issues = []
        
        # Validações específicas baseadas no conhecimento de negócio
        # Exemplo: Se há NF, deve haver cliente
        if 'numero_nf' in data_context and not data_context.get('cliente'):
            issues.append("NF sem cliente associado")
        
        return issues

# Função de conveniência para criar instância
def get_structural_ai() -> StructuralAI:
    """Retorna instância da IA estrutural"""
    return StructuralAI() 
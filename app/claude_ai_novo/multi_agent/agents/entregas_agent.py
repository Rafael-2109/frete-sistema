"""
🚚 ENTREGAS AGENT - Agente Especialista em Entregas

Agente especializado em monitoramento e gestão de entregas:
- Entregas monitoradas e status de finalização
- Agendamentos e reagendamentos  
- Prazos, atrasos e pontualidade
- Transportadoras e performance
- Problemas de entrega e soluções
"""

from typing import Dict, List, Any
from ..agent_types import AgentType
from .base_agent import BaseSpecialistAgent


class EntregasAgent(BaseSpecialistAgent):
    """Agente especialista em entregas e monitoramento"""
    
    def __init__(self, claude_client=None):
        super().__init__(AgentType.ENTREGAS, claude_client)
    
    def _load_specialist_prompt(self) -> str:
        """System prompt especializado em entregas"""
        return """
🚚 AGENTE ESPECIALISTA EM ENTREGAS

Você é um especialista em monitoramento e gestão de entregas. Sua expertise inclui:

**DOMÍNIO DE CONHECIMENTO:**
- Entregas monitoradas e status de finalização
- Agendamentos e reagendamentos
- Prazos, atrasos e pontualidade
- Transportadoras e motoristas
- Problemas de entrega e soluções
- Pendências financeiras relacionadas a entregas
- Canhotos de entrega e comprovação
- Performance de entrega por região

**DADOS QUE VOCÊ ANALISA:**
- EntregaMonitorada: status_finalizacao, data_entrega_prevista, data_hora_entrega_realizada
- AgendamentoEntrega: protocolo_agendamento, status, data_agendada
- Transportadoras e performance de entrega
- Histórico de reagendamentos e motivos
- Pendências financeiras de entregas

**SUA ESPECIALIDADE:**
- Calcular pontualidade e KPIs de entrega
- Identificar padrões de atraso por transportadora
- Analisar performance por região/cliente
- Detectar problemas operacionais recorrentes
- Sugerir otimizações de processo de entrega
- Monitorar prazos e alertar sobre atrasos
- Analisar motivos de reagendamento
- Calcular tempo médio de entrega por rota

**SEMPRE RESPONDA:**
1. Com foco específico em ENTREGAS e MONITORAMENTO
2. Baseado em dados reais do sistema
3. Com métricas de performance (pontualidade, tempo médio)
4. Com sugestões práticas para melhorias operacionais
5. Identifique padrões de atraso e suas causas
6. Sugira ações corretivas específicas
"""
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Conhecimento específico do domínio de entregas"""
        return {
            'main_models': [
                'EntregaMonitorada', 
                'AgendamentoEntrega',
                'Transportadora',
                'PendenciaFinanceiraNF'
            ],
            'key_fields': [
                'status_finalizacao', 
                'data_entrega_prevista', 
                'data_hora_entrega_realizada',
                'protocolo_agendamento',
                'data_agendada',
                'motivo_reagendamento',
                'canhoto_arquivo'
            ],
            'kpis': [
                'pontualidade_entrega',
                'taxa_entrega_primeiro_agendamento', 
                'tempo_medio_entrega',
                'taxa_reagendamento',
                'performance_por_transportadora',
                'entregas_no_prazo',
                'atrasos_por_regiao'
            ],
            'common_queries': [
                'entregas atrasadas',
                'performance transportadora', 
                'agendamentos hoje',
                'entregas pendentes',
                'pontualidade mensal',
                'problemas de entrega',
                'reagendamentos frequentes'
            ],
            'business_rules': [
                'Entrega só pode ser finalizada após embarque',
                'Agendamento deve ter protocolo único',
                'Reagendamento requer motivo obrigatório',
                'Canhoto é obrigatório para entregas finalizadas'
            ]
        }
    
    def _get_domain_keywords(self) -> List[str]:
        """Palavras-chave específicas do domínio de entregas"""
        return [
            'entrega', 'entregue', 'entregar',
            'transportadora', 'motorista', 'veículo',
            'agendamento', 'reagendamento', 'protocolo',
            'atraso', 'atrasada', 'prazo', 'pontualidade',
            'canhoto', 'comprovante', 'destinatário',
            'monitoramento', 'finalização', 'status',
            'pendente', 'realizada', 'cancelada'
        ]


# Exportações principais
__all__ = [
    'EntregasAgent'
] 
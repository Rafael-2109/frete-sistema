"""
📋 PEDIDOS AGENT - Agente Especialista em Pedidos

Agente especializado em gestão de pedidos e fluxo comercial:
- Status de pedidos e faturamento
- Cotações e aprovações comerciais
- Agendamentos e protocolos
- Separação e expedição
- Clientes e vendedores
"""

from typing import Dict, List, Any
from ..agent_types import AgentType
from .base_agent import BaseSpecialistAgent


class PedidosAgent(BaseSpecialistAgent):
    """Agente especialista em pedidos e fluxo comercial"""
    
    def __init__(self, claude_client=None):
        super().__init__(AgentType.PEDIDOS, claude_client)
    
    def _load_specialist_prompt(self) -> str:
        """System prompt especializado em pedidos"""
        return """
📋 AGENTE ESPECIALISTA EM PEDIDOS

Você é um especialista em gestão de pedidos e fluxo comercial. Sua expertise inclui:

**DOMÍNIO DE CONHECIMENTO:**
- Status de pedidos e faturamento
- Cotações e aprovações comerciais
- Agendamentos e protocolos
- Separação e expedição
- Clientes e vendedores
- Carteira de pedidos e pipeline
- Processo comercial completo
- Performance por vendedor/cliente

**DADOS QUE VOCÊ ANALISA:**
- Pedido: status_calculado, valor_saldo_total, agendamento
- Separação e itens por produto
- Relacionamento com embarques e faturamento
- Performance por cliente/vendedor
- Histórico de cotações e aprovações
- Prazos de entrega e cumprimento

**SUA ESPECIALIDADE:**
- Analisar carteira de pedidos por status
- Identificar gargalos no processo comercial
- Monitorar performance comercial por vendedor
- Detectar pedidos pendentes de ação
- Otimizar fluxo de separação e expedição
- Calcular conversão de cotação → pedido → faturamento
- Analisar tempo médio do processo
- Identificar clientes com pedidos parados

**SEMPRE RESPONDA:**
1. Com foco específico em PEDIDOS e PROCESSO COMERCIAL
2. Com análise do pipeline comercial (funil de vendas)
3. Com métricas de conversão e performance
4. Com sugestões de melhoria operacional/comercial
5. Identifique gargalos no processo
6. Analise performance por vendedor/cliente
7. Sugira ações para acelerar fechamentos
8. Monitore prazos e compromissos comerciais
"""
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Conhecimento específico do domínio de pedidos"""
        return {
            'main_models': [
                'Pedido', 
                'Separacao',
                'Cotacao',
                'Cliente',
                'Vendedor'
            ],
            'key_fields': [
                'status_calculado',
                'valor_saldo_total',
                'peso_total',
                'agendamento',
                'protocolo',
                'nf',
                'cotacao_id',
                'vendedor_codigo',
                'raz_social_red',
                'expedicao'
            ],
            'kpis': [
                'taxa_conversao_cotacao',
                'tempo_medio_separacao',
                'valor_medio_pedido',
                'pedidos_por_vendedor',
                'ticket_medio_cliente',
                'taxa_faturamento',
                'tempo_ciclo_comercial',
                'carteira_em_aberto'
            ],
            'common_queries': [
                'pedidos pendentes',
                'carteira cliente', 
                'separação atrasada',
                'pedidos sem cotação',
                'faturamento pendente',
                'performance vendedor',
                'pipeline comercial',
                'pedidos parados'
            ],
            'business_rules': [
                'Pedido precisa de cotação antes do faturamento',
                'Separação obrigatória antes do embarque',
                'Agendamento necessário para entrega',
                'Protocolo único por pedido'
            ]
        }
    
    def _get_domain_keywords(self) -> List[str]:
        """Palavras-chave específicas do domínio de pedidos"""
        return [
            'pedido', 'pedidos', 'cotação', 'cotações',
            'cliente', 'clientes', 'vendedor', 'vendedores',
            'separação', 'expedição', 'faturamento',
            'status', 'aberto', 'cotado', 'faturado',
            'agendamento', 'protocolo', 'aprovação',
            'carteira', 'pipeline', 'comercial',
            'valor', 'peso', 'produto', 'item',
            'prazo', 'entrega', 'expedição'
        ]


# Exportações principais
__all__ = [
    'PedidosAgent'
] 
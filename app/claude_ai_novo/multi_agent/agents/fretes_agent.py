"""
🚛 FRETES AGENT - Agente Especialista em Fretes

Agente especializado em gestão de fretes e custos logísticos:
- Cotações de frete e tabelas de preço
- Aprovações e pagamentos de frete
- CTEs e documentação fiscal
- Despesas extras e multas
- Performance financeira de transportadoras
"""

from typing import Dict, List, Any
from ..agent_types import AgentType
from .base_agent import BaseSpecialistAgent


class FretesAgent(BaseSpecialistAgent):
    """Agente especialista em fretes e custos logísticos"""
    
    def __init__(self, claude_client=None):
        super().__init__(AgentType.FRETES, claude_client)
    
    def _load_specialist_prompt(self) -> str:
        """System prompt especializado em fretes"""
        return """
🚛 AGENTE ESPECIALISTA EM FRETES

Você é um especialista em gestão de fretes e custos logísticos. Sua expertise inclui:

**DOMÍNIO DE CONHECIMENTO:**
- Cotações de frete e tabelas de preço
- Aprovações e pagamentos de frete  
- CTEs e documentação fiscal
- Despesas extras e multas
- Performance financeira de transportadoras
- Análise de custos logísticos
- Modalidades de frete (CIF, FOB)
- Negociação e otimização de custos

**DADOS QUE VOCÊ ANALISA:**
- Frete: valor_frete, status_aprovacao, numero_cte
- DespesaExtra: tipo_despesa, valor_despesa, motivo
- Transportadora: performance de custo e confiabilidade
- Tabelas de frete e modalidades por rota
- Histórico de pagamentos e inadimplência
- Comparativos de preço entre transportadoras

**SUA ESPECIALIDADE:**
- Analisar custos e rentabilidade de fretes
- Identificar oportunidades de economia
- Monitorar performance financeira por transportadora
- Detectar anomalias em custos e despesas
- Otimizar seleção de transportadoras
- Calcular KPIs financeiros (R$/kg, margem)
- Analisar tendências de preço
- Sugerir renegociações contratuais

**SEMPRE RESPONDA:**
1. Com foco específico em FRETES e CUSTOS
2. Com análise financeira detalhada (valores, percentuais)
3. Com comparativos de performance entre transportadoras
4. Com sugestões de otimização de custo
5. Identifique despesas extras excessivas
6. Analise eficiência de aprovação de fretes
7. Sugira estratégias de redução de custos
"""
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Conhecimento específico do domínio de fretes"""
        return {
            'main_models': [
                'Frete', 
                'DespesaExtra',
                'Transportadora',
                'TabelaFrete'
            ],
            'key_fields': [
                'valor_frete',
                'valor_cotado', 
                'valor_considerado',
                'valor_pago',
                'status_aprovacao',
                'numero_cte',
                'peso_total',
                'tipo_despesa',
                'valor_despesa'
            ],
            'kpis': [
                'custo_por_kg',
                'margem_frete',
                'performance_financeira',
                'economia_negociada',
                'taxa_aprovacao',
                'prazo_medio_pagamento',
                'despesas_extras_percentual',
                'variacao_custo_mensal'
            ],
            'common_queries': [
                'custos frete',
                'aprovações pendentes', 
                'despesas extras',
                'performance transportadora',
                'economia possível',
                'fretes mais caros',
                'comparativo custos',
                'margem operacional'
            ],
            'business_rules': [
                'Frete deve ter cotação antes da aprovação',
                'CTe obrigatório para pagamento',
                'Despesas extras requerem justificativa',
                'Aprovação necessária para valores acima da tabela'
            ]
        }
    
    def _get_domain_keywords(self) -> List[str]:
        """Palavras-chave específicas do domínio de fretes"""
        return [
            'frete', 'fretes', 'custo', 'custos',
            'valor', 'preço', 'cotação', 'tabela',
            'aprovação', 'aprovar', 'aprovado',
            'cte', 'pagamento', 'pagar', 'pago',
            'despesa', 'multa', 'taxa', 'adicional',
            'transportadora', 'transportadoras',
            'economia', 'otimização', 'redução',
            'margem', 'rentabilidade', 'financeiro'
        ]


# Exportações principais
__all__ = [
    'FretesAgent'
] 
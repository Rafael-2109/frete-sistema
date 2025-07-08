"""
💰 FINANCEIRO AGENT - Agente Especialista em Financeiro

Agente especializado em gestão financeira e faturamento:
- Faturamento e notas fiscais
- Despesas extras e multas
- Pendências financeiras
- Fluxo de caixa logístico
- Performance financeira
"""

from typing import Dict, List, Any
from ..agent_types import AgentType
from .base_agent import BaseSpecialistAgent


class FinanceiroAgent(BaseSpecialistAgent):
    """Agente especialista em financeiro e faturamento"""
    
    def __init__(self, claude_client=None):
        super().__init__(AgentType.FINANCEIRO, claude_client)
    
    def _load_specialist_prompt(self) -> str:
        """System prompt especializado em financeiro"""
        return """
💰 AGENTE ESPECIALISTA EM FINANCEIRO

Você é um especialista em gestão financeira e faturamento. Sua expertise inclui:

**DOMÍNIO DE CONHECIMENTO:**
- Faturamento e notas fiscais
- Despesas extras e multas
- Pendências financeiras por cliente/NF
- Fluxo de caixa logístico
- Performance financeira operacional
- Análise de rentabilidade
- Controle de inadimplência
- Margem de contribuição

**DADOS QUE VOCÊ ANALISA:**
- RelatorioFaturamentoImportado: faturamento e valores
- DespesaExtra: custos adicionais e justificativas
- PendenciaFinanceiraNF: pendências por nota fiscal
- Performance financeira por cliente/período
- Fluxo de recebimentos e pagamentos
- Análise de margem e rentabilidade

**SUA ESPECIALIDADE:**
- Analisar rentabilidade operacional por cliente
- Monitorar fluxo de faturamento e recebimento
- Detectar pendências críticas e riscos
- Otimizar custos operacionais e despesas
- Prever impactos financeiros de decisões
- Calcular margens e indicadores financeiros
- Identificar oportunidades de melhoria financeira
- Analisar inadimplência e riscos de crédito

**SEMPRE RESPONDA:**
1. Com foco específico em FINANCEIRO e RENTABILIDADE
2. Com análise de rentabilidade detalhada (valores, %)
3. Com métricas financeiras (margem, ROI, inadimplência)
4. Com sugestões de otimização financeira
5. Identifique riscos financeiros e pendências críticas
6. Analise impacto financeiro de operações
7. Sugira estratégias de melhoria da margem
8. Monitore indicadores de saúde financeira
"""
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Conhecimento específico do domínio financeiro"""
        return {
            'main_models': [
                'RelatorioFaturamentoImportado', 
                'DespesaExtra',
                'PendenciaFinanceiraNF',
                'Frete',
                'Cliente'
            ],
            'key_fields': [
                'valor_total',
                'data_fatura',
                'numero_nf',
                'nome_cliente',
                'valor_despesa',
                'data_vencimento',
                'observacao',
                'valor_frete',
                'margem_contribuicao'
            ],
            'kpis': [
                'margem_contribuicao',
                'fluxo_caixa_operacional',
                'inadimplencia_percentual',
                'ticket_medio_faturamento',
                'despesas_extras_percentual',
                'rentabilidade_cliente',
                'prazo_medio_recebimento',
                'crescimento_faturamento'
            ],
            'common_queries': [
                'faturamento mensal',
                'despesas pendentes', 
                'margem operacional',
                'pendências financeiras',
                'rentabilidade cliente',
                'fluxo de caixa',
                'inadimplência',
                'performance financeira'
            ],
            'business_rules': [
                'Faturamento deve ter NF válida',
                'Despesas requerem justificativa',
                'Pendências devem ter responsável',
                'Margem mínima para viabilidade operacional'
            ]
        }
    
    def _get_domain_keywords(self) -> List[str]:
        """Palavras-chave específicas do domínio financeiro"""
        return [
            'faturamento', 'faturar', 'faturado',
            'nota fiscal', 'nf', 'valor', 'valores',
            'despesa', 'despesas', 'custo', 'custos',
            'multa', 'multas', 'taxa', 'taxas',
            'pagamento', 'pagamentos', 'recebimento',
            'vencimento', 'vencer', 'vencido',
            'pendência', 'pendências', 'pendente',
            'margem', 'rentabilidade', 'lucro',
            'financeiro', 'financeira', 'inadimplência'
        ]


# Exportações principais
__all__ = [
    'FinanceiroAgent'
] 
"""
💰 FINANCEIRO AGENT - Agente Especialista em Financeiro

Agente especializado em gestão financeira:
- Faturamento e notas fiscais
- Contas a pagar e receber
- Fluxo de caixa
- Análise de custos
- Pendências financeiras
- Relatórios contábeis
"""

from typing import Dict, List, Any, Optional
from ...utils.agent_types import AgentType
from app.claude_ai_novo.coordinators.domain_agents.smart_base_agent import SmartBaseAgent


class FinanceiroAgent(SmartBaseAgent):
    """Agente especialista em financeiro - COM TODAS AS CAPACIDADES"""
    
    def __init__(self, claude_client=None):
        super().__init__(AgentType.FINANCEIRO, claude_client)
        # SmartBaseAgent já inicializa TODAS as capacidades automaticamente!
    
    def _resumir_dados_reais(self, dados_reais: Dict[str, Any]) -> Dict[str, Any]:
        """Resume dados reais específicos para FINANCEIRO"""
        try:
            resumo = {
                'timestamp': dados_reais.get('timestamp', ''),
                'dominio': 'financeiro',
                'total_registros': 0,
                'dados_encontrados': False
            }
            
            # Processar dados específicos de faturamento
            if 'faturamento' in dados_reais:
                dados_faturamento = dados_reais['faturamento']
                if isinstance(dados_faturamento, dict):
                    resumo['total_faturamento'] = dados_faturamento.get('total_faturamento', 0)
                    resumo['nfs_pendentes'] = dados_faturamento.get('nfs_pendentes', 0)
                    resumo['valor_total'] = dados_faturamento.get('valor_total', 0)
                    resumo['dados_encontrados'] = True
                    
                    # Adicionar insights específicos financeiros
                    if resumo['nfs_pendentes'] > 0:
                        resumo['alerta_nfs'] = f"{resumo['nfs_pendentes']} NFs pendentes"
                    
                    if resumo['valor_total'] > 1000000:
                        resumo['alerta_valor'] = f"Alto volume: R$ {resumo['valor_total']:,.2f}"
            
            # Processar dados de pendências
            if 'pendencias' in dados_reais:
                dados_pendencias = dados_reais['pendencias']
                if isinstance(dados_pendencias, dict):
                    resumo['pendencias_abertas'] = dados_pendencias.get('pendencias_abertas', 0)
                    resumo['valor_pendencias'] = dados_pendencias.get('valor_pendencias', 0)
                    resumo['dados_encontrados'] = True
            
            return resumo
            
        except Exception as e:
            self.logger_estruturado.error(f"❌ Erro ao resumir dados financeiros: {e}")
            return {'erro': str(e)}
    
    def _load_specialist_prompt(self) -> str:
        """System prompt especializado em financeiro COM TODAS AS CAPACIDADES"""
        return """
💰 AGENTE ESPECIALISTA EM FINANCEIRO - INTELIGÊNCIA COMPLETA

Você é um especialista em gestão financeira equipado com TODAS as capacidades avançadas:

**CAPACIDADES ATIVAS:**
✅ Dados reais do banco PostgreSQL
✅ Claude 4 Sonnet (não simulado)
✅ Cache Redis para performance
✅ Contexto conversacional (memória)
✅ Mapeamento semântico inteligente
✅ ML Models para predições
✅ Logs estruturados para auditoria
✅ Análise de tendências temporais
✅ Sistema de validação e confiança
✅ Sugestões inteligentes contextuais
✅ Alertas operacionais automáticos

**DOMÍNIO DE ESPECIALIZAÇÃO:**
- Faturamento e notas fiscais
- Contas a pagar e receber
- Fluxo de caixa e liquidez
- Análise de custos e margens
- Pendências financeiras
- Relatórios contábeis e fiscais
- Conciliação bancária
- Análise de inadimplência

**DADOS QUE VOCÊ ANALISA:**
- RelatorioFaturamentoImportado: NFs, valores, datas
- PendenciaFinanceiraNF: pendências e resoluções
- Fretes: custos e margens
- DespesaExtra: custos adicionais
- Clientes: histórico financeiro

**SEMPRE RESPONDA COM:**
1. Valores financeiros exatos
2. Análise de fluxo de caixa
3. Alertas para pendências críticas
4. Sugestões de otimização financeira
5. KPIs financeiros calculados
6. Tendências de faturamento

**EXEMPLOS DE ALERTAS A GERAR:**
- "🚨 CRÍTICO: R$ 250.000 em pendências vencidas"
- "⚠️ ATENÇÃO: Queda de 15% no faturamento mensal"
- "📈 TENDÊNCIA: Crescimento de 8% na margem"
- "💡 OPORTUNIDADE: Negociar prazo com 3 clientes"
"""
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Conhecimento específico do domínio financeiro"""
        return {
            'main_models': [
                'RelatorioFaturamentoImportado',
                'PendenciaFinanceiraNF',
                'Frete',
                'DespesaExtra'
            ],
            'key_fields': [
                'numero_nf',
                'valor_total',
                'data_fatura',
                'cnpj_cliente',
                'pendencia_tipo',
                'valor_pendencia',
                'data_vencimento'
            ],
            'kpis': [
                'faturamento_mensal',
                'margem_bruta',
                'inadimplencia',
                'tempo_medio_recebimento',
                'pendencias_criticas'
            ],
            'common_queries': [
                'faturamento mês',
                'pendências cliente',
                'notas fiscais',
                'fluxo caixa',
                'margem lucro',
                'inadimplência',
                'contas receber'
            ]
        }
    
    def _get_domain_keywords(self) -> List[str]:
        """Palavras-chave específicas do domínio financeiro"""
        return [
            'faturamento', 'faturar', 'fatura',
            'nota fiscal', 'nf', 'nfs',
            'pendencia', 'pendências', 'pendente',
            'pagamento', 'recebimento', 'cobranca',
            'valor', 'valores', 'total', 'subtotal',
            'margem', 'lucro', 'custo', 'despesa',
            'vencimento', 'prazo', 'atraso',
            'cliente', 'fornecedor', 'conta'
        ]


# Exportações principais
__all__ = [
    'FinanceiroAgent'
]

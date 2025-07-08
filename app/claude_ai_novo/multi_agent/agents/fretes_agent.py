"""
🚛 FRETES AGENT - Agente Especialista em Fretes

Agente especializado em gestão de fretes:
- Cotações e aprovações de frete
- Transportadoras e performance
- Custos e margens
- CTe e documentação
- Análise de rotas
- Otimização de custos
"""

from typing import Dict, List, Any, Optional
from ..agent_types import AgentType
from .smart_base_agent import SmartBaseAgent


class FretesAgent(SmartBaseAgent):
    """Agente especialista em fretes - COM TODAS AS CAPACIDADES"""
    
    def __init__(self, claude_client=None):
        super().__init__(AgentType.FRETES, claude_client)
        # SmartBaseAgent já inicializa TODAS as capacidades automaticamente!
    
    def _resumir_dados_reais(self, dados_reais: Dict[str, Any]) -> Dict[str, Any]:
        """Resume dados reais específicos para FRETES"""
        try:
            resumo = {
                'timestamp': dados_reais.get('timestamp', ''),
                'dominio': 'fretes',
                'total_registros': 0,
                'dados_encontrados': False
            }
            
            # Processar dados específicos de fretes
            if 'fretes' in dados_reais:
                dados_fretes = dados_reais['fretes']
                if isinstance(dados_fretes, dict):
                    resumo['total_fretes'] = dados_fretes.get('total_fretes', 0)
                    resumo['fretes_pendentes'] = dados_fretes.get('fretes_pendentes', 0)
                    resumo['fretes_aprovados'] = dados_fretes.get('fretes_aprovados', 0)
                    resumo['valor_total_fretes'] = dados_fretes.get('valor_total_fretes', 0)
                    resumo['dados_encontrados'] = True
                    
                    # Adicionar insights específicos de fretes
                    if resumo['fretes_pendentes'] > 0:
                        resumo['alerta_pendentes'] = f"{resumo['fretes_pendentes']} fretes pendentes"
                    
                    if resumo['valor_total_fretes'] > 100000:
                        resumo['alerta_custos'] = f"Alto custo de frete: R$ {resumo['valor_total_fretes']:,.2f}"
            
            # Processar dados de transportadoras
            if 'transportadoras' in dados_reais:
                dados_transportadoras = dados_reais['transportadoras']
                if isinstance(dados_transportadoras, dict):
                    resumo['transportadoras_ativas'] = dados_transportadoras.get('transportadoras_ativas', 0)
                    resumo['melhor_preco'] = dados_transportadoras.get('melhor_preco', 0)
                    resumo['dados_encontrados'] = True
            
            return resumo
            
        except Exception as e:
            self.logger_estruturado.error(f"❌ Erro ao resumir dados de fretes: {e}")
            return {'erro': str(e)}
    
    def _load_specialist_prompt(self) -> str:
        """System prompt especializado em fretes COM TODAS AS CAPACIDADES"""
        return """
🚛 AGENTE ESPECIALISTA EM FRETES - INTELIGÊNCIA COMPLETA

Você é um especialista em gestão de fretes equipado com TODAS as capacidades avançadas:

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
- Cotações e aprovações de frete
- Transportadoras e performance
- Custos e margens de frete
- CTe e documentação fiscal
- Análise de rotas e distâncias
- Otimização de custos logísticos
- Gestão de pagamentos
- Auditoria de fretes

**DADOS QUE VOCÊ ANALISA:**
- Frete: valor_cotado, valor_considerado, status_frete
- Transportadora: nome, performance, histórico
- CTe: números, valores, status
- DespesaExtra: custos adicionais, tipos
- Rotas: origem, destino, distâncias

**SEMPRE RESPONDA COM:**
1. Custos de frete atuais
2. Performance das transportadoras
3. Análise de rotas e otimizações
4. Alertas para custos elevados
5. Sugestões de negociação
6. Tendências de preços

**EXEMPLOS DE ALERTAS A GERAR:**
- "🚨 CRÍTICO: Frete 35% acima da média histórica"
- "⚠️ ATENÇÃO: Transportadora X com atraso recorrente"
- "📈 TENDÊNCIA: Aumento de 12% nos custos mensais"
- "💡 OPORTUNIDADE: Rota alternativa 20% mais barata"
"""
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Conhecimento específico do domínio de fretes"""
        return {
            'main_models': [
                'Frete',
                'Transportadora',
                'CTe',
                'DespesaExtra'
            ],
            'key_fields': [
                'valor_cotado',
                'valor_considerado',
                'status_frete',
                'transportadora_nome',
                'numero_cte',
                'data_aprovacao',
                'origem_destino'
            ],
            'kpis': [
                'custo_medio_frete',
                'performance_transportadora',
                'economia_negociada',
                'prazo_aprovacao',
                'desvio_orcamento'
            ],
            'common_queries': [
                'fretes pendentes',
                'custo frete',
                'transportadora',
                'cotação frete',
                'CTe pendente',
                'despesas extras',
                'aprovação frete'
            ]
        }
    
    def _get_domain_keywords(self) -> List[str]:
        """Palavras-chave específicas do domínio de fretes"""
        return [
            'frete', 'fretes', 'freteiro',
            'transportadora', 'transporte', 'logistica',
            'cotacao', 'cotação', 'cotar',
            'cte', 'conhecimento', 'documento',
            'valor', 'custo', 'preco', 'preço',
            'rota', 'origem', 'destino',
            'aprovacao', 'aprovado', 'pendente',
            'despesa', 'extra', 'adicional'
        ]


# Exportações principais
__all__ = [
    'FretesAgent'
]

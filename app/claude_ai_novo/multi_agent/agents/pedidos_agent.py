"""
📦 PEDIDOS AGENT - Agente Especialista em Pedidos

Agente especializado em gestão de pedidos:
- Pedidos em aberto e processamento
- Cotações e aprovações
- Carteira de pedidos
- Separação e faturamento
- Acompanhamento de status
- Integração com clientes
"""

from typing import Dict, List, Any, Optional
from ..agent_types import AgentType
from .smart_base_agent import SmartBaseAgent


class PedidosAgent(SmartBaseAgent):
    """Agente especialista em pedidos - COM TODAS AS CAPACIDADES"""
    
    def __init__(self, claude_client=None):
        super().__init__(AgentType.PEDIDOS, claude_client)
        # SmartBaseAgent já inicializa TODAS as capacidades automaticamente!
    
    def _resumir_dados_reais(self, dados_reais: Dict[str, Any]) -> Dict[str, Any]:
        """Resume dados reais específicos para PEDIDOS"""
        try:
            resumo = {
                'timestamp': dados_reais.get('timestamp', ''),
                'dominio': 'pedidos',
                'total_registros': 0,
                'dados_encontrados': False
            }
            
            # Processar dados específicos de pedidos
            if 'pedidos' in dados_reais:
                dados_pedidos = dados_reais['pedidos']
                if isinstance(dados_pedidos, dict):
                    resumo['total_pedidos'] = dados_pedidos.get('total_pedidos', 0)
                    resumo['pedidos_pendentes'] = dados_pedidos.get('pedidos_pendentes', 0)
                    resumo['pedidos_aprovados'] = dados_pedidos.get('pedidos_aprovados', 0)
                    resumo['valor_carteira'] = dados_pedidos.get('valor_carteira', 0)
                    resumo['dados_encontrados'] = True
                    
                    # Adicionar insights específicos de pedidos
                    if resumo['pedidos_pendentes'] > 0:
                        resumo['alerta_pendentes'] = f"{resumo['pedidos_pendentes']} pedidos pendentes"
                    
                    if resumo['valor_carteira'] > 500000:
                        resumo['alerta_carteira'] = f"Carteira robusta: R$ {resumo['valor_carteira']:,.2f}"
            
            # Processar dados de cotações
            if 'cotacoes' in dados_reais:
                dados_cotacoes = dados_reais['cotacoes']
                if isinstance(dados_cotacoes, dict):
                    resumo['cotacoes_pendentes'] = dados_cotacoes.get('cotacoes_pendentes', 0)
                    resumo['cotacoes_aprovadas'] = dados_cotacoes.get('cotacoes_aprovadas', 0)
                    resumo['dados_encontrados'] = True
            
            return resumo
            
        except Exception as e:
            self.logger_estruturado.error(f"❌ Erro ao resumir dados de pedidos: {e}")
            return {'erro': str(e)}
    
    def _load_specialist_prompt(self) -> str:
        """System prompt especializado em pedidos COM TODAS AS CAPACIDADES"""
        return """
📦 AGENTE ESPECIALISTA EM PEDIDOS - INTELIGÊNCIA COMPLETA

Você é um especialista em gestão de pedidos equipado com TODAS as capacidades avançadas:

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
- Pedidos em aberto e processamento
- Cotações e aprovações
- Carteira de pedidos ativos
- Separação e faturamento
- Acompanhamento de status
- Integração com clientes
- Análise de demanda
- Gestão de prazos

**DADOS QUE VOCÊ ANALISA:**
- Pedido: num_pedido, status, valor_total, data_pedido
- CarteiraPedidos: saldo, faturamento, separação
- Cotacao: status_cotacao, valor_cotado, aprovação
- Cliente: histórico de pedidos, frequência
- Agendamento: datas previstas, contatos

**SEMPRE RESPONDA COM:**
1. Status atual dos pedidos
2. Carteira de pedidos por cliente
3. Prazos e agendamentos
4. Alertas para atrasos
5. Análise de demanda
6. Sugestões de priorização

**EXEMPLOS DE ALERTAS A GERAR:**
- "🚨 CRÍTICO: 12 pedidos vencidos sem cotação"
- "⚠️ ATENÇÃO: Carteira do Assai baixa (R$ 45.000)"
- "📈 TENDÊNCIA: Aumento de 20% nos pedidos urgentes"
- "💡 OPORTUNIDADE: Antecipar separação de 5 pedidos"
"""
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Conhecimento específico do domínio de pedidos"""
        return {
            'main_models': [
                'Pedido',
                'CarteiraPedidos',
                'Cotacao',
                'AgendamentoEntrega'
            ],
            'key_fields': [
                'num_pedido',
                'status_pedido',
                'valor_total',
                'data_pedido',
                'cliente_codigo',
                'status_cotacao',
                'data_prevista_entrega'
            ],
            'kpis': [
                'carteira_ativa',
                'tempo_medio_cotacao',
                'taxa_aprovacao',
                'pedidos_no_prazo',
                'demanda_por_cliente'
            ],
            'common_queries': [
                'pedidos pendentes',
                'carteira cliente',
                'cotações aprovadas',
                'pedidos atrasados',
                'agendamentos hoje',
                'demanda mensal',
                'status pedidos'
            ]
        }
    
    def _get_domain_keywords(self) -> List[str]:
        """Palavras-chave específicas do domínio de pedidos"""
        return [
            'pedido', 'pedidos', 'pedir',
            'cotacao', 'cotação', 'cotar',
            'carteira', 'saldo', 'faturamento',
            'separacao', 'separação', 'separar',
            'agendamento', 'agendado', 'agendar',
            'cliente', 'demanda', 'solicitacao',
            'prazo', 'urgente', 'prioritario',
            'aprovacao', 'aprovado', 'pendente'
        ]


# Exportações principais
__all__ = [
    'PedidosAgent'
]

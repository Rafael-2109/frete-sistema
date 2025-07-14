"""
🚢 EMBARQUES AGENT - Agente Especialista em Embarques

Agente especializado em gestão de embarques:
- Embarques ativos e programados
- Volumes e cargas
- Liberação de cargas
- Separação e picking
- Programação de saída
- Integração com transportadoras
"""

from typing import Dict, List, Any, Optional
from ...utils.agent_types import AgentType
from app.claude_ai_novo.coordinators.domain_agents.smart_base_agent import SmartBaseAgent


class EmbarquesAgent(SmartBaseAgent):
    """Agente especialista em embarques - COM TODAS AS CAPACIDADES"""
    
    def __init__(self, claude_client=None):
        super().__init__(AgentType.EMBARQUES, claude_client)
        # SmartBaseAgent já inicializa TODAS as capacidades automaticamente!
    
    def _resumir_dados_reais(self, dados_reais: Dict[str, Any]) -> Dict[str, Any]:
        """Resume dados reais específicos para EMBARQUES"""
        try:
            resumo = {
                'timestamp': dados_reais.get('timestamp', ''),
                'dominio': 'embarques',
                'total_registros': 0,
                'dados_encontrados': False
            }
            
            # Processar dados específicos de embarques
            if 'embarques' in dados_reais:
                dados_embarques = dados_reais['embarques']
                if isinstance(dados_embarques, dict):
                    resumo['total_embarques'] = dados_embarques.get('total_embarques', 0)
                    resumo['embarques_ativos'] = dados_embarques.get('embarques_ativos', 0)
                    resumo['embarques_pendentes'] = dados_embarques.get('embarques_pendentes', 0)
                    resumo['embarques_saindo_hoje'] = dados_embarques.get('embarques_hoje', 0)
                    resumo['dados_encontrados'] = True
                    
                    # Adicionar insights específicos de embarques
                    if resumo['embarques_pendentes'] > 0:
                        resumo['alerta_pendentes'] = f"{resumo['embarques_pendentes']} embarques pendentes"
                    
                    if resumo['embarques_saindo_hoje'] > 5:
                        resumo['alerta_movimento'] = f"Movimento intenso: {resumo['embarques_saindo_hoje']} embarques hoje"
            
            # Processar dados de volumes e cargas
            if 'volumes' in dados_reais:
                dados_volumes = dados_reais['volumes']
                if isinstance(dados_volumes, dict):
                    resumo['total_volumes'] = dados_volumes.get('total_volumes', 0)
                    resumo['peso_total'] = dados_volumes.get('peso_total', 0)
                    resumo['dados_encontrados'] = True
            
            return resumo
            
        except Exception as e:
            self.logger_estruturado.error(f"❌ Erro ao resumir dados de embarques: {e}")
            return {'erro': str(e)}
    
    def _load_specialist_prompt(self) -> str:
        """System prompt especializado em embarques COM TODAS AS CAPACIDADES"""
        return """
🚢 AGENTE ESPECIALISTA EM EMBARQUES - INTELIGÊNCIA COMPLETA

Você é um especialista em gestão de embarques equipado com TODAS as capacidades avançadas:

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
- Embarques ativos e programados
- Volumes e cargas por embarque
- Liberação de cargas e documentos
- Separação e picking
- Programação de saída
- Integração com transportadoras
- Controle de expedição
- Otimização de cargas

**DADOS QUE VOCÊ ANALISA:**
- Embarque: status, data_embarque, numero_embarque
- EmbarqueItem: pedidos,produtos, peso, dimensões, quantidade, valor_unitario, valor_total
- Separacao: items_separados, quantidade, protocolo, data_agenda
- Transportadora: assignação e performance
- Tabela de fretes: tipo_carga, modalidade, frete_peso, frete_valor
- Programação de saída e cronograma

**SEMPRE RESPONDA COM:**
1. Status atual dos embarques
2. Volumes e cargas pendentes
3. Cronograma de saídas
4. Alertas para embarques atrasados
5. Eficiência de separação
6. Sugestões de otimização

**EXEMPLOS DE ALERTAS A GERAR:**
- "🚨 CRÍTICO: 8 embarques programados sem separação"
- "⚠️ ATENÇÃO: Embarque 1234 atrasado há 2 dias"
- "📈 TENDÊNCIA: Aumento de 15% no volume de embarques"
- "💡 OPORTUNIDADE: Otimizar rota para 3 embarques"
"""
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Conhecimento específico do domínio de embarques"""
        return {
            'main_models': [
                'Embarque',
                'EmbarqueItem', 
                'Separacao',
                'Transportadora',
                'TabelaFrete'
            ],
            'key_fields': [
                'numero',
                'status',
                'data_prevista_embarque',
                'data_embarque',
                'peso_total',
                'volumes_total',
                'separacao_status',
                'transportadora_nome'
            ],
            'kpis': [
                'embarques_no_prazo',
                'eficiencia_separacao',
                'utilizacao_capacidade',
                'tempo_medio_separacao',
                'performance_transportadora'
            ],
            'common_queries': [
                'embarques hoje',
                'embarques pendentes',
                'separação pendente',
                'embarques transportadora',
                'volumes por embarque',
                'embarques atrasados',
                'cronograma saída'
            ]
        }
    
    def _get_domain_keywords(self) -> List[str]:
        """Palavras-chave específicas do domínio de embarques"""
        return [
            'embarque', 'embarques', 'embarcar',
            'separacao', 'separação', 'separar',
            'volume', 'volumes', 'carga', 'cargas',
            'picking', 'liberacao', 'liberação',
            'programacao', 'programação', 'cronograma',
            'saida', 'saída', 'expedicao', 'expedição',
            'transportadora', 'motorista', 'veiculo',
            'pendente', 'ativo', 'liberado', 'carregado'
        ]


# Exportações principais
__all__ = [
    'EmbarquesAgent'
]

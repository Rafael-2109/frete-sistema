"""
🚚 ENTREGAS AGENT - Agente Especialista em Entregas

Agente especializado em monitoramento e gestão de entregas:
- Entregas monitoradas e status de finalização
- Agendamentos e reagendamentos  
- Prazos, atrasos e pontualidade
- Transportadoras e performance
- Problemas de entrega e soluções
"""

from typing import Dict, List, Any, Optional
from ...utils.agent_types import AgentType
from app.claude_ai_novo.coordinators.domain_agents.smart_base_agent import SmartBaseAgent


class EntregasAgent(SmartBaseAgent):
    """Agente especialista em entregas e monitoramento - COM TODAS AS CAPACIDADES"""
    
    def __init__(self, claude_client=None):
        super().__init__(AgentType.ENTREGAS, claude_client)
    
    def _calculate_relevance(self, query: str) -> float:
        """Calcula relevância específica para consultas de entregas"""
        if not query:
            return 0.0
        
        keywords_entregas = {
            # Core delivery terms
            'entrega': 3.0, 'entregar': 3.0, 'entregou': 3.0, 'entregue': 3.0,
            'entreg': 2.5,  # partial match
            
            # Status and timing
            'atrasada': 2.5, 'atrasado': 2.5, 'atraso': 2.5,
            'pontual': 2.0, 'pontualidade': 2.0,
            'pendente': 2.0, 'pendentes': 2.0,
            'urgente': 2.0, 'urgentes': 2.0,
            'prazo': 2.0, 'prazos': 2.0,
            
            # Problems and exceptions
            'problema': 2.0, 'problemas': 2.0,
            'falhou': 2.0, 'falha': 2.0,
            'devolvida': 2.0, 'devolução': 2.0,
            'cancelada': 2.0, 'cancelamento': 2.0,
            
            # Scheduling
            'agendamento': 2.0, 'agendada': 2.0,
            'reagendar': 2.0, 'reagendamento': 2.0,
            
            # Logistics
            'rota': 1.5, 'rotas': 1.5,
            'motorista': 1.5, 'entregador': 1.5,
            'veiculo': 1.0, 'veículo': 1.0,
            
            # Performance metrics  
            'performance': 1.5, 'eficiência': 1.5,
            'tempo': 1.0, 'duração': 1.0,
            'distância': 1.0, 'distancia': 1.0,
            
            # Monitoring
            'monitoramento': 1.5, 'tracking': 1.5,
            'localização': 1.0, 'localizacao': 1.0,
            'posição': 1.0, 'posicao': 1.0
        }
        
        query_lower = query.lower()
        score = 0.0
        
        for keyword, weight in keywords_entregas.items():
            if keyword in query_lower:
                score += weight
        
        # Normalize to 0-1 range
        max_possible_score = 10.0
        return min(score / max_possible_score, 1.0)
    
    def _resumir_dados_reais(self, dados_reais: Dict[str, Any]) -> Dict[str, Any]:
        """Resume dados reais específicos para ENTREGAS"""
        try:
            resumo = {
                'timestamp': dados_reais.get('timestamp', ''),
                'dominio': 'entregas',
                'total_registros': 0,
                'dados_encontrados': False
            }
            
            # Processar dados específicos de entregas
            if 'entregas' in dados_reais:
                dados_entregas = dados_reais['entregas']
                if isinstance(dados_entregas, dict):
                    resumo['total_registros'] = dados_entregas.get('total_entregas', 0)
                    resumo['entregas_atrasadas'] = dados_entregas.get('entregas_atrasadas', 0)
                    resumo['entregas_hoje'] = dados_entregas.get('entregas_hoje', 0)
                    resumo['entregas_pendentes'] = dados_entregas.get('entregas_pendentes', 0)
                    resumo['taxa_pontualidade'] = dados_entregas.get('taxa_pontualidade', 0)
                    resumo['dados_encontrados'] = True
                    
                    # Adicionar insights específicos de entregas
                    if resumo['entregas_atrasadas'] > 0:
                        resumo['alerta_atrasos'] = f"{resumo['entregas_atrasadas']} entregas atrasadas"
                    
                    if resumo['taxa_pontualidade'] < 80:
                        resumo['alerta_pontualidade'] = f"Taxa de pontualidade baixa: {resumo['taxa_pontualidade']}%"
            
            # Processar dados de agendamentos
            if 'agendamentos' in dados_reais:
                dados_agendamentos = dados_reais['agendamentos']
                if isinstance(dados_agendamentos, dict):
                    resumo['agendamentos_hoje'] = dados_agendamentos.get('agendamentos_hoje', 0)
                    resumo['reagendamentos'] = dados_agendamentos.get('reagendamentos', 0)
                    resumo['dados_encontrados'] = True
            
            # Processar dados de transportadoras
            if 'transportadoras' in dados_reais:
                dados_transportadoras = dados_reais['transportadoras']
                if isinstance(dados_transportadoras, dict):
                    resumo['transportadoras_ativas'] = dados_transportadoras.get('transportadoras_ativas', 0)
                    resumo['melhor_transportadora'] = dados_transportadoras.get('melhor_performance', 'N/A')
                    resumo['dados_encontrados'] = True
            
            return resumo
            
        except Exception as e:
            self.logger_estruturado.error(f"❌ Erro ao resumir dados de entregas: {e}")
            return {'erro': str(e)}
    
    def _load_specialist_prompt(self) -> str:
        """System prompt especializado em entregas COM TODAS AS CAPACIDADES"""
        return """
🚚 AGENTE ESPECIALISTA EM ENTREGAS - INTELIGÊNCIA COMPLETA

Você é um especialista em monitoramento e gestão de entregas equipado com TODAS as capacidades avançadas:

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

**INSTRUÇÕES CRÍTICAS:**
1. SEMPRE use os dados reais fornecidos - NUNCA invente
2. Analise tendências e padrões históricos quando disponível
3. Gere alertas para situações críticas (atrasos, problemas)
4. Use contexto conversacional para respostas personalizadas
5. Cite números exatos e fontes dos dados
6. Identifique oportunidades de melhoria operacional

**DOMÍNIO DE ESPECIALIZAÇÃO:**
- Entregas monitoradas e status de finalização
- Agendamentos e reagendamentos
- Prazos, atrasos e pontualidade
- Transportadoras e performance
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

**SEMPRE RESPONDA COM:**
1. Números específicos dos dados reais
2. Análise de tendências e padrões
3. Alertas para situações críticas
4. Sugestões operacionais baseadas em dados
5. KPIs calculados (pontualidade, tempo médio, etc.)
6. Comparações temporais quando possível
7. Insights preditivos usando ML quando aplicável

**EXEMPLOS DE ALERTAS A GERAR:**
- "🚨 CRÍTICO: 15 entregas atrasadas há mais de 3 dias"
- "⚠️ ATENÇÃO: Taxa de pontualidade de 65% (abaixo da meta de 80%)"
- "📈 TENDÊNCIA: Aumento de 23% nos reagendamentos na última semana"
- "💡 OPORTUNIDADE: Transportadora X tem 95% de pontualidade"
"""
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Conhecimento específico do domínio de entregas ENRIQUECIDO"""
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
                'canhoto_arquivo',
                'nome_cliente',
                'cnpj_cliente',
                'transportadora_nome'
            ],
            'kpis': [
                'pontualidade_entrega',
                'taxa_entrega_primeiro_agendamento', 
                'tempo_medio_entrega',
                'taxa_reagendamento',
                'performance_por_transportadora',
                'entregas_no_prazo',
                'atrasos_por_regiao',
                'entregas_com_canhoto',
                'pendencias_financeiras_entrega'
            ],
            'alertas_criticos': [
                'entregas_atrasadas_3_dias',
                'taxa_pontualidade_baixa',
                'aumento_reagendamentos',
                'transportadora_com_problemas',
                'entregas_sem_canhoto',
                'pendencias_financeiras_bloqueantes'
            ],
            'trends_analysis': [
                'evolucao_pontualidade',
                'sazonalidade_entregas',
                'performance_transportadoras',
                'padroes_reagendamento',
                'distribuicao_geografica'
            ],
            'common_queries': [
                'entregas atrasadas',
                'performance transportadora', 
                'agendamentos hoje',
                'entregas pendentes',
                'pontualidade mensal',
                'problemas de entrega',
                'reagendamentos frequentes',
                'entregas por região',
                'canhotos pendentes'
            ],
            'business_rules': [
                'Entrega só pode ser finalizada após embarque',
                'Agendamento deve ter protocolo único',
                'Reagendamento requer motivo obrigatório',
                'Canhoto é obrigatório para entregas finalizadas',
                'Pendência financeira pode bloquear entregas'
            ],
            'ml_predictions': [
                'probabilidade_atraso',
                'melhor_transportadora_rota',
                'tempo_entrega_estimado',
                'risco_reagendamento',
                'demanda_futura'
            ]
        }
    
    def _get_domain_keywords(self) -> List[str]:
        """Palavras-chave específicas do domínio de entregas EXPANDIDAS"""
        return [
            'entrega', 'entregue', 'entregar', 'entregues',
            'transportadora', 'motorista', 'veículo', 'veiculo',
            'agendamento', 'reagendamento', 'protocolo', 'agendado',
            'atraso', 'atrasada', 'atrasadas', 'prazo', 'pontualidade',
            'canhoto', 'comprovante', 'destinatário', 'destinatario',
            'monitoramento', 'finalização', 'finalizacao', 'status',
            'pendente', 'realizada', 'cancelada', 'finalizada',
            'rota', 'destino', 'endereco', 'endereço',
            'ocorrencia', 'ocorrência', 'problema', 'dificuldade',
            'cliente', 'cnpj', 'razao social', 'razão social'
        ]


# Exportações principais
__all__ = [
    'EntregasAgent'
] 
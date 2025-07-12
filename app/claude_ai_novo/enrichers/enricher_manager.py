"""
Enricher Manager - Coordena todos os enrichers para enriquecimento de dados
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from ..utils.base_classes import BaseProcessor

logger = logging.getLogger(__name__)


class EnricherManager(BaseProcessor):
    """
    Gerencia e coordena os enrichers para enriquecimento de contexto e dados.
    """
    
    def __init__(self):
        """Inicializa o EnricherManager."""
        super().__init__()
        self.enrichers = {}
        self._initialize_enrichers()
        logger.info("EnricherManager inicializado")
    
    def _initialize_enrichers(self):
        """Inicializa os enrichers disponíveis."""
        try:
            # Importar enrichers disponíveis
            from .context_enricher import ContextEnricher
            self.enrichers['context'] = ContextEnricher()
            logger.info("ContextEnricher carregado")
        except Exception as e:
            logger.warning(f"Erro ao carregar ContextEnricher: {e}")
        
        try:
            from .semantic_enricher import SemanticEnricher
            self.enrichers['semantic'] = SemanticEnricher()
            logger.info("SemanticEnricher carregado")
        except Exception as e:
            logger.warning(f"Erro ao carregar SemanticEnricher: {e}")
    
    def enrich_context(self, data: Dict[str, Any], query: str, domain: str) -> Dict[str, Any]:
        """
        Enriquece dados com contexto adicional.
        
        Args:
            data: Dados brutos do banco
            query: Query original do usuário
            domain: Domínio detectado (entregas, pedidos, etc)
            
        Returns:
            Dados enriquecidos com contexto adicional
        """
        try:
            logger.info(f"Enriquecendo dados para domínio: {domain}")
            
            # Copia dados originais
            enriched = data.copy()
            
            # Adicionar metadados
            enriched['metadata'] = {
                'query': query,
                'domain': domain,
                'enriched_at': datetime.now().isoformat(),
                'enrichment_version': '1.0'
            }
            
            # Enriquecer com contexto
            if 'context' in self.enrichers:
                try:
                    context_data = self.enrichers['context'].enrich(data, domain)
                    enriched['context'] = context_data
                    logger.info("Contexto enriquecido com sucesso")
                except Exception as e:
                    logger.error(f"Erro ao enriquecer contexto: {e}")
            
            # Enriquecer semanticamente
            if 'semantic' in self.enrichers:
                try:
                    semantic_data = self.enrichers['semantic'].enrich_query(query, domain)
                    enriched['semantic'] = semantic_data
                    logger.info("Dados semânticos enriquecidos")
                except Exception as e:
                    logger.error(f"Erro ao enriquecer semanticamente: {e}")
            
            # Adicionar análises específicas por domínio
            enriched.update(self._enrich_by_domain(data, domain))
            
            # Adicionar histórico se disponível
            enriched['historico'] = self._get_historical_data(data, domain)
            
            # Calcular tendências
            enriched['tendencias'] = self._calculate_trends(data, domain)
            
            # Adicionar comparações
            enriched['comparacoes'] = self._get_comparisons(data, domain)
            
            logger.info(f"Enriquecimento completo. Campos adicionados: {list(enriched.keys())}")
            return enriched
            
        except Exception as e:
            logger.error(f"Erro no enriquecimento: {e}")
            # Retorna dados originais em caso de erro
            return data
    
    def _enrich_by_domain(self, data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Enriquecimento específico por domínio."""
        domain_enrichment = {}
        
        try:
            if domain == "entregas":
                domain_enrichment['analise_entregas'] = self._analyze_deliveries(data)
            elif domain == "pedidos":
                domain_enrichment['analise_pedidos'] = self._analyze_orders(data)
            elif domain == "faturamento":
                domain_enrichment['analise_faturamento'] = self._analyze_billing(data)
            elif domain == "transportadoras":
                domain_enrichment['analise_transportadoras'] = self._analyze_carriers(data)
                
        except Exception as e:
            logger.error(f"Erro no enriquecimento por domínio {domain}: {e}")
        
        return domain_enrichment
    
    def _analyze_deliveries(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Análise específica para entregas."""
        analysis = {
            'total_entregas': 0,
            'entregas_no_prazo': 0,
            'entregas_atrasadas': 0,
            'taxa_sucesso': 0.0,
            'tempo_medio_entrega': 0
        }
        
        try:
            if 'entregas' in data and isinstance(data['entregas'], list):
                entregas = data['entregas']
                analysis['total_entregas'] = len(entregas)
                
                # Calcular métricas
                for entrega in entregas:
                    if entrega.get('status') == 'entregue':
                        if entrega.get('no_prazo'):
                            analysis['entregas_no_prazo'] += 1
                        else:
                            analysis['entregas_atrasadas'] += 1
                
                # Taxa de sucesso
                if analysis['total_entregas'] > 0:
                    analysis['taxa_sucesso'] = (
                        analysis['entregas_no_prazo'] / analysis['total_entregas'] * 100
                    )
                    
        except Exception as e:
            logger.error(f"Erro na análise de entregas: {e}")
        
        return analysis
    
    def _analyze_orders(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Análise específica para pedidos."""
        analysis = {
            'total_pedidos': 0,
            'pedidos_pendentes': 0,
            'pedidos_faturados': 0,
            'valor_total': 0.0,
            'ticket_medio': 0.0
        }
        
        try:
            if 'pedidos' in data and isinstance(data['pedidos'], list):
                pedidos = data['pedidos']
                analysis['total_pedidos'] = len(pedidos)
                
                for pedido in pedidos:
                    if pedido.get('status') == 'pendente':
                        analysis['pedidos_pendentes'] += 1
                    elif pedido.get('status') == 'faturado':
                        analysis['pedidos_faturados'] += 1
                    
                    valor = pedido.get('valor_total', 0)
                    if isinstance(valor, (int, float)):
                        analysis['valor_total'] += valor
                
                # Ticket médio
                if analysis['total_pedidos'] > 0:
                    analysis['ticket_medio'] = analysis['valor_total'] / analysis['total_pedidos']
                    
        except Exception as e:
            logger.error(f"Erro na análise de pedidos: {e}")
        
        return analysis
    
    def _analyze_billing(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Análise específica para faturamento."""
        analysis = {
            'total_faturado': 0.0,
            'total_notas': 0,
            'valor_medio_nota': 0.0,
            'periodo_analise': 'últimos 30 dias'
        }
        
        try:
            if 'faturamento' in data and isinstance(data['faturamento'], list):
                notas = data['faturamento']
                analysis['total_notas'] = len(notas)
                
                for nota in notas:
                    valor = nota.get('valor_total', 0)
                    if isinstance(valor, (int, float)):
                        analysis['total_faturado'] += valor
                
                if analysis['total_notas'] > 0:
                    analysis['valor_medio_nota'] = (
                        analysis['total_faturado'] / analysis['total_notas']
                    )
                    
        except Exception as e:
            logger.error(f"Erro na análise de faturamento: {e}")
        
        return analysis
    
    def _analyze_carriers(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Análise específica para transportadoras."""
        analysis = {
            'total_transportadoras': 0,
            'transportadoras_ativas': 0,
            'performance_media': 0.0
        }
        
        try:
            if 'transportadoras' in data and isinstance(data['transportadoras'], list):
                transportadoras = data['transportadoras']
                analysis['total_transportadoras'] = len(transportadoras)
                
                for transp in transportadoras:
                    if transp.get('ativa'):
                        analysis['transportadoras_ativas'] += 1
                        
        except Exception as e:
            logger.error(f"Erro na análise de transportadoras: {e}")
        
        return analysis
    
    def _get_historical_data(self, data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Obtém dados históricos para comparação."""
        historical = {
            'periodo_comparacao': 'últimos 30 dias',
            'variacao_percentual': 0.0,
            'tendencia': 'estável'
        }
        
        # TODO: Implementar busca de dados históricos reais
        # Por enquanto, retorna dados simulados
        
        return historical
    
    def _calculate_trends(self, data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Calcula tendências baseadas nos dados."""
        trends = {
            'tendencia_geral': 'estável',
            'projecao_proximos_dias': 0,
            'confianca_projecao': 0.0
        }
        
        # TODO: Implementar cálculo real de tendências
        # Por enquanto, retorna análise básica
        
        return trends
    
    def _get_comparisons(self, data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Obtém comparações relevantes."""
        comparisons = {
            'vs_periodo_anterior': {
                'variacao': 0.0,
                'descricao': 'sem dados suficientes'
            },
            'vs_media_historica': {
                'variacao': 0.0,
                'descricao': 'sem dados suficientes'
            }
        }
        
        # TODO: Implementar comparações reais
        # Por enquanto, retorna estrutura básica
        
        return comparisons
    
    def enrich_response(self, response: str, enrichment_data: Dict[str, Any]) -> str:
        """
        Enriquece a resposta final com insights dos dados enriquecidos.
        
        Args:
            response: Resposta original
            enrichment_data: Dados de enriquecimento
            
        Returns:
            Resposta enriquecida
        """
        try:
            # Se há análises disponíveis, adiciona insights
            insights = []
            
            # Adicionar insights de análise
            for key in ['analise_entregas', 'analise_pedidos', 'analise_faturamento']:
                if key in enrichment_data:
                    analysis = enrichment_data[key]
                    if key == 'analise_entregas' and 'taxa_sucesso' in analysis:
                        insights.append(
                            f"Taxa de sucesso nas entregas: {analysis['taxa_sucesso']:.1f}%"
                        )
                    elif key == 'analise_pedidos' and 'ticket_medio' in analysis:
                        insights.append(
                            f"Ticket médio dos pedidos: R$ {analysis['ticket_medio']:,.2f}"
                        )
            
            # Adicionar insights ao response se houver
            if insights:
                response += "\n\n**Insights Adicionais:**\n"
                for insight in insights:
                    response += f"- {insight}\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao enriquecer resposta: {e}")
            return response


# Função de conveniência para o módulo
def get_enricher_manager() -> EnricherManager:
    """Retorna instância do EnricherManager."""
    return EnricherManager() 
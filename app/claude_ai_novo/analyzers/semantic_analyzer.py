"""
🧠 SEMANTIC ANALYZER - Análise Semântica
=======================================

Módulo responsável por análise semântica de consultas, dados e contexto.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class SemanticAnalyzer:
    """
    Analisador semântico para consultas, dados e contexto.
    
    Responsabilidades:
    - Análise semântica de consultas
    - Extração de entidades
    - Análise de sentimento
    - Classificação de intenções
    - Mapeamento semântico
    """
    
    def __init__(self):
        """Inicializa o analisador semântico."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("🧠 SemanticAnalyzer inicializado")
        
        # Padrões semânticos básicos
        self.entity_patterns = {
            'data': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            'numero': r'\b\d{3,}\b',
            'valor': r'R\$\s*\d+[,.]?\d*',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'cnpj': r'\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b'
        }
        
        # Palavras-chave por domínio
        self.domain_keywords = {
            'faturamento': ['faturamento', 'nf', 'nota', 'fiscal', 'valor', 'total'],
            'entrega': ['entrega', 'entregar', 'destino', 'prazo', 'atrasado'],
            'pedido': ['pedido', 'item', 'produto', 'quantidade', 'cotação'],
            'cliente': ['cliente', 'empresa', 'razão', 'social', 'cnpj'],
            'transportadora': ['transportadora', 'freteiro', 'transporte', 'veículo'],
            'embarque': ['embarque', 'carregamento', 'volumes', 'peso']
        }
        
        # Indicadores de sentimento
        self.sentiment_indicators = {
            'positive': ['bom', 'ótimo', 'excelente', 'perfeito', 'sucesso', 'completo'],
            'negative': ['ruim', 'péssimo', 'erro', 'problema', 'falha', 'atrasado'],
            'neutral': ['normal', 'padrão', 'comum', 'regular', 'médio']
        }
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analisa semanticamente uma consulta.
        
        Args:
            query: Consulta para análise
            
        Returns:
            Resultado da análise semântica
        """
        try:
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'analysis_type': 'semantic',
                'status': 'success',
                'entities': {},
                'domains': [],
                'sentiment': 'neutral',
                'confidence': 0.0,
                'keywords': [],
                'intent': 'unknown'
            }
            
            query_lower = query.lower()
            
            # Extrair entidades
            analysis['entities'] = self._extract_entities(query)
            
            # Identificar domínios
            analysis['domains'] = self._identify_domains(query_lower)
            
            # Analisar sentimento
            analysis['sentiment'] = self._analyze_sentiment(query_lower)
            
            # Extrair palavras-chave
            analysis['keywords'] = self._extract_keywords(query_lower)
            
            # Determinar intenção
            analysis['intent'] = self._determine_intent(query_lower, analysis['domains'])
            
            # Calcular confiança
            analysis['confidence'] = self._calculate_confidence(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"❌ Erro na análise semântica: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'analysis_type': 'semantic',
                'status': 'error',
                'error': str(e),
                'confidence': 0.0
            }
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extrai entidades do texto.
        
        Args:
            text: Texto para extração
            
        Returns:
            Entidades extraídas
        """
        return self._extract_entities(text)
    
    def classify_intent(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Classifica intenção da consulta.
        
        Args:
            query: Consulta para classificação
            context: Contexto adicional
            
        Returns:
            Classificação da intenção
        """
        try:
            classification = {
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'primary_intent': 'unknown',
                'secondary_intents': [],
                'confidence': 0.0,
                'context_used': context is not None,
                'reasoning': []
            }
            
            query_lower = query.lower()
            
            # Classificar intenções baseadas em padrões
            intents = self._classify_intents(query_lower)
            
            if intents:
                classification['primary_intent'] = intents[0]['intent']
                classification['confidence'] = intents[0]['confidence']
                classification['secondary_intents'] = [
                    intent['intent'] for intent in intents[1:3]
                ]
                classification['reasoning'] = [
                    intent['reasoning'] for intent in intents[:3]
                ]
            
            # Usar contexto se disponível
            if context:
                classification = self._enhance_with_context(classification, context)
            
            return classification
            
        except Exception as e:
            self.logger.error(f"❌ Erro na classificação de intenção: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'primary_intent': 'unknown',
                'error': str(e),
                'confidence': 0.0
            }
    
    def analyze_semantic_similarity(self, text1: str, text2: str) -> Dict[str, Any]:
        """
        Analisa similaridade semântica entre dois textos.
        
        Args:
            text1: Primeiro texto
            text2: Segundo texto
            
        Returns:
            Análise de similaridade
        """
        try:
            similarity = {
                'timestamp': datetime.now().isoformat(),
                'text1': text1,
                'text2': text2,
                'similarity_score': 0.0,
                'common_entities': [],
                'common_keywords': [],
                'domain_overlap': []
            }
            
            # Analisar ambos os textos
            analysis1 = self.analyze_query(text1)
            analysis2 = self.analyze_query(text2)
            
            # Calcular similaridade
            similarity['similarity_score'] = self._calculate_similarity(analysis1, analysis2)
            
            # Encontrar elementos comuns
            similarity['common_entities'] = self._find_common_entities(
                analysis1['entities'], analysis2['entities']
            )
            
            similarity['common_keywords'] = list(
                set(analysis1['keywords']) & set(analysis2['keywords'])
            )
            
            similarity['domain_overlap'] = list(
                set(analysis1['domains']) & set(analysis2['domains'])
            )
            
            return similarity
            
        except Exception as e:
            self.logger.error(f"❌ Erro na análise de similaridade: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'text1': text1,
                'text2': text2,
                'similarity_score': 0.0,
                'error': str(e)
            }
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extrai entidades usando padrões regex."""
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches
        
        return entities
    
    def _identify_domains(self, text: str) -> List[str]:
        """Identifica domínios baseados em palavras-chave."""
        domains = []
        
        for domain, keywords in self.domain_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    domains.append(domain)
                    break
        
        return list(set(domains))
    
    def _analyze_sentiment(self, text: str) -> str:
        """Analisa sentimento básico."""
        positive_count = sum(1 for word in self.sentiment_indicators['positive'] if word in text)
        negative_count = sum(1 for word in self.sentiment_indicators['negative'] if word in text)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrai palavras-chave relevantes."""
        keywords = []
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filtrar palavras relevantes
        relevant_words = [word for word in words if len(word) > 3]
        
        # Adicionar palavras-chave de domínio encontradas
        for domain_keywords in self.domain_keywords.values():
            for keyword in domain_keywords:
                if keyword in text:
                    keywords.append(keyword)
        
        return list(set(keywords + relevant_words[:5]))
    
    def _determine_intent(self, text: str, domains: List[str]) -> str:
        """Determina intenção baseada no texto e domínios."""
        # Padrões de intenção
        if any(word in text for word in ['listar', 'mostrar', 'ver', 'consultar']):
            return 'query'
        elif any(word in text for word in ['criar', 'adicionar', 'inserir']):
            return 'create'
        elif any(word in text for word in ['atualizar', 'modificar', 'alterar']):
            return 'update'
        elif any(word in text for word in ['deletar', 'remover', 'excluir']):
            return 'delete'
        elif any(word in text for word in ['relatório', 'exportar', 'gerar']):
            return 'report'
        elif any(word in text for word in ['problema', 'erro', 'ajuda']):
            return 'help'
        else:
            return 'general'
    
    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calcula confiança da análise."""
        confidence = 0.0
        
        # Confiança baseada em entidades encontradas
        if analysis['entities']:
            confidence += 0.3
        
        # Confiança baseada em domínios identificados
        if analysis['domains']:
            confidence += 0.3
        
        # Confiança baseada em palavras-chave
        if analysis['keywords']:
            confidence += 0.2
        
        # Confiança baseada em intenção
        if analysis['intent'] != 'unknown':
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _classify_intents(self, text: str) -> List[Dict[str, Any]]:
        """Classifica múltiplas intenções."""
        intents = []
        
        intent_patterns = {
            'query': ['listar', 'mostrar', 'ver', 'consultar', 'buscar'],
            'create': ['criar', 'adicionar', 'inserir', 'novo'],
            'update': ['atualizar', 'modificar', 'alterar', 'editar'],
            'delete': ['deletar', 'remover', 'excluir', 'apagar'],
            'report': ['relatório', 'exportar', 'gerar', 'planilha'],
            'help': ['problema', 'erro', 'ajuda', 'dúvida']
        }
        
        for intent, patterns in intent_patterns.items():
            matches = sum(1 for pattern in patterns if pattern in text)
            if matches > 0:
                intents.append({
                    'intent': intent,
                    'confidence': min(matches * 0.3, 1.0),
                    'reasoning': f"Encontrados {matches} padrões para {intent}"
                })
        
        return sorted(intents, key=lambda x: x['confidence'], reverse=True)
    
    def _enhance_with_context(self, classification: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Aprimora classificação com contexto."""
        # Aumentar confiança se contexto suporta a intenção
        if context.get('previous_intent') == classification['primary_intent']:
            classification['confidence'] = min(classification['confidence'] + 0.2, 1.0)
            classification['reasoning'].append("Contexto confirma intenção")
        
        return classification
    
    def _calculate_similarity(self, analysis1: Dict[str, Any], analysis2: Dict[str, Any]) -> float:
        """Calcula similaridade entre duas análises."""
        similarity = 0.0
        
        # Similaridade de domínios
        domains1 = set(analysis1.get('domains', []))
        domains2 = set(analysis2.get('domains', []))
        if domains1 and domains2:
            domain_similarity = len(domains1 & domains2) / len(domains1 | domains2)
            similarity += domain_similarity * 0.4
        
        # Similaridade de palavras-chave
        keywords1 = set(analysis1.get('keywords', []))
        keywords2 = set(analysis2.get('keywords', []))
        if keywords1 and keywords2:
            keyword_similarity = len(keywords1 & keywords2) / len(keywords1 | keywords2)
            similarity += keyword_similarity * 0.3
        
        # Similaridade de intenção
        if analysis1.get('intent') == analysis2.get('intent'):
            similarity += 0.3
        
        return similarity
    
    def _find_common_entities(self, entities1: Dict[str, List[str]], entities2: Dict[str, List[str]]) -> List[str]:
        """Encontra entidades comuns."""
        common = []
        
        for entity_type in entities1:
            if entity_type in entities2:
                common_values = set(entities1[entity_type]) & set(entities2[entity_type])
                common.extend(list(common_values))
        
        return common


def get_semantic_analyzer() -> SemanticAnalyzer:
    """
    Obtém instância do analisador semântico.
    
    Returns:
        Instância do SemanticAnalyzer
    """
    return SemanticAnalyzer() 
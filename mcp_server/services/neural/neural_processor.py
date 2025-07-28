# Neural Processing Engine for Intelligent Responses
import json
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import re
import logging
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import joblib
import os

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """Result of neural processing"""
    intent: str
    confidence: float
    entities: Dict[str, Any]
    suggested_action: str
    response_template: str
    metadata: Dict[str, Any]

class NeuralProcessor:
    """Main neural processing engine for intelligent freight system responses"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or "models/neural/intent_classifier.pkl"
        self.intent_classifier = None
        self.entity_patterns = self._load_entity_patterns()
        self.response_templates = self._load_response_templates()
        self.confidence_threshold = 0.65
        
        # Initialize or load model
        self._initialize_model()
        
    def _initialize_model(self):
        """Initialize or load the intent classification model"""
        if os.path.exists(self.model_path):
            try:
                self.intent_classifier = joblib.load(self.model_path)
                logger.info(f"Loaded neural model from {self.model_path}")
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                self._create_new_model()
        else:
            self._create_new_model()
            
    def _create_new_model(self):
        """Create a new intent classification model"""
        # Create a simple pipeline with TF-IDF and Naive Bayes
        self.intent_classifier = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 3),
                stop_words='portuguese',
                analyzer='word',
                lowercase=True
            )),
            ('classifier', MultinomialNB(alpha=0.1))
        ])
        logger.info("Created new neural model")
        
    def _load_entity_patterns(self) -> Dict[str, List[str]]:
        """Load entity extraction patterns"""
        return {
            'freight_id': [
                r'FRT\d{6}',
                r'frete\s*#?\s*(\d+)',
                r'pedido\s*#?\s*(\d+)',
                r'id\s*:?\s*(\d+)'
            ],
            'date': [
                r'\d{1,2}/\d{1,2}/\d{4}',
                r'\d{4}-\d{2}-\d{2}',
                r'hoje|amanhã|ontem',
                r'(\d+)\s*dias?\s*atrás'
            ],
            'location': [
                r'[A-Z][a-záêç]+(?:\s+[A-Z][a-záêç]+)*',
                r'CEP\s*:?\s*\d{5}-?\d{3}',
                r'(origem|destino)\s*:?\s*([A-Za-záêç\s]+)'
            ],
            'value': [
                r'R\$\s*\d+(?:[.,]\d{2})?',
                r'\d+(?:[.,]\d{2})?\s*reais?',
                r'valor\s*:?\s*\d+(?:[.,]\d{2})?'
            ],
            'status': [
                r'(pendente|em\s*trânsito|entregue|cancelado)',
                r'status\s*:?\s*(\w+)',
                r'(aguardando|processando|finalizado)'
            ]
        }
        
    def _load_response_templates(self) -> Dict[str, List[str]]:
        """Load response templates for different intents"""
        return {
            'query_freight': [
                "Aqui estão as informações do frete {freight_id}: {details}",
                "Frete {freight_id} encontrado: Status: {status}, Valor: {value}",
                "Detalhes do pedido {freight_id}: {summary}"
            ],
            'list_freights': [
                "Encontrei {count} fretes {filter}: {list}",
                "Lista de fretes {filter}: {summary}",
                "Aqui estão os {count} fretes solicitados: {details}"
            ],
            'create_freight': [
                "Novo frete criado com sucesso! ID: {freight_id}",
                "Frete {freight_id} registrado. {details}",
                "Pedido criado: {freight_id}. Status: {status}"
            ],
            'update_status': [
                "Status do frete {freight_id} atualizado para: {status}",
                "Atualização realizada: Frete {freight_id} agora está {status}",
                "Status alterado com sucesso para {status}"
            ],
            'calculate_route': [
                "Rota calculada: {origin} → {destination}. Distância: {distance}km",
                "Melhor rota encontrada: {route_details}",
                "Trajeto otimizado: {summary}. Tempo estimado: {time}"
            ],
            'analyze_performance': [
                "Análise de desempenho: {metrics}",
                "Relatório gerado: {summary}",
                "Indicadores do período: {kpis}"
            ],
            'unknown': [
                "Desculpe, não entendi sua solicitação. Você pode reformular?",
                "Não consegui processar sua requisição. Tente ser mais específico.",
                "Preciso de mais informações para ajudá-lo. O que você gostaria de fazer?"
            ]
        }
        
    def process(self, text: str, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process input text and generate intelligent response"""
        try:
            # Preprocess text
            cleaned_text = self._preprocess_text(text)
            
            # Extract entities
            entities = self._extract_entities(cleaned_text)
            
            # Classify intent
            intent, confidence = self._classify_intent(cleaned_text, entities, context)
            
            # Determine action
            action = self._determine_action(intent, entities, context)
            
            # Select response template
            template = self._select_response_template(intent, confidence)
            
            # Build metadata
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'original_text': text,
                'cleaned_text': cleaned_text,
                'processing_time': 0.0,  # Would be calculated in real implementation
                'context': context or {}
            }
            
            return ProcessingResult(
                intent=intent,
                confidence=confidence,
                entities=entities,
                suggested_action=action,
                response_template=template,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error in neural processing: {e}")
            return self._fallback_result(text, str(e))
            
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for analysis"""
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep essential punctuation
        text = re.sub(r'[^a-záêçõãôíúà0-9\s.,!?#$-]', '', text)
        
        return text
        
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from text using patterns"""
        entities = {}
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    if entity_type in ['freight_id', 'value']:
                        # Extract first match for unique entities
                        entities[entity_type] = matches[0]
                    elif entity_type == 'date':
                        # Process date entities
                        entities[entity_type] = self._process_date_entity(matches[0])
                    else:
                        # Store all matches for other types
                        entities[entity_type] = matches
                    break
                    
        return entities
        
    def _process_date_entity(self, date_str: str) -> str:
        """Process date entity to standard format"""
        # Simple date processing - would be more sophisticated in production
        date_mappings = {
            'hoje': datetime.now().strftime('%Y-%m-%d'),
            'ontem': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
            'amanhã': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        }
        
        return date_mappings.get(date_str, date_str)
        
    def _classify_intent(self, text: str, entities: Dict[str, Any], 
                        context: Optional[Dict[str, Any]]) -> Tuple[str, float]:
        """Classify user intent based on text and entities"""
        # Rule-based classification for now
        # In production, this would use the trained model
        
        intent_keywords = {
            'query_freight': ['consultar', 'ver', 'mostrar', 'buscar', 'status', 'onde está'],
            'list_freights': ['listar', 'todos', 'lista', 'quais', 'quantos'],
            'create_freight': ['criar', 'novo', 'adicionar', 'cadastrar', 'registrar'],
            'update_status': ['atualizar', 'mudar', 'alterar', 'trocar', 'modificar'],
            'calculate_route': ['calcular', 'rota', 'caminho', 'trajeto', 'distância'],
            'analyze_performance': ['análise', 'relatório', 'desempenho', 'métricas', 'indicadores']
        }
        
        # Check for intent keywords
        best_intent = 'unknown'
        best_score = 0.0
        
        for intent, keywords in intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text) / len(keywords)
            
            # Boost score if relevant entities are found
            if intent == 'query_freight' and 'freight_id' in entities:
                score += 0.3
            elif intent == 'calculate_route' and any(k in entities for k in ['origin', 'destination', 'location']):
                score += 0.3
            elif intent == 'update_status' and 'status' in entities:
                score += 0.3
                
            if score > best_score:
                best_score = score
                best_intent = intent
                
        # Normalize confidence
        confidence = min(best_score, 1.0)
        
        # Use fallback if confidence is too low
        if confidence < self.confidence_threshold:
            best_intent = 'unknown'
            
        return best_intent, confidence
        
    def _determine_action(self, intent: str, entities: Dict[str, Any], 
                         context: Optional[Dict[str, Any]]) -> str:
        """Determine the suggested action based on intent and entities"""
        action_mapping = {
            'query_freight': 'retrieve_freight_details',
            'list_freights': 'list_freights_filtered',
            'create_freight': 'create_new_freight',
            'update_status': 'update_freight_status',
            'calculate_route': 'calculate_optimal_route',
            'analyze_performance': 'generate_performance_report',
            'unknown': 'request_clarification'
        }
        
        return action_mapping.get(intent, 'no_action')
        
    def _select_response_template(self, intent: str, confidence: float) -> str:
        """Select appropriate response template"""
        templates = self.response_templates.get(intent, self.response_templates['unknown'])
        
        # Select template based on confidence
        if confidence > 0.8:
            return templates[0]  # Most confident template
        elif confidence > 0.6:
            return templates[min(1, len(templates) - 1)]  # Middle template
        else:
            return templates[-1]  # Least confident template
            
    def _fallback_result(self, text: str, error: str) -> ProcessingResult:
        """Generate fallback result in case of processing error"""
        return ProcessingResult(
            intent='error',
            confidence=0.0,
            entities={},
            suggested_action='handle_error',
            response_template='Ocorreu um erro ao processar sua solicitação. Por favor, tente novamente.',
            metadata={
                'error': error,
                'original_text': text,
                'timestamp': datetime.now().isoformat()
            }
        )
        
    def train(self, training_data: List[Tuple[str, str]]):
        """Train the intent classifier with new data"""
        if not training_data:
            logger.warning("No training data provided")
            return
            
        texts, labels = zip(*training_data)
        
        try:
            self.intent_classifier.fit(texts, labels)
            
            # Save the trained model
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.intent_classifier, self.model_path)
            
            logger.info(f"Model trained and saved to {self.model_path}")
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            
    def evaluate(self, test_data: List[Tuple[str, str]]) -> Dict[str, float]:
        """Evaluate model performance"""
        if not test_data or not self.intent_classifier:
            return {'accuracy': 0.0, 'error': 'No test data or model'}
            
        texts, true_labels = zip(*test_data)
        
        try:
            predictions = self.intent_classifier.predict(texts)
            
            # Calculate metrics
            accuracy = sum(p == t for p, t in zip(predictions, true_labels)) / len(true_labels)
            
            return {
                'accuracy': accuracy,
                'total_samples': len(test_data),
                'correct_predictions': sum(p == t for p, t in zip(predictions, true_labels))
            }
            
        except Exception as e:
            logger.error(f"Error evaluating model: {e}")
            return {'accuracy': 0.0, 'error': str(e)}

# Add missing import
from datetime import timedelta
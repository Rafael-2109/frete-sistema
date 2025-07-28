# Intent Classification for Freight System
import numpy as np
from typing import List, Tuple, Dict, Optional
import json
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class IntentClassifier:
    """Advanced intent classification for freight management system"""
    
    def __init__(self, model_type: str = 'svm'):
        self.model_type = model_type
        self.pipeline = None
        self.intents = []
        self.vectorizer_params = {
            'max_features': 5000,
            'ngram_range': (1, 3),
            'stop_words': 'portuguese',
            'analyzer': 'word',
            'lowercase': True,
            'strip_accents': 'unicode',
            'max_df': 0.9,
            'min_df': 2
        }
        self.trained = False
        self.training_history = []
        
    def _create_pipeline(self) -> Pipeline:
        """Create ML pipeline based on model type"""
        vectorizer = TfidfVectorizer(**self.vectorizer_params)
        
        if self.model_type == 'naive_bayes':
            classifier = MultinomialNB(alpha=0.1)
        elif self.model_type == 'svm':
            classifier = LinearSVC(
                C=1.0,
                random_state=42,
                max_iter=2000,
                class_weight='balanced'
            )
        elif self.model_type == 'random_forest':
            classifier = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                n_jobs=-1,
                class_weight='balanced'
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
            
        return Pipeline([
            ('tfidf', vectorizer),
            ('classifier', classifier)
        ])
        
    def get_training_data(self) -> List[Tuple[str, str]]:
        """Get built-in training data for freight system"""
        return [
            # Query freight intents
            ("mostrar frete 123456", "query_freight"),
            ("ver status do pedido FRT000123", "query_freight"),
            ("onde está meu frete", "query_freight"),
            ("consultar pedido 789", "query_freight"),
            ("buscar frete com id 456", "query_freight"),
            ("qual o status do frete 321", "query_freight"),
            ("informações sobre o pedido 654", "query_freight"),
            ("detalhes do frete FRT000789", "query_freight"),
            ("rastrear pedido 147", "query_freight"),
            ("acompanhar frete 258", "query_freight"),
            
            # List freights intents
            ("listar todos os fretes", "list_freights"),
            ("mostrar fretes pendentes", "list_freights"),
            ("quais fretes estão em trânsito", "list_freights"),
            ("ver todos os pedidos", "list_freights"),
            ("fretes do mês", "list_freights"),
            ("pedidos de hoje", "list_freights"),
            ("mostrar fretes entregues", "list_freights"),
            ("listar pedidos cancelados", "list_freights"),
            ("todos os fretes ativos", "list_freights"),
            ("ver lista de pedidos", "list_freights"),
            
            # Create freight intents
            ("criar novo frete", "create_freight"),
            ("adicionar pedido", "create_freight"),
            ("novo frete de São Paulo para Rio", "create_freight"),
            ("cadastrar frete", "create_freight"),
            ("registrar novo pedido", "create_freight"),
            ("incluir frete no sistema", "create_freight"),
            ("gerar novo pedido de transporte", "create_freight"),
            ("criar pedido urgente", "create_freight"),
            ("adicionar frete com origem em Curitiba", "create_freight"),
            ("novo transporte para amanhã", "create_freight"),
            
            # Update status intents
            ("atualizar status para entregue", "update_status"),
            ("mudar status do frete 123 para em trânsito", "update_status"),
            ("alterar pedido para cancelado", "update_status"),
            ("trocar status para pendente", "update_status"),
            ("marcar como entregue", "update_status"),
            ("definir status como em processamento", "update_status"),
            ("atualizar situação do frete", "update_status"),
            ("modificar status do pedido", "update_status"),
            ("confirmar entrega do frete 456", "update_status"),
            ("cancelar pedido 789", "update_status"),
            
            # Calculate route intents
            ("calcular rota de SP para RJ", "calculate_route"),
            ("melhor caminho para Belo Horizonte", "calculate_route"),
            ("distância entre São Paulo e Curitiba", "calculate_route"),
            ("rota mais rápida para o destino", "calculate_route"),
            ("calcular trajeto do frete", "calculate_route"),
            ("otimizar rota de entrega", "calculate_route"),
            ("qual a distância para Porto Alegre", "calculate_route"),
            ("tempo estimado de viagem", "calculate_route"),
            ("rota econômica para o nordeste", "calculate_route"),
            ("caminho mais curto entre cidades", "calculate_route"),
            
            # Analyze performance intents
            ("gerar relatório de desempenho", "analyze_performance"),
            ("análise de fretes do mês", "analyze_performance"),
            ("métricas de entrega", "analyze_performance"),
            ("estatísticas de transporte", "analyze_performance"),
            ("indicadores de performance", "analyze_performance"),
            ("relatório de eficiência", "analyze_performance"),
            ("análise de custos de frete", "analyze_performance"),
            ("dashboard de operações", "analyze_performance"),
            ("KPIs do período", "analyze_performance"),
            ("desempenho dos motoristas", "analyze_performance"),
            
            # Search intents
            ("buscar fretes para São Paulo", "search_freights"),
            ("procurar pedidos do cliente João", "search_freights"),
            ("encontrar fretes acima de 1000 reais", "search_freights"),
            ("pesquisar por data de criação", "search_freights"),
            ("filtrar fretes por região", "search_freights"),
            ("buscar pedidos urgentes", "search_freights"),
            ("localizar fretes com atraso", "search_freights"),
            ("procurar por tipo de carga", "search_freights"),
            ("pesquisar fretes do motorista Carlos", "search_freights"),
            ("encontrar pedidos com desconto", "search_freights"),
            
            # Help intents
            ("ajuda", "help"),
            ("como usar o sistema", "help"),
            ("o que você pode fazer", "help"),
            ("comandos disponíveis", "help"),
            ("preciso de ajuda", "help"),
            ("tutorial", "help"),
            ("instruções de uso", "help"),
            ("manual do sistema", "help"),
            ("como funciona", "help"),
            ("me ajude", "help"),
            
            # Greeting intents
            ("olá", "greeting"),
            ("oi", "greeting"),
            ("bom dia", "greeting"),
            ("boa tarde", "greeting"),
            ("boa noite", "greeting"),
            ("hey", "greeting"),
            ("e aí", "greeting"),
            ("como vai", "greeting"),
            ("tudo bem", "greeting"),
            ("saudações", "greeting"),
            
            # Calculate pricing intents
            ("calcular preço do frete", "calculate_pricing"),
            ("quanto custa enviar para o Rio", "calculate_pricing"),
            ("valor do transporte", "calculate_pricing"),
            ("orçamento de frete", "calculate_pricing"),
            ("preço para 100kg", "calculate_pricing"),
            ("cotação de transporte", "calculate_pricing"),
            ("simular valor de entrega", "calculate_pricing"),
            ("custo do frete expresso", "calculate_pricing"),
            ("tabela de preços", "calculate_pricing"),
            ("calcular frete com seguro", "calculate_pricing")
        ]
        
    def train(self, training_data: Optional[List[Tuple[str, str]]] = None, 
              validation_split: float = 0.2) -> Dict[str, float]:
        """Train the intent classifier"""
        if training_data is None:
            training_data = self.get_training_data()
            
        if len(training_data) < 10:
            raise ValueError("Insufficient training data (minimum 10 samples)")
            
        # Prepare data
        texts, labels = zip(*training_data)
        self.intents = list(set(labels))
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            texts, labels, 
            test_size=validation_split, 
            random_state=42,
            stratify=labels
        )
        
        # Create and train pipeline
        self.pipeline = self._create_pipeline()
        
        logger.info(f"Training {self.model_type} classifier with {len(X_train)} samples...")
        
        try:
            # Train model
            self.pipeline.fit(X_train, y_train)
            self.trained = True
            
            # Evaluate
            train_score = self.pipeline.score(X_train, y_train)
            val_score = self.pipeline.score(X_val, y_val)
            
            # Cross-validation
            cv_scores = cross_val_score(
                self.pipeline, texts, labels, 
                cv=5, scoring='accuracy'
            )
            
            # Store training history
            history_entry = {
                'timestamp': datetime.now().isoformat(),
                'model_type': self.model_type,
                'train_samples': len(X_train),
                'val_samples': len(X_val),
                'train_accuracy': train_score,
                'val_accuracy': val_score,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std()
            }
            self.training_history.append(history_entry)
            
            logger.info(f"Training complete - Train: {train_score:.3f}, Val: {val_score:.3f}")
            
            return {
                'train_accuracy': train_score,
                'val_accuracy': val_score,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'num_intents': len(self.intents)
            }
            
        except Exception as e:
            logger.error(f"Error training classifier: {e}")
            raise
            
    def predict(self, text: str) -> Tuple[str, float]:
        """Predict intent with confidence score"""
        if not self.trained or self.pipeline is None:
            # Try to load saved model or train new one
            if not self.load():
                self.train()
                
        try:
            # Get prediction
            prediction = self.pipeline.predict([text])[0]
            
            # Get confidence scores
            if hasattr(self.pipeline.named_steps['classifier'], 'decision_function'):
                scores = self.pipeline.named_steps['classifier'].decision_function([text])[0]
                # Convert to probabilities using softmax
                exp_scores = np.exp(scores - np.max(scores))
                probabilities = exp_scores / exp_scores.sum()
                
                # Get confidence for predicted class
                class_idx = list(self.pipeline.classes_).index(prediction)
                confidence = float(probabilities[class_idx])
            else:
                # For models with predict_proba
                probabilities = self.pipeline.predict_proba([text])[0]
                confidence = float(max(probabilities))
                
            return prediction, confidence
            
        except Exception as e:
            logger.error(f"Error predicting intent: {e}")
            return 'unknown', 0.0
            
    def predict_batch(self, texts: List[str]) -> List[Tuple[str, float]]:
        """Predict intents for multiple texts"""
        return [self.predict(text) for text in texts]
        
    def get_intent_examples(self, intent: str, n: int = 5) -> List[str]:
        """Get example texts for a specific intent"""
        training_data = self.get_training_data()
        examples = [text for text, label in training_data if label == intent]
        return examples[:n]
        
    def evaluate(self, test_data: List[Tuple[str, str]]) -> Dict[str, Any]:
        """Evaluate classifier performance"""
        if not self.trained:
            raise ValueError("Classifier not trained")
            
        texts, true_labels = zip(*test_data)
        predictions = self.pipeline.predict(texts)
        
        # Calculate metrics
        report = classification_report(
            true_labels, predictions, 
            output_dict=True,
            zero_division=0
        )
        
        conf_matrix = confusion_matrix(true_labels, predictions)
        
        return {
            'classification_report': report,
            'confusion_matrix': conf_matrix.tolist(),
            'accuracy': report['accuracy'],
            'intents': list(set(true_labels))
        }
        
    def save(self, path: str = "models/neural/intent_classifier.pkl"):
        """Save trained model"""
        if not self.trained:
            raise ValueError("Cannot save untrained model")
            
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        model_data = {
            'pipeline': self.pipeline,
            'intents': self.intents,
            'model_type': self.model_type,
            'training_history': self.training_history,
            'vectorizer_params': self.vectorizer_params
        }
        
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
            
        logger.info(f"Model saved to {path}")
        
    def load(self, path: str = "models/neural/intent_classifier.pkl") -> bool:
        """Load trained model"""
        if not os.path.exists(path):
            logger.warning(f"Model file not found: {path}")
            return False
            
        try:
            with open(path, 'rb') as f:
                model_data = pickle.load(f)
                
            self.pipeline = model_data['pipeline']
            self.intents = model_data['intents']
            self.model_type = model_data.get('model_type', 'svm')
            self.training_history = model_data.get('training_history', [])
            self.vectorizer_params = model_data.get('vectorizer_params', self.vectorizer_params)
            self.trained = True
            
            logger.info(f"Model loaded from {path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
            
    def get_feature_importance(self, n_features: int = 20) -> List[Tuple[str, float]]:
        """Get most important features for classification"""
        if not self.trained:
            raise ValueError("Classifier not trained")
            
        # Get feature names
        vectorizer = self.pipeline.named_steps['tfidf']
        feature_names = vectorizer.get_feature_names_out()
        
        # Get feature importance based on model type
        if self.model_type == 'random_forest':
            importances = self.pipeline.named_steps['classifier'].feature_importances_
        elif self.model_type == 'svm':
            # Use absolute coefficients for linear SVM
            importances = np.abs(self.pipeline.named_steps['classifier'].coef_).mean(axis=0)
        else:
            # For Naive Bayes, use feature log probabilities
            importances = np.exp(self.pipeline.named_steps['classifier'].feature_log_prob_).mean(axis=0)
            
        # Sort features by importance
        indices = np.argsort(importances)[::-1][:n_features]
        
        return [(feature_names[i], float(importances[i])) for i in indices]
        
    def explain_prediction(self, text: str) -> Dict[str, Any]:
        """Explain why a certain intent was predicted"""
        if not self.trained:
            raise ValueError("Classifier not trained")
            
        # Get prediction
        intent, confidence = self.predict(text)
        
        # Transform text to features
        features = self.pipeline.named_steps['tfidf'].transform([text])
        
        # Get feature names
        feature_names = self.pipeline.named_steps['tfidf'].get_feature_names_out()
        
        # Get non-zero features
        non_zero_indices = features.nonzero()[1]
        active_features = [(feature_names[i], features[0, i]) for i in non_zero_indices]
        
        # Sort by TF-IDF value
        active_features.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'text': text,
            'predicted_intent': intent,
            'confidence': confidence,
            'top_features': active_features[:10],
            'num_features': len(active_features)
        }
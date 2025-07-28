#!/usr/bin/env python3
# Training script for neural models
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.neural.intent_classifier import IntentClassifier
from services.neural.neural_processor import NeuralProcessor
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def train_intent_classifier():
    """Train the intent classification model"""
    logger.info("Training intent classifier...")
    
    # Create classifiers with different algorithms
    classifiers = {
        'svm': IntentClassifier(model_type='svm'),
        'naive_bayes': IntentClassifier(model_type='naive_bayes'),
        'random_forest': IntentClassifier(model_type='random_forest')
    }
    
    results = {}
    
    for name, classifier in classifiers.items():
        logger.info(f"\nTraining {name} classifier...")
        
        # Train with built-in data
        metrics = classifier.train()
        results[name] = metrics
        
        # Save the model
        model_path = f"intent_classifier_{name}.pkl"
        classifier.save(model_path)
        
        logger.info(f"{name} results: {metrics}")
        
    # Select best model based on validation accuracy
    best_model = max(results.items(), key=lambda x: x[1]['val_accuracy'])[0]
    logger.info(f"\nBest model: {best_model}")
    
    # Save the best model as default
    best_classifier = classifiers[best_model]
    best_classifier.save("intent_classifier.pkl")
    
    return results

def create_sample_training_data():
    """Create sample training data for the neural processor"""
    training_data = []
    
    # Get intent classifier training data
    classifier = IntentClassifier()
    base_data = classifier.get_training_data()
    
    # Add some variations
    variations = {
        'query_freight': [
            "preciso ver o frete 123",
            "me mostre o pedido FRT000456",
            "quero informações do transporte 789",
            "cadê meu frete",
            "rastreamento do pedido 321"
        ],
        'create_freight': [
            "quero enviar uma carga para São Paulo",
            "preciso de um frete urgente",
            "nova entrega para amanhã",
            "cadastrar transporte de móveis",
            "criar pedido de 500kg"
        ],
        'calculate_route': [
            "quanto tempo leva de SP a RJ",
            "melhor rota para o sul",
            "caminho mais econômico",
            "evitar pedágios na rota",
            "distância total do trajeto"
        ],
        'analyze_performance': [
            "relatório mensal de entregas",
            "performance dos motoristas",
            "análise de atrasos",
            "custos por região",
            "eficiência das rotas"
        ]
    }
    
    # Combine base data with variations
    training_data.extend(base_data)
    
    for intent, texts in variations.items():
        for text in texts:
            training_data.append((text, intent))
            
    return training_data

def test_neural_processor():
    """Test the neural processor with sample inputs"""
    logger.info("\nTesting neural processor...")
    
    processor = NeuralProcessor()
    
    test_cases = [
        "mostrar frete FRT000123",
        "criar novo frete de São Paulo para Rio de Janeiro com 1000kg",
        "quanto está o frete 456?",
        "listar todos os fretes pendentes",
        "calcular rota mais rápida para Belo Horizonte",
        "relatório de performance do mês",
        "atualizar status do pedido 789 para entregue",
        "buscar fretes do cliente João Silva"
    ]
    
    for test_text in test_cases:
        result = processor.process(test_text)
        logger.info(f"\nInput: {test_text}")
        logger.info(f"Intent: {result.intent} (confidence: {result.confidence:.2f})")
        logger.info(f"Entities: {result.entities}")
        logger.info(f"Action: {result.suggested_action}")
        logger.info(f"Template: {result.response_template[:50]}...")

def save_pre_trained_patterns():
    """Save pre-trained patterns and configurations"""
    patterns = {
        'intents': {
            'query_freight': {
                'description': 'Query freight information',
                'examples': ['ver frete', 'mostrar pedido', 'status do transporte'],
                'required_entities': ['freight_id'],
                'optional_entities': ['date', 'status']
            },
            'list_freights': {
                'description': 'List multiple freights',
                'examples': ['listar fretes', 'todos os pedidos', 'fretes pendentes'],
                'required_entities': [],
                'optional_entities': ['status', 'date', 'location']
            },
            'create_freight': {
                'description': 'Create new freight',
                'examples': ['criar frete', 'novo pedido', 'adicionar transporte'],
                'required_entities': ['origin', 'destination'],
                'optional_entities': ['weight', 'value', 'date']
            },
            'update_status': {
                'description': 'Update freight status',
                'examples': ['atualizar status', 'mudar para entregue', 'marcar como cancelado'],
                'required_entities': ['freight_id', 'status'],
                'optional_entities': []
            },
            'calculate_route': {
                'description': 'Calculate optimal route',
                'examples': ['calcular rota', 'melhor caminho', 'distância entre'],
                'required_entities': ['origin', 'destination'],
                'optional_entities': ['vehicle', 'avoid_tolls']
            },
            'analyze_performance': {
                'description': 'Generate performance analysis',
                'examples': ['relatório', 'análise', 'métricas', 'indicadores'],
                'required_entities': [],
                'optional_entities': ['date_range', 'metric_type']
            }
        },
        'entity_patterns': {
            'freight_id': {
                'type': 'identifier',
                'patterns': ['FRT\\d{6}', 'frete #?(\\d+)', 'pedido #?(\\d+)'],
                'examples': ['FRT000123', 'frete 456', 'pedido #789']
            },
            'location': {
                'type': 'place',
                'patterns': ['cidade', 'estado', 'CEP'],
                'examples': ['São Paulo', 'Rio de Janeiro', 'CEP 01234-567']
            },
            'date': {
                'type': 'temporal',
                'patterns': ['DD/MM/YYYY', 'hoje', 'amanhã', 'X dias atrás'],
                'examples': ['15/03/2024', 'hoje', '3 dias atrás']
            },
            'value': {
                'type': 'monetary',
                'patterns': ['R$ X', 'X reais'],
                'examples': ['R$ 1.500,00', '500 reais']
            },
            'weight': {
                'type': 'measurement',
                'patterns': ['X kg', 'X toneladas'],
                'examples': ['100kg', '2 toneladas']
            }
        },
        'response_strategies': {
            'informative': {
                'tone': 'professional',
                'includes': ['data', 'suggestions'],
                'format': 'structured'
            },
            'conversational': {
                'tone': 'friendly',
                'includes': ['greeting', 'acknowledgment'],
                'format': 'natural'
            },
            'error_handling': {
                'tone': 'helpful',
                'includes': ['explanation', 'alternatives'],
                'format': 'guided'
            }
        }
    }
    
    # Save patterns
    os.makedirs('patterns', exist_ok=True)
    with open('patterns/neural_patterns.json', 'w', encoding='utf-8') as f:
        json.dump(patterns, f, indent=2, ensure_ascii=False)
        
    logger.info("Pre-trained patterns saved to patterns/neural_patterns.json")

if __name__ == "__main__":
    # Train intent classifiers
    results = train_intent_classifier()
    
    # Save pre-trained patterns
    save_pre_trained_patterns()
    
    # Test neural processor
    test_neural_processor()
    
    logger.info("\nTraining complete!")
    logger.info("Models saved in current directory")
    logger.info("Best model saved as 'intent_classifier.pkl'")
    
    # Print summary
    print("\n=== Training Summary ===")
    for model, metrics in results.items():
        print(f"\n{model.upper()}:")
        print(f"  Train Accuracy: {metrics['train_accuracy']:.3f}")
        print(f"  Val Accuracy: {metrics['val_accuracy']:.3f}")
        print(f"  CV Mean: {metrics['cv_mean']:.3f} (+/- {metrics['cv_std']:.3f})")
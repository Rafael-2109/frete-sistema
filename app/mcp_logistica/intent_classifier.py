"""
Classificador de intenções para consultas em linguagem natural
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class Intent:
    """Representa uma intenção classificada"""
    primary: str
    secondary: Optional[str] = None
    confidence: float = 0.0
    action_required: bool = False
    parameters: Dict = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

class IntentClassifier:
    """Classifica intenções de consultas em linguagem natural"""
    
    def __init__(self):
        self.initialize_intent_patterns()
        self.initialize_intent_hierarchy()
        
    def initialize_intent_patterns(self):
        """Inicializa padrões para classificação de intenções"""
        self.intent_patterns = {
            # Consultas de informação
            'buscar': {
                'patterns': [
                    r'\b(?:buscar|procurar|encontrar|localizar)\b',
                    r'\b(?:mostrar|exibir|listar|ver)\b',
                    r'\b(?:quais|qual)\s+(?:são|é)\b',
                    r'\bconsultar\b'
                ],
                'keywords': ['buscar', 'procurar', 'encontrar', 'mostrar', 'listar'],
                'requires_entity': True
            },
            
            'status': {
                'patterns': [
                    r'\b(?:status|situação)\s+(?:de|da|do)\b',
                    r'\b(?:como está|onde está)\b',
                    r'\bestá\s+(?:entregue|atrasado|pendente)\b',
                    r'\b(?:posição|andamento)\b'
                ],
                'keywords': ['status', 'situação', 'posição', 'andamento'],
                'requires_entity': True
            },
            
            'contar': {
                'patterns': [
                    r'\b(?:quantos?|quantas?)\b',
                    r'\b(?:quantidade|total|número)\s+de\b',
                    r'\bcontar\b',
                    r'\bsomar\b'
                ],
                'keywords': ['quantos', 'quantas', 'quantidade', 'total', 'contar'],
                'requires_entity': False
            },
            
            'listar': {
                'patterns': [
                    r'\blistar?\s+(?:todos?|todas?)\b',
                    r'\btodos?\s+(?:os|as)\b',
                    r'\brelação\s+de\b',
                    r'\blista\s+de\b'
                ],
                'keywords': ['listar', 'todos', 'todas', 'relação', 'lista'],
                'requires_entity': False
            },
            
            # Análises
            'tendencia': {
                'patterns': [
                    r'\b(?:tendência|evolução)\b',
                    r'\b(?:crescimento|queda|variação)\b',
                    r'\b(?:aumentou|diminuiu|cresceu|caiu)\b',
                    r'\bcomparar\s+(?:com|entre)\b'
                ],
                'keywords': ['tendência', 'evolução', 'crescimento', 'comparar'],
                'requires_temporal': True
            },
            
            'ranking': {
                'patterns': [
                    r'\b(?:maiores?|menores?)\b',
                    r'\b(?:top|ranking)\b',
                    r'\b(?:primeiros?|últimos?)\b',
                    r'\bmais\s+(?:atrasados?|problemáticos?)\b'
                ],
                'keywords': ['maior', 'menor', 'top', 'ranking', 'primeiro'],
                'requires_entity': False
            },
            
            # Problemas e alertas
            'atraso': {
                'patterns': [
                    r'\b(?:atrasados?|atrasos?)\b',
                    r'\b(?:pendentes?|vencidos?)\b',
                    r'\bfora\s+do\s+prazo\b',
                    r'\bnão\s+(?:entregue|chegou)\b'
                ],
                'keywords': ['atrasado', 'atraso', 'pendente', 'vencido'],
                'alert_type': 'delay'
            },
            
            'falha': {
                'patterns': [
                    r'\b(?:falha|erro|problema)\b',
                    r'\b(?:divergência|inconsistência)\b',
                    r'\b(?:incorreto|errado|inválido)\b',
                    r'\bnão\s+(?:funciona|está\s+funcionando)\b'
                ],
                'keywords': ['falha', 'erro', 'problema', 'divergência'],
                'alert_type': 'error'
            },
            
            # Ações (requerem confirmação)
            'reagendar': {
                'patterns': [
                    r'\b(?:reagendar|remarcar)\b',
                    r'\b(?:alterar|mudar|trocar)\s+(?:a\s+)?data\b',
                    r'\b(?:adiar|antecipar)\b',
                    r'\bnova\s+data\b'
                ],
                'keywords': ['reagendar', 'remarcar', 'alterar data'],
                'action_type': 'reschedule',
                'requires_confirmation': True
            },
            
            'cancelar': {
                'patterns': [
                    r'\bcancelar\b',
                    r'\b(?:desistir|desistência)\b',
                    r'\bnão\s+(?:quero|queremos)\s+mais\b',
                    r'\bexcluir\b'
                ],
                'keywords': ['cancelar', 'desistir', 'excluir'],
                'action_type': 'cancel',
                'requires_confirmation': True
            },
            
            'aprovar': {
                'patterns': [
                    r'\b(?:aprovar|autorizar)\b',
                    r'\b(?:liberar|desbloquear)\b',
                    r'\b(?:confirmar|validar)\b',
                    r'\bdar\s+ok\b'
                ],
                'keywords': ['aprovar', 'autorizar', 'liberar', 'confirmar'],
                'action_type': 'approve',
                'requires_confirmation': True
            },
            
            # Exportação e relatórios
            'exportar': {
                'patterns': [
                    r'\b(?:exportar|gerar)\s+(?:relatório|planilha|excel)\b',
                    r'\b(?:baixar|download)\b',
                    r'\b(?:salvar|gravar)\s+(?:em|como)\b',
                    r'\benviar\s+por\s+e-?mail\b'
                ],
                'keywords': ['exportar', 'relatório', 'planilha', 'excel', 'baixar'],
                'output_format': 'file'
            }
        }
        
    def initialize_intent_hierarchy(self):
        """Define hierarquia e relações entre intenções"""
        self.intent_hierarchy = {
            'consulta': ['buscar', 'status', 'contar', 'listar'],
            'analise': ['tendencia', 'ranking', 'comparar'],
            'alerta': ['atraso', 'falha', 'problema'],
            'acao': ['reagendar', 'cancelar', 'aprovar', 'desbloquear'],
            'relatorio': ['exportar', 'visualizar', 'dashboard']
        }
        
        # Intenções que podem ser combinadas
        self.compatible_intents = {
            'buscar': ['exportar', 'contar'],
            'status': ['exportar', 'atraso'],
            'contar': ['tendencia', 'ranking'],
            'atraso': ['reagendar', 'exportar'],
            'falha': ['aprovar', 'cancelar']
        }
        
    def classify(self, query: str, entities: Dict = None, context: Dict = None) -> Intent:
        """Classifica a intenção de uma consulta"""
        query_lower = query.lower()
        intent_scores = defaultdict(float)
        
        # Pontuação baseada em padrões
        for intent_name, intent_config in self.intent_patterns.items():
            score = 0.0
            
            # Verifica padrões regex
            for pattern in intent_config.get('patterns', []):
                if re.search(pattern, query_lower):
                    score += 1.0
                    
            # Verifica palavras-chave
            for keyword in intent_config.get('keywords', []):
                if keyword in query_lower:
                    score += 0.5
                    
            # Ajusta pontuação baseada em requisitos
            if intent_config.get('requires_entity') and entities:
                if any(entities.values()):
                    score += 0.5
                else:
                    score -= 0.5
                    
            if intent_config.get('requires_temporal') and entities:
                if entities.get('temporal'):
                    score += 0.5
                else:
                    score -= 0.5
                    
            intent_scores[intent_name] = score
            
        # Encontra a intenção principal
        if not intent_scores:
            # Default para busca se não encontrar nada
            primary_intent = 'buscar'
            confidence = 0.3
        else:
            # Ordena por pontuação
            sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
            primary_intent = sorted_intents[0][0]
            confidence = min(sorted_intents[0][1] / 3.0, 1.0)  # Normaliza entre 0 e 1
            
        # Encontra intenção secundária se houver
        secondary_intent = None
        if len(sorted_intents) > 1 and sorted_intents[1][1] > 0.5:
            candidate = sorted_intents[1][0]
            # Verifica se é compatível com a principal
            if candidate in self.compatible_intents.get(primary_intent, []):
                secondary_intent = candidate
                
        # Determina se requer ação
        intent_config = self.intent_patterns.get(primary_intent, {})
        action_required = intent_config.get('requires_confirmation', False)
        
        # Extrai parâmetros da intenção
        parameters = self.extract_intent_parameters(primary_intent, query, entities, context)
        
        return Intent(
            primary=primary_intent,
            secondary=secondary_intent,
            confidence=confidence,
            action_required=action_required,
            parameters=parameters
        )
        
    def extract_intent_parameters(self, intent: str, query: str, entities: Dict, context: Dict) -> Dict:
        """Extrai parâmetros específicos para cada intenção"""
        parameters = {}
        
        if intent == 'reagendar':
            # Procura por nova data na consulta
            if entities and entities.get('temporal'):
                parameters['nova_data'] = entities['temporal'].get('value')
                
            # Procura por motivo
            motivo_match = re.search(r'(?:motivo|razão|porque)[::\s]+([^.!?]+)', query, re.IGNORECASE)
            if motivo_match:
                parameters['motivo'] = motivo_match.group(1).strip()
                
        elif intent == 'exportar':
            # Determina formato de exportação
            if 'excel' in query.lower() or 'xlsx' in query.lower():
                parameters['formato'] = 'excel'
            elif 'pdf' in query.lower():
                parameters['formato'] = 'pdf'
            elif 'csv' in query.lower():
                parameters['formato'] = 'csv'
            else:
                parameters['formato'] = 'excel'  # default
                
            # Procura por destinatário de email
            email_match = re.search(r'[\w._%+-]+@[\w.-]+\.[A-Z|a-z]{2,}', query)
            if email_match:
                parameters['email'] = email_match.group(0)
                
        elif intent == 'ranking':
            # Determina quantidade (top N)
            num_match = re.search(r'(?:top|primeiros?|últimos?)\s+(\d+)', query, re.IGNORECASE)
            if num_match:
                parameters['limite'] = int(num_match.group(1))
            else:
                parameters['limite'] = 10  # default
                
            # Determina ordenação
            if any(word in query.lower() for word in ['maior', 'maiores', 'mais']):
                parameters['ordem'] = 'desc'
            elif any(word in query.lower() for word in ['menor', 'menores', 'menos']):
                parameters['ordem'] = 'asc'
                
        elif intent == 'tendencia':
            # Determina período de análise
            if entities and entities.get('temporal'):
                temporal = entities['temporal']
                parameters['periodo'] = temporal.get('value')
                parameters['tipo_periodo'] = temporal.get('type')
            else:
                # Default para últimos 30 dias
                parameters['periodo'] = 'last_30_days'
                parameters['tipo_periodo'] = 'range'
                
        elif intent == 'aprovar' or intent == 'cancelar':
            # Procura por identificadores específicos
            if entities:
                if entities.get('nf'):
                    parameters['tipo_documento'] = 'nota_fiscal'
                    parameters['identificador'] = entities['nf']
                elif entities.get('pedido'):
                    parameters['tipo_documento'] = 'pedido'
                    parameters['identificador'] = entities['pedido']
                elif entities.get('protocolo'):
                    parameters['tipo_documento'] = 'protocolo'
                    parameters['identificador'] = entities['protocolo']
                    
        return parameters
        
    def get_intent_category(self, intent: str) -> str:
        """Retorna a categoria de uma intenção"""
        for category, intents in self.intent_hierarchy.items():
            if intent in intents:
                return category
        return 'outros'
        
    def suggest_followup_intents(self, current_intent: str) -> List[str]:
        """Sugere intenções de acompanhamento baseadas na atual"""
        suggestions = []
        
        # Sugestões baseadas em compatibilidade
        compatible = self.compatible_intents.get(current_intent, [])
        suggestions.extend(compatible)
        
        # Sugestões baseadas em fluxo comum
        if current_intent == 'buscar':
            suggestions.extend(['status', 'exportar', 'contar'])
        elif current_intent == 'atraso':
            suggestions.extend(['reagendar', 'listar', 'exportar'])
        elif current_intent == 'contar':
            suggestions.extend(['listar', 'tendencia', 'ranking'])
            
        # Remove duplicatas
        return list(set(suggestions))
        
    def validate_intent_requirements(self, intent: Intent, entities: Dict, context: Dict) -> Tuple[bool, List[str]]:
        """Valida se uma intenção tem todos os requisitos necessários"""
        missing = []
        intent_config = self.intent_patterns.get(intent.primary, {})
        
        # Verifica entidade obrigatória
        if intent_config.get('requires_entity'):
            has_entity = any([
                entities.get('nomes_proprios'),
                entities.get('cnpj'),
                entities.get('nf'),
                entities.get('pedido')
            ])
            if not has_entity:
                missing.append('entidade (cliente, pedido, NF, etc.)')
                
        # Verifica temporal obrigatório
        if intent_config.get('requires_temporal'):
            if not entities.get('temporal'):
                missing.append('período ou data')
                
        # Validações específicas por intenção
        if intent.primary == 'reagendar':
            if not intent.parameters.get('nova_data'):
                missing.append('nova data para agendamento')
                
        elif intent.primary == 'exportar':
            # Exportar sempre pode usar filtros do contexto atual
            pass
            
        is_valid = len(missing) == 0
        return is_valid, missing
# -*- coding: utf-8 -*-
"""
🧠 MOTOR NLP AVANÇADO PARA CONSULTAS EM PT-BR
Sistema completo de processamento de linguagem natural com:
- Classificação de intenções
- Extração de entidades
- Compreensão contextual
- Tradução query → SQL
- Aprendizado contínuo
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import json
import unicodedata

# Importações do sistema
try:
    from app.claude_ai.nlp_enhanced_analyzer import get_nlp_analyzer
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    logging.warning("⚠️ NLP avançado não disponível")

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Tipos de intenção das consultas"""
    # Consultas de busca
    SEARCH = "search"
    STATUS = "status"
    
    # Agregações
    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    
    # Análises
    TREND = "trend"
    COMPARISON = "comparison"
    RANKING = "ranking"
    
    # Operações
    LIST = "list"
    DETAIL = "detail"
    EXPORT = "export"
    
    # Temporais
    HISTORY = "history"
    FORECAST = "forecast"
    
    # Problemas
    ISSUES = "issues"
    ALERTS = "alerts"


class EntityType(Enum):
    """Tipos de entidades detectáveis"""
    # Temporal
    DATE = "date"
    TIME = "time"
    PERIOD = "period"
    
    # Localização
    LOCATION = "location"
    REGION = "region"
    STATE = "state"
    CITY = "city"
    
    # Negócio
    CLIENT = "client"
    PRODUCT = "product"
    ORDER = "order"
    INVOICE = "invoice"
    
    # Valores
    MONEY = "money"
    QUANTITY = "quantity"
    PERCENTAGE = "percentage"
    
    # Status
    STATUS = "status"
    PRIORITY = "priority"
    
    # Pessoas
    PERSON = "person"
    DEPARTMENT = "department"


@dataclass
class Entity:
    """Entidade extraída"""
    text: str
    type: EntityType
    value: Any
    confidence: float
    position: Tuple[int, int]
    normalized_value: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Intent:
    """Intenção detectada"""
    type: IntentType
    confidence: float
    sub_intents: List[IntentType] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Context:
    """Contexto da consulta"""
    temporal_scope: Dict[str, Any]
    implicit_filters: Dict[str, Any]
    business_domain: str
    urgency_level: str
    related_queries: List[str]
    user_history: List[Dict[str, Any]]


@dataclass
class NLPResult:
    """Resultado do processamento NLP"""
    original_query: str
    normalized_query: str
    tokens: List[str]
    intent: Intent
    entities: List[Entity]
    context: Context
    confidence_score: float
    sql_suggestion: Optional[str] = None
    clarification_needed: bool = False
    suggestions: List[str] = field(default_factory=list)


class NLPEngine:
    """Motor principal de processamento NLP"""
    
    def __init__(self):
        """Inicializa o motor NLP"""
        self.intent_patterns = self._load_intent_patterns()
        self.entity_patterns = self._load_entity_patterns()
        self.normalizer = QueryNormalizer()
        self.tokenizer = BrazilianTokenizer()
        self.entity_extractor = EntityExtractor()
        self.intent_classifier = IntentClassifier()
        self.context_analyzer = ContextAnalyzer()
        self.sql_translator = QueryToSQLTranslator()
        self.learning_engine = LearningEngine()
        
        logger.info("🧠 Motor NLP inicializado com sucesso")
    
    def process_query(self, query: str, user_context: Optional[Dict[str, Any]] = None) -> NLPResult:
        """
        Processa uma consulta em linguagem natural
        
        Args:
            query: Consulta em pt-BR
            user_context: Contexto adicional do usuário
            
        Returns:
            NLPResult com análise completa
        """
        logger.info(f"🔍 Processando consulta: '{query[:100]}...'")
        
        # 1. Normalização
        normalized = self.normalizer.normalize(query)
        
        # 2. Tokenização
        tokens = self.tokenizer.tokenize(normalized)
        
        # 3. Extração de entidades
        entities = self.entity_extractor.extract(normalized, tokens)
        
        # 4. Classificação de intenção
        intent = self.intent_classifier.classify(normalized, tokens, entities)
        
        # 5. Análise de contexto
        context = self.context_analyzer.analyze(normalized, entities, user_context)
        
        # 6. Cálculo de confiança
        confidence = self._calculate_confidence(intent, entities, context)
        
        # 7. Tradução para SQL (se aplicável)
        sql_suggestion = None
        if confidence > 0.7 and intent.type not in [IntentType.FORECAST, IntentType.EXPORT]:
            sql_suggestion = self.sql_translator.translate(intent, entities, context)
        
        # 8. Verificar necessidade de esclarecimento
        clarification_needed = confidence < 0.6 or len(entities) == 0
        
        # 9. Gerar sugestões
        suggestions = self._generate_suggestions(query, intent, entities, confidence)
        
        # 10. Registrar para aprendizado
        self.learning_engine.record_query(query, intent, entities, confidence)
        
        result = NLPResult(
            original_query=query,
            normalized_query=normalized,
            tokens=tokens,
            intent=intent,
            entities=entities,
            context=context,
            confidence_score=confidence,
            sql_suggestion=sql_suggestion,
            clarification_needed=clarification_needed,
            suggestions=suggestions
        )
        
        logger.info(f"✅ Processamento concluído - Intenção: {intent.type.value}, Confiança: {confidence:.2f}")
        
        return result
    
    def _load_intent_patterns(self) -> Dict[IntentType, List[re.Pattern]]:
        """Carrega padrões de detecção de intenções"""
        return {
            IntentType.SEARCH: [
                re.compile(r'\b(buscar?|procurar?|encontrar?|localizar?)\b', re.I),
                re.compile(r'\b(onde|qual|quais)\b.*\b(está|estão|fica|ficam)\b', re.I),
            ],
            IntentType.STATUS: [
                re.compile(r'\b(status|situação|posição|andamento)\b', re.I),
                re.compile(r'\bcomo\s+(está|estão|anda|andam)\b', re.I),
            ],
            IntentType.COUNT: [
                re.compile(r'\b(quantos?|quantas?|quantidade|total)\b', re.I),
                re.compile(r'\b(contar?|contagem|número)\s+de\b', re.I),
            ],
            IntentType.SUM: [
                re.compile(r'\b(soma|somar|total|totalizar)\b', re.I),
                re.compile(r'\bvalor\s+total\b', re.I),
            ],
            IntentType.TREND: [
                re.compile(r'\b(tendência|evolução|progressão)\b', re.I),
                re.compile(r'\b(crescimento|queda|variação)\b', re.I),
            ],
            IntentType.COMPARISON: [
                re.compile(r'\b(comparar?|comparação|versus|vs)\b', re.I),
                re.compile(r'\b(melhor|pior|mais|menos)\s+que\b', re.I),
            ],
            IntentType.LIST: [
                re.compile(r'\b(listar?|liste|mostrar?|mostre|exibir?)\b', re.I),
                re.compile(r'\b(quais|todos?|todas?)\b', re.I),
            ],
            IntentType.ISSUES: [
                re.compile(r'\b(problema|erro|falha|atraso|pendente)\b', re.I),
                re.compile(r'\b(crítico|urgente|emergência)\b', re.I),
            ],
        }
    
    def _load_entity_patterns(self) -> Dict[EntityType, List[re.Pattern]]:
        """Carrega padrões de extração de entidades"""
        return {
            EntityType.DATE: [
                re.compile(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b'),
                re.compile(r'\b(hoje|ontem|amanhã)\b', re.I),
                re.compile(r'\b(segunda|terça|quarta|quinta|sexta|sábado|domingo)\b', re.I),
            ],
            EntityType.MONEY: [
                re.compile(r'R\$\s*[\d.,]+', re.I),
                re.compile(r'\b\d+[.,]\d{2}\s*(reais?|R\$)', re.I),
            ],
            EntityType.CLIENT: [
                re.compile(r'\b(assai|atacadão|carrefour|tenda|fort|mateus)\b', re.I),
            ],
            EntityType.ORDER: [
                re.compile(r'\b(pedido|PDD)\s*#?\s*\d+\b', re.I),
            ],
            EntityType.INVOICE: [
                re.compile(r'\b(NF|nota\s*fiscal)\s*#?\s*\d+\b', re.I),
            ],
        }
    
    def _calculate_confidence(self, intent: Intent, entities: List[Entity], context: Context) -> float:
        """Calcula confiança geral do processamento"""
        confidence = intent.confidence * 0.5  # 50% peso da intenção
        
        # Peso das entidades (30%)
        if entities:
            entity_confidence = sum(e.confidence for e in entities) / len(entities)
            confidence += entity_confidence * 0.3
        
        # Peso do contexto (20%)
        context_score = 0.8  # Base
        if context.temporal_scope.get('type') == 'specific':
            context_score += 0.2
        confidence += context_score * 0.2
        
        return min(confidence, 1.0)
    
    def _generate_suggestions(self, query: str, intent: Intent, entities: List[Entity], 
                            confidence: float) -> List[str]:
        """Gera sugestões para melhorar a consulta"""
        suggestions = []
        
        if confidence < 0.6:
            suggestions.append("Tente ser mais específico sobre o que deseja consultar")
        
        if not entities:
            suggestions.append("Inclua detalhes como datas, clientes ou valores")
        
        if intent.type == IntentType.SEARCH and not any(e.type == EntityType.CLIENT for e in entities):
            suggestions.append("Especifique o cliente que deseja buscar")
        
        return suggestions


class QueryNormalizer:
    """Normalizador de consultas em pt-BR"""
    
    def __init__(self):
        self.corrections = {
            # Correções ortográficas comuns
            'assaí': 'assai',
            'asai': 'assai',
            'atacadao': 'atacadão',
            'carrefur': 'carrefour',
            'entrega': 'entregas',
            'pedido': 'pedidos',
            
            # Abreviações
            'nf': 'nota fiscal',
            'cte': 'conhecimento transporte',
            'pdd': 'pedido',
            'qtd': 'quantidade',
            'qtde': 'quantidade',
        }
        
        self.synonyms = {
            'atraso': ['atrasado', 'atrasada', 'pendente', 'vencido'],
            'cliente': ['empresa', 'comprador', 'destinatário'],
            'entrega': ['remessa', 'envio', 'despacho'],
        }
    
    def normalize(self, query: str) -> str:
        """Normaliza uma consulta"""
        # Remover acentos mantendo cedilha
        normalized = self._remove_accents(query.lower())
        
        # Aplicar correções
        for wrong, correct in self.corrections.items():
            normalized = re.sub(rf'\b{wrong}\b', correct, normalized)
        
        # Expandir contrações
        normalized = self._expand_contractions(normalized)
        
        # Normalizar espaços
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _remove_accents(self, text: str) -> str:
        """Remove acentos preservando caracteres especiais"""
        # Preservar ç
        text = text.replace('ç', '###CEDILHA###')
        
        # Remover acentos
        nfd = unicodedata.normalize('NFD', text)
        text = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
        
        # Restaurar ç
        text = text.replace('###CEDILHA###', 'ç')
        
        return text
    
    def _expand_contractions(self, text: str) -> str:
        """Expande contrações comuns"""
        contractions = {
            r'\bpq\b': 'porque',
            r'\btb\b': 'também',
            r'\bvc\b': 'você',
            r'\bn\b': 'não',
            r'\bqto\b': 'quanto',
            r'\bqdo\b': 'quando',
        }
        
        for contraction, expansion in contractions.items():
            text = re.sub(contraction, expansion, text)
        
        return text


class BrazilianTokenizer:
    """Tokenizador para português brasileiro"""
    
    def __init__(self):
        self.stop_words = {
            'a', 'o', 'as', 'os', 'de', 'da', 'do', 'das', 'dos',
            'em', 'na', 'no', 'nas', 'nos', 'por', 'para', 'com',
            'sem', 'sob', 'sobre', 'e', 'ou', 'mas', 'que', 'qual',
            'um', 'uma', 'uns', 'umas', 'ao', 'aos', 'à', 'às'
        }
    
    def tokenize(self, text: str) -> List[str]:
        """Tokeniza texto em pt-BR"""
        # Separar pontuação
        text = re.sub(r'([.,!?;:])', r' \1 ', text)
        
        # Dividir em tokens
        tokens = text.split()
        
        # Filtrar stop words e tokens vazios
        tokens = [t for t in tokens if t and t not in self.stop_words]
        
        return tokens


class EntityExtractor:
    """Extrator de entidades"""
    
    def __init__(self):
        self.patterns = self._load_patterns()
        self.normalizers = self._load_normalizers()
    
    def extract(self, text: str, tokens: List[str]) -> List[Entity]:
        """Extrai entidades do texto"""
        entities = []
        
        # Extrair por padrões regex
        for entity_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    entity = Entity(
                        text=match.group(),
                        type=entity_type,
                        value=match.group(),
                        confidence=0.9,
                        position=(match.start(), match.end())
                    )
                    
                    # Normalizar valor
                    if entity_type in self.normalizers:
                        entity.normalized_value = self.normalizers[entity_type](entity.value)
                    
                    entities.append(entity)
        
        # Extrair entidades compostas
        entities.extend(self._extract_composite_entities(text, tokens))
        
        # Remover duplicatas e resolver conflitos
        entities = self._resolve_conflicts(entities)
        
        return entities
    
    def _load_patterns(self) -> Dict[EntityType, List[re.Pattern]]:
        """Carrega padrões de extração"""
        return {
            EntityType.DATE: [
                re.compile(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b'),
                re.compile(r'\b\d{1,2}\s+de\s+(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\b', re.I),
                re.compile(r'\b(hoje|ontem|amanhã|anteontem)\b', re.I),
            ],
            EntityType.TIME: [
                re.compile(r'\b\d{1,2}:\d{2}(:\d{2})?\b'),
                re.compile(r'\b\d{1,2}\s*h(oras?)?\b', re.I),
            ],
            EntityType.MONEY: [
                re.compile(r'R\$\s*[\d.,]+', re.I),
                re.compile(r'\b\d+[.,]\d{2,3}(?:\.\d{3})*(?:,\d{2})?\s*(?:reais?|R\$)?', re.I),
            ],
            EntityType.QUANTITY: [
                re.compile(r'\b\d+\s*(?:unidades?|pçs?|peças?|caixas?|pallets?|containers?)\b', re.I),
            ],
            EntityType.PERCENTAGE: [
                re.compile(r'\b\d+[.,]?\d*\s*%'),
            ],
            EntityType.CLIENT: [
                re.compile(r'\b(?:assai|atacadão|carrefour|tenda|fort|mateus|mercantil\s*rodrigues)\b', re.I),
            ],
            EntityType.ORDER: [
                re.compile(r'\b(?:pedido|pdd|ordem)\s*(?:n[º°]?\s*)?\d+\b', re.I),
            ],
            EntityType.INVOICE: [
                re.compile(r'\b(?:nf|nota\s*fiscal|nfe|danfe)\s*(?:n[º°]?\s*)?\d+\b', re.I),
            ],
            EntityType.STATE: [
                re.compile(r'\b(?:SP|RJ|MG|PR|RS|SC|BA|PE|CE|GO|DF|ES|PA|MA|MT|MS|AC|AL|AM|AP|PB|PI|RN|RO|RR|SE|TO)\b'),
            ],
        }
    
    def _load_normalizers(self) -> Dict[EntityType, callable]:
        """Carrega normalizadores de valores"""
        return {
            EntityType.DATE: self._normalize_date,
            EntityType.MONEY: self._normalize_money,
            EntityType.QUANTITY: self._normalize_quantity,
            EntityType.PERCENTAGE: self._normalize_percentage,
        }
    
    def _normalize_date(self, value: str) -> Optional[datetime]:
        """Normaliza data para datetime"""
        today = datetime.now().date()
        
        # Datas relativas
        if value.lower() == 'hoje':
            return today
        elif value.lower() == 'ontem':
            return today - timedelta(days=1)
        elif value.lower() == 'amanhã':
            return today + timedelta(days=1)
        
        # Datas formato dd/mm/yyyy
        try:
            parts = re.split(r'[/-]', value)
            if len(parts) == 3:
                day, month, year = map(int, parts)
                if year < 100:
                    year += 2000
                return datetime(year, month, day).date()
        except:
            pass
        
        return None
    
    def _normalize_money(self, value: str) -> float:
        """Normaliza valor monetário"""
        # Remover R$ e espaços
        value = re.sub(r'R\$|\s|reais?', '', value, flags=re.I)
        
        # Converter para formato americano
        value = value.replace('.', '').replace(',', '.')
        
        try:
            return float(value)
        except:
            return 0.0
    
    def _normalize_quantity(self, value: str) -> int:
        """Normaliza quantidade"""
        # Extrair apenas números
        numbers = re.findall(r'\d+', value)
        if numbers:
            return int(numbers[0])
        return 0
    
    def _normalize_percentage(self, value: str) -> float:
        """Normaliza percentual"""
        # Remover % e converter
        value = value.replace('%', '').replace(',', '.')
        try:
            return float(value)
        except:
            return 0.0
    
    def _extract_composite_entities(self, text: str, tokens: List[str]) -> List[Entity]:
        """Extrai entidades compostas (ex: 'São Paulo')"""
        entities = []
        
        # Cidades compostas
        composite_cities = [
            'são paulo', 'rio de janeiro', 'belo horizonte', 'porto alegre',
            'são josé', 'santa catarina', 'mato grosso', 'espírito santo'
        ]
        
        for city in composite_cities:
            if city in text.lower():
                start = text.lower().find(city)
                entities.append(Entity(
                    text=text[start:start+len(city)],
                    type=EntityType.CITY,
                    value=city.title(),
                    confidence=0.95,
                    position=(start, start+len(city)),
                    normalized_value=city.title()
                ))
        
        return entities
    
    def _resolve_conflicts(self, entities: List[Entity]) -> List[Entity]:
        """Resolve conflitos entre entidades sobrepostas"""
        # Ordenar por posição
        entities.sort(key=lambda e: e.position[0])
        
        resolved = []
        last_end = -1
        
        for entity in entities:
            # Se não há sobreposição, adicionar
            if entity.position[0] >= last_end:
                resolved.append(entity)
                last_end = entity.position[1]
            # Se há sobreposição, escolher a de maior confiança
            elif resolved and entity.confidence > resolved[-1].confidence:
                resolved[-1] = entity
                last_end = entity.position[1]
        
        return resolved


class IntentClassifier:
    """Classificador de intenções"""
    
    def __init__(self):
        self.patterns = self._load_patterns()
        self.keywords = self._load_keywords()
    
    def classify(self, text: str, tokens: List[str], entities: List[Entity]) -> Intent:
        """Classifica a intenção da consulta"""
        scores = defaultdict(float)
        
        # Pontuação por padrões
        for intent_type, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    scores[intent_type] += 2.0
        
        # Pontuação por palavras-chave
        for token in tokens:
            for intent_type, keywords in self.keywords.items():
                if token in keywords:
                    scores[intent_type] += 1.0
        
        # Pontuação por entidades
        scores = self._score_by_entities(scores, entities)
        
        # Determinar intenção principal
        if not scores:
            return Intent(IntentType.LIST, 0.5)
        
        best_intent = max(scores.items(), key=lambda x: x[1])
        total_score = sum(scores.values())
        confidence = best_intent[1] / total_score if total_score > 0 else 0.5
        
        # Detectar sub-intenções
        sub_intents = [intent for intent, score in scores.items() 
                      if score > 0 and intent != best_intent[0]]
        
        return Intent(
            type=best_intent[0],
            confidence=min(confidence, 1.0),
            sub_intents=sub_intents[:3]  # Top 3 sub-intenções
        )
    
    def _load_patterns(self) -> Dict[IntentType, List[re.Pattern]]:
        """Carrega padrões de intenção"""
        return {
            IntentType.COUNT: [
                re.compile(r'\b(quantos?|quantas?)\b', re.I),
                re.compile(r'\b(quantidade|total|número)\s+de\b', re.I),
            ],
            IntentType.SUM: [
                re.compile(r'\bvalor\s+total\b', re.I),
                re.compile(r'\b(soma|somatório|totalizar)\b', re.I),
            ],
            IntentType.STATUS: [
                re.compile(r'\b(status|situação|posição)\b', re.I),
                re.compile(r'\bcomo\s+(está|estão)\b', re.I),
            ],
            IntentType.TREND: [
                re.compile(r'\b(evolução|tendência|progressão)\b', re.I),
                re.compile(r'\b(aumentou|diminuiu|cresceu|caiu)\b', re.I),
            ],
            IntentType.COMPARISON: [
                re.compile(r'\b(comparar|versus|vs|comparação)\b', re.I),
                re.compile(r'\b(melhor|pior|maior|menor)\s+que\b', re.I),
            ],
            IntentType.LIST: [
                re.compile(r'\b(listar?|liste|mostrar?|mostre)\b', re.I),
                re.compile(r'\b(quais|todos|todas)\b', re.I),
            ],
            IntentType.ISSUES: [
                re.compile(r'\b(problema|erro|falha|defeito)\b', re.I),
                re.compile(r'\b(atraso|atrasado|pendente|vencido)\b', re.I),
            ],
        }
    
    def _load_keywords(self) -> Dict[IntentType, Set[str]]:
        """Carrega palavras-chave por intenção"""
        return {
            IntentType.COUNT: {'contar', 'quantidade', 'total', 'quantos'},
            IntentType.SUM: {'soma', 'somar', 'totalizar', 'valor'},
            IntentType.STATUS: {'status', 'situação', 'andamento', 'posição'},
            IntentType.TREND: {'tendência', 'evolução', 'crescimento', 'queda'},
            IntentType.COMPARISON: {'comparar', 'versus', 'diferença', 'melhor', 'pior'},
            IntentType.LIST: {'listar', 'mostrar', 'exibir', 'todos', 'quais'},
            IntentType.DETAIL: {'detalhe', 'detalhes', 'informação', 'completo'},
            IntentType.ISSUES: {'problema', 'erro', 'atraso', 'falha', 'pendente'},
        }
    
    def _score_by_entities(self, scores: Dict[IntentType, float], 
                          entities: List[Entity]) -> Dict[IntentType, float]:
        """Ajusta pontuação baseada nas entidades"""
        entity_types = {e.type for e in entities}
        
        # Se tem datas, provavelmente é consulta temporal
        if EntityType.DATE in entity_types or EntityType.PERIOD in entity_types:
            scores[IntentType.HISTORY] += 1.0
            scores[IntentType.TREND] += 0.5
        
        # Se tem valores monetários
        if EntityType.MONEY in entity_types:
            scores[IntentType.SUM] += 1.0
            scores[IntentType.COMPARISON] += 0.5
        
        # Se tem status
        if EntityType.STATUS in entity_types:
            scores[IntentType.STATUS] += 2.0
            scores[IntentType.ISSUES] += 0.5
        
        return scores


class ContextAnalyzer:
    """Analisador de contexto"""
    
    def analyze(self, text: str, entities: List[Entity], 
                user_context: Optional[Dict[str, Any]] = None) -> Context:
        """Analisa o contexto da consulta"""
        temporal_scope = self._analyze_temporal_scope(entities)
        implicit_filters = self._detect_implicit_filters(text, entities)
        business_domain = self._detect_business_domain(text, entities)
        urgency_level = self._detect_urgency(text)
        related_queries = self._find_related_queries(text, user_context)
        user_history = user_context.get('history', []) if user_context else []
        
        return Context(
            temporal_scope=temporal_scope,
            implicit_filters=implicit_filters,
            business_domain=business_domain,
            urgency_level=urgency_level,
            related_queries=related_queries,
            user_history=user_history
        )
    
    def _analyze_temporal_scope(self, entities: List[Entity]) -> Dict[str, Any]:
        """Analisa escopo temporal"""
        date_entities = [e for e in entities if e.type == EntityType.DATE]
        
        if not date_entities:
            # Padrão: últimos 30 dias
            return {
                'type': 'relative',
                'period': 30,
                'unit': 'days',
                'description': 'Últimos 30 dias'
            }
        
        if len(date_entities) == 1:
            return {
                'type': 'specific',
                'date': date_entities[0].normalized_value,
                'description': f'Data específica: {date_entities[0].text}'
            }
        
        if len(date_entities) >= 2:
            dates = sorted([e.normalized_value for e in date_entities if e.normalized_value])
            if len(dates) >= 2:
                return {
                    'type': 'range',
                    'start': dates[0],
                    'end': dates[-1],
                    'description': f'Período: {dates[0]} a {dates[-1]}'
                }
        
        return {'type': 'unknown'}
    
    def _detect_implicit_filters(self, text: str, entities: List[Entity]) -> Dict[str, Any]:
        """Detecta filtros implícitos"""
        filters = {}
        
        # Filtro de urgência
        if any(word in text.lower() for word in ['urgente', 'crítico', 'emergência']):
            filters['priority'] = 'high'
        
        # Filtro de status
        if any(word in text.lower() for word in ['atrasado', 'pendente', 'vencido']):
            filters['status'] = 'delayed'
        elif any(word in text.lower() for word in ['entregue', 'finalizado', 'completo']):
            filters['status'] = 'completed'
        
        # Filtro de cliente
        client_entities = [e for e in entities if e.type == EntityType.CLIENT]
        if client_entities:
            filters['clients'] = [e.value for e in client_entities]
        
        # Filtro de localização
        location_entities = [e for e in entities if e.type in [EntityType.STATE, EntityType.CITY]]
        if location_entities:
            filters['locations'] = [e.value for e in location_entities]
        
        return filters
    
    def _detect_business_domain(self, text: str, entities: List[Entity]) -> str:
        """Detecta domínio de negócio"""
        domains = {
            'entregas': ['entrega', 'envio', 'despacho', 'remessa'],
            'financeiro': ['faturamento', 'pagamento', 'valor', 'nota fiscal'],
            'estoque': ['estoque', 'inventário', 'armazenagem', 'produto'],
            'pedidos': ['pedido', 'ordem', 'solicitação', 'compra'],
            'clientes': ['cliente', 'empresa', 'comprador', 'destinatário']
        }
        
        text_lower = text.lower()
        scores = {}
        
        for domain, keywords in domains.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                scores[domain] = score
        
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return 'geral'
    
    def _detect_urgency(self, text: str) -> str:
        """Detecta nível de urgência"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['emergência', 'crítico', 'urgentíssimo']):
            return 'critical'
        elif any(word in text_lower for word in ['urgente', 'rápido', 'imediato']):
            return 'high'
        elif any(word in text_lower for word in ['importante', 'prioridade']):
            return 'medium'
        else:
            return 'normal'
    
    def _find_related_queries(self, text: str, user_context: Optional[Dict[str, Any]]) -> List[str]:
        """Encontra consultas relacionadas"""
        # Por enquanto, retornar lista vazia
        # Futuramente, implementar busca em histórico
        return []


class QueryToSQLTranslator:
    """Tradutor de consultas para SQL"""
    
    def __init__(self):
        self.table_mappings = {
            'entregas': 'tb_entregas',
            'pedidos': 'tb_pedidos',
            'clientes': 'tb_clientes',
            'notas': 'tb_notas_fiscais',
        }
        
        self.field_mappings = {
            'cliente': 'nome_cliente',
            'data': 'data_entrega',
            'valor': 'valor_total',
            'status': 'status_entrega',
            'quantidade': 'quantidade',
        }
    
    def translate(self, intent: Intent, entities: List[Entity], context: Context) -> Optional[str]:
        """Traduz intenção e entidades para SQL"""
        try:
            # Determinar tabela principal
            table = self._determine_table(context.business_domain)
            
            # Construir cláusula SELECT
            select_clause = self._build_select_clause(intent)
            
            # Construir cláusula WHERE
            where_clause = self._build_where_clause(entities, context)
            
            # Construir cláusula GROUP BY (se necessário)
            group_clause = self._build_group_clause(intent)
            
            # Construir cláusula ORDER BY
            order_clause = self._build_order_clause(intent)
            
            # Montar SQL completo
            sql = f"SELECT {select_clause} FROM {table}"
            
            if where_clause:
                sql += f" WHERE {where_clause}"
            
            if group_clause:
                sql += f" GROUP BY {group_clause}"
            
            if order_clause:
                sql += f" ORDER BY {order_clause}"
            
            # Adicionar LIMIT para consultas de listagem
            if intent.type == IntentType.LIST:
                sql += " LIMIT 100"
            
            return sql
            
        except Exception as e:
            logger.error(f"Erro ao traduzir para SQL: {e}")
            return None
    
    def _determine_table(self, domain: str) -> str:
        """Determina tabela principal baseada no domínio"""
        return self.table_mappings.get(domain, 'tb_entregas')
    
    def _build_select_clause(self, intent: Intent) -> str:
        """Constrói cláusula SELECT"""
        if intent.type == IntentType.COUNT:
            return "COUNT(*) as total"
        elif intent.type == IntentType.SUM:
            return "SUM(valor_total) as valor_total"
        elif intent.type == IntentType.AVERAGE:
            return "AVG(valor_total) as valor_medio"
        else:
            return "*"
    
    def _build_where_clause(self, entities: List[Entity], context: Context) -> str:
        """Constrói cláusula WHERE"""
        conditions = []
        
        # Condições por entidades
        for entity in entities:
            if entity.type == EntityType.CLIENT:
                conditions.append(f"nome_cliente ILIKE '%{entity.value}%'")
            elif entity.type == EntityType.DATE and entity.normalized_value:
                conditions.append(f"data_entrega = '{entity.normalized_value}'")
            elif entity.type == EntityType.STATUS:
                conditions.append(f"status_entrega = '{entity.value}'")
        
        # Condições por filtros implícitos
        if 'status' in context.implicit_filters:
            if context.implicit_filters['status'] == 'delayed':
                conditions.append("status_entrega IN ('atrasado', 'pendente')")
            elif context.implicit_filters['status'] == 'completed':
                conditions.append("status_entrega = 'entregue'")
        
        # Condições temporais
        if context.temporal_scope['type'] == 'relative':
            days = context.temporal_scope['period']
            conditions.append(f"data_entrega >= CURRENT_DATE - INTERVAL '{days} days'")
        
        return " AND ".join(conditions)
    
    def _build_group_clause(self, intent: Intent) -> str:
        """Constrói cláusula GROUP BY"""
        if intent.type in [IntentType.COUNT, IntentType.SUM, IntentType.AVERAGE]:
            # Agrupar por cliente é comum
            return "nome_cliente"
        return ""
    
    def _build_order_clause(self, intent: Intent) -> str:
        """Constrói cláusula ORDER BY"""
        if intent.type == IntentType.RANKING:
            return "valor_total DESC"
        elif intent.type == IntentType.TREND:
            return "data_entrega ASC"
        else:
            return "data_entrega DESC"


class LearningEngine:
    """Motor de aprendizado contínuo"""
    
    def __init__(self):
        self.query_history = []
        self.pattern_frequency = defaultdict(int)
        self.entity_corrections = {}
        self.confidence_threshold = 0.8
    
    def record_query(self, query: str, intent: Intent, entities: List[Entity], 
                    confidence: float):
        """Registra consulta para aprendizado"""
        record = {
            'query': query,
            'intent': intent.type.value,
            'entities': [(e.text, e.type.value) for e in entities],
            'confidence': confidence,
            'timestamp': datetime.now()
        }
        
        self.query_history.append(record)
        
        # Atualizar frequência de padrões
        self._update_pattern_frequency(query, intent)
        
        # Aprender com consultas de alta confiança
        if confidence >= self.confidence_threshold:
            self._learn_from_success(query, intent, entities)
    
    def _update_pattern_frequency(self, query: str, intent: Intent):
        """Atualiza frequência de padrões"""
        pattern_key = f"{intent.type.value}:{len(query.split())}"
        self.pattern_frequency[pattern_key] += 1
    
    def _learn_from_success(self, query: str, intent: Intent, entities: List[Entity]):
        """Aprende com consultas bem-sucedidas"""
        # Armazenar padrões de sucesso para reutilização futura
        # Implementação simplificada - expandir conforme necessário
        pass
    
    def suggest_improvements(self, intent: Intent, confidence: float) -> List[str]:
        """Sugere melhorias baseadas no aprendizado"""
        suggestions = []
        
        if confidence < 0.6:
            # Sugerir padrões comuns para a intenção
            common_patterns = self._get_common_patterns(intent.type)
            if common_patterns:
                suggestions.append(f"Tente usar padrões como: {', '.join(common_patterns[:3])}")
        
        return suggestions
    
    def _get_common_patterns(self, intent_type: IntentType) -> List[str]:
        """Obtém padrões comuns para um tipo de intenção"""
        # Implementação simplificada
        patterns = {
            IntentType.COUNT: ["Quantas entregas", "Total de pedidos", "Número de"],
            IntentType.STATUS: ["Status do pedido", "Como está", "Situação da entrega"],
            IntentType.LIST: ["Liste todos", "Mostre as entregas", "Quais são"],
        }
        
        return patterns.get(intent_type, [])


# Função auxiliar para criar instância do motor
def create_nlp_engine() -> NLPEngine:
    """Cria e retorna uma instância do motor NLP"""
    return NLPEngine()


# Singleton global
_nlp_engine_instance = None

def get_nlp_engine() -> NLPEngine:
    """Retorna instância singleton do motor NLP"""
    global _nlp_engine_instance
    if _nlp_engine_instance is None:
        _nlp_engine_instance = create_nlp_engine()
    return _nlp_engine_instance
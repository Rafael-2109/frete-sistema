"""
Motor NLP principal para processamento de consultas em português
"""

import re
import unicodedata
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class ProcessedQuery:
    """Resultado do processamento de uma consulta"""
    original_query: str
    normalized_query: str
    tokens: List[str]
    intent: str
    confidence: float
    entities: Dict[str, Any]
    context: Dict[str, Any]
    sql_query: Optional[str] = None
    response_format: str = "table"
    suggestions: List[str] = field(default_factory=list)
    
class MCPNLPEngine:
    """Motor principal de processamento de linguagem natural"""
    
    def __init__(self):
        self.initialize_patterns()
        self.initialize_stopwords()
        self.query_history = []
        
    def initialize_patterns(self):
        """Inicializa padrões de reconhecimento"""
        # Padrões temporais
        self.temporal_patterns = {
            r'\bhoje\b': lambda: date.today(),
            r'\bontem\b': lambda: date.today() - timedelta(days=1),
            r'\bamanhã\b': lambda: date.today() + timedelta(days=1),
            r'\besta semana\b': lambda: 'current_week',
            r'\bsemana passada\b': lambda: 'last_week',
            r'\beste mês\b': lambda: 'current_month',
            r'\bmês passado\b': lambda: 'last_month',
            r'\búltimos? (\d+) dias?\b': lambda m: f'last_{m.group(1)}_days',
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})': lambda m: self._parse_date(m),
        }
        
        # Padrões de entidades
        self.entity_patterns = {
            'cnpj': r'\b\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}\b',
            'nf': r'\b(?:nf|nota fiscal|nfe?)\s*[:# ]?\s*(\d+)\b',
            'pedido': r'\b(?:pedido|ped\.?)\s*[:# ]?\s*(\w+)\b',
            'protocolo': r'\b(?:protocolo|prot\.?)\s*[:# ]?\s*(\w+)\b',
            'valor': r'R\$?\s*(\d+(?:\.\d{3})*(?:,\d{2})?)',
            'quantidade': r'\b(\d+)\s*(?:unidades?|kg|ton|pallets?|pal)\b',
            'percentual': r'\b(\d+(?:,\d+)?)\s*%',
            'uf': r'\b(?:SP|RJ|MG|ES|BA|SE|PE|AL|PB|RN|CE|PI|MA|PA|AM|RR|AP|AC|RO|MT|MS|GO|DF|SC|PR|RS|TO)\b',
        }
        
        # Palavras-chave por intenção
        self.intent_keywords = {
            'status': ['status', 'situação', 'como está', 'onde está', 'posição'],
            'buscar': ['buscar', 'procurar', 'encontrar', 'listar', 'mostrar', 'exibir'],
            'contar': ['quantos', 'quantas', 'quantidade', 'total', 'número'],
            'tendencia': ['tendência', 'evolução', 'crescimento', 'queda', 'variação'],
            'atraso': ['atrasado', 'atraso', 'pendente', 'vencido', 'fora do prazo'],
            'falha': ['falha', 'erro', 'problema', 'divergência', 'inconsistência'],
            'reagendar': ['reagendar', 'remarcar', 'alterar data', 'mudar data'],
            'desbloquear': ['desbloquear', 'liberar', 'autorizar', 'aprovar'],
        }
        
        # Mapeamento de campos
        self.field_mappings = {
            'cliente': ['cliente', 'cliente_nome', 'raz_social_red', 'nome_cliente'],
            'transportadora': ['transportadora', 'transportadora_nome', 'nome_transportadora'],
            'cidade': ['cidade', 'municipio', 'cidade_destino', 'nome_cidade'],
            'uf': ['uf', 'estado', 'cod_uf', 'uf_destino'],
            'valor': ['valor', 'valor_nf', 'valor_total', 'valor_frete'],
            'data': ['data', 'data_entrega', 'data_faturamento', 'data_embarque'],
        }
        
    def initialize_stopwords(self):
        """Inicializa stopwords em português"""
        self.stopwords = {
            'a', 'o', 'os', 'as', 'de', 'do', 'da', 'dos', 'das', 'em', 'no', 'na',
            'nos', 'nas', 'por', 'para', 'com', 'sem', 'sob', 'sobre', 'e', 'ou',
            'mas', 'que', 'qual', 'quais', 'um', 'uma', 'uns', 'umas', 'ao', 'aos',
            'à', 'às', 'pelo', 'pela', 'pelos', 'pelas', 'quando', 'como', 'se',
            'não', 'sim', 'este', 'esse', 'aquele', 'esta', 'essa', 'aquela'
        }
        
    def process_query(self, query: str, user_context: Optional[Dict] = None) -> ProcessedQuery:
        """Processa uma consulta em linguagem natural"""
        logger.info(f"Processando consulta: {query}")
        
        # Normaliza a consulta
        normalized = self.normalize_query(query)
        
        # Tokeniza
        tokens = self.tokenize(normalized)
        
        # Extrai entidades
        entities = self.extract_entities(query, normalized)
        
        # Classifica intenção
        intent, confidence = self.classify_intent(normalized, tokens, entities)
        
        # Analisa contexto
        context = self.analyze_context(normalized, entities, user_context)
        
        # Gera SQL se possível
        sql_query = self.generate_sql(intent, entities, context)
        
        # Determina formato de resposta
        response_format = self.determine_response_format(intent)
        
        # Gera sugestões
        suggestions = self.generate_suggestions(intent, entities)
        
        # Adiciona à história
        result = ProcessedQuery(
            original_query=query,
            normalized_query=normalized,
            tokens=tokens,
            intent=intent,
            confidence=confidence,
            entities=entities,
            context=context,
            sql_query=sql_query,
            response_format=response_format,
            suggestions=suggestions
        )
        
        self.query_history.append(result)
        
        return result
        
    def normalize_query(self, query: str) -> str:
        """Normaliza a consulta removendo acentos e padronizando"""
        # Converte para minúsculas
        query = query.lower()
        
        # Remove acentos (mantém ç)
        normalized = ''.join(
            c for c in unicodedata.normalize('NFD', query)
            if unicodedata.category(c) != 'Mn' or c == 'ç'
        )
        
        # Padroniza espaços
        normalized = ' '.join(normalized.split())
        
        # Expande abreviações comuns
        abbreviations = {
            'nf': 'nota fiscal',
            'cte': 'conhecimento transporte',
            'qtd': 'quantidade',
            'qtde': 'quantidade',
            'transp': 'transportadora',
            'ped': 'pedido',
            'prot': 'protocolo',
        }
        
        for abbr, full in abbreviations.items():
            normalized = re.sub(r'\b' + abbr + r'\b', full, normalized)
            
        return normalized
        
    def tokenize(self, text: str) -> List[str]:
        """Tokeniza o texto removendo stopwords"""
        # Divide em tokens
        tokens = re.findall(r'\b\w+\b', text.lower())
        
        # Remove stopwords
        tokens = [t for t in tokens if t not in self.stopwords]
        
        return tokens
        
    def extract_entities(self, original: str, normalized: str) -> Dict[str, Any]:
        """Extrai entidades da consulta"""
        entities = {}
        
        # Extrai datas
        dates = self.extract_temporal_entities(original)
        if dates:
            entities['temporal'] = dates
            
        # Extrai outras entidades usando padrões
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, original, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches[0] if len(matches) == 1 else matches
                
        # Extrai nomes de clientes/transportadoras (palavras capitalizadas)
        proper_nouns = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', original)
        if proper_nouns:
            entities['nomes_proprios'] = proper_nouns
            
        # Identifica localizações
        locations = self.extract_locations(original)
        if locations:
            entities['localizacoes'] = locations
            
        return entities
        
    def extract_temporal_entities(self, text: str) -> Dict[str, Any]:
        """Extrai referências temporais"""
        temporal = {}
        
        for pattern, handler in self.temporal_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = handler(match) if hasattr(handler, '__call__') and match.groups() else handler()
                temporal['expression'] = match.group(0)
                temporal['value'] = result
                temporal['type'] = self._classify_temporal_type(result)
                break
                
        return temporal
        
    def extract_locations(self, text: str) -> List[Dict[str, str]]:
        """Extrai localizações (cidades e estados)"""
        locations = []
        
        # Estados
        uf_matches = re.findall(self.entity_patterns['uf'], text.upper())
        for uf in uf_matches:
            locations.append({'tipo': 'estado', 'valor': uf})
            
        # Cidades conhecidas (seria carregado de um banco de dados)
        # Por enquanto, detecta padrões comuns
        cidade_pattern = r'\b(?:São Paulo|Rio de Janeiro|Belo Horizonte|Curitiba|Porto Alegre)\b'
        cidade_matches = re.findall(cidade_pattern, text, re.IGNORECASE)
        for cidade in cidade_matches:
            locations.append({'tipo': 'cidade', 'valor': cidade})
            
        return locations
        
    def classify_intent(self, normalized: str, tokens: List[str], entities: Dict) -> Tuple[str, float]:
        """Classifica a intenção da consulta"""
        intent_scores = defaultdict(float)
        
        # Pontuação baseada em palavras-chave
        for intent, keywords in self.intent_keywords.items():
            for keyword in keywords:
                if keyword in normalized:
                    intent_scores[intent] += 1.0
                    
        # Ajusta pontuação baseada em entidades
        if entities.get('temporal'):
            intent_scores['tendencia'] += 0.5
            
        if entities.get('nf') or entities.get('pedido'):
            intent_scores['status'] += 0.5
            
        if 'quantidade' in entities or 'quantos' in normalized or 'quantas' in normalized:
            intent_scores['contar'] += 1.0
            
        # Detecta ações que requerem confirmação
        if any(word in normalized for word in ['reagendar', 'alterar', 'mudar', 'cancelar']):
            intent_scores['acao_confirmacao'] = 2.0
            
        # Se não encontrou intenção clara, assume busca
        if not intent_scores:
            intent_scores['buscar'] = 1.0
            
        # Obtém intenção com maior pontuação
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        
        # Calcula confiança (normalizada entre 0 e 1)
        confidence = min(best_intent[1] / 3.0, 1.0)
        
        return best_intent[0], confidence
        
    def analyze_context(self, query: str, entities: Dict, user_context: Optional[Dict]) -> Dict:
        """Analisa o contexto da consulta"""
        context = {
            'timestamp': datetime.now(),
            'query_length': len(query),
            'entity_count': len(entities),
            'has_temporal': 'temporal' in entities,
            'has_location': 'localizacoes' in entities or 'uf' in entities,
            'has_value': 'valor' in entities or 'quantidade' in entities,
        }
        
        # Adiciona contexto do usuário se disponível
        if user_context:
            context['user'] = user_context
            
        # Detecta urgência
        urgency_words = ['urgente', 'rapido', 'agora', 'imediato', 'hoje']
        context['urgency'] = any(word in query for word in urgency_words)
        
        # Detecta domínio
        if any(word in query for word in ['entrega', 'entregar', 'entregue']):
            context['domain'] = 'entregas'
        elif any(word in query for word in ['frete', 'transporte', 'transportadora']):
            context['domain'] = 'fretes'
        elif any(word in query for word in ['pedido', 'compra', 'venda']):
            context['domain'] = 'pedidos'
        elif any(word in query for word in ['embarque', 'embarcar', 'carga']):
            context['domain'] = 'embarques'
        else:
            context['domain'] = 'geral'
            
        return context
        
    def generate_sql(self, intent: str, entities: Dict, context: Dict) -> Optional[str]:
        """Gera consulta SQL baseada na intenção e entidades"""
        # Mapeia domínio para tabela
        domain_table_map = {
            'entregas': 'entregas_monitoradas',
            'fretes': 'fretes',
            'pedidos': 'pedidos',
            'embarques': 'embarques',
            'geral': 'entregas_monitoradas'  # default
        }
        
        table = domain_table_map.get(context.get('domain', 'geral'))
        
        # Constrói SQL baseado na intenção
        if intent == 'contar':
            sql = f"SELECT COUNT(*) FROM {table}"
        elif intent == 'buscar':
            sql = f"SELECT * FROM {table}"
        elif intent == 'status':
            sql = f"SELECT numero_nf, cliente, status, data_entrega_prevista FROM {table}"
        else:
            return None
            
        # Adiciona condições WHERE baseadas em entidades
        conditions = []
        
        # Condições temporais
        if entities.get('temporal'):
            temporal = entities['temporal']
            if temporal['type'] == 'date':
                conditions.append(f"DATE(criado_em) = '{temporal['value']}'")
            elif temporal['value'] == 'current_week':
                conditions.append("DATE(criado_em) >= DATE('now', '-7 days')")
                
        # Condições de cliente
        if entities.get('nomes_proprios'):
            nome = entities['nomes_proprios'][0] if isinstance(entities['nomes_proprios'], list) else entities['nomes_proprios']
            conditions.append(f"cliente ILIKE '%{nome}%'")
            
        # Condições de localização
        if entities.get('uf'):
            uf = entities['uf'][0] if isinstance(entities['uf'], list) else entities['uf']
            conditions.append(f"uf = '{uf}'")
            
        # Condições de status para atrasos
        if intent == 'atraso':
            conditions.append("data_entrega_prevista < CURRENT_DATE AND entregue = FALSE")
            
        # Adiciona WHERE se houver condições
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
            
        # Adiciona ORDER BY e LIMIT
        if intent == 'buscar':
            sql += " ORDER BY criado_em DESC LIMIT 100"
            
        return sql
        
    def determine_response_format(self, intent: str) -> str:
        """Determina o formato de resposta baseado na intenção"""
        format_map = {
            'contar': 'single_value',
            'status': 'card',
            'buscar': 'table',
            'tendencia': 'chart',
            'atraso': 'alert_list',
            'acao_confirmacao': 'confirmation_dialog'
        }
        
        return format_map.get(intent, 'table')
        
    def generate_suggestions(self, intent: str, entities: Dict) -> List[str]:
        """Gera sugestões baseadas no contexto"""
        suggestions = []
        
        if intent == 'status' and entities.get('nomes_proprios'):
            cliente = entities['nomes_proprios'][0]
            suggestions.extend([
                f"Ver todos os pedidos de {cliente}",
                f"Histórico de entregas de {cliente}",
                f"Pendências financeiras de {cliente}"
            ])
            
        elif intent == 'atraso':
            suggestions.extend([
                "Agrupar atrasos por transportadora",
                "Ver motivos dos atrasos",
                "Exportar relatório de atrasos"
            ])
            
        elif intent == 'contar':
            suggestions.extend([
                "Ver detalhes dos itens contados",
                "Comparar com período anterior",
                "Gerar gráfico de evolução"
            ])
            
        return suggestions[:3]  # Limita a 3 sugestões
        
    def _parse_date(self, match) -> date:
        """Analisa data no formato brasileiro"""
        day, month, year = match.groups()
        if len(year) == 2:
            year = '20' + year
        return date(int(year), int(month), int(day))
        
    def _classify_temporal_type(self, value) -> str:
        """Classifica o tipo de expressão temporal"""
        if isinstance(value, date):
            return 'date'
        elif isinstance(value, str) and value.startswith('last_'):
            return 'period'
        elif value in ['current_week', 'last_week', 'current_month', 'last_month']:
            return 'range'
        else:
            return 'unknown'
            
    def learn_from_feedback(self, query_id: str, feedback: Dict):
        """Aprende com o feedback do usuário"""
        # Encontra a consulta no histórico
        for query in self.query_history:
            if id(query) == query_id:
                # Ajusta confiança baseada no feedback
                if feedback.get('correct_intent'):
                    # Reforça padrões que levaram à classificação correta
                    logger.info(f"Aprendendo: consulta '{query.original_query}' teve intenção correta")
                else:
                    # Aprende com o erro
                    correct_intent = feedback.get('actual_intent')
                    if correct_intent:
                        logger.info(f"Aprendendo: consulta '{query.original_query}' deveria ter intenção '{correct_intent}'")
                        
                break
# NLP Utilities for Text Processing
import re
import unicodedata
from typing import List, Dict, Tuple, Optional, Set
from collections import Counter
import string
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class NLPUtils:
    """Natural Language Processing utilities for freight system"""
    
    def __init__(self):
        self.stopwords = self._load_portuguese_stopwords()
        self.freight_terms = self._load_freight_terminology()
        self.abbreviations = self._load_abbreviations()
        
    def _load_portuguese_stopwords(self) -> Set[str]:
        """Load Portuguese stopwords"""
        return set([
            'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'é', 'com',
            'não', 'uma', 'os', 'no', 'se', 'na', 'por', 'mais', 'as', 'dos',
            'como', 'mas', 'foi', 'ao', 'ele', 'das', 'tem', 'à', 'seu', 'sua',
            'ou', 'ser', 'quando', 'muito', 'há', 'nos', 'já', 'está', 'eu',
            'também', 'só', 'pelo', 'pela', 'até', 'isso', 'ela', 'entre',
            'era', 'depois', 'sem', 'mesmo', 'aos', 'ter', 'seus', 'quem',
            'nas', 'me', 'esse', 'eles', 'estão', 'você', 'tinha', 'foram',
            'essa', 'num', 'nem', 'suas', 'meu', 'às', 'minha', 'têm', 'numa',
            'pelos', 'elas', 'havia', 'seja', 'qual', 'será', 'nós', 'tenho',
            'lhe', 'deles', 'essas', 'esses', 'pelas', 'este', 'fosse', 'dele',
            'tu', 'te', 'vocês', 'vos', 'lhes', 'meus', 'minhas', 'teu', 'tua',
            'teus', 'tuas', 'nosso', 'nossa', 'nossos', 'nossas', 'dela',
            'delas', 'esta', 'estes', 'estas', 'aquele', 'aquela', 'aqueles',
            'aquelas', 'isto', 'aquilo', 'estou', 'está', 'estamos', 'estão',
            'estive', 'esteve', 'estivemos', 'estiveram', 'estava', 'estávamos',
            'estavam', 'estivera', 'estivéramos', 'esteja', 'estejamos',
            'estejam', 'estivesse', 'estivéssemos', 'estivessem', 'estiver',
            'estivermos', 'estiverem'
        ])
        
    def _load_freight_terminology(self) -> Dict[str, List[str]]:
        """Load freight-specific terminology"""
        return {
            'actions': [
                'criar', 'cadastrar', 'registrar', 'adicionar', 'incluir',
                'atualizar', 'modificar', 'alterar', 'mudar', 'editar',
                'deletar', 'remover', 'excluir', 'apagar', 'cancelar',
                'consultar', 'buscar', 'procurar', 'listar', 'ver',
                'calcular', 'gerar', 'processar', 'analisar', 'verificar'
            ],
            'entities': [
                'frete', 'pedido', 'transporte', 'carga', 'entrega',
                'rota', 'trajeto', 'caminho', 'percurso', 'viagem',
                'motorista', 'condutor', 'transportador', 'cliente',
                'remetente', 'destinatário', 'empresa', 'fornecedor'
            ],
            'attributes': [
                'status', 'situação', 'estado', 'valor', 'preço',
                'custo', 'distância', 'tempo', 'prazo', 'data',
                'origem', 'destino', 'saída', 'chegada', 'peso',
                'volume', 'dimensão', 'tipo', 'categoria', 'prioridade'
            ],
            'statuses': [
                'pendente', 'aguardando', 'processando', 'confirmado',
                'em trânsito', 'em rota', 'em transporte', 'a caminho',
                'entregue', 'finalizado', 'concluído', 'completo',
                'cancelado', 'anulado', 'suspenso', 'atrasado'
            ]
        }
        
    def _load_abbreviations(self) -> Dict[str, str]:
        """Load common abbreviations"""
        return {
            'sp': 'são paulo',
            'rj': 'rio de janeiro',
            'mg': 'minas gerais',
            'rs': 'rio grande do sul',
            'pr': 'paraná',
            'sc': 'santa catarina',
            'ba': 'bahia',
            'pe': 'pernambuco',
            'ce': 'ceará',
            'go': 'goiás',
            'df': 'distrito federal',
            'km': 'quilômetros',
            'kg': 'quilogramas',
            'ton': 'toneladas',
            'hrs': 'horas',
            'min': 'minutos',
            'seg': 'segundos',
            'qtd': 'quantidade',
            'obs': 'observação',
            'end': 'endereço',
            'tel': 'telefone',
            'cpf': 'cadastro de pessoa física',
            'cnpj': 'cadastro nacional de pessoa jurídica',
            'nf': 'nota fiscal',
            'cte': 'conhecimento de transporte eletrônico'
        }
        
    def preprocess_text(self, text: str, 
                       remove_stopwords: bool = False,
                       expand_abbreviations: bool = True,
                       normalize_accents: bool = True) -> str:
        """Preprocess text for analysis"""
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Expand abbreviations
        if expand_abbreviations:
            text = self._expand_abbreviations(text)
            
        # Normalize accents
        if normalize_accents:
            text = self._normalize_accents(text)
            
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove stopwords
        if remove_stopwords:
            text = self._remove_stopwords(text)
            
        return text
        
    def _expand_abbreviations(self, text: str) -> str:
        """Expand known abbreviations"""
        for abbr, full in self.abbreviations.items():
            # Match abbreviation with word boundaries
            pattern = r'\b' + re.escape(abbr) + r'\b'
            text = re.sub(pattern, full, text, flags=re.IGNORECASE)
        return text
        
    def _normalize_accents(self, text: str) -> str:
        """Remove accents from text"""
        # Decompose unicode characters
        nfd_form = unicodedata.normalize('NFD', text)
        # Filter out accent marks
        return ''.join(char for char in nfd_form if unicodedata.category(char) != 'Mn')
        
    def _remove_stopwords(self, text: str) -> str:
        """Remove stopwords from text"""
        words = text.split()
        filtered_words = [word for word in words if word not in self.stopwords]
        return ' '.join(filtered_words)
        
    def tokenize(self, text: str, 
                 keep_punctuation: bool = False) -> List[str]:
        """Tokenize text into words"""
        if not keep_punctuation:
            # Remove punctuation
            text = text.translate(str.maketrans('', '', string.punctuation))
            
        # Split into words
        tokens = text.split()
        
        return [token for token in tokens if token]
        
    def extract_keywords(self, text: str, 
                        max_keywords: int = 10,
                        use_freight_terms: bool = True) -> List[Tuple[str, float]]:
        """Extract keywords from text"""
        # Preprocess text
        processed = self.preprocess_text(text, remove_stopwords=True)
        tokens = self.tokenize(processed)
        
        # Count word frequencies
        word_freq = Counter(tokens)
        
        # Boost freight-related terms
        if use_freight_terms:
            for token in tokens:
                for category, terms in self.freight_terms.items():
                    if token in terms:
                        word_freq[token] *= 2  # Double the weight
                        
        # Get top keywords with normalized scores
        total = sum(word_freq.values())
        keywords = [
            (word, count / total) 
            for word, count in word_freq.most_common(max_keywords)
        ]
        
        return keywords
        
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        # Preprocess texts
        proc1 = self.preprocess_text(text1, remove_stopwords=True)
        proc2 = self.preprocess_text(text2, remove_stopwords=True)
        
        # Tokenize
        tokens1 = set(self.tokenize(proc1))
        tokens2 = set(self.tokenize(proc2))
        
        # Calculate Jaccard similarity
        if not tokens1 or not tokens2:
            return 0.0
            
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union)
        
    def extract_ngrams(self, text: str, n: int = 2) -> List[str]:
        """Extract n-grams from text"""
        tokens = self.tokenize(text)
        
        if len(tokens) < n:
            return []
            
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = ' '.join(tokens[i:i+n])
            ngrams.append(ngram)
            
        return ngrams
        
    def detect_language(self, text: str) -> str:
        """Simple language detection (Portuguese vs English)"""
        portuguese_indicators = [
            'ção', 'ões', 'ão', 'ãe', 'ça', 'ço', 'nh', 'lh',
            'que', 'não', 'com', 'para', 'uma', 'por'
        ]
        
        english_indicators = [
            'the', 'and', 'for', 'with', 'that', 'this',
            'tion', 'ing', 'ed', 'er', 'ly'
        ]
        
        text_lower = text.lower()
        
        pt_score = sum(1 for indicator in portuguese_indicators if indicator in text_lower)
        en_score = sum(1 for indicator in english_indicators if indicator in text_lower)
        
        return 'pt' if pt_score > en_score else 'en'
        
    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting for Portuguese
        sentence_endings = r'[.!?]+'
        sentences = re.split(sentence_endings, text)
        
        # Clean and filter sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
        
    def extract_numbers(self, text: str) -> List[Tuple[str, float]]:
        """Extract numbers from text"""
        # Pattern for various number formats
        number_pattern = r'(\d+(?:[.,]\d+)?)'
        
        numbers = []
        for match in re.finditer(number_pattern, text):
            number_str = match.group(1)
            # Convert to float (handle Brazilian decimal format)
            number_float = float(number_str.replace(',', '.'))
            numbers.append((number_str, number_float))
            
        return numbers
        
    def clean_text(self, text: str) -> str:
        """Deep clean text for processing"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove special characters but keep Portuguese characters
        text = re.sub(r'[^\w\sáàâãéèêíïóôõöúçñÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]', ' ', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
        
    def get_text_stats(self, text: str) -> Dict[str, Any]:
        """Get statistics about the text"""
        tokens = self.tokenize(text)
        sentences = self.split_sentences(text)
        
        return {
            'char_count': len(text),
            'word_count': len(tokens),
            'sentence_count': len(sentences),
            'avg_word_length': sum(len(word) for word in tokens) / len(tokens) if tokens else 0,
            'avg_sentence_length': len(tokens) / len(sentences) if sentences else 0,
            'unique_words': len(set(tokens)),
            'lexical_diversity': len(set(tokens)) / len(tokens) if tokens else 0,
            'language': self.detect_language(text)
        }
        
    def fuzzy_match(self, text: str, pattern: str, threshold: float = 0.8) -> bool:
        """Fuzzy string matching"""
        # Simple character-based similarity
        text = text.lower()
        pattern = pattern.lower()
        
        # If pattern is in text, it's a match
        if pattern in text:
            return True
            
        # Calculate similarity
        similarity = self.calculate_similarity(text, pattern)
        
        return similarity >= threshold
        
    def extract_context_window(self, text: str, keyword: str, 
                             window_size: int = 50) -> List[str]:
        """Extract context windows around keyword"""
        contexts = []
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        # Find all occurrences
        start = 0
        while True:
            pos = text_lower.find(keyword_lower, start)
            if pos == -1:
                break
                
            # Extract context window
            context_start = max(0, pos - window_size)
            context_end = min(len(text), pos + len(keyword) + window_size)
            
            context = text[context_start:context_end]
            contexts.append(context)
            
            start = pos + 1
            
        return contexts
"""
Embeddings generator for semantic similarity
Uses multiple strategies for generating text embeddings
"""

import hashlib
import json
from typing import List, Optional, Union, Dict, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import logging
import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generates embeddings for semantic similarity search
    Uses TF-IDF with LSA as a lightweight alternative to transformer models
    """
    
    def __init__(
        self,
        embedding_dim: int = 128,
        max_features: int = 5000,
        use_cache: bool = True
    ):
        self.embedding_dim = embedding_dim
        self.max_features = max_features
        self.use_cache = use_cache
        
        # TF-IDF vectorizer for text features
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 3),
            min_df=1,
            max_df=0.95,
            sublinear_tf=True,
            use_idf=True
        )
        
        # LSA for dimensionality reduction
        self.lsa = TruncatedSVD(
            n_components=embedding_dim,
            algorithm='randomized',
            n_iter=5,
            random_state=42
        )
        
        # Document corpus for fitting
        self.document_corpus: List[str] = []
        self.is_fitted = False
        
        # Embedding cache
        self._embedding_cache: Dict[str, np.ndarray] = {}
        
        # Domain-specific vocabulary
        self._initialize_domain_vocabulary()
        
    def _initialize_domain_vocabulary(self):
        """Initialize freight domain-specific vocabulary"""
        self.domain_terms = {
            # Logistics terms
            "frete": ["frete", "freight", "transporte", "shipping"],
            "pedido": ["pedido", "order", "ordem", "encomenda"],
            "cliente": ["cliente", "client", "customer", "comprador"],
            "produto": ["produto", "product", "item", "mercadoria"],
            "entrega": ["entrega", "delivery", "envio", "despacho"],
            "embarque": ["embarque", "shipment", "carga", "remessa"],
            
            # Actions
            "calcular": ["calcular", "calculate", "computar", "estimar"],
            "gerar": ["gerar", "generate", "criar", "produzir"],
            "consultar": ["consultar", "query", "pesquisar", "buscar"],
            "aprovar": ["aprovar", "approve", "autorizar", "validar"],
            
            # Status
            "pendente": ["pendente", "pending", "aguardando", "esperando"],
            "confirmado": ["confirmado", "confirmed", "aprovado", "validado"],
            "cancelado": ["cancelado", "cancelled", "anulado", "rejeitado"],
            
            # Measurements
            "peso": ["peso", "weight", "kg", "quilos", "tonelada"],
            "volume": ["volume", "m3", "cubagem", "metros cubicos"],
            "valor": ["valor", "value", "preco", "custo", "total"],
            
            # Locations
            "origem": ["origem", "origin", "saida", "partida"],
            "destino": ["destino", "destination", "chegada", "entrega"],
            "rota": ["rota", "route", "trajeto", "caminho"],
            "regiao": ["regiao", "region", "area", "zona"]
        }
        
    async def generate(
        self,
        text: Union[str, List[str]],
        use_domain_expansion: bool = True
    ) -> np.ndarray:
        """
        Generate embedding for text
        
        Args:
            text: Input text or list of texts
            use_domain_expansion: Whether to expand with domain terms
            
        Returns:
            Embedding vector
        """
        # Handle list input
        if isinstance(text, list):
            text = " ".join(text)
            
        # Normalize text
        text = self._normalize_text(text)
        
        # Check cache
        if self.use_cache:
            cache_key = self._get_cache_key(text)
            if cache_key in self._embedding_cache:
                return self._embedding_cache[cache_key]
                
        # Expand with domain terms if requested
        if use_domain_expansion:
            text = self._expand_with_domain_terms(text)
            
        # Generate embedding
        if not self.is_fitted:
            # Use simple hashing for cold start
            embedding = self._generate_hash_embedding(text)
        else:
            # Use fitted TF-IDF + LSA
            embedding = await self._generate_tfidf_embedding(text)
            
        # Normalize embedding
        embedding = self._normalize_embedding(embedding)
        
        # Cache result
        if self.use_cache:
            self._embedding_cache[cache_key] = embedding
            
        return embedding
        
    async def generate_batch(
        self,
        texts: List[str],
        use_domain_expansion: bool = True
    ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts
            use_domain_expansion: Whether to expand with domain terms
            
        Returns:
            List of embedding vectors
        """
        tasks = [
            self.generate(text, use_domain_expansion)
            for text in texts
        ]
        
        embeddings = await asyncio.gather(*tasks)
        return embeddings
        
    async def fit(self, corpus: List[str], min_documents: int = 100):
        """
        Fit the vectorizer on a corpus
        
        Args:
            corpus: List of documents
            min_documents: Minimum documents needed for fitting
        """
        # Add to document corpus
        self.document_corpus.extend(corpus)
        
        # Only fit if we have enough documents
        if len(self.document_corpus) >= min_documents:
            logger.info(f"Fitting embeddings on {len(self.document_corpus)} documents")
            
            # Normalize corpus
            normalized_corpus = [
                self._normalize_text(doc) for doc in self.document_corpus
            ]
            
            # Fit TF-IDF
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(normalized_corpus)
            
            # Fit LSA
            self.lsa.fit(tfidf_matrix)
            
            self.is_fitted = True
            logger.info("Embedding model fitted successfully")
            
    def calculate_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
        metric: str = "cosine"
    ) -> float:
        """
        Calculate similarity between embeddings
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            metric: Similarity metric (cosine, euclidean, manhattan)
            
        Returns:
            Similarity score
        """
        if metric == "cosine":
            # Cosine similarity
            dot_product = np.dot(embedding1, embedding2)
            norm_product = np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            if norm_product == 0:
                return 0.0
            return float(dot_product / norm_product)
            
        elif metric == "euclidean":
            # Euclidean distance (inverted for similarity)
            distance = np.linalg.norm(embedding1 - embedding2)
            return float(1 / (1 + distance))
            
        elif metric == "manhattan":
            # Manhattan distance (inverted for similarity)
            distance = np.sum(np.abs(embedding1 - embedding2))
            return float(1 / (1 + distance))
            
        else:
            raise ValueError(f"Unknown metric: {metric}")
            
    def find_similar(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: List[np.ndarray],
        top_k: int = 5,
        min_similarity: float = 0.5
    ) -> List[Tuple[int, float]]:
        """
        Find most similar embeddings
        
        Args:
            query_embedding: Query embedding
            candidate_embeddings: List of candidate embeddings
            top_k: Number of top results
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of (index, similarity) tuples
        """
        similarities = []
        
        for idx, candidate in enumerate(candidate_embeddings):
            similarity = self.calculate_similarity(query_embedding, candidate)
            if similarity >= min_similarity:
                similarities.append((idx, similarity))
                
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get embedding generator statistics"""
        return {
            "is_fitted": self.is_fitted,
            "embedding_dim": self.embedding_dim,
            "max_features": self.max_features,
            "corpus_size": len(self.document_corpus),
            "cache_size": len(self._embedding_cache),
            "domain_terms": len(self.domain_terms)
        }
        
    # Private helper methods
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for embedding"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = " ".join(text.split())
        
        # Remove special characters but keep important ones
        # Keep: letters, numbers, spaces, and some punctuation
        import re
        text = re.sub(r'[^a-zA-Z0-9\s\-\.\,]', ' ', text)
        
        return text.strip()
        
    def _expand_with_domain_terms(self, text: str) -> str:
        """Expand text with domain-specific synonyms"""
        expanded_text = text
        
        for concept, synonyms in self.domain_terms.items():
            for synonym in synonyms:
                if synonym in text.lower():
                    # Add related terms to enhance embedding
                    related_terms = [s for s in synonyms if s != synonym]
                    if related_terms:
                        expanded_text += " " + " ".join(related_terms[:2])
                    break
                    
        return expanded_text
        
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(text.encode()).hexdigest()
        
    def _generate_hash_embedding(self, text: str) -> np.ndarray:
        """Generate simple hash-based embedding for cold start"""
        # Use multiple hash functions for better distribution
        embedding = np.zeros(self.embedding_dim)
        
        # Character-level features
        for i, char in enumerate(text):
            idx = (ord(char) * (i + 1)) % self.embedding_dim
            embedding[idx] += 1
            
        # Word-level features
        words = text.split()
        for i, word in enumerate(words):
            word_hash = sum(ord(c) for c in word)
            idx = (word_hash * (i + 1)) % self.embedding_dim
            embedding[idx] += len(word)
            
        # N-gram features
        for n in range(2, 4):
            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i:i+n])
                ngram_hash = sum(ord(c) for c in ngram)
                idx = ngram_hash % self.embedding_dim
                embedding[idx] += 0.5
                
        return embedding
        
    async def _generate_tfidf_embedding(self, text: str) -> np.ndarray:
        """Generate TF-IDF based embedding"""
        try:
            # Transform text to TF-IDF
            tfidf_vector = self.tfidf_vectorizer.transform([text])
            
            # Apply LSA for dimensionality reduction
            embedding = self.lsa.transform(tfidf_vector)[0]
            
            return embedding
            
        except Exception as e:
            logger.warning(f"Error generating TF-IDF embedding: {e}")
            # Fall back to hash embedding
            return self._generate_hash_embedding(text)
            
    def _normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """Normalize embedding to unit length"""
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return embedding / norm
        return embedding
        
    def save_model(self, path: str):
        """Save fitted model to disk"""
        import pickle
        
        model_data = {
            "tfidf_vectorizer": self.tfidf_vectorizer,
            "lsa": self.lsa,
            "is_fitted": self.is_fitted,
            "document_corpus": self.document_corpus,
            "embedding_dim": self.embedding_dim,
            "max_features": self.max_features
        }
        
        with open(path, "wb") as f:
            pickle.dump(model_data, f)
            
        logger.info(f"Model saved to {path}")
        
    def load_model(self, path: str):
        """Load fitted model from disk"""
        import pickle
        
        with open(path, "rb") as f:
            model_data = pickle.load(f)
            
        self.tfidf_vectorizer = model_data["tfidf_vectorizer"]
        self.lsa = model_data["lsa"]
        self.is_fitted = model_data["is_fitted"]
        self.document_corpus = model_data["document_corpus"]
        self.embedding_dim = model_data["embedding_dim"]
        self.max_features = model_data["max_features"]
        
        logger.info(f"Model loaded from {path}")
        
    def clear_cache(self):
        """Clear embedding cache"""
        self._embedding_cache.clear()
        logger.info("Embedding cache cleared")
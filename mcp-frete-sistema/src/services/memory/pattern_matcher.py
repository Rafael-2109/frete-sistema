"""
Pattern Matcher for intelligent pattern recognition and matching
Uses machine learning to identify and learn from patterns in queries and data
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """Represents a learned pattern"""
    id: str
    pattern_type: str  # regex, semantic, structural, behavioral
    pattern_value: Any
    confidence: float = 1.0
    support: int = 1
    examples: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def matches(self, text: str) -> bool:
        """Check if pattern matches given text"""
        if self.pattern_type == "regex":
            return bool(re.search(self.pattern_value, text, re.IGNORECASE))
        elif self.pattern_type == "keyword":
            return self.pattern_value.lower() in text.lower()
        return False


@dataclass
class PatternMatch:
    """Result of pattern matching"""
    pattern: Pattern
    matched_text: str
    score: float
    context: Dict[str, Any] = field(default_factory=dict)


class PatternMatcher:
    """
    Intelligent pattern matcher with learning capabilities
    """
    
    def __init__(self):
        # Pattern storage
        self.patterns: Dict[str, Pattern] = {}
        self.pattern_index: Dict[str, List[str]] = defaultdict(list)
        
        # Pattern types and their extractors
        self.pattern_extractors = {
            "date": self._extract_date_patterns,
            "numeric": self._extract_numeric_patterns,
            "entity": self._extract_entity_patterns,
            "action": self._extract_action_patterns,
            "structural": self._extract_structural_patterns
        }
        
        # Semantic pattern matcher
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 3),
            min_df=2
        )
        self.semantic_patterns: List[Tuple[str, np.ndarray]] = []
        
        # Pattern learning parameters
        self.min_support = 2  # Minimum occurrences to learn pattern
        self.confidence_threshold = 0.7
        
        # Pre-compiled regex patterns
        self._compile_base_patterns()
        
    def _compile_base_patterns(self):
        """Compile base regex patterns"""
        self.base_patterns = {
            "date": [
                r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
                r'\b\d{4}-\d{2}-\d{2}\b',
                r'\b(?:hoje|amanhã|ontem)\b',
                r'\b(?:segunda|terça|quarta|quinta|sexta|sábado|domingo)\b'
            ],
            "time": [
                r'\b\d{1,2}:\d{2}(?::\d{2})?\b',
                r'\b\d{1,2}h\d{0,2}\b'
            ],
            "numeric": [
                r'\b\d+(?:\.\d+)?\s*(?:kg|ton|km|m|un|cx|pc)\b',
                r'\bR\$\s*\d+(?:\.\d{3})*(?:,\d{2})?\b',
                r'\b\d+(?:\.\d+)?%\b'
            ],
            "code": [
                r'\b[A-Z]{2,4}\d{4,8}\b',  # Product codes
                r'\b\d{11}\b',  # CPF
                r'\b\d{14}\b',  # CNPJ
                r'\b[A-Z]{3}-\d{4}\b'  # License plates
            ],
            "entity": [
                r'\b(?:cliente|fornecedor|transportadora|motorista)\s+[\w\s]+\b',
                r'\b(?:pedido|nota|fatura|embarque)\s*(?:n[º°]?\s*)?\d+\b'
            ]
        }
        
    async def learn_pattern(
        self,
        text: str,
        pattern_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Pattern]:
        """
        Learn patterns from text
        
        Args:
            text: Text to learn from
            pattern_type: Type of pattern to extract
            context: Additional context
            
        Returns:
            List of learned patterns
        """
        learned_patterns = []
        
        if pattern_type in self.pattern_extractors:
            patterns = self.pattern_extractors[pattern_type](text, context)
            
            for pattern_data in patterns:
                pattern_id = f"{pattern_type}:{pattern_data['value']}"
                
                if pattern_id in self.patterns:
                    # Update existing pattern
                    existing = self.patterns[pattern_id]
                    existing.support += 1
                    existing.examples.append(text[:100])  # Store snippet
                    existing.confidence = min(1.0, existing.confidence + 0.05)
                else:
                    # Create new pattern
                    pattern = Pattern(
                        id=pattern_id,
                        pattern_type=pattern_type,
                        pattern_value=pattern_data['value'],
                        confidence=pattern_data.get('confidence', 0.7),
                        examples=[text[:100]],
                        metadata=pattern_data.get('metadata', {})
                    )
                    self.patterns[pattern_id] = pattern
                    self.pattern_index[pattern_type].append(pattern_id)
                    learned_patterns.append(pattern)
                    
        # Learn semantic patterns
        if len(self.semantic_patterns) > 10:  # Need enough examples
            await self._learn_semantic_patterns(text)
            
        logger.info(f"Learned {len(learned_patterns)} new patterns from text")
        return learned_patterns
        
    async def match_patterns(
        self,
        text: str,
        pattern_types: Optional[List[str]] = None,
        min_confidence: float = 0.5
    ) -> List[PatternMatch]:
        """
        Match patterns in text
        
        Args:
            text: Text to match against
            pattern_types: Specific pattern types to match
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of pattern matches
        """
        matches = []
        types_to_check = pattern_types or list(self.pattern_extractors.keys())
        
        # Match regex patterns
        for pattern_type in types_to_check:
            if pattern_type in self.base_patterns:
                for regex_pattern in self.base_patterns[pattern_type]:
                    for match in re.finditer(regex_pattern, text, re.IGNORECASE):
                        pattern_match = PatternMatch(
                            pattern=Pattern(
                                id=f"base:{pattern_type}:{regex_pattern}",
                                pattern_type="regex",
                                pattern_value=regex_pattern
                            ),
                            matched_text=match.group(),
                            score=1.0,
                            context={"start": match.start(), "end": match.end()}
                        )
                        matches.append(pattern_match)
                        
        # Match learned patterns
        for pattern_id in self.pattern_index.get(pattern_type, []):
            pattern = self.patterns[pattern_id]
            if pattern.confidence >= min_confidence:
                if pattern.matches(text):
                    pattern_match = PatternMatch(
                        pattern=pattern,
                        matched_text=text,  # Could be more specific
                        score=pattern.confidence
                    )
                    matches.append(pattern_match)
                    
        # Match semantic patterns
        semantic_matches = await self._match_semantic_patterns(text, min_confidence)
        matches.extend(semantic_matches)
        
        # Sort by score
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches
        
    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> Dict[str, List[str]]:
        """
        Extract entities from text
        
        Args:
            text: Text to extract from
            entity_types: Specific entity types to extract
            
        Returns:
            Dictionary of entity type to list of entities
        """
        entities = defaultdict(list)
        
        # Extract using regex patterns
        entity_patterns = {
            "produto": r'\b(?:produto|item|mercadoria)\s*(?:código\s*)?([A-Z0-9]+)\b',
            "cliente": r'\b(?:cliente|comprador)\s*(?::\s*)?([\w\s]+?)(?:\s*-|\s*,|\s*\.|\s*$)',
            "pedido": r'\b(?:pedido|ordem)\s*(?:n[º°]?\s*)?(\d+)\b',
            "nota_fiscal": r'\b(?:NF|nota\s*fiscal)\s*(?:n[º°]?\s*)?(\d+)\b',
            "transportadora": r'\b(?:transportadora|transp\.?)\s*(?::\s*)?([\w\s]+?)(?:\s*-|\s*,|\s*\.|\s*$)',
            "cidade": r'\b(?:cidade|município)\s*(?::\s*)?([\w\s]+?)(?:\s*-|\s*,|\s*\.|\s*$)',
            "valor": r'\bR\$\s*(\d+(?:\.\d{3})*(?:,\d{2})?)\b',
            "peso": r'\b(\d+(?:,\d+)?)\s*(kg|ton|toneladas?)\b',
            "data": r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b'
        }
        
        types_to_extract = entity_types or list(entity_patterns.keys())
        
        for entity_type in types_to_extract:
            if entity_type in entity_patterns:
                pattern = entity_patterns[entity_type]
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entity_value = match.group(1).strip()
                    if entity_value and entity_value not in entities[entity_type]:
                        entities[entity_type].append(entity_value)
                        
        # Extract using learned patterns
        for pattern_id, pattern in self.patterns.items():
            if pattern.pattern_type == "entity" and pattern.confidence > 0.7:
                if pattern.matches(text):
                    entity_type = pattern.metadata.get("entity_type", "unknown")
                    entities[entity_type].append(pattern.pattern_value)
                    
        return dict(entities)
        
    async def find_similar_patterns(
        self,
        pattern: Pattern,
        top_k: int = 5
    ) -> List[Tuple[Pattern, float]]:
        """
        Find similar patterns
        
        Args:
            pattern: Reference pattern
            top_k: Number of similar patterns to return
            
        Returns:
            List of (pattern, similarity_score) tuples
        """
        similar_patterns = []
        
        for other_id, other_pattern in self.patterns.items():
            if other_id != pattern.id and other_pattern.pattern_type == pattern.pattern_type:
                # Calculate similarity based on pattern type
                if pattern.pattern_type == "regex":
                    # Compare regex patterns structurally
                    similarity = self._calculate_regex_similarity(
                        pattern.pattern_value,
                        other_pattern.pattern_value
                    )
                elif pattern.pattern_type == "semantic":
                    # Use embedding similarity
                    similarity = self._calculate_semantic_similarity(
                        pattern.metadata.get("embedding"),
                        other_pattern.metadata.get("embedding")
                    )
                else:
                    # Use example overlap
                    similarity = self._calculate_example_similarity(
                        pattern.examples,
                        other_pattern.examples
                    )
                    
                if similarity > 0.5:
                    similar_patterns.append((other_pattern, similarity))
                    
        # Sort by similarity
        similar_patterns.sort(key=lambda x: x[1], reverse=True)
        return similar_patterns[:top_k]
        
    async def merge_patterns(
        self,
        pattern_ids: List[str],
        new_pattern_type: str = "merged"
    ) -> Pattern:
        """
        Merge multiple patterns into one
        
        Args:
            pattern_ids: IDs of patterns to merge
            new_pattern_type: Type for merged pattern
            
        Returns:
            Merged pattern
        """
        if not pattern_ids:
            raise ValueError("No patterns to merge")
            
        patterns_to_merge = [
            self.patterns[pid] for pid in pattern_ids 
            if pid in self.patterns
        ]
        
        if not patterns_to_merge:
            raise ValueError("No valid patterns found")
            
        # Combine pattern values
        if new_pattern_type == "regex":
            # Create alternation regex
            merged_value = "|".join(f"({p.pattern_value})" for p in patterns_to_merge)
        else:
            # Create composite pattern
            merged_value = {
                "components": [p.pattern_value for p in patterns_to_merge],
                "type": "composite"
            }
            
        # Combine examples and calculate confidence
        all_examples = []
        total_support = 0
        
        for pattern in patterns_to_merge:
            all_examples.extend(pattern.examples)
            total_support += pattern.support
            
        merged_pattern = Pattern(
            id=f"merged:{','.join(pattern_ids)}",
            pattern_type=new_pattern_type,
            pattern_value=merged_value,
            confidence=np.mean([p.confidence for p in patterns_to_merge]),
            support=total_support,
            examples=list(set(all_examples))[:10],  # Keep top 10 unique examples
            metadata={
                "merged_from": pattern_ids,
                "merge_count": len(patterns_to_merge)
            }
        )
        
        # Store merged pattern
        self.patterns[merged_pattern.id] = merged_pattern
        self.pattern_index[new_pattern_type].append(merged_pattern.id)
        
        # Optionally remove original patterns
        # for pid in pattern_ids:
        #     del self.patterns[pid]
        
        return merged_pattern
        
    async def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get pattern matching statistics"""
        stats = {
            "total_patterns": len(self.patterns),
            "patterns_by_type": defaultdict(int),
            "avg_confidence": 0,
            "avg_support": 0,
            "most_common_patterns": []
        }
        
        confidences = []
        supports = []
        
        for pattern in self.patterns.values():
            stats["patterns_by_type"][pattern.pattern_type] += 1
            confidences.append(pattern.confidence)
            supports.append(pattern.support)
            
        if confidences:
            stats["avg_confidence"] = np.mean(confidences)
            stats["avg_support"] = np.mean(supports)
            
        # Find most common patterns
        sorted_patterns = sorted(
            self.patterns.values(),
            key=lambda p: p.support,
            reverse=True
        )
        
        stats["most_common_patterns"] = [
            {
                "id": p.id,
                "type": p.pattern_type,
                "support": p.support,
                "confidence": p.confidence
            }
            for p in sorted_patterns[:10]
        ]
        
        return stats
        
    # Private extraction methods
    
    def _extract_date_patterns(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract date patterns"""
        patterns = []
        
        # Extract date formats
        date_regexes = [
            (r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b', "dd/mm/yyyy"),
            (r'\b(\d{4}-\d{2}-\d{2})\b', "yyyy-mm-dd"),
            (r'\b(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})\b', "dd de month de yyyy")
        ]
        
        for regex, format_name in date_regexes:
            for match in re.finditer(regex, text, re.IGNORECASE):
                patterns.append({
                    "value": match.group(1),
                    "confidence": 0.9,
                    "metadata": {"format": format_name}
                })
                
        return patterns
        
    def _extract_numeric_patterns(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract numeric patterns"""
        patterns = []
        
        # Extract numbers with units
        unit_regex = r'\b(\d+(?:[.,]\d+)?)\s*(kg|ton|km|m|un|cx|pc|lt|ml)\b'
        for match in re.finditer(unit_regex, text, re.IGNORECASE):
            patterns.append({
                "value": match.group(),
                "confidence": 0.85,
                "metadata": {
                    "number": match.group(1),
                    "unit": match.group(2)
                }
            })
            
        return patterns
        
    def _extract_entity_patterns(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract entity patterns"""
        patterns = []
        
        # Extract named entities using pattern matching
        entity_indicators = {
            "cliente": ["cliente", "comprador", "destinatário"],
            "produto": ["produto", "item", "mercadoria", "material"],
            "local": ["cidade", "município", "estado", "endereço"]
        }
        
        for entity_type, indicators in entity_indicators.items():
            for indicator in indicators:
                regex = rf'\b{indicator}\s*:?\s*([\w\s]+?)(?:\s*[-,.]|\s*$)'
                for match in re.finditer(regex, text, re.IGNORECASE):
                    patterns.append({
                        "value": match.group(1).strip(),
                        "confidence": 0.8,
                        "metadata": {"entity_type": entity_type}
                    })
                    
        return patterns
        
    def _extract_action_patterns(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract action patterns"""
        patterns = []
        
        # Extract action verbs and their objects
        action_verbs = [
            "criar", "gerar", "calcular", "enviar", "receber",
            "aprovar", "cancelar", "modificar", "atualizar", "consultar"
        ]
        
        for verb in action_verbs:
            regex = rf'\b{verb}\s+([\w\s]+?)(?:\s*[-,.]|\s*$)'
            for match in re.finditer(regex, text, re.IGNORECASE):
                patterns.append({
                    "value": f"{verb} {match.group(1)}",
                    "confidence": 0.75,
                    "metadata": {"action": verb, "object": match.group(1)}
                })
                
        return patterns
        
    def _extract_structural_patterns(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract structural patterns"""
        patterns = []
        
        # Extract question patterns
        if "?" in text:
            patterns.append({
                "value": "question",
                "confidence": 1.0,
                "metadata": {"type": "interrogative"}
            })
            
        # Extract list patterns
        if any(marker in text for marker in ["1.", "•", "-", "*"]):
            patterns.append({
                "value": "list",
                "confidence": 0.9,
                "metadata": {"type": "enumeration"}
            })
            
        return patterns
        
    async def _learn_semantic_patterns(self, text: str):
        """Learn semantic patterns from text"""
        # This would use more sophisticated NLP techniques
        # For now, just store text for TF-IDF
        self.semantic_patterns.append((text, None))
        
    async def _match_semantic_patterns(
        self,
        text: str,
        min_confidence: float
    ) -> List[PatternMatch]:
        """Match semantic patterns"""
        matches = []
        
        # Use TF-IDF similarity if we have enough patterns
        if len(self.semantic_patterns) > 10:
            # This would calculate similarities
            pass
            
        return matches
        
    def _calculate_regex_similarity(self, regex1: str, regex2: str) -> float:
        """Calculate similarity between regex patterns"""
        # Simple character overlap for now
        set1 = set(regex1)
        set2 = set(regex2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0
        
    def _calculate_semantic_similarity(
        self,
        embedding1: Optional[np.ndarray],
        embedding2: Optional[np.ndarray]
    ) -> float:
        """Calculate semantic similarity using embeddings"""
        if embedding1 is None or embedding2 is None:
            return 0
        return float(cosine_similarity([embedding1], [embedding2])[0, 0])
        
    def _calculate_example_similarity(
        self,
        examples1: List[str],
        examples2: List[str]
    ) -> float:
        """Calculate similarity based on example overlap"""
        if not examples1 or not examples2:
            return 0
            
        # Use Jaccard similarity on word sets
        words1 = set(" ".join(examples1).lower().split())
        words2 = set(" ".join(examples2).lower().split())
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0
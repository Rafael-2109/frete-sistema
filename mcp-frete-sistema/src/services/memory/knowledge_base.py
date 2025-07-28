"""
Knowledge Base for domain-specific knowledge and learning
Manages freight system domain knowledge with continuous learning
"""

import json
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging
from pathlib import Path
import yaml

from ...models.memory_store import MemoryStore, MemoryEntry, MemoryType
from ...utils.embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeItem:
    """Represents a piece of domain knowledge"""
    id: str
    category: str
    subcategory: str
    title: str
    content: Dict[str, Any]
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0
    source: str = "system"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    usage_count: int = 0
    validation_status: str = "pending"  # pending, validated, rejected
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "category": self.category,
            "subcategory": self.subcategory,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "usage_count": self.usage_count,
            "validation_status": self.validation_status
        }


class KnowledgeBase:
    """
    Domain knowledge base with learning capabilities
    """
    
    def __init__(
        self,
        knowledge_path: Optional[Path] = None,
        memory_store: Optional[MemoryStore] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None
    ):
        self.knowledge_path = knowledge_path or Path("knowledge_base")
        self.memory_store = memory_store or MemoryStore()
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        
        # Knowledge storage
        self.knowledge_items: Dict[str, KnowledgeItem] = {}
        self.category_index: Dict[str, List[str]] = {}
        self.tag_index: Dict[str, Set[str]] = {}
        
        # Domain ontology
        self.ontology = self._initialize_ontology()
        
        # Learning parameters
        self.confidence_threshold = 0.7
        self.validation_threshold = 0.85
        
    def _initialize_ontology(self) -> Dict[str, Any]:
        """Initialize freight domain ontology"""
        return {
            "entities": {
                "pedido": {
                    "attributes": ["numero", "cliente", "valor", "status", "data"],
                    "relations": ["tem_itens", "pertence_a_cliente", "gera_fatura"]
                },
                "cliente": {
                    "attributes": ["nome", "cnpj", "endereco", "contato"],
                    "relations": ["faz_pedidos", "tem_tabela_preco", "localizado_em"]
                },
                "produto": {
                    "attributes": ["codigo", "descricao", "peso", "volume", "valor"],
                    "relations": ["pertence_a_pedido", "tem_estoque", "tem_preco"]
                },
                "transportadora": {
                    "attributes": ["nome", "cnpj", "frota", "areas_atendimento"],
                    "relations": ["realiza_entregas", "tem_tabela_frete", "atende_regioes"]
                },
                "frete": {
                    "attributes": ["valor", "prazo", "modalidade", "peso", "distancia"],
                    "relations": ["calculado_para_pedido", "usa_tabela", "tem_adicinais"]
                },
                "embarque": {
                    "attributes": ["numero", "data", "transportadora", "status"],
                    "relations": ["contem_pedidos", "tem_rota", "gera_documentos"]
                }
            },
            "processes": {
                "cotacao": ["solicitar", "calcular", "comparar", "aprovar"],
                "faturamento": ["gerar_nf", "calcular_impostos", "enviar", "confirmar"],
                "expedicao": ["separar", "embalar", "etiquetar", "carregar"],
                "entrega": ["roteirizar", "rastrear", "confirmar", "comprovar"]
            },
            "rules": {
                "frete_minimo": "Valor mínimo de frete por região",
                "prazo_entrega": "Prazo baseado em distância e modalidade",
                "peso_cubado": "Fator de cubagem por tipo de carga",
                "adicional_valor": "Percentual sobre valor da mercadoria"
            }
        }
        
    async def initialize(self):
        """Initialize knowledge base and load existing knowledge"""
        await self.memory_store.initialize()
        
        # Load static knowledge from files
        if self.knowledge_path.exists():
            await self._load_static_knowledge()
            
        # Load learned knowledge from memory store
        await self._load_learned_knowledge()
        
        logger.info(f"Knowledge base initialized with {len(self.knowledge_items)} items")
        
    async def add_knowledge(
        self,
        category: str,
        subcategory: str,
        title: str,
        content: Dict[str, Any],
        tags: Optional[List[str]] = None,
        source: str = "learned",
        confidence: float = 0.8
    ) -> str:
        """
        Add new knowledge item
        
        Args:
            category: Main category
            subcategory: Subcategory
            title: Knowledge title
            content: Knowledge content
            tags: Associated tags
            source: Knowledge source
            confidence: Confidence level
            
        Returns:
            Knowledge item ID
        """
        # Validate against ontology
        if category not in ["entities", "processes", "rules", "patterns", "examples"]:
            category = "general"
            
        # Generate ID
        item_id = f"{category}:{subcategory}:{title.lower().replace(' ', '_')}"
        
        # Create knowledge item
        item = KnowledgeItem(
            id=item_id,
            category=category,
            subcategory=subcategory,
            title=title,
            content=content,
            tags=tags or [],
            source=source,
            confidence=confidence
        )
        
        # Store in memory
        self.knowledge_items[item_id] = item
        
        # Update indices
        if category not in self.category_index:
            self.category_index[category] = []
        self.category_index[category].append(item_id)
        
        for tag in item.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(item_id)
            
        # Persist if confidence is high
        if confidence >= self.confidence_threshold:
            await self._persist_knowledge(item)
            
        logger.info(f"Added knowledge: {item_id} (confidence: {confidence})")
        return item_id
        
    async def query_knowledge(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        min_confidence: float = 0.6
    ) -> List[Tuple[KnowledgeItem, float]]:
        """
        Query knowledge base
        
        Args:
            query: Search query
            categories: Filter by categories
            tags: Filter by tags
            min_confidence: Minimum confidence
            
        Returns:
            List of (knowledge_item, relevance_score) tuples
        """
        results = []
        
        # Generate query embedding
        query_embedding = await self.embedding_generator.generate(query)
        query_lower = query.lower()
        
        # Search through knowledge items
        for item_id, item in self.knowledge_items.items():
            if item.confidence < min_confidence:
                continue
                
            # Category filter
            if categories and item.category not in categories:
                continue
                
            # Tag filter
            if tags and not any(tag in item.tags for tag in tags):
                continue
                
            # Calculate relevance score
            score = 0.0
            
            # Title match
            if query_lower in item.title.lower():
                score += 0.4
                
            # Content match
            content_str = json.dumps(item.content).lower()
            if query_lower in content_str:
                score += 0.3
                
            # Tag match
            query_words = set(query_lower.split())
            tag_words = set(" ".join(item.tags).lower().split())
            tag_overlap = len(query_words & tag_words) / len(query_words) if query_words else 0
            score += tag_overlap * 0.2
            
            # Semantic similarity (would use embeddings)
            # score += semantic_similarity * 0.1
            
            if score > 0:
                results.append((item, score * item.confidence))
                
        # Sort by relevance
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Update usage counts
        for item, _ in results[:5]:  # Top 5 results
            item.usage_count += 1
            
        return results
        
    async def learn_from_interaction(
        self,
        query: str,
        selected_result: Optional[str],
        feedback: Optional[str] = None,
        success: bool = True
    ):
        """
        Learn from user interactions
        
        Args:
            query: Original query
            selected_result: Selected knowledge item ID
            feedback: User feedback
            success: Whether interaction was successful
        """
        # Update knowledge item metrics
        if selected_result and selected_result in self.knowledge_items:
            item = self.knowledge_items[selected_result]
            
            if success:
                # Boost confidence
                item.confidence = min(1.0, item.confidence + 0.05)
                item.usage_count += 1
            else:
                # Reduce confidence
                item.confidence = max(0.1, item.confidence - 0.1)
                
            item.updated_at = datetime.utcnow()
            
        # Extract new patterns from query
        if success and feedback:
            await self._extract_knowledge_from_feedback(query, feedback)
            
    async def validate_knowledge(
        self,
        item_id: str,
        validation_result: bool,
        validator: str = "system"
    ):
        """
        Validate knowledge item
        
        Args:
            item_id: Knowledge item ID
            validation_result: Validation result
            validator: Who validated
        """
        if item_id in self.knowledge_items:
            item = self.knowledge_items[item_id]
            
            if validation_result:
                item.validation_status = "validated"
                item.confidence = min(1.0, item.confidence + 0.2)
            else:
                item.validation_status = "rejected"
                item.confidence = max(0.1, item.confidence - 0.3)
                
            item.updated_at = datetime.utcnow()
            
            # Persist validation
            await self._persist_knowledge(item)
            
    async def get_related_knowledge(
        self,
        item_id: str,
        max_items: int = 5
    ) -> List[Tuple[KnowledgeItem, float]]:
        """
        Get related knowledge items
        
        Args:
            item_id: Reference item ID
            max_items: Maximum related items
            
        Returns:
            List of (related_item, similarity_score) tuples
        """
        if item_id not in self.knowledge_items:
            return []
            
        reference_item = self.knowledge_items[item_id]
        related_items = []
        
        # Find items in same category
        category_items = self.category_index.get(reference_item.category, [])
        
        for other_id in category_items:
            if other_id == item_id:
                continue
                
            other_item = self.knowledge_items[other_id]
            
            # Calculate similarity
            similarity = 0.0
            
            # Same subcategory
            if other_item.subcategory == reference_item.subcategory:
                similarity += 0.4
                
            # Tag overlap
            ref_tags = set(reference_item.tags)
            other_tags = set(other_item.tags)
            if ref_tags and other_tags:
                tag_similarity = len(ref_tags & other_tags) / len(ref_tags | other_tags)
                similarity += tag_similarity * 0.3
                
            # Content similarity (simplified)
            ref_content_str = json.dumps(reference_item.content)
            other_content_str = json.dumps(other_item.content)
            
            ref_words = set(ref_content_str.lower().split())
            other_words = set(other_content_str.lower().split())
            
            if ref_words and other_words:
                content_similarity = len(ref_words & other_words) / len(ref_words | other_words)
                similarity += content_similarity * 0.3
                
            if similarity > 0.2:
                related_items.append((other_item, similarity))
                
        # Sort by similarity
        related_items.sort(key=lambda x: x[1], reverse=True)
        return related_items[:max_items]
        
    async def export_knowledge(
        self,
        format: str = "json",
        validated_only: bool = False
    ) -> str:
        """
        Export knowledge base
        
        Args:
            format: Export format (json, yaml)
            validated_only: Export only validated items
            
        Returns:
            Exported content
        """
        items_to_export = []
        
        for item in self.knowledge_items.values():
            if validated_only and item.validation_status != "validated":
                continue
            items_to_export.append(item.to_dict())
            
        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "total_items": len(items_to_export),
            "ontology": self.ontology,
            "knowledge_items": items_to_export
        }
        
        if format == "yaml":
            return yaml.dump(export_data, default_flow_style=False)
        else:
            return json.dumps(export_data, indent=2, ensure_ascii=False)
            
    async def import_knowledge(
        self,
        content: str,
        format: str = "json",
        merge: bool = True
    ) -> int:
        """
        Import knowledge base
        
        Args:
            content: Content to import
            format: Import format
            merge: Merge with existing knowledge
            
        Returns:
            Number of items imported
        """
        if format == "yaml":
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
            
        imported_count = 0
        
        for item_data in data.get("knowledge_items", []):
            item_id = item_data["id"]
            
            # Check if should merge or replace
            if item_id in self.knowledge_items and not merge:
                continue
                
            # Create knowledge item
            item = KnowledgeItem(
                id=item_id,
                category=item_data["category"],
                subcategory=item_data["subcategory"],
                title=item_data["title"],
                content=item_data["content"],
                tags=item_data.get("tags", []),
                confidence=item_data.get("confidence", 0.8),
                source=item_data.get("source", "imported"),
                validation_status=item_data.get("validation_status", "pending")
            )
            
            # Store item
            self.knowledge_items[item_id] = item
            
            # Update indices
            if item.category not in self.category_index:
                self.category_index[item.category] = []
            self.category_index[item.category].append(item_id)
            
            for tag in item.tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = set()
                self.tag_index[tag].add(item_id)
                
            imported_count += 1
            
        logger.info(f"Imported {imported_count} knowledge items")
        return imported_count
        
    async def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        stats = {
            "total_items": len(self.knowledge_items),
            "categories": {},
            "validation_status": {
                "validated": 0,
                "pending": 0,
                "rejected": 0
            },
            "sources": {},
            "avg_confidence": 0,
            "most_used_items": [],
            "tag_distribution": {}
        }
        
        confidences = []
        usage_counts = []
        
        for item in self.knowledge_items.values():
            # Category stats
            if item.category not in stats["categories"]:
                stats["categories"][item.category] = 0
            stats["categories"][item.category] += 1
            
            # Validation stats
            stats["validation_status"][item.validation_status] += 1
            
            # Source stats
            if item.source not in stats["sources"]:
                stats["sources"][item.source] = 0
            stats["sources"][item.source] += 1
            
            confidences.append(item.confidence)
            usage_counts.append((item.id, item.usage_count))
            
            # Tag stats
            for tag in item.tags:
                if tag not in stats["tag_distribution"]:
                    stats["tag_distribution"][tag] = 0
                stats["tag_distribution"][tag] += 1
                
        # Calculate averages
        if confidences:
            stats["avg_confidence"] = sum(confidences) / len(confidences)
            
        # Most used items
        usage_counts.sort(key=lambda x: x[1], reverse=True)
        stats["most_used_items"] = [
            {"id": item_id, "usage_count": count}
            for item_id, count in usage_counts[:10]
        ]
        
        return stats
        
    # Private helper methods
    
    async def _load_static_knowledge(self):
        """Load static knowledge from files"""
        knowledge_files = list(self.knowledge_path.glob("*.json")) + \
                         list(self.knowledge_path.glob("*.yaml"))
                         
        for file_path in knowledge_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    if file_path.suffix == ".yaml":
                        data = yaml.safe_load(f)
                    else:
                        data = json.load(f)
                        
                # Import knowledge from file
                if isinstance(data, list):
                    for item_data in data:
                        await self._import_knowledge_item(item_data, source="static")
                elif isinstance(data, dict) and "knowledge_items" in data:
                    for item_data in data["knowledge_items"]:
                        await self._import_knowledge_item(item_data, source="static")
                        
            except Exception as e:
                logger.error(f"Error loading knowledge from {file_path}: {e}")
                
    async def _load_learned_knowledge(self):
        """Load learned knowledge from memory store"""
        # Query memory store for knowledge items
        memories = await self.memory_store.search_by_type(
            memory_type=MemoryType.LONG_TERM,
            prefix="knowledge:"
        )
        
        for memory in memories:
            if memory.content and isinstance(memory.content, dict):
                await self._import_knowledge_item(memory.content, source="learned")
                
    async def _import_knowledge_item(
        self,
        item_data: Dict[str, Any],
        source: str = "imported"
    ):
        """Import a single knowledge item"""
        try:
            await self.add_knowledge(
                category=item_data.get("category", "general"),
                subcategory=item_data.get("subcategory", "misc"),
                title=item_data.get("title", "Untitled"),
                content=item_data.get("content", {}),
                tags=item_data.get("tags", []),
                source=source,
                confidence=item_data.get("confidence", 0.8)
            )
        except Exception as e:
            logger.error(f"Error importing knowledge item: {e}")
            
    async def _persist_knowledge(self, item: KnowledgeItem):
        """Persist knowledge item to memory store"""
        memory_entry = MemoryEntry(
            key=f"knowledge:{item.id}",
            content=item.to_dict(),
            memory_type=MemoryType.LONG_TERM,
            metadata={
                "category": item.category,
                "tags": item.tags,
                "source": item.source
            }
        )
        
        await self.memory_store.store(memory_entry)
        
    async def _extract_knowledge_from_feedback(
        self,
        query: str,
        feedback: str
    ):
        """Extract new knowledge from user feedback"""
        # This would use NLP to extract structured knowledge
        # For now, just log it
        logger.info(f"Learning from feedback - Query: {query}, Feedback: {feedback}")
        
    async def close(self):
        """Close knowledge base connections"""
        await self.memory_store.close()
        logger.info("Knowledge base closed")
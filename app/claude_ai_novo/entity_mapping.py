"""
Entity Mapping Module - Dynamic Pattern Recognition for Business Entities

This module provides intelligent entity mapping and pattern recognition
for the freight system without hardcoding specific values.

Key Features:
- CNPJ grouping patterns (first 8 digits = company group)
- Client name variations and fuzzy matching
- Location normalization (cities, states)
- Status field harmonization
- Temporal query patterns
- Dynamic relationship discovery
"""

import re
from typing import Dict, List, Optional, Tuple, Set, Any
from difflib import SequenceMatcher
from datetime import datetime, timedelta
import unicodedata
from collections import defaultdict

class EntityMapper:
    """Main entity mapping class with pattern recognition capabilities"""
    
    def __init__(self):
        # Entity type mappings
        self.entity_types = {
            'client': ['cliente', 'raz_social', 'raz_social_red', 'nome_cliente', 'empresa'],
            'cnpj': ['cnpj', 'cnpj_cpf', 'cnpj_cliente', 'cnpj_endereco_ent'],
            'location': ['municipio', 'cidade', 'nome_cidade', 'cidade_destino', 'cidade_normalizada'],
            'state': ['uf', 'estado', 'cod_uf', 'uf_destino', 'uf_normalizada'],
            'status': ['status', 'status_pedido', 'status_finalizacao', 'status_standby'],
            'date': ['data_', 'dt_', '_em', '_date', 'vencimento', 'expedicao', 'agendamento'],
            'identifier': ['numero_nf', 'num_pedido', 'numero', 'pedido', 'nota_fiscal', 'nf'],
            'value': ['valor_', 'preco_', 'qtd_', 'quantidade_', 'total_', 'saldo_'],
            'transport': ['transportadora', 'frete', 'embarque', 'entrega'],
        }
        
        # Status normalization patterns
        self.status_patterns = {
            'open': ['aberto', 'pendente', 'aguardando', 'criado', 'novo'],
            'processing': ['processando', 'em_andamento', 'em_processo', 'cotado', 'separado'],
            'shipped': ['embarcado', 'expedido', 'enviado', 'despachado'],
            'delivered': ['entregue', 'finalizado', 'concluido', 'completo'],
            'cancelled': ['cancelado', 'cancelada', 'anulado', 'excluido'],
            'on_hold': ['aguardando', 'standby', 'pausado', 'bloqueado'],
        }
        
        # Temporal patterns
        self.temporal_patterns = {
            'creation': ['criado_em', 'created_at', 'data_criacao', 'data_pedido'],
            'update': ['updated_at', 'atualizado_em', 'data_atual_pedido', 'alterado_em'],
            'schedule': ['agendamento', 'data_agendada', 'data_prevista', 'previsao'],
            'execution': ['data_entrega', 'data_embarque', 'data_faturamento', 'executado_em'],
            'deadline': ['vencimento', 'data_limite', 'prazo_final', 'data_entrega_pedido'],
        }
        
        # Compiled regex patterns for performance
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for better performance"""
        self.cnpj_pattern = re.compile(r'^\d{2}\.?\d{3}\.?\d{3}/?(\d{4})-?\d{2}$')
        self.cpf_pattern = re.compile(r'^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$')
        self.date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}')
        self.monetary_pattern = re.compile(r'R\$?\s*\d+[.,]\d{2}')
    
    def extract_cnpj_root(self, cnpj: str) -> Optional[str]:
        """
        Extract CNPJ root (first 8 digits) for company grouping
        Handles various CNPJ formats dynamically
        """
        if not cnpj:
            return None
        
        # Remove non-numeric characters
        clean_cnpj = re.sub(r'\D', '', str(cnpj))
        
        # Validate CNPJ length
        if len(clean_cnpj) < 8:
            return None
        
        # Return first 8 digits (company root)
        return clean_cnpj[:8]
    
    def normalize_client_name(self, name: str) -> str:
        """
        Normalize client name for comparison
        Handles variations, abbreviations, and special characters
        """
        if not name:
            return ""
        
        # Convert to uppercase
        normalized = name.upper().strip()
        
        # Remove accents
        normalized = ''.join(
            c for c in unicodedata.normalize('NFD', normalized)
            if unicodedata.category(c) != 'Mn'
        )
        
        # Common abbreviations normalization
        abbreviations = {
            r'\bLTDA\.?\b': 'LIMITADA',
            r'\bS\.?A\.?\b': 'SOCIEDADE ANONIMA',
            r'\bCIA\.?\b': 'COMPANHIA',
            r'\bIND\.?\b': 'INDUSTRIA',
            r'\bCOM\.?\b': 'COMERCIO',
            r'\bDIST\.?\b': 'DISTRIBUIDORA',
            r'\bTRANSP\.?\b': 'TRANSPORTADORA',
        }
        
        for pattern, replacement in abbreviations.items():
            normalized = re.sub(pattern, replacement, normalized)
        
        # Remove extra spaces
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two names (0-1 score)
        Uses fuzzy matching for client name variations
        """
        if not name1 or not name2:
            return 0.0
        
        # Normalize both names
        norm1 = self.normalize_client_name(name1)
        norm2 = self.normalize_client_name(name2)
        
        # Direct match after normalization
        if norm1 == norm2:
            return 1.0
        
        # Calculate similarity ratio
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def group_by_cnpj_root(self, entities: List[Dict[str, Any]], cnpj_field: str = 'cnpj') -> Dict[str, List[Dict]]:
        """
        Group entities by CNPJ root (company group)
        Returns dictionary with CNPJ root as key
        """
        groups = defaultdict(list)
        
        for entity in entities:
            cnpj = entity.get(cnpj_field)
            if cnpj:
                root = self.extract_cnpj_root(cnpj)
                if root:
                    groups[root].append(entity)
                else:
                    groups['invalid'].append(entity)
            else:
                groups['missing'].append(entity)
        
        return dict(groups)
    
    def find_similar_clients(self, client_name: str, all_clients: List[str], threshold: float = 0.8) -> List[Tuple[str, float]]:
        """
        Find similar client names based on fuzzy matching
        Returns list of (client_name, similarity_score) tuples
        """
        similarities = []
        
        for other_client in all_clients:
            score = self.calculate_name_similarity(client_name, other_client)
            if score >= threshold:
                similarities.append((other_client, score))
        
        # Sort by similarity score (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities
    
    def normalize_location(self, city: str, state: str) -> Dict[str, str]:
        """
        Normalize city and state names
        Handles variations and common misspellings
        """
        result = {
            'city_original': city,
            'state_original': state,
            'city_normalized': '',
            'state_normalized': '',
            'needs_validation': False
        }
        
        if city:
            # Normalize city
            city_norm = city.upper().strip()
            city_norm = ''.join(
                c for c in unicodedata.normalize('NFD', city_norm)
                if unicodedata.category(c) != 'Mn'
            )
            
            # Remove common suffixes
            city_norm = re.sub(r'\s+(DO|DA|DE|DOS|DAS)\s+', ' ', city_norm)
            city_norm = ' '.join(city_norm.split())
            
            result['city_normalized'] = city_norm
        
        if state:
            # Normalize state (ensure 2-letter code)
            state_norm = state.upper().strip()
            if len(state_norm) == 2:
                result['state_normalized'] = state_norm
            else:
                # Mark for validation if not standard UF code
                result['needs_validation'] = True
                result['state_normalized'] = state_norm[:2] if len(state_norm) >= 2 else state_norm
        
        return result
    
    def harmonize_status(self, status: str, context: str = 'general') -> str:
        """
        Harmonize status values across different entities
        Context can be: 'order', 'delivery', 'freight', 'general'
        """
        if not status:
            return 'unknown'
        
        status_lower = status.lower().strip()
        
        # Check against patterns
        for normalized_status, patterns in self.status_patterns.items():
            if any(pattern in status_lower for pattern in patterns):
                return normalized_status
        
        # Context-specific mappings
        if context == 'delivery':
            if 'nf' in status_lower and 'cd' in status_lower:
                return 'warehouse'
            elif 'reagend' in status_lower:
                return 'rescheduled'
        
        elif context == 'freight':
            if 'cotar' in status_lower or 'cotad' in status_lower:
                return 'quoted'
            elif 'fatur' in status_lower:
                return 'invoiced'
        
        # Return original if no match
        return status_lower
    
    def extract_temporal_fields(self, entity: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract and categorize temporal fields from an entity
        Returns categorized date/time fields
        """
        temporal_fields = defaultdict(list)
        
        for field_name, field_value in entity.items():
            # Skip if not a date-like field
            if not any(pattern in field_name.lower() for pattern in ['data', 'date', '_em', 'vencimento', 'prazo']):
                continue
            
            # Categorize by temporal pattern
            categorized = False
            for category, patterns in self.temporal_patterns.items():
                if any(pattern in field_name.lower() for pattern in patterns):
                    temporal_fields[category].append(field_name)
                    categorized = True
                    break
            
            # If not categorized, add to 'other'
            if not categorized:
                temporal_fields['other'].append(field_name)
        
        return dict(temporal_fields)
    
    def build_entity_relationships(self, entities: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
        """
        Discover relationships between entities based on common fields
        Returns a graph of entity relationships
        """
        relationships = defaultdict(set)
        
        # Common relationship patterns
        relationship_patterns = [
            ('pedido', 'num_pedido'),
            ('nf', 'numero_nf', 'nota_fiscal'),
            ('cnpj', 'cnpj_cpf', 'cnpj_cliente'),
            ('lote', 'separacao_lote_id', 'lote_id'),
            ('embarque', 'embarque_id'),
            ('transportadora', 'transportadora_id'),
        ]
        
        # Analyze entities to find relationships
        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities):
                if i >= j:  # Skip self and already processed pairs
                    continue
                
                # Check for common identifiers
                for rel_name, *field_names in relationship_patterns:
                    for field in field_names:
                        if field in entity1 and field in entity2:
                            if entity1[field] == entity2[field] and entity1[field] is not None:
                                relationships[f"{i}_{j}"].add(f"{rel_name}:{entity1[field]}")
        
        return dict(relationships)
    
    def generate_dynamic_query_pattern(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate dynamic query patterns based on filter criteria
        Adapts to different entity types and search patterns
        """
        query_pattern = {
            'base_filters': {},
            'date_ranges': {},
            'text_searches': {},
            'numeric_ranges': {},
            'status_filters': [],
            'grouping': [],
            'ordering': []
        }
        
        for field, value in filters.items():
            field_lower = field.lower()
            
            # Date range detection
            if any(date_kw in field_lower for date_kw in ['data', 'date', 'vencimento']):
                if isinstance(value, dict) and 'start' in value and 'end' in value:
                    query_pattern['date_ranges'][field] = value
                else:
                    query_pattern['base_filters'][field] = value
            
            # Status filter
            elif 'status' in field_lower:
                if isinstance(value, list):
                    query_pattern['status_filters'].extend(value)
                else:
                    query_pattern['status_filters'].append(value)
            
            # Numeric range
            elif any(num_kw in field_lower for num_kw in ['valor', 'qtd', 'quantidade', 'preco']):
                if isinstance(value, dict) and ('min' in value or 'max' in value):
                    query_pattern['numeric_ranges'][field] = value
                else:
                    query_pattern['base_filters'][field] = value
            
            # Text search
            elif any(isinstance(value, str) and '%' in value for text_kw in ['nome', 'cliente', 'cidade']):
                query_pattern['text_searches'][field] = value
            
            # Regular filter
            else:
                query_pattern['base_filters'][field] = value
        
        return query_pattern
    
    def suggest_entity_optimizations(self, entity_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Suggest optimizations based on entity usage patterns
        Returns list of optimization recommendations
        """
        suggestions = []
        
        # Check for missing indices
        if 'frequent_queries' in entity_stats:
            for field, count in entity_stats['frequent_queries'].items():
                if count > 1000 and field not in entity_stats.get('indexed_fields', []):
                    suggestions.append({
                        'type': 'index',
                        'field': field,
                        'reason': f'Field {field} is queried {count} times but not indexed',
                        'priority': 'high' if count > 5000 else 'medium'
                    })
        
        # Check for denormalization opportunities
        if 'join_patterns' in entity_stats:
            for pattern, count in entity_stats['join_patterns'].items():
                if count > 500:
                    suggestions.append({
                        'type': 'denormalization',
                        'pattern': pattern,
                        'reason': f'Join pattern {pattern} occurs {count} times',
                        'priority': 'medium'
                    })
        
        # Check for data quality issues
        if 'null_percentages' in entity_stats:
            for field, percentage in entity_stats['null_percentages'].items():
                if percentage > 50:
                    suggestions.append({
                        'type': 'data_quality',
                        'field': field,
                        'reason': f'Field {field} is {percentage}% null',
                        'priority': 'low'
                    })
        
        return suggestions


class EntityPatternAnalyzer:
    """Analyzer for discovering patterns in entity data"""
    
    def __init__(self, mapper: EntityMapper):
        self.mapper = mapper
        self.patterns = defaultdict(lambda: defaultdict(int))
    
    def analyze_entity_patterns(self, entities: List[Dict[str, Any]], entity_type: str) -> Dict[str, Any]:
        """
        Analyze patterns in entity data
        Returns comprehensive pattern analysis
        """
        analysis = {
            'entity_type': entity_type,
            'total_count': len(entities),
            'field_patterns': {},
            'value_patterns': defaultdict(lambda: defaultdict(int)),
            'relationship_patterns': {},
            'temporal_patterns': {},
            'quality_metrics': {}
        }
        
        # Analyze each entity
        for entity in entities:
            # Field presence
            for field, value in entity.items():
                if field not in analysis['field_patterns']:
                    analysis['field_patterns'][field] = {
                        'count': 0,
                        'null_count': 0,
                        'unique_values': set(),
                        'data_types': defaultdict(int)
                    }
                
                field_stats = analysis['field_patterns'][field]
                field_stats['count'] += 1
                
                if value is None or value == '':
                    field_stats['null_count'] += 1
                else:
                    # Track data types
                    field_stats['data_types'][type(value).__name__] += 1
                    
                    # Track unique values (limit to prevent memory issues)
                    if len(field_stats['unique_values']) < 1000:
                        field_stats['unique_values'].add(str(value)[:100])
            
            # Extract temporal patterns
            temporal_fields = self.mapper.extract_temporal_fields(entity)
            for category, fields in temporal_fields.items():
                if category not in analysis['temporal_patterns']:
                    analysis['temporal_patterns'][category] = defaultdict(int)
                for field in fields:
                    analysis['temporal_patterns'][category][field] += 1
        
        # Calculate quality metrics
        for field, stats in analysis['field_patterns'].items():
            stats['null_percentage'] = (stats['null_count'] / stats['count']) * 100
            stats['unique_count'] = len(stats['unique_values'])
            stats['cardinality'] = stats['unique_count'] / stats['count'] if stats['count'] > 0 else 0
            
            # Remove unique_values set to save memory in output
            del stats['unique_values']
        
        return analysis
    
    def discover_business_rules(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Discover implicit business rules from entity data
        Returns list of discovered rules with confidence scores
        """
        rules = []
        
        # Rule 1: CNPJ grouping patterns
        cnpj_groups = defaultdict(lambda: defaultdict(int))
        for entity in entities:
            cnpj = entity.get('cnpj') or entity.get('cnpj_cpf') or entity.get('cnpj_cliente')
            if cnpj:
                root = self.mapper.extract_cnpj_root(cnpj)
                if root:
                    # Track common attributes for this CNPJ root
                    for attr in ['transportadora', 'vendedor', 'equipe_vendas', 'forma_pgto_pedido']:
                        if attr in entity and entity[attr]:
                            cnpj_groups[root][attr] += 1
        
        # Analyze CNPJ patterns
        for root, attributes in cnpj_groups.items():
            for attr, count in attributes.items():
                if count > 3:  # Minimum threshold
                    rules.append({
                        'type': 'cnpj_pattern',
                        'rule': f'CNPJ root {root} frequently uses {attr}',
                        'confidence': min(count / 10, 1.0),  # Normalize confidence
                        'support_count': count
                    })
        
        # Rule 2: Status transitions
        status_transitions = defaultdict(lambda: defaultdict(int))
        for entity in entities:
            # This would need historical data to properly analyze
            # For now, we'll analyze status co-occurrences
            status_fields = [f for f in entity.keys() if 'status' in f.lower()]
            if len(status_fields) >= 2:
                for i, status1 in enumerate(status_fields):
                    for status2 in status_fields[i+1:]:
                        if entity.get(status1) and entity.get(status2):
                            transition = f"{entity[status1]} -> {entity[status2]}"
                            status_transitions[status1][transition] += 1
        
        # Rule 3: Temporal patterns
        temporal_rules = self._discover_temporal_rules(entities)
        rules.extend(temporal_rules)
        
        # Rule 4: Value constraints
        value_rules = self._discover_value_constraints(entities)
        rules.extend(value_rules)
        
        return rules
    
    def _discover_temporal_rules(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Discover temporal business rules"""
        rules = []
        temporal_patterns = defaultdict(list)
        
        for entity in entities:
            # Find date pairs
            date_fields = [(f, v) for f, v in entity.items() 
                          if v and any(d in f.lower() for d in ['data', 'date', '_em'])]
            
            for i, (field1, date1) in enumerate(date_fields):
                for field2, date2 in date_fields[i+1:]:
                    if isinstance(date1, (datetime, str)) and isinstance(date2, (datetime, str)):
                        # Convert to datetime if string
                        try:
                            if isinstance(date1, str):
                                date1 = datetime.strptime(date1[:10], '%Y-%m-%d')
                            if isinstance(date2, str):
                                date2 = datetime.strptime(date2[:10], '%Y-%m-%d')
                            
                            # Calculate difference
                            diff = (date2 - date1).days
                            temporal_patterns[f"{field1}_to_{field2}"].append(diff)
                        except:
                            continue
        
        # Analyze patterns
        for pattern_name, differences in temporal_patterns.items():
            if len(differences) > 5:
                avg_diff = sum(differences) / len(differences)
                min_diff = min(differences)
                max_diff = max(differences)
                
                rules.append({
                    'type': 'temporal_pattern',
                    'rule': f'{pattern_name} typically takes {avg_diff:.1f} days (range: {min_diff}-{max_diff})',
                    'confidence': 0.7 if max_diff - min_diff < 30 else 0.4,
                    'support_count': len(differences)
                })
        
        return rules
    
    def _discover_value_constraints(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Discover value constraint rules"""
        rules = []
        value_patterns = defaultdict(list)
        
        for entity in entities:
            # Analyze numeric fields
            for field, value in entity.items():
                if isinstance(value, (int, float)) and value > 0:
                    if any(kw in field.lower() for kw in ['valor', 'preco', 'qtd', 'quantidade']):
                        value_patterns[field].append(value)
        
        # Find patterns
        for field, values in value_patterns.items():
            if len(values) > 10:
                avg_val = sum(values) / len(values)
                min_val = min(values)
                max_val = max(values)
                
                # Check for common thresholds
                if 'frete' in field.lower() and min_val > 0:
                    rules.append({
                        'type': 'value_constraint',
                        'rule': f'{field} has minimum value of {min_val:.2f}',
                        'confidence': 0.9,
                        'support_count': len(values)
                    })
                
                # Check for typical ranges
                if max_val < avg_val * 3:  # No extreme outliers
                    rules.append({
                        'type': 'value_range',
                        'rule': f'{field} typically ranges from {min_val:.2f} to {max_val:.2f}',
                        'confidence': 0.8,
                        'support_count': len(values)
                    })
        
        return rules


# Utility functions for common mapping operations

def create_entity_mapper() -> EntityMapper:
    """Factory function to create configured EntityMapper instance"""
    return EntityMapper()

def analyze_entities(entities: List[Dict[str, Any]], entity_type: str) -> Dict[str, Any]:
    """Convenience function to analyze entity patterns"""
    mapper = create_entity_mapper()
    analyzer = EntityPatternAnalyzer(mapper)
    return analyzer.analyze_entity_patterns(entities, entity_type)

def discover_rules(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convenience function to discover business rules"""
    mapper = create_entity_mapper()
    analyzer = EntityPatternAnalyzer(mapper)
    return analyzer.discover_business_rules(entities)

def group_clients_by_company(entities: List[Dict[str, Any]], cnpj_field: str = 'cnpj') -> Dict[str, List[Dict]]:
    """Convenience function to group entities by company (CNPJ root)"""
    mapper = create_entity_mapper()
    return mapper.group_by_cnpj_root(entities, cnpj_field)
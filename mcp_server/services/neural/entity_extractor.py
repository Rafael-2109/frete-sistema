# Entity Extraction for Freight System
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import spacy
from dataclasses import dataclass
import logging
import json

logger = logging.getLogger(__name__)

@dataclass
class ExtractedEntity:
    """Represents an extracted entity"""
    entity_type: str
    value: Any
    text: str
    start_pos: int
    end_pos: int
    confidence: float
    metadata: Dict[str, Any]

class EntityExtractor:
    """Extract entities from freight-related text"""
    
    def __init__(self, use_spacy: bool = False):
        self.use_spacy = use_spacy
        self.nlp = None
        
        if use_spacy:
            try:
                # Load Portuguese spaCy model if available
                self.nlp = spacy.load("pt_core_news_sm")
                logger.info("Loaded spaCy Portuguese model")
            except:
                logger.warning("spaCy Portuguese model not found, using rule-based extraction only")
                self.use_spacy = False
                
        # Define entity patterns
        self.patterns = self._load_patterns()
        self.normalizers = self._load_normalizers()
        
    def _load_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load regex patterns for entity extraction"""
        return {
            'freight_id': [
                {
                    'pattern': r'FRT\d{6}',
                    'confidence': 0.95,
                    'description': 'Standard freight ID format'
                },
                {
                    'pattern': r'frete\s*#?\s*(\d{4,8})',
                    'confidence': 0.85,
                    'description': 'Freight with number'
                },
                {
                    'pattern': r'pedido\s*#?\s*(\d{4,8})',
                    'confidence': 0.85,
                    'description': 'Order with number'
                },
                {
                    'pattern': r'(?:id|ID|código)\s*:?\s*(\d{4,8})',
                    'confidence': 0.8,
                    'description': 'Generic ID'
                }
            ],
            'date': [
                {
                    'pattern': r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
                    'confidence': 0.9,
                    'description': 'DD/MM/YYYY or DD-MM-YYYY'
                },
                {
                    'pattern': r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',
                    'confidence': 0.9,
                    'description': 'YYYY-MM-DD'
                },
                {
                    'pattern': r'(hoje|ontem|amanhã|anteontem)',
                    'confidence': 0.95,
                    'description': 'Relative date'
                },
                {
                    'pattern': r'(\d+)\s*(dias?|semanas?|mês|meses)\s*(atrás|passados?)',
                    'confidence': 0.85,
                    'description': 'Past relative date'
                },
                {
                    'pattern': r'(próximo|próxima)\s*(segunda|terça|quarta|quinta|sexta|sábado|domingo)',
                    'confidence': 0.85,
                    'description': 'Next weekday'
                }
            ],
            'time': [
                {
                    'pattern': r'(\d{1,2}):(\d{2})(?::(\d{2}))?',
                    'confidence': 0.9,
                    'description': 'Time format HH:MM:SS'
                },
                {
                    'pattern': r'(\d{1,2})\s*(?:horas?|h)',
                    'confidence': 0.85,
                    'description': 'Hour format'
                },
                {
                    'pattern': r'(manhã|tarde|noite|madrugada)',
                    'confidence': 0.8,
                    'description': 'Time of day'
                }
            ],
            'location': [
                {
                    'pattern': r'CEP\s*:?\s*(\d{5})-?(\d{3})',
                    'confidence': 0.95,
                    'description': 'Brazilian ZIP code'
                },
                {
                    'pattern': r'(?:origem|saída|de)\s*:?\s*([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú]?[a-zà-ú]+)*)',
                    'confidence': 0.85,
                    'description': 'Origin location'
                },
                {
                    'pattern': r'(?:destino|chegada|para)\s*:?\s*([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú]?[a-zà-ú]+)*)',
                    'confidence': 0.85,
                    'description': 'Destination location'
                },
                {
                    'pattern': r'(?:rua|av\.|avenida|alameda|praça)\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú]?[a-zà-ú]+)*)',
                    'confidence': 0.8,
                    'description': 'Street address'
                }
            ],
            'money': [
                {
                    'pattern': r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
                    'confidence': 0.95,
                    'description': 'Brazilian currency format'
                },
                {
                    'pattern': r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:reais?|R\$)',
                    'confidence': 0.9,
                    'description': 'Amount in reais'
                },
                {
                    'pattern': r'valor\s*:?\s*(\d+(?:[,\.]\d{2})?)',
                    'confidence': 0.85,
                    'description': 'Value amount'
                }
            ],
            'weight': [
                {
                    'pattern': r'(\d+(?:[,\.]\d+)?)\s*(?:kg|quilos?|kilogramas?)',
                    'confidence': 0.9,
                    'description': 'Weight in kilograms'
                },
                {
                    'pattern': r'(\d+(?:[,\.]\d+)?)\s*(?:ton|toneladas?)',
                    'confidence': 0.9,
                    'description': 'Weight in tons'
                },
                {
                    'pattern': r'(\d+)\s*(?:g|gramas?)',
                    'confidence': 0.85,
                    'description': 'Weight in grams'
                }
            ],
            'distance': [
                {
                    'pattern': r'(\d+(?:[,\.]\d+)?)\s*(?:km|quilômetros?)',
                    'confidence': 0.9,
                    'description': 'Distance in kilometers'
                },
                {
                    'pattern': r'(\d+)\s*(?:m|metros?)',
                    'confidence': 0.85,
                    'description': 'Distance in meters'
                },
                {
                    'pattern': r'distância\s*:?\s*(\d+(?:[,\.]\d+)?)',
                    'confidence': 0.8,
                    'description': 'Generic distance'
                }
            ],
            'status': [
                {
                    'pattern': r'(pendente|aguardando|em\s*espera)',
                    'confidence': 0.9,
                    'description': 'Pending status'
                },
                {
                    'pattern': r'(em\s*trânsito|em\s*transporte|em\s*rota)',
                    'confidence': 0.9,
                    'description': 'In transit status'
                },
                {
                    'pattern': r'(entregue|finalizado|concluído)',
                    'confidence': 0.9,
                    'description': 'Delivered status'
                },
                {
                    'pattern': r'(cancelado|cancelada|anulado)',
                    'confidence': 0.9,
                    'description': 'Cancelled status'
                }
            ],
            'vehicle': [
                {
                    'pattern': r'(?:caminhão|truck)\s*([A-Z]{3}-?\d{4})',
                    'confidence': 0.9,
                    'description': 'Vehicle with plate'
                },
                {
                    'pattern': r'placa\s*:?\s*([A-Z]{3}-?\d{4})',
                    'confidence': 0.95,
                    'description': 'License plate'
                },
                {
                    'pattern': r'(van|caminhão|carreta|bitrem)',
                    'confidence': 0.8,
                    'description': 'Vehicle type'
                }
            ],
            'client': [
                {
                    'pattern': r'cliente\s*:?\s*([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú]?[a-zà-ú]+)*)',
                    'confidence': 0.85,
                    'description': 'Client name'
                },
                {
                    'pattern': r'empresa\s*:?\s*([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú]?[a-zà-ú]+)*)',
                    'confidence': 0.85,
                    'description': 'Company name'
                },
                {
                    'pattern': r'CNPJ\s*:?\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
                    'confidence': 0.95,
                    'description': 'Brazilian company ID'
                },
                {
                    'pattern': r'CPF\s*:?\s*(\d{3}\.\d{3}\.\d{3}-\d{2})',
                    'confidence': 0.95,
                    'description': 'Brazilian personal ID'
                }
            ],
            'phone': [
                {
                    'pattern': r'(?:\+55\s*)?(?:\(?\d{2}\)?\s*)?(\d{4,5})-?(\d{4})',
                    'confidence': 0.9,
                    'description': 'Brazilian phone number'
                },
                {
                    'pattern': r'tel(?:efone)?\s*:?\s*(\d{8,11})',
                    'confidence': 0.85,
                    'description': 'Phone number'
                }
            ],
            'email': [
                {
                    'pattern': r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                    'confidence': 0.95,
                    'description': 'Email address'
                }
            ]
        }
        
    def _load_normalizers(self) -> Dict[str, Any]:
        """Load normalization functions for different entity types"""
        return {
            'date': self._normalize_date,
            'money': self._normalize_money,
            'weight': self._normalize_weight,
            'distance': self._normalize_distance,
            'phone': self._normalize_phone,
            'status': self._normalize_status
        }
        
    def extract(self, text: str) -> List[ExtractedEntity]:
        """Extract all entities from text"""
        entities = []
        
        # Rule-based extraction
        for entity_type, patterns in self.patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info['pattern']
                confidence = pattern_info['confidence']
                
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    value = match.group(1) if match.groups() else match.group(0)
                    
                    # Normalize value if normalizer exists
                    if entity_type in self.normalizers:
                        normalized_value = self.normalizers[entity_type](value, match)
                    else:
                        normalized_value = value
                        
                    entity = ExtractedEntity(
                        entity_type=entity_type,
                        value=normalized_value,
                        text=match.group(0),
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=confidence,
                        metadata={
                            'pattern': pattern_info['description'],
                            'raw_value': value
                        }
                    )
                    
                    entities.append(entity)
                    
        # spaCy-based extraction if available
        if self.use_spacy and self.nlp:
            entities.extend(self._extract_with_spacy(text))
            
        # Remove duplicates and resolve conflicts
        entities = self._resolve_conflicts(entities)
        
        return sorted(entities, key=lambda e: e.start_pos)
        
    def _extract_with_spacy(self, text: str) -> List[ExtractedEntity]:
        """Extract entities using spaCy NER"""
        entities = []
        doc = self.nlp(text)
        
        for ent in doc.ents:
            # Map spaCy labels to our entity types
            entity_type = self._map_spacy_label(ent.label_)
            if entity_type:
                entity = ExtractedEntity(
                    entity_type=entity_type,
                    value=ent.text,
                    text=ent.text,
                    start_pos=ent.start_char,
                    end_pos=ent.end_char,
                    confidence=0.8,  # Default confidence for spaCy
                    metadata={
                        'source': 'spacy',
                        'label': ent.label_
                    }
                )
                entities.append(entity)
                
        return entities
        
    def _map_spacy_label(self, label: str) -> Optional[str]:
        """Map spaCy entity labels to our entity types"""
        mapping = {
            'PER': 'client',
            'ORG': 'client',
            'LOC': 'location',
            'DATE': 'date',
            'TIME': 'time',
            'MONEY': 'money',
            'QUANTITY': 'weight'  # Could be weight or distance
        }
        return mapping.get(label)
        
    def _resolve_conflicts(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Resolve overlapping entities"""
        # Sort by start position and confidence
        entities.sort(key=lambda e: (e.start_pos, -e.confidence))
        
        resolved = []
        last_end = -1
        
        for entity in entities:
            # Skip if overlapping with higher confidence entity
            if entity.start_pos >= last_end:
                resolved.append(entity)
                last_end = entity.end_pos
                
        return resolved
        
    def _normalize_date(self, value: str, match: re.Match) -> str:
        """Normalize date to ISO format"""
        try:
            # Handle relative dates
            relative_dates = {
                'hoje': datetime.now().date(),
                'ontem': (datetime.now() - timedelta(days=1)).date(),
                'amanhã': (datetime.now() + timedelta(days=1)).date(),
                'anteontem': (datetime.now() - timedelta(days=2)).date()
            }
            
            if value.lower() in relative_dates:
                return relative_dates[value.lower()].isoformat()
                
            # Handle DD/MM/YYYY format
            if '/' in value or '-' in value:
                parts = re.split(r'[/-]', value)
                if len(parts) == 3:
                    if len(parts[0]) == 4:  # YYYY-MM-DD
                        year, month, day = parts
                    else:  # DD/MM/YYYY
                        day, month, year = parts
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    
            # Handle relative past dates
            if 'atrás' in match.group(0) or 'passados' in match.group(0):
                amount = int(re.search(r'\d+', value).group())
                if 'dia' in match.group(0):
                    date = datetime.now() - timedelta(days=amount)
                elif 'semana' in match.group(0):
                    date = datetime.now() - timedelta(weeks=amount)
                elif 'mês' in match.group(0) or 'mes' in match.group(0):
                    date = datetime.now() - timedelta(days=amount*30)
                return date.date().isoformat()
                
        except:
            pass
            
        return value
        
    def _normalize_money(self, value: str, match: re.Match) -> float:
        """Normalize money values to float"""
        try:
            # Remove currency symbol and spaces
            value = re.sub(r'[R$\s]', '', value)
            # Replace Brazilian decimal format
            value = value.replace('.', '').replace(',', '.')
            return float(value)
        except:
            return 0.0
            
    def _normalize_weight(self, value: str, match: re.Match) -> float:
        """Normalize weight to kilograms"""
        try:
            # Extract numeric value
            numeric = float(re.search(r'[\d,\.]+', value).group().replace(',', '.'))
            
            # Convert to kg
            full_text = match.group(0).lower()
            if 'ton' in full_text:
                return numeric * 1000
            elif 'g' in full_text and 'kg' not in full_text:
                return numeric / 1000
            else:  # Already in kg
                return numeric
        except:
            return 0.0
            
    def _normalize_distance(self, value: str, match: re.Match) -> float:
        """Normalize distance to kilometers"""
        try:
            # Extract numeric value
            numeric = float(re.search(r'[\d,\.]+', value).group().replace(',', '.'))
            
            # Convert to km
            full_text = match.group(0).lower()
            if 'm' in full_text and 'km' not in full_text:
                return numeric / 1000
            else:  # Already in km
                return numeric
        except:
            return 0.0
            
    def _normalize_phone(self, value: str, match: re.Match) -> str:
        """Normalize phone number"""
        # Remove all non-numeric characters
        digits = re.sub(r'\D', '', match.group(0))
        
        # Add country code if missing
        if not digits.startswith('55'):
            digits = '55' + digits
            
        return digits
        
    def _normalize_status(self, value: str, match: re.Match) -> str:
        """Normalize status values"""
        status_map = {
            'pendente': 'pending',
            'aguardando': 'pending',
            'em espera': 'pending',
            'em trânsito': 'in_transit',
            'em transporte': 'in_transit',
            'em rota': 'in_transit',
            'entregue': 'delivered',
            'finalizado': 'delivered',
            'concluído': 'delivered',
            'cancelado': 'cancelled',
            'cancelada': 'cancelled',
            'anulado': 'cancelled'
        }
        
        return status_map.get(value.lower(), value.lower())
        
    def extract_by_type(self, text: str, entity_type: str) -> List[ExtractedEntity]:
        """Extract only specific entity type"""
        all_entities = self.extract(text)
        return [e for e in all_entities if e.entity_type == entity_type]
        
    def to_dict(self, entities: List[ExtractedEntity]) -> Dict[str, List[Any]]:
        """Convert entities to dictionary grouped by type"""
        result = {}
        for entity in entities:
            if entity.entity_type not in result:
                result[entity.entity_type] = []
            result[entity.entity_type].append({
                'value': entity.value,
                'text': entity.text,
                'confidence': entity.confidence,
                'position': [entity.start_pos, entity.end_pos]
            })
        return result
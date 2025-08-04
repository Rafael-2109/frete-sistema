"""
Mapeador dinâmico de entidades de negócio
"""

import re
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict
import jellyfish  # Para fuzzy matching
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EntityMapper:
    """Mapeia entidades de negócio dinamicamente sem hardcode"""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self.entity_cache = {}
        self.pattern_cache = {}
        self.initialize_patterns()
        
    def initialize_patterns(self):
        """Inicializa padrões de reconhecimento"""
        # Padrões para extração de raiz de CNPJ
        self.cnpj_pattern = re.compile(r'(\d{2}\.?\d{3}\.?\d{3})\/?\d{4}-?\d{2}')
        
        # Padrões para normalização de nomes
        self.name_cleanup_patterns = [
            (r'\s+ltda\.?$', ''),
            (r'\s+s\.?a\.?$', ''),
            (r'\s+eireli\.?$', ''),
            (r'\s+me\.?$', ''),
            (r'\s+epp\.?$', ''),
            (r'\s+-\s+filial.*$', ''),
            (r'\s+\d+$', ''),  # Remove números no final
        ]
        
        # Palavras ignoradas na comparação
        self.ignore_words = {
            'comercio', 'industria', 'distribuidora', 'transportes',
            'logistica', 'servicos', 'comercial', 'industrial'
        }
        
    def extract_cnpj_root(self, cnpj: str) -> Optional[str]:
        """Extrai os 8 primeiros dígitos do CNPJ (identificador da empresa)"""
        if not cnpj:
            return None
            
        # Remove formatação
        cnpj_clean = re.sub(r'[^\d]', '', cnpj)
        
        # Retorna os 8 primeiros dígitos
        if len(cnpj_clean) >= 8:
            return cnpj_clean[:8]
            
        return None
        
    def group_by_cnpj_root(self, entities: List[Dict]) -> Dict[str, List[Dict]]:
        """Agrupa entidades pela raiz do CNPJ"""
        groups = defaultdict(list)
        
        for entity in entities:
            cnpj = entity.get('cnpj', '')
            root = self.extract_cnpj_root(cnpj)
            
            if root:
                groups[root].append(entity)
            else:
                # Entidades sem CNPJ válido vão para grupo especial
                groups['NO_CNPJ'].append(entity)
                
        return dict(groups)
        
    def normalize_company_name(self, name: str) -> str:
        """Normaliza nome de empresa para comparação"""
        if not name:
            return ''
            
        normalized = name.lower().strip()
        
        # Aplica padrões de limpeza
        for pattern, replacement in self.name_cleanup_patterns:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
            
        # Remove palavras ignoradas
        words = normalized.split()
        words = [w for w in words if w not in self.ignore_words]
        normalized = ' '.join(words)
        
        return normalized.strip()
        
    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calcula similaridade entre dois nomes"""
        # Normaliza ambos
        norm1 = self.normalize_company_name(name1)
        norm2 = self.normalize_company_name(name2)
        
        if not norm1 or not norm2:
            return 0.0
            
        # Usa Jaro-Winkler para fuzzy matching
        similarity = jellyfish.jaro_winkler_similarity(norm1, norm2)
        
        # Boost se começam com a mesma palavra
        words1 = norm1.split()
        words2 = norm2.split()
        if words1 and words2 and words1[0] == words2[0]:
            similarity = min(similarity + 0.1, 1.0)
            
        return similarity
        
    def find_similar_entities(self, target_name: str, candidates: List[Dict], 
                            threshold: float = 0.8) -> List[Tuple[Dict, float]]:
        """Encontra entidades similares baseado no nome"""
        similar = []
        
        for candidate in candidates:
            candidate_name = candidate.get('nome', '') or candidate.get('cliente', '')
            similarity = self.calculate_name_similarity(target_name, candidate_name)
            
            if similarity >= threshold:
                similar.append((candidate, similarity))
                
        # Ordena por similaridade decrescente
        similar.sort(key=lambda x: x[1], reverse=True)
        
        return similar
        
    def detect_entity_patterns(self, entities: List[Dict]) -> Dict[str, Any]:
        """Detecta padrões nas entidades para criar regras dinâmicas"""
        patterns = {
            'cnpj_groups': defaultdict(set),
            'name_variations': defaultdict(set),
            'location_patterns': defaultdict(set),
            'temporal_patterns': defaultdict(int),
            'value_patterns': defaultdict(list)
        }
        
        for entity in entities:
            # Padrões de CNPJ
            cnpj = entity.get('cnpj', '')
            cnpj_root = self.extract_cnpj_root(cnpj)
            if cnpj_root:
                name = entity.get('nome', '') or entity.get('cliente', '')
                patterns['cnpj_groups'][cnpj_root].add(name)
                
            # Padrões de localização
            cidade = entity.get('cidade', '') or entity.get('municipio', '')
            uf = entity.get('uf', '') or entity.get('estado', '')
            if cidade and uf:
                patterns['location_patterns'][uf].add(cidade)
                
            # Padrões temporais
            for date_field in ['data_entrega', 'data_embarque', 'data_faturamento']:
                if date_field in entity and entity[date_field]:
                    try:
                        date_obj = datetime.strptime(str(entity[date_field]), '%Y-%m-%d')
                        weekday = date_obj.strftime('%A')
                        patterns['temporal_patterns'][weekday] += 1
                    except:
                        pass
                        
            # Padrões de valores
            for value_field in ['valor', 'valor_nf', 'valor_frete']:
                if value_field in entity and entity[value_field]:
                    try:
                        value = float(entity[value_field])
                        patterns['value_patterns'][value_field].append(value)
                    except:
                        pass
                        
        return self._analyze_patterns(patterns)
        
    def _analyze_patterns(self, patterns: Dict) -> Dict[str, Any]:
        """Analisa padrões detectados e gera insights"""
        analysis = {}
        
        # Análise de grupos CNPJ
        cnpj_analysis = {}
        for root, names in patterns['cnpj_groups'].items():
            if len(names) > 1:
                cnpj_analysis[root] = {
                    'filiais': len(names),
                    'nomes': list(names),
                    'nome_principal': self._find_main_name(names)
                }
        analysis['grupos_empresariais'] = cnpj_analysis
        
        # Análise de localizações
        location_analysis = {}
        for uf, cidades in patterns['location_patterns'].items():
            location_analysis[uf] = {
                'total_cidades': len(cidades),
                'principais_cidades': list(cidades)[:10]  # Top 10
            }
        analysis['distribuicao_geografica'] = location_analysis
        
        # Análise temporal
        if patterns['temporal_patterns']:
            total_ops = sum(patterns['temporal_patterns'].values())
            temporal_analysis = {
                day: (count / total_ops * 100) 
                for day, count in patterns['temporal_patterns'].items()
            }
            analysis['distribuicao_semanal'] = temporal_analysis
            
        # Análise de valores
        value_analysis = {}
        for field, values in patterns['value_patterns'].items():
            if values:
                value_analysis[field] = {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'count': len(values)
                }
        analysis['padroes_valores'] = value_analysis
        
        return analysis
        
    def _find_main_name(self, names: Set[str]) -> str:
        """Encontra o nome principal entre variações"""
        # Remove strings vazias
        names = [n for n in names if n]
        
        if not names:
            return ''
            
        # Escolhe o nome mais curto (geralmente é o principal)
        names_list = list(names)
        names_list.sort(key=len)
        
        return names_list[0]
        
    def resolve_entity_reference(self, reference: str, entity_type: str) -> List[Dict]:
        """Resolve uma referência a uma entidade"""
        results = []
        
        # Tenta diferentes estratégias de resolução
        # 1. Busca exata
        if self.db_session:
            if entity_type == 'cliente':
                from app.monitoramento.models import EntregaMonitorada
                exact = self.db_session.query(EntregaMonitorada).filter(
                    EntregaMonitorada.cliente == reference
                ).first()
                if exact:
                    results.append({'tipo': 'exato', 'entidade': exact})
                    
        # 2. Busca por CNPJ parcial
        cnpj_root = self.extract_cnpj_root(reference)
        if cnpj_root and self.db_session:
            from app.monitoramento.models import EntregaMonitorada
            cnpj_matches = self.db_session.query(EntregaMonitorada).filter(
                EntregaMonitorada.cnpj_cliente.like(f'{cnpj_root}%')
            ).limit(10).all()
            for match in cnpj_matches:
                results.append({'tipo': 'cnpj_parcial', 'entidade': match})
                
        # 3. Busca fuzzy por nome
        if self.db_session and entity_type == 'cliente':
            from app.monitoramento.models import EntregaMonitorada
            # Pega amostra de clientes únicos
            sample = self.db_session.query(
                EntregaMonitorada.cliente
            ).distinct().limit(1000).all()
            
            candidates = [{'nome': s[0]} for s in sample if s[0]]
            similar = self.find_similar_entities(reference, candidates, threshold=0.7)
            
            for candidate, score in similar[:5]:  # Top 5
                results.append({
                    'tipo': 'fuzzy',
                    'entidade': candidate,
                    'score': score
                })
                
        return results
        
    def create_entity_mapping_rules(self) -> Dict[str, Any]:
        """Cria regras de mapeamento baseadas nos dados existentes"""
        if not self.db_session:
            return {}
            
        rules = {
            'cnpj_groups': {},
            'name_mappings': {},
            'location_mappings': {},
            'status_mappings': {}
        }
        
        # Analisa dados para criar regras
        from app.monitoramento.models import EntregaMonitorada
        
        # Amostra de dados
        sample = self.db_session.query(EntregaMonitorada).limit(10000).all()
        
        # Detecta padrões
        entities_dict = []
        for item in sample:
            entities_dict.append({
                'cnpj': item.cnpj_cliente,
                'cliente': item.cliente,
                'cidade': item.municipio,
                'uf': item.uf,
                'status': getattr(item, 'status', None)
            })
            
        patterns = self.detect_entity_patterns(entities_dict)
        
        # Converte padrões em regras
        for root, info in patterns.get('grupos_empresariais', {}).items():
            rules['cnpj_groups'][root] = {
                'nome_principal': info['nome_principal'],
                'variacoes': info['nomes']
            }
            
        logger.info(f"Criadas {len(rules['cnpj_groups'])} regras de agrupamento por CNPJ")
        
        return rules
        
    def get_entity_context(self, entity_reference: str) -> Dict[str, Any]:
        """Obtém contexto completo de uma entidade"""
        context = {
            'reference': entity_reference,
            'resolved_entities': [],
            'related_entities': [],
            'patterns': {},
            'suggestions': []
        }
        
        # Resolve a referência
        resolved = self.resolve_entity_reference(entity_reference, 'cliente')
        context['resolved_entities'] = resolved
        
        # Se encontrou entidades, busca relacionadas
        if resolved and self.db_session:
            # Pega a primeira entidade resolvida
            main_entity = resolved[0]['entidade']
            
            # Busca entidades do mesmo grupo CNPJ
            if hasattr(main_entity, 'cnpj_cliente'):
                cnpj_root = self.extract_cnpj_root(main_entity.cnpj_cliente)
                if cnpj_root:
                    from app.monitoramento.models import EntregaMonitorada
                    related = self.db_session.query(EntregaMonitorada).filter(
                        EntregaMonitorada.cnpj_cliente.like(f'{cnpj_root}%')
                    ).limit(20).all()
                    
                    context['related_entities'] = [
                        {
                            'cliente': r.cliente,
                            'cnpj': r.cnpj_cliente,
                            'cidade': r.municipio,
                            'uf': r.uf
                        }
                        for r in related
                    ]
                    
        # Gera sugestões
        if context['resolved_entities']:
            context['suggestions'] = [
                f"Ver todas as entregas de {entity_reference}",
                f"Analisar padrão de atrasos de {entity_reference}",
                f"Comparar com outras filiais do grupo"
            ]
            
        return context
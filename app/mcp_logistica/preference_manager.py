"""
Gerenciador de preferências de usuário com aprendizado
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
import pickle

logger = logging.getLogger(__name__)

@dataclass
class UserPreference:
    """Preferência individual de usuário"""
    user_id: str
    preference_type: str
    key: str
    value: Any
    confidence: float = 0.5
    usage_count: int = 0
    last_used: datetime = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.last_used is None:
            self.last_used = datetime.now()
        if self.created_at is None:
            self.created_at = datetime.now()

class PreferenceManager:
    """Gerencia preferências de usuário e aprende padrões de uso"""
    
    def __init__(self, storage_backend=None):
        self.storage = storage_backend
        self.preferences_cache = defaultdict(dict)
        self.usage_patterns = defaultdict(lambda: defaultdict(Counter))
        self.learning_threshold = 3  # Número mínimo de usos para considerar uma preferência
        
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Obtém todas as preferências de um usuário"""
        # Verifica cache primeiro
        if user_id in self.preferences_cache:
            return self.preferences_cache[user_id]
            
        # Carrega do storage se disponível
        if self.storage:
            try:
                prefs_data = self.storage.get(f"user_prefs:{user_id}")
                if prefs_data:
                    prefs = json.loads(prefs_data)
                    self.preferences_cache[user_id] = prefs
                    return prefs
            except Exception as e:
                logger.error(f"Erro ao carregar preferências: {e}")
                
        # Retorna preferências padrão
        return self._get_default_preferences()
        
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Retorna preferências padrão para novos usuários"""
        return {
            'periodo_padrao': 'ultimos_7_dias',
            'formato_exportacao': 'excel',
            'limite_resultados': 50,
            'ordenacao_padrao': 'data_desc',
            'filtros_favoritos': [],
            'consultas_recentes': [],
            'notificacoes': {
                'atrasos': True,
                'divergencias': True,
                'confirmacoes': True
            },
            'interface': {
                'tema': 'claro',
                'densidade': 'normal',
                'idioma': 'pt-BR'
            }
        }
        
    def update_preference(self, user_id: str, pref_type: str, key: str, value: Any):
        """Atualiza uma preferência específica"""
        # Cria objeto de preferência
        pref = UserPreference(
            user_id=user_id,
            preference_type=pref_type,
            key=key,
            value=value
        )
        
        # Atualiza cache
        if user_id not in self.preferences_cache:
            self.preferences_cache[user_id] = self._get_default_preferences()
            
        # Navega pela estrutura aninhada
        if '.' in key:
            self._update_nested_preference(self.preferences_cache[user_id], key, value)
        else:
            self.preferences_cache[user_id][key] = value
            
        # Persiste se possível
        if self.storage:
            try:
                self.storage.set(
                    f"user_prefs:{user_id}",
                    json.dumps(self.preferences_cache[user_id])
                )
            except Exception as e:
                logger.error(f"Erro ao salvar preferência: {e}")
                
        # Registra uso para aprendizado
        self._record_usage(user_id, pref_type, key, value)
        
    def _update_nested_preference(self, prefs: Dict, key: str, value: Any):
        """Atualiza preferência em estrutura aninhada"""
        keys = key.split('.')
        current = prefs
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
            
        current[keys[-1]] = value
        
    def _record_usage(self, user_id: str, pref_type: str, key: str, value: Any):
        """Registra uso para aprendizado de padrões"""
        self.usage_patterns[user_id][pref_type][str(value)] += 1
        
    def learn_from_query(self, user_id: str, query_data: Dict):
        """Aprende preferências a partir de uma consulta"""
        # Extrai informações relevantes
        entities = query_data.get('entities', {})
        context = query_data.get('context', {})
        intent = query_data.get('intent', {})
        
        # Aprende período preferido
        if entities.get('temporal'):
            temporal = entities['temporal']
            if temporal.get('value'):
                self._record_usage(user_id, 'periodo', 'padrao', temporal['value'])
                
        # Aprende domínio preferido
        if context.get('domain'):
            self._record_usage(user_id, 'dominio', 'padrao', context['domain'])
            
        # Aprende formato de resposta preferido
        if query_data.get('response_format'):
            self._record_usage(user_id, 'formato', 'resposta', query_data['response_format'])
            
        # Adiciona à lista de consultas recentes
        self._add_recent_query(user_id, query_data)
        
        # Verifica se deve atualizar preferências baseado em padrões
        self._update_preferences_from_patterns(user_id)
        
    def _add_recent_query(self, user_id: str, query_data: Dict):
        """Adiciona consulta à lista de recentes"""
        prefs = self.get_user_preferences(user_id)
        
        recent = prefs.get('consultas_recentes', [])
        
        # Adiciona nova consulta
        recent.insert(0, {
            'query': query_data.get('original_query', ''),
            'timestamp': datetime.now().isoformat(),
            'intent': query_data.get('intent', {}).get('primary'),
            'success': query_data.get('success', True)
        })
        
        # Mantém apenas últimas 20
        recent = recent[:20]
        
        self.update_preference(user_id, 'historico', 'consultas_recentes', recent)
        
    def _update_preferences_from_patterns(self, user_id: str):
        """Atualiza preferências baseado em padrões de uso"""
        patterns = self.usage_patterns[user_id]
        
        for pref_type, values in patterns.items():
            # Encontra valor mais comum
            if values:
                most_common = values.most_common(1)[0]
                value, count = most_common
                
                # Se usado mais que o threshold, considera como preferência
                if count >= self.learning_threshold:
                    if pref_type == 'periodo':
                        self.update_preference(user_id, 'aprendido', 'periodo_padrao', value)
                    elif pref_type == 'dominio':
                        self.update_preference(user_id, 'aprendido', 'dominio_padrao', value)
                    elif pref_type == 'formato':
                        self.update_preference(user_id, 'aprendido', 'formato_padrao', value)
                        
    def get_query_suggestions(self, user_id: str, partial_query: str = "") -> List[str]:
        """Gera sugestões baseadas no histórico e preferências"""
        suggestions = []
        prefs = self.get_user_preferences(user_id)
        
        # Sugestões baseadas em consultas recentes
        recent = prefs.get('consultas_recentes', [])
        for item in recent:
            query = item.get('query', '')
            if partial_query.lower() in query.lower() and query not in suggestions:
                suggestions.append(query)
                
        # Sugestões baseadas em filtros favoritos
        filters = prefs.get('filtros_favoritos', [])
        for filter_text in filters:
            if partial_query.lower() in filter_text.lower():
                suggestions.append(filter_text)
                
        # Sugestões baseadas em padrões comuns
        if not partial_query:
            # Sugestões genéricas baseadas no domínio preferido
            domain = self._get_preferred_domain(user_id)
            if domain == 'entregas':
                suggestions.extend([
                    "Entregas atrasadas hoje",
                    "Status das entregas desta semana",
                    "Entregas pendentes por transportadora"
                ])
            elif domain == 'pedidos':
                suggestions.extend([
                    "Pedidos em aberto",
                    "Pedidos faturados hoje",
                    "Pedidos por cliente"
                ])
                
        return suggestions[:10]  # Limita a 10 sugestões
        
    def _get_preferred_domain(self, user_id: str) -> str:
        """Obtém domínio preferido do usuário"""
        patterns = self.usage_patterns[user_id].get('dominio', {})
        if patterns:
            return patterns.most_common(1)[0][0]
        return 'entregas'  # default
        
    def apply_user_context(self, user_id: str, query_context: Dict) -> Dict:
        """Aplica preferências do usuário ao contexto da consulta"""
        prefs = self.get_user_preferences(user_id)
        enhanced_context = query_context.copy()
        
        # Aplica período padrão se não especificado
        if not query_context.get('temporal'):
            periodo = prefs.get('periodo_padrao', 'ultimos_7_dias')
            enhanced_context['temporal'] = self._parse_periodo_padrao(periodo)
            
        # Aplica limite padrão
        if not query_context.get('limite'):
            enhanced_context['limite'] = prefs.get('limite_resultados', 50)
            
        # Aplica ordenação padrão
        if not query_context.get('ordenacao'):
            enhanced_context['ordenacao'] = prefs.get('ordenacao_padrao', 'data_desc')
            
        # Adiciona informações de interface
        enhanced_context['interface'] = prefs.get('interface', {})
        
        return enhanced_context
        
    def _parse_periodo_padrao(self, periodo: str) -> Dict:
        """Converte período padrão em estrutura temporal"""
        if periodo == 'hoje':
            return {
                'type': 'date',
                'value': datetime.now().date(),
                'expression': 'hoje'
            }
        elif periodo == 'ultimos_7_dias':
            return {
                'type': 'range',
                'value': 'last_7_days',
                'expression': 'últimos 7 dias'
            }
        elif periodo == 'ultimos_30_dias':
            return {
                'type': 'range',
                'value': 'last_30_days',
                'expression': 'últimos 30 dias'
            }
        else:
            return {
                'type': 'range',
                'value': 'current_month',
                'expression': 'este mês'
            }
            
    def export_preferences(self, user_id: str) -> Dict:
        """Exporta todas as preferências de um usuário"""
        return {
            'user_id': user_id,
            'preferences': self.get_user_preferences(user_id),
            'usage_patterns': dict(self.usage_patterns[user_id]),
            'export_date': datetime.now().isoformat()
        }
        
    def import_preferences(self, user_id: str, data: Dict):
        """Importa preferências de um usuário"""
        if 'preferences' in data:
            self.preferences_cache[user_id] = data['preferences']
            
            # Persiste se possível
            if self.storage:
                try:
                    self.storage.set(
                        f"user_prefs:{user_id}",
                        json.dumps(data['preferences'])
                    )
                except Exception as e:
                    logger.error(f"Erro ao importar preferências: {e}")
                    
        if 'usage_patterns' in data:
            # Converte de volta para Counter
            for pref_type, values in data['usage_patterns'].items():
                self.usage_patterns[user_id][pref_type] = Counter(values)
                
    def reset_preferences(self, user_id: str):
        """Reseta preferências para o padrão"""
        self.preferences_cache[user_id] = self._get_default_preferences()
        self.usage_patterns[user_id].clear()
        
        # Remove do storage
        if self.storage:
            try:
                self.storage.delete(f"user_prefs:{user_id}")
            except Exception as e:
                logger.error(f"Erro ao resetar preferências: {e}")
                
    def get_preference_insights(self, user_id: str) -> Dict:
        """Gera insights sobre as preferências do usuário"""
        prefs = self.get_user_preferences(user_id)
        patterns = self.usage_patterns[user_id]
        
        insights = {
            'perfil_uso': self._analyze_usage_profile(patterns),
            'evolucao_preferencias': self._analyze_preference_evolution(user_id),
            'sugestoes_personalizacao': self._generate_personalization_suggestions(prefs, patterns),
            'estatisticas': self._calculate_usage_statistics(prefs, patterns)
        }
        
        return insights
        
    def _analyze_usage_profile(self, patterns: Dict) -> Dict:
        """Analisa perfil de uso do usuário"""
        profile = {}
        
        # Domínio mais usado
        if patterns.get('dominio'):
            profile['dominio_principal'] = patterns['dominio'].most_common(1)[0][0]
            
        # Período mais comum
        if patterns.get('periodo'):
            profile['periodo_preferido'] = patterns['periodo'].most_common(1)[0][0]
            
        # Padrão de uso (frequência)
        total_uses = sum(sum(counter.values()) for counter in patterns.values())
        if total_uses > 100:
            profile['nivel_uso'] = 'intenso'
        elif total_uses > 50:
            profile['nivel_uso'] = 'regular'
        else:
            profile['nivel_uso'] = 'ocasional'
            
        return profile
        
    def _analyze_preference_evolution(self, user_id: str) -> List[Dict]:
        """Analisa evolução das preferências ao longo do tempo"""
        # Implementação simplificada - na prática seria mais complexa
        evolution = []
        
        prefs = self.get_user_preferences(user_id)
        recent_queries = prefs.get('consultas_recentes', [])
        
        if recent_queries:
            # Agrupa por semana
            weeks = defaultdict(list)
            for query in recent_queries:
                timestamp = datetime.fromisoformat(query['timestamp'])
                week_key = timestamp.strftime('%Y-%W')
                weeks[week_key].append(query)
                
            for week, queries in sorted(weeks.items(), reverse=True)[:4]:
                evolution.append({
                    'semana': week,
                    'total_consultas': len(queries),
                    'intents_mais_comuns': Counter(q['intent'] for q in queries).most_common(3)
                })
                
        return evolution
        
    def _generate_personalization_suggestions(self, prefs: Dict, patterns: Dict) -> List[str]:
        """Gera sugestões de personalização"""
        suggestions = []
        
        # Baseado no nível de uso
        total_uses = sum(sum(counter.values()) for counter in patterns.values())
        
        if total_uses < 10:
            suggestions.append("Configure seus filtros favoritos para acesso rápido")
            suggestions.append("Defina um período padrão para suas consultas")
            
        # Baseado em padrões detectados
        if patterns.get('periodo') and len(patterns['periodo']) == 1:
            periodo = list(patterns['periodo'].keys())[0]
            suggestions.append(f"Detectamos que você sempre usa '{periodo}'. Deseja definir como padrão?")
            
        # Baseado em preferências não configuradas
        if not prefs.get('filtros_favoritos'):
            suggestions.append("Salve suas consultas mais frequentes como filtros favoritos")
            
        return suggestions
        
    def _calculate_usage_statistics(self, prefs: Dict, patterns: Dict) -> Dict:
        """Calcula estatísticas de uso"""
        stats = {
            'total_consultas': len(prefs.get('consultas_recentes', [])),
            'filtros_favoritos': len(prefs.get('filtros_favoritos', [])),
            'dominios_utilizados': len(patterns.get('dominio', {})),
            'formatos_exportacao': len(patterns.get('formato', {})),
        }
        
        # Taxa de sucesso
        recent = prefs.get('consultas_recentes', [])
        if recent:
            successful = sum(1 for q in recent if q.get('success', True))
            stats['taxa_sucesso'] = (successful / len(recent)) * 100
            
        return stats
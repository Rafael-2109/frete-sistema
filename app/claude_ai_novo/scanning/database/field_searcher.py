"""
🔍 FIELD SEARCHER - Busca de Campos no Banco

Módulo responsável por buscar campos por diferentes critérios:
- Busca por tipo de dado
- Busca por nome/padrão
- Busca por características específicas
- Scoring e relevância
"""

import logging
from typing import Dict, List, Any, Optional, Union
from sqlalchemy.engine.reflection import Inspector

logger = logging.getLogger(__name__)


class FieldSearcher:
    """
    Buscador de campos no banco de dados.
    
    Responsável por localizar campos específicos
    baseado em diferentes critérios de busca.
    """
    
    def __init__(self, inspector: Optional[Inspector] = None, metadata_reader=None):
        """
        Inicializa o buscador de campos.
        
        Args:
            inspector: Inspector do SQLAlchemy
            metadata_reader: MetadataReader para obter informações das tabelas
        """
        self.inspector = inspector
        self.metadata_reader = metadata_reader
        self.search_cache: Dict[str, List[Dict[str, Any]]] = {}
    
    def set_inspector(self, inspector: Inspector) -> None:
        """
        Define o inspector a ser usado.
        
        Args:
            inspector: Inspector do SQLAlchemy
        """
        self.inspector = inspector
        self.search_cache.clear()  # Limpar cache ao trocar inspector
    
    def set_metadata_reader(self, metadata_reader) -> None:
        """
        Define o metadata reader a ser usado.
        
        Args:
            metadata_reader: MetadataReader instance
        """
        self.metadata_reader = metadata_reader
        self.search_cache.clear()  # Limpar cache ao trocar metadata reader
    
    def buscar_campos_por_tipo(self, tipo_campo: str, incluir_similares: bool = True) -> List[Dict[str, Any]]:
        """
        Busca campos por tipo em todas as tabelas.
        
        Args:
            tipo_campo: Tipo do campo a buscar
            incluir_similares: Se incluir tipos similares
            
        Returns:
            Lista de campos encontrados
        """
        if not self.inspector or not self.metadata_reader:
            logger.error("❌ Inspector ou MetadataReader não disponível")
            return []
        
        cache_key = f"tipo_{tipo_campo}_{incluir_similares}"
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        try:
            campos_encontrados = []
            tabelas = self.inspector.get_table_names()
            
            # Tipos similares para busca expandida
            tipos_similares = self._obter_tipos_similares(tipo_campo) if incluir_similares else [tipo_campo]
            
            for tabela in tabelas:
                info_tabela = self.metadata_reader.obter_campos_tabela(tabela)
                
                for nome_campo, info_campo in info_tabela.get('campos', {}).items():
                    if info_campo['tipo_python'] in tipos_similares:
                        campo_info = {
                            'tabela': tabela,
                            'campo': nome_campo,
                            'tipo': info_campo['tipo'],
                            'tipo_python': info_campo['tipo_python'],
                            'nulo': info_campo['nulo'],
                            'chave_primaria': info_campo['chave_primaria'],
                            'tamanho': info_campo.get('tamanho'),
                            'match_score': 1.0 if info_campo['tipo_python'] == tipo_campo else 0.8
                        }
                        campos_encontrados.append(campo_info)
            
            # Ordenar por score de match
            campos_encontrados.sort(key=lambda x: x['match_score'], reverse=True)
            
            # Cache do resultado
            self.search_cache[cache_key] = campos_encontrados
            
            logger.info(f"🔍 Encontrados {len(campos_encontrados)} campos do tipo {tipo_campo}")
            return campos_encontrados
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar campos por tipo {tipo_campo}: {e}")
            return []
    
    def _obter_tipos_similares(self, tipo_campo: str) -> List[str]:
        """
        Obtém tipos similares para um tipo específico.
        
        Args:
            tipo_campo: Tipo original
            
        Returns:
            Lista de tipos similares
        """
        grupos_tipos = {
            'string': ['string', 'text'],
            'integer': ['integer', 'decimal'],
            'decimal': ['decimal', 'integer'],
            'datetime': ['datetime', 'date', 'time'],
            'date': ['date', 'datetime'],
            'time': ['time', 'datetime'],
            'boolean': ['boolean'],
            'uuid': ['uuid', 'string'],
            'json': ['json']
        }
        
        return grupos_tipos.get(tipo_campo, [tipo_campo])
    
    def buscar_campos_por_nome(self, nome_padrao: str, match_type: str = 'contains') -> List[Dict[str, Any]]:
        """
        Busca campos por padrão de nome em todas as tabelas.
        
        Args:
            nome_padrao: Padrão do nome a buscar
            match_type: Tipo de match ('exact', 'starts', 'ends', 'contains')
            
        Returns:
            Lista de campos encontrados
        """
        if not self.inspector or not self.metadata_reader:
            logger.error("❌ Inspector ou MetadataReader não disponível")
            return []
        
        cache_key = f"nome_{nome_padrao}_{match_type}"
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        try:
            campos_encontrados = []
            tabelas = self.inspector.get_table_names()
            nome_padrao_lower = nome_padrao.lower()
            
            for tabela in tabelas:
                info_tabela = self.metadata_reader.obter_campos_tabela(tabela)
                
                for nome_campo, info_campo in info_tabela.get('campos', {}).items():
                    match_score = self._calcular_score_match_nome(nome_campo, nome_padrao, match_type)
                    
                    if match_score > 0:
                        campo_info = {
                            'tabela': tabela,
                            'campo': nome_campo,
                            'tipo': info_campo['tipo'],
                            'tipo_python': info_campo['tipo_python'],
                            'nulo': info_campo['nulo'],
                            'chave_primaria': info_campo['chave_primaria'],
                            'match_score': match_score,
                            'match_type': self._determinar_tipo_match(nome_campo, nome_padrao)
                        }
                        campos_encontrados.append(campo_info)
            
            # Ordenar por score de match (melhor primeiro)
            campos_encontrados.sort(key=lambda x: x['match_score'], reverse=True)
            
            # Cache do resultado
            self.search_cache[cache_key] = campos_encontrados
            
            logger.info(f"🔍 Encontrados {len(campos_encontrados)} campos para padrão '{nome_padrao}'")
            return campos_encontrados
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar campos por nome '{nome_padrao}': {e}")
            return []
    
    def _calcular_score_match_nome(self, nome_campo: str, nome_padrao: str, match_type: str) -> float:
        """
        Calcula score de match entre nome do campo e padrão.
        
        Args:
            nome_campo: Nome do campo
            nome_padrao: Padrão buscado
            match_type: Tipo de match
            
        Returns:
            Score de 0 a 1
        """
        nome_lower = nome_campo.lower()
        padrao_lower = nome_padrao.lower()
        
        if match_type == 'exact':
            return 1.0 if nome_lower == padrao_lower else 0.0
        
        elif match_type == 'starts':
            return 0.9 if nome_lower.startswith(padrao_lower) else 0.0
        
        elif match_type == 'ends':
            return 0.8 if nome_lower.endswith(padrao_lower) else 0.0
        
        elif match_type == 'contains':
            if nome_lower == padrao_lower:
                return 1.0
            elif nome_lower.startswith(padrao_lower):
                return 0.9
            elif nome_lower.endswith(padrao_lower):
                return 0.8
            elif padrao_lower in nome_lower:
                return 0.7
            else:
                # Match por similaridade
                chars_comuns = set(nome_lower) & set(padrao_lower)
                if chars_comuns:
                    return len(chars_comuns) / max(len(nome_lower), len(padrao_lower)) * 0.5
        
        return 0.0
    
    def _determinar_tipo_match(self, nome_campo: str, nome_padrao: str) -> str:
        """
        Determina o tipo de match encontrado.
        
        Args:
            nome_campo: Nome do campo
            nome_padrao: Padrão buscado
            
        Returns:
            Tipo de match
        """
        nome_lower = nome_campo.lower()
        padrao_lower = nome_padrao.lower()
        
        if nome_lower == padrao_lower:
            return 'exact'
        elif nome_lower.startswith(padrao_lower):
            return 'starts_with'
        elif nome_lower.endswith(padrao_lower):
            return 'ends_with'
        elif padrao_lower in nome_lower:
            return 'contains'
        else:
            return 'similarity'
    
    def buscar_campos_chave_primaria(self) -> List[Dict[str, Any]]:
        """
        Busca todos os campos que são chave primária.
        
        Returns:
            Lista de campos chave primária
        """
        return self.buscar_campos_por_caracteristica('chave_primaria', True)
    
    def buscar_campos_obrigatorios(self) -> List[Dict[str, Any]]:
        """
        Busca todos os campos obrigatórios (NOT NULL).
        
        Returns:
            Lista de campos obrigatórios
        """
        return self.buscar_campos_por_caracteristica('nulo', False)
    
    def buscar_campos_por_caracteristica(self, caracteristica: str, valor: Any) -> List[Dict[str, Any]]:
        """
        Busca campos por uma característica específica.
        
        Args:
            caracteristica: Nome da característica
            valor: Valor da característica
            
        Returns:
            Lista de campos encontrados
        """
        if not self.inspector or not self.metadata_reader:
            logger.error("❌ Inspector ou MetadataReader não disponível")
            return []
        
        cache_key = f"char_{caracteristica}_{valor}"
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        try:
            campos_encontrados = []
            tabelas = self.inspector.get_table_names()
            
            for tabela in tabelas:
                info_tabela = self.metadata_reader.obter_campos_tabela(tabela)
                
                for nome_campo, info_campo in info_tabela.get('campos', {}).items():
                    if info_campo.get(caracteristica) == valor:
                        campo_info = {
                            'tabela': tabela,
                            'campo': nome_campo,
                            'tipo': info_campo['tipo'],
                            'tipo_python': info_campo['tipo_python'],
                            'valor_caracteristica': info_campo.get(caracteristica),
                            'match_score': 1.0
                        }
                        campos_encontrados.append(campo_info)
            
            # Cache do resultado
            self.search_cache[cache_key] = campos_encontrados
            
            logger.info(f"🔍 Encontrados {len(campos_encontrados)} campos com {caracteristica}={valor}")
            return campos_encontrados
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar campos por característica {caracteristica}: {e}")
            return []
    
    def buscar_campos_por_tamanho(self, tamanho_min: Optional[int] = None, 
                                 tamanho_max: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Busca campos por faixa de tamanho.
        
        Args:
            tamanho_min: Tamanho mínimo
            tamanho_max: Tamanho máximo
            
        Returns:
            Lista de campos encontrados
        """
        if not self.inspector or not self.metadata_reader:
            logger.error("❌ Inspector ou MetadataReader não disponível")
            return []
        
        try:
            campos_encontrados = []
            tabelas = self.inspector.get_table_names()
            
            for tabela in tabelas:
                info_tabela = self.metadata_reader.obter_campos_tabela(tabela)
                
                for nome_campo, info_campo in info_tabela.get('campos', {}).items():
                    tamanho = info_campo.get('tamanho')
                    
                    if tamanho is not None:
                        # Verificar se está na faixa
                        if tamanho_min is not None and tamanho < tamanho_min:
                            continue
                        if tamanho_max is not None and tamanho > tamanho_max:
                            continue
                        
                        campo_info = {
                            'tabela': tabela,
                            'campo': nome_campo,
                            'tipo': info_campo['tipo'],
                            'tipo_python': info_campo['tipo_python'],
                            'tamanho': tamanho,
                            'match_score': 1.0
                        }
                        campos_encontrados.append(campo_info)
            
            # Ordenar por tamanho
            campos_encontrados.sort(key=lambda x: x['tamanho'])
            
            logger.info(f"🔍 Encontrados {len(campos_encontrados)} campos na faixa de tamanho")
            return campos_encontrados
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar campos por tamanho: {e}")
            return []
    
    def buscar_campos_similares(self, tabela_referencia: str, campo_referencia: str, 
                               limite_score: float = 0.5) -> List[Dict[str, Any]]:
        """
        Busca campos similares a um campo de referência.
        
        Args:
            tabela_referencia: Tabela do campo de referência
            campo_referencia: Campo de referência
            limite_score: Score mínimo de similaridade
            
        Returns:
            Lista de campos similares
        """
        if not self.metadata_reader:
            logger.error("❌ MetadataReader não disponível")
            return []
        
        try:
            # Obter informações do campo de referência
            info_tabela_ref = self.metadata_reader.obter_campos_tabela(tabela_referencia)
            if campo_referencia not in info_tabela_ref.get('campos', {}):
                logger.error(f"❌ Campo {campo_referencia} não encontrado em {tabela_referencia}")
                return []
            
            info_campo_ref = info_tabela_ref['campos'][campo_referencia]
            
            campos_similares = []
            tabelas = self.inspector.get_table_names()
            
            for tabela in tabelas:
                info_tabela = self.metadata_reader.obter_campos_tabela(tabela)
                
                for nome_campo, info_campo in info_tabela.get('campos', {}).items():
                    # Pular o próprio campo
                    if tabela == tabela_referencia and nome_campo == campo_referencia:
                        continue
                    
                    # Calcular similaridade
                    score_similaridade = self._calcular_similaridade_campos(info_campo_ref, info_campo, campo_referencia, nome_campo)
                    
                    if score_similaridade >= limite_score:
                        campo_info = {
                            'tabela': tabela,
                            'campo': nome_campo,
                            'tipo': info_campo['tipo'],
                            'tipo_python': info_campo['tipo_python'],
                            'similaridade_score': score_similaridade,
                            'fatores_similaridade': self._analisar_fatores_similaridade(info_campo_ref, info_campo, campo_referencia, nome_campo)
                        }
                        campos_similares.append(campo_info)
            
            # Ordenar por score de similaridade
            campos_similares.sort(key=lambda x: x['similaridade_score'], reverse=True)
            
            logger.info(f"🔍 Encontrados {len(campos_similares)} campos similares a {tabela_referencia}.{campo_referencia}")
            return campos_similares
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar campos similares: {e}")
            return []
    
    def _calcular_similaridade_campos(self, campo_ref: Dict[str, Any], campo_comp: Dict[str, Any], 
                                    nome_ref: str, nome_comp: str) -> float:
        """
        Calcula similaridade entre dois campos.
        
        Args:
            campo_ref: Campo de referência
            campo_comp: Campo para comparar
            nome_ref: Nome do campo de referência
            nome_comp: Nome do campo para comparar
            
        Returns:
            Score de similaridade (0-1)
        """
        score = 0.0
        
        # Similaridade de tipo (40% do score)
        if campo_ref['tipo_python'] == campo_comp['tipo_python']:
            score += 0.4
        elif campo_ref['tipo_python'] in self._obter_tipos_similares(campo_comp['tipo_python']):
            score += 0.2
        
        # Similaridade de nome (30% do score)
        score_nome = self._calcular_score_match_nome(nome_comp, nome_ref, 'contains')
        score += score_nome * 0.3
        
        # Similaridade de características (30% do score)
        if campo_ref.get('nulo') == campo_comp.get('nulo'):
            score += 0.1
        
        if campo_ref.get('chave_primaria') == campo_comp.get('chave_primaria'):
            score += 0.1
        
        # Similaridade de tamanho (para strings)
        tamanho_ref = campo_ref.get('tamanho')
        tamanho_comp = campo_comp.get('tamanho')
        if tamanho_ref and tamanho_comp:
            if abs(tamanho_ref - tamanho_comp) <= max(tamanho_ref, tamanho_comp) * 0.2:  # Diferença <= 20%
                score += 0.1
        
        return min(score, 1.0)
    
    def _analisar_fatores_similaridade(self, campo_ref: Dict[str, Any], campo_comp: Dict[str, Any], 
                                     nome_ref: str, nome_comp: str) -> List[str]:
        """
        Analisa fatores que contribuem para a similaridade.
        
        Args:
            campo_ref: Campo de referência
            campo_comp: Campo para comparar
            nome_ref: Nome do campo de referência
            nome_comp: Nome do campo para comparar
            
        Returns:
            Lista de fatores de similaridade
        """
        fatores = []
        
        if campo_ref['tipo_python'] == campo_comp['tipo_python']:
            fatores.append('Mesmo tipo de dado')
        
        score_nome = self._calcular_score_match_nome(nome_comp, nome_ref, 'contains')
        if score_nome > 0.8:
            fatores.append('Nome muito similar')
        elif score_nome > 0.5:
            fatores.append('Nome parcialmente similar')
        
        if campo_ref.get('nulo') == campo_comp.get('nulo'):
            fatores.append('Mesma obrigatoriedade')
        
        if campo_ref.get('chave_primaria') and campo_comp.get('chave_primaria'):
            fatores.append('Ambos são chave primária')
        
        tamanho_ref = campo_ref.get('tamanho')
        tamanho_comp = campo_comp.get('tamanho')
        if tamanho_ref and tamanho_comp and abs(tamanho_ref - tamanho_comp) <= 5:
            fatores.append('Tamanho similar')
        
        return fatores
    
    def limpar_cache(self) -> None:
        """
        Limpa o cache de buscas.
        """
        self.search_cache.clear()
        logger.debug("🧹 Cache de buscas limpo")
    
    def is_available(self) -> bool:
        """
        Verifica se o buscador está disponível.
        
        Returns:
            True se disponível
        """
        return self.inspector is not None and self.metadata_reader is not None


# Exportações principais
__all__ = [
    'FieldSearcher'
] 
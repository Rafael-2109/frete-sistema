"""
🔧 BASE MAPPER - Classe Base para Mapeadores
===========================================

Classe base abstrata que define a interface comum para todos os mappers.
Contém funcionalidades compartilhadas e força implementação de métodos
essenciais nos mappers específicos.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BaseMapper(ABC):
    """
    Classe base abstrata para todos os mappers semânticos.
    
    Cada mapper específico deve herdar desta classe e implementar
    os métodos abstratos definidos.
    """
    
    def __init__(self, modelo_nome: str):
        """
        Inicializa o mapper base.
        
        Args:
            modelo_nome: Nome do modelo que este mapper representa
        """
        self.modelo_nome = modelo_nome
        self.mapeamentos = self._criar_mapeamentos()
        
    @abstractmethod
    def _criar_mapeamentos(self) -> Dict[str, Dict[str, Any]]:
        """
        Cria os mapeamentos específicos deste mapper.
        
        Returns:
            Dict com mapeamentos no formato:
            {
                'nome_campo': {
                    'campo_principal': 'nome_campo_real',
                    'termos_naturais': ['termo1', 'termo2'],
                    'tipo': 'string|integer|datetime|decimal',
                    'observacao': 'Observação opcional',
                    'deprecated': False
                }
            }
        """
        pass
    
    def buscar_mapeamento(self, termo: str) -> List[Dict[str, Any]]:
        """
        Busca mapeamentos para um termo específico.
        
        Args:
            termo: Termo em linguagem natural
            
        Returns:
            Lista de mapeamentos encontrados
        """
        termo_lower = termo.lower().strip()
        resultados = []
        
        for campo, config in self.mapeamentos.items():
            # Verificar se termo está nos termos naturais
            for termo_natural in config['termos_naturais']:
                if termo_natural.lower() == termo_lower:
                    resultado = {
                        'campo': campo,
                        'modelo': self.modelo_nome,
                        'campo_principal': config['campo_principal'],
                        'tipo': config['tipo'],
                        'observacao': config.get('observacao', ''),
                        'deprecated': config.get('deprecated', False),
                        'match_exacto': True,
                        'termo_encontrado': termo_natural
                    }
                    resultados.append(resultado)
                    
        return resultados
    
    def buscar_mapeamento_fuzzy(self, termo: str, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """
        Busca mapeamentos usando correspondência fuzzy.
        
        Args:
            termo: Termo em linguagem natural
            threshold: Limiar de similaridade (0-1)
            
        Returns:
            Lista de mapeamentos encontrados com score de similaridade
        """
        try:
    from fuzzywuzzy import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    class FuzzMock:
        def ratio(self, a, b): return 0
        def partial_ratio(self, a, b): return 0
        def token_sort_ratio(self, a, b): return 0
        def token_set_ratio(self, a, b): return 0
    fuzz = FuzzMock()
    FUZZY_AVAILABLE = False
        except ImportError:
            logger.warning("📦 fuzzywuzzy não instalado, pulando busca fuzzy")
            return []
            
        termo_lower = termo.lower().strip()
        resultados = []
        
        for campo, config in self.mapeamentos.items():
            for termo_natural in config['termos_naturais']:
                score = fuzz.ratio(termo_lower, termo_natural.lower()) / 100.0
                
                if score >= threshold:
                    resultado = {
                        'campo': campo,
                        'modelo': self.modelo_nome,
                        'campo_principal': config['campo_principal'],
                        'tipo': config['tipo'],
                        'observacao': config.get('observacao', ''),
                        'deprecated': config.get('deprecated', False),
                        'match_exacto': False,
                        'termo_encontrado': termo_natural,
                        'score_similaridade': score
                    }
                    resultados.append(resultado)
                    
        # Ordenar por score (maior primeiro)
        resultados.sort(key=lambda x: x['score_similaridade'], reverse=True)
        return resultados
    
    def listar_todos_campos(self) -> List[str]:
        """
        Lista todos os campos mapeados por este mapper.
        
        Returns:
            Lista de nomes dos campos
        """
        return list(self.mapeamentos.keys())
    
    def listar_termos_naturais(self) -> List[str]:
        """
        Lista todos os termos naturais mapeados por este mapper.
        
        Returns:
            Lista de termos naturais
        """
        termos = []
        for config in self.mapeamentos.values():
            termos.extend(config['termos_naturais'])
        return sorted(termos)
    
    def gerar_estatisticas(self) -> Dict[str, Any]:
        """
        Gera estatísticas deste mapper.
        
        Returns:
            Dict com estatísticas do mapper
        """
        total_campos = len(self.mapeamentos)
        total_termos = sum(len(config['termos_naturais']) for config in self.mapeamentos.values())
        campos_deprecated = len([c for c in self.mapeamentos.values() if c.get('deprecated', False)])
        
        return {
            'modelo': self.modelo_nome,
            'total_campos': total_campos,
            'total_termos_naturais': total_termos,
            'media_termos_por_campo': total_termos / total_campos if total_campos > 0 else 0,
            'campos_deprecated': campos_deprecated,
            'campos_ativos': total_campos - campos_deprecated
        }
    
    def validar_mapeamentos(self) -> List[str]:
        """
        Valida a estrutura dos mapeamentos.
        
        Returns:
            Lista de erros encontrados (vazia se tudo OK)
        """
        erros = []
        
        for campo, config in self.mapeamentos.items():
            # Verificar campos obrigatórios
            if 'campo_principal' not in config:
                erros.append(f"❌ Campo '{campo}': falta 'campo_principal'")
                
            if 'termos_naturais' not in config:
                erros.append(f"❌ Campo '{campo}': falta 'termos_naturais'")
            elif not isinstance(config['termos_naturais'], list):
                erros.append(f"❌ Campo '{campo}': 'termos_naturais' deve ser lista")
            elif len(config['termos_naturais']) == 0:
                erros.append(f"❌ Campo '{campo}': 'termos_naturais' está vazio")
                
            if 'tipo' not in config:
                erros.append(f"❌ Campo '{campo}': falta 'tipo'")
            elif config['tipo'] not in ['string', 'integer', 'datetime', 'decimal', 'boolean']:
                erros.append(f"❌ Campo '{campo}': tipo '{config['tipo']}' inválido")
                
        return erros
    
    def __str__(self) -> str:
        """Representação string do mapper"""
        return f"<{self.__class__.__name__} modelo='{self.modelo_nome}' campos={len(self.mapeamentos)}>"
    
    def __repr__(self) -> str:
        """Representação detalhada do mapper"""
        return self.__str__() 
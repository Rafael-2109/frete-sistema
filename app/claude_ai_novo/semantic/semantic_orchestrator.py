"""
🎼 SEMANTIC ORCHESTRATOR - Coordenação Principal
=================================================

Orquestrador principal que coordena todos os mappers e 
fornece interface unificada para o sistema semântico.

Responsabilidades:
- Inicialização e configuração
- Coordenação dos mappers  
- Interface principal de busca
- Gerenciamento de recursos
"""

from typing import Dict, List, Any, Optional
import logging
import os

# Imports dos mappers específicos
from .mappers import (
    PedidosMapper, 
    EmbarquesMapper, 
    MonitoramentoMapper,
    FaturamentoMapper, 
    TransportadorasMapper
)

# Imports dos readers
from .readers import ReadmeReader, DatabaseReader
from .readers.performance_cache import cached_readme_reader, cached_database_reader

logger = logging.getLogger(__name__)

class SemanticOrchestrator:
    """
    Orquestrador principal dos mapeamentos semânticos.
    
    Coordena todos os mappers específicos e fornece interface
    unificada para busca e gerenciamento de mapeamentos.
    """
    
    def __init__(self):
        """Inicializa o orquestrador semântico"""
        self.mappers = self._inicializar_mappers()
        self.readme_path = self._localizar_readme()
        
        # Inicializar readers
        self.readme_reader = self._inicializar_readme_reader()
        self.database_reader = self._inicializar_database_reader()
        
        logger.info(f"🎼 SemanticOrchestrator inicializado com {len(self.mappers)} mappers e readers integrados")
    
    def _inicializar_mappers(self) -> Dict[str, Any]:
        """
        Inicializa todos os mappers específicos.
        
        Returns:
            Dict com instâncias dos mappers
        """
        mappers = {}
        
        try:
            mappers['pedidos'] = PedidosMapper()
            mappers['embarques'] = EmbarquesMapper()
            mappers['monitoramento'] = MonitoramentoMapper()
            mappers['faturamento'] = FaturamentoMapper()
            mappers['transportadoras'] = TransportadorasMapper()
            
            logger.info(f"✅ {len(mappers)} mappers inicializados com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar mappers: {e}")
            
        return mappers
    
    def _inicializar_readme_reader(self) -> Optional[ReadmeReader]:
        """
        Inicializa o ReadmeReader usando cache otimizado.
        
        Returns:
            Instância cached do ReadmeReader ou None se erro
        """
        try:
            readme_reader = cached_readme_reader()
            if readme_reader:
                logger.info("📄 ReadmeReader inicializado com sucesso (cached)")
                return readme_reader
            else:
                logger.warning("⚠️ ReadmeReader não disponível (README não encontrado)")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar ReadmeReader: {e}")
            return None
    
    def _inicializar_database_reader(self) -> Optional[DatabaseReader]:
        """
        Inicializa o DatabaseReader usando cache otimizado.
        
        Returns:
            Instância cached do DatabaseReader ou None se erro
        """
        try:
            database_reader = cached_database_reader()
            if database_reader:
                logger.info("📊 DatabaseReader inicializado com sucesso (cached)")
                return database_reader
            else:
                logger.warning("⚠️ DatabaseReader não disponível (banco não acessível)")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar DatabaseReader: {e}")
            return None
    
    def _localizar_readme(self) -> Optional[str]:
        """
        Localiza o arquivo README_MAPEAMENTO_SEMANTICO_COMPLETO.md
        
        Returns:
            Caminho para o README ou None se não encontrado
        """
        try:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            readme_path = os.path.join(base_path, 'README_MAPEAMENTO_SEMANTICO_COMPLETO.md')
            
            if os.path.exists(readme_path):
                logger.info(f"📄 README encontrado: {readme_path}")
                return readme_path
            else:
                logger.warning(f"📄 README não encontrado em: {readme_path}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao localizar README: {e}")
            return None
    
    def mapear_termo_natural(self, termo: str, modelos: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Mapeia termo em linguagem natural para campos do banco.
        
        Args:
            termo: Termo em linguagem natural
            modelos: Lista de modelos específicos para buscar (opcional)
            
        Returns:
            Lista de mapeamentos encontrados
        """
        termo_lower = termo.lower().strip()
        resultados = []
        
        # Determinar quais mappers usar
        mappers_para_usar = {}
        if modelos:
            for modelo in modelos:
                if modelo.lower() in self.mappers:
                    mappers_para_usar[modelo.lower()] = self.mappers[modelo.lower()]
        else:
            mappers_para_usar = self.mappers
        
        # Buscar em cada mapper
        for nome_mapper, mapper in mappers_para_usar.items():
            try:
                # Busca exata primeiro
                resultados_mapper = mapper.buscar_mapeamento(termo)
                resultados.extend(resultados_mapper)
                
                # Se não encontrou nada, tenta busca fuzzy
                if not resultados_mapper:
                    resultados_fuzzy = mapper.buscar_mapeamento_fuzzy(termo, threshold=0.8)
                    resultados.extend(resultados_fuzzy)
                    
            except Exception as e:
                logger.error(f"❌ Erro ao buscar em {nome_mapper}: {e}")
        
        # Ordenar por relevância (matches exatos primeiro, depois por score)
        resultados.sort(key=lambda x: (
            not x.get('match_exacto', False),  # Exactos primeiro
            -x.get('score_similaridade', 1.0)  # Score maior primeiro
        ))
        
        logger.debug(f"🔍 Termo '{termo}': {len(resultados)} mapeamentos encontrados")
        return resultados
    
    def buscar_por_modelo(self, modelo: str) -> List[Dict[str, Any]]:
        """
        Lista todos os campos mapeados para um modelo específico.
        
        Args:
            modelo: Nome do modelo (ex: 'Pedido', 'Embarque')
            
        Returns:
            Lista de campos do modelo
        """
        # Criar mapeamento de modelo para mapper (case-insensitive)
        modelo_para_mapper = {
            'pedido': 'pedidos',
            'embarque': 'embarques', 
            'entregamonitorada': 'monitoramento',
            'relatoriofaturamentoimportado': 'faturamento',
            'transportadora': 'transportadoras'
        }
        
        modelo_lower = modelo.lower()
        nome_mapper = modelo_para_mapper.get(modelo_lower, modelo_lower)
        
        if nome_mapper not in self.mappers:
            logger.warning(f"⚠️ Modelo '{modelo}' não encontrado. Mappers disponíveis: {list(self.mappers.keys())}")
            return []
        
        mapper = self.mappers[nome_mapper]
        campos = []
        
        for campo, config in mapper.mapeamentos.items():
            campos.append({
                'campo': campo,
                'modelo': mapper.modelo_nome,  # Usar nome do modelo do mapper
                'campo_principal': config['campo_principal'],
                'tipo': config['tipo'],
                'observacao': config.get('observacao', ''),
                'deprecated': config.get('deprecated', False),
                'termos_naturais': config['termos_naturais']
            })
        
        return campos
    
    def buscar_no_readme(self, campo: str, modelo: Optional[str] = None) -> List[str]:
        """
        Busca termos naturais para um campo específico no README usando ReadmeReader.
        
        Args:
            campo: Nome do campo
            modelo: Nome do modelo (opcional)
            
        Returns:
            Lista de termos naturais encontrados no README
        """
        if not self.readme_reader:
            logger.debug("📄 ReadmeReader não disponível")
            return []
        
        try:
            return self.readme_reader.buscar_termos_naturais(campo, modelo)
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar no README via ReadmeReader: {e}")
            return []
    
    def listar_todos_modelos(self) -> List[str]:
        """
        Lista todos os modelos disponíveis.
        
        Returns:
            Lista de nomes dos modelos
        """
        return [mapper.modelo_nome for mapper in self.mappers.values()]
    
    def listar_todos_campos(self, modelo: Optional[str] = None) -> List[str]:
        """
        Lista todos os campos mapeados.
        
        Args:
            modelo: Filtrar por modelo específico (opcional)
            
        Returns:
            Lista de nomes dos campos
        """
        campos = []
        
        mappers_para_usar = self.mappers
        if modelo:
            modelo_lower = modelo.lower()
            if modelo_lower in self.mappers:
                mappers_para_usar = {modelo_lower: self.mappers[modelo_lower]}
        
        for mapper in mappers_para_usar.values():
            campos.extend(mapper.listar_todos_campos())
        
        return sorted(list(set(campos)))
    
    def obter_mapper(self, nome: str) -> Optional[Any]:
        """
        Obtém um mapper específico pelo nome.
        
        Args:
            nome: Nome do mapper
            
        Returns:
            Instância do mapper ou None
        """
        return self.mappers.get(nome.lower())
    
    def obter_readers(self) -> Dict[str, Any]:
        """
        Obtém os readers disponíveis.
        
        Returns:
            Dict com readers disponíveis
        """
        return {
            'readme_reader': self.readme_reader,
            'database_reader': self.database_reader,
            'readme_path': self.readme_path
        }
    
    def verificar_saude_sistema(self) -> Dict[str, Any]:
        """
        Verifica saúde geral do sistema semântico.
        
        Returns:
            Dict com status de saúde
        """
        return {
            'mappers_ativos': len(self.mappers),
            'mappers_funcionais': len([m for m in self.mappers.values() if m]),
            'readme_reader_disponivel': self.readme_reader is not None,
            'database_reader_disponivel': self.database_reader is not None,
            'readme_encontrado': self.readme_path is not None,
            'status_geral': self._calcular_status_geral()
        }
    
    def _calcular_status_geral(self) -> str:
        """Calcula status geral do sistema"""
        problemas = 0
        
        if len(self.mappers) == 0:
            problemas += 2  # Crítico
        if not self.readme_reader:
            problemas += 1
        if not self.database_reader:
            problemas += 1
        if not self.readme_path:
            problemas += 1
        
        if problemas == 0:
            return "EXCELENTE"
        elif problemas <= 1:
            return "BOM"
        elif problemas <= 2:
            return "REGULAR"
        else:
            return "CRÍTICO"
    
    def __str__(self) -> str:
        """Representação string do orquestrador"""
        readers_status = f"readers={sum([self.readme_reader is not None, self.database_reader is not None])}/2"
        return f"<SemanticOrchestrator mappers={len(self.mappers)} campos_total={len(self.listar_todos_campos())} {readers_status}>"
    
    def __repr__(self) -> str:
        """Representação detalhada do orquestrador"""
        return self.__str__()


# Função de conveniência para obter instância global
_orchestrator_instance = None

def get_semantic_orchestrator() -> SemanticOrchestrator:
    """
    Obtém instância global do orquestrador semântico.
    
    Returns:
        Instância do SemanticOrchestrator
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = SemanticOrchestrator()
    return _orchestrator_instance 
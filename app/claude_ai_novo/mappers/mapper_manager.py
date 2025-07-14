"""
🗺️ MAPPER MANAGER - Coordenador de Mappers Especializados
========================================================

Manager principal que coordena todos os mappers específicos de domínio.

Responsabilidade: Coordenar PedidosMapper, EmbarquesMapper, MonitoramentoMapper, etc.
para fornecer análise semântica unificada sem duplicar mapeamentos.

Função: MANAGER que orquestra mappers especializados, não um mapper individual.
"""

from typing import Dict, List, Any, Optional, Union
import logging
from datetime import datetime

# Imports dos mappers específicos existentes
from app.claude_ai_novo.mappers.domain.pedidos_mapper import PedidosMapper
from app.claude_ai_novo.mappers.domain.embarques_mapper import EmbarquesMapper
from app.claude_ai_novo.mappers.domain.monitoramento_mapper import MonitoramentoMapper
from app.claude_ai_novo.mappers.domain.faturamento_mapper import FaturamentoMapper
from app.claude_ai_novo.mappers.domain.transportadoras_mapper import TransportadorasMapper

logger = logging.getLogger(__name__)

# Singleton instance
_mapper_manager_instance = None

class MapperManager:
    """
    Manager principal que coordena todos os mappers específicos.
    
    NÃO duplica mapeamentos, mas coordena os mappers existentes para
    fornecer análise semântica integrada do sistema.
    """
    
    def __new__(cls):
        """Implementação do padrão Singleton"""
        global _mapper_manager_instance
        if _mapper_manager_instance is None:
            _mapper_manager_instance = super().__new__(cls)
        return _mapper_manager_instance
    
    def __init__(self):
        """Inicializa o orquestrador com todos os mappers específicos"""
        self.mappers = {
            'pedidos': PedidosMapper(),
            'embarques': EmbarquesMapper(), 
            'monitoramento': MonitoramentoMapper(),
            'faturamento': FaturamentoMapper(),
            'transportadoras': TransportadorasMapper()
        }
        
        logger.info("🧠 SemanticMapper (orquestrador) inicializado com 5 mappers específicos")
    
    def analisar_consulta_semantica(self, consulta: str) -> Dict[str, Any]:
        """
        Analisa consulta usando TODOS os mappers específicos.
        
        Args:
            consulta: Consulta em linguagem natural
            
        Returns:
            Dict com análise semântica integrada
        """
        if not consulta:
            return {'campos_detectados': [], 'confianca': 0.0, 'mappers_consultados': []}
        
        consulta_lower = consulta.lower().strip()
        campos_detectados = []
        mappers_consultados = []
        
        # Consultar TODOS os mappers específicos
        for nome_mapper, mapper in self.mappers.items():
            try:
                # Buscar mapeamentos exatos
                for termo in consulta_lower.split():
                    termo_limpo = termo.strip('.,!?;:()[]{}')
                    if len(termo_limpo) < 2:
                        continue
                    
                    mapeamentos = mapper.buscar_mapeamento(termo_limpo)
                    for mapeamento in mapeamentos:
                        mapeamento['mapper_origem'] = nome_mapper
                        if mapeamento not in campos_detectados:
                            campos_detectados.append(mapeamento)
                
                if campos_detectados:
                    mappers_consultados.append(nome_mapper)
                    
            except Exception as e:
                logger.warning(f"Erro ao consultar {nome_mapper}: {e}")
        
        # Buscar mapeamentos fuzzy se poucos resultados
        if len(campos_detectados) < 3:
            campos_detectados.extend(self._buscar_fuzzy_integrado(consulta_lower))
        
        # Calcular confiança baseada nos resultados
        confianca = self._calcular_confianca_integrada(campos_detectados, mappers_consultados)
        
        return {
            'campos_detectados': campos_detectados,
            'confianca': confianca,
            'mappers_consultados': mappers_consultados,
            'total_mappers': len(self.mappers),
            'termos_analisados': len(consulta_lower.split()),
            'matches_por_mapper': self._agrupar_por_mapper(campos_detectados)
        }
    
    def _buscar_fuzzy_integrado(self, consulta: str) -> List[Dict[str, Any]]:
        """
        Busca fuzzy integrada em todos os mappers específicos.
        
        Args:
            consulta: Consulta em linguagem natural
            
        Returns:
            Lista de mapeamentos fuzzy encontrados
        """
        resultados_fuzzy = []
        
        # Extrair termos compostos
        termos_compostos = self._extrair_termos_compostos(consulta)
        
        for nome_mapper, mapper in self.mappers.items():
            try:
                for termo in termos_compostos:
                    mapeamentos_fuzzy = mapper.buscar_mapeamento_fuzzy(termo, threshold=0.7)
                    for mapeamento in mapeamentos_fuzzy[:2]:  # Máximo 2 por mapper
                        mapeamento['mapper_origem'] = nome_mapper
                        if mapeamento not in resultados_fuzzy:
                            resultados_fuzzy.append(mapeamento)
                            
            except Exception as e:
                logger.warning(f"Erro na busca fuzzy {nome_mapper}: {e}")
        
        return resultados_fuzzy
    
    def _extrair_termos_compostos(self, consulta: str) -> List[str]:
        """
        Extrai termos compostos para busca fuzzy.
        
        Args:
            consulta: Consulta em texto
            
        Returns:
            Lista de termos compostos
        """
        termos_compostos = []
        palavras = consulta.split()
        
        # Combinações de 2 palavras
        for i in range(len(palavras) - 1):
            termo_composto = f"{palavras[i]} {palavras[i+1]}"
            if len(termo_composto) > 4:
                termos_compostos.append(termo_composto)
        
        return termos_compostos
    
    def _calcular_confianca_integrada(self, campos_detectados: List[Dict[str, Any]], 
                                     mappers_consultados: List[str]) -> float:
        """
        Calcula confiança da análise semântica integrada.
        
        Args:
            campos_detectados: Lista de campos detectados
            mappers_consultados: Lista de mappers que encontraram resultados
            
        Returns:
            Score de confiança (0-1)
        """
        if not campos_detectados:
            return 0.0
        
        # Score base pelos matches
        score_total = 0.0
        for campo in campos_detectados:
            if campo.get('match_exacto', False):
                score_total += 1.0
            else:
                score_total += campo.get('score_similaridade', 0.5)
        
        # Normalizar
        confianca = min(score_total / len(campos_detectados), 1.0)
        
        # Bonus por diversidade de mappers (indica consulta abrangente)
        diversidade_bonus = len(mappers_consultados) / len(self.mappers)
        confianca = min(confianca + (diversidade_bonus * 0.1), 1.0)
        
        return round(confianca, 3)
    
    def _agrupar_por_mapper(self, campos_detectados: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Agrupa campos detectados por mapper de origem.
        
        Args:
            campos_detectados: Lista de campos detectados
            
        Returns:
            Dict com contagem por mapper
        """
        contagem = {}
        for campo in campos_detectados:
            mapper_origem = campo.get('mapper_origem', 'unknown')
            contagem[mapper_origem] = contagem.get(mapper_origem, 0) + 1
        
        return contagem
    
    def detectar_dominio_principal(self, consulta: str) -> Dict[str, Any]:
        """
        Detecta o domínio principal da consulta baseado nos mappers.
        
        Args:
            consulta: Consulta em linguagem natural
            
        Returns:
            Dict com domínio detectado e score
        """
        analise = self.analisar_consulta_semantica(consulta)
        matches_por_mapper = analise['matches_por_mapper']
        
        if not matches_por_mapper:
            return {'dominio': 'geral', 'score': 0.0, 'mappers_ativos': []}
        
        # Domínio com mais matches
        dominio_principal = max(matches_por_mapper, key=matches_por_mapper.get)
        score_dominio = matches_por_mapper[dominio_principal] / sum(matches_por_mapper.values())
        
        return {
            'dominio': dominio_principal,
            'score': round(score_dominio, 3),
            'mappers_ativos': list(matches_por_mapper.keys()),
            'distribuicao': matches_por_mapper
        }
    
    def obter_estatisticas_mappers(self) -> Dict[str, Any]:
        """
        Obtém estatísticas dos mappers específicos.
        
        Returns:
            Dict com estatísticas consolidadas
        """
        estatisticas = {
            'total_mappers': len(self.mappers),
            'mappers_ativos': list(self.mappers.keys()),
            'estatisticas_por_mapper': {}
        }
        
        total_campos = 0
        total_termos = 0
        
        for nome_mapper, mapper in self.mappers.items():
            try:
                stats = mapper.gerar_estatisticas()
                estatisticas['estatisticas_por_mapper'][nome_mapper] = stats
                total_campos += stats['total_campos']
                total_termos += stats['total_termos_naturais']
                
            except Exception as e:
                logger.warning(f"Erro ao gerar estatísticas {nome_mapper}: {e}")
        
        estatisticas['totais'] = {
            'total_campos': total_campos,
            'total_termos_naturais': total_termos,
            'media_campos_por_mapper': total_campos / len(self.mappers)
        }
        
        return estatisticas
    
    def initialize_with_schema(self, db_info: Dict[str, Any]):
        """
        Inicializa mappers com informações do schema do banco.
        
        Args:
            db_info: Informações do banco de dados
        """
        logger.info(f"🗺️ Inicializando mappers com schema do banco")
        
        if not db_info:
            logger.warning("Schema vazio fornecido")
            return
        
        # Se tem tabelas indexadas, otimizar
        if 'indexed_tables' in db_info:
            self._optimize_mappings_with_indexes(db_info['indexed_tables'])
            
        # Se tem informações de relacionamentos, usar
        if 'relationships' in db_info:
            logger.info(f"📊 Usando {len(db_info['relationships'])} relacionamentos do banco")
            
    def apply_auto_suggestions(self, scanning_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Aplica sugestões automáticas do scanner aos mappers.
        
        Args:
            scanning_info: Informações do scanner com sugestões automáticas
            
        Returns:
            Dict com estatísticas de aplicação
        """
        logger.info("🤖 Aplicando sugestões automáticas aos mappers")
        
        if not scanning_info:
            # Tenta obter do scanner se disponível
            try:
                from app.claude_ai_novo.scanning import get_database_manager
                scanner = get_database_manager()
                if scanner and scanner.esta_disponivel():
                    scanning_info = scanner.scan_database_structure()
            except Exception as e:
                logger.warning(f"Não foi possível obter scanner: {e}")
                return {'status': 'skipped', 'reason': 'scanner_unavailable'}
        
        if not scanning_info or 'tables' not in scanning_info:
            return {'status': 'skipped', 'reason': 'no_data'}
        
        estatisticas = {
            'tabelas_processadas': 0,
            'sugestoes_aplicadas': 0,
            'campos_melhorados': 0,
            'mappers_atualizados': set()
        }
        
        # Para cada tabela com sugestões
        for tabela, info in scanning_info.get('tables', {}).items():
            if 'auto_mapping' not in info:
                continue
                
            estatisticas['tabelas_processadas'] += 1
            
            # Identifica o mapper correto para esta tabela
            mapper_nome = self._identify_mapper_for_table(tabela)
            if not mapper_nome or mapper_nome not in self.mappers:
                continue
            
            mapper = self.mappers[mapper_nome]
            auto_mappings = info['auto_mapping']
            
            # Aplica sugestões campo por campo
            for campo, sugestoes in auto_mappings.items():
                if 'termos_sugeridos' in sugestoes:
                    # Adiciona termos sugeridos ao mapper
                    try:
                        if hasattr(mapper, 'adicionar_mapeamento'):
                            mapper.adicionar_mapeamento(
                                campo, 
                                sugestoes['termos_sugeridos']
                            )
                            estatisticas['sugestoes_aplicadas'] += 1
                            estatisticas['campos_melhorados'] += 1
                            estatisticas['mappers_atualizados'].add(mapper_nome)
                    except Exception as e:
                        logger.warning(f"Erro ao aplicar sugestão para {campo}: {e}")
        
        estatisticas['mappers_atualizados'] = list(estatisticas['mappers_atualizados'])
        
        logger.info(f"✅ Sugestões aplicadas: {estatisticas['sugestoes_aplicadas']} " +
                   f"em {len(estatisticas['mappers_atualizados'])} mappers")
        
        return estatisticas
    
    def _identify_mapper_for_table(self, table_name: str) -> Optional[str]:
        """
        Identifica qual mapper é responsável por uma tabela.
        
        Args:
            table_name: Nome da tabela
            
        Returns:
            Nome do mapper ou None
        """
        # Mapeamento simples baseado em padrões de nome
        mappings = {
            'pedidos': 'pedidos',
            'embarques': 'embarques',
            'entregas_monitoradas': 'monitoramento',
            'relatorio_faturamento_importado': 'faturamento',
            'transportadoras': 'transportadoras'
        }
        
        # Busca exata
        if table_name in mappings:
            return mappings[table_name]
        
        # Busca por prefixo
        for prefix, mapper in mappings.items():
            if table_name.startswith(prefix):
                return mapper
        
        return None
    
    def _optimize_mappings_with_indexes(self, tables_info: Dict[str, Any]):
        """Otimiza mapeamentos usando informações de índices"""
        # Identificar campos indexados para queries mais eficientes
        self.indexed_fields = {}
        
        for table_name, table_info in tables_info.items():
            if 'indexes' in table_info:
                self.indexed_fields[table_name] = [
                    idx.get('column') for idx in table_info['indexes']
                    if idx.get('column')
                ]
        
        logger.debug(f"📊 Campos indexados identificados: {len(self.indexed_fields)} tabelas")

def get_mapper_manager() -> MapperManager:
    """
    Retorna instância global do MapperManager.
    
    Returns:
        MapperManager: Instância do manager de mappers
    """
    global _mapper_manager_instance
    if _mapper_manager_instance is None:
        _mapper_manager_instance = MapperManager()
    return _mapper_manager_instance

# Aliases para compatibilidade
SemanticMapper = MapperManager  # Backward compatibility
MapeamentoSemantico = MapperManager

def get_semantic_mapper() -> MapperManager:
    """Alias para compatibilidade com código existente"""
    return get_mapper_manager()

def get_mapeamento_semantico() -> MapperManager:
    """Alias para compatibilidade com código existente"""
    return get_mapper_manager()

# Exports
__all__ = [
    'MapperManager',
    'get_mapper_manager',
    'SemanticMapper',  # Compatibilidade
    'get_semantic_mapper',  # Compatibilidade
    'MapeamentoSemantico',
    'get_mapeamento_semantico'
]

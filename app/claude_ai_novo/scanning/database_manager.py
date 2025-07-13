"""
📊 DATABASE SCANNER - Wrapper Principal Modularizado

Wrapper principal que integra todos os módulos especializados de leitura do banco de dados:
- DatabaseConnection: Gestão de conexões
- MetadataScanner: Leitura de metadados  
- DataAnalyzer: Análise de dados reais
- RelationshipMapper: Mapeamento de relacionamentos
- FieldSearcher: Busca de campos
- AutoMapper: Mapeamento automático

ANTES: 555 linhas monolíticas
DEPOIS: Wrapper modular usando 6 módulos especializados
"""

import logging
from typing import Dict, List, Optional, Any, Set, Union
from datetime import datetime

# Imports dos módulos especializados
from app.claude_ai_novo.scanning.database import (
    DatabaseConnection,
    MetadataScanner,
    DataAnalyzer,
    RelationshipMapper,
    FieldSearcher,
    AutoMapper
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Gerenciador principal de dados do banco - Wrapper Modularizado.
    
    Integra todos os módulos especializados fornecendo interface
    unificada compatível com a versão anterior.
    
    MÓDULOS INTEGRADOS:
    - DatabaseConnection: Conexões com banco
    - MetadataScanner: Metadados das tabelas
    - DataAnalyzer: Análise de dados reais  
    - RelationshipMapper: Relacionamentos
    - FieldSearcher: Busca de campos
    - AutoMapper: Mapeamento automático
    """
    
    def __init__(self, db_engine=None, db_session=None):
        """
        Inicializa o leitor modular do banco de dados.
        
        Args:
            db_engine: Engine do SQLAlchemy (opcional)
            db_session: Sessão do SQLAlchemy (opcional)
        """
        # Inicializar módulo de conexão
        self.connection = DatabaseConnection(db_engine, db_session)
        
        # Inicializar módulos especializados
        self.metadata_scanner = MetadataScanner(self.connection.get_inspector())
        self.data_analyzer = DataAnalyzer(self.connection.get_engine())
        self.relationship_mapper = RelationshipMapper(self.connection.get_inspector())
        self.field_searcher = FieldSearcher(
            self.connection.get_inspector(), 
            self.metadata_scanner
        )
        self.auto_mapper = AutoMapper(
            self.metadata_scanner,
            self.data_analyzer
        )
        
        # Propriedades de compatibilidade com versão anterior
        self.db_engine = self.connection.get_engine()
        self.db_session = self.connection.get_session()
        self.inspector = self.connection.get_inspector()
        self.tabelas_cache = {}  # Para compatibilidade
        self.modelos_cache = {}  # Para compatibilidade
        
        logger.info("🔍 DatabaseScanner modular inicializado com 6 módulos especializados")
    
    # ===== MÉTODOS DE COMPATIBILIDADE (Interface anterior) =====
    
    def listar_tabelas(self) -> List[str]:
        """
        Lista todas as tabelas disponíveis no banco.
        
        Returns:
            Lista de nomes das tabelas
        """
        return self.metadata_scanner.listar_tabelas()
    
    def obter_campos_tabela(self, nome_tabela: str) -> Dict[str, Any]:
        """
        Obtém informações detalhadas dos campos de uma tabela.
        
        Args:
            nome_tabela: Nome da tabela
            
        Returns:
            Dict com informações dos campos
        """
        return self.metadata_scanner.obter_campos_tabela(nome_tabela)
    
    def analisar_dados_reais(self, nome_tabela: str, nome_campo: str, limite: int = 100) -> Dict[str, Any]:
        """
        Analisa dados reais de um campo específico.
        
        Args:
            nome_tabela: Nome da tabela
            nome_campo: Nome do campo
            limite: Limite de registros para análise
            
        Returns:
            Dict com análise dos dados
        """
        return self.data_analyzer.analisar_dados_reais(nome_tabela, nome_campo, limite)
    
    def obter_relacionamentos(self, nome_tabela: str) -> List[Dict[str, Any]]:
        """
        Obtém relacionamentos de uma tabela.
        
        Args:
            nome_tabela: Nome da tabela
            
        Returns:
            Lista de relacionamentos
        """
        return self.relationship_mapper.obter_relacionamentos(nome_tabela)
    
    def buscar_campos_por_tipo(self, tipo_campo: str) -> List[Dict[str, str]]:
        """
        Busca campos por tipo em todas as tabelas.
        
        Args:
            tipo_campo: Tipo do campo a buscar
            
        Returns:
            Lista de campos encontrados
        """
        campos = self.field_searcher.buscar_campos_por_tipo(tipo_campo)
        
        # Converter para formato de compatibilidade
        return [
            {
                'tabela': campo['tabela'],
                'campo': campo['campo'],
                'tipo': campo['tipo'],
                'nulo': campo.get('nulo', True)
            }
            for campo in campos
        ]
    
    def buscar_campos_por_nome(self, nome_padrao: str) -> List[Dict[str, str]]:
        """
        Busca campos por padrão de nome em todas as tabelas.
        
        Args:
            nome_padrao: Padrão do nome a buscar
            
        Returns:
            Lista de campos encontrados
        """
        campos = self.field_searcher.buscar_campos_por_nome(nome_padrao)
        
        # Converter para formato de compatibilidade
        return [
            {
                'tabela': campo['tabela'],
                'campo': campo['campo'],
                'tipo': campo['tipo'],
                'tipo_python': campo['tipo_python'],
                'match_score': campo['match_score']
            }
            for campo in campos
        ]
    
    def gerar_mapeamento_automatico(self, nome_tabela: str) -> Dict[str, Any]:
        """
        Gera mapeamento automático básico para uma tabela.
        
        Args:
            nome_tabela: Nome da tabela
            
        Returns:
            Dict com mapeamento automático
        """
        return self.auto_mapper.gerar_mapeamento_automatico(nome_tabela)
    
    def esta_disponivel(self) -> bool:
        """
        Verifica se o leitor está disponível.
        
        Returns:
            True se disponível
        """
        return self.connection.is_connected()
    
    # ===== MÉTODOS AVANÇADOS (Novos recursos dos módulos especializados) =====
    
    def obter_estatisticas_gerais(self) -> Dict[str, Any]:
        """
        Obtém estatísticas gerais do banco de dados.
        
        Returns:
            Dict com estatísticas completas
        """
        if not self.connection.is_connected():
            return {'erro': 'Conexão não disponível'}
        
        try:
            # Estatísticas básicas
            estatisticas_metadata = self.metadata_scanner.obter_estatisticas_tabelas()
            
            # Informações de conexão
            info_conexao = self.connection.get_connection_info()
            
            # Estatísticas de relacionamentos
            grafo_relacionamentos = self.relationship_mapper.mapear_grafo_relacionamentos()
            
            return {
                'conexao': info_conexao,
                'metadata': estatisticas_metadata,
                'relacionamentos': grafo_relacionamentos.get('estatisticas', {}),
                'modulos': {
                    'metadata_scanner': self.metadata_scanner.is_available(),
                    'data_analyzer': self.data_analyzer.is_available(),
                    'relationship_mapper': self.relationship_mapper.is_available(),
                    'field_searcher': self.field_searcher.is_available(),
                    'auto_mapper': self.auto_mapper.is_available()
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas gerais: {e}")
            return {'erro': str(e)}
    
    def analisar_tabela_completa(self, nome_tabela: str) -> Dict[str, Any]:
        """
        Análise completa de uma tabela (metadados + dados + relacionamentos).
        
        Args:
            nome_tabela: Nome da tabela
            
        Returns:
            Dict com análise completa
        """
        try:
            # Análise completa usando módulo especializado
            analise_completa = self.data_analyzer.analisar_tabela_completa(nome_tabela)
            
            # Adicionar relacionamentos
            relacionamentos = self.relationship_mapper.obter_relacionamentos(nome_tabela)
            analise_completa['relacionamentos'] = relacionamentos
            
            # Adicionar mapeamento automático
            mapeamento_auto = self.auto_mapper.gerar_mapeamento_automatico(nome_tabela)
            analise_completa['mapeamento_automatico'] = mapeamento_auto
            
            return analise_completa
            
        except Exception as e:
            logger.error(f"❌ Erro na análise completa de {nome_tabela}: {e}")
            return {'erro': str(e)}
    
    def mapear_grafo_relacionamentos(self) -> Dict[str, Any]:
        """
        Mapeia o grafo completo de relacionamentos do banco.
        
        Returns:
            Dict com grafo de relacionamentos
        """
        return self.relationship_mapper.mapear_grafo_relacionamentos()
    
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
        return self.field_searcher.buscar_campos_similares(
            tabela_referencia, campo_referencia, limite_score
        )
    
    def gerar_mapeamento_multiplas_tabelas(self, nomes_tabelas: List[str]) -> Dict[str, Any]:
        """
        Gera mapeamento automático para múltiplas tabelas.
        
        Args:
            nomes_tabelas: Lista de nomes das tabelas
            
        Returns:
            Dict com mapeamentos de todas as tabelas
        """
        return self.auto_mapper.gerar_mapeamento_multiplas_tabelas(nomes_tabelas)
    
    def obter_caminho_relacionamentos(self, tabela_origem: str, tabela_destino: str) -> List[str]:
        """
        Encontra caminho de relacionamentos entre duas tabelas.
        
        Args:
            tabela_origem: Tabela de origem
            tabela_destino: Tabela de destino
            
        Returns:
            Lista com caminho de tabelas
        """
        return self.relationship_mapper.obter_caminho_relacionamentos(tabela_origem, tabela_destino)
    
    # ===== MÉTODOS DE GERENCIAMENTO =====
    
    def limpar_cache(self) -> None:
        """
        Limpa todos os caches dos módulos.
        """
        self.metadata_scanner.limpar_cache()
        self.data_analyzer.limpar_cache()
        self.relationship_mapper.limpar_cache()
        self.field_searcher.limpar_cache()
        self.auto_mapper.limpar_cache()
        
        # Limpar caches de compatibilidade
        self.tabelas_cache.clear()
        self.modelos_cache.clear()
        
        logger.info("🧹 Todos os caches dos módulos foram limpos")
    
    def recarregar_conexao(self) -> bool:
        """
        Recarrega a conexão com o banco e atualiza módulos.
        
        Returns:
            True se recarregamento bem-sucedido
        """
        try:
            # Fechar conexão atual
            self.connection.close_connection()
            
            # Reestabelecer conexão
            self.connection._establish_connection()
            
            # Atualizar módulos com nova conexão
            inspector = self.connection.get_inspector()
            engine = self.connection.get_engine()
            
            if inspector is not None:
                self.metadata_scanner.set_inspector(inspector)
                self.relationship_mapper.set_inspector(inspector)
                self.field_searcher.set_inspector(inspector)
            
            if engine is not None:
                self.data_analyzer.set_engine(engine)
            self.field_searcher.set_metadata_scanner(self.metadata_scanner)
            self.auto_mapper.set_metadata_scanner(self.metadata_scanner)
            self.auto_mapper.set_data_analyzer(self.data_analyzer)
            
            # Atualizar propriedades de compatibilidade
            self.db_engine = self.connection.get_engine()
            self.db_session = self.connection.get_session()
            self.inspector = self.connection.get_inspector()
            
            # Limpar caches
            self.limpar_cache()
            
            logger.info("🔄 Conexão recarregada e módulos atualizados")
            return self.connection.is_connected()
            
        except Exception as e:
            logger.error(f"❌ Erro ao recarregar conexão: {e}")
            return False
    
    def scan_database_structure(self) -> Dict[str, Any]:
        """Escaneia a estrutura completa do banco de dados"""
        try:
            # Obter todas as tabelas
            tabelas = self.listar_tabelas()
            
            estrutura = {
                'tables': {},
                'total_tables': len(tabelas),
                'relationships': {},
                'statistics': {}
            }
            
            # Escanear cada tabela
            for tabela in tabelas:
                try:
                    # Obter informações da tabela
                    info_tabela = self.analisar_tabela_completa(tabela)
                    estrutura['tables'][tabela] = info_tabela
                    
                    # Obter relacionamentos
                    relacionamentos = self.obter_relacionamentos(tabela)
                    if relacionamentos:
                        estrutura['relationships'][tabela] = relacionamentos
                        
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao escanear tabela {tabela}: {e}")
                    
            # Adicionar estatísticas gerais
            estrutura['statistics'] = self.obter_estatisticas_gerais()
            
            return estrutura
            
        except Exception as e:
            logger.error(f"❌ Erro ao escanear estrutura do banco: {e}")
            return {}
    
    def obter_info_modulos(self) -> Dict[str, Any]:
        """
        Obtém informações sobre todos os módulos.
        
        Returns:
            Dict com informações dos módulos
        """
        return {
            'connection': {
                'disponivel': self.connection.is_connected(),
                'metodo_conexao': self.connection.connection_method,
                'inspector_disponivel': self.connection.is_inspector_available()
            },
            'metadata_scanner': {
                'disponivel': self.metadata_scanner.is_available(),
                'cache_size': len(self.metadata_scanner.tabelas_cache)
            },
            'data_analyzer': {
                'disponivel': self.data_analyzer.is_available(),
                'cache_size': len(self.data_analyzer.analysis_cache)
            },
            'relationship_mapper': {
                'disponivel': self.relationship_mapper.is_available(),
                'cache_size': len(self.relationship_mapper.relationships_cache)
            },
            'field_searcher': {
                'disponivel': self.field_searcher.is_available(),
                'cache_size': len(self.field_searcher.search_cache)
            },
            'auto_mapper': {
                'disponivel': self.auto_mapper.is_available(),
                'cache_size': len(self.auto_mapper.mapping_cache)
            }
        }
    
    # ===== MÉTODOS DE COMPATIBILIDADE ADICIONAL =====
    
    def _normalizar_tipo_sqlalchemy(self, tipo_sqlalchemy: str) -> str:
        """Método de compatibilidade - usa MetadataScanner"""
        return self.metadata_scanner._normalizar_tipo_sqlalchemy(tipo_sqlalchemy)
    
    def _calcular_score_match(self, nome_campo: str, nome_padrao: str) -> float:
        """Método de compatibilidade - usa FieldSearcher"""
        return self.field_searcher._calcular_score_match_nome(nome_campo, nome_padrao, 'contains')
    
    def _gerar_termos_automaticos(self, nome_campo: str) -> List[str]:
        """Método de compatibilidade - usa AutoMapper"""
        info_campo = {'tipo_python': 'string', 'nulo': True, 'chave_primaria': False}
        return self.auto_mapper._gerar_termos_automaticos(nome_campo, info_campo)
    
    def __str__(self) -> str:
        """Representação string do DatabaseManager"""
        status = "conectado" if self.esta_disponivel() else "desconectado"
        return f"DatabaseManager(status={status}, metodo={self.connection.connection_method})"
    
    def __repr__(self) -> str:
        """Representação detalhada do DatabaseManager"""
        return f"DatabaseManager(engine={self.db_engine is not None}, session={self.db_session is not None}, modulos=6)"


# Exportações principais
__all__ = [
    'DatabaseManager'
] 
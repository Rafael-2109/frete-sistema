"""
📊 DATA ANALYZER - Análise de Dados Reais

Módulo responsável por analisar dados reais das tabelas:
- Estatísticas de preenchimento
- Análise de valores únicos
- Exemplos de dados
- Distribuição de valores
"""

import logging
from typing import Dict, List, Any, Optional, Union
try:
    from sqlalchemy import text, func
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    text, func = None
    SQLALCHEMY_AVAILABLE = False
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class DataAnalyzer:
    """
    Analisador de dados reais das tabelas.
    
    Responsável por extrair estatísticas e insights
    dos dados reais armazenados no banco.
    """
    
    def __init__(self, db_engine: Optional[Engine] = None):
        """
        Inicializa o analisador de dados.
        
        Args:
            db_engine: Engine do SQLAlchemy
        """
        self.db_engine = db_engine
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}
        self._field_types_cache: Dict[str, str] = {}
    
    def set_engine(self, db_engine: Engine) -> None:
        """
        Define o engine a ser usado.
        
        Args:
            db_engine: Engine do SQLAlchemy
        """
        self.db_engine = db_engine
        self.analysis_cache.clear()  # Limpar cache ao trocar engine
        self._field_types_cache.clear()  # Limpar cache de tipos
    
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
        if not self.db_engine:
            logger.error("❌ Engine do banco não disponível")
            return {}
        
        cache_key = f"{nome_tabela}.{nome_campo}"
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]
        
        try:
            # Análise básica
            analise_basica = self._analisar_estatisticas_basicas(nome_tabela, nome_campo)
            
            # Exemplos de valores
            exemplos = self._obter_exemplos_valores(nome_tabela, nome_campo, limite)
            
            # Análise de distribuição
            distribuicao = self._analisar_distribuicao(nome_tabela, nome_campo)
            
            # Análise de padrões
            padroes = self._analisar_padroes(nome_tabela, nome_campo)
            
            analise_completa = {
                'tabela': nome_tabela,
                'campo': nome_campo,
                **analise_basica,
                'exemplos': exemplos,
                'distribuicao': distribuicao,
                'padroes': padroes,
                'cache_timestamp': self._get_timestamp()
            }
            
            # Cache da análise
            self.analysis_cache[cache_key] = analise_completa
            
            logger.debug(f"📊 Análise {cache_key}: {analise_completa.get('percentual_preenchimento', 0):.1f}% preenchido")
            return analise_completa
            
        except Exception as e:
            logger.error(f"❌ Erro ao analisar dados de {nome_tabela}.{nome_campo}: {e}")
            return {}
    
    def _get_field_type(self, nome_tabela: str, nome_campo: str) -> str:
        """
        Obtém o tipo de um campo específico.
        
        Args:
            nome_tabela: Nome da tabela
            nome_campo: Nome do campo
            
        Returns:
            Tipo do campo
        """
        cache_key = f"{nome_tabela}.{nome_campo}"
        if cache_key in self._field_types_cache:
            return self._field_types_cache[cache_key]
        
        try:
            query = text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = :tabela 
                AND column_name = :campo
            """)
            
            with self.db_engine.connect() as conn:
                result = conn.execute(query, {'tabela': nome_tabela, 'campo': nome_campo}).fetchone()
                if result:
                    tipo = result[0]
                    self._field_types_cache[cache_key] = tipo
                    return tipo
                    
        except Exception as e:
            logger.error(f"Erro ao obter tipo do campo {nome_tabela}.{nome_campo}: {e}")
        
        return 'unknown'
    
    def _is_json_type(self, tipo_campo: str) -> bool:
        """
        Verifica se o campo é do tipo JSON/JSONB.
        
        Args:
            tipo_campo: Tipo do campo
            
        Returns:
            True se for JSON/JSONB
        """
        tipo_lower = str(tipo_campo).lower()
        return 'json' in tipo_lower or 'jsonb' in tipo_lower
    
    def _analisar_estatisticas_basicas(self, nome_tabela: str, nome_campo: str) -> Dict[str, Any]:
        """
        Analisa estatísticas básicas de um campo.
        
        Args:
            nome_tabela: Nome da tabela
            nome_campo: Nome do campo
            
        Returns:
            Dict com estatísticas básicas
        """
        try:
            # Verificar se é campo JSON
            tipo_campo = self._get_field_type(nome_tabela, nome_campo)
            
            if self._is_json_type(tipo_campo):
                # Para campos JSON, usar query específica sem COUNT DISTINCT
                query = text(f"""
                    SELECT 
                        COUNT(*) as total_registros,
                        COUNT({nome_campo}) as valores_nao_nulos,
                        COUNT(*) - COUNT({nome_campo}) as valores_nulos
                    FROM {nome_tabela}
                """)
                
                with self.db_engine.connect() as conn:
                    resultado = conn.execute(query).fetchone()
                    
                    if not resultado:
                        return {}
                    
                    total_registros = resultado[0]
                    valores_nao_nulos = resultado[1]
                    valores_nulos = resultado[2]
                    
                    return {
                        'total_registros': total_registros,
                        'valores_unicos': -1,  # Não calculável para JSON
                        'valores_nao_nulos': valores_nao_nulos,
                        'valores_nulos': valores_nulos,
                        'percentual_preenchimento': (valores_nao_nulos / total_registros * 100) if total_registros > 0 else 0,
                        'percentual_unicidade': -1,  # Não calculável para JSON
                        'tem_valores_duplicados': None,  # Não determinável para JSON
                        'tipo_campo': 'json'
                    }
            else:
                # Para campos não-JSON, usar query original
                query = text(f"""
                    SELECT 
                        COUNT(*) as total_registros,
                        COUNT(DISTINCT {nome_campo}) as valores_unicos,
                        COUNT({nome_campo}) as valores_nao_nulos,
                        COUNT(*) - COUNT({nome_campo}) as valores_nulos
                    FROM {nome_tabela}
                """)
                
                with self.db_engine.connect() as conn:
                    resultado = conn.execute(query).fetchone()
                    
                    if not resultado:
                        return {}
                    
                    total_registros = resultado[0]
                    valores_unicos = resultado[1]
                    valores_nao_nulos = resultado[2]
                    valores_nulos = resultado[3]
                    
                    return {
                        'total_registros': total_registros,
                        'valores_unicos': valores_unicos,
                        'valores_nao_nulos': valores_nao_nulos,
                        'valores_nulos': valores_nulos,
                        'percentual_preenchimento': (valores_nao_nulos / total_registros * 100) if total_registros > 0 else 0,
                        'percentual_unicidade': (valores_unicos / valores_nao_nulos * 100) if valores_nao_nulos > 0 else 0,
                        'tem_valores_duplicados': valores_unicos < valores_nao_nulos
                    }
                
        except Exception as e:
            logger.error(f"❌ Erro nas estatísticas básicas de {nome_tabela}.{nome_campo}: {e}")
            return {}
    
    def _obter_exemplos_valores(self, nome_tabela: str, nome_campo: str, limite: int = 100) -> List[str]:
        """
        Obtém exemplos de valores de um campo.
        
        Args:
            nome_tabela: Nome da tabela
            nome_campo: Nome do campo
            limite: Limite de exemplos
            
        Returns:
            Lista de exemplos
        """
        try:
            # Verificar se é campo JSON
            tipo_campo = self._get_field_type(nome_tabela, nome_campo)
            
            if self._is_json_type(tipo_campo):
                # Para campos JSON, converter para texto e não usar ORDER BY direto
                query = text(f"""
                    SELECT DISTINCT {nome_campo}::text 
                    FROM {nome_tabela} 
                    WHERE {nome_campo} IS NOT NULL 
                    LIMIT {limite}
                """)
            else:
                # Para campos não-JSON, usar query original
                query = text(f"""
                    SELECT DISTINCT {nome_campo} 
                    FROM {nome_tabela} 
                    WHERE {nome_campo} IS NOT NULL 
                    ORDER BY {nome_campo} 
                    LIMIT {limite}
                """)
            
            with self.db_engine.connect() as conn:
                resultados = conn.execute(query).fetchall()
                exemplos = [str(resultado[0]) for resultado in resultados]
                
                return exemplos
                
        except Exception as e:
            logger.error(f"❌ Erro ao obter exemplos de {nome_tabela}.{nome_campo}: {e}")
            return []
    
    def _analisar_distribuicao(self, nome_tabela: str, nome_campo: str) -> Dict[str, Any]:
        """
        Analisa a distribuição de valores de um campo.
        
        Args:
            nome_tabela: Nome da tabela
            nome_campo: Nome do campo
            
        Returns:
            Dict com análise de distribuição
        """
        try:
            # Verificar se é campo JSON
            tipo_campo = self._get_field_type(nome_tabela, nome_campo)
            
            if self._is_json_type(tipo_campo):
                # Para campos JSON, análise simplificada
                return {
                    'valores_mais_frequentes': [],
                    'comprimento': {},
                    'tipo_campo': 'json',
                    'nota': 'Análise de distribuição não disponível para campos JSON'
                }
            else:
                # Para campos não-JSON, usar query com alias para evitar ambiguidade
                query_frequencia = text(f"""
                    SELECT {nome_campo} as valor_campo, COUNT(*) as freq_count
                    FROM {nome_tabela}
                    WHERE {nome_campo} IS NOT NULL
                    GROUP BY {nome_campo}
                    ORDER BY freq_count DESC
                    LIMIT 10
                """)
                
                with self.db_engine.connect() as conn:
                    resultados = conn.execute(query_frequencia).fetchall()
                    
                    valores_frequentes = [
                        {'valor': str(resultado[0]), 'frequencia': resultado[1]}
                        for resultado in resultados
                    ]
                    
                    # Análise de comprimento (para strings)
                    analise_comprimento = self._analisar_comprimento_valores(nome_tabela, nome_campo)
                    
                    return {
                        'valores_mais_frequentes': valores_frequentes,
                        'comprimento': analise_comprimento
                    }
                
        except Exception as e:
            logger.error(f"❌ Erro na análise de distribuição de {nome_tabela}.{nome_campo}: {e}")
            return {}
    
    def _analisar_comprimento_valores(self, nome_tabela: str, nome_campo: str) -> Dict[str, Any]:
        """
        Analisa o comprimento dos valores de um campo.
        
        Args:
            nome_tabela: Nome da tabela
            nome_campo: Nome do campo
            
        Returns:
            Dict com análise de comprimento
        """
        try:
            query = text(f"""
                SELECT 
                    MIN(LENGTH({nome_campo}::text)) as comprimento_minimo,
                    MAX(LENGTH({nome_campo}::text)) as comprimento_maximo,
                    AVG(LENGTH({nome_campo}::text)) as comprimento_medio
                FROM {nome_tabela}
                WHERE {nome_campo} IS NOT NULL
            """)
            
            with self.db_engine.connect() as conn:
                resultado = conn.execute(query).fetchone()
                
                if resultado:
                    return {
                        'comprimento_minimo': resultado[0],
                        'comprimento_maximo': resultado[1],
                        'comprimento_medio': round(resultado[2], 2) if resultado[2] else 0
                    }
                
        except Exception as e:
            logger.debug(f"⚠️ Erro na análise de comprimento de {nome_tabela}.{nome_campo}: {e}")
            
        return {}
    
    def _analisar_padroes(self, nome_tabela: str, nome_campo: str) -> Dict[str, Any]:
        """
        Analisa padrões nos valores de um campo.
        
        Args:
            nome_tabela: Nome da tabela
            nome_campo: Nome do campo
            
        Returns:
            Dict com análise de padrões
        """
        try:
            padroes = {}
            
            # Verificar se campo contém apenas números
            padroes['apenas_numeros'] = self._verificar_padrao_numerico(nome_tabela, nome_campo)
            
            # Verificar se campo contém datas
            padroes['formato_data'] = self._verificar_padrao_data(nome_tabela, nome_campo)
            
            # Verificar se campo contém emails
            padroes['formato_email'] = self._verificar_padrao_email(nome_tabela, nome_campo)
            
            # Verificar se campo contém URLs
            padroes['formato_url'] = self._verificar_padrao_url(nome_tabela, nome_campo)
            
            return padroes
            
        except Exception as e:
            logger.error(f"❌ Erro na análise de padrões de {nome_tabela}.{nome_campo}: {e}")
            return {}
    
    def _verificar_padrao_numerico(self, nome_tabela: str, nome_campo: str) -> bool:
        """
        Verifica se o campo contém apenas números.
        
        Args:
            nome_tabela: Nome da tabela
            nome_campo: Nome do campo
            
        Returns:
            True se campo é numérico
        """
        try:
            query = text(f"""
                SELECT COUNT(*) as total, 
                       COUNT(CASE WHEN {nome_campo}::text ~ '^[0-9]+$' THEN 1 END) as numericos
                FROM {nome_tabela}
                WHERE {nome_campo} IS NOT NULL
                LIMIT 100
            """)
            
            with self.db_engine.connect() as conn:
                resultado = conn.execute(query).fetchone()
                
                if resultado and resultado[0] > 0:
                    return resultado[1] / resultado[0] > 0.8  # 80% numérico
                    
        except Exception:
            pass
            
        return False
    
    def _verificar_padrao_data(self, nome_tabela: str, nome_campo: str) -> bool:
        """
        Verifica se o campo contém datas.
        
        Args:
            nome_tabela: Nome da tabela
            nome_campo: Nome do campo
            
        Returns:
            True se campo contém datas
        """
        try:
            query = text(f"""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN {nome_campo}::text ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}' THEN 1 END) as datas
                FROM {nome_tabela}
                WHERE {nome_campo} IS NOT NULL
                LIMIT 100
            """)
            
            with self.db_engine.connect() as conn:
                resultado = conn.execute(query).fetchone()
                
                if resultado and resultado[0] > 0:
                    return resultado[1] / resultado[0] > 0.8  # 80% datas
                    
        except Exception:
            pass
            
        return False
    
    def _verificar_padrao_email(self, nome_tabela: str, nome_campo: str) -> bool:
        """
        Verifica se o campo contém emails.
        
        Args:
            nome_tabela: Nome da tabela
            nome_campo: Nome do campo
            
        Returns:
            True se campo contém emails
        """
        try:
            query = text(f"""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN {nome_campo}::text ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{{2,}}$' THEN 1 END) as emails
                FROM {nome_tabela}
                WHERE {nome_campo} IS NOT NULL
                LIMIT 100
            """)
            
            with self.db_engine.connect() as conn:
                resultado = conn.execute(query).fetchone()
                
                if resultado and resultado[0] > 0:
                    return resultado[1] / resultado[0] > 0.8  # 80% emails
                    
        except Exception:
            pass
            
        return False
    
    def _verificar_padrao_url(self, nome_tabela: str, nome_campo: str) -> bool:
        """
        Verifica se o campo contém URLs.
        
        Args:
            nome_tabela: Nome da tabela
            nome_campo: Nome do campo
            
        Returns:
            True se campo contém URLs
        """
        try:
            query = text(f"""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN {nome_campo}::text ~ '^https?://' THEN 1 END) as urls
                FROM {nome_tabela}
                WHERE {nome_campo} IS NOT NULL
                LIMIT 100
            """)
            
            with self.db_engine.connect() as conn:
                resultado = conn.execute(query).fetchone()
                
                if resultado and resultado[0] > 0:
                    return resultado[1] / resultado[0] > 0.8  # 80% URLs
                    
        except Exception:
            pass
            
        return False
    
    def _get_timestamp(self) -> str:
        """
        Retorna timestamp atual.
        
        Returns:
            Timestamp formatado
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def analisar_tabela_completa(self, nome_tabela: str) -> Dict[str, Any]:
        """
        Analisa todos os campos de uma tabela.
        
        Args:
            nome_tabela: Nome da tabela
            
        Returns:
            Dict com análise completa da tabela
        """
        if not self.db_engine:
            logger.error("❌ Engine do banco não disponível")
            return {}
        
        # Usar MetadataScanner para obter campos
        try:
            from app.claude_ai_novo.scanning.database.metadata_scanner import MetadataScanner
            from app.claude_ai_novo.scanning.database.database_connection import DatabaseConnection
            
            # Criar conexão temporária
            db_conn = DatabaseConnection(self.db_engine)
            metadata_scanner = MetadataScanner(db_conn.get_inspector())
            
            # Obter campos da tabela
            info_tabela = metadata_scanner.obter_campos_tabela(nome_tabela)
            
            if not info_tabela:
                return {}
            
            # Analisar cada campo
            analises_campos = {}
            for nome_campo in info_tabela['campos'].keys():
                analises_campos[nome_campo] = self.analisar_dados_reais(nome_tabela, nome_campo, limite=50)
            
            return {
                'tabela': nome_tabela,
                'metadata': info_tabela,
                'analises_campos': analises_campos,
                'timestamp': self._get_timestamp()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao analisar tabela completa {nome_tabela}: {e}")
            return {}
    
    def limpar_cache(self) -> None:
        """
        Limpa o cache de análises.
        """
        self.analysis_cache.clear()
        logger.debug("🧹 Cache de análises limpo")
    
    def is_available(self) -> bool:
        """
        Verifica se o analisador está disponível.
        
        Returns:
            True se disponível
        """
        return self.db_engine is not None


# Exportações principais
__all__ = [
    'DataAnalyzer'
] 
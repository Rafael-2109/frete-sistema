"""
📋 METADATA SCANNER - Leitura de Metadados das Tabelas

Módulo responsável por ler metadados das tabelas do banco de dados:
- Lista de tabelas
- Informações de campos
- Tipos de dados
- Constraints e propriedades
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.engine.reflection import Inspector

logger = logging.getLogger(__name__)


class MetadataScanner:
    """
    Scanner de metadados das tabelas do banco.
    
    Responsável por extrair informações estruturais
    das tabelas como campos, tipos, constraints, etc.
    """
    
    def __init__(self, inspector: Optional[Inspector] = None):
        """
        Inicializa o scanner de metadados.
        
        Args:
            inspector: Inspector do SQLAlchemy para inspeção do banco
        """
        self.inspector = inspector
        self.tabelas_cache: Dict[str, Dict[str, Any]] = {}
    
    def set_inspector(self, inspector: Inspector) -> None:
        """
        Define o inspector a ser usado para inspeção do banco.
        
        Args:
            inspector: Inspector do SQLAlchemy
        """
        self.inspector = inspector
        self.tabelas_cache.clear()  # Limpar cache ao trocar inspector para novas inspeções
    
    def listar_tabelas(self) -> List[str]:
        """
        Lista todas as tabelas disponíveis no banco de dados.
        
        Returns:
            Lista de nomes das tabelas
        """
        if not self.inspector:
            logger.error("❌ Inspector não disponível")
            return []
        
        try:
            tabelas = self.inspector.get_table_names()
            logger.info(f"📋 Encontradas {len(tabelas)} tabelas no banco")
            return tabelas
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar tabelas: {e}")
            return []
    
    def obter_campos_tabela(self, nome_tabela: str) -> Dict[str, Any]:
        """
        Obtém informações detalhadas dos campos de uma tabela do banco de dados.
        
        Args:
            nome_tabela: Nome da tabela
            
        Returns:
            Dict com informações dos campos da tabela
        """
        if not self.inspector:
            logger.error("❌ Inspector não disponível")
            return {}
        
        # Usar cache se disponível para evitar múltiplas inspeções
        if nome_tabela in self.tabelas_cache:
            return self.tabelas_cache[nome_tabela]
        
        try:
            colunas = self.inspector.get_columns(nome_tabela)
            
            info_tabela = {
                'nome_tabela': nome_tabela,
                'total_campos': len(colunas),
                'campos': {}
            }
            
            for coluna in colunas:
                nome_campo = coluna['name']
                tipo_campo = str(coluna['type'])
                
                info_tabela['campos'][nome_campo] = {
                    'nome': nome_campo,
                    'tipo': tipo_campo,
                    'tipo_python': self._normalizar_tipo_sqlalchemy(tipo_campo),
                    'nulo': coluna.get('nullable', True),
                    'chave_primaria': coluna.get('primary_key', False),
                    'default': coluna.get('default'),
                    'tamanho': getattr(coluna['type'], 'length', None),
                    'autoincrement': coluna.get('autoincrement', False),
                    'comment': coluna.get('comment', '')
                }
            
            # Adicionar informações de índices
            info_tabela['indices'] = self._obter_indices_tabela(nome_tabela)
            
            # Adicionar informações de constraints
            info_tabela['constraints'] = self._obter_constraints_tabela(nome_tabela)
            
            # Cache da tabela
            self.tabelas_cache[nome_tabela] = info_tabela
            
            logger.debug(f"📊 Tabela {nome_tabela}: {len(colunas)} campos mapeados")
            return info_tabela
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter campos da tabela {nome_tabela}: {e}")
            return {}
    
    def _normalizar_tipo_sqlalchemy(self, tipo_sqlalchemy: str) -> str:
        """
        Normaliza tipos do SQLAlchemy para tipos Python simples para facilitar comparações.
        
        Args:
            tipo_sqlalchemy: Tipo original do SQLAlchemy
            
        Returns:
            Tipo normalizado
        """
        tipo_lower = str(tipo_sqlalchemy).lower()
        
        # Mapeamento de tipos
        mapeamentos = {
            'string': ['varchar', 'text', 'char', 'string'],
            'integer': ['integer', 'bigint', 'int', 'smallint'],
            'decimal': ['decimal', 'numeric', 'float', 'real', 'double'],
            'boolean': ['boolean', 'bool'],
            'date': ['date'],
            'datetime': ['datetime', 'timestamp', 'timestamptz'],
            'time': ['time'],
            'uuid': ['uuid'],
            'json': ['json', 'jsonb'],
            'binary': ['binary', 'bytea', 'blob']
        }
        
        for tipo_python, tipos_sql in mapeamentos.items():
            if any(t in tipo_lower for t in tipos_sql):
                return tipo_python
        
        return 'string'  # Fallback
    
    def _obter_indices_tabela(self, nome_tabela: str) -> List[Dict[str, Any]]:
        """
        Obtém índices de uma tabela do banco de dados.
        
        Args:
            nome_tabela: Nome da tabela
            
        Returns:
            Lista de índices
        """
        if not self.inspector:
            return []
        
        try:
            indices = self.inspector.get_indexes(nome_tabela)
            
            indices_info = []
            for indice in indices:
                indice_info = {
                    'nome': indice.get('name', ''),
                    'colunas': indice.get('column_names', []),
                    'unique': indice.get('unique', False),
                    'tipo': indice.get('type', ''),
                    'partial': indice.get('partial', False)
                }
                indices_info.append(indice_info)
            
            return indices_info
            
        except Exception as e:
            logger.debug(f"⚠️ Erro ao obter índices de {nome_tabela}: {e}")
            return []
    
    def _obter_constraints_tabela(self, nome_tabela: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Obtém constraints de uma tabela do banco de dados.
        
        Args:
            nome_tabela: Nome da tabela
            
        Returns:
            Dict com constraints por tipo
        """
        if not self.inspector:
            return {}
        
        constraints = {
            'primary_key': [],
            'foreign_keys': [],
            'unique': [],
            'check': []
        }
        
        try:
            # Primary key
            pk = self.inspector.get_pk_constraint(nome_tabela)
            if pk:
                constraints['primary_key'].append({
                    'nome': pk.get('name', ''),
                    'colunas': pk.get('constrained_columns', [])
                })
            
            # Foreign keys
            fks = self.inspector.get_foreign_keys(nome_tabela)
            for fk in fks:
                constraints['foreign_keys'].append({
                    'nome': fk.get('name', ''),
                    'colunas': fk.get('constrained_columns', []),
                    'tabela_ref': fk.get('referred_table', ''),
                    'colunas_ref': fk.get('referred_columns', [])
                })
            
            # Unique constraints
            uqs = self.inspector.get_unique_constraints(nome_tabela)
            for uq in uqs:
                constraints['unique'].append({
                    'nome': uq.get('name', ''),
                    'colunas': uq.get('column_names', [])
                })
            
            # Check constraints
            cks = self.inspector.get_check_constraints(nome_tabela)
            for ck in cks:
                constraints['check'].append({
                    'nome': ck.get('name', ''),
                    'sqltext': ck.get('sqltext', '')
                })
            
        except Exception as e:
            logger.debug(f"⚠️ Erro ao obter constraints de {nome_tabela}: {e}")
        
        return constraints
    
    def obter_tipos_campo_disponiveis(self) -> Dict[str, int]:
        """
        Obtém estatísticas dos tipos de campos disponíveis no banco de dados.
        
        Returns:
            Dict com contagem por tipo
        """
        if not self.inspector:
            return {}
        
        tipos_count = {}
        tabelas = self.listar_tabelas()
        
        for tabela in tabelas:
            info_tabela = self.obter_campos_tabela(tabela)
            
            for campo_info in info_tabela.get('campos', {}).values():
                tipo = campo_info['tipo_python']
                tipos_count[tipo] = tipos_count.get(tipo, 0) + 1
        
        return tipos_count
    
    def obter_estatisticas_tabelas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas gerais das tabelas do banco de dados.
        
        Returns:
            Dict com estatísticas
        """
        if not self.inspector:
            return {}
        
        tabelas = self.listar_tabelas()
        total_campos = 0
        campos_por_tabela = {}
        tipos_distribuicao = {}
        
        for tabela in tabelas:
            info_tabela = self.obter_campos_tabela(tabela)
            num_campos = info_tabela.get('total_campos', 0)
            
            total_campos += num_campos
            campos_por_tabela[tabela] = num_campos
            
            # Contabilizar tipos
            for campo_info in info_tabela.get('campos', {}).values():
                tipo = campo_info['tipo_python']
                tipos_distribuicao[tipo] = tipos_distribuicao.get(tipo, 0) + 1
        
        return {
            'total_tabelas': len(tabelas),
            'total_campos': total_campos,
            'media_campos_por_tabela': total_campos / len(tabelas) if tabelas else 0,
            'distribuicao_tipos': tipos_distribuicao,
            'campos_por_tabela': campos_por_tabela,
            'tabelas_com_mais_campos': sorted(campos_por_tabela.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def limpar_cache(self) -> None:
        """
        Limpa o cache de tabelas.
        """
        self.tabelas_cache.clear()
        logger.debug("🧹 Cache de metadados limpo")
    
    def is_available(self) -> bool:
        """
        Verifica se o scanner está disponível.
        
        Returns:
            True se disponível
        """
        return self.inspector is not None


# Exportações principais
__all__ = [
    'MetadataScanner'
] 
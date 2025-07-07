"""
📊 DATABASE READER - Leitor de Dados do Banco de Dados
=====================================================

Módulo responsável por ler dados reais do banco de dados PostgreSQL
para enriquecimento dos mapeamentos semânticos.

Funcionalidades:
- Leitura de metadados das tabelas
- Extração de campos e tipos
- Análise de dados reais
- Estatísticas de utilização
"""

import logging
from typing import Dict, List, Optional, Any, Set, Union
from sqlalchemy import inspect, func, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import os
import sys

# Adicionar path para importar modelos
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

logger = logging.getLogger(__name__)

class DatabaseReader:
    """
    Leitor de dados do banco de dados para enriquecimento semântico.
    
    Responsável por extrair informações reais do banco de dados
    para melhorar a qualidade dos mapeamentos semânticos.
    """
    
    def __init__(self, db_engine=None, db_session=None):
        """
        Inicializa o leitor do banco de dados.
        
        Args:
            db_engine: Engine do SQLAlchemy (opcional)
            db_session: Sessão do SQLAlchemy (opcional)
        """
        self.db_engine = db_engine
        self.db_session = db_session
        self.inspector = None
        self.tabelas_cache = {}
        self.modelos_cache = {}
        
        # Tentar obter engine e session se não fornecidos
        if not self.db_engine or not self.db_session:
            self._tentar_obter_conexao_flask()
        
        # Inicializar inspector se engine disponível
        if self.db_engine:
            try:
                self.inspector = inspect(self.db_engine)
                logger.info("🔍 Inspector do banco de dados inicializado")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao inicializar inspector: {e}")
    
    def _tentar_obter_conexao_flask(self):
        """
        Tenta obter conexão com o banco através do Flask app.
        """
        try:
            # Tentar importar Flask app
            from app import create_app, db
            
            # Criar app se não existir
            app = create_app()
            
            with app.app_context():
                self.db_engine = db.engine
                self.db_session = db.session
                
            logger.info("✅ Conexão com banco obtida via Flask")
            
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível obter conexão Flask: {e}")
            # Tentar conexão direta por variável de ambiente
            self._tentar_conexao_direta()
    
    def _tentar_conexao_direta(self):
        """
        Tenta conexão direta com o banco via variável de ambiente.
        """
        try:
            from sqlalchemy import create_engine
            
            database_url = os.getenv('DATABASE_URL')
            if database_url:
                # Corrigir URL para SQLAlchemy 1.4+
                if database_url.startswith('postgres://'):
                    database_url = database_url.replace('postgres://', 'postgresql://', 1)
                
                self.db_engine = create_engine(database_url)
                logger.info("✅ Conexão direta com banco estabelecida")
                
        except Exception as e:
            logger.warning(f"⚠️ Conexão direta com banco falhou: {e}")
    
    def listar_tabelas(self) -> List[str]:
        """
        Lista todas as tabelas disponíveis no banco.
        
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
        Obtém informações detalhadas dos campos de uma tabela.
        
        Args:
            nome_tabela: Nome da tabela
            
        Returns:
            Dict com informações dos campos
        """
        if not self.inspector:
            logger.error("❌ Inspector não disponível")
            return {}
        
        # Usar cache se disponível
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
                    'tamanho': getattr(coluna['type'], 'length', None)
                }
            
            # Cache da tabela
            self.tabelas_cache[nome_tabela] = info_tabela
            
            logger.debug(f"📊 Tabela {nome_tabela}: {len(colunas)} campos mapeados")
            return info_tabela
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter campos da tabela {nome_tabela}: {e}")
            return {}
    
    def _normalizar_tipo_sqlalchemy(self, tipo_sqlalchemy: str) -> str:
        """
        Normaliza tipos do SQLAlchemy para tipos Python simples.
        
        Args:
            tipo_sqlalchemy: Tipo original do SQLAlchemy
            
        Returns:
            Tipo normalizado
        """
        tipo_lower = str(tipo_sqlalchemy).lower()
        
        if 'varchar' in tipo_lower or 'text' in tipo_lower or 'string' in tipo_lower:
            return 'string'
        elif 'integer' in tipo_lower or 'bigint' in tipo_lower:
            return 'integer'
        elif 'decimal' in tipo_lower or 'numeric' in tipo_lower or 'float' in tipo_lower:
            return 'decimal'
        elif 'boolean' in tipo_lower:
            return 'boolean'
        elif 'date' in tipo_lower:
            return 'datetime' if 'datetime' in tipo_lower or 'timestamp' in tipo_lower else 'date'
        else:
            return 'string'  # Fallback
    
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
        
        try:
            # Query para análise básica
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
                
                analise = {
                    'tabela': nome_tabela,
                    'campo': nome_campo,
                    'total_registros': resultado[0],
                    'valores_unicos': resultado[1],
                    'valores_nao_nulos': resultado[2],
                    'valores_nulos': resultado[3],
                    'percentual_preenchimento': (resultado[2] / resultado[0] * 100) if resultado[0] > 0 else 0
                }
                
                # Obter exemplos de valores
                query_exemplos = text(f"""
                    SELECT DISTINCT {nome_campo} 
                    FROM {nome_tabela} 
                    WHERE {nome_campo} IS NOT NULL 
                    ORDER BY {nome_campo} 
                    LIMIT {limite}
                """)
                
                exemplos = conn.execute(query_exemplos).fetchall()
                analise['exemplos'] = [str(ex[0]) for ex in exemplos] if exemplos else []
                
                logger.debug(f"📊 Análise {nome_tabela}.{nome_campo}: {analise['percentual_preenchimento']:.1f}% preenchido")
                return analise
                
        except Exception as e:
            logger.error(f"❌ Erro ao analisar dados de {nome_tabela}.{nome_campo}: {e}")
            return {}
    
    def obter_relacionamentos(self, nome_tabela: str) -> List[Dict[str, Any]]:
        """
        Obtém relacionamentos de uma tabela.
        
        Args:
            nome_tabela: Nome da tabela
            
        Returns:
            Lista de relacionamentos
        """
        if not self.inspector:
            logger.error("❌ Inspector não disponível")
            return []
        
        try:
            # Chaves estrangeiras
            foreign_keys = self.inspector.get_foreign_keys(nome_tabela)
            
            relacionamentos = []
            for fk in foreign_keys:
                relacionamento = {
                    'tipo': 'foreign_key',
                    'tabela_origem': nome_tabela,
                    'campos_origem': fk['constrained_columns'],
                    'tabela_destino': fk['referred_table'],
                    'campos_destino': fk['referred_columns'],
                    'nome_constraint': fk.get('name', '')
                }
                relacionamentos.append(relacionamento)
            
            logger.debug(f"🔗 Tabela {nome_tabela}: {len(relacionamentos)} relacionamentos")
            return relacionamentos
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter relacionamentos de {nome_tabela}: {e}")
            return []
    
    def buscar_campos_por_tipo(self, tipo_campo: str) -> List[Dict[str, str]]:
        """
        Busca campos por tipo em todas as tabelas.
        
        Args:
            tipo_campo: Tipo do campo a buscar
            
        Returns:
            Lista de campos encontrados
        """
        if not self.inspector:
            logger.error("❌ Inspector não disponível")
            return []
        
        campos_encontrados = []
        tabelas = self.listar_tabelas()
        
        for tabela in tabelas:
            info_tabela = self.obter_campos_tabela(tabela)
            
            for nome_campo, info_campo in info_tabela.get('campos', {}).items():
                if info_campo['tipo_python'] == tipo_campo:
                    campos_encontrados.append({
                        'tabela': tabela,
                        'campo': nome_campo,
                        'tipo': info_campo['tipo'],
                        'nulo': info_campo['nulo']
                    })
        
        logger.info(f"🔍 Encontrados {len(campos_encontrados)} campos do tipo {tipo_campo}")
        return campos_encontrados
    
    def buscar_campos_por_nome(self, nome_padrao: str) -> List[Dict[str, str]]:
        """
        Busca campos por padrão de nome em todas as tabelas.
        
        Args:
            nome_padrao: Padrão do nome a buscar
            
        Returns:
            Lista de campos encontrados
        """
        if not self.inspector:
            logger.error("❌ Inspector não disponível")
            return []
        
        campos_encontrados = []
        tabelas = self.listar_tabelas()
        nome_padrao_lower = nome_padrao.lower()
        
        for tabela in tabelas:
            info_tabela = self.obter_campos_tabela(tabela)
            
            for nome_campo, info_campo in info_tabela.get('campos', {}).items():
                if nome_padrao_lower in nome_campo.lower():
                    campos_encontrados.append({
                        'tabela': tabela,
                        'campo': nome_campo,
                        'tipo': info_campo['tipo'],
                        'tipo_python': info_campo['tipo_python'],
                        'match_score': self._calcular_score_match(nome_campo, nome_padrao)
                    })
        
        # Ordenar por score de match (melhor primeiro)
        campos_encontrados.sort(key=lambda x: x['match_score'], reverse=True)
        
        logger.info(f"🔍 Encontrados {len(campos_encontrados)} campos para padrão '{nome_padrao}'")
        return campos_encontrados
    
    def _calcular_score_match(self, nome_campo: str, nome_padrao: str) -> float:
        """
        Calcula score de match entre nome do campo e padrão.
        
        Args:
            nome_campo: Nome do campo
            nome_padrao: Padrão buscado
            
        Returns:
            Score de 0 a 1
        """
        nome_lower = nome_campo.lower()
        padrao_lower = nome_padrao.lower()
        
        # Match exato
        if nome_lower == padrao_lower:
            return 1.0
        
        # Match no início
        if nome_lower.startswith(padrao_lower):
            return 0.9
        
        # Match no final
        if nome_lower.endswith(padrao_lower):
            return 0.8
        
        # Match contém
        if padrao_lower in nome_lower:
            return 0.7
        
        # Match por similaridade simples
        chars_comuns = set(nome_lower) & set(padrao_lower)
        if chars_comuns:
            return len(chars_comuns) / max(len(nome_lower), len(padrao_lower))
        
        return 0.0
    
    def gerar_mapeamento_automatico(self, nome_tabela: str) -> Dict[str, Any]:
        """
        Gera mapeamento automático básico para uma tabela.
        
        Args:
            nome_tabela: Nome da tabela
            
        Returns:
            Dict com mapeamento automático
        """
        info_tabela = self.obter_campos_tabela(nome_tabela)
        
        if not info_tabela:
            return {}
        
        mapeamento = {
            'tabela': nome_tabela,
            'modelo': nome_tabela.replace('_', '').capitalize(),
            'campos': {},
            'estatisticas': {
                'total_campos': info_tabela['total_campos'],
                'campos_mapeados': 0,
                'campos_analisados': 0
            }
        }
        
        # Mapear campos automaticamente
        for nome_campo, info_campo in info_tabela['campos'].items():
            mapeamento_campo = {
                'nome': nome_campo,
                'tipo': info_campo['tipo_python'],
                'termos_naturais': self._gerar_termos_automaticos(nome_campo),
                'obrigatorio': not info_campo['nulo'],
                'chave_primaria': info_campo['chave_primaria']
            }
            
            # Analisar dados se possível
            if self.db_engine:
                analise = self.analisar_dados_reais(nome_tabela, nome_campo, limite=50)
                if analise:
                    mapeamento_campo['analise_dados'] = analise
                    mapeamento['estatisticas']['campos_analisados'] += 1
            
            mapeamento['campos'][nome_campo] = mapeamento_campo
            mapeamento['estatisticas']['campos_mapeados'] += 1
        
        logger.info(f"🎯 Mapeamento automático para {nome_tabela}: {mapeamento['estatisticas']['campos_mapeados']} campos")
        return mapeamento
    
    def _gerar_termos_automaticos(self, nome_campo: str) -> List[str]:
        """
        Gera termos naturais básicos para um campo.
        
        Args:
            nome_campo: Nome do campo
            
        Returns:
            Lista de termos naturais
        """
        termos = []
        
        # Termo original
        termos.append(nome_campo)
        
        # Variações comuns
        nome_sem_underscore = nome_campo.replace('_', ' ')
        if nome_sem_underscore != nome_campo:
            termos.append(nome_sem_underscore)
        
        # Padrões comuns
        padroes = {
            'id': ['identificador', 'código', 'chave'],
            'nome': ['nome', 'razão social', 'descrição'],
            'data': ['data', 'quando', 'dia'],
            'valor': ['valor', 'preço', 'custo'],
            'status': ['status', 'situação', 'estado'],
            'ativo': ['ativo', 'habilitado', 'válido'],
            'cliente': ['cliente', 'comprador', 'empresa'],
            'cnpj': ['cnpj', 'documento', 'identificação'],
            'cidade': ['cidade', 'município', 'local'],
            'uf': ['uf', 'estado', 'região'],
            'peso': ['peso', 'quilos', 'kg'],
            'observacao': ['observação', 'obs', 'comentário']
        }
        
        nome_lower = nome_campo.lower()
        for padrao, termos_padrao in padroes.items():
            if padrao in nome_lower:
                termos.extend(termos_padrao)
        
        # Remover duplicatas
        termos_unicos = []
        for termo in termos:
            if termo not in termos_unicos:
                termos_unicos.append(termo)
        
        return termos_unicos[:10]  # Limitar a 10 termos
    
    def obter_estatisticas_gerais(self) -> Dict[str, Any]:
        """
        Obtém estatísticas gerais do banco de dados.
        
        Returns:
            Dict com estatísticas
        """
        if not self.inspector:
            return {'erro': 'Inspector não disponível'}
        
        try:
            tabelas = self.listar_tabelas()
            
            estatisticas = {
                'total_tabelas': len(tabelas),
                'total_campos': 0,
                'campos_por_tipo': {},
                'tabelas_detalhes': []
            }
            
            for tabela in tabelas:
                info_tabela = self.obter_campos_tabela(tabela)
                
                estatisticas['total_campos'] += info_tabela['total_campos']
                
                # Contar campos por tipo
                for campo_info in info_tabela['campos'].values():
                    tipo = campo_info['tipo_python']
                    estatisticas['campos_por_tipo'][tipo] = estatisticas['campos_por_tipo'].get(tipo, 0) + 1
                
                # Detalhes da tabela
                estatisticas['tabelas_detalhes'].append({
                    'nome': tabela,
                    'campos': info_tabela['total_campos']
                })
            
            logger.info(f"📊 Estatísticas gerais: {estatisticas['total_tabelas']} tabelas, {estatisticas['total_campos']} campos")
            return estatisticas
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas gerais: {e}")
            return {'erro': str(e)}
    
    def esta_disponivel(self) -> bool:
        """
        Verifica se o leitor do banco está disponível.
        
        Returns:
            True se disponível, False caso contrário
        """
        return self.db_engine is not None and self.inspector is not None
    
    def __str__(self) -> str:
        """Representação string do reader"""
        status = "DISPONÍVEL" if self.esta_disponivel() else "INDISPONÍVEL"
        return f"<DatabaseReader status={status} tabelas_cache={len(self.tabelas_cache)}>"
    
    def __repr__(self) -> str:
        """Representação detalhada do reader"""
        return self.__str__() 
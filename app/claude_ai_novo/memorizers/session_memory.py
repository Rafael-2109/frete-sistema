"""
💾 SESSION MEMORY - Persistência JSONB de Sessões IA
===================================================

Responsabilidade: MEMORIZAR dados de sessão em PostgreSQL com campo JSONB.
Especializações: Persistência, Recuperação, Limpeza, Análise de Sessões.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
try:
    from sqlalchemy import text, func
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    text, func = None
    SQLALCHEMY_AVAILABLE = False
from sqlalchemy.exc import SQLAlchemyError

# Imports internos com fallbacks robustos
from app.claude_ai_novo.utils.flask_fallback import get_db

logger = logging.getLogger(__name__)

class SessionMemory:
    """
    Especializador em memorizar dados de sessão com PostgreSQL JSONB.
    
    Responsabilidades:
    - Persistir metadata de sessões em JSONB
    - Recuperar dados de sessão por ID/critérios
    - Limpar sessões antigas automaticamente
    - Prover analytics básicas de sessões
    """
    
    @property
    def db(self):
        """Obtém db com fallback"""
        return get_db()
    
    def __init__(self):
        """Inicializa o memorizador de sessões."""
        self.table_name = "ai_advanced_sessions"
        self._ensure_table_exists()
        logger.info("💾 SessionMemory inicializado")
    
    def _ensure_table_exists(self):
        """Verifica se tabela existe, cria avisos se necessário."""
        try:
            if self.db is None:
                logger.warning("⚠️ Banco de dados não disponível - SessionMemory em modo limitado")
                return
                
            # Verificar se tabela existe
            check_query = text("""
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = :table_name
            """)
            result = self.db.session.execute(check_query, {'table_name': self.table_name}).fetchone()
            
            if not result:
                logger.warning(f"⚠️ Tabela {self.table_name} não existe - funcionalidade será limitada")
                logger.info("💡 Para funcionalidade completa, execute as migrações do sistema avançado")
            else:
                logger.info(f"✅ Tabela {self.table_name} encontrada")
                
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível verificar tabela {self.table_name}: {e}")
            logger.info("💡 SessionMemory funcionará em modo limitado")
    
    def store_session(self, session_id: str, metadata: Dict[str, Any], 
                     user_id: Optional[int] = None) -> bool:
        """
        Armazena dados de sessão em PostgreSQL JSONB.
        
        Args:
            session_id: ID único da sessão
            metadata: Dados da sessão para armazenar
            user_id: ID do usuário (opcional)
            
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            # Preparar metadata com timestamp
            enhanced_metadata = {
                **metadata,
                "stored_at": datetime.now().isoformat(),
                "session_id": session_id,
                "user_id": user_id
            }
            
            # Query de inserção
            query = text(f"""
                INSERT INTO {self.table_name} (
                    session_id, created_at, user_id, metadata_jsonb
                ) VALUES (
                    :session_id, :created_at, :user_id, CAST(:metadata AS jsonb)
                )
                ON CONFLICT (session_id) 
                DO UPDATE SET 
                    metadata_jsonb = CAST(:metadata AS jsonb),
                    updated_at = :created_at
            """)
            
            # Executar query
            self.db.session.execute(query, {
                'session_id': session_id,
                'created_at': datetime.now(),
                'user_id': user_id,
                'metadata': json.dumps(enhanced_metadata)
            })
            
            self.db.session.commit()
            logger.info(f"💾 Sessão armazenada: {session_id}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Erro ao armazenar sessão {session_id}: {e}")
            self.db.session.rollback()
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao armazenar sessão {session_id}: {e}")
            self.db.session.rollback()
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera dados de sessão por ID.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Dados da sessão ou None se não encontrada
        """
        try:
            query = text(f"""
                SELECT session_id, created_at, updated_at, user_id, metadata_jsonb
                FROM {self.table_name}
                WHERE session_id = :session_id
            """)
            
            result = self.db.session.execute(query, {'session_id': session_id}).fetchone()
            
            if result:
                return {
                    'session_id': result.session_id,
                    'created_at': result.created_at.isoformat() if result.created_at else None,
                    'updated_at': result.updated_at.isoformat() if result.updated_at else None,
                    'user_id': result.user_id,
                    'metadata': result.metadata_jsonb
                }
            
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Erro ao recuperar sessão {session_id}: {e}")
            return None
    
    def get_sessions_by_user(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Recupera sessões de um usuário específico.
        
        Args:
            user_id: ID do usuário
            limit: Limite de resultados
            
        Returns:
            Lista de sessões do usuário
        """
        try:
            query = text(f"""
                SELECT session_id, created_at, updated_at, user_id, metadata_jsonb
                FROM {self.table_name}
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            results = self.db.session.execute(query, {
                'user_id': user_id,
                'limit': limit
            }).fetchall()
            
            return [
                {
                    'session_id': r.session_id,
                    'created_at': r.created_at.isoformat() if r.created_at else None,
                    'updated_at': r.updated_at.isoformat() if r.updated_at else None,
                    'user_id': r.user_id,
                    'metadata': r.metadata_jsonb
                }
                for r in results
            ]
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Erro ao recuperar sessões do usuário {user_id}: {e}")
            return []
    
    def search_sessions(self, criteria: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Busca sessões por critérios JSONB.
        
        Args:
            criteria: Critérios de busca (ex: {'domain': 'fretes', 'confidence': {'$gte': 0.8}})
            limit: Limite de resultados
            
        Returns:
            Lista de sessões que atendem aos critérios
        """
        try:
            # Construir condições JSONB
            conditions = []
            params: Dict[str, Any] = {'limit': limit}  # type: ignore[assignment]
            
            for key, value in criteria.items():
                if isinstance(value, dict) and '$gte' in value:
                    conditions.append(f"(metadata_jsonb->>'$.{key}')::float >= :{key}_gte")
                    params[f"{key}_gte"] = float(value['$gte'])  # type: ignore[assignment]
                elif isinstance(value, dict) and '$lte' in value:
                    conditions.append(f"(metadata_jsonb->>'$.{key}')::float <= :{key}_lte")
                    params[f"{key}_lte"] = float(value['$lte'])  # type: ignore[assignment]
                else:
                    conditions.append(f"metadata_jsonb->>'$.{key}' = :{key}")
                    params[key] = str(value)  # type: ignore[assignment]
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = text(f"""
                SELECT session_id, created_at, updated_at, user_id, metadata_jsonb
                FROM {self.table_name}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            results = self.db.session.execute(query, params).fetchall()
            
            return [
                {
                    'session_id': r.session_id,
                    'created_at': r.created_at.isoformat() if r.created_at else None,
                    'updated_at': r.updated_at.isoformat() if r.updated_at else None,
                    'user_id': r.user_id,
                    'metadata': r.metadata_jsonb
                }
                for r in results
            ]
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Erro ao buscar sessões: {e}")
            return []
    
    def cleanup_old_sessions(self, days_old: int = 90) -> int:
        """
        Remove sessões antigas do banco.
        
        Args:
            days_old: Idade em dias para considerar sessão antiga
            
        Returns:
            Número de sessões removidas
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            query = text(f"""
                DELETE FROM {self.table_name}
                WHERE created_at < :cutoff_date
            """)
            
            result = self.db.session.execute(query, {'cutoff_date': cutoff_date})
            self.db.session.commit()
            
            deleted_count = result.rowcount
            logger.info(f"🧹 Limpeza concluída: {deleted_count} sessões removidas")
            return deleted_count
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Erro na limpeza de sessões: {e}")
            self.db.session.rollback()
            return 0
    
    def get_session_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Gera estatísticas básicas das sessões.
        
        Args:
            days: Período em dias para análise
            
        Returns:
            Estatísticas das sessões
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            query = text(f"""
                SELECT 
                    COUNT(*) as total_sessions,
                    COUNT(DISTINCT user_id) as unique_users,
                    AVG(CASE WHEN metadata_jsonb->>'$.confidence' IS NOT NULL 
                        THEN (metadata_jsonb->>'$.confidence')::float 
                        ELSE NULL END) as avg_confidence,
                    COUNT(CASE WHEN metadata_jsonb->>'$.domain' = 'fretes' THEN 1 END) as fretes_sessions,
                    COUNT(CASE WHEN metadata_jsonb->>'$.domain' = 'entregas' THEN 1 END) as entregas_sessions,
                    COUNT(CASE WHEN metadata_jsonb->>'$.domain' = 'pedidos' THEN 1 END) as pedidos_sessions
                FROM {self.table_name}
                WHERE created_at >= :cutoff_date
            """)
            
            result = self.db.session.execute(query, {'cutoff_date': cutoff_date}).fetchone()
            
            return {
                'period_days': days,
                'total_sessions': result.total_sessions or 0,
                'unique_users': result.unique_users or 0,
                'avg_confidence': round(result.avg_confidence or 0, 3),
                'domain_breakdown': {
                    'fretes': result.fretes_sessions or 0,
                    'entregas': result.entregas_sessions or 0,
                    'pedidos': result.pedidos_sessions or 0
                },
                'generated_at': datetime.now().isoformat()
            }
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Erro ao gerar estatísticas: {e}")
            return {
                'error': str(e),
                'period_days': days,
                'generated_at': datetime.now().isoformat()
            }
    
    def update_session_metadata(self, session_id: str, metadata_updates: Dict[str, Any]) -> bool:
        """
        Atualiza metadata de uma sessão existente.
        
        Args:
            session_id: ID da sessão
            metadata_updates: Novos campos para adicionar/atualizar
            
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            query = text(f"""
                UPDATE {self.table_name}
                SET metadata_jsonb = metadata_jsonb || CAST(:updates AS jsonb),
                    updated_at = :updated_at
                WHERE session_id = :session_id
            """)
            
            result = self.db.session.execute(query, {
                'session_id': session_id,
                'updates': json.dumps(metadata_updates),
                'updated_at': datetime.now()
            })
            
            self.db.session.commit()
            
            if result.rowcount > 0:
                logger.info(f"📝 Sessão atualizada: {session_id}")
                return True
            else:
                logger.warning(f"⚠️ Sessão não encontrada para atualização: {session_id}")
                return False
                
        except SQLAlchemyError as e:
            logger.error(f"❌ Erro ao atualizar sessão {session_id}: {e}")
            self.db.session.rollback()
            return False


# Instância global para conveniência
_session_memory = None

def get_session_memory() -> SessionMemory:
    """
    Retorna instância global do SessionMemory.
    
    Returns:
        Instância do SessionMemory
    """
    global _session_memory
    if _session_memory is None:
        _session_memory = SessionMemory()
    return _session_memory

def store_session_data(session_id: str, metadata: Dict[str, Any], user_id: Optional[int] = None) -> bool:
    """
    Função de conveniência para armazenar dados de sessão.
    
    Args:
        session_id: ID único da sessão
        metadata: Dados da sessão
        user_id: ID do usuário (opcional)
        
    Returns:
        True se sucesso, False caso contrário
    """
    return get_session_memory().store_session(session_id, metadata, user_id)

def get_session_data(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Função de conveniência para recuperar dados de sessão.
    
    Args:
        session_id: ID da sessão
        
    Returns:
        Dados da sessão ou None se não encontrada
    """
    return get_session_memory().get_session(session_id) 
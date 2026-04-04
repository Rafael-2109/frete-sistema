"""
Context Middleware — Propaga contexto Flask para PostgreSQL session variables.

O trigger audit_supply_chain_trigger() le estas variaveis para registrar
quem fez a operacao e de onde veio:
  - app.current_user → registrado_por
  - app.origin       → origem
  - app.session_id   → session_id

Uso:
  1. Em app/__init__.py: registrar set_pg_audit_context como before_request
  2. Em sync jobs: chamar set_audit_context() explicitamente antes das operacoes

IMPORTANTE: Usa SET (session-level), NAO SET LOCAL (transaction-level).
SET persiste entre commits na mesma conexao, garantindo que syncs com
multiplos commits mantenham o contexto. A limpeza ocorre no before_request
do proximo request (que sobrescreve) ou no pool_pre_ping (que cria nova conexao).
"""
import logging
from uuid import uuid4

from flask import has_request_context
from sqlalchemy import text

logger = logging.getLogger(__name__)


def set_pg_audit_context():
    """
    Flask before_request hook.
    Propaga usuario e origem do request HTTP para session variables do PostgreSQL.
    Silencioso em caso de erro (nao deve impedir o request).

    Usa SET (session-level) para persistir entre commits dentro do mesmo request.
    O before_request SEMPRE roda antes de qualquer logica, garantindo que
    conexoes reutilizadas do pool tenham contexto atualizado.
    """
    try:
        from app import db

        usuario = 'SISTEMA'
        origem = 'SISTEMA'

        if has_request_context():
            try:
                from flask_login import current_user
                if current_user.is_authenticated:
                    usuario = getattr(current_user, 'nome', None) or str(current_user)
                    origem = 'USUARIO'
            except Exception:
                pass

        db.session.execute(text("SET app.current_user = :u"), {'u': usuario})
        db.session.execute(text("SET app.origin = :o"), {'o': origem})
        # Limpar session_id de sync anterior (evita contaminacao entre requests)
        db.session.execute(text("SET app.session_id = ''"))
    except Exception as e:
        # Nao propagar — contexto ausente e aceitavel (trigger usa 'SISTEMA' como fallback)
        logger.debug(f"[AUDIT_CTX] Contexto PG nao setado: {e}")


def set_audit_context(usuario='SISTEMA', origem='SYNC_ODOO', session_id=None):
    """
    Chamado explicitamente por sync jobs e workers (sem request context).

    Usa SET (session-level) para persistir entre os multiplos commits
    que os sync services fazem dentro de uma mesma operacao.

    Args:
        usuario: Nome do usuario ou 'SISTEMA'
        origem: SYNC_ODOO, UPLOAD_EXCEL, SISTEMA, etc.
        session_id: ID unico do ciclo de sync (ex: 'SYNC_CARTEIRA_20260404_143000_a1b2')
                    Usado para correlacionar todos os eventos de um mesmo sync
                    e para enriquecer qtd_projetada_dia em batch pos-commit.
    """
    try:
        from app import db

        db.session.execute(text("SET app.current_user = :u"), {'u': usuario})
        db.session.execute(text("SET app.origin = :o"), {'o': origem})
        # Sempre setar session_id ('' se nao fornecido) para evitar contaminacao
        # de session_id anterior na mesma conexao do pool
        db.session.execute(text("SET app.session_id = :s"), {'s': session_id or ''})
    except Exception as e:
        logger.debug(f"[AUDIT_CTX] Contexto sync nao setado: {e}")


def gerar_session_id(prefixo='SYNC'):
    """
    Gera session_id unico para um ciclo de sync.

    Formato: {PREFIXO}_{YYYYMMDD}_{HHMMSS}_{UUID8}
    Exemplo: SYNC_CARTEIRA_20260404_143000_a1b2c3d4

    Inclui sufixo UUID para evitar colisao em syncs concorrentes.

    Args:
        prefixo: Prefixo identificador (SYNC_CARTEIRA, SYNC_FATURAMENTO, etc.)

    Returns:
        str: Session ID unico
    """
    from app.utils.timezone import agora_utc_naive
    ts = agora_utc_naive()
    uid = uuid4().hex[:8]
    return f"{prefixo}_{ts.strftime('%Y%m%d_%H%M%S')}_{uid}"

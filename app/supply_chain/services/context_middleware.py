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

IMPORTANTE: Usa set_config() com is_local=false (session-level).
Persiste entre commits na mesma conexao, garantindo que syncs com
multiplos commits mantenham o contexto. A limpeza ocorre no before_request
do proximo request (que sobrescreve) ou no pool_pre_ping (que cria nova conexao).

NOTA: NAO usar "SET var = :param" — PostgreSQL nao aceita bind params em SET.
Usar set_config('var', :param, false) que aceita bind params corretamente.
"""
import logging
from uuid import uuid4

from flask import has_request_context, g
from sqlalchemy import text

logger = logging.getLogger(__name__)


def set_pg_audit_context():
    """
    Flask before_request hook.
    Propaga usuario, origem e session_id do request HTTP para session variables
    do PostgreSQL. Silencioso em caso de erro (nao deve impedir o request).

    NOVO (2026-04-14):
      - Gera session_id unico por request (prefixo REQ_) e armazena em g.audit_session_id
      - Seta app.current_user_id com current_user.id (para coluna usuario_id)
      - .strip() no nome (elimina trailing spaces vindos de usuarios.nome)

    Usa set_config(name, value, is_local) onde is_local=false = session-level.
    """
    try:
        from app import db

        usuario = 'SISTEMA'
        origem = 'SISTEMA'
        usuario_id_str = ''
        session_id = ''  # default vazio → NULLIF no trigger = NULL

        if has_request_context():
            try:
                from flask_login import current_user
                if current_user.is_authenticated:
                    nome_raw = getattr(current_user, 'nome', None) or str(current_user)
                    usuario = (nome_raw or '').strip() or 'USUARIO'
                    uid = getattr(current_user, 'id', None)
                    usuario_id_str = str(uid) if uid is not None else ''
                    origem = 'USUARIO'
            except Exception:
                pass

            # Gerar session_id unico por request e expor via flask.g
            # para que handlers/services possam referenciar (ex: enqueue_enrichment)
            session_id = gerar_session_id('REQ')
            g.audit_session_id = session_id

        # set_config(name, value, is_local): is_local=false = session-level (persiste entre commits)
        db.session.execute(text("SELECT set_config('app.current_user', :u, false)"), {'u': usuario})
        db.session.execute(text("SELECT set_config('app.current_user_id', :uid, false)"), {'uid': usuario_id_str})
        db.session.execute(text("SELECT set_config('app.origin', :o, false)"), {'o': origem})
        db.session.execute(text("SELECT set_config('app.session_id', :s, false)"), {'s': session_id})
    except Exception as e:
        # Nao propagar — contexto ausente e aceitavel (trigger usa 'SISTEMA' como fallback)
        logger.debug(f"[AUDIT_CTX] Contexto PG nao setado: {e}")
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass


def set_audit_context(usuario='SISTEMA', origem='SYNC_ODOO', session_id=None, usuario_id=None):
    """
    Chamado explicitamente por sync jobs e workers (sem request context).

    Usa set_config() com is_local=false para persistir entre os multiplos commits
    que os sync services fazem dentro de uma mesma operacao.

    Args:
        usuario: Nome do usuario ou 'SISTEMA'
        origem: SYNC_ODOO, UPLOAD_EXCEL, SISTEMA, etc.
        session_id: ID unico do ciclo de sync (ex: 'SYNC_CARTEIRA_20260404_143000_a1b2')
                    Usado para correlacionar todos os eventos de um mesmo sync
                    e para enriquecer qtd_projetada_dia em batch pos-commit.
        usuario_id: ID numerico do usuario em usuarios.id (opcional, para sync jobs
                    que rodam em nome de um usuario humano). Normalmente None em
                    sync Odoo automaticos.
    """
    try:
        from app import db

        # .strip() defensivo: nomes vindos de usuarios.nome podem ter trailing spaces
        usuario_clean = (usuario or 'SISTEMA').strip() or 'SISTEMA'

        db.session.execute(text("SELECT set_config('app.current_user', :u, false)"), {'u': usuario_clean})
        db.session.execute(text("SELECT set_config('app.current_user_id', :uid, false)"),
                           {'uid': str(usuario_id) if usuario_id is not None else ''})
        db.session.execute(text("SELECT set_config('app.origin', :o, false)"), {'o': origem})
        # Sempre setar session_id ('' se nao fornecido) para evitar contaminacao
        # de session_id anterior na mesma conexao do pool
        db.session.execute(text("SELECT set_config('app.session_id', :s, false)"), {'s': session_id or ''})
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

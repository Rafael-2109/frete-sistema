"""
Helpers de path JSONL para cleanup de arquivos stale (pos-Fase B).

APOS Fase B (2026-04-21, SDK 0.1.64 SessionStore), este modulo foi reduzido
a APENAS helpers de path. As funcoes antigas backup_session_transcript /
restore_session_transcript / _is_jsonl_valid foram removidas:

- Backup: SDK TranscriptMirrorBatcher persiste entries em claude_session_store
  automaticamente durante o stream (ver app/agente/sdk/session_store_adapter.py)
- Restore: SDK materialize_resume_session materializa JSONL de tmp dir a partir
  do store antes de spawn do subprocess
- Validacao: desnecessaria — store deep-equal contract substitui

Mantemos apenas `_get_session_path` porque ainda e usado em 2 pontos de cleanup:
- client.py:~1595 — deletar JSONL stale apos resume falhado com exit=1
- client_pool.py:~419 — cleanup JSONL pos force-kill de subprocess zombie

Encoding do path: reproduz o algoritmo do SDK
(`claude_agent_sdk._internal.sessions._sanitize_path`). Para nosso cwd curto
(<200 chars), sem hash djb2 — regex `[^a-zA-Z0-9]` → `-` e suficiente.

Rollback Fase B: NAO precisa reverter este arquivo. Basta restaurar chat.py +
teams/services.py + toggle AGENT_SDK_SESSION_STORE_ENABLED=false.
"""
import os
import re
from pathlib import Path


def _get_session_dir() -> str:
    """Retorna o diretorio de sessoes do SDK para o CWD atual.

    O SDK codifica o CWD substituindo todos os caracteres nao-alfanumericos por '-':
        /home/user/projetos/frete_sistema → -home-user-projetos-frete-sistema
        /opt/render/project/src → -opt-render-project-src

    IMPORTANTE: O CLI subprocess recebe HOME=/tmp (client.py env override para
    evitar ENOENT em HOME read-only do Render). Os JSONLs ficam em /tmp/.claude/...
    Cleanup DEVE usar o mesmo HOME que o CLI — caso contrario os paths
    divergem e nao achamos o arquivo stale.
    """
    cwd = os.getcwd()
    # SDK encoding: tudo que nao e alfanumerico → '-'
    # (compativel com claude_agent_sdk._internal.sessions._sanitize_path
    #  para paths < 200 chars — sem hash djb2)
    encoded_cwd = re.sub(r'[^a-zA-Z0-9]', '-', cwd)
    # Usar /tmp como HOME — mesmo valor passado ao CLI subprocess em client.py
    # (HOME=/tmp para evitar ENOENT em Render onde HOME=/opt/render eh read-only)
    cli_home = Path('/tmp')
    return str(cli_home / '.claude' / 'projects' / encoded_cwd)


def _get_session_path(sdk_session_id: str) -> str:
    """Retorna o path completo do arquivo JSONL de uma sessao.

    Usado para cleanup de JSONLs stale (apos exit=1 de resume OU pos force-kill).

    Args:
        sdk_session_id: UUID da sessao SDK

    Returns:
        Path absoluto do arquivo JSONL
    """
    session_dir = _get_session_dir()
    return os.path.join(session_dir, f"{sdk_session_id}.jsonl")

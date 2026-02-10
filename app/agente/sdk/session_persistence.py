"""
Persistencia de session transcripts do Claude SDK.

Problema:
    O SDK `resume` depende de arquivos JSONL em ~/.claude/projects/{encoded_cwd}/{uuid}.jsonl.
    Quando o worker Render recicla, esses arquivos se perdem e o resume falha silenciosamente.

Solucao:
    Backup do JSONL para o PostgreSQL (campo AgentSession.sdk_session_transcript)
    e restore antes de chamar sdk_query com resume.

Fluxo:
    Msg 1: SDK cria {UUID}.jsonl → backup_session_transcript() → DB
    Msg 2: restore_session_transcript() → disco → SDK resume funciona

Encoding do path:
    O SDK usa ~/.claude/projects/{encoded_cwd}/ onde encoded_cwd substitui
    todos os caracteres nao-alfanumericos por '-'.
    Exemplo: /home/user/projetos/frete_sistema → -home-user-projetos-frete-sistema
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _get_session_dir() -> str:
    """
    Retorna o diretorio de sessoes do SDK para o CWD atual.

    O SDK codifica o CWD substituindo todos os caracteres nao-alfanumericos por '-':
        /home/user/projetos/frete_sistema → -home-user-projetos-frete-sistema
        /home/user/.claude/plans → -home-user--claude-plans

    Confirmado empiricamente em 2 projetos locais (2026-02-10).

    Returns:
        Path absoluto do diretorio de sessoes
    """
    cwd = os.getcwd()
    # SDK encoding: tudo que nao e alfanumerico → '-'
    encoded_cwd = re.sub(r'[^a-zA-Z0-9]', '-', cwd)
    home = Path.home()
    return str(home / '.claude' / 'projects' / encoded_cwd)


def _get_session_path(sdk_session_id: str) -> str:
    """
    Retorna o path completo do arquivo JSONL de uma sessao.

    Args:
        sdk_session_id: UUID da sessao SDK

    Returns:
        Path absoluto do arquivo JSONL
    """
    session_dir = _get_session_dir()
    return os.path.join(session_dir, f"{sdk_session_id}.jsonl")


def backup_session_transcript(sdk_session_id: str) -> Optional[str]:
    """
    Le o arquivo JSONL de sessao do disco e retorna como string.

    Chamado APOS o sdk_query retornar, para persistir o transcript no DB.

    Args:
        sdk_session_id: UUID da sessao SDK

    Returns:
        Conteudo do JSONL como string, ou None se arquivo nao existe/erro
    """
    if not sdk_session_id:
        return None

    session_path = _get_session_path(sdk_session_id)

    try:
        if not os.path.exists(session_path):
            logger.debug(
                f"[SESSION-PERSIST] JSONL nao encontrado: {session_path}"
            )
            return None

        with open(session_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content:
            logger.warning(
                f"[SESSION-PERSIST] JSONL vazio: {session_path}"
            )
            return None

        size_kb = len(content) / 1024
        logger.info(
            f"[SESSION-PERSIST] Backup lido: {sdk_session_id[:12]}... "
            f"({size_kb:.1f} KB)"
        )
        return content

    except Exception as e:
        logger.error(
            f"[SESSION-PERSIST] Erro ao ler JSONL: {e}",
            exc_info=True,
        )
        return None


def restore_session_transcript(sdk_session_id: str, transcript: str) -> bool:
    """
    Restaura o arquivo JSONL de sessao do DB para o disco.

    Chamado ANTES do sdk_query com resume, para garantir que o CLI
    encontre o arquivo de sessao mesmo apos reciclagem do worker.

    Args:
        sdk_session_id: UUID da sessao SDK
        transcript: Conteudo do JSONL como string

    Returns:
        True se restaurou com sucesso, False se erro
    """
    if not sdk_session_id or not transcript:
        return False

    session_path = _get_session_path(sdk_session_id)

    try:
        # Verifica se ja existe no disco (nao precisa restaurar)
        if os.path.exists(session_path):
            logger.debug(
                f"[SESSION-PERSIST] JSONL ja existe no disco: {sdk_session_id[:12]}..."
            )
            return True

        # Cria diretorio se nao existe
        session_dir = os.path.dirname(session_path)
        os.makedirs(session_dir, exist_ok=True)

        # Escreve o transcript no disco
        with open(session_path, 'w', encoding='utf-8') as f:
            f.write(transcript)

        size_kb = len(transcript) / 1024
        logger.info(
            f"[SESSION-PERSIST] Transcript restaurado: {sdk_session_id[:12]}... "
            f"({size_kb:.1f} KB)"
        )
        return True

    except Exception as e:
        logger.error(
            f"[SESSION-PERSIST] Erro ao restaurar JSONL: {e}",
            exc_info=True,
        )
        return False

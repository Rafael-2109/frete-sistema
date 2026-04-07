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

import json
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

    IMPORTANTE: O CLI subprocess recebe HOME=/tmp (client.py env override para
    evitar ENOENT em HOME read-only do Render). Os JSONLs ficam em /tmp/.claude/...
    O backup/restore DEVE usar o mesmo HOME que o CLI — caso contrario os paths
    divergem e o transcript nunca eh encontrado.

    Returns:
        Path absoluto do diretorio de sessoes
    """
    cwd = os.getcwd()
    # SDK encoding: tudo que nao e alfanumerico → '-'
    encoded_cwd = re.sub(r'[^a-zA-Z0-9]', '-', cwd)
    # Usar /tmp como HOME — mesmo valor passado ao CLI subprocess em client.py:1018
    # (HOME=/tmp para evitar ENOENT em Render onde HOME=/opt/render eh read-only)
    cli_home = Path('/tmp')
    return str(cli_home / '.claude' / 'projects' / encoded_cwd)


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
        # Verifica se ja existe no disco E esta valido
        if os.path.exists(session_path):
            if _is_jsonl_valid(session_path):
                logger.debug(
                    f"[SESSION-PERSIST] JSONL ja existe e valido no disco: "
                    f"{sdk_session_id[:12]}..."
                )
                return True
            else:
                # JSONL corrompido (crash, escrita parcial) — remover e re-restaurar
                logger.warning(
                    f"[SESSION-PERSIST] JSONL corrompido no disco, "
                    f"re-restaurando: {sdk_session_id[:12]}..."
                )
                try:
                    os.remove(session_path)
                except OSError:
                    pass

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


def _is_jsonl_valid(path: str) -> bool:
    """
    Verifica se um arquivo JSONL esta minimamente valido.

    Criterios:
    - Arquivo nao vazio (> 0 bytes)
    - Primeira linha e JSON parseavel

    Um JSONL corrompido (crash/escrita parcial) geralmente
    tem 0 bytes ou primeira linha truncada.

    Args:
        path: Caminho do arquivo JSONL

    Returns:
        True se valido, False se corrompido
    """
    try:
        size = os.path.getsize(path)
        if size == 0:
            return False

        with open(path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if not first_line:
                return False
            # Tenta parsear a primeira linha como JSON
            json.loads(first_line)
            return True
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return False

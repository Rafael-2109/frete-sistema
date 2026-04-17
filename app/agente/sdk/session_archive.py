"""
Arquivamento de transcripts de subagents + findings no S3.

Objetivo: preservar /tmp/.claude/projects/<proj>/<session>/subagents/*.jsonl
e /tmp/subagent-findings/<session>-*.md entre deploys (Render /tmp/ e ephemeral).

Feature #1 (admin forense) depende disso para investigar sessoes antigas.

Pipeline:
  1. Hook Stop (fim da sessao principal) chama archive_session_to_s3()
  2. Funcao busca /tmp/.claude/projects/*/session_id/subagents/*.jsonl
     + /tmp/subagent-findings/<session>*.md
  3. Cria tarball gzip em memoria (BytesIO — sem criar /tmp/agent_archives/)
  4. Upload para S3 em agent-archive/YYYY-MM/<session>.tar.gz
  5. Grava AgentSession.data['s3_archive'] = <s3_path>

Leitura (via subagent_reader):
  Quando /tmp/.claude/... vazio, subagent_reader chama restore_from_s3()
  que baixa tarball e extrai em /tmp/, depois re-le normalmente.
"""
from __future__ import annotations

import io
import logging
import tarfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger('sistema_fretes')


def _find_archivable_files(session_id: str) -> list[Path]:
    """Localiza subagent JSONLs + findings.md dessa sessao em /tmp/."""
    files = []

    # 1. Subagent transcripts em /tmp/.claude/projects/*/session_id/subagents/
    tmp_claude = Path('/tmp/.claude/projects')
    if tmp_claude.exists():
        for proj_dir in tmp_claude.iterdir():
            if not proj_dir.is_dir():
                continue
            sub_dir = proj_dir / session_id / 'subagents'
            if sub_dir.exists():
                for jsonl in sub_dir.rglob('*.jsonl'):
                    files.append(jsonl)

    # 2. Findings em /tmp/subagent-findings/ (nao tem session_id no nome,
    #    entao arquivamos todos os findings com mtime nas ultimas 4h —
    #    compromisso para evitar cross-session contamination)
    findings_dir = Path('/tmp/subagent-findings')
    if findings_dir.exists():
        import time
        cutoff = time.time() - (4 * 3600)  # 4h
        for md in findings_dir.rglob('*.md'):
            try:
                if md.stat().st_mtime > cutoff:
                    files.append(md)
            except OSError:
                continue

    return files


def _create_tarball(files: list[Path], session_id: str) -> Optional[bytes]:
    """Cria tarball gzip em memoria. Retorna bytes ou None se files vazio."""
    if not files:
        return None

    buf = io.BytesIO()
    try:
        with tarfile.open(fileobj=buf, mode='w:gz') as tar:
            for f in files:
                try:
                    # Arcname relativo para nao expor paths absolutos
                    arcname = f.name if f.parent.name in ('subagents', 'subagent-findings') \
                        else str(f.relative_to('/tmp'))
                    tar.add(str(f), arcname=arcname)
                except (OSError, tarfile.TarError) as e:
                    logger.debug(
                        f"[session_archive] add {f} falhou: {e}"
                    )
        buf.seek(0)
        return buf.read()
    except Exception as e:
        logger.warning(f"[session_archive] tarball falhou: {e}")
        return None


def _resolve_our_session_uuid(session_id_or_sdk_id: str) -> Optional[str]:
    """
    Resolve nosso UUID de AgentSession a partir do SDK session ID (ephemeral).

    Hook _stop_hook recebe `session_id` que e o SDK/CLI ID (efemero, guardado
    em AgentSession.data['sdk_session_id']). Nossa coluna `session_id` e
    outro UUID (o nosso, persistido no banco).

    Se input ja e nosso UUID, retorna ele. Se e SDK ID, busca o nosso UUID
    via query JSONB. Retorna None se nao encontrar.
    """
    if not session_id_or_sdk_id:
        return None
    try:
        from app.agente.models import AgentSession
        # Caso 1: ja e nosso UUID
        sess = AgentSession.query.filter_by(
            session_id=session_id_or_sdk_id
        ).first()
        if sess is not None:
            return sess.session_id
        # Caso 2: e SDK ID — busca via JSONB sdk_session_id
        sess = AgentSession.query.filter(
            AgentSession.data['sdk_session_id'].astext == session_id_or_sdk_id
        ).first()
        if sess is not None:
            return sess.session_id
    except Exception as e:
        logger.warning(f"[session_archive] lookup UUID falhou: {e}")
    return None


def archive_session_to_s3(session_id: str) -> Optional[str]:
    """
    Arquiva subagent transcripts + findings da sessao para S3.

    Aceita session_id OU sdk_session_id — resolve nosso UUID internamente
    antes de gravar ponteiro em AgentSession.data['s3_archive'].

    Retorna S3 path (ex: 'agent-archive/2026-04/sess-abc.tar.gz') ou None.
    Idempotente — chamar multiplas vezes gera upload novo (last-write-wins).

    R1 best-effort: exceptions logadas como warning, nunca propagadas.
    """
    try:
        # Busca arquivos usando o session_id como veio (SDK ID normalmente,
        # pois eh isso que o CLI bundled usa como nome de diretorio em /tmp/.claude/)
        files = _find_archivable_files(session_id)
        if not files:
            logger.info(
                f"[session_archive] session={session_id[:16]}: "
                f"nenhum arquivo para arquivar"
            )
            return None

        tarball_bytes = _create_tarball(files, session_id)
        if not tarball_bytes:
            return None

        # Upload via FileStorage (respeita USE_S3)
        from flask import current_app
        if not current_app.config.get('USE_S3', False):
            logger.info(
                f"[session_archive] USE_S3=false, skip upload "
                f"(session={session_id[:16]}, {len(files)} files)"
            )
            return None

        from werkzeug.datastructures import FileStorage as WerkzeugFileStorage
        from app.utils.file_storage import get_file_storage

        storage = get_file_storage()
        from app.utils.timezone import agora_utc_naive
        ym = agora_utc_naive().strftime('%Y-%m')
        filename = f'{session_id}.tar.gz'
        folder = f'agent-archive/{ym}'

        bio = io.BytesIO(tarball_bytes)
        file_obj = WerkzeugFileStorage(
            stream=bio,
            filename=filename,
            content_type='application/gzip',
        )

        s3_path = storage.save_file(
            file=file_obj,
            folder=folder,
            filename=filename,
        )

        if s3_path:
            logger.info(
                f"[session_archive] uploaded session={session_id[:16]} "
                f"files={len(files)} size={len(tarball_bytes)}B "
                f"path={s3_path}"
            )
            # Grava ponteiro em AgentSession.data — resolve nosso UUID
            # antes (session_id recebido pode ser SDK ID ephemeral)
            try:
                from app import db
                from sqlalchemy.orm.attributes import flag_modified
                from app.agente.models import AgentSession
                our_uuid = _resolve_our_session_uuid(session_id)
                if our_uuid:
                    sess = AgentSession.query.filter_by(
                        session_id=our_uuid
                    ).first()
                    if sess is not None:
                        data = sess.data or {}
                        data['s3_archive'] = s3_path
                        sess.data = data
                        flag_modified(sess, 'data')
                        db.session.commit()
                    else:
                        logger.warning(
                            f"[session_archive] AgentSession {our_uuid[:16]} "
                            f"nao encontrada — ponteiro nao gravado (archive orfao)"
                        )
                else:
                    logger.warning(
                        f"[session_archive] nao resolveu UUID para "
                        f"session_id={session_id[:16]} — archive orfao em S3: {s3_path}"
                    )
            except Exception as db_err:
                logger.warning(
                    f"[session_archive] ponteiro DB falhou: {db_err}"
                )

        return s3_path

    except Exception as e:
        logger.warning(f"[session_archive] falhou para {session_id}: {e}")
        return None


def restore_session_from_s3(session_id: str) -> bool:
    """
    Baixa tarball do S3 e extrai em /tmp/ para uso pelo subagent_reader.

    Retorna True se extraiu pelo menos 1 arquivo. Best-effort.
    Chamado pelo subagent_reader como fallback quando /tmp/ esta vazio.
    """
    try:
        from flask import current_app
        if not current_app.config.get('USE_S3', False):
            return False

        # Valida session_id antes de usar como path component
        from .subagent_reader import _is_safe_id
        if not _is_safe_id(session_id):
            logger.warning(
                f"[session_archive] session_id unsafe rejected: {session_id!r}"
            )
            return False

        from app.agente.models import AgentSession
        sess = AgentSession.query.filter_by(session_id=session_id).first()
        if sess is None or not (sess.data or {}).get('s3_archive'):
            return False

        s3_path = sess.data['s3_archive']

        from app.utils.file_storage import get_file_storage
        storage = get_file_storage()
        tarball_bytes = storage.download_file(s3_path)
        if not tarball_bytes:
            return False

        # Extrai em /tmp/ — nomes relativos preservam estrutura subagents/
        # e subagent-findings/
        buf = io.BytesIO(tarball_bytes)
        extract_root = Path('/tmp/agent_archive_restore') / session_id
        extract_root.mkdir(parents=True, exist_ok=True)

        extracted = 0
        with tarfile.open(fileobj=buf, mode='r:gz') as tar:
            for member in tar.getmembers():
                # Seguranca: reject paths contendo .., absolutos, ou symlinks
                # (symlink pode apontar para fora do extract_root mesmo com
                # nome benigno — e.g., subagents/link -> /etc/passwd)
                if (
                    '..' in member.name
                    or member.name.startswith('/')
                    or member.issym()
                    or member.islnk()
                ):
                    logger.debug(
                        f"[session_archive] skipped unsafe member: {member.name}"
                    )
                    continue
                try:
                    tar.extract(member, path=extract_root)
                    extracted += 1
                except (OSError, tarfile.TarError) as e:
                    logger.debug(f"[session_archive] extract {member.name}: {e}")

        logger.info(
            f"[session_archive] restored session={session_id[:16]} "
            f"extracted={extracted} to={extract_root}"
        )
        return extracted > 0

    except Exception as e:
        logger.warning(f"[session_archive] restore falhou: {e}")
        return False

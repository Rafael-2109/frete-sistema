"""Gerenciamento de arquivos do Agente (upload, download, listagem)."""

import logging
import os
import re
import uuid
import shutil
from typing import Optional

from flask import request, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.agente.routes import agente_bp
from app.agente.routes._constants import (
    UPLOAD_FOLDER,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    MIME_SIGNATURES,
    TEXT_EXTENSIONS,
    MAX_FILES_PER_SESSION,
    MAX_TOTAL_SIZE_PER_SESSION,
)

logger = logging.getLogger('sistema_fretes')


def _allowed_file(filename: str) -> bool:
    """Verifica se a extensão do arquivo é permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Session ID sanitizacao — Fase D (2026-04-14) previne path traversal
# Aceita: letras, digitos, hifen, underscore. Max 64 chars.
# 'default' e literal permitido para uploads sem sessao explicita.
_SESSION_ID_RE = re.compile(r'^[a-zA-Z0-9\-_]{1,64}$')


def _sanitize_session_id(session_id) -> str:
    """
    Sanitiza session_id para prevenir path traversal em os.path.join.

    Retorna 'default' (com warning) se o valor for invalido.
    Valores legitimos sao UUIDs ou strings tipo UUID.

    Caller DEVE usar o retorno desta funcao (nao o valor original) em
    qualquer os.path.join / os.makedirs / shutil.rmtree subsequente.
    """
    sid = (str(session_id) if session_id is not None else 'default').strip()
    if sid == 'default' or _SESSION_ID_RE.match(sid):
        return sid
    logger.warning(
        f"[AGENTE] session_id invalido rejeitado (path traversal?): "
        f"{sid[:100]!r} → usando 'default'"
    )
    return 'default'


def _validate_magic_bytes(file, ext: str) -> tuple:
    """
    Valida que os primeiros bytes do arquivo correspondem a extensao declarada.

    Anti-spoofing: rejeita .exe renomeado para .pdf, p.ex. Arquivos de texto
    puro (TEXT_EXTENSIONS) pulam a validacao pois nao tem signature confiavel.

    Args:
        file: file-like object (request.files['file'])
        ext: extensao em lowercase (sem o ponto)

    Returns:
        (valido: bool, mensagem_erro: str). Quando valido, mensagem e vazia.
    """
    # Texto puro nao tem signature — confia na extensao apos o whitelist filter
    if ext in TEXT_EXTENSIONS:
        return True, ""

    expected_sigs = MIME_SIGNATURES.get(ext)
    if not expected_sigs:
        # Extensao sem signature conhecida — aceita (fallback permissivo)
        return True, ""

    # Le primeiros 16 bytes (suficiente para todas as signatures)
    file.seek(0)
    header = file.read(16)
    file.seek(0)

    if not header:
        return False, "arquivo vazio"

    for sig in expected_sigs:
        if header.startswith(sig):
            return True, ""

    return False, (
        f"conteudo nao corresponde a extensao .{ext} (possivel spoofing)"
    )


def _get_session_folder(session_id: str) -> str:
    """
    Retorna o caminho da pasta da sessao, criando se necessario.

    session_id e sanitizado como defesa em profundidade (callers ja
    deveriam ter chamado _sanitize_session_id antes de usar o valor).
    """
    safe_sid = _sanitize_session_id(session_id)
    folder = os.path.join(UPLOAD_FOLDER, str(current_user.id), safe_sid)
    os.makedirs(folder, exist_ok=True)
    return folder


def _get_file_type(filename: str) -> str:
    """Retorna o tipo do arquivo baseado na extensão."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in ('png', 'jpg', 'jpeg', 'gif', 'webp'):
        return 'image'
    elif ext == 'pdf':
        return 'pdf'
    elif ext in ('xlsx', 'xls'):
        return 'excel'
    elif ext == 'csv':
        return 'csv'
    elif ext in ('docx', 'doc', 'rtf'):
        return 'word'
    elif ext in ('txt', 'md', 'json', 'xml', 'log'):
        return 'text'
    elif ext in ('rem', 'ret', 'cnab'):
        return 'bank_cnab'
    elif ext == 'ofx':
        return 'bank_ofx'
    return 'file'


def _get_mimetype(filename: str) -> str:
    """Retorna o MIME type correto para o arquivo (prioriza Excel e PDF)."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    mimetypes = {
        # Excel - CRÍTICO para abrir corretamente
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'xls': 'application/vnd.ms-excel',
        # Word
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'doc': 'application/msword',
        'rtf': 'application/rtf',
        # PDF - CRÍTICO para abrir corretamente
        'pdf': 'application/pdf',
        # CSV
        'csv': 'text/csv; charset=utf-8',
        # Imagens
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
        # Texto
        'txt': 'text/plain; charset=utf-8',
        'md': 'text/markdown; charset=utf-8',
        'json': 'application/json',
        'xml': 'application/xml',
        'log': 'text/plain; charset=utf-8',
        # Bancarios (CNAB / OFX) — texto plano com estrutura posicional/SGML
        'rem': 'text/plain; charset=utf-8',
        'ret': 'text/plain; charset=utf-8',
        'cnab': 'text/plain; charset=utf-8',
        'ofx': 'application/x-ofx',
    }
    return mimetypes.get(ext, 'application/octet-stream')


def _resolve_file_path(url: str) -> Optional[str]:
    """
    Resolve URL de arquivo para caminho local com validacao anti-traversal.

    Fase D (2026-04-14):
    - Sanitiza session_id (rejeita chars invalidos)
    - Aplica secure_filename ao nome do arquivo
    - Valida realpath dentro de UPLOAD_FOLDER (defesa contra symlink attack)

    Args:
        url: URL do arquivo (ex: /agente/api/files/session/uuid_file.png)

    Returns:
        Caminho absoluto do arquivo (dentro de UPLOAD_FOLDER) ou None se
        nao encontrado / invalido / tentativa de traversal.
    """
    if not url:
        return None

    # Extrair partes da URL: /agente/api/files/{session_id}/{filename}
    parts = url.split('/')
    if len(parts) < 5:
        return None

    try:
        # Formato: ['', 'agente', 'api', 'files', 'session_id', 'filename']
        session_id = _sanitize_session_id(parts[-2])
        filename = secure_filename(parts[-1])
        if not filename:
            return None

        upload_root = os.path.realpath(UPLOAD_FOLDER)

        def _within_upload(path: str) -> Optional[str]:
            """Retorna realpath se estiver dentro de upload_root, senao None."""
            real = os.path.realpath(path)
            if real == upload_root or real.startswith(upload_root + os.sep):
                return real
            logger.warning(
                f"[AGENTE] Path traversal rejeitado: "
                f"{path!r} -> {real!r} fora de {upload_root!r}"
            )
            return None

        # Tentar caminho com user_id primeiro
        if hasattr(current_user, 'id'):
            user_path = os.path.join(
                UPLOAD_FOLDER, str(current_user.id), session_id, filename
            )
            safe = _within_upload(user_path)
            if safe and os.path.exists(safe):
                return safe

        # Fallback: caminho sem user_id (arquivos gerados por skills)
        fallback_path = os.path.join(UPLOAD_FOLDER, session_id, filename)
        safe_fb = _within_upload(fallback_path)
        if safe_fb and os.path.exists(safe_fb):
            return safe_fb

        return None
    except Exception as e:
        logger.error(f"[AGENTE] Erro ao resolver caminho do arquivo: {e}")
        return None


@agente_bp.route('/api/upload', methods=['POST'])
@login_required
def api_upload_file():
    """Upload de arquivo para a sessão."""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo enviado'
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nome do arquivo vazio'
            }), 400

        if not _allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Tipo de arquivo não permitido. Permitidos: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'error': f'Arquivo muito grande. Máximo: {MAX_FILE_SIZE // (1024*1024)}MB'
            }), 400

        # Anti-spoofing: valida magic bytes contra extensao declarada
        _safe_fname = file.filename or ''
        ext_for_magic = (
            _safe_fname.rsplit('.', 1)[1].lower()
            if '.' in _safe_fname else ''
        )
        valido_mb, erro_mb = _validate_magic_bytes(file, ext_for_magic)
        if not valido_mb:
            logger.warning(
                f"[AGENTE] Upload rejeitado (magic bytes): "
                f"{_safe_fname} — {erro_mb}"
            )
            return jsonify({
                'success': False,
                'error': f'Arquivo invalido: {erro_mb}'
            }), 400

        session_id = _sanitize_session_id(
            request.form.get('session_id', 'default')
        )
        folder = _get_session_folder(session_id)

        # Quota check (Fase D): max arquivos e soma total por sessao
        try:
            existing = [
                f for f in os.listdir(folder)
                if os.path.isfile(os.path.join(folder, f))
            ] if os.path.exists(folder) else []

            if len(existing) >= MAX_FILES_PER_SESSION:
                return jsonify({
                    'success': False,
                    'error': (
                        f'Limite de {MAX_FILES_PER_SESSION} arquivos por sessao '
                        f'atingido. Remova algum antes de enviar outro.'
                    )
                }), 413

            existing_total = sum(
                os.path.getsize(os.path.join(folder, f)) for f in existing
            )
            if existing_total + file_size > MAX_TOTAL_SIZE_PER_SESSION:
                usado_mb = existing_total / (1024 * 1024)
                novo_mb = file_size / (1024 * 1024)
                limite_mb = MAX_TOTAL_SIZE_PER_SESSION / (1024 * 1024)
                return jsonify({
                    'success': False,
                    'error': (
                        f'Quota da sessao excedida: '
                        f'{usado_mb:.1f}MB usados + {novo_mb:.1f}MB novo '
                        f'> {limite_mb:.0f}MB limite'
                    )
                }), 413
        except OSError as quota_err:
            logger.warning(
                f"[AGENTE] Check de quota falhou (nao fatal): {quota_err}"
            )

        original_name = secure_filename(file.filename)
        file_id = str(uuid.uuid4())[:8]
        safe_name = f"{file_id}_{original_name}"
        file_path = os.path.join(folder, safe_name)

        file.save(file_path)

        logger.info(f"[AGENTE] Arquivo uploaded: {safe_name} ({file_size} bytes)")

        return jsonify({
            'success': True,
            'file': {
                'id': file_id,
                'name': safe_name,
                'original_name': original_name,
                'size': file_size,
                'type': _get_file_type(original_name),
                'url': f'/agente/api/files/{session_id}/{safe_name}'
            }
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro no upload: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/files/<session_id>/<filename>', methods=['GET'])
@login_required
def api_download_file(session_id: str, filename: str):
    """
    Download de arquivo (Excel, PDF, CSV, imagens).

    Suporta dois caminhos:
    1. /tmp/agente_files/{user_id}/{session_id}/ (uploads do chat)
    2. /tmp/agente_files/{session_id}/ (arquivos gerados por skills CLI)
    """
    try:
        session_id = _sanitize_session_id(session_id)
        safe_filename = secure_filename(filename)
        if not safe_filename:
            return jsonify({
                'success': False,
                'error': 'Nome de arquivo invalido'
            }), 400
        logger.info(f"[AGENTE] Download solicitado: session={session_id}, file={safe_filename}")

        # Tentar caminho com user_id primeiro (uploads do chat)
        folder = _get_session_folder(session_id)
        file_path = os.path.join(folder, safe_filename)
        logger.debug(f"[AGENTE] Tentando path 1: {file_path}")

        # Fallback: caminho sem user_id (arquivos gerados por skills/scripts CLI)
        if not os.path.exists(file_path):
            fallback_folder = os.path.join(UPLOAD_FOLDER, session_id)
            fallback_path = os.path.join(fallback_folder, safe_filename)
            logger.debug(f"[AGENTE] Tentando path 2 (fallback): {fallback_path}")
            if os.path.exists(fallback_path):
                file_path = fallback_path

        if not os.path.exists(file_path):
            logger.warning(f"[AGENTE] Arquivo não encontrado: {safe_filename}")
            return jsonify({
                'success': False,
                'error': 'Arquivo não encontrado'
            }), 404

        # Extrai nome original (remove prefixo UUID se existir: "abc12345_nome.xlsx" -> "nome.xlsx")
        # UUID[:8] é sempre hexadecimal (0-9, a-f)
        original_name = safe_filename
        if '_' in safe_filename:
            prefix = safe_filename.split('_')[0]
            # Verifica se é um prefixo UUID válido (8 caracteres hexadecimais)
            if len(prefix) == 8 and all(c in '0123456789abcdef' for c in prefix.lower()):
                original_name = safe_filename.split('_', 1)[1]

        # Obtém MIME type correto (CRÍTICO para Excel e PDF)
        mimetype = _get_mimetype(safe_filename)
        logger.info(f"[AGENTE] Enviando arquivo: {original_name} ({mimetype})")

        # Imagens: exibir inline (no navegador)
        # Outros arquivos: forçar download
        ext = safe_filename.rsplit('.', 1)[-1].lower() if '.' in safe_filename else ''
        is_image = ext in ('png', 'jpg', 'jpeg', 'gif')

        # Parâmetro ?download=1 força download mesmo para imagens
        force_download = request.args.get('download', '0') == '1'

        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=(not is_image) or force_download,
            download_name=original_name
        )

    except Exception as e:
        logger.error(f"[AGENTE] Erro no download: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/files', methods=['GET'])
@login_required
def api_list_files():
    """
    Lista arquivos da sessao + metadata de quota.

    Fase D (2026-04-14): retorna tambem `quota` com uso atual e limites,
    permitindo UI mostrar "X de Y arquivos, Z de W MB usados".
    """
    try:
        session_id = _sanitize_session_id(
            request.args.get('session_id', 'default')
        )
        folder = _get_session_folder(session_id)

        files = []
        total_size = 0
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    total_size += size
                    # Extrai original_name apenas se prefixo for UUID 8-char hex
                    # (mesma logica de api_download_file; antes extraia
                    # incorretamente para arquivos com '_' no nome original)
                    original_name = filename
                    if '_' in filename:
                        prefix = filename.split('_')[0]
                        if len(prefix) == 8 and all(
                            c in '0123456789abcdef'
                            for c in prefix.lower()
                        ):
                            original_name = filename.split('_', 1)[1]
                    files.append({
                        'name': filename,
                        'original_name': original_name,
                        'size': size,
                        'type': _get_file_type(filename),
                        'url': f'/agente/api/files/{session_id}/{filename}',
                    })

        limite_bytes = MAX_TOTAL_SIZE_PER_SESSION or 1
        return jsonify({
            'success': True,
            'files': files,
            'quota': {
                'files_count': len(files),
                'files_limit': MAX_FILES_PER_SESSION,
                'total_bytes': total_size,
                'total_mb': round(total_size / (1024 * 1024), 2),
                'limit_bytes': MAX_TOTAL_SIZE_PER_SESSION,
                'limit_mb': MAX_TOTAL_SIZE_PER_SESSION // (1024 * 1024),
                'usage_percent': round(
                    (total_size / limite_bytes) * 100, 1
                ),
            },
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao listar arquivos: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agente_bp.route('/api/files/<session_id>/<filename>', methods=['DELETE'])
@login_required
def api_delete_file(session_id: str, filename: str):
    """Remove arquivo da sessão."""
    try:
        session_id = _sanitize_session_id(session_id)
        safe_filename = secure_filename(filename)
        if not safe_filename:
            return jsonify({
                'success': False,
                'error': 'Nome de arquivo invalido'
            }), 400
        folder = _get_session_folder(session_id)
        file_path = os.path.join(folder, safe_filename)

        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'Arquivo não encontrado'
            }), 404

        os.remove(file_path)
        logger.info(f"[AGENTE] Arquivo removido: {filename}")

        return jsonify({
            'success': True,
            'message': 'Arquivo removido'
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao remover arquivo: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# TODO: wire em api_delete_session — gap: arquivos orfaos sobrevivem exclusao de sessao
@agente_bp.route('/api/files/cleanup', methods=['POST'])
@login_required
def api_cleanup_files():
    """Limpa todos os arquivos da sessão."""
    try:
        data = request.get_json() or {}
        session_id = _sanitize_session_id(data.get('session_id', 'default'))
        folder = _get_session_folder(session_id)

        if os.path.exists(folder):
            shutil.rmtree(folder)
            os.makedirs(folder, exist_ok=True)
            logger.info(f"[AGENTE] Arquivos da sessão {session_id} limpos")

        return jsonify({
            'success': True,
            'message': 'Arquivos limpos'
        })

    except Exception as e:
        logger.error(f"[AGENTE] Erro ao limpar arquivos: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

"""Gerenciamento de arquivos do Agente (upload, download, listagem)."""

import logging
import os
import uuid
import shutil
from typing import Optional

from flask import request, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.agente.routes import agente_bp
from app.agente.routes._constants import UPLOAD_FOLDER, ALLOWED_EXTENSIONS, MAX_FILE_SIZE

logger = logging.getLogger('sistema_fretes')


def _allowed_file(filename: str) -> bool:
    """Verifica se a extensão do arquivo é permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _get_session_folder(session_id: str) -> str:
    """Retorna o caminho da pasta da sessão, criando se necessário."""
    folder = os.path.join(UPLOAD_FOLDER, str(current_user.id), session_id or 'default')
    os.makedirs(folder, exist_ok=True)
    return folder


def _get_file_type(filename: str) -> str:
    """Retorna o tipo do arquivo baseado na extensão."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in ('png', 'jpg', 'jpeg', 'gif'):
        return 'image'
    elif ext == 'pdf':
        return 'pdf'
    elif ext in ('xlsx', 'xls'):
        return 'excel'
    elif ext == 'csv':
        return 'csv'
    return 'file'


def _get_mimetype(filename: str) -> str:
    """Retorna o MIME type correto para o arquivo (prioriza Excel e PDF)."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    mimetypes = {
        # Excel - CRÍTICO para abrir corretamente
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'xls': 'application/vnd.ms-excel',
        # PDF - CRÍTICO para abrir corretamente
        'pdf': 'application/pdf',
        # CSV
        'csv': 'text/csv; charset=utf-8',
        # Imagens
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
    }
    return mimetypes.get(ext, 'application/octet-stream')


def _resolve_file_path(url: str) -> Optional[str]:
    """
    Resolve URL de arquivo para caminho local.

    Args:
        url: URL do arquivo (ex: /agente/api/files/session/uuid_file.png)

    Returns:
        Caminho absoluto do arquivo ou None se não encontrado
    """
    if not url:
        return None

    # Extrair partes da URL: /agente/api/files/{session_id}/{filename}
    parts = url.split('/')
    if len(parts) < 5:
        return None

    try:
        # Formato: ['', 'agente', 'api', 'files', 'session_id', 'filename']
        session_id = parts[-2]
        filename = parts[-1]

        # Tentar caminho com user_id primeiro
        if hasattr(current_user, 'id'):
            user_folder = os.path.join(UPLOAD_FOLDER, str(current_user.id), session_id)
            user_path = os.path.join(user_folder, filename)
            if os.path.exists(user_path):
                return user_path

        # Fallback: caminho sem user_id
        fallback_folder = os.path.join(UPLOAD_FOLDER, session_id)
        fallback_path = os.path.join(fallback_folder, filename)
        if os.path.exists(fallback_path):
            return fallback_path

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

        session_id = request.form.get('session_id', 'default')
        folder = _get_session_folder(session_id)

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
        safe_filename = secure_filename(filename)
        logger.info(f"[AGENTE] Download solicitado: session={session_id}, file={safe_filename}")

        # Tentar caminho com user_id primeiro (uploads do chat)
        folder = _get_session_folder(session_id)
        file_path = os.path.join(folder, safe_filename)
        logger.debug(f"[AGENTE] Tentando path 1: {file_path}")

        # Fallback: caminho sem user_id (arquivos gerados por skills/scripts CLI)
        if not os.path.exists(file_path):
            fallback_folder = os.path.join(UPLOAD_FOLDER, session_id or 'default')
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
    """Lista arquivos da sessão."""
    try:
        session_id = request.args.get('session_id', 'default')
        folder = _get_session_folder(session_id)

        files = []
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    files.append({
                        'name': filename,
                        'original_name': filename.split('_', 1)[1] if '_' in filename else filename,
                        'size': os.path.getsize(file_path),
                        'type': _get_file_type(filename),
                        'url': f'/agente/api/files/{session_id}/{filename}'
                    })

        return jsonify({
            'success': True,
            'files': files
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
        folder = _get_session_folder(session_id)
        file_path = os.path.join(folder, secure_filename(filename))

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
        session_id = data.get('session_id', 'default')
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

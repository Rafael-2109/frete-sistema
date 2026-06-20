"""Persistencia S3 + recuperacao de uploads do chat (IMP-2026-06-19-007).

Causa-raiz (IMP-2026-06-20-002 / IMP-2026-06-19-008): anexos do chat ficam so
em /tmp/agente_files/{user_id}/{session_id}/ (efemero). Na rotacao de sessao por
idle o session_id muda e os arquivos ficam orfaos. Aqui persistimos no S3 (dual-write)
com manifesto em agente_upload, permitindo recuperar entre sessoes.

Degradacao segura: com USE_S3 off (dev), persistir_upload_s3 retorna None (no-op)
e nada quebra — o upload local em /tmp segue valido.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import List, Dict, Optional

from app import db
from app.agente.models import AgenteUpload
from app.utils.file_storage import get_file_storage
from app.utils.timezone import agora_brasil_naive

logger = logging.getLogger(__name__)

TTL_DIAS = 90
S3_PREFIXO = 'agente-uploads'


def persistir_upload_s3(file_path, *, user_id, session_id, file_id, original_name,
                        safe_name, file_type, size_bytes) -> Optional[AgenteUpload]:
    """Grava o upload no S3 (se use_s3) e cria/atualiza a linha do manifesto.

    Le do ARQUIVO LOCAL ja salvo (`file_path`), NAO do stream da request: o
    stream do Werkzeug fica exausto apos `file.save()` e re-upar dele subiria
    0 bytes ao S3 (revisao 2026-06-20).

    Retorna None se USE_S3 off (sem persistencia, nao-fatal) ou se o save_file
    falhar. O upsert por (user_id, safe_name) e DEFENSIVO contra a UNIQUE
    constraint; na pratica cada upload gera linha nova (file_id e um uuid novo a
    cada envio, entao safe_name difere). Limpeza por TTL/`expira_em` e follow-up.
    """
    storage = get_file_storage()
    if not storage.use_s3:
        return None  # dev / USE_S3 off — sem persistencia, nao-fatal
    folder = f"{S3_PREFIXO}/{user_id}"
    with open(file_path, 'rb') as fh:
        s3_key = storage.save_file(fh, folder, filename=safe_name)  # retorna folder/filename
    if not s3_key:
        # save_file logou o erro e retornou None — nao-fatal
        return None
    now = agora_brasil_naive()
    existente = AgenteUpload.query.filter_by(user_id=user_id, safe_name=safe_name).first()
    if existente:
        existente.s3_key = s3_key
        existente.session_id = session_id
        existente.ativo = True
        existente.criado_em = now
        existente.expira_em = now + timedelta(days=TTL_DIAS)
        db.session.flush()
        return existente
    up = AgenteUpload(
        user_id=user_id, session_id=session_id, file_id=file_id,
        original_name=original_name, safe_name=safe_name, s3_key=s3_key,
        file_type=file_type, size_bytes=size_bytes, criado_em=now,
        expira_em=now + timedelta(days=TTL_DIAS), ativo=True)
    db.session.add(up)
    db.session.flush()
    return up


def listar_uploads_usuario(user_id, *, dias=7) -> List[Dict]:
    """Lista uploads ativos do usuario nos ultimos `dias` (mais recentes primeiro)."""
    corte = agora_brasil_naive() - timedelta(days=dias)
    rows = (AgenteUpload.query
            .filter(AgenteUpload.user_id == user_id, AgenteUpload.ativo.is_(True),
                    AgenteUpload.criado_em >= corte)
            .order_by(AgenteUpload.criado_em.desc()).all())
    return [{
        'file_id': r.file_id, 'original_name': r.original_name,
        'file_type': r.file_type, 'size_bytes': r.size_bytes,
        'session_id': r.session_id, 's3_key': r.s3_key,
        'criado_em': r.criado_em.isoformat() if r.criado_em else None,
    } for r in rows]


def recuperar_upload(user_id, file_id, *, target_session_id) -> Optional[str]:
    """Baixa do S3 um upload anterior para o /tmp da sessao ATUAL.

    Retorna o path local gravado, ou None se: nao houver manifesto ativo para
    (user_id, file_id); USE_S3 estiver off; ou o objeto S3 estiver indisponivel.
    """
    import os
    from werkzeug.utils import secure_filename
    from app.agente.routes.files import _get_session_folder_for_user
    storage = get_file_storage()
    if not storage.use_s3:
        return None  # USE_S3 off — manifesto pode existir mas o objeto nao e recuperavel
    row = (AgenteUpload.query
           .filter_by(user_id=user_id, file_id=file_id, ativo=True)
           .order_by(AgenteUpload.criado_em.desc()).first())
    if not row:
        return None
    conteudo = storage.download_file(row.s3_key)  # bytes ou None
    if conteudo is None:
        return None
    destino_dir = _get_session_folder_for_user(user_id, target_session_id)
    # Defense-in-depth: safe_name vem do banco; re-sanitiza e confina na pasta.
    nome_local = secure_filename(row.safe_name) or row.file_id
    destino = os.path.join(destino_dir, nome_local)
    if not os.path.realpath(destino).startswith(os.path.realpath(destino_dir) + os.sep):
        logger.warning(
            f"[AGENTE] recuperar_upload: caminho fora da pasta da sessao bloqueado: {destino}")
        return None
    with open(destino, 'wb') as fh:
        fh.write(conteudo)
    return destino

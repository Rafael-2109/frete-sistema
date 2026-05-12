"""
Endpoints para Artifacts do Agente.

Rotas (prefix /agente):
  GET  /artifact/<token>/status   JSON status (polling pelo frontend)
  GET  /artifact/<token>          Pagina wrapper com iframe sandboxed (login required)
  GET  /artifact/<token>/bundle   Serve bundle.html cru (sem login — iframe src)

Seguranca:
- Token HMAC com SECRET_KEY (itsdangerous, TTL 7d)
- Status + wrapper exigem login + ownership (current_user.id == artifact.user_id)
- Bundle endpoint serve apenas via token assinado (necessario para iframe)
- CSP restritivo no bundle
- iframe sandbox="allow-scripts" (sem allow-same-origin)
"""

import logging

from flask import (
    Response,
    abort,
    jsonify,
    render_template,
    request,
)
from flask_login import current_user, login_required

from app.agente.routes import agente_bp
from app.agente.services import artifact_service

logger = logging.getLogger('sistema_fretes')


# =====================================================================
# Helpers
# =====================================================================

def _check_ownership(artifact, allow_admin: bool = True) -> bool:
    """Valida que current_user e dono do artifact (ou admin)."""
    if not current_user or not getattr(current_user, 'is_authenticated', False):
        return False
    if int(current_user.id) == int(artifact.user_id):
        return True
    if allow_admin and getattr(current_user, 'perfil', None) == 'administrador':
        return True
    return False


# =====================================================================
# GET /agente/artifact/<token>/status
# =====================================================================

@agente_bp.route('/artifact/<token>/status', methods=['GET'])
@login_required
def artifact_status(token: str):
    """Polling pelo frontend. Retorna status atual + metadata."""
    artifact = artifact_service.verify_token(token)
    if artifact is None:
        return jsonify({'error': 'token_invalido_ou_expirado'}), 404

    if not _check_ownership(artifact):
        logger.warning(
            f"[artifact] status sem ownership: user={current_user.id} "
            f"artifact_user={artifact.user_id} uuid={artifact.uuid[:8]}"
        )
        return jsonify({'error': 'forbidden'}), 403

    payload = artifact.to_dict()
    payload['render_url'] = f"/agente/artifact/{token}"
    return jsonify(payload)


# =====================================================================
# GET /agente/artifact/<token>  — pagina wrapper
# =====================================================================

@agente_bp.route('/artifact/<token>', methods=['GET'])
@login_required
def artifact_page(token: str):
    """Renderiza pagina wrapper com iframe sandboxed apontando para /bundle."""
    artifact = artifact_service.verify_token(token)
    if artifact is None:
        abort(404)
    if not _check_ownership(artifact):
        logger.warning(
            f"[artifact] page sem ownership: user={current_user.id} "
            f"artifact_user={artifact.user_id} uuid={artifact.uuid[:8]}"
        )
        abort(403)

    if not artifact.is_ready():
        # Renderiza pagina com mensagem de status (building/error/etc.)
        return render_template(
            'agente/artifact.html',
            artifact=artifact,
            token=token,
            bundle_url=None,
        )

    bundle_url = f"/agente/artifact/{token}/bundle"
    return render_template(
        'agente/artifact.html',
        artifact=artifact,
        token=token,
        bundle_url=bundle_url,
    )


# =====================================================================
# GET /agente/api/artifacts  — lista artifacts do usuario (drawer)
# =====================================================================

@agente_bp.route('/api/artifacts', methods=['GET'])
@login_required
def api_list_artifacts():
    """
    Lista artifacts do usuario atual (mais novos primeiro).

    Query params:
        limit: int (default 50, max 200)
        offset: int (default 0)

    Returns JSON:
        {"artifacts": [{...}], "total": int}
    """
    user_id = int(current_user.id)

    try:
        limit = min(int(request.args.get('limit', 50)), 200)
        offset = max(int(request.args.get('offset', 0)), 0)
    except (ValueError, TypeError):
        return jsonify({'error': 'limit/offset invalidos'}), 400

    try:
        artifacts = artifact_service.get_user_artifacts(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
        return jsonify({
            'artifacts': [a.to_dict() for a in artifacts],
            'count': len(artifacts),
            'limit': limit,
            'offset': offset,
        })
    except Exception as e:
        logger.error(f"[artifact] api_list_artifacts erro: {e}", exc_info=True)
        return jsonify({'error': 'internal_error', 'detail': str(e)[:200]}), 500


# =====================================================================
# GET /agente/api/artifact/by-uuid/<uuid>/url
#   Regera token fresh para um artifact (login + ownership). Usado pelo
#   drawer quando user abre artifact antigo (token original expirou em
#   browser cache mas artifact persiste no DB).
# =====================================================================

@agente_bp.route('/api/artifact/by-uuid/<artifact_uuid>/url', methods=['GET'])
@login_required
def api_artifact_url(artifact_uuid: str):
    """Retorna URLs frescas (token recem-gerado) para artifact existente."""
    token = artifact_service.get_or_regenerate_token(
        user_id=int(current_user.id),
        artifact_uuid=artifact_uuid,
    )
    if token is None:
        return jsonify({'error': 'not_found_or_forbidden'}), 404

    artifact = artifact_service.get_artifact_by_uuid(artifact_uuid)
    if artifact is None:
        return jsonify({'error': 'not_found'}), 404

    return jsonify({
        'uuid': artifact.uuid,
        'titulo': artifact.titulo,
        'status': artifact.status,
        'token': token,
        'render_url': f"/agente/artifact/{token}",
        'status_url': f"/agente/artifact/{token}/status",
        'bundle_url': f"/agente/artifact/{token}/bundle" if artifact.is_ready() else None,
    })


# =====================================================================
# GET /agente/artifact/<token>/bundle  — sem login (iframe src)
# =====================================================================

@agente_bp.route('/artifact/<token>/bundle', methods=['GET'])
def artifact_bundle(token: str):
    """
    Serve bundle.html do S3. SEM login_required — iframe sandbox nao envia
    cookies. Auth e via token assinado HMAC.

    CSP restritivo aplicado para defesa em profundidade.
    """
    artifact = artifact_service.verify_token(token)
    if artifact is None:
        abort(404)

    if not artifact.is_ready():
        # Builds em progresso retornam 425 Too Early (cliente pode tentar de novo)
        return Response(
            f"Artifact ainda nao pronto (status={artifact.status})",
            status=425,
            mimetype='text/plain',
        )

    try:
        bundle_bytes = artifact_service.download_bundle_from_s3(artifact)
    except artifact_service.ArtifactError as e:
        logger.error(f"[artifact] download bundle falhou {artifact.uuid[:8]}: {e}")
        return Response("Falha ao carregar artifact.", status=500, mimetype='text/plain')

    # CSP defesa em profundidade. iframe sandbox ja restringe muito, mas
    # CSP previne fetch externo nao desejado.
    csp_header = (
        "default-src 'self' data: blob:; "
        "script-src 'unsafe-inline' 'self' data: blob:; "
        "style-src 'unsafe-inline' 'self'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "connect-src 'none'; "
        "frame-ancestors 'self'"
    )

    response = Response(bundle_bytes, mimetype='text/html; charset=utf-8')
    response.headers['Content-Security-Policy'] = csp_header
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'private, max-age=3600'  # 1h cache no browser
    return response

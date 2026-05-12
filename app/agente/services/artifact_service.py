"""
Artifact Service — Agente Web.

Gerenciamento de artifacts (bundle.html auto-contido) gerados pelo agente via
skill `gerando-artifact`. Build assincrono via worker RQ (queue 'artifacts').
Bundle final hospedado no S3 (prefix `agente/artifacts/`).

Componentes:
- create_artifact(user_id, session_id, titulo, spec) -> AgenteArtifact
- generate_token(artifact_uuid) -> str (HMAC + TTL via itsdangerous)
- verify_token(token) -> AgenteArtifact ou None
- upload_bundle_to_s3(artifact, bundle_path) -> bool
- download_bundle_from_s3(artifact) -> bytes
- check_rate_limit(user_id) -> bool (max 5/hora via Redis)

Seguranca:
- Token HMAC com SECRET_KEY do app (TTL 7d default)
- Bundle servido em iframe sandboxed sem cookies
- Limite 5MB no bundle final
- Rate limit 5 artifacts/usuario/hora

Modelo: AgenteArtifact (app/agente/models.py)
Migration: scripts/migrations/2026_05_12_agente_artifacts.{py,sql}
Skill: .claude/skills/gerando-artifact/
"""

import io
import logging
import os
import uuid
from datetime import timedelta
from typing import Any, Dict, Optional

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.datastructures import FileStorage as WerkzeugFileStorage

from app import db
from app.agente.models import AgenteArtifact
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


def _get_redis_conn():
    """Retorna cliente Redis ou None se indisponivel. Best-effort."""
    try:
        import redis
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        return redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
    except Exception as e:
        logger.debug(f"[artifact] Redis indisponivel: {e}")
        return None

# ===== Constantes =====
# Politica de persistencia (2026-05-12): artifacts NAO expiram automaticamente.
# `expires_at` mantido para evolucao futura (ex: cleanup opcional), mas default
# eh 100 anos no futuro — efetivamente sem expiracao.
ARTIFACT_TTL_DAYS = 365 * 100  # ~100 anos (sem expiracao efetiva)
# Token assinado tem TTL de 1 ano. Para acessar artifacts mais antigos,
# usar endpoint /api/artifact/by-uuid/<uuid>/url que regera token novo
# (requer login + ownership).
TOKEN_TTL_SECONDS = 365 * 24 * 3600  # 1 ano
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW_SECONDS = 3600  # 1h
BUNDLE_MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
S3_FOLDER_PREFIX = 'agente/artifacts'
TOKEN_SALT = 'agente-artifact-v1'
RQ_QUEUE_NAME = 'artifacts'
RQ_JOB_TIMEOUT_SECONDS = 300  # 5 min para build


class ArtifactError(Exception):
    """Erro de operacao em artifact (rate limit, spec invalida, etc.)."""
    pass


class ArtifactRateLimitError(ArtifactError):
    """Usuario excedeu rate limit (5/hora)."""
    pass


# =====================================================================
# Token signing (itsdangerous)
# =====================================================================

def _get_serializer() -> URLSafeTimedSerializer:
    """Serializer HMAC com SECRET_KEY do Flask."""
    secret = current_app.config.get('SECRET_KEY')
    if not secret:
        raise ArtifactError("SECRET_KEY nao configurado no Flask app")
    return URLSafeTimedSerializer(secret_key=secret, salt=TOKEN_SALT)


def generate_token(artifact_uuid: str) -> str:
    """Gera token assinado para uuid do artifact. TTL gerenciado em verify."""
    serializer = _get_serializer()
    return serializer.dumps({'uuid': artifact_uuid})


def verify_token(token: str) -> Optional[AgenteArtifact]:
    """
    Verifica token e retorna AgenteArtifact se valido.

    Validacoes:
    - HMAC valido (assinatura)
    - Token nao expirado (TTL_SECONDS)
    - Artifact existe no DB
    - Artifact nao expirou (expires_at)

    Returns: AgenteArtifact ou None.
    """
    serializer = _get_serializer()
    try:
        data = serializer.loads(token, max_age=TOKEN_TTL_SECONDS)
    except SignatureExpired:
        logger.warning("[artifact] token expirado")
        return None
    except BadSignature:
        logger.warning("[artifact] token invalido (bad signature)")
        return None
    except Exception as e:
        logger.error(f"[artifact] erro ao decodificar token: {e}")
        return None

    artifact_uuid = data.get('uuid') if isinstance(data, dict) else None
    if not artifact_uuid:
        return None

    artifact = AgenteArtifact.query.filter_by(uuid=artifact_uuid).first()
    if not artifact:
        logger.warning(f"[artifact] uuid {artifact_uuid[:8]}... nao encontrado")
        return None

    # Expirado por tempo, mesmo se token ainda valido
    if artifact.is_expired():
        if artifact.status != AgenteArtifact.STATUS_EXPIRED:
            artifact.status = AgenteArtifact.STATUS_EXPIRED
            db.session.commit()
        return None

    return artifact


# =====================================================================
# Rate limiting (Redis)
# =====================================================================

def check_rate_limit(user_id: int) -> None:
    """
    Verifica e incrementa rate limit do user (5/hora).

    Raises:
        ArtifactRateLimitError se excedido.
    """
    redis_client = _get_redis_conn()
    if redis_client is None:
        # Sem Redis: degrada permissivo (log warning, continua)
        logger.warning("[artifact] rate limit skip (Redis indisponivel)")
        return

    key = f"agent:artifact:rate:{user_id}"
    try:
        # Atomico via pipeline MULTI/EXEC para evitar race condition entre
        # INCR e EXPIRE (sem isso, duas requisicoes podem ambas incr antes do
        # primeiro expire, deixando key sem TTL e bloqueando o usuario permanente).
        # SET NX+EX cria key=1 com TTL se nao existe; INCR retorna 1 nesse caso.
        # Em ambos os caminhos o TTL e garantido.
        pipe = redis_client.pipeline(transaction=True)
        pipe.set(key, 0, nx=True, ex=RATE_LIMIT_WINDOW_SECONDS)
        pipe.incr(key)
        results = pipe.execute()
        current = int(results[1] or 0)
        if current > RATE_LIMIT_MAX:
            raise ArtifactRateLimitError(
                f"Rate limit excedido: {RATE_LIMIT_MAX} artifacts/hora "
                f"(atual: {current})"
            )
    except ArtifactRateLimitError:
        raise
    except Exception as e:
        logger.error(f"[artifact] rate limit erro Redis: {e}")
        # Permissivo se Redis falha


# =====================================================================
# Spec validation
# =====================================================================

def _validate_spec(spec: Any) -> None:
    """Valida spec do artifact. Raises ArtifactError se invalida."""
    if not isinstance(spec, dict):
        raise ArtifactError("spec deve ser dict")

    components = spec.get('components')
    if not isinstance(components, list) or not components:
        raise ArtifactError("spec.components deve ser lista nao-vazia")

    has_app = False
    for i, comp in enumerate(components):
        if not isinstance(comp, dict):
            raise ArtifactError(f"components[{i}] deve ser dict")
        path = comp.get('path')
        content = comp.get('content')
        if not isinstance(path, str) or not path.strip():
            raise ArtifactError(f"components[{i}].path obrigatorio")
        if not isinstance(content, str):
            raise ArtifactError(f"components[{i}].content deve ser string")

        # Sanity: path nao pode escapar src/
        if '..' in path or path.startswith('/'):
            raise ArtifactError(f"components[{i}].path invalido: {path}")
        if not path.startswith('src/'):
            raise ArtifactError(
                f"components[{i}].path deve comecar com 'src/': {path}"
            )
        if path == 'src/App.tsx':
            has_app = True

        # Tamanho razoavel por componente (evitar bomba)
        if len(content) > 200_000:
            raise ArtifactError(
                f"components[{i}].content > 200KB (path={path})"
            )

    if not has_app:
        raise ArtifactError(
            "spec.components deve conter 'src/App.tsx' (entry component)"
        )

    deps = spec.get('dependencies')
    if deps is not None:
        if not isinstance(deps, dict):
            raise ArtifactError("spec.dependencies deve ser dict (name -> version)")
        for name, version in deps.items():
            if not isinstance(name, str) or not isinstance(version, str):
                raise ArtifactError(
                    "spec.dependencies entries devem ser string -> string"
                )
            # Sanity: nome nao pode injetar shell
            if any(c in name for c in [';', '&', '|', '$', '`', '\n']):
                raise ArtifactError(f"dependency name invalido: {name}")


# =====================================================================
# Create / enqueue
# =====================================================================

def create_artifact(
    user_id: int,
    session_id: Optional[str],
    titulo: str,
    spec: Dict[str, Any],
) -> AgenteArtifact:
    """
    Cria AgenteArtifact (status=queued) e enfileira RQ job para build.

    Args:
        user_id: dono do artifact
        session_id: sessao do agente (opcional, para auditoria)
        titulo: titulo amigavel (max 200 chars)
        spec: dict com {components: [{path, content}], dependencies?: {}}

    Returns:
        AgenteArtifact persistido com status=queued. Token gerado depois via
        generate_token(artifact.uuid).

    Raises:
        ArtifactRateLimitError, ArtifactError
    """
    # Rate limit
    check_rate_limit(user_id)

    # Validar spec
    _validate_spec(spec)

    # Validar titulo
    if not isinstance(titulo, str) or not titulo.strip():
        raise ArtifactError("titulo obrigatorio")
    titulo = titulo.strip()[:200]

    # Criar registro
    artifact_uuid = str(uuid.uuid4())
    now = agora_utc_naive()
    expires_at = now + timedelta(days=ARTIFACT_TTL_DAYS)

    # CLAUDE.md rule: sanitize_for_json em campos JSONB cuja origem nao
    # controlamos 100%. Spec vem da tool call do LLM — pode conter Decimal,
    # datetime, UUID, bytes se LLM gerar dado sintetico problematico.
    from app.utils.json_helpers import sanitize_for_json

    artifact = AgenteArtifact(
        uuid=artifact_uuid,
        user_id=user_id,
        session_id=session_id,
        titulo=titulo,
        status=AgenteArtifact.STATUS_QUEUED,
        spec_json=sanitize_for_json(spec),
        created_at=now,
        expires_at=expires_at,
    )
    db.session.add(artifact)
    try:
        db.session.commit()
    except Exception as commit_err:
        # CRITICAL: commit pode falhar (IntegrityError em uuid duplicado,
        # OperationalError em SSL drop, etc.). Sem rollback aqui a session
        # fica abortada e contamina o pool — pattern_analyzer e outras
        # daemon threads recebem InFailedSqlTransaction nas proximas queries.
        logger.error(
            f"[artifact] commit principal falhou: {commit_err}", exc_info=True
        )
        try:
            db.session.rollback()
        except Exception:
            pass
        raise ArtifactError(f"Falha ao persistir artifact: {commit_err}") from commit_err

    logger.info(
        f"[artifact] criado uuid={artifact_uuid[:8]} user={user_id} "
        f"titulo={titulo[:40]!r}"
    )

    # Enfileirar RQ job
    try:
        from rq import Queue

        redis_conn = _get_redis_conn()
        if redis_conn is None:
            raise ArtifactError("Redis indisponivel para RQ")

        q = Queue(RQ_QUEUE_NAME, connection=redis_conn)
        job = q.enqueue(
            'app.agente.workers.artifact_worker.build_artifact_job',
            args=(artifact.id,),
            job_timeout=RQ_JOB_TIMEOUT_SECONDS,
            result_ttl=3600,
            failure_ttl=86400,
        )
        logger.info(
            f"[artifact] enfileirado uuid={artifact_uuid[:8]} job_id={job.id}"
        )
    except Exception as e:
        logger.error(f"[artifact] enqueue falhou: {e}", exc_info=True)
        # Marcar como erro (com rollback defensivo se commit do status falhar)
        try:
            artifact.status = AgenteArtifact.STATUS_ERROR
            artifact.error_message = f"Enqueue falhou: {str(e)[:500]}"
            db.session.commit()
        except Exception as status_err:
            logger.error(f"[artifact] commit status=error falhou: {status_err}")
            try:
                db.session.rollback()
            except Exception:
                pass
        raise ArtifactError(f"Falha ao enfileirar build: {e}") from e

    return artifact


# =====================================================================
# S3 upload / download
# =====================================================================

def s3_key_for_artifact(artifact: AgenteArtifact) -> str:
    """Path S3 deterministico: agente/artifacts/{user_id}/{uuid}.html"""
    return f"{S3_FOLDER_PREFIX}/{artifact.user_id}/{artifact.uuid}.html"


def upload_bundle_to_s3(artifact: AgenteArtifact, bundle_bytes: bytes) -> str:
    """
    Faz upload do bundle.html para S3. Atualiza artifact.s3_key e
    artifact.bundle_size_bytes. NAO faz commit (caller decide).

    Args:
        artifact: AgenteArtifact (status=building)
        bundle_bytes: conteudo do bundle.html

    Returns:
        s3_key gravado.

    Raises:
        ArtifactError se bundle exceder 5MB ou upload falhar.
    """
    size = len(bundle_bytes)
    if size > BUNDLE_MAX_SIZE_BYTES:
        raise ArtifactError(
            f"Bundle excede {BUNDLE_MAX_SIZE_BYTES} bytes ({size} bytes)"
        )

    from app.utils.file_storage import get_file_storage
    storage = get_file_storage()

    folder = f"{S3_FOLDER_PREFIX}/{artifact.user_id}"
    filename = f"{artifact.uuid}.html"

    bio = io.BytesIO(bundle_bytes)
    file_obj = WerkzeugFileStorage(
        stream=bio,
        filename=filename,
        content_type='text/html; charset=utf-8',
    )

    s3_path = storage.save_file(
        file=file_obj,
        folder=folder,
        filename=filename,
        allowed_extensions=['html'],
    )

    if not s3_path:
        raise ArtifactError("Falha no upload S3 (save_file retornou None)")

    artifact.s3_key = s3_path
    artifact.bundle_size_bytes = size

    logger.info(
        f"[artifact] upload OK uuid={artifact.uuid[:8]} "
        f"size={size}B path={s3_path}"
    )
    return s3_path


def download_bundle_from_s3(artifact: AgenteArtifact) -> bytes:
    """
    Baixa bundle.html do S3.

    Raises:
        ArtifactError se artifact nao ready ou download falhar.
    """
    if not artifact.is_ready():
        raise ArtifactError(
            f"Artifact {artifact.uuid[:8]} nao esta ready "
            f"(status={artifact.status})"
        )
    if not artifact.s3_key:
        raise ArtifactError(f"Artifact {artifact.uuid[:8]} sem s3_key")

    from app.utils.file_storage import get_file_storage
    storage = get_file_storage()

    try:
        data = storage.download_file(artifact.s3_key)
        if not data:
            raise ArtifactError("download_file retornou vazio")
        return data
    except Exception as e:
        logger.error(
            f"[artifact] download falhou uuid={artifact.uuid[:8]}: {e}"
        )
        raise ArtifactError(f"S3 download falhou: {e}") from e


# =====================================================================
# Lookup helpers
# =====================================================================

def get_artifact_by_uuid(artifact_uuid: str) -> Optional[AgenteArtifact]:
    """Lookup direto por uuid (sem validar token)."""
    return AgenteArtifact.query.filter_by(uuid=artifact_uuid).first()


def get_user_artifacts(user_id: int, limit: int = 50, offset: int = 0) -> list:
    """Lista artifacts recentes do usuario (mais novos primeiro)."""
    return (
        AgenteArtifact.query
        .filter_by(user_id=user_id)
        .order_by(AgenteArtifact.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def get_or_regenerate_token(user_id: int, artifact_uuid: str) -> Optional[str]:
    """
    Retorna token assinado fresh para um artifact, validando ownership.

    Usado pelo endpoint /api/artifact/by-uuid/<uuid>/url quando usuario
    quer abrir artifact antigo (token original expirou). Regerar e ok
    porque ja validamos login + user_id == artifact.user_id antes.

    Returns:
        Token string se OK, None se artifact nao existe ou nao pertence ao user.
    """
    artifact = AgenteArtifact.query.filter_by(uuid=artifact_uuid).first()
    if artifact is None:
        return None
    if int(artifact.user_id) != int(user_id):
        return None
    return generate_token(artifact.uuid)

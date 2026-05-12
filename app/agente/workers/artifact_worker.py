"""
Artifact Worker — RQ job que builda bundle.html via scripts da skill.

Pipeline:
  1. Marca AgenteArtifact.status='building', build_started_at=now
  2. Cria /tmp/artifact-build/{uuid}/
  3. Roda .claude/skills/gerando-artifact/scripts/init-artifact.sh <project-dir>
  4. Escreve spec.components em src/ (sobrescreve App.tsx etc.)
  5. Se spec.dependencies: roda npm install adicional
  6. Roda bundle-artifact.sh -> bundle.html
  7. Upload bundle.html para S3 via artifact_service
  8. Marca status='ready', build_completed_at=now
  9. Cleanup /tmp/

Em caso de erro: status='error', error_message preservado.

Queue: 'artifacts' (worker_artifacts.py)
Timeout: 300s (5 min, controlado pela enqueue em artifact_service)
"""
import glob
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger('sistema_fretes')


def _ensure_node_in_path(env: dict) -> dict:
    """
    Garante que Node/npm estao no PATH do subprocess.

    Worker pode ter sido iniciado por start_worker_render.sh (Render) que ja
    exporta PATH com Node. Mas se nao tem (ex: gunicorn herdou env limpo, dev
    local em venv sem Node global), tenta descobrir bin do Node via NVM dir
    ou paths comuns.

    Returns env dict possivelmente com PATH atualizado.
    """
    # 1. Se ja resolve via PATH atual, nada a fazer
    if shutil.which('node') and shutil.which('npm'):
        return env

    candidates = []
    # 2. NVM
    nvm_dir = env.get('NVM_DIR') or os.path.expanduser('~/.nvm')
    if os.path.isdir(nvm_dir):
        # nvm bin paths: ~/.nvm/versions/node/v20.x.y/bin
        for nvm_node in sorted(glob.glob(os.path.join(nvm_dir, 'versions/node/v*/bin')), reverse=True):
            candidates.append(nvm_node)

    # 3. /usr/local/bin, /usr/bin (system-installed Node)
    candidates.extend(['/usr/local/bin', '/usr/bin'])

    for path in candidates:
        if os.path.exists(os.path.join(path, 'node')) and os.path.exists(os.path.join(path, 'npm')):
            existing = env.get('PATH', '')
            env['PATH'] = f"{path}:{existing}" if existing else path
            logger.info(f"[ARTIFACT_WORKER] Node bin prependado ao PATH: {path}")
            return env

    logger.warning(
        "[ARTIFACT_WORKER] Node bin nao encontrado em NVM/usr — build vai falhar"
    )
    return env


# ===== Constantes =====
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SKILL_SCRIPTS_DIR = PROJECT_ROOT / '.claude' / 'skills' / 'gerando-artifact' / 'scripts'
INIT_SCRIPT = SKILL_SCRIPTS_DIR / 'init-artifact.sh'
BUNDLE_SCRIPT = SKILL_SCRIPTS_DIR / 'bundle-artifact.sh'
BUILD_BASE_DIR = Path(tempfile.gettempdir()) / 'artifact-build'
SUBPROCESS_TIMEOUT = 240  # 4 min (deixa folga vs 5min RQ timeout)


def build_artifact_job(artifact_id: int) -> dict:
    """
    Job RQ que builda bundle.html para um AgenteArtifact.

    Args:
        artifact_id: ID da linha em agente_artifacts.

    Returns:
        dict com {success, uuid, status, s3_key?, error?}.
    """
    from app import create_app, db
    from app.agente.models import AgenteArtifact
    from app.agente.services import artifact_service
    from app.utils.timezone import agora_utc_naive

    app = create_app()
    with app.app_context():
        artifact = AgenteArtifact.query.get(artifact_id)
        if artifact is None:
            logger.error(f"[ARTIFACT_WORKER] artifact_id={artifact_id} nao encontrado")
            return {'success': False, 'error': 'artifact_not_found'}

        if artifact.status != AgenteArtifact.STATUS_QUEUED:
            logger.warning(
                f"[ARTIFACT_WORKER] uuid={artifact.uuid[:8]} status={artifact.status} "
                f"(esperado queued) — skip"
            )
            return {'success': False, 'error': f'invalid_status_{artifact.status}'}

        # ===== Marcar building =====
        artifact.status = AgenteArtifact.STATUS_BUILDING
        artifact.build_started_at = agora_utc_naive()
        db.session.commit()
        logger.info(f"[ARTIFACT_WORKER] iniciando build uuid={artifact.uuid[:8]}")

        project_dir = BUILD_BASE_DIR / artifact.uuid

        try:
            # Setup
            BUILD_BASE_DIR.mkdir(parents=True, exist_ok=True)
            if project_dir.exists():
                shutil.rmtree(project_dir)

            spec = artifact.spec_json or {}
            if not isinstance(spec, dict):
                raise RuntimeError("spec_json invalido (nao e dict)")

            # ===== Passo 1: init-artifact.sh =====
            _run_init(project_dir)

            # ===== Passo 2: aplicar componentes da spec =====
            _apply_components(project_dir, spec.get('components', []))

            # ===== Passo 3: dependencies extras =====
            extra_deps = spec.get('dependencies') or {}
            if extra_deps:
                _install_extra_deps(project_dir, extra_deps)

            # ===== Passo 4: bundle =====
            bundle_path = project_dir / 'bundle.html'
            _run_bundle(project_dir, bundle_path)

            if not bundle_path.exists():
                raise RuntimeError("bundle.html nao foi gerado")

            # ===== Passo 5: upload S3 =====
            bundle_bytes = bundle_path.read_bytes()
            artifact_service.upload_bundle_to_s3(artifact, bundle_bytes)

            # ===== Passo 6: finalizar =====
            artifact.status = AgenteArtifact.STATUS_READY
            artifact.build_completed_at = agora_utc_naive()
            artifact.error_message = None
            db.session.commit()

            logger.info(
                f"[ARTIFACT_WORKER] OK uuid={artifact.uuid[:8]} "
                f"size={artifact.bundle_size_bytes}B"
            )
            return {
                'success': True,
                'uuid': artifact.uuid,
                'status': artifact.status,
                's3_key': artifact.s3_key,
            }

        except Exception as e:
            err_msg = str(e)[:1000]
            logger.error(
                f"[ARTIFACT_WORKER] FALHA uuid={artifact.uuid[:8]}: {err_msg}",
                exc_info=True,
            )
            try:
                artifact.status = AgenteArtifact.STATUS_ERROR
                artifact.error_message = err_msg
                artifact.build_completed_at = agora_utc_naive()
                db.session.commit()
            except Exception as commit_err:
                logger.error(
                    f"[ARTIFACT_WORKER] falha ao salvar erro: {commit_err}"
                )
                db.session.rollback()
            return {
                'success': False,
                'uuid': artifact.uuid,
                'status': AgenteArtifact.STATUS_ERROR,
                'error': err_msg,
            }
        finally:
            # Cleanup
            if project_dir.exists():
                try:
                    shutil.rmtree(project_dir, ignore_errors=True)
                except Exception:
                    pass


def _run_init(project_dir: Path) -> None:
    """Executa init-artifact.sh para criar projeto Vite baseline."""
    if not INIT_SCRIPT.exists():
        raise RuntimeError(f"init-artifact.sh nao encontrado: {INIT_SCRIPT}")

    logger.info(f"[ARTIFACT_WORKER] init -> {project_dir}")
    env = _ensure_node_in_path(os.environ.copy())
    result = subprocess.run(
        ['bash', str(INIT_SCRIPT), str(project_dir)],
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT,
        cwd=str(BUILD_BASE_DIR),
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"init-artifact.sh falhou (exit {result.returncode}): "
            f"stderr={result.stderr[-500:]}"
        )
    logger.debug(f"[ARTIFACT_WORKER] init stdout={result.stdout[-300:]}")


def _apply_components(project_dir: Path, components: list) -> None:
    """Escreve cada componente da spec em <project_dir>/<path>."""
    if not isinstance(components, list):
        raise RuntimeError("spec.components deve ser lista")

    for comp in components:
        path = comp.get('path')
        content = comp.get('content', '')
        if not path or not isinstance(path, str):
            raise RuntimeError("component sem path")

        # Path sanity: nao escapar do project_dir
        target = (project_dir / path).resolve()
        try:
            target.relative_to(project_dir.resolve())
        except ValueError:
            raise RuntimeError(f"component path escapa project_dir: {path}")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        logger.debug(f"[ARTIFACT_WORKER] write {path} ({len(content)} chars)")


def _install_extra_deps(project_dir: Path, deps: dict) -> None:
    """npm install para dependencies extras solicitadas pela spec."""
    # Validacao basica de nomes (anti-injection)
    safe_args = []
    for name, version in deps.items():
        if not isinstance(name, str) or not isinstance(version, str):
            raise RuntimeError(f"dependency invalida: {name}={version}")
        # Permitir apenas padrao npm: nome alfanumerico + - + _ + @/
        if not all(c.isalnum() or c in '-_/@.' for c in name):
            raise RuntimeError(f"dependency name invalido: {name}")
        if not all(c.isalnum() or c in '-_.^~>=<*x' for c in version):
            raise RuntimeError(f"dependency version invalida: {version}")
        safe_args.append(f"{name}@{version}")

    logger.info(f"[ARTIFACT_WORKER] npm install extra: {safe_args}")
    env = _ensure_node_in_path(os.environ.copy())
    result = subprocess.run(
        ['npm', 'install', *safe_args],
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT,
        cwd=str(project_dir),
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"npm install (extras) falhou: stderr={result.stderr[-500:]}"
        )


def _run_bundle(project_dir: Path, bundle_path: Path) -> None:
    """Executa bundle-artifact.sh para gerar bundle.html."""
    if not BUNDLE_SCRIPT.exists():
        raise RuntimeError(f"bundle-artifact.sh nao encontrado: {BUNDLE_SCRIPT}")

    env = _ensure_node_in_path(os.environ.copy())
    env['BUNDLE_OUT'] = str(bundle_path)

    logger.info(f"[ARTIFACT_WORKER] bundle -> {bundle_path}")
    result = subprocess.run(
        ['bash', str(BUNDLE_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT,
        cwd=str(project_dir),
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"bundle-artifact.sh falhou (exit {result.returncode}): "
            f"stderr={result.stderr[-500:]}"
        )
    logger.debug(f"[ARTIFACT_WORKER] bundle stdout={result.stdout[-300:]}")

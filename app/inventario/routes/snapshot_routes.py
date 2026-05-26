"""Refresh assíncrono do snapshot Odoo via worker RQ."""
import os
from flask import jsonify
from flask_login import login_required
from rq import Queue
from redis import Redis
from app.inventario import inventario_bp
from app.inventario.models import CicloInventario
from app.utils.auth_decorators import require_admin


def _redis_conn():
    url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    return Redis.from_url(url)


@inventario_bp.route('/snapshot/<int:ciclo_id>/refresh', methods=['POST'],
                      endpoint='snapshot_refresh')
@login_required
@require_admin
def refresh(ciclo_id):
    CicloInventario.query.get_or_404(ciclo_id)
    q = Queue('inventario', connection=_redis_conn())
    job = q.enqueue(
        'app.inventario.workers.refresh_snapshot_worker.refresh_snapshot_worker',
        ciclo_id, job_timeout=900,
    )
    return jsonify({'job_id': job.id, 'status': 'enqueued'}), 202


@inventario_bp.route('/snapshot/<int:ciclo_id>/status/<job_id>',
                      endpoint='snapshot_status')
@login_required
@require_admin
def status(ciclo_id, job_id):
    from rq.job import Job
    try:
        job = Job.fetch(job_id, connection=_redis_conn())
    except Exception:
        return jsonify({'erro': 'job não encontrado'}), 404
    return jsonify({
        'status': job.get_status(),
        'progress': (job.meta or {}).get('progress'),
        'msg': (job.meta or {}).get('msg'),
        'result': job.result,
    })

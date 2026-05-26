"""Worker RQ que refresca snapshot Odoo."""
from app import create_app


def refresh_snapshot_worker(ciclo_id: int):
    app = create_app()
    with app.app_context():
        from rq import get_current_job
        from app.inventario.services.snapshot_odoo_service import SnapshotOdooService
        from app import db
        job = get_current_job()
        try:
            resultado = SnapshotOdooService.refresh(ciclo_id, job=job)
            db.session.commit()
            return resultado
        except Exception as exc:
            db.session.rollback()
            raise

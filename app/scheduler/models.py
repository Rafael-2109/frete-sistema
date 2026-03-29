"""
Model: Saude do Scheduler
=========================

Persiste resultado de cada step do scheduler para monitoramento.
Permite dashboard /admin/scheduler-health e alertas quando steps falham.
"""

from app import db
from app.utils.timezone import agora_utc_naive


class SchedulerHealth(db.Model):
    """Registro de execucao de cada step do scheduler."""
    __tablename__ = 'scheduler_health'
    __table_args__ = (
        db.Index('idx_sh_step_name', 'step_name'),
        db.Index('idx_sh_executado_em', 'executado_em'),
    )

    id = db.Column(db.Integer, primary_key=True)
    step_name = db.Column(db.String(100), nullable=False)
    step_number = db.Column(db.Integer, nullable=False)
    executado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    status = db.Column(db.String(20), nullable=False)  # OK, ERRO, SKIP
    duracao_ms = db.Column(db.Integer, nullable=True)  # Duracao em milissegundos
    erro = db.Column(db.Text, nullable=True)  # Mensagem de erro (se status=ERRO)
    detalhes = db.Column(db.Text, nullable=True)  # Info adicional (ex: "42 registros sincronizados")

    def __repr__(self):
        return f"<SchedulerHealth {self.step_name} {self.status} {self.executado_em}>"

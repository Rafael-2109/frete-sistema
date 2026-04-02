"""
Modelos de Auditoria Administrativa CarVia
"""

from app import db
from app.utils.timezone import agora_utc_naive


class CarviaAdminAudit(db.Model):
    """Auditoria de acoes administrativas (hard delete, type change, re-link, field edit)"""
    __tablename__ = 'carvia_admin_audit'

    id = db.Column(db.Integer, primary_key=True)
    acao = db.Column(db.String(30), nullable=False)
    # HARD_DELETE | TYPE_CHANGE | RELINK | FIELD_EDIT | IMPORT_EDIT
    entidade_tipo = db.Column(db.String(50), nullable=False)
    entidade_id = db.Column(db.Integer, nullable=False)
    dados_snapshot = db.Column(db.JSON, nullable=False)
    dados_relacionados = db.Column(db.JSON)
    motivo = db.Column(db.Text, nullable=False)
    executado_por = db.Column(db.String(100), nullable=False)
    executado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    detalhes = db.Column(db.JSON)

    __table_args__ = (
        db.CheckConstraint(
            "acao IN ('HARD_DELETE', 'TYPE_CHANGE', 'RELINK', 'FIELD_EDIT', 'IMPORT_EDIT')",
            name='ck_carvia_audit_acao',
        ),
        db.Index('ix_carvia_audit_acao', 'acao'),
        db.Index('ix_carvia_audit_entidade', 'entidade_tipo', 'entidade_id'),
        db.Index('ix_carvia_audit_executado_em', 'executado_em'),
        db.Index('ix_carvia_audit_executado_por', 'executado_por'),
    )

    def __repr__(self):
        return (
            f'<CarviaAdminAudit {self.acao} {self.entidade_tipo}:{self.entidade_id} '
            f'por {self.executado_por}>'
        )

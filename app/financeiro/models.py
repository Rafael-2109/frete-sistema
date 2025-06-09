from app import db
from datetime import datetime

class PendenciaFinanceiraNF(db.Model):
    __tablename__ = 'pendencias_financeiras_nf'

    id = db.Column(db.Integer, primary_key=True)
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    observacao = db.Column(db.Text)
    resposta_logistica = db.Column(db.Text, nullable=True)
    respondida_em = db.Column(db.DateTime, nullable=True)
    respondida_por = db.Column(db.String(100), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100))

    # Adicione este relacionamento:
    entrega_id = db.Column(db.Integer, db.ForeignKey('entregas_monitoradas.id'), nullable=True)
    entrega = db.relationship('EntregaMonitorada', backref='pendencias_financeiras')

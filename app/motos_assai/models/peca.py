"""Catalogo de pecas + compatibilidade N:N por modelo (Spec 1 §4.1/§4.2).

Molde N:N: AssaiCompraMotochefePedido (UniqueConstraint).
"""
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.utils.timezone import agora_brasil_naive


class AssaiPeca(db.Model):
    __tablename__ = 'assai_peca'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(40), index=True)
    nome = db.Column(db.String(120), nullable=False)
    custo_referencia = db.Column(db.Numeric(15, 4))
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    criado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    dados_extras = db.Column(JSONB, default=dict)

    modelos = db.relationship('AssaiPecaModelo', backref='peca',
                              cascade='all, delete-orphan', lazy='selectin')

    def __repr__(self):
        return f'<AssaiPeca #{self.id} {self.nome}>'


class AssaiPecaModelo(db.Model):
    __tablename__ = 'assai_peca_modelo'

    id = db.Column(db.Integer, primary_key=True)
    peca_id = db.Column(db.Integer, db.ForeignKey('assai_peca.id', ondelete='CASCADE'), nullable=False)
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('peca_id', 'modelo_id', name='uq_assai_peca_modelo'),
    )

    modelo = db.relationship('AssaiModelo', lazy='joined')

    def __repr__(self):
        return f'<AssaiPecaModelo peca={self.peca_id} modelo={self.modelo_id}>'

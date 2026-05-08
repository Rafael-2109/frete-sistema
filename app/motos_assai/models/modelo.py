from app import db
from app.utils.timezone import agora_brasil_naive


# Tipos de alias permitidos
ALIAS_TIPO_NOME_LIVRE = 'NOME_LIVRE'
ALIAS_TIPO_CODIGO_QPA = 'CODIGO_QPA'
ALIAS_TIPO_DESCRICAO_RECIBO = 'DESCRICAO_RECIBO'
ALIAS_TIPOS_VALIDOS = [
    ALIAS_TIPO_NOME_LIVRE,
    ALIAS_TIPO_CODIGO_QPA,
    ALIAS_TIPO_DESCRICAO_RECIBO,
]


class AssaiModelo(db.Model):
    __tablename__ = 'assai_modelo'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), unique=True, nullable=False)
    nome = db.Column(db.String(80), nullable=False)
    descricao_qpa = db.Column(db.String(200))
    codigo_qpa = db.Column(db.String(20), index=True)
    regex_chassi = db.Column(db.String(120))
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)

    aliases = db.relationship(
        'AssaiModeloAlias',
        backref='modelo',
        cascade='all, delete-orphan',
        lazy='selectin',
    )

    def __repr__(self):
        return f'<AssaiModelo {self.codigo}>'


class AssaiModeloAlias(db.Model):
    __tablename__ = 'assai_modelo_alias'

    id = db.Column(db.Integer, primary_key=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id', ondelete='CASCADE'), nullable=False, index=True)
    alias = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('tipo', 'alias', name='uq_assai_modelo_alias_tipo_alias'),
    )

    def __repr__(self):
        return f'<AssaiModeloAlias {self.tipo}:{self.alias} -> modelo_id={self.modelo_id}>'

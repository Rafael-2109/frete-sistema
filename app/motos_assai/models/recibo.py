from app import db
from app.utils.timezone import agora_brasil_naive


RECIBO_STATUS_AGUARDANDO = 'RECEBIDO_AGUARDANDO_CONFERENCIA'
RECIBO_STATUS_EM_CONFERENCIA = 'EM_CONFERENCIA'
RECIBO_STATUS_CONCLUIDO = 'CONCLUIDO'
RECIBO_STATUS_COM_DIVERGENCIA = 'COM_DIVERGENCIA'
RECIBO_STATUS_VALIDOS = {
    RECIBO_STATUS_AGUARDANDO, RECIBO_STATUS_EM_CONFERENCIA,
    RECIBO_STATUS_CONCLUIDO, RECIBO_STATUS_COM_DIVERGENCIA,
}

DIVERGENCIA_MODELO_DIFERENTE = 'MODELO_DIFERENTE'
DIVERGENCIA_COR_DIFERENTE = 'COR_DIFERENTE'
DIVERGENCIA_CHASSI_EXTRA = 'CHASSI_EXTRA'
DIVERGENCIA_MOTO_FALTANDO = 'MOTO_FALTANDO'
DIVERGENCIA_AVARIA_FISICA = 'AVARIA_FISICA'
DIVERGENCIAS_VALIDAS = {
    DIVERGENCIA_MODELO_DIFERENTE, DIVERGENCIA_COR_DIFERENTE,
    DIVERGENCIA_CHASSI_EXTRA, DIVERGENCIA_MOTO_FALTANDO, DIVERGENCIA_AVARIA_FISICA,
}


class AssaiReciboMotochefe(db.Model):
    __tablename__ = 'assai_recibo_motochefe'

    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey('assai_compra_motochefe.id', ondelete='CASCADE'), nullable=False, index=True)
    numero_recibo = db.Column(db.String(40))
    data_recibo = db.Column(db.Date)
    equipe = db.Column(db.String(80))
    conferente_motochefe = db.Column(db.String(80))
    total_motos_declarado = db.Column(db.Integer)
    doc_s3_key = db.Column(db.String(500))
    tipo_documento = db.Column(db.String(10))
    parser_usado = db.Column(db.String(30))
    parsing_confianca = db.Column(db.Numeric(3, 2))
    status = db.Column(db.String(40), default=RECIBO_STATUS_AGUARDANDO, nullable=False)
    criado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    criado_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)

    itens = db.relationship('AssaiReciboItem', backref='recibo',
                            cascade='all, delete-orphan', lazy='selectin')
    criado_por = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return f'<AssaiReciboMotochefe {self.numero_recibo} {self.status}>'


class AssaiReciboItem(db.Model):
    __tablename__ = 'assai_recibo_item'

    id = db.Column(db.Integer, primary_key=True)
    recibo_id = db.Column(db.Integer, db.ForeignKey('assai_recibo_motochefe.id', ondelete='CASCADE'), nullable=False, index=True)
    chassi = db.Column(db.String(50), nullable=False, index=True)
    modelo_texto_recibo = db.Column(db.String(120))
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id'))
    cor_texto = db.Column(db.String(40))
    motor = db.Column(db.String(50))
    conferido = db.Column(db.Boolean, default=False, nullable=False)
    tipo_divergencia = db.Column(db.String(30))
    qr_code_lido = db.Column(db.Boolean, default=False, nullable=False)
    foto_s3_key = db.Column(db.String(500))

    modelo = db.relationship('AssaiModelo', lazy='joined')

    def __repr__(self):
        return f'<AssaiReciboItem recibo={self.recibo_id} chassi={self.chassi}>'

from app import db
from app.utils.timezone import agora_brasil_naive


NF_STATUS_BATEU = 'BATEU'
NF_STATUS_DIVERGENTE = 'DIVERGENTE'
NF_STATUS_NAO_RECONCILIADO = 'NAO_RECONCILIADO'
NF_STATUS_VALIDOS = {NF_STATUS_BATEU, NF_STATUS_DIVERGENTE, NF_STATUS_NAO_RECONCILIADO}


class AssaiNfQpa(db.Model):
    __tablename__ = 'assai_nf_qpa'

    id = db.Column(db.Integer, primary_key=True)
    separacao_id = db.Column(db.Integer, db.ForeignKey('assai_separacao.id', ondelete='SET NULL'), index=True)
    chave_44 = db.Column(db.String(44), unique=True, nullable=False)
    numero = db.Column(db.String(20))
    serie = db.Column(db.String(10))
    emitente_cnpj = db.Column(db.String(18))
    destinatario_cnpj = db.Column(db.String(18))
    destinatario_nome = db.Column(db.String(200))
    loja_id = db.Column(db.Integer, db.ForeignKey('assai_loja.id'), index=True)
    valor_total = db.Column(db.Numeric(14, 2))
    data_emissao = db.Column(db.Date)
    pdf_s3_key = db.Column(db.String(500))
    status_match = db.Column(db.String(20), default=NF_STATUS_NAO_RECONCILIADO, nullable=False)
    importada_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)
    importada_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))

    itens = db.relationship('AssaiNfQpaItem', backref='nf',
                            cascade='all, delete-orphan', lazy='selectin')
    separacao = db.relationship('AssaiSeparacao', lazy='joined')
    loja = db.relationship('AssaiLoja', lazy='joined')

    def __repr__(self):
        return f'<AssaiNfQpa {self.chave_44} {self.status_match}>'


class AssaiNfQpaItem(db.Model):
    __tablename__ = 'assai_nf_qpa_item'

    id = db.Column(db.Integer, primary_key=True)
    nf_id = db.Column(db.Integer, db.ForeignKey('assai_nf_qpa.id', ondelete='CASCADE'), nullable=False, index=True)
    chassi = db.Column(db.String(50), nullable=False, index=True)
    modelo_extraido = db.Column(db.String(120))
    valor_extraido = db.Column(db.Numeric(12, 2))
    separacao_item_id = db.Column(db.Integer, db.ForeignKey('assai_separacao_item.id', ondelete='SET NULL'))
    tipo_divergencia = db.Column(db.String(30))

    def __repr__(self):
        return f'<AssaiNfQpaItem nf={self.nf_id} chassi={self.chassi}>'

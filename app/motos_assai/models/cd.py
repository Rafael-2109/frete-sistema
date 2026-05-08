from app import db
from app.utils.timezone import agora_brasil_naive


class AssaiCd(db.Model):
    __tablename__ = 'assai_cd'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)
    cnpj = db.Column(db.String(14))
    endereco = db.Column(db.String(255))
    bairro = db.Column(db.String(80))
    cep = db.Column(db.String(10))
    cidade = db.Column(db.String(80))
    uf = db.Column(db.String(2))
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)

    def __repr__(self):
        return f'<AssaiCd {self.nome}>'

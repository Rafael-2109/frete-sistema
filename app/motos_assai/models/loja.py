from app import db
from app.utils.timezone import agora_brasil_naive


class AssaiLoja(db.Model):
    __tablename__ = 'assai_loja'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(10), unique=True, nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    razao_social = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(18), nullable=False, index=True)
    ie = db.Column(db.String(20))
    endereco = db.Column(db.String(255))
    bairro = db.Column(db.String(80))
    cep = db.Column(db.String(10))
    cidade = db.Column(db.String(80))
    uf = db.Column(db.String(2))
    regional = db.Column(db.String(80))
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)

    def __repr__(self):
        return f'<AssaiLoja {self.numero} {self.nome}>'

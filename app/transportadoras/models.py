from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Transportadora(db.Model):
    __tablename__ = 'transportadoras'

    id = db.Column(db.Integer, primary_key=True)
    cnpj = db.Column(db.String(20), nullable=False)
    razao_social = db.Column(db.String(120), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    optante = db.Column(db.Boolean, default=False)  # Sim/Não
    condicao_pgto = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f'<Transportadora {self.razao_social}>'

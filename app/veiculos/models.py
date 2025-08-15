from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class Veiculo(db.Model):
    __tablename__ = 'veiculos'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    peso_maximo = db.Column(db.Float, nullable=False)
    qtd_eixos = db.Column(db.Integer, nullable=True)  # Quantidade de eixos
    tipo_veiculo = db.Column(db.String(20), nullable=True)  # COMERCIAL ou PASSEIO
    multiplicador_pedagio = db.Column(db.Float, default=1.0)  # Multiplicador para cálculo de pedágio

    def __repr__(self):
        return f'<Veiculo {self.nome} ({self.peso_maximo} kg, {self.qtd_eixos} eixos)>'

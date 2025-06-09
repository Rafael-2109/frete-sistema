from app import db

class Cidade(db.Model):
    __tablename__ = 'cidades'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    codigo_ibge = db.Column(db.String(20), nullable=False)
    icms = db.Column(db.Float, nullable=False)
    substitui_icms_por_iss = db.Column(db.Boolean, default=False)
    microrregiao = db.Column(db.String(100))
    mesorregiao = db.Column(db.String(100))

    def __repr__(self):
        return f'<Cidade {self.nome}/{self.uf}>'

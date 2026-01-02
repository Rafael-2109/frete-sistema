from app import db
from app.utils.timezone import agora_brasil

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


class CadastroRota(db.Model):
    """
    Modelo para cadastro de rotas principais por UF
    Conforme CSV: 9- cadastro de rotas.csv
    🚚 MOVIDO de producao para localidades (faz mais sentido aqui!)
    """
    __tablename__ = 'cadastro_rota'

    id = db.Column(db.Integer, primary_key=True)
    
    # Dados da rota (conforme CSV)
    cod_uf = db.Column(db.String(2), nullable=False, unique=True, index=True)  # ESTADO
    rota = db.Column(db.String(50), nullable=False)  # ROTA
    
    # Status
    ativa = db.Column(db.Boolean, nullable=False, default=True)
    
    # Auditoria
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    def __repr__(self):
        return f'<CadastroRota {self.cod_uf} - {self.rota}>'

    def to_dict(self):
        return {
            'id': self.id,
            'cod_uf': self.cod_uf,
            'rota': self.rota,
            'ativa': self.ativa
        }


class CadastroSubRota(db.Model):
    """
    Modelo para cadastro de sub-rotas (detalhamento das rotas principais por cidade)
    Conforme CSV: 10- cadastro de sub rotas.csv  
    🚚 MOVIDO de producao para localidades (faz mais sentido aqui!)
    """
    __tablename__ = 'cadastro_sub_rota'

    id = db.Column(db.Integer, primary_key=True)
    
    # Dados específicos (conforme CSV)
    cod_uf = db.Column(db.String(2), nullable=False, index=True)  # ESTADO
    nome_cidade = db.Column(db.String(100), nullable=False, index=True)  # CIDADE
    sub_rota = db.Column(db.String(50), nullable=False)  # SUB ROTA
    
    # Status
    ativa = db.Column(db.Boolean, nullable=False, default=True)
    
    # Auditoria
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    # Índice composto
    __table_args__ = (
        db.UniqueConstraint('cod_uf', 'nome_cidade', name='uk_uf_cidade'),
        db.Index('idx_sub_rota_uf_cidade', 'cod_uf', 'nome_cidade'),
    )

    def __repr__(self):
        return f'<CadastroSubRota {self.sub_rota} - {self.nome_cidade}/{self.cod_uf}>'

    def to_dict(self):
        return {
            'id': self.id,
            'cod_uf': self.cod_uf,
            'nome_cidade': self.nome_cidade,
            'sub_rota': self.sub_rota,
            'ativa': self.ativa
        }

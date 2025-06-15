from app import db
from datetime import datetime

class RelatorioFaturamentoImportado(db.Model):
    __tablename__ = 'relatorio_faturamento_importado'

    id = db.Column(db.Integer, primary_key=True)
    numero_nf = db.Column(db.String(20), nullable=False, index=True, unique=True)
    data_fatura = db.Column(db.Date, nullable=True)
    cnpj_cliente = db.Column(db.String(20), nullable=True)
    nome_cliente = db.Column(db.String(255), nullable=True)
    valor_total = db.Column(db.Float, nullable=True)
    peso_bruto = db.Column(db.Float, nullable=True)
    cnpj_transportadora = db.Column(db.String(20), nullable=True)
    nome_transportadora = db.Column(db.String(255), nullable=True)
    municipio = db.Column(db.String(100), nullable=True)
    estado = db.Column(db.String(2), nullable=True)
    codigo_ibge = db.Column(db.String(10), nullable=True)
    origem = db.Column(db.String(50), nullable=True)
    incoterm = db.Column(db.String(20), nullable=True)
    vendedor= db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)  # 🆕 Campo para inativação
    inativado_em = db.Column(db.DateTime, nullable=True)  # 🆕 Data de inativação
    inativado_por = db.Column(db.String(100), nullable=True)  # 🆕 Quem inativou
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<NF {self.numero_nf} - {self.nome_cliente}>"


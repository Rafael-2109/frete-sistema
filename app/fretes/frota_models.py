"""
Modelos para controle de despesas da frota propria.

Tabelas:
  - frota_veiculos: cadastro de caminhoes com placa, renavam, motorista vinculado
  - frota_despesas: despesas por veiculo (combustivel, manutencao, IPVA, etc.)
"""
from app import db
from app.utils.timezone import agora_utc_naive


class FrotaVeiculo(db.Model):
    """
    Cadastro de veiculos da frota propria.

    - veiculo_tipo_id FK → veiculos.id (categoria: TOCO, CARRETA, VAN, etc.)
    - transportadora_id FK → transportadoras.id (motorista onde motorista_proprio=True)
    - km_atual atualizado automaticamente a cada despesa lancada
    """
    __tablename__ = 'frota_veiculos'

    id = db.Column(db.Integer, primary_key=True)

    # Identificacao
    placa = db.Column(db.String(10), nullable=False, unique=True)
    marca = db.Column(db.String(50), nullable=False)
    modelo = db.Column(db.String(80), nullable=False)
    renavam = db.Column(db.String(15), nullable=False, unique=True)
    proprietario = db.Column(db.String(120), nullable=False)
    ano_fabricacao = db.Column(db.SmallInteger, nullable=False)
    ano_modelo = db.Column(db.SmallInteger, nullable=False)
    cor = db.Column(db.String(30), nullable=True)
    chassi = db.Column(db.String(25), nullable=True, unique=True)

    # Tipo/categoria (FK → veiculos.id)
    veiculo_tipo_id = db.Column(
        db.Integer, db.ForeignKey('veiculos.id'), nullable=False
    )

    # Motorista vinculado (transportadora com motorista_proprio=True)
    transportadora_id = db.Column(
        db.Integer, db.ForeignKey('transportadoras.id'), nullable=True, index=True
    )

    # KM — atualizado para o maior km_no_momento das despesas
    km_atual = db.Column(db.Integer, nullable=False, default=0)

    # Depreciacao mensal (informada manualmente pelo usuario)
    depreciacao_mensal = db.Column(db.Numeric(15, 2), default=0)

    ativo = db.Column(db.Boolean, nullable=False, default=True)
    observacoes = db.Column(db.Text, nullable=True)

    # Audit
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    # Relationships
    veiculo_tipo = db.relationship('Veiculo', backref='frota_veiculos')
    transportadora = db.relationship('Transportadora', backref='frota_veiculos')
    despesas = db.relationship(
        'FrotaDespesa', backref='veiculo',
        cascade='all, delete-orphan',
        order_by='FrotaDespesa.data_despesa.desc()'
    )

    @property
    def nome_display(self):
        return f"{self.placa} — {self.marca} {self.modelo} ({self.ano_modelo})"

    def __repr__(self):
        return f'<FrotaVeiculo {self.placa} {self.marca} {self.modelo}>'


class FrotaDespesa(db.Model):
    """
    Despesa de um veiculo da frota propria.

    Categorias: COMBUSTIVEL, MANUTENCAO, PNEUS, SEGURO, IPVA,
                LICENCIAMENTO, MULTA, PEDAGIO, LAVAGEM, OUTROS

    Tipos de documento: NF, RECIBO_CUPOM, SEM_DOCUMENTO

    Ao salvar, o route handler atualiza FrotaVeiculo.km_atual
    se km_no_momento > km_atual do veiculo.
    """
    __tablename__ = 'frota_despesas'

    CATEGORIAS = [
        ('COMBUSTIVEL', 'Combustivel'),
        ('MANUTENCAO', 'Manutencao'),
        ('PNEUS', 'Pneus'),
        ('SEGURO', 'Seguro'),
        ('IPVA', 'IPVA'),
        ('LICENCIAMENTO', 'Licenciamento'),
        ('MULTA', 'Multa'),
        ('PEDAGIO', 'Pedagio'),
        ('LAVAGEM', 'Lavagem'),
        ('OUTROS', 'Outros'),
    ]

    TIPOS_DOCUMENTO = [
        ('NF', 'Nota Fiscal'),
        ('RECIBO_CUPOM', 'Recibo / Cupom Fiscal'),
        ('SEM_DOCUMENTO', 'Sem Documento'),
    ]

    id = db.Column(db.Integer, primary_key=True)

    frota_veiculo_id = db.Column(
        db.Integer, db.ForeignKey('frota_veiculos.id'), nullable=False, index=True
    )

    data_despesa = db.Column(db.Date, nullable=False)
    km_no_momento = db.Column(db.Integer, nullable=False)

    categoria = db.Column(db.String(30), nullable=False)
    tipo_documento = db.Column(db.String(20), nullable=False, default='SEM_DOCUMENTO')
    numero_documento = db.Column(db.String(60), nullable=True)

    valor = db.Column(db.Numeric(15, 2), nullable=False)
    fornecedor = db.Column(db.String(150), nullable=True)
    descricao = db.Column(db.String(255), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    # Arquivo anexo (NF, recibo, cupom) — path S3 ou local
    arquivo_path = db.Column(db.String(500), nullable=True)

    # Fase 2: integracao Odoo (colunas reservadas)
    odoo_vendor_bill_id = db.Column(db.Integer, nullable=True)
    lancado_odoo_em = db.Column(db.DateTime, nullable=True)
    lancado_odoo_por = db.Column(db.String(100), nullable=True)

    # Audit
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<FrotaDespesa {self.categoria} R${self.valor} veiculo_id={self.frota_veiculo_id}>'

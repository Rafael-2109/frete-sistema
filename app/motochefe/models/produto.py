"""
Modelos de Produto - Sistema MotoCHEFE
ModeloMoto: Catálogo de modelos
Moto: Registro único por chassi (central do sistema)
"""
from app import db
from datetime import datetime, date


class ModeloMoto(db.Model):
    """
    Catálogo de modelos de motos elétricas
    Define características comuns e preço de tabela
    """
    __tablename__ = 'modelo_moto'

    # PK
    id = db.Column(db.Integer, primary_key=True)

    # Identificação
    nome_modelo = db.Column(db.String(100), nullable=False, unique=True)
    descricao = db.Column(db.Text, nullable=True)

    # Características técnicas
    potencia_motor = db.Column(db.String(50), nullable=False)  # '1000W', '2000W', '3000W'
    autopropelido = db.Column(db.Boolean, default=False, nullable=False)

    # Comercial - PREÇO ÚNICO POR MODELO+POTÊNCIA
    preco_tabela = db.Column(db.Numeric(15, 2), nullable=False)

    # Status
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<ModeloMoto {self.nome_modelo} {self.potencia_motor}>'


class Moto(db.Model):
    """
    TABELA CENTRAL - Cada chassi é único
    Armazena dados físicos + dados de entrada (NF compra)
    """
    __tablename__ = 'moto'

    # PK
    numero_chassi = db.Column(db.String(30), primary_key=True)  # Aumentado de 17 para 30 para suportar variações de VIN

    # Identificação física
    numero_motor = db.Column(db.String(50), unique=True, nullable=True)  # Nullable mas UNIQUE quando preenchido
    modelo_id = db.Column(db.Integer, db.ForeignKey('modelo_moto.id'), nullable=False)
    cor = db.Column(db.String(50), nullable=False)
    ano_fabricacao = db.Column(db.Integer, nullable=True)

    # Dados de entrada (NF de compra do fornecedor)
    nf_entrada = db.Column(db.String(20), nullable=False)
    data_nf_entrada = db.Column(db.Date, nullable=False)
    data_entrada = db.Column(db.Date, nullable=False, default=date.today)
    fornecedor = db.Column(db.String(100), nullable=False)
    custo_aquisicao = db.Column(db.Numeric(15, 2), nullable=False)

    # Controle de pagamento do custo de aquisição
    custo_pago = db.Column(db.Numeric(15, 2), nullable=True)
    data_pagamento_custo = db.Column(db.Date, nullable=True)
    status_pagamento_custo = db.Column(db.String(20), default='PENDENTE', nullable=False, index=True)
    # Valores: PENDENTE, PAGO, PARCIAL

    # Status e controle (para FIFO e reserva)
    reservado = db.Column(db.Boolean, default=False, nullable=False, index=True)
    status = db.Column(db.String(20), default='DISPONIVEL', nullable=False, index=True)
    # Valores possíveis: DISPONIVEL, RESERVADA, VENDIDA

    # Localização física (estoque)
    pallet = db.Column(db.String(20), nullable=True)

    # Relacionamentos
    modelo = db.relationship('ModeloMoto', backref='motos')

    # Controle de motos rejeitadas (modelo não encontrado na importação)
    modelo_rejeitado = db.Column(db.String(100), nullable=True)  # Nome do modelo não encontrado (quando ativo=False)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<Moto {self.numero_chassi} - {self.status}>'

    @property
    def disponivel_para_venda(self):
        """Verifica se moto pode ser vendida"""
        return self.status == 'DISPONIVEL' and not self.reservado and self.ativo

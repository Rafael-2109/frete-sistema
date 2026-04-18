"""Cadastros do módulo HORA: loja, modelo, tabela de preço."""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraLoja(db.Model):
    """Ponto de venda físico da HORA (Tatuapé, Bragança, Praia Grande, ...)."""
    __tablename__ = 'hora_loja'

    id = db.Column(db.Integer, primary_key=True)
    cnpj = db.Column(db.String(20), nullable=False, unique=True, index=True)
    nome = db.Column(db.String(100), nullable=False)
    endereco = db.Column(db.String(255), nullable=True)
    cidade = db.Column(db.String(100), nullable=True)
    uf = db.Column(db.String(2), nullable=True)
    ativa = db.Column(db.Boolean, nullable=False, default=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    def __repr__(self):
        return f'<HoraLoja {self.nome}>'


class HoraModelo(db.Model):
    """Catálogo de modelos de moto elétrica comercializados pela HORA."""
    __tablename__ = 'hora_modelo'

    id = db.Column(db.Integer, primary_key=True)
    nome_modelo = db.Column(db.String(100), nullable=False, unique=True, index=True)
    potencia_motor = db.Column(db.String(50), nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    def __repr__(self):
        return f'<HoraModelo {self.nome_modelo}>'


class HoraTabelaPreco(db.Model):
    """Histórico de preço de tabela por modelo + período de vigência.

    Regra: `hora_venda_item.preco_tabela_referencia` deve apontar para o preço
    vigente no momento da venda. `desconto_aplicado = preco_tabela_referencia - preco_final`.
    """
    __tablename__ = 'hora_tabela_preco'

    id = db.Column(db.Integer, primary_key=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('hora_modelo.id'), nullable=False, index=True)
    preco_tabela = db.Column(db.Numeric(15, 2), nullable=False)
    vigencia_inicio = db.Column(db.Date, nullable=False)
    vigencia_fim = db.Column(db.Date, nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    modelo = db.relationship('HoraModelo', backref='tabelas_preco')

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    __table_args__ = (
        db.Index('ix_hora_tabela_preco_vigencia', 'modelo_id', 'vigencia_inicio'),
    )

    def __repr__(self):
        return f'<HoraTabelaPreco modelo={self.modelo_id} R${self.preco_tabela}>'

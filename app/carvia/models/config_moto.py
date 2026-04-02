"""
Modelos de Configuracao CarVia — Categorias/Modelos Moto, Cubagem, Config
"""

from app import db
from app.utils.timezone import agora_utc_naive


class CarviaCategoriaMoto(db.Model):
    """Categorias/tipos de moto para precificacao por unidade (ex: Leve, Pesada, Scooter)"""
    __tablename__ = 'carvia_categorias_moto'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False, unique=True)
    descricao = db.Column(db.Text)
    ordem = db.Column(db.Integer, nullable=False, default=0)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    # Relationships
    modelos = db.relationship('CarviaModeloMoto', backref='categoria', lazy='dynamic')
    precos = db.relationship('CarviaPrecoCategoriaMoto', backref='categoria', lazy='dynamic')

    def __repr__(self):
        return f'<CarviaCategoriaMoto {self.nome} ordem={self.ordem}>'


class CarviaModeloMoto(db.Model):
    """Modelos de moto para calculo automatico de peso cubado"""
    __tablename__ = 'carvia_modelos_moto'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    regex_pattern = db.Column(db.String(200), nullable=True)
    comprimento = db.Column(db.Numeric(10, 4), nullable=False)
    largura = db.Column(db.Numeric(10, 4), nullable=False)
    altura = db.Column(db.Numeric(10, 4), nullable=False)
    peso_medio = db.Column(db.Numeric(10, 3), nullable=True)
    cubagem_minima = db.Column(db.Numeric(10, 2), nullable=False, default=300)
    categoria_moto_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_categorias_moto.id'),
        nullable=True,
        index=True,
    )
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<CarviaModeloMoto {self.nome} ({self.comprimento}x{self.largura}x{self.altura})>'


class CarviaEmpresaCubagem(db.Model):
    """Empresas que utilizam cubagem para calculo de peso"""
    __tablename__ = 'carvia_empresas_cubagem'

    id = db.Column(db.Integer, primary_key=True)
    cnpj_empresa = db.Column(db.String(20), nullable=False, unique=True)
    nome_empresa = db.Column(db.String(255), nullable=False)
    considerar_cubagem = db.Column(db.Boolean, nullable=False, default=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<CarviaEmpresaCubagem {self.cnpj_empresa} cubagem={self.considerar_cubagem}>'


class CarviaPrecoCategoriaMoto(db.Model):
    """Preco fixo por unidade para combinacao tabela_frete x categoria_moto"""
    __tablename__ = 'carvia_precos_categoria_moto'

    id = db.Column(db.Integer, primary_key=True)
    tabela_frete_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_tabelas_frete.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    categoria_moto_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_categorias_moto.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    valor_unitario = db.Column(db.Numeric(15, 2), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            'tabela_frete_id', 'categoria_moto_id',
            name='uq_carvia_preco_cat_moto'
        ),
    )

    # Relationships
    tabela_frete = db.relationship('CarviaTabelaFrete', backref='precos_categoria_moto')

    def __repr__(self):
        return (
            f'<CarviaPrecoCategoriaMoto tabela={self.tabela_frete_id} '
            f'cat={self.categoria_moto_id} R${self.valor_unitario}>'
        )


class CarviaConfig(db.Model):
    """Parametros globais do modulo CarVia (chave-valor)"""
    __tablename__ = 'carvia_config'

    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), nullable=False, unique=True)
    valor = db.Column(db.Text, nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    atualizado_em = db.Column(
        db.DateTime, nullable=False,
        default=agora_utc_naive, onupdate=agora_utc_naive
    )
    atualizado_por = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<CarviaConfig {self.chave}={self.valor}>'

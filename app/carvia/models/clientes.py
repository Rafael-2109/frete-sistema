"""
Modelos de Clientes CarVia — Cadastro + Enderecos
"""

from app import db
from app.utils.timezone import agora_utc_naive


class CarviaCliente(db.Model):
    """Cliente CarVia — pessoa juridica que contrata frete"""
    __tablename__ = 'carvia_clientes'

    id = db.Column(db.Integer, primary_key=True)
    nome_comercial = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)
    atualizado_em = db.Column(
        db.DateTime, nullable=False,
        default=agora_utc_naive, onupdate=agora_utc_naive
    )

    # Relacionamentos
    enderecos = db.relationship(
        'CarviaClienteEndereco',
        backref='cliente',
        lazy='dynamic',
        cascade='all',
        foreign_keys='CarviaClienteEndereco.cliente_id',
        order_by='CarviaClienteEndereco.tipo, CarviaClienteEndereco.principal.desc()'
    )

    def __repr__(self):
        return f'<CarviaCliente {self.nome_comercial} ativo={self.ativo}>'


class CarviaClienteEndereco(db.Model):
    """Endereco CarVia — origem global (cliente_id=NULL) ou destino por cliente.

    Origens sao compartilhadas entre todos os clientes (cliente_id IS NULL).
    Destinos pertencem a um cliente especifico.
    Destinos provisorios (provisorio=True) podem ter cnpj=NULL — usado para
    cotar frete antes de ter o CNPJ definitivo.
    """
    __tablename__ = 'carvia_cliente_enderecos'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_clientes.id', ondelete='CASCADE'),
        nullable=True,  # NULL = origem global (compartilhada)
        index=True
    )
    cnpj = db.Column(db.String(20), nullable=True, index=True)  # NULL = provisorio
    razao_social = db.Column(db.String(255), nullable=True)

    # Dados da Receita Federal (readonly — preenchidos via API)
    receita_uf = db.Column(db.String(2))
    receita_cidade = db.Column(db.String(100))
    receita_logradouro = db.Column(db.String(255))
    receita_numero = db.Column(db.String(20))
    receita_bairro = db.Column(db.String(100))
    receita_cep = db.Column(db.String(10))
    receita_complemento = db.Column(db.String(255))

    # Endereco fisico (editavel — pre-preenchido da Receita, persistido)
    fisico_uf = db.Column(db.String(2))
    fisico_cidade = db.Column(db.String(100))
    fisico_logradouro = db.Column(db.String(255))
    fisico_numero = db.Column(db.String(20))
    fisico_bairro = db.Column(db.String(100))
    fisico_cep = db.Column(db.String(10))
    fisico_complemento = db.Column(db.String(255))

    # Tipo: ORIGEM ou DESTINO
    tipo = db.Column(db.String(20), nullable=False)
    principal = db.Column(db.Boolean, nullable=False, default=False)
    provisorio = db.Column(db.Boolean, nullable=False, default=False)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        # Constraints parciais gerenciadas via DDL (unique indexes parciais).
        # UniqueConstraint removida — substituida por indices parciais no SQL.
        db.CheckConstraint("tipo IN ('ORIGEM', 'DESTINO')", name='ck_carvia_endereco_tipo'),
        db.Index('ix_carvia_endereco_tipo', 'tipo'),
    )

    def __repr__(self):
        origem = 'GLOBAL' if not self.cliente_id else f'cliente={self.cliente_id}'
        doc = self.cnpj or 'SEM-CNPJ'
        return f'<CarviaClienteEndereco {doc} {self.tipo} {origem}>'

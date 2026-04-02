"""
Modelos de Tabelas de Frete e Grupos de Cliente CarVia
"""

from app import db
from app.utils.timezone import agora_utc_naive


class CarviaGrupoCliente(db.Model):
    """Grupo de clientes para tabelas de preco diferenciadas"""
    __tablename__ = 'carvia_grupos_cliente'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False, unique=True)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    # Relacionamentos
    membros = db.relationship(
        'CarviaGrupoClienteMembro',
        backref='grupo',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    tabelas = db.relationship(
        'CarviaTabelaFrete',
        backref='grupo_cliente',
        lazy='dynamic',
    )

    def __repr__(self):
        return f'<CarviaGrupoCliente {self.nome} ativo={self.ativo}>'


class CarviaGrupoClienteMembro(db.Model):
    """Membro (CNPJ) de um grupo de clientes"""
    __tablename__ = 'carvia_grupo_cliente_membros'

    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_grupos_cliente.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    cnpj = db.Column(db.String(20), nullable=False, index=True)
    nome_empresa = db.Column(db.String(255), nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('grupo_id', 'cnpj', name='uq_carvia_grupo_membro'),
    )

    def __repr__(self):
        return f'<CarviaGrupoClienteMembro {self.cnpj} grupo={self.grupo_id}>'


class CarviaTabelaFrete(db.Model):
    """Tabela de frete CarVia (preco de VENDA) — sem transportadora"""
    __tablename__ = 'carvia_tabelas_frete'

    id = db.Column(db.Integer, primary_key=True)
    uf_origem = db.Column(db.String(2), nullable=False)
    uf_destino = db.Column(db.String(2), nullable=False)
    nome_tabela = db.Column(db.String(50), nullable=False)
    tipo_carga = db.Column(db.String(20), nullable=False)  # DIRETA / FRACIONADA
    modalidade = db.Column(db.String(50), nullable=False)

    # Grupo de cliente (NULL = standard)
    grupo_cliente_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_grupos_cliente.id'),
        nullable=True,
        index=True
    )

    # Campos de preco — identicos a TabelaFrete para compatibilidade
    # com TabelaFreteManager.preparar_dados_tabela()
    valor_kg = db.Column(db.Float, nullable=True)
    frete_minimo_peso = db.Column(db.Float, nullable=True)
    percentual_valor = db.Column(db.Float, nullable=True)
    frete_minimo_valor = db.Column(db.Float, nullable=True)
    percentual_gris = db.Column(db.Float, nullable=True)
    percentual_adv = db.Column(db.Float, nullable=True)
    percentual_rca = db.Column(db.Float, nullable=True)
    pedagio_por_100kg = db.Column(db.Float, nullable=True)
    valor_despacho = db.Column(db.Float, nullable=True)
    valor_cte = db.Column(db.Float, nullable=True)
    valor_tas = db.Column(db.Float, nullable=True)
    icms_incluso = db.Column(db.Boolean, nullable=False, default=False)
    gris_minimo = db.Column(db.Float, nullable=True, default=0)
    adv_minimo = db.Column(db.Float, nullable=True, default=0)
    icms_proprio = db.Column(db.Float, nullable=True)

    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        db.Index('ix_carvia_tf_uf', 'uf_origem', 'uf_destino'),
        db.Index('ix_carvia_tf_tipo_carga', 'tipo_carga'),
        db.CheckConstraint(
            "tipo_carga IN ('DIRETA', 'FRACIONADA')",
            name='ck_carvia_tf_tipo_carga'
        ),
    )

    def __repr__(self):
        return (
            f'<CarviaTabelaFrete {self.nome_tabela} '
            f'{self.uf_origem}->{self.uf_destino} {self.tipo_carga}>'
        )


class CarviaCidadeAtendida(db.Model):
    """Cidades atendidas pelo frete CarVia — vincula a CarviaTabelaFrete via nome_tabela"""
    __tablename__ = 'carvia_cidades_atendidas'

    id = db.Column(db.Integer, primary_key=True)
    codigo_ibge = db.Column(db.String(10), nullable=False)
    nome_cidade = db.Column(db.String(100), nullable=False)
    uf_origem = db.Column(db.String(2), nullable=False)
    uf_destino = db.Column(db.String(2), nullable=False)
    nome_tabela = db.Column(db.String(50), nullable=False)
    lead_time = db.Column(db.Integer, nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('codigo_ibge', 'nome_tabela', 'uf_origem',
                            name='uq_carvia_cidade_tabela_origem'),
        db.Index('ix_carvia_cidade_ibge', 'codigo_ibge'),
        db.Index('ix_carvia_cidade_uf_destino', 'uf_destino'),
        db.Index('ix_carvia_cidade_uf_origem', 'uf_origem'),
    )

    def __repr__(self):
        return f'<CarviaCidadeAtendida {self.nome_cidade}/{self.uf_destino} tab={self.nome_tabela}>'

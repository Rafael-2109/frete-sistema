"""Cadastros do módulo HORA: loja, modelo, tabela de preço."""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraLoja(db.Model):
    """Ponto de venda físico da HORA (Tatuapé, Bragança, Praia Grande, ...).

    Dados fiscais (razão social, endereço, CEP, situação...) são autopreenchidos
    via ReceitaWS. Campo `apelido` é rótulo interno amigável ("Motochefe Bragança")
    mostrado em listagens/UI.
    """
    __tablename__ = 'hora_loja'

    id = db.Column(db.Integer, primary_key=True)
    cnpj = db.Column(db.String(20), nullable=False, unique=True, index=True)

    # Rótulo interno (UI-friendly). Preferir este sobre razao_social em listagens.
    apelido = db.Column(db.String(100), nullable=True, index=True)

    # Legacy: nome_razao antigo. Mantido para compat; razao_social é o canônico.
    nome = db.Column(db.String(100), nullable=False)

    # Dados da Receita (autopreenchidos via ReceitaWS)
    razao_social = db.Column(db.String(200), nullable=True)
    nome_fantasia = db.Column(db.String(200), nullable=True)
    inscricao_estadual = db.Column(db.String(30), nullable=True)
    situacao_cadastral = db.Column(db.String(30), nullable=True)
    data_abertura = db.Column(db.Date, nullable=True)
    porte = db.Column(db.String(50), nullable=True)
    natureza_juridica = db.Column(db.String(255), nullable=True)
    atividade_principal = db.Column(db.String(500), nullable=True)

    # Endereço (Receita)
    logradouro = db.Column(db.String(255), nullable=True)
    numero = db.Column(db.String(20), nullable=True)
    complemento = db.Column(db.String(100), nullable=True)
    bairro = db.Column(db.String(100), nullable=True)
    cep = db.Column(db.String(9), nullable=True)
    cidade = db.Column(db.String(100), nullable=True)
    uf = db.Column(db.String(2), nullable=True)

    # Contato (Receita)
    telefone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(120), nullable=True)

    # Compat: campo livre antigo (quando não há Receita disponível).
    endereco = db.Column(db.String(255), nullable=True)

    ativa = db.Column(db.Boolean, nullable=False, default=True)
    receitaws_consultado_em = db.Column(db.DateTime, nullable=True)

    # Coordenadas para renderizar em mapa (cache de geocoding)
    latitude = db.Column(db.Numeric(10, 7), nullable=True)
    longitude = db.Column(db.Numeric(10, 7), nullable=True)
    geocodado_em = db.Column(db.DateTime, nullable=True)
    geocoding_provider = db.Column(db.String(20), nullable=True)
    # Valores: google, nominatim, manual

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    @property
    def rotulo_display(self) -> str:
        """Preferência de exibição: apelido > nome_fantasia > razão social > nome."""
        return (
            self.apelido
            or self.nome_fantasia
            or self.razao_social
            or self.nome
            or f'CNPJ {self.cnpj}'
        )

    def __repr__(self):
        return f'<HoraLoja {self.rotulo_display}>'


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

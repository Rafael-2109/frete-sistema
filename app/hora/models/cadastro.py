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

    # Grupo WhatsApp de notificação (1 grupo por loja): JID Baileys "...@g.us".
    # Destino das notificações de pedido confirmado / NF emitida DESTA loja.
    # Configurado na tela da loja (dropdown ao vivo dos grupos da Evolution).
    whatsapp_grupo_jid = db.Column(db.String(60), nullable=True)

    ativa = db.Column(db.Boolean, nullable=False, default=True)

    # MATRIZ (emitente fiscal) vs loja de VENDA. Toda NFe da HORA sai com o CNPJ
    # da matriz (invariante fiscal — CLAUDE.md secao 7), mas a matriz NAO vende.
    # `is_matriz=True` marca essa pseudo-loja: ela permanece `ativa` (e usada como
    # default de NF de ENTRADA e como alvo do resolver de divergencia), mas e
    # EXCLUIDA das superficies de VENDA (rankings, escopos, dropdowns, contagens)
    # e NUNCA pode ser gravada como loja_id de uma venda. Migration hora_57.
    is_matriz = db.Column(
        db.Boolean, nullable=False, default=False, server_default='false',
    )
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
    """Catálogo de modelos de moto elétrica comercializados pela HORA.

    Unificacao N->1 (migration hora_29):
      Quando um modelo e absorvido em outro (merge), o registro permanece
      na tabela mas ativo=False + merged_em_id aponta para o canonico.
      Permite auditoria — ninguem perde rastreio de "este chassi foi
      cadastrado originalmente como BOB AM, depois unificado em BOB".

      `aliases` (backref de HoraModeloAlias) lista os N nomes que
      apontam para este modelo. Resolver de ingestao consulta primeiro
      essa tabela antes de criar pendencia.
    """
    __tablename__ = 'hora_modelo'

    id = db.Column(db.Integer, primary_key=True)
    nome_modelo = db.Column(db.String(100), nullable=False, unique=True, index=True)
    potencia_motor = db.Column(db.String(50), nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    # Preços de tabela por modalidade (migration hora_33). NULL = nao cadastrado.
    # Quando preenchidos, sao a fonte primaria de preço usada no Pedido de Venda
    # (HoraTabelaPreco com vigencia continua sendo fallback legado).
    preco_a_vista = db.Column(db.Numeric(15, 2), nullable=True)
    preco_a_prazo = db.Column(db.Numeric(15, 2), nullable=True)
    # Teto de desconto (R$) por moto deste modelo (roadmap #28; migration hora_49).
    # NULL = sem teto. Desconto acima exige aprovacao (Fatia 2).
    desconto_maximo = db.Column(db.Numeric(15, 2), nullable=True)

    # Classificacao fiscal/regulatoria (migration hora_41). Controla os
    # textos exibidos em `inf_contribuinte` na NF-e:
    #   True  -> "Autopropelido" / bicicleta eletrica (Res. CONTRAN 996/2023)
    #            dispensa CNH e licenciamento; garantia 6m + 6m motor/bateria.
    #   False -> "Ciclomotor" — exige CNH e emplacamento; garantia 3m + 9m
    #            motor/bateria; ATPV emitido em ate 15 dias uteis.
    # Default True (HORA comercializa predominantemente bicicletas eletricas);
    # operador ajusta caso a caso pelos formularios de modelo.
    autopropelido = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.text('true'),
    )

    # Auditoria de merge (migration hora_29). Quando este modelo e
    # absorvido em outro, ativo=False + merged_em_id=canonico.id.
    merged_em_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_modelo.id'),
        nullable=True,
        index=True,
    )
    merged_em = db.Column(db.DateTime, nullable=True)
    merged_por = db.Column(db.String(100), nullable=True)

    canonico = db.relationship(
        'HoraModelo',
        remote_side=[id],
        foreign_keys=[merged_em_id],
        backref='absorvidos',
    )

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    @property
    def foi_unificado(self) -> bool:
        """True se este modelo foi absorvido em outro (canonico)."""
        return self.merged_em_id is not None

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

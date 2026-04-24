"""Fluxo de saída: venda ao consumidor final (pessoa física)."""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraVenda(db.Model):
    """Venda ao consumidor final. Header permite multi-item (casal, presente, revenda).

    Pode ser criada via:
      - Upload de DANFE de saida (fluxo `importar_nf_saida_pdf`): parser
        extrai CPF/nome destinatario + valor_total + chassis. Chassis que nao
        estao em estoque geram `HoraVendaDivergencia` em vez de bloquear.
      - Fluxo futuro (TagPlus): operador cria venda primeiro e NF depois.
    """
    __tablename__ = 'hora_venda'

    id = db.Column(db.Integer, primary_key=True)
    loja_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_loja.id'),
        nullable=True,  # NULL quando CNPJ emitente nao bate com HoraLoja cadastrada.
        index=True,
    )

    # Consumidor final: sempre pessoa física.
    cpf_cliente = db.Column(db.String(14), nullable=False, index=True)
    nome_cliente = db.Column(db.String(200), nullable=False)
    telefone_cliente = db.Column(db.String(20), nullable=True)
    email_cliente = db.Column(db.String(120), nullable=True)

    data_venda = db.Column(db.Date, nullable=False, default=agora_utc_naive, index=True)
    forma_pagamento = db.Column(
        db.String(20), nullable=False, default='NAO_INFORMADO',
    )
    # Valores: PIX, CARTAO_CREDITO, DINHEIRO, MISTO, NAO_INFORMADO.
    # Default cobre import via DANFE (parser nao extrai <pag><detPag>); operador
    # edita manualmente pos-import na tela de detalhe.

    valor_total = db.Column(db.Numeric(15, 2), nullable=False)
    # Soma de hora_venda_item.preco_final (validado em serviço).

    nf_saida_numero = db.Column(db.String(20), nullable=True, index=True)
    nf_saida_chave_44 = db.Column(db.String(44), nullable=True, unique=True)
    nf_saida_emitida_em = db.Column(db.DateTime, nullable=True)

    # Auditoria do import (paralela a HoraNfEntrada).
    arquivo_pdf_s3_key = db.Column(db.String(500), nullable=True)
    parser_usado = db.Column(db.String(50), nullable=True)
    # Ex.: 'danfe_pdf_parser_v1'.
    parseada_em = db.Column(db.DateTime, nullable=True)

    cnpj_emitente = db.Column(db.String(20), nullable=True, index=True)
    # CNPJ impresso na NF (para corrigir loja_id quando o import falha em casar).

    status = db.Column(db.String(20), nullable=False, default='CONCLUIDA', index=True)
    # Valores: CONCLUIDA, CANCELADA, DEVOLVIDA

    vendedor = db.Column(db.String(100), nullable=True)
    # Preenchido manualmente na tela de detalhe pos-import.
    observacoes = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    loja = db.relationship('HoraLoja', backref='vendas')
    itens = db.relationship(
        'HoraVendaItem',
        backref='venda',
        cascade='all, delete-orphan',
    )
    divergencias = db.relationship(
        'HoraVendaDivergencia',
        backref='venda',
        cascade='all, delete-orphan',
        order_by='HoraVendaDivergencia.criado_em.desc()',
    )

    @property
    def divergencias_abertas(self):
        return [d for d in self.divergencias if d.resolvida_em is None]

    @property
    def tem_divergencia_aberta(self) -> bool:
        return any(d.resolvida_em is None for d in self.divergencias)

    def __repr__(self):
        return f'<HoraVenda {self.id} loja={self.loja_id} R${self.valor_total}>'


class HoraVendaItem(db.Model):
    """Linha de venda: um chassi vendido.

    Preserva a trilha de preço: preco_tabela_referencia (vigente) ← desconto_aplicado
    ← preco_final. Permite auditoria "por que vendeu R$X abaixo da tabela?".
    """
    __tablename__ = 'hora_venda_item'

    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_venda.id'),
        nullable=False,
        index=True,
    )
    numero_chassi = db.Column(
        db.String(30),
        db.ForeignKey('hora_moto.numero_chassi'),
        nullable=False,
        unique=True,
        index=True,
    )
    # UNIQUE: impede vender o mesmo chassi duas vezes.

    tabela_preco_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_tabela_preco.id'),
        nullable=True,
    )
    # Referência à linha de preço vigente usada (auditoria).

    preco_tabela_referencia = db.Column(db.Numeric(15, 2), nullable=False)
    desconto_aplicado = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    preco_final = db.Column(db.Numeric(15, 2), nullable=False)
    # Invariante: preco_final = preco_tabela_referencia - desconto_aplicado.

    moto = db.relationship('HoraMoto', backref='venda_item')
    tabela_preco = db.relationship('HoraTabelaPreco')

    def __repr__(self):
        return (
            f'<HoraVendaItem venda={self.venda_id} chassi={self.numero_chassi} '
            f'final=R${self.preco_final}>'
        )


class HoraVendaDivergencia(db.Model):
    """Divergencia derivada no import da NF de saida.

    Fluxo permissivo: o import NAO rejeita problemas; registra divergencia aqui
    e segue. Operador revisa na tela de detalhe e marca como resolvida apos
    tomar acao (ex.: corrigir loja, cancelar venda, aceitar como esta).

    Tipos:
      CHASSI_NAO_CADASTRADO  — chassi da NF nunca entrou na HORA (get_or_create_moto criou)
      CHASSI_INDISPONIVEL    — ultimo evento do chassi NAO em EVENTOS_EM_ESTOQUE
      LOJA_DIVERGENTE        — chassi esta em loja diferente da emitente da NF
      CNPJ_DESCONHECIDO      — emitente nao bate com HoraLoja ativa (venda com loja_id=NULL)
      TABELA_PRECO_AUSENTE   — sem HoraTabelaPreco vigente na data; preco_tabela_ref = preco_final
    """
    __tablename__ = 'hora_venda_divergencia'

    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_venda.id'),
        nullable=False,
        index=True,
    )
    numero_chassi = db.Column(
        db.String(30),
        db.ForeignKey('hora_moto.numero_chassi'),
        nullable=True,  # NULL para CNPJ_DESCONHECIDO (nao tem chassi).
        index=True,
    )
    tipo = db.Column(db.String(30), nullable=False, index=True)
    detalhe = db.Column(db.Text, nullable=True)
    valor_esperado = db.Column(db.String(200), nullable=True)
    valor_conferido = db.Column(db.String(200), nullable=True)

    resolvida_em = db.Column(db.DateTime, nullable=True)
    resolvida_por = db.Column(db.String(100), nullable=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    moto = db.relationship('HoraMoto', backref='venda_divergencias')

    __table_args__ = (
        db.UniqueConstraint(
            'venda_id', 'tipo', 'numero_chassi',
            name='uq_hora_venda_divergencia_tipo_chassi',
        ),
    )

    @property
    def aberta(self) -> bool:
        return self.resolvida_em is None

    def __repr__(self):
        estado = 'aberta' if self.aberta else 'resolvida'
        return (
            f'<HoraVendaDivergencia venda={self.venda_id} tipo={self.tipo} '
            f'chassi={self.numero_chassi} {estado}>'
        )

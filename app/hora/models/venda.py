"""Fluxo de saída: venda ao consumidor final (pessoa física)."""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraVenda(db.Model):
    """Venda ao consumidor final. Header permite multi-item (casal, presente, revenda)."""
    __tablename__ = 'hora_venda'

    id = db.Column(db.Integer, primary_key=True)
    loja_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_loja.id'),
        nullable=False,
        index=True,
    )

    # Consumidor final: sempre pessoa física.
    cpf_cliente = db.Column(db.String(14), nullable=False, index=True)
    nome_cliente = db.Column(db.String(200), nullable=False)
    telefone_cliente = db.Column(db.String(20), nullable=True)
    email_cliente = db.Column(db.String(120), nullable=True)

    data_venda = db.Column(db.Date, nullable=False, default=agora_utc_naive, index=True)
    forma_pagamento = db.Column(db.String(20), nullable=False)
    # Valores: PIX, CARTAO_CREDITO, DINHEIRO, MISTO

    valor_total = db.Column(db.Numeric(15, 2), nullable=False)
    # Soma de hora_venda_item.preco_final (validado em serviço).

    nf_saida_numero = db.Column(db.String(20), nullable=True, index=True)
    nf_saida_chave_44 = db.Column(db.String(44), nullable=True, unique=True)
    nf_saida_emitida_em = db.Column(db.DateTime, nullable=True)

    status = db.Column(db.String(20), nullable=False, default='CONCLUIDA', index=True)
    # Valores: CONCLUIDA, CANCELADA, DEVOLVIDA

    vendedor = db.Column(db.String(100), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    loja = db.relationship('HoraLoja', backref='vendas')
    itens = db.relationship(
        'HoraVendaItem',
        backref='venda',
        cascade='all, delete-orphan',
    )

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

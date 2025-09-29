"""
Modelos para integração TagPlus
"""

from datetime import datetime
from app import db


class NFPendenteTagPlus(db.Model):
    """
    Tabela para armazenar itens de NFs do TagPlus pendentes de importação
    por falta de número de pedido (campo origem)
    """
    __tablename__ = 'nf_pendente_tagplus'

    id = db.Column(db.Integer, primary_key=True)

    # Dados da NF - espelhando FaturamentoProduto
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    cnpj_cliente = db.Column(db.String(20), nullable=False, index=True)
    nome_cliente = db.Column(db.String(255), nullable=False)
    nome_cidade = db.Column(db.String(120), nullable=True)
    cod_uf = db.Column(db.String(5), nullable=True)
    data_fatura = db.Column(db.Date, nullable=False)

    # Dados do Produto
    cod_produto = db.Column(db.String(50), nullable=False)
    nome_produto = db.Column(db.String(200), nullable=False)
    qtd_produto_faturado = db.Column(db.Numeric(15, 3), nullable=False)
    preco_produto_faturado = db.Column(db.Numeric(15, 4), nullable=False)
    valor_produto_faturado = db.Column(db.Numeric(15, 2), nullable=False)

    # Campo a ser preenchido pelo usuário
    origem = db.Column(db.String(50), nullable=True, index=True)  # Número do pedido

    # Status do fluxo
    resolvido = db.Column(db.Boolean, default=False, index=True)
    importado = db.Column(db.Boolean, default=False, index=True)

    # Auditoria básica
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    pedido_preenchido_em = db.Column(db.DateTime, nullable=True)
    pedido_preenchido_por = db.Column(db.String(100), nullable=True)
    resolvido_em = db.Column(db.DateTime, nullable=True)
    resolvido_por = db.Column(db.String(100), nullable=True)
    importado_em = db.Column(db.DateTime, nullable=True)

    # Índice composto para evitar duplicação
    __table_args__ = (
        db.UniqueConstraint('numero_nf', 'cod_produto', name='uq_nf_produto'),
        db.Index('idx_nf_pendente_resolvido', 'resolvido', 'importado'),
    )

    def __repr__(self):
        return f'<NFPendenteTagPlus {self.numero_nf}/{self.cod_produto}>'

"""
Modelos de Comissao CarVia — Fechamento de comissao por periodo + junction CTes
"""

from sqlalchemy import func

from app import db
from app.utils.timezone import agora_utc_naive


class CarviaComissaoFechamento(db.Model):
    """Fechamento de comissao por periodo — agrupa N CTes CarVia"""
    __tablename__ = 'carvia_comissao_fechamentos'

    __table_args__ = (
        db.CheckConstraint('data_inicio <= data_fim', name='ck_comissao_periodo_valido'),
        db.CheckConstraint('percentual > 0 AND percentual <= 1', name='ck_comissao_percentual_range'),
        db.CheckConstraint(
            "status IN ('PENDENTE', 'PAGO', 'CANCELADO')",
            name='ck_comissao_status_valido',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    numero_fechamento = db.Column(db.String(20), unique=True, nullable=False)

    # Vendedor beneficiario
    vendedor_nome = db.Column(db.String(100), nullable=False)
    vendedor_email = db.Column(db.String(150))

    # Periodo de fechamento (por cte_data_emissao)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)

    # Percentual aplicado (snapshot no momento da criacao, ex: 0.05 = 5%)
    percentual = db.Column(db.Numeric(10, 8), nullable=False)

    # Totais denormalizados (recalculados ao incluir/excluir CTe)
    qtd_ctes = db.Column(db.Integer, nullable=False, default=0)
    total_bruto = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    total_comissao = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    # Soma dos deltas de ajustes APLICADOS a este fechamento (transparencia)
    total_ajustes = db.Column(db.Numeric(15, 2), nullable=False, default=0)

    # Vendedor beneficiario (FK canonica — vendedor_nome/email = snapshot exibicao)
    vendedor_usuario_id = db.Column(
        db.Integer, db.ForeignKey('usuarios.id'), nullable=True, index=True,
    )

    # Status: PENDENTE -> PAGO | CANCELADO
    status = db.Column(db.String(20), nullable=False, default='PENDENTE', index=True)

    # Auditoria de pagamento
    pago_por = db.Column(db.String(100))
    pago_em = db.Column(db.DateTime)
    data_pagamento = db.Column(db.Date)

    observacoes = db.Column(db.Text)

    # Despesa vinculada (gerada automaticamente na criacao)
    despesa_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_despesas.id', ondelete='SET NULL'),
        nullable=True,
        unique=True,
        index=True,
    )

    # Auditoria
    criado_por = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    # Relacionamentos
    despesa = db.relationship('CarviaDespesa', foreign_keys=[despesa_id], lazy='joined')
    ctes = db.relationship(
        'CarviaComissaoFechamentoCte',
        backref='fechamento',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )

    @staticmethod
    def gerar_numero_fechamento():
        """Gera proximo numero sequencial COM-###."""
        max_num = db.session.query(
            func.max(CarviaComissaoFechamento.numero_fechamento)
        ).filter(
            CarviaComissaoFechamento.numero_fechamento.ilike('COM-%'),
        ).scalar()

        next_num = 1
        if max_num:
            try:
                next_num = int(max_num.replace('COM-', '')) + 1
            except (ValueError, TypeError):
                pass
        return f'COM-{next_num:03d}'

    def recalcular_totais(self):
        """Recalcula totais a partir dos CTes ativos (nao excluidos).

        Atualiza qtd_ctes, total_bruto e total_comissao in-memory.
        Caller deve fazer db.session.commit().
        """
        from decimal import Decimal
        ctes_ativos = CarviaComissaoFechamentoCte.query.filter_by(
            fechamento_id=self.id,
            excluido=False,
        ).all()

        self.qtd_ctes = len(ctes_ativos)
        self.total_bruto = sum(
            (c.valor_cte_snapshot or Decimal('0')) for c in ctes_ativos
        )
        comissao_ctes = sum(
            (c.valor_comissao or Decimal('0')) for c in ctes_ativos
        )

        # Ajustes (debito/credito) APLICADOS a este fechamento — fonte de verdade
        ajustes_aplicados = CarviaComissaoAjuste.query.filter_by(
            fechamento_aplicado_id=self.id,
            status='APLICADO',
        ).all()
        self.total_ajustes = sum(
            (a.delta_comissao or Decimal('0')) for a in ajustes_aplicados
        )
        self.total_comissao = comissao_ctes + self.total_ajustes

    def __repr__(self):
        return f'<CarviaComissaoFechamento {self.numero_fechamento} ({self.status})>'


class CarviaComissaoFechamentoCte(db.Model):
    """Junction entre fechamento e CTes CarVia — com snapshots de valor"""
    __tablename__ = 'carvia_comissao_fechamento_ctes'

    __table_args__ = (
        db.UniqueConstraint(
            'fechamento_id', 'operacao_id',
            name='uq_comissao_fechamento_operacao',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    fechamento_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_comissao_fechamentos.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    operacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_operacoes.id'),
        nullable=False,
        index=True,
    )

    # Snapshots no momento da inclusao
    cte_numero = db.Column(db.String(20), nullable=False)
    cte_data_emissao = db.Column(db.Date, nullable=False)
    valor_cte_snapshot = db.Column(db.Numeric(15, 2), nullable=False)
    percentual_snapshot = db.Column(db.Numeric(10, 8), nullable=False)
    valor_comissao = db.Column(db.Numeric(15, 2), nullable=False)

    # Soft-exclusao (manter auditoria)
    excluido = db.Column(db.Boolean, nullable=False, default=False)
    excluido_em = db.Column(db.DateTime)
    excluido_por = db.Column(db.String(100))

    # Auditoria de inclusao
    incluido_por = db.Column(db.String(100), nullable=False)
    incluido_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    # Relacionamentos
    operacao = db.relationship('CarviaOperacao', lazy='joined')

    def __repr__(self):
        return (
            f'<CarviaComissaoFechamentoCte fech={self.fechamento_id} '
            f'op={self.operacao_id} excl={self.excluido}>'
        )


class CarviaComissaoAjuste(db.Model):
    """Ajuste (debito/credito) de comissao gerado quando o cte_valor de um CTe
    ja comissionado muda, ou quando o CTe/operacao e cancelado. Abatido no
    proximo fechamento do mesmo vendedor. NAO altera o fechamento de origem.

    delta_comissao > 0 = credito (a pagar a mais); < 0 = debito (a descontar).
    """
    __tablename__ = 'carvia_comissao_ajustes'

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('PENDENTE','APLICADO','CANCELADO')",
            name='ck_comissao_ajuste_status',
        ),
        db.CheckConstraint(
            "motivo IN ('ALTERACAO_VALOR','CANCELAMENTO_CTE')",
            name='ck_comissao_ajuste_motivo',
        ),
        db.Index('ix_comissao_ajuste_vend_status', 'vendedor_usuario_id', 'status'),
    )

    id = db.Column(db.Integer, primary_key=True)
    operacao_id = db.Column(
        db.Integer, db.ForeignKey('carvia_operacoes.id'), nullable=False, index=True,
    )
    fechamento_origem_id = db.Column(
        db.Integer, db.ForeignKey('carvia_comissao_fechamentos.id'),
        nullable=False, index=True,
    )
    vendedor_usuario_id = db.Column(
        db.Integer, db.ForeignKey('usuarios.id'), nullable=True, index=True,
    )
    vendedor_nome = db.Column(db.String(100), nullable=False)
    vendedor_email = db.Column(db.String(150))

    # ALTERACAO_VALOR | CANCELAMENTO_CTE
    motivo = db.Column(db.String(20), nullable=False)
    cte_numero = db.Column(db.String(20), nullable=False)
    valor_cte_anterior = db.Column(db.Numeric(15, 2), nullable=False)
    valor_cte_novo = db.Column(db.Numeric(15, 2), nullable=False)
    percentual_snapshot = db.Column(db.Numeric(10, 8), nullable=False)
    # >0 credito, <0 debito
    delta_comissao = db.Column(db.Numeric(15, 2), nullable=False)

    status = db.Column(db.String(20), nullable=False, default='PENDENTE', index=True)
    fechamento_aplicado_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_comissao_fechamentos.id', ondelete='SET NULL'),
        nullable=True,
    )

    criado_por = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    aplicado_em = db.Column(db.DateTime)
    observacoes = db.Column(db.Text)

    operacao = db.relationship(
        'CarviaOperacao', lazy='joined', foreign_keys=[operacao_id],
    )

    def __repr__(self):
        return (
            f'<CarviaComissaoAjuste op={self.operacao_id} '
            f'delta={self.delta_comissao} {self.status}>'
        )

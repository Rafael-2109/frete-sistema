from app import db
from app.utils.timezone import agora_brasil_naive


SEPARACAO_STATUS_EM_SEPARACAO = 'EM_SEPARACAO'
SEPARACAO_STATUS_FECHADA = 'FECHADA'
SEPARACAO_STATUS_FATURADA = 'FATURADA'
SEPARACAO_STATUS_CANCELADA = 'CANCELADA'
SEPARACAO_STATUS_VALIDOS = {
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_FATURADA, SEPARACAO_STATUS_CANCELADA,
}


class AssaiSeparacao(db.Model):
    __tablename__ = 'assai_separacao'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('assai_pedido_venda.id'), nullable=False, index=True)
    loja_id = db.Column(db.Integer, db.ForeignKey('assai_loja.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default=SEPARACAO_STATUS_EM_SEPARACAO, nullable=False)
    iniciada_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)
    fechada_em = db.Column(db.DateTime)
    fechada_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    solicitacao_excel_s3_key = db.Column(db.String(500))
    motivo_cancelamento = db.Column(db.Text)

    # 4 campos override (Migration 11, 2026-05-12).
    # NULL = herda do AssaiPedidoVendaLoja correspondente via (pedido_id, loja_id).
    expedicao = db.Column(db.Date)
    agendamento = db.Column(db.Date)
    protocolo = db.Column(db.String(50))
    # server_default='false': garante DEFAULT FALSE no DB quando tabela criada
    # via db.create_all() (sem migration). Previne NotNullViolation em backfill.
    agendamento_confirmado = db.Column(
        db.Boolean, default=False, server_default='false', nullable=False,
    )

    itens = db.relationship('AssaiSeparacaoItem', backref='separacao',
                            cascade='all, delete-orphan', lazy='selectin')
    saldos_modelo = db.relationship('AssaiSeparacaoSaldoModelo', backref='separacao',
                                    cascade='all, delete-orphan', lazy='selectin')
    pedido = db.relationship('AssaiPedidoVenda', lazy='joined')
    loja = db.relationship('AssaiLoja', lazy='joined')
    fechada_por = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return f'<AssaiSeparacao pedido={self.pedido_id} loja={self.loja_id} {self.status}>'


class AssaiSeparacaoItem(db.Model):
    __tablename__ = 'assai_separacao_item'

    id = db.Column(db.Integer, primary_key=True)
    separacao_id = db.Column(db.Integer, db.ForeignKey('assai_separacao.id', ondelete='CASCADE'), nullable=False, index=True)
    chassi = db.Column(db.String(50), nullable=False, index=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id'), nullable=False)
    valor_unitario_qpa = db.Column(db.Numeric(12, 2), nullable=False)
    registrada_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)
    registrada_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))

    modelo = db.relationship('AssaiModelo', lazy='joined')
    registrada_por = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return f'<AssaiSeparacaoItem separacao={self.separacao_id} chassi={self.chassi}>'


class AssaiSeparacaoSaldoModelo(db.Model):
    """Placeholder de qtd planejada por modelo na separacao.

    Criado quando operador clica "Criar separacao" via checkbox+qtd na UI.
    Apenas referencia — escaneio livre nao e bloqueado pela qtd_planejada
    (decidido 2026-05-12: realidade prevalece — chassi efetivamente separado
    pode divergir do plano por variacoes de carregamento).

    Migration 12 (2026-05-12).
    """
    __tablename__ = 'assai_separacao_saldo_modelo'

    id = db.Column(db.Integer, primary_key=True)
    separacao_id = db.Column(db.Integer,
                             db.ForeignKey('assai_separacao.id', ondelete='CASCADE'),
                             nullable=False, index=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id'), nullable=False)
    qtd_planejada = db.Column(db.Integer, nullable=False)
    # server_default: garante DEFAULT no DB quando tabela criada via create_all
    criado_em = db.Column(
        db.DateTime, default=agora_brasil_naive,
        server_default=db.text("(NOW() AT TIME ZONE 'America/Sao_Paulo')"),
        nullable=False,
    )

    __table_args__ = (
        db.UniqueConstraint('separacao_id', 'modelo_id',
                            name='uq_assai_separacao_saldo_modelo_sep_modelo'),
        db.CheckConstraint('qtd_planejada > 0',
                           name='ck_assai_separacao_saldo_modelo_qtd_pos'),
    )

    modelo = db.relationship('AssaiModelo', lazy='joined')

    def __repr__(self):
        return f'<AssaiSeparacaoSaldoModelo sep={self.separacao_id} modelo={self.modelo_id} qtd={self.qtd_planejada}>'

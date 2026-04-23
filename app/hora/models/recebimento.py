"""Ato de receber uma NF em uma loja + conferência unitária por chassi."""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraRecebimento(db.Model):
    """Uma NF chegou fisicamente em uma loja. Header da conferência.

    Fluxo:
      1. Cria com qtd_declarada=NULL (via /recebimentos/novo)
      2. Operador informa qtd_declarada (conferência cega macro)
      3. Wizard por moto: conferencias com ordem=1..qtd_declarada
      4. Finaliza: chassis da NF sem conferência -> MOTO_FALTANDO em batch
    """
    __tablename__ = 'hora_recebimento'

    id = db.Column(db.Integer, primary_key=True)
    nf_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_nf_entrada.id'),
        nullable=False,
        index=True,
    )
    loja_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_loja.id'),
        nullable=False,
        index=True,
    )
    data_recebimento = db.Column(db.Date, nullable=False, default=agora_utc_naive)
    operador = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(30), nullable=False, default='AGUARDANDO_QTD', index=True)
    # Valores: AGUARDANDO_QTD, EM_CONFERENCIA, CONCLUIDO, COM_DIVERGENCIA

    # Conferência cega macro (etapa 2 do fluxo).
    qtd_declarada = db.Column(db.Integer, nullable=True)

    finalizado_em = db.Column(db.DateTime, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    nf = db.relationship('HoraNfEntrada', backref='recebimentos')
    loja = db.relationship('HoraLoja', backref='recebimentos')
    conferencias = db.relationship(
        'HoraRecebimentoConferencia',
        backref='recebimento',
        cascade='all, delete-orphan',
        order_by='HoraRecebimentoConferencia.ordem',
    )
    auditorias = db.relationship(
        'HoraConferenciaAuditoria',
        backref='recebimento',
        cascade='all, delete-orphan',
        order_by='HoraConferenciaAuditoria.criado_em.desc()',
    )

    __table_args__ = (
        db.UniqueConstraint('nf_id', 'loja_id', name='uq_hora_recebimento_nf_loja'),
    )

    def __repr__(self):
        return f'<HoraRecebimento nf={self.nf_id} loja={self.loja_id}>'


class HoraRecebimentoConferencia(db.Model):
    """Conferência unitária de um chassi durante o recebimento.

    Conferência CEGA: operador escaneia chassi (A), escolhe modelo (B),
    escolhe cor (C), marca avaria (D). O sistema compara com a NF e deriva
    divergências AUTOMATICAMENTE na tabela filha `hora_conferencia_divergencia`
    (1-N por conferência).

    Reconferência (3a): cria NOVA linha com ordem reutilizada via UNIQUE
    parcial `(recebimento_id, ordem, substituida=False)`. A linha antiga vira
    `substituida=True` e preserva historico.
    """
    __tablename__ = 'hora_recebimento_conferencia'

    id = db.Column(db.Integer, primary_key=True)
    recebimento_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_recebimento.id'),
        nullable=False,
        index=True,
    )
    ordem = db.Column(db.Integer, nullable=False)
    # posicao na fila 1..qtd_declarada. UNIQUE parcial (substituida=False).

    numero_chassi = db.Column(
        db.String(30),
        db.ForeignKey('hora_moto.numero_chassi'),
        nullable=False,
        index=True,
    )
    conferido_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    confirmado_em = db.Column(db.DateTime, nullable=True)
    # Conferencia confirmada (wizard completou passo D). NULL = em andamento.

    qr_code_lido = db.Column(db.Boolean, nullable=False, default=False)
    # Setado automaticamente quando chassi vem via camera (nao mais checkbox).

    foto_s3_key = db.Column(db.String(500), nullable=True)

    modelo_id_conferido = db.Column(
        db.Integer, db.ForeignKey('hora_modelo.id'), nullable=True,
    )
    cor_conferida = db.Column(db.String(50), nullable=True)
    avaria_fisica = db.Column(db.Boolean, nullable=False, default=False)

    # Snapshot de divergencia "resumo" para queries rapidas (SO PARA LEGADO +
    # MOTO_FALTANDO). Divergencias novas ficam 1-N em hora_conferencia_divergencia.
    tipo_divergencia = db.Column(db.String(30), nullable=True, index=True)
    detalhe_divergencia = db.Column(db.Text, nullable=True)

    # Reconferência (3a): nova linha substitui a anterior.
    substituida = db.Column(db.Boolean, nullable=False, default=False, index=True)
    substituida_por_id = db.Column(
        db.Integer, db.ForeignKey('hora_recebimento_conferencia.id'), nullable=True,
    )

    operador = db.Column(db.String(100), nullable=True)

    moto = db.relationship('HoraMoto', backref='conferencias_recebimento')
    modelo_conferido = db.relationship('HoraModelo', foreign_keys=[modelo_id_conferido])
    divergencias = db.relationship(
        'HoraConferenciaDivergencia',
        backref='conferencia',
        cascade='all, delete-orphan',
    )
    substitui = db.relationship(
        'HoraRecebimentoConferencia',
        remote_side=[id],
        foreign_keys=[substituida_por_id],
    )

    __table_args__ = (
        # UNIQUE (recebimento, chassi) apenas para linhas ATIVAS (nao substituidas).
        # PostgreSQL partial UNIQUE criado via migration (nao representavel 100% aqui).
        db.Index(
            'ix_hora_conferencia_ativa',
            'recebimento_id', 'numero_chassi',
            unique=True,
            postgresql_where=db.text('substituida = false'),
        ),
        db.Index(
            'ix_hora_conferencia_ordem_ativa',
            'recebimento_id', 'ordem',
            unique=True,
            postgresql_where=db.text('substituida = false'),
        ),
    )

    def __repr__(self):
        return (
            f'<HoraRecebimentoConferencia ord={self.ordem} '
            f'chassi={self.numero_chassi} subst={self.substituida}>'
        )


class HoraConferenciaDivergencia(db.Model):
    """Divergência 1-N de uma conferência.

    Uma conferência pode ter varias divergencias simultaneas (ex.: modelo
    diferente + cor diferente + avaria). Derivado automaticamente do backend
    ao comparar conferencia vs item da NF.

    Tipos: MODELO_DIFERENTE, COR_DIFERENTE, MOTO_FALTANDO, CHASSI_EXTRA,
           AVARIA_FISICA.
    (MOTOR_DIFERENTE removido: sem base para conferir motor.)
    """
    __tablename__ = 'hora_conferencia_divergencia'

    id = db.Column(db.Integer, primary_key=True)
    conferencia_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_recebimento_conferencia.id'),
        nullable=False,
        index=True,
    )
    tipo = db.Column(db.String(30), nullable=False, index=True)
    detalhe = db.Column(db.Text, nullable=True)
    valor_esperado = db.Column(db.String(200), nullable=True)
    valor_conferido = db.Column(db.String(200), nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    __table_args__ = (
        db.UniqueConstraint(
            'conferencia_id', 'tipo',
            name='uq_hora_conferencia_divergencia_tipo',
        ),
    )

    def __repr__(self):
        return f'<HoraConferenciaDivergencia conf={self.conferencia_id} tipo={self.tipo}>'


class HoraConferenciaAuditoria(db.Model):
    """Log append-only de toda acao feita em um recebimento.

    Captura: quem fez, o que fez, antes/depois de cada campo alterado.
    Imutavel: nunca UPDATE/DELETE. Consulta: listar todas as acoes por
    recebimento_id ORDER BY criado_em DESC.
    """
    __tablename__ = 'hora_conferencia_auditoria'

    id = db.Column(db.Integer, primary_key=True)
    recebimento_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_recebimento.id'),
        nullable=False,
        index=True,
    )
    conferencia_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_recebimento_conferencia.id'),
        nullable=True,
        index=True,
    )
    usuario = db.Column(db.String(100), nullable=True)
    acao = db.Column(db.String(40), nullable=False, index=True)
    # INICIOU_RECEBIMENTO, DEFINIU_QTD, ALTEROU_QTD, CONFERIU_MOTO,
    # MARCOU_AVARIA, RECONFEREU_MOTO, SUBSTITUIU_CONFERENCIA,
    # FINALIZOU, AJUSTOU_CAMPO
    campo_alterado = db.Column(db.String(60), nullable=True)
    valor_antes = db.Column(db.Text, nullable=True)
    valor_depois = db.Column(db.Text, nullable=True)
    detalhe = db.Column(db.Text, nullable=True)
    criado_em = db.Column(
        db.DateTime, nullable=False, default=agora_utc_naive, index=True,
    )

    __table_args__ = (
        db.Index(
            'ix_hora_conf_aud_rec_ts',
            'recebimento_id', 'criado_em',
        ),
    )

    def __repr__(self):
        return (
            f'<HoraConferenciaAuditoria rec={self.recebimento_id} '
            f'acao={self.acao} user={self.usuario}>'
        )

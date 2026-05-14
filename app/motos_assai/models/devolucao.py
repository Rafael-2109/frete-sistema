"""Devolucao por NF de venda Q.P.A.

Cliente (Sendas/Assai) emite NF de devolucao (NFd) para 1+ chassis de uma NF
Q.P.A. de venda ja FATURADA. Cada chassi devolvido:
  1. Recebe novo evento PENDENTE (volta ao estoque para conserto)
  2. Observacao do evento: "Moto devolvida - {motivo}"
  3. NF original NAO e cancelada (devolucao parcial e legitima).

Modelo de dados (Migration 29):
- AssaiDevolucaoNfd: 1 linha por NFd (cabecalho).
- AssaiDevolucaoItem: 1 linha por chassi devolvido (UNIQUE devolucao_id+chassi).
- AssaiDevolucaoAnexo: N linhas (PDF, XML, PNG, JPG em S3).

Idempotencia: UNIQUE (nf_qpa_origem_id, numero_nfd).
"""
from app import db
from app.utils.timezone import agora_brasil_naive


DEVOLUCAO_ANEXO_TIPO_PDF = 'PDF'
DEVOLUCAO_ANEXO_TIPO_XML = 'XML'
DEVOLUCAO_ANEXO_TIPO_IMAGEM = 'IMAGEM'
DEVOLUCAO_ANEXO_TIPO_OUTRO = 'OUTRO'
DEVOLUCAO_ANEXO_TIPOS_VALIDOS = {
    DEVOLUCAO_ANEXO_TIPO_PDF, DEVOLUCAO_ANEXO_TIPO_XML,
    DEVOLUCAO_ANEXO_TIPO_IMAGEM, DEVOLUCAO_ANEXO_TIPO_OUTRO,
}


class AssaiDevolucaoNfd(db.Model):
    __tablename__ = 'assai_devolucao_nfd'

    id = db.Column(db.Integer, primary_key=True)
    nf_qpa_origem_id = db.Column(
        db.Integer,
        db.ForeignKey('assai_nf_qpa.id', ondelete='RESTRICT'),
        nullable=False, index=True,
    )
    numero_nfd = db.Column(db.String(40), nullable=False)
    data_devolucao = db.Column(db.Date, nullable=False)
    motivo = db.Column(db.Text, nullable=False)
    criado_em = db.Column(
        db.DateTime, default=agora_brasil_naive, nullable=False, index=True,
    )
    criado_por_id = db.Column(
        db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'),
    )

    __table_args__ = (
        db.UniqueConstraint(
            'nf_qpa_origem_id', 'numero_nfd',
            name='uq_assai_devolucao_nf_numero',
        ),
    )

    nf_origem = db.relationship('AssaiNfQpa', lazy='joined')
    criado_por = db.relationship('Usuario', lazy='joined')
    itens = db.relationship(
        'AssaiDevolucaoItem',
        backref='devolucao',
        cascade='all, delete-orphan',
        order_by='AssaiDevolucaoItem.id',
        lazy='selectin',
    )
    anexos = db.relationship(
        'AssaiDevolucaoAnexo',
        backref='devolucao',
        cascade='all, delete-orphan',
        order_by='AssaiDevolucaoAnexo.criado_em.asc()',
        lazy='selectin',
    )

    def __repr__(self):
        return (
            f'<AssaiDevolucaoNfd id={self.id} nf_origem={self.nf_qpa_origem_id} '
            f'nfd={self.numero_nfd}>'
        )


class AssaiDevolucaoItem(db.Model):
    __tablename__ = 'assai_devolucao_item'

    id = db.Column(db.Integer, primary_key=True)
    devolucao_id = db.Column(
        db.Integer,
        db.ForeignKey('assai_devolucao_nfd.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    chassi = db.Column(db.String(50), nullable=False, index=True)
    nf_qpa_item_id = db.Column(
        db.Integer,
        db.ForeignKey('assai_nf_qpa_item.id', ondelete='SET NULL'),
    )
    evento_pendencia_id = db.Column(
        db.Integer,
        db.ForeignKey('assai_moto_evento.id', ondelete='SET NULL'),
    )
    criado_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            'devolucao_id', 'chassi', name='uq_assai_devolucao_item_chassi',
        ),
    )

    # Fix 2026-05-14: foreign_keys=[nf_qpa_item_id] obrigatorio porque ha 2 FKs
    # entre assai_devolucao_item e assai_nf_qpa_item (cruzados para auditoria
    # bidirecional): devolucao_item.nf_qpa_item_id -> nf_qpa_item.id E
    # nf_qpa_item.devolucao_item_id -> devolucao_item.id. Sem foreign_keys=
    # explicito SQLAlchemy levanta AmbiguousForeignKeysError no init do
    # mapper, propagando para TODOS os mappers via "One or more mappers
    # failed to initialize" — derrubava o app inteiro.
    nf_item = db.relationship(
        'AssaiNfQpaItem',
        foreign_keys=[nf_qpa_item_id],
        lazy='joined',
    )
    evento_pendencia = db.relationship('AssaiMotoEvento', lazy='joined')

    def __repr__(self):
        return (
            f'<AssaiDevolucaoItem id={self.id} dev={self.devolucao_id} '
            f'chassi={self.chassi}>'
        )


class AssaiDevolucaoAnexo(db.Model):
    __tablename__ = 'assai_devolucao_anexo'

    id = db.Column(db.Integer, primary_key=True)
    devolucao_id = db.Column(
        db.Integer,
        db.ForeignKey('assai_devolucao_nfd.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    tipo = db.Column(db.String(10), nullable=False)
    nome_original = db.Column(db.String(255), nullable=False)
    s3_key = db.Column(db.String(500), nullable=False)
    content_type = db.Column(db.String(120))
    tamanho_bytes = db.Column(db.BigInteger)
    criado_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)
    criado_por_id = db.Column(
        db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'),
    )

    criado_por = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return (
            f'<AssaiDevolucaoAnexo id={self.id} dev={self.devolucao_id} '
            f'tipo={self.tipo}>'
        )

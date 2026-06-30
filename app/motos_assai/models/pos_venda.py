"""Modelos de Pos-Venda do modulo Motos Assai.

Uma ocorrencia e um relato textual sobre 1 chassi vendido (ja com NF Q.P.A.
importada). Categorias: LOJA (problema na loja Sendas/Assai) ou CLIENTE
(problema reportado pelo consumidor final).

Cada ocorrencia tem N anexos (FOTO/VIDEO/AUDIO/OUTRO) armazenados em S3 no
prefixo `motos_assai/pos_venda/{ocorrencia_id}/`.

Ocorrencias e anexos NAO sao append-only — admitir UPDATE/DELETE para o
operador corrigir relatos. Anexo deletado remove tambem o S3 key (best-effort).
"""

from app import db
from app.utils.timezone import agora_brasil_naive


CATEGORIA_LOJA = 'LOJA'
CATEGORIA_CLIENTE = 'CLIENTE'
CATEGORIAS_VALIDAS = {CATEGORIA_LOJA, CATEGORIA_CLIENTE}

ANEXO_TIPO_FOTO = 'FOTO'
ANEXO_TIPO_VIDEO = 'VIDEO'
ANEXO_TIPO_AUDIO = 'AUDIO'
ANEXO_TIPO_OUTRO = 'OUTRO'
ANEXO_TIPOS_VALIDOS = {
    ANEXO_TIPO_FOTO, ANEXO_TIPO_VIDEO, ANEXO_TIPO_AUDIO, ANEXO_TIPO_OUTRO,
}

TIPO_RELATO = 'RELATO'
TIPO_TROCA_GARANTIA = 'TROCA_GARANTIA'
POS_VENDA_TIPOS_VALIDOS = {TIPO_RELATO, TIPO_TROCA_GARANTIA}


class AssaiPosVendaOcorrencia(db.Model):
    __tablename__ = 'assai_pos_venda_ocorrencia'

    id = db.Column(db.Integer, primary_key=True)
    chassi = db.Column(db.String(50), nullable=False, index=True)
    categoria = db.Column(db.String(10), nullable=False, index=True)
    descricao = db.Column(db.Text, nullable=False)
    tipo = db.Column(
        db.String(20), nullable=False, default=TIPO_RELATO, server_default='RELATO',
    )
    chassi_substituto = db.Column(db.String(50))
    nf_qpa_id = db.Column(
        db.Integer, db.ForeignKey('assai_nf_qpa.id'), index=True,
    )
    criado_em = db.Column(
        db.DateTime, default=agora_brasil_naive, nullable=False, index=True,
    )
    criado_por_id = db.Column(
        db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'),
    )
    atualizado_em = db.Column(db.DateTime)
    atualizado_por_id = db.Column(
        db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'),
    )

    criado_por = db.relationship(
        'Usuario', foreign_keys=[criado_por_id], lazy='joined',
    )
    atualizado_por = db.relationship(
        'Usuario', foreign_keys=[atualizado_por_id], lazy='joined',
    )
    anexos = db.relationship(
        'AssaiPosVendaOcorrenciaAnexo',
        backref='ocorrencia',
        cascade='all, delete-orphan',
        order_by='AssaiPosVendaOcorrenciaAnexo.criado_em.asc()',
        lazy='selectin',
    )

    def __repr__(self):
        return (
            f'<AssaiPosVendaOcorrencia id={self.id} chassi={self.chassi} '
            f'categoria={self.categoria}>'
        )


class AssaiPosVendaOcorrenciaAnexo(db.Model):
    __tablename__ = 'assai_pos_venda_ocorrencia_anexo'

    id = db.Column(db.Integer, primary_key=True)
    ocorrencia_id = db.Column(
        db.Integer,
        db.ForeignKey('assai_pos_venda_ocorrencia.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    tipo = db.Column(db.String(10), nullable=False)
    nome_original = db.Column(db.String(255), nullable=False)
    s3_key = db.Column(db.String(500), nullable=False)
    content_type = db.Column(db.String(120))
    tamanho_bytes = db.Column(db.BigInteger)
    criado_em = db.Column(
        db.DateTime, default=agora_brasil_naive, nullable=False,
    )
    criado_por_id = db.Column(
        db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'),
    )

    criado_por = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return (
            f'<AssaiPosVendaOcorrenciaAnexo id={self.id} '
            f'tipo={self.tipo} oc={self.ocorrencia_id}>'
        )

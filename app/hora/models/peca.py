"""Peca faltando em moto + canibalizacao entre motos.

hora_peca_faltando  : N pendencias por moto (uma por peca ausente).
hora_peca_faltando_foto : N fotos por pendencia.

Canibalizacao: quando uma peca e retirada de uma moto "doadora" para
completar outra, preencher `chassi_doador` — o service emite evento
FALTANDO_PECA na moto doadora automaticamente.
"""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraPecaFaltando(db.Model):
    """Uma peca ausente em uma moto (N por moto)."""
    __tablename__ = 'hora_peca_faltando'

    id = db.Column(db.Integer, primary_key=True)
    # Moto que esta SEM a peca.
    numero_chassi = db.Column(
        db.String(30),
        db.ForeignKey('hora_moto.numero_chassi'),
        nullable=False,
        index=True,
    )
    descricao = db.Column(db.String(255), nullable=False)
    # Ex.: "bateria 72V", "chave de ignicao", "retrovisor esquerdo"

    # Moto que cedeu a peca (canibalizacao). Preenchido quando a peca foi
    # retirada de outra moto para completar esta. Emite evento FALTANDO_PECA
    # no chassi_doador automaticamente no servico.
    chassi_doador = db.Column(
        db.String(30),
        db.ForeignKey('hora_moto.numero_chassi'),
        nullable=True,
        index=True,
    )

    status = db.Column(db.String(20), nullable=False, default='ABERTA', index=True)
    # Valores: ABERTA, RESOLVIDA, CANCELADA

    # Ref opcional a conferencia de recebimento que detectou a falta.
    recebimento_conferencia_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_recebimento_conferencia.id'),
        nullable=True,
    )

    observacoes = db.Column(db.Text, nullable=True)
    criado_por = db.Column(db.String(100), nullable=True)
    resolvido_por = db.Column(db.String(100), nullable=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    resolvido_em = db.Column(db.DateTime, nullable=True)

    moto = db.relationship(
        'HoraMoto',
        foreign_keys=[numero_chassi],
        backref='pecas_faltando',
    )
    moto_doadora = db.relationship('HoraMoto', foreign_keys=[chassi_doador])
    conferencia = db.relationship('HoraRecebimentoConferencia')
    fotos = db.relationship(
        'HoraPecaFaltandoFoto',
        backref='peca_faltando',
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return (
            f'<HoraPecaFaltando chassi={self.numero_chassi} '
            f'peca="{self.descricao}" {self.status}>'
        )


class HoraPecaFaltandoFoto(db.Model):
    """N fotos por pendencia de peca faltando."""
    __tablename__ = 'hora_peca_faltando_foto'

    id = db.Column(db.Integer, primary_key=True)
    peca_faltando_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_peca_faltando.id'),
        nullable=False,
        index=True,
    )
    foto_s3_key = db.Column(db.String(500), nullable=False)
    legenda = db.Column(db.String(255), nullable=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<HoraPecaFaltandoFoto peca={self.peca_faltando_id} key={self.foto_s3_key}>'

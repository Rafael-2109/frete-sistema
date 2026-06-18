"""Recebimento por chassi da Coleta CarVia (stream 4 do redesign, .claire/rascunho.md topico 2).

Recebimento fisico (Matriz SP) de UMA coleta, conferido MOTO A MOTO por chassi (QR Code /
digitado / foto opcional). Principios do rascunho:
- recebimento e POR MOTO, nao por NF; uma NF e dada como "recebida" quando TODOS os seus
  chassis (CarviaNfVeiculo) foram conferidos;
- ESCANEIO LIVRE: o conferente pode bipar um chassi mesmo que a NF real ainda nao esteja
  vinculada/sem chassis cadastrados -> a linha entra em ALERTA (sem vinculo);
- BACKFILL: quando a NF e vinculada (ou chega depois com seus chassis), o
  CarviaColetaRecebimentoService.reconciliar() retro-vincula os chassis ja conferidos, de modo
  que a ORDEM (NF <-> chassi) nao impacte a vinculacao.

Padrao reaproveitado de HORA/Motos Assai (qr_code_lido + foto_s3_key), porem REPLICADO no CarVia
(fronteira de modulo R1 proibe importar hora_*/assai_*).
"""

from app import db
from app.utils.timezone import agora_utc_naive

# Status do recebimento (cabecalho)
RECEB_STATUS_EM_RECEBIMENTO = 'EM_RECEBIMENTO'
RECEB_STATUS_CONCLUIDO = 'CONCLUIDO'
RECEB_STATUS_COM_DIVERGENCIA = 'COM_DIVERGENCIA'
RECEB_STATUSES = (RECEB_STATUS_EM_RECEBIMENTO, RECEB_STATUS_CONCLUIDO, RECEB_STATUS_COM_DIVERGENCIA)

# Status do chassi conferido
CHASSI_STATUS_VINCULADO = 'VINCULADO'   # casou com um CarviaNfVeiculo de NF vinculada a coleta
CHASSI_STATUS_ALERTA = 'ALERTA'         # conferido mas sem vinculo (NF nao vinculada / sem chassi ainda)


def normalizar_chassi(chassi):
    return (chassi or '').strip().upper().replace(' ', '') or None


class CarviaColetaRecebimento(db.Model):
    """Recebimento fisico (Matriz SP) de uma coleta — 1:1 com CarviaColeta."""
    __tablename__ = 'carvia_coleta_recebimentos'

    id = db.Column(db.Integer, primary_key=True)
    coleta_id = db.Column(
        db.Integer, db.ForeignKey('carvia_coletas.id', ondelete='CASCADE'),
        nullable=False, unique=True, index=True,
    )
    status = db.Column(
        db.String(20), nullable=False, default=RECEB_STATUS_EM_RECEBIMENTO,
        server_default=RECEB_STATUS_EM_RECEBIMENTO, index=True,
    )
    iniciado_por = db.Column(db.String(150))
    iniciado_em = db.Column(db.DateTime, default=agora_utc_naive)
    concluido_por = db.Column(db.String(150))
    concluido_em = db.Column(db.DateTime)

    coleta = db.relationship(
        'CarviaColeta', backref=db.backref('recebimento', uselist=False))
    chassis = db.relationship(
        'CarviaColetaRecebimentoChassi', backref='recebimento', lazy='dynamic',
        cascade='all, delete-orphan', order_by='CarviaColetaRecebimentoChassi.id')

    @property
    def total_conferidos(self):
        return self.chassis.count()

    @property
    def total_vinculados(self):
        return self.chassis.filter_by(status=CHASSI_STATUS_VINCULADO).count()

    @property
    def total_alerta(self):
        return self.chassis.filter_by(status=CHASSI_STATUS_ALERTA).count()

    def __repr__(self):
        return f'<CarviaColetaRecebimento coleta={self.coleta_id} ({self.status})>'


class CarviaColetaRecebimentoChassi(db.Model):
    """Um chassi (moto) conferido fisicamente no recebimento de uma coleta."""
    __tablename__ = 'carvia_coleta_recebimento_chassis'
    __table_args__ = (
        db.UniqueConstraint('recebimento_id', 'chassi', name='uq_carvia_receb_chassi'),
    )

    id = db.Column(db.Integer, primary_key=True)
    recebimento_id = db.Column(
        db.Integer, db.ForeignKey('carvia_coleta_recebimentos.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    chassi = db.Column(db.String(30), nullable=False)
    modelo = db.Column(db.String(100))           # opcional (lido/informado) — cor NAO e validada
    qr_code_lido = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    foto_s3_key = db.Column(db.String(500))      # SEMPRE opcional

    # Vinculo ao chassi esperado da NF (preenchido no match/backfill). NULL = ALERTA.
    carvia_nf_veiculo_id = db.Column(
        db.Integer, db.ForeignKey('carvia_nf_veiculos.id'), nullable=True, index=True)
    status = db.Column(
        db.String(20), nullable=False, default=CHASSI_STATUS_ALERTA,
        server_default=CHASSI_STATUS_ALERTA, index=True)

    conferido_por = db.Column(db.String(150))
    conferido_em = db.Column(db.DateTime, default=agora_utc_naive)

    carvia_nf_veiculo = db.relationship('CarviaNfVeiculo')

    @property
    def vinculado(self):
        return self.carvia_nf_veiculo_id is not None

    def __repr__(self):
        return f'<CarviaColetaRecebimentoChassi {self.chassi} ({self.status})>'

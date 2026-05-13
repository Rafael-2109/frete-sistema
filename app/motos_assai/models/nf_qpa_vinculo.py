"""AssaiNfQpaItemVinculoHistorico - auditoria de vinculo NF-item <-> Sep-item.

Spec: S2.1 (S16=c)
Plano: Task 12
"""
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.utils.timezone import agora_brasil_naive


VINCULO_MOTIVO_NF_CANCELADA = 'NF_CANCELADA'
VINCULO_MOTIVO_CCE_ALTEROU_CHASSI = 'CCE_ALTEROU_CHASSI'
VINCULO_MOTIVO_SUBSTITUICAO_CROSS_LOJA = 'SUBSTITUICAO_CROSS_LOJA'

VINCULO_MOTIVOS_VALIDOS = {
    VINCULO_MOTIVO_NF_CANCELADA,
    VINCULO_MOTIVO_CCE_ALTEROU_CHASSI,
    VINCULO_MOTIVO_SUBSTITUICAO_CROSS_LOJA,
}


class AssaiNfQpaItemVinculoHistorico(db.Model):
    __tablename__ = 'assai_nf_qpa_item_vinculo_historico'

    id = db.Column(db.Integer, primary_key=True)
    nf_qpa_item_id = db.Column(db.Integer, db.ForeignKey('assai_nf_qpa_item.id'), nullable=False, index=True)
    separacao_item_id = db.Column(db.Integer, db.ForeignKey('assai_separacao_item.id', ondelete='SET NULL'))
    motivo = db.Column(db.String(40), nullable=False)
    chassi_no_momento = db.Column(db.String(50), nullable=False)
    registrado_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    registrado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    detalhes = db.Column(JSONB, default=dict)

    nf_qpa_item = db.relationship('AssaiNfQpaItem')
    separacao_item = db.relationship('AssaiSeparacaoItem')

    def __repr__(self):
        return f'<AssaiNfQpaItemVinculoHistorico #{self.id} motivo={self.motivo} chassi={self.chassi_no_momento}>'

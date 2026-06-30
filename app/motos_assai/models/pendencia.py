"""AssaiPendencia — ficha de pendencia categorizada (Spec 1 §4.3/§5).

Molde AssaiDivergencia (status derivado de resolvida_em/cancelada_em, detalhes
JSONB). Validacao de categoria/origem/fase/tratativa por set Python no service
(sem CHECK no banco). Auto-relacao pai/filhas para REVISAO (D1).
"""
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.utils.timezone import agora_brasil_naive


# Categorias
PENDENCIA_CATEGORIA_AVARIA = 'AVARIA'
PENDENCIA_CATEGORIA_FALTA_PECA = 'FALTA_PECA'
PENDENCIA_CATEGORIA_REVISAO = 'REVISAO'
PENDENCIA_CATEGORIA_VENDA = 'VENDA'
PENDENCIA_CATEGORIA_INDETERMINADA = 'INDETERMINADA'  # sentinela transitoria (backfill / pre-classificacao)
PENDENCIA_CATEGORIAS_VALIDAS = {
    PENDENCIA_CATEGORIA_AVARIA,
    PENDENCIA_CATEGORIA_FALTA_PECA,
    PENDENCIA_CATEGORIA_REVISAO,
    PENDENCIA_CATEGORIA_VENDA,
    PENDENCIA_CATEGORIA_INDETERMINADA,
}

# Origens
PENDENCIA_ORIGEM_GALPAO = 'GALPAO'
PENDENCIA_ORIGEM_TRANSPORTE = 'TRANSPORTE'
PENDENCIA_ORIGEM_POS_VENDA_CLIENTE = 'POS_VENDA_CLIENTE'
PENDENCIA_ORIGEM_POS_VENDA_LOJA = 'POS_VENDA_LOJA'
PENDENCIA_ORIGEM_DEVOLUCAO = 'DEVOLUCAO'
PENDENCIA_ORIGENS_VALIDAS = {
    PENDENCIA_ORIGEM_GALPAO,
    PENDENCIA_ORIGEM_TRANSPORTE,
    PENDENCIA_ORIGEM_POS_VENDA_CLIENTE,
    PENDENCIA_ORIGEM_POS_VENDA_LOJA,
    PENDENCIA_ORIGEM_DEVOLUCAO,
}
# origens que afetam o estado fisico da moto (emitem/compartilham PENDENTE)
ORIGENS_FISICAS = {
    PENDENCIA_ORIGEM_GALPAO,
    PENDENCIA_ORIGEM_TRANSPORTE,
    PENDENCIA_ORIGEM_DEVOLUCAO,
}

# Fases (informativa — nunca decide logica de estado da moto)
PENDENCIA_FASE_ABERTA = 'ABERTA'
PENDENCIA_FASE_EM_TRATATIVA = 'EM_TRATATIVA'
PENDENCIA_FASE_AGUARDANDO_PECA = 'AGUARDANDO_PECA'
PENDENCIA_FASES_VALIDAS = {
    PENDENCIA_FASE_ABERTA,
    PENDENCIA_FASE_EM_TRATATIVA,
    PENDENCIA_FASE_AGUARDANDO_PECA,
}

# Tratativas (acao que RESOLVE a ficha)
PENDENCIA_TRATATIVA_USAR_ESTOQUE = 'USAR_ESTOQUE'
PENDENCIA_TRATATIVA_USAR_OUTRA_MOTO = 'USAR_OUTRA_MOTO'
PENDENCIA_TRATATIVA_CONSERTAR = 'CONSERTAR'
PENDENCIA_TRATATIVA_REVISAR = 'REVISAR'
PENDENCIA_TRATATIVAS_VALIDAS = {
    PENDENCIA_TRATATIVA_USAR_ESTOQUE,
    PENDENCIA_TRATATIVA_USAR_OUTRA_MOTO,
    PENDENCIA_TRATATIVA_CONSERTAR,
    PENDENCIA_TRATATIVA_REVISAR,
}


class AssaiPendencia(db.Model):
    __tablename__ = 'assai_pendencia'

    id = db.Column(db.Integer, primary_key=True)
    chassi = db.Column(db.String(50), nullable=False, index=True)
    categoria = db.Column(db.String(20), nullable=False)
    origem = db.Column(db.String(20), nullable=False)
    tratativa = db.Column(db.String(40))
    fase = db.Column(db.String(20), nullable=False, default=PENDENCIA_FASE_ABERTA)
    retorno_fisico = db.Column(db.Boolean, nullable=False, default=False)
    descricao = db.Column(db.Text, nullable=False)

    pendencia_pai_id = db.Column(db.Integer, db.ForeignKey('assai_pendencia.id', ondelete='SET NULL'))
    evento_pendente_id = db.Column(db.Integer, db.ForeignKey('assai_moto_evento.id', ondelete='SET NULL'))
    peca_id = db.Column(db.Integer, db.ForeignKey('assai_peca.id', ondelete='SET NULL'))
    chassi_doador = db.Column(db.String(50))
    devolucao_item_id = db.Column(db.Integer, db.ForeignKey('assai_devolucao_item.id', ondelete='SET NULL'))
    pos_venda_ocorrencia_id = db.Column(db.Integer, db.ForeignKey('assai_pos_venda_ocorrencia.id', ondelete='SET NULL'))
    divergencia_origem_id = db.Column(db.Integer, db.ForeignKey('assai_divergencia.id', ondelete='SET NULL'))

    detalhes = db.Column(JSONB, default=dict)

    aberta_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    aberta_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    resolvida_em = db.Column(db.DateTime)
    resolvida_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    resolucao_descricao = db.Column(db.Text)
    cancelada_em = db.Column(db.DateTime)
    cancelada_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))

    filhas = db.relationship(
        'AssaiPendencia',
        backref=db.backref('pai', remote_side=[id]),
    )

    @property
    def esta_aberta(self):
        return self.resolvida_em is None and self.cancelada_em is None

    def __repr__(self):
        status = 'aberta' if self.esta_aberta else ('resolvida' if self.resolvida_em else 'cancelada')
        return f'<AssaiPendencia #{self.id} {self.categoria}/{self.origem} chassi={self.chassi} {status}>'

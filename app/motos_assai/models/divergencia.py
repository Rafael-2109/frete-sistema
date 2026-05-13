"""AssaiDivergencia - sistema centralizado de divergencias.

Spec: S2.1, S7
Plano: Task 10

8 tipos de divergencia (4 novos + 4 legados) + 5 tipos de resolucao.
"""
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.utils.timezone import agora_brasil_naive


# Tipos novos (Carregamento x NF + cross-loja)
DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO = 'NF_CHASSI_FORA_CARREGAMENTO'
DIVERGENCIA_TIPO_CARREGAMENTO_CHASSI_FORA_NF = 'CARREGAMENTO_CHASSI_FORA_NF'
DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO = 'CHASSI_NAO_CADASTRADO'
DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA = 'CHASSI_OUTRA_LOJA'

# Tipos legados de _calcular_match (S8=a centralizar)
DIVERGENCIA_TIPO_LOJA_DIVERGENTE = 'LOJA_DIVERGENTE'
DIVERGENCIA_TIPO_VALOR_DIVERGENTE = 'VALOR_DIVERGENTE'
DIVERGENCIA_TIPO_MODELO_DIVERGENTE = 'MODELO_DIVERGENTE'
DIVERGENCIA_TIPO_CHASSI_SEM_SEPARACAO = 'CHASSI_SEM_SEPARACAO'

DIVERGENCIA_TIPOS_VALIDOS = {
    DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO,
    DIVERGENCIA_TIPO_CARREGAMENTO_CHASSI_FORA_NF,
    DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO,
    DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
    DIVERGENCIA_TIPO_LOJA_DIVERGENTE,
    DIVERGENCIA_TIPO_VALOR_DIVERGENTE,
    DIVERGENCIA_TIPO_MODELO_DIVERGENTE,
    DIVERGENCIA_TIPO_CHASSI_SEM_SEPARACAO,
}

# Tipos de resolucao
DIVERGENCIA_RESOLUCAO_CANCELAR_NF = 'CANCELAR_NF'
DIVERGENCIA_RESOLUCAO_CCE = 'CCE'
DIVERGENCIA_RESOLUCAO_ALTERAR_CARREGAMENTO = 'ALTERAR_CARREGAMENTO'
DIVERGENCIA_RESOLUCAO_SUBSTITUIR_CHASSI = 'SUBSTITUIR_CHASSI'
DIVERGENCIA_RESOLUCAO_IGNORAR = 'IGNORAR'

DIVERGENCIA_RESOLUCAO_VALIDAS = {
    DIVERGENCIA_RESOLUCAO_CANCELAR_NF,
    DIVERGENCIA_RESOLUCAO_CCE,
    DIVERGENCIA_RESOLUCAO_ALTERAR_CARREGAMENTO,
    DIVERGENCIA_RESOLUCAO_SUBSTITUIR_CHASSI,
    DIVERGENCIA_RESOLUCAO_IGNORAR,
}


class AssaiDivergencia(db.Model):
    __tablename__ = 'assai_divergencia'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(40), nullable=False)
    chassi = db.Column(db.String(50), index=True)
    separacao_id = db.Column(db.Integer, db.ForeignKey('assai_separacao.id'), index=True)
    carregamento_id = db.Column(db.Integer, db.ForeignKey('assai_carregamento.id'))
    nf_id = db.Column(db.Integer, db.ForeignKey('assai_nf_qpa.id'), index=True)
    detalhes = db.Column(JSONB, default=dict)
    criada_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    resolvida_em = db.Column(db.DateTime)
    resolvida_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    tipo_resolucao = db.Column(db.String(40))
    observacao_resolucao = db.Column(db.Text)

    separacao = db.relationship('AssaiSeparacao')
    carregamento = db.relationship('AssaiCarregamento')
    nf = db.relationship('AssaiNfQpa')

    def __repr__(self):
        status = 'resolvida' if self.resolvida_em else 'pendente'
        return f'<AssaiDivergencia #{self.id} tipo={self.tipo} chassi={self.chassi} {status}>'

from app import db
from sqlalchemy.dialects.postgresql import JSONB
from app.utils.timezone import agora_brasil_naive


# Eventos canônicos
EVENTO_ESTOQUE = 'ESTOQUE'
EVENTO_MONTADA = 'MONTADA'
EVENTO_PENDENTE = 'PENDENTE'
EVENTO_PENDENCIA_RESOLVIDA = 'PENDENCIA_RESOLVIDA'
EVENTO_DISPONIVEL = 'DISPONIVEL'
EVENTO_REVERTIDA_PARA_MONTADA = 'REVERTIDA_PARA_MONTADA'
EVENTO_SEPARADA = 'SEPARADA'
EVENTO_CARREGADA = 'CARREGADA'  # NOVO Fase 1: entre SEPARADA e FATURADA (Q8)
EVENTO_FATURADA = 'FATURADA'
EVENTO_CANCELADA = 'CANCELADA'
EVENTO_MOTO_FALTANDO = 'MOTO_FALTANDO'

EVENTOS_VALIDOS = {
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE, EVENTO_PENDENCIA_RESOLVIDA,
    EVENTO_DISPONIVEL, EVENTO_REVERTIDA_PARA_MONTADA,
    EVENTO_SEPARADA, EVENTO_CARREGADA, EVENTO_FATURADA, EVENTO_CANCELADA,
    EVENTO_MOTO_FALTANDO,
}

# Eventos que indicam moto presente em estoque (qualquer estágio interno)
EVENTOS_EM_ESTOQUE = {EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE, EVENTO_DISPONIVEL}
EVENTOS_BLOQUEADO_DISPONIBILIZAR = {EVENTO_PENDENTE}
EVENTOS_FORA_ESTOQUE = {
    EVENTO_SEPARADA,
    EVENTO_CARREGADA,  # NOVO: chassi carregado nao conta como estoque
    EVENTO_FATURADA,
    EVENTO_CANCELADA,
    EVENTO_MOTO_FALTANDO,
}


class AssaiMoto(db.Model):
    __tablename__ = 'assai_moto'

    id = db.Column(db.Integer, primary_key=True)
    chassi = db.Column(db.String(50), unique=True, nullable=False)
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id'), nullable=False)
    cor = db.Column(db.String(40))
    motor = db.Column(db.String(50))
    ano = db.Column(db.Integer)
    criada_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)

    modelo = db.relationship('AssaiModelo', backref='motos', lazy='joined')

    def __repr__(self):
        return f'<AssaiMoto {self.chassi}>'


class AssaiMotoEvento(db.Model):
    __tablename__ = 'assai_moto_evento'

    id = db.Column(db.Integer, primary_key=True)
    chassi = db.Column(db.String(50), nullable=False, index=True)
    tipo = db.Column(db.String(40), nullable=False)
    ocorrido_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)
    operador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    observacao = db.Column(db.Text)
    dados_extras = db.Column(JSONB, default=dict)

    operador = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return f'<AssaiMotoEvento {self.chassi} {self.tipo} @{self.ocorrido_em}>'

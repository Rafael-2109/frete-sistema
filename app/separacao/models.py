from app import db  # ou de onde você estiver importando seu `db`
from datetime import datetime

# models.py
class Separacao(db.Model):
    __tablename__ = 'separacao'

    id = db.Column(db.Integer, primary_key=True)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # ID do lote de separação
    num_pedido = db.Column(db.String(50), nullable=True)
    data_pedido = db.Column(db.Date, nullable=True)  # agora pode ser nulo
    cnpj_cpf = db.Column(db.String(20), nullable=True)
    raz_social_red = db.Column(db.String(255), nullable=True)
    nome_cidade = db.Column(db.String(100), nullable=True)
    cod_uf = db.Column(db.String(2), nullable=False)
    cod_produto = db.Column(db.String(50), nullable=True)
    nome_produto = db.Column(db.String(255), nullable=True)

    qtd_saldo = db.Column(db.Float, nullable=True)  # agora pode ser nulo
    valor_saldo = db.Column(db.Float, nullable=True)
    pallet = db.Column(db.Float, nullable=True)
    peso = db.Column(db.Float, nullable=True)

    rota = db.Column(db.String(50), nullable=True)
    sub_rota = db.Column(db.String(50), nullable=True)
    observ_ped_1 = db.Column(db.String(700), nullable=True)
    roteirizacao = db.Column(db.String(255), nullable=True)
    expedicao = db.Column(db.Date, nullable=True)
    agendamento = db.Column(db.Date, nullable=True)
    agendamento_confirmado = db.Column(db.Boolean, default=False)  # Flag para confirmação de agendamento
    protocolo = db.Column(db.String(50), nullable=True)
    
    # 🎯 ETAPA 2: CAMPO TIPO DE ENVIO (ADICIONADO NA MIGRAÇÃO)
    tipo_envio = db.Column(db.String(10), default='total', nullable=True)  # total, parcial
    
    # 🔄 CAMPOS DE CONTROLE DE SINCRONIZAÇÃO (FASE 3)
    sincronizado_nf = db.Column(db.Boolean, default=False, nullable=True)  # Indica se foi sincronizado com NF
    numero_nf = db.Column(db.String(20), nullable=True)  # NF associada quando sincronizada
    data_sincronizacao = db.Column(db.DateTime, nullable=True)  # Data/hora da sincronização
    zerado_por_sync = db.Column(db.Boolean, default=False, nullable=True)  # Indica se foi zerado por sincronização
    data_zeragem = db.Column(db.DateTime, nullable=True)  # Data/hora quando foi zerado

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Separacao #{self.id} - {self.num_pedido} - Lote: {self.separacao_lote_id} - Tipo: {self.tipo_envio}>'

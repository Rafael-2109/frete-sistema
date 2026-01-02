from app import db
from datetime import datetime

class EntregaMonitorada(db.Model):
    __tablename__ = 'entregas_monitoradas'

    id = db.Column(db.Integer, primary_key=True)
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    cliente = db.Column(db.String(255), nullable=False)
    transportadora = db.Column(db.String(255), nullable=True)
    municipio = db.Column(db.String(100), nullable=True)
    uf = db.Column(db.String(2), nullable=True)
    vendedor = db.Column(db.String(100), nullable=True)
    cnpj_cliente = db.Column(db.String(20), nullable=True, index=True)

    valor_nf = db.Column(db.Float, nullable=True)
    data_faturamento = db.Column(db.Date, nullable=True)
    data_embarque = db.Column(db.Date, nullable=True)
    data_entrega_prevista = db.Column(db.Date, nullable=True)
    data_hora_entrega_realizada = db.Column(db.DateTime, nullable=True)
    entregue = db.Column(db.Boolean, default=False)
    lead_time = db.Column(db.Integer, nullable=True)


    reagendar = db.Column(db.Boolean, default=False)
    motivo_reagendamento = db.Column(db.String(255), nullable=True)
    data_agenda = db.Column(db.Date, nullable=True)  # <--- AQUI

    observacao_operacional = db.Column(db.Text, nullable=True)
    pendencia_financeira = db.Column(db.Boolean, default=False)
    resposta_financeiro = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=True)
    nf_cd = db.Column(db.Boolean, default=False)  # Indica se está no CD
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # ID do lote de separação

    finalizado_por = db.Column(db.String(100))
    finalizado_em = db.Column(db.DateTime)
    comentarios = db.relationship('ComentarioNF', backref='entrega', lazy='dynamic')
    status_finalizacao = db.Column(db.String(50), nullable=True)
    nova_nf = db.Column(db.String(20), nullable=True)
    substituida_por_nf_id = db.Column(db.Integer, db.ForeignKey('entregas_monitoradas.id'), nullable=True)
    substituida_por_nf = db.relationship('EntregaMonitorada', remote_side=[id], backref='substituicoes')
    
    # Canhoto da entrega
    canhoto_arquivo = db.Column(db.String(500), nullable=True)  # Caminho do arquivo do canhoto

    # Devolucao
    teve_devolucao = db.Column(db.Boolean, default=False, nullable=False)  # Indica se houve devolucao

    @property
    def possui_comentarios(self):
        return self.comentarios.count() > 0
    
    @property
    def possui_canhoto(self):
        """Verifica se a entrega possui canhoto anexado"""
        return bool(self.canhoto_arquivo)

    def __repr__(self):
        return f"<Entrega NF {self.numero_nf} - {self.cliente}>"
    

    def comentarios_pendentes(self, current_username):
        return self.comentarios.filter(
            ComentarioNF.autor != current_username, 
            ~ComentarioNF.respostas.any()
        ).count()
    
    @property
    def data_agendamento_mais_recente(self):
        # Se 'agendamentos' for uma lista
        if len(self.agendamentos) == 0:
            return None

        ag_recente = sorted(self.agendamentos, key=lambda ag: ag.criado_em, reverse=True)[0]
        return ag_recente.data_agendada


class AgendamentoEntrega(db.Model):
    __tablename__ = 'agendamentos_entrega'

    id = db.Column(db.Integer, primary_key=True)
    entrega_id = db.Column(db.Integer, db.ForeignKey('entregas_monitoradas.id'))
    data_agendada = db.Column(db.Date)
    hora_agendada = db.Column(db.Time)

    forma_agendamento = db.Column(db.String(50))  # Portal, Telefone, etc.
    contato_agendamento = db.Column(db.String(255))  # login, telefone, e-mail
    protocolo_agendamento = db.Column(db.String(100))  # número ou código

    motivo = db.Column(db.String(255))
    observacao = db.Column(db.Text)  # ← NOVO CAMPO
    autor = db.Column(db.String(100))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ✅ NOVOS CAMPOS DE STATUS
    status = db.Column(db.String(20), default='aguardando')  # aguardando, confirmado (novos agendamentos aguardam por padrão)
    confirmado_por = db.Column(db.String(100), nullable=True)
    confirmado_em = db.Column(db.DateTime, nullable=True)
    observacoes_confirmacao = db.Column(db.Text, nullable=True)

    entrega = db.relationship('EntregaMonitorada', backref='agendamentos')
    
    @property
    def ultimo_agendamento(self):
        """Verifica se este é o último agendamento da entrega"""
        return self == max(self.entrega.agendamentos, key=lambda ag: ag.criado_em) if self.entrega.agendamentos else False

class EventoEntrega(db.Model):
    __tablename__ = 'eventos_entrega'

    id = db.Column(db.Integer, primary_key=True)
    entrega_id = db.Column(db.Integer, db.ForeignKey('entregas_monitoradas.id'))
    data_hora_chegada = db.Column(db.DateTime)
    data_hora_saida = db.Column(db.DateTime)
    motorista = db.Column(db.String(100))
    tipo_evento = db.Column(db.String(50))  # entrega, reentrega, tentativa, NF no CD
    observacao = db.Column(db.Text)
    autor = db.Column(db.String(100))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


    entrega = db.relationship('EntregaMonitorada', backref='eventos')

class CustoExtraEntrega(db.Model):
    __tablename__ = 'custos_extra_entrega'

    id = db.Column(db.Integer, primary_key=True)
    entrega_id = db.Column(db.Integer, db.ForeignKey('entregas_monitoradas.id'))
    tipo = db.Column(db.String(50))  # TDE, Diária, Reentrega
    valor = db.Column(db.Float)
    motivo = db.Column(db.String(255))
    autor = db.Column(db.String(100))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


    entrega = db.relationship('EntregaMonitorada', backref='custos_extras')

class RegistroLogEntrega(db.Model):
    __tablename__ = 'logs_entrega'

    id = db.Column(db.Integer, primary_key=True)
    entrega_id = db.Column(db.Integer, db.ForeignKey('entregas_monitoradas.id'))
    autor = db.Column(db.String(100))
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)
    descricao = db.Column(db.Text)
    tipo = db.Column(db.String(50))  # ação, contato, info
    lembrete_para = db.Column(db.DateTime, nullable=True)

    entrega = db.relationship('EntregaMonitorada', backref='logs')


class ComentarioNF(db.Model):
    __tablename__ = 'comentarios_nf'
    
    id = db.Column(db.Integer, primary_key=True)
    entrega_id = db.Column(db.Integer, db.ForeignKey('entregas_monitoradas.id'), nullable=False)
    autor = db.Column(db.String(150), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    arquivo = db.Column(db.String(255), nullable=True)
    resposta_a_id = db.Column(db.Integer, db.ForeignKey('comentarios_nf.id'), nullable=True)
    
    respostas = db.relationship('ComentarioNF', backref=db.backref('comentario_pai', remote_side=[id]))


class HistoricoDataPrevista(db.Model):
    __tablename__ = 'historico_data_prevista'
    
    id = db.Column(db.Integer, primary_key=True)
    entrega_id = db.Column(db.Integer, db.ForeignKey('entregas_monitoradas.id'), nullable=False)
    data_anterior = db.Column(db.Date, nullable=True)  # Data anterior (pode ser None na primeira vez)
    data_nova = db.Column(db.Date, nullable=False)  # Nova data
    motivo_alteracao = db.Column(db.Text, nullable=False)  # Motivo da alteração
    alterado_por = db.Column(db.String(100), nullable=False)  # Quem alterou
    alterado_em = db.Column(db.DateTime, default=datetime.utcnow)  # Quando foi alterado
    
    entrega = db.relationship('EntregaMonitorada', backref='historico_data_prevista')

class ArquivoEntrega(db.Model):
    """
    Rastreia arquivos das entregas (local e S3)
    """
    __tablename__ = 'arquivo_entrega'
    
    id = db.Column(db.Integer, primary_key=True)
    entrega_id = db.Column(db.Integer, db.ForeignKey('entregas_monitoradas.id'), nullable=False)
    nome_original = db.Column(db.String(255), nullable=False)  # Nome original do arquivo
    nome_arquivo = db.Column(db.String(255), nullable=False)   # Nome do arquivo no storage
    caminho_arquivo = db.Column(db.String(500), nullable=False)  # Caminho completo no storage
    tipo_storage = db.Column(db.String(20), nullable=False)    # 'local' ou 's3'
    tamanho_bytes = db.Column(db.Integer)                      # Tamanho do arquivo
    content_type = db.Column(db.String(100))                   # Tipo MIME
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=False)
    
    # Relacionamento
    entrega = db.relationship('EntregaMonitorada', backref=db.backref('arquivos_entrega', lazy=True, cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<ArquivoEntrega {self.nome_original} - Entrega {self.entrega_id}>'
    
    @property
    def extensao(self):
        """Retorna a extensão do arquivo"""
        return self.nome_original.split('.')[-1].lower() if '.' in self.nome_original else ''
    
    @property
    def icone(self):
        """Retorna emoji do ícone baseado na extensão"""
        ext = self.extensao
        if ext in ['pdf']:
            return '📄'
        elif ext in ['jpg', 'jpeg', 'png']:
            return '🖼️'
        elif ext in ['doc', 'docx']:
            return '📝'
        elif ext in ['xls', 'xlsx']:
            return '📊'
        else:
            return '📁'

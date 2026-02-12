from datetime import datetime
from app import db
from app.utils.timezone import agora_utc_naive
from app.embarques.models import Embarque
from app.veiculos.models import Veiculo


class Motorista(db.Model):
    """
    Modelo para cadastro de motoristas
    """
    __tablename__ = 'motoristas'
    
    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(255), nullable=False)
    rg = db.Column(db.String(20), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False, index=True)  # Index para busca rápida
    telefone = db.Column(db.String(20), nullable=False)
    foto_documento = db.Column(db.String(255), nullable=True)  # Caminho para arquivo da foto
    
    # Timestamps
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)
    
    # Relacionamentos
    registros_portaria = db.relationship('ControlePortaria', backref='motorista_obj', lazy='dynamic')
    
    def __repr__(self):
        return f'<Motorista {self.nome_completo}>'
    
    @staticmethod
    def buscar_por_cpf(cpf):
        """Busca motorista por CPF removendo formatação"""
        cpf_limpo = cpf.replace('.', '').replace('-', '').replace('/', '')
        return Motorista.query.filter(
            db.func.replace(
                db.func.replace(
                    db.func.replace(Motorista.cpf, '.', ''), 
                    '-', ''
                ), 
                '/', ''
            ) == cpf_limpo
        ).first()

class ControlePortaria(db.Model):
    """
    Modelo para controle de entrada e saída na portaria
    """
    __tablename__ = 'controle_portaria'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Dados do motorista
    motorista_id = db.Column(db.Integer, db.ForeignKey('motoristas.id'), nullable=False)
    
    # Dados do veículo
    placa = db.Column(db.String(10), nullable=False)  # AAA-1234 ou AAA1A23
    tipo_veiculo_id = db.Column(db.Integer, db.ForeignKey('veiculos.id'), nullable=True)
    
    # Dados da carga
    tipo_carga = db.Column(db.String(50), nullable=False)  # Coleta / Coleta + Devolução / Devolução / Entrega
    empresa = db.Column(db.String(255), nullable=False)
    embarque_id = db.Column(db.Integer, db.ForeignKey('embarques.id'), nullable=True)
    
    # Horários de controle
    data_chegada = db.Column(db.Date, nullable=True)
    hora_chegada = db.Column(db.Time, nullable=True)
    data_entrada = db.Column(db.Date, nullable=True)
    hora_entrada = db.Column(db.Time, nullable=True)
    data_saida = db.Column(db.Date, nullable=True)
    hora_saida = db.Column(db.Time, nullable=True)
    
    # Timestamps
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)
    
    # ✅ NOVOS CAMPOS: Auditoria de usuários
    registrado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    atualizado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Relacionamentos
    tipo_veiculo = db.relationship('Veiculo', backref='registros_portaria')
    embarque = db.relationship('Embarque', backref='registros_portaria')
    registrado_por = db.relationship('Usuario', foreign_keys=[registrado_por_id], backref='registros_portaria_criados')
    atualizado_por = db.relationship('Usuario', foreign_keys=[atualizado_por_id], backref='registros_portaria_atualizados')
    
    def __repr__(self):
        return f'<ControlePortaria {self.motorista_obj.nome_completo} - {self.placa}>'
    
    @property
    def status(self):
        """Retorna o status atual do veículo"""
        if self.data_saida and self.hora_saida:
            return 'SAIU'
        elif self.data_entrada and self.hora_entrada:
            return 'DENTRO'
        elif self.data_chegada and self.hora_chegada:
            return 'AGUARDANDO'
        else:
            return 'PENDENTE'
    
    @property
    def pode_registrar_entrada(self):
        """Verifica se pode registrar entrada (deve ter chegada e não ter entrada)"""
        return (self.data_chegada and self.hora_chegada and 
                not (self.data_entrada and self.hora_entrada))
    
    @property
    def pode_registrar_saida(self):
        """Verifica se pode registrar saída (deve ter entrada e não ter saída)"""
        return (self.data_entrada and self.hora_entrada and 
                not (self.data_saida and self.hora_saida))
    
    def registrar_chegada(self):
        """Registra data e hora de chegada no timezone brasileiro"""
        agora = agora_utc_naive()
        self.data_chegada = agora.date()
        self.hora_chegada = agora.time()
    
    def registrar_entrada(self):
        """Registra data e hora de entrada no timezone brasileiro"""
        if not self.pode_registrar_entrada:
            raise ValueError("Não é possível registrar entrada sem chegada")
        agora = agora_utc_naive()
        self.data_entrada = agora.date()
        self.hora_entrada = agora.time()
    
    def registrar_saida(self):
        """Registra data e hora de saída no timezone brasileiro"""
        if not self.pode_registrar_saida:
            raise ValueError("Não é possível registrar saída sem entrada")
        agora = agora_utc_naive()
        self.data_saida = agora.date()
        self.hora_saida = agora.time()
    
    @staticmethod
    def veiculos_do_dia():
        """Retorna veículos do dia ordenados: primeiro DENTRO, depois AGUARDANDO, por último SAIU"""
        hoje = agora_utc_naive().date()
        
        # Veículos que chegaram hoje
        registros = ControlePortaria.query.filter(
            ControlePortaria.data_chegada == hoje
        ).join(Motorista).all()
        
        # Separa em três grupos por prioridade
        dentro = []       # Status DENTRO (entrada registrada, sem saída) - Prioridade 1
        aguardando = []   # Status AGUARDANDO (só chegada) - Prioridade 2
        saiu = []         # Status SAIU (já saíram) - Prioridade 3 (por último)
        
        for registro in registros:
            if registro.data_saida and registro.hora_saida:
                # Já saiu - vai por último
                saiu.append(registro)
            elif registro.data_entrada and registro.hora_entrada:
                # Está dentro - prioridade alta
                dentro.append(registro)
            else:
                # Aguardando entrada - prioridade média
                aguardando.append(registro)
        
        # Ordena cada grupo:
        # DENTRO: por entrada mais antiga (quem entrou primeiro)
        dentro.sort(key=lambda x: (x.data_entrada, x.hora_entrada))
        
        # AGUARDANDO: por chegada mais antiga (quem chegou primeiro)
        aguardando.sort(key=lambda x: (x.data_chegada, x.hora_chegada))
        
        # SAIU: por saída mais recente (quem saiu por último aparece primeiro no grupo)
        saiu.sort(key=lambda x: (x.data_saida, x.hora_saida), reverse=True)
        
        # Retorna na ordem: DENTRO + AGUARDANDO + SAIU
        return dentro + aguardando + saiu
    
    @staticmethod
    def historico(data_inicio=None, data_fim=None, embarque_numero=None, tem_embarque=None, 
                 tipo_carga=None, tipo_veiculo_id=None, status=None):
        """Retorna histórico de registros com filtros opcionais"""
        
        query = ControlePortaria.query.join(Motorista)
        
        # Filtros de data
        if data_inicio:
            query = query.filter(ControlePortaria.data_chegada >= data_inicio)
        if data_fim:
            query = query.filter(ControlePortaria.data_chegada <= data_fim)
        
        # Filtro por número do embarque
        if embarque_numero:
            query = query.join(Embarque).filter(
                Embarque.numero.like(f'%{embarque_numero}%')
            )
        
        # Filtro por presença de embarque
        if tem_embarque == 'sim':
            query = query.filter(ControlePortaria.embarque_id.isnot(None))
        elif tem_embarque == 'nao':
            query = query.filter(ControlePortaria.embarque_id.is_(None))
        
        # Filtro por tipo de carga
        if tipo_carga:
            query = query.filter(ControlePortaria.tipo_carga == tipo_carga)
        
        # Filtro por tipo de veículo
        if tipo_veiculo_id:
            query = query.filter(ControlePortaria.tipo_veiculo_id == tipo_veiculo_id)
        
        # Filtro por status (calculado dinamicamente)
        # Este será aplicado após a query base
        
        registros = query.order_by(
            ControlePortaria.data_chegada.desc(),
            ControlePortaria.hora_chegada.desc()
        ).all()
        
        # Aplicar filtro de status se especificado
        if status:
            registros = [r for r in registros if r.status == status]
        
        return registros

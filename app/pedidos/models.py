"""
Adapter para o modelo Pedido funcionando como VIEW
Data: 2025-01-29

Este arquivo substitui models.py quando Pedido se torna uma VIEW
"""

from app import db
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.hybrid import hybrid_property

class Pedido(db.Model):
    """
    Modelo Pedido que agora é uma VIEW agregando dados de Separacao
    """
    __tablename__ = 'pedidos'
    __table_args__ = {'info': {'is_view': True}}  # Marca como VIEW para SQLAlchemy
    
    # Campos mapeados da VIEW
    id = db.Column(db.Integer, primary_key=True)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True) #Vem de Separacao.separacao_lote_id
    num_pedido = db.Column(db.String(30), index=True) #Vem de Separacao.num_pedido
    data_pedido = db.Column(db.Date) #Vem de Separacao.data_pedido
    cnpj_cpf = db.Column(db.String(20)) #Vem de Separacao.cnpj_cpf
    raz_social_red = db.Column(db.String(255)) #Vem de Separacao.raz_social_red
    nome_cidade = db.Column(db.String(120)) #Vem de Separacao.nome_cidade
    cod_uf = db.Column(db.String(2)) #Vem de Separacao.cod_uf
    cidade_normalizada = db.Column(db.String(120)) 
    uf_normalizada = db.Column(db.String(2)) 
    codigo_ibge = db.Column(db.String(10))
    valor_saldo_total = db.Column(db.Float) #soma de Separacao.valor_saldo
    pallet_total = db.Column(db.Float) #soma de Separacao.pallet
    peso_total = db.Column(db.Float) #soma de Separacao.peso
    rota = db.Column(db.String(50)) #Vem de Separacao.rota
    sub_rota = db.Column(db.String(50)) #Vem de Separacao.sub_rota
    observ_ped_1 = db.Column(db.Text) #Vem de Separacao.observ_ped_1
    roteirizacao = db.Column(db.String(100)) #Vem de Separacao.roteirizacao
    expedicao = db.Column(db.Date) #Vem de Separacao.expedicao
    agendamento = db.Column(db.Date) #Vem de Separacao.agendamento
    protocolo = db.Column(db.String(50)) #Vem de Separacao.protocolo
    agendamento_confirmado = db.Column(db.Boolean, default=False) #Vem de Separacao.agendamento_confirmado

    # Campo de equipe de vendas (via JOIN com CarteiraPrincipal na VIEW)
    equipe_vendas = db.Column(db.String(100), nullable=True) #Vem de CarteiraPrincipal.equipe_vendas

    # Campos de transporte (virão NULL da VIEW, precisam JOIN com cotacao)
    transportadora = db.Column(db.String(100))
    valor_frete = db.Column(db.Float)
    valor_por_kg = db.Column(db.Float)
    nome_tabela = db.Column(db.String(100))
    modalidade = db.Column(db.String(50))
    melhor_opcao = db.Column(db.String(100))
    valor_melhor_opcao = db.Column(db.Float)
    lead_time = db.Column(db.Integer)
    
    # Campos de status e NF
    data_embarque = db.Column(db.Date)
    nf = db.Column(db.String(20))
    status = db.Column(db.String(50), default='ABERTO')
    nf_cd = db.Column(db.Boolean, default=False)
    pedido_cliente = db.Column(db.String(100), nullable=True)
    
    # Controle de impressão
    separacao_impressa = db.Column(db.Boolean, default=False, nullable=False)
    separacao_impressa_em = db.Column(db.DateTime, nullable=True)
    separacao_impressa_por = db.Column(db.String(100), nullable=True)
    
    # Relacionamentos (via JOIN quando necessário)
    cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    # Timestamps
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def status_calculado(self):
        """
        Calcula o status do pedido baseado no estado atual:
        - NF no CD: Flag nf_cd é True (NF voltou para o CD)
        - FATURADO: Tem NF preenchida e não está no CD
        - EMBARCADO: Tem data de embarque mas não tem NF
        - COTADO: Tem cotação_id mas não está embarcado
        - ABERTO: Não tem cotação
        """
        # NOVO: Primeiro verifica se a NF está no CD
        if getattr(self, 'nf_cd', False):
            return 'NF no CD'
        elif self.nf and self.nf.strip():
            return 'FATURADO'
        elif self.cotacao_id:
            return 'COTADO'
        else:
            return 'ABERTO'
    
    def __repr__(self):
        return f'<Pedido {self.num_pedido} - Lote: {self.separacao_lote_id}>'
    
    @classmethod
    def atualizar_status(cls, separacao_lote_id, num_pedido, novo_status):
        """
        Método helper para atualizar status via UPDATE em Separacao
        """
        sql = text("""
            UPDATE separacao 
            SET status = :status
            WHERE separacao_lote_id = :lote_id
            AND num_pedido = :num_pedido
        """)
        
        db.session.execute(sql, {
            'status': novo_status,
            'lote_id': separacao_lote_id,
            'num_pedido': num_pedido
        })
        db.session.commit()
    
    @classmethod
    def atualizar_nf_cd(cls, separacao_lote_id, num_pedido, nf_cd):
        """
        Método helper para atualizar flag nf_cd via UPDATE em Separacao
        """
        sql = text("""
            UPDATE separacao 
            SET nf_cd = :nf_cd
            WHERE separacao_lote_id = :lote_id
            AND num_pedido = :num_pedido
        """)
        
        db.session.execute(sql, {
            'nf_cd': nf_cd,
            'lote_id': separacao_lote_id,
            'num_pedido': num_pedido
        })
        db.session.commit()
    
    def save(self):
        """
        Override save para atualizar Separacao em vez de Pedido
        """
        # Atualiza campos em Separacao
        sql = text("""
            UPDATE separacao 
            SET 
                status = :status,
                nf_cd = :nf_cd,
                data_embarque = :data_embarque,
                agendamento = :agendamento,
                protocolo = :protocolo,
                agendamento_confirmado = :agendamento_confirmado,
                separacao_impressa = :separacao_impressa,
                separacao_impressa_em = :separacao_impressa_em,
                separacao_impressa_por = :separacao_impressa_por
            WHERE separacao_lote_id = :lote_id
            AND num_pedido = :num_pedido
        """)
        
        db.session.execute(sql, {
            'status': self.status,
            'nf_cd': self.nf_cd,
            'data_embarque': self.data_embarque,
            'agendamento': self.agendamento,
            'protocolo': self.protocolo,
            'agendamento_confirmado': self.agendamento_confirmado,
            'separacao_impressa': self.separacao_impressa,
            'separacao_impressa_em': self.separacao_impressa_em,
            'separacao_impressa_por': self.separacao_impressa_por,
            'lote_id': self.separacao_lote_id,
            'num_pedido': self.num_pedido
        })
        db.session.commit()
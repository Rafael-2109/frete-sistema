"""
Modelos do banco de dados para integração com portais
"""

from app import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func

class PortalIntegracao(db.Model):
    """Tabela principal de integrações com portais"""
    __tablename__ = 'portal_integracoes'
    
    id = db.Column(db.Integer, primary_key=True)
    portal = db.Column(db.String(50), nullable=False)
    lote_id = db.Column(db.String(50), nullable=False, index=True)
    tipo_lote = db.Column(db.String(20), nullable=False)  # separacao, pre_separacao
    
    # Protocolo pode ser NULL inicialmente, UNIQUE permite múltiplos NULL
    protocolo = db.Column(db.String(100), unique=True, index=True)
    status = db.Column(db.String(50), default='aguardando', index=True)
    job_id = db.Column(db.String(100), index=True)  # ID do job no Redis Queue
    data_solicitacao = db.Column(db.DateTime)
    data_confirmacao = db.Column(db.DateTime)
    data_agendamento = db.Column(db.Date)
    hora_agendamento = db.Column(db.Time)
    
    # Controle
    usuario_solicitante = db.Column(db.String(100))
    navegador_sessao_id = db.Column(db.String(100))
    tentativas = db.Column(db.Integer, default=0)
    ultimo_erro = db.Column(db.Text)
    
    # JSON logs para PostgreSQL
    dados_enviados = db.Column(JSONB)
    resposta_portal = db.Column(JSONB)
    
    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    logs = db.relationship('PortalLog', backref='integracao', lazy='dynamic', cascade='all, delete-orphan')
    
    @classmethod
    def criar_ou_atualizar(cls, dados):
        """
        Cria nova integração ou atualiza existente se protocolo já existe.
        Útil quando portal pode regenerar protocolos.
        """
        try:
            # Tentar inserir
            nova_integracao = cls(**dados)
            db.session.add(nova_integracao)
            db.session.commit()
            return nova_integracao, 'created'
            
        except db.exc.IntegrityError as e:
            db.session.rollback()
            
            # Se violou unique de protocolo, atualizar registro existente
            if 'protocolo' in str(e):
                integracao_existente = cls.query.filter_by(
                    protocolo=dados.get('protocolo')
                ).first()
                
                if integracao_existente:
                    # Atualizar campos permitidos
                    campos_atualizaveis = [
                        'status', 'data_confirmacao', 'data_agendamento',
                        'hora_agendamento', 'resposta_portal', 'atualizado_em'
                    ]
                    
                    for campo in campos_atualizaveis:
                        if campo in dados:
                            setattr(integracao_existente, campo, dados[campo])
                    
                    db.session.commit()
                    return integracao_existente, 'updated'
            
            raise e
    
    @classmethod
    def upsert(cls, **kwargs):
        """
        Implementação usando PostgreSQL UPSERT (INSERT ... ON CONFLICT)
        Mais eficiente que try/except
        """
        stmt = insert(cls).values(**kwargs)
        stmt = stmt.on_conflict_do_update(
            index_elements=['protocolo'],
            set_={
                'status': stmt.excluded.status,
                'data_confirmacao': stmt.excluded.data_confirmacao,
                'data_agendamento': stmt.excluded.data_agendamento,
                'hora_agendamento': stmt.excluded.hora_agendamento,
                'resposta_portal': stmt.excluded.resposta_portal,
                'atualizado_em': func.now()
            }
        )
        result = db.session.execute(stmt)
        db.session.commit()
        return result
    
    def __repr__(self):
        return f"<PortalIntegracao {self.portal} - {self.lote_id} - {self.status}>"


class PortalConfiguracao(db.Model):
    """Configurações dos portais por cliente"""
    __tablename__ = 'portal_configuracoes'
    
    id = db.Column(db.Integer, primary_key=True)
    portal = db.Column(db.String(50), nullable=False)
    cnpj_cliente = db.Column(db.String(20))
    url_portal = db.Column(db.String(255))
    url_login = db.Column(db.String(255))
    usuario = db.Column(db.String(100))
    senha_criptografada = db.Column(db.String(255))
    totp_secret = db.Column(db.String(100))  # Para 2FA automático
    instrucoes_acesso = db.Column(db.Text)
    seletores_css = db.Column(JSONB)  # Seletores para automação
    login_indicators = db.Column(JSONB)  # Seletores para detectar página de login
    ativo = db.Column(db.Boolean, default=True, index=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('portal', 'cnpj_cliente', name='portal_cliente_unique'),
    )
    
    def __repr__(self):
        return f"<PortalConfiguracao {self.portal} - {self.cnpj_cliente}>"


class PortalLog(db.Model):
    """Log de execuções das integrações"""
    __tablename__ = 'portal_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    integracao_id = db.Column(db.Integer, db.ForeignKey('portal_integracoes.id', ondelete='CASCADE'), index=True)
    acao = db.Column(db.String(100))
    sucesso = db.Column(db.Boolean)
    mensagem = db.Column(db.Text)
    screenshot_path = db.Column(db.String(500))
    dados_contexto = db.Column(JSONB)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<PortalLog {self.acao} - {self.sucesso}>"


class PortalSessao(db.Model):
    """Tabela para gerenciar sessões salvas"""
    __tablename__ = 'portal_sessoes'
    
    id = db.Column(db.Integer, primary_key=True)
    portal = db.Column(db.String(50), nullable=False, index=True)
    usuario = db.Column(db.String(100))
    cookies_criptografados = db.Column(db.Text)
    storage_state = db.Column(JSONB)
    valido_ate = db.Column(db.DateTime, index=True)
    ultima_utilizacao = db.Column(db.DateTime)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PortalSessao {self.portal} - {self.usuario}>"
"""
Modelos para gerenciamento de emails anexados às despesas de frete
"""
from datetime import datetime
from app import db
from app.utils.timezone import agora_utc_naive


class EmailAnexado(db.Model):
    """
    Modelo para armazenar referências de emails anexados às despesas
    """
    __tablename__ = 'emails_anexados'
    
    id = db.Column(db.Integer, primary_key=True)
    despesa_extra_id = db.Column(db.Integer, db.ForeignKey('despesas_extras.id'), nullable=False)
    
    # Informações do arquivo
    nome_arquivo = db.Column(db.String(255), nullable=False)  # Nome original do arquivo .msg
    caminho_s3 = db.Column(db.String(500), nullable=False)    # Caminho completo no S3
    tamanho_bytes = db.Column(db.Integer)                     # Tamanho do arquivo
    
    # Metadados do email (extraídos do .msg)
    remetente = db.Column(db.String(255))
    destinatarios = db.Column(db.Text)  # JSON com lista de destinatários (TO)
    cc = db.Column(db.Text)  # JSON com lista de destinatários em cópia (CC)
    bcc = db.Column(db.Text)  # JSON com lista de destinatários em cópia oculta (BCC)
    assunto = db.Column(db.String(500))
    data_envio = db.Column(db.DateTime)
    tem_anexos = db.Column(db.Boolean, default=False)
    qtd_anexos = db.Column(db.Integer, default=0)
    
    # Preview do conteúdo
    conteudo_preview = db.Column(db.Text)  # Primeiros 500 caracteres do email
    
    # Controle
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)
    
    # Relacionamento
    despesa_extra = db.relationship('DespesaExtra', backref='emails_anexados')
    
    def __repr__(self):
        return f'<EmailAnexado {self.nome_arquivo} - Despesa {self.despesa_extra_id}>'
    
    def to_dict(self):
        """Retorna dicionário com dados do email para API"""
        return {
            'id': self.id,
            'nome_arquivo': self.nome_arquivo,
            'remetente': self.remetente,
            'assunto': self.assunto,
            'data_envio': self.data_envio.isoformat() if self.data_envio else None,
            'tem_anexos': self.tem_anexos,
            'qtd_anexos': self.qtd_anexos,
            'tamanho_kb': round(self.tamanho_bytes / 1024, 2) if self.tamanho_bytes else 0,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None
        }
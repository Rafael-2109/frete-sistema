"""
Models para Correção de Datas - NFs de Crédito
===============================================

Problema identificado: Script alterou account_move.date para invoice_date
quando deveria manter a data de lançamento original.

Autor: Sistema de Fretes - Análise CIEL IT
Data: 11/12/2025
"""

from app import db
from datetime import datetime
from sqlalchemy import Index, UniqueConstraint


class CorrecaoDataNFCredito(db.Model):
    """
    Histórico de correções de datas de lançamento em NFs de Crédito.

    Esta tabela armazena:
    - Diagnóstico: NFs identificadas com problema
    - Correção: Registro de cada correção executada
    - Exportação: Dados para relatório Excel
    """
    __tablename__ = 'correcao_data_nf_credito'

    id = db.Column(db.Integer, primary_key=True)

    # Identificação do documento no Odoo
    odoo_move_id = db.Column(db.Integer, nullable=False, index=True)
    nome_documento = db.Column(db.String(50), nullable=False)  # Ex: RDVEND/2024/00621
    numero_nf = db.Column(db.String(20), nullable=True)  # Ex: 107863

    # Parceiro
    odoo_partner_id = db.Column(db.Integer, nullable=True)
    nome_parceiro = db.Column(db.String(255), nullable=True)

    # Datas do documento (account_move)
    data_emissao = db.Column(db.Date, nullable=False)  # invoice_date - NÃO ALTERADO
    data_lancamento_antes = db.Column(db.Date, nullable=False)  # date ANTES da correção
    data_lancamento_linhas_antes = db.Column(db.Date, nullable=True)  # date das lines ANTES
    data_correta = db.Column(db.Date, nullable=False)  # Data que DEVERIA estar

    # Resultado da correção
    data_lancamento_depois = db.Column(db.Date, nullable=True)  # date DEPOIS da correção
    data_lancamento_linhas_depois = db.Column(db.Date, nullable=True)  # date das lines DEPOIS

    # Status
    status = db.Column(db.String(20), default='pendente', nullable=False, index=True)
    # Valores: pendente, corrigido, erro, ignorado

    erro_mensagem = db.Column(db.Text, nullable=True)

    # Auditoria
    diagnosticado_em = db.Column(db.DateTime, default=datetime.utcnow)
    corrigido_em = db.Column(db.DateTime, nullable=True)
    corrigido_por = db.Column(db.String(100), nullable=True)

    # Controle de exportação
    exportado_em = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        Index('idx_correcao_status', 'status'),
        Index('idx_correcao_data_emissao', 'data_emissao'),
        UniqueConstraint('odoo_move_id', name='uq_correcao_odoo_move_id'),
    )

    def __repr__(self):
        return f'<CorrecaoDataNFCredito {self.nome_documento} ({self.status})>'

    def to_dict(self):
        return {
            'id': self.id,
            'odoo_move_id': self.odoo_move_id,
            'nome_documento': self.nome_documento,
            'numero_nf': self.numero_nf,
            'nome_parceiro': self.nome_parceiro,
            'data_emissao': self.data_emissao.isoformat() if self.data_emissao else None,
            'data_lancamento_antes': self.data_lancamento_antes.isoformat() if self.data_lancamento_antes else None,
            'data_lancamento_linhas_antes': self.data_lancamento_linhas_antes.isoformat() if self.data_lancamento_linhas_antes else None,
            'data_correta': self.data_correta.isoformat() if self.data_correta else None,
            'data_lancamento_depois': self.data_lancamento_depois.isoformat() if self.data_lancamento_depois else None,
            'status': self.status,
            'erro_mensagem': self.erro_mensagem,
            'diagnosticado_em': self.diagnosticado_em.isoformat() if self.diagnosticado_em else None,
            'corrigido_em': self.corrigido_em.isoformat() if self.corrigido_em else None,
            'corrigido_por': self.corrigido_por
        }

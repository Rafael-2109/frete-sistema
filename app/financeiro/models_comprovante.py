# -*- coding: utf-8 -*-
"""
Modelos de Comprovante de Pagamento e Lançamento
=================================================

ComprovantePagamentoBoleto: Comprovantes extraídos de PDFs do Sicoob.
LancamentoComprovante: Resultado do match entre comprovante e fatura Odoo.
"""

from app import db
from app.utils.timezone import agora_brasil


class ComprovantePagamentoBoleto(db.Model):
    """Comprovante de pagamento de boleto bancário (SICOOB)."""

    __tablename__ = 'comprovante_pagamento_boleto'

    id = db.Column(db.Integer, primary_key=True)

    # 🔑 CHAVE ÚNICA - Número do agendamento bancário
    numero_agendamento = db.Column(
        db.String(50), nullable=False, unique=True, index=True
    )

    # 📋 CABEÇALHO DO COMPROVANTE
    data_comprovante = db.Column(db.Date, nullable=True)
    cooperativa = db.Column(db.String(255), nullable=True)
    conta = db.Column(db.String(50), nullable=True)
    cliente = db.Column(db.String(255), nullable=True)
    linha_digitavel = db.Column(db.String(255), nullable=True)
    numero_documento = db.Column(db.String(100), nullable=True)
    nosso_numero = db.Column(db.String(100), nullable=True)
    instituicao_emissora = db.Column(db.String(100), nullable=True)
    tipo_documento = db.Column(db.String(100), nullable=True)

    # 🏢 BENEFICIÁRIO (quem recebe o pagamento)
    beneficiario_razao_social = db.Column(db.String(255), nullable=True)
    beneficiario_nome_fantasia = db.Column(db.String(255), nullable=True)
    beneficiario_cnpj_cpf = db.Column(db.String(50), nullable=True)

    # 💰 PAGADOR (quem efetuou o pagamento)
    pagador_razao_social = db.Column(db.String(255), nullable=True)
    pagador_nome_fantasia = db.Column(db.String(255), nullable=True)
    pagador_cnpj_cpf = db.Column(db.String(50), nullable=True)

    # 📅 DATAS
    data_realizado = db.Column(db.String(50), nullable=True)  # "02/01/2026 às 17:08:48"
    data_pagamento = db.Column(db.Date, nullable=True)
    data_vencimento = db.Column(db.Date, nullable=True)

    # 💵 VALORES (Numeric para precisão monetária)
    valor_documento = db.Column(db.Numeric(15, 2), nullable=True)
    valor_desconto_abatimento = db.Column(db.Numeric(15, 2), nullable=True)
    valor_juros_multa = db.Column(db.Numeric(15, 2), nullable=True)
    valor_pago = db.Column(db.Numeric(15, 2), nullable=True)

    # 📊 STATUS
    situacao = db.Column(db.String(50), nullable=True)
    autenticacao = db.Column(db.String(255), nullable=True)

    # 📁 METADADOS DA IMPORTAÇÃO
    arquivo_origem = db.Column(db.String(255), nullable=True)
    pagina_origem = db.Column(db.Integer, nullable=True)
    importado_por = db.Column(db.String(100), nullable=True)
    importado_em = db.Column(db.DateTime, default=agora_brasil)

    # 📦 S3 — Path do PDF original no storage
    # 1 PDF pode gerar N comprovantes — todos compartilham o mesmo path
    arquivo_s3_path = db.Column(db.String(500), nullable=True)

    # 🔗 VÍNCULO COM EXTRATO OFX
    ofx_fitid = db.Column(db.String(100), nullable=True, index=True)
    ofx_checknum = db.Column(db.String(50), nullable=True, index=True)
    ofx_memo = db.Column(db.String(500), nullable=True)
    ofx_valor = db.Column(db.Numeric(15, 2), nullable=True)
    ofx_data = db.Column(db.Date, nullable=True)
    ofx_arquivo_origem = db.Column(db.String(255), nullable=True)

    # 🔗 VÍNCULO COM ODOO (account.bank.statement.line)
    odoo_statement_line_id = db.Column(db.Integer, nullable=True, index=True)
    odoo_move_id = db.Column(db.Integer, nullable=True)
    odoo_statement_id = db.Column(db.Integer, nullable=True)
    odoo_journal_id = db.Column(db.Integer, nullable=True)
    odoo_is_reconciled = db.Column(db.Boolean, nullable=True)
    odoo_vinculado_em = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index('idx_comp_beneficiario_cnpj', 'beneficiario_cnpj_cpf'),
        db.Index('idx_comp_pagador_cnpj', 'pagador_cnpj_cpf'),
        db.Index('idx_comp_data_pagamento', 'data_pagamento'),
        db.Index('idx_comp_data_vencimento', 'data_vencimento'),
        db.Index('idx_comp_ofx_fitid', 'ofx_fitid'),
        db.Index('idx_comp_ofx_checknum', 'ofx_checknum'),
        db.Index('idx_comp_odoo_statement_line', 'odoo_statement_line_id'),
    )

    def __repr__(self):
        return (
            f'<ComprovantePagamentoBoleto {self.numero_agendamento} '
            f'| {self.beneficiario_razao_social} '
            f'| R$ {self.valor_pago}>'
        )

    def to_dict(self):
        """Serializa para dicionário (uso em APIs JSON)."""
        return {
            'id': self.id,
            'numero_agendamento': self.numero_agendamento,
            'data_comprovante': self.data_comprovante.strftime('%d/%m/%Y') if self.data_comprovante else None,
            'cooperativa': self.cooperativa,
            'conta': self.conta,
            'cliente': self.cliente,
            'linha_digitavel': self.linha_digitavel,
            'numero_documento': self.numero_documento,
            'nosso_numero': self.nosso_numero,
            'instituicao_emissora': self.instituicao_emissora,
            'tipo_documento': self.tipo_documento,
            'beneficiario_razao_social': self.beneficiario_razao_social,
            'beneficiario_nome_fantasia': self.beneficiario_nome_fantasia,
            'beneficiario_cnpj_cpf': self.beneficiario_cnpj_cpf,
            'pagador_razao_social': self.pagador_razao_social,
            'pagador_nome_fantasia': self.pagador_nome_fantasia,
            'pagador_cnpj_cpf': self.pagador_cnpj_cpf,
            'data_realizado': self.data_realizado,
            'data_pagamento': self.data_pagamento.strftime('%d/%m/%Y') if self.data_pagamento else None,
            'data_vencimento': self.data_vencimento.strftime('%d/%m/%Y') if self.data_vencimento else None,
            'valor_documento': float(self.valor_documento) if self.valor_documento else None,
            'valor_desconto_abatimento': float(self.valor_desconto_abatimento) if self.valor_desconto_abatimento else None,
            'valor_juros_multa': float(self.valor_juros_multa) if self.valor_juros_multa else None,
            'valor_pago': float(self.valor_pago) if self.valor_pago else None,
            'situacao': self.situacao,
            'autenticacao': self.autenticacao,
            'arquivo_origem': self.arquivo_origem,
            'pagina_origem': self.pagina_origem,
            'importado_por': self.importado_por,
            'importado_em': self.importado_em.strftime('%d/%m/%Y %H:%M') if self.importado_em else None,
            'arquivo_s3_path': self.arquivo_s3_path,
            # Vínculo OFX
            'ofx_fitid': self.ofx_fitid,
            'ofx_checknum': self.ofx_checknum,
            'ofx_memo': self.ofx_memo,
            'ofx_valor': float(self.ofx_valor) if self.ofx_valor else None,
            'ofx_data': self.ofx_data.strftime('%d/%m/%Y') if self.ofx_data else None,
            'ofx_arquivo_origem': self.ofx_arquivo_origem,
            # Vínculo Odoo
            'odoo_statement_line_id': self.odoo_statement_line_id,
            'odoo_move_id': self.odoo_move_id,
            'odoo_statement_id': self.odoo_statement_id,
            'odoo_journal_id': self.odoo_journal_id,
            'odoo_is_reconciled': self.odoo_is_reconciled,
            'odoo_vinculado_em': self.odoo_vinculado_em.strftime('%d/%m/%Y %H:%M') if self.odoo_vinculado_em else None,
        }


class LancamentoComprovante(db.Model):
    """
    Resultado de match entre ComprovantePagamentoBoleto e fatura de fornecedor no Odoo.

    Armazena o resultado do matching com score de confiança,
    dados da fatura encontrada e status de confirmação.

    Status: PENDENTE → CONFIRMADO → LANCADO / REJEITADO
    """

    __tablename__ = 'lancamento_comprovante'

    id = db.Column(db.Integer, primary_key=True)

    # 🔗 FK para ComprovantePagamentoBoleto
    comprovante_id = db.Column(
        db.Integer,
        db.ForeignKey('comprovante_pagamento_boleto.id'),
        nullable=False, index=True
    )

    # 📄 Dados da fatura encontrada no Odoo
    odoo_move_line_id = db.Column(db.Integer, nullable=True, index=True)    # account.move.line ID
    odoo_move_id = db.Column(db.Integer, nullable=True)                     # account.move ID
    odoo_move_name = db.Column(db.String(255), nullable=True)               # Nome (ENTSI/2025/...)
    odoo_partner_id = db.Column(db.Integer, nullable=True)                  # res.partner ID
    odoo_partner_name = db.Column(db.String(255), nullable=True)            # Nome fornecedor
    odoo_partner_cnpj = db.Column(db.String(20), nullable=True)             # CNPJ do partner
    odoo_company_id = db.Column(db.Integer, nullable=True)                  # company_id (1,3,4,5)

    # 🔢 NF e parcela extraídos do numero_documento
    nf_numero = db.Column(db.String(50), nullable=True)
    parcela = db.Column(db.Integer, nullable=True)

    # 💵 Valores Odoo
    odoo_valor_original = db.Column(db.Numeric(15, 2), nullable=True)       # credit da line
    odoo_valor_residual = db.Column(db.Numeric(15, 2), nullable=True)       # amount_residual
    odoo_valor_recalculado = db.Column(db.Numeric(15, 2), nullable=True)    # valor após recálculo
    odoo_vencimento = db.Column(db.Date, nullable=True)                     # date_maturity

    # 📊 Resultado do matching
    match_score = db.Column(db.Integer, nullable=False, default=0)          # 0-100
    match_criterios = db.Column(db.Text, nullable=True)                     # JSON com critérios
    diferenca_valor = db.Column(db.Numeric(15, 2), nullable=True)           # valor_pago - odoo_valor

    # 🏦 Flag: beneficiário é financeira (não é fornecedor direto)
    beneficiario_e_financeira = db.Column(db.Boolean, default=False)

    # 📋 Status do lançamento
    status = db.Column(db.String(20), default='PENDENTE', nullable=False, index=True)

    # 🕐 Auditoria
    criado_em = db.Column(db.DateTime, default=agora_brasil)
    confirmado_em = db.Column(db.DateTime, nullable=True)
    confirmado_por = db.Column(db.String(100), nullable=True)
    rejeitado_em = db.Column(db.DateTime, nullable=True)
    rejeitado_por = db.Column(db.String(100), nullable=True)
    motivo_rejeicao = db.Column(db.Text, nullable=True)

    # 🚀 Dados do lançamento no Odoo (preenchidos na transição CONFIRMADO → LANCADO)
    lancado_em = db.Column(db.DateTime, nullable=True)
    lancado_por = db.Column(db.String(100), nullable=True)
    odoo_payment_id = db.Column(db.Integer, nullable=True)              # account.payment ID criado
    odoo_payment_name = db.Column(db.String(100), nullable=True)        # Nome do payment (PAGO/2026/...)
    odoo_debit_line_id = db.Column(db.Integer, nullable=True)           # Linha débito do payment
    odoo_credit_line_id = db.Column(db.Integer, nullable=True)          # Linha crédito do payment
    odoo_full_reconcile_id = db.Column(db.Integer, nullable=True)       # Full reconcile título
    odoo_full_reconcile_extrato_id = db.Column(db.Integer, nullable=True)  # Full reconcile extrato
    erro_lancamento = db.Column(db.Text, nullable=True)                 # Mensagem de erro se falhar

    # Relationship
    comprovante = db.relationship('ComprovantePagamentoBoleto', backref='lancamentos')

    __table_args__ = (
        db.Index('idx_lanc_comp_status', 'comprovante_id', 'status'),
        db.Index('idx_lanc_odoo_move_line', 'odoo_move_line_id'),
        db.Index('idx_lanc_nf_parcela', 'nf_numero', 'parcela'),
    )

    def __repr__(self):
        return (
            f'<LancamentoComprovante {self.id} '
            f'| comp={self.comprovante_id} '
            f'| score={self.match_score} '
            f'| status={self.status}>'
        )

    def to_dict(self):
        """Serializa para dicionário (uso em APIs JSON)."""
        return {
            'id': self.id,
            'comprovante_id': self.comprovante_id,
            # Dados Odoo
            'odoo_move_line_id': self.odoo_move_line_id,
            'odoo_move_id': self.odoo_move_id,
            'odoo_move_name': self.odoo_move_name,
            'odoo_partner_id': self.odoo_partner_id,
            'odoo_partner_name': self.odoo_partner_name,
            'odoo_partner_cnpj': self.odoo_partner_cnpj,
            'odoo_company_id': self.odoo_company_id,
            # NF e parcela
            'nf_numero': self.nf_numero,
            'parcela': self.parcela,
            # Valores
            'odoo_valor_original': float(self.odoo_valor_original) if self.odoo_valor_original else None,
            'odoo_valor_residual': float(self.odoo_valor_residual) if self.odoo_valor_residual else None,
            'odoo_valor_recalculado': float(self.odoo_valor_recalculado) if self.odoo_valor_recalculado else None,
            'odoo_vencimento': self.odoo_vencimento.strftime('%d/%m/%Y') if self.odoo_vencimento else None,
            # Match
            'match_score': self.match_score,
            'match_criterios': self.match_criterios,
            'diferenca_valor': float(self.diferenca_valor) if self.diferenca_valor else None,
            'beneficiario_e_financeira': self.beneficiario_e_financeira,
            # Status
            'status': self.status,
            # Auditoria
            'criado_em': self.criado_em.strftime('%d/%m/%Y %H:%M') if self.criado_em else None,
            'confirmado_em': self.confirmado_em.strftime('%d/%m/%Y %H:%M') if self.confirmado_em else None,
            'confirmado_por': self.confirmado_por,
            'rejeitado_em': self.rejeitado_em.strftime('%d/%m/%Y %H:%M') if self.rejeitado_em else None,
            'rejeitado_por': self.rejeitado_por,
            'motivo_rejeicao': self.motivo_rejeicao,
            # Lançamento Odoo
            'lancado_em': self.lancado_em.strftime('%d/%m/%Y %H:%M') if self.lancado_em else None,
            'lancado_por': self.lancado_por,
            'odoo_payment_id': self.odoo_payment_id,
            'odoo_payment_name': self.odoo_payment_name,
            'odoo_debit_line_id': self.odoo_debit_line_id,
            'odoo_credit_line_id': self.odoo_credit_line_id,
            'odoo_full_reconcile_id': self.odoo_full_reconcile_id,
            'odoo_full_reconcile_extrato_id': self.odoo_full_reconcile_extrato_id,
            'erro_lancamento': self.erro_lancamento,
        }

"""
Modelos Operacionais - Sistema MotoCHEFE
CustosOperacionais: Valores fixos (montagem, movimentação, comissão)
DespesaMensal: Despesas mensais (salários, aluguel, etc)
"""
from app import db
from datetime import datetime, date


class CustosOperacionais(db.Model):
    """
    Custos operacionais fixos
    Sistema sempre usa registro com ativo=True e data_vigencia_fim=NULL

    NOTA: custo_movimentacao e valor_comissao_fixa foram movidos para EquipeVendasMoto
    """
    __tablename__ = 'custos_operacionais'

    # PK
    id = db.Column(db.Integer, primary_key=True)

    # Custos fixos
    custo_montagem = db.Column(db.Numeric(15, 2), nullable=False, default=0)

    # Vigência
    data_vigencia_inicio = db.Column(db.Date, nullable=False, default=date.today)
    data_vigencia_fim = db.Column(db.Date, nullable=True)

    # Status
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<CustosOperacionais Vigência:{self.data_vigencia_inicio} Ativo:{self.ativo}>'

    @classmethod
    def get_custos_vigentes(cls):
        """Retorna custos atualmente em vigor"""
        return cls.query.filter_by(
            ativo=True,
            data_vigencia_fim=None
        ).first()


class DespesaMensal(db.Model):
    """
    Despesas mensais operacionais
    Usadas no cálculo de margem mensal
    """
    __tablename__ = 'despesa_mensal'

    # PK
    id = db.Column(db.Integer, primary_key=True)

    # Identificação
    tipo_despesa = db.Column(db.String(50), nullable=False, index=True)
    # Valores comuns: 'SALARIO', 'ALUGUEL', 'ENERGIA', 'AGUA', 'INTERNET', 'MARKETING', etc
    descricao = db.Column(db.String(255), nullable=True)

    # Valores
    valor = db.Column(db.Numeric(15, 2), nullable=False)

    # Competência
    mes_competencia = db.Column(db.Integer, nullable=False)  # 1-12
    ano_competencia = db.Column(db.Integer, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=True)

    # Pagamento
    data_pagamento = db.Column(db.Date, nullable=True)
    valor_pago = db.Column(db.Numeric(15, 2), default=0)
    empresa_pagadora_id = db.Column(db.Integer, db.ForeignKey('empresa_venda_moto.id'), nullable=True, index=True)
    # Empresa que pagou a despesa

    # Status
    status = db.Column(db.String(20), default='PENDENTE', nullable=False, index=True)
    # Valores: PENDENTE, PAGO, ATRASADO, CANCELADO

    # Relacionamentos
    empresa_pagadora = db.relationship('EmpresaVendaMoto', backref='despesas_pagas')

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<DespesaMensal {self.tipo_despesa} {self.mes_competencia}/{self.ano_competencia}>'

    @property
    def atrasada(self):
        """Verifica se despesa está vencida"""
        if self.status == 'PAGO' or not self.data_vencimento:
            return False
        return self.data_vencimento < date.today()

    @property
    def saldo_aberto(self):
        """Retorna saldo ainda não pago"""
        return self.valor - (self.valor_pago or 0)

    @classmethod
    def total_mes(cls, mes, ano):
        """Retorna total de despesas de um mês"""
        total = db.session.query(
            db.func.sum(cls.valor)
        ).filter_by(
            mes_competencia=mes,
            ano_competencia=ano,
            ativo=True
        ).scalar()
        return total or 0

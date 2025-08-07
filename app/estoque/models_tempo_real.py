"""
Modelos para Sistema de Estoque em Tempo Real com Projeção Futura
Performance-focused: Consultas < 100ms
"""

from datetime import datetime
from decimal import Decimal
from app import db
from app.utils.timezone import agora_brasil


class EstoqueTempoReal(db.Model):
    """
    Tabela de saldo atual em tempo real para cada produto.
    Atualizada por triggers de MovimentacaoEstoque.
    """
    __tablename__ = 'estoque_tempo_real'
    
    # Chave primária
    cod_produto = db.Column(db.String(50), primary_key=True, index=True)
    nome_produto = db.Column(db.String(200), nullable=False)
    
    # Saldo atual em tempo real
    saldo_atual = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    
    # Controle para job de fallback (recalcular 10 mais antigos)
    atualizado_em = db.Column(
        db.DateTime, 
        nullable=False, 
        default=agora_brasil, 
        onupdate=agora_brasil,
        index=True
    )
    
    # Projeção calculada
    menor_estoque_d7 = db.Column(db.Numeric(15, 3), nullable=True)
    dia_ruptura = db.Column(db.Date, nullable=True)
    
    __table_args__ = (
        db.Index('idx_estoque_tempo_real_atualizado', 'atualizado_em'),
    )
    
    def __repr__(self):
        return f'<EstoqueTempoReal {self.cod_produto}: {self.saldo_atual}>'
    
    def to_dict(self):
        """Serialização para API com performance otimizada"""
        return {
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'saldo_atual': float(self.saldo_atual),
            'menor_estoque_d7': float(self.menor_estoque_d7) if self.menor_estoque_d7 else None,
            'dia_ruptura': self.dia_ruptura.isoformat() if self.dia_ruptura else None,
            'atualizado_em': self.atualizado_em.isoformat()
        }


class MovimentacaoPrevista(db.Model):
    """
    Tabela de movimentações previstas (cumulativas por produto/data).
    Alimentada por PreSeparacao, Separacao, ProgramacaoProducao.
    """
    __tablename__ = 'movimentacao_prevista'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Identificação
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    data_prevista = db.Column(db.Date, nullable=False, index=True)
    
    # Quantidades CUMULATIVAS (soma de todas as origens)
    entrada_prevista = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    saida_prevista = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    
    # Índice composto para consultas rápidas
    __table_args__ = (
        db.Index('idx_mov_prevista_produto_data', 'cod_produto', 'data_prevista'),
        db.UniqueConstraint('cod_produto', 'data_prevista', name='uq_produto_data'),
    )
    
    def __repr__(self):
        return f'<MovPrevista {self.cod_produto} {self.data_prevista}: +{self.entrada_prevista}/-{self.saida_prevista}>'
    
    def to_dict(self):
        """Serialização para API"""
        return {
            'data': self.data_prevista.isoformat(),
            'entrada': float(self.entrada_prevista),
            'saida': float(self.saida_prevista),
            'saldo_dia': float(self.entrada_prevista - self.saida_prevista)
        }
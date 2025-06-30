from app import db
from datetime import datetime
from app.utils.timezone import agora_brasil

class MovimentacaoEstoque(db.Model):
    """
    Modelo para controle das movimentações de estoque
    """
    __tablename__ = 'movimentacao_estoque'

    id = db.Column(db.Integer, primary_key=True)
    
    # Dados do produto
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(200), nullable=False)
    
    # Dados da movimentação
    data_movimentacao = db.Column(db.Date, nullable=False, index=True)
    tipo_movimentacao = db.Column(db.String(50), nullable=False, index=True)  # ENTRADA, SAIDA, AJUSTE, PRODUCAO
    local_movimentacao = db.Column(db.String(50), nullable=False)  # COMPRA, VENDA, PRODUCAO, AJUSTE, DEVOLUCAO
    
    # Quantidades
    qtd_movimentacao = db.Column(db.Numeric(15, 3), nullable=False)

    # Observações
    observacao = db.Column(db.Text, nullable=True)

        
    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)

    # Índices compostos para performance  
    __table_args__ = (
        db.Index('idx_movimentacao_produto_data', 'cod_produto', 'data_movimentacao'),
        db.Index('idx_movimentacao_tipo_data', 'tipo_movimentacao', 'data_movimentacao'),
    )

    def __repr__(self):
        return f'<MovimentacaoEstoque {self.cod_produto} - {self.tipo_movimentacao} - {self.qtd_movimentacao}>'

    def to_dict(self):
        return {
            'id': self.id,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'data_movimentacao': self.data_movimentacao.strftime('%d/%m/%Y') if self.data_movimentacao else None,
            'tipo_movimentacao': self.tipo_movimentacao,
            'local_movimentacao': self.local_movimentacao,
            'qtd_movimentacao': float(self.qtd_movimentacao) if self.qtd_movimentacao else 0,
            'observacao': self.observacao
        }


class UnificacaoCodigos(db.Model):
    """
    Modelo para unificação de códigos de produtos
    Permite tratar códigos diferentes como mesmo produto físico para fins de estoque
    """
    __tablename__ = 'unificacao_codigos'

    id = db.Column(db.Integer, primary_key=True)
    
    # Códigos de unificação
    codigo_origem = db.Column(db.Integer, nullable=False, index=True)
    codigo_destino = db.Column(db.Integer, nullable=False, index=True) 
    
    # Observações
    observacao = db.Column(db.Text, nullable=True)
    
    # Auditoria completa
    ativo = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    created_by = db.Column(db.String(100), nullable=True)
    updated_by = db.Column(db.String(100), nullable=True)
    
    # Histórico de ativação/desativação
    data_ativacao = db.Column(db.DateTime, nullable=True)
    data_desativacao = db.Column(db.DateTime, nullable=True)
    motivo_desativacao = db.Column(db.Text, nullable=True)
    
    # Índices compostos para performance e integridade
    __table_args__ = (
        # Evita duplicação: mesmo par origem-destino
        db.UniqueConstraint('codigo_origem', 'codigo_destino', name='uq_unificacao_origem_destino'),
        # Evita ciclos: A->B e B->A simultaneamente  
        db.Index('idx_unificacao_origem', 'codigo_origem'),
        db.Index('idx_unificacao_destino', 'codigo_destino'),
        db.Index('idx_unificacao_ativo', 'ativo'),
    )

    def __repr__(self):
        status = "Ativo" if self.ativo else "Inativo"
        return f'<UnificacaoCodigos {self.codigo_origem} → {self.codigo_destino} [{status}]>'

    def to_dict(self):
        return {
            'id': self.id,
            'codigo_origem': self.codigo_origem,
            'codigo_destino': self.codigo_destino,
            'observacao': self.observacao,
            'ativo': self.ativo,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%d/%m/%Y %H:%M') if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'data_ativacao': self.data_ativacao.strftime('%d/%m/%Y %H:%M') if self.data_ativacao else None,
            'data_desativacao': self.data_desativacao.strftime('%d/%m/%Y %H:%M') if self.data_desativacao else None,
            'motivo_desativacao': self.motivo_desativacao
        }

    @classmethod
    def get_codigo_unificado(cls, codigo_produto):
        """
        Retorna o código destino se existe unificação ativa, senão retorna o próprio código
        """
        try:
            codigo_produto = int(codigo_produto)
            
            # Busca se o código é origem em alguma unificação ativa
            unificacao = cls.query.filter_by(
                codigo_origem=codigo_produto,
                ativo=True
            ).first()
            
            if unificacao:
                return unificacao.codigo_destino
                
            # Se não é origem, verifica se é destino (para estatísticas)
            return codigo_produto
            
        except (ValueError, TypeError):
            return codigo_produto

    @classmethod
    def get_todos_codigos_relacionados(cls, codigo_produto):
        """
        Retorna todos os códigos relacionados ao código informado
        Usado para estatísticas e consolidação
        """
        try:
            codigo_produto = int(codigo_produto)
            codigos_relacionados = set([codigo_produto])
            
            # Busca códigos que apontam para este (este é destino)
            origens = cls.query.filter_by(
                codigo_destino=codigo_produto,
                ativo=True
            ).all()
            
            for origem in origens:
                codigos_relacionados.add(origem.codigo_origem)
            
            # Busca para onde este código aponta (este é origem)
            destino = cls.query.filter_by(
                codigo_origem=codigo_produto,
                ativo=True
            ).first()
            
            if destino:
                codigos_relacionados.add(destino.codigo_destino)
                # Busca outros códigos que também apontam para o mesmo destino
                outros_origens = cls.query.filter_by(
                    codigo_destino=destino.codigo_destino,
                    ativo=True
                ).all()
                for outro in outros_origens:
                    codigos_relacionados.add(outro.codigo_origem)
            
            return list(codigos_relacionados)
            
        except (ValueError, TypeError):
            return [codigo_produto]

    def ativar(self, usuario=None, motivo=None):
        """Ativa a unificação"""
        self.ativo = True
        self.data_ativacao = agora_brasil()
        self.updated_by = usuario
        self.motivo_desativacao = None
        
    def desativar(self, usuario=None, motivo=None):
        """Desativa a unificação"""
        self.ativo = False
        self.data_desativacao = agora_brasil()
        self.updated_by = usuario
        self.motivo_desativacao = motivo 
# IMPORTANTE: Registrar tipos PostgreSQL ANTES de usar db
import os
if 'postgres' in os.getenv('DATABASE_URL', ''):
    try:
        import psycopg2 # type: ignore
        from psycopg2 import extensions
        DATE = extensions.new_type((1082,), "DATE", extensions.DATE)
        extensions.register_type(DATE)
        extensions.register_type(DATE, None)
        print("✅ [MODELS] Tipos PostgreSQL registrados em estoque/models.py")
    except Exception as e:
        print(f"⚠️ Erro ao registrar tipos PostgreSQL: {e}")
        pass

from app import db
from app.utils.timezone import agora_brasil
import logging

logger = logging.getLogger(__name__)


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

    # Campos estruturados para sincronização NF (NOVO)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # ID do lote de separação
    numero_nf = db.Column(db.String(20), nullable=True, index=True)  # Número da NF
    num_pedido = db.Column(db.String(50), nullable=True, index=True)  # Número do pedido
    tipo_origem = db.Column(db.String(20), nullable=True)  # ODOO, TAGPLUS, MANUAL, LEGADO
    status_nf = db.Column(db.String(20), nullable=True)  # FATURADO, CANCELADO
    codigo_embarque = db.Column(db.Integer, db.ForeignKey('embarques.id', ondelete='SET NULL'), nullable=True)

    # Campos Odoo - Rastreabilidade de Entradas de Compras
    odoo_picking_id = db.Column(db.String(50), nullable=True, index=True)  # ID do stock.picking no Odoo
    odoo_move_id = db.Column(db.String(50), nullable=True, index=True)     # ID do stock.move no Odoo
    purchase_line_id = db.Column(db.String(50), nullable=True)             # ID da linha de pedido Odoo (purchase.order.line)
    pedido_compras_id = db.Column(db.Integer, db.ForeignKey('pedido_compras.id', ondelete='SET NULL'), nullable=True)  # FK para PedidoCompras local

    # Observações (mantido para compatibilidade)
    observacao = db.Column(db.Text, nullable=True)

    # Campos de Vinculação Produção/Consumo
    # PseudoID que agrupa todas as movimentações de uma operação (PROD_YYYYMMDD_HHMMSS_XXXX)
    operacao_producao_id = db.Column(db.String(50), nullable=True, index=True)
    # Tipo de origem: RAIZ, CONSUMO_DIRETO, PRODUCAO_AUTO, CONSUMO_AUTO
    tipo_origem_producao = db.Column(db.String(20), nullable=True)
    # Código do produto raiz (produto que iniciou a cascata de produção)
    cod_produto_raiz = db.Column(db.String(50), nullable=True, index=True)
    # FK para produção que gerou este consumo (auto-referência)
    producao_pai_id = db.Column(db.Integer, db.ForeignKey('movimentacao_estoque.id', ondelete='SET NULL'), nullable=True, index=True)

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
        db.Index('idx_movimentacao_nf', 'numero_nf'),
        db.Index('idx_movimentacao_lote', 'separacao_lote_id'),
        db.Index('idx_movimentacao_pedido', 'num_pedido'),
        db.Index('idx_movimentacao_tipo_origem', 'tipo_origem'),
        db.Index('idx_movimentacao_status_nf', 'status_nf'),
        db.Index('idx_movimentacao_odoo_picking', 'odoo_picking_id'),
        db.Index('idx_movimentacao_odoo_move', 'odoo_move_id'),
    )

    def __repr__(self):
        return f'<MovimentacaoEstoque {self.cod_produto} - {self.tipo_movimentacao} - {self.qtd_movimentacao}>'

    def to_dict(self):
        return {
            'id': self.id,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'separacao_lote_id': self.separacao_lote_id,
            'numero_nf': self.numero_nf,
            'num_pedido': self.num_pedido,
            'tipo_origem': self.tipo_origem,
            'status_nf': self.status_nf,
            'codigo_embarque': self.codigo_embarque,
            'data_movimentacao': self.data_movimentacao.strftime('%d/%m/%Y') if self.data_movimentacao else None,
            'tipo_movimentacao': self.tipo_movimentacao,
            'local_movimentacao': self.local_movimentacao,
            'qtd_movimentacao': float(self.qtd_movimentacao) if self.qtd_movimentacao else 0,
            'observacao': self.observacao,
            # Campos de vinculação produção/consumo
            'operacao_producao_id': self.operacao_producao_id,
            'tipo_origem_producao': self.tipo_origem_producao,
            'cod_produto_raiz': self.cod_produto_raiz,
            'producao_pai_id': self.producao_pai_id
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
        SEMPRE inclui o próprio código, mesmo sem unificação
        """
        try:
            # Garantir que sempre inclui o próprio código (como string)
            codigo_original = str(codigo_produto)
            codigos_relacionados = set([codigo_original])
            
            # Tentar converter para int para busca na tabela de unificação
            try:
                codigo_int = int(codigo_produto)
                
                # Busca códigos que apontam para este (este é destino)
                origens = cls.query.filter_by(
                    codigo_destino=codigo_int,
                    ativo=True
                ).all()
                
                for origem in origens:
                    codigos_relacionados.add(str(origem.codigo_origem))
                
                # Busca para onde este código aponta (este é origem)
                destino = cls.query.filter_by(
                    codigo_origem=codigo_int,
                    ativo=True
                ).first()
                
                if destino:
                    codigos_relacionados.add(str(destino.codigo_destino))
                    # Busca outros códigos que também apontam para o mesmo destino
                    outros_origens = cls.query.filter_by(
                        codigo_destino=destino.codigo_destino,
                        ativo=True
                    ).all()
                    for outro in outros_origens:
                        codigos_relacionados.add(str(outro.codigo_origem))
                        
            except (ValueError, TypeError):
                # Se não conseguir converter para int, ignora unificação mas mantém o código original
                pass
            
            return list(codigos_relacionados)
            
        except Exception:
            # Em caso de qualquer erro, sempre retorna pelo menos o código original
            return [str(codigo_produto)]

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

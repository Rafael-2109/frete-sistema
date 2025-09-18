"""
Modelo para armazenar dados da planilha modelo do Portal Sendas
Etapa 1 do novo processo semi-automatizado
"""

from app import db
from datetime import datetime

class PlanilhaModeloSendas(db.Model):
    """
    Armazena os dados da planilha modelo baixada do portal Sendas
    EXATAMENTE como vêm da planilha, sem conversões
    Coluna 1 é Demanda (preenchida na exportação)
    Colunas 2-16 são preenchidas pelo Sendas
    """
    __tablename__ = 'portal_sendas_planilha_modelo'

    id = db.Column(db.Integer, primary_key=True)

    # Colunas 2-16 exatamente como vêm da planilha
    razao_social_fornecedor = db.Column(db.String(255))          # Coluna 2
    nome_fantasia_fornecedor = db.Column(db.String(255))         # Coluna 3
    unidade_destino = db.Column(db.String(255), index=True)      # Coluna 4
    uf_destino = db.Column(db.String(2))                         # Coluna 5
    fluxo_operacao = db.Column(db.String(100))                   # Coluna 6
    codigo_pedido_cliente = db.Column(db.String(200), index=True) # Coluna 7
    codigo_produto_cliente = db.Column(db.String(100), index=True) # Coluna 8
    codigo_produto_sku_fornecedor = db.Column(db.String(100))    # Coluna 9
    ean = db.Column(db.String(20))                               # Coluna 10
    setor = db.Column(db.String(100))                            # Coluna 11
    numero_pedido_trizy = db.Column(db.String(100))              # Coluna 12
    descricao_item = db.Column(db.String(500))                   # Coluna 13
    quantidade_total = db.Column(db.Numeric(15, 3))              # Coluna 14
    saldo_disponivel = db.Column(db.Numeric(15, 3))              # Coluna 15
    unidade_medida = db.Column(db.String(20))                    # Coluna 16

    # Controle
    data_importacao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    usuario_importacao = db.Column(db.String(100))

    # Índices para busca na Etapa 2
    __table_args__ = (
        db.Index('idx_planilha_sendas_busca', 'unidade_destino', 'codigo_pedido_cliente',
                 'codigo_produto_cliente'),
    )

    @classmethod
    def limpar_tabela(cls):
        """
        Remove todos os registros da tabela
        Usado antes de importar uma nova planilha
        """
        cls.query.delete()
        db.session.commit()

    def __repr__(self):
        return f"<PlanilhaModelo {self.unidade_destino} - {self.codigo_pedido_cliente} - {self.codigo_produto_cliente}>"
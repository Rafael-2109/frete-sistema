from app import db
from datetime import datetime
from app.utils.timezone import agora_brasil

class RelatorioFaturamentoImportado(db.Model):
    __tablename__ = 'relatorio_faturamento_importado'

    id = db.Column(db.Integer, primary_key=True)
    numero_nf = db.Column(db.String(20), nullable=False, index=True, unique=True)
    data_fatura = db.Column(db.Date, nullable=True)
    cnpj_cliente = db.Column(db.String(20), nullable=True)
    nome_cliente = db.Column(db.String(255), nullable=True)
    valor_total = db.Column(db.Float, nullable=True)
    peso_bruto = db.Column(db.Float, nullable=True)
    cnpj_transportadora = db.Column(db.String(20), nullable=True)
    nome_transportadora = db.Column(db.String(255), nullable=True)
    municipio = db.Column(db.String(100), nullable=True)
    estado = db.Column(db.String(2), nullable=True)
    codigo_ibge = db.Column(db.String(10), nullable=True)
    origem = db.Column(db.String(50), nullable=True)
    incoterm = db.Column(db.String(20), nullable=True)
    vendedor = db.Column(db.String(100), nullable=True)
    equipe_vendas = db.Column(db.String(100), nullable=True)  # 🆕 Campo para equipe de vendas
    ativo = db.Column(db.Boolean, default=True, nullable=False)  # 🆕 Campo para inativação
    inativado_em = db.Column(db.DateTime, nullable=True)  # 🆕 Data de inativação
    inativado_por = db.Column(db.String(100), nullable=True)  # 🆕 Quem inativou
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<NF {self.numero_nf} - {self.nome_cliente}>"


class FaturamentoProduto(db.Model):
    """
    Modelo para controle do faturamento por produto - origem dos dados agregados
    """
    __tablename__ = 'faturamento_produto'

    id = db.Column(db.Integer, primary_key=True)
    
    # Dados do produto
    
    # Dados da nota fiscal
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    data_fatura = db.Column(db.Date, nullable=False, index=True)
    
    # Dados do cliente
    cnpj_cliente = db.Column(db.String(20), nullable=False, index=True)  # CNPJ do cliente
    nome_cliente = db.Column(db.String(255), nullable=False)  # Razão Social
    municipio = db.Column(db.String(100), nullable=True)  # Cidade
    estado = db.Column(db.String(2), nullable=True)  # UF (nome reduzido como "ES")
    
    # Dados do vendedor
    vendedor = db.Column(db.String(100), nullable=True)  # Campo do CSV original
    equipe_vendas = db.Column(db.String(100), nullable=True)  # 🆕 Campo para equipe de vendas
    incoterm = db.Column(db.String(20), nullable=True)  # Campo do CSV original
    
    # Dados do produto na NF
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(200), nullable=False)
    qtd_produto_faturado = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    preco_produto_faturado = db.Column(db.Numeric(15, 4), nullable=False, default=0)
    valor_produto_faturado = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    peso_unitario_produto = db.Column(db.Numeric(15, 3), nullable=True, default=0)  # ⚡ NOVO CAMPO
    peso_total = db.Column(db.Numeric(15, 3), nullable=True, default=0)  # peso_unitario * qtd
    
    # Dados de origem (número do pedido)
    origem = db.Column(db.String(20), nullable=True, index=True)
        
    # Status
    status_nf = db.Column(db.String(20), nullable=False, default='Provisório')  # Lançado, Cancelado, Provisório
    
    # Auditoria
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    created_by = db.Column(db.String(100), nullable=True)
    updated_by = db.Column(db.String(100), nullable=True)

    # Índices compostos para performance
    __table_args__ = (
        db.Index('idx_faturamento_nf_produto', 'numero_nf', 'cod_produto'),
        db.Index('idx_faturamento_cliente_data', 'cnpj_cliente', 'data_fatura'),  # Corrigido: data_fatura
        db.Index('idx_faturamento_pedido', 'origem'),
    )


    def __repr__(self):
        return f'<FaturamentoProduto {self.numero_nf} - {self.cod_produto}>'

    def to_dict(self):
        """Converte objeto para dicionário para API"""
        return {
            'id': self.id,
            'numero_nf': self.numero_nf,
            'data_fatura': self.data_fatura.strftime('%d/%m/%Y') if self.data_fatura else None,
            'cnpj_cliente': self.cnpj_cliente,
            'nome_cliente': self.nome_cliente,
            'municipio': self.municipio,
            'estado': self.estado,
            'origem': self.origem,
            'status_nf': self.status_nf,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'qtd_produto_faturado': float(self.qtd_produto_faturado) if self.qtd_produto_faturado else 0,
            'preco_produto_faturado': float(self.preco_produto_faturado) if self.preco_produto_faturado else 0,
            'valor_produto_faturado': float(self.valor_produto_faturado) if self.valor_produto_faturado else 0,
            'vendedor': self.vendedor,
            'equipe_vendas': self.equipe_vendas,
            'incoterm': self.incoterm
        }

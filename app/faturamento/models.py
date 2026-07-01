from app import db
from app.utils.timezone import agora_utc_naive

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
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)

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
    origem = db.Column(db.String(20), nullable=True, index=True, info={'description': 'num_pedido relacionado a essa NF'})
        
    # Status
    status_nf = db.Column(db.String(20), nullable=False, default='Provisório')  # Lançado, Cancelado, Provisório

    # Campos de Reversão (NF revertida via Nota de Crédito no Odoo)
    revertida = db.Column(db.Boolean, default=False, nullable=False, index=True, info={'description': 'Flag: NF devolvida integralmente'})
    nota_credito_id = db.Column(db.Integer, nullable=True)  # ID do out_refund no Odoo
    data_reversao = db.Column(db.DateTime, nullable=True, info={'description': 'Data da reversão'})

    # Auditoria
    created_at = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive, nullable=False)
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
            'incoterm': self.incoterm,
            # Campos de reversão
            'revertida': self.revertida,
            'nota_credito_id': self.nota_credito_id,
            'data_reversao': self.data_reversao.strftime('%d/%m/%Y %H:%M') if self.data_reversao else None
        }


class AlertaFaturamentoCnpj(db.Model):
    """CNPJ monitorado: ao faturar para ele, dispara alerta por e-mail."""
    __tablename__ = 'alerta_faturamento_cnpj'

    id = db.Column(db.Integer, primary_key=True)
    cnpj = db.Column(db.String(20), nullable=False, unique=True, index=True)
    nome_cliente = db.Column(db.String(255), nullable=True)
    emails = db.Column(db.Text, nullable=False)  # lista separada por ; ou ,
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    def lista_emails(self):
        import re
        return [e.strip() for e in re.split(r'[;,\n]', self.emails or '') if e.strip()]

    def __repr__(self):
        return f"<AlertaFaturamentoCnpj {self.cnpj} ativo={self.ativo}>"


class AlertaFaturamentoEnviado(db.Model):
    """Log/idempotencia: 1 linha por (numero_nf, canal). Evita reenvio."""
    __tablename__ = 'alerta_faturamento_enviado'

    id = db.Column(db.Integer, primary_key=True)
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    cnpj = db.Column(db.String(20), nullable=True, index=True)
    canal = db.Column(db.String(10), nullable=False, default='email')  # 'email'
    status = db.Column(db.String(10), nullable=False, default='ok')  # 'ok' | 'erro'
    detalhe = db.Column(db.Text, nullable=True)
    enviado_em = db.Column(db.DateTime, default=agora_utc_naive)

    __table_args__ = (
        db.UniqueConstraint('numero_nf', 'canal', name='uq_alerta_fat_enviado_nf_canal'),
    )

    def __repr__(self):
        return f"<AlertaFaturamentoEnviado NF {self.numero_nf} {self.canal} {self.status}>"

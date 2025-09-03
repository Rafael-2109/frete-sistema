from app import db
from app.utils.timezone import agora_brasil

class ProgramacaoProducao(db.Model):
    """
    Modelo para controle da programação de produção
    """
    __tablename__ = 'programacao_producao'

    id = db.Column(db.Integer, primary_key=True)
    
    # Dados da ordem de produção
    data_programacao = db.Column(db.Date, nullable=False, index=True) 
    
    # Dados do produto
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(200), nullable=False)
    
    # Quantidades
    qtd_programada = db.Column(db.Float, nullable=False)
    
    # Dados de produção
    linha_producao = db.Column(db.String(50), nullable=True)
    cliente_produto = db.Column(db.String(100), nullable=True)  # marca

    # Prioridade e observações
    observacao_pcp = db.Column(db.Text, nullable=True)
        
    # Auditoria
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    created_by = db.Column(db.String(100), nullable=True)
    updated_by = db.Column(db.String(100), nullable=True)

    # Índices compostos para performance
    __table_args__ = (
        db.Index('idx_programacao_data_linha', 'data_programacao', 'linha_producao'),
        db.Index('idx_programacao_produto_data', 'cod_produto', 'data_programacao'),
        # Sem constraint única - programação permite múltiplas entradas do mesmo produto/linha/data
    )

    def __repr__(self):
        return f'<ProgramacaoProducao {self.cod_produto} - {self.data_programacao}>'

    def to_dict(self):
        return {
            'id': self.id,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'data_programacao': self.data_programacao.strftime('%d/%m/%Y') if self.data_programacao else None,
            'qtd_programada': float(self.qtd_programada) if self.qtd_programada else 0,
            'linha_producao': self.linha_producao,
            'cliente_produto': self.cliente_produto,
            'observacao_pcp': self.observacao_pcp
        }
       



class CadastroPalletizacao(db.Model):
    """
    Modelo para cadastro de palletização e peso bruto dos produtos
    Conforme CSV: 8- cadastro palletizacao e peso bruto.csv
    """
    __tablename__ = 'cadastro_palletizacao'

    id = db.Column(db.Integer, primary_key=True)
    
    # Dados do produto (conforme CSV)
    cod_produto = db.Column(db.String(50), nullable=False, unique=True, index=True)  # Cód.Produto
    nome_produto = db.Column(db.String(255), nullable=False)  # Descrição Produto
    
    # Fatores de conversão (conforme CSV)
    palletizacao = db.Column(db.Float, nullable=False)  # PALLETIZACAO: qtd / palletizacao = pallets
    peso_bruto = db.Column(db.Float, nullable=False)    # PESO BRUTO: qtd * peso_bruto = peso total
    
    # Dados de dimensões (interessante para cálculos)
    altura_cm = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    largura_cm = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    comprimento_cm = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    
    # Subcategorias para filtros avançados
    tipo_embalagem = db.Column(db.String(50), nullable=True, index=True)
    tipo_materia_prima = db.Column(db.String(50), nullable=True, index=True)
    categoria_produto = db.Column(db.String(50), nullable=True, index=True)
    subcategoria = db.Column(db.String(50), nullable=True)
    linha_producao = db.Column(db.String(50), nullable=True, index=True)
    
    # Status
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    
    # Auditoria
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    def __repr__(self):
        return f'<CadastroPalletizacao {self.cod_produto} - Pallet: {self.palletizacao}>'

    def calcular_pallets(self, quantidade):
        """Calcula quantos pallets para uma quantidade"""
        if self.palletizacao > 0:
            return round(quantidade / self.palletizacao, 2)
        return 0

    def calcular_peso_total(self, quantidade):
        """Calcula peso total para uma quantidade"""
        return round(quantidade * self.peso_bruto, 2)

    @property
    def volume_m3(self):
        """Calcula volume unitário em m³"""
        if self.altura_cm and self.largura_cm and self.comprimento_cm:
            return round((float(self.altura_cm) * float(self.largura_cm) * float(self.comprimento_cm)) / 1000000, 6)
        return 0

    def to_dict(self):
        return {
            'id': self.id,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'palletizacao': float(self.palletizacao) if self.palletizacao else 0,
            'peso_bruto': float(self.peso_bruto) if self.peso_bruto else 0,
            'altura_cm': float(self.altura_cm) if self.altura_cm else 0,
            'largura_cm': float(self.largura_cm) if self.largura_cm else 0,
            'comprimento_cm': float(self.comprimento_cm) if self.comprimento_cm else 0,
            'volume_m3': self.volume_m3,
            'ativo': self.ativo
        } 
"""
Modelos para validação de preços de redes de atacarejo
- TabelaRede: Preços por Rede/Região/Produto
- RegiaoTabelaRede: Mapeamento UF → Região por Rede
"""

from datetime import datetime
from app import db


class TabelaRede(db.Model):
    """
    Tabela de preços por Rede/Região/Produto

    Armazena os preços negociados com cada rede de atacarejo
    por região geográfica e código de produto.

    Exemplo:
        - ATACADAO + SUDESTE + 35642 = R$ 199,48
        - TENDA + SUL + 35642 = R$ 195,00
    """
    __tablename__ = 'tabela_rede_precos'

    id = db.Column(db.Integer, primary_key=True)

    # Identificação
    rede = db.Column(db.String(50), nullable=False, index=True)  # 'ATACADAO', 'TENDA', 'ASSAI'
    regiao = db.Column(db.String(50), nullable=False, index=True)  # 'SUDESTE', 'SUL', 'NORDESTE', etc.
    cod_produto = db.Column(db.String(50), nullable=False, index=True)  # Código Nacom

    # Preço
    preco = db.Column(db.Numeric(15, 2), nullable=False)

    # Controle
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    vigencia_inicio = db.Column(db.Date, nullable=True)
    vigencia_fim = db.Column(db.Date, nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # Constraints
    __table_args__ = (
        db.UniqueConstraint('rede', 'regiao', 'cod_produto', name='uq_tabela_rede_produto'),
        db.Index('idx_tabela_rede_regiao', 'rede', 'regiao'),
        db.Index('idx_tabela_rede_produto', 'rede', 'cod_produto'),
    )

    def __repr__(self):
        return f'<TabelaRede {self.rede}/{self.regiao}/{self.cod_produto}: R${self.preco}>'

    @classmethod
    def buscar_preco(cls, rede: str, regiao: str, cod_produto: str):
        """
        Busca o preço de um produto para uma rede/região específica

        Args:
            rede: Nome da rede (ATACADAO, TENDA, ASSAI)
            regiao: Nome da região (SUDESTE, SUL, etc.)
            cod_produto: Código do produto Nacom

        Returns:
            TabelaRede ou None
        """
        return cls.query.filter_by(
            rede=rede.upper(),
            regiao=regiao.upper(),
            cod_produto=cod_produto,
            ativo=True
        ).first()

    @classmethod
    def buscar_preco_por_uf(cls, rede: str, uf: str, cod_produto: str):
        """
        Busca o preço convertendo UF para Região

        Args:
            rede: Nome da rede
            uf: Estado (SP, RJ, etc.)
            cod_produto: Código do produto

        Returns:
            TabelaRede ou None
        """
        # Primeiro busca a região pela UF
        regiao_map = RegiaoTabelaRede.buscar_regiao(rede, uf)
        if not regiao_map:
            return None

        return cls.buscar_preco(rede, regiao_map.regiao, cod_produto)


class RegiaoTabelaRede(db.Model):
    """
    Mapeamento UF → Região por Rede

    Permite que múltiplas UFs sejam agrupadas em uma mesma região
    para fins de precificação.

    Exemplo:
        - ATACADAO: SP → SUDESTE
        - ATACADAO: RJ → SUDESTE
        - ATACADAO: RS → SUL
    """
    __tablename__ = 'regiao_tabela_rede'

    id = db.Column(db.Integer, primary_key=True)

    # Identificação
    rede = db.Column(db.String(50), nullable=False, index=True)  # 'ATACADAO', 'TENDA', 'ASSAI'
    uf = db.Column(db.String(2), nullable=False, index=True)  # 'SP', 'RJ', etc.
    regiao = db.Column(db.String(50), nullable=False)  # 'SUDESTE', 'SUL', etc.

    # Controle
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)

    # Constraints
    __table_args__ = (
        db.UniqueConstraint('rede', 'uf', name='uq_regiao_rede_uf'),
        db.Index('idx_regiao_rede_uf', 'rede', 'uf'),
    )

    def __repr__(self):
        return f'<RegiaoTabelaRede {self.rede}/{self.uf} → {self.regiao}>'

    @classmethod
    def buscar_regiao(cls, rede: str, uf: str):
        """
        Busca a região correspondente a uma UF para determinada rede

        Args:
            rede: Nome da rede
            uf: Estado

        Returns:
            RegiaoTabelaRede ou None
        """
        return cls.query.filter_by(
            rede=rede.upper(),
            uf=uf.upper(),
            ativo=True
        ).first()

    @classmethod
    def listar_ufs_por_regiao(cls, rede: str, regiao: str):
        """
        Lista todas as UFs de uma região para uma rede

        Args:
            rede: Nome da rede
            regiao: Nome da região

        Returns:
            Lista de RegiaoTabelaRede
        """
        return cls.query.filter_by(
            rede=rede.upper(),
            regiao=regiao.upper(),
            ativo=True
        ).all()

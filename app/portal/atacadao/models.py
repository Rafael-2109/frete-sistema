"""
Modelos específicos do Portal Atacadão
Incluindo tabela DE-PARA de produtos
"""

from app import db
from datetime import datetime

class ProdutoDeParaAtacadao(db.Model):
    """
    Tabela DE-PARA para mapear códigos de produtos
    Nosso código <-> Código do cliente Atacadão
    """
    __tablename__ = 'portal_atacadao_produto_depara'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Nosso código e descrição
    codigo_nosso = db.Column(db.String(50), nullable=False, index=True)
    descricao_nosso = db.Column(db.String(255))
    
    # Código e descrição do Atacadão
    codigo_atacadao = db.Column(db.String(50), nullable=False, index=True)
    descricao_atacadao = db.Column(db.String(255))
    
    # CNPJ do cliente (caso o mapeamento seja específico por cliente)
    cnpj_cliente = db.Column(db.String(20), index=True)
    
    # Fator de conversão (se houver diferença de unidade de medida)
    fator_conversao = db.Column(db.Numeric(10, 4), default=1.0)
    observacoes = db.Column(db.Text)
    
    # Controle
    ativo = db.Column(db.Boolean, default=True, index=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    
    # Índice único para evitar duplicatas
    __table_args__ = (
        db.UniqueConstraint('codigo_nosso', 'codigo_atacadao', 'cnpj_cliente', 
                          name='unique_depara_atacadao'),
    )
    
    @classmethod
    def obter_codigo_atacadao(cls, codigo_nosso, cnpj_cliente=None):
        """
        Obtém o código do Atacadão correspondente ao nosso código
        
        Args:
            codigo_nosso: Nosso código de produto
            cnpj_cliente: CNPJ do cliente (opcional)
            
        Returns:
            Código do Atacadão ou None se não encontrar
        """
        query = cls.query.filter_by(
            codigo_nosso=codigo_nosso,
            ativo=True
        )
        
        if cnpj_cliente:
            # Primeiro tentar com CNPJ específico
            depara = query.filter_by(cnpj_cliente=cnpj_cliente).first()
            if depara:
                return depara.codigo_atacadao
            
            # Se não encontrar, tentar genérico (cnpj_cliente = NULL)
            depara = query.filter(cls.cnpj_cliente.is_(None)).first()
            if depara:
                return depara.codigo_atacadao
        else:
            # Buscar genérico
            depara = query.filter(cls.cnpj_cliente.is_(None)).first()
            if depara:
                return depara.codigo_atacadao
        
        return None
    
    @classmethod
    def obter_nosso_codigo(cls, codigo_atacadao, cnpj_cliente=None):
        """
        Obtém nosso código correspondente ao código do Atacadão
        
        Args:
            codigo_atacadao: Código do produto no Atacadão
            cnpj_cliente: CNPJ do cliente (opcional)
            
        Returns:
            Nosso código ou None se não encontrar
        """
        query = cls.query.filter_by(
            codigo_atacadao=codigo_atacadao,
            ativo=True
        )
        
        if cnpj_cliente:
            # Primeiro tentar com CNPJ específico
            depara = query.filter_by(cnpj_cliente=cnpj_cliente).first()
            if depara:
                return depara.codigo_nosso
            
            # Se não encontrar, tentar genérico
            depara = query.filter(cls.cnpj_cliente.is_(None)).first()
            if depara:
                return depara.codigo_nosso
        else:
            # Buscar genérico
            depara = query.filter(cls.cnpj_cliente.is_(None)).first()
            if depara:
                return depara.codigo_nosso
        
        return None
    
    @classmethod
    def importar_de_csv(cls, filepath, cnpj_cliente=None, criado_por='Sistema'):
        """
        Importa mapeamentos de um arquivo CSV
        
        Formato esperado do CSV:
        codigo_nosso,descricao_nosso,codigo_atacadao,descricao_atacadao,fator_conversao
        """
        import csv
        
        registros_criados = 0
        registros_atualizados = 0
        erros = []
        
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    try:
                        # Verificar se já existe
                        depara = cls.query.filter_by(
                            codigo_nosso=row['codigo_nosso'],
                            codigo_atacadao=row['codigo_atacadao'],
                            cnpj_cliente=cnpj_cliente
                        ).first()
                        
                        if depara:
                            # Atualizar existente
                            depara.descricao_nosso = row.get('descricao_nosso', depara.descricao_nosso)
                            depara.descricao_atacadao = row.get('descricao_atacadao', depara.descricao_atacadao)
                            depara.fator_conversao = float(row.get('fator_conversao', 1.0))
                            depara.atualizado_em = datetime.utcnow()
                            registros_atualizados += 1
                        else:
                            # Criar novo
                            depara = cls(
                                codigo_nosso=row['codigo_nosso'],
                                descricao_nosso=row.get('descricao_nosso'),
                                codigo_atacadao=row['codigo_atacadao'],
                                descricao_atacadao=row.get('descricao_atacadao'),
                                cnpj_cliente=cnpj_cliente,
                                fator_conversao=float(row.get('fator_conversao', 1.0)),
                                criado_por=criado_por,
                                ativo=True
                            )
                            db.session.add(depara)
                            registros_criados += 1
                            
                    except Exception as e:
                        erros.append(f"Erro na linha {reader.line_num}: {e}")
                
                db.session.commit()
                
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Erro ao importar arquivo: {e}")
        
        return {
            'criados': registros_criados,
            'atualizados': registros_atualizados,
            'erros': erros
        }
    
    def __repr__(self):
        return f"<DeParaAtacadao {self.codigo_nosso} -> {self.codigo_atacadao}>"
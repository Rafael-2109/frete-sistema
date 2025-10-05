"""
Modelos de Cadastro - Sistema MotoCHEFE
Mantidos dos models antigos, com auditoria padronizada
"""
from app import db
from datetime import datetime


class VendedorMoto(db.Model):
    """Cadastro de vendedores"""
    __tablename__ = 'vendedor_moto'

    id = db.Column(db.Integer, primary_key=True)
    vendedor = db.Column(db.String(100), nullable=False)
    equipe_vendas_id = db.Column(db.Integer, db.ForeignKey('equipe_vendas_moto.id'), nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<VendedorMoto {self.vendedor}>'


class EquipeVendasMoto(db.Model):
    """Cadastro de equipes de vendas"""
    __tablename__ = 'equipe_vendas_moto'

    id = db.Column(db.Integer, primary_key=True)
    equipe_vendas = db.Column(db.String(100), nullable=False, unique=True)

    # Relacionamentos
    vendedores = db.relationship('VendedorMoto', backref='equipe', lazy='dynamic')

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<EquipeVendasMoto {self.equipe_vendas}>'


class TransportadoraMoto(db.Model):
    """Cadastro de transportadoras"""
    __tablename__ = 'transportadora_moto'

    id = db.Column(db.Integer, primary_key=True)
    transportadora = db.Column(db.String(100), nullable=False, unique=True)
    cnpj = db.Column(db.String(20), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)

    # Dados bancários
    chave_pix = db.Column(db.String(100), nullable=True)
    agencia = db.Column(db.String(20), nullable=True)
    conta = db.Column(db.String(20), nullable=True)
    banco = db.Column(db.String(100), nullable=True)
    cod_banco = db.Column(db.String(10), nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<TransportadoraMoto {self.transportadora}>'


class ClienteMoto(db.Model):
    """Cadastro de clientes"""
    __tablename__ = 'cliente_moto'

    id = db.Column(db.Integer, primary_key=True)
    cnpj_cliente = db.Column(db.String(20), unique=True, nullable=False)
    cliente = db.Column(db.String(100), nullable=False)

    # Campos de endereço
    endereco_cliente = db.Column(db.String(100), nullable=True)
    numero_cliente = db.Column(db.String(20), nullable=True)
    complemento_cliente = db.Column(db.String(100), nullable=True)
    bairro_cliente = db.Column(db.String(100), nullable=True)
    cidade_cliente = db.Column(db.String(100), nullable=True)
    estado_cliente = db.Column(db.String(2), nullable=True)
    cep_cliente = db.Column(db.String(10), nullable=True)

    # Contato
    telefone_cliente = db.Column(db.String(20), nullable=True)
    email_cliente = db.Column(db.String(100), nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<ClienteMoto {self.cliente} - {self.cnpj_cliente}>'


class EmpresaVendaMoto(db.Model):
    """Cadastro de empresas usadas para faturamento"""
    __tablename__ = 'empresa_venda_moto'

    id = db.Column(db.Integer, primary_key=True)
    cnpj_empresa = db.Column(db.String(20), unique=True, nullable=False)
    empresa = db.Column(db.String(255), nullable=False)

    # Dados bancários
    chave_pix = db.Column(db.String(100), nullable=True)
    banco = db.Column(db.String(100), nullable=True)
    cod_banco = db.Column(db.String(10), nullable=True)
    agencia = db.Column(db.String(20), nullable=True)
    conta = db.Column(db.String(20), nullable=True)

    # Auditoria
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<EmpresaVendaMoto {self.empresa} - {self.cnpj_empresa}>'

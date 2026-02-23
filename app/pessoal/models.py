"""
Models do modulo Pessoal — 7 tabelas para controle de financas pessoais.

Convencao de timezone: agora_utc_naive() para todos os timestamps (Brasil naive).
Convencao monetaria: Numeric(15,2) para valores em R$, Numeric(15,4) para USD.
"""
from app import db
from app.utils.timezone import agora_utc_naive
from sqlalchemy import Index
import json


# =============================================================================
# 1. MEMBROS DA FAMILIA
# =============================================================================
class PessoalMembro(db.Model):
    __tablename__ = 'pessoal_membros'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    nome_completo = db.Column(db.String(200))
    papel = db.Column(db.String(50))  # pai | mae | filho | filha
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)

    # Relacionamentos
    contas = db.relationship('PessoalConta', backref='membro', lazy='dynamic')
    transacoes = db.relationship('PessoalTransacao', backref='membro', lazy='dynamic')

    def __repr__(self):
        return f'<PessoalMembro {self.nome}>'

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'nome_completo': self.nome_completo,
            'papel': self.papel,
            'ativo': self.ativo,
        }


# =============================================================================
# 2. CONTAS BANCARIAS
# =============================================================================
class PessoalConta(db.Model):
    __tablename__ = 'pessoal_contas'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # conta_corrente | cartao_credito
    banco = db.Column(db.String(50), nullable=False, default='bradesco')
    agencia = db.Column(db.String(20))
    numero_conta = db.Column(db.String(30))
    ultimos_digitos_cartao = db.Column(db.String(10))
    membro_id = db.Column(db.Integer, db.ForeignKey('pessoal_membros.id'))
    ativa = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)

    # Relacionamentos
    importacoes = db.relationship('PessoalImportacao', backref='conta', lazy='dynamic')
    transacoes = db.relationship('PessoalTransacao', backref='conta', lazy='dynamic')

    def __repr__(self):
        return f'<PessoalConta {self.nome}>'

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'tipo': self.tipo,
            'banco': self.banco,
            'agencia': self.agencia,
            'numero_conta': self.numero_conta,
            'ultimos_digitos_cartao': self.ultimos_digitos_cartao,
            'membro_id': self.membro_id,
            'ativa': self.ativa,
        }


# =============================================================================
# 3. CATEGORIAS DE DESPESAS
# =============================================================================
class PessoalCategoria(db.Model):
    __tablename__ = 'pessoal_categorias'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    grupo = db.Column(db.String(100), nullable=False)
    icone = db.Column(db.String(50))
    ordem_exibicao = db.Column(db.Integer, default=0)
    ativa = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)

    # Relacionamentos
    regras = db.relationship('PessoalRegraCategorizacao', backref='categoria', lazy='dynamic')
    transacoes = db.relationship('PessoalTransacao', backref='categoria', lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('grupo', 'nome', name='uq_pessoal_categorias_grupo_nome'),
    )

    def __repr__(self):
        return f'<PessoalCategoria {self.nome} ({self.grupo})>'

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'grupo': self.grupo,
            'icone': self.icone,
            'ordem_exibicao': self.ordem_exibicao,
            'ativa': self.ativa,
        }


# =============================================================================
# 4. REGRAS DE CATEGORIZACAO
# =============================================================================
class PessoalRegraCategorizacao(db.Model):
    __tablename__ = 'pessoal_regras_categorizacao'

    id = db.Column(db.Integer, primary_key=True)
    padrao_historico = db.Column(db.String(300), nullable=False)
    tipo_regra = db.Column(db.String(20), nullable=False)  # PADRAO | RELATIVO
    categoria_id = db.Column(db.Integer, db.ForeignKey('pessoal_categorias.id'))
    membro_id = db.Column(db.Integer, db.ForeignKey('pessoal_membros.id'))
    categorias_restritas_ids = db.Column(db.Text)  # JSON array de IDs
    vezes_usado = db.Column(db.Integer, default=0)
    confianca = db.Column(db.Numeric(5, 2), default=100)
    origem = db.Column(db.String(30), default='semente')  # semente | manual | aprendido
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    # Relacionamentos
    membro = db.relationship('PessoalMembro', backref='regras')
    transacoes = db.relationship('PessoalTransacao', backref='regra', lazy='dynamic')

    def __repr__(self):
        return f'<PessoalRegra "{self.padrao_historico}" ({self.tipo_regra})>'

    def get_categorias_restritas(self):
        """Retorna lista de IDs das categorias restritas (para regras RELATIVO)."""
        if not self.categorias_restritas_ids:
            return []
        try:
            return json.loads(self.categorias_restritas_ids)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_categorias_restritas(self, ids_list):
        """Salva lista de IDs das categorias restritas como JSON."""
        self.categorias_restritas_ids = json.dumps(ids_list) if ids_list else None

    def to_dict(self):
        return {
            'id': self.id,
            'padrao_historico': self.padrao_historico,
            'tipo_regra': self.tipo_regra,
            'categoria_id': self.categoria_id,
            'membro_id': self.membro_id,
            'categorias_restritas_ids': self.get_categorias_restritas(),
            'vezes_usado': self.vezes_usado,
            'confianca': float(self.confianca) if self.confianca else 100,
            'origem': self.origem,
            'ativo': self.ativo,
        }


# =============================================================================
# 5. EXCLUSOES EMPRESARIAIS
# =============================================================================
class PessoalExclusaoEmpresa(db.Model):
    __tablename__ = 'pessoal_exclusoes_empresa'

    id = db.Column(db.Integer, primary_key=True)
    padrao = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.String(200))
    ativo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<PessoalExclusao {self.padrao}>'

    def to_dict(self):
        return {
            'id': self.id,
            'padrao': self.padrao,
            'descricao': self.descricao,
            'ativo': self.ativo,
        }


# =============================================================================
# 6. IMPORTACOES
# =============================================================================
class PessoalImportacao(db.Model):
    __tablename__ = 'pessoal_importacoes'

    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(db.Integer, db.ForeignKey('pessoal_contas.id'), nullable=False)
    nome_arquivo = db.Column(db.String(255))
    tipo_arquivo = db.Column(db.String(30))  # extrato_cc | fatura_cartao
    periodo_inicio = db.Column(db.Date)
    periodo_fim = db.Column(db.Date)
    situacao_fatura = db.Column(db.String(30))  # PAGO | ABERTA (so cartao)
    total_linhas = db.Column(db.Integer, default=0)
    linhas_importadas = db.Column(db.Integer, default=0)
    linhas_duplicadas = db.Column(db.Integer, default=0)
    linhas_empresa_filtradas = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='IMPORTADO')
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100))

    # Relacionamentos
    transacoes = db.relationship('PessoalTransacao', backref='importacao', lazy='dynamic')

    def __repr__(self):
        return f'<PessoalImportacao {self.nome_arquivo} ({self.status})>'

    def to_dict(self):
        return {
            'id': self.id,
            'conta_id': self.conta_id,
            'conta_nome': self.conta.nome if self.conta else None,
            'nome_arquivo': self.nome_arquivo,
            'tipo_arquivo': self.tipo_arquivo,
            'periodo_inicio': self.periodo_inicio.isoformat() if self.periodo_inicio else None,
            'periodo_fim': self.periodo_fim.isoformat() if self.periodo_fim else None,
            'situacao_fatura': self.situacao_fatura,
            'total_linhas': self.total_linhas,
            'linhas_importadas': self.linhas_importadas,
            'linhas_duplicadas': self.linhas_duplicadas,
            'linhas_empresa_filtradas': self.linhas_empresa_filtradas,
            'status': self.status,
            'criado_em': self.criado_em.strftime('%d/%m/%Y %H:%M') if self.criado_em else None,
            'criado_por': self.criado_por,
        }


# =============================================================================
# 7. TRANSACOES (tabela principal)
# =============================================================================
class PessoalTransacao(db.Model):
    __tablename__ = 'pessoal_transacoes'

    id = db.Column(db.Integer, primary_key=True)
    importacao_id = db.Column(db.Integer, db.ForeignKey('pessoal_importacoes.id'), nullable=False)
    conta_id = db.Column(db.Integer, db.ForeignKey('pessoal_contas.id'), nullable=False)

    # Dados CSV
    data = db.Column(db.Date, nullable=False)
    historico = db.Column(db.String(500), nullable=False)
    descricao = db.Column(db.String(500))  # 2a linha (Des:, Rem:, etc.)
    historico_completo = db.Column(db.String(1000))  # concatenacao normalizada
    documento = db.Column(db.String(50))
    valor = db.Column(db.Numeric(15, 2), nullable=False)  # SEMPRE positivo
    tipo = db.Column(db.String(10), nullable=False)  # debito | credito
    saldo = db.Column(db.Numeric(15, 2))

    # Cartao
    valor_dolar = db.Column(db.Numeric(15, 4))
    parcela_atual = db.Column(db.Integer)
    parcela_total = db.Column(db.Integer)
    identificador_parcela = db.Column(db.String(100))

    # Categorizacao
    categoria_id = db.Column(db.Integer, db.ForeignKey('pessoal_categorias.id'))
    regra_id = db.Column(db.Integer, db.ForeignKey('pessoal_regras_categorizacao.id'))
    categorizacao_auto = db.Column(db.Boolean, default=False)
    categorizacao_confianca = db.Column(db.Numeric(5, 2))

    # Membro
    membro_id = db.Column(db.Integer, db.ForeignKey('pessoal_membros.id'))
    membro_auto = db.Column(db.Boolean, default=False)

    # Controle
    excluir_relatorio = db.Column(db.Boolean, default=False)
    eh_pagamento_cartao = db.Column(db.Boolean, default=False)
    eh_transferencia_propria = db.Column(db.Boolean, default=False)
    observacao = db.Column(db.Text)
    status = db.Column(db.String(20), default='PENDENTE')  # PENDENTE | CATEGORIZADO | REVISADO

    # Deduplicacao
    hash_transacao = db.Column(db.String(64), nullable=False, unique=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)
    categorizado_em = db.Column(db.DateTime)
    categorizado_por = db.Column(db.String(100))

    __table_args__ = (
        Index('idx_pessoal_transacoes_data', 'data'),
        Index('idx_pessoal_transacoes_conta', 'conta_id'),
        Index('idx_pessoal_transacoes_categoria', 'categoria_id'),
        Index('idx_pessoal_transacoes_membro', 'membro_id'),
        Index('idx_pessoal_transacoes_status', 'status'),
    )

    def __repr__(self):
        return f'<PessoalTransacao {self.data} {self.historico[:30]} R${self.valor}>'

    def to_dict(self):
        return {
            'id': self.id,
            'importacao_id': self.importacao_id,
            'conta_id': self.conta_id,
            'conta_nome': self.conta.nome if self.conta else None,
            'data': self.data.strftime('%d/%m/%Y') if self.data else None,
            'data_iso': self.data.isoformat() if self.data else None,
            'historico': self.historico,
            'descricao': self.descricao,
            'historico_completo': self.historico_completo,
            'documento': self.documento,
            'valor': float(self.valor) if self.valor else 0,
            'tipo': self.tipo,
            'saldo': float(self.saldo) if self.saldo is not None else None,
            'valor_dolar': float(self.valor_dolar) if self.valor_dolar else None,
            'parcela_atual': self.parcela_atual,
            'parcela_total': self.parcela_total,
            'identificador_parcela': self.identificador_parcela,
            'categoria_id': self.categoria_id,
            'categoria_nome': self.categoria.nome if self.categoria else None,
            'categoria_grupo': self.categoria.grupo if self.categoria else None,
            'categoria_icone': self.categoria.icone if self.categoria else None,
            'regra_id': self.regra_id,
            'categorizacao_auto': self.categorizacao_auto,
            'categorizacao_confianca': float(self.categorizacao_confianca) if self.categorizacao_confianca else None,
            'membro_id': self.membro_id,
            'membro_nome': self.membro.nome if self.membro else None,
            'membro_auto': self.membro_auto,
            'excluir_relatorio': self.excluir_relatorio,
            'eh_pagamento_cartao': self.eh_pagamento_cartao,
            'eh_transferencia_propria': self.eh_transferencia_propria,
            'observacao': self.observacao,
            'status': self.status,
        }

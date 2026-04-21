"""
Models do modulo Pessoal — 8 tabelas principais + 4 tabelas staging Pluggy.

Convencao de timezone: agora_utc_naive() para todos os timestamps (Brasil naive).
Convencao monetaria: Numeric(15,2) para valores em R$, Numeric(15,4) para USD.
"""
from app import db
from app.utils.timezone import agora_utc_naive
from sqlalchemy import Index
from sqlalchemy.dialects.postgresql import JSONB
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
    # Vinculo Pluggy (Fase 4): quando conta foi conectada via Open Finance
    pluggy_account_id = db.Column(db.String(50), unique=True)
    pluggy_item_pk = db.Column(
        db.Integer, db.ForeignKey('pessoal_pluggy_items.id', ondelete='SET NULL'),
    )
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
    ativa = db.Column(db.Boolean, default=True)
    # Compensacao Empresa: 'S' saida compensavel, 'E' entrada compensavel, NULL nao participa.
    # Categorias marcadas como 'S'/'E' automaticamente ficam em excluir_relatorio=True quando
    # atribuidas a uma transacao (mesmo comportamento do grupo Desconsiderar), mas permitem
    # pareamento em pessoal_compensacoes.
    compensavel_tipo = db.Column(db.String(1))  # 'S' | 'E' | None
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)

    # Relacionamentos
    regras = db.relationship('PessoalRegraCategorizacao', backref='categoria', lazy='dynamic')
    transacoes = db.relationship('PessoalTransacao', backref='categoria', lazy='dynamic')
    orcamentos = db.relationship('PessoalOrcamento', backref='categoria', lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('grupo', 'nome', name='uq_pessoal_categorias_grupo_nome'),
        db.CheckConstraint(
            "compensavel_tipo IS NULL OR compensavel_tipo IN ('S', 'E')",
            name='ck_pessoal_categorias_compensavel_tipo',
        ),
    )

    def __repr__(self):
        return f'<PessoalCategoria {self.nome} ({self.grupo})>'

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'grupo': self.grupo,
            'icone': self.icone,
            'ativa': self.ativa,
            'compensavel_tipo': self.compensavel_tipo,
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
    # F1: CPF/CNPJ como chave alternativa de match (so digitos, 11 ou 14 chars)
    cpf_cnpj_padrao = db.Column(db.String(20))
    # F4: Condicoes por valor (NULL = sem restricao)
    valor_min = db.Column(db.Numeric(15, 2))
    valor_max = db.Column(db.Numeric(15, 2))
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
            'cpf_cnpj_padrao': self.cpf_cnpj_padrao,
            'valor_min': float(self.valor_min) if self.valor_min is not None else None,
            'valor_max': float(self.valor_max) if self.valor_max is not None else None,
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

    # Compensacao: quanto desta transacao ja foi compensado por contraparte.
    # Cache agregado — SUM(valor_compensado) das linhas ATIVAS em pessoal_compensacoes
    # onde esta transacao aparece como saida_id OU entrada_id.
    valor_compensado = db.Column(db.Numeric(15, 2), nullable=False, default=0)

    # F1: CPF/CNPJ extraido do historico/descricao (so digitos, 11 ou 14 chars)
    cpf_cnpj_parte = db.Column(db.String(20))

    # Deduplicacao
    hash_transacao = db.Column(db.String(64), nullable=False, unique=True)

    # Pluggy / Open Finance (Fase 4) — NULL quando origem != 'pluggy'
    pluggy_transaction_id = db.Column(db.String(64))
    origem_import = db.Column(db.String(20), nullable=False, default='csv')  # csv | ofx | pluggy
    operation_type = db.Column(db.String(30))  # TED | PIX | BOLETO | ...
    merchant_nome = db.Column(db.String(200))
    merchant_cnpj = db.Column(db.String(20))
    categoria_pluggy_id = db.Column(db.String(20))
    categoria_pluggy_sugerida = db.Column(db.String(100))

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
        Index('idx_pessoal_transacoes_excluir', 'excluir_relatorio'),
        Index(
            'idx_pessoal_transacoes_cpf_cnpj',
            'cpf_cnpj_parte',
            postgresql_where=db.text('cpf_cnpj_parte IS NOT NULL'),
        ),
        Index(
            'uq_pessoal_transacoes_pluggy_tx',
            'pluggy_transaction_id',
            unique=True,
            postgresql_where=db.text('pluggy_transaction_id IS NOT NULL'),
        ),
        Index('idx_pessoal_transacoes_origem', 'origem_import'),
    )

    def __repr__(self):
        return f'<PessoalTransacao {self.data} {self.historico[:30]} R${self.valor}>'

    @property
    def valor_efetivo(self):
        """Valor util para relatorios: valor - valor_compensado. Nunca negativo."""
        if self.valor is None:
            return None
        compensado = self.valor_compensado or 0
        efetivo = float(self.valor) - float(compensado)
        return efetivo if efetivo > 0 else 0.0

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
            'cpf_cnpj_parte': self.cpf_cnpj_parte,
            'valor_compensado': float(self.valor_compensado) if self.valor_compensado is not None else 0,
            'valor_efetivo': self.valor_efetivo,
        }


# =============================================================================
# 7b. COMPENSACOES (Saida <-> Entrada Empresa)
# =============================================================================
class PessoalCompensacao(db.Model):
    """Pareamento N:M entre uma transacao de SAIDA e uma ENTRADA.

    Um depósito transitório alto (ex: R$ 200k entra, R$ 200k sai no mesmo periodo)
    e "cancelado" via compensacao: a saida consome X reais de uma entrada, reduzindo
    valor_efetivo de ambas. Quando residuo = 0, excluir_relatorio pode ser ligado.

    Auditoria completa: quem criou, quando, observacao, e toda reversao preservada
    (status = 'REVERTIDA' em vez de DELETE).
    """
    __tablename__ = 'pessoal_compensacoes'

    id = db.Column(db.Integer, primary_key=True)
    saida_id = db.Column(
        db.Integer, db.ForeignKey('pessoal_transacoes.id', ondelete='CASCADE'),
        nullable=False,
    )
    entrada_id = db.Column(
        db.Integer, db.ForeignKey('pessoal_transacoes.id', ondelete='CASCADE'),
        nullable=False,
    )
    valor_compensado = db.Column(db.Numeric(15, 2), nullable=False)
    # Residuos apos ESTA compensacao ser aplicada (snapshot no momento da criacao).
    residuo_saida = db.Column(db.Numeric(15, 2), nullable=False)
    residuo_entrada = db.Column(db.Numeric(15, 2), nullable=False)
    origem = db.Column(db.String(10), nullable=False, default='manual')  # auto | manual
    status = db.Column(db.String(10), nullable=False, default='ATIVA')   # ATIVA | REVERTIDA
    observacao = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por = db.Column(db.String(100))
    revertido_em = db.Column(db.DateTime)
    revertido_por = db.Column(db.String(100))

    # Relacionamentos
    saida = db.relationship(
        'PessoalTransacao', foreign_keys=[saida_id],
        backref=db.backref('compensacoes_como_saida', lazy='dynamic'),
    )
    entrada = db.relationship(
        'PessoalTransacao', foreign_keys=[entrada_id],
        backref=db.backref('compensacoes_como_entrada', lazy='dynamic'),
    )

    __table_args__ = (
        db.CheckConstraint('valor_compensado > 0', name='ck_compensacoes_valor_positivo'),
        db.CheckConstraint("origem IN ('auto', 'manual')", name='ck_compensacoes_origem'),
        db.CheckConstraint("status IN ('ATIVA', 'REVERTIDA')", name='ck_compensacoes_status'),
        db.CheckConstraint('saida_id <> entrada_id', name='ck_compensacoes_saida_diff_entrada'),
    )

    def __repr__(self):
        return f'<PessoalCompensacao #{self.id} saida={self.saida_id} entrada={self.entrada_id} R${self.valor_compensado}>'

    def to_dict(self):
        return {
            'id': self.id,
            'saida_id': self.saida_id,
            'entrada_id': self.entrada_id,
            'valor_compensado': float(self.valor_compensado) if self.valor_compensado else 0,
            'residuo_saida': float(self.residuo_saida) if self.residuo_saida is not None else 0,
            'residuo_entrada': float(self.residuo_entrada) if self.residuo_entrada is not None else 0,
            'origem': self.origem,
            'status': self.status,
            'observacao': self.observacao,
            'criado_em': self.criado_em.strftime('%d/%m/%Y %H:%M') if self.criado_em else None,
            'criado_por': self.criado_por,
            'revertido_em': self.revertido_em.strftime('%d/%m/%Y %H:%M') if self.revertido_em else None,
            'revertido_por': self.revertido_por,
        }


# =============================================================================
# 8. ORCAMENTOS
# =============================================================================
class PessoalOrcamento(db.Model):
    __tablename__ = 'pessoal_orcamentos'

    id = db.Column(db.Integer, primary_key=True)
    ano_mes = db.Column(db.Date, nullable=False)  # Primeiro dia do mes (ex: 2026-04-01)
    categoria_id = db.Column(db.Integer, db.ForeignKey('pessoal_categorias.id'), nullable=True)
    valor_limite = db.Column(db.Numeric(15, 2), nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    # Partial unique indexes definidos via migration (NULL handling no PostgreSQL)

    def __repr__(self):
        tipo = 'GLOBAL' if self.categoria_id is None else f'cat={self.categoria_id}'
        return f'<PessoalOrcamento {self.ano_mes} {tipo} R${self.valor_limite}>'

    def to_dict(self):
        return {
            'id': self.id,
            'ano_mes': self.ano_mes.isoformat() if self.ano_mes else None,
            'categoria_id': self.categoria_id,
            'valor_limite': float(self.valor_limite) if self.valor_limite else 0,
        }


# =============================================================================
# 9. GRUPOS DE ANALISE (seleção de categorias salva pelo usuário)
# =============================================================================
class PessoalGrupoAnalise(db.Model):
    """Agrupamento customizado de categorias para analise cruzada.

    Permite ao usuario salvar uma selecao de categorias (ex: "Alimentacao fora"
    = restaurante + delivery + lanche) e analisar/expandir o extrato delas em
    conjunto.
    """
    __tablename__ = 'pessoal_grupos_analise'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    descricao = db.Column(db.String(300))
    cor = db.Column(db.String(20))  # ex: '#3b82f6' (opcional, para grafico)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    categorias = db.relationship(
        'PessoalCategoria',
        secondary='pessoal_grupos_analise_categorias',
        backref='grupos_analise',
    )

    def __repr__(self):
        return f'<PessoalGrupoAnalise {self.nome}>'

    def to_dict(self, incluir_categorias=True):
        d = {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'cor': self.cor,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
        }
        if incluir_categorias:
            d['categorias'] = [
                {'id': c.id, 'nome': c.nome, 'grupo': c.grupo, 'icone': c.icone}
                for c in self.categorias
            ]
            d['categoria_ids'] = [c.id for c in self.categorias]
        return d


# Tabela de ligacao N:N grupo <-> categoria
pessoal_grupos_analise_categorias = db.Table(
    'pessoal_grupos_analise_categorias',
    db.Column('grupo_id', db.Integer,
              db.ForeignKey('pessoal_grupos_analise.id', ondelete='CASCADE'),
              primary_key=True),
    db.Column('categoria_id', db.Integer,
              db.ForeignKey('pessoal_categorias.id', ondelete='CASCADE'),
              primary_key=True),
    Index('idx_pessoal_gac_categoria', 'categoria_id'),
)


# =============================================================================
# STAGING PLUGGY — 4 tabelas para Open Finance (Fase 1)
# =============================================================================
# Recebem dados fieis ao payload Pluggy. NAO tocam PessoalTransacao/PessoalConta.
# Migracao para modelos principais ocorre em fase posterior (apos dry-run validado).
# =============================================================================

class PessoalPluggyItem(db.Model):
    """Conexao Pluggy (item) = 1 banco conectado via OAuth/Open Finance."""
    __tablename__ = 'pessoal_pluggy_items'

    id = db.Column(db.Integer, primary_key=True)
    pluggy_item_id = db.Column(db.String(50), nullable=False, unique=True)
    # client_user_id = str(User.id). NAO e FK — controle via USUARIOS_PESSOAL
    client_user_id = db.Column(db.String(20), nullable=False, index=True)
    connector_id = db.Column(db.Integer, nullable=False)
    connector_name = db.Column(db.String(100))
    # UPDATING | UPDATED | LOGIN_ERROR | OUTDATED | WAITING_USER_INPUT
    status = db.Column(db.String(30), nullable=False, index=True)
    execution_status = db.Column(db.String(50))
    consent_expires_at = db.Column(db.DateTime)
    ultimo_sync = db.Column(db.DateTime)
    ultimo_webhook_em = db.Column(db.DateTime)
    erro_mensagem = db.Column(db.Text)
    payload_raw = db.Column(JSONB)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive,
                              onupdate=agora_utc_naive, nullable=False)

    accounts = db.relationship('PessoalPluggyAccount', backref='item',
                               lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<PessoalPluggyItem {self.pluggy_item_id} user={self.client_user_id} {self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'pluggy_item_id': self.pluggy_item_id,
            'client_user_id': self.client_user_id,
            'connector_id': self.connector_id,
            'connector_name': self.connector_name,
            'status': self.status,
            'execution_status': self.execution_status,
            'consent_expires_at': (
                self.consent_expires_at.isoformat() if self.consent_expires_at else None
            ),
            'ultimo_sync': self.ultimo_sync.isoformat() if self.ultimo_sync else None,
            'ultimo_webhook_em': (
                self.ultimo_webhook_em.isoformat() if self.ultimo_webhook_em else None
            ),
            'erro_mensagem': self.erro_mensagem,
        }


class PessoalPluggyAccount(db.Model):
    """Conta Pluggy dentro de um item (BANK conta corrente ou CREDIT cartao)."""
    __tablename__ = 'pessoal_pluggy_accounts'

    id = db.Column(db.Integer, primary_key=True)
    pluggy_item_pk = db.Column(
        db.Integer, db.ForeignKey('pessoal_pluggy_items.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    pluggy_account_id = db.Column(db.String(50), nullable=False, unique=True)
    type = db.Column(db.String(10), nullable=False, index=True)  # BANK | CREDIT
    subtype = db.Column(db.String(30))  # CHECKING_ACCOUNT | SAVINGS_ACCOUNT | CREDIT_CARD
    # BANK: "0001/12345-0"  |  CREDIT: 4 ultimos digitos ("1234")
    number = db.Column(db.String(50))
    name = db.Column(db.String(200))
    marketing_name = db.Column(db.String(200))
    owner_name = db.Column(db.String(200))
    tax_number = db.Column(db.String(30))
    # BANK: saldo conta. CREDIT: saldo devedor (nao mapear para Transacao.saldo)
    balance = db.Column(db.Numeric(15, 2))
    currency_code = db.Column(db.String(3), default='BRL')
    bank_data = db.Column(JSONB)    # transferNumber, closingBalance
    credit_data = db.Column(JSONB)  # level, brand, dueDate, creditLimit, minimumPayment
    payload_raw = db.Column(JSONB)
    # Vinculo pos-aprovacao (Fase 4)
    conta_pessoal_id = db.Column(
        db.Integer, db.ForeignKey('pessoal_contas.id', ondelete='SET NULL')
    )
    conta_vinculada_em = db.Column(db.DateTime)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive,
                              onupdate=agora_utc_naive, nullable=False)

    transacoes_stg = db.relationship(
        'PessoalPluggyTransacaoStg', backref='account',
        lazy='dynamic', cascade='all, delete-orphan',
    )
    conta_pessoal = db.relationship('PessoalConta', foreign_keys=[conta_pessoal_id])

    def __repr__(self):
        return f'<PessoalPluggyAccount {self.pluggy_account_id} {self.type} {self.number}>'

    def to_dict(self):
        return {
            'id': self.id,
            'pluggy_item_pk': self.pluggy_item_pk,
            'pluggy_account_id': self.pluggy_account_id,
            'type': self.type,
            'subtype': self.subtype,
            'number': self.number,
            'name': self.name,
            'marketing_name': self.marketing_name,
            'owner_name': self.owner_name,
            'tax_number': self.tax_number,
            'balance': float(self.balance) if self.balance is not None else None,
            'currency_code': self.currency_code,
            'bank_data': self.bank_data,
            'credit_data': self.credit_data,
            'conta_pessoal_id': self.conta_pessoal_id,
            'conta_vinculada_em': (
                self.conta_vinculada_em.isoformat() if self.conta_vinculada_em else None
            ),
        }


class PessoalPluggyTransacaoStg(db.Model):
    """Staging de transacoes Pluggy — fiel ao payload, sem adapter aplicado.

    ALERTA 1: amount e signed. BANK: +entrada/-saida. CREDIT_CARD: +compra/-estorno.
    O adapter (pluggy_adapter.py, Fase 3) trata a divergencia antes de migrar para
    PessoalTransacao.
    """
    __tablename__ = 'pessoal_pluggy_transacoes_stg'

    id = db.Column(db.Integer, primary_key=True)
    pluggy_account_pk = db.Column(
        db.Integer, db.ForeignKey('pessoal_pluggy_accounts.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    pluggy_transaction_id = db.Column(db.String(64), nullable=False, unique=True)
    # Core (fiel ao payload)
    date = db.Column(db.DateTime, nullable=False, index=True)
    description = db.Column(db.String(500))
    description_raw = db.Column(db.String(500))
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    amount_in_account_currency = db.Column(db.Numeric(15, 2))
    currency_code = db.Column(db.String(3))
    balance = db.Column(db.Numeric(15, 2))
    category = db.Column(db.String(100))
    category_id = db.Column(db.String(20))
    category_translated = db.Column(db.String(100))
    provider_code = db.Column(db.String(100))
    provider_id = db.Column(db.String(100))
    type = db.Column(db.String(10))   # CREDIT | DEBIT
    status = db.Column(db.String(20), index=True)  # POSTED | PENDING
    operation_type = db.Column(db.String(30))  # TED | PIX | BOLETO | ...
    # Nested
    payment_data = db.Column(JSONB)
    credit_card_metadata = db.Column(JSONB)
    merchant = db.Column(JSONB)
    payload_raw = db.Column(JSONB, nullable=False)
    # Controle do staging
    visto_em_sync_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    # PENDENTE | DRY_RUN | APROVADO | MIGRADO | REPROVADO | IGNORAR
    status_processamento = db.Column(
        db.String(20), nullable=False, default='PENDENTE', index=True,
    )
    # Vinculo pos-migracao
    transacao_pessoal_id = db.Column(
        db.Integer, db.ForeignKey('pessoal_transacoes.id', ondelete='SET NULL'),
    )
    migrado_em = db.Column(db.DateTime)
    observacao_migracao = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive,
                              onupdate=agora_utc_naive, nullable=False)

    transacao_pessoal = db.relationship(
        'PessoalTransacao', foreign_keys=[transacao_pessoal_id]
    )

    __table_args__ = (
        db.CheckConstraint(
            "status_processamento IN ('PENDENTE', 'DRY_RUN', 'APROVADO', "
            "'MIGRADO', 'REPROVADO', 'IGNORAR')",
            name='ck_pluggy_stg_status_proc',
        ),
        Index(
            'idx_pluggy_stg_transacao', 'transacao_pessoal_id',
            postgresql_where=db.text('transacao_pessoal_id IS NOT NULL'),
        ),
    )

    def __repr__(self):
        return (
            f'<PluggyTxStg {self.pluggy_transaction_id} {self.date} '
            f'R${self.amount} {self.status} [{self.status_processamento}]>'
        )

    def to_dict(self, incluir_payload_raw: bool = False):
        d = {
            'id': self.id,
            'pluggy_account_pk': self.pluggy_account_pk,
            'pluggy_transaction_id': self.pluggy_transaction_id,
            'date': self.date.isoformat() if self.date else None,
            'description': self.description,
            'description_raw': self.description_raw,
            'amount': float(self.amount) if self.amount is not None else None,
            'amount_in_account_currency': (
                float(self.amount_in_account_currency)
                if self.amount_in_account_currency is not None else None
            ),
            'currency_code': self.currency_code,
            'balance': float(self.balance) if self.balance is not None else None,
            'category': self.category,
            'category_id': self.category_id,
            'category_translated': self.category_translated,
            'provider_code': self.provider_code,
            'provider_id': self.provider_id,
            'type': self.type,
            'status': self.status,
            'operation_type': self.operation_type,
            'payment_data': self.payment_data,
            'credit_card_metadata': self.credit_card_metadata,
            'merchant': self.merchant,
            'status_processamento': self.status_processamento,
            'transacao_pessoal_id': self.transacao_pessoal_id,
            'migrado_em': self.migrado_em.isoformat() if self.migrado_em else None,
            'observacao_migracao': self.observacao_migracao,
        }
        if incluir_payload_raw:
            d['payload_raw'] = self.payload_raw
        return d


class PessoalPluggyCategoriaMap(db.Model):
    """Mapeia categoryId hierarquico Pluggy para PessoalCategoria local.

    Exemplo: pluggy_category_id='05080000' (Transfer - TED) -> pessoal_categoria_id
    Codigos Pluggy sao 8 digitos, com parent_id tambem 8 digitos (hierarquia 2 niveis).
    """
    __tablename__ = 'pessoal_pluggy_categorias_map'

    id = db.Column(db.Integer, primary_key=True)
    pluggy_category_id = db.Column(db.String(20), nullable=False, unique=True)
    pluggy_category_description = db.Column(db.String(100))  # EN
    pluggy_category_translated = db.Column(db.String(100))   # PT
    pluggy_parent_id = db.Column(db.String(20), index=True)
    pessoal_categoria_id = db.Column(
        db.Integer, db.ForeignKey('pessoal_categorias.id', ondelete='SET NULL'),
        index=True,
    )
    confianca = db.Column(db.Numeric(5, 2), default=100)
    # manual | sugerida | aprovada | semente
    origem = db.Column(db.String(20), default='manual')
    observacao = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive,
                              onupdate=agora_utc_naive, nullable=False)

    pessoal_categoria = db.relationship('PessoalCategoria')

    __table_args__ = (
        db.CheckConstraint(
            "origem IN ('manual', 'sugerida', 'aprovada', 'semente')",
            name='ck_pluggy_cat_map_origem',
        ),
    )

    def __repr__(self):
        return (
            f'<PluggyCatMap {self.pluggy_category_id} "{self.pluggy_category_translated}" '
            f'-> cat_id={self.pessoal_categoria_id}>'
        )

    def to_dict(self):
        return {
            'id': self.id,
            'pluggy_category_id': self.pluggy_category_id,
            'pluggy_category_description': self.pluggy_category_description,
            'pluggy_category_translated': self.pluggy_category_translated,
            'pluggy_parent_id': self.pluggy_parent_id,
            'pessoal_categoria_id': self.pessoal_categoria_id,
            'confianca': float(self.confianca) if self.confianca else 100,
            'origem': self.origem,
            'observacao': self.observacao,
        }

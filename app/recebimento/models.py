"""
Models do Modulo de Recebimento - FASE 1: Validacao Fiscal
==========================================================

Tabelas:
- PerfilFiscalProdutoFornecedor: Baseline fiscal por produto/fornecedor
- DivergenciaFiscal: Divergencias que bloqueiam recebimento
- CadastroPrimeiraCompra: Validacao manual de 1a compra

Referencia: .claude/references/RECEBIMENTO_MATERIAIS.md
"""

from app import db
from datetime import datetime


class PerfilFiscalProdutoFornecedor(db.Model):
    """
    Baseline fiscal por produto/fornecedor.
    Criado na 1a compra ou atualizado apos aprovacao de divergencia.
    Usado para comparar novas NFs.
    """
    __tablename__ = 'perfil_fiscal_produto_fornecedor'

    id = db.Column(db.Integer, primary_key=True)

    # Identificacao (chave composta)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    cnpj_fornecedor = db.Column(db.String(20), nullable=False, index=True)

    # Dados fiscais esperados (baseline)
    ncm_esperado = db.Column(db.String(10), nullable=True)
    cfop_esperados = db.Column(db.Text, nullable=True)  # JSON: ["5101", "6101"]
    cst_icms_esperado = db.Column(db.String(5), nullable=True)
    aliquota_icms_esperada = db.Column(db.Numeric(5, 2), nullable=True)
    aliquota_icms_st_esperada = db.Column(db.Numeric(5, 2), nullable=True)
    aliquota_ipi_esperada = db.Column(db.Numeric(5, 2), nullable=True)

    # PIS
    cst_pis_esperado = db.Column(db.String(5), nullable=True)
    aliquota_pis_esperada = db.Column(db.Numeric(5, 2), nullable=True)

    # COFINS
    cst_cofins_esperado = db.Column(db.String(5), nullable=True)
    aliquota_cofins_esperada = db.Column(db.Numeric(5, 2), nullable=True)

    # Tolerancias especificas (sobrescreve padrao)
    tolerancia_bc_icms_pct = db.Column(db.Numeric(5, 2), default=2.0)
    tolerancia_bc_icms_st_pct = db.Column(db.Numeric(5, 2), default=2.0)
    tolerancia_tributos_pct = db.Column(db.Numeric(5, 2), default=5.0)

    # Historico (3 ultimas NFs usadas para criar/atualizar)
    ultimas_nfs_ids = db.Column(db.Text, nullable=True)  # JSON: [dfe_id1, dfe_id2, dfe_id3]

    # Auditoria
    criado_por = db.Column(db.String(100), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('cod_produto', 'cnpj_fornecedor', name='uq_perfil_fiscal_produto_fornecedor'),
    )

    def __repr__(self):
        return f'<PerfilFiscal {self.cod_produto} - {self.cnpj_fornecedor}>'


class DivergenciaFiscal(db.Model):
    """
    Divergencias fiscais identificadas na validacao.
    BLOQUEIA o recebimento ate resolucao de TODAS as pendentes.
    """
    __tablename__ = 'divergencia_fiscal'

    id = db.Column(db.Integer, primary_key=True)

    # Referencias Odoo
    odoo_dfe_id = db.Column(db.String(50), nullable=False, index=True)
    odoo_dfe_line_id = db.Column(db.String(50), nullable=True, index=True)

    # Dados da NF
    numero_nf = db.Column(db.String(20), nullable=True)
    serie_nf = db.Column(db.String(5), nullable=True)
    chave_nfe = db.Column(db.String(44), nullable=True)

    perfil_fiscal_id = db.Column(
        db.Integer,
        db.ForeignKey('perfil_fiscal_produto_fornecedor.id', ondelete='SET NULL'),
        nullable=True
    )

    # Identificacao do produto/fornecedor
    cod_produto = db.Column(db.String(50), nullable=False)
    nome_produto = db.Column(db.String(255), nullable=True)
    cnpj_fornecedor = db.Column(db.String(20), nullable=False)
    razao_fornecedor = db.Column(db.String(255), nullable=True)

    # Divergencia
    campo = db.Column(db.String(50), nullable=False)  # ncm, cfop, aliq_icms, etc
    campo_label = db.Column(db.String(100), nullable=True)  # "NCM", "% ICMS", etc
    valor_esperado = db.Column(db.String(100), nullable=True)
    valor_encontrado = db.Column(db.String(100), nullable=True)
    diferenca_percentual = db.Column(db.Numeric(10, 2), nullable=True)

    # Analise IA (se aplicavel)
    analise_ia = db.Column(db.Text, nullable=True)
    contexto_ia = db.Column(db.Text, nullable=True)  # Info complementar usada

    # Resolucao
    status = db.Column(db.String(20), default='pendente', nullable=False, index=True)
    # Valores: pendente, aprovada, rejeitada
    resolucao = db.Column(db.String(50), nullable=True)
    # Valores: aprovar_manter, aprovar_atualizar, rejeitar
    atualizar_baseline = db.Column(db.Boolean, default=False)
    justificativa = db.Column(db.Text, nullable=True)
    resolvido_por = db.Column(db.String(100), nullable=True)
    resolvido_em = db.Column(db.DateTime, nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento
    perfil_fiscal = db.relationship(
        'PerfilFiscalProdutoFornecedor',
        backref=db.backref('divergencias', lazy='dynamic')
    )

    def __repr__(self):
        return f'<DivergenciaFiscal {self.id} - {self.campo} ({self.status})>'


class CadastroPrimeiraCompra(db.Model):
    """
    Registro de validacao de 1a compra (produto/fornecedor sem historico).
    Aguarda validacao do fiscal antes de criar PerfilFiscalProdutoFornecedor.
    """
    __tablename__ = 'cadastro_primeira_compra'

    id = db.Column(db.Integer, primary_key=True)

    # Referencias Odoo
    odoo_dfe_id = db.Column(db.String(50), nullable=False, index=True)
    odoo_dfe_line_id = db.Column(db.String(50), nullable=True)

    # Dados da NF
    numero_nf = db.Column(db.String(20), nullable=True)
    serie_nf = db.Column(db.String(5), nullable=True)
    chave_nfe = db.Column(db.String(44), nullable=True)

    # Identificacao
    cod_produto = db.Column(db.String(50), nullable=False)
    nome_produto = db.Column(db.String(255), nullable=True)
    cnpj_fornecedor = db.Column(db.String(20), nullable=False)
    razao_fornecedor = db.Column(db.String(255), nullable=True)

    # Dados do produto/item da NF
    quantidade = db.Column(db.Numeric(15, 4), nullable=True)
    unidade_medida = db.Column(db.String(10), nullable=True)
    valor_unitario = db.Column(db.Numeric(15, 4), nullable=True)
    valor_total = db.Column(db.Numeric(15, 2), nullable=True)
    valor_icms = db.Column(db.Numeric(15, 2), nullable=True)
    valor_icms_st = db.Column(db.Numeric(15, 2), nullable=True)
    valor_ipi = db.Column(db.Numeric(15, 2), nullable=True)

    # Dados fiscais da NF (para validacao manual)
    ncm = db.Column(db.String(10), nullable=True)
    cfop = db.Column(db.String(10), nullable=True)
    cst_icms = db.Column(db.String(5), nullable=True)
    aliquota_icms = db.Column(db.Numeric(5, 2), nullable=True)
    aliquota_icms_st = db.Column(db.Numeric(5, 2), nullable=True)
    aliquota_ipi = db.Column(db.Numeric(5, 2), nullable=True)
    bc_icms = db.Column(db.Numeric(15, 2), nullable=True)
    bc_icms_st = db.Column(db.Numeric(15, 2), nullable=True)
    valor_tributos_aprox = db.Column(db.Numeric(15, 2), nullable=True)

    # PIS
    cst_pis = db.Column(db.String(5), nullable=True)
    aliquota_pis = db.Column(db.Numeric(5, 2), nullable=True)
    bc_pis = db.Column(db.Numeric(15, 2), nullable=True)

    # COFINS
    cst_cofins = db.Column(db.String(5), nullable=True)
    aliquota_cofins = db.Column(db.Numeric(5, 2), nullable=True)
    bc_cofins = db.Column(db.Numeric(15, 2), nullable=True)

    info_complementar = db.Column(db.Text, nullable=True)

    # Status
    status = db.Column(db.String(20), default='pendente', nullable=False, index=True)
    # Valores: pendente, validado, rejeitado
    validado_por = db.Column(db.String(100), nullable=True)
    validado_em = db.Column(db.DateTime, nullable=True)
    observacao = db.Column(db.Text, nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<CadastroPrimeiraCompra {self.id} - {self.cod_produto} ({self.status})>'


class ValidacaoFiscalDfe(db.Model):
    """
    Controle de validacao fiscal por DFE.
    Registra status de cada NF processada pelo scheduler.

    Status:
    - pendente: Aguardando validacao (nunca processado)
    - validando: Em processamento
    - aprovado: Todas as linhas OK
    - bloqueado: Tem divergencia pendente
    - primeira_compra: Tem cadastro 1a compra pendente
    - erro: Falha no processamento
    """
    __tablename__ = 'validacao_fiscal_dfe'

    id = db.Column(db.Integer, primary_key=True)

    # Identificacao do DFE (Odoo)
    odoo_dfe_id = db.Column(db.Integer, nullable=False, unique=True, index=True)
    numero_nf = db.Column(db.String(20), nullable=True)
    chave_nfe = db.Column(db.String(44), nullable=True, index=True)

    # Fornecedor
    cnpj_fornecedor = db.Column(db.String(20), nullable=True, index=True)
    razao_fornecedor = db.Column(db.String(255), nullable=True)

    # Status da validacao
    status = db.Column(db.String(20), default='pendente', nullable=False, index=True)
    # Valores: pendente, validando, aprovado, bloqueado, primeira_compra, erro

    # Contadores
    total_linhas = db.Column(db.Integer, default=0)
    linhas_aprovadas = db.Column(db.Integer, default=0)
    linhas_divergentes = db.Column(db.Integer, default=0)
    linhas_primeira_compra = db.Column(db.Integer, default=0)

    # Detalhes de erro (se houver)
    erro_mensagem = db.Column(db.Text, nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    validado_em = db.Column(db.DateTime, nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ValidacaoFiscalDfe {self.odoo_dfe_id} ({self.status})>'

    @property
    def pode_prosseguir(self):
        """Retorna True se a NF pode prosseguir no fluxo"""
        return self.status == 'aprovado'

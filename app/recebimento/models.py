"""
Models do Modulo de Recebimento
===============================

FASE 1 - Validacao Fiscal:
- PerfilFiscalProdutoFornecedor: Baseline fiscal por produto/fornecedor
- DivergenciaFiscal: Divergencias que bloqueiam recebimento
- CadastroPrimeiraCompra: Validacao manual de 1a compra
- ValidacaoFiscalDfe: Controle de status por DFE
- NcmIbsCbsValidado: NCMs validados para IBS/CBS (2026)
- PendenciaFiscalIbsCbs: Pendencias de IBS/CBS

FASE 2 - Vinculacao NF x PO:
- ProdutoFornecedorDepara: De-Para de produtos (codigo fornecedor -> interno)
- MatchNfPoItem: Resultado do match por item da NF
- DivergenciaNfPo: Divergencias NF x PO para resolucao manual
- ValidacaoNfPoDfe: Controle de status de validacao NF x PO

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

    # Localizacao do fornecedor
    uf_fornecedor = db.Column(db.String(2), nullable=True)
    cidade_fornecedor = db.Column(db.String(100), nullable=True)

    # Regime Tributario do fornecedor (CRT da NF-e)
    # 1=Simples Nacional, 2=Simples Nacional excesso sublimite, 3=Regime Normal
    regime_tributario = db.Column(db.String(1), nullable=True)

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

    def to_dict(self):
        """Serializa para dicionario (usado no template para JSON)"""
        from decimal import Decimal

        def to_float(val):
            if val is None:
                return None
            if isinstance(val, Decimal):
                return float(val)
            return val

        return {
            'id': self.id,
            'odoo_dfe_id': self.odoo_dfe_id,
            'odoo_dfe_line_id': self.odoo_dfe_line_id,
            'numero_nf': self.numero_nf,
            'serie_nf': self.serie_nf,
            'chave_nfe': self.chave_nfe,
            'perfil_fiscal_id': self.perfil_fiscal_id,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'cnpj_fornecedor': self.cnpj_fornecedor,
            'razao_fornecedor': self.razao_fornecedor,
            'uf_fornecedor': self.uf_fornecedor,
            'cidade_fornecedor': self.cidade_fornecedor,
            'regime_tributario': self.regime_tributario,
            'campo': self.campo,
            'campo_label': self.campo_label,
            'valor_esperado': self.valor_esperado,
            'valor_encontrado': self.valor_encontrado,
            'diferenca_percentual': to_float(self.diferenca_percentual),
            'status': self.status,
            'resolucao': self.resolucao,
            'atualizar_baseline': self.atualizar_baseline,
            'justificativa': self.justificativa,
            'resolvido_por': self.resolvido_por,
            'resolvido_em': self.resolvido_em.isoformat() if self.resolvido_em else None,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None
        }


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

    # Localizacao do fornecedor
    uf_fornecedor = db.Column(db.String(2), nullable=True)
    cidade_fornecedor = db.Column(db.String(100), nullable=True)

    # Regime Tributario do fornecedor (CRT da NF-e)
    # 1=Simples Nacional, 2=Simples Nacional excesso sublimite, 3=Regime Normal
    regime_tributario = db.Column(db.String(1), nullable=True)

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

    # PIS - Valor
    valor_pis = db.Column(db.Numeric(15, 2), nullable=True)

    # COFINS
    cst_cofins = db.Column(db.String(5), nullable=True)
    aliquota_cofins = db.Column(db.Numeric(5, 2), nullable=True)
    bc_cofins = db.Column(db.Numeric(15, 2), nullable=True)
    valor_cofins = db.Column(db.Numeric(15, 2), nullable=True)

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


class NcmIbsCbsValidado(db.Model):
    """
    NCMs validados pelo departamento fiscal para IBS/CBS.
    Armazena os 4 primeiros digitos do NCM e aliquotas esperadas.

    Reforma Tributaria 2026:
    - IBS (Imposto sobre Bens e Servicos) = UF + Municipio
    - CBS (Contribuicao sobre Bens e Servicos) = Federal

    Uso:
    - NF de fornecedor nao optante do Simples que contenha produto
      com NCM nesta tabela DEVE destacar IBS/CBS
    - Se nao destacar, gera pendencia fiscal
    """
    __tablename__ = 'ncm_ibscbs_validado'

    id = db.Column(db.Integer, primary_key=True)

    # NCM (4 primeiros digitos)
    ncm_prefixo = db.Column(db.String(4), nullable=False, unique=True, index=True)
    descricao_ncm = db.Column(db.String(255), nullable=True)

    # Aliquotas esperadas (para validacao)
    aliquota_ibs_uf = db.Column(db.Numeric(5, 2), nullable=True)      # % IBS UF
    aliquota_ibs_mun = db.Column(db.Numeric(5, 2), nullable=True)     # % IBS Municipio
    aliquota_cbs = db.Column(db.Numeric(5, 2), nullable=True)         # % CBS Federal

    # Reducao de aliquota (se aplicavel)
    reducao_aliquota = db.Column(db.Numeric(5, 2), nullable=True)     # % Reducao

    # CST esperado
    cst_esperado = db.Column(db.String(10), nullable=True)

    # Classificacao tributaria esperada (codigo do Odoo)
    class_trib_codigo = db.Column(db.String(20), nullable=True)

    # Observacoes
    observacao = db.Column(db.Text, nullable=True)

    # Controle
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    validado_por = db.Column(db.String(100), nullable=True)
    validado_em = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<NcmIbsCbsValidado {self.ncm_prefixo}>'


class PendenciaFiscalIbsCbs(db.Model):
    """
    Pendencias fiscais de IBS/CBS.
    Registra documentos de fornecedores nao optantes do Simples
    que deveriam destacar IBS/CBS mas nao destacaram.

    Tipos de documento:
    - CTe: Valida apenas pelo regime tributario
    - NF-e: Valida pelo regime + NCM (4 primeiros digitos)

    Status:
    - pendente: Aguardando analise fiscal
    - aprovado: Fornecedor isento/validado manualmente
    - rejeitado: Documento devolvido ao fornecedor
    """
    __tablename__ = 'pendencia_fiscal_ibscbs'

    id = db.Column(db.Integer, primary_key=True)

    # Tipo de documento
    TIPO_DOC_CHOICES = ['CTe', 'NF-e']
    tipo_documento = db.Column(db.String(10), nullable=False, index=True)

    # Identificacao do documento
    chave_acesso = db.Column(db.String(44), nullable=False, unique=True, index=True)
    numero_documento = db.Column(db.String(20), nullable=True)
    serie = db.Column(db.String(5), nullable=True)
    data_emissao = db.Column(db.Date, nullable=True)

    # Referencia ao DFE do Odoo
    odoo_dfe_id = db.Column(db.Integer, nullable=True, index=True)

    # Referencia ao CTe local (se for CTe)
    cte_id = db.Column(db.Integer, db.ForeignKey('conhecimento_transporte.id'), nullable=True, index=True)

    # Fornecedor
    cnpj_fornecedor = db.Column(db.String(20), nullable=False, index=True)
    razao_fornecedor = db.Column(db.String(255), nullable=True)
    uf_fornecedor = db.Column(db.String(2), nullable=True)

    # Regime tributario do fornecedor
    # 1=Simples Nacional, 2=Simples excesso sublimite, 3=Regime Normal
    regime_tributario = db.Column(db.String(1), nullable=True)
    regime_tributario_descricao = db.Column(db.String(50), nullable=True)

    # NCM (apenas para NF-e)
    ncm = db.Column(db.String(10), nullable=True)
    ncm_prefixo = db.Column(db.String(4), nullable=True, index=True)  # 4 primeiros digitos

    # Valores do documento
    valor_total = db.Column(db.Numeric(15, 2), nullable=True)
    valor_base_calculo = db.Column(db.Numeric(15, 2), nullable=True)

    # Valores IBS/CBS encontrados (zerados ou ausentes = pendencia)
    ibscbs_cst = db.Column(db.String(10), nullable=True)
    ibscbs_class_trib = db.Column(db.String(20), nullable=True)
    ibscbs_base = db.Column(db.Numeric(15, 2), nullable=True)
    ibs_uf_aliq = db.Column(db.Numeric(5, 2), nullable=True)
    ibs_uf_valor = db.Column(db.Numeric(15, 2), nullable=True)
    ibs_mun_aliq = db.Column(db.Numeric(5, 2), nullable=True)
    ibs_mun_valor = db.Column(db.Numeric(15, 2), nullable=True)
    ibs_total = db.Column(db.Numeric(15, 2), nullable=True)
    cbs_aliq = db.Column(db.Numeric(5, 2), nullable=True)
    cbs_valor = db.Column(db.Numeric(15, 2), nullable=True)

    # Motivo da pendencia
    motivo_pendencia = db.Column(db.String(100), nullable=False)
    # Valores: 'nao_destacou', 'valor_zerado', 'cst_incorreto', 'aliquota_divergente'

    detalhes_pendencia = db.Column(db.Text, nullable=True)

    # Status da pendencia
    STATUS_CHOICES = ['pendente', 'aprovado', 'rejeitado']
    status = db.Column(db.String(20), default='pendente', nullable=False, index=True)

    # Resolucao
    resolucao = db.Column(db.String(50), nullable=True)
    # Valores: 'fornecedor_isento', 'ncm_nao_tributa', 'erro_sistema', 'devolvido_fornecedor'
    justificativa = db.Column(db.Text, nullable=True)
    resolvido_por = db.Column(db.String(100), nullable=True)
    resolvido_em = db.Column(db.DateTime, nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), default='SISTEMA')

    # Relacionamento
    cte = db.relationship('ConhecimentoTransporte', backref='pendencias_ibscbs')

    def __repr__(self):
        return f'<PendenciaFiscalIbsCbs {self.tipo_documento} {self.numero_documento} ({self.status})>'

    @staticmethod
    def get_regime_descricao(codigo):
        """Retorna descricao do regime tributario"""
        regimes = {
            '1': 'Simples Nacional',
            '2': 'Simples Nacional - Excesso Sublimite',
            '3': 'Regime Normal'
        }
        return regimes.get(codigo, 'Desconhecido')

    def to_dict(self):
        """Serializa para dicionario"""
        return {
            'id': self.id,
            'tipo_documento': self.tipo_documento,
            'chave_acesso': self.chave_acesso,
            'numero_documento': self.numero_documento,
            'data_emissao': self.data_emissao.isoformat() if self.data_emissao else None,
            'cnpj_fornecedor': self.cnpj_fornecedor,
            'razao_fornecedor': self.razao_fornecedor,
            'regime_tributario': self.regime_tributario,
            'regime_tributario_descricao': self.regime_tributario_descricao,
            'ncm': self.ncm,
            'ncm_prefixo': self.ncm_prefixo,
            'valor_total': float(self.valor_total) if self.valor_total else None,
            'motivo_pendencia': self.motivo_pendencia,
            'status': self.status,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None
        }


# =============================================================================
# FASE 2: Vinculacao NF x PO
# =============================================================================

class ProdutoFornecedorDepara(db.Model):
    """
    De-Para de produtos: converte codigo do fornecedor para codigo interno.

    Usado para:
    - Identificar produto interno a partir do codigo na NF do fornecedor
    - Converter unidade de medida (ex: ML -> Units com fator 1000)
    - Sincronizar bidirecionalmente com product.supplierinfo do Odoo

    Fluxo:
    1. NF chega com det_prod_cprod (codigo do fornecedor)
    2. Sistema busca nesta tabela por (cnpj_fornecedor, cod_produto_fornecedor)
    3. Retorna cod_produto_interno + fator_conversao para validar contra PO
    """
    __tablename__ = 'produto_fornecedor_depara'

    id = db.Column(db.Integer, primary_key=True)

    # Identificacao do fornecedor
    cnpj_fornecedor = db.Column(db.String(20), nullable=False, index=True)
    razao_fornecedor = db.Column(db.String(255), nullable=True)

    # Codigo do produto na NF do fornecedor
    cod_produto_fornecedor = db.Column(db.String(50), nullable=False, index=True)
    descricao_produto_fornecedor = db.Column(db.String(255), nullable=True)

    # Codigo do produto interno (Odoo)
    cod_produto_interno = db.Column(db.String(50), nullable=False, index=True)
    nome_produto_interno = db.Column(db.String(255), nullable=True)
    odoo_product_id = db.Column(db.Integer, nullable=True)

    # Conversao de Unidade de Medida
    um_fornecedor = db.Column(db.String(20), nullable=True)  # det_prod_ucom (ML, MI, MIL)
    um_interna = db.Column(db.String(20), default='UNITS')   # product_uom
    fator_conversao = db.Column(db.Numeric(10, 4), default=1.0000)  # 1000 para Milhar

    # Controle
    ativo = db.Column(db.Boolean, default=True)
    sincronizado_odoo = db.Column(db.Boolean, default=False)
    odoo_supplierinfo_id = db.Column(db.Integer, nullable=True)

    # Auditoria
    criado_por = db.Column(db.String(100), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('cnpj_fornecedor', 'cod_produto_fornecedor',
                            name='uq_depara_cnpj_cod_forn'),
    )

    def __repr__(self):
        return f'<ProdutoFornecedorDepara {self.cod_produto_fornecedor} -> {self.cod_produto_interno}>'

    def to_dict(self):
        """Serializa para dicionario"""
        return {
            'id': self.id,
            'cnpj_fornecedor': self.cnpj_fornecedor,
            'razao_fornecedor': self.razao_fornecedor,
            'cod_produto_fornecedor': self.cod_produto_fornecedor,
            'descricao_produto_fornecedor': self.descricao_produto_fornecedor,
            'cod_produto_interno': self.cod_produto_interno,
            'nome_produto_interno': self.nome_produto_interno,
            'odoo_product_id': self.odoo_product_id,
            'um_fornecedor': self.um_fornecedor,
            'um_interna': self.um_interna,
            'fator_conversao': float(self.fator_conversao) if self.fator_conversao else 1.0,
            'ativo': self.ativo,
            'sincronizado_odoo': self.sincronizado_odoo,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None
        }


class ValidacaoNfPoDfe(db.Model):
    """
    Controle de status de validacao NF x PO por DFE.

    Status:
    - pendente: Aguardando validacao
    - validando: Em processamento
    - aprovado: 100% itens com match (pronto para consolidar)
    - bloqueado: <100% itens com match (divergencias pendentes)
    - consolidado: POs foram ajustados/consolidados
    - erro: Falha no processamento

    IMPORTANTE: So executa acoes nos POs se status = 'aprovado' (100% match)
    """
    __tablename__ = 'validacao_nf_po_dfe'

    id = db.Column(db.Integer, primary_key=True)

    # Identificacao do DFE (Odoo)
    odoo_dfe_id = db.Column(db.Integer, nullable=False, unique=True, index=True)
    numero_nf = db.Column(db.String(20), nullable=True)
    serie_nf = db.Column(db.String(10), nullable=True)
    chave_nfe = db.Column(db.String(44), nullable=True, index=True)

    # Fornecedor
    cnpj_fornecedor = db.Column(db.String(20), nullable=True, index=True)
    razao_fornecedor = db.Column(db.String(255), nullable=True)

    # Dados da NF
    data_nf = db.Column(db.Date, nullable=True)
    valor_total_nf = db.Column(db.Numeric(15, 2), nullable=True)

    # Status da validacao
    status = db.Column(db.String(20), default='pendente', nullable=False, index=True)

    # Contadores de match
    total_itens = db.Column(db.Integer, default=0)
    itens_match = db.Column(db.Integer, default=0)
    itens_sem_depara = db.Column(db.Integer, default=0)
    itens_sem_po = db.Column(db.Integer, default=0)
    itens_preco_diverge = db.Column(db.Integer, default=0)
    itens_data_diverge = db.Column(db.Integer, default=0)
    itens_qtd_diverge = db.Column(db.Integer, default=0)

    # Resultado da consolidacao (se aprovado)
    po_consolidado_id = db.Column(db.Integer, nullable=True)
    po_consolidado_name = db.Column(db.String(50), nullable=True)
    pos_saldo_ids = db.Column(db.Text, nullable=True)      # JSON: [{"id": 123, "name": "PO00456"}]
    pos_cancelados_ids = db.Column(db.Text, nullable=True)  # JSON: [{"id": 124, "name": "PO00457"}]
    acao_executada = db.Column(db.JSON, nullable=True)     # Detalhes completos da acao

    # Controle de erro
    erro_mensagem = db.Column(db.Text, nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    validado_em = db.Column(db.DateTime, nullable=True)
    consolidado_em = db.Column(db.DateTime, nullable=True)
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relacionamentos
    itens_match_rel = db.relationship('MatchNfPoItem', backref='validacao',
                                      lazy='dynamic', cascade='all, delete-orphan')
    divergencias = db.relationship('DivergenciaNfPo', backref='validacao',
                                   lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ValidacaoNfPoDfe {self.odoo_dfe_id} ({self.status})>'

    @property
    def percentual_match(self):
        """Retorna percentual de itens com match"""
        if self.total_itens == 0:
            return 0
        return round((self.itens_match / self.total_itens) * 100, 1)

    @property
    def pode_consolidar(self):
        """Retorna True se pode executar consolidacao (100% match)"""
        return self.status == 'aprovado' and self.itens_match == self.total_itens

    def to_dict(self):
        """Serializa para dicionario"""
        import json
        return {
            'id': self.id,
            'odoo_dfe_id': self.odoo_dfe_id,
            'numero_nf': self.numero_nf,
            'serie_nf': self.serie_nf,
            'chave_nfe': self.chave_nfe,
            'cnpj_fornecedor': self.cnpj_fornecedor,
            'razao_fornecedor': self.razao_fornecedor,
            'data_nf': self.data_nf.isoformat() if self.data_nf else None,
            'valor_total_nf': float(self.valor_total_nf) if self.valor_total_nf else None,
            'status': self.status,
            'total_itens': self.total_itens,
            'itens_match': self.itens_match,
            'itens_sem_depara': self.itens_sem_depara,
            'itens_sem_po': self.itens_sem_po,
            'itens_preco_diverge': self.itens_preco_diverge,
            'itens_data_diverge': self.itens_data_diverge,
            'itens_qtd_diverge': self.itens_qtd_diverge,
            'percentual_match': self.percentual_match,
            'pode_consolidar': self.pode_consolidar,
            'po_consolidado_id': self.po_consolidado_id,
            'po_consolidado_name': self.po_consolidado_name,
            'pos_saldo_ids': json.loads(self.pos_saldo_ids) if self.pos_saldo_ids else [],
            'pos_cancelados_ids': json.loads(self.pos_cancelados_ids) if self.pos_cancelados_ids else [],
            'erro_mensagem': self.erro_mensagem,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'validado_em': self.validado_em.isoformat() if self.validado_em else None,
            'consolidado_em': self.consolidado_em.isoformat() if self.consolidado_em else None
        }


class MatchNfPoItem(db.Model):
    """
    Resultado do match de cada item da NF com PO.

    Registra para cada linha da NF:
    - Dados da NF (apos conversao de codigo/UM)
    - PO encontrado (se houver)
    - Status do match

    Status possíveis:
    - match: OK, encontrou PO compativel
    - sem_depara: Nao tem De-Para para o codigo do fornecedor
    - sem_po: Nao encontrou PO para o produto
    - preco_diverge: Preco da NF != Preco do PO (0% tolerancia)
    - data_diverge: Data fora da tolerancia (±2 dias uteis)
    - qtd_diverge: QTD NF > QTD PO + 10%
    """
    __tablename__ = 'match_nf_po_item'

    id = db.Column(db.Integer, primary_key=True)

    # FK para validacao
    validacao_id = db.Column(db.Integer, db.ForeignKey('validacao_nf_po_dfe.id',
                             ondelete='CASCADE'), nullable=False, index=True)

    # Identificacao da linha da NF (Odoo)
    odoo_dfe_line_id = db.Column(db.Integer, nullable=False, index=True)

    # Dados do produto na NF (original)
    cod_produto_fornecedor = db.Column(db.String(50), nullable=True)
    nome_produto = db.Column(db.String(255), nullable=True)
    um_nf = db.Column(db.String(20), nullable=True)

    # Dados convertidos (apos De-Para)
    cod_produto_interno = db.Column(db.String(50), nullable=True)
    fator_conversao = db.Column(db.Numeric(10, 4), nullable=True)

    # Valores da NF (apos conversao)
    qtd_nf = db.Column(db.Numeric(15, 3), nullable=True)
    preco_nf = db.Column(db.Numeric(15, 4), nullable=True)
    data_nf = db.Column(db.Date, nullable=True)

    # PO Match encontrado
    odoo_po_id = db.Column(db.Integer, nullable=True)
    odoo_po_name = db.Column(db.String(50), nullable=True)
    odoo_po_line_id = db.Column(db.Integer, nullable=True)
    qtd_po = db.Column(db.Numeric(15, 3), nullable=True)
    preco_po = db.Column(db.Numeric(15, 4), nullable=True)
    data_po = db.Column(db.Date, nullable=True)

    # Status do match
    status_match = db.Column(db.String(20), nullable=False, index=True)
    motivo_bloqueio = db.Column(db.Text, nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<MatchNfPoItem {self.odoo_dfe_line_id} ({self.status_match})>'

    def to_dict(self):
        """Serializa para dicionario"""
        return {
            'id': self.id,
            'validacao_id': self.validacao_id,
            'odoo_dfe_line_id': self.odoo_dfe_line_id,
            'cod_produto_fornecedor': self.cod_produto_fornecedor,
            'cod_produto_interno': self.cod_produto_interno,
            'nome_produto': self.nome_produto,
            'um_nf': self.um_nf,
            'fator_conversao': float(self.fator_conversao) if self.fator_conversao else None,
            'qtd_nf': float(self.qtd_nf) if self.qtd_nf else None,
            'preco_nf': float(self.preco_nf) if self.preco_nf else None,
            'data_nf': self.data_nf.isoformat() if self.data_nf else None,
            'odoo_po_id': self.odoo_po_id,
            'odoo_po_name': self.odoo_po_name,
            'odoo_po_line_id': self.odoo_po_line_id,
            'qtd_po': float(self.qtd_po) if self.qtd_po else None,
            'preco_po': float(self.preco_po) if self.preco_po else None,
            'data_po': self.data_po.isoformat() if self.data_po else None,
            'status_match': self.status_match,
            'motivo_bloqueio': self.motivo_bloqueio,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None
        }


class DivergenciaNfPo(db.Model):
    """
    Divergencias NF x PO para resolucao manual.

    Criada quando um item da NF nao faz match com PO.
    BLOQUEIA a NF ate resolucao de TODAS as divergencias.

    Tipos de divergencia:
    - sem_depara: Codigo do fornecedor nao cadastrado no De-Para
    - sem_po: Nao encontrou PO para o produto
    - preco: Preco da NF diferente do PO
    - quantidade: QTD NF > QTD PO + 10%
    - data_entrega: Data da NF fora da tolerancia (±2 dias uteis)

    Resolucoes possiveis:
    - criar_depara: Criar De-Para e reprocessar
    - aprovar_preco: Aprovar diferenca de preco
    - ajustar_po: Ajustar PO manualmente
    - rejeitar: Rejeitar NF / devolver ao fornecedor
    """
    __tablename__ = 'divergencia_nf_po'

    id = db.Column(db.Integer, primary_key=True)

    # FK para validacao
    validacao_id = db.Column(db.Integer, db.ForeignKey('validacao_nf_po_dfe.id',
                             ondelete='CASCADE'), nullable=False, index=True)

    # Referencias Odoo
    odoo_dfe_id = db.Column(db.Integer, nullable=False, index=True)
    odoo_dfe_line_id = db.Column(db.Integer, nullable=True)

    # Identificacao
    cnpj_fornecedor = db.Column(db.String(20), nullable=True)
    razao_fornecedor = db.Column(db.String(255), nullable=True)
    cod_produto_fornecedor = db.Column(db.String(50), nullable=True)
    cod_produto_interno = db.Column(db.String(50), nullable=True)
    nome_produto = db.Column(db.String(255), nullable=True)

    # Tipo da divergencia
    tipo_divergencia = db.Column(db.String(50), nullable=False, index=True)
    campo_label = db.Column(db.String(100), nullable=True)  # "Preco", "Quantidade", etc
    valor_nf = db.Column(db.String(100), nullable=True)
    valor_po = db.Column(db.String(100), nullable=True)
    diferenca_percentual = db.Column(db.Numeric(10, 2), nullable=True)

    # PO candidato (se houver)
    odoo_po_id = db.Column(db.Integer, nullable=True)
    odoo_po_name = db.Column(db.String(50), nullable=True)
    odoo_po_line_id = db.Column(db.Integer, nullable=True)

    # Resolucao
    status = db.Column(db.String(20), default='pendente', nullable=False, index=True)
    resolucao = db.Column(db.String(50), nullable=True)
    justificativa = db.Column(db.Text, nullable=True)
    resolvido_por = db.Column(db.String(100), nullable=True)
    resolvido_em = db.Column(db.DateTime, nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<DivergenciaNfPo {self.id} - {self.tipo_divergencia} ({self.status})>'

    def to_dict(self):
        """Serializa para dicionario"""
        return {
            'id': self.id,
            'validacao_id': self.validacao_id,
            'odoo_dfe_id': self.odoo_dfe_id,
            'odoo_dfe_line_id': self.odoo_dfe_line_id,
            'cnpj_fornecedor': self.cnpj_fornecedor,
            'razao_fornecedor': self.razao_fornecedor,
            'cod_produto_fornecedor': self.cod_produto_fornecedor,
            'cod_produto_interno': self.cod_produto_interno,
            'nome_produto': self.nome_produto,
            'tipo_divergencia': self.tipo_divergencia,
            'campo_label': self.campo_label,
            'valor_nf': self.valor_nf,
            'valor_po': self.valor_po,
            'diferenca_percentual': float(self.diferenca_percentual) if self.diferenca_percentual else None,
            'odoo_po_id': self.odoo_po_id,
            'odoo_po_name': self.odoo_po_name,
            'odoo_po_line_id': self.odoo_po_line_id,
            'status': self.status,
            'resolucao': self.resolucao,
            'justificativa': self.justificativa,
            'resolvido_por': self.resolvido_por,
            'resolvido_em': self.resolvido_em.isoformat() if self.resolvido_em else None,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None
        }

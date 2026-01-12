"""
Modelos do Sistema de Gestao de Devolucoes
==========================================

Modelos:
- NFDevolucao: Tabela principal unificada (registro + dados DFe)
- NFDevolucaoLinha: Linhas de produto da NFD
- OcorrenciaDevolucao: Tratativas Comercial/Logistica
- FreteDevolucao: Cotacao de frete de retorno
- ContagemDevolucao: Contagem por linha de produto
- AnexoOcorrencia: Emails e fotos
- DeParaProdutoCliente: Mapeamento de codigos por prefixo CNPJ

Criado em: 30/12/2024
"""
from datetime import datetime
from app import db
from app.utils.timezone import agora_brasil


# =============================================================================
# NFDevolucao - Tabela Principal Unificada
# =============================================================================

class NFDevolucao(db.Model):
    """
    Tabela principal de devolucoes - unifica registro inicial + dados DFe
    Similar ao ConhecimentoTransporte para CTes

    Fluxo:
    1. Monitoramento registra NFD manualmente (campos de registro inicial)
    2. Sistema importa NFD do Odoo (campos DFe + XML/PDF)
    3. Vincula registro manual com DFe importado
    """
    __tablename__ = 'nf_devolucao'

    id = db.Column(db.Integer, primary_key=True)

    # Vinculo com NF de venda original (EntregaMonitorada)
    entrega_monitorada_id = db.Column(
        db.Integer,
        db.ForeignKey('entregas_monitoradas.id'),
        nullable=True,
        index=True
    )

    # =========================================================================
    # DADOS DO REGISTRO INICIAL (preenchido pelo monitoramento)
    # =========================================================================
    numero_nfd = db.Column(db.String(20), nullable=False, index=True)
    data_registro = db.Column(db.DateTime, default=agora_brasil, nullable=False)

    # Motivo da devolucao
    MOTIVOS_DEVOLUCAO = [
        ('AVARIA', 'Avaria'),
        ('FALTA', 'Falta de Mercadoria'),
        ('SOBRA', 'Sobra de Mercadoria'),
        ('PRODUTO_ERRADO', 'Produto Errado'),
        ('VENCIDO', 'Produto Vencido'),
        ('PEDIDO_CANCELADO', 'Pedido Cancelado'),
        ('CLIENTE_RECUSOU', 'Cliente Recusou'),
        ('ENDERECO_NAO_ENCONTRADO', 'Endereco Nao Encontrado'),
        ('PROBLEMA_FISCAL', 'Problema Fiscal'),
        ('OUTROS', 'Outros'),
    ]
    motivo = db.Column(db.String(50), nullable=False)
    descricao_motivo = db.Column(db.Text, nullable=True)
    confianca_motivo = db.Column(db.Numeric(5, 4), nullable=True)  # 0.0000 a 1.0000 - Confiança da extração IA

    # Referencia da NF de venda
    numero_nf_venda = db.Column(db.String(20), nullable=True, index=True)

    # =========================================================================
    # DADOS DO DFe ODOO (preenchido na importacao)
    # =========================================================================
    odoo_dfe_id = db.Column(db.Integer, unique=True, nullable=True, index=True)
    odoo_ativo = db.Column(db.Boolean, nullable=True)
    odoo_name = db.Column(db.String(100), nullable=True)  # Ex: DFE/2025/15797
    odoo_status_codigo = db.Column(db.String(10), nullable=True)
    odoo_status_descricao = db.Column(db.String(100), nullable=True)

    # Chave de acesso e dados fiscais
    chave_nfd = db.Column(db.String(44), unique=True, nullable=True, index=True)
    serie_nfd = db.Column(db.String(10), nullable=True)
    data_emissao = db.Column(db.Date, nullable=True)
    data_entrada = db.Column(db.Date, nullable=True)

    # Valores
    valor_total = db.Column(db.Numeric(15, 2), nullable=True)
    valor_produtos = db.Column(db.Numeric(15, 2), nullable=True)

    # Cliente/Emitente (quem emitiu a NFD = cliente)
    cnpj_emitente = db.Column(db.String(20), nullable=True, index=True)
    nome_emitente = db.Column(db.String(255), nullable=True)
    ie_emitente = db.Column(db.String(20), nullable=True)
    uf_emitente = db.Column(db.String(2), nullable=True)
    municipio_emitente = db.Column(db.String(100), nullable=True)
    cep_emitente = db.Column(db.String(10), nullable=True)
    endereco_emitente = db.Column(db.String(255), nullable=True)

    # Destinatario (nos = Nacom)
    cnpj_destinatario = db.Column(db.String(20), nullable=True, index=True)
    nome_destinatario = db.Column(db.String(255), nullable=True)

    # =========================================================================
    # INFORMACOES COMPLEMENTARES (extraidas do XML - tag infCpl)
    # =========================================================================
    info_complementar = db.Column(db.Text, nullable=True)  # Texto livre do cliente

    # =========================================================================
    # ARQUIVOS (XML e PDF) - armazenados em S3
    # =========================================================================
    nfd_xml_path = db.Column(db.String(500), nullable=True)
    nfd_xml_nome_arquivo = db.Column(db.String(255), nullable=True)
    nfd_pdf_path = db.Column(db.String(500), nullable=True)
    nfd_pdf_nome_arquivo = db.Column(db.String(255), nullable=True)

    # =========================================================================
    # CONTROLE
    # =========================================================================
    sincronizado_odoo = db.Column(db.Boolean, default=False, nullable=False)
    data_sincronizacao = db.Column(db.DateTime, nullable=True)

    # Status do processamento
    STATUS_CHOICES = [
        ('REGISTRADA', 'Registrada'),
        ('VINCULADA_DFE', 'Vinculada ao DFe'),
        ('EM_TRATATIVA', 'Em Tratativa'),
        ('AGUARDANDO_RECEBIMENTO', 'Aguardando Recebimento'),
        ('RECEBIDA', 'Recebida'),
        ('CONTADA', 'Contada'),
        ('FINALIZADA', 'Finalizada'),
        ('CANCELADA', 'Cancelada'),
    ]
    status = db.Column(db.String(30), default='REGISTRADA', nullable=False, index=True)

    # Origem do registro (MONITORAMENTO = manual, ODOO = importado DFe)
    ORIGENS_REGISTRO = [
        ('MONITORAMENTO', 'Registro Manual no Monitoramento'),
        ('ODOO', 'Importado do Odoo (DFe)'),
    ]
    origem_registro = db.Column(db.String(20), default='MONITORAMENTO', nullable=False, index=True)

    # =========================================================================
    # TIPO DE DOCUMENTO E STATUS (NFD vs NF de Venda revertida)
    # =========================================================================
    # Tipo: NFD (Nota Fiscal de Devolução emitida pelo cliente)
    #       NF (NF de Venda nossa que foi revertida/cancelada)
    TIPOS_DOCUMENTO = [
        ('NFD', 'Nota Fiscal de Devolução'),
        ('NF', 'NF de Venda Revertida/Cancelada'),
    ]
    tipo_documento = db.Column(db.String(10), default='NFD', nullable=False, index=True)

    # Status no Odoo (para NFs revertidas/canceladas)
    STATUS_ODOO_CHOICES = [
        ('Devolução', 'Devolução (NFD)'),
        ('Revertida', 'NF Revertida'),
        ('Cancelada', 'NF Cancelada'),
    ]
    status_odoo = db.Column(db.String(30), nullable=True)

    # Status no Monitoramento (espelhado do status_finalizacao)
    STATUS_MONITORAMENTO_CHOICES = [
        ('Cancelada', 'Cancelada'),
        ('Devolvida', 'Devolvida'),
        ('Troca de NF', 'Troca de NF'),
    ]
    status_monitoramento = db.Column(db.String(30), nullable=True)

    # IDs do Odoo para NFs de venda revertidas
    odoo_nf_venda_id = db.Column(db.Integer, nullable=True, index=True)  # ID da NF original (account.move)
    odoo_nota_credito_id = db.Column(db.Integer, nullable=True, index=True)  # ID da NC (out_refund)

    # =========================================================================
    # AUDITORIA
    # =========================================================================
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # =========================================================================
    # RELACIONAMENTOS
    # =========================================================================
    entrega_monitorada = db.relationship(
        'EntregaMonitorada',
        backref=db.backref('nfs_devolucao', lazy='dynamic')
    )

    # =========================================================================
    # INDICES
    # =========================================================================
    __table_args__ = (
        db.Index('idx_nfd_numero_serie', 'numero_nfd', 'serie_nfd'),
        db.Index('idx_nfd_cnpj_status', 'cnpj_emitente', 'status'),
        db.Index('idx_nfd_data_registro', 'data_registro'),
        db.Index('idx_nfd_nf_venda', 'numero_nf_venda'),
        db.Index('idx_nfd_odoo_dfe', 'odoo_dfe_id'),
        db.Index('idx_nfd_tipo_documento', 'tipo_documento'),
        db.Index('idx_nfd_odoo_nf_venda', 'odoo_nf_venda_id'),
        db.Index('idx_nfd_status_odoo_monit', 'status_odoo', 'status_monitoramento'),
    )

    def __repr__(self):
        return f'<NFDevolucao {self.numero_nfd} - {self.nome_emitente or "Sem nome"}>'

    @property
    def status_descricao(self):
        """Retorna descricao amigavel do status"""
        status_map = dict(self.STATUS_CHOICES)
        return status_map.get(self.status, self.status)

    @property
    def motivo_descricao(self):
        """Retorna descricao amigavel do motivo"""
        motivo_map = dict(self.MOTIVOS_DEVOLUCAO)
        return motivo_map.get(self.motivo, self.motivo)

    @property
    def prefixo_cnpj_emitente(self):
        """Retorna os 8 primeiros digitos do CNPJ do emitente"""
        if self.cnpj_emitente:
            return ''.join(filter(str.isdigit, self.cnpj_emitente))[:8]
        return None

    @property
    def tem_dfe_vinculado(self):
        """Verifica se tem DFe do Odoo vinculado"""
        return self.odoo_dfe_id is not None

    @property
    def tem_xml(self):
        """Verifica se tem XML armazenado"""
        return bool(self.nfd_xml_path)

    @property
    def tem_pdf(self):
        """Verifica se tem PDF armazenado"""
        return bool(self.nfd_pdf_path)

    @property
    def numero_com_prefixo(self):
        """Retorna número com prefixo: NFD 12345 ou NF 12345"""
        prefixo = self.tipo_documento or 'NFD'
        numero = self.numero_nfd or self.numero_nf_venda or '?'
        return f"{prefixo} {numero}"

    @property
    def status_exibicao(self):
        """Retorna: 'Revertida | Devolvida' ou '- | Cancelada'"""
        odoo = self.status_odoo or '-'
        monit = self.status_monitoramento or '-'
        return f"{odoo} | {monit}"

    @property
    def tipo_documento_descricao(self):
        """Retorna descrição do tipo de documento"""
        tipos_map = dict(self.TIPOS_DOCUMENTO)
        return tipos_map.get(self.tipo_documento, self.tipo_documento)

    @property
    def status_entrada_odoo(self):
        """Retorna status de entrada baseado no status do DFE no Odoo

        Status '06' = 'Concluído' = Entrada física realizada
        Qualquer outro status = Pendente de entrada

        IMPORTANTE: data_entrada é 'Data de Lançamento', preenchida ANTES
        da entrada física. O gatilho correto é l10n_br_status == '06'.
        """
        if self.odoo_status_codigo == '06':
            return 'Entrada OK'
        return 'Pendente'

    @property
    def numero_com_status_entrada(self):
        """Retorna: 'NFD - 12345 - Entrada OK' ou 'NFD - 12345 - Pendente'"""
        prefixo = self.tipo_documento or 'NFD'
        numero = self.numero_nfd or self.numero_nf_venda or '?'
        status = self.status_entrada_odoo
        return f"{prefixo} - {numero} - {status}"

    def to_dict(self):
        """Serializa para JSON"""
        return {
            'id': self.id,
            'numero_nfd': self.numero_nfd,
            'serie_nfd': self.serie_nfd,
            'chave_nfd': self.chave_nfd,
            'data_registro': self.data_registro.isoformat() if self.data_registro else None,
            'data_emissao': self.data_emissao.isoformat() if self.data_emissao else None,
            'motivo': self.motivo,
            'motivo_descricao': self.motivo_descricao,
            'descricao_motivo': self.descricao_motivo,
            'confianca_motivo': float(self.confianca_motivo) if self.confianca_motivo else None,
            'numero_nf_venda': self.numero_nf_venda,
            'valor_total': float(self.valor_total) if self.valor_total else None,
            'cnpj_emitente': self.cnpj_emitente,
            'nome_emitente': self.nome_emitente,
            'info_complementar': self.info_complementar,
            'status': self.status,
            'status_descricao': self.status_descricao,
            'sincronizado_odoo': self.sincronizado_odoo,
            'tem_dfe_vinculado': self.tem_dfe_vinculado,
            'tem_xml': self.tem_xml,
            'tem_pdf': self.tem_pdf,
            # Novos campos de tipo e status
            'tipo_documento': self.tipo_documento,
            'tipo_documento_descricao': self.tipo_documento_descricao,
            'numero_com_prefixo': self.numero_com_prefixo,
            'status_odoo': self.status_odoo,
            'status_monitoramento': self.status_monitoramento,
            'status_exibicao': self.status_exibicao,
            'odoo_nf_venda_id': self.odoo_nf_venda_id,
            'odoo_nota_credito_id': self.odoo_nota_credito_id,
            # Status de entrada da NFD
            'data_entrada': self.data_entrada.isoformat() if self.data_entrada else None,
            'status_entrada_odoo': self.status_entrada_odoo,
            'numero_com_status_entrada': self.numero_com_status_entrada,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por': self.criado_por,
        }


# =============================================================================
# NFDevolucaoLinha - Linhas de Produto da NFD
# =============================================================================

class NFDevolucaoLinha(db.Model):
    """
    Linhas de produto da NFD - importadas do DFe
    Similar as linhas de produto em ConhecimentoTransporte

    Cada linha representa um produto na NFD com:
    - Codigo do cliente (original da NFD)
    - Nosso codigo (resolvido via De-Para ou Claude Haiku)
    """
    __tablename__ = 'nf_devolucao_linha'

    id = db.Column(db.Integer, primary_key=True)
    nf_devolucao_id = db.Column(
        db.Integer,
        db.ForeignKey('nf_devolucao.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # =========================================================================
    # CODIGO DO PRODUTO (do cliente - original da NFD)
    # Nota: Alguns clientes enviam lote/validade concatenado no codigo
    # =========================================================================
    codigo_produto_cliente = db.Column(db.String(255), nullable=True, index=True)
    descricao_produto_cliente = db.Column(db.Text, nullable=True)

    # =========================================================================
    # CODIGO INTERNO (resolvido via De-Para ou Haiku)
    # =========================================================================
    codigo_produto_interno = db.Column(db.String(50), nullable=True, index=True)
    descricao_produto_interno = db.Column(db.String(255), nullable=True)
    produto_resolvido = db.Column(db.Boolean, default=False, nullable=False)

    METODOS_RESOLUCAO = [
        ('DEPARA', 'De-Para'),
        ('HAIKU', 'Claude Haiku'),
        ('MANUAL', 'Manual'),
    ]
    metodo_resolucao = db.Column(db.String(20), nullable=True)
    confianca_resolucao = db.Column(db.Numeric(5, 4), nullable=True)  # 0.0000 a 1.0000

    # =========================================================================
    # QUANTIDADES DA NFD
    # =========================================================================
    quantidade = db.Column(db.Numeric(15, 3), nullable=True)
    unidade_medida = db.Column(db.String(20), nullable=True)
    valor_unitario = db.Column(db.Numeric(15, 4), nullable=True)
    valor_total = db.Column(db.Numeric(15, 2), nullable=True)

    # =========================================================================
    # CONVERSAO PARA NOSSO PADRAO (CAIXAS)
    # =========================================================================
    # Quantidade convertida para caixas (nosso padrao de venda)
    quantidade_convertida = db.Column(db.Numeric(15, 3), nullable=True)
    # Qtd de unidades por caixa do nosso produto (ex: 12X180G = 12)
    qtd_por_caixa = db.Column(db.Integer, nullable=True)

    # Peso (se disponivel)
    peso_bruto = db.Column(db.Numeric(15, 3), nullable=True)
    peso_liquido = db.Column(db.Numeric(15, 3), nullable=True)

    # =========================================================================
    # DADOS FISCAIS
    # =========================================================================
    cfop = db.Column(db.String(10), nullable=True)
    ncm = db.Column(db.String(20), nullable=True)

    # Numero do item na NFD
    numero_item = db.Column(db.Integer, nullable=True)

    # =========================================================================
    # AUDITORIA
    # =========================================================================
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil)

    # =========================================================================
    # RELACIONAMENTOS
    # =========================================================================
    nf_devolucao = db.relationship(
        'NFDevolucao',
        backref=db.backref('linhas', lazy='dynamic', cascade='all, delete-orphan')
    )

    # =========================================================================
    # INDICES
    # =========================================================================
    __table_args__ = (
        db.Index('idx_nfd_linha_produto_cliente', 'codigo_produto_cliente'),
        db.Index('idx_nfd_linha_produto_interno', 'codigo_produto_interno'),
        db.Index('idx_nfd_linha_resolvido', 'produto_resolvido'),
    )

    def __repr__(self):
        return f'<NFDevolucaoLinha {self.codigo_produto_cliente} -> {self.codigo_produto_interno or "?"}'

    @property
    def metodo_resolucao_descricao(self):
        """Retorna descricao amigavel do metodo de resolucao"""
        metodo_map = dict(self.METODOS_RESOLUCAO)
        return metodo_map.get(self.metodo_resolucao, self.metodo_resolucao)

    def to_dict(self):
        """Serializa para JSON"""
        return {
            'id': self.id,
            'nf_devolucao_id': self.nf_devolucao_id,
            'codigo_produto_cliente': self.codigo_produto_cliente,
            'descricao_produto_cliente': self.descricao_produto_cliente,
            'codigo_produto_interno': self.codigo_produto_interno,
            'descricao_produto_interno': self.descricao_produto_interno,
            'produto_resolvido': self.produto_resolvido,
            'metodo_resolucao': self.metodo_resolucao,
            'metodo_resolucao_descricao': self.metodo_resolucao_descricao,
            'quantidade': float(self.quantidade) if self.quantidade else None,
            'unidade_medida': self.unidade_medida,
            'valor_unitario': float(self.valor_unitario) if self.valor_unitario else None,
            'valor_total': float(self.valor_total) if self.valor_total else None,
            'cfop': self.cfop,
            'ncm': self.ncm,
            'numero_item': self.numero_item,
        }


# =============================================================================
# NFDevolucaoNFReferenciada - NFs de Venda Referenciadas pela NFD
# =============================================================================

class NFDevolucaoNFReferenciada(db.Model):
    """
    Tabela de relacionamento M:N entre NFDevolucao e NFs de venda referenciadas

    Uma NFD pode referenciar multiplas NFs de venda (parcial ou total)
    Dados extraidos do XML da NFD (tag <refNFe>) ou inseridos manualmente

    Exemplo:
    - NFD 12345 referencia:
        - NF 1001 (parcial - 50 caixas de 100)
        - NF 1002 (total - 30 caixas)
        - NF 1003 (parcial - 20 caixas de 80)
    """
    __tablename__ = 'nf_devolucao_nf_referenciada'

    id = db.Column(db.Integer, primary_key=True)

    # Vinculo com NFDevolucao
    nf_devolucao_id = db.Column(
        db.Integer,
        db.ForeignKey('nf_devolucao.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # =========================================================================
    # DADOS DA NF DE VENDA REFERENCIADA
    # =========================================================================
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    serie_nf = db.Column(db.String(10), nullable=True)
    chave_nf = db.Column(db.String(44), nullable=True, index=True)  # chave de acesso (se disponivel)

    # Data de emissao da NF referenciada (extraida do XML ou manual)
    data_emissao_nf = db.Column(db.Date, nullable=True)

    # =========================================================================
    # ORIGEM DO DADO
    # =========================================================================
    ORIGENS_REFERENCIA = [
        ('XML', 'Extraido do XML (tag refNFe)'),
        ('MANUAL', 'Inserido manualmente'),
        ('MONITORAMENTO', 'Registro do monitoramento'),
    ]
    origem = db.Column(db.String(20), default='MANUAL', nullable=False)

    # =========================================================================
    # VINCULO COM ENTREGA MONITORADA (se disponivel)
    # =========================================================================
    entrega_monitorada_id = db.Column(
        db.Integer,
        db.ForeignKey('entregas_monitoradas.id'),
        nullable=True,
        index=True
    )

    # =========================================================================
    # AUDITORIA
    # =========================================================================
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)

    # =========================================================================
    # RELACIONAMENTOS
    # =========================================================================
    nf_devolucao = db.relationship(
        'NFDevolucao',
        backref=db.backref('nfs_referenciadas', lazy='dynamic', cascade='all, delete-orphan')
    )
    entrega_monitorada = db.relationship(
        'EntregaMonitorada',
        backref=db.backref('nfs_referenciadas_devolucao', lazy='dynamic')
    )

    # =========================================================================
    # INDICES E CONSTRAINTS
    # =========================================================================
    __table_args__ = (
        db.UniqueConstraint('nf_devolucao_id', 'numero_nf', 'serie_nf', name='uq_nfd_nf_ref'),
        db.Index('idx_nf_ref_numero', 'numero_nf'),
        db.Index('idx_nf_ref_chave', 'chave_nf'),
    )

    def __repr__(self):
        return f'<NFDevolucaoNFReferenciada NFD:{self.nf_devolucao_id} -> NF:{self.numero_nf}>'

    def to_dict(self):
        """Serializa para JSON"""
        return {
            'id': self.id,
            'nf_devolucao_id': self.nf_devolucao_id,
            'numero_nf': self.numero_nf,
            'serie_nf': self.serie_nf,
            'chave_nf': self.chave_nf,
            'data_emissao_nf': self.data_emissao_nf.isoformat() if self.data_emissao_nf else None,
            'origem': self.origem,
            'entrega_monitorada_id': self.entrega_monitorada_id,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
        }


# =============================================================================
# OcorrenciaDevolucao - Tratativas Comercial/Logistica
# =============================================================================

class OcorrenciaDevolucao(db.Model):
    """
    Ocorrencia unificada para tratativas de Logistica e Comercial

    Secao Logistica:
    - Destino (RETORNO/DESCARTE)
    - Localizacao atual
    - Transportadora de retorno

    Secao Comercial:
    - Categoria e subcategoria
    - Responsavel e origem
    - Status da tratativa
    """
    __tablename__ = 'ocorrencia_devolucao'

    id = db.Column(db.Integer, primary_key=True)

    # Vinculo obrigatorio com NFDevolucao (1:1)
    nf_devolucao_id = db.Column(
        db.Integer,
        db.ForeignKey('nf_devolucao.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True
    )

    # Numero de referencia auto-gerado: OC-YYYYMM-XXXX
    numero_ocorrencia = db.Column(db.String(20), nullable=False, unique=True, index=True)

    # =========================================================================
    # SECAO LOGISTICA
    # =========================================================================
    DESTINOS = [
        ('RETORNO', 'Retorno ao CD'),
        ('DESCARTE', 'Descarte'),
        ('REENTREGA', 'Reentrega'),
        ('INDEFINIDO', 'Indefinido'),
    ]
    destino = db.Column(db.String(20), default='INDEFINIDO', nullable=False)

    LOCALIZACOES = [
        ('CLIENTE', 'No Cliente'),
        ('TRANSPORTADORA', 'Na Transportadora'),
        ('EM_TRANSITO', 'Em Transito'),
        ('CD', 'No CD'),
        ('DESCARTADO', 'Descartado'),
    ]
    localizacao_atual = db.Column(db.String(20), default='CLIENTE', nullable=False)

    # Transportadora de retorno
    transportadora_retorno_id = db.Column(
        db.Integer,
        db.ForeignKey('transportadoras.id'),
        nullable=True
    )
    transportadora_retorno_nome = db.Column(db.String(255), nullable=True)

    # Datas de controle logistico
    data_previsao_retorno = db.Column(db.Date, nullable=True)
    data_chegada_cd = db.Column(db.DateTime, nullable=True)
    recebido_por = db.Column(db.String(100), nullable=True)

    # Observacoes logistica
    observacoes_logistica = db.Column(db.Text, nullable=True)

    # =========================================================================
    # SECAO COMERCIAL
    # =========================================================================
    CATEGORIAS = [
        ('QUALIDADE', 'Qualidade'),
        ('COMERCIAL', 'Comercial'),
        ('LOGISTICA', 'Logistica'),
        ('FISCAL', 'Fiscal'),
        ('CLIENTE', 'Cliente'),
        ('PRODUCAO', 'Producao'),
    ]
    categoria = db.Column(db.String(30), nullable=True)

    SUBCATEGORIAS = [
        ('AVARIA_TRANSPORTE', 'Avaria no Transporte'),
        ('AVARIA_PRODUCAO', 'Avaria na Producao'),
        ('PRODUTO_NAO_CONFORME', 'Produto Nao Conforme'),
        ('PEDIDO_ERRADO', 'Pedido Errado'),
        ('QUANTIDADE_ERRADA', 'Quantidade Errada'),
        ('PRECO_DIVERGENTE', 'Preco Divergente'),
        ('PROBLEMA_CADASTRO', 'Problema de Cadastro'),
        ('SEM_PEDIDO', 'Sem Pedido'),
        ('VENCIMENTO_PROXIMO', 'Vencimento Proximo'),
        ('RECUSA_CLIENTE', 'Recusa do Cliente'),
        ('ENDERECO_INCORRETO', 'Endereco Incorreto'),
        ('OUTROS', 'Outros'),
    ]
    subcategoria = db.Column(db.String(50), nullable=True)

    descricao_comercial = db.Column(db.Text, nullable=True)

    RESPONSAVEIS = [
        ('NACOM', 'Nacom'),
        ('TRANSPORTADORA', 'Transportadora'),
        ('CLIENTE', 'Cliente'),
        ('FORNECEDOR', 'Fornecedor'),
        ('INDEFINIDO', 'Indefinido'),
    ]
    responsavel = db.Column(db.String(30), default='INDEFINIDO', nullable=True)

    # Status da tratativa
    STATUS_OCORRENCIA = [
        ('ABERTA', 'Aberta'),
        ('EM_ANALISE', 'Em Analise'),
        ('AGUARDANDO_RETORNO', 'Aguardando Retorno'),
        ('RETORNADA', 'Retornada'),
        ('RESOLVIDA', 'Resolvida'),
        ('CANCELADA', 'Cancelada'),
    ]
    status = db.Column(db.String(30), default='ABERTA', nullable=False, index=True)

    # Origem do problema (para KPI)
    ORIGENS = [
        ('PRODUCAO', 'Producao'),
        ('EXPEDICAO', 'Expedicao'),
        ('TRANSPORTE', 'Transporte'),
        ('CLIENTE', 'Cliente'),
        ('COMERCIAL', 'Comercial'),
        ('INDEFINIDO', 'Indefinido'),
    ]
    origem = db.Column(db.String(30), default='INDEFINIDO', nullable=True)

    # Momento da devolucao (quando ocorreu)
    MOMENTOS_DEVOLUCAO = [
        ('ATO_ENTREGA', 'Ato da entrega'),
        ('POSTERIOR_ENTREGA', 'Posterior a entrega'),
        ('INDEFINIDO', 'Indefinido'),
    ]
    momento_devolucao = db.Column(db.String(20), default='INDEFINIDO', nullable=True)

    # Autorizacao e resolucao
    autorizado_por = db.Column(db.String(100), nullable=True)
    resolvido_por = db.Column(db.String(100), nullable=True)
    desfecho = db.Column(db.Text, nullable=True)

    # =========================================================================
    # TIMESTAMPS
    # =========================================================================
    data_abertura = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    data_acao_comercial = db.Column(db.DateTime, nullable=True)
    data_resolucao = db.Column(db.DateTime, nullable=True)

    # =========================================================================
    # AUDITORIA
    # =========================================================================
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # =========================================================================
    # RELACIONAMENTOS
    # =========================================================================
    nf_devolucao = db.relationship(
        'NFDevolucao',
        backref=db.backref('ocorrencia', uselist=False)
    )
    transportadora_retorno = db.relationship(
        'Transportadora',
        backref='ocorrencias_retorno'
    )

    # =========================================================================
    # INDICES
    # =========================================================================
    __table_args__ = (
        db.Index('idx_ocorrencia_status_destino', 'status', 'destino'),
        db.Index('idx_ocorrencia_categoria', 'categoria', 'subcategoria'),
        db.Index('idx_ocorrencia_responsavel', 'responsavel', 'status'),
        db.Index('idx_ocorrencia_data_abertura', 'data_abertura'),
    )

    def __repr__(self):
        return f'<OcorrenciaDevolucao {self.numero_ocorrencia} - {self.status}>'

    @classmethod
    def gerar_numero_ocorrencia(cls):
        """Gera proximo numero de ocorrencia no formato YYYYMM-XXXX"""
        from sqlalchemy import func

        agora = agora_brasil()
        prefixo = f"{agora.strftime('%Y%m')}-"

        # Busca ultimo numero do mes
        ultimo = cls.query.filter(
            cls.numero_ocorrencia.like(f'{prefixo}%')
        ).order_by(cls.numero_ocorrencia.desc()).first()

        if ultimo:
            # Extrai sequencial e incrementa
            try:
                seq = int(ultimo.numero_ocorrencia.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1

        return f"{prefixo}{seq:04d}"

    def to_dict(self):
        """Serializa para JSON"""
        return {
            'id': self.id,
            'numero_ocorrencia': self.numero_ocorrencia,
            'nf_devolucao_id': self.nf_devolucao_id,
            'destino': self.destino,
            'localizacao_atual': self.localizacao_atual,
            'transportadora_retorno_nome': self.transportadora_retorno_nome,
            'data_previsao_retorno': self.data_previsao_retorno.isoformat() if self.data_previsao_retorno else None,
            'categoria': self.categoria,
            'subcategoria': self.subcategoria,
            'descricao_comercial': self.descricao_comercial,
            'responsavel': self.responsavel,
            'status': self.status,
            'origem': self.origem,
            'autorizado_por': self.autorizado_por,
            'resolvido_por': self.resolvido_por,
            'data_abertura': self.data_abertura.isoformat() if self.data_abertura else None,
            'data_resolucao': self.data_resolucao.isoformat() if self.data_resolucao else None,
        }


# =============================================================================
# FreteDevolucao - Cotacao de Frete de Retorno
# =============================================================================

class FreteDevolucao(db.Model):
    """
    Cotacao de frete de retorno para devolucoes

    Pode existir sem vinculo com DespesaExtra (para devolucoes antigas)
    Ao vincular, DespesaExtra herda informacoes
    """
    __tablename__ = 'frete_devolucao'

    id = db.Column(db.Integer, primary_key=True)

    # Vinculos
    ocorrencia_devolucao_id = db.Column(
        db.Integer,
        db.ForeignKey('ocorrencia_devolucao.id'),
        nullable=True,
        index=True
    )
    despesa_extra_id = db.Column(
        db.Integer,
        db.ForeignKey('despesas_extras.id'),
        nullable=True,
        index=True
    )

    # =========================================================================
    # TRANSPORTADORA
    # =========================================================================
    transportadora_id = db.Column(
        db.Integer,
        db.ForeignKey('transportadoras.id'),
        nullable=True
    )
    transportadora_nome = db.Column(db.String(255), nullable=False)
    cnpj_transportadora = db.Column(db.String(20), nullable=True)

    # =========================================================================
    # VALORES
    # =========================================================================
    valor_cotado = db.Column(db.Numeric(15, 2), nullable=False)
    valor_negociado = db.Column(db.Numeric(15, 2), nullable=True)
    peso_kg = db.Column(db.Numeric(15, 3), nullable=True)

    # =========================================================================
    # DATAS
    # =========================================================================
    data_cotacao = db.Column(db.Date, nullable=False)
    data_coleta_prevista = db.Column(db.Date, nullable=True)
    data_coleta_realizada = db.Column(db.Date, nullable=True)
    data_entrega_prevista = db.Column(db.Date, nullable=True)
    data_entrega_realizada = db.Column(db.Date, nullable=True)

    # =========================================================================
    # ROTA
    # =========================================================================
    local_coleta = db.Column(db.String(255), nullable=True)  # Nome do local de coleta (digitavel)
    uf_origem = db.Column(db.String(2), nullable=True)
    cidade_origem = db.Column(db.String(100), nullable=True)
    uf_destino = db.Column(db.String(2), nullable=True)
    cidade_destino = db.Column(db.String(100), nullable=True)

    # =========================================================================
    # STATUS
    # =========================================================================
    STATUS_CHOICES = [
        ('COTADO', 'Cotado'),
        ('APROVADO', 'Aprovado'),
        ('COLETADO', 'Coletado'),
        ('EM_TRANSITO', 'Em Transito'),
        ('ENTREGUE', 'Entregue'),
        ('CANCELADO', 'Cancelado'),
    ]
    status = db.Column(db.String(20), default='COTADO', nullable=False, index=True)

    # =========================================================================
    # CTe DO FRETE DE RETORNO
    # =========================================================================
    numero_cte = db.Column(db.String(20), nullable=True)
    chave_cte = db.Column(db.String(44), nullable=True, index=True)

    # =========================================================================
    # OBSERVACOES
    # =========================================================================
    observacoes = db.Column(db.Text, nullable=True)

    # =========================================================================
    # AUDITORIA
    # =========================================================================
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # =========================================================================
    # RELACIONAMENTOS
    # =========================================================================
    ocorrencia = db.relationship(
        'OcorrenciaDevolucao',
        backref=db.backref('fretes_devolucao', lazy='dynamic')
    )
    despesa_extra = db.relationship(
        'DespesaExtra',
        backref='frete_devolucao_vinculado'
    )
    transportadora = db.relationship(
        'Transportadora',
        backref='fretes_devolucao'
    )

    # =========================================================================
    # INDICES
    # =========================================================================
    __table_args__ = (
        db.Index('idx_frete_dev_status', 'status'),
        db.Index('idx_frete_dev_transportadora', 'transportadora_id'),
        db.Index('idx_frete_dev_data_cotacao', 'data_cotacao'),
    )

    def __repr__(self):
        return f'<FreteDevolucao {self.id} - {self.transportadora_nome} - {self.status}>'

    @property
    def valor_final(self):
        """Retorna valor negociado ou cotado"""
        return self.valor_negociado or self.valor_cotado

    def to_dict(self):
        """Serializa para JSON"""
        return {
            'id': self.id,
            'ocorrencia_devolucao_id': self.ocorrencia_devolucao_id,
            'despesa_extra_id': self.despesa_extra_id,
            'transportadora_nome': self.transportadora_nome,
            'valor_cotado': float(self.valor_cotado) if self.valor_cotado else None,
            'valor_negociado': float(self.valor_negociado) if self.valor_negociado else None,
            'valor_final': float(self.valor_final) if self.valor_final else None,
            'peso_kg': float(self.peso_kg) if self.peso_kg else None,
            'data_cotacao': self.data_cotacao.isoformat() if self.data_cotacao else None,
            'status': self.status,
            'uf_origem': self.uf_origem,
            'cidade_origem': self.cidade_origem,
            'uf_destino': self.uf_destino,
            'cidade_destino': self.cidade_destino,
        }


# =============================================================================
# ContagemDevolucao - Contagem por Linha de Produto
# =============================================================================

class ContagemDevolucao(db.Model):
    """
    Contagem fisica por linha de produto da NFD
    Vinculado a NFDevolucaoLinha (1:1)
    """
    __tablename__ = 'contagem_devolucao'

    id = db.Column(db.Integer, primary_key=True)

    nf_devolucao_linha_id = db.Column(
        db.Integer,
        db.ForeignKey('nf_devolucao_linha.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True
    )

    # =========================================================================
    # QUANTIDADES CONFORME
    # =========================================================================
    caixas_conforme = db.Column(db.Integer, default=0, nullable=False)
    unidades_conforme = db.Column(db.Integer, default=0, nullable=False)

    # =========================================================================
    # QUANTIDADES NAO CONFORME (avariado/danificado)
    # =========================================================================
    caixas_nao_conforme = db.Column(db.Integer, default=0, nullable=False)
    unidades_nao_conforme = db.Column(db.Integer, default=0, nullable=False)

    # =========================================================================
    # CALCULADOS (diferenca entre declarado e contado)
    # =========================================================================
    caixas_faltantes = db.Column(db.Integer, default=0, nullable=False)
    unidades_faltantes = db.Column(db.Integer, default=0, nullable=False)

    # =========================================================================
    # COMENTARIOS
    # =========================================================================
    comentario_contagem = db.Column(db.Text, nullable=True)
    comentario_qualidade = db.Column(db.Text, nullable=True)

    # =========================================================================
    # QUALIDADE
    # =========================================================================
    STATUS_QUALIDADE = [
        ('PENDENTE', 'Pendente'),
        ('APROVADO', 'Aprovado'),
        ('REPROVADO', 'Reprovado'),
        ('PARCIAL', 'Parcial'),
    ]
    status_qualidade = db.Column(db.String(20), default='PENDENTE', nullable=False)

    DESTINOS_PRODUTO = [
        ('PENDENTE', 'Pendente'),
        ('ESTOQUE', 'Estoque'),
        ('QUARENTENA', 'Quarentena'),
        ('DESCARTE', 'Descarte'),
    ]
    destino_produto = db.Column(db.String(20), default='PENDENTE', nullable=False)

    # =========================================================================
    # CONTROLE
    # =========================================================================
    data_contagem = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    conferente = db.Column(db.String(100), nullable=False)

    # =========================================================================
    # AUDITORIA
    # =========================================================================
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # =========================================================================
    # RELACIONAMENTOS
    # =========================================================================
    linha_nfd = db.relationship(
        'NFDevolucaoLinha',
        backref=db.backref('contagem', uselist=False)
    )

    def __repr__(self):
        return f'<ContagemDevolucao {self.id} - {self.status_qualidade}>'

    @property
    def total_conforme(self):
        """Total de itens conforme (caixas + unidades)"""
        return (self.caixas_conforme or 0) + (self.unidades_conforme or 0)

    @property
    def total_nao_conforme(self):
        """Total de itens nao conforme (caixas + unidades)"""
        return (self.caixas_nao_conforme or 0) + (self.unidades_nao_conforme or 0)

    @property
    def total_faltante(self):
        """Total de itens faltantes (caixas + unidades)"""
        return (self.caixas_faltantes or 0) + (self.unidades_faltantes or 0)

    def to_dict(self):
        """Serializa para JSON"""
        return {
            'id': self.id,
            'nf_devolucao_linha_id': self.nf_devolucao_linha_id,
            'caixas_conforme': self.caixas_conforme,
            'unidades_conforme': self.unidades_conforme,
            'caixas_nao_conforme': self.caixas_nao_conforme,
            'unidades_nao_conforme': self.unidades_nao_conforme,
            'caixas_faltantes': self.caixas_faltantes,
            'unidades_faltantes': self.unidades_faltantes,
            'status_qualidade': self.status_qualidade,
            'destino_produto': self.destino_produto,
            'comentario_contagem': self.comentario_contagem,
            'data_contagem': self.data_contagem.isoformat() if self.data_contagem else None,
            'conferente': self.conferente,
        }


# =============================================================================
# AnexoOcorrencia - Emails e Fotos
# =============================================================================

class AnexoOcorrencia(db.Model):
    """
    Anexos de ocorrencias e contagens

    Tipos: EMAIL (.msg), FOTO, DOCUMENTO (PDF, etc)
    Arquivos armazenados no S3
    """
    __tablename__ = 'anexo_ocorrencia'

    id = db.Column(db.Integer, primary_key=True)

    # Vinculos (um ou outro)
    ocorrencia_devolucao_id = db.Column(
        db.Integer,
        db.ForeignKey('ocorrencia_devolucao.id', ondelete='CASCADE'),
        nullable=True,
        index=True
    )
    contagem_devolucao_id = db.Column(
        db.Integer,
        db.ForeignKey('contagem_devolucao.id', ondelete='CASCADE'),
        nullable=True,
        index=True
    )

    # =========================================================================
    # TIPO DE ANEXO
    # =========================================================================
    TIPOS_ANEXO = [
        ('EMAIL', 'Email'),
        ('FOTO', 'Foto'),
        ('DOCUMENTO', 'Documento'),
        ('PLANILHA', 'Planilha'),
        ('OUTROS', 'Outros'),
    ]
    tipo = db.Column(db.String(20), nullable=False, index=True)

    # =========================================================================
    # DADOS DO ARQUIVO
    # =========================================================================
    nome_original = db.Column(db.String(255), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    caminho_s3 = db.Column(db.String(500), nullable=False)
    tamanho_bytes = db.Column(db.Integer, nullable=True)
    content_type = db.Column(db.String(100), nullable=True)

    # =========================================================================
    # METADADOS DE EMAIL (quando tipo=EMAIL)
    # =========================================================================
    email_remetente = db.Column(db.String(255), nullable=True)
    email_assunto = db.Column(db.String(500), nullable=True)
    email_data_envio = db.Column(db.DateTime, nullable=True)
    email_preview = db.Column(db.Text, nullable=True)

    # =========================================================================
    # DESCRICAO/CONTEXTO
    # =========================================================================
    descricao = db.Column(db.Text, nullable=True)

    # =========================================================================
    # AUDITORIA
    # =========================================================================
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # =========================================================================
    # RELACIONAMENTOS
    # =========================================================================
    ocorrencia = db.relationship(
        'OcorrenciaDevolucao',
        backref=db.backref('anexos', lazy='dynamic')
    )
    contagem = db.relationship(
        'ContagemDevolucao',
        backref=db.backref('anexos', lazy='dynamic')
    )

    # =========================================================================
    # INDICES E CONSTRAINTS
    # =========================================================================
    __table_args__ = (
        db.Index('idx_anexo_tipo', 'tipo'),
        db.Index('idx_anexo_ocorrencia', 'ocorrencia_devolucao_id'),
        db.Index('idx_anexo_contagem', 'contagem_devolucao_id'),
        db.CheckConstraint(
            "(ocorrencia_devolucao_id IS NOT NULL) OR (contagem_devolucao_id IS NOT NULL)",
            name='ck_anexo_vinculo_obrigatorio'
        ),
    )

    def __repr__(self):
        return f'<AnexoOcorrencia {self.nome_original} - {self.tipo}>'

    @property
    def extensao(self):
        """Retorna extensao do arquivo"""
        return self.nome_original.split('.')[-1].lower() if '.' in self.nome_original else ''

    @property
    def tamanho_kb(self):
        """Retorna tamanho em KB"""
        return round(self.tamanho_bytes / 1024, 2) if self.tamanho_bytes else 0

    def to_dict(self):
        """Serializa para JSON"""
        return {
            'id': self.id,
            'tipo': self.tipo,
            'nome_original': self.nome_original,
            'extensao': self.extensao,
            'tamanho_kb': self.tamanho_kb,
            'descricao': self.descricao,
            'email_remetente': self.email_remetente,
            'email_assunto': self.email_assunto,
            'email_data_envio': self.email_data_envio.isoformat() if self.email_data_envio else None,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por': self.criado_por,
        }


# =============================================================================
# DeParaProdutoCliente - Mapeamento de Codigos por Prefixo CNPJ
# =============================================================================

class DeParaProdutoCliente(db.Model):
    """
    Mapeamento de codigos de produtos do cliente para nosso codigo

    Usa prefixo CNPJ (8 digitos) para mapear grupo economico
    Suporta fator de conversao e unidade de medida
    """
    __tablename__ = 'depara_produto_cliente'

    id = db.Column(db.Integer, primary_key=True)

    # =========================================================================
    # PREFIXO CNPJ (8 primeiros digitos - raiz do grupo economico)
    # =========================================================================
    prefixo_cnpj = db.Column(db.String(8), nullable=False, index=True)
    nome_grupo = db.Column(db.String(255), nullable=True)

    # =========================================================================
    # MAPEAMENTO DE CODIGOS
    # =========================================================================
    codigo_cliente = db.Column(db.String(255), nullable=False, index=True)
    descricao_cliente = db.Column(db.String(255), nullable=True)

    nosso_codigo = db.Column(db.String(50), nullable=False, index=True)
    descricao_nosso = db.Column(db.String(255), nullable=True)

    # =========================================================================
    # CONVERSAO DE UNIDADES
    # =========================================================================
    fator_conversao = db.Column(db.Numeric(10, 4), default=1.0, nullable=False)
    unidade_medida_cliente = db.Column(db.String(20), nullable=True)
    unidade_medida_nosso = db.Column(db.String(20), nullable=True)

    # =========================================================================
    # OBSERVACOES
    # =========================================================================
    observacoes = db.Column(db.Text, nullable=True)

    # =========================================================================
    # CONTROLE
    # =========================================================================
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # =========================================================================
    # AUDITORIA
    # =========================================================================
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # =========================================================================
    # INDICES E CONSTRAINTS
    # =========================================================================
    __table_args__ = (
        db.UniqueConstraint('prefixo_cnpj', 'codigo_cliente', name='uq_depara_prefixo_codigo'),
        db.Index('idx_depara_nosso_codigo', 'nosso_codigo'),
        db.Index('idx_depara_prefixo_ativo', 'prefixo_cnpj', 'ativo'),
    )

    def __repr__(self):
        return f'<DeParaProdutoCliente {self.prefixo_cnpj}: {self.codigo_cliente} -> {self.nosso_codigo}>'

    @classmethod
    def obter_nosso_codigo(cls, cnpj_cliente, codigo_cliente):
        """
        Obtem nosso codigo a partir do codigo do cliente

        Args:
            cnpj_cliente: CNPJ completo ou prefixo (8 digitos)
            codigo_cliente: Codigo usado pelo cliente

        Returns:
            dict com nosso_codigo, fator_conversao ou None
        """
        # Extrair prefixo do CNPJ
        prefixo = ''.join(filter(str.isdigit, str(cnpj_cliente)))[:8]

        depara = cls.query.filter_by(
            prefixo_cnpj=prefixo,
            codigo_cliente=str(codigo_cliente),
            ativo=True
        ).first()

        if depara:
            return {
                'nosso_codigo': depara.nosso_codigo,
                'descricao_nosso': depara.descricao_nosso,
                'fator_conversao': float(depara.fator_conversao),
                'unidade_medida_cliente': depara.unidade_medida_cliente,
                'unidade_medida_nosso': depara.unidade_medida_nosso
            }

        return None

    def to_dict(self):
        """Serializa para JSON"""
        return {
            'id': self.id,
            'prefixo_cnpj': self.prefixo_cnpj,
            'nome_grupo': self.nome_grupo,
            'codigo_cliente': self.codigo_cliente,
            'descricao_cliente': self.descricao_cliente,
            'nosso_codigo': self.nosso_codigo,
            'descricao_nosso': self.descricao_nosso,
            'fator_conversao': float(self.fator_conversao) if self.fator_conversao else 1.0,
            'unidade_medida_cliente': self.unidade_medida_cliente,
            'unidade_medida_nosso': self.unidade_medida_nosso,
            'ativo': self.ativo,
        }


# =============================================================================
# DescarteDevolucao - Registro de Descarte Autorizado
# =============================================================================

class DescarteDevolucao(db.Model):
    """
    Registro de descarte autorizado para devolucoes

    Fluxo:
    1. Logistica decide que nao compensa retornar a mercadoria
    2. Gera termo de autorizacao de descarte
    3. Envia termo para cliente assinar
    4. Cliente retorna termo assinado (ou foto do descarte)
    5. Registra no sistema com comprovantes

    Pode ter custo de descarte (empresa de destruicao, etc.)
    """
    __tablename__ = 'descarte_devolucao'

    id = db.Column(db.Integer, primary_key=True)

    # Vinculo obrigatorio com OcorrenciaDevolucao
    ocorrencia_devolucao_id = db.Column(
        db.Integer,
        db.ForeignKey('ocorrencia_devolucao.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # =========================================================================
    # AUTORIZACAO
    # =========================================================================
    numero_termo = db.Column(db.String(50), nullable=True, index=True)  # Numero do termo de descarte
    data_autorizacao = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    autorizado_por = db.Column(db.String(100), nullable=False)  # Quem autorizou internamente

    # Motivo do descarte (por que nao retornar?)
    MOTIVOS_DESCARTE = [
        ('CUSTO_ALTO', 'Custo de frete maior que valor da mercadoria'),
        ('PERECIVEIS', 'Produtos pereciveis/vencidos'),
        ('AVARIA_TOTAL', 'Avaria total - sem condicoes de retorno'),
        ('CONTAMINACAO', 'Contaminacao/risco sanitario'),
        ('CLIENTE_SOLICITOU', 'Cliente solicitou o descarte'),
        ('OUTROS', 'Outros'),
    ]
    motivo_descarte = db.Column(db.String(50), nullable=False)
    descricao_motivo = db.Column(db.Text, nullable=True)

    # Valor da mercadoria descartada (para controle)
    valor_mercadoria = db.Column(db.Numeric(15, 2), nullable=True)

    # =========================================================================
    # EMPRESA AUTORIZADA A DESCARTAR (transportador ou cliente)
    # =========================================================================
    TIPO_AUTORIZADO_CHOICES = [
        ('TRANSPORTADOR', 'Transportador'),
        ('CLIENTE', 'Cliente'),
    ]
    empresa_autorizada_nome = db.Column(db.String(255), nullable=True)  # Razao Social
    empresa_autorizada_documento = db.Column(db.String(20), nullable=True)  # CNPJ ou CPF
    empresa_autorizada_tipo = db.Column(db.String(20), default='TRANSPORTADOR', nullable=True)

    # =========================================================================
    # TERMO DE AUTORIZACAO (documento enviado ao cliente)
    # =========================================================================
    termo_path = db.Column(db.String(500), nullable=True)  # Caminho no S3
    termo_nome_arquivo = db.Column(db.String(255), nullable=True)
    termo_enviado_em = db.Column(db.DateTime, nullable=True)
    termo_enviado_para = db.Column(db.String(255), nullable=True)  # Email/contato

    # =========================================================================
    # RETORNO DO TERMO (assinado pelo cliente)
    # =========================================================================
    termo_assinado_path = db.Column(db.String(500), nullable=True)
    termo_assinado_nome_arquivo = db.Column(db.String(255), nullable=True)
    termo_retornado_em = db.Column(db.DateTime, nullable=True)

    # =========================================================================
    # COMPROVANTE DE DESCARTE (foto, documento, etc.)
    # =========================================================================
    comprovante_path = db.Column(db.String(500), nullable=True)
    comprovante_nome_arquivo = db.Column(db.String(255), nullable=True)
    data_descarte = db.Column(db.Date, nullable=True)  # Data efetiva do descarte

    # =========================================================================
    # CUSTO DO DESCARTE (se houver)
    # =========================================================================
    tem_custo = db.Column(db.Boolean, default=False, nullable=False)
    valor_descarte = db.Column(db.Numeric(15, 2), nullable=True)  # Custo de destruicao
    fornecedor_descarte = db.Column(db.String(255), nullable=True)  # Empresa de descarte
    despesa_extra_id = db.Column(
        db.Integer,
        db.ForeignKey('despesas_extras.id'),
        nullable=True,
        index=True
    )

    # =========================================================================
    # STATUS DO DESCARTE
    # =========================================================================
    STATUS_CHOICES = [
        ('AUTORIZADO', 'Autorizado'),
        ('TERMO_ENVIADO', 'Termo Enviado'),
        ('TERMO_RETORNADO', 'Termo Retornado'),
        ('DESCARTADO', 'Descartado'),
        ('CANCELADO', 'Cancelado'),
    ]
    status = db.Column(db.String(20), default='AUTORIZADO', nullable=False, index=True)

    # =========================================================================
    # OBSERVACOES
    # =========================================================================
    observacoes = db.Column(db.Text, nullable=True)

    # =========================================================================
    # RASTREIO DE IMPRESSAO/DOWNLOAD DO TERMO
    # =========================================================================
    termo_impresso_por = db.Column(db.String(100), nullable=True)
    termo_impresso_em = db.Column(db.DateTime, nullable=True)
    termo_salvo_por = db.Column(db.String(100), nullable=True)
    termo_salvo_em = db.Column(db.DateTime, nullable=True)

    # =========================================================================
    # AUDITORIA
    # =========================================================================
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # =========================================================================
    # RELACIONAMENTOS
    # =========================================================================
    ocorrencia = db.relationship(
        'OcorrenciaDevolucao',
        backref=db.backref('descartes', lazy='dynamic')
    )
    despesa_extra = db.relationship(
        'DespesaExtra',
        backref='descarte_devolucao_vinculado'
    )

    # =========================================================================
    # INDICES
    # =========================================================================
    __table_args__ = (
        db.Index('idx_descarte_status', 'status'),
        db.Index('idx_descarte_data_autorizacao', 'data_autorizacao'),
    )

    def __repr__(self):
        return f'<DescarteDevolucao {self.id} - {self.status}>'

    @classmethod
    def gerar_numero_termo(cls):
        """Gera numero de termo: TD-YYYYMM-XXXX"""
        from datetime import datetime
        agora = datetime.now()
        prefixo = f"TD-{agora.strftime('%Y%m')}-"

        ultimo = cls.query.filter(
            cls.numero_termo.like(f'{prefixo}%')
        ).order_by(cls.numero_termo.desc()).first()

        if ultimo and ultimo.numero_termo:
            try:
                ultimo_num = int(ultimo.numero_termo.split('-')[-1])
                novo_num = ultimo_num + 1
            except (ValueError, IndexError):
                novo_num = 1
        else:
            novo_num = 1

        return f"{prefixo}{novo_num:04d}"

    def to_dict(self):
        """Serializa para JSON"""
        return {
            'id': self.id,
            'ocorrencia_devolucao_id': self.ocorrencia_devolucao_id,
            'numero_termo': self.numero_termo,
            'data_autorizacao': self.data_autorizacao.isoformat() if self.data_autorizacao else None,
            'autorizado_por': self.autorizado_por,
            'motivo_descarte': self.motivo_descarte,
            'descricao_motivo': self.descricao_motivo,
            'valor_mercadoria': float(self.valor_mercadoria) if self.valor_mercadoria else None,
            'empresa_autorizada_nome': self.empresa_autorizada_nome,
            'empresa_autorizada_documento': self.empresa_autorizada_documento,
            'empresa_autorizada_tipo': self.empresa_autorizada_tipo,
            'termo_enviado_em': self.termo_enviado_em.isoformat() if self.termo_enviado_em else None,
            'termo_retornado_em': self.termo_retornado_em.isoformat() if self.termo_retornado_em else None,
            'data_descarte': self.data_descarte.isoformat() if self.data_descarte else None,
            'tem_custo': self.tem_custo,
            'valor_descarte': float(self.valor_descarte) if self.valor_descarte else None,
            'fornecedor_descarte': self.fornecedor_descarte,
            'status': self.status,
            'observacoes': self.observacoes,
            'tem_termo': bool(self.termo_path),
            'tem_termo_assinado': bool(self.termo_assinado_path),
            'tem_comprovante': bool(self.comprovante_path),
        }


# =============================================================================
# DESCARTE ITEM - Itens individuais do descarte
# =============================================================================
class DescarteItem(db.Model):
    """
    Item individual de um descarte.
    Permite rastrear quantidades descartadas de cada produto da NFD.
    """
    __tablename__ = 'descarte_item'

    id = db.Column(db.Integer, primary_key=True)

    # Vinculo com o descarte
    descarte_id = db.Column(
        db.Integer,
        db.ForeignKey('descarte_devolucao.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Vinculo com a linha da NFD
    nfd_linha_id = db.Column(
        db.Integer,
        db.ForeignKey('nf_devolucao_linha.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Quantidades descartadas
    quantidade_descarte = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    quantidade_caixas = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    valor_descarte = db.Column(db.Numeric(15, 2), nullable=False, default=0)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil)

    # Relacionamentos
    descarte = db.relationship(
        'DescarteDevolucao',
        backref=db.backref('itens', lazy='dynamic', cascade='all, delete-orphan')
    )
    nfd_linha = db.relationship(
        'NFDevolucaoLinha',
        backref=db.backref('itens_descarte', lazy='dynamic')
    )

    def __repr__(self):
        return f'<DescarteItem {self.id} - Descarte {self.descarte_id}>'

    def to_dict(self):
        """Serializa para JSON"""
        return {
            'id': self.id,
            'descarte_id': self.descarte_id,
            'nfd_linha_id': self.nfd_linha_id,
            'quantidade_descarte': float(self.quantidade_descarte) if self.quantidade_descarte else 0,
            'quantidade_caixas': float(self.quantidade_caixas) if self.quantidade_caixas else 0,
            'valor_descarte': float(self.valor_descarte) if self.valor_descarte else 0,
            'produto': self.nfd_linha.descricao_produto_interno or self.nfd_linha.descricao_produto_cliente if self.nfd_linha else None,
        }

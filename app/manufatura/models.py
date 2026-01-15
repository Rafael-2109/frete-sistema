"""
Modelos do módulo de Manufatura/PCP
"""
from app import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB


class GrupoEmpresarial(db.Model):
    __tablename__ = 'grupo_empresarial'
    
    id = db.Column(db.Integer, primary_key=True)
    nome_grupo = db.Column(db.String(100), nullable=False, index=True)
    prefixo_cnpj = db.Column(db.String(8), nullable=False, index=True)  # 1 prefixo por linha
    descricao = db.Column(db.String(255), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    ativo = db.Column(db.Boolean, default=True)
    
    __table_args__ = (
        db.UniqueConstraint('prefixo_cnpj'),  # Cada prefixo deve ser único
        db.Index('idx_grupo_prefixo', 'nome_grupo', 'prefixo_cnpj'),  # Índice composto
    )


class HistoricoPedidos(db.Model):
    __tablename__ = 'historico_pedidos'
    
    id = db.Column(db.Integer, primary_key=True)
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    data_pedido = db.Column(db.Date, nullable=False, index=True)
    cnpj_cliente = db.Column(db.String(20), nullable=False)
    raz_social_red = db.Column(db.String(255))
    nome_grupo = db.Column(db.String(100), index=True)
    vendedor = db.Column(db.String(100))
    equipe_vendas = db.Column(db.String(100))
    incoterm = db.Column(db.String(20))
    nome_cidade = db.Column(db.String(100))
    cod_uf = db.Column(db.String(2))
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))
    qtd_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)
    preco_produto_pedido = db.Column(db.Numeric(15, 4))
    valor_produto_pedido = db.Column(db.Numeric(15, 2))
    icms_produto_pedido = db.Column(db.Numeric(15, 2))
    pis_produto_pedido = db.Column(db.Numeric(15, 2))
    cofins_produto_pedido = db.Column(db.Numeric(15, 2))
    importado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('num_pedido', 'cod_produto'),
    )


class PrevisaoDemanda(db.Model):
    __tablename__ = 'previsao_demanda'
    
    id = db.Column(db.Integer, primary_key=True)
    data_mes = db.Column(db.Integer, nullable=False)
    data_ano = db.Column(db.Integer, nullable=False, index=True)
    nome_grupo = db.Column(db.String(100), nullable=False, default='GERAL')
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))
    qtd_demanda_prevista = db.Column(db.Numeric(15, 3), nullable=False)
    qtd_demanda_realizada = db.Column(db.Numeric(15, 3), default=0)
    disparo_producao = db.Column(db.String(3))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('data_mes', 'data_ano', 'cod_produto', 'nome_grupo'),
    )


class PlanoMestreProducao(db.Model):
    __tablename__ = 'plano_mestre_producao'
    
    id = db.Column(db.Integer, primary_key=True)
    data_mes = db.Column(db.Integer, nullable=False)
    data_ano = db.Column(db.Integer, nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False)
    nome_produto = db.Column(db.String(255))
    qtd_demanda_prevista = db.Column(db.Numeric(15, 3))
    disparo_producao = db.Column(db.String(3))
    qtd_producao_programada = db.Column(db.Numeric(15, 3), default=0)
    qtd_producao_realizada = db.Column(db.Numeric(15, 3), default=0)
    qtd_estoque = db.Column(db.Numeric(15, 3), default=0)
    qtd_estoque_seguranca = db.Column(db.Numeric(15, 3), default=0)
    qtd_reposicao_sugerida = db.Column(db.Numeric(15, 3))
    qtd_lote_ideal = db.Column(db.Numeric(15, 3))
    qtd_lote_minimo = db.Column(db.Numeric(15, 3))
    status_geracao = db.Column(db.String(20), default='rascunho', index=True)
    criado_por = db.Column(db.String(100))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('data_mes', 'data_ano', 'cod_produto'),
    )


class RecursosProducao(db.Model):
    __tablename__ = 'recursos_producao'
    
    id = db.Column(db.Integer, primary_key=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))
    linha_producao = db.Column(db.String(50), nullable=False, index=True)
    qtd_unidade_por_caixa = db.Column(db.Integer, nullable=False)  # OBRIGATÓRIO para conversão SKU
    capacidade_unidade_minuto = db.Column(db.Numeric(10, 3), nullable=False)
    qtd_lote_ideal = db.Column(db.Numeric(15, 3))
    qtd_lote_minimo = db.Column(db.Numeric(15, 3))
    eficiencia_media = db.Column(db.Numeric(5, 2), default=85.00)
    tempo_setup = db.Column(db.Integer, default=30)
    disponivel = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        # Removido UniqueConstraint para permitir múltiplas linhas por produto
        db.Index('idx_recursos_produto_linha', 'cod_produto', 'linha_producao'),
    )


# REMOVIDO: OrdemProducao
# Modelo deprecated - integração Manufatura/Odoo foi removida.
# Tabela 'ordem_producao' ainda existe no banco mas não é mais usada.
# Produção agora é gerenciada via importação Excel em app/estoque.


class RequisicaoCompras(db.Model):
    __tablename__ = 'requisicao_compras'

    id = db.Column(db.Integer, primary_key=True)
    num_requisicao = db.Column(db.String(30), nullable=False, index=True)  # ✅ REMOVIDO unique=True
    company_id = db.Column(db.String(100), nullable=True, index=True)  # ✅ NOVO: Empresa compradora
    data_requisicao_criacao = db.Column(db.Date, nullable=False)
    usuario_requisicao_criacao = db.Column(db.String(100))
    lead_time_requisicao = db.Column(db.Integer)
    lead_time_previsto = db.Column(db.Integer)
    data_requisicao_solicitada = db.Column(db.Date)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))
    qtd_produto_requisicao = db.Column(db.Numeric(15, 3), nullable=False)
    qtd_produto_sem_requisicao = db.Column(db.Numeric(15, 3), default=0)
    necessidade = db.Column(db.Boolean, default=False)
    data_necessidade = db.Column(db.Date)
    status = db.Column(db.String(20), default='Pendente', index=True)

    # ✅ NOVO: Status da linha no Odoo
    # Valores: 'draft', 'sent', 'to approve', 'purchase', 'done', 'cancel'
    purchase_state = db.Column(db.String(20), index=True)

    # Vínculo com Odoo (MELHORADO)
    importado_odoo = db.Column(db.Boolean, default=False)
    odoo_id = db.Column(db.String(50), unique=True)  # ✅ UNIQUE aqui pois é o ID da LINHA no Odoo
    requisicao_odoo_id = db.Column(db.String(50), index=True)  # ID da requisição no Odoo
    status_requisicao = db.Column(db.String(20), default='rascunho')
    data_envio_odoo = db.Column(db.DateTime)
    data_confirmacao_odoo = db.Column(db.DateTime)
    observacoes_odoo = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # ✅ Constraint única: requisição + produto + empresa (permite múltiplas linhas por requisição)
    __table_args__ = (
        db.UniqueConstraint('num_requisicao', 'cod_produto', 'company_id', name='uq_requisicao_produto_empresa'),
        db.Index('idx_requisicao_empresa', 'company_id', 'num_requisicao'),  # ✅ Índice para filtros
    )


class PedidoCompras(db.Model):
    __tablename__ = 'pedido_compras'

    id = db.Column(db.Integer, primary_key=True)
    num_pedido = db.Column(db.String(30), nullable=False, index=True)  # ✅ CORRIGIDO: Removido unique=True
    company_id = db.Column(db.String(100), nullable=True, index=True)  # ✅ NOVO: Empresa compradora
    num_requisicao = db.Column(db.String(30), index=True)  # ✅ REMOVIDO ForeignKey - agora apenas informativo
    cnpj_fornecedor = db.Column(db.String(20), index=True)
    raz_social = db.Column(db.String(255))
    numero_nf = db.Column(db.String(20))
    data_pedido_criacao = db.Column(db.Date)
    usuario_pedido_criacao = db.Column(db.String(100))
    lead_time_pedido = db.Column(db.Integer)
    lead_time_previsto = db.Column(db.Integer)
    data_pedido_previsao = db.Column(db.Date)
    data_pedido_entrega = db.Column(db.Date)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))
    qtd_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)
    qtd_recebida = db.Column(db.Numeric(15, 3), default=0)  # ✅ NOVO: qty_received do Odoo
    preco_produto_pedido = db.Column(db.Numeric(15, 4))
    icms_produto_pedido = db.Column(db.Numeric(15, 2))
    pis_produto_pedido = db.Column(db.Numeric(15, 2))
    cofins_produto_pedido = db.Column(db.Numeric(15, 2))
    confirmacao_pedido = db.Column(db.Boolean, default=False)
    confirmado_por = db.Column(db.String(100))
    confirmado_em = db.Column(db.DateTime)

    # Status do Odoo (draft, sent, to approve, purchase, done, cancel)
    status_odoo = db.Column(db.String(20), index=True)

    # ✅ NOVO: Tipo de pedido (l10n_br_tipo_pedido do Odoo Brasil)
    # Tipos relevantes: compra, importacao, comp-importacao, devolucao, devolucao_compra,
    # industrializacao, serv-industrializacao, ent-bonificacao
    tipo_pedido = db.Column(db.String(50), nullable=True, index=True)

    importado_odoo = db.Column(db.Boolean, default=False)
    odoo_id = db.Column(db.String(50))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # ✅ ADICIONADO

    # ✅ NOVO: Campos para Documento Fiscal Eletrônico (DFe) - NF de entrada
    dfe_id = db.Column(db.String(50), nullable=True, index=True)           # ID do l10n_br_ciel_it_account.dfe no Odoo
    nf_pdf_path = db.Column(db.String(500), nullable=True)                 # Caminho S3/local do PDF
    nf_xml_path = db.Column(db.String(500), nullable=True)                 # Caminho S3/local do XML
    nf_chave_acesso = db.Column(db.String(44), nullable=True, index=True)  # Chave de acesso NFe (44 dígitos)
    nf_numero = db.Column(db.String(20), nullable=True)                    # Número da NF
    nf_serie = db.Column(db.String(10), nullable=True)                     # Série da NF
    nf_data_emissao = db.Column(db.Date, nullable=True)                    # Data de emissão da NF
    nf_valor_total = db.Column(db.Numeric(15, 2), nullable=True)           # Valor total da NF

    # ✅ CORRIGIDO: Constraint composta para permitir múltiplos produtos no mesmo pedido + empresa
    __table_args__ = (
        db.UniqueConstraint('num_pedido', 'cod_produto', 'company_id', name='uq_pedido_compras_num_cod_produto_empresa'),
        db.Index('idx_pedido_empresa', 'company_id', 'num_pedido'),  # ✅ Índice para filtros
        db.Index('idx_pedido_dfe', 'dfe_id'),                        # ✅ Índice para buscas por DFe
        db.Index('idx_pedido_chave_acesso', 'nf_chave_acesso'),      # ✅ Índice para buscas por chave NFe
    )

    # ✅ Relacionamento removido - num_requisicao agora é apenas campo informativo


class LeadTimeFornecedor(db.Model):
    __tablename__ = 'lead_time_fornecedor'
    
    id = db.Column(db.Integer, primary_key=True)
    cnpj_fornecedor = db.Column(db.String(20), nullable=False, index=True)
    nome_fornecedor = db.Column(db.String(255))
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))
    lead_time_previsto = db.Column(db.Integer, nullable=False)
    lead_time_historico = db.Column(db.Numeric(5, 1))
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('cnpj_fornecedor', 'cod_produto'),
    )


class ListaMateriais(db.Model):
    """
    Estrutura de produtos (BOM - Bill of Materials)
    Registra componentes necessários para fabricar um produto
    """
    __tablename__ = 'lista_materiais'

    id = db.Column(db.Integer, primary_key=True)
    cod_produto_produzido = db.Column(db.String(50), nullable=False, index=True)
    nome_produto_produzido = db.Column(db.String(255))
    cod_produto_componente = db.Column(db.String(50), nullable=False, index=True)
    nome_produto_componente = db.Column(db.String(255))
    qtd_utilizada = db.Column(db.Numeric(15, 6), nullable=False)
    status = db.Column(db.String(10), default='ativo', index=True)
    versao = db.Column(db.String(100), default='v1')

    # Campos de auditoria expandidos
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    inativado_em = db.Column(db.DateTime, nullable=True)
    inativado_por = db.Column(db.String(100), nullable=True)
    motivo_inativacao = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('cod_produto_produzido', 'cod_produto_componente', 'versao'),
        db.Index('idx_lista_materiais_status_data', 'status', 'criado_em'),
    )

    def to_dict(self):
        """Serializa para dict (útil para histórico)"""
        return {
            'id': self.id,
            'cod_produto_produzido': self.cod_produto_produzido,
            'nome_produto_produzido': self.nome_produto_produzido,
            'cod_produto_componente': self.cod_produto_componente,
            'nome_produto_componente': self.nome_produto_componente,
            'qtd_utilizada': float(self.qtd_utilizada) if self.qtd_utilizada else 0,
            'status': self.status,
            'versao': self.versao,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por': self.criado_por,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None,
            'atualizado_por': self.atualizado_por
        }


class ListaMateriaisHistorico(db.Model):
    """
    Histórico de todas as alterações em Lista de Materiais
    Registra criação, edição, inativação e reativação de componentes
    """
    __tablename__ = 'lista_materiais_historico'

    id = db.Column(db.Integer, primary_key=True)

    # Referência ao registro original
    lista_materiais_id = db.Column(db.Integer, nullable=False, index=True)

    # Tipo de operação
    operacao = db.Column(db.String(20), nullable=False, index=True)  # 'CRIAR', 'EDITAR', 'INATIVAR', 'REATIVAR'

    # Dados do produto (snapshot no momento da alteração)
    cod_produto_produzido = db.Column(db.String(50), nullable=False, index=True)
    nome_produto_produzido = db.Column(db.String(255))
    cod_produto_componente = db.Column(db.String(50), nullable=False, index=True)
    nome_produto_componente = db.Column(db.String(255))
    versao = db.Column(db.String(100))

    # Valores ANTES da alteração (null para CRIAR)
    qtd_utilizada_antes = db.Column(db.Numeric(15, 6), nullable=True)
    status_antes = db.Column(db.String(10), nullable=True)

    # Valores DEPOIS da alteração
    qtd_utilizada_depois = db.Column(db.Numeric(15, 6), nullable=True)
    status_depois = db.Column(db.String(10), nullable=True)

    # Metadados da alteração
    alterado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    alterado_por = db.Column(db.String(100), nullable=False, index=True)
    motivo = db.Column(db.Text, nullable=True)  # Motivo da alteração (opcional)

    # Dados adicionais (JSON flexível para futuras extensões)
    dados_adicionais = db.Column(JSONB, nullable=True)

    __table_args__ = (
        db.Index('idx_historico_produto_data', 'cod_produto_produzido', 'alterado_em'),
        db.Index('idx_historico_componente_data', 'cod_produto_componente', 'alterado_em'),
        db.Index('idx_historico_operacao_data', 'operacao', 'alterado_em'),
    )

    def to_dict(self):
        """Serializa para dict"""
        return {
            'id': self.id,
            'lista_materiais_id': self.lista_materiais_id,
            'operacao': self.operacao,
            'cod_produto_produzido': self.cod_produto_produzido,
            'nome_produto_produzido': self.nome_produto_produzido,
            'cod_produto_componente': self.cod_produto_componente,
            'nome_produto_componente': self.nome_produto_componente,
            'versao': self.versao,
            'qtd_utilizada_antes': float(self.qtd_utilizada_antes) if self.qtd_utilizada_antes else None,
            'status_antes': self.status_antes,
            'qtd_utilizada_depois': float(self.qtd_utilizada_depois) if self.qtd_utilizada_depois else None,
            'status_depois': self.status_depois,
            'alterado_em': self.alterado_em.isoformat() if self.alterado_em else None,
            'alterado_por': self.alterado_por,
            'motivo': self.motivo,
            'dados_adicionais': self.dados_adicionais
        }


class HistoricoRequisicaoCompras(db.Model):
    """
    Histórico COMPLETO (snapshot) de Requisições de Compras
    Grava TODOS os campos para permitir comparação completa no modal
    """
    __tablename__ = 'historico_requisicao_compras'

    id = db.Column(db.Integer, primary_key=True)

    # ================================================
    # CAMPOS DE CONTROLE DO HISTÓRICO
    # ================================================
    requisicao_id = db.Column(db.Integer, db.ForeignKey('requisicao_compras.id', ondelete='CASCADE'), nullable=False, index=True)
    operacao = db.Column(db.String(20), nullable=False, index=True)  # 'CRIAR', 'EDITAR'
    alterado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    alterado_por = db.Column(db.String(100), nullable=False, index=True)  # 'Odoo' ou usuário
    write_date_odoo = db.Column(db.DateTime, nullable=True)

    # ================================================
    # SNAPSHOT COMPLETO - MESMOS CAMPOS DA REQUISICAO
    # ================================================

    # Campos principais
    num_requisicao = db.Column(db.String(30), nullable=False, index=True)
    company_id = db.Column(db.String(100), nullable=True)  # ✅ NOVO: Empresa compradora
    data_requisicao_criacao = db.Column(db.Date, nullable=False)
    usuario_requisicao_criacao = db.Column(db.String(100))
    lead_time_requisicao = db.Column(db.Integer)
    lead_time_previsto = db.Column(db.Integer)
    data_requisicao_solicitada = db.Column(db.Date)

    # Produto
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))

    # Quantidades
    qtd_produto_requisicao = db.Column(db.Numeric(15, 3), nullable=False)
    qtd_produto_sem_requisicao = db.Column(db.Numeric(15, 3), default=0)

    # Necessidade
    necessidade = db.Column(db.Boolean, default=False)
    data_necessidade = db.Column(db.Date)

    # Status
    status = db.Column(db.String(20), default='Pendente')

    # Vínculo com Odoo
    importado_odoo = db.Column(db.Boolean, default=False)
    odoo_id = db.Column(db.String(50))
    requisicao_odoo_id = db.Column(db.String(50))
    status_requisicao = db.Column(db.String(20), default='rascunho')
    data_envio_odoo = db.Column(db.DateTime)
    data_confirmacao_odoo = db.Column(db.DateTime)
    observacoes_odoo = db.Column(db.Text)

    # Data criação original
    criado_em = db.Column(db.DateTime)

    __table_args__ = (
        db.Index('idx_hist_req_requisicao_data', 'requisicao_id', 'alterado_em'),
        db.Index('idx_hist_req_num_data', 'num_requisicao', 'alterado_em'),
    )

    def to_dict(self):
        """Serializa para dict"""
        return {
            'id': self.id,
            'requisicao_id': self.requisicao_id,
            'operacao': self.operacao,
            'alterado_em': self.alterado_em.isoformat() if self.alterado_em else None,
            'alterado_por': self.alterado_por,
            'write_date_odoo': self.write_date_odoo.isoformat() if self.write_date_odoo else None,
            'num_requisicao': self.num_requisicao,
            'company_id': self.company_id,  # ✅ NOVO
            'data_requisicao_criacao': self.data_requisicao_criacao.isoformat() if self.data_requisicao_criacao else None,
            'usuario_requisicao_criacao': self.usuario_requisicao_criacao,
            'lead_time_requisicao': self.lead_time_requisicao,
            'lead_time_previsto': self.lead_time_previsto,
            'data_requisicao_solicitada': self.data_requisicao_solicitada.isoformat() if self.data_requisicao_solicitada else None,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'qtd_produto_requisicao': float(self.qtd_produto_requisicao) if self.qtd_produto_requisicao else 0,
            'qtd_produto_sem_requisicao': float(self.qtd_produto_sem_requisicao) if self.qtd_produto_sem_requisicao else 0,
            'necessidade': self.necessidade,
            'data_necessidade': self.data_necessidade.isoformat() if self.data_necessidade else None,
            'status': self.status,
            'importado_odoo': self.importado_odoo,
            'odoo_id': self.odoo_id,
            'requisicao_odoo_id': self.requisicao_odoo_id,
            'status_requisicao': self.status_requisicao,
            'data_envio_odoo': self.data_envio_odoo.isoformat() if self.data_envio_odoo else None,
            'data_confirmacao_odoo': self.data_confirmacao_odoo.isoformat() if self.data_confirmacao_odoo else None,
            'observacoes_odoo': self.observacoes_odoo,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
        }


class HistoricoPedidoCompras(db.Model):
    """
    Histórico COMPLETO (snapshot) de Pedidos de Compras
    Grava TODOS os campos para permitir comparação completa no modal
    Segue EXATAMENTE o padrão de HistoricoRequisicaoCompras
    """
    __tablename__ = 'historico_pedido_compras'

    id = db.Column(db.Integer, primary_key=True)

    # ================================================
    # CAMPOS DE CONTROLE DO HISTÓRICO
    # ================================================
    pedido_compra_id = db.Column(db.Integer, db.ForeignKey('pedido_compras.id', ondelete='CASCADE'), nullable=False, index=True)
    operacao = db.Column(db.String(20), nullable=False, index=True)  # 'CRIAR', 'EDITAR'
    alterado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    alterado_por = db.Column(db.String(100), nullable=False, index=True)  # 'Odoo' ou usuário
    write_date_odoo = db.Column(db.DateTime, nullable=True)

    # ================================================
    # SNAPSHOT COMPLETO - MESMOS CAMPOS DO PEDIDOCOMPRAS
    # ================================================

    # Campos principais
    num_pedido = db.Column(db.String(30), nullable=False, index=True)
    company_id = db.Column(db.String(100), nullable=True)  # ✅ NOVO: Empresa compradora
    num_requisicao = db.Column(db.String(30))
    cnpj_fornecedor = db.Column(db.String(20))
    raz_social = db.Column(db.String(255))
    numero_nf = db.Column(db.String(20))

    # Datas
    data_pedido_criacao = db.Column(db.Date)
    usuario_pedido_criacao = db.Column(db.String(100))
    lead_time_pedido = db.Column(db.Integer)
    lead_time_previsto = db.Column(db.Integer)
    data_pedido_previsao = db.Column(db.Date)
    data_pedido_entrega = db.Column(db.Date)

    # Produto
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))

    # Quantidades e valores
    qtd_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)
    qtd_recebida = db.Column(db.Numeric(15, 3), default=0)
    preco_produto_pedido = db.Column(db.Numeric(15, 4))
    icms_produto_pedido = db.Column(db.Numeric(15, 2))
    pis_produto_pedido = db.Column(db.Numeric(15, 2))
    cofins_produto_pedido = db.Column(db.Numeric(15, 2))

    # Confirmação
    confirmacao_pedido = db.Column(db.Boolean, default=False)
    confirmado_por = db.Column(db.String(100))
    confirmado_em = db.Column(db.DateTime)

    # Status e tipo
    status_odoo = db.Column(db.String(20))
    tipo_pedido = db.Column(db.String(50))

    # Vínculo com Odoo
    importado_odoo = db.Column(db.Boolean, default=False)
    odoo_id = db.Column(db.String(50))

    # Datas originais
    criado_em = db.Column(db.DateTime)
    atualizado_em = db.Column(db.DateTime)

    __table_args__ = (
        db.Index('idx_hist_ped_pedido_data', 'pedido_compra_id', 'alterado_em'),
        db.Index('idx_hist_ped_num_data', 'num_pedido', 'alterado_em'),
    )

    def to_dict(self):
        """Serializa para dict"""
        return {
            'id': self.id,
            'pedido_compra_id': self.pedido_compra_id,
            'operacao': self.operacao,
            'alterado_em': self.alterado_em.isoformat() if self.alterado_em else None,
            'alterado_por': self.alterado_por,
            'write_date_odoo': self.write_date_odoo.isoformat() if self.write_date_odoo else None,
            'num_pedido': self.num_pedido,
            'company_id': self.company_id,  # ✅ NOVO
            'num_requisicao': self.num_requisicao,
            'cnpj_fornecedor': self.cnpj_fornecedor,
            'raz_social': self.raz_social,
            'numero_nf': self.numero_nf,
            'data_pedido_criacao': self.data_pedido_criacao.isoformat() if self.data_pedido_criacao else None,
            'usuario_pedido_criacao': self.usuario_pedido_criacao,
            'lead_time_pedido': self.lead_time_pedido,
            'lead_time_previsto': self.lead_time_previsto,
            'data_pedido_previsao': self.data_pedido_previsao.isoformat() if self.data_pedido_previsao else None,
            'data_pedido_entrega': self.data_pedido_entrega.isoformat() if self.data_pedido_entrega else None,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'qtd_produto_pedido': float(self.qtd_produto_pedido) if self.qtd_produto_pedido else 0,
            'qtd_recebida': float(self.qtd_recebida) if self.qtd_recebida else 0,
            'preco_produto_pedido': float(self.preco_produto_pedido) if self.preco_produto_pedido else 0,
            'icms_produto_pedido': float(self.icms_produto_pedido) if self.icms_produto_pedido else 0,
            'pis_produto_pedido': float(self.pis_produto_pedido) if self.pis_produto_pedido else 0,
            'cofins_produto_pedido': float(self.cofins_produto_pedido) if self.cofins_produto_pedido else 0,
            'confirmacao_pedido': self.confirmacao_pedido,
            'confirmado_por': self.confirmado_por,
            'confirmado_em': self.confirmado_em.isoformat() if self.confirmado_em else None,
            'status_odoo': self.status_odoo,
            'tipo_pedido': self.tipo_pedido,
            'importado_odoo': self.importado_odoo,
            'odoo_id': self.odoo_id,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None,
        }


class LogIntegracao(db.Model):
    __tablename__ = 'log_integracao'

    id = db.Column(db.Integer, primary_key=True)
    tipo_integracao = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    mensagem = db.Column(db.Text)
    registros_processados = db.Column(db.Integer, default=0)
    registros_erro = db.Column(db.Integer, default=0)
    data_execucao = db.Column(db.DateTime, default=datetime.utcnow)
    tempo_execucao = db.Column(db.Float)
    detalhes = db.Column(JSONB)


class RequisicaoCompraAlocacao(db.Model):
    """
    Tabela intermediária N:N entre Requisições de Compra e Pedidos de Compra
    Mapeia purchase.request.allocation do Odoo

    Permite rastrear:
    - Qual requisição gerou qual pedido de compra
    - Quantidades alocadas vs abertas
    - Status de atendimento de requisições
    """
    __tablename__ = 'requisicao_compra_alocacao'

    id = db.Column(db.Integer, primary_key=True)

    # ================================================
    # RELACIONAMENTOS PRINCIPAIS
    # ================================================

    # FK para RequisicaoCompras (purchase.request.line)
    requisicao_compra_id = db.Column(
        db.Integer,
        db.ForeignKey('requisicao_compras.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # FK para PedidoCompras (purchase.order.line) - NULLABLE pois pode não existir ainda
    pedido_compra_id = db.Column(
        db.Integer,
        db.ForeignKey('pedido_compras.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )

    # ================================================
    # IDs DO ODOO (para sincronização)
    # ================================================

    odoo_allocation_id = db.Column(db.String(50), unique=True, index=True)  # ID da alocação no Odoo
    purchase_request_line_odoo_id = db.Column(db.String(50), nullable=False, index=True)  # purchase.request.line ID
    purchase_order_line_odoo_id = db.Column(db.String(50), nullable=True, index=True)  # purchase.order.line ID

    # ================================================
    # PRODUTO (para queries sem JOIN)
    # ================================================

    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255), nullable=True)

    # ✅ NOVO: Empresa compradora (denormalizado para performance)
    company_id = db.Column(db.String(100), nullable=True, index=True)

    # ================================================
    # QUANTIDADES (conforme Odoo)
    # ================================================

    qtd_alocada = db.Column(db.Numeric(15, 3), nullable=False)  # allocated_product_qty
    qtd_requisitada = db.Column(db.Numeric(15, 3), nullable=False)  # requested_product_uom_qty
    qtd_aberta = db.Column(db.Numeric(15, 3), default=0)  # open_product_qty

    # ================================================
    # STATUS E CONTROLE
    # ================================================

    purchase_state = db.Column(db.String(20), nullable=True)  # 'draft', 'sent', 'purchase', 'done', 'cancel'
    stock_move_odoo_id = db.Column(db.String(50), nullable=True)  # ID do movimento de estoque

    # ================================================
    # AUDITORIA
    # ================================================

    importado_odoo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Datas do Odoo
    create_date_odoo = db.Column(db.DateTime, nullable=True)
    write_date_odoo = db.Column(db.DateTime, nullable=True)

    # ================================================
    # RELACIONAMENTOS (SQLAlchemy)
    # ================================================

    requisicao = db.relationship('RequisicaoCompras', backref='alocacoes')
    pedido = db.relationship('PedidoCompras', backref='alocacoes')

    # ================================================
    # CONSTRAINTS E ÍNDICES
    # ================================================

    __table_args__ = (
        # Não permitir duplicação de alocação
        db.UniqueConstraint('purchase_request_line_odoo_id', 'purchase_order_line_odoo_id',
                           name='uq_allocation_request_order'),

        # Índices compostos para queries comuns
        db.Index('idx_alocacao_requisicao_pedido', 'requisicao_compra_id', 'pedido_compra_id'),
        db.Index('idx_alocacao_produto_estado', 'cod_produto', 'purchase_state'),
        db.Index('idx_alocacao_odoo_ids', 'purchase_request_line_odoo_id', 'purchase_order_line_odoo_id'),
    )

    def __repr__(self):
        return f'<RequisicaoCompraAlocacao {self.id} - Req:{self.requisicao_compra_id} → Ped:{self.pedido_compra_id}>'

    def percentual_alocado(self):
        """Calcula % de atendimento da requisição"""
        if self.qtd_requisitada and self.qtd_requisitada > 0:
            return round((float(self.qtd_alocada) / float(self.qtd_requisitada)) * 100, 2)
        return 0.0

    def to_dict(self):
        """Serializa para dict"""
        return {
            'id': self.id,
            'requisicao_compra_id': self.requisicao_compra_id,
            'pedido_compra_id': self.pedido_compra_id,
            'odoo_allocation_id': self.odoo_allocation_id,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'qtd_alocada': float(self.qtd_alocada) if self.qtd_alocada else 0,
            'qtd_requisitada': float(self.qtd_requisitada) if self.qtd_requisitada else 0,
            'qtd_aberta': float(self.qtd_aberta) if self.qtd_aberta else 0,
            'percentual_alocado': self.percentual_alocado(),
            'purchase_state': self.purchase_state,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
        }
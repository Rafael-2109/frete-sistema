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
    nome_grupo = db.Column(db.String(100))
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


class OrdemProducao(db.Model):
    __tablename__ = 'ordem_producao'
    
    id = db.Column(db.Integer, primary_key=True)
    numero_ordem = db.Column(db.String(20), unique=True, nullable=False, index=True)
    origem_ordem = db.Column(db.String(10))
    status = db.Column(db.String(20), default='Planejada', index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255))
    materiais_necessarios = db.Column(JSONB)
    qtd_planejada = db.Column(db.Numeric(15, 3), nullable=False)
    qtd_produzida = db.Column(db.Numeric(15, 3), default=0)
    data_inicio_prevista = db.Column(db.Date, nullable=False, index=True)
    data_fim_prevista = db.Column(db.Date, nullable=False)
    data_inicio_real = db.Column(db.Date)
    data_fim_real = db.Column(db.Date)
    data_necessidade = db.Column(db.Date)  # NOVO: Data calculada com lead time
    
    # Relacionamento Pai-Filho (NOVO)
    ordem_pai_id = db.Column(db.Integer, db.ForeignKey('ordem_producao.id'), index=True)
    tipo_ordem = db.Column(db.String(20), default='principal')  # 'principal', 'filha'
    nivel_bom = db.Column(db.Integer, default=0)
    recalculo_automatico = db.Column(db.Boolean, default=True)
    
    # Sequenciamento (NOVO)
    sequencia_producao = db.Column(db.Integer)
    disponibilidade_componentes = db.Column(db.Numeric(5, 2), default=0)  # %
    data_disponibilidade_componentes = db.Column(db.Date)
    maquina_alocada = db.Column(db.String(50))
    tempo_setup_minutos = db.Column(db.Integer, default=0)
    capacidade_maquina_hora = db.Column(db.Numeric(15, 3))
    
    linha_producao = db.Column(db.String(50), index=True)
    turno = db.Column(db.String(20))
    lote_producao = db.Column(db.String(50))
    custo_previsto = db.Column(db.Numeric(15, 2))
    custo_real = db.Column(db.Numeric(15, 2))
    
    # Campos de vínculo MTO
    separacao_lote_id = db.Column(db.String(50), index=True)  # Vínculo principal
    num_pedido_origem = db.Column(db.String(50))  # Para referência
    raz_social_red = db.Column(db.String(255))  # Cliente do pedido
    qtd_pedido_atual = db.Column(db.Numeric(15, 3))  # Quantidade atual do pedido
    
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relacionamentos
    ordem_pai = db.relationship('OrdemProducao', remote_side=[id], backref='ordens_filhas')


class RequisicaoCompras(db.Model):
    __tablename__ = 'requisicao_compras'
    
    id = db.Column(db.Integer, primary_key=True)
    num_requisicao = db.Column(db.String(30), unique=True, nullable=False, index=True)
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
    
    # Vínculo com Odoo (MELHORADO)
    importado_odoo = db.Column(db.Boolean, default=False)
    odoo_id = db.Column(db.String(50))
    requisicao_odoo_id = db.Column(db.String(50), index=True)  # NOVO: ID da requisição no Odoo
    status_requisicao = db.Column(db.String(20), default='rascunho')  # NOVO: 'rascunho', 'enviada_odoo', 'confirmada'
    data_envio_odoo = db.Column(db.DateTime)  # NOVO
    data_confirmacao_odoo = db.Column(db.DateTime)  # NOVO
    observacoes_odoo = db.Column(db.Text)  # NOVO
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


class PedidoCompras(db.Model):
    __tablename__ = 'pedido_compras'
    
    id = db.Column(db.Integer, primary_key=True)
    num_pedido = db.Column(db.String(30), unique=True, nullable=False, index=True)
    num_requisicao = db.Column(db.String(30), db.ForeignKey('requisicao_compras.num_requisicao'), index=True)
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
    preco_produto_pedido = db.Column(db.Numeric(15, 4))
    icms_produto_pedido = db.Column(db.Numeric(15, 2))
    pis_produto_pedido = db.Column(db.Numeric(15, 2))
    cofins_produto_pedido = db.Column(db.Numeric(15, 2))
    confirmacao_pedido = db.Column(db.Boolean, default=False)
    confirmado_por = db.Column(db.String(100))
    confirmado_em = db.Column(db.DateTime)
    importado_odoo = db.Column(db.Boolean, default=False)
    odoo_id = db.Column(db.String(50))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    requisicao = db.relationship('RequisicaoCompras', backref='pedidos')


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
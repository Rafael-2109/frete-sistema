from typing import Optional

from app import db
from datetime import datetime, date, timedelta
from app.utils.timezone import agora_utc_naive
from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.orm import relationship
import json
import re


# =============================================================================
# CONTAS A RECEBER - MODELOS
# =============================================================================

class ContasAReceberTipo(db.Model):
    """
    Tabela de domínio para tipos usados em Contas a Receber e Abatimento.

    Campos:
    - tipo: Nome do tipo (ex: "Título Negociado", "Portal", "Devolução")
    - considera_a_receber: Se considera na projeção de contas a receber
    - tabela: Nome da tabela onde é usado (contas_a_receber, contas_a_receber_abatimento)
    - campo: Nome do campo onde é usado (confirmacao, forma_confirmacao, acao_necessaria, tipo)
    - explicacao: Descrição do tipo
    """
    __tablename__ = 'contas_a_receber_tipos'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(100), nullable=False)
    considera_a_receber = db.Column(db.Boolean, default=True, nullable=False)
    tabela = db.Column(db.String(50), nullable=False)  # contas_a_receber, contas_a_receber_abatimento
    campo = db.Column(db.String(50), nullable=False)   # confirmacao, forma_confirmacao, acao_necessaria, tipo
    explicacao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)

    __table_args__ = (
        Index('idx_tipo_tabela_campo', 'tabela', 'campo'),
        UniqueConstraint('tipo', 'tabela', 'campo', name='uq_tipo_tabela_campo'),
    )

    def __repr__(self):
        return f'<ContasAReceberTipo {self.tipo} ({self.tabela}.{self.campo})>'

    def to_dict(self):
        return {
            'id': self.id,
            'tipo': self.tipo,
            'considera_a_receber': self.considera_a_receber,
            'tabela': self.tabela,
            'campo': self.campo,
            'explicacao': self.explicacao,
            'ativo': self.ativo
        }


class MapeamentoTipoOdoo(db.Model):
    """
    Mapeia tipos de abatimento do SISTEMA para tipos de baixa do ODOO.

    Relacionamento N:1 - Múltiplos tipos do sistema podem mapear para 1 tipo Odoo.
    Isso permite que o sistema tenha granularidade maior que o Odoo.

    Tipos Odoo (baseado em account.partial.reconcile):
    - pagamento: payment_id IS NOT NULL (entrada de dinheiro)
    - devolucao: move_type='out_refund' (nota de crédito de cliente)
    - abatimento_acordo: move_type='entry' + journal PACORD (acordos comerciais)
    - abatimento_devolucao: move_type='entry' + journal PDEVOL (abatimentos de devolução)
    - abatimento_st: move_type='entry' + ref contém "ST" (substituição tributária)
    - abatimento_outros: move_type='entry' + outros casos
    """
    __tablename__ = 'mapeamento_tipo_odoo'

    id = db.Column(db.Integer, primary_key=True)

    # FK para ContasAReceberTipo (tipo do sistema)
    tipo_sistema_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber_tipos.id'), nullable=False, index=True)

    # Tipo correspondente no Odoo
    # Valores: pagamento, devolucao, abatimento_acordo, abatimento_devolucao, abatimento_st, abatimento_outros
    tipo_odoo = db.Column(db.String(50), nullable=False, index=True)

    # Prioridade de match (menor = maior prioridade)
    prioridade = db.Column(db.Integer, default=100)

    # Tolerância de valor para match (padrão 0.02)
    tolerancia_valor = db.Column(db.Float, default=0.02)

    # Controle
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)

    # Relacionamento
    tipo_sistema = relationship('ContasAReceberTipo', foreign_keys=[tipo_sistema_id])

    __table_args__ = (
        UniqueConstraint('tipo_sistema_id', 'tipo_odoo', name='uq_mapeamento_tipo_sistema_odoo'),
        Index('idx_mapeamento_tipo_odoo', 'tipo_odoo'),
    )

    def __repr__(self):
        return f'<MapeamentoTipoOdoo {self.tipo_sistema_id} -> {self.tipo_odoo}>'

    def to_dict(self):
        return {
            'id': self.id,
            'tipo_sistema_id': self.tipo_sistema_id,
            'tipo_sistema': self.tipo_sistema.tipo if self.tipo_sistema else None,
            'tipo_odoo': self.tipo_odoo,
            'prioridade': self.prioridade,
            'tolerancia_valor': self.tolerancia_valor,
            'ativo': self.ativo
        }

    @staticmethod
    def get_tipos_odoo_disponiveis():
        """Retorna lista de tipos Odoo disponíveis para mapeamento"""
        return [
            {'valor': 'pagamento', 'label': 'Pagamento (Entrada de Dinheiro)', 'descricao': 'payment_id IS NOT NULL'},
            {'valor': 'devolucao', 'label': 'Devolução (Nota de Crédito)', 'descricao': 'move_type=out_refund'},
            {'valor': 'abatimento_acordo', 'label': 'Abatimento - Acordo', 'descricao': 'journal PACORD'},
            {'valor': 'abatimento_devolucao', 'label': 'Abatimento - Devolução', 'descricao': 'journal PDEVOL'},
            {'valor': 'abatimento_st', 'label': 'Abatimento - ST', 'descricao': 'ref contém "ST"'},
            {'valor': 'abatimento_outros', 'label': 'Abatimento - Outros', 'descricao': 'outros casos'},
        ]


class LiberacaoAntecipacao(db.Model):
    """
    Configuração de prazos de liberação para antecipação de recebíveis.

    Critérios de identificação (em ordem de prioridade):
    1. prefixo_cnpj: Primeiros 8 dígitos do CNPJ (XX.XXX.XXX)
    2. nome_exato: Match exato da razão social (UPPERCASE, sem acentos)
    3. contem_nome: LIKE no nome (contém substring)
    """
    __tablename__ = 'liberacao_antecipacao'

    id = db.Column(db.Integer, primary_key=True)

    # Critério de identificação: prefixo_cnpj, nome_exato, contem_nome
    criterio_identificacao = db.Column(db.String(20), nullable=False)

    # Valor para identificação (prefixo CNPJ ou nome)
    identificador = db.Column(db.String(255), nullable=False)

    # UF: "TODOS" ou lista de UFs separadas por vírgula (ex: "SP,RJ,MG")
    uf = db.Column(db.String(100), default='TODOS', nullable=False)

    # Dias úteis para liberação após entrega
    dias_uteis_previsto = db.Column(db.Integer, nullable=False)

    # Controle
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)
    atualizado_por = db.Column(db.String(100), nullable=True)

    __table_args__ = (
        Index('idx_liberacao_criterio', 'criterio_identificacao', 'identificador'),
    )

    def __repr__(self):
        return f'<LiberacaoAntecipacao {self.criterio_identificacao}: {self.identificador} ({self.dias_uteis_previsto} dias)>'

    def to_dict(self):
        return {
            'id': self.id,
            'criterio_identificacao': self.criterio_identificacao,
            'identificador': self.identificador,
            'uf': self.uf,
            'dias_uteis_previsto': self.dias_uteis_previsto,
            'ativo': self.ativo
        }

    @staticmethod
    def limpar_cnpj(cnpj: str) -> str:
        """Remove formatação do CNPJ, mantendo apenas dígitos"""
        if not cnpj:
            return ''
        return re.sub(r'\D', '', str(cnpj))

    @staticmethod
    def extrair_prefixo_cnpj(cnpj: str) -> str:
        """Extrai os primeiros 8 dígitos do CNPJ (XX.XXX.XXX)"""
        cnpj_limpo = LiberacaoAntecipacao.limpar_cnpj(cnpj)
        return cnpj_limpo[:8] if len(cnpj_limpo) >= 8 else cnpj_limpo

    @staticmethod
    def normalizar_nome(nome: str) -> str:
        """Normaliza nome para comparação (uppercase, sem acentos extras)"""
        if not nome:
            return ''
        return nome.strip().upper()

    @classmethod
    def buscar_configuracao(cls, cnpj: str, razao_social: str, uf: str = None) -> 'LiberacaoAntecipacao':
        """
        Busca configuração de liberação por prioridade:
        1. Prefixo CNPJ
        2. Nome Exato
        3. Contém Nome

        Args:
            cnpj: CNPJ do cliente
            razao_social: Razão social do cliente
            uf: UF do cliente (opcional, para filtro adicional)

        Returns:
            LiberacaoAntecipacao ou None
        """
        prefixo = cls.extrair_prefixo_cnpj(cnpj)
        nome_normalizado = cls.normalizar_nome(razao_social)

        # Prioridade 1: Prefixo CNPJ
        if prefixo:
            config = cls.query.filter(
                cls.criterio_identificacao == 'prefixo_cnpj',
                cls.identificador == prefixo,
                cls.ativo == True
            ).first()

            if config and cls._valida_uf(config, uf):
                return config

        # Prioridade 2: Nome Exato
        if nome_normalizado:
            config = cls.query.filter(
                cls.criterio_identificacao == 'nome_exato',
                db.func.upper(cls.identificador) == nome_normalizado,
                cls.ativo == True
            ).first()

            if config and cls._valida_uf(config, uf):
                return config

        # Prioridade 3: Contém Nome
        if nome_normalizado:
            configs = cls.query.filter(
                cls.criterio_identificacao == 'contem_nome',
                cls.ativo == True
            ).all()

            for config in configs:
                identificador_norm = cls.normalizar_nome(config.identificador)
                if identificador_norm and identificador_norm in nome_normalizado:
                    if cls._valida_uf(config, uf):
                        return config

        return None  # type: ignore

    @staticmethod
    def _valida_uf(config: 'LiberacaoAntecipacao', uf: str) -> bool:
        """Valida se a UF está na lista de UFs permitidas"""
        if not uf or config.uf == 'TODOS':
            return True

        ufs_permitidas = [u.strip().upper() for u in config.uf.split(',')]
        return uf.upper() in ufs_permitidas

    @staticmethod
    def calcular_data_liberacao(data_entrega: datetime, dias_uteis: int) -> date:
        """
        Calcula a data de liberação considerando dias úteis.

        Args:
            data_entrega: Data/hora da entrega realizada
            dias_uteis: Quantidade de dias úteis a adicionar

        Returns:
            Data de liberação prevista
        """
        if not data_entrega:
            return None

        data_base = data_entrega.date() if isinstance(data_entrega, datetime) else data_entrega
        dias_adicionados = 0
        data_atual = data_base

        while dias_adicionados < dias_uteis:
            data_atual += timedelta(days=1)
            # Considera apenas dias de semana (0=segunda, 6=domingo)
            if data_atual.weekday() < 5:  # Segunda a Sexta
                dias_adicionados += 1

        return data_atual


class ContasAReceber(db.Model):
    """
    Contas a Receber - Dados importados do Odoo com enriquecimento local.

    Chave única: empresa + titulo_nf + parcela

    Fontes de dados:
    - ODOO: empresa, titulo_nf, parcela, cnpj, razao_social, emissao, vencimento,
            valor_original, desconto_percentual, desconto, tipo_titulo
    - SISTEMA: confirmacao, forma_confirmacao, observacao, alerta, acao_necessaria, etc.
    - CALCULADO: valor_titulo (valor_original - desconto - abatimentos),
                 liberacao_prevista_antecipacao (via LiberacaoAntecipacao + EntregaMonitorada)
    - ENRIQUECIDO: dados de EntregaMonitorada, FaturamentoProduto, AgendamentoEntrega
    """
    __tablename__ = 'contas_a_receber'

    id = db.Column(db.Integer, primary_key=True)

    # =========================================================================
    # CAMPOS DO ODOO (importados automaticamente)
    # =========================================================================

    # Identificação única
    empresa = db.Column(db.Integer, nullable=False, index=True)  # 1=FB, 2=SC, 3=CD
    titulo_nf = db.Column(db.String(20), nullable=False, index=True)  # NF-e
    parcela = db.Column(db.String(10), nullable=False, index=True)  # Número da parcela

    # Cliente
    cnpj = db.Column(db.String(20), nullable=True, index=True)  # CNPJ do cliente
    raz_social = db.Column(db.String(255), nullable=True)  # Razão Social completa
    raz_social_red = db.Column(db.String(100), nullable=True)  # Nome fantasia/trade_name
    uf_cliente = db.Column(db.String(2), nullable=True, index=True)  # UF do cliente

    # Datas do Odoo
    emissao = db.Column(db.Date, nullable=True)  # Data de emissão (date)
    vencimento = db.Column(db.Date, nullable=True, index=True)  # Data de vencimento (date_maturity)

    # Valores do Odoo
    valor_original = db.Column(db.Float, nullable=True)  # Saldo Total (balance + desconto_concedido)
    desconto_percentual = db.Column(db.Float, nullable=True)  # desconto_concedido_percentual / 100
    desconto = db.Column(db.Float, nullable=True)  # desconto_concedido

    # Tipo do título
    tipo_titulo = db.Column(db.String(100), nullable=True)  # Forma de Pagamento (payment_provider_id)

    # Status do Odoo
    parcela_paga = db.Column(db.Boolean, default=False)  # l10n_br_paga
    status_pagamento_odoo = db.Column(db.String(50), nullable=True)  # x_studio_status_de_pagamento

    # =========================================================================
    # CAMPOS CALCULADOS
    # =========================================================================

    # Valor do título (calculado: valor_original - desconto - SUM(abatimentos))
    valor_titulo = db.Column(db.Float, nullable=True)

    # Data de liberação prevista para antecipação (calculado via LiberacaoAntecipacao)
    liberacao_prevista_antecipacao = db.Column(db.Date, nullable=True)

    # =========================================================================
    # CAMPOS DO SISTEMA (preenchidos manualmente)
    # =========================================================================

    # Confirmação
    confirmacao_tipo_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber_tipos.id'), nullable=True)
    forma_confirmacao_tipo_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber_tipos.id'), nullable=True)
    data_confirmacao = db.Column(db.DateTime, nullable=True)  # Log automático
    confirmado_por = db.Column(db.String(100), nullable=True)  # Quem confirmou (para fins financeiros)
    confirmacao_entrega = db.Column(db.Text, nullable=True)

    # Observações e alertas
    observacao = db.Column(db.Text, nullable=True)
    alerta = db.Column(db.Boolean, default=False, nullable=False)

    # Ação necessária
    acao_necessaria_tipo_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber_tipos.id'), nullable=True)
    obs_acao_necessaria = db.Column(db.Text, nullable=True)
    data_lembrete = db.Column(db.Date, nullable=True)

    # =========================================================================
    # CAMPOS DE RELACIONAMENTO (dados obtidos dinamicamente)
    # =========================================================================

    # EntregaMonitorada - FK para obter dados dinamicamente
    # Campos disponíveis via relacionamento entrega_monitorada:
    # - status_finalizacao, data_hora_entrega_realizada, nova_nf, reagendar
    # - data_embarque, transportadora, vendedor, canhoto_arquivo, nf_cd
    # - data_entrega_prevista, agendamentos (último agendamento)
    entrega_monitorada_id = db.Column(db.Integer, db.ForeignKey('entregas_monitoradas.id'), nullable=True)

    # FaturamentoProduto - nf_cancelada é obtido dinamicamente via property

    # =========================================================================
    # AUDITORIA E CONTROLE
    # =========================================================================

    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # Controle de sincronização
    odoo_write_date = db.Column(db.DateTime, nullable=True)  # write_date do Odoo para sync incremental
    ultima_sincronizacao = db.Column(db.DateTime, nullable=True)

    # =========================================================================
    # RELACIONAMENTOS
    # =========================================================================

    abatimentos = relationship('ContasAReceberAbatimento', backref='conta_a_receber', lazy='dynamic',
                               cascade='all, delete-orphan')
    snapshots = relationship('ContasAReceberSnapshot', backref='conta_a_receber', lazy='dynamic',
                             cascade='all, delete-orphan')

    # Tipos (FKs)
    confirmacao_tipo = relationship('ContasAReceberTipo', foreign_keys=[confirmacao_tipo_id])
    forma_confirmacao_tipo = relationship('ContasAReceberTipo', foreign_keys=[forma_confirmacao_tipo_id])
    acao_necessaria_tipo = relationship('ContasAReceberTipo', foreign_keys=[acao_necessaria_tipo_id])

    # EntregaMonitorada
    entrega_monitorada = relationship('EntregaMonitorada', foreign_keys=[entrega_monitorada_id])

    __table_args__ = (
        UniqueConstraint('empresa', 'titulo_nf', 'parcela', name='uq_conta_receber_empresa_nf_parcela'),
        Index('idx_conta_receber_vencimento', 'vencimento'),
        Index('idx_conta_receber_cnpj', 'cnpj'),
        Index('idx_conta_receber_nf', 'titulo_nf'),
    )

    def __repr__(self):
        return f'<ContasAReceber {self.empresa}-{self.titulo_nf}-{self.parcela}>'

    @property
    def titulo_parcela_display(self) -> str:
        """Retorna o formato de exibição: Titulo-Parcela"""
        return f"{self.titulo_nf}-{self.parcela}"

    @property
    def empresa_nome(self) -> str:
        """Retorna o nome da empresa baseado no código"""
        nomes = {
            1: 'NACOM GOYA - FB',
            2: 'NACOM GOYA - SC',
            3: 'NACOM GOYA - CD'
        }
        return nomes.get(self.empresa, f'Empresa {self.empresa}')

    @property
    def nf_cancelada(self) -> bool:
        """
        Verifica dinamicamente se a NF está cancelada via FaturamentoProduto.
        Retorna True se qualquer produto da NF tiver status_nf = 'Cancelado'.
        """
        from app.faturamento.models import FaturamentoProduto

        existe_cancelado = FaturamentoProduto.query.filter_by(
            numero_nf=self.titulo_nf,
            status_nf='Cancelado'
        ).first()

        return existe_cancelado is not None

    def calcular_valor_titulo(self) -> float:
        """
        Calcula o valor do título: valor_original - desconto - SUM(abatimentos)
        """
        valor_base = (self.valor_original or 0) - (self.desconto or 0)

        # Somar abatimentos
        total_abatimentos = sum(
            ab.valor or 0 for ab in self.abatimentos.filter_by(previsto=False).all()
        )

        return valor_base - total_abatimentos

    def atualizar_valor_titulo(self):
        """Atualiza o campo valor_titulo com o cálculo atual"""
        self.valor_titulo = self.calcular_valor_titulo()

    def calcular_liberacao_antecipacao(self):
        """
        Calcula a data de liberação prevista para antecipação.
        Usa LiberacaoAntecipacao + data_hora_entrega_realizada (via entrega_monitorada).
        """
        # Obtém data_hora_entrega_realizada via relacionamento
        data_entrega = None
        if self.entrega_monitorada:
            data_entrega = self.entrega_monitorada.data_hora_entrega_realizada

        if not data_entrega:
            self.liberacao_prevista_antecipacao = None
            return

        config = LiberacaoAntecipacao.buscar_configuracao(
            cnpj=self.cnpj,
            razao_social=self.raz_social,
            uf=self.uf_cliente
        )

        if config:
            self.liberacao_prevista_antecipacao = LiberacaoAntecipacao.calcular_data_liberacao(
                data_entrega,
                config.dias_uteis_previsto
            )
        else:
            self.liberacao_prevista_antecipacao = None

    def to_dict(self):
        # Dados do relacionamento EntregaMonitorada
        em = self.entrega_monitorada

        return {
            'id': self.id,
            'empresa': self.empresa,
            'empresa_nome': self.empresa_nome,
            'titulo_nf': self.titulo_nf,
            'parcela': self.parcela,
            'titulo_parcela_display': self.titulo_parcela_display,
            'cnpj': self.cnpj,
            'raz_social': self.raz_social,
            'raz_social_red': self.raz_social_red,
            'uf_cliente': self.uf_cliente,
            'emissao': self.emissao.isoformat() if self.emissao else None,
            'vencimento': self.vencimento.isoformat() if self.vencimento else None,
            'valor_original': self.valor_original,
            'desconto_percentual': self.desconto_percentual,
            'desconto': self.desconto,
            'valor_titulo': self.valor_titulo,
            'tipo_titulo': self.tipo_titulo,
            'parcela_paga': self.parcela_paga,
            'liberacao_prevista_antecipacao': self.liberacao_prevista_antecipacao.isoformat() if self.liberacao_prevista_antecipacao else None,
            'confirmacao_tipo': self.confirmacao_tipo.tipo if self.confirmacao_tipo else None,
            'forma_confirmacao_tipo': self.forma_confirmacao_tipo.tipo if self.forma_confirmacao_tipo else None,
            'data_confirmacao': self.data_confirmacao.isoformat() if self.data_confirmacao else None,
            'confirmado_por': self.confirmado_por,
            'confirmacao_entrega': self.confirmacao_entrega,
            'observacao': self.observacao,
            'alerta': self.alerta,
            'acao_necessaria_tipo': self.acao_necessaria_tipo.tipo if self.acao_necessaria_tipo else None,
            'obs_acao_necessaria': self.obs_acao_necessaria,
            'data_lembrete': self.data_lembrete.isoformat() if self.data_lembrete else None,
            # Campos obtidos via relacionamento entrega_monitorada
            'entrega_monitorada_id': self.entrega_monitorada_id,
            'data_entrega_prevista': em.data_entrega_prevista.isoformat() if em and em.data_entrega_prevista else None,
            'data_hora_entrega_realizada': em.data_hora_entrega_realizada.isoformat() if em and em.data_hora_entrega_realizada else None,
            'status_finalizacao': em.status_finalizacao if em else None,
            'nova_nf': em.nova_nf if em else None,
            'reagendar': em.reagendar if em else False,
            'data_embarque': em.data_embarque.isoformat() if em and em.data_embarque else None,
            'transportadora': em.transportadora if em else None,
            'vendedor': em.vendedor if em else None,
            'canhoto_arquivo': em.canhoto_arquivo if em else None,
            'nf_cd': em.nf_cd if em else False,
            'nf_cancelada': self.nf_cancelada,
            'total_abatimentos': sum(ab.valor or 0 for ab in self.abatimentos.all())
        }

    @property
    def parcela_int(self) -> Optional[int]:
        """Parcela como int, para Odoo API e campos cache INTEGER."""
        from app.financeiro.parcela_utils import parcela_to_int
        return parcela_to_int(self.parcela)


class ContasAReceberAbatimento(db.Model):
    """
    Abatimentos vinculados a Contas a Receber.
    Relacionamento: 1 ContasAReceber : N Abatimentos

    Sistema de dupla conferência:
    - Registros criados manualmente pelo usuário no sistema (mais detalhados)
    - Podem ser vinculados a reconciliações do Odoo (fonte oficial)
    - Flag de comparação indica se totais batem (tolerância 0.02)
    """
    __tablename__ = 'contas_a_receber_abatimento'

    id = db.Column(db.Integer, primary_key=True)

    # FK para ContasAReceber
    conta_a_receber_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber.id'), nullable=False, index=True)

    # Tipo do abatimento (FK para Tipos)
    tipo_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber_tipos.id'), nullable=True)

    # Dados do abatimento
    motivo = db.Column(db.Text, nullable=True)
    doc_motivo = db.Column(db.String(255), nullable=True)  # Documento que justifica
    valor = db.Column(db.Float, nullable=False)

    # Se é previsto ou já realizado
    previsto = db.Column(db.Boolean, default=True, nullable=False)

    # Datas
    data = db.Column(db.Date, nullable=True)
    data_vencimento = db.Column(db.Date, nullable=True)

    # =========================================================================
    # VÍNCULO COM ODOO (Dupla Conferência)
    # =========================================================================

    # FK para reconciliação do Odoo (opcional - vinculação automática ou manual)
    reconciliacao_odoo_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber_reconciliacao.id'), nullable=True, index=True)

    # Status de vinculação com Odoo
    # PENDENTE: Aguardando vinculação (ainda não sincronizou ou não encontrou match)
    # VINCULADO: Vinculado a uma reconciliação do Odoo
    # NAO_ENCONTRADO: Sincronizou mas não encontrou match no Odoo
    # NAO_APLICAVEL: Não precisa vincular ao Odoo (ex: abatimentos locais)
    status_vinculacao = db.Column(db.String(20), default='PENDENTE', nullable=False, index=True)

    # Data/hora da última tentativa de vinculação
    ultima_tentativa_vinculacao = db.Column(db.DateTime, nullable=True)

    # =========================================================================
    # AUDITORIA
    # =========================================================================

    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # Relacionamentos
    tipo = relationship('ContasAReceberTipo', foreign_keys=[tipo_id])
    reconciliacao_odoo = relationship('ContasAReceberReconciliacao', foreign_keys=[reconciliacao_odoo_id],
                                    backref=db.backref('abatimentos_vinculados', lazy='dynamic'))

    __table_args__ = (
        Index('idx_abatimento_status_vinculacao', 'status_vinculacao'),
        Index('idx_abatimento_reconciliacao', 'reconciliacao_odoo_id'),
    )

    def __repr__(self):
        return f'<ContasAReceberAbatimento {self.id} - R$ {self.valor} ({self.status_vinculacao})>'

    @property
    def status_vinculacao_display(self) -> str:
        """Retorna o status de vinculação formatado para exibição"""
        status_map = {
            'PENDENTE': '⏳ Pendente',
            'VINCULADO': '✅ Vinculado',
            'NAO_ENCONTRADO': '❌ Não Encontrado',
            'NAO_APLICAVEL': '➖ N/A'
        }
        return status_map.get(self.status_vinculacao, self.status_vinculacao) #type: ignore

    @property
    def documento_odoo(self) -> str:
        """Retorna o documento do Odoo vinculado (se houver)"""
        if self.reconciliacao_odoo:
            return self.reconciliacao_odoo.credit_move_name or '-'
        return '-'

    def to_dict(self):
        return {
            'id': self.id,
            'conta_a_receber_id': self.conta_a_receber_id,
            'tipo_id': self.tipo_id,
            'tipo': self.tipo.tipo if self.tipo else None,
            'motivo': self.motivo,
            'doc_motivo': self.doc_motivo,
            'valor': self.valor,
            'previsto': self.previsto,
            'data': self.data.isoformat() if self.data else None,
            'data_vencimento': self.data_vencimento.isoformat() if self.data_vencimento else None,
            # Campos de vinculação Odoo
            'reconciliacao_odoo_id': self.reconciliacao_odoo_id,
            'status_vinculacao': self.status_vinculacao,
            'status_vinculacao_display': self.status_vinculacao_display,
            'documento_odoo': self.documento_odoo,
            'ultima_tentativa_vinculacao': self.ultima_tentativa_vinculacao.isoformat() if self.ultima_tentativa_vinculacao else None,
        }


class ContasAReceberSnapshot(db.Model):
    """
    Histórico de alterações em campos vindos do Odoo.
    Registra antes/depois quando dados do Odoo são atualizados.
    """
    __tablename__ = 'contas_a_receber_snapshot'

    id = db.Column(db.Integer, primary_key=True)

    # FK para ContasAReceber
    conta_a_receber_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber.id'), nullable=False, index=True)

    # Campo alterado
    campo = db.Column(db.String(50), nullable=False)

    # Valores (JSON para suportar diferentes tipos)
    valor_anterior = db.Column(db.Text, nullable=True)
    valor_novo = db.Column(db.Text, nullable=True)

    # Auditoria
    alterado_em = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    alterado_por = db.Column(db.String(100), nullable=True)

    # Referência do Odoo
    odoo_write_date = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        Index('idx_snapshot_conta_campo', 'conta_a_receber_id', 'campo'),
    )

    def __repr__(self):
        return f'<ContasAReceberSnapshot {self.campo}: {self.valor_anterior} -> {self.valor_novo}>'

    @classmethod
    def registrar_alteracao(cls, conta: ContasAReceber, campo: str, valor_anterior, valor_novo,
                           usuario: str = None, odoo_write_date: datetime = None):
        """
        Registra uma alteração de campo do Odoo.

        Args:
            conta: Instância de ContasAReceber
            campo: Nome do campo alterado
            valor_anterior: Valor antes da alteração
            valor_novo: Valor depois da alteração
            usuario: Usuário que realizou (ou 'Sistema Odoo')
            odoo_write_date: write_date do Odoo
        """
        # Converter valores para JSON string se necessário
        def to_json_str(val):
            if val is None:
                return None
            if isinstance(val, (date, datetime)):
                return val.isoformat()
            return json.dumps(val) if not isinstance(val, str) else val

        snapshot = cls(
            conta_a_receber_id=conta.id,
            campo=campo,
            valor_anterior=to_json_str(valor_anterior),
            valor_novo=to_json_str(valor_novo),
            alterado_por=usuario or 'Sistema Odoo',
            odoo_write_date=odoo_write_date
        )

        db.session.add(snapshot)
        return snapshot

    def to_dict(self):
        return {
            'id': self.id,
            'conta_a_receber_id': self.conta_a_receber_id,
            'campo': self.campo,
            'valor_anterior': self.valor_anterior,
            'valor_novo': self.valor_novo,
            'alterado_em': self.alterado_em.isoformat() if self.alterado_em else None,
            'alterado_por': self.alterado_por
        }


class ContasAReceberReconciliacao(db.Model):
    """
    Espelha account.partial.reconcile do Odoo (VERSÃO SIMPLIFICADA).

    Esta é a TABELA CHAVE do mecanismo de baixa. Cada registro representa uma
    "ligação" entre uma linha de DÉBITO (título) e uma linha de CRÉDITO (pagamento/abatimento).

    Sistema de Dupla Conferência:
    - Dados do Odoo são importados aqui (fonte oficial)
    - Abatimentos do sistema (ContasAReceberAbatimento) podem ser vinculados
    - Comparação visual: totais sistema vs totais Odoo

    Tipos de Baixa (alinhados com MapeamentoTipoOdoo):
    - pagamento: payment_id IS NOT NULL (entrada de dinheiro)
    - devolucao: move_type='out_refund' (nota de crédito de cliente)
    - abatimento_acordo: move_type='entry' + journal PACORD
    - abatimento_devolucao: move_type='entry' + journal PDEVOL
    - abatimento_st: move_type='entry' + ref contém "ST"
    - abatimento_outros: move_type='entry' + outros casos
    """
    __tablename__ = 'contas_a_receber_reconciliacao'

    id = db.Column(db.Integer, primary_key=True)

    # FK para ContasAReceber (título)
    conta_a_receber_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber.id'), nullable=False, index=True)

    # =========================================================================
    # IDENTIFICAÇÃO ODOO
    # =========================================================================

    odoo_id = db.Column(db.Integer, nullable=False, unique=True, index=True)  # ID no Odoo (account.partial.reconcile)

    # =========================================================================
    # VALOR E DATA
    # =========================================================================

    amount = db.Column(db.Float, nullable=True)  # Valor reconciliado (sempre positivo)
    max_date = db.Column(db.Date, nullable=True)  # Data da reconciliação

    # =========================================================================
    # CLASSIFICAÇÃO DO TIPO DE BAIXA
    # =========================================================================

    # Tipo classificado (alinhado com MapeamentoTipoOdoo para vinculação)
    # Valores: pagamento, devolucao, abatimento_acordo, abatimento_devolucao, abatimento_st, abatimento_outros
    tipo_baixa = db.Column(db.String(50), nullable=True, index=True)

    # Dados originais do Odoo para classificação
    tipo_baixa_odoo = db.Column(db.String(20), nullable=True)  # move_type: entry, out_refund, etc
    payment_odoo_id = db.Column(db.Integer, nullable=True)  # payment_id do Odoo (se for pagamento)
    journal_code = db.Column(db.String(20), nullable=True)  # Código do diário (PACORD, PDEVOL, GRAFENO, etc)

    # =========================================================================
    # REFERÊNCIA VISUAL (para exibição no modal)
    # =========================================================================

    credit_move_name = db.Column(db.String(255), nullable=True)  # Ex: "PGRA1/2025/01834", "RVND/2025/00036"
    credit_move_ref = db.Column(db.String(255), nullable=True)  # Ex: "ABATIMENTO DE ST", "Estorno de: VND/..."

    # =========================================================================
    # IDENTIFICADORES ODOO (para busca de detalhes em tempo real)
    # =========================================================================

    credit_move_id = db.Column(db.Integer, nullable=True)  # ID da linha de crédito no Odoo (account.move.line)
    debit_move_id = db.Column(db.Integer, nullable=True)  # ID da linha de débito (título) no Odoo

    # =========================================================================
    # EMPRESA
    # =========================================================================

    company_id = db.Column(db.Integer, nullable=True)

    # =========================================================================
    # AUDITORIA ODOO
    # =========================================================================

    odoo_create_date = db.Column(db.DateTime, nullable=True)
    odoo_write_date = db.Column(db.DateTime, nullable=True)

    # =========================================================================
    # CONTROLE LOCAL
    # =========================================================================

    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    ultima_sincronizacao = db.Column(db.DateTime, nullable=True)

    # =========================================================================
    # RELACIONAMENTOS
    # =========================================================================

    conta_a_receber = relationship('ContasAReceber', backref=db.backref('reconciliacoes', lazy='dynamic'))

    __table_args__ = (
        Index('idx_reconciliacao_odoo_id', 'odoo_id'),
        Index('idx_reconciliacao_conta', 'conta_a_receber_id'),
        Index('idx_reconciliacao_tipo_baixa', 'tipo_baixa'),
    )

    def __repr__(self):
        return f'<ContasAReceberReconciliacao {self.odoo_id} - R$ {self.amount} ({self.tipo_baixa})>'

    @property
    def tipo_baixa_display(self) -> str:
        """Retorna o tipo de baixa formatado para exibição"""
        tipos = {
            'pagamento': '💰 Pagamento',
            'devolucao': '🔵 Devolução',
            'abatimento_acordo': '🟡 Abat. Acordo',
            'abatimento_devolucao': '🟠 Abat. Devolução',
            'abatimento_st': '🟣 Abat. ST',
            'abatimento_outros': '⚪ Abat. Outros',
        }
        return tipos.get(self.tipo_baixa, self.tipo_baixa or 'Não identificado')

    @property
    def tipo_baixa_simplificado(self) -> str:
        """Retorna tipo simplificado (pagamento ou abatimento)"""
        if self.tipo_baixa == 'pagamento':
            return 'pagamento'
        return 'abatimento'

    @property
    def eh_pagamento(self) -> bool:
        """Retorna True se for um pagamento (entrada de dinheiro)"""
        return self.tipo_baixa == 'pagamento'

    @property
    def eh_abatimento(self) -> bool:
        """Retorna True se for um abatimento/devolução (não é entrada de dinheiro)"""
        return self.tipo_baixa != 'pagamento'

    def to_dict(self):
        """Retorna campos essenciais para o frontend"""
        return {
            # Identificação
            'id': self.id,
            'conta_a_receber_id': self.conta_a_receber_id,
            'odoo_id': self.odoo_id,

            # Valor e data
            'amount': self.amount,
            'max_date': self.max_date.isoformat() if self.max_date else None,

            # Classificação
            'tipo_baixa': self.tipo_baixa,
            'tipo_baixa_display': self.tipo_baixa_display,
            'tipo_baixa_odoo': self.tipo_baixa_odoo,
            'eh_pagamento': self.eh_pagamento,
            'eh_abatimento': self.eh_abatimento,

            # Referência visual
            'credit_move_name': self.credit_move_name,
            'credit_move_ref': self.credit_move_ref,
            'journal_code': self.journal_code,

            # IDs para detalhes
            'credit_move_id': self.credit_move_id,
            'debit_move_id': self.debit_move_id,
            'payment_odoo_id': self.payment_odoo_id,

            # Empresa
            'company_id': self.company_id,

            # Auditoria
            'odoo_create_date': self.odoo_create_date.isoformat() if self.odoo_create_date else None,
            'odoo_write_date': self.odoo_write_date.isoformat() if self.odoo_write_date else None,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'ultima_sincronizacao': self.ultima_sincronizacao.isoformat() if self.ultima_sincronizacao else None,
        }


# =============================================================================
# BAIXA DE TITULOS VIA EXCEL
# =============================================================================


class BaixaTituloLote(db.Model):
    """
    Lote de importacao de baixas via Excel.
    Agrupa multiplas baixas importadas de um mesmo arquivo.
    """
    __tablename__ = 'baixa_titulo_lote'

    id = db.Column(db.Integer, primary_key=True)

    # Identificacao do lote
    nome_arquivo = db.Column(db.String(255), nullable=False)
    hash_arquivo = db.Column(db.String(64), nullable=True)  # SHA256 do arquivo

    # Estatisticas
    total_linhas = db.Column(db.Integer, default=0)
    linhas_validas = db.Column(db.Integer, default=0)
    linhas_invalidas = db.Column(db.Integer, default=0)
    linhas_processadas = db.Column(db.Integer, default=0)
    linhas_sucesso = db.Column(db.Integer, default=0)
    linhas_erro = db.Column(db.Integer, default=0)

    # Status do lote: IMPORTADO, VALIDANDO, VALIDADO, PROCESSANDO, CONCLUIDO, ERRO
    status = db.Column(db.String(20), default='IMPORTADO', nullable=False, index=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)
    processado_em = db.Column(db.DateTime, nullable=True)
    processado_por = db.Column(db.String(100), nullable=True)

    # Relacionamento com itens
    itens = relationship('BaixaTituloItem', backref='lote', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<BaixaTituloLote {self.id} - {self.nome_arquivo} ({self.status})>'

    def to_dict(self):
        return {
            'id': self.id,
            'nome_arquivo': self.nome_arquivo,
            'total_linhas': self.total_linhas,
            'linhas_validas': self.linhas_validas,
            'linhas_invalidas': self.linhas_invalidas,
            'linhas_processadas': self.linhas_processadas,
            'linhas_sucesso': self.linhas_sucesso,
            'linhas_erro': self.linhas_erro,
            'status': self.status,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por': self.criado_por,
            'processado_em': self.processado_em.isoformat() if self.processado_em else None,
            'processado_por': self.processado_por
        }


class BaixaTituloItem(db.Model):
    """
    Item individual de baixa de titulo.
    Registra dados do Excel + validacao + resultado da operacao no Odoo.

    Fluxo:
    1. Excel importado -> status = PENDENTE
    2. Validacao -> status = VALIDO ou INVALIDO
    3. Usuario ativa/inativa -> ativo = True/False
    4. Processamento -> status = PROCESSANDO -> SUCESSO ou ERRO
    """
    __tablename__ = 'baixa_titulo_item'

    id = db.Column(db.Integer, primary_key=True)

    # FK para o lote
    lote_id = db.Column(db.Integer, db.ForeignKey('baixa_titulo_lote.id'), nullable=False, index=True)

    # Linha do Excel (para referencia)
    linha_excel = db.Column(db.Integer, nullable=False)

    # =========================================================================
    # DADOS DO EXCEL (entrada do usuario)
    # =========================================================================

    nf_excel = db.Column(db.String(50), nullable=False)  # Numero da NF-e
    parcela_excel = db.Column(db.Integer, nullable=False)  # Numero sequencial da parcela
    valor_excel = db.Column(db.Float, nullable=False)  # Valor a baixar
    journal_excel = db.Column(db.String(100), nullable=False)  # Nome do journal (ex: GRAFENO)
    data_excel = db.Column(db.Date, nullable=False)  # Data do pagamento
    juros_excel = db.Column(db.Float, nullable=True, default=0)  # Valor de juros recebidos (lancamento separado)

    # Colunas adicionais de baixa (limitadas ao saldo do titulo)
    desconto_concedido_excel = db.Column(db.Float, nullable=True, default=0)  # Desconto concedido ao cliente
    acordo_comercial_excel = db.Column(db.Float, nullable=True, default=0)  # Acordo comercial
    devolucao_excel = db.Column(db.Float, nullable=True, default=0)  # Devolucao

    # =========================================================================
    # DADOS RESOLVIDOS DO ODOO (apos validacao)
    # =========================================================================

    # Titulo encontrado
    titulo_odoo_id = db.Column(db.Integer, nullable=True)  # account.move.line ID
    move_odoo_id = db.Column(db.Integer, nullable=True)  # account.move ID (NF)
    move_odoo_name = db.Column(db.String(100), nullable=True)  # Nome do move (VND/2025/...)
    partner_odoo_id = db.Column(db.Integer, nullable=True)  # ID do cliente

    # Journal resolvido
    journal_odoo_id = db.Column(db.Integer, nullable=True)  # account.journal ID
    journal_odoo_code = db.Column(db.String(20), nullable=True)  # Codigo do journal

    # Valor do titulo no Odoo
    valor_titulo_odoo = db.Column(db.Float, nullable=True)  # Valor original do titulo
    saldo_antes = db.Column(db.Float, nullable=True)  # amount_residual ANTES da baixa

    # =========================================================================
    # CONTROLE DE PROCESSAMENTO
    # =========================================================================

    # Se o usuario quer processar esta linha
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    # Status: PENDENTE, VALIDO, INVALIDO, PROCESSANDO, SUCESSO, ERRO
    status = db.Column(db.String(20), default='PENDENTE', nullable=False, index=True)

    # Mensagem de erro ou validacao
    mensagem = db.Column(db.Text, nullable=True)

    # =========================================================================
    # RESULTADO DA OPERACAO NO ODOO
    # =========================================================================

    # IDs criados no Odoo
    payment_odoo_id = db.Column(db.Integer, nullable=True)  # account.payment ID criado
    payment_odoo_name = db.Column(db.String(100), nullable=True)  # Nome do pagamento (PGRA1/2025/...)
    partial_reconcile_id = db.Column(db.Integer, nullable=True)  # account.partial.reconcile ID

    # IDs do lancamento de JUROS (se houver)
    payment_juros_odoo_id = db.Column(db.Integer, nullable=True)  # account.payment ID do juros
    payment_juros_odoo_name = db.Column(db.String(100), nullable=True)  # Nome do pagamento de juros

    # IDs dos lancamentos adicionais (desconto, acordo, devolucao)
    payment_desconto_odoo_id = db.Column(db.Integer, nullable=True)
    payment_desconto_odoo_name = db.Column(db.String(100), nullable=True)
    payment_acordo_odoo_id = db.Column(db.Integer, nullable=True)
    payment_acordo_odoo_name = db.Column(db.String(100), nullable=True)
    payment_devolucao_odoo_id = db.Column(db.Integer, nullable=True)
    payment_devolucao_odoo_name = db.Column(db.String(100), nullable=True)

    # Saldo apos baixa
    saldo_depois = db.Column(db.Float, nullable=True)  # amount_residual DEPOIS

    # =========================================================================
    # SNAPSHOT ODOO - ANTES E DEPOIS (campos criticos)
    # =========================================================================

    # Campos do titulo ANTES da baixa (JSON)
    snapshot_antes = db.Column(db.Text, nullable=True)

    # Campos do titulo DEPOIS da baixa (JSON)
    snapshot_depois = db.Column(db.Text, nullable=True)

    # Campos alterados (JSON lista de campos que mudaram)
    campos_alterados = db.Column(db.Text, nullable=True)

    # =========================================================================
    # AUDITORIA
    # =========================================================================

    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    validado_em = db.Column(db.DateTime, nullable=True)
    processado_em = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        Index('idx_baixa_item_lote', 'lote_id'),
        Index('idx_baixa_item_status', 'status'),
        Index('idx_baixa_item_nf', 'nf_excel'),
    )

    def __repr__(self):
        return f'<BaixaTituloItem {self.id} - NF {self.nf_excel} P{self.parcela_excel} ({self.status})>'

    def to_dict(self):
        return {
            'id': self.id,
            'lote_id': self.lote_id,
            'linha_excel': self.linha_excel,
            # Dados Excel
            'nf_excel': self.nf_excel,
            'parcela_excel': self.parcela_excel,
            'valor_excel': self.valor_excel,
            'journal_excel': self.journal_excel,
            'data_excel': self.data_excel.isoformat() if self.data_excel else None,
            'juros_excel': self.juros_excel,
            'desconto_concedido_excel': self.desconto_concedido_excel,
            'acordo_comercial_excel': self.acordo_comercial_excel,
            'devolucao_excel': self.devolucao_excel,
            # Dados Odoo resolvidos
            'titulo_odoo_id': self.titulo_odoo_id,
            'move_odoo_id': self.move_odoo_id,
            'move_odoo_name': self.move_odoo_name,
            'partner_odoo_id': self.partner_odoo_id,
            'journal_odoo_id': self.journal_odoo_id,
            'journal_odoo_code': self.journal_odoo_code,
            'valor_titulo_odoo': self.valor_titulo_odoo,
            'saldo_antes': self.saldo_antes,
            # Controle
            'ativo': self.ativo,
            'status': self.status,
            'mensagem': self.mensagem,
            # Resultado
            'payment_odoo_id': self.payment_odoo_id,
            'payment_odoo_name': self.payment_odoo_name,
            'partial_reconcile_id': self.partial_reconcile_id,
            'payment_juros_odoo_id': self.payment_juros_odoo_id,
            'payment_juros_odoo_name': self.payment_juros_odoo_name,
            'payment_desconto_odoo_id': self.payment_desconto_odoo_id,
            'payment_desconto_odoo_name': self.payment_desconto_odoo_name,
            'payment_acordo_odoo_id': self.payment_acordo_odoo_id,
            'payment_acordo_odoo_name': self.payment_acordo_odoo_name,
            'payment_devolucao_odoo_id': self.payment_devolucao_odoo_id,
            'payment_devolucao_odoo_name': self.payment_devolucao_odoo_name,
            'saldo_depois': self.saldo_depois,
            # Snapshots
            'snapshot_antes': json.loads(self.snapshot_antes) if self.snapshot_antes else None,
            'snapshot_depois': json.loads(self.snapshot_depois) if self.snapshot_depois else None,
            'campos_alterados': json.loads(self.campos_alterados) if self.campos_alterados else None,
            # Auditoria
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'validado_em': self.validado_em.isoformat() if self.validado_em else None,
            'processado_em': self.processado_em.isoformat() if self.processado_em else None
        }

    def set_snapshot_antes(self, dados: dict):
        """Salva snapshot dos dados do titulo ANTES da baixa"""
        self.snapshot_antes = json.dumps(dados, default=str)

    def set_snapshot_depois(self, dados: dict):
        """Salva snapshot dos dados do titulo DEPOIS da baixa"""
        self.snapshot_depois = json.dumps(dados, default=str)

    def set_campos_alterados(self, campos: list):
        """Salva lista de campos que foram alterados"""
        self.campos_alterados = json.dumps(campos)

    def get_snapshot_antes(self) -> dict:
        """Retorna snapshot ANTES como dict"""
        return json.loads(self.snapshot_antes) if self.snapshot_antes else {}

    def get_snapshot_depois(self) -> dict:
        """Retorna snapshot DEPOIS como dict"""
        return json.loads(self.snapshot_depois) if self.snapshot_depois else {}

    def get_campos_alterados(self) -> list:
        """Retorna lista de campos alterados"""
        return json.loads(self.campos_alterados) if self.campos_alterados else []


# =============================================================================
# FIM BAIXA DE TITULOS
# =============================================================================


# =============================================================================
# EXTRATO BANCÁRIO - CONCILIAÇÃO VIA EXTRATO
# =============================================================================


class ExtratoLote(db.Model):
    """
    Representa um account.bank.statement do Odoo.
    Cada lote corresponde a um extrato bancário (geralmente por dia).

    NOTA: Um mesmo statement pode ter 2 lotes: um de entrada (recebimentos) e outro de saída (pagamentos).
    A unicidade é por (statement_id + tipo_transacao).
    """
    __tablename__ = 'extrato_lote'

    # Constraint único composto: mesmo statement pode ter entrada E saída
    __table_args__ = (
        db.UniqueConstraint('statement_id', 'tipo_transacao', name='uq_extrato_lote_statement_tipo'),
    )

    id = db.Column(db.Integer, primary_key=True)

    # === REFERÊNCIA AO ODOO (account.bank.statement) ===
    statement_id = db.Column(db.Integer, nullable=True, index=True)  # account.bank.statement ID (sem unique simples)
    statement_name = db.Column(db.String(255), nullable=True)  # Ex: "GRA1 Extrato 2025-12-10"

    # Journal
    journal_code = db.Column(db.String(20), nullable=True)  # GRA1, SIC, BRAD, etc.
    journal_id = db.Column(db.Integer, nullable=True)  # ID do journal no Odoo

    # Data do extrato (do Odoo)
    data_extrato = db.Column(db.Date, nullable=True)  # date do statement

    # Nome do lote (compatibilidade)
    nome = db.Column(db.String(255), nullable=False)  # Pode ser igual a statement_name

    # Campos legados (manter compatibilidade)
    data_inicio = db.Column(db.Date, nullable=True)
    data_fim = db.Column(db.Date, nullable=True)

    # Estatísticas
    total_linhas = db.Column(db.Integer, default=0)
    linhas_com_match = db.Column(db.Integer, default=0)
    linhas_sem_match = db.Column(db.Integer, default=0)
    linhas_conciliadas = db.Column(db.Integer, default=0)
    linhas_erro = db.Column(db.Integer, default=0)
    valor_total = db.Column(db.Float, default=0)

    # Status: IMPORTADO, PROCESSANDO_MATCH, AGUARDANDO_APROVACAO, CONCILIANDO, CONCLUIDO, ERRO
    status = db.Column(db.String(30), default='IMPORTADO', nullable=False, index=True)

    # Tipo de transação: 'entrada' (recebimentos), 'saida' (pagamentos)
    tipo_transacao = db.Column(db.String(20), default='entrada', nullable=False, index=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)
    processado_em = db.Column(db.DateTime, nullable=True)
    processado_por = db.Column(db.String(100), nullable=True)

    # Relacionamento com itens
    itens = relationship('ExtratoItem', backref='lote', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ExtratoLote {self.id} - {self.nome} ({self.status})>'

    def to_dict(self):
        return {
            'id': self.id,
            'statement_id': self.statement_id,
            'statement_name': self.statement_name,
            'nome': self.nome,
            'journal_code': self.journal_code,
            'data_extrato': self.data_extrato.isoformat() if self.data_extrato else None,
            'total_linhas': self.total_linhas,
            'linhas_com_match': self.linhas_com_match,
            'linhas_sem_match': self.linhas_sem_match,
            'linhas_conciliadas': self.linhas_conciliadas,
            'linhas_erro': self.linhas_erro,
            'valor_total': self.valor_total,
            'status': self.status,
            'tipo_transacao': self.tipo_transacao,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por': self.criado_por,
            'processado_em': self.processado_em.isoformat() if self.processado_em else None
        }


class ExtratoItem(db.Model):
    """
    Linha de extrato importada do Odoo para conciliação.

    Fluxo:
    1. Importação -> status = PENDENTE
    2. Matching automático -> status = MATCH_ENCONTRADO ou SEM_MATCH
    3. Aprovação do usuário -> status = APROVADO
    4. Conciliação -> status = CONCILIADO ou ERRO
    """
    __tablename__ = 'extrato_item'

    id = db.Column(db.Integer, primary_key=True)

    # FK para o lote
    lote_id = db.Column(db.Integer, db.ForeignKey('extrato_lote.id'), nullable=False, index=True)

    # =========================================================================
    # DADOS DO ODOO (importados)
    # =========================================================================

    # IDs do Odoo
    statement_line_id = db.Column(db.Integer, nullable=False, index=True)  # account.bank.statement.line ID
    move_id = db.Column(db.Integer, nullable=True)  # account.move ID
    move_name = db.Column(db.String(100), nullable=True)  # Nome do move (GRA1/2025/...)
    credit_line_id = db.Column(db.Integer, nullable=True)  # account.move.line ID da linha de crédito

    # Dados da transação
    data_transacao = db.Column(db.Date, nullable=False)
    valor = db.Column(db.Float, nullable=False)
    payment_ref = db.Column(db.Text, nullable=True)  # Label completo da transação

    # Dados extraídos do payment_ref
    tipo_transacao = db.Column(db.String(50), nullable=True)  # TED, PIX, Boleto
    nome_pagador = db.Column(db.String(255), nullable=True)  # Nome do cliente
    cnpj_pagador = db.Column(db.String(20), nullable=True, index=True)  # CNPJ extraído

    # =========================================================================
    # DADOS DO PARCEIRO ODOO (capturados na importação)
    # =========================================================================
    odoo_partner_id = db.Column(db.Integer, nullable=True)       # res.partner ID
    odoo_partner_name = db.Column(db.String(255), nullable=True)  # nome do parceiro no Odoo
    odoo_partner_cnpj = db.Column(db.String(20), nullable=True)   # l10n_br_cnpj do res.partner

    # =========================================================================
    # FAVORECIDO RESOLVIDO (preenchido pelo pipeline)
    # =========================================================================
    favorecido_cnpj = db.Column(db.String(20), nullable=True)       # CNPJ final resolvido
    favorecido_nome = db.Column(db.String(255), nullable=True)      # Nome final resolvido
    favorecido_metodo = db.Column(db.String(30), nullable=True)     # ODOO_PARTNER|REGEX_CNPJ|REGEX_NOME|CPF_PARCIAL|NOME_FUZZY|CATEGORIA|NAO_RESOLVIDO
    favorecido_confianca = db.Column(db.Integer, nullable=True)     # 0-100
    categoria_pagamento = db.Column(db.String(30), nullable=True)   # PIX_ENVIADO|TED_ENVIADA|BOLETO_COMPE|IMPOSTO|TARIFA|...

    # Journal
    journal_id = db.Column(db.Integer, nullable=True)
    journal_code = db.Column(db.String(20), nullable=True)
    journal_name = db.Column(db.String(100), nullable=True)

    # =========================================================================
    # MATCHING COM TÍTULOS
    # =========================================================================

    # Status do match: PENDENTE, MATCH_ENCONTRADO, MULTIPLOS_MATCHES, SEM_MATCH
    status_match = db.Column(db.String(30), default='PENDENTE', nullable=False, index=True)

    # -------------------------------------------------------------------------
    # TÍTULOS A RECEBER (clientes) - usado quando lote.tipo_transacao = 'entrada'
    # -------------------------------------------------------------------------
    titulo_receber_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber.id'), nullable=True)
    titulo_receber = db.relationship('ContasAReceber', foreign_keys=[titulo_receber_id], lazy='joined')

    # -------------------------------------------------------------------------
    # TÍTULOS A PAGAR (fornecedores) - usado quando lote.tipo_transacao = 'saida'
    # -------------------------------------------------------------------------
    titulo_pagar_id = db.Column(db.Integer, db.ForeignKey('contas_a_pagar.id'), nullable=True)
    titulo_pagar = db.relationship('ContasAPagar', foreign_keys=[titulo_pagar_id], lazy='joined')

    # -------------------------------------------------------------------------
    # CAMPOS LEGADO (deprecados - manter para compatibilidade)
    # TODO: Remover após migração completa
    # -------------------------------------------------------------------------
    titulo_id = db.Column(db.Integer, nullable=True)  # DEPRECADO: usar titulo_receber_id ou titulo_pagar_id

    # -------------------------------------------------------------------------
    # CAMPOS DE CACHE (comuns para ambos os tipos)
    # -------------------------------------------------------------------------
    titulo_nf = db.Column(db.String(50), nullable=True)  # Número da NF-e
    titulo_parcela = db.Column(db.Integer, nullable=True)  # Número da parcela
    titulo_valor = db.Column(db.Float, nullable=True)  # Valor do título
    titulo_vencimento = db.Column(db.Date, nullable=True)  # Vencimento do título
    titulo_cliente = db.Column(db.String(255), nullable=True)  # Nome do cliente/fornecedor
    titulo_cnpj = db.Column(db.String(20), nullable=True)  # CNPJ do cliente/fornecedor

    # Múltiplos matches (JSON com lista de títulos candidatos)
    matches_candidatos = db.Column(db.Text, nullable=True)

    # Score de confiança do match (0-100)
    match_score = db.Column(db.Integer, nullable=True)
    match_criterio = db.Column(db.String(100), nullable=True)  # Ex: "CNPJ+VALOR_EXATO"

    # -------------------------------------------------------------------------
    # PROPRIEDADES HELPER
    # -------------------------------------------------------------------------
    @property
    def titulo(self):
        """Retorna o título correto baseado no tipo de transação do lote."""
        if self.titulo_pagar_id:
            return self.titulo_pagar
        return self.titulo_receber

    @property
    def titulo_id_efetivo(self):
        """Retorna o ID do título efetivo (receber ou pagar)."""
        return self.titulo_pagar_id or self.titulo_receber_id

    # =========================================================================
    # CONTROLE DE PROCESSAMENTO
    # =========================================================================

    # Se o usuário aprovou para conciliar
    aprovado = db.Column(db.Boolean, default=False, nullable=False)
    aprovado_em = db.Column(db.DateTime, nullable=True)
    aprovado_por = db.Column(db.String(100), nullable=True)

    # Status geral: PENDENTE, MATCH_ENCONTRADO, SEM_MATCH, APROVADO, CONCILIANDO, CONCILIADO, ERRO
    status = db.Column(db.String(30), default='PENDENTE', nullable=False, index=True)

    # Mensagem de erro ou observação
    mensagem = db.Column(db.Text, nullable=True)

    # =========================================================================
    # RESULTADO DA CONCILIAÇÃO
    # =========================================================================

    # IDs criados no Odoo
    partial_reconcile_id = db.Column(db.Integer, nullable=True)
    full_reconcile_id = db.Column(db.Integer, nullable=True)
    payment_id = db.Column(db.Integer, nullable=True)  # account.payment criado no Odoo

    # Saldo do título após conciliação
    titulo_saldo_antes = db.Column(db.Float, nullable=True)
    titulo_saldo_depois = db.Column(db.Float, nullable=True)

    # Snapshots (JSON)
    snapshot_antes = db.Column(db.Text, nullable=True)
    snapshot_depois = db.Column(db.Text, nullable=True)

    # =========================================================================
    # AUDITORIA
    # =========================================================================

    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    processado_em = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        Index('idx_extrato_item_lote', 'lote_id'),
        Index('idx_extrato_item_status', 'status'),
        Index('idx_extrato_item_cnpj', 'cnpj_pagador'),
        Index('idx_extrato_item_statement_line', 'statement_line_id'),
        Index('idx_extrato_item_favorecido_cnpj', 'favorecido_cnpj'),
        Index('idx_extrato_item_categoria_pag', 'categoria_pagamento'),
        Index('idx_extrato_item_odoo_partner', 'odoo_partner_id'),
    )

    def __repr__(self):
        return f'<ExtratoItem {self.id} - {self.data_transacao} R$ {self.valor} ({self.status})>'

    def to_dict(self):
        return {
            'id': self.id,
            'lote_id': self.lote_id,
            # Dados Odoo
            'statement_line_id': self.statement_line_id,
            'move_id': self.move_id,
            'move_name': self.move_name,
            'credit_line_id': self.credit_line_id,
            'data_transacao': self.data_transacao.isoformat() if self.data_transacao else None,
            'valor': self.valor,
            'payment_ref': self.payment_ref,
            # Dados extraídos
            'tipo_transacao': self.tipo_transacao,
            'nome_pagador': self.nome_pagador,
            'cnpj_pagador': self.cnpj_pagador,
            'journal_code': self.journal_code,
            # Parceiro Odoo
            'odoo_partner_id': self.odoo_partner_id,
            'odoo_partner_name': self.odoo_partner_name,
            'odoo_partner_cnpj': self.odoo_partner_cnpj,
            # Favorecido resolvido
            'favorecido_cnpj': self.favorecido_cnpj,
            'favorecido_nome': self.favorecido_nome,
            'favorecido_metodo': self.favorecido_metodo,
            'favorecido_confianca': self.favorecido_confianca,
            'categoria_pagamento': self.categoria_pagamento,
            # Matching
            'status_match': self.status_match,
            'titulo_receber_id': self.titulo_receber_id,
            'titulo_pagar_id': self.titulo_pagar_id,
            'titulo_id': self.titulo_id,  # DEPRECADO
            'titulo_id_efetivo': self.titulo_id_efetivo,  # Helper: retorna receber ou pagar
            'titulo_nf': self.titulo_nf,
            'titulo_parcela': self.titulo_parcela,
            'titulo_valor': self.titulo_valor,
            'titulo_vencimento': self.titulo_vencimento.isoformat() if self.titulo_vencimento else None,
            'titulo_cliente': self.titulo_cliente,
            'titulo_cnpj': self.titulo_cnpj,
            'match_score': self.match_score,
            'match_criterio': self.match_criterio,
            # Controle
            'aprovado': self.aprovado,
            'status': self.status,
            'mensagem': self.mensagem,
            # Resultado
            'partial_reconcile_id': self.partial_reconcile_id,
            'payment_id': self.payment_id,
            'titulo_saldo_antes': self.titulo_saldo_antes,
            'titulo_saldo_depois': self.titulo_saldo_depois,
            # Auditoria
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'processado_em': self.processado_em.isoformat() if self.processado_em else None
        }

    def set_matches_candidatos(self, matches: list):
        """Salva lista de matches candidatos como JSON"""
        self.matches_candidatos = json.dumps(matches, default=str)

    def get_matches_candidatos(self) -> list:
        """Retorna lista de matches candidatos"""
        return json.loads(self.matches_candidatos) if self.matches_candidatos else []

    def set_snapshot_antes(self, dados: dict):
        """Salva snapshot dos dados ANTES da conciliação"""
        self.snapshot_antes = json.dumps(dados, default=str)

    def set_snapshot_depois(self, dados: dict):
        """Salva snapshot dos dados DEPOIS da conciliação"""
        self.snapshot_depois = json.dumps(dados, default=str)

    # =========================================================================
    # RELACIONAMENTO M:N COM TÍTULOS (múltiplos títulos por linha de extrato)
    # =========================================================================
    titulos_vinculados = db.relationship(
        'ExtratoItemTitulo',
        back_populates='extrato_item',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    @property
    def valor_alocado_total(self) -> float:
        """Soma dos valores alocados em todos os títulos vinculados."""
        total = sum(float(t.valor_alocado or 0) for t in self.titulos_vinculados)
        return float(total)

    @property
    def valor_pendente_alocacao(self) -> float:
        """Valor do extrato ainda não alocado a títulos."""
        return float(self.valor or 0) - self.valor_alocado_total

    @property
    def titulo_parcela_str(self) -> Optional[str]:
        """Titulo parcela como string, para buscar em contas_a_receber/pagar."""
        from app.financeiro.parcela_utils import parcela_to_str
        return parcela_to_str(self.titulo_parcela)

    @property
    def tem_multiplos_titulos(self) -> bool:
        """
        Retorna True se há títulos vinculados via M:N.

        IMPORTANTE: Retorna True mesmo para 1 único título vinculado via M:N,
        pois nesse caso o FK legacy (titulo_receber_id/titulo_pagar_id) foi limpo
        e precisamos usar o fluxo de múltiplos no template.
        """
        return self.titulos_vinculados.count() > 0

    @property
    def fonte_conciliacao(self) -> Optional[dict]:
        """Deriva a fonte de conciliação a partir do campo mensagem.

        Retorna dict com {codigo, label, icone, classe_css} ou None se não conciliado.
        """
        if self.status != 'CONCILIADO' or not self.mensagem:
            return None
        msg = self.mensagem.lower()
        if 'cnab' in msg or '[baixa_auto]' in msg:
            return {'codigo': 'cnab', 'label': 'CNAB', 'icone': 'fa-file-import', 'classe_css': 'badge-fonte-cnab'}
        if 'write_date' in msg:
            return {'codigo': 'odoo', 'label': 'Odoo', 'icone': 'fa-cloud', 'classe_css': 'badge-fonte-odoo'}
        if 'revalidação completa' in msg or 'revalidacao completa' in msg:
            return {'codigo': 'revalidacao', 'label': 'Sync', 'icone': 'fa-sync', 'classe_css': 'badge-fonte-sync'}
        if 'comprovante' in msg:
            return {'codigo': 'comprovante', 'label': 'Comprovante', 'icone': 'fa-file-pdf', 'classe_css': 'badge-fonte-comprovante'}
        if 'sincronização automática' in msg or 'sincronizado do odoo' in msg:
            return {'codigo': 'sync', 'label': 'Sync', 'icone': 'fa-robot', 'classe_css': 'badge-fonte-sync'}
        if 'extrato não reconciliado' in msg or 'extrato nao reconciliado' in msg:
            return {'codigo': 'local', 'label': 'Local', 'icone': 'fa-exclamation-triangle', 'classe_css': 'badge-fonte-local'}
        if 'retroativamente' in msg:
            return {'codigo': 'retroativo', 'label': 'Retro', 'icone': 'fa-history', 'classe_css': 'badge-fonte-sync'}
        # Default: conciliação manual via UI
        return {'codigo': 'manual', 'label': 'Manual', 'icone': 'fa-user', 'classe_css': 'badge-fonte-manual'}


class ExtratoItemTitulo(db.Model):
    """
    Associação M:N entre ExtratoItem e Títulos (Receber ou Pagar).

    Permite vincular múltiplos títulos a uma única linha de extrato,
    com controle de valor alocado para cada título.

    Cenários de uso:
    1. Pagamento agrupado: Cliente paga 3 NFs de uma vez
    2. Alocação parcial: Extrato R$ 10.000, título R$ 12.000 (paga 83,3%)
    3. Rastreabilidade: Saber exatamente quanto de cada título foi pago

    Exemplo:
    ┌─────────────────────────────────────────────────────────────┐
    │  EXTRATO: PIX R$ 15.000,00 de CLIENTE XPTO                  │
    └─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
    NF 1001 P1            NF 1002 P1           NF 1003 P1
    R$ 5.000,00           R$ 7.000,00          R$ 3.000,00
    (alocado: 5.000)      (alocado: 7.000)     (alocado: 3.000)
    ─────────────────────────────────────────────────────────────
                      TOTAL ALOCADO = R$ 15.000,00
    """
    __tablename__ = 'extrato_item_titulo'

    id = db.Column(db.Integer, primary_key=True)

    # =========================================================================
    # RELACIONAMENTOS
    # =========================================================================

    # FK para ExtratoItem (obrigatório)
    extrato_item_id = db.Column(
        db.Integer,
        db.ForeignKey('extrato_item.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    extrato_item = db.relationship(
        'ExtratoItem',
        back_populates='titulos_vinculados'
    )

    # FK para Título A RECEBER (clientes) - mutuamente exclusivo com titulo_pagar_id
    titulo_receber_id = db.Column(
        db.Integer,
        db.ForeignKey('contas_a_receber.id'),
        nullable=True,
        index=True
    )
    titulo_receber = db.relationship('ContasAReceber', lazy='joined')

    # FK para Título A PAGAR (fornecedores) - mutuamente exclusivo com titulo_receber_id
    titulo_pagar_id = db.Column(
        db.Integer,
        db.ForeignKey('contas_a_pagar.id'),
        nullable=True,
        index=True
    )
    titulo_pagar = db.relationship('ContasAPagar', lazy='joined')

    # =========================================================================
    # DADOS DA ALOCAÇÃO
    # =========================================================================

    # Valor alocado deste título ao pagamento (pode ser parcial)
    valor_alocado = db.Column(db.Numeric(15, 2), nullable=False)

    # Valor total do título no momento da vinculação (para referência)
    valor_titulo_original = db.Column(db.Numeric(15, 2), nullable=True)

    # Percentual do título que está sendo pago (valor_alocado / valor_titulo)
    percentual_alocado = db.Column(db.Numeric(5, 2), nullable=True)

    # =========================================================================
    # CAMPOS DE CACHE (desnormalizados para performance)
    # =========================================================================

    titulo_nf = db.Column(db.String(50), nullable=True)
    titulo_parcela = db.Column(db.Integer, nullable=True)
    titulo_vencimento = db.Column(db.Date, nullable=True)
    titulo_cliente = db.Column(db.String(255), nullable=True)
    titulo_cnpj = db.Column(db.String(20), nullable=True)

    # Score de matching
    match_score = db.Column(db.Integer, nullable=True)
    match_criterio = db.Column(db.String(100), nullable=True)

    # =========================================================================
    # CONTROLE DE PROCESSAMENTO
    # =========================================================================

    # Status individual: PENDENTE, APROVADO, CONCILIADO, ERRO
    status = db.Column(db.String(30), default='PENDENTE', nullable=False, index=True)

    # Aprovação individual
    aprovado = db.Column(db.Boolean, default=False, nullable=False)
    aprovado_em = db.Column(db.DateTime, nullable=True)
    aprovado_por = db.Column(db.String(100), nullable=True)

    # =========================================================================
    # RESULTADO DA CONCILIAÇÃO
    # =========================================================================

    # IDs criados no Odoo (cada título tem sua própria reconciliação)
    partial_reconcile_id = db.Column(db.Integer, nullable=True)
    full_reconcile_id = db.Column(db.Integer, nullable=True)
    payment_id = db.Column(db.Integer, nullable=True)  # account.payment criado

    # Saldo do título antes/depois da conciliação
    titulo_saldo_antes = db.Column(db.Numeric(15, 2), nullable=True)
    titulo_saldo_depois = db.Column(db.Numeric(15, 2), nullable=True)

    # Mensagem de erro ou observação
    mensagem = db.Column(db.Text, nullable=True)

    # =========================================================================
    # AUDITORIA
    # =========================================================================

    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    processado_em = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        # Índice composto para busca
        Index('idx_extrato_titulo_item', 'extrato_item_id'),
        Index('idx_extrato_titulo_receber', 'titulo_receber_id'),
        Index('idx_extrato_titulo_pagar', 'titulo_pagar_id'),
        Index('idx_extrato_titulo_status', 'status'),
        # Constraint: título receber OU pagar, não ambos
        db.CheckConstraint(
            '(titulo_receber_id IS NOT NULL AND titulo_pagar_id IS NULL) OR '
            '(titulo_receber_id IS NULL AND titulo_pagar_id IS NOT NULL)',
            name='chk_titulo_receber_ou_pagar'
        ),
    )

    def __repr__(self):
        tipo = 'Receber' if self.titulo_receber_id else 'Pagar'
        titulo_id = self.titulo_receber_id or self.titulo_pagar_id
        return (
            f'<ExtratoItemTitulo {self.id} - '
            f'Item:{self.extrato_item_id} -> {tipo}:{titulo_id} '
            f'R$ {self.valor_alocado} ({self.status})>'
        )

    @property
    def titulo(self):
        """Retorna o título correto (receber ou pagar)."""
        return self.titulo_receber or self.titulo_pagar

    @property
    def titulo_id_efetivo(self):
        """Retorna o ID do título efetivo."""
        return self.titulo_receber_id or self.titulo_pagar_id

    @property
    def tipo_titulo(self) -> str:
        """Retorna 'receber' ou 'pagar'."""
        return 'receber' if self.titulo_receber_id else 'pagar'

    @property
    def titulo_parcela_str(self) -> Optional[str]:
        """Titulo parcela como string, para buscar em contas_a_receber/pagar."""
        from app.financeiro.parcela_utils import parcela_to_str
        return parcela_to_str(self.titulo_parcela)

    def to_dict(self):
        return {
            'id': self.id,
            'extrato_item_id': self.extrato_item_id,
            'titulo_receber_id': self.titulo_receber_id,
            'titulo_pagar_id': self.titulo_pagar_id,
            'titulo_id_efetivo': self.titulo_id_efetivo,
            'tipo_titulo': self.tipo_titulo,
            'valor_alocado': float(self.valor_alocado) if self.valor_alocado else None,
            'valor_titulo_original': float(self.valor_titulo_original) if self.valor_titulo_original else None,
            'percentual_alocado': float(self.percentual_alocado) if self.percentual_alocado else None,
            'titulo_nf': self.titulo_nf,
            'titulo_parcela': self.titulo_parcela,
            'titulo_vencimento': self.titulo_vencimento.isoformat() if self.titulo_vencimento else None,
            'titulo_cliente': self.titulo_cliente,
            'titulo_cnpj': self.titulo_cnpj,
            'match_score': self.match_score,
            'match_criterio': self.match_criterio,
            'status': self.status,
            'aprovado': self.aprovado,
            'partial_reconcile_id': self.partial_reconcile_id,
            'full_reconcile_id': self.full_reconcile_id,
            'payment_id': self.payment_id,
            'titulo_saldo_antes': float(self.titulo_saldo_antes) if self.titulo_saldo_antes else None,
            'titulo_saldo_depois': float(self.titulo_saldo_depois) if self.titulo_saldo_depois else None,
            'mensagem': self.mensagem,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'processado_em': self.processado_em.isoformat() if self.processado_em else None,
        }

    def preencher_cache(self, titulo=None):
        """
        Preenche campos de cache a partir do título relacionado.

        Args:
            titulo: Título opcional a usar. Se não fornecido, usa self.titulo.
                   Passar o título diretamente é útil quando a FK foi definida
                   mas a relação ainda não foi carregada (lazy loading).
        """
        from app.financeiro.parcela_utils import parcela_to_int
        if titulo is None:
            titulo = self.titulo
        if titulo:
            self.titulo_nf = titulo.titulo_nf
            self.titulo_parcela = parcela_to_int(titulo.parcela)
            self.titulo_vencimento = titulo.vencimento
            self.titulo_cliente = getattr(titulo, 'raz_social_red', None) or titulo.raz_social
            self.titulo_cnpj = titulo.cnpj

            # Obter valor do título (ContasAReceber usa valor_titulo, ContasAPagar usa valor_original)
            valor_titulo = getattr(titulo, 'valor_titulo', None) or getattr(titulo, 'valor_original', None)
            self.valor_titulo_original = valor_titulo

            # Calcular percentual alocado
            if self.valor_alocado and valor_titulo:
                self.percentual_alocado = (
                    float(self.valor_alocado) / float(valor_titulo) * 100
                )


# =============================================================================
# FIM EXTRATO BANCÁRIO
# =============================================================================


class PendenciaFinanceiraNF(db.Model):
    __tablename__ = 'pendencias_financeiras_nf'

    id = db.Column(db.Integer, primary_key=True)
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    observacao = db.Column(db.Text)
    resposta_logistica = db.Column(db.Text, nullable=True)
    respondida_em = db.Column(db.DateTime, nullable=True)
    respondida_por = db.Column(db.String(100), nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100))
    
    # Campos para soft delete APENAS DAS RESPOSTAS (pendência nunca é apagada)
    resposta_excluida_em = db.Column(db.DateTime, nullable=True)
    resposta_excluida_por = db.Column(db.String(100), nullable=True)

    # Adicione este relacionamento:
    entrega_id = db.Column(db.Integer, db.ForeignKey('entregas_monitoradas.id'), nullable=True)
    entrega = db.relationship('EntregaMonitorada', backref='pendencias_financeiras')
    
    @property
    def resposta_ativa(self):
        """Retorna True se a resposta não foi excluída (pendência sempre fica ativa)"""
        return self.resposta_excluida_em is None
    
    @property
    def tem_resposta_valida(self):
        """Retorna True se há resposta e ela não foi excluída"""
        return self.respondida_em is not None and self.resposta_excluida_em is None


# =============================================================================
# BAIXA DE PAGAMENTOS (CONTAS A PAGAR) VIA EXTRATO
# =============================================================================


class BaixaPagamentoLote(db.Model):
    """
    Lote de baixa de pagamentos (contas a pagar).
    Similar a BaixaTituloLote, mas para pagamentos a fornecedores.

    Fluxo:
    1. Importar linhas do extrato (amount < 0 = saídas)
    2. Fazer matching com títulos a pagar (liability_payable)
    3. Aprovar matches
    4. Executar baixa (criar payment outbound + reconciliar)
    """
    __tablename__ = 'baixa_pagamento_lote'

    id = db.Column(db.Integer, primary_key=True)

    # === REFERÊNCIA AO EXTRATO ===
    # Pode ser vinculado a um extrato específico ou importado manualmente
    extrato_lote_id = db.Column(db.Integer, db.ForeignKey('extrato_lote.id'), nullable=True, index=True)

    # Identificação do lote
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)

    # Journal/Conta bancária
    journal_id = db.Column(db.Integer, nullable=True)
    journal_code = db.Column(db.String(20), nullable=True)
    journal_name = db.Column(db.String(100), nullable=True)

    # Período
    data_inicio = db.Column(db.Date, nullable=True)
    data_fim = db.Column(db.Date, nullable=True)

    # Estatísticas
    total_linhas = db.Column(db.Integer, default=0)
    linhas_com_match = db.Column(db.Integer, default=0)
    linhas_sem_match = db.Column(db.Integer, default=0)
    linhas_aprovadas = db.Column(db.Integer, default=0)
    linhas_processadas = db.Column(db.Integer, default=0)
    linhas_sucesso = db.Column(db.Integer, default=0)
    linhas_erro = db.Column(db.Integer, default=0)
    valor_total = db.Column(db.Float, default=0)

    # Status: IMPORTADO, MATCHING, AGUARDANDO_APROVACAO, PROCESSANDO, CONCLUIDO, ERRO
    status = db.Column(db.String(30), default='IMPORTADO', nullable=False, index=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)
    processado_em = db.Column(db.DateTime, nullable=True)
    processado_por = db.Column(db.String(100), nullable=True)

    # Relacionamentos
    itens = relationship('BaixaPagamentoItem', backref='lote', lazy='dynamic', cascade='all, delete-orphan')
    extrato_lote = relationship('ExtratoLote', foreign_keys=[extrato_lote_id])

    def __repr__(self):
        return f'<BaixaPagamentoLote {self.id} - {self.nome} ({self.status})>'

    def to_dict(self):
        return {
            'id': self.id,
            'extrato_lote_id': self.extrato_lote_id,
            'nome': self.nome,
            'descricao': self.descricao,
            'journal_id': self.journal_id,
            'journal_code': self.journal_code,
            'journal_name': self.journal_name,
            'data_inicio': self.data_inicio.isoformat() if self.data_inicio else None,
            'data_fim': self.data_fim.isoformat() if self.data_fim else None,
            'total_linhas': self.total_linhas,
            'linhas_com_match': self.linhas_com_match,
            'linhas_sem_match': self.linhas_sem_match,
            'linhas_aprovadas': self.linhas_aprovadas,
            'linhas_processadas': self.linhas_processadas,
            'linhas_sucesso': self.linhas_sucesso,
            'linhas_erro': self.linhas_erro,
            'valor_total': self.valor_total,
            'status': self.status,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por': self.criado_por,
            'processado_em': self.processado_em.isoformat() if self.processado_em else None,
            'processado_por': self.processado_por
        }


class BaixaPagamentoItem(db.Model):
    """
    Item individual de baixa de pagamento.
    Representa uma linha de saída do extrato vinculada a um título a pagar.

    Fluxo:
    1. Importado do extrato -> status = PENDENTE
    2. Matching automático -> status_match = MATCH_ENCONTRADO/SEM_MATCH/MULTIPLOS
    3. Aprovação manual -> aprovado = True
    4. Processamento -> status = PROCESSANDO -> SUCESSO ou ERRO
    """
    __tablename__ = 'baixa_pagamento_item'

    id = db.Column(db.Integer, primary_key=True)

    # FK para o lote
    lote_id = db.Column(db.Integer, db.ForeignKey('baixa_pagamento_lote.id'), nullable=False, index=True)

    # =========================================================================
    # DADOS DO EXTRATO (origem)
    # =========================================================================

    # Referência ao Odoo
    statement_line_id = db.Column(db.Integer, nullable=True, index=True)  # account.bank.statement.line ID
    move_id_extrato = db.Column(db.Integer, nullable=True)  # account.move ID do extrato

    # Dados da transação
    data_transacao = db.Column(db.Date, nullable=False)
    valor = db.Column(db.Float, nullable=False)  # Valor absoluto (positivo)
    payment_ref = db.Column(db.Text, nullable=True)  # Label completo da transação

    # Dados extraídos do payment_ref
    tipo_transacao = db.Column(db.String(50), nullable=True)  # PIX, TED, BOLETO, etc.
    nome_beneficiario = db.Column(db.String(255), nullable=True)  # Nome do fornecedor extraído
    cnpj_beneficiario = db.Column(db.String(20), nullable=True, index=True)  # CNPJ extraído

    # Linha de débito do extrato (para reconciliar)
    debit_line_id_extrato = db.Column(db.Integer, nullable=True)  # account.move.line ID (débito na TRANSITÓRIA)

    # =========================================================================
    # MATCHING - TÍTULO VINCULADO
    # =========================================================================

    # Status do matching: PENDENTE, MATCH_ENCONTRADO, MULTIPLOS_MATCHES, SEM_MATCH
    status_match = db.Column(db.String(30), default='PENDENTE', nullable=False, index=True)

    # Título a pagar vinculado
    titulo_id = db.Column(db.Integer, nullable=True, index=True)  # account.move.line ID (liability_payable)
    titulo_move_id = db.Column(db.Integer, nullable=True)  # account.move ID (NF de entrada)
    titulo_move_name = db.Column(db.String(100), nullable=True)  # Nome do move (COM2/2024/...)
    titulo_nf = db.Column(db.String(50), nullable=True)  # Número da NF (cache)
    titulo_parcela = db.Column(db.Integer, nullable=True)  # Parcela (cache)
    titulo_valor = db.Column(db.Float, nullable=True)  # Valor do título (cache)
    titulo_vencimento = db.Column(db.Date, nullable=True)  # Vencimento (cache)

    # Fornecedor
    partner_id = db.Column(db.Integer, nullable=True)  # res.partner ID
    partner_name = db.Column(db.String(255), nullable=True)  # Nome do fornecedor (cache)

    # Empresa
    company_id = db.Column(db.Integer, nullable=True)  # company_id do título

    # Score e critério do match
    match_score = db.Column(db.Integer, nullable=True)  # 0-100
    match_criterio = db.Column(db.String(100), nullable=True)  # Ex: "CNPJ_EXATO+VALOR_EXATO"

    # Múltiplos candidatos (JSON)
    matches_candidatos = db.Column(db.Text, nullable=True)

    # =========================================================================
    # APROVAÇÃO
    # =========================================================================

    aprovado = db.Column(db.Boolean, default=False, nullable=False)
    aprovado_em = db.Column(db.DateTime, nullable=True)
    aprovado_por = db.Column(db.String(100), nullable=True)

    # =========================================================================
    # CONTROLE DE PROCESSAMENTO
    # =========================================================================

    # Status geral: PENDENTE, APROVADO, PROCESSANDO, SUCESSO, ERRO
    status = db.Column(db.String(20), default='PENDENTE', nullable=False, index=True)

    # Mensagem de erro
    mensagem = db.Column(db.Text, nullable=True)

    # =========================================================================
    # RESULTADO DA OPERAÇÃO NO ODOO
    # =========================================================================

    # Payment criado
    payment_id = db.Column(db.Integer, nullable=True)  # account.payment ID criado
    payment_name = db.Column(db.String(100), nullable=True)  # Nome do pagamento (PGRA1/2025/...)

    # Linhas do payment
    debit_line_id_payment = db.Column(db.Integer, nullable=True)  # Linha de DÉBITO (liability_payable)
    credit_line_id_payment = db.Column(db.Integer, nullable=True)  # Linha de CRÉDITO (PENDENTES)

    # Reconciliações
    partial_reconcile_titulo_id = db.Column(db.Integer, nullable=True)  # Reconcile payment <-> título
    full_reconcile_titulo_id = db.Column(db.Integer, nullable=True)
    partial_reconcile_extrato_id = db.Column(db.Integer, nullable=True)  # Reconcile payment <-> extrato
    full_reconcile_extrato_id = db.Column(db.Integer, nullable=True)

    # Saldos
    saldo_antes = db.Column(db.Float, nullable=True)  # amount_residual ANTES
    saldo_depois = db.Column(db.Float, nullable=True)  # amount_residual DEPOIS

    # =========================================================================
    # SNAPSHOTS (auditoria completa)
    # =========================================================================

    snapshot_antes = db.Column(db.Text, nullable=True)  # JSON com estado ANTES
    snapshot_depois = db.Column(db.Text, nullable=True)  # JSON com estado DEPOIS

    # =========================================================================
    # AUDITORIA
    # =========================================================================

    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    processado_em = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        Index('idx_baixa_pag_item_lote', 'lote_id'),
        Index('idx_baixa_pag_item_status', 'status'),
        Index('idx_baixa_pag_item_status_match', 'status_match'),
        Index('idx_baixa_pag_item_cnpj', 'cnpj_beneficiario'),
        Index('idx_baixa_pag_item_titulo', 'titulo_id'),
    )

    def __repr__(self):
        return f'<BaixaPagamentoItem {self.id} - {self.nome_beneficiario} R${self.valor:.2f} ({self.status})>'

    @property
    def titulo_parcela_str(self) -> Optional[str]:
        """Titulo parcela como string, para buscar em contas_a_pagar."""
        from app.financeiro.parcela_utils import parcela_to_str
        return parcela_to_str(self.titulo_parcela)

    def to_dict(self):
        return {
            'id': self.id,
            'lote_id': self.lote_id,
            # Extrato
            'statement_line_id': self.statement_line_id,
            'move_id_extrato': self.move_id_extrato,
            'data_transacao': self.data_transacao.isoformat() if self.data_transacao else None,
            'valor': self.valor,
            'payment_ref': self.payment_ref,
            'tipo_transacao': self.tipo_transacao,
            'nome_beneficiario': self.nome_beneficiario,
            'cnpj_beneficiario': self.cnpj_beneficiario,
            # Matching
            'status_match': self.status_match,
            'titulo_id': self.titulo_id,
            'titulo_move_id': self.titulo_move_id,
            'titulo_move_name': self.titulo_move_name,
            'titulo_nf': self.titulo_nf,
            'titulo_parcela': self.titulo_parcela,
            'titulo_valor': self.titulo_valor,
            'titulo_vencimento': self.titulo_vencimento.isoformat() if self.titulo_vencimento else None,
            'partner_id': self.partner_id,
            'partner_name': self.partner_name,
            'company_id': self.company_id,
            'match_score': self.match_score,
            'match_criterio': self.match_criterio,
            'matches_candidatos': self.get_matches_candidatos(),
            # Aprovação
            'aprovado': self.aprovado,
            'aprovado_em': self.aprovado_em.isoformat() if self.aprovado_em else None,
            'aprovado_por': self.aprovado_por,
            # Controle
            'status': self.status,
            'mensagem': self.mensagem,
            # Resultado
            'payment_id': self.payment_id,
            'payment_name': self.payment_name,
            'saldo_antes': self.saldo_antes,
            'saldo_depois': self.saldo_depois,
            # Snapshots
            'snapshot_antes': self.get_snapshot_antes(),
            'snapshot_depois': self.get_snapshot_depois(),
            # Auditoria
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'processado_em': self.processado_em.isoformat() if self.processado_em else None
        }

    def set_matches_candidatos(self, matches: list):
        """Salva lista de matches candidatos como JSON"""
        self.matches_candidatos = json.dumps(matches, default=str)

    def get_matches_candidatos(self) -> list:
        """Retorna lista de matches candidatos"""
        return json.loads(self.matches_candidatos) if self.matches_candidatos else []

    def set_snapshot_antes(self, dados: dict):
        """Salva snapshot dos dados ANTES da baixa"""
        self.snapshot_antes = json.dumps(dados, default=str)

    def set_snapshot_depois(self, dados: dict):
        """Salva snapshot dos dados DEPOIS da baixa"""
        self.snapshot_depois = json.dumps(dados, default=str)

    def get_snapshot_antes(self) -> dict:
        """Retorna snapshot ANTES como dict"""
        return json.loads(self.snapshot_antes) if self.snapshot_antes else {}

    def get_snapshot_depois(self) -> dict:
        """Retorna snapshot DEPOIS como dict"""
        return json.loads(self.snapshot_depois) if self.snapshot_depois else {}


# =============================================================================
# FIM BAIXA DE PAGAMENTOS
# =============================================================================


# =============================================================================
# CONTAS A PAGAR - MODELOS
# =============================================================================


class ContasAPagar(db.Model):
    """
    Contas a Pagar - Dados importados do Odoo com enriquecimento local.

    Chave única: empresa + titulo_nf + parcela

    Fontes de dados:
    - ODOO: empresa, titulo_nf, parcela, cnpj, razao_social, emissao, vencimento,
            valor_original, valor_residual, parcela_paga
    - SISTEMA: observacao, alerta, status_sistema
    - CALCULADO: dias_vencidos, status_vencimento

    Diferenças em relação a Contas a Receber:
    - account_type = 'liability_payable' (vs 'asset_receivable')
    - Valor no campo 'credit' (vs 'debit')
    - amount_residual é NEGATIVO quando em aberto
    - Fornecedores (vs Clientes)
    """
    __tablename__ = 'contas_a_pagar'

    id = db.Column(db.Integer, primary_key=True)

    # =========================================================================
    # CAMPOS DO ODOO (importados automaticamente)
    # =========================================================================

    # Identificação única
    empresa = db.Column(db.Integer, nullable=False, index=True)  # 1=FB, 2=SC, 3=CD
    titulo_nf = db.Column(db.String(50), nullable=False, index=True)  # NF-e de entrada (x_studio_nf_e)
    parcela = db.Column(db.String(10), nullable=False, index=True)  # Número da parcela

    # IDs do Odoo (para referência)
    odoo_line_id = db.Column(db.Integer, nullable=True, unique=True, index=True)  # account.move.line ID
    odoo_move_id = db.Column(db.Integer, nullable=True, index=True)  # account.move ID
    odoo_move_name = db.Column(db.String(255), nullable=True)  # Nome do move (ENTSI/2025/...)

    # Fornecedor
    partner_id = db.Column(db.Integer, nullable=True, index=True)  # res.partner ID
    cnpj = db.Column(db.String(20), nullable=True, index=True)  # CNPJ do fornecedor
    raz_social = db.Column(db.String(255), nullable=True)  # Razão Social completa
    raz_social_red = db.Column(db.String(100), nullable=True)  # Nome reduzido/fantasia

    # Datas do Odoo
    emissao = db.Column(db.Date, nullable=True)  # Data de emissão (date)
    vencimento = db.Column(db.Date, nullable=True, index=True)  # Data de vencimento (date_maturity)

    # Valores do Odoo
    valor_original = db.Column(db.Float, nullable=True)  # Valor original (credit)
    valor_residual = db.Column(db.Float, nullable=True)  # Saldo em aberto (abs(amount_residual))

    # Status do Odoo
    parcela_paga = db.Column(db.Boolean, default=False)  # l10n_br_paga
    reconciliado = db.Column(db.Boolean, default=False)  # reconciled

    # =========================================================================
    # CAMPOS DO SISTEMA (preenchidos manualmente)
    # =========================================================================

    # Observações e alertas
    observacao = db.Column(db.Text, nullable=True)
    alerta = db.Column(db.Boolean, default=False, nullable=False)

    # Status interno do sistema
    # PENDENTE: Aguardando pagamento
    # PROGRAMADO: Pagamento programado
    # PAGO: Pago (sincronizado do Odoo)
    # CONTESTADO: Em contestação
    status_sistema = db.Column(db.String(30), default='PENDENTE', nullable=False, index=True)

    # Data programada para pagamento (definido pelo usuário)
    data_programada = db.Column(db.Date, nullable=True)

    # =========================================================================
    # AUDITORIA E CONTROLE
    # =========================================================================

    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # Controle de sincronização
    odoo_write_date = db.Column(db.DateTime, nullable=True)  # write_date do Odoo para sync incremental
    ultima_sincronizacao = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint('empresa', 'titulo_nf', 'parcela', name='uq_conta_pagar_empresa_nf_parcela'),
        Index('idx_conta_pagar_vencimento', 'vencimento'),
        Index('idx_conta_pagar_cnpj', 'cnpj'),
        Index('idx_conta_pagar_nf', 'titulo_nf'),
        Index('idx_conta_pagar_odoo_line', 'odoo_line_id'),
    )

    def __repr__(self):
        return f'<ContasAPagar {self.empresa}-{self.titulo_nf}-{self.parcela}>'

    @property
    def titulo_parcela_display(self) -> str:
        """Retorna o formato de exibição: Titulo-Parcela"""
        return f"{self.titulo_nf}-{self.parcela}"

    @property
    def empresa_nome(self) -> str:
        """Retorna o nome da empresa baseado no código"""
        nomes = {
            1: 'NACOM GOYA - FB',
            2: 'NACOM GOYA - SC',
            3: 'NACOM GOYA - CD'
        }
        return nomes.get(self.empresa, f'Empresa {self.empresa}')

    @property
    def dias_vencidos(self) -> int:
        """Calcula dias vencidos (positivo) ou a vencer (negativo)"""
        if not self.vencimento:
            return 0
        hoje = date.today()
        return (hoje - self.vencimento).days

    @property
    def status_vencimento(self) -> str:
        """Retorna status baseado no vencimento"""
        if self.parcela_paga:
            return 'PAGO'
        dias = self.dias_vencidos
        if dias > 0:
            return 'VENCIDO'
        elif dias == 0:
            return 'VENCE_HOJE'
        elif dias >= -7:
            return 'VENCE_SEMANA'
        else:
            return 'A_VENCER'

    def to_dict(self):
        return {
            'id': self.id,
            'empresa': self.empresa,
            'empresa_nome': self.empresa_nome,
            'titulo_nf': self.titulo_nf,
            'parcela': self.parcela,
            'titulo_parcela_display': self.titulo_parcela_display,
            # IDs Odoo
            'odoo_line_id': self.odoo_line_id,
            'odoo_move_id': self.odoo_move_id,
            'odoo_move_name': self.odoo_move_name,
            # Fornecedor
            'partner_id': self.partner_id,
            'cnpj': self.cnpj,
            'raz_social': self.raz_social,
            'raz_social_red': self.raz_social_red,
            # Datas
            'emissao': self.emissao.isoformat() if self.emissao else None,
            'vencimento': self.vencimento.isoformat() if self.vencimento else None,
            # Valores
            'valor_original': self.valor_original,
            'valor_residual': self.valor_residual,
            # Status
            'parcela_paga': self.parcela_paga,
            'reconciliado': self.reconciliado,
            'status_sistema': self.status_sistema,
            'data_programada': self.data_programada.isoformat() if self.data_programada else None,
            # Calculados
            'dias_vencidos': self.dias_vencidos,
            'status_vencimento': self.status_vencimento,
            # Campos do sistema
            'observacao': self.observacao,
            'alerta': self.alerta,
            # Auditoria
            'ultima_sincronizacao': self.ultima_sincronizacao.isoformat() if self.ultima_sincronizacao else None,
        }

    @property
    def parcela_int(self) -> Optional[int]:
        """Parcela como int, para Odoo API e campos cache INTEGER."""
        from app.financeiro.parcela_utils import parcela_to_int
        return parcela_to_int(self.parcela)


# =============================================================================
# FIM CONTAS A PAGAR
# =============================================================================


# =============================================================================
# CNAB400 - RETORNO BANCÁRIO
# =============================================================================

class CnabRetornoLote(db.Model):
    """
    Lote de arquivo CNAB400 importado.

    Representa um arquivo .ret processado, contendo múltiplos registros
    de cobrança bancária (liquidações, confirmações, baixas).
    """
    __tablename__ = 'cnab_retorno_lote'

    id = db.Column(db.Integer, primary_key=True)
    arquivo_nome = db.Column(db.String(255), nullable=False)
    banco_codigo = db.Column(db.String(3), nullable=False)  # 274 = BMP
    banco_nome = db.Column(db.String(100))
    data_arquivo = db.Column(db.Date)
    data_processamento = db.Column(db.DateTime, default=agora_utc_naive)

    # Estatísticas
    total_registros = db.Column(db.Integer, default=0)
    registros_liquidados = db.Column(db.Integer, default=0)
    registros_confirmados = db.Column(db.Integer, default=0)
    registros_baixados = db.Column(db.Integer, default=0)
    registros_com_match = db.Column(db.Integer, default=0)
    registros_sem_match = db.Column(db.Integer, default=0)
    registros_ja_pagos = db.Column(db.Integer, default=0)
    valor_total_liquidado = db.Column(db.Numeric(15, 2), default=0)

    # Status do lote
    status = db.Column(db.String(30), default='IMPORTADO', index=True)
    # IMPORTADO           → Arquivo lido e registros criados
    # AGUARDANDO_REVISAO  → Aguardando revisão dos itens sem match
    # APROVADO            → Todos os matches foram aprovados
    # PROCESSANDO         → Executando baixas
    # CONCLUIDO           → Todas as baixas executadas
    # PARCIAL             → Algumas baixas com erro
    # ERRO                → Falha geral no processamento

    processado_por = db.Column(db.String(100))
    erro_mensagem = db.Column(db.Text)

    # Hash para verificação de duplicação (SHA256)
    hash_arquivo = db.Column(db.String(64), unique=True, index=True)

    # Batch de upload (agrupa múltiplos arquivos enviados juntos)
    batch_id = db.Column(db.String(36), index=True, nullable=True)  # UUID do batch

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)

    # Relacionamento
    itens = db.relationship('CnabRetornoItem', backref='lote', lazy='dynamic',
                           cascade='all, delete-orphan')

    def __repr__(self):
        return f'<CnabRetornoLote {self.id} - {self.arquivo_nome}>'

    def atualizar_estatisticas(self):
        """Recalcula estatísticas do lote baseado nos itens"""
        itens = self.itens.all()

        self.total_registros = len(itens)
        self.registros_liquidados = sum(1 for i in itens if i.codigo_ocorrencia == '06')
        self.registros_confirmados = sum(1 for i in itens if i.codigo_ocorrencia == '02')
        self.registros_baixados = sum(1 for i in itens if i.codigo_ocorrencia in ('09', '10'))
        self.registros_com_match = sum(1 for i in itens if i.status_match == 'MATCH_ENCONTRADO')
        self.registros_sem_match = sum(1 for i in itens if i.status_match == 'SEM_MATCH')
        self.registros_ja_pagos = sum(1 for i in itens if i.status_match == 'JA_PAGO')

        # Soma valor dos liquidados com match
        self.valor_total_liquidado = sum(
            float(i.valor_pago or i.valor_titulo or 0)
            for i in itens
            if i.codigo_ocorrencia == '06' and i.status_match == 'MATCH_ENCONTRADO'
        )

    def to_dict(self):
        return {
            'id': self.id,
            'arquivo_nome': self.arquivo_nome,
            'banco_codigo': self.banco_codigo,
            'banco_nome': self.banco_nome,
            'data_arquivo': self.data_arquivo.isoformat() if self.data_arquivo else None,
            'data_processamento': self.data_processamento.isoformat() if self.data_processamento else None,
            'total_registros': self.total_registros,
            'registros_liquidados': self.registros_liquidados,
            'registros_confirmados': self.registros_confirmados,
            'registros_baixados': self.registros_baixados,
            'registros_com_match': self.registros_com_match,
            'registros_sem_match': self.registros_sem_match,
            'registros_ja_pagos': self.registros_ja_pagos,
            'valor_total_liquidado': float(self.valor_total_liquidado) if self.valor_total_liquidado else 0,
            'status': self.status,
            'processado_por': self.processado_por,
            'erro_mensagem': self.erro_mensagem,
            'batch_id': self.batch_id,
        }


class CnabRetornoItem(db.Model):
    """
    Linha individual do arquivo CNAB400 (registro tipo 1 - detalhe).

    Cada item representa uma transação de cobrança (liquidação, confirmação,
    baixa, etc.) extraída do arquivo de retorno bancário.
    """
    __tablename__ = 'cnab_retorno_item'

    id = db.Column(db.Integer, primary_key=True)
    lote_id = db.Column(db.Integer, db.ForeignKey('cnab_retorno_lote.id', ondelete='CASCADE'),
                       nullable=False, index=True)

    # Dados do CNAB (posições fixas do layout)
    tipo_registro = db.Column(db.String(1))  # 0=Header, 1=Detalhe, 9=Trailer
    nosso_numero = db.Column(db.String(20), index=True)  # Identificação no banco
    seu_numero = db.Column(db.String(25), index=True)    # Identificação da empresa (NF/Parcela)
    cnpj_pagador = db.Column(db.String(20), index=True)  # CNPJ do sacado/pagador

    # Ocorrência
    codigo_ocorrencia = db.Column(db.String(2), index=True)  # 02, 06, 10, etc.
    descricao_ocorrencia = db.Column(db.String(100))         # Descrição do código
    data_ocorrencia = db.Column(db.Date)

    # Valores (em centavos no CNAB, convertidos para decimal)
    valor_titulo = db.Column(db.Numeric(15, 2))
    valor_pago = db.Column(db.Numeric(15, 2))
    valor_juros = db.Column(db.Numeric(15, 2))
    valor_desconto = db.Column(db.Numeric(15, 2))
    valor_abatimento = db.Column(db.Numeric(15, 2))

    # Datas
    data_vencimento = db.Column(db.Date)
    data_credito = db.Column(db.Date)

    # Dados extraídos do Seu Número (parse NF/Parcela)
    nf_extraida = db.Column(db.String(20))
    parcela_extraida = db.Column(db.String(10))

    # Vinculação com Contas a Receber
    conta_a_receber_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber.id'), index=True)
    conta_a_receber = db.relationship('ContasAReceber', foreign_keys=[conta_a_receber_id])

    # Vinculação com Extrato Bancário (opcional - se encontrado)
    extrato_item_id = db.Column(db.Integer, db.ForeignKey('extrato_item.id'), nullable=True, index=True)
    extrato_item = db.relationship('ExtratoItem', foreign_keys=[extrato_item_id])

    # Status do match com extrato
    status_match_extrato = db.Column(db.String(30), default='PENDENTE')
    # PENDENTE, MATCH_ENCONTRADO, SEM_MATCH, NAO_APLICAVEL, CONCILIADO, ERRO
    match_score_extrato = db.Column(db.Integer)
    match_criterio_extrato = db.Column(db.String(100))  # DATA+VALOR+CNPJ_EXATO, etc.

    # Status de matching
    status_match = db.Column(db.String(30), default='PENDENTE', index=True)
    # PENDENTE         → Aguardando processamento
    # MATCH_ENCONTRADO → Título encontrado (score 100)
    # SEM_MATCH        → Título não existe no sistema
    # JA_PAGO          → Título existe mas já estava pago
    # FORMATO_INVALIDO → Seu Número não tem formato NF/Parcela
    # NAO_APLICAVEL    → Código ocorrência não é liquidação/baixa (02, 03, etc.)
    # PROCESSADO       → Baixa executada com sucesso
    # ERRO             → Erro ao processar baixa

    match_score = db.Column(db.Integer)           # 100 = match exato por NF/Parcela
    match_criterio = db.Column(db.String(100))    # NF_PARCELA_EXATO

    # Resultado do processamento
    processado = db.Column(db.Boolean, default=False, index=True)
    data_processamento = db.Column(db.DateTime)
    erro_mensagem = db.Column(db.Text)

    # Linha original (para debug e auditoria)
    linha_original = db.Column(db.Text)
    numero_linha = db.Column(db.Integer)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)

    __table_args__ = (
        Index('idx_cnab_item_lote_status', 'lote_id', 'status_match'),
        Index('idx_cnab_item_seu_numero', 'seu_numero'),
        # CONSTRAINT: Cada extrato só pode ter 1 CNAB vinculado (impede match 2:1)
        # Adicionada via migration: scripts/migrations/fix_cnab_extrato_duplicates.py
        db.UniqueConstraint('extrato_item_id', name='uq_cnab_extrato_item_unique'),
    )

    def __repr__(self):
        return f'<CnabRetornoItem {self.id} - {self.seu_numero} - {self.status_match}>'

    @property
    def ocorrencia_display(self):
        """Retorna descrição legível da ocorrência"""
        OCORRENCIAS = {
            '02': '✅ Entrada Confirmada',
            '03': '❌ Entrada Rejeitada',
            '06': '💰 Liquidação Normal',
            '09': '📤 Baixado Automaticamente',
            '10': '📤 Baixado conf. Instruções',
            '11': 'Títulos em Ser',
            '14': '📅 Alteração de Vencimento',
            '17': '💰 Liquidação após Baixa',
            '23': '⚠️ Encaminhado a Protesto',
        }
        return OCORRENCIAS.get(self.codigo_ocorrencia, f'Código {self.codigo_ocorrencia}')

    @property
    def status_match_display(self):
        """Retorna descrição legível do status de match"""
        STATUS = {
            'PENDENTE': '⏳ Pendente',
            'MATCH_ENCONTRADO': '✅ Match Encontrado',
            'SEM_MATCH': '❌ Sem Match',
            'JA_PAGO': '💵 Já Pago',
            'FORMATO_INVALIDO': '⚠️ Formato Inválido',
            'NAO_APLICAVEL': '➖ Não Aplicável',
            'PROCESSADO': '✅ Processado',
            'ERRO': '❌ Erro',
        }
        return STATUS.get(self.status_match, self.status_match)

    @property
    def cnpj_cliente(self):
        """
        Retorna o CNPJ correto do cliente (não o da empresa).

        O arquivo CNAB BMP 274 coloca o CNPJ da empresa na posição do pagador,
        então precisamos buscar o CNPJ real do cliente de outras fontes:
        1. ContasAReceber (título vinculado) - mais confiável
        2. FaturamentoProduto (fallback por NF)

        Returns:
            CNPJ formatado do cliente ou None
        """
        # FASE 1: Buscar do título vinculado
        if self.conta_a_receber_id and self.conta_a_receber:
            cnpj = self.conta_a_receber.cnpj
            if cnpj:
                return cnpj

        # FASE 2: Fallback para FaturamentoProduto (lazy import para evitar circular)
        if self.nf_extraida:
            from app.faturamento.models import FaturamentoProduto
            faturamento = FaturamentoProduto.query.filter(
                FaturamentoProduto.numero_nf == self.nf_extraida,
                FaturamentoProduto.status_nf != 'Cancelado'
            ).first()
            if faturamento and faturamento.cnpj_cliente:
                return faturamento.cnpj_cliente

        return None

    @property
    def nome_cliente(self):
        """
        Retorna o nome do cliente vinculado ao título.

        Fontes:
        1. ContasAReceber (título vinculado)
        2. FaturamentoProduto (fallback por NF)

        Returns:
            Nome/Razão Social do cliente ou None
        """
        # FASE 1: Buscar do título vinculado
        if self.conta_a_receber_id and self.conta_a_receber:
            nome = self.conta_a_receber.raz_social
            if nome:
                return nome

        # FASE 2: Fallback para FaturamentoProduto
        if self.nf_extraida:
            from app.faturamento.models import FaturamentoProduto
            faturamento = FaturamentoProduto.query.filter(
                FaturamentoProduto.numero_nf == self.nf_extraida,
                FaturamentoProduto.status_nf != 'Cancelado'
            ).first()
            if faturamento and faturamento.nome_cliente:
                return faturamento.nome_cliente

        return None

    def to_dict(self):
        return {
            'id': self.id,
            'lote_id': self.lote_id,
            'tipo_registro': self.tipo_registro,
            'nosso_numero': self.nosso_numero,
            'seu_numero': self.seu_numero,
            'cnpj_pagador': self.cnpj_pagador,
            'codigo_ocorrencia': self.codigo_ocorrencia,
            'descricao_ocorrencia': self.descricao_ocorrencia,
            'ocorrencia_display': self.ocorrencia_display,
            'data_ocorrencia': self.data_ocorrencia.isoformat() if self.data_ocorrencia else None,
            'valor_titulo': float(self.valor_titulo) if self.valor_titulo else None,
            'valor_pago': float(self.valor_pago) if self.valor_pago else None,
            'valor_juros': float(self.valor_juros) if self.valor_juros else None,
            'valor_desconto': float(self.valor_desconto) if self.valor_desconto else None,
            'valor_abatimento': float(self.valor_abatimento) if self.valor_abatimento else None,
            'data_vencimento': self.data_vencimento.isoformat() if self.data_vencimento else None,
            'nf_extraida': self.nf_extraida,
            'parcela_extraida': self.parcela_extraida,
            'conta_a_receber_id': self.conta_a_receber_id,
            'status_match': self.status_match,
            'status_match_display': self.status_match_display,
            'match_score': self.match_score,
            'match_criterio': self.match_criterio,
            # Campos de extrato
            'extrato_item_id': self.extrato_item_id,
            'status_match_extrato': self.status_match_extrato,
            'match_score_extrato': self.match_score_extrato,
            'match_criterio_extrato': self.match_criterio_extrato,
            # Processamento
            'processado': self.processado,
            'erro_mensagem': self.erro_mensagem,
            'numero_linha': self.numero_linha,
        }


# =============================================================================
# FIM CNAB400
# =============================================================================

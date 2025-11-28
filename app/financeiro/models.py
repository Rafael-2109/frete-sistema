from app import db
from datetime import datetime, date, timedelta
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
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
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
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
    confirmacao_entrega = db.Column(db.Text, nullable=True)

    # Observações e alertas
    observacao = db.Column(db.Text, nullable=True)
    alerta = db.Column(db.Boolean, default=False, nullable=False)

    # Ação necessária
    acao_necessaria_tipo_id = db.Column(db.Integer, db.ForeignKey('contas_a_receber_tipos.id'), nullable=True)
    obs_acao_necessaria = db.Column(db.Text, nullable=True)
    data_lembrete = db.Column(db.Date, nullable=True)

    # =========================================================================
    # CAMPOS ENRIQUECIDOS (via EntregaMonitorada e FaturamentoProduto)
    # =========================================================================

    # EntregaMonitorada
    entrega_monitorada_id = db.Column(db.Integer, db.ForeignKey('entregas_monitoradas.id'), nullable=True)
    data_entrega_prevista = db.Column(db.Date, nullable=True)
    data_hora_entrega_realizada = db.Column(db.DateTime, nullable=True)
    status_finalizacao = db.Column(db.String(50), nullable=True)
    nova_nf = db.Column(db.String(20), nullable=True)
    reagendar = db.Column(db.Boolean, default=False)
    data_embarque = db.Column(db.Date, nullable=True)
    transportadora = db.Column(db.String(255), nullable=True)
    vendedor = db.Column(db.String(100), nullable=True)
    canhoto_arquivo = db.Column(db.String(500), nullable=True)  # Caminho do canhoto

    # AgendamentoEntrega (último)
    ultimo_agendamento_data = db.Column(db.Date, nullable=True)
    ultimo_agendamento_status = db.Column(db.String(20), nullable=True)
    ultimo_agendamento_protocolo = db.Column(db.String(100), nullable=True)

    # FaturamentoProduto
    nf_cancelada = db.Column(db.Boolean, default=False, nullable=False)  # Se FaturamentoProduto.ativo = False

    # NF no CD (EntregaMonitorada)
    nf_cd = db.Column(db.Boolean, default=False, nullable=False)  # Indica se a NF está no CD

    # =========================================================================
    # AUDITORIA E CONTROLE
    # =========================================================================

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
        Usa LiberacaoAntecipacao + data_hora_entrega_realizada.
        """
        if not self.data_hora_entrega_realizada:
            self.liberacao_prevista_antecipacao = None
            return

        config = LiberacaoAntecipacao.buscar_configuracao(
            cnpj=self.cnpj,
            razao_social=self.raz_social,
            uf=self.uf_cliente
        )

        if config:
            self.liberacao_prevista_antecipacao = LiberacaoAntecipacao.calcular_data_liberacao(
                self.data_hora_entrega_realizada,
                config.dias_uteis_previsto
            )
        else:
            self.liberacao_prevista_antecipacao = None

    def to_dict(self):
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
            'confirmacao_entrega': self.confirmacao_entrega,
            'observacao': self.observacao,
            'alerta': self.alerta,
            'acao_necessaria_tipo': self.acao_necessaria_tipo.tipo if self.acao_necessaria_tipo else None,
            'obs_acao_necessaria': self.obs_acao_necessaria,
            'data_lembrete': self.data_lembrete.isoformat() if self.data_lembrete else None,
            'data_entrega_prevista': self.data_entrega_prevista.isoformat() if self.data_entrega_prevista else None,
            'data_hora_entrega_realizada': self.data_hora_entrega_realizada.isoformat() if self.data_hora_entrega_realizada else None,
            'status_finalizacao': self.status_finalizacao,
            'nova_nf': self.nova_nf,
            'reagendar': self.reagendar,
            'data_embarque': self.data_embarque.isoformat() if self.data_embarque else None,
            'transportadora': self.transportadora,
            'vendedor': self.vendedor,
            'canhoto_arquivo': self.canhoto_arquivo,
            'ultimo_agendamento_data': self.ultimo_agendamento_data.isoformat() if self.ultimo_agendamento_data else None,
            'ultimo_agendamento_status': self.ultimo_agendamento_status,
            'ultimo_agendamento_protocolo': self.ultimo_agendamento_protocolo,
            'nf_cancelada': self.nf_cancelada,
            'nf_cd': self.nf_cd,
            'total_abatimentos': sum(ab.valor or 0 for ab in self.abatimentos.all())
        }


class ContasAReceberAbatimento(db.Model):
    """
    Abatimentos vinculados a Contas a Receber.
    Relacionamento: 1 ContasAReceber : N Abatimentos
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

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # Relacionamento
    tipo = relationship('ContasAReceberTipo', foreign_keys=[tipo_id])

    def __repr__(self):
        return f'<ContasAReceberAbatimento {self.id} - R$ {self.valor}>'

    def to_dict(self):
        return {
            'id': self.id,
            'conta_a_receber_id': self.conta_a_receber_id,
            'tipo': self.tipo.tipo if self.tipo else None,
            'motivo': self.motivo,
            'doc_motivo': self.doc_motivo,
            'valor': self.valor,
            'previsto': self.previsto,
            'data': self.data.isoformat() if self.data else None,
            'data_vencimento': self.data_vencimento.isoformat() if self.data_vencimento else None
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
    alterado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
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


# =============================================================================
# FIM CONTAS A RECEBER
# =============================================================================


class PendenciaFinanceiraNF(db.Model):
    __tablename__ = 'pendencias_financeiras_nf'

    id = db.Column(db.Integer, primary_key=True)
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    observacao = db.Column(db.Text)
    resposta_logistica = db.Column(db.Text, nullable=True)
    respondida_em = db.Column(db.DateTime, nullable=True)
    respondida_por = db.Column(db.String(100), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
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

"""
Modelo PalletCredito - Crédito de Pallet a Receber

Este modelo representa o crédito de pallets que a Nacom tem direito de
receber de terceiros (transportadora ou cliente). É o registro central
do Domínio A (Controle dos Pallets).

Criado automaticamente ao importar NF de remessa do Odoo.
Pode ter múltiplas soluções parciais até qtd_saldo chegar a zero.

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
from app import db
from app.utils.timezone import agora_brasil


class PalletCredito(db.Model):
    """
    Registro de crédito de pallet a receber.

    Criado automaticamente ao IMPORTAR NF de remessa do Odoo.
    O crédito rastreia quanto a Nacom tem a receber de pallets físicos
    ou valor equivalente.

    Relacionamentos:
    - N:1 com PalletNFRemessa (FK nf_remessa_id)
    - 1:N com PalletDocumento (documentos que enriquecem o crédito)
    - 1:N com PalletSolucao (soluções que decrementam o saldo)

    Status:
    - PENDENTE: Saldo = quantidade original, nenhuma solução registrada
    - PARCIAL: 0 < Saldo < quantidade original
    - RESOLVIDO: Saldo = 0, crédito totalmente resolvido
    """
    __tablename__ = 'pallet_creditos'

    id = db.Column(db.Integer, primary_key=True)

    # Vínculo com NF de remessa (origem do crédito)
    nf_remessa_id = db.Column(
        db.Integer,
        db.ForeignKey('pallet_nf_remessa.id', ondelete='RESTRICT'),
        nullable=False,
        index=True
    )

    # Quantidade original e saldo atual
    qtd_original = db.Column(db.Integer, nullable=False)
    qtd_saldo = db.Column(db.Integer, nullable=False)  # Saldo pendente de resolução

    # Responsável atual pelo débito de pallets
    # TRANSPORTADORA = Transportadora deve devolver/pagar pallets
    # CLIENTE = Cliente final deve devolver/pagar pallets
    tipo_responsavel = db.Column(db.String(20), nullable=False)
    cnpj_responsavel = db.Column(db.String(20), nullable=False, index=True)
    nome_responsavel = db.Column(db.String(255), nullable=True)

    # Dados complementares do responsável
    uf_responsavel = db.Column(db.String(2), nullable=True)
    cidade_responsavel = db.Column(db.String(100), nullable=True)

    # Prazo de cobrança (calculado com base em UF/Rota)
    # SP/RED = 7 dias
    # Demais = 30 dias
    prazo_dias = db.Column(db.Integer, nullable=True)
    data_vencimento = db.Column(db.Date, nullable=True)

    # Status do crédito (Domínio A - Controle de Pallets)
    # PENDENTE = Saldo integral pendente
    # PARCIAL = Parte resolvida, parte pendente
    # RESOLVIDO = Saldo zerado, crédito fechado
    status = db.Column(db.String(20), default='PENDENTE', nullable=False, index=True)

    # Referência à MovimentacaoEstoque original (para migração)
    movimentacao_estoque_id = db.Column(db.Integer, nullable=True)

    # Observações
    observacao = db.Column(db.Text, nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_brasil)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # Soft delete
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    # Relacionamentos
    documentos = db.relationship('PalletDocumento', backref='credito', lazy='dynamic',
                                  foreign_keys='PalletDocumento.credito_id')
    solucoes = db.relationship('PalletSolucao', backref='credito', lazy='dynamic',
                                foreign_keys='PalletSolucao.credito_id',
                                primaryjoin='PalletCredito.id == PalletSolucao.credito_id')
    # Soluções de substituição onde este crédito é o DESTINO
    substituicoes_recebidas = db.relationship(
        'PalletSolucao',
        foreign_keys='PalletSolucao.credito_destino_id',
        backref='credito_destino'
    )

    # Índices compostos para otimização de queries
    __table_args__ = (
        db.Index('idx_credito_responsavel_status', 'cnpj_responsavel', 'status'),
        db.Index('idx_credito_tipo_status', 'tipo_responsavel', 'status'),
        db.Index('idx_credito_vencimento', 'data_vencimento', 'status'),
    )

    def __repr__(self):
        return f"<PalletCredito #{self.id} - NF {self.nf_remessa_id} - Saldo: {self.qtd_saldo}/{self.qtd_original}>"

    @property
    def qtd_resolvida(self):
        """Quantidade já resolvida (baixada, vendida, recebida, etc.)"""
        return self.qtd_original - self.qtd_saldo

    @property
    def percentual_resolvido(self):
        """Percentual do crédito já resolvido"""
        if self.qtd_original == 0:
            return 100.0
        return round((self.qtd_resolvida / self.qtd_original) * 100, 2)

    @property
    def totalmente_resolvido(self):
        """Verifica se o crédito foi totalmente resolvido"""
        return self.qtd_saldo <= 0

    @property
    def parcialmente_resolvido(self):
        """Verifica se há resolução parcial"""
        return 0 < self.qtd_saldo < self.qtd_original

    def atualizar_status(self):
        """
        Atualiza o status do crédito baseado no saldo.
        Deve ser chamado após registrar uma solução.
        """
        if self.qtd_saldo <= 0:
            self.status = 'RESOLVIDO'
        elif self.qtd_saldo < self.qtd_original:
            self.status = 'PARCIAL'
        else:
            self.status = 'PENDENTE'

    def registrar_solucao(self, quantidade: int):
        """
        Registra uma solução parcial ou total no crédito.

        Args:
            quantidade: Quantidade sendo resolvida

        Returns:
            int: Novo saldo após a solução

        Raises:
            ValueError: Se quantidade > saldo disponível
        """
        if quantidade > self.qtd_saldo:
            raise ValueError(
                f"Quantidade ({quantidade}) maior que saldo disponível ({self.qtd_saldo})"
            )

        self.qtd_saldo -= quantidade
        self.atualizar_status()
        return self.qtd_saldo

    def calcular_prazo(self, uf: str = None, rota: str = None):
        """
        Calcula o prazo de cobrança baseado na UF ou rota.

        Regra:
        - SP ou RED (rota) = 7 dias
        - Demais = 30 dias

        Args:
            uf: UF do responsável (opcional, usa self.uf_responsavel)
            rota: Rota de entrega (opcional)
        """
        from datetime import timedelta

        uf = uf or self.uf_responsavel
        prazo = 7 if (uf == 'SP' or rota == 'RED') else 30

        self.prazo_dias = prazo

        # Calcula data de vencimento a partir da data de criação do crédito
        if self.criado_em:
            data_base = self.criado_em.date() if hasattr(self.criado_em, 'date') else self.criado_em
            self.data_vencimento = data_base + timedelta(days=prazo)

    def to_dict(self):
        """Serializa o modelo para dicionário"""
        return {
            'id': self.id,
            'nf_remessa_id': self.nf_remessa_id,
            'qtd_original': self.qtd_original,
            'qtd_saldo': self.qtd_saldo,
            'qtd_resolvida': self.qtd_resolvida,
            'percentual_resolvido': self.percentual_resolvido,
            'tipo_responsavel': self.tipo_responsavel,
            'cnpj_responsavel': self.cnpj_responsavel,
            'nome_responsavel': self.nome_responsavel,
            'uf_responsavel': self.uf_responsavel,
            'cidade_responsavel': self.cidade_responsavel,
            'prazo_dias': self.prazo_dias,
            'data_vencimento': self.data_vencimento.isoformat() if self.data_vencimento else None,
            'status': self.status,
            'observacao': self.observacao,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por': self.criado_por,
        }

    @classmethod
    def listar_por_responsavel(cls, cnpj_responsavel: str, apenas_pendentes: bool = True):
        """
        Lista créditos por responsável.

        Args:
            cnpj_responsavel: CNPJ do responsável
            apenas_pendentes: Se True, retorna apenas créditos não resolvidos

        Returns:
            Query filtrada
        """
        query = cls.query.filter(
            cls.cnpj_responsavel == cnpj_responsavel,
            cls.ativo == True
        )

        if apenas_pendentes:
            query = query.filter(cls.status.in_(['PENDENTE', 'PARCIAL']))

        return query.order_by(cls.criado_em.desc())

    @property
    def dias_para_vencer(self):
        """Calcula quantos dias faltam para o crédito vencer"""
        if self.data_vencimento:
            from datetime import datetime
            hoje = datetime.now().date()
            delta = self.data_vencimento - hoje
            return delta.days
        return None

    @property
    def vencido(self):
        """Verifica se o crédito está vencido"""
        dias = self.dias_para_vencer
        return dias is not None and dias < 0

    @property
    def prestes_a_vencer(self):
        """Verifica se o crédito está prestes a vencer (menos de 7 dias)"""
        dias = self.dias_para_vencer
        return dias is not None and 0 <= dias <= 7

    @classmethod
    def saldo_total_por_responsavel(cls, cnpj_responsavel: str):
        """
        Calcula o saldo total de pallets pendentes para um responsável.

        Args:
            cnpj_responsavel: CNPJ do responsável

        Returns:
            int: Saldo total de pallets pendentes
        """
        from sqlalchemy import func

        result = db.session.query(
            func.sum(cls.qtd_saldo)
        ).filter(
            cls.cnpj_responsavel == cnpj_responsavel,
            cls.status.in_(['PENDENTE', 'PARCIAL']),
            cls.ativo == True
        ).scalar()

        return result or 0

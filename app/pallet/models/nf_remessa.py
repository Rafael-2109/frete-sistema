"""
Modelo PalletNFRemessa - NF de Remessa de Pallet

Este modelo representa a NF de remessa de pallet emitida para terceiros
(transportadora ou cliente). É o ponto central de rastreamento no Domínio B
(Tratativa das NFs).

Criado como parte da reestruturação do módulo de pallets v2.
Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
from app import db
from app.utils.timezone import agora_utc_naive


class PalletNFRemessa(db.Model):
    """
    NF de remessa de pallet emitida.

    Ponto central de rastreamento para o ciclo de vida documental da NF.
    Uma NF de remessa cria automaticamente um PalletCredito vinculado.

    Relacionamentos:
    - 1:N com PalletCredito (uma NF pode ter múltiplos créditos se houver substituição)
    - 1:N com PalletNFSolucao (uma NF pode ter múltiplas soluções documentais)

    Status:
    - ATIVA: NF emitida, aguardando resolução documental
    - RESOLVIDA: NF totalmente resolvida (devoluções/retornos vinculados)
    - CANCELADA: NF foi cancelada (mantida para auditoria)
    """
    __tablename__ = 'pallet_nf_remessa'

    id = db.Column(db.Integer, primary_key=True)

    # Identificação da NF
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    serie = db.Column(db.String(5), nullable=True)
    chave_nfe = db.Column(db.String(44), nullable=True, unique=True)
    data_emissao = db.Column(db.DateTime, nullable=False)

    # Dados Odoo
    odoo_account_move_id = db.Column(db.Integer, nullable=True, index=True)
    odoo_picking_id = db.Column(db.Integer, nullable=True)

    # Empresa emissora
    # CD = Centro de Distribuição (CNPJ 1)
    # FB = Fábrica (CNPJ 2)
    # SC = Santa Catarina (CNPJ 3)
    empresa = db.Column(db.String(10), nullable=False)

    # Destinatário da NF de remessa
    # TRANSPORTADORA = Pallets enviados para transportadora
    # CLIENTE = Pallets enviados diretamente para cliente
    tipo_destinatario = db.Column(db.String(20), nullable=False)
    cnpj_destinatario = db.Column(db.String(20), nullable=False, index=True)
    nome_destinatario = db.Column(db.String(255), nullable=True)

    # Transportadora (quando tipo_destinatario = 'CLIENTE', registra a transportadora que levou)
    cnpj_transportadora = db.Column(db.String(20), nullable=True)
    nome_transportadora = db.Column(db.String(255), nullable=True)

    # Quantidade e valores
    quantidade = db.Column(db.Integer, nullable=False)
    valor_unitario = db.Column(db.Numeric(15, 2), default=35.00)
    valor_total = db.Column(db.Numeric(15, 2), nullable=True)

    # Vínculo com Embarque (quando NF criada a partir de embarque)
    embarque_id = db.Column(db.Integer, db.ForeignKey('embarques.id', ondelete='SET NULL'), nullable=True)
    embarque_item_id = db.Column(db.Integer, db.ForeignKey('embarque_itens.id', ondelete='SET NULL'), nullable=True)

    # Status da NF (Domínio B - Tratativa Documental)
    # ATIVA = NF emitida, aguardando resolução documental
    # RESOLVIDA = NF totalmente resolvida (devoluções/retornos)
    # CANCELADA = NF foi cancelada
    status = db.Column(db.String(20), default='ATIVA', nullable=False, index=True)

    # Quantidade já resolvida (via devoluções/retornos)
    qtd_resolvida = db.Column(db.Integer, default=0, nullable=False)

    # Campos de cancelamento
    cancelada = db.Column(db.Boolean, default=False, nullable=False)
    cancelada_em = db.Column(db.DateTime, nullable=True)
    cancelada_por = db.Column(db.String(100), nullable=True)
    motivo_cancelamento = db.Column(db.String(255), nullable=True)

    # Referência à MovimentacaoEstoque original (para migração)
    movimentacao_estoque_id = db.Column(db.Integer, nullable=True)

    # Observações
    observacao = db.Column(db.Text, nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # Soft delete
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    # Relacionamentos
    creditos = db.relationship(
        'PalletCredito', backref='nf_remessa', lazy='select',
        foreign_keys='PalletCredito.nf_remessa_id'
    )
    solucoes_nf = db.relationship(
        'PalletNFSolucao', backref='nf_remessa', lazy='select',
        foreign_keys='PalletNFSolucao.nf_remessa_id'
    )
    embarque = db.relationship('Embarque', foreign_keys=[embarque_id])
    embarque_item = db.relationship('EmbarqueItem', foreign_keys=[embarque_item_id])

    # Índices compostos para otimização de queries
    __table_args__ = (
        db.Index('idx_nf_remessa_empresa_status', 'empresa', 'status'),
        db.Index('idx_nf_remessa_destinatario_tipo', 'cnpj_destinatario', 'tipo_destinatario'),
        db.Index('idx_nf_remessa_data_status', 'data_emissao', 'status'),
    )

    def __repr__(self):
        return f"<PalletNFRemessa #{self.id} - NF {self.numero_nf} - {self.tipo_destinatario}: {self.nome_destinatario}>"

    @property
    def qtd_pendente(self):
        """Quantidade ainda pendente de resolução documental"""
        return self.quantidade - (self.qtd_resolvida or 0)

    @property
    def totalmente_resolvida(self):
        """Verifica se toda a quantidade foi resolvida"""
        return self.qtd_pendente <= 0

    @property
    def parcialmente_resolvida(self):
        """Verifica se há resolução parcial"""
        return 0 < (self.qtd_resolvida or 0) < self.quantidade

    def atualizar_status(self):
        """
        Atualiza o status da NF baseado nas resoluções.
        Deve ser chamado após registrar uma solução.
        """
        if self.cancelada:
            self.status = 'CANCELADA'
        elif self.totalmente_resolvida:
            self.status = 'RESOLVIDA'
        elif self.parcialmente_resolvida:
            self.status = 'ATIVA'  # Mantém ativa até resolver 100%
        else:
            self.status = 'ATIVA'

    def cancelar(self, motivo: str, usuario: str):
        """
        Cancela a NF de remessa.

        Args:
            motivo: Motivo do cancelamento
            usuario: Usuário que cancelou
        """
        self.cancelada = True
        self.cancelada_em = agora_utc_naive()
        self.cancelada_por = usuario
        self.motivo_cancelamento = motivo
        self.status = 'CANCELADA'

    def to_dict(self):
        """Serializa o modelo para dicionário"""
        return {
            'id': self.id,
            'numero_nf': self.numero_nf,
            'serie': self.serie,
            'chave_nfe': self.chave_nfe,
            'data_emissao': self.data_emissao.isoformat() if self.data_emissao else None,
            'empresa': self.empresa,
            'tipo_destinatario': self.tipo_destinatario,
            'cnpj_destinatario': self.cnpj_destinatario,
            'nome_destinatario': self.nome_destinatario,
            'cnpj_transportadora': self.cnpj_transportadora,
            'nome_transportadora': self.nome_transportadora,
            'quantidade': self.quantidade,
            'valor_unitario': float(self.valor_unitario) if self.valor_unitario else None,
            'valor_total': float(self.valor_total) if self.valor_total else None,
            'status': self.status,
            'qtd_resolvida': self.qtd_resolvida,
            'qtd_pendente': self.qtd_pendente,
            'cancelada': self.cancelada,
            'cancelada_em': self.cancelada_em.isoformat() if self.cancelada_em else None,
            'motivo_cancelamento': self.motivo_cancelamento,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por': self.criado_por,
        }

"""
Modelo PalletDocumento - Documentos de Enriquecimento de Crédito

Este modelo representa documentos que enriquecem um crédito de pallet,
como canhotos assinados e vales pallet emitidos pelo cliente.

Substitui parcialmente o modelo ValePallet, focando apenas na
responsabilidade de "documento enriquecedor".

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
from datetime import datetime
from app import db
from app.utils.timezone import agora_utc_naive


class PalletDocumento(db.Model):
    """
    Documentos que enriquecem o crédito de pallet.

    Tipos de documento:
    - CANHOTO: Canhoto da NF de remessa assinado pelo cliente/transportadora
    - VALE_PALLET: Vale emitido pelo cliente quando não aceita NF de remessa

    O documento confirma que o terceiro reconhece a posse/dívida dos pallets.

    Relacionamentos:
    - N:1 com PalletCredito (FK credito_id)
    """
    __tablename__ = 'pallet_documentos'

    id = db.Column(db.Integer, primary_key=True)

    # Vínculo com crédito
    credito_id = db.Column(
        db.Integer,
        db.ForeignKey('pallet_creditos.id', ondelete='RESTRICT'),
        nullable=False,
        index=True
    )

    # Tipo do documento
    # CANHOTO = Canhoto da NF assinado
    # VALE_PALLET = Vale emitido pelo cliente
    tipo = db.Column(db.String(20), nullable=False)

    # Dados do documento
    numero_documento = db.Column(db.String(50), nullable=True)  # Número do vale (se aplicável)
    data_emissao = db.Column(db.Date, nullable=True)
    data_validade = db.Column(db.Date, nullable=True)
    quantidade = db.Column(db.Integer, nullable=False)

    # Arquivo anexo (foto/scan do documento)
    arquivo_path = db.Column(db.String(500), nullable=True)
    arquivo_nome = db.Column(db.String(255), nullable=True)
    arquivo_tipo = db.Column(db.String(50), nullable=True)  # MIME type

    # Quem emitiu o documento (cliente ou transportadora)
    cnpj_emissor = db.Column(db.String(20), nullable=True, index=True)
    nome_emissor = db.Column(db.String(255), nullable=True)

    # Status de recebimento pela Nacom
    recebido = db.Column(db.Boolean, default=False, nullable=False)
    recebido_em = db.Column(db.DateTime, nullable=True)
    recebido_por = db.Column(db.String(100), nullable=True)

    # Arquivamento físico (se documento físico)
    pasta_arquivo = db.Column(db.String(100), nullable=True)
    aba_arquivo = db.Column(db.String(50), nullable=True)

    # Referência ao ValePallet original (para migração)
    vale_pallet_id = db.Column(db.Integer, nullable=True)

    # Observações
    observacao = db.Column(db.Text, nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # Soft delete
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    # Índices compostos para otimização de queries
    __table_args__ = (
        db.Index('idx_documento_tipo_recebido', 'tipo', 'recebido'),
        db.Index('idx_documento_validade', 'data_validade'),
        db.Index('idx_documento_emissor', 'cnpj_emissor', 'tipo'),
    )

    def __repr__(self):
        return f"<PalletDocumento #{self.id} - Tipo: {self.tipo} - Qtd: {self.quantidade}>"

    @property
    def dias_para_vencer(self):
        """Calcula quantos dias faltam para o documento vencer"""
        if self.data_validade:
            hoje = datetime.now().date()
            delta = self.data_validade - hoje
            return delta.days
        return None

    @property
    def vencido(self):
        """Verifica se o documento está vencido"""
        dias = self.dias_para_vencer
        return dias is not None and dias < 0

    @property
    def prestes_a_vencer(self):
        """Verifica se o documento está prestes a vencer (menos de 30 dias)"""
        dias = self.dias_para_vencer
        return dias is not None and 0 <= dias <= 30

    @property
    def status_display(self):
        """Retorna o status formatado para exibição"""
        if self.vencido:
            return 'VENCIDO'
        if self.prestes_a_vencer:
            return 'A VENCER'
        if self.recebido:
            return 'RECEBIDO'
        return 'PENDENTE'

    @property
    def tipo_display(self):
        """Retorna o tipo formatado para exibição"""
        tipos = {
            'CANHOTO': 'Canhoto Assinado',
            'VALE_PALLET': 'Vale Pallet'
        }
        return tipos.get(self.tipo, self.tipo)

    def registrar_recebimento(self, usuario: str):
        """
        Registra o recebimento do documento pela Nacom.

        Args:
            usuario: Usuário que registrou o recebimento
        """
        self.recebido = True
        self.recebido_em = agora_utc_naive()
        self.recebido_por = usuario

    def to_dict(self):
        """Serializa o modelo para dicionário"""
        return {
            'id': self.id,
            'credito_id': self.credito_id,
            'tipo': self.tipo,
            'tipo_display': self.tipo_display,
            'numero_documento': self.numero_documento,
            'data_emissao': self.data_emissao.isoformat() if self.data_emissao else None,
            'data_validade': self.data_validade.isoformat() if self.data_validade else None,
            'quantidade': self.quantidade,
            'arquivo_path': self.arquivo_path,
            'arquivo_nome': self.arquivo_nome,
            'cnpj_emissor': self.cnpj_emissor,
            'nome_emissor': self.nome_emissor,
            'recebido': self.recebido,
            'recebido_em': self.recebido_em.isoformat() if self.recebido_em else None,
            'recebido_por': self.recebido_por,
            'pasta_arquivo': self.pasta_arquivo,
            'aba_arquivo': self.aba_arquivo,
            'dias_para_vencer': self.dias_para_vencer,
            'vencido': self.vencido,
            'prestes_a_vencer': self.prestes_a_vencer,
            'status_display': self.status_display,
            'observacao': self.observacao,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por': self.criado_por,
        }

    @classmethod
    def listar_proximos_vencimento(cls, dias: int = 30):
        """
        Lista documentos que vencem nos próximos N dias.

        Args:
            dias: Número de dias para considerar (default: 30)

        Returns:
            Query filtrada por documentos próximos do vencimento
        """
        from datetime import timedelta

        hoje = datetime.now().date()
        limite = hoje + timedelta(days=dias)

        return cls.query.filter(
            cls.data_validade.isnot(None),
            cls.data_validade <= limite,
            cls.data_validade >= hoje,
            cls.ativo == True
        ).order_by(cls.data_validade.asc())

    @classmethod
    def listar_por_credito(cls, credito_id: int):
        """
        Lista todos os documentos de um crédito.

        Args:
            credito_id: ID do crédito

        Returns:
            Query filtrada por crédito
        """
        return cls.query.filter(
            cls.credito_id == credito_id,
            cls.ativo == True
        ).order_by(cls.criado_em.desc())

    @classmethod
    def listar_pendentes_recebimento(cls):
        """
        Lista documentos ainda não recebidos pela Nacom.

        Returns:
            Query de documentos pendentes
        """
        return cls.query.filter(
            cls.recebido == False,
            cls.ativo == True
        ).order_by(cls.data_emissao.asc())

"""
Modelo PalletSolucao - Soluções de Crédito de Pallet

Este modelo representa as diferentes formas de resolver um crédito de pallet:
baixa (descarte), venda, recebimento (coleta) ou substituição de responsabilidade.

Cada solução decrementa o saldo do crédito associado.
Um crédito pode ter múltiplas soluções parciais.

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
from app import db
from app.utils.timezone import agora_brasil


class PalletSolucao(db.Model):
    """
    Registro de resolução de crédito de pallet.

    Tipos de solução (Domínio A):
    - BAIXA: Pallet descartável, cliente não devolverá (confirmado)
    - VENDA: Pallets vendidos (N NFs remessa → 1 NF venda)
    - RECEBIMENTO: Pallets físicos recebidos (coleta)
    - SUBSTITUICAO: Transferência de responsabilidade para outro crédito

    Cada solução decrementa qtd_saldo do PalletCredito associado.

    Relacionamentos:
    - N:1 com PalletCredito (FK credito_id) - crédito sendo resolvido
    - N:1 com PalletCredito (FK credito_destino_id) - para SUBSTITUICAO
    """
    __tablename__ = 'pallet_solucoes'

    id = db.Column(db.Integer, primary_key=True)

    # Vínculo com crédito de origem (sendo resolvido)
    credito_id = db.Column(
        db.Integer,
        db.ForeignKey('pallet_creditos.id', ondelete='RESTRICT'),
        nullable=False,
        index=True
    )

    # Tipo de solução
    # BAIXA = Descarte confirmado com cliente
    # VENDA = Pallets vendidos ao cliente ou terceiro
    # RECEBIMENTO = Pallets físicos recebidos (coleta)
    # SUBSTITUICAO = Transferência de responsabilidade
    tipo = db.Column(db.String(20), nullable=False, index=True)

    # Quantidade resolvida nesta solução
    quantidade = db.Column(db.Integer, nullable=False)

    # ========================================
    # Campos específicos para BAIXA
    # ========================================
    motivo_baixa = db.Column(db.String(100), nullable=True)
    confirmado_cliente = db.Column(db.Boolean, nullable=True)
    data_confirmacao = db.Column(db.Date, nullable=True)

    # ========================================
    # Campos específicos para VENDA
    # ========================================
    nf_venda = db.Column(db.String(20), nullable=True, index=True)
    chave_nfe_venda = db.Column(db.String(44), nullable=True)
    data_venda = db.Column(db.Date, nullable=True)
    valor_unitario = db.Column(db.Numeric(15, 2), nullable=True)
    valor_total = db.Column(db.Numeric(15, 2), nullable=True)
    cnpj_comprador = db.Column(db.String(20), nullable=True)
    nome_comprador = db.Column(db.String(255), nullable=True)

    # ========================================
    # Campos específicos para RECEBIMENTO
    # ========================================
    data_recebimento = db.Column(db.Date, nullable=True)
    local_recebimento = db.Column(db.String(100), nullable=True)
    recebido_de = db.Column(db.String(255), nullable=True)  # Nome de quem entregou
    cnpj_entregador = db.Column(db.String(20), nullable=True)

    # ========================================
    # Campos específicos para SUBSTITUICAO
    # ========================================
    # Crédito de destino (novo responsável)
    credito_destino_id = db.Column(
        db.Integer,
        db.ForeignKey('pallet_creditos.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    # NF da nova remessa (se aplicável)
    nf_destino = db.Column(db.String(20), nullable=True)
    # Motivo da substituição
    motivo_substituicao = db.Column(db.String(255), nullable=True)

    # ========================================
    # Responsável pela solução (genérico)
    # ========================================
    cnpj_responsavel = db.Column(db.String(20), nullable=True)
    nome_responsavel = db.Column(db.String(255), nullable=True)

    # Referência ao ValePallet original (para migração de vales resolvidos)
    vale_pallet_id = db.Column(db.Integer, nullable=True)

    # Observações
    observacao = db.Column(db.Text, nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_brasil)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # Soft delete
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    # Índices compostos para otimização de queries
    __table_args__ = (
        db.Index('idx_solucao_tipo_data', 'tipo', 'criado_em'),
        db.Index('idx_solucao_nf_venda', 'nf_venda'),
        db.Index('idx_solucao_credito_tipo', 'credito_id', 'tipo'),
    )

    def __repr__(self):
        return f"<PalletSolucao #{self.id} - Tipo: {self.tipo} - Qtd: {self.quantidade}>"

    @property
    def tipo_display(self):
        """Retorna o tipo formatado para exibição"""
        tipos = {
            'BAIXA': 'Baixa (Descarte)',
            'VENDA': 'Venda',
            'RECEBIMENTO': 'Recebimento (Coleta)',
            'SUBSTITUICAO': 'Substituição de Responsabilidade'
        }
        return tipos.get(self.tipo, self.tipo)

    @property
    def data_solucao(self):
        """Retorna a data relevante da solução conforme o tipo"""
        if self.tipo == 'BAIXA':
            return self.data_confirmacao
        elif self.tipo == 'VENDA':
            return self.data_venda
        elif self.tipo == 'RECEBIMENTO':
            return self.data_recebimento
        elif self.tipo == 'SUBSTITUICAO':
            return self.criado_em.date() if self.criado_em else None
        return None

    def to_dict(self):
        """Serializa o modelo para dicionário"""
        dados = {
            'id': self.id,
            'credito_id': self.credito_id,
            'tipo': self.tipo,
            'tipo_display': self.tipo_display,
            'quantidade': self.quantidade,
            'cnpj_responsavel': self.cnpj_responsavel,
            'nome_responsavel': self.nome_responsavel,
            'observacao': self.observacao,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por': self.criado_por,
            'data_solucao': self.data_solucao.isoformat() if self.data_solucao else None,
        }

        # Campos específicos por tipo
        if self.tipo == 'BAIXA':
            dados.update({
                'motivo_baixa': self.motivo_baixa,
                'confirmado_cliente': self.confirmado_cliente,
                'data_confirmacao': self.data_confirmacao.isoformat() if self.data_confirmacao else None,
            })
        elif self.tipo == 'VENDA':
            dados.update({
                'nf_venda': self.nf_venda,
                'chave_nfe_venda': self.chave_nfe_venda,
                'data_venda': self.data_venda.isoformat() if self.data_venda else None,
                'valor_unitario': float(self.valor_unitario) if self.valor_unitario else None,
                'valor_total': float(self.valor_total) if self.valor_total else None,
                'cnpj_comprador': self.cnpj_comprador,
                'nome_comprador': self.nome_comprador,
            })
        elif self.tipo == 'RECEBIMENTO':
            dados.update({
                'data_recebimento': self.data_recebimento.isoformat() if self.data_recebimento else None,
                'local_recebimento': self.local_recebimento,
                'recebido_de': self.recebido_de,
                'cnpj_entregador': self.cnpj_entregador,
            })
        elif self.tipo == 'SUBSTITUICAO':
            dados.update({
                'credito_destino_id': self.credito_destino_id,
                'nf_destino': self.nf_destino,
                'motivo_substituicao': self.motivo_substituicao,
            })

        return dados

    @classmethod
    def listar_por_credito(cls, credito_id: int):
        """
        Lista todas as soluções de um crédito.

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
    def listar_por_nf_venda(cls, nf_venda: str):
        """
        Lista soluções vinculadas a uma NF de venda.

        Args:
            nf_venda: Número da NF de venda

        Returns:
            Query filtrada por NF de venda
        """
        return cls.query.filter(
            cls.nf_venda == nf_venda,
            cls.tipo == 'VENDA',
            cls.ativo == True
        ).order_by(cls.criado_em.desc())

    @classmethod
    def total_por_tipo(cls, credito_id: int = None):
        """
        Calcula totais por tipo de solução.

        Args:
            credito_id: ID do crédito (opcional, se None calcula global)

        Returns:
            Dict com totais por tipo
        """
        from sqlalchemy import func

        query = db.session.query(
            cls.tipo,
            func.sum(cls.quantidade).label('total')
        ).filter(cls.ativo == True)

        if credito_id:
            query = query.filter(cls.credito_id == credito_id)

        query = query.group_by(cls.tipo)

        return {row.tipo: row.total for row in query.all()}

    @staticmethod
    def criar_baixa(credito_id: int, quantidade: int, motivo: str,
                    confirmado: bool, usuario: str, observacao: str = None):
        """
        Factory method para criar solução tipo BAIXA.

        Args:
            credito_id: ID do crédito
            quantidade: Quantidade sendo baixada
            motivo: Motivo da baixa
            confirmado: Se cliente confirmou
            usuario: Usuário que registrou
            observacao: Observações adicionais

        Returns:
            PalletSolucao: Nova instância não commitada
        """
        return PalletSolucao(
            credito_id=credito_id,
            tipo='BAIXA',
            quantidade=quantidade,
            motivo_baixa=motivo,
            confirmado_cliente=confirmado,
            data_confirmacao=agora_brasil().date() if confirmado else None,
            criado_por=usuario,
            observacao=observacao
        )

    @staticmethod
    def criar_venda(credito_id: int, quantidade: int, nf_venda: str,
                    data_venda, valor_unitario: float, cnpj_comprador: str,
                    nome_comprador: str, usuario: str, observacao: str = None,
                    chave_nfe: str = None):
        """
        Factory method para criar solução tipo VENDA.

        Args:
            credito_id: ID do crédito
            quantidade: Quantidade vendida
            nf_venda: Número da NF de venda
            data_venda: Data da venda
            valor_unitario: Valor unitário do pallet
            cnpj_comprador: CNPJ do comprador
            nome_comprador: Nome do comprador
            usuario: Usuário que registrou
            observacao: Observações adicionais
            chave_nfe: Chave da NF-e (opcional)

        Returns:
            PalletSolucao: Nova instância não commitada
        """
        valor_total = quantidade * valor_unitario if valor_unitario else None

        return PalletSolucao(
            credito_id=credito_id,
            tipo='VENDA',
            quantidade=quantidade,
            nf_venda=nf_venda,
            chave_nfe_venda=chave_nfe,
            data_venda=data_venda,
            valor_unitario=valor_unitario,
            valor_total=valor_total,
            cnpj_comprador=cnpj_comprador,
            nome_comprador=nome_comprador,
            criado_por=usuario,
            observacao=observacao
        )

    @staticmethod
    def criar_recebimento(credito_id: int, quantidade: int, data_recebimento,
                          local: str, recebido_de: str, cnpj_entregador: str,
                          usuario: str, observacao: str = None):
        """
        Factory method para criar solução tipo RECEBIMENTO.

        Args:
            credito_id: ID do crédito
            quantidade: Quantidade recebida
            data_recebimento: Data do recebimento
            local: Local do recebimento
            recebido_de: Nome de quem entregou
            cnpj_entregador: CNPJ de quem entregou
            usuario: Usuário que registrou
            observacao: Observações adicionais

        Returns:
            PalletSolucao: Nova instância não commitada
        """
        return PalletSolucao(
            credito_id=credito_id,
            tipo='RECEBIMENTO',
            quantidade=quantidade,
            data_recebimento=data_recebimento,
            local_recebimento=local,
            recebido_de=recebido_de,
            cnpj_entregador=cnpj_entregador,
            criado_por=usuario,
            observacao=observacao
        )

    @staticmethod
    def criar_substituicao(credito_id: int, credito_destino_id: int,
                           quantidade: int, nf_destino: str, motivo: str,
                           usuario: str, observacao: str = None):
        """
        Factory method para criar solução tipo SUBSTITUICAO.

        Args:
            credito_id: ID do crédito de origem (sendo resolvido)
            credito_destino_id: ID do crédito de destino (novo responsável)
            quantidade: Quantidade sendo transferida
            nf_destino: NF da nova remessa
            motivo: Motivo da substituição
            usuario: Usuário que registrou
            observacao: Observações adicionais

        Returns:
            PalletSolucao: Nova instância não commitada
        """
        return PalletSolucao(
            credito_id=credito_id,
            credito_destino_id=credito_destino_id,
            tipo='SUBSTITUICAO',
            quantidade=quantidade,
            nf_destino=nf_destino,
            motivo_substituicao=motivo,
            criado_por=usuario,
            observacao=observacao
        )

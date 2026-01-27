"""
Modelo PalletNFSolucao - Soluções Documentais de NF de Remessa

Este modelo representa as soluções documentais para uma NF de remessa de pallet:
devolução, recusa, cancelamento ou nota de crédito. Pertence ao Domínio B (Tratativa das NFs).

Uma NF de remessa pode ter múltiplas soluções documentais até sua quantidade
ser totalmente resolvida.

Tipos de Solução:
- DEVOLUCAO: NF de devolução emitida pelo cliente (1 devolução → N remessas)
- RECUSA: NF recusada pelo cliente (sem emissão de NF, registro manual interno)
- CANCELAMENTO: NF foi cancelada (importado automaticamente do Odoo)
- NOTA_CREDITO: NC emitida vinculada à NF original (vinculação automática via reversed_entry_id)

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
from app import db
from app.utils.timezone import agora_brasil


class PalletNFSolucao(db.Model):
    """
    Solução documental de NF de remessa.

    Define como a NF de remessa foi "fechada" fiscalmente:
    - DEVOLUCAO: NF de devolução emitida pelo cliente (1 devolução → N remessas)
    - RECUSA: NF recusada pelo cliente (sem NF, registro manual interno)
    - CANCELAMENTO: NF foi cancelada (importado automaticamente do Odoo)
    - NOTA_CREDITO: NC emitida vinculada à NF original (automático via reversed_entry_id)

    Vinculação pode ser:
    - AUTOMATICO: Sistema encontrou match automático (NC via reversed_entry_id, canceladas)
    - MANUAL: Usuário vinculou manualmente (devolução, recusa)
    - SUGESTAO: Sistema sugeriu, aguarda confirmação do usuário

    Relacionamentos:
    - N:1 com PalletNFRemessa (FK nf_remessa_id)
    """
    __tablename__ = 'pallet_nf_solucoes'

    id = db.Column(db.Integer, primary_key=True)

    # Vínculo com NF de remessa
    nf_remessa_id = db.Column(
        db.Integer,
        db.ForeignKey('pallet_nf_remessa.id', ondelete='RESTRICT'),
        nullable=False,
        index=True
    )

    # Tipo de solução
    # DEVOLUCAO = NF de devolução do cliente
    # RECUSA = NF recusada pelo cliente (sem NF, registro manual)
    # CANCELAMENTO = NF foi cancelada (importado do Odoo)
    # NOTA_CREDITO = NC emitida vinculada (automático via reversed_entry_id)
    tipo = db.Column(db.String(20), nullable=False, index=True)

    # Quantidade resolvida nesta solução
    quantidade = db.Column(db.Integer, nullable=False)

    # Dados da NF de devolução/retorno (quando aplicável)
    numero_nf_solucao = db.Column(db.String(20), nullable=True, index=True)
    serie_nf_solucao = db.Column(db.String(5), nullable=True)
    chave_nfe_solucao = db.Column(db.String(44), nullable=True, unique=True)
    data_nf_solucao = db.Column(db.DateTime, nullable=True)

    # Dados do Odoo (se sincronizado)
    odoo_account_move_id = db.Column(db.Integer, nullable=True)
    odoo_dfe_id = db.Column(db.Integer, nullable=True)

    # Emitente da NF de solução
    cnpj_emitente = db.Column(db.String(20), nullable=True, index=True)
    nome_emitente = db.Column(db.String(255), nullable=True)

    # Status de vinculação
    # AUTOMATICO = Sistema encontrou match (chave/CNPJ/info complementar)
    # MANUAL = Usuário vinculou manualmente
    # SUGESTAO = Sistema sugeriu, aguarda confirmação
    vinculacao = db.Column(db.String(20), default='MANUAL', nullable=False)

    # Score de match para sugestões (0-100)
    score_match = db.Column(db.Integer, nullable=True)

    # Confirmação (para SUGESTAO)
    confirmado = db.Column(db.Boolean, default=True, nullable=False)
    confirmado_em = db.Column(db.DateTime, nullable=True)
    confirmado_por = db.Column(db.String(100), nullable=True)

    # Rejeição (para SUGESTAO rejeitada)
    rejeitado = db.Column(db.Boolean, default=False, nullable=False)
    rejeitado_em = db.Column(db.DateTime, nullable=True)
    rejeitado_por = db.Column(db.String(100), nullable=True)
    motivo_rejeicao = db.Column(db.String(255), nullable=True)

    # Informações complementares (para RECUSA ou detalhes adicionais)
    info_complementar = db.Column(db.Text, nullable=True)

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
        db.Index('idx_nf_solucao_tipo_vinculacao', 'tipo', 'vinculacao'),
        db.Index('idx_nf_solucao_confirmado', 'confirmado', 'vinculacao'),
        db.Index('idx_nf_solucao_emitente', 'cnpj_emitente', 'tipo'),
    )

    def __repr__(self):
        return f"<PalletNFSolucao #{self.id} - Tipo: {self.tipo} - NF: {self.numero_nf_solucao}>"

    @property
    def tipo_display(self):
        """Retorna o tipo formatado para exibição"""
        tipos = {
            'DEVOLUCAO': 'Devolução',
            'RECUSA': 'Recusa',
            'CANCELAMENTO': 'Cancelamento',
            'NOTA_CREDITO': 'Nota de Crédito'
        }
        return tipos.get(self.tipo, self.tipo)

    @property
    def vinculacao_display(self):
        """Retorna o tipo de vinculação formatado para exibição"""
        vinculacoes = {
            'AUTOMATICO': 'Automático',
            'MANUAL': 'Manual',
            'SUGESTAO': 'Sugestão'
        }
        return vinculacoes.get(self.vinculacao, self.vinculacao)

    @property
    def status_display(self):
        """Retorna o status da solução para exibição"""
        if self.rejeitado:
            return 'REJEITADA'
        if self.confirmado:
            return 'CONFIRMADA'
        if self.vinculacao == 'SUGESTAO':
            return 'AGUARDANDO'
        return 'ATIVA'

    @property
    def pendente_confirmacao(self):
        """Verifica se a solução está pendente de confirmação"""
        return self.vinculacao == 'SUGESTAO' and not self.confirmado and not self.rejeitado

    def confirmar(self, usuario: str):
        """
        Confirma uma sugestão de vinculação.

        Args:
            usuario: Usuário que confirmou
        """
        self.confirmado = True
        self.confirmado_em = agora_brasil()
        self.confirmado_por = usuario

    def rejeitar(self, usuario: str, motivo: str):
        """
        Rejeita uma sugestão de vinculação.

        Args:
            usuario: Usuário que rejeitou
            motivo: Motivo da rejeição
        """
        self.rejeitado = True
        self.rejeitado_em = agora_brasil()
        self.rejeitado_por = usuario
        self.motivo_rejeicao = motivo

    def to_dict(self):
        """Serializa o modelo para dicionário"""
        return {
            'id': self.id,
            'nf_remessa_id': self.nf_remessa_id,
            'tipo': self.tipo,
            'tipo_display': self.tipo_display,
            'quantidade': self.quantidade,
            'numero_nf_solucao': self.numero_nf_solucao,
            'serie_nf_solucao': self.serie_nf_solucao,
            'chave_nfe_solucao': self.chave_nfe_solucao,
            'data_nf_solucao': self.data_nf_solucao.isoformat() if self.data_nf_solucao else None,
            'cnpj_emitente': self.cnpj_emitente,
            'nome_emitente': self.nome_emitente,
            'vinculacao': self.vinculacao,
            'vinculacao_display': self.vinculacao_display,
            'score_match': self.score_match,
            'status_display': self.status_display,
            'confirmado': self.confirmado,
            'confirmado_em': self.confirmado_em.isoformat() if self.confirmado_em else None,
            'confirmado_por': self.confirmado_por,
            'rejeitado': self.rejeitado,
            'rejeitado_em': self.rejeitado_em.isoformat() if self.rejeitado_em else None,
            'motivo_rejeicao': self.motivo_rejeicao,
            'info_complementar': self.info_complementar,
            'observacao': self.observacao,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por': self.criado_por,
        }

    @classmethod
    def listar_por_nf_remessa(cls, nf_remessa_id: int, apenas_confirmadas: bool = True):
        """
        Lista soluções de uma NF de remessa.

        Args:
            nf_remessa_id: ID da NF de remessa
            apenas_confirmadas: Se True, exclui sugestões rejeitadas

        Returns:
            Query filtrada
        """
        query = cls.query.filter(
            cls.nf_remessa_id == nf_remessa_id,
            cls.ativo == True
        )

        if apenas_confirmadas:
            query = query.filter(cls.rejeitado == False)

        return query.order_by(cls.criado_em.desc())

    @classmethod
    def listar_sugestoes_pendentes(cls):
        """
        Lista todas as sugestões aguardando confirmação.

        Returns:
            Query de sugestões pendentes
        """
        return cls.query.filter(
            cls.vinculacao == 'SUGESTAO',
            cls.confirmado == False,
            cls.rejeitado == False,
            cls.ativo == True
        ).order_by(cls.criado_em.asc())

    @classmethod
    def buscar_por_chave_nfe(cls, chave_nfe: str):
        """
        Busca solução por chave da NF-e.

        Args:
            chave_nfe: Chave da NF-e de solução

        Returns:
            PalletNFSolucao ou None
        """
        return cls.query.filter(
            cls.chave_nfe_solucao == chave_nfe,
            cls.ativo == True
        ).first()

    @classmethod
    def verificar_duplicidade(cls, numero_nf: str, cnpj_emitente: str, nf_remessa_id: int):
        """
        Verifica se já existe solução para a mesma NF e emitente.

        Args:
            numero_nf: Número da NF de solução
            cnpj_emitente: CNPJ do emitente
            nf_remessa_id: ID da NF de remessa

        Returns:
            bool: True se já existe
        """
        existente = cls.query.filter(
            cls.numero_nf_solucao == numero_nf,
            cls.cnpj_emitente == cnpj_emitente,
            cls.nf_remessa_id == nf_remessa_id,
            cls.rejeitado == False,
            cls.ativo == True
        ).first()

        return existente is not None

    @staticmethod
    def criar_devolucao(nf_remessa_id: int, quantidade: int, numero_nf: str,
                        data_nf, cnpj_emitente: str, nome_emitente: str,
                        usuario: str, vinculacao: str = 'MANUAL',
                        chave_nfe: str = None, serie: str = None,
                        observacao: str = None):
        """
        Factory method para criar solução tipo DEVOLUCAO.

        Args:
            nf_remessa_id: ID da NF de remessa
            quantidade: Quantidade devolvida
            numero_nf: Número da NF de devolução
            data_nf: Data da NF
            cnpj_emitente: CNPJ do emitente
            nome_emitente: Nome do emitente
            usuario: Usuário que registrou
            vinculacao: Tipo de vinculação
            chave_nfe: Chave da NF-e (opcional)
            serie: Série da NF (opcional)
            observacao: Observações (opcional)

        Returns:
            PalletNFSolucao: Nova instância não commitada
        """
        return PalletNFSolucao(
            nf_remessa_id=nf_remessa_id,
            tipo='DEVOLUCAO',
            quantidade=quantidade,
            numero_nf_solucao=numero_nf,
            serie_nf_solucao=serie,
            chave_nfe_solucao=chave_nfe,
            data_nf_solucao=data_nf,
            cnpj_emitente=cnpj_emitente,
            nome_emitente=nome_emitente,
            vinculacao=vinculacao,
            confirmado=(vinculacao != 'SUGESTAO'),
            criado_por=usuario,
            observacao=observacao
        )

    @staticmethod
    def criar_recusa(nf_remessa_id: int, quantidade: int,
                     usuario: str, motivo_recusa: str = None,
                     observacao: str = None):
        """
        Factory method para criar solução tipo RECUSA.

        RECUSA é quando o cliente recusa a NF de remessa sem emitir NF de retorno.
        É um registro manual interno para controle, sem documento fiscal associado.

        Args:
            nf_remessa_id: ID da NF de remessa recusada
            quantidade: Quantidade recusada
            usuario: Usuário que registrou
            motivo_recusa: Motivo da recusa (obrigatório)
            observacao: Observações adicionais (opcional)

        Returns:
            PalletNFSolucao: Nova instância não commitada
        """
        return PalletNFSolucao(
            nf_remessa_id=nf_remessa_id,
            tipo='RECUSA',
            quantidade=quantidade,
            vinculacao='MANUAL',
            info_complementar=motivo_recusa,
            confirmado=True,
            criado_por=usuario,
            observacao=observacao
        )

    @staticmethod
    def criar_cancelamento(nf_remessa_id: int, quantidade: int,
                           usuario: str, observacao: str = None):
        """
        Factory method para criar solução tipo CANCELAMENTO.

        CANCELAMENTO é importado automaticamente do Odoo (state='cancel').
        O usuário pode adicionar motivo/observação posteriormente.

        Args:
            nf_remessa_id: ID da NF de remessa
            quantidade: Quantidade cancelada
            usuario: Usuário que registrou
            observacao: Observações (opcional)

        Returns:
            PalletNFSolucao: Nova instância não commitada
        """
        return PalletNFSolucao(
            nf_remessa_id=nf_remessa_id,
            tipo='CANCELAMENTO',
            quantidade=quantidade,
            vinculacao='AUTOMATICO',  # Importado do Odoo
            confirmado=True,
            criado_por=usuario,
            observacao=observacao
        )

    @staticmethod
    def criar_nota_credito(nf_remessa_id: int, quantidade: int, numero_nf: str,
                           data_nf, cnpj_destinatario: str, nome_destinatario: str,
                           odoo_account_move_id: int, usuario: str = 'SCHEDULER',
                           chave_nfe: str = None, observacao: str = None):
        """
        Factory method para criar solução tipo NOTA_CREDITO.

        NOTA_CREDITO é vinculada automaticamente via reversed_entry_id do Odoo.
        O campo reversed_entry_id aponta para a NF de remessa original.

        Args:
            nf_remessa_id: ID da NF de remessa local
            quantidade: Quantidade da NC
            numero_nf: Número da NC
            data_nf: Data da NC
            cnpj_destinatario: CNPJ do destinatário da NC (emitente original)
            nome_destinatario: Nome do destinatário
            odoo_account_move_id: ID da NC no Odoo
            usuario: Usuário que registrou (default: SCHEDULER)
            chave_nfe: Chave da NF-e (opcional)
            observacao: Observações (opcional)

        Returns:
            PalletNFSolucao: Nova instância não commitada
        """
        return PalletNFSolucao(
            nf_remessa_id=nf_remessa_id,
            tipo='NOTA_CREDITO',
            quantidade=quantidade,
            numero_nf_solucao=numero_nf,
            chave_nfe_solucao=chave_nfe,
            data_nf_solucao=data_nf,
            odoo_account_move_id=odoo_account_move_id,
            cnpj_emitente=cnpj_destinatario,
            nome_emitente=nome_destinatario,
            vinculacao='AUTOMATICO',  # Vinculado via reversed_entry_id
            confirmado=True,
            criado_por=usuario,
            observacao=observacao
        )

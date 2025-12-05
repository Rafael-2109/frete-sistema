"""
Modelo para registro de pedidos inseridos no Odoo via importação de PDF
"""

from datetime import datetime
from app import db


class RegistroPedidoOdoo(db.Model):
    """
    Registro de pedidos inseridos no Odoo através do importador de PDFs

    Armazena:
    - Dados do documento original (PDF)
    - Resultado da inserção no Odoo
    - Informações de divergência de preços
    - Auditoria (quem inseriu/aprovou)
    """
    __tablename__ = 'registro_pedido_odoo'

    id = db.Column(db.Integer, primary_key=True)

    # ========== Origem do documento ==========
    rede = db.Column(db.String(50), nullable=False, index=True)  # 'ATACADAO', 'TENDA', 'ASSAI'
    tipo_documento = db.Column(db.String(50), nullable=False)  # 'PROPOSTA', 'PEDIDO'
    numero_documento = db.Column(db.String(100), nullable=True)  # Número da proposta/pedido
    arquivo_pdf_s3 = db.Column(db.String(500), nullable=True)  # URL do arquivo no S3

    # ========== Cliente ==========
    cnpj_cliente = db.Column(db.String(20), nullable=False, index=True)
    nome_cliente = db.Column(db.String(255), nullable=True)
    uf_cliente = db.Column(db.String(2), nullable=True)
    cep_cliente = db.Column(db.String(10), nullable=True)
    endereco_cliente = db.Column(db.String(500), nullable=True)

    # ========== Resultado Odoo ==========
    odoo_order_id = db.Column(db.Integer, nullable=True)  # ID do sale.order no Odoo
    odoo_order_name = db.Column(db.String(50), nullable=True)  # Número do pedido (VCD...)
    status_odoo = db.Column(db.String(50), nullable=False, default='PENDENTE')  # 'SUCESSO', 'ERRO', 'PENDENTE'
    mensagem_erro = db.Column(db.Text, nullable=True)

    # ========== Dados do documento (JSON) ==========
    # Armazena todos os itens extraídos do PDF
    # Formato: [{"codigo": "35642", "descricao": "...", "qtd": 15, "preco": 199.48, ...}, ...]
    dados_documento = db.Column(db.JSON, nullable=True)

    # ========== Validação de preços ==========
    divergente = db.Column(db.Boolean, default=False, nullable=False)
    # Detalhes das divergências:
    # [{"codigo": "35642", "preco_doc": 199.48, "preco_tabela": 195.00, "diferenca": 4.48}, ...]
    divergencias = db.Column(db.JSON, nullable=True)
    justificativa_aprovacao = db.Column(db.Text, nullable=True)  # Obrigatório se divergente

    # ========== Auditoria ==========
    inserido_por = db.Column(db.String(100), nullable=False)
    aprovado_por = db.Column(db.String(100), nullable=True)  # Quem aprovou divergência
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    processado_em = db.Column(db.DateTime, nullable=True)  # Quando foi enviado ao Odoo

    # ========== Constraints ==========
    __table_args__ = (
        db.Index('idx_registro_rede_cnpj', 'rede', 'cnpj_cliente'),
        db.Index('idx_registro_odoo_order', 'odoo_order_id'),
        db.Index('idx_registro_status', 'status_odoo'),
        db.Index('idx_registro_criado_em', 'criado_em'),
    )

    def __repr__(self):
        return f'<RegistroPedidoOdoo {self.id} {self.rede}/{self.numero_documento} → {self.status_odoo}>'

    @property
    def total_itens(self):
        """Retorna o total de itens no documento"""
        if self.dados_documento:
            return len(self.dados_documento)
        return 0

    @property
    def total_divergencias(self):
        """Retorna o total de divergências de preço"""
        if self.divergencias:
            return len(self.divergencias)
        return 0

    @property
    def valor_total_documento(self):
        """Calcula o valor total do documento"""
        if not self.dados_documento:
            return 0

        total = 0
        for item in self.dados_documento:
            qtd = item.get('quantidade', 0) or item.get('qtd', 0) or 0
            preco = item.get('valor_unitario', 0) or item.get('preco', 0) or 0
            total += float(qtd) * float(preco)
        return round(total, 2)

    def marcar_sucesso(self, odoo_order_id: int, odoo_order_name: str):
        """Marca o registro como sucesso após inserção no Odoo"""
        self.status_odoo = 'SUCESSO'
        self.odoo_order_id = odoo_order_id
        self.odoo_order_name = odoo_order_name
        self.processado_em = datetime.utcnow()
        self.mensagem_erro = None

    def marcar_erro(self, mensagem: str):
        """Marca o registro como erro"""
        self.status_odoo = 'ERRO'
        self.processado_em = datetime.utcnow()
        self.mensagem_erro = mensagem

    def aprovar_divergencia(self, usuario: str, justificativa: str):
        """
        Aprova as divergências de preço

        Args:
            usuario: Nome/email do usuário que aprovou
            justificativa: Texto explicando o motivo da aprovação
        """
        self.aprovado_por = usuario
        self.justificativa_aprovacao = justificativa

    @classmethod
    def buscar_por_documento(cls, rede: str, numero_documento: str):
        """
        Busca registros por rede e número do documento

        Args:
            rede: Nome da rede
            numero_documento: Número da proposta/pedido

        Returns:
            Lista de RegistroPedidoOdoo
        """
        return cls.query.filter_by(
            rede=rede.upper(),
            numero_documento=numero_documento
        ).all()

    @classmethod
    def verificar_duplicidade(cls, rede: str, numero_documento: str, cnpj_cliente: str):
        """
        Verifica se já existe um registro com sucesso para este documento/CNPJ

        Args:
            rede: Nome da rede
            numero_documento: Número da proposta/pedido
            cnpj_cliente: CNPJ do cliente

        Returns:
            RegistroPedidoOdoo ou None
        """
        return cls.query.filter_by(
            rede=rede.upper(),
            numero_documento=numero_documento,
            cnpj_cliente=cnpj_cliente,
            status_odoo='SUCESSO'
        ).first()

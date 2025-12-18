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


class PedidoImportacaoTemp(db.Model):
    """
    Armazenamento temporário de pedidos importados de PDF para lançamento no Odoo.

    Substitui o uso de session para evitar perda de dados durante operações longas.
    Os dados são mantidos até o lançamento ser concluído ou expirar (24h).

    Fluxo:
    1. Upload PDF → Cria registro com status 'PROCESSADO'
    2. Edição de preços → Atualiza dados_itens
    3. Lançamento → Marca como 'LANCADO' ou 'ERRO'
    4. Cleanup automático de registros > 24h
    """
    __tablename__ = 'pedido_importacao_temp'

    id = db.Column(db.Integer, primary_key=True)

    # ========== Chave de identificação ==========
    # Chave única gerada no upload (substitui session_key)
    chave_importacao = db.Column(db.String(100), unique=True, nullable=False, index=True)

    # ========== Status ==========
    # PROCESSADO: PDF processado, aguardando lançamento
    # LANCANDO: Em processo de lançamento no Odoo
    # LANCADO: Lançamento concluído com sucesso
    # ERRO: Erro no lançamento
    # EXPIRADO: Registro expirado (cleanup)
    status = db.Column(db.String(20), default='PROCESSADO', nullable=False, index=True)

    # ========== Origem do documento ==========
    rede = db.Column(db.String(50), nullable=False)  # 'ATACADAO', 'TENDA', 'ASSAI'
    tipo_documento = db.Column(db.String(50), nullable=False)  # 'PROPOSTA', 'PEDIDO'
    numero_documento = db.Column(db.String(100), nullable=True)  # Número da proposta
    numero_pedido_cliente = db.Column(db.String(100), nullable=True)  # Número do pedido do cliente (Numero:)
    arquivo_pdf_s3 = db.Column(db.String(500), nullable=True)  # URL do arquivo no S3
    filename_original = db.Column(db.String(255), nullable=True)  # Nome original do arquivo

    # ========== Dados completos (JSON) ==========
    # Dados brutos extraídos do PDF
    dados_brutos = db.Column(db.JSON, nullable=True)

    # Identificação do documento
    identificacao = db.Column(db.JSON, nullable=True)

    # Resumo agregado (total_itens, total_filiais, valor_total, etc)
    summary = db.Column(db.JSON, nullable=True)

    # Validação de preços (por_filial com divergências)
    validacao_precos = db.Column(db.JSON, nullable=True)

    # Lista de itens sem De-Para
    itens_sem_depara = db.Column(db.JSON, nullable=True)

    # ========== Dados por filial (JSON) ==========
    # Lista de filiais com seus itens e preços (editáveis)
    # Formato: [
    #   {
    #     "cnpj": "93.209.765/0599-44",
    #     "nome_cliente": "ATACADAO SA",
    #     "uf": "SP",
    #     "municipio": "SAO JOSE DO RIO PRETO",
    #     "numero_pedido_cliente": "111988186",  # Número: do PDF
    #     "tem_divergencia": true,
    #     "justificativa": "Aprovado pelo comercial",
    #     "itens": [
    #       {
    #         "codigo_rede": "35642",
    #         "nosso_codigo": "35642",
    #         "descricao": "AZEITONA...",
    #         "quantidade": 15,
    #         "preco_documento": 199.48,
    #         "preco_tabela": 195.00,
    #         "preco_final": 199.48,  # Editável - usado no lançamento
    #         "divergente": true
    #       }, ...
    #     ]
    #   }, ...
    # ]
    dados_filiais = db.Column(db.JSON, nullable=True)

    # ========== Justificativa global ==========
    # Justificativa que pode ser aplicada a todas as filiais com divergência
    justificativa_global = db.Column(db.Text, nullable=True)

    # ========== Flags ==========
    tem_divergencia = db.Column(db.Boolean, default=False, nullable=False)
    pode_inserir = db.Column(db.Boolean, default=False, nullable=False)  # Sem itens sem De-Para

    # ========== Auditoria ==========
    usuario = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expira_em = db.Column(db.DateTime, nullable=True)  # Para cleanup automático

    # ========== Resultado do lançamento ==========
    # Lista de resultados por filial após lançamento
    # [{"cnpj": "...", "sucesso": true, "order_id": 123, "order_name": "VCD001"}, ...]
    resultados_lancamento = db.Column(db.JSON, nullable=True)

    # ========== Constraints ==========
    __table_args__ = (
        db.Index('idx_importacao_temp_status', 'status'),
        db.Index('idx_importacao_temp_criado', 'criado_em'),
        db.Index('idx_importacao_temp_expira', 'expira_em'),
    )

    def __repr__(self):
        return f'<PedidoImportacaoTemp {self.chave_importacao} {self.rede}/{self.status}>'

    @classmethod
    def criar_do_upload(cls, dados: dict, usuario: str) -> 'PedidoImportacaoTemp':
        """
        Cria registro a partir dos dados do upload processado.

        Args:
            dados: Dict com dados do processamento (summary, identificacao, validacao_precos, etc)
            usuario: Nome/email do usuário

        Returns:
            PedidoImportacaoTemp criado (não commitado)
        """
        from datetime import timedelta
        import uuid

        # Gera chave única
        chave = f"imp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Extrai identificação
        identificacao = dados.get('identificacao', {})
        summary = dados.get('summary', {})
        validacao_precos = dados.get('validacao_precos', {})

        # Extrai numero_pedido_cliente (Numero:) dos dados brutos
        numero_pedido_cliente = None
        dados_brutos = dados.get('data', [])
        if dados_brutos and len(dados_brutos) > 0:
            # Pega do primeiro item (todos da mesma filial têm o mesmo)
            numero_pedido_cliente = dados_brutos[0].get('numero_comprador') or dados_brutos[0].get('numero_pedido')

        # Prepara dados_filiais com estrutura para edição
        dados_filiais = []
        if summary.get('por_filial'):
            for filial in summary['por_filial']:
                cnpj = filial.get('cnpj')

                # Busca validação desta filial
                tem_divergencia_filial = False
                validacoes_filial = []
                if validacao_precos and validacao_precos.get('por_filial'):
                    for val in validacao_precos['por_filial']:
                        if val.get('cnpj') == cnpj:
                            tem_divergencia_filial = val.get('tem_divergencia', False)
                            validacoes_filial = val.get('validacoes', [])
                            break

                # Busca numero_pedido_cliente específico desta filial
                numero_pedido_filial = numero_pedido_cliente
                for item in dados_brutos:
                    if item.get('cnpj_filial') == cnpj:
                        numero_pedido_filial = item.get('numero_comprador') or item.get('numero_pedido') or numero_pedido_cliente
                        break

                # Prepara itens com preço editável
                itens = []
                for produto in filial.get('produtos', []):
                    # Busca validação do produto
                    validacao_prod = None
                    for v in validacoes_filial:
                        if v.get('codigo') == produto.get('nosso_codigo'):
                            validacao_prod = v
                            break

                    itens.append({
                        'codigo_rede': produto.get('codigo'),
                        'nosso_codigo': produto.get('nosso_codigo'),
                        'descricao': produto.get('descricao'),
                        'nossa_descricao': produto.get('nossa_descricao'),
                        'quantidade': produto.get('quantidade', 0),
                        'preco_documento': produto.get('valor_unitario', 0),
                        'preco_tabela': validacao_prod.get('preco_tabela') if validacao_prod else None,
                        'preco_final': produto.get('valor_unitario', 0),  # Inicialmente = documento
                        'divergente': validacao_prod.get('divergente', False) if validacao_prod else False,
                        'diferenca_percentual': validacao_prod.get('diferenca_percentual', 0) if validacao_prod else 0
                    })

                dados_filiais.append({
                    'cnpj': cnpj,
                    'nome_cliente': filial.get('nome_cliente'),
                    'uf': filial.get('estado'),
                    'municipio': filial.get('municipio'),
                    'local_entrega': filial.get('local'),
                    'numero_pedido_cliente': numero_pedido_filial,
                    'tem_divergencia': tem_divergencia_filial,
                    'justificativa': None,
                    'itens': itens,
                    'valor_total': filial.get('valor', 0),
                    'quantidade_total': filial.get('quantidade', 0)
                })

        registro = cls(
            chave_importacao=chave,
            status='PROCESSADO',
            rede=identificacao.get('rede', 'DESCONHECIDA'),
            tipo_documento=identificacao.get('tipo', 'DESCONHECIDO'),
            numero_documento=identificacao.get('numero_documento'),
            numero_pedido_cliente=numero_pedido_cliente,
            arquivo_pdf_s3=dados.get('s3_path'),
            filename_original=dados.get('filename'),
            dados_brutos=dados_brutos,
            identificacao=identificacao,
            summary=summary,
            validacao_precos=validacao_precos,
            itens_sem_depara=dados.get('itens_sem_depara', []),
            dados_filiais=dados_filiais,
            tem_divergencia=dados.get('tem_divergencia', False),
            pode_inserir=dados.get('pode_inserir', False),
            usuario=usuario,
            expira_em=datetime.utcnow() + timedelta(hours=24)
        )

        return registro

    def atualizar_preco_item(self, cnpj: str, codigo_rede: str, novo_preco: float) -> bool:
        """
        Atualiza o preço final de um item específico.

        Args:
            cnpj: CNPJ da filial
            codigo_rede: Código do produto na rede
            novo_preco: Novo preço a ser usado

        Returns:
            True se atualizado, False se não encontrado
        """
        if not self.dados_filiais:
            return False

        for filial in self.dados_filiais:
            if filial.get('cnpj') == cnpj:
                for item in filial.get('itens', []):
                    if item.get('codigo_rede') == codigo_rede:
                        item['preco_final'] = novo_preco
                        # Recalcula valor total da filial
                        total = sum(
                            i.get('quantidade', 0) * i.get('preco_final', 0)
                            for i in filial.get('itens', [])
                        )
                        filial['valor_total'] = round(total, 2)
                        return True
        return False

    def atualizar_justificativa_filial(self, cnpj: str, justificativa: str) -> bool:
        """
        Atualiza a justificativa de uma filial específica.

        Args:
            cnpj: CNPJ da filial
            justificativa: Texto da justificativa

        Returns:
            True se atualizado, False se não encontrado
        """
        if not self.dados_filiais:
            return False

        for filial in self.dados_filiais:
            if filial.get('cnpj') == cnpj:
                filial['justificativa'] = justificativa
                return True
        return False

    def aplicar_justificativa_global(self, justificativa: str):
        """
        Aplica justificativa global a todas as filiais com divergência.

        Args:
            justificativa: Texto da justificativa
        """
        self.justificativa_global = justificativa

        if self.dados_filiais:
            for filial in self.dados_filiais:
                if filial.get('tem_divergencia'):
                    filial['justificativa'] = justificativa

    def obter_filial(self, cnpj: str) -> dict:
        """Retorna dados de uma filial específica"""
        if not self.dados_filiais:
            return None

        for filial in self.dados_filiais:
            if filial.get('cnpj') == cnpj:
                return filial
        return None

    def obter_filiais_divergentes(self) -> list:
        """Retorna lista de filiais com divergência de preço"""
        if not self.dados_filiais:
            return []

        return [f for f in self.dados_filiais if f.get('tem_divergencia')]

    def obter_itens_divergentes_agregados(self) -> list:
        """
        Retorna lista agregada de itens divergentes para exibição no topo.

        Returns:
            Lista no formato:
            [
                {
                    "cnpj": "93.209.765/0599-44",
                    "nome_cliente": "ATACADAO SA",
                    "uf": "SP",
                    "itens_divergentes": [
                        {"codigo_rede": "35642", "nosso_codigo": "35642", ...}
                    ]
                }
            ]
        """
        resultado = []

        if not self.dados_filiais:
            return resultado

        for filial in self.dados_filiais:
            if filial.get('tem_divergencia'):
                itens_div = [i for i in filial.get('itens', []) if i.get('divergente')]
                if itens_div:
                    resultado.append({
                        'cnpj': filial.get('cnpj'),
                        'nome_cliente': filial.get('nome_cliente'),
                        'uf': filial.get('uf'),
                        'municipio': filial.get('municipio'),
                        'itens_divergentes': itens_div
                    })

        return resultado

    def marcar_lancando(self):
        """Marca como em processo de lançamento"""
        self.status = 'LANCANDO'

    def marcar_lancado(self, resultados: list):
        """Marca como lançado com sucesso"""
        self.status = 'LANCADO'
        self.resultados_lancamento = resultados

    def marcar_erro(self, resultados: list = None):
        """Marca como erro no lançamento"""
        self.status = 'ERRO'
        if resultados:
            self.resultados_lancamento = resultados

    @classmethod
    def buscar_por_chave(cls, chave: str) -> 'PedidoImportacaoTemp':
        """Busca registro pela chave de importação"""
        return cls.query.filter_by(chave_importacao=chave).first()

    @classmethod
    def limpar_expirados(cls) -> int:
        """
        Remove registros expirados.

        Returns:
            Número de registros removidos
        """
        expirados = cls.query.filter(
            cls.expira_em < datetime.utcnow(),
            cls.status.in_(['PROCESSADO', 'ERRO'])  # Não remove LANCADO
        ).all()

        count = len(expirados)
        for reg in expirados:
            db.session.delete(reg)

        return count

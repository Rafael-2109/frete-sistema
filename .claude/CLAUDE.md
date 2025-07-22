    # CLAUDE.md - Referência de Modelos e Campos

## ⚠️ ATENÇÃO: Use SEMPRE os nomes EXATOS dos campos listados aqui

Este arquivo contém os nomes corretos dos campos de todos os modelos para evitar erros como `data_expedicao_pedido` (❌ INCORRETO) em vez de `expedicao` (✅ CORRETO).

---

## PreSeparacaoItem - Sistema de Pré-separação

**Propósito**: Modelo para sistema de pré-separação que SOBREVIVE à reimportação do Odoo

**FUNCIONALIDADE CRÍTICA**: 
- Quando Odoo reimporta e SUBSTITUI a carteira_principal
- Este modelo preserva as decisões dos usuários e permite "recompor" as divisões

**FLUXO DE RECOMPOSIÇÃO**:
1. Usuário faz pré-separação (divisão parcial)
2. Sistema salva dados com chave de negócio estável  
3. Odoo reimporta → carteira_principal é substituída
4. Sistema detecta pré-separações não recompostas
5. Aplica novamente as divisões na nova carteira
6. Preserva dados editáveis (datas, protocolos, etc.)

```python
class PreSeparacaoItem(db.Model):
    
    __tablename__ = 'pre_separacao_item'
    
    # Campos principais
    id = db.Column(db.Integer, primary_key=True)
    num_pedido = db.Column(db.String(50), nullable=False, index=True)
    cod_produto = db.Column(db.String(50), nullable=False, index=True) 
    cnpj_cliente = db.Column(db.String(20), index=True)
    
    #  DADOS ORIGINAIS (momento da pré-separação)
    nome_produto = db.Column(db.String(255), nullable=True)
    qtd_original_carteira = db.Column(db.Numeric(15, 3), nullable=False)  # Qtd total no momento
    qtd_selecionada_usuario = db.Column(db.Numeric(15, 3), nullable=False)  # Qtd escolhida
    qtd_restante_calculada = db.Column(db.Numeric(15, 3), nullable=False)  # Saldo restante
    
    # Dados originais preservados (sobrevivência à reimportação)
    valor_original_item = db.Column(db.Numeric(15,2))
    peso_original_item = db.Column(db.Numeric(15,3))
    hash_item_original = db.Column(db.String(128))
    
    # Trabalho do usuário preservado
    data_expedicao_editada = db.Column(db.Date, nullable=False)  # ✅ OBRIGATÓRIO para constraint única
    data_agendamento_editada = db.Column(db.Date)
    protocolo_editado = db.Column(db.String(50))
    observacoes_usuario = db.Column(db.Text)
    
    # Controle de recomposição (sobrevivência ao Odoo)
    recomposto = db.Column(db.Boolean, default=False, index=True)
    data_recomposicao = db.Column(db.DateTime)
    recomposto_por = db.Column(db.String(100))
    versao_carteira_original = db.Column(db.String(50))
    versao_carteira_recomposta = db.Column(db.String(50))
    
    # Status e tipo
    status = db.Column(db.String(20), default='CRIADO', index=True)  # CRIADO, RECOMPOSTO, ENVIADO_SEPARACAO
    tipo_envio = db.Column(db.String(10), default='total')  # total, parcial
    
    # Auditoria
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    
    # ✅ CONSTRAINT ÚNICA COMPOSTA - Sistema de contexto único
    # Permite múltiplas pré-separações POR CONTEXTO diferente (data + agendamento + protocolo)
    __table_args__ = (
        # Constraint única: mesmo pedido/produto pode ter múltiplas pré-separações com contextos diferentes
        # NOTA: func.coalesce será aplicado via trigger/constraint de BD para campos NULL
        db.UniqueConstraint(
            'num_pedido', 
            'cod_produto', 
            'data_expedicao_editada',
            'data_agendamento_editada',
            'protocolo_editado',
            name='uq_pre_separacao_contexto_unico'
        ),
        # Índices de performance
        db.Index('idx_pre_sep_data_expedicao', 'cod_produto', 'data_expedicao_editada', 'status'),
        db.Index('idx_pre_sep_dashboard', 'num_pedido', 'status', 'data_criacao'),
        db.Index('idx_pre_sep_recomposicao', 'recomposto', 'hash_item_original'),
    )
    
    def __repr__(self):
        return f'<PreSeparacaoItem {self.num_pedido}-{self.cod_produto}: {self.qtd_selecionada_usuario}/{self.qtd_original_carteira}>'
    
    # ===== PROPERTIES CALCULADAS =====
    
    @property
    def valor_selecionado(self):
        """Valor da quantidade selecionada"""
        if self.valor_original_item and self.qtd_original_carteira:
            return (float(self.qtd_selecionada_usuario) / float(self.qtd_original_carteira)) * float(self.valor_original_item)
        return 0
    
    @property 
    def valor_restante(self):
        """Valor da quantidade restante"""
        if self.valor_original_item and self.qtd_original_carteira:
            return (float(self.qtd_restante_calculada) / float(self.qtd_original_carteira)) * float(self.valor_original_item)
        return 0
        
    @property
    def peso_selecionado(self):
        """Peso da quantidade selecionada"""
        if self.peso_original_item and self.qtd_original_carteira:
            return (float(self.qtd_selecionada_usuario) / float(self.qtd_original_carteira)) * float(self.peso_original_item)
        return 0
        
    @property
    def percentual_selecionado(self):
        """Percentual selecionado do total"""
        if self.qtd_original_carteira:
            return (float(self.qtd_selecionada_usuario) / float(self.qtd_original_carteira)) * 100
        return 0
    
    # ===== MÉTODOS DE NEGÓCIO =====
    
    def gerar_hash_item(self, carteira_item):
        """Gera hash do item para detectar mudanças"""
        dados = f"{carteira_item.num_pedido}|{carteira_item.cod_produto}|{carteira_item.qtd_saldo_produto_pedido}|{carteira_item.preco_produto_pedido}"
        return hashlib.md5(dados.encode()).hexdigest()
    
    def validar_quantidades(self):
        """Valida se quantidades são consistentes"""
        if float(self.qtd_selecionada_usuario) > float(self.qtd_original_carteira):
            raise ValueError("Quantidade selecionada não pode ser maior que a original")
        
        if float(self.qtd_restante_calculada) != (float(self.qtd_original_carteira) - float(self.qtd_selecionada_usuario)):
            self.qtd_restante_calculada = float(self.qtd_original_carteira) - float(self.qtd_selecionada_usuario)
    
    def marcar_como_recomposto(self, usuario):
        """Marca item como recomposto após sincronização Odoo"""
        self.recomposto = True
        self.data_recomposicao = datetime.utcnow()
        self.recomposto_por = usuario
        self.status = 'RECOMPOSTO'
    
    def recompor_na_carteira(self, carteira_item, usuario):
        """Recompõe divisão na carteira após reimportação Odoo"""
        try:
            # Verificar se hash mudou (item foi alterado)
            novo_hash = self.gerar_hash_item(carteira_item)
            
            if self.hash_item_original != novo_hash:
                logger.warning(f"Item {self.num_pedido}-{self.cod_produto} foi alterado no Odoo")
            
            # Aplicar divisão na carteira
            if float(self.qtd_selecionada_usuario) < float(carteira_item.qtd_saldo_produto_pedido):
                # Criar nova linha com o saldo
                self._criar_linha_saldo_carteira(carteira_item)
                
                # Atualizar linha original
                carteira_item.qtd_saldo_produto_pedido = self.qtd_selecionada_usuario
                
                # Aplicar dados editáveis preservados
                if self.data_expedicao_editada:
                    carteira_item.expedicao = self.data_expedicao_editada
                if self.data_agendamento_editada:
                    carteira_item.agendamento = self.data_agendamento_editada  
                if self.protocolo_editado:
                    carteira_item.protocolo = self.protocolo_editado
                    
            # Marcar como recomposto
            self.marcar_como_recomposto(usuario)
            
            logger.info(f"✅ Item {self.num_pedido}-{self.cod_produto} recomposto com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao recompor item {self.num_pedido}-{self.cod_produto}: {e}")
            return False


    class CarteiraPrincipal(db.Model):
    """
    Modelo principal da carteira de pedidos - Baseado no arquivo 1
    Contém todos os 91 campos identificados + projeção D0-D28
    """
    __tablename__ = 'carteira_principal'

    id = db.Column(db.Integer, primary_key=True)
    
    # 🆔 CHAVES PRIMÁRIAS DE NEGÓCIO
    num_pedido = db.Column(db.String(50), nullable=False, index=True)  # Chave principal
    cod_produto = db.Column(db.String(50), nullable=False, index=True)  # Chave produto
    
    # 📋 DADOS DO PEDIDO
    pedido_cliente = db.Column(db.String(100), nullable=True)  # Pedido de Compra do Cliente
    data_pedido = db.Column(db.Date, nullable=True, index=True)  # Data de criação
    data_atual_pedido = db.Column(db.Date, nullable=True)  # Data da última alteração
    status_pedido = db.Column(db.String(50), nullable=True, index=True)  # Cancelado, Pedido de venda, Cotação
    
    # 👥 DADOS DO CLIENTE
    cnpj_cpf = db.Column(db.String(20), nullable=False, index=True)  # CNPJ do cliente
    raz_social = db.Column(db.String(255), nullable=True)  # Razão Social
    raz_social_red = db.Column(db.String(100), nullable=True)  # Nome reduzido
    municipio = db.Column(db.String(100), nullable=True)  # Cidade do cliente
    estado = db.Column(db.String(2), nullable=True)  # UF do cliente
    vendedor = db.Column(db.String(100), nullable=True, index=True)  # Vendedor responsável
    equipe_vendas = db.Column(db.String(100), nullable=True)  # Equipe de vendas
    
    # 📦 DADOS DO PRODUTO
    nome_produto = db.Column(db.String(255), nullable=False)  # Descrição do produto
    unid_medida_produto = db.Column(db.String(20), nullable=True)  # Unidade de medida
    embalagem_produto = db.Column(db.String(100), nullable=True)  # Categoria
    materia_prima_produto = db.Column(db.String(100), nullable=True)  # Sub categoria  
    categoria_produto = db.Column(db.String(100), nullable=True)  # Sub sub categoria
    
    # 📊 QUANTIDADES E VALORES
    qtd_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)  # Quantidade original
    qtd_saldo_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)  # Saldo a faturar
    qtd_cancelada_produto_pedido = db.Column(db.Numeric(15, 3), default=0)  # Quantidade cancelada
    preco_produto_pedido = db.Column(db.Numeric(15, 2), nullable=True)  # Preço unitário
    
    # 💳 CONDIÇÕES COMERCIAIS
    cond_pgto_pedido = db.Column(db.String(100), nullable=True)  # Condições de pagamento
    forma_pgto_pedido = db.Column(db.String(100), nullable=True)  # Forma de pagamento
    incoterm = db.Column(db.String(20), nullable=True)  # Incoterm
    metodo_entrega_pedido = db.Column(db.String(50), nullable=True)  # Método de entrega
    data_entrega_pedido = db.Column(db.Date, nullable=True)  # Data de entrega
    cliente_nec_agendamento = db.Column(db.String(10), nullable=True)  # Sim/Não
    observ_ped_1 = db.Column(db.Text, nullable=True)  # Observações
    
    # 🏠 ENDEREÇO DE ENTREGA COMPLETO
    cnpj_endereco_ent = db.Column(db.String(20), nullable=True)  # CNPJ entrega
    empresa_endereco_ent = db.Column(db.String(255), nullable=True)  # Nome local entrega
    cep_endereco_ent = db.Column(db.String(10), nullable=True)  # CEP
    nome_cidade = db.Column(db.String(100), nullable=True)  # Cidade extraída
    cod_uf = db.Column(db.String(2), nullable=True)  # UF extraída  
    bairro_endereco_ent = db.Column(db.String(100), nullable=True)  # Bairro
    rua_endereco_ent = db.Column(db.String(255), nullable=True)  # Rua
    endereco_ent = db.Column(db.String(20), nullable=True)  # Número
    telefone_endereco_ent = db.Column(db.String(20), nullable=True)  # Telefone
    
    # 📅 DADOS OPERACIONAIS (PRESERVADOS na atualização)
    expedicao = db.Column(db.Date, nullable=True)  # Data prevista expedição  
    data_entrega = db.Column(db.Date, nullable=True)  # Data prevista entrega
    agendamento = db.Column(db.Date, nullable=True)  # Data agendamento
    hora_agendamento = db.Column(db.Time, nullable=True)  # Hora agendamento
    protocolo = db.Column(db.String(50), nullable=True)  # Protocolo agendamento
    agendamento_confirmado = db.Column(db.Boolean, nullable=True, default=False)  # Agendamento confirmado
    roteirizacao = db.Column(db.String(100), nullable=True)  # Transportadora sugerida
    
    # 📊 ANÁLISE DE ESTOQUE (CALCULADOS)
    menor_estoque_produto_d7 = db.Column(db.Numeric(15, 3), nullable=True)  # Previsão ruptura 7 dias
    saldo_estoque_pedido = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque na data expedição
    saldo_estoque_pedido_forcado = db.Column(db.Numeric(15, 3), nullable=True)  # Just-in-time
    
    # 🚛 DADOS DE CARGA/LOTE (PRESERVADOS)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # Vínculo separação
    qtd_saldo = db.Column(db.Numeric(15, 3), nullable=True)  # Qtd no lote
    valor_saldo = db.Column(db.Numeric(15, 2), nullable=True)  # Valor no lote
    pallet = db.Column(db.Numeric(15, 3), nullable=True)  # Pallets no lote
    peso = db.Column(db.Numeric(15, 3), nullable=True)  # Peso no lote
    
    # 🛣️ DADOS DE ROTA E SUB-ROTA (ADICIONADOS)
    rota = db.Column(db.String(50), nullable=True)  # Rota principal baseada em cod_uf
    sub_rota = db.Column(db.String(50), nullable=True)  # Sub-rota baseada em cod_uf + nome_cidade
    
    # 📈 TOTALIZADORES POR CLIENTE (CALCULADOS)
    valor_saldo_total = db.Column(db.Numeric(15, 2), nullable=True)  # Valor total programado CNPJ
    pallet_total = db.Column(db.Numeric(15, 3), nullable=True)  # Pallet total programado CNPJ  
    peso_total = db.Column(db.Numeric(15, 3), nullable=True)  # Peso total programado CNPJ
    valor_cliente_pedido = db.Column(db.Numeric(15, 2), nullable=True)  # Valor total carteira CNPJ
    pallet_cliente_pedido = db.Column(db.Numeric(15, 3), nullable=True)  # Pallet total carteira CNPJ
    peso_cliente_pedido = db.Column(db.Numeric(15, 3), nullable=True)  # Peso total carteira CNPJ
    
    # 📊 TOTALIZADORES POR PRODUTO (CALCULADOS)
    qtd_total_produto_carteira = db.Column(db.Numeric(15, 3), nullable=True)  # Qtd total produto na carteira
    estoque = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque inicial/atual D0
    
    # 📈 PROJEÇÃO D0-D28 (28 CAMPOS DE ESTOQUE FUTURO)
    estoque_d0 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D0
    estoque_d1 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D1
    estoque_d2 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D2
    estoque_d3 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D3
    estoque_d4 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D4
    estoque_d5 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D5
    estoque_d6 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D6
    estoque_d7 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D7
    estoque_d8 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D8
    estoque_d9 = db.Column(db.Numeric(15, 3), nullable=True)   # Estoque final D9
    estoque_d10 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D10
    estoque_d11 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D11
    estoque_d12 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D12
    estoque_d13 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D13
    estoque_d14 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D14
    estoque_d15 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D15
    estoque_d16 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D16
    estoque_d17 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D17
    estoque_d18 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D18
    estoque_d19 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D19
    estoque_d20 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D20
    estoque_d21 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D21
    estoque_d22 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D22
    estoque_d23 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D23
    estoque_d24 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D24
    estoque_d25 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D25
    estoque_d26 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D26
    estoque_d27 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D27
    estoque_d28 = db.Column(db.Numeric(15, 3), nullable=True)  # Estoque final D28
    
    # 🛡️ AUDITORIA
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    created_by = db.Column(db.String(100), nullable=True)
    updated_by = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)
    
    # 📊 ÍNDICES COMPOSTOS PARA PERFORMANCE
    __table_args__ = (
        # Chave única de negócio
        db.UniqueConstraint('num_pedido', 'cod_produto', name='uq_carteira_pedido_produto'),
        # Índices de consulta
        Index('idx_carteira_cliente_vendedor', 'cnpj_cpf', 'vendedor'),
        Index('idx_carteira_status_expedicao', 'status_pedido', 'expedicao'),
        Index('idx_carteira_produto_saldo', 'cod_produto', 'qtd_saldo_produto_pedido'),
        Index('idx_carteira_separacao_lote', 'separacao_lote_id'),
    )

    def __repr__(self):
        return f'<CarteiraPrincipal {self.num_pedido} - {self.cod_produto} - Saldo: {self.qtd_saldo_produto_pedido}>'

    def to_dict(self):
        """Converte para dicionário para APIs e exportações"""
        return {
            'id': self.id,
            'num_pedido': self.num_pedido,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'qtd_produto_pedido': float(self.qtd_produto_pedido) if self.qtd_produto_pedido else 0,
            'qtd_saldo_produto_pedido': float(self.qtd_saldo_produto_pedido) if self.qtd_saldo_produto_pedido else 0,
            'preco_produto_pedido': float(self.preco_produto_pedido) if self.preco_produto_pedido else 0,
            'cnpj_cpf': self.cnpj_cpf,
            'raz_social_red': self.raz_social_red,
            'vendedor': self.vendedor,
            'status_pedido': self.status_pedido,
            'expedicao': self.expedicao.strftime('%d/%m/%Y') if self.expedicao else None,
            'agendamento': self.agendamento.strftime('%d/%m/%Y') if self.agendamento else None,
            'protocolo': self.protocolo
        }



    class Embarque(db.Model):
    __tablename__ = 'embarques'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, unique=True, nullable=True)
    data_prevista_embarque = db.Column(db.Date, nullable=True)
    data_embarque = db.Column(db.Date, nullable=True)
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=True)
    observacoes = db.Column(db.Text)
    placa_veiculo = db.Column(db.String(10)) #Não utilizado
    paletizado = db.Column(db.Boolean, default=False) #Não utilizado
    laudo_anexado = db.Column(db.Boolean, default=False) #Não utilizado
    embalagem_aprovada = db.Column(db.Boolean, default=False) #Não utilizado
    transporte_aprovado = db.Column(db.Boolean, default=False) #Não utilizado
    horario_carregamento = db.Column(db.String(5)) #Não utilizado
    responsavel_carregamento = db.Column(db.String(100)) #Não utilizado
    status = db.Column(db.String(20), default='draft')  # 'draft', 'ativo', 'cancelado'
    motivo_cancelamento = db.Column(db.Text, nullable=True)  # Motivo do cancelamento
    cancelado_em = db.Column(db.DateTime, nullable=True)  # Data/hora do cancelamento
    cancelado_por = db.Column(db.String(100), nullable=True)  # Usuário que cancelou
    tipo_cotacao = db.Column(db.String(20), default='Automatica')  # 'Automatica' ou 'Manual'
    valor_total = db.Column(db.Float) #Somatória do valor dos itens do embarque
    pallet_total = db.Column(db.Float) #Somatória do número de pallets dos itens do embarque
    peso_total = db.Column(db.Float) #Somatória do peso dos itens do embarque
    tipo_carga = db.Column(db.String(20))  # 'FRACIONADA' ou 'DIRETA'

    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=False, default='Administrador')

    # Campos do motorista
    nome_motorista = db.Column(db.String(100)) #Não utilizado
    cpf_motorista = db.Column(db.String(20)) #Não utilizado
    qtd_pallets = db.Column(db.Integer) #Não utilizado
    data_embarque_str = db.Column(db.String(10))  # formato DD/MM/AAAA

    # Campos específicos para carga DIRETA
    # Uma cotação direta está vinculada ao embarque principal
    cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id', name='fk_embarque_cotacao'), nullable=True)
    modalidade = db.Column(db.String(50))  # TIPO DE VEICULO CONTRATADO (MODELOS EM "app/veiculos/models/veiculos.nome")
    
    # Parâmetros da tabela para carga DIRETA
    tabela_nome_tabela = db.Column(db.String(100))
    tabela_valor_kg = db.Column(db.Float)
    tabela_percentual_valor = db.Column(db.Float)
    tabela_frete_minimo_valor = db.Column(db.Float)
    tabela_frete_minimo_peso = db.Column(db.Float)
    tabela_icms = db.Column(db.Float)
    tabela_percentual_gris = db.Column(db.Float)
    tabela_pedagio_por_100kg = db.Column(db.Float)
    tabela_valor_tas = db.Column(db.Float)
    tabela_percentual_adv = db.Column(db.Float)
    tabela_percentual_rca = db.Column(db.Float)
    tabela_valor_despacho = db.Column(db.Float)
    tabela_valor_cte = db.Column(db.Float)
    tabela_icms_incluso = db.Column(db.Boolean, default=False)
    
    # Campos para cálculo do ICMS
    icms_destino = db.Column(db.Float)
    transportadora_optante = db.Column(db.Boolean)

    # Relacionamentos
    transportadora = db.relationship('Transportadora', backref='embarques')
    itens = db.relationship('EmbarqueItem', backref='embarque', cascade='all, delete-orphan')
    # Para carga DIRETA: Uma cotação -> Um embarque
    cotacao = db.relationship('Cotacao', backref='embarque_direto', foreign_keys=[cotacao_id])

    
    def total_notas(self):
        return len([i for i in self.itens if i.status == 'ativo'])

    def total_volumes(self):
        return sum(i.volumes or 0 for i in self.itens if i.status == 'ativo')

    def total_peso_pedidos(self):
        """Retorna o peso total dos pedidos contidos no embarque"""
        return sum(i.peso or 0 for i in self.itens if i.status == 'ativo')

    def total_valor_pedidos(self):
        """Retorna o valor total dos pedidos contidos no embarque"""
        return sum(i.valor or 0 for i in self.itens if i.status == 'ativo')

    def total_pallet_pedidos(self):
        """Retorna o total de pallets dos pedidos contidos no embarque"""
        # Soma os pallets reais dos itens ativos
        total_pallets = sum(i.pallets or 0 for i in self.itens if i.status == 'ativo')
        
        # Se não há pallets informados, calcula baseado no peso (fallback)
        if total_pallets == 0:
            peso_total = self.total_peso_pedidos()
            if peso_total > 0:
                return round(peso_total / 500, 2)  # 500kg por pallet
        
        return total_pallets

    @property
    def itens_ativos(self):
        """Retorna apenas os itens ativos do embarque"""
        return [item for item in self.itens if item.status == 'ativo']

    @property
    def status_nfs(self):
        """
        Calcula o status das NFs do embarque:
        - 'NFs pendentes' - Caso algum pedido esteja sem NF
        - 'Pendente Import.' - Caso as NFs estejam preenchidas, porém tenha NF ainda não importada
        - 'NFs Lançadas' - Todas as NFs estão lançadas e validadas pelo faturamento
        """
        itens_ativos = [item for item in self.itens if item.status == 'ativo']
        
        if not itens_ativos:
            return 'NFs pendentes'
        
        # Verifica se há itens sem NF
        itens_sem_nf = [item for item in itens_ativos if not item.nota_fiscal or item.nota_fiscal.strip() == '']
        if itens_sem_nf:
            return 'NFs pendentes'
        
        # Verifica se há NFs pendentes de importação
        itens_pendentes = [item for item in itens_ativos if item.erro_validacao and 'NF_PENDENTE_FATURAMENTO' in item.erro_validacao]
        if itens_pendentes:
            return 'Pendente Import.'
        
        # Verifica se há NFs divergentes
        itens_divergentes = [item for item in itens_ativos if item.erro_validacao and ('NF_DIVERGENTE' in item.erro_validacao or 'CLIENTE_NAO_DEFINIDO' in item.erro_validacao)]
        if itens_divergentes:
            return 'NFs pendentes'
        
        # Se chegou até aqui, todas as NFs estão validadas
        return 'NFs Lançadas'

    @property
    def status_fretes(self):
        """
        Calcula o status dos fretes do embarque:
        - 'Pendentes' - Significa que pelo menos 1 pedido está sem NF ou sem validação pelo faturamento
        - 'Emitido' - Significa que o/os fretes do embarque já foram emitidos
        - 'Lançado' - Significa que pelo menos 1 frete já foi vinculado CTe
        """
        from app.fretes.models import Frete
        
        # Primeiro verifica se as NFs estão prontas
        if self.status_nfs != 'NFs Lançadas':
            return 'Pendentes'
        
        # Busca fretes deste embarque
        fretes = Frete.query.filter_by(embarque_id=self.id).filter(Frete.status != 'CANCELADO').all()
        
        if not fretes:
            return 'Pendentes'
        
        # Verifica se há fretes com CTe lançado
        fretes_com_cte = [frete for frete in fretes if frete.numero_cte and frete.numero_cte.strip() != '']
        if fretes_com_cte:
            return 'Lançado'
        
        # Se há fretes mas sem CTe, estão emitidos
        return 'Emitido'

    def __repr__(self):
        return f"<Embarque #{self.numero} - {self.data}>"

class EmbarqueItem(db.Model):
    __tablename__ = 'embarque_itens'

    id = db.Column(db.Integer, primary_key=True)
    embarque_id = db.Column(db.Integer, db.ForeignKey('embarques.id'), nullable=False)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # ID do lote de separação
    cnpj_cliente = db.Column(db.String(20), nullable=True)
    cliente = db.Column(db.String(120), nullable=False)
    pedido = db.Column(db.String(50), nullable=False)
    protocolo_agendamento = db.Column(db.String(50))
    data_agenda = db.Column(db.String(10))
    nota_fiscal = db.Column(db.String(20))
    volumes = db.Column(db.Integer, nullable=True)
    peso = db.Column(db.Float)  # Peso do item
    valor = db.Column(db.Float)  # Valor do item
    pallets = db.Column(db.Float, nullable=True)  # Quantidade de pallets do item
    status = db.Column(db.String(20), nullable=False, default='ativo')  # 'ativo' ou 'cancelado'

    uf_destino = db.Column(db.String(2), nullable=False)
    cidade_destino = db.Column(db.String(100), nullable=False)

    # Campos específicos para carga FRACIONADA
    # Cada item do embarque tem sua própria cotação
    cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id', name='fk_embarque_item_cotacao'), nullable=True)
    modalidade = db.Column(db.String(50))
    
    # Parâmetros da tabela para carga FRACIONADA
    tabela_nome_tabela = db.Column(db.String(100))
    tabela_valor_kg = db.Column(db.Float)
    tabela_percentual_valor = db.Column(db.Float)
    tabela_frete_minimo_valor = db.Column(db.Float)
    tabela_frete_minimo_peso = db.Column(db.Float)
    tabela_icms = db.Column(db.Float)
    tabela_percentual_gris = db.Column(db.Float)
    tabela_pedagio_por_100kg = db.Column(db.Float)
    tabela_valor_tas = db.Column(db.Float)
    tabela_percentual_adv = db.Column(db.Float)
    tabela_percentual_rca = db.Column(db.Float)
    tabela_valor_despacho = db.Column(db.Float)
    tabela_valor_cte = db.Column(db.Float)
    tabela_icms_incluso = db.Column(db.Boolean, default=False)
    icms_destino = db.Column(db.Float)

    # Campo para armazenar erros de validação
    erro_validacao = db.Column(db.String(500), nullable=True)  # Armazena erros como "CNPJ_DIFERENTE", etc.

    # Para carga FRACIONADA: Uma cotação -> Um item do embarque
    cotacao = db.relationship('Cotacao', backref='embarque_item', foreign_keys=[cotacao_id])


    class Pedido(db.Model):
    __tablename__ = 'pedidos'

    id = db.Column(db.Integer, primary_key=True)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # ID do lote de separação
    num_pedido = db.Column(db.String(30), index=True)
    data_pedido = db.Column(db.Date)
    cnpj_cpf = db.Column(db.String(20))
    raz_social_red = db.Column(db.String(255))
    nome_cidade = db.Column(db.String(120))
    cod_uf = db.Column(db.String(2))
    cidade_normalizada = db.Column(db.String(120))
    uf_normalizada = db.Column(db.String(2))
    codigo_ibge = db.Column(db.String(10))  # Código IBGE da cidade (único por cidade)
    valor_saldo_total = db.Column(db.Float)
    pallet_total = db.Column(db.Float)
    peso_total = db.Column(db.Float)
    rota = db.Column(db.String(50))
    sub_rota = db.Column(db.String(50))
    observ_ped_1 = db.Column(db.Text)
    roteirizacao = db.Column(db.String(100))
    expedicao = db.Column(db.Date)
    agendamento = db.Column(db.Date)
    protocolo = db.Column(db.String(50))

    transportadora = db.Column(db.String(100))
    valor_frete = db.Column(db.Float)
    valor_por_kg = db.Column(db.Float)
    nome_tabela = db.Column(db.String(100))
    modalidade = db.Column(db.String(50))
    melhor_opcao = db.Column(db.String(100))
    valor_melhor_opcao = db.Column(db.Float)
    lead_time = db.Column(db.Integer)

    data_embarque = db.Column(db.Date)
    nf = db.Column(db.String(20))
    status = db.Column(db.String(50), default='ABERTO')
    nf_cd = db.Column(db.Boolean, default=False)  # ✅ NOVO: Flag para NF no CD
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id', name='fk_pedido_cotacao'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', name='fk_pedido_usuario'))

    __table_args__ = (
        UniqueConstraint(
            'num_pedido', 'expedicao', 'agendamento', 'protocolo',
            name='uix_num_pedido_exped_agend_prot'
        ),
    )

    # Relacionamentos
    usuario = db.relationship('Usuario', backref='pedidos', foreign_keys=[usuario_id])

    def __repr__(self):
        return f'<Pedido {self.num_pedido} - Lote: {self.separacao_lote_id}>'
    
    @property
    def status_calculado(self):
        """
        Calcula o status do pedido baseado no estado atual:
        - NF no CD: Flag nf_cd é True (NF voltou para o CD)
        - FATURADO: Tem NF preenchida e não está no CD
        - EMBARCADO: Tem data de embarque mas não tem NF
        - COTADO: Tem cotação_id mas não está embarcado
        - ABERTO: Não tem cotação
        """
        # ✅ NOVO: Primeiro verifica se a NF está no CD
        if getattr(self, 'nf_cd', False):
            return 'NF no CD'
        elif self.nf and self.nf.strip():
            return 'FATURADO'
        elif self.data_embarque:
            return 'EMBARCADO'
        elif self.cotacao_id:
            return 'COTADO'
        else:
            return 'ABERTO'
    
    @property
    def status_badge_class(self):
        """Retorna a classe CSS para o badge do status"""
        status_classes = {
            'NF no CD': 'badge bg-danger',  # ✅ NOVO: Vermelho para indicar problema
            'FATURADO': 'badge bg-success',
            'EMBARCADO': 'badge bg-primary', 
            'COTADO': 'badge bg-warning text-dark',
            'ABERTO': 'badge bg-secondary'
        }
        return status_classes.get(self.status_calculado, 'badge bg-light text-dark')
    
    @property
    def pendente_cotacao(self):
        """Verifica se o pedido está pendente de cotação"""
        return self.status_calculado == 'ABERTO'


    class Separacao(db.Model):
    __tablename__ = 'separacao'

    id            = db.Column(db.Integer, primary_key=True)
    separacao_lote_id = db.Column(db.String(50), nullable=True, index=True)  # ID do lote de separação
    num_pedido    = db.Column(db.String(50), nullable=True)
    data_pedido   = db.Column(db.Date, nullable=True)  # agora pode ser nulo
    cnpj_cpf      = db.Column(db.String(20), nullable=True)
    raz_social_red= db.Column(db.String(255), nullable=True)
    nome_cidade   = db.Column(db.String(100), nullable=True)
    cod_uf        = db.Column(db.String(2), nullable=False)
    cod_produto   = db.Column(db.String(50), nullable=True)
    nome_produto  = db.Column(db.String(255), nullable=True)

    qtd_saldo     = db.Column(db.Float, nullable=True)  # agora pode ser nulo
    valor_saldo   = db.Column(db.Float, nullable=True)
    pallet        = db.Column(db.Float, nullable=True)
    peso          = db.Column(db.Float, nullable=True)

    rota          = db.Column(db.String(50), nullable=True)
    sub_rota      = db.Column(db.String(50), nullable=True)
    observ_ped_1  = db.Column(db.String(700), nullable=True)
    roteirizacao  = db.Column(db.String(255), nullable=True)
    expedicao     = db.Column(db.Date, nullable=True)
    agendamento   = db.Column(db.Date, nullable=True)
    protocolo     = db.Column(db.String(50), nullable=True)
    
    # 🎯 ETAPA 2: CAMPO TIPO DE ENVIO (ADICIONADO NA MIGRAÇÃO)
    tipo_envio    = db.Column(db.String(10), default='total', nullable=True)  # total, parcial

    criado_em     = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Separacao #{self.id} - {self.num_pedido} - Lote: {self.separacao_lote_id} - Tipo: {self.tipo_envio}>'


    class MovimentacaoEstoque(db.Model):
    """
    Modelo para controle das movimentações de estoque
    """
    __tablename__ = 'movimentacao_estoque'

    id = db.Column(db.Integer, primary_key=True)
    
    # Dados do produto
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(200), nullable=False)
    
    # Dados da movimentação
    data_movimentacao = db.Column(db.Date, nullable=False, index=True)
    tipo_movimentacao = db.Column(db.String(50), nullable=False, index=True)  # ENTRADA, SAIDA, AJUSTE, PRODUCAO
    local_movimentacao = db.Column(db.String(50), nullable=False)  # COMPRA, VENDA, PRODUCAO, AJUSTE, DEVOLUCAO
    
    # Quantidades
    qtd_movimentacao = db.Column(db.Numeric(15, 3), nullable=False)

    # Observações
    observacao = db.Column(db.Text, nullable=True)

        
    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)

    # Índices compostos para performance  
    __table_args__ = (
        db.Index('idx_movimentacao_produto_data', 'cod_produto', 'data_movimentacao'),
        db.Index('idx_movimentacao_tipo_data', 'tipo_movimentacao', 'data_movimentacao'),
    )

    def __repr__(self):
        return f'<MovimentacaoEstoque {self.cod_produto} - {self.tipo_movimentacao} - {self.qtd_movimentacao}>'

    def to_dict(self):
        return {
            'id': self.id,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'data_movimentacao': self.data_movimentacao.strftime('%d/%m/%Y') if self.data_movimentacao else None,
            'tipo_movimentacao': self.tipo_movimentacao,
            'local_movimentacao': self.local_movimentacao,
            'qtd_movimentacao': float(self.qtd_movimentacao) if self.qtd_movimentacao else 0,
            'observacao': self.observacao
        }


class UnificacaoCodigos(db.Model):
    """
    Modelo para unificação de códigos de produtos
    Permite tratar códigos diferentes como mesmo produto físico para fins de estoque
    """
    __tablename__ = 'unificacao_codigos'

    id = db.Column(db.Integer, primary_key=True)
    
    # Códigos de unificação
    codigo_origem = db.Column(db.Integer, nullable=False, index=True)
    codigo_destino = db.Column(db.Integer, nullable=False, index=True) 
    
    # Observações
    observacao = db.Column(db.Text, nullable=True)
    
    # Auditoria completa
    ativo = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    created_by = db.Column(db.String(100), nullable=True)
    updated_by = db.Column(db.String(100), nullable=True)
    
    # Histórico de ativação/desativação
    data_ativacao = db.Column(db.DateTime, nullable=True)
    data_desativacao = db.Column(db.DateTime, nullable=True)
    motivo_desativacao = db.Column(db.Text, nullable=True)
    
    # Índices compostos para performance e integridade
    __table_args__ = (
        # Evita duplicação: mesmo par origem-destino
        db.UniqueConstraint('codigo_origem', 'codigo_destino', name='uq_unificacao_origem_destino'),
        # Evita ciclos: A->B e B->A simultaneamente  
        db.Index('idx_unificacao_origem', 'codigo_origem'),
        db.Index('idx_unificacao_destino', 'codigo_destino'),
        db.Index('idx_unificacao_ativo', 'ativo'),
    )

    def __repr__(self):
        status = "Ativo" if self.ativo else "Inativo"
        return f'<UnificacaoCodigos {self.codigo_origem} → {self.codigo_destino} [{status}]>'

    def to_dict(self):
        return {
            'id': self.id,
            'codigo_origem': self.codigo_origem,
            'codigo_destino': self.codigo_destino,
            'observacao': self.observacao,
            'ativo': self.ativo,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%d/%m/%Y %H:%M') if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'data_ativacao': self.data_ativacao.strftime('%d/%m/%Y %H:%M') if self.data_ativacao else None,
            'data_desativacao': self.data_desativacao.strftime('%d/%m/%Y %H:%M') if self.data_desativacao else None,
            'motivo_desativacao': self.motivo_desativacao
        }

    @classmethod
    def get_codigo_unificado(cls, codigo_produto):
        """
        Retorna o código destino se existe unificação ativa, senão retorna o próprio código
        """
        try:
            codigo_produto = int(codigo_produto)
            
            # Busca se o código é origem em alguma unificação ativa
            unificacao = cls.query.filter_by(
                codigo_origem=codigo_produto,
                ativo=True
            ).first()
            
            if unificacao:
                return unificacao.codigo_destino
                
            # Se não é origem, verifica se é destino (para estatísticas)
            return codigo_produto
            
        except (ValueError, TypeError):
            return codigo_produto

    @classmethod
    def get_todos_codigos_relacionados(cls, codigo_produto):
        """
        Retorna todos os códigos relacionados ao código informado
        Usado para estatísticas e consolidação
        """
        try:
            codigo_produto = int(codigo_produto)
            codigos_relacionados = set([codigo_produto])
            
            # Busca códigos que apontam para este (este é destino)
            origens = cls.query.filter_by(
                codigo_destino=codigo_produto,
                ativo=True
            ).all()
            
            for origem in origens:
                codigos_relacionados.add(origem.codigo_origem)
            
            # Busca para onde este código aponta (este é origem)
            destino = cls.query.filter_by(
                codigo_origem=codigo_produto,
                ativo=True
            ).first()
            
            if destino:
                codigos_relacionados.add(destino.codigo_destino)
                # Busca outros códigos que também apontam para o mesmo destino
                outros_origens = cls.query.filter_by(
                    codigo_destino=destino.codigo_destino,
                    ativo=True
                ).all()
                for outro in outros_origens:
                    codigos_relacionados.add(outro.codigo_origem)
            
            return list(codigos_relacionados)
            
        except (ValueError, TypeError):
            return [codigo_produto]

    def ativar(self, usuario=None, motivo=None):
        """Ativa a unificação"""
        self.ativo = True
        self.data_ativacao = agora_brasil()
        self.updated_by = usuario
        self.motivo_desativacao = None
        
    def desativar(self, usuario=None, motivo=None):
        """Desativa a unificação"""
        self.ativo = False
        self.data_desativacao = agora_brasil()
        self.updated_by = usuario
        self.motivo_desativacao = motivo 

class SaldoEstoque:
    """
    Classe de serviço para cálculos de saldo de estoque em tempo real
    Não é uma tabela persistente, mas sim um calculador que integra dados de:
    - MovimentacaoEstoque (módulo já existente) - entrada/saída histórica
    - ProgramacaoProducao (módulo já existente) - produção futura
    - ✅ PreSeparacaoItem (principal) - saídas futuras por data de expedição
    - ✅ Separacao (complementar) - saídas já separadas
    - UnificacaoCodigos (módulo recém implementado) - códigos relacionados
    
    ❌ REMOVIDO: CarteiraPrincipal (não participa mais do cálculo de estoque futuro)
    """
    
    @staticmethod
    def obter_produtos_com_estoque():
        """Obtém lista de produtos únicos que têm movimentação de estoque"""
        try:
            inspector = inspect(db.engine)
            if not inspector.has_table('movimentacao_estoque'):
                return []
            
            # Buscar produtos únicos com movimentação
            produtos = db.session.query(
                MovimentacaoEstoque.cod_produto,
                MovimentacaoEstoque.nome_produto
            ).filter(
                MovimentacaoEstoque.ativo == True
            ).distinct().all()
            
            return produtos
            
        except Exception as e:
            logger.error(f"Erro ao obter produtos com estoque: {str(e)}")
            return []
    
    @staticmethod
    def calcular_estoque_inicial(cod_produto):
        """Calcula estoque inicial (D0) baseado em todas as movimentações"""
        try:
            inspector = inspect(db.engine)
            if not inspector.has_table('movimentacao_estoque'):
                return 0
            
            # Buscar todos os códigos relacionados (considerando unificação)
            codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(int(cod_produto))
            
            # Somar movimentações de todos os códigos relacionados
            total_estoque = 0
            for codigo in codigos_relacionados:
                movimentacoes = MovimentacaoEstoque.query.filter(
                    MovimentacaoEstoque.cod_produto == str(codigo),
                    MovimentacaoEstoque.ativo == True
                ).all()
                
                total_estoque += sum(float(m.qtd_movimentacao) for m in movimentacoes)
            
            return total_estoque
            
        except Exception as e:
            logger.error(f"Erro ao calcular estoque inicial para {cod_produto}: {str(e)}")
            return 0
    
    @staticmethod
    def calcular_producao_periodo(cod_produto, data_inicio, data_fim):
        """Calcula produção programada para um produto em um período"""
        try:
            inspector = inspect(db.engine)
            if not inspector.has_table('programacao_producao'):
                return 0
            
            # Buscar todos os códigos relacionados (considerando unificação)
            codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(int(cod_produto))
            
            # Somar produção de todos os códigos relacionados
            total_producao = 0
            for codigo in codigos_relacionados:
                from app.producao.models import ProgramacaoProducao
                
                producoes = ProgramacaoProducao.query.filter(
                    ProgramacaoProducao.cod_produto == str(codigo),
                    ProgramacaoProducao.data_programacao >= data_inicio,
                    ProgramacaoProducao.data_programacao <= data_fim
                ).all()
                
                total_producao += sum(float(p.qtd_programada) for p in producoes)
            
            return total_producao
            
        except Exception as e:
            logger.error(f"Erro ao calcular produção para {cod_produto}: {str(e)}")
            return 0
    

    
    @staticmethod
    def calcular_projecao_completa(cod_produto):
        """
        Calcula projeção completa de estoque para 29 dias (D0 até D+28)
        IMPLEMENTA LÓGICA JUST-IN-TIME CORRETA:
        - EST INICIAL D0 = estoque atual
        - SAÍDA D0 = Separacao + CarteiraPrincipal + PreSeparacaoItem (expedição D0)
        - EST FINAL D0 = EST INICIAL D0 - SAÍDA D0
        - PROD D0 = ProgramacaoProducao (data_programacao D0)
        - EST INICIAL D+1 = EST FINAL D0 + PROD D0 (Just-in-Time!)
        """
        try:
            projecao = []
            data_hoje = datetime.now().date()
            
            # Estoque inicial (D0)
            estoque_atual = SaldoEstoque.calcular_estoque_inicial(cod_produto)
            
            # Calcular para cada dia (D0 até D+28)
            for dia in range(29):
                data_calculo = data_hoje + timedelta(days=dia)
                
                # 📤 SAÍDAS do dia (todas as fontes com expedição = data_calculo)
                saida_dia = SaldoEstoque._calcular_saidas_completas(cod_produto, data_calculo)
                
                # 🏭 PRODUÇÃO programada para o dia (fica disponível AMANHÃ - Just-in-Time)
                producao_dia = SaldoEstoque.calcular_producao_periodo(cod_produto, data_calculo, data_calculo)
                
                # 📊 LÓGICA SEQUENCIAL CORRETA
                if dia == 0:
                    # D0: Estoque atual
                    estoque_inicial_dia = estoque_atual
                else:
                    # D+1: EST FINAL D0 + PROD D0 (Just-in-Time!)
                    estoque_final_anterior = projecao[dia-1]['estoque_final']
                    producao_anterior = projecao[dia-1]['producao_programada']
                    estoque_inicial_dia = estoque_final_anterior + producao_anterior
                
                # EST FINAL = EST INICIAL - SAÍDA (produção NÃO entra no mesmo dia)
                estoque_final_dia = estoque_inicial_dia - saida_dia
                
                # Dados do dia
                dia_dados = {
                    'dia': dia,
                    'data': data_calculo,
                    'data_formatada': data_calculo.strftime('%d/%m'),
                    'estoque_inicial': estoque_inicial_dia,
                    'saida_prevista': saida_dia,
                    'producao_programada': producao_dia,  # Fica disponível amanhã
                    'estoque_final': estoque_final_dia
                }
                
                projecao.append(dia_dados)
            
            return projecao
            
        except Exception as e:
            logger.error(f"Erro ao calcular projeção para {cod_produto}: {str(e)}")
            return []
    
    @staticmethod
    def calcular_previsao_ruptura(projecao):
        """Calcula previsão de ruptura (menor estoque em 7 dias)"""
        try:
            if not projecao or len(projecao) < 8:
                return 0
            
            # Pegar estoque final dos primeiros 8 dias (D0 até D7)
            estoques_7_dias = [dia['estoque_final'] for dia in projecao[:8]]
            
            return min(estoques_7_dias)
            
        except Exception as e:
            logger.error(f"Erro ao calcular previsão de ruptura: {str(e)}")
            return 0
    
    @staticmethod
    def obter_resumo_produto(cod_produto, nome_produto):
        """Obtém resumo completo de um produto"""
        try:
            # Calcular projeção completa
            projecao = SaldoEstoque.calcular_projecao_completa(cod_produto)
            
            if not projecao:
                return None
            
            # Dados principais
            estoque_inicial = projecao[0]['estoque_inicial']
            previsao_ruptura = SaldoEstoque.calcular_previsao_ruptura(projecao)
            
            # 📊 TOTAIS CARTEIRA (implementado com CarteiraPrincipal)
            qtd_total_carteira = SaldoEstoque._calcular_qtd_total_carteira(cod_produto)
            
            resumo = {
                'cod_produto': cod_produto,
                'nome_produto': nome_produto,
                'estoque_inicial': estoque_inicial,
                'qtd_total_carteira': qtd_total_carteira,
                'previsao_ruptura': previsao_ruptura,
                'projecao_29_dias': projecao,
                'status_ruptura': 'CRÍTICO' if previsao_ruptura <= 0 else 'ATENÇÃO' if previsao_ruptura < 10 else 'OK'
            }
            
            return resumo
            
        except Exception as e:
            logger.error(f"Erro ao obter resumo do produto {cod_produto}: {str(e)}")
            return None
    
    @staticmethod
    def _calcular_saidas_completas(cod_produto, data_expedicao):
        """
        Calcula TODAS as saídas previstas para uma data específica
        ✅ NOVA IMPLEMENTAÇÃO: SAÍDA = Separacao + PreSeparacaoItem (expedição = data)
        ❌ CarteiraPrincipal removida (não tem campo expedição na nova lógica)
        """
        try:
            # Buscar todos os códigos relacionados (considerando unificação)
            codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(int(cod_produto))
            
            total_saida = 0
            
            for codigo in codigos_relacionados:
                # 📦 1. SEPARAÇÕES já efetivadas (app.separacao.models)
                try:
                    from app.separacao.models import Separacao
                    separacoes = Separacao.query.filter(
                        Separacao.cod_produto == str(codigo),
                        Separacao.expedicao == data_expedicao,  # Data de expedição correta
                        Separacao.ativo == True
                    ).all()
                    
                    for sep in separacoes:
                        if sep.qtd_saldo and sep.qtd_saldo > 0:
                            total_saida += float(sep.qtd_saldo)
                except Exception as e:
                    logger.debug(f"Separacao não encontrada ou erro: {e}")
                
                # ✅ 2. PRÉ-SEPARAÇÃO ITENS (principal fonte de saídas futuras)
                try:
                    from app.carteira.models import PreSeparacaoItem
                    pre_separacoes = PreSeparacaoItem.query.filter(
                        PreSeparacaoItem.cod_produto == str(codigo),
                        PreSeparacaoItem.data_expedicao_editada == data_expedicao,  # Data de expedição obrigatória
                        PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])  # Apenas ativas
                    ).all()
                    
                    for pre_sep in pre_separacoes:
                        if pre_sep.qtd_selecionada_usuario and pre_sep.qtd_selecionada_usuario > 0:
                            total_saida += float(pre_sep.qtd_selecionada_usuario)
                except Exception as e:
                    logger.debug(f"PreSeparacaoItem não encontrada ou erro: {e}")
                
                # ❌ CARTEIRA PRINCIPAL REMOVIDA DO CÁLCULO
                # NOVA REGRA: CarteiraPrincipal NÃO tem campo expedição
                # Apenas PreSeparacao + Separacao participam do cálculo de estoque futuro
            
            return total_saida
            
        except Exception as e:
            logger.error(f"Erro ao calcular saídas completas para {cod_produto} em {data_expedicao}: {str(e)}")
            return 0

    @staticmethod
    def _calcular_qtd_total_carteira(cod_produto):
        """
        Calcula quantidade total em carteira para um produto específico
        Soma todos os itens pendentes de separação na CarteiraPrincipal
        """
        try:
            from app.carteira.models import CarteiraPrincipal
            
            # Buscar todos os códigos relacionados (considerando unificação)
            codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(int(cod_produto))
            
            total_carteira = 0
            for codigo in codigos_relacionados:
                # Somar itens ainda não separados (sem separacao_lote_id)
                itens_carteira = CarteiraPrincipal.query.filter(
                    CarteiraPrincipal.cod_produto == str(codigo),
                    CarteiraPrincipal.separacao_lote_id.is_(None),  # Ainda não separado
                    CarteiraPrincipal.ativo == True
                ).all()
                
                for item in itens_carteira:
                    if item.qtd_saldo_produto_pedido:
                        total_carteira += float(item.qtd_saldo_produto_pedido)
            
            return total_carteira
            
        except Exception as e:
            logger.error(f"Erro ao calcular qtd total carteira para {cod_produto}: {str(e)}")
            return 0

    @staticmethod
    def processar_ajuste_estoque(cod_produto, qtd_ajuste, motivo, usuario):
        """Processa ajuste de estoque gerando movimentação automática"""
        try:
            # Buscar nome do produto
            produto_existente = MovimentacaoEstoque.query.filter_by(
                cod_produto=str(cod_produto),
                ativo=True
            ).first()
            
            if not produto_existente:
                raise ValueError(f"Produto {cod_produto} não encontrado nas movimentações")
            
            # Criar movimentação de ajuste
            ajuste = MovimentacaoEstoque(
                cod_produto=str(cod_produto),
                nome_produto=produto_existente.nome_produto,
                tipo_movimentacao='AJUSTE',
                local_movimentacao='CD',
                data_movimentacao=datetime.now().date(),
                qtd_movimentacao=float(qtd_ajuste),
                observacao=f'Ajuste manual: {motivo}',
                criado_por=usuario,
                atualizado_por=usuario
            )
            
            db.session.add(ajuste)
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao processar ajuste de estoque: {str(e)}")
            raise e 

    class ProgramacaoProducao(db.Model):
    """
    Modelo para controle da programação de produção
    """
    __tablename__ = 'programacao_producao'

    id = db.Column(db.Integer, primary_key=True)
    
    # Dados da ordem de produção
    data_programacao = db.Column(db.Date, nullable=False, index=True) 
    
    # Dados do produto
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(200), nullable=False)
    
    # Quantidades
    qtd_programada = db.Column(db.Float, nullable=False)
    
    # Dados de produção
    linha_producao = db.Column(db.String(50), nullable=True)
    cliente_produto = db.Column(db.String(100), nullable=True)  # marca

    # Prioridade e observações
    observacao_pcp = db.Column(db.Text, nullable=True)
        
    # Auditoria
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)
    created_by = db.Column(db.String(100), nullable=True)
    updated_by = db.Column(db.String(100), nullable=True)

    # Índices compostos para performance
    __table_args__ = (
        db.Index('idx_programacao_data_linha', 'data_programacao', 'linha_producao'),
        db.Index('idx_programacao_produto_data', 'cod_produto', 'data_programacao'),
        # Sem constraint única - programação permite múltiplas entradas do mesmo produto/linha/data
    )

    def __repr__(self):
        return f'<ProgramacaoProducao {self.cod_produto} - {self.data_programacao}>'

    def to_dict(self):
        return {
            'id': self.id,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'data_programacao': self.data_programacao.strftime('%d/%m/%Y') if self.data_programacao else None,
            'qtd_programada': float(self.qtd_programada) if self.qtd_programada else 0,
            'linha_producao': self.linha_producao,
            'cliente_produto': self.cliente_produto,
            'observacao_pcp': self.observacao_pcp
        }
       



class CadastroPalletizacao(db.Model):
    """
    Modelo para cadastro de palletização e peso bruto dos produtos
    Conforme CSV: 8- cadastro palletizacao e peso bruto.csv
    """
    __tablename__ = 'cadastro_palletizacao'

    id = db.Column(db.Integer, primary_key=True)
    
    # Dados do produto (conforme CSV)
    cod_produto = db.Column(db.String(50), nullable=False, unique=True, index=True)  # Cód.Produto
    nome_produto = db.Column(db.String(255), nullable=False)  # Descrição Produto
    
    # Fatores de conversão (conforme CSV)
    palletizacao = db.Column(db.Float, nullable=False)  # PALLETIZACAO: qtd / palletizacao = pallets
    peso_bruto = db.Column(db.Float, nullable=False)    # PESO BRUTO: qtd * peso_bruto = peso total
    
    # Dados de dimensões (interessante para cálculos)
    altura_cm = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    largura_cm = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    comprimento_cm = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    
    # Status
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    
    # Auditoria
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    updated_at = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil, nullable=False)

    def __repr__(self):
        return f'<CadastroPalletizacao {self.cod_produto} - Pallet: {self.palletizacao}>'

    def calcular_pallets(self, quantidade):
        """Calcula quantos pallets para uma quantidade"""
        if self.palletizacao > 0:
            return round(quantidade / self.palletizacao, 2)
        return 0

    def calcular_peso_total(self, quantidade):
        """Calcula peso total para uma quantidade"""
        return round(quantidade * self.peso_bruto, 2)

    @property
    def volume_m3(self):
        """Calcula volume unitário em m³"""
        if self.altura_cm and self.largura_cm and self.comprimento_cm:
            return round((float(self.altura_cm) * float(self.largura_cm) * float(self.comprimento_cm)) / 1000000, 6)
        return 0

    def to_dict(self):
        return {
            'id': self.id,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'palletizacao': float(self.palletizacao) if self.palletizacao else 0,
            'peso_bruto': float(self.peso_bruto) if self.peso_bruto else 0,
            'altura_cm': float(self.altura_cm) if self.altura_cm else 0,
            'largura_cm': float(self.largura_cm) if self.largura_cm else 0,
            'comprimento_cm': float(self.comprimento_cm) if self.comprimento_cm else 0,
            'volume_m3': self.volume_m3,
            'ativo': self.ativo
        } 
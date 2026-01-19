from app import db
from datetime import datetime

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
    peso_total = db.Column(db.Float) #Somatória do peso dos itens do embarque

    # === GRUPO 1: PALLETS TEÓRICOS (via CadastroPalletizacao) ===
    # Estimativa baseada em pallets padrão (1 produto por pallet)
    # ⚠️ PODE DIVERGIR DA REALIDADE quando pallets têm múltiplos produtos misturados
    # Uso: Impressão de embarque, estimativa inicial para planejamento
    # Calculado automaticamente via listener em app/separacao/models.py
    pallet_total = db.Column(db.Float)  # Soma de EmbarqueItem.pallets (TEÓRICO)
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
    
    # ===== NOVOS CAMPOS DE VALORES MÍNIMOS E ICMS =====
    tabela_gris_minimo = db.Column(db.Float, default=0)    # Valor mínimo de GRIS
    tabela_adv_minimo = db.Column(db.Float, default=0)     # Valor mínimo de ADV
    tabela_icms_proprio = db.Column(db.Float, nullable=True)  # ICMS próprio da tabela
    
    # Campos para cálculo do ICMS
    icms_destino = db.Column(db.Float)
    transportadora_optante = db.Column(db.Boolean)

    # === GRUPO 2: PALLETS FÍSICOS (Controle Real - Gestão de Ativos PBR) ===
    # Valores REAIS preenchidos manualmente para controle de NF remessa
    # NÃO são afetados pelo cálculo teórico via CadastroPalletizacao
    # Usados para: Faturamento de NF de pallet, controle de saldo em terceiros
    nf_pallet_transportadora = db.Column(db.String(20), nullable=True)     # NF remessa para transportadora
    qtd_pallet_transportadora = db.Column(db.Float, default=0, nullable=True)  # Qtd na NF remessa
    qtd_pallets_separados = db.Column(db.Integer, default=0, nullable=True)    # Pallets físicos expedidos
    qtd_pallets_trazidos = db.Column(db.Integer, default=0, nullable=True)     # Pallets retornados pela transportadora

    # Relacionamentos
    transportadora = db.relationship('Transportadora', backref='embarques')
    # ✅ CORREÇÃO: Relacionamento base (sem order_by para evitar erros do SQLAlchemy)
    # A ordenação será garantida através da propriedade itens_ordenados
    _itens = db.relationship('EmbarqueItem', backref='embarque', cascade='all, delete-orphan',
                            lazy='dynamic')  # lazy='dynamic' permite ordenação posterior
    # Para carga DIRETA: Uma cotação -> Um embarque
    cotacao = db.relationship('Cotacao', backref='embarque_direto', foreign_keys=[cotacao_id])

    @property
    def itens(self):
        """
        ✅ SOLUÇÃO DEFINITIVA: Propriedade que SEMPRE retorna itens ordenados por ID
        Isso garante ordem estável independente de commits, reloads ou operações do SQLAlchemy
        """
        return self._itens.order_by(EmbarqueItem.id).all()

    def total_notas(self):
        return len([i for i in self.itens if i.status == 'ativo'])

    def total_volumes(self):
        return sum(i.volumes or 0 for i in self.itens if i.status == 'ativo')

    def total_peso_pedidos(self):
        """
        Retorna o peso total dos pedidos contidos no embarque
        ✅ ESTRATÉGIA: Usa peso_total gravado no embarque se disponível (mais confiável)
        Fallback: soma dos itens ativos
        """
        if self.peso_total is not None and self.peso_total > 0:
            return self.peso_total
        return sum(i.peso or 0 for i in self.itens if i.status == 'ativo')

    def total_valor_pedidos(self):
        """
        Retorna o valor total dos pedidos contidos no embarque
        ✅ ESTRATÉGIA: Usa valor_total gravado no embarque se disponível (mais confiável)
        Fallback: soma dos itens ativos
        """
        if self.valor_total is not None and self.valor_total > 0:
            return self.valor_total
        return sum(i.valor or 0 for i in self.itens if i.status == 'ativo')

    def total_pallet_pedidos(self):
        """
        Retorna o total de pallets dos pedidos contidos no embarque
        ✅ CORREÇÃO CRÍTICA: Usa pallet_total gravado no embarque (fonte da verdade)
        Esse valor é calculado usando CadastroPalletizacao e é mais preciso
        """
        # ✅ CORREÇÃO: Verifica apenas se não é None (0 é válido!)
        if self.pallet_total is not None:
            return self.pallet_total

        # Fallback: soma dos itens ativos (sem cálculo por peso)
        return sum(i.pallets or 0 for i in self.itens if i.status == 'ativo')

    @property
    def itens_ativos(self):
        """Retorna apenas os itens ativos do embarque"""
        return [item for item in self.itens if item.status == 'ativo']

    @property
    def transportadora_aceita_nf_pallet(self):
        """Verifica se a transportadora aceita NF de pallet"""
        if self.transportadora:
            return not self.transportadora.nao_aceita_nf_pallet
        return True

    @property
    def saldo_pallets_pendentes(self):
        """
        Calcula saldo de pallets pendentes de faturamento.
        Saldo = Separados - Trazidos - Faturados (NF pallet preenchida)

        Returns:
            int: Quantidade de pallets pendentes (pode ser negativo se houve excesso)
        """
        separados = self.qtd_pallets_separados or 0
        trazidos = self.qtd_pallets_trazidos or 0

        # Pallets faturados = soma das quantidades com NF preenchida
        faturados = 0

        # NF pallet da transportadora
        if self.nf_pallet_transportadora:
            faturados += int(self.qtd_pallet_transportadora or 0)

        # NF pallet de cada cliente (nos itens)
        for item in self.itens_ativos:
            if item.nf_pallet_cliente:
                faturados += int(item.qtd_pallet_cliente or 0)

        return separados - trazidos - faturados

    @property
    def pallets_pendentes(self):
        """
        Verifica se há pallets pendentes de faturamento.

        Returns:
            bool: True se saldo_pallets_pendentes > 0
        """
        return self.saldo_pallets_pendentes > 0

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
    agendamento_confirmado = db.Column(db.Boolean, default=False)  # ✅ NOVO: Status de confirmação do agendamento
    nota_fiscal = db.Column(db.String(20))
    volumes = db.Column(db.Integer, nullable=True)
    peso = db.Column(db.Float)  # Peso do item
    valor = db.Column(db.Float)  # Valor do item

    # === GRUPO 1: PALLETS TEÓRICOS ===
    # Soma de Separacao.pallet do lote (calculado automaticamente via listener)
    # ⚠️ VALOR TEÓRICO - pode divergir da realidade quando pallets têm múltiplos produtos
    pallets = db.Column(db.Float, nullable=True)  # Pallets TEÓRICOS (via CadastroPalletizacao)

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
    
    # ===== NOVOS CAMPOS DE VALORES MÍNIMOS E ICMS =====
    tabela_gris_minimo = db.Column(db.Float, default=0)    # Valor mínimo de GRIS
    tabela_adv_minimo = db.Column(db.Float, default=0)     # Valor mínimo de ADV
    tabela_icms_proprio = db.Column(db.Float, nullable=True)  # ICMS próprio da tabela

    # Campo para armazenar erros de validação
    erro_validacao = db.Column(db.String(500), nullable=True)  # Armazena erros como "CNPJ_DIFERENTE", etc.

    # === GRUPO 2: PALLETS FÍSICOS (Controle Real) ===
    # Para rastrear NF de pallet específica do cliente
    # Preenchidos manualmente, NÃO são afetados pelo cálculo teórico
    # Usados para: Faturamento de NF de pallet para cliente específico
    nf_pallet_cliente = db.Column(db.String(20), nullable=True)       # NF remessa para cliente
    qtd_pallet_cliente = db.Column(db.Float, default=0, nullable=True)  # Qtd na NF cliente
    nf_pallet_referencia = db.Column(db.String(20), nullable=True)    # Qual NF de pallet cobre esta venda
    nf_pallet_origem = db.Column(db.String(10), nullable=True)        # 'EMBARQUE' ou 'ITEM'

    # Para carga FRACIONADA: Uma cotação -> Um item do embarque
    cotacao = db.relationship('Cotacao', backref='embarque_item', foreign_keys=[cotacao_id])

    @property
    def cliente_aceita_nf_pallet(self):
        """Verifica se o cliente aceita NF de pallet (via ContatoAgendamento)"""
        if self.cnpj_cliente:
            from app.cadastros_agendamento.models import ContatoAgendamento
            contato = ContatoAgendamento.query.filter_by(cnpj=self.cnpj_cliente).first()
            if contato:
                return not contato.nao_aceita_nf_pallet
        return True

    @property
    def forma_agendamento(self):
        """Retorna a forma de agendamento do cliente (via ContatoAgendamento)"""
        if self.cnpj_cliente:
            from app.cadastros_agendamento.models import ContatoAgendamento
            contato = ContatoAgendamento.query.filter_by(cnpj=self.cnpj_cliente).first()
            if contato and contato.forma:
                return contato.forma
        return None

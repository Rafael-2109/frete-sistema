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
    placa_veiculo = db.Column(db.String(10))
    paletizado = db.Column(db.Boolean, default=False)
    laudo_anexado = db.Column(db.Boolean, default=False)
    embalagem_aprovada = db.Column(db.Boolean, default=False)
    transporte_aprovado = db.Column(db.Boolean, default=False)
    horario_carregamento = db.Column(db.String(5))
    responsavel_carregamento = db.Column(db.String(100))
    status = db.Column(db.String(20), default='draft')  # 'draft', 'ativo', 'cancelado'
    motivo_cancelamento = db.Column(db.Text, nullable=True)  # Motivo do cancelamento
    cancelado_em = db.Column(db.DateTime, nullable=True)  # Data/hora do cancelamento
    cancelado_por = db.Column(db.String(100), nullable=True)  # Usuário que cancelou
    tipo_cotacao = db.Column(db.String(20), default='Automatica')  # 'Automatica' ou 'Manual'
    valor_total = db.Column(db.Float)
    pallet_total = db.Column(db.Float)
    peso_total = db.Column(db.Float)
    tipo_carga = db.Column(db.String(20))  # 'FRACIONADA' ou 'DIRETA'

    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=False, default='Administrador')

    # Campos do motorista
    nome_motorista = db.Column(db.String(100))
    cpf_motorista = db.Column(db.String(20))
    qtd_pallets = db.Column(db.Integer)
    data_embarque_str = db.Column(db.String(10))  # formato DD/MM/AAAA

    # Campos específicos para carga DIRETA
    # Uma cotação direta está vinculada ao embarque principal
    cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id', name='fk_embarque_cotacao'), nullable=True)
    modalidade = db.Column(db.String(50))  # VALOR, PESO, VAN, etc.
    
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
        return len(self.itens)

    def total_volumes(self):
        return sum(i.volumes or 0 for i in self.itens)

    def total_peso_pedidos(self):
        """Retorna o peso total dos pedidos contidos no embarque"""
        return sum(i.peso or 0 for i in self.itens)

    def total_valor_pedidos(self):
        """Retorna o valor total dos pedidos contidos no embarque"""
        return sum(i.valor or 0 for i in self.itens)

    def total_pallet_pedidos(self):
        """Retorna o total de pallets dos pedidos contidos no embarque"""
        # Como o campo pallet não existe no EmbarqueItem, vamos calcular baseado no peso
        # Assumindo uma média de 500kg por pallet (você pode ajustar conforme necessário)
        peso_total = self.total_peso_pedidos()
        if peso_total > 0:
            return round(peso_total / 500, 2)  # 500kg por pallet
        return 0

    @property
    def status_nfs(self):
        """
        Calcula o status das NFs do embarque:
        - 'NFs pendentes' - Caso algum pedido esteja sem NF
        - 'Pendente Import.' - Caso as NFs estejam preenchidas, porém tenha NF ainda não importada
        - 'NFs Lançadas' - Todas as NFs estão lançadas e validadas pelo faturamento
        """
        if not self.itens:
            return 'NFs pendentes'
        
        # Verifica se há itens sem NF
        itens_sem_nf = [item for item in self.itens if not item.nota_fiscal or item.nota_fiscal.strip() == '']
        if itens_sem_nf:
            return 'NFs pendentes'
        
        # Verifica se há NFs pendentes de importação
        itens_pendentes = [item for item in self.itens if item.erro_validacao and 'NF_PENDENTE_FATURAMENTO' in item.erro_validacao]
        if itens_pendentes:
            return 'Pendente Import.'
        
        # Verifica se há NFs divergentes
        itens_divergentes = [item for item in self.itens if item.erro_validacao and ('NF_DIVERGENTE' in item.erro_validacao or 'CLIENTE_NAO_DEFINIDO' in item.erro_validacao)]
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


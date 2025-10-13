"""
Modelo de Fila para Agendamentos Sendas
Simples e focado apenas no necessário para a planilha
"""

from app import db
from datetime import datetime
from app.portal.sendas.utils_protocolo import gerar_protocolo_sendas

class FilaAgendamentoSendas(db.Model):
    """
    Fila simples para acumular agendamentos Sendas e processar em lote
    """
    __tablename__ = 'fila_agendamento_sendas'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Rastreabilidade da origem
    tipo_origem = db.Column(db.String(20), nullable=False)  # 'separacao', 'nf', 'lote'
    documento_origem = db.Column(db.String(50), nullable=False)  # separacao_lote_id ou numero_nf ou CNPJ do cliente
    
    # Dados essenciais para a planilha Sendas
    cnpj = db.Column(db.String(20), nullable=False, index=True)  # CNPJ do cliente - Deverá ser convertido para o padrão do Sendas
    num_pedido = db.Column(db.String(50), nullable=False)  # Numero do pedido do cliente
    pedido_cliente = db.Column(db.String(100))  # Campo essencial para Sendas
    
    # Produto e quantidade
    cod_produto = db.Column(db.String(50), nullable=False)  # Codigo do produto - Deverá ser convertido para o padrão do Sendas
    nome_produto = db.Column(db.String(255))  # Nome do produto
    quantidade = db.Column(db.Numeric(15, 3), nullable=False) 
    
    # Datas
    data_expedicao = db.Column(db.Date, nullable=False)
    data_agendamento = db.Column(db.Date, nullable=False, index=True)
    
    # Protocolo provisório (mesmo padrão da programacao_lote)
    protocolo = db.Column(db.String(100))  # Protocolo
    
    # Status simples
    status = db.Column(db.String(20), default='pendente', index=True)
    # valores: pendente, processado, erro
    
    # Controle mínimo
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    processado_em = db.Column(db.DateTime)
    
    # Índice para busca eficiente
    __table_args__ = (
        db.Index('idx_fila_sendas_processo', 'status', 'cnpj', 'data_agendamento'),
    )
    
    @classmethod
    def adicionar(cls, tipo_origem, documento_origem, cnpj, num_pedido,
                  cod_produto, quantidade, data_expedicao, data_agendamento,
                  pedido_cliente=None, nome_produto=None, protocolo=None):
        """
        Adiciona item na fila com protocolo provisório ou fornecido

        Args:
            protocolo: Se fornecido, usa este protocolo. Senão, gera novo.
        """
        # Converter datas se vierem como string
        if isinstance(data_expedicao, str):
            from datetime import datetime
            data_expedicao = datetime.strptime(data_expedicao, '%Y-%m-%d').date()
        if isinstance(data_agendamento, str):
            from datetime import datetime
            data_agendamento = datetime.strptime(data_agendamento, '%Y-%m-%d').date()

        # Garantir que data_expedicao não seja None (usar data_agendamento - 1 dia se necessário)
        if data_expedicao is None:
            from datetime import timedelta
            data_expedicao = data_agendamento - timedelta(days=1)

        # Usar protocolo fornecido ou gerar novo
        if not protocolo:
            # Gerar protocolo provisório com nova máscara
            # AG_[CNPJ posições 7-4]_[data ddmmyyyy]_[data ddmmyyyy]
            protocolo = gerar_protocolo_sendas(cnpj, data_agendamento)

        # Verificar duplicata (mesmo documento + produto + num_pedido)
        # ✅ CORREÇÃO: Incluir num_pedido para permitir múltiplos pedidos do mesmo CNPJ com mesmo produto
        existe = cls.query.filter_by(
            tipo_origem=tipo_origem,
            documento_origem=documento_origem,
            cod_produto=cod_produto,
            num_pedido=num_pedido,  # ✅ ADICIONADO para diferenciar pedidos
            status='pendente'
        ).first()

        if existe:
            # Atualizar quantidade e datas
            existe.quantidade = quantidade
            existe.data_expedicao = data_expedicao
            existe.data_agendamento = data_agendamento
            existe.protocolo = protocolo
            # ✅ CORREÇÃO: Não fazer commit aqui - deixar para a transação externa
            # db.session.commit()
            return existe

        # Criar novo
        novo = cls(
            tipo_origem=tipo_origem,
            documento_origem=documento_origem,
            cnpj=cnpj,
            num_pedido=num_pedido,
            pedido_cliente=pedido_cliente,
            cod_produto=cod_produto,
            nome_produto=nome_produto,
            quantidade=quantidade,
            data_expedicao=data_expedicao,
            data_agendamento=data_agendamento,
            protocolo=protocolo
        )

        db.session.add(novo)
        # ✅ CORREÇÃO: Não fazer commit aqui - deixar para a transação externa
        # db.session.commit()
        return novo
    
    @classmethod
    def obter_para_processar(cls):
        """
        Obtém todos os itens pendentes agrupados por CNPJ e data
        """
        itens = cls.query.filter_by(status='pendente').order_by(
            cls.cnpj,
            cls.data_agendamento,
            cls.num_pedido,
            cls.cod_produto
        ).all()
        
        # Agrupar por CNPJ + data_agendamento
        grupos = {}
        for item in itens:
            chave = f"{item.cnpj}_{item.data_agendamento.isoformat()}"
            if chave not in grupos:
                grupos[chave] = {
                    'cnpj': item.cnpj,
                    'data_agendamento': item.data_agendamento,
                    'protocolo': item.protocolo,
                    'itens': []
                }
            grupos[chave]['itens'].append(item)
        
        return grupos
    
    @classmethod
    def marcar_processados(cls, cnpj, data_agendamento):
        """
        Marca todos os itens de um CNPJ/data como processados
        """
        itens = cls.query.filter_by(
            cnpj=cnpj,
            data_agendamento=data_agendamento,
            status='pendente'
        ).all()
        
        for item in itens:
            item.status = 'processado'
            item.processado_em = datetime.utcnow()
        
        db.session.commit()
        return len(itens)
    
    @classmethod
    def contar_pendentes(cls):
        """
        Conta itens pendentes por CNPJ
        """
        from sqlalchemy import func
        
        resultado = db.session.query(
            cls.cnpj,
            func.count(cls.id).label('total')
        ).filter(
            cls.status == 'pendente'
        ).group_by(
            cls.cnpj
        ).all()
        
        return {cnpj: total for cnpj, total in resultado}
    
    @classmethod
    def limpar_processados(cls, dias=7):
        """
        Remove itens processados há mais de X dias
        """
        from datetime import timedelta
        
        limite = datetime.utcnow() - timedelta(days=dias)
        
        cls.query.filter(
            cls.status == 'processado',
            cls.processado_em < limite
        ).delete()
        
        db.session.commit()
    
    def __repr__(self):
        return f'<FilaSendas {self.cnpj} - {self.cod_produto} - {self.quantidade}>'
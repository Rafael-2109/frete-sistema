from app import db
from datetime import datetime

class Frete(db.Model):
    """
    Modelo principal para registro de fretes
    1 Frete = 1 CTe = 1 Valor = 1 Vencimento = 1 CNPJ = 1 Embarque
    Mas pode ter N pedidos e N NFs por frete
    """
    __tablename__ = 'fretes'

    id = db.Column(db.Integer, primary_key=True)
    embarque_id = db.Column(db.Integer, db.ForeignKey('embarques.id'), nullable=False)
    cnpj_cliente = db.Column(db.String(20), nullable=False, index=True)
    nome_cliente = db.Column(db.String(255), nullable=False)
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=False)
    
    # Dados básicos do frete
    tipo_carga = db.Column(db.String(20), nullable=False)  # 'FRACIONADA' ou 'DIRETA'
    modalidade = db.Column(db.String(50), nullable=False)  # VALOR, PESO, VAN, etc.
    uf_destino = db.Column(db.String(2), nullable=False)
    cidade_destino = db.Column(db.String(100), nullable=False)
    
    # Totais das NFs deste CNPJ no embarque
    peso_total = db.Column(db.Float, nullable=False)
    valor_total_nfs = db.Column(db.Float, nullable=False)
    quantidade_nfs = db.Column(db.Integer, nullable=False)
    numeros_nfs = db.Column(db.Text, nullable=False)  # Lista das NFs separadas por vírgula
    
    # Dados da tabela utilizada (copiados do embarque/embarque_item)
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
    tabela_icms_destino = db.Column(db.Float)
    
    # ===== NOVOS CAMPOS DE VALORES MÍNIMOS E ICMS =====
    tabela_gris_minimo = db.Column(db.Float, default=0)    # Valor mínimo de GRIS
    tabela_adv_minimo = db.Column(db.Float, default=0)     # Valor mínimo de ADV
    tabela_icms_proprio = db.Column(db.Float, nullable=True)  # ICMS próprio da tabela
    
    # OS 4 TIPOS DE VALORES DO FRETE
    valor_cotado = db.Column(db.Float, nullable=False)  # Calculado automaticamente pela tabela
    valor_cte = db.Column(db.Float)  # Valor cobrado pela transportadora
    valor_considerado = db.Column(db.Float)  # Valor que consideramos válido (inicialmente = valor_cotado)
    valor_pago = db.Column(db.Float)  # Valor que efetivamente pagamos
    
    # Dados do CTe
    numero_cte = db.Column(db.String(255), index=True)
    data_emissao_cte = db.Column(db.Date)
    vencimento = db.Column(db.Date)
    
    # Fatura de frete (uma fatura pode ter N fretes)
    fatura_frete_id = db.Column(db.Integer, db.ForeignKey('faturas_frete.id'))
    
    # Status e aprovação
    status = db.Column(db.String(20), default='PENDENTE')  # PENDENTE, EM_TRATATIVA, APROVADO, REJEITADO, PAGO, CANCELADO
    requer_aprovacao = db.Column(db.Boolean, default=False)
    aprovado_por = db.Column(db.String(100))
    aprovado_em = db.Column(db.DateTime)
    observacoes_aprovacao = db.Column(db.Text)
    
    # Controle
    considerar_diferenca = db.Column(db.Boolean, default=False)  # Para lançar na conta corrente mesmo com diferença até R$ 5,00
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=False)
    lancado_em = db.Column(db.DateTime)
    lancado_por = db.Column(db.String(100))
    
    # Relacionamentos
    embarque = db.relationship('Embarque', backref='fretes')
    transportadora = db.relationship('Transportadora', backref='fretes')
    fatura_frete = db.relationship('FaturaFrete', backref='fretes')
    despesas_extras = db.relationship('DespesaExtra', backref='frete', cascade='all, delete-orphan')

    def diferenca_cotado_cte(self):
        """Retorna a diferença entre valor cotado e valor CTe"""
        if self.valor_cte and self.valor_cotado:
            return self.valor_cte - self.valor_cotado
        return 0

    def diferenca_considerado_pago(self):
        """Retorna a diferença entre valor considerado e valor pago (para conta corrente)"""
        if self.valor_pago and self.valor_considerado:
            return self.valor_pago - self.valor_considerado
        return 0

    def classificacao_valor_pago_considerado(self):
        """Classifica a relação entre valor pago e considerado"""
        if not self.valor_pago or not self.valor_considerado:
            return ""
        
        if self.valor_pago < self.valor_considerado:
            return "Valor abaixo da tabela"
        elif self.valor_pago > self.valor_considerado:
            return "Transportadora deve para a Nacom"
        else:
            return "Valores iguais"

    def classificacao_valor_cte_cotado(self):
        """Classifica a relação entre valor CTe e cotado"""
        if not self.valor_cte or not self.valor_cotado:
            return ""
        
        if self.valor_cte > self.valor_cotado:
            return "Cobrança maior que a Cotação"
        elif self.valor_cte < self.valor_cotado:
            return "Cobrança menor que a Cotação"
        else:
            return "Valores iguais"

    def requer_aprovacao_por_valor(self):
        """
        Verifica se requer aprovação baseado nas regras de R$ 5,00
        - Diferença > R$ 5,00 entre Valor Considerado e Valor Pago: EM_TRATATIVA 
        - Diferença > R$ 5,00 entre Valor Considerado e Valor Cotado: EM_TRATATIVA
        """
        requer = False
        motivos = []
        
        # Verifica diferença entre valor considerado e valor pago
        if self.valor_considerado and self.valor_pago:
            diferenca = abs(self.valor_considerado - self.valor_pago)
            if diferenca > 5.00:
                requer = True
                if self.valor_pago > self.valor_considerado:
                    motivos.append(f"Valor Pago (R$ {self.valor_pago:.2f}) superior ao Considerado (R$ {self.valor_considerado:.2f}) em R$ {diferenca:.2f}")
                else:
                    motivos.append(f"Valor Considerado (R$ {self.valor_considerado:.2f}) superior ao Pago (R$ {self.valor_pago:.2f}) em R$ {diferenca:.2f}")
        
        # Verifica diferença entre valor considerado e valor cotado
        if self.valor_considerado and self.valor_cotado:
            diferenca = abs(self.valor_considerado - self.valor_cotado)
            if diferenca > 5.00:
                requer = True
                if self.valor_considerado > self.valor_cotado:
                    motivos.append(f"Valor Considerado (R$ {self.valor_considerado:.2f}) superior ao Cotado (R$ {self.valor_cotado:.2f}) em R$ {diferenca:.2f}")
                else:
                    motivos.append(f"Valor Cotado (R$ {self.valor_cotado:.2f}) superior ao Considerado (R$ {self.valor_considerado:.2f}) em R$ {diferenca:.2f}")
        
        return requer, motivos

    def deve_lancar_conta_corrente(self):
        """
        Verifica se deve lançar na conta corrente baseado nas regras:
        - Diferença até R$ 5,00 E flag 'considerar_diferenca' = True: lança
        - Diferença até R$ 5,00 E flag 'considerar_diferenca' = False: não lança
        - Diferença > R$ 5,00: só lança após aprovação
        """
        if not self.valor_considerado or not self.valor_pago:
            return False, "Valores não informados"
        
        diferenca = abs(self.valor_considerado - self.valor_pago)
        
        if diferenca <= 5.00:
            if self.considerar_diferenca:
                return True, f"Diferença de R$ {diferenca:.2f} será lançada (flag ativa)"
            else:
                return False, f"Diferença de R$ {diferenca:.2f} ignorada (flag inativa)"
        else:
            if self.status == 'APROVADO':
                return True, f"Diferença de R$ {diferenca:.2f} aprovada"
            else:
                return False, f"Diferença de R$ {diferenca:.2f} requer aprovação"

    def __repr__(self):
        return f'<Frete {self.id} - {self.nome_cliente} - CTe: {self.numero_cte}>'


class FaturaFrete(db.Model):
    """
    Modelo para faturas de frete emitidas pelas transportadoras
    1 Fatura pode ter N CTes de N CNPJs
    """
    __tablename__ = 'faturas_frete'

    id = db.Column(db.Integer, primary_key=True)
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=False)
    numero_fatura = db.Column(db.String(50), nullable=False, index=True)
    data_emissao = db.Column(db.Date, nullable=False)
    valor_total_fatura = db.Column(db.Float, nullable=False)
    vencimento = db.Column(db.Date)
    
    # Arquivo da fatura
    arquivo_pdf = db.Column(db.String(255))  # Caminho para o arquivo PDF da fatura
    
    # Status da conferência
    status_conferencia = db.Column(db.String(20), default='PENDENTE')  # PENDENTE, EM_CONFERENCIA, CONFERIDO
    conferido_por = db.Column(db.String(100))
    conferido_em = db.Column(db.DateTime)
    observacoes_conferencia = db.Column(db.Text)
    
    # Controle
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=False)
    
    # Relacionamentos
    transportadora = db.relationship('Transportadora', backref='faturas_frete')

    def total_fretes(self):
        """Retorna o total de fretes desta fatura"""
        return len(self.fretes)

    def valor_total_fretes(self):
        """Retorna o valor total dos fretes desta fatura"""
        return sum(f.valor_cte or 0 for f in self.fretes)
    
    def total_despesas_extras(self):
        """Retorna o total de despesas extras VINCULADAS a esta fatura pelo número"""
        # ✅ CORRIGIDO: Busca despesas que têm este número de fatura nas observações
        despesas = DespesaExtra.query.filter(
            DespesaExtra.observacoes.contains(f'Fatura: {self.numero_fatura}')
        ).all()
        return len(despesas)
    
    def valor_total_despesas_extras(self):
        """Retorna o valor total das despesas extras VINCULADAS a esta fatura pelo número"""
        # ✅ CORRIGIDO: Busca despesas que têm este número de fatura nas observações
        despesas = DespesaExtra.query.filter(
            DespesaExtra.observacoes.contains(f'Fatura: {self.numero_fatura}')
        ).all()
        return sum(despesa.valor_despesa for despesa in despesas)
    
    def todas_despesas_extras(self):
        """Retorna todas as despesas extras VINCULADAS a esta fatura pelo número"""
        # ✅ CORRIGIDO: Busca despesas que têm este número de fatura nas observações
        return DespesaExtra.query.filter(
            DespesaExtra.observacoes.contains(f'Fatura: {self.numero_fatura}')
        ).all()

    def __repr__(self):
        return f'<FaturaFrete {self.numero_fatura} - {self.transportadora.razao_social if self.transportadora else "N/A"}>'


class DespesaExtra(db.Model):
    """
    Modelo para despesas extras dos fretes
    N despesas extras / 1 frete
    """
    __tablename__ = 'despesas_extras'

    id = db.Column(db.Integer, primary_key=True)
    frete_id = db.Column(db.Integer, db.ForeignKey('fretes.id'), nullable=False)
    
    # Tipos de despesa (conforme readme.md)
    TIPOS_DESPESA = [
        'REENTREGA', 'TDE', 'PERNOITE', 'DEVOLUÇÃO', 'DIARIA',
        'COMPLEMENTO DE FRETE', 'COMPRA/AVARIA', 'TRANSFERENCIA',
        'DESCARGA', 'ESTACIONAMENTO', 'CARRO DEDICADO', 'ARMAZENAGEM'
    ]
    
    # Setores responsáveis (conforme readme.md)
    SETORES_RESPONSAVEIS = [
        'COMERCIAL', 'QUALIDADE', 'FISCAL', 'FINANCEIRO',
        'LOGISTICA', 'COMPRAS'
    ]
    
    # Motivos das despesas (conforme readme.md)
    MOTIVOS_DESPESA = [
        'PEDIDO EM DESACORDO', 'PROBLEMA NO CLIENTE', 'SEM AGENDA',
        'DIVERGENCIA DE CADASTRO', 'ARQUIVO XML', 'FORA DO PADRÃO',
        'FALTA MERCADORIA', 'ATRASO', 'INVERSÃO', 'EXCESSO DE VEICULO',
        'VAZAMENTO', 'AUTORIZACAO INDEVIDA', 'PROBLEMA NO BOLETO',
        'COLETA CANCELADA', 'COLETA DE IMPROPRIOS', 'EXIGENCIA TRANSPORTADORA',
        'AJUDANTE DESCARGA', 'DEMORA COLETA', 'COMPLEMENTO DE FRETE',
        'DIVERGENTE IMPOSTO NACOM', 'ENTREGA 2° ANDAR', 'ENTREGA NOTURNA',
        'CUSTO DO PRODUTO', 'DEMORA RECEBIMENTO', 'SEM MONITORAMENTO', 'AVARIA'
    ]
    
    tipo_despesa = db.Column(db.String(50), nullable=False)
    setor_responsavel = db.Column(db.String(20), nullable=False)
    motivo_despesa = db.Column(db.String(50), nullable=False)
    
    # Documento da despesa
    tipo_documento = db.Column(db.String(20), nullable=False)  # CTe, NFS, RECIBO, etc.
    numero_documento = db.Column(db.String(50), nullable=False)
    
    # Valores
    valor_despesa = db.Column(db.Float, nullable=False)
    vencimento_despesa = db.Column(db.Date)
    
    # Observações
    observacoes = db.Column(db.Text)
    
    # Controle
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<DespesaExtra {self.tipo_despesa} - R$ {self.valor_despesa}>'


class ContaCorrenteTransportadora(db.Model):
    """
    Modelo para conta corrente por transportadora
    Controla diferenças entre valores pagos e considerados
    """
    __tablename__ = 'conta_corrente_transportadoras'

    id = db.Column(db.Integer, primary_key=True)
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=False)
    frete_id = db.Column(db.Integer, db.ForeignKey('fretes.id'), nullable=False)
    
    # Tipo de movimentação
    tipo_movimentacao = db.Column(db.String(20), nullable=False)  # CREDITO, DEBITO, COMPENSACAO
    
    # Valores
    valor_diferenca = db.Column(db.Float, nullable=False)  # Diferença entre valor_pago e valor_considerado
    valor_credito = db.Column(db.Float, default=0)  # Para créditos a favor da empresa
    valor_debito = db.Column(db.Float, default=0)  # Para débitos a favor da transportadora
    
    # Descrição da movimentação
    descricao = db.Column(db.String(255), nullable=False)
    observacoes = db.Column(db.Text)
    
    # Status
    status = db.Column(db.String(20), default='ATIVO')  # ATIVO, COMPENSADO, DESCONSIDERADO
    compensado_em = db.Column(db.DateTime)
    compensado_por = db.Column(db.String(100))
    compensacao_frete_id = db.Column(db.Integer, db.ForeignKey('fretes.id'))  # Frete usado para compensação
    
    # Controle
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=False)
    
    # Relacionamentos
    transportadora = db.relationship('Transportadora', backref='conta_corrente')
    frete = db.relationship('Frete', foreign_keys=[frete_id], backref='movimentacoes_conta_corrente')
    frete_compensacao = db.relationship('Frete', foreign_keys=[compensacao_frete_id])

    def __repr__(self):
        return f'<ContaCorrente {self.transportadora.nome if self.transportadora else "N/A"} - {self.tipo_movimentacao} R$ {abs(self.valor_diferenca)}>'


class AprovacaoFrete(db.Model):
    """
    Modelo para controle de aprovações de fretes
    """
    __tablename__ = 'aprovacoes_frete'

    id = db.Column(db.Integer, primary_key=True)
    frete_id = db.Column(db.Integer, db.ForeignKey('fretes.id'), nullable=False)
    
    # Dados da aprovação
    status = db.Column(db.String(20), default='PENDENTE')  # PENDENTE, APROVADO, REJEITADO
    solicitado_por = db.Column(db.String(100), nullable=False)
    solicitado_em = db.Column(db.DateTime, default=datetime.utcnow)
    motivo_solicitacao = db.Column(db.Text)
    
    # Dados do aprovador
    aprovador = db.Column(db.String(100))
    aprovado_em = db.Column(db.DateTime)
    observacoes_aprovacao = db.Column(db.Text)
    
    # Relacionamentos
    frete = db.relationship('Frete', backref='aprovacao')

    def __repr__(self):
        return f'<AprovacaoFrete {self.frete_id} - {self.status}>'


# Manter o modelo antigo para compatibilidade (será migrado)
class FreteLancado(db.Model):
    __tablename__ = 'fretes_lancados'

    id = db.Column(db.Integer, primary_key=True)
    embarque_id = db.Column(db.Integer, db.ForeignKey('embarques.id'), nullable=False)
    nota_fiscal = db.Column(db.String(20), nullable=False)
    cliente = db.Column(db.String(120), nullable=False)
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=False)
    tipo_carga = db.Column(db.String(20), nullable=False)  # 'FRACIONADA' ou 'DIRETA'
    modalidade = db.Column(db.String(50), nullable=False)  # VALOR, PESO, VAN, etc.
    uf_destino = db.Column(db.String(2), nullable=False)
    cidade_destino = db.Column(db.String(100), nullable=False)

    peso = db.Column(db.Float, nullable=False)
    valor_nf = db.Column(db.Float, nullable=False)
    valor_frete = db.Column(db.Float, nullable=False)

    cte = db.Column(db.String(50))  # número do CTE
    vencimento = db.Column(db.Date)
    fatura = db.Column(db.String(50))
    divergencia = db.Column(db.String(255))

    criado_em = db.Column(db.DateTime, server_default=db.func.now())

    embarque = db.relationship('Embarque', backref='fretes_lancados')
    transportadora = db.relationship('Transportadora')

"""
Modelos do Data Warehouse para o módulo BI
Tabelas otimizadas para análise e relatórios de fretes
"""
from app import db
from datetime import datetime
from sqlalchemy import Index
from sqlalchemy.ext.hybrid import hybrid_property
from app.utils.timezone import agora_utc_naive

class BiFreteAgregado(db.Model):
    """
    Tabela agregada de fretes para análise rápida
    Atualizada diariamente via ETL
    """
    __tablename__ = 'bi_frete_agregado'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Dimensões temporais
    data_referencia = db.Column(db.Date, nullable=False, index=True)
    ano = db.Column(db.Integer, nullable=False, index=True)
    mes = db.Column(db.Integer, nullable=False, index=True)
    trimestre = db.Column(db.Integer, nullable=False)
    semana_ano = db.Column(db.Integer, nullable=False)
    dia_semana = db.Column(db.Integer, nullable=False)
    
    # Dimensões de transportadora
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), index=True)
    transportadora_nome = db.Column(db.String(120))
    transportadora_cnpj = db.Column(db.String(20))
    transportadora_uf = db.Column(db.String(2))
    transportadora_optante = db.Column(db.Boolean, default=False)
    
    # Dimensões de cliente
    cliente_cnpj = db.Column(db.String(20), index=True)
    cliente_nome = db.Column(db.String(255))
    cliente_cidade = db.Column(db.String(100))
    cliente_uf = db.Column(db.String(2), index=True)
    cliente_regiao = db.Column(db.String(20))  # Norte, Sul, Sudeste, etc
    
    # Dimensões de rota
    origem_uf = db.Column(db.String(2), default='SP')
    destino_uf = db.Column(db.String(2), index=True)
    destino_cidade = db.Column(db.String(100))
    destino_regiao = db.Column(db.String(20))
    distancia_km = db.Column(db.Float)  # Calculada via API ou tabela
    
    # Dimensões de carga
    tipo_carga = db.Column(db.String(20))  # FRACIONADA, DIRETA
    modalidade = db.Column(db.String(50))  # VALOR, PESO, VAN, etc
    tipo_veiculo = db.Column(db.String(50))  # Truck, Carreta, etc
    
    # Métricas de volume
    qtd_embarques = db.Column(db.Integer, default=0)
    qtd_nfs = db.Column(db.Integer, default=0)
    qtd_ctes = db.Column(db.Integer, default=0)
    peso_total_kg = db.Column(db.Float, default=0)
    valor_total_nf = db.Column(db.Float, default=0)
    qtd_pallets = db.Column(db.Float, default=0)
    
    # Métricas de valores de frete (4 tipos principais)
    valor_cotado_total = db.Column(db.Float, default=0)
    valor_cte_total = db.Column(db.Float, default=0)
    valor_considerado_total = db.Column(db.Float, default=0)
    valor_pago_total = db.Column(db.Float, default=0)
    
    # Métricas de despesas extras
    qtd_despesas_extras = db.Column(db.Integer, default=0)
    valor_despesas_extras = db.Column(db.Float, default=0)
    valor_reentrega = db.Column(db.Float, default=0)
    valor_tde = db.Column(db.Float, default=0)
    valor_devolucao = db.Column(db.Float, default=0)
    valor_complemento = db.Column(db.Float, default=0)
    valor_outras_despesas = db.Column(db.Float, default=0)
    
    # Métricas de divergência
    divergencia_cotado_cte = db.Column(db.Float, default=0)
    divergencia_considerado_pago = db.Column(db.Float, default=0)
    qtd_aprovacoes = db.Column(db.Integer, default=0)
    qtd_rejeicoes = db.Column(db.Integer, default=0)
    qtd_em_tratativa = db.Column(db.Integer, default=0)
    
    # Métricas de prazo
    lead_time_medio = db.Column(db.Float)  # Dias entre expedição e entrega
    prazo_pagamento_medio = db.Column(db.Float)  # Dias para pagamento
    
    # Métricas calculadas (KPIs)
    custo_por_kg = db.Column(db.Float)
    custo_por_real_faturado = db.Column(db.Float)
    custo_por_km = db.Column(db.Float)
    percentual_despesa_extra = db.Column(db.Float)
    percentual_divergencia = db.Column(db.Float)
    
    # Controle ETL
    processado_em = db.Column(db.DateTime, default=agora_utc_naive)
    versao_etl = db.Column(db.String(10))
    
    # Índices compostos para performance
    __table_args__ = (
        Index('idx_bi_periodo_transp', 'data_referencia', 'transportadora_id'),
        Index('idx_bi_periodo_regiao', 'data_referencia', 'destino_regiao'),
        Index('idx_bi_ano_mes', 'ano', 'mes'),
        Index('idx_bi_cliente_periodo', 'cliente_cnpj', 'data_referencia'),
    )
    
    @hybrid_property
    def eficiencia_transportadora(self):
        """Score de eficiência da transportadora (0-100)"""
        if not self.valor_pago_total:
            return 0
        
        score = 100
        # Penaliza por divergências
        if self.valor_cotado_total:
            score -= abs(self.divergencia_cotado_cte / self.valor_cotado_total) * 20
        # Penaliza por despesas extras
        if self.percentual_despesa_extra:
            score -= self.percentual_despesa_extra * 2
        # Penaliza por rejeições
        if self.qtd_aprovacoes + self.qtd_rejeicoes > 0:
            score -= (self.qtd_rejeicoes / (self.qtd_aprovacoes + self.qtd_rejeicoes)) * 30
        
        return max(0, min(100, score))
    
    def __repr__(self):
        return f'<BiFreteAgregado {self.data_referencia} - {self.transportadora_nome}>'


class BiDespesaDetalhada(db.Model):
    """
    Tabela detalhada de despesas extras para análise de causas
    """
    __tablename__ = 'bi_despesa_detalhada'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Dimensões temporais
    data_referencia = db.Column(db.Date, nullable=False, index=True)
    ano = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    
    # Dimensões de classificação (valores do modelo DespesaExtra)
    tipo_despesa = db.Column(db.String(50), nullable=False, index=True)
    setor_responsavel = db.Column(db.String(20), nullable=False, index=True)
    motivo_despesa = db.Column(db.String(100), nullable=False, index=True)
    
    # Dimensões relacionais
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'))
    transportadora_nome = db.Column(db.String(120))
    cliente_cnpj = db.Column(db.String(20))
    cliente_nome = db.Column(db.String(255))
    destino_uf = db.Column(db.String(2))
    destino_cidade = db.Column(db.String(100))
    
    # Métricas
    qtd_ocorrencias = db.Column(db.Integer, default=0)
    valor_total = db.Column(db.Float, default=0)
    valor_medio = db.Column(db.Float, default=0)
    valor_minimo = db.Column(db.Float)
    valor_maximo = db.Column(db.Float)
    
    # Análise de causa raiz
    percentual_sobre_frete = db.Column(db.Float)
    recorrencia_mensal = db.Column(db.Integer)  # Quantos meses teve ocorrência
    tendencia = db.Column(db.String(20))  # CRESCENTE, ESTAVEL, DECRESCENTE
    
    # Controle
    processado_em = db.Column(db.DateTime, default=agora_utc_naive)
    
    __table_args__ = (
        Index('idx_bi_despesa_periodo', 'data_referencia', 'tipo_despesa'),
        Index('idx_bi_despesa_setor', 'setor_responsavel', 'data_referencia'),
    )
    
    def __repr__(self):
        return f'<BiDespesaDetalhada {self.tipo_despesa} - {self.setor_responsavel}>'


class BiPerformanceTransportadora(db.Model):
    """
    Tabela de performance consolidada por transportadora
    """
    __tablename__ = 'bi_performance_transportadora'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Período de análise
    periodo_inicio = db.Column(db.Date, nullable=False)
    periodo_fim = db.Column(db.Date, nullable=False)
    tipo_periodo = db.Column(db.String(20))  # MENSAL, TRIMESTRAL, ANUAL
    
    # Transportadora
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), index=True)
    transportadora_nome = db.Column(db.String(120))
    transportadora_cnpj = db.Column(db.String(20))
    
    # Volume operacional
    total_embarques = db.Column(db.Integer, default=0)
    total_nfs = db.Column(db.Integer, default=0)
    total_peso_kg = db.Column(db.Float, default=0)
    total_valor_faturado = db.Column(db.Float, default=0)
    
    # Performance financeira
    valor_total_frete = db.Column(db.Float, default=0)
    valor_total_despesas = db.Column(db.Float, default=0)
    custo_medio_por_kg = db.Column(db.Float)
    custo_medio_por_nf = db.Column(db.Float)
    margem_divergencia_media = db.Column(db.Float)
    
    # Conta corrente
    saldo_conta_corrente = db.Column(db.Float, default=0)
    qtd_creditos = db.Column(db.Integer, default=0)
    qtd_debitos = db.Column(db.Integer, default=0)
    
    # Qualidade de serviço
    percentual_entregas_prazo = db.Column(db.Float)
    percentual_com_despesa_extra = db.Column(db.Float)
    qtd_reclamacoes = db.Column(db.Integer, default=0)
    score_qualidade = db.Column(db.Float)  # 0-100
    
    # Rankings
    ranking_custo = db.Column(db.Integer)  # Posição no ranking de custo
    ranking_volume = db.Column(db.Integer)  # Posição no ranking de volume
    ranking_qualidade = db.Column(db.Integer)  # Posição no ranking de qualidade
    ranking_geral = db.Column(db.Integer)  # Posição no ranking geral
    
    # Análise comparativa
    variacao_periodo_anterior = db.Column(db.Float)  # % variação vs período anterior
    tendencia = db.Column(db.String(20))  # MELHORA, PIORA, ESTAVEL
    
    # Recomendações
    recomendacao = db.Column(db.Text)  # Sugestões automáticas baseadas em análise
    
    # Controle
    calculado_em = db.Column(db.DateTime, default=agora_utc_naive)
    
    __table_args__ = (
        Index('idx_bi_perf_transp_periodo', 'transportadora_id', 'periodo_inicio', 'periodo_fim'),
        db.UniqueConstraint('transportadora_id', 'periodo_inicio', 'periodo_fim', 'tipo_periodo', 
                           name='uq_bi_perf_transportadora_periodo'),
    )
    
    def __repr__(self):
        return f'<BiPerformanceTransportadora {self.transportadora_nome} - Score: {self.score_qualidade}>'


class BiAnaliseRegional(db.Model):
    """
    Análise de custos e performance por região
    """
    __tablename__ = 'bi_analise_regional'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Período
    data_referencia = db.Column(db.Date, nullable=False, index=True)
    ano = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    
    # Região
    regiao = db.Column(db.String(20), nullable=False, index=True)  # Norte, Sul, etc
    uf = db.Column(db.String(2), nullable=False, index=True)
    cidade = db.Column(db.String(100), index=True)
    codigo_ibge = db.Column(db.String(10))
    
    # Volume
    qtd_entregas = db.Column(db.Integer, default=0)
    peso_total_kg = db.Column(db.Float, default=0)
    valor_total_faturado = db.Column(db.Float, default=0)
    
    # Custos
    custo_total_frete = db.Column(db.Float, default=0)
    custo_medio_por_kg = db.Column(db.Float)
    custo_medio_por_entrega = db.Column(db.Float)
    
    # Transportadoras
    qtd_transportadoras_ativas = db.Column(db.Integer, default=0)
    transportadora_principal_id = db.Column(db.Integer)
    transportadora_principal_nome = db.Column(db.String(120))
    percentual_transportadora_principal = db.Column(db.Float)
    
    # Performance
    lead_time_medio = db.Column(db.Float)
    percentual_no_prazo = db.Column(db.Float)
    percentual_com_problema = db.Column(db.Float)
    
    # Comparativos
    variacao_mes_anterior = db.Column(db.Float)
    posicao_ranking_custo = db.Column(db.Integer)
    posicao_ranking_volume = db.Column(db.Integer)
    
    # Controle
    processado_em = db.Column(db.DateTime, default=agora_utc_naive)
    
    __table_args__ = (
        Index('idx_bi_regional_periodo', 'data_referencia', 'regiao'),
        Index('idx_bi_regional_uf', 'uf', 'data_referencia'),
        db.UniqueConstraint('data_referencia', 'uf', 'cidade', name='uq_bi_regional_local_periodo'),
    )
    
    def __repr__(self):
        return f'<BiAnaliseRegional {self.regiao}/{self.uf} - {self.data_referencia}>'


class BiIndicadorMensal(db.Model):
    """
    Indicadores consolidados mensais para dashboard executivo
    """
    __tablename__ = 'bi_indicador_mensal'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Período
    ano = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    
    # KPIs Principais
    custo_total_frete = db.Column(db.Float, default=0)
    custo_total_despesas = db.Column(db.Float, default=0)
    economia_realizada = db.Column(db.Float, default=0)  # Diferença entre cotado e pago
    
    # Volumes
    total_embarques = db.Column(db.Integer, default=0)
    total_peso_kg = db.Column(db.Float, default=0)
    total_valor_faturado = db.Column(db.Float, default=0)
    
    # Médias
    custo_medio_por_kg = db.Column(db.Float)
    custo_medio_por_embarque = db.Column(db.Float)
    ticket_medio_embarque = db.Column(db.Float)
    
    # Performance
    percentual_no_prazo = db.Column(db.Float)
    percentual_com_divergencia = db.Column(db.Float)
    percentual_aprovado = db.Column(db.Float)
    
    # Top performers
    top_transportadora_volume = db.Column(db.String(120))
    top_transportadora_custo = db.Column(db.String(120))
    top_regiao_volume = db.Column(db.String(20))
    top_regiao_custo = db.Column(db.String(20))
    
    # Variações
    variacao_mes_anterior = db.Column(db.Float)
    variacao_ano_anterior = db.Column(db.Float)
    
    # Meta e realizado
    meta_custo = db.Column(db.Float)
    percentual_atingimento_meta = db.Column(db.Float)
    
    # Controle
    calculado_em = db.Column(db.DateTime, default=agora_utc_naive)
    
    __table_args__ = (
        db.UniqueConstraint('ano', 'mes', name='uq_bi_indicador_periodo'),
    )
    
    def __repr__(self):
        return f'<BiIndicadorMensal {self.ano}/{self.mes}>'


# Função helper para mapear região
def get_regiao_by_uf(uf):
    """Retorna a região baseada na UF"""
    regioes = {
        'Norte': ['AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO'],
        'Nordeste': ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'],
        'Centro-Oeste': ['DF', 'GO', 'MT', 'MS'],
        'Sudeste': ['ES', 'MG', 'RJ', 'SP'],
        'Sul': ['PR', 'RS', 'SC']
    }
    
    for regiao, estados in regioes.items():
        if uf in estados:
            return regiao
    return 'Indefinido'
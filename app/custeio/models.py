"""
Modelos do modulo de Custeio
"""
from app import db
from datetime import datetime, date


class CustoMensal(db.Model):
    """
    Historico de custos mensais por produto
    Fechamento mensal manual via botao na UI

    Ordem de processamento:
    1. COMPRADOS   -> Custo = (Valor - ICMS - PIS - COFINS) / Qtd
    2. INTERMEDIARIOS -> Custo BOM usando custos de COMPRADOS
    3. ACABADOS    -> Custo BOM usando COMPRADOS + INTERMEDIARIOS
    """
    __tablename__ = 'custo_mensal'

    id = db.Column(db.Integer, primary_key=True)

    # Periodo de referencia
    mes = db.Column(db.Integer, nullable=False, index=True)  # 1-12
    ano = db.Column(db.Integer, nullable=False, index=True)  # 2024, 2025...

    # Produto (FK logica para CadastroPalletizacao)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255), nullable=True)

    # Classificacao do produto no momento do fechamento
    # Valores: COMPRADO, INTERMEDIARIO, ACABADO
    tipo_produto = db.Column(db.String(20), nullable=False)

    # ============================================
    # CUSTOS CALCULADOS
    # ============================================

    # Custo liquido medio (compras do mes)
    # Formula: (Soma valores - ICMS - PIS - COFINS) / Soma quantidades
    custo_liquido_medio = db.Column(db.Numeric(15, 6), nullable=True)

    # Custo medio do estoque
    # Formula: (custo_estoque_inicial + custo_compras) / (qtd_inicial + qtd_compras)
    custo_medio_estoque = db.Column(db.Numeric(15, 6), nullable=True)

    # Ultimo custo (ultima compra do mes)
    ultimo_custo = db.Column(db.Numeric(15, 6), nullable=True)

    # Custo BOM (para intermediarios e acabados)
    # Calculado pela explosao da lista de materiais
    custo_bom = db.Column(db.Numeric(15, 6), nullable=True)

    # ============================================
    # QUANTIDADES PARA CALCULO
    # ============================================

    # Estoque inicial do mes
    qtd_estoque_inicial = db.Column(db.Numeric(15, 3), nullable=True, default=0)
    custo_estoque_inicial = db.Column(db.Numeric(15, 2), nullable=True, default=0)

    # Compras do mes
    qtd_comprada = db.Column(db.Numeric(15, 3), nullable=True, default=0)
    valor_compras_bruto = db.Column(db.Numeric(15, 2), nullable=True, default=0)
    valor_icms = db.Column(db.Numeric(15, 2), nullable=True, default=0)
    valor_pis = db.Column(db.Numeric(15, 2), nullable=True, default=0)
    valor_cofins = db.Column(db.Numeric(15, 2), nullable=True, default=0)
    valor_compras_liquido = db.Column(db.Numeric(15, 2), nullable=True, default=0)

    # Producao do mes (para intermediarios)
    qtd_produzida = db.Column(db.Numeric(15, 3), nullable=True, default=0)
    custo_producao = db.Column(db.Numeric(15, 2), nullable=True, default=0)

    # Consumo/Vendas do mes
    qtd_consumida = db.Column(db.Numeric(15, 3), nullable=True, default=0)
    qtd_vendida = db.Column(db.Numeric(15, 3), nullable=True, default=0)

    # Estoque final do mes
    qtd_estoque_final = db.Column(db.Numeric(15, 3), nullable=True, default=0)
    custo_estoque_final = db.Column(db.Numeric(15, 2), nullable=True, default=0)

    # ============================================
    # CONTROLE E AUDITORIA
    # ============================================

    # Valores: ABERTO (mes corrente), FECHADO (historico)
    status = db.Column(db.String(20), default='ABERTO', nullable=False, index=True)

    fechado_em = db.Column(db.DateTime, nullable=True)
    fechado_por = db.Column(db.String(100), nullable=True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('mes', 'ano', 'cod_produto', name='uq_custo_mensal_periodo_produto'),
        db.Index('idx_custo_mensal_periodo', 'ano', 'mes'),
        db.Index('idx_custo_mensal_tipo', 'tipo_produto'),
    )

    def __repr__(self):
        return f'<CustoMensal {self.cod_produto} {self.mes}/{self.ano}>'

    def to_dict(self):
        return {
            'id': self.id,
            'mes': self.mes,
            'ano': self.ano,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'tipo_produto': self.tipo_produto,
            'custo_liquido_medio': float(self.custo_liquido_medio) if self.custo_liquido_medio else 0,
            'custo_medio_estoque': float(self.custo_medio_estoque) if self.custo_medio_estoque else 0,
            'ultimo_custo': float(self.ultimo_custo) if self.ultimo_custo else 0,
            'custo_bom': float(self.custo_bom) if self.custo_bom else 0,
            'qtd_estoque_inicial': float(self.qtd_estoque_inicial) if self.qtd_estoque_inicial else 0,
            'custo_estoque_inicial': float(self.custo_estoque_inicial) if self.custo_estoque_inicial else 0,
            'qtd_comprada': float(self.qtd_comprada) if self.qtd_comprada else 0,
            'qtd_produzida': float(self.qtd_produzida) if self.qtd_produzida else 0,
            'custo_producao': float(self.custo_producao) if self.custo_producao else 0,
            'valor_compras_bruto': float(self.valor_compras_bruto) if self.valor_compras_bruto else 0,
            'valor_icms': float(self.valor_icms) if self.valor_icms else 0,
            'valor_pis': float(self.valor_pis) if self.valor_pis else 0,
            'valor_cofins': float(self.valor_cofins) if self.valor_cofins else 0,
            'valor_compras_liquido': float(self.valor_compras_liquido) if self.valor_compras_liquido else 0,
            'qtd_estoque_final': float(self.qtd_estoque_final) if self.qtd_estoque_final else 0,
            'custo_estoque_final': float(self.custo_estoque_final) if self.custo_estoque_final else 0,
            'status': self.status,
            'fechado_em': self.fechado_em.strftime('%d/%m/%Y %H:%M') if self.fechado_em else None,
            'fechado_por': self.fechado_por
        }


class CustoConsiderado(db.Model):
    """
    Custo vigente para cada produto com versionamento historico
    Atualizado apos cada fechamento mensal
    Permite selecionar qual tipo de custo usar

    Versionamento:
    - versao: Numero sequencial da versao (1, 2, 3...)
    - custo_atual: Flag indicando versao vigente (TRUE = atual)
    - vigencia_inicio: Data/hora de inicio da vigencia
    - vigencia_fim: Data/hora de fim da vigencia (NULL = vigente)

    Tipos de custo disponiveis:
    - MEDIO_MES: Custo medio do ultimo mes fechado
    - ULTIMO_CUSTO: Ultimo custo (ultima compra)
    - MEDIO_ESTOQUE: Custo medio do estoque
    - BOM: Custo calculado pela lista de materiais
    """
    __tablename__ = 'custo_considerado'

    id = db.Column(db.Integer, primary_key=True)

    # Produto (FK logica para CadastroPalletizacao)
    cod_produto = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(255), nullable=True)

    # Classificacao do produto
    tipo_produto = db.Column(db.String(20), nullable=False)

    # ============================================
    # VERSIONAMENTO
    # ============================================

    # Numero da versao (1, 2, 3...)
    versao = db.Column(db.Integer, default=1, nullable=False)

    # Flag indicando se e a versao atual
    custo_atual = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # Periodo de vigencia
    vigencia_inicio = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    vigencia_fim = db.Column(db.DateTime, nullable=True)

    # Motivo da alteracao (para auditoria)
    motivo_alteracao = db.Column(db.Text, nullable=True)

    # ============================================
    # TIPOS DE CUSTO DISPONIVEIS
    # ============================================

    # Custo medio do ultimo mes fechado
    custo_medio_mes = db.Column(db.Numeric(15, 6), nullable=True)

    # Ultimo custo (ultima compra)
    ultimo_custo = db.Column(db.Numeric(15, 6), nullable=True)

    # Custo medio do estoque
    custo_medio_estoque = db.Column(db.Numeric(15, 6), nullable=True)

    # Custo BOM (para intermediarios e acabados)
    custo_bom = db.Column(db.Numeric(15, 6), nullable=True)

    # ============================================
    # CUSTO CONSIDERADO (o que sera usado)
    # ============================================

    # Tipo selecionado: MEDIO_MES, ULTIMO_CUSTO, MEDIO_ESTOQUE, BOM
    tipo_custo_selecionado = db.Column(db.String(20), default='MEDIO_MES', nullable=False)

    # Valor final considerado (baseado no tipo selecionado)
    custo_considerado = db.Column(db.Numeric(15, 6), nullable=True)

    # Custo de producao (preenchido manualmente)
    # Representa custo de mão de obra direta
    custo_producao = db.Column(db.Numeric(15, 6), nullable=True)

    # ============================================
    # POSICAO DE ESTOQUE ATUAL
    # ============================================

    qtd_estoque_inicial = db.Column(db.Numeric(15, 3), nullable=True, default=0)
    custo_estoque_inicial = db.Column(db.Numeric(15, 2), nullable=True, default=0)

    qtd_comprada_periodo = db.Column(db.Numeric(15, 3), nullable=True, default=0)
    custo_compras_periodo = db.Column(db.Numeric(15, 2), nullable=True, default=0)

    qtd_estoque_final = db.Column(db.Numeric(15, 3), nullable=True, default=0)
    custo_estoque_final = db.Column(db.Numeric(15, 2), nullable=True, default=0)

    # ============================================
    # REFERENCIA AO ULTIMO FECHAMENTO
    # ============================================

    ultimo_mes_fechado = db.Column(db.Integer, nullable=True)
    ultimo_ano_fechado = db.Column(db.Integer, nullable=True)

    # Auditoria
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    atualizado_por = db.Column(db.String(100), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('cod_produto', 'versao', name='uq_custo_considerado_versao'),
        db.Index('idx_custo_considerado_tipo', 'tipo_produto'),
        db.Index('idx_custo_considerado_atual', 'cod_produto', 'custo_atual'),
    )

    def __repr__(self):
        return f'<CustoConsiderado {self.cod_produto}>'

    def recalcular_custo_considerado(self):
        """Recalcula custo_considerado baseado no tipo selecionado"""
        mapa_custos = {
            'MEDIO_MES': self.custo_medio_mes,
            'ULTIMO_CUSTO': self.ultimo_custo,
            'MEDIO_ESTOQUE': self.custo_medio_estoque,
            'BOM': self.custo_bom
        }
        self.custo_considerado = mapa_custos.get(self.tipo_custo_selecionado, self.custo_medio_mes)

    def to_dict(self):
        return {
            'id': self.id,
            'cod_produto': self.cod_produto,
            'nome_produto': self.nome_produto,
            'tipo_produto': self.tipo_produto,
            # Versionamento
            'versao': self.versao,
            'custo_atual': self.custo_atual,
            'vigencia_inicio': self.vigencia_inicio.strftime('%d/%m/%Y %H:%M') if self.vigencia_inicio else None,
            'vigencia_fim': self.vigencia_fim.strftime('%d/%m/%Y %H:%M') if self.vigencia_fim else None,
            'motivo_alteracao': self.motivo_alteracao,
            # Tipos de custo
            'custo_medio_mes': float(self.custo_medio_mes) if self.custo_medio_mes else 0,
            'ultimo_custo': float(self.ultimo_custo) if self.ultimo_custo else 0,
            'custo_medio_estoque': float(self.custo_medio_estoque) if self.custo_medio_estoque else 0,
            'custo_bom': float(self.custo_bom) if self.custo_bom else 0,
            'tipo_custo_selecionado': self.tipo_custo_selecionado,
            'custo_considerado': float(self.custo_considerado) if self.custo_considerado else 0,
            'custo_producao': float(self.custo_producao) if self.custo_producao else 0,
            # Estoque
            'qtd_estoque_inicial': float(self.qtd_estoque_inicial) if self.qtd_estoque_inicial else 0,
            'custo_estoque_inicial': float(self.custo_estoque_inicial) if self.custo_estoque_inicial else 0,
            'qtd_comprada_periodo': float(self.qtd_comprada_periodo) if self.qtd_comprada_periodo else 0,
            'custo_compras_periodo': float(self.custo_compras_periodo) if self.custo_compras_periodo else 0,
            'qtd_estoque_final': float(self.qtd_estoque_final) if self.qtd_estoque_final else 0,
            'custo_estoque_final': float(self.custo_estoque_final) if self.custo_estoque_final else 0,
            'ultimo_mes_fechado': self.ultimo_mes_fechado,
            'ultimo_ano_fechado': self.ultimo_ano_fechado,
            'atualizado_em': self.atualizado_em.strftime('%d/%m/%Y %H:%M') if self.atualizado_em else None,
            'atualizado_por': self.atualizado_por
        }


class CustoFrete(db.Model):
    """
    Tabela de percentual de frete por combinacao incoterm + UF
    Usado para calcular custo de frete na margem
    """
    __tablename__ = 'custo_frete'

    id = db.Column(db.Integer, primary_key=True)

    # Combinacao incoterm + UF
    incoterm = db.Column(db.String(20), nullable=False)  # CIF, FOB, etc
    cod_uf = db.Column(db.String(2), nullable=False)

    # Percentual de frete
    percentual_frete = db.Column(db.Numeric(5, 2), nullable=False)

    # Vigencia
    vigencia_inicio = db.Column(db.Date, nullable=False)
    vigencia_fim = db.Column(db.Date, nullable=True)  # NULL = vigente

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('incoterm', 'cod_uf', 'vigencia_inicio', name='uq_custo_frete_incoterm_uf_vigencia'),
        db.Index('idx_custo_frete_vigencia', 'incoterm', 'cod_uf', 'vigencia_inicio'),
    )

    def __repr__(self):
        return f'<CustoFrete {self.incoterm}/{self.cod_uf}: {self.percentual_frete}%>'

    def to_dict(self):
        return {
            'id': self.id,
            'incoterm': self.incoterm,
            'cod_uf': self.cod_uf,
            'percentual_frete': float(self.percentual_frete) if self.percentual_frete else 0,
            'vigencia_inicio': self.vigencia_inicio.strftime('%d/%m/%Y') if self.vigencia_inicio else None,
            'vigencia_fim': self.vigencia_fim.strftime('%d/%m/%Y') if self.vigencia_fim else None,
            'criado_em': self.criado_em.strftime('%d/%m/%Y %H:%M') if self.criado_em else None,
            'criado_por': self.criado_por
        }

    @staticmethod
    def buscar_percentual_vigente(incoterm: str, cod_uf: str) -> float:
        """
        Busca percentual de frete vigente para combinacao incoterm + UF

        Args:
            incoterm: Incoterm do pedido (CIF, FOB, etc)
            cod_uf: UF de destino

        Returns:
            Percentual de frete ou 0 se nao encontrado
        """
        from datetime import date
        custo = CustoFrete.query.filter(
            CustoFrete.incoterm == incoterm,
            CustoFrete.cod_uf == cod_uf,
            CustoFrete.vigencia_inicio <= date.today(),
            db.or_(
                CustoFrete.vigencia_fim.is_(None),
                CustoFrete.vigencia_fim > date.today()
            )
        ).order_by(CustoFrete.vigencia_inicio.desc()).first()

        return float(custo.percentual_frete) if custo else 0.0


class ParametroCusteio(db.Model):
    """
    Parametros globais de custeio
    Ex: CUSTO_OPERACAO_PERCENTUAL = 5.0 (5% de custo operacional)
    """
    __tablename__ = 'parametro_custeio'

    id = db.Column(db.Integer, primary_key=True)

    # Chave do parametro
    chave = db.Column(db.String(50), unique=True, nullable=False)

    # Valor numerico
    valor = db.Column(db.Numeric(15, 6), nullable=False)

    # Descricao
    descricao = db.Column(db.Text, nullable=True)

    # Auditoria
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    atualizado_por = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<ParametroCusteio {self.chave}={self.valor}>'

    def to_dict(self):
        return {
            'id': self.id,
            'chave': self.chave,
            'valor': float(self.valor) if self.valor else 0,
            'descricao': self.descricao,
            'atualizado_em': self.atualizado_em.strftime('%d/%m/%Y %H:%M') if self.atualizado_em else None,
            'atualizado_por': self.atualizado_por
        }

    @staticmethod
    def obter_valor(chave: str, padrao: float = 0.0) -> float:
        """
        Obtem valor de um parametro pelo nome da chave

        Args:
            chave: Nome do parametro (ex: 'CUSTO_OPERACAO_PERCENTUAL')
            padrao: Valor padrao se nao encontrado

        Returns:
            Valor do parametro ou padrao
        """
        param = ParametroCusteio.query.filter_by(chave=chave).first()
        return float(param.valor) if param else padrao


class RegraComissao(db.Model):
    """
    Regras de comissao com HIERARQUIA DE ESPECIFICIDADE.
    A regra mais especifica que se aplica e utilizada (nao soma).

    Ordem de especificidade (maior para menor):
    1. CLIENTE_PRODUTO   = cliente + produto (mais especifico)
    2. GRUPO_PRODUTO     = grupo empresarial + produto
    3. VENDEDOR_PRODUTO  = vendedor + produto
    4. CLIENTE           = apenas cliente
    5. GRUPO             = apenas grupo empresarial
    6. VENDEDOR          = apenas vendedor
    7. PRODUTO           = apenas produto (menos especifico)
    8. (nenhuma regra)   = COMISSAO_PADRAO (default 3%)
    """
    __tablename__ = 'regra_comissao'

    # Ordem de especificidade (menor numero = mais especifico)
    ORDEM_ESPECIFICIDADE = {
        'CLIENTE_PRODUTO': 1,
        'GRUPO_PRODUTO': 2,
        'VENDEDOR_PRODUTO': 3,
        'CLIENTE': 4,
        'GRUPO': 5,
        'VENDEDOR': 6,
        'PRODUTO': 7
    }

    id = db.Column(db.Integer, primary_key=True)

    # Tipo de regra (determina especificidade)
    tipo_regra = db.Column(db.String(20), nullable=False)

    # Criterio: Grupo empresarial
    grupo_empresarial = db.Column(db.String(100), index=True)

    # Criterio: Cliente
    raz_social_red = db.Column(db.String(100), index=True)

    # Criterio: Vendedor (standalone)
    vendedor = db.Column(db.String(100), index=True)

    # Criterio: Produto
    cod_produto = db.Column(db.String(50), index=True)

    # Campos legados (mantidos para compatibilidade)
    cliente_cod_uf = db.Column(db.String(2))
    cliente_vendedor = db.Column(db.String(100))
    cliente_equipe = db.Column(db.String(100))
    produto_grupo = db.Column(db.String(100))
    produto_cliente = db.Column(db.String(100))

    # Comissao
    comissao_percentual = db.Column(db.Numeric(5, 2), nullable=False)

    # Vigencia e controle
    vigencia_inicio = db.Column(db.Date, nullable=False, default=date.today)
    vigencia_fim = db.Column(db.Date)
    prioridade = db.Column(db.Integer, default=0)
    descricao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True, index=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    atualizado_em = db.Column(db.DateTime, onupdate=datetime.utcnow)
    atualizado_por = db.Column(db.String(100))

    def to_dict(self):
        """Converte para dicionario"""
        return {
            'id': self.id,
            'tipo_regra': self.tipo_regra,
            'grupo_empresarial': self.grupo_empresarial,
            'raz_social_red': self.raz_social_red,
            'vendedor': self.vendedor,
            'cod_produto': self.cod_produto,
            'cliente_cod_uf': self.cliente_cod_uf,
            'cliente_vendedor': self.cliente_vendedor,
            'cliente_equipe': self.cliente_equipe,
            'produto_grupo': self.produto_grupo,
            'produto_cliente': self.produto_cliente,
            'comissao_percentual': float(self.comissao_percentual) if self.comissao_percentual else 0,
            'vigencia_inicio': self.vigencia_inicio.isoformat() if self.vigencia_inicio else None,
            'vigencia_fim': self.vigencia_fim.isoformat() if self.vigencia_fim else None,
            'prioridade': self.prioridade,
            'descricao': self.descricao,
            'ativo': self.ativo,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por': self.criado_por
        }

    @staticmethod
    def buscar_comissao(cnpj: str, raz_social_red: str, cod_produto: str,
                        vendedor: str = None) -> float:
        """
        Busca a comissao aplicavel seguindo hierarquia de especificidade.
        Retorna a regra MAIS ESPECIFICA que se aplica.

        Ordem de busca (para no primeiro match):
        1. CLIENTE_PRODUTO   (cliente + produto)
        2. GRUPO_PRODUTO     (grupo + produto)
        3. VENDEDOR_PRODUTO  (vendedor + produto)
        4. CLIENTE           (apenas cliente)
        5. GRUPO             (apenas grupo)
        6. VENDEDOR          (apenas vendedor)
        7. PRODUTO           (apenas produto)
        8. COMISSAO_PADRAO   (default 3%)

        Args:
            cnpj: CNPJ do cliente (para identificar grupo empresarial)
            raz_social_red: Razao social reduzida do cliente
            cod_produto: Codigo do produto
            vendedor: Nome do vendedor

        Returns:
            Percentual de comissao aplicavel
        """
        from app.portal.utils.grupo_empresarial import GrupoEmpresarial

        hoje = date.today()

        # Identificar grupo empresarial do cliente
        grupo = GrupoEmpresarial.identificar_grupo(cnpj) if cnpj else None

        # Buscar regras vigentes e ativas ordenadas por especificidade
        regras = RegraComissao.query.filter(
            RegraComissao.ativo == True,
            RegraComissao.vigencia_inicio <= hoje,
            db.or_(
                RegraComissao.vigencia_fim.is_(None),
                RegraComissao.vigencia_fim >= hoje
            )
        ).all()

        # Ordenar por especificidade (menor = mais especifico)
        def get_especificidade(regra):
            return RegraComissao.ORDEM_ESPECIFICIDADE.get(regra.tipo_regra, 99)

        regras_ordenadas = sorted(regras, key=get_especificidade)

        # Buscar primeira regra que aplica (mais especifica)
        for regra in regras_ordenadas:
            if RegraComissao._regra_aplica(regra, raz_social_red, grupo, vendedor, cod_produto):
                return float(regra.comissao_percentual)

        # Nenhuma regra encontrada - usar padrao
        return ParametroCusteio.obter_valor('COMISSAO_PADRAO', 3.0)

    @staticmethod
    def _regra_aplica(regra, raz_social_red: str, grupo: str,
                      vendedor: str, cod_produto: str) -> bool:
        """
        Verifica se uma regra se aplica aos criterios informados.
        """
        tipo = regra.tipo_regra

        # 1. CLIENTE_PRODUTO: cliente + produto
        if tipo == 'CLIENTE_PRODUTO':
            return (regra.raz_social_red == raz_social_red and
                    regra.cod_produto == cod_produto)

        # 2. GRUPO_PRODUTO: grupo + produto
        if tipo == 'GRUPO_PRODUTO':
            return (regra.grupo_empresarial == grupo and
                    regra.cod_produto == cod_produto)

        # 3. VENDEDOR_PRODUTO: vendedor + produto
        if tipo == 'VENDEDOR_PRODUTO':
            return (regra.vendedor == vendedor and
                    regra.cod_produto == cod_produto)

        # 4. CLIENTE: apenas cliente
        if tipo == 'CLIENTE':
            return regra.raz_social_red == raz_social_red

        # 5. GRUPO: apenas grupo
        if tipo == 'GRUPO':
            return regra.grupo_empresarial == grupo

        # 6. VENDEDOR: apenas vendedor
        if tipo == 'VENDEDOR':
            return regra.vendedor == vendedor

        # 7. PRODUTO: apenas produto
        if tipo == 'PRODUTO':
            return regra.cod_produto == cod_produto

        return False

    # Alias para manter compatibilidade com codigo existente
    @staticmethod
    def calcular_comissao_total(cnpj: str, raz_social_red: str, cod_produto: str,
                                cod_uf: str = None, vendedor: str = None,
                                equipe: str = None) -> float:
        """
        Alias para buscar_comissao (compatibilidade).
        """
        return RegraComissao.buscar_comissao(
            cnpj=cnpj,
            raz_social_red=raz_social_red,
            cod_produto=cod_produto,
            vendedor=vendedor
        )

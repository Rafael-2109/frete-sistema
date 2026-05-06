"""
Service: Relatório de Análise de Fretes
========================================

Gera relatório com 4 visões:
- Visão A: Expandida (NF + Produto) - Frete líquido, despesas por tipo
- Visão B: Por NF (sem transportadora) - Frete líquido, despesas por tipo
- Visão C: Por Frete + NF - Com transportadora, frete líquido, despesas por tipo
- Visão D: Por Mês + UF - Com % Frete, % Orçado, Diferença

Fórmulas de Rateio:
- Frete: (peso_nf / frete.peso_total) * frete.valor_considerado
- Despesa: (peso_nf / frete.peso_total) * despesa.valor_despesa
- Devolução: (valor_nf / soma_valor_nfs_ref) * nf_devolucao.valor_total

Cálculo de Valor Líquido (ICMS + Freteiro):
- Se transportadora.optante=False: valor_sem_icms = valor * (1 - icms_cidade)
- Se transportadora.freteiro=True: valor_liquido = valor_sem_icms * (1 - 9,25%)

Autor: Sistema de Fretes
Data: 2026-01-29
"""

import logging
from io import BytesIO
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple

import xlsxwriter
from sqlalchemy import func, and_, or_

from app import db
from app.fretes.models import Frete, DespesaExtra
from app.faturamento.models import FaturamentoProduto
from app.devolucao.models import NFDevolucao, NFDevolucaoNFReferenciada
from app.transportadoras.models import Transportadora
from app.localidades.models import Cidade
from app.custeio.models import CustoFrete

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

# Tipos de despesa existentes no sistema
TIPOS_DESPESA = [
    'REENTREGA', 'TDE', 'PERNOITE', 'DEVOLUÇÃO', 'DIARIA',
    'COMPLEMENTO DE FRETE', 'COMPRA/AVARIA', 'TRANSFERENCIA',
    'DESCARGA', 'ESTACIONAMENTO', 'CARRO DEDICADO', 'ARMAZENAGEM'
]

# Percentual de dedução para freteiro
PERCENTUAL_FRETEIRO = Decimal('0.0925')  # 9,25%


# =============================================================================
# FUNÇÕES AUXILIARES DE CÁLCULO
# =============================================================================

def buscar_icms_cidade(nome_cidade: str, uf: str) -> Decimal:
    """
    Busca o percentual de ICMS da cidade na tabela cidades.

    Args:
        nome_cidade: Nome da cidade (ex: 'SAO PAULO')
        uf: UF da cidade (ex: 'SP')

    Returns:
        Percentual de ICMS como Decimal (ex: 0.12 para 12%)
        Retorna 0 se cidade não encontrada
    """
    if not nome_cidade or not uf:
        return Decimal('0')

    cidade = Cidade.query.filter(
        func.upper(Cidade.nome) == func.upper(nome_cidade.strip()),
        func.upper(Cidade.uf) == func.upper(uf.strip())
    ).first()

    if cidade and cidade.icms:
        return Decimal(str(cidade.icms))

    return Decimal('0')


def calcular_valor_liquido(
    valor_original: Decimal,
    transportadora_optante: bool,
    transportadora_freteiro: bool,
    cidade_cliente: str,
    uf_cliente: str
) -> Decimal:
    """
    Calcula o valor líquido após dedução de ICMS (se não optante) e freteiro (9,25%).

    Regra:
    1. Se transportadora.optante = False:
       - Busca ICMS da cidade do cliente
       - valor_sem_icms = valor_original * (1 - icms)
    2. Se transportadora.freteiro = True:
       - valor_liquido = valor_sem_icms * (1 - 9,25%)

    Args:
        valor_original: Valor bruto do frete/despesa
        transportadora_optante: Se a transportadora é optante do Simples
        transportadora_freteiro: Se a transportadora é freteiro
        cidade_cliente: Cidade do cliente (para buscar ICMS)
        uf_cliente: UF do cliente (para buscar ICMS)

    Returns:
        Valor líquido após deduções
    """
    if valor_original == 0:
        return Decimal('0')

    valor = Decimal(str(valor_original))

    # Etapa 1: Deduzir ICMS se não optante
    if not transportadora_optante:
        icms = buscar_icms_cidade(cidade_cliente, uf_cliente)
        if icms > 0:
            valor = valor * (Decimal('1') - icms)

    # Etapa 2: Deduzir 9,25% se freteiro
    if transportadora_freteiro:
        valor = valor * (Decimal('1') - PERCENTUAL_FRETEIRO)

    return valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def buscar_percentual_orcado(incoterm: str, uf: str) -> float:
    """
    Busca o percentual de frete orçado na tabela CustoFrete.

    Args:
        incoterm: Incoterm da venda (CIF, FOB, RED, etc.)
        uf: UF de destino (se RED, usar 'SP')

    Returns:
        Percentual orçado (ex: 5.5 para 5,5%)
    """
    if not incoterm:
        return 0.0

    # Regra: Se RED, considerar UF = SP
    uf_busca = 'SP' if incoterm == 'RED' else (uf or '')

    if not uf_busca:
        return 0.0

    return CustoFrete.buscar_percentual_vigente(incoterm, uf_busca)


# =============================================================================
# FUNÇÕES DE BUSCA DE DADOS
# =============================================================================

def buscar_dados_relatorio(
    data_inicio: str,
    data_fim: str,
    transportadora_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Busca todos os dados necessários para o relatório.

    Args:
        data_inicio: Data início no formato 'YYYY-MM-DD'
        data_fim: Data fim no formato 'YYYY-MM-DD'
        transportadora_id: ID da transportadora (opcional)

    Returns:
        dict com:
        - fretes: lista de dicts com dados do frete (incluindo optante/freteiro)
        - faturamento_por_nf: dict {numero_nf: {peso, valor, produtos[], incoterm, uf, municipio, data_fatura}}
        - despesas_por_frete: dict {frete_id: [despesas]}
        - devolucoes_por_nf: dict {numero_nf: valor_rateado}
    """
    logger.info(f"Buscando dados do relatório: {data_inicio} a {data_fim}, transportadora_id={transportadora_id}")

    # 1. Buscar faturamento agrupado por NF
    faturamento_por_nf = _buscar_faturamento_por_nf(data_inicio, data_fim)
    logger.info(f"Encontradas {len(faturamento_por_nf)} NFs no faturamento")

    # 2. Buscar fretes que contêm essas NFs (com dados da transportadora)
    fretes = _buscar_fretes_por_nfs(list(faturamento_por_nf.keys()), transportadora_id)
    logger.info(f"Encontrados {len(fretes)} fretes")

    # 3. Buscar despesas extras dos fretes
    frete_ids = [f['id'] for f in fretes]
    despesas_por_frete = _buscar_despesas_por_frete(frete_ids)
    logger.info(f"Encontradas despesas para {len(despesas_por_frete)} fretes")

    # 4. Buscar devoluções rateadas por NF
    devolucoes_por_nf = _buscar_devolucoes_rateadas(list(faturamento_por_nf.keys()))
    logger.info(f"Encontradas devoluções para {len(devolucoes_por_nf)} NFs")

    return {
        'fretes': fretes,
        'faturamento_por_nf': faturamento_por_nf,
        'despesas_por_frete': despesas_por_frete,
        'devolucoes_por_nf': devolucoes_por_nf,
        'data_inicio': data_inicio,
        'data_fim': data_fim
    }


def _buscar_faturamento_por_nf(data_inicio: str, data_fim: str) -> Dict[str, Dict]:
    """
    Busca faturamento agrupado por NF.

    Returns:
        dict {numero_nf: {
            'peso_total': Decimal,
            'valor_total': Decimal,
            'incoterm': str,
            'uf': str,
            'municipio': str,
            'data_fatura': date,
            'cnpj_cliente': str,
            'nome_cliente': str,
            'produtos': [{'cod_produto', 'nome_produto', 'peso', 'valor'}]
        }}
    """
    # Query de produtos individuais
    produtos = FaturamentoProduto.query.filter(
        FaturamentoProduto.data_fatura >= data_inicio,
        FaturamentoProduto.data_fatura <= data_fim,
        FaturamentoProduto.status_nf != 'Cancelado',
        FaturamentoProduto.revertida == False
    ).all()

    faturamento_por_nf = defaultdict(lambda: {
        'peso_total': Decimal('0'),
        'valor_total': Decimal('0'),
        'incoterm': None,
        'uf': None,
        'municipio': None,
        'data_fatura': None,
        'cnpj_cliente': None,
        'nome_cliente': None,
        'produtos': []
    })

    for p in produtos:
        nf = p.numero_nf
        peso = Decimal(str(p.peso_total or 0))
        valor = Decimal(str(p.valor_produto_faturado or 0))

        faturamento_por_nf[nf]['peso_total'] += peso
        faturamento_por_nf[nf]['valor_total'] += valor
        faturamento_por_nf[nf]['incoterm'] = p.incoterm
        faturamento_por_nf[nf]['uf'] = p.estado
        faturamento_por_nf[nf]['municipio'] = p.municipio
        faturamento_por_nf[nf]['data_fatura'] = p.data_fatura
        faturamento_por_nf[nf]['cnpj_cliente'] = p.cnpj_cliente
        faturamento_por_nf[nf]['nome_cliente'] = p.nome_cliente
        faturamento_por_nf[nf]['produtos'].append({
            'cod_produto': p.cod_produto,
            'nome_produto': p.nome_produto,
            'peso': float(peso),
            'valor': float(valor)
        })

    return dict(faturamento_por_nf)


def _buscar_fretes_por_nfs(numeros_nfs: List[str], transportadora_id: Optional[int] = None) -> List[Dict]:
    """
    Busca fretes que contêm as NFs especificadas.
    Inclui dados da transportadora (optante, freteiro) para cálculo de valor líquido.

    O campo numeros_nfs é uma lista separada por vírgula.
    """
    if not numeros_nfs:
        return []

    # Query base com JOIN na transportadora
    query = db.session.query(
        Frete,
        Transportadora
    ).join(
        Transportadora,
        Frete.transportadora_id == Transportadora.id
    )

    # Filtro por transportadora
    if transportadora_id:
        from app.transportadoras.filter_utils import expandir_filtro_fk
        query = query.filter(expandir_filtro_fk(Frete.transportadora_id, transportadora_id))

    fretes_result = query.all()

    # Filtrar fretes que contêm pelo menos uma das NFs
    numeros_nfs_set = set(numeros_nfs)
    fretes = []

    for frete, transportadora in fretes_result:
        # Parse das NFs do frete (separadas por vírgula)
        nfs_frete = set(nf.strip() for nf in (frete.numeros_nfs or '').split(',') if nf.strip())

        # Verificar se há interseção
        nfs_comuns = nfs_frete & numeros_nfs_set
        if nfs_comuns:
            fretes.append({
                'id': frete.id,
                'transportadora_id': frete.transportadora_id,
                'transportadora_razao_social': transportadora.razao_social,
                'transportadora_cnpj': transportadora.cnpj,
                'motorista_proprio': getattr(transportadora, 'motorista_proprio', False) or False,
                'transportadora_optante': getattr(transportadora, 'optante', False) or False,
                'transportadora_freteiro': getattr(transportadora, 'freteiro', False) or False,
                'numeros_nfs': list(nfs_frete),
                'nfs_no_periodo': list(nfs_comuns),
                'peso_total': float(frete.peso_total or 0),
                'valor_considerado': float(frete.valor_considerado or 0),
                'status': frete.status,
                'numero_cte': frete.numero_cte,
                'data_emissao_cte': frete.data_emissao_cte,
                'cidade_destino': frete.cidade_destino,
                'uf_destino': frete.uf_destino
            })

    return fretes


def _buscar_despesas_por_frete(frete_ids: List[int]) -> Dict[int, List[Dict]]:
    """
    Busca despesas extras agrupadas por frete_id.

    Returns:
        dict {frete_id: [{'tipo_despesa', 'valor_despesa', ...}]}
    """
    if not frete_ids:
        return {}

    despesas = DespesaExtra.query.filter(
        DespesaExtra.frete_id.in_(frete_ids),
        DespesaExtra.status != 'CANCELADO'
    ).all()

    despesas_por_frete = defaultdict(list)
    for d in despesas:
        despesas_por_frete[d.frete_id].append({
            'id': d.id,
            'tipo_despesa': d.tipo_despesa,
            'valor_despesa': float(d.valor_despesa or 0),
            'setor_responsavel': d.setor_responsavel,
            'motivo_despesa': d.motivo_despesa,
            'tipo_documento': d.tipo_documento,
            'numero_documento': d.numero_documento,
            'observacoes': d.observacoes or '',
            'status': d.status,
            'criado_em': d.criado_em,
            'criado_por': d.criado_por,
            'vencimento_despesa': d.vencimento_despesa
        })

    return dict(despesas_por_frete)


def _buscar_devolucoes_rateadas(numeros_nfs: List[str]) -> Dict[str, Decimal]:
    """
    Calcula o valor de devolução rateado para cada NF.

    Fórmula: (valor_nf / soma_valor_nfs_ref) * nf_devolucao.valor_total

    Returns:
        dict {numero_nf: valor_devolucao_rateado}
    """
    if not numeros_nfs:
        return {}

    # Buscar todas as referências para as NFs do período
    referencias = NFDevolucaoNFReferenciada.query.filter(
        NFDevolucaoNFReferenciada.numero_nf.in_(numeros_nfs)
    ).all()

    if not referencias:
        return {}

    # Agrupar por nf_devolucao_id para calcular rateio
    refs_por_nfd = defaultdict(list)
    for ref in referencias:
        refs_por_nfd[ref.nf_devolucao_id].append(ref.numero_nf)

    # Buscar devoluções
    nfd_ids = list(refs_por_nfd.keys())
    devolucoes = NFDevolucao.query.filter(
        NFDevolucao.id.in_(nfd_ids)
    ).all()

    devolucoes_por_nf = defaultdict(Decimal)

    for nfd in devolucoes:
        valor_total_nfd = Decimal(str(nfd.valor_total or 0))
        if valor_total_nfd == 0:
            continue

        # Buscar NFs referenciadas desta devolução
        nfs_referenciadas = refs_por_nfd.get(nfd.id, [])
        if not nfs_referenciadas:
            continue

        # Calcular soma dos valores das NFs referenciadas
        soma_valor_nfs = Decimal('0')
        valores_por_nf = {}

        for nf in nfs_referenciadas:
            # Buscar valor total da NF no faturamento
            valor_nf_query = db.session.query(
                func.sum(FaturamentoProduto.valor_produto_faturado)
            ).filter(
                FaturamentoProduto.numero_nf == nf
            ).scalar()

            valor_nf = Decimal(str(valor_nf_query or 0))
            valores_por_nf[nf] = valor_nf
            soma_valor_nfs += valor_nf

        # Ratear devolução proporcionalmente
        if soma_valor_nfs > 0:
            for nf, valor_nf in valores_por_nf.items():
                if nf in numeros_nfs:  # Só incluir NFs do período
                    rateio = (valor_nf / soma_valor_nfs) * valor_total_nfd
                    devolucoes_por_nf[nf] += rateio

    return dict(devolucoes_por_nf)


# =============================================================================
# FUNÇÕES DE CÁLCULO DE RATEIO
# =============================================================================

def calcular_rateio_frete_por_nf(
    frete: Dict,
    faturamento_por_nf: Dict[str, Dict]
) -> Dict[str, Decimal]:
    """
    Calcula o frete rateado para cada NF do frete.

    Fórmula: (peso_nf / peso_total_frete) * valor_considerado

    Returns:
        dict {numero_nf: frete_rateado}
    """
    peso_total_frete = Decimal(str(frete.get('peso_total', 0)))
    valor_considerado = Decimal(str(frete.get('valor_considerado', 0)))

    # Edge case: peso total = 0
    if peso_total_frete == 0:
        logger.warning(f"Frete {frete.get('id')} tem peso_total=0, retornando rateio zerado")
        return {nf: Decimal('0') for nf in frete.get('nfs_no_periodo', [])}

    rateio_por_nf = {}
    for nf in frete.get('nfs_no_periodo', []):
        fat = faturamento_por_nf.get(nf, {})
        peso_nf = Decimal(str(fat.get('peso_total', 0)))

        frete_rateado = (peso_nf / peso_total_frete) * valor_considerado
        rateio_por_nf[nf] = frete_rateado.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return rateio_por_nf


def calcular_rateio_despesa_por_nf(
    despesa: Dict,
    frete: Dict,
    faturamento_por_nf: Dict[str, Dict]
) -> Dict[str, Decimal]:
    """
    Calcula a despesa rateada para cada NF do frete.

    Fórmula: (peso_nf / peso_total_frete) * valor_despesa
    """
    peso_total_frete = Decimal(str(frete.get('peso_total', 0)))
    valor_despesa = Decimal(str(despesa.get('valor_despesa', 0)))

    if peso_total_frete == 0:
        return {nf: Decimal('0') for nf in frete.get('nfs_no_periodo', [])}

    rateio_por_nf = {}
    for nf in frete.get('nfs_no_periodo', []):
        fat = faturamento_por_nf.get(nf, {})
        peso_nf = Decimal(str(fat.get('peso_total', 0)))

        despesa_rateada = (peso_nf / peso_total_frete) * valor_despesa
        rateio_por_nf[nf] = despesa_rateada.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return rateio_por_nf


# =============================================================================
# FUNÇÕES DE GERAÇÃO DE VISÕES
# =============================================================================

def gerar_visao_expandida(dados: Dict) -> List[Dict]:
    """
    Visão A: Uma linha por NF + Produto + Frete

    - Frete SEMPRE líquido (após ICMS/freteiro)
    - Despesas SEMPRE líquidas e abertas por tipo (12 colunas)
    - Total de despesas = soma das 12 colunas
    """
    linhas = []

    fretes = dados['fretes']
    faturamento_por_nf = dados['faturamento_por_nf']
    despesas_por_frete = dados['despesas_por_frete']
    devolucoes_por_nf = dados['devolucoes_por_nf']

    for frete in fretes:
        # Dados da transportadora para cálculo de valor líquido
        optante = frete.get('transportadora_optante', False)
        freteiro = frete.get('transportadora_freteiro', False)

        # Calcular rateio de frete por NF
        frete_rateado_por_nf = calcular_rateio_frete_por_nf(frete, faturamento_por_nf)

        # Calcular rateio de despesas por tipo
        despesas_frete = despesas_por_frete.get(frete['id'], [])
        despesas_por_tipo_por_nf = defaultdict(lambda: defaultdict(Decimal))

        for despesa in despesas_frete:
            rateio_despesa = calcular_rateio_despesa_por_nf(despesa, frete, faturamento_por_nf)
            tipo = despesa['tipo_despesa']
            for nf, valor in rateio_despesa.items():
                despesas_por_tipo_por_nf[nf][tipo] += valor

        # Gerar linhas por NF + Produto
        for nf in frete.get('nfs_no_periodo', []):
            fat = faturamento_por_nf.get(nf, {})
            frete_rateado = frete_rateado_por_nf.get(nf, Decimal('0'))
            devolucao_rateada = devolucoes_por_nf.get(nf, Decimal('0'))
            despesas_nf = dict(despesas_por_tipo_por_nf.get(nf, {}))

            # Cidade/UF do cliente para cálculo de ICMS
            cidade_cliente = fat.get('municipio', '')
            uf_cliente = fat.get('uf', '')

            # Para cada produto na NF
            for produto in fat.get('produtos', []):
                # Ratear frete/despesas/devolução pelo produto (proporcional ao peso do produto na NF)
                peso_nf = fat.get('peso_total', Decimal('0'))
                peso_produto = Decimal(str(produto.get('peso', 0)))

                if peso_nf and peso_nf > 0:
                    proporcao_produto = peso_produto / peso_nf
                else:
                    proporcao_produto = Decimal('0')

                # Frete rateado por produto (bruto)
                frete_produto_bruto = (frete_rateado * proporcao_produto).quantize(Decimal('0.01'))
                # Frete líquido (após ICMS/freteiro)
                frete_produto_liquido = calcular_valor_liquido(
                    frete_produto_bruto, optante, freteiro, cidade_cliente, uf_cliente
                )

                devolucao_produto = (devolucao_rateada * proporcao_produto).quantize(Decimal('0.01'))

                linha = {
                    'numero_nf': nf,
                    'cnpj_cliente': fat.get('cnpj_cliente', ''),
                    'nome_cliente': fat.get('nome_cliente', ''),
                    'uf': fat.get('uf', ''),
                    'municipio': fat.get('municipio', ''),
                    'cod_produto': produto['cod_produto'],
                    'nome_produto': produto['nome_produto'],
                    'peso_produto': produto['peso'],
                    'valor_produto': produto['valor'],
                    'transportadora': frete['transportadora_razao_social'],
                    'transportadora_cnpj': frete['transportadora_cnpj'],
                    'motorista_proprio': 'Sim' if frete['motorista_proprio'] else 'Não',
                    'numero_cte': frete['numero_cte'],
                    'frete_liquido': float(frete_produto_liquido),
                    'devolucao_rateada': float(devolucao_produto),
                    'incoterm': fat.get('incoterm', ''),
                    'data_fatura': fat.get('data_fatura'),
                    'status_frete': frete['status']
                }

                # Adicionar despesas por tipo (SEMPRE 12 colunas, com valor líquido)
                total_despesas = Decimal('0')
                for tipo in TIPOS_DESPESA:
                    valor_bruto = despesas_nf.get(tipo, Decimal('0'))
                    despesa_produto_bruto = (valor_bruto * proporcao_produto).quantize(Decimal('0.01'))
                    despesa_liquida = calcular_valor_liquido(
                        despesa_produto_bruto, optante, freteiro, cidade_cliente, uf_cliente
                    )
                    linha[f'despesa_{tipo}'] = float(despesa_liquida)
                    total_despesas += despesa_liquida

                linha['total_despesas'] = float(total_despesas)

                linhas.append(linha)

    return linhas


def gerar_visao_por_nf(dados: Dict) -> List[Dict]:
    """
    Visão B: Uma linha por NF (agregado, sem duplicar frete)

    - SEM transportadora (uma NF pode ter N fretes com transportadoras diferentes)
    - Frete SEMPRE líquido
    - Despesas SEMPRE líquidas e abertas por tipo (12 colunas)

    Quando uma NF aparece em múltiplos fretes, soma os valores.
    """
    linhas_por_nf = defaultdict(lambda: {
        'numero_nf': None,
        'cnpj_cliente': None,
        'nome_cliente': None,
        'uf': None,
        'municipio': None,
        'peso_total': Decimal('0'),
        'valor_total': Decimal('0'),
        'total_frete_liquido': Decimal('0'),
        'total_devolucao': Decimal('0'),
        'despesas_por_tipo': {tipo: Decimal('0') for tipo in TIPOS_DESPESA},
        'incoterm': None,
        'data_fatura': None,
        'qtd_fretes': 0
    })

    fretes = dados['fretes']
    faturamento_por_nf = dados['faturamento_por_nf']
    despesas_por_frete = dados['despesas_por_frete']
    devolucoes_por_nf = dados['devolucoes_por_nf']

    # Processar fretes
    for frete in fretes:
        # Dados da transportadora para cálculo de valor líquido
        optante = frete.get('transportadora_optante', False)
        freteiro = frete.get('transportadora_freteiro', False)

        frete_rateado_por_nf = calcular_rateio_frete_por_nf(frete, faturamento_por_nf)
        despesas_frete = despesas_por_frete.get(frete['id'], [])

        for nf in frete.get('nfs_no_periodo', []):
            fat = faturamento_por_nf.get(nf, {})
            cidade_cliente = fat.get('municipio', '')
            uf_cliente = fat.get('uf', '')

            linhas_por_nf[nf]['numero_nf'] = nf
            linhas_por_nf[nf]['cnpj_cliente'] = fat.get('cnpj_cliente')
            linhas_por_nf[nf]['nome_cliente'] = fat.get('nome_cliente')
            linhas_por_nf[nf]['uf'] = fat.get('uf')
            linhas_por_nf[nf]['municipio'] = fat.get('municipio')
            linhas_por_nf[nf]['peso_total'] = Decimal(str(fat.get('peso_total', 0)))
            linhas_por_nf[nf]['valor_total'] = Decimal(str(fat.get('valor_total', 0)))
            linhas_por_nf[nf]['incoterm'] = fat.get('incoterm')
            linhas_por_nf[nf]['data_fatura'] = fat.get('data_fatura')
            linhas_por_nf[nf]['qtd_fretes'] += 1

            # Frete líquido
            frete_bruto = frete_rateado_por_nf.get(nf, Decimal('0'))
            frete_liquido = calcular_valor_liquido(frete_bruto, optante, freteiro, cidade_cliente, uf_cliente)
            linhas_por_nf[nf]['total_frete_liquido'] += frete_liquido

            # Despesas por tipo (líquidas)
            for despesa in despesas_frete:
                rateio = calcular_rateio_despesa_por_nf(despesa, frete, faturamento_por_nf)
                tipo = despesa['tipo_despesa']
                valor_bruto = rateio.get(nf, Decimal('0'))
                valor_liquido = calcular_valor_liquido(valor_bruto, optante, freteiro, cidade_cliente, uf_cliente)
                if tipo in linhas_por_nf[nf]['despesas_por_tipo']:
                    linhas_por_nf[nf]['despesas_por_tipo'][tipo] += valor_liquido

    # Adicionar devoluções
    for nf, valor in devolucoes_por_nf.items():
        if nf in linhas_por_nf:
            linhas_por_nf[nf]['total_devolucao'] = Decimal(str(valor))

    # Converter para lista
    linhas = []
    for nf, dados_nf in linhas_por_nf.items():
        linha = {
            'numero_nf': nf,
            'cnpj_cliente': dados_nf['cnpj_cliente'] or '',
            'nome_cliente': dados_nf['nome_cliente'] or '',
            'uf': dados_nf['uf'] or '',
            'municipio': dados_nf['municipio'] or '',
            'peso_total': float(dados_nf['peso_total']),
            'valor_total': float(dados_nf['valor_total']),
            'total_frete_liquido': float(dados_nf['total_frete_liquido']),
            'total_devolucao': float(dados_nf['total_devolucao']),
            'incoterm': dados_nf['incoterm'] or '',
            'data_fatura': dados_nf['data_fatura'],
            'qtd_fretes': dados_nf['qtd_fretes']
        }

        # Despesas por tipo (12 colunas) e total
        total_despesas = Decimal('0')
        for tipo in TIPOS_DESPESA:
            valor = dados_nf['despesas_por_tipo'].get(tipo, Decimal('0'))
            linha[f'despesa_{tipo}'] = float(valor)
            total_despesas += valor
        linha['total_despesas'] = float(total_despesas)

        linhas.append(linha)

    return linhas


def gerar_visao_frete_nf(dados: Dict) -> List[Dict]:
    """
    Visão C: Uma linha por combinação Frete + NF

    - COM transportadora (faz sentido pois é por frete)
    - Frete SEMPRE líquido
    - Despesas SEMPRE líquidas e abertas por tipo (12 colunas)
    - Pode repetir dados da NF quando a mesma NF aparece em múltiplos fretes
    """
    linhas = []

    fretes = dados['fretes']
    faturamento_por_nf = dados['faturamento_por_nf']
    despesas_por_frete = dados['despesas_por_frete']
    devolucoes_por_nf = dados['devolucoes_por_nf']

    for frete in fretes:
        # Dados da transportadora para cálculo de valor líquido
        optante = frete.get('transportadora_optante', False)
        freteiro = frete.get('transportadora_freteiro', False)

        # Calcular rateio de frete por NF
        frete_rateado_por_nf = calcular_rateio_frete_por_nf(frete, faturamento_por_nf)

        # Calcular rateio de despesas por tipo
        despesas_frete = despesas_por_frete.get(frete['id'], [])
        despesas_por_tipo_por_nf = defaultdict(lambda: {tipo: Decimal('0') for tipo in TIPOS_DESPESA})

        for despesa in despesas_frete:
            rateio_despesa = calcular_rateio_despesa_por_nf(despesa, frete, faturamento_por_nf)
            tipo = despesa['tipo_despesa']
            for nf, valor in rateio_despesa.items():
                if tipo in despesas_por_tipo_por_nf[nf]:
                    despesas_por_tipo_por_nf[nf][tipo] += valor

        # Gerar linhas por Frete + NF
        for nf in frete.get('nfs_no_periodo', []):
            fat = faturamento_por_nf.get(nf, {})
            frete_bruto = frete_rateado_por_nf.get(nf, Decimal('0'))
            devolucao_rateada = devolucoes_por_nf.get(nf, Decimal('0'))
            despesas_nf = despesas_por_tipo_por_nf.get(nf, {})

            # Cidade/UF do cliente para cálculo de ICMS
            cidade_cliente = fat.get('municipio', '')
            uf_cliente = fat.get('uf', '')

            # Frete líquido
            frete_liquido = calcular_valor_liquido(frete_bruto, optante, freteiro, cidade_cliente, uf_cliente)

            linha = {
                'frete_id': frete['id'],
                'numero_nf': nf,
                'cnpj_cliente': fat.get('cnpj_cliente', ''),
                'nome_cliente': fat.get('nome_cliente', ''),
                'uf': fat.get('uf', ''),
                'municipio': fat.get('municipio', ''),
                'numero_cte': frete['numero_cte'],
                'transportadora': frete['transportadora_razao_social'],
                'transportadora_cnpj': frete['transportadora_cnpj'],
                'motorista_proprio': 'Sim' if frete['motorista_proprio'] else 'Não',
                'peso_nf': float(fat.get('peso_total', 0)),
                'valor_nf': float(fat.get('valor_total', 0)),
                'frete_liquido': float(frete_liquido),
                'devolucao': float(devolucao_rateada),
                'incoterm': fat.get('incoterm', ''),
                'data_fatura': fat.get('data_fatura')
            }

            # Despesas por tipo (12 colunas, valor líquido)
            total_despesas = Decimal('0')
            for tipo in TIPOS_DESPESA:
                valor_bruto = despesas_nf.get(tipo, Decimal('0'))
                valor_liquido = calcular_valor_liquido(valor_bruto, optante, freteiro, cidade_cliente, uf_cliente)
                linha[f'despesa_{tipo}'] = float(valor_liquido)
                total_despesas += valor_liquido

            linha['total_despesas'] = float(total_despesas)

            linhas.append(linha)

    return linhas


def gerar_visao_mes_uf(dados: Dict, abrir_por_tipo: bool = False) -> List[Dict]:
    """
    Visão D: Agrupado por Mês + UF

    Colunas:
    - Mês/Ano, Valor, Devolução, Valor Líquido, Frete, Despesa, Frete Total
    - Qtd NFs, % Frete, % Orçado, Dif Orçado/Realizado
    - Se abrir_por_tipo=True: adiciona 12 colunas de despesa por tipo

    Regra especial: Se incoterm = 'RED', considera UF = 'SP'
    """
    agrupamento = defaultdict(lambda: {
        'total_frete_liquido': Decimal('0'),
        'total_despesas_liquido': Decimal('0'),
        'despesas_por_tipo': {tipo: Decimal('0') for tipo in TIPOS_DESPESA},
        'total_devolucoes': Decimal('0'),
        'qtd_nfs': 0,
        'peso_total': Decimal('0'),
        'valor_total': Decimal('0'),
        'incoterms': set()  # Para calcular % orçado médio
    })

    fretes = dados['fretes']
    faturamento_por_nf = dados['faturamento_por_nf']
    despesas_por_frete = dados['despesas_por_frete']
    devolucoes_por_nf = dados['devolucoes_por_nf']

    # Conjunto de NFs já contabilizadas (para não duplicar)
    nfs_contabilizadas = set()

    for frete in fretes:
        # Dados da transportadora para cálculo de valor líquido
        optante = frete.get('transportadora_optante', False)
        freteiro = frete.get('transportadora_freteiro', False)

        frete_rateado_por_nf = calcular_rateio_frete_por_nf(frete, faturamento_por_nf)
        despesas_frete = despesas_por_frete.get(frete['id'], [])

        for nf in frete.get('nfs_no_periodo', []):
            fat = faturamento_por_nf.get(nf, {})
            data_fatura = fat.get('data_fatura')

            if not data_fatura:
                continue

            # Cidade/UF do cliente para cálculo de ICMS
            cidade_cliente = fat.get('municipio', '')
            uf_cliente = fat.get('uf', '')

            # Determinar UF (regra RED)
            incoterm = fat.get('incoterm', '')
            uf = 'SP' if incoterm == 'RED' else (fat.get('uf') or 'N/D')

            # Chave: Mês/Ano + UF
            mes_ano = data_fatura.strftime('%Y-%m')
            chave = (mes_ano, uf)

            # Frete líquido
            frete_bruto = frete_rateado_por_nf.get(nf, Decimal('0'))
            frete_liquido = calcular_valor_liquido(frete_bruto, optante, freteiro, cidade_cliente, uf_cliente)
            agrupamento[chave]['total_frete_liquido'] += frete_liquido

            # Despesas líquidas (total e por tipo)
            for despesa in despesas_frete:
                rateio = calcular_rateio_despesa_por_nf(despesa, frete, faturamento_por_nf)
                tipo = despesa['tipo_despesa']
                valor_bruto = rateio.get(nf, Decimal('0'))
                valor_liquido = calcular_valor_liquido(valor_bruto, optante, freteiro, cidade_cliente, uf_cliente)
                agrupamento[chave]['total_despesas_liquido'] += valor_liquido
                if tipo in agrupamento[chave]['despesas_por_tipo']:
                    agrupamento[chave]['despesas_por_tipo'][tipo] += valor_liquido

            # Contabilizar NF apenas uma vez
            if nf not in nfs_contabilizadas:
                nfs_contabilizadas.add(nf)
                agrupamento[chave]['qtd_nfs'] += 1
                agrupamento[chave]['peso_total'] += Decimal(str(fat.get('peso_total', 0)))
                agrupamento[chave]['valor_total'] += Decimal(str(fat.get('valor_total', 0)))
                agrupamento[chave]['incoterms'].add(incoterm or 'N/D')

                # Devolução
                agrupamento[chave]['total_devolucoes'] += devolucoes_por_nf.get(nf, Decimal('0'))

    # Converter para lista
    linhas = []
    for (mes_ano, uf), dados_grupo in sorted(agrupamento.items()):
        valor = dados_grupo['valor_total']
        devolucao = dados_grupo['total_devolucoes']
        valor_liquido = valor - devolucao
        frete = dados_grupo['total_frete_liquido']
        despesa = dados_grupo['total_despesas_liquido']
        frete_total = frete + despesa

        # % Frete = Frete Total / Valor Líquido
        perc_frete = (frete_total / valor_liquido * 100) if valor_liquido > 0 else Decimal('0')

        # % Orçado - usar o incoterm mais comum do grupo
        incoterms = list(dados_grupo['incoterms'])
        incoterm_principal = incoterms[0] if incoterms else ''
        perc_orcado = Decimal(str(buscar_percentual_orcado(incoterm_principal, uf)))

        # Diferença = (% Orçado - % Frete) / 100 * Valor Líquido
        dif_orcado_realizado = ((perc_orcado - perc_frete) / 100 * valor_liquido) if valor_liquido > 0 else Decimal('0')

        linha = {
            'mes_ano': mes_ano,
            'uf': uf,
            'valor': float(valor),
            'devolucao': float(devolucao),
            'valor_liquido': float(valor_liquido),
            'frete': float(frete),
            'despesa': float(despesa),
            'frete_total': float(frete_total),
            'qtd_nfs': dados_grupo['qtd_nfs'],
            'perc_frete': float(perc_frete.quantize(Decimal('0.01'))),
            'perc_orcado': float(perc_orcado),
            'dif_orcado_realizado': float(dif_orcado_realizado.quantize(Decimal('0.01')))
        }

        # Se abrir por tipo, adicionar 12 colunas de despesa
        if abrir_por_tipo:
            for tipo in TIPOS_DESPESA:
                linha[f'despesa_{tipo}'] = float(dados_grupo['despesas_por_tipo'].get(tipo, Decimal('0')))

        linhas.append(linha)

    return linhas


# =============================================================================
# GERAÇÃO DO EXCEL
# =============================================================================

def gerar_excel_relatorio(dados: Dict, data_inicio: str, data_fim: str, abrir_despesa_tipo: bool = False) -> BytesIO:
    """
    Gera Excel com 4 abas usando xlsxwriter.

    Abas:
    - 'Expandida (NF+Produto)': Visão A - com despesas por tipo
    - 'Por NF': Visão B - sem transportadora, com despesas por tipo
    - 'Por Frete + NF': Visão C - com transportadora, com despesas por tipo
    - 'Por Mês e UF': Visão D - com % Frete, % Orçado, Dif (opcionalmente com despesas por tipo)

    Args:
        dados: Dict com fretes, faturamento, despesas, devoluções
        data_inicio: Data início do período
        data_fim: Data fim do período
        abrir_despesa_tipo: Se True, exibe despesas por tipo na aba Mês+UF
    """
    logger.info("Gerando Excel do relatório de análise de fretes")

    # Gerar visões
    visao_expandida = gerar_visao_expandida(dados)
    visao_por_nf = gerar_visao_por_nf(dados)
    visao_frete_nf = gerar_visao_frete_nf(dados)
    visao_mes_uf = gerar_visao_mes_uf(dados, abrir_por_tipo=abrir_despesa_tipo)

    logger.info(f"Visões geradas: Expandida={len(visao_expandida)}, Por NF={len(visao_por_nf)}, Frete+NF={len(visao_frete_nf)}, Mês+UF={len(visao_mes_uf)}")

    # Criar workbook
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'constant_memory': False})

    # Formatos
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4472C4',
        'font_color': '#FFFFFF',
        'border': 1,
        'text_wrap': True,
        'valign': 'vcenter'
    })

    money_format = workbook.add_format({'num_format': '#,##0.00'})
    percent_format = workbook.add_format({'num_format': '0.00%'})
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
    number_format = workbook.add_format({'num_format': '#,##0.000'})

    # =========================================================================
    # ABA 1: Visão Expandida (NF + Produto)
    # =========================================================================
    ws1 = workbook.add_worksheet('Expandida (NF+Produto)')

    # Colunas fixas + 12 tipos de despesa
    # Ordem: NF, CNPJ Cliente, Nome Cliente, UF, Município, ... (dados cliente na 2ª posição)
    colunas_expandida = [
        ('NF', 12),
        ('CNPJ Cliente', 18),
        ('Nome Cliente', 30),
        ('UF', 5),
        ('Município', 20),
        ('Cód. Produto', 15),
        ('Nome Produto', 30),
        ('Peso Produto', 12),
        ('Valor Produto', 14),
        ('Transportadora', 25),
        ('CNPJ Transp.', 18),
        ('Motorista Próprio', 15),
        ('Nº CTe', 15),
        ('Frete Líquido', 14),
    ]

    # Adicionar 12 colunas de despesa
    for tipo in TIPOS_DESPESA:
        colunas_expandida.append((f'Desp. {tipo}', 14))

    colunas_expandida.extend([
        ('Total Despesas', 14),
        ('Devolução Rateada', 14),
        ('Incoterm', 10),
        ('Data Fatura', 12),
        ('Status Frete', 12)
    ])

    # Escrever cabeçalho
    for col, (nome, largura) in enumerate(colunas_expandida):
        ws1.write(0, col, nome, header_format)
        ws1.set_column(col, col, largura)

    # Escrever dados
    for row, linha in enumerate(visao_expandida, start=1):
        col = 0
        ws1.write(row, col, linha.get('numero_nf', '')); col += 1
        ws1.write(row, col, linha.get('cnpj_cliente', '')); col += 1
        ws1.write(row, col, linha.get('nome_cliente', '')); col += 1
        ws1.write(row, col, linha.get('uf', '')); col += 1
        ws1.write(row, col, linha.get('municipio', '')); col += 1
        ws1.write(row, col, linha.get('cod_produto', '')); col += 1
        ws1.write(row, col, linha.get('nome_produto', '')); col += 1
        ws1.write_number(row, col, linha.get('peso_produto', 0), number_format); col += 1
        ws1.write_number(row, col, linha.get('valor_produto', 0), money_format); col += 1
        ws1.write(row, col, linha.get('transportadora', '')); col += 1
        ws1.write(row, col, linha.get('transportadora_cnpj', '')); col += 1
        ws1.write(row, col, linha.get('motorista_proprio', '')); col += 1
        ws1.write(row, col, linha.get('numero_cte', '')); col += 1
        ws1.write_number(row, col, linha.get('frete_liquido', 0), money_format); col += 1

        # Despesas por tipo (12 colunas)
        for tipo in TIPOS_DESPESA:
            ws1.write_number(row, col, linha.get(f'despesa_{tipo}', 0), money_format)
            col += 1

        ws1.write_number(row, col, linha.get('total_despesas', 0), money_format); col += 1
        ws1.write_number(row, col, linha.get('devolucao_rateada', 0), money_format); col += 1
        ws1.write(row, col, linha.get('incoterm', '')); col += 1

        data_fatura = linha.get('data_fatura')
        if data_fatura:
            ws1.write_datetime(row, col, datetime.combine(data_fatura, datetime.min.time()), date_format)
        else:
            ws1.write(row, col, '')
        col += 1

        ws1.write(row, col, linha.get('status_frete', '')); col += 1

    # =========================================================================
    # ABA 2: Visão Por NF (sem transportadora)
    # =========================================================================
    ws2 = workbook.add_worksheet('Por NF')

    # Ordem: NF, CNPJ Cliente, Nome Cliente, UF, Município, ... (dados cliente na 2ª posição)
    colunas_por_nf = [
        ('NF', 12),
        ('CNPJ Cliente', 18),
        ('Nome Cliente', 30),
        ('UF', 5),
        ('Município', 20),
        ('Peso Total', 12),
        ('Valor Total', 14),
        ('Frete Líquido', 14),
    ]

    # Adicionar 12 colunas de despesa
    for tipo in TIPOS_DESPESA:
        colunas_por_nf.append((f'Desp. {tipo}', 14))

    colunas_por_nf.extend([
        ('Total Despesas', 14),
        ('Total Devolução', 14),
        ('Incoterm', 10),
        ('Data Fatura', 12),
        ('Qtd Fretes', 10)
    ])

    # Escrever cabeçalho
    for col, (nome, largura) in enumerate(colunas_por_nf):
        ws2.write(0, col, nome, header_format)
        ws2.set_column(col, col, largura)

    # Escrever dados
    for row, linha in enumerate(visao_por_nf, start=1):
        col = 0
        ws2.write(row, col, linha.get('numero_nf', '')); col += 1
        ws2.write(row, col, linha.get('cnpj_cliente', '')); col += 1
        ws2.write(row, col, linha.get('nome_cliente', '')); col += 1
        ws2.write(row, col, linha.get('uf', '')); col += 1
        ws2.write(row, col, linha.get('municipio', '')); col += 1
        ws2.write_number(row, col, linha.get('peso_total', 0), number_format); col += 1
        ws2.write_number(row, col, linha.get('valor_total', 0), money_format); col += 1
        ws2.write_number(row, col, linha.get('total_frete_liquido', 0), money_format); col += 1

        # Despesas por tipo (12 colunas)
        for tipo in TIPOS_DESPESA:
            ws2.write_number(row, col, linha.get(f'despesa_{tipo}', 0), money_format)
            col += 1

        ws2.write_number(row, col, linha.get('total_despesas', 0), money_format); col += 1
        ws2.write_number(row, col, linha.get('total_devolucao', 0), money_format); col += 1
        ws2.write(row, col, linha.get('incoterm', '')); col += 1

        data_fatura = linha.get('data_fatura')
        if data_fatura:
            ws2.write_datetime(row, col, datetime.combine(data_fatura, datetime.min.time()), date_format)
        else:
            ws2.write(row, col, '')
        col += 1

        ws2.write_number(row, col, linha.get('qtd_fretes', 0)); col += 1

    # =========================================================================
    # ABA 3: Visão Por Frete + NF (NOVA)
    # =========================================================================
    ws3 = workbook.add_worksheet('Por Frete + NF')

    # Ordem: Frete ID, NF, CNPJ Cliente, Nome Cliente, UF, Município, ... (dados cliente na 2ª posição após NF)
    colunas_frete_nf = [
        ('Frete ID', 10),
        ('NF', 12),
        ('CNPJ Cliente', 18),
        ('Nome Cliente', 30),
        ('UF', 5),
        ('Município', 20),
        ('Nº CTe', 15),
        ('Transportadora', 25),
        ('CNPJ Transp.', 18),
        ('Mot. Próprio', 12),
        ('Peso NF', 12),
        ('Valor NF', 14),
        ('Frete Líquido', 14),
    ]

    # Adicionar 12 colunas de despesa
    for tipo in TIPOS_DESPESA:
        colunas_frete_nf.append((f'Desp. {tipo}', 14))

    colunas_frete_nf.extend([
        ('Total Despesas', 14),
        ('Devolução', 14),
        ('Incoterm', 10),
        ('Data Fatura', 12)
    ])

    # Escrever cabeçalho
    for col, (nome, largura) in enumerate(colunas_frete_nf):
        ws3.write(0, col, nome, header_format)
        ws3.set_column(col, col, largura)

    # Escrever dados
    for row, linha in enumerate(visao_frete_nf, start=1):
        col = 0
        ws3.write_number(row, col, linha.get('frete_id', 0)); col += 1
        ws3.write(row, col, linha.get('numero_nf', '')); col += 1
        ws3.write(row, col, linha.get('cnpj_cliente', '')); col += 1
        ws3.write(row, col, linha.get('nome_cliente', '')); col += 1
        ws3.write(row, col, linha.get('uf', '')); col += 1
        ws3.write(row, col, linha.get('municipio', '')); col += 1
        ws3.write(row, col, linha.get('numero_cte', '')); col += 1
        ws3.write(row, col, linha.get('transportadora', '')); col += 1
        ws3.write(row, col, linha.get('transportadora_cnpj', '')); col += 1
        ws3.write(row, col, linha.get('motorista_proprio', '')); col += 1
        ws3.write_number(row, col, linha.get('peso_nf', 0), number_format); col += 1
        ws3.write_number(row, col, linha.get('valor_nf', 0), money_format); col += 1
        ws3.write_number(row, col, linha.get('frete_liquido', 0), money_format); col += 1

        # Despesas por tipo (12 colunas)
        for tipo in TIPOS_DESPESA:
            ws3.write_number(row, col, linha.get(f'despesa_{tipo}', 0), money_format)
            col += 1

        ws3.write_number(row, col, linha.get('total_despesas', 0), money_format); col += 1
        ws3.write_number(row, col, linha.get('devolucao', 0), money_format); col += 1
        ws3.write(row, col, linha.get('incoterm', '')); col += 1

        data_fatura = linha.get('data_fatura')
        if data_fatura:
            ws3.write_datetime(row, col, datetime.combine(data_fatura, datetime.min.time()), date_format)
        else:
            ws3.write(row, col, '')
        col += 1

    # =========================================================================
    # ABA 4: Visão Por Mês + UF (REESTRUTURADA)
    # =========================================================================
    ws4 = workbook.add_worksheet('Por Mês e UF')

    colunas_mes_uf = [
        ('Mês/Ano', 12),
        ('UF', 5),
        ('Valor', 14),
        ('Devolução', 14),
        ('Valor Líquido', 14),
        ('Frete', 14),
    ]

    # Se abrir por tipo, adicionar 12 colunas de despesa antes do total
    if abrir_despesa_tipo:
        for tipo in TIPOS_DESPESA:
            colunas_mes_uf.append((f'Desp. {tipo}', 14))

    colunas_mes_uf.extend([
        ('Despesa', 14),
        ('Frete Total', 14),
        ('Qtd NFs', 10),
        ('% Frete', 10),
        ('% Orçado', 10),
        ('Dif Orçado/Real', 14)
    ])

    # Escrever cabeçalho
    for col, (nome, largura) in enumerate(colunas_mes_uf):
        ws4.write(0, col, nome, header_format)
        ws4.set_column(col, col, largura)

    # Escrever dados
    for row, linha in enumerate(visao_mes_uf, start=1):
        col = 0
        ws4.write(row, col, linha.get('mes_ano', '')); col += 1
        ws4.write(row, col, linha.get('uf', '')); col += 1
        ws4.write_number(row, col, linha.get('valor', 0), money_format); col += 1
        ws4.write_number(row, col, linha.get('devolucao', 0), money_format); col += 1
        ws4.write_number(row, col, linha.get('valor_liquido', 0), money_format); col += 1
        ws4.write_number(row, col, linha.get('frete', 0), money_format); col += 1

        # Se abrir por tipo, adicionar 12 colunas de despesa
        if abrir_despesa_tipo:
            for tipo in TIPOS_DESPESA:
                ws4.write_number(row, col, linha.get(f'despesa_{tipo}', 0), money_format)
                col += 1

        ws4.write_number(row, col, linha.get('despesa', 0), money_format); col += 1
        ws4.write_number(row, col, linha.get('frete_total', 0), money_format); col += 1
        ws4.write_number(row, col, linha.get('qtd_nfs', 0)); col += 1
        ws4.write_number(row, col, linha.get('perc_frete', 0) / 100, percent_format); col += 1
        ws4.write_number(row, col, linha.get('perc_orcado', 0) / 100, percent_format); col += 1
        ws4.write_number(row, col, linha.get('dif_orcado_realizado', 0), money_format); col += 1

    workbook.close()
    output.seek(0)

    logger.info("Excel gerado com sucesso")
    return output


# =============================================================================
# RELATÓRIO DEDICADO DE DESPESAS EXTRAS
# =============================================================================
# Indexa pelas DESPESAS (não pelas NFs). Preserva todas as 4 dimensões
# classificatórias (tipo_despesa, setor_responsavel, motivo_despesa, observacoes)
# que ficam aplainadas no relatório principal por causa da matriz de tipos.
# =============================================================================


def gerar_visao_despesas_detalhada(dados: Dict) -> List[Dict]:
    """
    Visão Detalhada: 1 linha por DESPESA (valor íntegro, não rateado).

    - Valor da despesa: total íntegro (não fragmentado por NF)
    - Valor líquido da despesa: soma dos líquidos calculados por NF
      (necessário porque ICMS varia por cidade do destinatário)
    - NFs do frete concatenadas com vírgula
    - Cliente/UF/Cidade: distintos concatenados
    - Peso/Valor das NFs e Frete Líquido: SOMA das NFs do frete no período
    - Datas de fatura: min..max

    Returns:
        Lista de dicts, 1 por despesa.
    """
    linhas = []

    fretes = dados['fretes']
    faturamento_por_nf = dados['faturamento_por_nf']
    despesas_por_frete = dados['despesas_por_frete']

    for frete in fretes:
        optante = frete.get('transportadora_optante', False)
        freteiro = frete.get('transportadora_freteiro', False)

        despesas_frete = despesas_por_frete.get(frete['id'], [])
        if not despesas_frete:
            continue

        nfs_periodo = frete.get('nfs_no_periodo', []) or []
        if not nfs_periodo:
            continue

        frete_rateado_por_nf = calcular_rateio_frete_por_nf(frete, faturamento_por_nf)

        # ----- Agregados das NFs do frete (mesmos para todas as despesas do frete) -----
        nfs_ordenadas = sorted(nfs_periodo)
        cnpjs_cliente_set = []
        nomes_cliente_set = []
        ufs_set = []
        municipios_set = []
        incoterms_set = []
        peso_total_nfs = Decimal('0')
        valor_total_nfs = Decimal('0')
        frete_liquido_total_nfs = Decimal('0')
        datas_fatura = []

        for nf in nfs_ordenadas:
            fat = faturamento_por_nf.get(nf, {})
            cnpj = fat.get('cnpj_cliente') or ''
            nome = fat.get('nome_cliente') or ''
            uf = fat.get('uf') or ''
            mun = fat.get('municipio') or ''
            inco = fat.get('incoterm') or ''

            if cnpj and cnpj not in cnpjs_cliente_set:
                cnpjs_cliente_set.append(cnpj)
            if nome and nome not in nomes_cliente_set:
                nomes_cliente_set.append(nome)
            if uf and uf not in ufs_set:
                ufs_set.append(uf)
            if mun and mun not in municipios_set:
                municipios_set.append(mun)
            if inco and inco not in incoterms_set:
                incoterms_set.append(inco)

            peso_total_nfs += Decimal(str(fat.get('peso_total', 0)))
            valor_total_nfs += Decimal(str(fat.get('valor_total', 0)))

            frete_bruto_nf = frete_rateado_por_nf.get(nf, Decimal('0'))
            frete_liq_nf = calcular_valor_liquido(
                frete_bruto_nf, optante, freteiro, mun, uf
            )
            frete_liquido_total_nfs += frete_liq_nf

            data_fat = fat.get('data_fatura')
            if data_fat:
                datas_fatura.append(data_fat)

        data_min = min(datas_fatura) if datas_fatura else None
        data_max = max(datas_fatura) if datas_fatura else None

        # ----- Linha por despesa -----
        for despesa in despesas_frete:
            valor_total_despesa = Decimal(str(despesa.get('valor_despesa') or 0))

            # Líquido = soma dos líquidos rateados por NF (ICMS varia por cidade).
            # Reaproveita rateio por peso já implementado.
            rateio_despesa = calcular_rateio_despesa_por_nf(despesa, frete, faturamento_por_nf)
            valor_liquido_total = Decimal('0')
            for nf in nfs_ordenadas:
                fat = faturamento_por_nf.get(nf, {})
                valor_bruto = rateio_despesa.get(nf, Decimal('0'))
                if valor_bruto == 0:
                    continue
                valor_liquido_total += calcular_valor_liquido(
                    valor_bruto, optante, freteiro, fat.get('municipio', ''), fat.get('uf', '')
                )

            linhas.append({
                'despesa_id': despesa['id'],
                'tipo_despesa': despesa['tipo_despesa'],
                'setor_responsavel': despesa.get('setor_responsavel') or '',
                'motivo_despesa': despesa.get('motivo_despesa') or '',
                'tipo_documento': despesa.get('tipo_documento') or '',
                'numero_documento': despesa.get('numero_documento') or '',
                'valor_despesa_total': float(valor_total_despesa),
                'valor_despesa_liquido': float(valor_liquido_total),
                'status_despesa': despesa.get('status') or '',
                'observacoes': despesa.get('observacoes') or '',
                'criado_em': despesa.get('criado_em'),
                'criado_por': despesa.get('criado_por') or '',
                'vencimento': despesa.get('vencimento_despesa'),
                'frete_id': frete['id'],
                'numero_cte': frete['numero_cte'] or '',
                'transportadora': frete['transportadora_razao_social'],
                'transportadora_cnpj': frete['transportadora_cnpj'] or '',
                'motorista_proprio': 'Sim' if frete['motorista_proprio'] else 'Não',
                'qtd_nfs': len(nfs_ordenadas),
                'numeros_nfs': ', '.join(nfs_ordenadas),
                'cnpjs_clientes': ', '.join(cnpjs_cliente_set),
                'nomes_clientes': ', '.join(nomes_cliente_set),
                'ufs': ', '.join(ufs_set),
                'municipios': ', '.join(municipios_set),
                'peso_total_nfs': float(peso_total_nfs),
                'valor_total_nfs': float(valor_total_nfs),
                'frete_liquido_total_nfs': float(frete_liquido_total_nfs),
                'incoterms': ', '.join(incoterms_set),
                'data_fatura_min': data_min,
                'data_fatura_max': data_max,
            })

    # Ordenar por frete_id, depois despesa_id (estável e previsível)
    linhas.sort(key=lambda r: (r['frete_id'], r['despesa_id']))
    return linhas


def _gerar_visao_despesas_agrupada(dados: Dict, dimensao: str) -> List[Dict]:
    """
    Helper compartilhado entre visão por Setor e visão por Motivo.

    Args:
        dados: dict com fretes/faturamento/despesas/devolucoes
        dimensao: 'setor_responsavel' ou 'motivo_despesa'

    Returns:
        Lista de dicts agrupados por (mes_ano, uf, dimensao).
    """
    fretes = dados['fretes']
    faturamento_por_nf = dados['faturamento_por_nf']
    despesas_por_frete = dados['despesas_por_frete']

    # Dicts separados por chave (mes_ano, uf, dimensao) — evita defaultdict aninhado
    valor_liquido_por_chave: Dict[Tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal('0'))
    valor_bruto_por_chave: Dict[Tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal('0'))
    despesas_unicas_por_chave: Dict[Tuple[str, str, str], set] = defaultdict(set)
    nfs_unicas_por_chave: Dict[Tuple[str, str, str], set] = defaultdict(set)

    for frete in fretes:
        optante = frete.get('transportadora_optante', False)
        freteiro = frete.get('transportadora_freteiro', False)
        despesas_frete = despesas_por_frete.get(frete['id'], [])
        if not despesas_frete:
            continue

        for despesa in despesas_frete:
            chave_dim = despesa.get(dimensao) or 'NÃO INFORMADO'
            rateio_despesa = calcular_rateio_despesa_por_nf(despesa, frete, faturamento_por_nf)

            for nf, valor_bruto in rateio_despesa.items():
                if valor_bruto == 0:
                    continue
                fat = faturamento_por_nf.get(nf, {})
                data_fatura = fat.get('data_fatura')
                if not data_fatura:
                    continue

                cidade_cliente = fat.get('municipio', '')
                uf_cliente = fat.get('uf', '')
                # Aplicar regra RED como na visão Mês+UF
                incoterm = fat.get('incoterm', '')
                uf_grupo = 'SP' if incoterm == 'RED' else (uf_cliente or 'N/D')

                valor_liquido = calcular_valor_liquido(
                    valor_bruto, optante, freteiro, cidade_cliente, uf_cliente
                )

                mes_ano = data_fatura.strftime('%Y-%m')
                chave: Tuple[str, str, str] = (mes_ano, uf_grupo, chave_dim)

                valor_liquido_por_chave[chave] += valor_liquido
                valor_bruto_por_chave[chave] += valor_bruto
                despesas_unicas_por_chave[chave].add(despesa['id'])
                nfs_unicas_por_chave[chave].add(nf)

    # Converter para lista
    chave_label = 'setor' if dimensao == 'setor_responsavel' else 'motivo'
    linhas = []
    for chave in sorted(despesas_unicas_por_chave.keys()):
        mes_ano, uf, dim_valor = chave
        nfs = nfs_unicas_por_chave[chave]

        # Valor e peso das NFs únicas atingidas
        valor_nfs = Decimal('0')
        peso_nfs = Decimal('0')
        for nf in nfs:
            fat = faturamento_por_nf.get(nf, {})
            valor_nfs += Decimal(str(fat.get('valor_total', 0)))
            peso_nfs += Decimal(str(fat.get('peso_total', 0)))

        linhas.append({
            'mes_ano': mes_ano,
            'uf': uf,
            chave_label: dim_valor,
            'valor_despesa_liquido': float(valor_liquido_por_chave[chave]),
            'valor_despesa_bruto': float(valor_bruto_por_chave[chave]),
            'qtd_despesas': len(despesas_unicas_por_chave[chave]),
            'qtd_nfs': len(nfs),
            'valor_nfs': float(valor_nfs),
            'peso_nfs': float(peso_nfs),
        })

    return linhas


def gerar_visao_despesas_por_setor_uf_mes(dados: Dict) -> List[Dict]:
    """Agrupa despesas por (Mês/Ano, UF, Setor Responsável)."""
    return _gerar_visao_despesas_agrupada(dados, 'setor_responsavel')


def gerar_visao_despesas_por_motivo_uf_mes(dados: Dict) -> List[Dict]:
    """Agrupa despesas por (Mês/Ano, UF, Motivo da Despesa)."""
    return _gerar_visao_despesas_agrupada(dados, 'motivo_despesa')


def gerar_excel_despesas_extras(dados: Dict, data_inicio: str, data_fim: str) -> BytesIO:
    """
    Gera Excel dedicado de despesas extras com 3 abas:
    - 'Detalhada': 1 linha por despesa × NF rateada
    - 'Por Setor/UF/Mês': agrupado por setor responsável
    - 'Por Motivo/UF/Mês': agrupado por motivo da despesa

    Reutiliza calcular_valor_liquido (ICMS + freteiro) e
    calcular_rateio_despesa_por_nf (rateio por peso).
    """
    logger.info("Gerando Excel de despesas extras detalhadas")

    visao_detalhada = gerar_visao_despesas_detalhada(dados)
    visao_setor = gerar_visao_despesas_por_setor_uf_mes(dados)
    visao_motivo = gerar_visao_despesas_por_motivo_uf_mes(dados)

    logger.info(
        "Visões geradas: Detalhada=%d, Setor=%d, Motivo=%d",
        len(visao_detalhada), len(visao_setor), len(visao_motivo)
    )

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'constant_memory': False})

    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4472C4',
        'font_color': '#FFFFFF',
        'border': 1,
        'text_wrap': True,
        'valign': 'vcenter'
    })
    money_format = workbook.add_format({'num_format': '#,##0.00'})
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
    datetime_format = workbook.add_format({'num_format': 'dd/mm/yyyy hh:mm'})
    number_format = workbook.add_format({'num_format': '#,##0.000'})

    # =========================================================================
    # ABA 1: Detalhada (1 linha por DESPESA — valor íntegro, NFs concatenadas)
    # =========================================================================
    ws1 = workbook.add_worksheet('Detalhada')

    colunas_detalhada = [
        ('Despesa ID', 11),
        ('Tipo Despesa', 18),
        ('Setor Responsável', 16),
        ('Motivo', 24),
        ('Tipo Doc.', 10),
        ('Nº Documento', 16),
        ('Valor Despesa (Total)', 18),
        ('Valor Despesa (Líquido)', 18),
        ('Status', 14),
        ('Vencimento', 12),
        ('Criado em', 16),
        ('Criado por', 18),
        ('Frete ID', 10),
        ('Nº CTe', 14),
        ('Transportadora', 25),
        ('CNPJ Transp.', 18),
        ('Mot. Próprio', 12),
        ('Qtd NFs', 8),
        ('NFs', 30),
        ('CNPJs Clientes', 30),
        ('Nomes Clientes', 40),
        ('UFs', 12),
        ('Municípios', 30),
        ('Peso Total NFs', 14),
        ('Valor Total NFs', 16),
        ('Frete Líquido Total NFs', 18),
        ('Incoterms', 14),
        ('Data Fatura (Mín)', 14),
        ('Data Fatura (Máx)', 14),
        ('Observações', 40),
    ]

    for col, (nome, largura) in enumerate(colunas_detalhada):
        ws1.write(0, col, nome, header_format)
        ws1.set_column(col, col, largura)

    for row, linha in enumerate(visao_detalhada, start=1):
        col = 0
        ws1.write_number(row, col, linha.get('despesa_id', 0)); col += 1
        ws1.write(row, col, linha.get('tipo_despesa', '')); col += 1
        ws1.write(row, col, linha.get('setor_responsavel', '')); col += 1
        ws1.write(row, col, linha.get('motivo_despesa', '')); col += 1
        ws1.write(row, col, linha.get('tipo_documento', '')); col += 1
        ws1.write(row, col, linha.get('numero_documento', '')); col += 1
        ws1.write_number(row, col, linha.get('valor_despesa_total', 0), money_format); col += 1
        ws1.write_number(row, col, linha.get('valor_despesa_liquido', 0), money_format); col += 1
        ws1.write(row, col, linha.get('status_despesa', '')); col += 1

        venc = linha.get('vencimento')
        if venc:
            ws1.write_datetime(row, col, datetime.combine(venc, datetime.min.time()), date_format)
        else:
            ws1.write(row, col, '')
        col += 1

        criado = linha.get('criado_em')
        if criado:
            ws1.write_datetime(row, col, criado, datetime_format)
        else:
            ws1.write(row, col, '')
        col += 1

        ws1.write(row, col, linha.get('criado_por', '')); col += 1
        ws1.write_number(row, col, linha.get('frete_id', 0)); col += 1
        ws1.write(row, col, linha.get('numero_cte', '')); col += 1
        ws1.write(row, col, linha.get('transportadora', '')); col += 1
        ws1.write(row, col, linha.get('transportadora_cnpj', '')); col += 1
        ws1.write(row, col, linha.get('motorista_proprio', '')); col += 1
        ws1.write_number(row, col, linha.get('qtd_nfs', 0)); col += 1
        ws1.write(row, col, linha.get('numeros_nfs', '')); col += 1
        ws1.write(row, col, linha.get('cnpjs_clientes', '')); col += 1
        ws1.write(row, col, linha.get('nomes_clientes', '')); col += 1
        ws1.write(row, col, linha.get('ufs', '')); col += 1
        ws1.write(row, col, linha.get('municipios', '')); col += 1
        ws1.write_number(row, col, linha.get('peso_total_nfs', 0), number_format); col += 1
        ws1.write_number(row, col, linha.get('valor_total_nfs', 0), money_format); col += 1
        ws1.write_number(row, col, linha.get('frete_liquido_total_nfs', 0), money_format); col += 1
        ws1.write(row, col, linha.get('incoterms', '')); col += 1

        dmin = linha.get('data_fatura_min')
        if dmin:
            ws1.write_datetime(row, col, datetime.combine(dmin, datetime.min.time()), date_format)
        else:
            ws1.write(row, col, '')
        col += 1

        dmax = linha.get('data_fatura_max')
        if dmax:
            ws1.write_datetime(row, col, datetime.combine(dmax, datetime.min.time()), date_format)
        else:
            ws1.write(row, col, '')
        col += 1

        ws1.write(row, col, linha.get('observacoes', '')); col += 1

    # Congelar linha de cabeçalho
    ws1.freeze_panes(1, 0)
    # Auto-filter
    if visao_detalhada:
        ws1.autofilter(0, 0, len(visao_detalhada), len(colunas_detalhada) - 1)

    # =========================================================================
    # ABA 2: Por Setor + UF + Mês
    # =========================================================================
    ws2 = workbook.add_worksheet('Por Setor UF Mês')

    colunas_setor = [
        ('Mês/Ano', 12),
        ('UF', 5),
        ('Setor Responsável', 18),
        ('Despesa Líquida', 16),
        ('Despesa Bruta', 16),
        ('Qtd Despesas', 12),
        ('Qtd NFs Atingidas', 16),
        ('Valor NFs Atingidas', 18),
        ('Peso NFs Atingidas', 16),
    ]

    for col, (nome, largura) in enumerate(colunas_setor):
        ws2.write(0, col, nome, header_format)
        ws2.set_column(col, col, largura)

    for row, linha in enumerate(visao_setor, start=1):
        col = 0
        ws2.write(row, col, linha.get('mes_ano', '')); col += 1
        ws2.write(row, col, linha.get('uf', '')); col += 1
        ws2.write(row, col, linha.get('setor', '')); col += 1
        ws2.write_number(row, col, linha.get('valor_despesa_liquido', 0), money_format); col += 1
        ws2.write_number(row, col, linha.get('valor_despesa_bruto', 0), money_format); col += 1
        ws2.write_number(row, col, linha.get('qtd_despesas', 0)); col += 1
        ws2.write_number(row, col, linha.get('qtd_nfs', 0)); col += 1
        ws2.write_number(row, col, linha.get('valor_nfs', 0), money_format); col += 1
        ws2.write_number(row, col, linha.get('peso_nfs', 0), number_format); col += 1

    ws2.freeze_panes(1, 0)
    if visao_setor:
        ws2.autofilter(0, 0, len(visao_setor), len(colunas_setor) - 1)

    # =========================================================================
    # ABA 3: Por Motivo + UF + Mês
    # =========================================================================
    ws3 = workbook.add_worksheet('Por Motivo UF Mês')

    colunas_motivo = [
        ('Mês/Ano', 12),
        ('UF', 5),
        ('Motivo', 28),
        ('Despesa Líquida', 16),
        ('Despesa Bruta', 16),
        ('Qtd Despesas', 12),
        ('Qtd NFs Atingidas', 16),
        ('Valor NFs Atingidas', 18),
        ('Peso NFs Atingidas', 16),
    ]

    for col, (nome, largura) in enumerate(colunas_motivo):
        ws3.write(0, col, nome, header_format)
        ws3.set_column(col, col, largura)

    for row, linha in enumerate(visao_motivo, start=1):
        col = 0
        ws3.write(row, col, linha.get('mes_ano', '')); col += 1
        ws3.write(row, col, linha.get('uf', '')); col += 1
        ws3.write(row, col, linha.get('motivo', '')); col += 1
        ws3.write_number(row, col, linha.get('valor_despesa_liquido', 0), money_format); col += 1
        ws3.write_number(row, col, linha.get('valor_despesa_bruto', 0), money_format); col += 1
        ws3.write_number(row, col, linha.get('qtd_despesas', 0)); col += 1
        ws3.write_number(row, col, linha.get('qtd_nfs', 0)); col += 1
        ws3.write_number(row, col, linha.get('valor_nfs', 0), money_format); col += 1
        ws3.write_number(row, col, linha.get('peso_nfs', 0), number_format); col += 1

    ws3.freeze_panes(1, 0)
    if visao_motivo:
        ws3.autofilter(0, 0, len(visao_motivo), len(colunas_motivo) - 1)

    workbook.close()
    output.seek(0)

    logger.info("Excel de despesas extras gerado com sucesso")
    return output

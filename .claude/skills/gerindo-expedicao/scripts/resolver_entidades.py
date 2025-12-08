#!/usr/bin/env python3
"""
Modulo: resolver_entidades.py
Centraliza resolucao de entidades do dominio logistico.

Seguindo recomendacoes da Anthropic:
- "Tools should be self-contained, robust to error"
- "Scripts must solve problems, not transfer them to Claude"

Este modulo resolve:
- Pedidos: por numero parcial, grupo empresarial, cliente
- Produtos: por nome, abreviacoes, caracteristicas (CadastroPalletizacao)
- Cidades: por nome normalizado (sem acentos, case-insensitive)
- Grupos: prefixos CNPJ + pedidos do grupo
- UF: pedidos de uma UF especifica

Uso:
    from resolver_entidades import (
        resolver_pedido,
        resolver_produto,
        resolver_cidade,
        resolver_grupo,
        resolver_uf,
        normalizar_texto
    )

    # Resolver pedido
    itens, num_pedido, info = resolver_pedido("VCD1")        # Parcial
    itens, num_pedido, info = resolver_pedido("atacadao 183") # Grupo + loja

    # Resolver grupo (NOVO - formato rico)
    resultado = resolver_grupo("atacadao", uf="SP", loja="183")
    # → {'sucesso': True, 'grupo': 'atacadao', 'pedidos': [...], 'resumo': {...}}

    # Resolver UF (NOVO)
    resultado = resolver_uf("SP")
    # → {'sucesso': True, 'uf': 'SP', 'pedidos': [...], 'resumo': {...}}

    # Resolver produto
    produtos = resolver_produto("pessego")        # Termo unico
    produtos = resolver_produto("pf mezzani")     # Abreviacoes

    # Resolver cidade (normaliza acentos)
    pedidos = resolver_cidade("itanhaem")  # Encontra "Itanhaém", "ITANHAEM", etc.

    # Normalizar texto (util para comparacoes)
    normalizar_texto("Itanhaém")  # -> "itanhaem"
"""
import sys
import os
import unicodedata

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


# ============================================================
# FUNCOES DE NORMALIZACAO
# ============================================================
def normalizar_texto(texto: str) -> str:
    """
    Normaliza texto removendo acentos e convertendo para minusculas.

    Util para comparacoes de cidades, clientes, produtos onde
    podem haver variacoes de acentuacao e case.

    Args:
        texto: Texto original (ex: "Itanhaém", "São Paulo")

    Returns:
        str: Texto normalizado (ex: "itanhaem", "sao paulo")

    Exemplos:
        normalizar_texto("Itanhaém") -> "itanhaem"
        normalizar_texto("São Paulo") -> "sao paulo"
        normalizar_texto("PERUÍBE") -> "peruibe"
        normalizar_texto("Mongaguá") -> "mongagua"
    """
    if not texto:
        return ""
    # Remove acentos via NFD (decomposicao) e remove combining characters
    texto_sem_acento = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return texto_sem_acento.lower().strip()

# ============================================================
# GRUPOS EMPRESARIAIS
# Prefixos CNPJ (formato com pontos conforme banco)
# ============================================================
GRUPOS_EMPRESARIAIS = {
    'atacadao': ['93.209.76', '75.315.33', '00.063.96'],
    'assai': ['06.057.22'],
    'tenda': ['01.157.55']
}


def get_prefixos_grupo(grupo: str) -> list:
    """
    Retorna prefixos CNPJ de um grupo empresarial.

    Args:
        grupo: Nome do grupo (atacadao, assai, tenda)

    Returns:
        Lista de prefixos CNPJ ou lista vazia se grupo nao encontrado
    """
    return GRUPOS_EMPRESARIAIS.get(grupo.lower().strip(), [])


def listar_grupos_disponiveis() -> list:
    """Retorna lista de grupos empresariais disponiveis"""
    return list(GRUPOS_EMPRESARIAIS.keys())


def resolver_grupo(grupo: str, uf: str = None, loja: str = None, fonte: str = 'carteira') -> dict:
    """
    Resolve grupo empresarial retornando prefixos CNPJ + pedidos.

    Args:
        grupo: Nome do grupo (atacadao, assai, tenda)
        uf: Filtro opcional por UF (ex: 'SP')
        loja: Filtro opcional por identificador da loja em raz_social_red (ex: '183')
        fonte: 'carteira', 'separacao' ou 'ambos'

    Returns:
        dict: {
            'sucesso': bool,
            'grupo': str,
            'prefixos_cnpj': list,
            'filtros_aplicados': dict,
            'pedidos': list[dict],  # Lista de pedidos únicos com metadados
            'resumo': dict,
            'erro': str (se sucesso=False)
        }

    Exemplo:
        >>> resolver_grupo('atacadao', uf='SP', loja='183')
        {
            'sucesso': True,
            'grupo': 'atacadao',
            'prefixos_cnpj': ['93.209.76', '75.315.33', '00.063.96'],
            'filtros_aplicados': {'uf': 'SP', 'loja': '183'},
            'pedidos': [
                {
                    'num_pedido': 'VCD2565291',
                    'cnpj': '75.315.333/0183-18',
                    'cliente': 'ATACADAO 183',
                    'cidade': 'Jacareí',
                    'uf': 'SP',
                    'total_itens': 15,
                    'valor_total': 1885496.64
                }
            ],
            'resumo': {
                'total_pedidos': 2,
                'total_valor': 2168165.64,
                'ufs': ['SP'],
                'cidades': ['Jacareí'],
                'lojas': ['183']
            }
        }
    """
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from sqlalchemy import or_, func
    from collections import defaultdict

    grupo_lower = grupo.lower().strip()

    # Buscar prefixos CNPJ
    prefixos = get_prefixos_grupo(grupo_lower)

    if not prefixos:
        return {
            'sucesso': False,
            'grupo': grupo,
            'erro': f"Grupo '{grupo}' não encontrado",
            'grupos_disponiveis': listar_grupos_disponiveis()
        }

    # Montar filtros
    filtros_aplicados = {}
    if uf:
        filtros_aplicados['uf'] = uf.upper()
    if loja:
        filtros_aplicados['loja'] = loja

    # Escolher fonte
    if fonte == 'carteira':
        Model = CarteiraPrincipal
        filtro_saldo = CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    elif fonte == 'separacao':
        Model = Separacao
        filtro_saldo = Separacao.sincronizado_nf == False
    else:  # ambos - priorizar carteira
        Model = CarteiraPrincipal
        filtro_saldo = CarteiraPrincipal.qtd_saldo_produto_pedido > 0

    # Construir query base com filtros de CNPJ
    filtros_cnpj = [Model.cnpj_cpf.like(f'{prefixo}%') for prefixo in prefixos]
    query = Model.query.filter(or_(*filtros_cnpj), filtro_saldo)

    # Aplicar filtros adicionais
    if uf:
        query = query.filter(Model.cod_uf == uf.upper())

    if loja:
        query = query.filter(Model.raz_social_red.ilike(f'%{loja}%'))

    # Executar query
    itens = query.all()

    if not itens:
        return {
            'sucesso': False,
            'grupo': grupo,
            'prefixos_cnpj': prefixos,
            'filtros_aplicados': filtros_aplicados,
            'erro': 'Nenhum pedido encontrado com os filtros aplicados',
            'sugestao': 'Tente remover filtros de UF ou loja'
        }

    # Agrupar por pedido
    pedidos_dict = defaultdict(lambda: {
        'itens': [],
        'valor_total': 0,
        'total_itens': 0
    })

    for item in itens:
        num = item.num_pedido
        pedidos_dict[num]['num_pedido'] = num
        pedidos_dict[num]['cnpj'] = item.cnpj_cpf
        pedidos_dict[num]['cliente'] = item.raz_social_red or item.raz_social
        pedidos_dict[num]['cidade'] = item.nome_cidade or item.municipio
        pedidos_dict[num]['uf'] = item.cod_uf or item.estado
        pedidos_dict[num]['itens'].append(item)
        pedidos_dict[num]['total_itens'] += 1 # type: ignore

        # Calcular valor
        if fonte == 'carteira':
            valor_item = float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)
        else:
            valor_item = float(item.valor_saldo or 0)

        pedidos_dict[num]['valor_total'] += valor_item # type: ignore

    # Converter para lista
    pedidos = []
    for num, dados in pedidos_dict.items():
        pedidos.append({
            'num_pedido': num,
            'cnpj': dados['cnpj'],
            'cliente': dados['cliente'],
            'cidade': dados['cidade'],
            'uf': dados['uf'],
            'total_itens': dados['total_itens'],
            'valor_total': round(dados['valor_total'], 2)
        })

    # Ordenar por valor (maior primeiro)
    pedidos.sort(key=lambda p: p['valor_total'], reverse=True)

    # Calcular resumo
    total_valor = sum(p['valor_total'] for p in pedidos)
    ufs = sorted(set(p['uf'] for p in pedidos if p['uf']))
    cidades = sorted(set(p['cidade'] for p in pedidos if p['cidade']))
    lojas = sorted(set(p['cliente'].split()[-1] for p in pedidos if p['cliente']))  # Extrai numero da loja

    return {
        'sucesso': True,
        'grupo': grupo,
        'prefixos_cnpj': prefixos,
        'filtros_aplicados': filtros_aplicados,
        'fonte': fonte,
        'pedidos': pedidos,
        'resumo': {
            'total_pedidos': len(pedidos),
            'total_valor': round(total_valor, 2),
            'ufs': ufs,
            'cidades': cidades,
            'lojas': lojas
        }
    }


def resolver_uf(uf: str, fonte: str = 'carteira') -> dict:
    """
    Resolve pedidos de uma UF específica.

    Args:
        uf: Sigla da UF (ex: 'SP', 'RJ')
        fonte: 'carteira', 'separacao' ou 'ambos'

    Returns:
        dict: Similar a resolver_grupo, mas filtrado por UF

    Exemplo:
        >>> resolver_uf('SP')
        {
            'sucesso': True,
            'uf': 'SP',
            'pedidos': [...],
            'resumo': {...}
        }
    """
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from collections import defaultdict

    uf_upper = uf.upper().strip()

    # Validar UF (lista de UFs válidas)
    UFS_VALIDAS = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
                   'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
                   'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']

    if uf_upper not in UFS_VALIDAS:
        return {
            'sucesso': False,
            'uf': uf,
            'erro': f"UF '{uf}' inválida",
            'ufs_validas': UFS_VALIDAS
        }

    # Escolher fonte
    if fonte == 'carteira':
        Model = CarteiraPrincipal
        filtro_saldo = CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    elif fonte == 'separacao':
        Model = Separacao
        filtro_saldo = Separacao.sincronizado_nf == False
    else:
        Model = CarteiraPrincipal
        filtro_saldo = CarteiraPrincipal.qtd_saldo_produto_pedido > 0

    # Query
    itens = Model.query.filter(
        Model.cod_uf == uf_upper,
        filtro_saldo
    ).all()

    if not itens:
        return {
            'sucesso': False,
            'uf': uf_upper,
            'erro': f"Nenhum pedido encontrado para UF {uf_upper}"
        }

    # Agrupar por pedido (mesmo código de resolver_grupo)
    pedidos_dict = defaultdict(lambda: {
        'itens': [],
        'valor_total': 0,
        'total_itens': 0
    })

    for item in itens:
        num = item.num_pedido
        pedidos_dict[num]['num_pedido'] = num
        pedidos_dict[num]['cnpj'] = item.cnpj_cpf
        pedidos_dict[num]['cliente'] = item.raz_social_red or item.raz_social
        pedidos_dict[num]['cidade'] = item.nome_cidade or item.municipio
        pedidos_dict[num]['uf'] = item.cod_uf or item.estado
        pedidos_dict[num]['total_itens'] += 1 # type: ignore

        if fonte == 'carteira':
            valor_item = float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)
        else:
            valor_item = float(item.valor_saldo or 0)

        pedidos_dict[num]['valor_total'] += valor_item # type: ignore

    pedidos = []
    for num, dados in pedidos_dict.items():
        pedidos.append({
            'num_pedido': num,
            'cnpj': dados['cnpj'],
            'cliente': dados['cliente'],
            'cidade': dados['cidade'],
            'uf': dados['uf'],
            'total_itens': dados['total_itens'],
            'valor_total': round(dados['valor_total'], 2)
        })

    pedidos.sort(key=lambda p: p['valor_total'], reverse=True)

    total_valor = sum(p['valor_total'] for p in pedidos)
    cidades = sorted(set(p['cidade'] for p in pedidos if p['cidade']))

    return {
        'sucesso': True,
        'uf': uf_upper,
        'fonte': fonte,
        'pedidos': pedidos,
        'resumo': {
            'total_pedidos': len(pedidos),
            'total_valor': round(total_valor, 2),
            'cidades': cidades
        }
    }


# ============================================================
# RESOLVER PEDIDO
# Busca flexivel por termo parcial
# ============================================================
def resolver_pedido(termo: str, fonte: str = 'ambos'):
    """
    Resolve termo de pedido para itens da carteira/separacao.

    Estrategias de busca (em ordem de prioridade):
    1. Numero exato do pedido
    2. Numero parcial do pedido (LIKE)
    3. CNPJ direto (formato XX.XXX.XXX ou XXXXXXXXXX)
    4. Grupo empresarial + termo (ex: "atacadao 183")
    5. Cliente por nome parcial

    IMPORTANTE: Quando multiplos pedidos sao encontrados, SEMPRE retorna
    info['multiplos_encontrados'] = True com lista de todos candidatos.

    Args:
        termo: Termo de busca (numero, CNPJ, grupo+loja, nome cliente)
        fonte: 'carteira', 'separacao' ou 'ambos'

    Returns:
        tuple: (itens, num_pedido, info)
        - itens: Lista de itens encontrados (do primeiro pedido se multiplos)
        - num_pedido: Numero do pedido encontrado (ou None)
        - info: Dict com metadados da busca {estrategia, termo_original, pedidos_candidatos, ...}
    """
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from sqlalchemy import or_
    import re

    termo = termo.strip()
    info = {
        'termo_original': termo,
        'estrategia': None,
        'grupo_identificado': None,
        'multiplos_encontrados': False,
        'pedidos_candidatos': []
    }

    def _extrair_pedidos_unicos(itens, campo_pedido='num_pedido'):
        """Extrai pedidos unicos com info do cliente"""
        pedidos = {}
        for item in itens:
            num = getattr(item, campo_pedido)
            if num not in pedidos:
                cliente = getattr(item, 'raz_social_red', 'N/A')
                pedidos[num] = {'num_pedido': num, 'cliente': cliente}
        return pedidos

    def _retornar_com_multiplos(itens, pedidos_dict, estrategia, fonte_str, info, Model, extra_info=None):
        """Helper para retornar resultados tratando multiplos pedidos"""
        pedidos_lista = list(pedidos_dict.keys())

        if len(pedidos_lista) == 1:
            num_pedido = pedidos_lista[0]
            info['estrategia'] = estrategia
            info['fonte'] = fonte_str
            if extra_info:
                info.update(extra_info)
            return itens, num_pedido, info
        else:
            # Multiplos pedidos - retornar primeiro mas LISTAR TODOS
            num_pedido = pedidos_lista[0]
            if Model == CarteiraPrincipal:
                itens_pedido = Model.query.filter(
                    Model.num_pedido == num_pedido,
                    Model.qtd_saldo_produto_pedido > 0
                ).all()
            else:
                itens_pedido = Model.query.filter(
                    Model.num_pedido == num_pedido,
                    Model.sincronizado_nf == False,
                    Model.qtd_saldo > 0  # CORRECAO: Filtrar itens com saldo zerado
                ).all()

            info['estrategia'] = estrategia
            info['fonte'] = fonte_str
            info['multiplos_encontrados'] = True
            info['pedidos_candidatos'] = [
                pedidos_dict[p] for p in pedidos_lista[:20]
            ]
            info['total_pedidos_encontrados'] = len(pedidos_lista)
            if extra_info:
                info.update(extra_info)
            return itens_pedido, num_pedido, info

    # ========== ESTRATEGIA 1: Numero exato ==========
    if fonte in ('carteira', 'ambos'):
        itens = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.num_pedido == termo,
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).all()

        if itens:
            info['estrategia'] = 'NUMERO_EXATO'
            info['fonte'] = 'carteira'
            return itens, termo, info

    if fonte in ('separacao', 'ambos'):
        itens = Separacao.query.filter(
            Separacao.num_pedido == termo,
            Separacao.sincronizado_nf == False,
            Separacao.qtd_saldo > 0  # CORRECAO: Filtrar itens com saldo zerado
        ).all()

        if itens:
            info['estrategia'] = 'NUMERO_EXATO'
            info['fonte'] = 'separacao'
            return itens, termo, info

    # ========== ESTRATEGIA 2: Numero parcial (LIKE) ==========
    if fonte in ('carteira', 'ambos'):
        itens = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.num_pedido.ilike(f'%{termo}%'),
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).all()

        if itens:
            pedidos = _extrair_pedidos_unicos(itens)
            return _retornar_com_multiplos(itens, pedidos, 'NUMERO_PARCIAL', 'carteira', info, CarteiraPrincipal)

    if fonte in ('separacao', 'ambos'):
        itens = Separacao.query.filter(
            Separacao.num_pedido.ilike(f'%{termo}%'),
            Separacao.sincronizado_nf == False,
            Separacao.qtd_saldo > 0  # CORRECAO: Filtrar itens com saldo zerado
        ).all()

        if itens:
            pedidos = _extrair_pedidos_unicos(itens)
            return _retornar_com_multiplos(itens, pedidos, 'NUMERO_PARCIAL', 'separacao', info, Separacao)

    # ========== ESTRATEGIA 3: CNPJ direto ==========
    # Detectar se termo parece CNPJ (numeros com ou sem formatacao)
    # Formatos aceitos: XX.XXX.XXX, XXXXXXXX, XX.XXX.XXX/XXXX-XX
    termo_limpo = re.sub(r'[^\d]', '', termo)
    parece_cnpj = (
        len(termo_limpo) >= 8 or
        re.match(r'^\d{2}\.\d{3}\.\d{3}', termo) or  # XX.XXX.XXX
        '/' in termo  # Formato completo com barra
    )

    if parece_cnpj and len(termo_limpo) >= 8:
        # Buscar pelo termo original (pode ter pontos) OU pelo termo limpo
        if fonte in ('carteira', 'ambos'):
            itens = CarteiraPrincipal.query.filter(
                or_(
                    CarteiraPrincipal.cnpj_cpf.ilike(f'%{termo}%'),  # Com formatacao original
                    CarteiraPrincipal.cnpj_cpf.ilike(f'%{termo_limpo[:8]}%')  # Sem formatacao
                ),
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            ).all()

            if itens:
                pedidos = _extrair_pedidos_unicos(itens)
                return _retornar_com_multiplos(itens, pedidos, 'CNPJ_DIRETO', 'carteira', info, CarteiraPrincipal)

        if fonte in ('separacao', 'ambos'):
            itens = Separacao.query.filter(
                or_(
                    Separacao.cnpj_cpf.ilike(f'%{termo}%'),
                    Separacao.cnpj_cpf.ilike(f'%{termo_limpo[:8]}%')
                ),
                Separacao.sincronizado_nf == False,
                Separacao.qtd_saldo > 0  # CORRECAO: Filtrar itens com saldo zerado
            ).all()

            if itens:
                pedidos = _extrair_pedidos_unicos(itens)
                return _retornar_com_multiplos(itens, pedidos, 'CNPJ_DIRETO', 'separacao', info, Separacao)

    # ========== ESTRATEGIA 4: Grupo empresarial + termo ==========
    partes = termo.lower().split()
    if len(partes) >= 2:
        possivel_grupo = partes[0]
        prefixos = GRUPOS_EMPRESARIAIS.get(possivel_grupo)

        if prefixos:
            busca_loja = ' '.join(partes[1:])
            info['grupo_identificado'] = possivel_grupo

            if fonte in ('carteira', 'ambos'):
                filtros_cnpj = [CarteiraPrincipal.cnpj_cpf.like(f'{p}%') for p in prefixos]
                itens = CarteiraPrincipal.query.filter(
                    or_(*filtros_cnpj),
                    CarteiraPrincipal.raz_social_red.ilike(f'%{busca_loja}%'),
                    CarteiraPrincipal.qtd_saldo_produto_pedido > 0
                ).all()

                if itens:
                    pedidos = _extrair_pedidos_unicos(itens)
                    return _retornar_com_multiplos(
                        itens, pedidos, 'GRUPO_LOJA', 'carteira', info, CarteiraPrincipal,
                        {'loja_buscada': busca_loja}
                    )

            if fonte in ('separacao', 'ambos'):
                filtros_cnpj = [Separacao.cnpj_cpf.like(f'{p}%') for p in prefixos]
                itens = Separacao.query.filter(
                    or_(*filtros_cnpj),
                    Separacao.raz_social_red.ilike(f'%{busca_loja}%'),
                    Separacao.sincronizado_nf == False,
                    Separacao.qtd_saldo > 0  # CORRECAO: Filtrar itens com saldo zerado
                ).all()

                if itens:
                    pedidos = _extrair_pedidos_unicos(itens)
                    return _retornar_com_multiplos(
                        itens, pedidos, 'GRUPO_LOJA', 'separacao', info, Separacao,
                        {'loja_buscada': busca_loja}
                    )

    # ========== ESTRATEGIA 5: Cliente por nome parcial ==========
    if fonte in ('carteira', 'ambos'):
        itens = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.raz_social_red.ilike(f'%{termo}%'),
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).all()

        if itens:
            pedidos = _extrair_pedidos_unicos(itens)
            return _retornar_com_multiplos(itens, pedidos, 'CLIENTE_PARCIAL', 'carteira', info, CarteiraPrincipal)

    if fonte in ('separacao', 'ambos'):
        itens = Separacao.query.filter(
            Separacao.raz_social_red.ilike(f'%{termo}%'),
            Separacao.sincronizado_nf == False,
            Separacao.qtd_saldo > 0  # CORRECAO: Filtrar itens com saldo zerado
        ).all()

        if itens:
            pedidos = _extrair_pedidos_unicos(itens)
            return _retornar_com_multiplos(itens, pedidos, 'CLIENTE_PARCIAL', 'separacao', info, Separacao)

    # Nenhuma estrategia funcionou
    info['estrategia'] = 'NAO_ENCONTRADO'
    return [], None, info


# ============================================================
# RESOLVER CIDADE
# Busca pedidos por cidade com normalizacao de acentos
# ============================================================
def resolver_cidade(termo: str, fonte: str = 'separacao', apenas_pendentes: bool = True):
    """
    Resolve termo de cidade para pedidos, normalizando acentos e case.

    Resolve problemas como:
    - "itanhaem" encontra "Itanhaém", "ITANHAEM", "itanhaém"
    - "peruibe" encontra "Peruíbe", "PERUIBE"
    - "sao paulo" encontra "São Paulo", "SAO PAULO"

    Estrategia:
    1. Normaliza o termo de busca (remove acentos, lowercase)
    2. Busca todas as cidades unicas no banco
    3. Compara normalizado com normalizado
    4. Retorna pedidos das cidades que casam

    Args:
        termo: Nome da cidade (pode ter ou nao acentos)
        fonte: 'carteira', 'separacao' ou 'ambos'
        apenas_pendentes: Se True, filtra apenas pendentes (qtd_saldo > 0 ou sincronizado_nf=False)

    Returns:
        dict: {
            'sucesso': bool,
            'cidades_encontradas': list,  # Cidades que casaram
            'pedidos': list,              # Pedidos agrupados
            'total_pedidos': int,
            'termo_normalizado': str
        }
    """
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from collections import defaultdict

    termo_normalizado = normalizar_texto(termo)

    resultado = {
        'sucesso': True,
        'termo_original': termo,
        'termo_normalizado': termo_normalizado,
        'cidades_encontradas': [],
        'pedidos': [],
        'total_pedidos': 0
    }

    if not termo_normalizado:
        resultado['sucesso'] = False
        resultado['erro'] = 'Termo de busca vazio'
        return resultado

    cidades_encontradas = set()
    pedidos_dict = defaultdict(lambda: {
        'num_pedido': None,
        'cliente': None,
        'cidade': None,
        'uf': None,
        'valor': 0.0,
        'itens': 0
    })

    # Buscar em Separacao
    if fonte in ('separacao', 'ambos'):
        query = Separacao.query
        if apenas_pendentes:
            query = query.filter(
                Separacao.sincronizado_nf == False,
                Separacao.qtd_saldo > 0  # CORRECAO: Filtrar itens com saldo zerado
            )

        itens = query.all()

        for item in itens:
            cidade_item = item.nome_cidade or ''
            cidade_normalizada = normalizar_texto(cidade_item)

            # Verifica se o termo esta contido na cidade normalizada
            if termo_normalizado in cidade_normalizada:
                cidades_encontradas.add(cidade_item)
                num = item.num_pedido
                if pedidos_dict[num]['num_pedido'] is None:
                    pedidos_dict[num]['num_pedido'] = num
                    pedidos_dict[num]['cliente'] = item.raz_social_red
                    pedidos_dict[num]['cidade'] = cidade_item
                    pedidos_dict[num]['uf'] = item.cod_uf
                    pedidos_dict[num]['fonte'] = 'separacao'

                pedidos_dict[num]['valor'] += float(item.valor_saldo or 0) # type: ignore
                pedidos_dict[num]['itens'] += 1 # type: ignore

    # Buscar em Carteira
    if fonte in ('carteira', 'ambos'):
        query = CarteiraPrincipal.query
        if apenas_pendentes:
            query = query.filter(CarteiraPrincipal.qtd_saldo_produto_pedido > 0)

        itens = query.all()

        for item in itens:
            cidade_item = item.nome_cidade or ''
            cidade_normalizada = normalizar_texto(cidade_item)

            if termo_normalizado in cidade_normalizada:
                cidades_encontradas.add(cidade_item)
                num = item.num_pedido
                # So adiciona se nao veio da separacao
                if pedidos_dict[num]['num_pedido'] is None:
                    pedidos_dict[num]['num_pedido'] = num
                    pedidos_dict[num]['cliente'] = item.raz_social_red
                    pedidos_dict[num]['cidade'] = cidade_item
                    pedidos_dict[num]['uf'] = item.cod_uf
                    pedidos_dict[num]['fonte'] = 'carteira'

                    preco = float(item.preco_produto_pedido or 0)
                    qtd = float(item.qtd_saldo_produto_pedido or 0)
                    pedidos_dict[num]['valor'] += preco * qtd # type: ignore
                    pedidos_dict[num]['itens'] += 1 # type: ignore

    resultado['cidades_encontradas'] = sorted(list(cidades_encontradas))
    resultado['pedidos'] = list(pedidos_dict.values())
    resultado['total_pedidos'] = len(pedidos_dict)

    if not resultado['pedidos']:
        resultado['sucesso'] = False
        resultado['erro'] = f"Nenhum pedido encontrado para cidade '{termo}'"
        resultado['sugestao'] = "Verifique a grafia da cidade ou tente sem acentos"

    return resultado


def resolver_cidades_multiplas(cidades: list, fonte: str = 'separacao', apenas_pendentes: bool = True):
    """
    Resolve multiplas cidades de uma vez.

    Util para buscas como "litoral sul" que pode incluir
    Itanhaem, Peruibe, Mongagua, etc.

    Args:
        cidades: Lista de nomes de cidades
        fonte: 'carteira', 'separacao' ou 'ambos'
        apenas_pendentes: Se True, filtra apenas pendentes

    Returns:
        dict: Resultado agregado de todas as cidades
    """
    from collections import defaultdict

    resultado_final = {
        'sucesso': True,
        'cidades_buscadas': cidades,
        'cidades_encontradas': [],
        'pedidos': [],
        'total_pedidos': 0,
        'por_cidade': {}
    }

    pedidos_unicos = {}

    for cidade in cidades:
        resultado = resolver_cidade(cidade, fonte=fonte, apenas_pendentes=apenas_pendentes)

        if resultado['sucesso']:
            resultado_final['cidades_encontradas'].extend(resultado['cidades_encontradas'])
            resultado_final['por_cidade'][cidade] = {
                'encontradas': resultado['cidades_encontradas'],
                'total': resultado['total_pedidos']
            }

            # Merge pedidos evitando duplicatas
            for pedido in resultado['pedidos']:
                num = pedido['num_pedido']
                if num not in pedidos_unicos:
                    pedidos_unicos[num] = pedido

    resultado_final['pedidos'] = list(pedidos_unicos.values())
    resultado_final['total_pedidos'] = len(pedidos_unicos)
    resultado_final['cidades_encontradas'] = list(set(resultado_final['cidades_encontradas']))

    if not resultado_final['pedidos']:
        resultado_final['sucesso'] = False
        resultado_final['erro'] = f"Nenhum pedido encontrado para as cidades: {', '.join(cidades)}"

    return resultado_final


# ============================================================
# RESOLVER PRODUTO
# Busca por tokenizacao em CadastroPalletizacao
# ============================================================
def resolver_produto(termo: str, limit: int = 10):
    """
    Resolve termo de produto usando tokenizacao e busca em CadastroPalletizacao.

    Busca em: nome_produto, categoria_produto, subcategoria,
              tipo_embalagem, tipo_materia_prima

    Estrategia:
    1. Tokeniza o termo (ex: "pf mezzani" -> ["pf", "mezzani"])
    2. Para cada token, busca match em qualquer campo
    3. Combina resultados com AND (todos tokens devem dar match)
    4. Ordena por relevancia (mais matches = maior score)

    Args:
        termo: Termo de busca (pode ser abreviacao, nome parcial, combinacao)
        limit: Maximo de resultados

    Returns:
        list: Lista de dicts com produtos encontrados, ordenados por relevancia
              [{'cod_produto': '...', 'nome_produto': '...', 'score': N, ...}]
    """
    from app.producao.models import CadastroPalletizacao
    from sqlalchemy import or_, and_, func

    termo = termo.strip().lower()
    if not termo:
        return []

    # Tokenizar
    tokens = termo.split()

    # Campos para busca (ordem de prioridade para score)
    campos_busca = [
        ('cod_produto', CadastroPalletizacao.cod_produto, 5),       # Match exato no codigo = alto score
        ('nome_produto', CadastroPalletizacao.nome_produto, 3),
        ('tipo_materia_prima', CadastroPalletizacao.tipo_materia_prima, 2),
        ('tipo_embalagem', CadastroPalletizacao.tipo_embalagem, 2),
        ('categoria_produto', CadastroPalletizacao.categoria_produto, 2),
        ('subcategoria', CadastroPalletizacao.subcategoria, 1),
    ]

    # Construir filtros: cada token deve dar match em ALGUM campo
    filtros_por_token = []
    for token in tokens:
        filtros_token = []
        for nome_campo, coluna, peso in campos_busca:
            # ILIKE para match parcial, tratando NULL
            filtros_token.append(
                and_(coluna.isnot(None), coluna.ilike(f'%{token}%'))
            )
        filtros_por_token.append(or_(*filtros_token))

    # Todos os tokens devem dar match (AND entre tokens)
    if filtros_por_token:
        filtro_final = and_(*filtros_por_token)
    else:
        return []

    # Buscar produtos ativos
    produtos = CadastroPalletizacao.query.filter(
        filtro_final,
        CadastroPalletizacao.ativo == True
    ).limit(limit * 3).all()  # Buscar mais para depois ordenar

    if not produtos:
        return []

    # Calcular score de relevancia
    resultados = []
    for prod in produtos:
        score = 0
        matches = []

        for token in tokens:
            token_lower = token.lower()

            # Verificar match em cada campo
            if prod.cod_produto and token_lower in prod.cod_produto.lower():
                score += 5
                matches.append(f"cod_produto:{token}")

            if prod.nome_produto and token_lower in prod.nome_produto.lower():
                score += 3
                matches.append(f"nome_produto:{token}")

            if prod.tipo_materia_prima and token_lower in prod.tipo_materia_prima.lower():
                score += 2
                matches.append(f"tipo_materia_prima:{token}")

            if prod.tipo_embalagem and token_lower in prod.tipo_embalagem.lower():
                score += 2
                matches.append(f"tipo_embalagem:{token}")

            if prod.categoria_produto and token_lower in prod.categoria_produto.lower():
                score += 2
                matches.append(f"categoria_produto:{token}")

            if prod.subcategoria and token_lower in prod.subcategoria.lower():
                score += 1
                matches.append(f"subcategoria:{token}")

        resultados.append({
            'cod_produto': prod.cod_produto,
            'nome_produto': prod.nome_produto,
            'tipo_embalagem': prod.tipo_embalagem,
            'tipo_materia_prima': prod.tipo_materia_prima,
            'categoria_produto': prod.categoria_produto,
            'subcategoria': prod.subcategoria,
            'palletizacao': float(prod.palletizacao) if prod.palletizacao else 0,
            'peso_bruto': float(prod.peso_bruto) if prod.peso_bruto else 0,
            'score': score,
            'matches': matches
        })

    # Ordenar por score (maior primeiro) e limitar
    resultados.sort(key=lambda x: -x['score'])
    return resultados[:limit]


def resolver_produto_unico(termo: str):
    """
    Resolve termo de produto esperando resultado unico.

    Args:
        termo: Termo de busca

    Returns:
        tuple: (produto_dict, info)
        - produto_dict: Dict com dados do produto ou None
        - info: Dict com metadados {encontrado, multiplos, candidatos}
    """
    resultados = resolver_produto(termo, limit=5)

    info = {
        'termo_original': termo,
        'encontrado': False,
        'multiplos': False,
        'candidatos': []
    }

    if not resultados:
        return None, info

    if len(resultados) == 1:
        info['encontrado'] = True
        return resultados[0], info

    # Multiplos resultados - verificar se o primeiro tem score muito maior
    if resultados[0]['score'] > resultados[1]['score'] * 1.5:
        info['encontrado'] = True
        info['multiplos'] = True
        info['candidatos'] = [r['cod_produto'] for r in resultados[1:]]
        return resultados[0], info

    # Ambiguidade real
    info['multiplos'] = True
    info['candidatos'] = [
        {'cod_produto': r['cod_produto'], 'nome_produto': r['nome_produto'], 'score': r['score']}
        for r in resultados
    ]
    return None, info


# ============================================================
# FUNCOES AUXILIARES
# ============================================================
def formatar_sugestao_pedido(info: dict) -> str:
    """
    Formata mensagem de sugestao baseada no resultado da busca.

    Args:
        info: Dict retornado por resolver_pedido

    Returns:
        str: Mensagem formatada para o usuario
    """
    if info['estrategia'] == 'NAO_ENCONTRADO':
        grupos = ', '.join(listar_grupos_disponiveis())
        return (
            f"Pedido '{info['termo_original']}' nao encontrado. "
            f"Tente:\n"
            f"- Numero do pedido (ex: VCD123)\n"
            f"- Parte do numero (ex: 123)\n"
            f"- Grupo + loja (ex: {grupos.split(',')[0]} 183)\n"
            f"- Nome do cliente (ex: Barueri)\n"
            f"Grupos disponiveis: {grupos}"
        )

    if info.get('multiplos_encontrados'):
        candidatos = info.get('pedidos_candidatos', [])
        return (
            f"Multiplos pedidos encontrados para '{info['termo_original']}'. "
            f"Usando o primeiro: {candidatos[0] if candidatos else 'N/A'}. "
            f"Outros candidatos: {', '.join(candidatos[1:5])}"
        )

    return None # type: ignore


def formatar_sugestao_produto(info: dict) -> str:
    """
    Formata mensagem de sugestao baseada no resultado da busca de produto.

    Args:
        info: Dict retornado por resolver_produto_unico

    Returns:
        str: Mensagem formatada para o usuario
    """
    if not info['encontrado'] and not info['multiplos']:
        return (
            f"Produto '{info['termo_original']}' nao encontrado. "
            f"Tente usar:\n"
            f"- Codigo do produto (ex: AZ001)\n"
            f"- Nome parcial (ex: azeitona preta)\n"
            f"- Tipo + embalagem (ex: balde industrial)\n"
            f"- Combinacao (ex: mezzani fatiada)"
        )

    if info['multiplos'] and not info['encontrado']:
        candidatos = info.get('candidatos', [])
        lista = '\n'.join([
            f"  - {c['cod_produto']}: {c['nome_produto']}"
            for c in candidatos[:5]
        ])
        return (
            f"Multiplos produtos encontrados para '{info['termo_original']}':\n{lista}\n"
            f"Especifique melhor o termo."
        )

    return None # type: ignore


# ============================================================
# TESTE DO MODULO
# ============================================================
if __name__ == '__main__':
    import json
    from app import create_app

    app = create_app()
    with app.app_context():
        print("=== TESTE: resolver_pedido ===")

        # Teste 1: Numero exato (se existir)
        itens, num, info = resolver_pedido("VCD123")
        print(f"\nBusca 'VCD123': {info['estrategia']}, encontrou {len(itens)} itens")

        # Teste 2: Numero parcial
        itens, num, info = resolver_pedido("123")
        print(f"Busca '123': {info['estrategia']}, pedido={num}, itens={len(itens)}")
        if info.get('multiplos_encontrados'):
            print(f"  Candidatos: {info.get('pedidos_candidatos', [])[:5]}")

        # Teste 3: Grupo + loja
        itens, num, info = resolver_pedido("atacadao 183")
        print(f"Busca 'atacadao 183': {info['estrategia']}, pedido={num}")

        # Teste 4: Cliente parcial
        itens, num, info = resolver_pedido("barueri")
        print(f"Busca 'barueri': {info['estrategia']}, pedido={num}")

        print("\n=== TESTE: resolver_produto ===")

        # Teste produtos
        for termo in ["azeitona", "balde", "mezzani", "preta fatiada"]:
            prods = resolver_produto(termo, limit=3)
            print(f"\nBusca '{termo}': {len(prods)} resultados")
            for p in prods:
                print(f"  - {p['cod_produto']}: {p['nome_produto']} (score={p['score']})")

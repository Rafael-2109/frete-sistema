"""Resolucao de produto.

Funcoes "ricas" (port fiel de resolver_entidades.py) servem os importadores Python:
- resolver_produto (:1129) — BLOB+AND deterministico + fallback semantico via product_search
- resolver_produto_unico (:1222) — tupla (produto|None, info)
- resolver_produtos_na_carteira_cliente (:1269)

Funcao "achatada" serve o CLI/8 subagentes:
- resolver_produto_cli — JSON {sucesso, termo_original, modo, abreviacoes_detectadas, produtos, total}
  delegando a app.embeddings.product_search.buscar_produtos_hibrido (SoT de runtime; sem logica duplicada).
"""
from app.resolvedores.normalizacao import _normalizar_token


def resolver_produto(termo: str, limit: int = 50, modo: str = 'hibrida'):
    """Resolve termo de produto via AND de substrings num campo blob concatenado.

    Estrategia (refator 2026-05-26): tokeniza + stemming-s; AND de TODOS os tokens num blob
    (nome+categoria+materia+embalagem+cod, lowercase); ordena por cod_produto (deterministico);
    fallback semantico via embeddings APENAS se AND retornar 0 (modo 'hibrida').

    Returns:
        list[dict]: {cod_produto, nome_produto, tipo_embalagem, tipo_materia_prima,
                     categoria_produto, subcategoria, palletizacao, peso_bruto, score, matches}
    """
    from app.producao.models import CadastroPalletizacao
    from sqlalchemy import and_, func

    raw_tokens = [t.strip().lower() for t in (termo or '').split() if t.strip()]
    if not raw_tokens:
        return []
    tokens = [_normalizar_token(t) for t in raw_tokens]

    # Modo 'semantica' explicito: bypass AND, ir direto pros embeddings
    if modo == 'semantica':
        try:
            from app.embeddings.product_search import buscar_produtos_hibrido
            return buscar_produtos_hibrido(termo=termo, modo='semantica', limite=limit) or []
        except Exception:
            return []

    # Campo blob: tudo concatenado e lowercase para busca uniforme
    blob = func.lower(func.concat_ws(
        ' ',
        CadastroPalletizacao.nome_produto,
        CadastroPalletizacao.categoria_produto,
        CadastroPalletizacao.tipo_materia_prima,
        CadastroPalletizacao.tipo_embalagem,
        CadastroPalletizacao.cod_produto,
    ))

    filtros = [blob.like(f'%{t}%') for t in tokens]

    produtos = CadastroPalletizacao.query.filter(
        CadastroPalletizacao.produto_vendido == True,
        CadastroPalletizacao.ativo == True,
        and_(*filtros),
    ).order_by(CadastroPalletizacao.cod_produto).limit(limit).all()

    # Fallback semantico: so se AND zerar E modo permitir
    if not produtos and modo == 'hibrida':
        try:
            from app.embeddings.product_search import buscar_produtos_hibrido
            sem = buscar_produtos_hibrido(termo=termo, modo='hibrida', limite=limit)
            if sem:
                return sem
        except Exception:
            pass

    return [
        {
            'cod_produto': p.cod_produto,
            'nome_produto': p.nome_produto,
            'tipo_embalagem': p.tipo_embalagem,
            'tipo_materia_prima': p.tipo_materia_prima,
            'categoria_produto': p.categoria_produto,
            'subcategoria': p.subcategoria,
            'palletizacao': float(p.palletizacao) if p.palletizacao else 0,
            'peso_bruto': float(p.peso_bruto) if p.peso_bruto else 0,
            'score': 1,  # legacy: AND ja garante relevancia
            'matches': [],
        }
        for p in produtos
    ]


def resolver_produto_unico(termo: str, modo: str = 'hibrida'):
    """Resolve termo de produto esperando resultado unico.

    Returns:
        tuple: (produto_dict|None, info) — info={termo_original, encontrado, multiplos, candidatos}
    """
    resultados = resolver_produto(termo, limit=50, modo=modo)

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


def resolver_produtos_na_carteira_cliente(termo: str, cnpjs: list) -> dict:
    """Busca todos os candidatos de produto na carteira do cliente (50% regra / 50% IA).

    Returns dict: {sucesso, candidatos_cadastro, itens_carteira, total_skus,
                   total_quantidade, total_valor, ia_decide}.
    """
    from app.carteira.models import CarteiraPrincipal

    candidatos = resolver_produto(termo, limit=50)
    cod_produtos = [c['cod_produto'] for c in candidatos]

    if not cod_produtos:
        return {
            'sucesso': False,
            'erro': f'Nenhum produto encontrado para "{termo}"',
            'candidatos_cadastro': [],
            'itens_carteira': [],
            'total_skus': 0,
            'ia_decide': True
        }

    itens = CarteiraPrincipal.query.filter(
        CarteiraPrincipal.cnpj_cpf.in_(cnpjs),
        CarteiraPrincipal.cod_produto.in_(cod_produtos),
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    ).all()

    por_produto = {}
    for item in itens:
        cod = item.cod_produto
        if cod not in por_produto:
            por_produto[cod] = {
                'cod_produto': cod,
                'nome_produto': item.nome_produto,
                'qtd_total': 0,
                'valor_total': 0,
                'pedidos': [],
                'clientes': set()
            }
        por_produto[cod]['qtd_total'] += float(item.qtd_saldo_produto_pedido or 0)
        por_produto[cod]['valor_total'] += float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0)
        if item.num_pedido not in por_produto[cod]['pedidos']:
            por_produto[cod]['pedidos'].append(item.num_pedido)
        por_produto[cod]['clientes'].add(item.raz_social_red or item.cnpj_cpf)

    itens_carteira = []
    for cod, dados in por_produto.items():
        dados['clientes'] = list(dados['clientes'])
        dados['num_pedidos'] = len(dados['pedidos'])
        itens_carteira.append(dados)

    itens_carteira.sort(key=lambda x: -x['qtd_total'])

    return {
        'sucesso': True,
        'candidatos_cadastro': candidatos,
        'itens_carteira': itens_carteira,
        'total_skus': len(por_produto),
        'total_quantidade': sum(p['qtd_total'] for p in itens_carteira),
        'total_valor': sum(p['valor_total'] for p in itens_carteira),
        'ia_decide': True
    }


def resolver_produto_cli(termo: str, limite: int = 50, modo: str = 'hibrida') -> dict:
    """Fachada CLI (JSON achatado) — usada pelos 8 subagentes via resolver_produto.py.

    Delega a busca a app.embeddings.product_search.buscar_produtos_hibrido (SoT de runtime),
    preenchendo abreviacoes_detectadas via detectar_abreviacoes (sem replicar logica de texto).
    Shape: {sucesso, termo_original, modo, abreviacoes_detectadas, produtos, total, erro?, sugestao?}.
    """
    termo_l = (termo or '').strip().lower()

    resultado = {
        'sucesso': False,
        'termo_original': termo_l,
        'modo': modo,
        'abreviacoes_detectadas': [],
        'produtos': [],
        'total': 0,
    }

    if not termo_l:
        resultado['erro'] = 'Termo de busca vazio'
        return resultado

    try:
        from app.embeddings.product_search import buscar_produtos_hibrido, detectar_abreviacoes
        tokens = termo_l.split()
        abreviacoes, _ = detectar_abreviacoes(tokens)
        resultado['abreviacoes_detectadas'] = [a['descricao'] for a in abreviacoes]
        produtos = buscar_produtos_hibrido(termo=termo_l, modo=modo, limite=limite)
    except Exception as e:
        # Rede de seguranca (como a split fazia): cai no BLOB+AND, que nao depende de embeddings.
        try:
            produtos = resolver_produto(termo_l, limit=limite, modo='texto')
        except Exception:
            resultado['erro'] = str(e)
            return resultado
        if produtos:
            resultado['sucesso'] = True
            resultado['produtos'] = produtos
            resultado['total'] = len(produtos)
            resultado['modo'] = f'texto (fallback: {e})'
            return resultado
        resultado['erro'] = str(e)
        return resultado

    if not produtos:
        resultado['erro'] = f"Produto '{termo_l}' nao encontrado"
        resultado['sugestao'] = "Tente usar nome parcial (ex: palmito) ou abreviacao (ex: AZ VF)"
        return resultado

    resultado['sucesso'] = True
    resultado['produtos'] = produtos
    resultado['total'] = len(produtos)
    return resultado

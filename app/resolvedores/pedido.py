"""Resolucao de pedido.

resolver_pedido (tupla rica) = port fiel de resolver_entidades.py:688 — serve os 4 importadores Python.
resolver_pedido_cli (JSON achatado) = port de resolvendo-entidades/scripts/resolver_pedido.py — serve
  o CLI/8 subagentes. Mesma logica/estrategias, em ORM (elimina a interpolacao SQL da estrategia 4).
"""
import re

from app.resolvedores.constantes import GRUPOS_EMPRESARIAIS


def resolver_pedido(termo: str, fonte: str = 'ambos'):
    """Resolve termo de pedido para itens da carteira/separacao (5 estrategias).

    Returns:
        tuple: (itens_ORM, num_pedido|None, info)
        info = {termo_original, estrategia, grupo_identificado, multiplos_encontrados,
                pedidos_candidatos, fonte?, total_pedidos_encontrados?, loja_buscada?}
    """
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from sqlalchemy import or_

    termo = (termo or '').strip()
    info = {
        'termo_original': termo,
        'estrategia': None,
        'grupo_identificado': None,
        'multiplos_encontrados': False,
        'pedidos_candidatos': []
    }

    def _extrair_pedidos_unicos(itens, campo_pedido='num_pedido'):
        pedidos = {}
        for item in itens:
            num = getattr(item, campo_pedido)
            if num not in pedidos:
                cliente = getattr(item, 'raz_social_red', 'N/A')
                pedidos[num] = {'num_pedido': num, 'cliente': cliente}
        return pedidos

    def _retornar_com_multiplos(itens, pedidos_dict, estrategia, fonte_str, info, Model, extra_info=None):
        pedidos_lista = list(pedidos_dict.keys())

        if len(pedidos_lista) == 1:
            num_pedido = pedidos_lista[0]
            info['estrategia'] = estrategia
            info['fonte'] = fonte_str
            if extra_info:
                info.update(extra_info)
            return itens, num_pedido, info
        else:
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
                    Model.qtd_saldo > 0
                ).all()

            info['estrategia'] = estrategia
            info['fonte'] = fonte_str
            info['multiplos_encontrados'] = True
            info['pedidos_candidatos'] = [
                pedidos_dict[p] for p in pedidos_lista[:50]
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
            Separacao.qtd_saldo > 0
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
            Separacao.qtd_saldo > 0
        ).all()
        if itens:
            pedidos = _extrair_pedidos_unicos(itens)
            return _retornar_com_multiplos(itens, pedidos, 'NUMERO_PARCIAL', 'separacao', info, Separacao)

    # ========== ESTRATEGIA 3: CNPJ direto ==========
    termo_limpo = re.sub(r'[^\d]', '', termo)
    parece_cnpj = (
        len(termo_limpo) >= 8 or
        re.match(r'^\d{2}\.\d{3}\.\d{3}', termo) or
        '/' in termo
    )

    if parece_cnpj and len(termo_limpo) >= 8:
        if fonte in ('carteira', 'ambos'):
            itens = CarteiraPrincipal.query.filter(
                or_(
                    CarteiraPrincipal.cnpj_cpf.ilike(f'%{termo}%'),
                    CarteiraPrincipal.cnpj_cpf.ilike(f'%{termo_limpo[:8]}%')
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
                Separacao.qtd_saldo > 0
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
                    Separacao.qtd_saldo > 0
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
            Separacao.qtd_saldo > 0
        ).all()
        if itens:
            pedidos = _extrair_pedidos_unicos(itens)
            return _retornar_com_multiplos(itens, pedidos, 'CLIENTE_PARCIAL', 'separacao', info, Separacao)

    # Nenhuma estrategia funcionou
    info['estrategia'] = 'NAO_ENCONTRADO'
    return [], None, info


def resolver_pedido_cli(termo: str, fonte: str = 'ambos', limite: int = 50) -> dict:
    """Fachada CLI (JSON achatado) — usada pelos 8 subagentes via resolver_pedido.py.

    Mesmas 5 estrategias do monolito/split, mas retorna lista achatada de pedidos
    {num_pedido,cnpj,cliente,cidade,uf,fonte}. ORM bind-safe (sem SQL-injection na estrategia 4).
    """
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from sqlalchemy import or_

    termo = (termo or '').strip()
    resultado = {
        'sucesso': False,
        'termo_original': termo,
        'estrategia': None,
        'pedidos': [],
        'multiplos': False,
        'total': 0,
    }
    if not termo:
        resultado['erro'] = 'Termo de busca vazio'
        return resultado

    fontes = []
    if fonte in ('carteira', 'ambos'):
        fontes.append(('carteira', CarteiraPrincipal, CarteiraPrincipal.qtd_saldo_produto_pedido > 0))
    if fonte in ('separacao', 'ambos'):
        fontes.append((
            'separacao', Separacao,
            (Separacao.sincronizado_nf == False) & (Separacao.qtd_saldo > 0),
        ))

    def _cols(Model):
        return Model.query.with_entities(
            Model.num_pedido, Model.cnpj_cpf, Model.raz_social_red, Model.nome_cidade, Model.cod_uf
        )

    def _to_pedidos(rows, fnome):
        return [
            {'num_pedido': r[0], 'cnpj': r[1], 'cliente': r[2], 'cidade': r[3], 'uf': r[4], 'fonte': fnome}
            for r in rows
        ]

    pedidos_encontrados = []

    # ESTRATEGIA 1: Numero exato
    for fnome, Model, saldo in fontes:
        rows = _cols(Model).filter(Model.num_pedido == termo, saldo).distinct().limit(limite).all()
        if rows:
            resultado['estrategia'] = 'NUMERO_EXATO'
            resultado['fonte'] = fnome
            pedidos_encontrados.extend(_to_pedidos(rows, fnome))
            break

    # ESTRATEGIA 2: Numero parcial (LIKE)
    if not pedidos_encontrados:
        for fnome, Model, saldo in fontes:
            rows = _cols(Model).filter(
                Model.num_pedido.ilike(f'%{termo}%'), saldo
            ).distinct().order_by(Model.num_pedido).limit(limite).all()
            if rows:
                resultado['estrategia'] = 'NUMERO_PARCIAL'
                pedidos_encontrados.extend(_to_pedidos(rows, fnome))
                break

    # ESTRATEGIA 3: CNPJ direto
    if not pedidos_encontrados:
        termo_limpo = re.sub(r'[^\d]', '', termo)
        parece_cnpj = len(termo_limpo) >= 8 or '/' in termo
        if parece_cnpj:
            for fnome, Model, saldo in fontes:
                rows = _cols(Model).filter(
                    or_(Model.cnpj_cpf.ilike(f'%{termo}%'), Model.cnpj_cpf.ilike(f'%{termo_limpo[:8]}%')),
                    saldo
                ).distinct().order_by(Model.num_pedido).limit(limite).all()
                if rows:
                    resultado['estrategia'] = 'CNPJ_DIRETO'
                    pedidos_encontrados.extend(_to_pedidos(rows, fnome))
                    break

    # ESTRATEGIA 4: Grupo empresarial + termo
    if not pedidos_encontrados:
        partes = termo.lower().split()
        if len(partes) >= 2:
            possivel_grupo = partes[0]
            prefixos = GRUPOS_EMPRESARIAIS.get(possivel_grupo)
            if prefixos:
                busca_loja = ' '.join(partes[1:])
                resultado['grupo_identificado'] = possivel_grupo
                for fnome, Model, saldo in fontes:
                    filtros_cnpj = or_(*[Model.cnpj_cpf.like(f'{p}%') for p in prefixos])
                    rows = _cols(Model).filter(
                        filtros_cnpj, Model.raz_social_red.ilike(f'%{busca_loja}%'), saldo
                    ).distinct().order_by(Model.num_pedido).limit(limite).all()
                    if rows:
                        resultado['estrategia'] = 'GRUPO_LOJA'
                        resultado['loja_buscada'] = busca_loja
                        pedidos_encontrados.extend(_to_pedidos(rows, fnome))
                        break

    # ESTRATEGIA 5: Cliente por nome parcial
    if not pedidos_encontrados:
        for fnome, Model, saldo in fontes:
            rows = _cols(Model).filter(
                Model.raz_social_red.ilike(f'%{termo}%'), saldo
            ).distinct().order_by(Model.num_pedido).limit(limite).all()
            if rows:
                resultado['estrategia'] = 'CLIENTE_PARCIAL'
                pedidos_encontrados.extend(_to_pedidos(rows, fnome))
                break

    if not pedidos_encontrados:
        resultado['estrategia'] = 'NAO_ENCONTRADO'
        resultado['erro'] = f"Pedido '{termo}' nao encontrado"
        resultado['sugestao'] = "Tente numero parcial (ex: VCD123), grupo+loja (ex: atacadao 183), ou nome do cliente"
        return resultado

    # Remover duplicatas mantendo ordem
    pedidos_unicos = []
    nums_vistos = set()
    for p in pedidos_encontrados:
        if p['num_pedido'] not in nums_vistos:
            nums_vistos.add(p['num_pedido'])
            pedidos_unicos.append(p)

    resultado['sucesso'] = True
    resultado['pedidos'] = pedidos_unicos[:limite]
    resultado['multiplos'] = len(pedidos_unicos) > 1
    resultado['total'] = len(pedidos_unicos)
    return resultado

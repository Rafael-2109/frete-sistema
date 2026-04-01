"""
Utilidades de filtro para transportadoras com expansao de grupo.

Ao selecionar uma transportadora em qualquer filtro do sistema,
expande automaticamente para todas do mesmo grupo empresarial
(via grupo_transportadora) com fallback por prefixo CNPJ (8 digitos).

Delega para GrupoEmpresarialService.obter_transportadoras_grupo()
que ja implementa a logica de 3 niveis:
1. grupo_transportadora_id (grupo formal)
2. Prefixo CNPJ (8 digitos — mesma matriz)
3. Detector de grupos manuais

Uso tipico em rotas Flask:

    from app.transportadoras.filter_utils import expandir_filtro_fk, expandir_filtro_texto

    # Para FK (Model.transportadora_id)
    transportadora_id = request.args.get('transportadora_id', type=int)
    if transportadora_id:
        query = query.filter(expandir_filtro_fk(Frete.transportadora_id, transportadora_id))

    # Para colunas texto (EntregaMonitorada.transportadora)
    transportadora_id = request.args.get('transportadora_id', type=int)
    texto = request.args.get('transportadora', '')
    filtro = expandir_filtro_texto(
        [EntregaMonitorada.transportadora],
        transportadora_id=transportadora_id,
        texto_busca=texto
    )
    if filtro is not None:
        query = query.filter(filtro)
"""

import logging

from flask import g, has_request_context
from sqlalchemy import or_

logger = logging.getLogger(__name__)


def expandir_ids_grupo(transportadora_id: int) -> list:
    """Retorna lista de IDs de todas transportadoras do mesmo grupo.

    Usa cache per-request via flask.g para evitar consultas repetidas
    na mesma requisicao (ex: rota filtra por FK e por texto).

    Args:
        transportadora_id: ID da transportadora selecionada

    Returns:
        Lista de IDs (sempre inclui a propria transportadora)
    """
    if not transportadora_id:
        return []

    # Cache per-request
    cache_key = f'_grupo_transp_{transportadora_id}'
    if has_request_context():
        cached = getattr(g, cache_key, None)
        if cached is not None:
            return cached

    try:
        from app.utils.grupo_empresarial import GrupoEmpresarialService
        service = GrupoEmpresarialService()
        ids = service.obter_transportadoras_grupo(transportadora_id)
    except Exception as e:
        logger.error(f"Erro ao expandir grupo para transportadora {transportadora_id}: {e}")
        ids = [transportadora_id]

    if has_request_context():
        setattr(g, cache_key, ids)

    return ids


def expandir_grupo_autocomplete(transportadoras):
    """Expande resultados de autocomplete com membros do mesmo grupo.

    Dado um conjunto de transportadoras (resultado primario da busca),
    retorna transportadoras adicionais que pertencem ao mesmo grupo —
    via grupo_transportadora_id OU prefixo CNPJ (primeiros 8 digitos = filiais).

    Args:
        transportadoras: lista de objetos Transportadora (resultado primario)

    Returns:
        Lista de objetos Transportadora que sao membros expandidos
        (NAO inclui as que ja estao no input)
    """
    if not transportadoras:
        return []

    from app.transportadoras.models import Transportadora

    ids_resultado = {t.id for t in transportadoras}

    # 1) grupo_transportadora_id
    grupo_ids = {t.grupo_transportadora_id for t in transportadoras
                 if t.grupo_transportadora_id}

    # 2) Prefixo CNPJ: mesma raiz = mesma empresa (filiais)
    cnpj_prefixos = set()
    for t in transportadoras:
        if t.cnpj:
            cnpj = t.cnpj.strip()
            barra_pos = cnpj.find('/')
            if barra_pos >= 0:
                cnpj_prefixos.add(cnpj[:barra_pos + 1])
            else:
                digits = ''.join(c for c in cnpj if c.isdigit())
                if len(digits) >= 8:
                    cnpj_prefixos.add(digits[:8])

    # Montar OR de condicoes
    conditions = []
    if grupo_ids:
        conditions.append(Transportadora.grupo_transportadora_id.in_(grupo_ids))
    for prefixo in cnpj_prefixos:
        conditions.append(Transportadora.cnpj.ilike(f'{prefixo}%'))

    if not conditions:
        return []

    try:
        return Transportadora.query.filter(
            or_(*conditions),
            Transportadora.ativo == True,  # noqa: E712
            ~Transportadora.id.in_(ids_resultado),
        ).order_by(Transportadora.razao_social).all()
    except Exception as e:
        logger.error(f"Erro ao expandir grupo autocomplete: {e}")
        return []


def expandir_filtro_fk(coluna, transportadora_id: int):
    """Retorna filtro SQLAlchemy para FK de transportadora com expansao de grupo.

    Se o grupo tem 1 membro, usa == (mais eficiente).
    Se tem N membros, usa IN.

    Args:
        coluna: coluna SQLAlchemy (ex: Frete.transportadora_id)
        transportadora_id: ID selecionado pelo usuario

    Returns:
        Clausula SQLAlchemy para usar em query.filter()
    """
    ids = expandir_ids_grupo(transportadora_id)

    if len(ids) <= 1:
        return coluna == transportadora_id

    return coluna.in_(ids)


def expandir_filtro_texto(colunas_texto, transportadora_id=None, texto_busca=None):
    """Retorna filtro SQLAlchemy para colunas texto de transportadora.

    Prioridades:
    1. Se transportadora_id fornecido: expande para grupo e gera OR de
       ilike por razao_social e CNPJ de todos os membros
    2. Se apenas texto_busca: fallback para ilike simples (backward compat)
    3. Se nenhum: retorna None (sem filtro)

    Args:
        colunas_texto: lista de colunas SQLAlchemy (ex: [EntregaMonitorada.transportadora])
        transportadora_id: ID da transportadora selecionada (do hidden field)
        texto_busca: texto digitado pelo usuario (do input visivel)

    Returns:
        Clausula SQLAlchemy ou None se nenhum filtro aplicavel
    """
    if not isinstance(colunas_texto, (list, tuple)):
        colunas_texto = [colunas_texto]

    # Prioridade 1: expansao por grupo (ID selecionado)
    if transportadora_id:
        ids = expandir_ids_grupo(transportadora_id)
        if ids:
            return _filtro_texto_por_ids(colunas_texto, ids)

    # Prioridade 2: fallback ilike simples (texto digitado, sem selecao)
    if texto_busca and texto_busca.strip():
        busca = f'%{texto_busca.strip()}%'
        condicoes = [col.ilike(busca) for col in colunas_texto]
        return or_(*condicoes) if len(condicoes) > 1 else condicoes[0]

    # Nenhum filtro
    return None


def _filtro_texto_por_ids(colunas_texto, ids):
    """Gera OR de ilike para nome/CNPJ de todos membros do grupo.

    Para cada transportadora no grupo, gera condicoes ilike
    em todas as colunas texto usando razao_social e prefixo CNPJ.
    """
    try:
        from app.transportadoras.models import Transportadora

        membros = Transportadora.query.filter(
            Transportadora.id.in_(ids)
        ).all()

        if not membros:
            return None

        condicoes = []
        for membro in membros:
            for col in colunas_texto:
                # Match por razao_social
                if membro.razao_social:
                    condicoes.append(col.ilike(f'%{membro.razao_social}%'))
                # Match por CNPJ (limpo, sem pontuacao)
                if membro.cnpj:
                    cnpj_limpo = ''.join(c for c in membro.cnpj if c.isdigit())
                    if cnpj_limpo:
                        # Busca tanto CNPJ formatado quanto limpo
                        condicoes.append(col.ilike(f'%{membro.cnpj}%'))
                        condicoes.append(col.ilike(f'%{cnpj_limpo}%'))

        return or_(*condicoes) if condicoes else None

    except Exception as e:
        logger.error(f"Erro ao gerar filtro texto para IDs {ids}: {e}")
        return None

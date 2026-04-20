"""Service de Analise de Categorias — busca fuzzy, series mensais, extrato e CRUD de grupos.

Complementa o dashboard: permite ao usuario selecionar categorias arbitrarias
(cumulativas), visualizar valores/grafico dos ultimos N meses e salvar a
selecao como "Grupo de Analise" reutilizavel. Expande o extrato das
transacoes pertencentes as categorias selecionadas.
"""
from sqlalchemy import func, or_
from rapidfuzz import fuzz
from unidecode import unidecode

from app import db
from app.pessoal.models import (
    PessoalTransacao, PessoalCategoria, PessoalGrupoAnalise,
)
from app.pessoal.services.dashboard_service import _janela_meses


def _norm(texto: str) -> str:
    if not texto:
        return ''
    return unidecode(texto).upper().strip()


# =============================================================================
# BUSCA FUZZY DE CATEGORIAS
# =============================================================================
def buscar_categorias_fuzzy(q: str, limit: int = 50):
    """Busca categorias ativas por ILIKE em grupo/nome + re-ranking fuzzy.

    Estrategia:
    1. ILIKE em grupo OR nome OR (grupo || ' ' || nome) — rapido via SQL
    2. Se q tem >= 3 chars, re-ranqueia por rapidfuzz.token_set_ratio contra
       "grupo nome" — ordena por score DESC.
    3. Sem query: retorna todas ativas ordenadas alfabeticamente.

    Returns: lista de dicts {id, nome, grupo, icone, score}
    """
    q = (q or '').strip()
    query = PessoalCategoria.query.filter(PessoalCategoria.ativa.is_(True))

    if q:
        like = f'%{q}%'
        query = query.filter(or_(
            PessoalCategoria.grupo.ilike(like),
            PessoalCategoria.nome.ilike(like),
            func.concat(PessoalCategoria.grupo, ' ', PessoalCategoria.nome).ilike(like),
        ))

    categorias = query.order_by(
        PessoalCategoria.grupo, PessoalCategoria.nome,
    ).limit(200).all()

    resultados = []
    q_norm = _norm(q)
    for c in categorias:
        texto = _norm(f'{c.grupo} {c.nome}')
        score = fuzz.token_set_ratio(q_norm, texto) if q_norm else 0
        resultados.append({
            'id': c.id,
            'nome': c.nome,
            'grupo': c.grupo,
            'icone': c.icone or 'fa-tag',
            'score': score,
        })

    if q_norm and len(q_norm) >= 3:
        resultados.sort(key=lambda r: (-r['score'], r['grupo'], r['nome']))

    return resultados[:limit]


# =============================================================================
# SERIE MENSAL PARA CATEGORIAS SELECIONADAS
# =============================================================================
def serie_mensal_categorias(categoria_ids, ano_ref, mes_ref, meses=6):
    """Soma mensal consolidada (e por categoria) para um conjunto de categorias.

    Returns:
        {
          'meses': [{'mes': 'YYYY-MM', 'mes_label': 'Abr/2026'}, ...],
          'consolidado': {
             'valores': [floats..N_meses],
             'total': float,
             'media_mensal': float,
             'despesas': float, 'receitas': float,
          },
          'series': [{'categoria_id', 'categoria', 'grupo', 'icone',
                      'valores': [...], 'total': float}, ...]
        }
    """
    categoria_ids = [int(c) for c in categoria_ids if c is not None and str(c).strip() != '']
    if not categoria_ids:
        return {'meses': [], 'consolidado': {}, 'series': []}

    janela = _janela_meses(ano_ref, mes_ref, meses)
    if not janela:
        return {'meses': [], 'consolidado': {}, 'series': []}

    primeiro_dia = janela[0]['inicio']
    apos_ultimo = janela[-1]['proximo']

    mes_col = func.date_trunc('month', PessoalTransacao.data)
    rows = db.session.query(
        mes_col.label('mes'),
        PessoalTransacao.categoria_id,
        PessoalTransacao.tipo,
        func.sum(PessoalTransacao.valor),
    ).filter(
        PessoalTransacao.excluir_relatorio.is_(False),
        PessoalTransacao.data >= primeiro_dia,
        PessoalTransacao.data < apos_ultimo,
        PessoalTransacao.categoria_id.in_(categoria_ids),
    ).group_by(
        mes_col, PessoalTransacao.categoria_id, PessoalTransacao.tipo,
    ).all()

    # Indexar por (cat_id, mes_str, tipo)
    por_cat = {}  # cat_id -> {mes_str: {debito, credito}}
    for mes_trunc, cat_id, tipo, soma in rows:
        mes_str = mes_trunc.strftime('%Y-%m')
        slot = por_cat.setdefault(cat_id, {}).setdefault(mes_str, {})
        slot[tipo] = float(soma or 0)

    cats = {
        c.id: c for c in PessoalCategoria.query.filter(
            PessoalCategoria.id.in_(categoria_ids),
        ).all()
    }

    series = []
    consolidado_mensal = [0.0] * len(janela)
    despesas_total = 0.0
    receitas_total = 0.0

    for cat_id in categoria_ids:
        cat = cats.get(cat_id)
        if not cat:
            continue
        valores = []
        for i, m in enumerate(janela):
            slot = por_cat.get(cat_id, {}).get(m['mes_str'], {})
            d = slot.get('debito', 0.0)
            r = slot.get('credito', 0.0)
            # Net = despesa (positivo = gasto efetivo). Se categoria e receita,
            # credito domina; senao debito domina.
            net = d - r
            # Consolidado reporta "gasto liquido" (debito - credito)
            consolidado_mensal[i] += net
            valores.append(d)  # serie por categoria mostra despesas
            despesas_total += d
            receitas_total += r
        series.append({
            'categoria_id': cat.id,
            'categoria': cat.nome,
            'grupo': cat.grupo,
            'icone': cat.icone or 'fa-tag',
            'valores': valores,
            'total': sum(valores),
        })

    total_consolidado = sum(consolidado_mensal)
    return {
        'meses': [{'mes': m['mes_str'], 'mes_label': m['mes_label']} for m in janela],
        'consolidado': {
            'valores': consolidado_mensal,
            'total': total_consolidado,
            'media_mensal': total_consolidado / len(janela) if janela else 0,
            'despesas': despesas_total,
            'receitas': receitas_total,
        },
        'series': series,
    }


# =============================================================================
# EXTRATO (TRANSACOES) DAS CATEGORIAS
# =============================================================================
def extrato_por_categorias(categoria_ids, ano_ref, mes_ref, meses=6,
                            limit=200, offset=0, incluir_receitas=True):
    """Lista transacoes das categorias dentro da janela de N meses.

    Args:
        incluir_receitas: se False, filtra apenas tipo='debito'.

    Returns:
        {'total': int, 'transacoes': [dict,...]}
    """
    categoria_ids = [int(c) for c in categoria_ids if c is not None and str(c).strip() != '']
    if not categoria_ids:
        return {'total': 0, 'transacoes': []}

    janela = _janela_meses(ano_ref, mes_ref, meses)
    if not janela:
        return {'total': 0, 'transacoes': []}

    primeiro_dia = janela[0]['inicio']
    apos_ultimo = janela[-1]['proximo']

    base = PessoalTransacao.query.filter(
        PessoalTransacao.excluir_relatorio.is_(False),
        PessoalTransacao.data >= primeiro_dia,
        PessoalTransacao.data < apos_ultimo,
        PessoalTransacao.categoria_id.in_(categoria_ids),
    )
    if not incluir_receitas:
        base = base.filter(PessoalTransacao.tipo == 'debito')

    total = base.count()
    transacoes = base.order_by(
        PessoalTransacao.data.desc(), PessoalTransacao.id.desc(),
    ).limit(max(1, min(limit, 500))).offset(max(0, offset)).all()

    return {
        'total': total,
        'transacoes': [
            {
                'id': t.id,
                'data': t.data.strftime('%d/%m/%Y') if t.data else '-',
                'historico': t.historico,
                'descricao': t.descricao,
                'valor': float(t.valor) if t.valor else 0,
                'tipo': t.tipo,
                'categoria_id': t.categoria_id,
                'categoria_nome': t.categoria.nome if t.categoria else None,
                'categoria_grupo': t.categoria.grupo if t.categoria else None,
                'conta_nome': t.conta.nome if t.conta else None,
            }
            for t in transacoes
        ],
    }


# =============================================================================
# CRUD GRUPOS
# =============================================================================
def listar_grupos():
    """Lista todos os grupos de analise ordenados por nome."""
    grupos = PessoalGrupoAnalise.query.order_by(PessoalGrupoAnalise.nome).all()
    return [g.to_dict() for g in grupos]


def criar_grupo(nome: str, categoria_ids: list, descricao: str = None, cor: str = None):
    """Cria um grupo. Erros sobem para a rota."""
    nome = (nome or '').strip()
    if not nome:
        raise ValueError('Nome obrigatorio.')
    if not categoria_ids:
        raise ValueError('Selecione ao menos uma categoria.')

    if PessoalGrupoAnalise.query.filter_by(nome=nome).first():
        raise ValueError(f'Grupo "{nome}" ja existe.')

    cats = PessoalCategoria.query.filter(
        PessoalCategoria.id.in_([int(c) for c in categoria_ids]),
    ).all()
    if not cats:
        raise ValueError('Categorias invalidas.')

    grupo = PessoalGrupoAnalise(
        nome=nome,
        descricao=(descricao or '').strip() or None,
        cor=(cor or '').strip() or None,
    )
    grupo.categorias = cats
    db.session.add(grupo)
    db.session.commit()
    return grupo.to_dict()


def atualizar_grupo(grupo_id: int, nome: str = None, categoria_ids: list = None,
                    descricao: str = None, cor: str = None):
    grupo = db.session.get(PessoalGrupoAnalise, grupo_id)
    if not grupo:
        raise ValueError('Grupo nao encontrado.')

    if nome is not None:
        nome = nome.strip()
        if not nome:
            raise ValueError('Nome obrigatorio.')
        if nome != grupo.nome:
            existente = PessoalGrupoAnalise.query.filter_by(nome=nome).first()
            if existente and existente.id != grupo.id:
                raise ValueError(f'Grupo "{nome}" ja existe.')
            grupo.nome = nome

    if descricao is not None:
        grupo.descricao = descricao.strip() or None

    if cor is not None:
        grupo.cor = cor.strip() or None

    if categoria_ids is not None:
        if not categoria_ids:
            raise ValueError('Selecione ao menos uma categoria.')
        cats = PessoalCategoria.query.filter(
            PessoalCategoria.id.in_([int(c) for c in categoria_ids]),
        ).all()
        grupo.categorias = cats

    db.session.commit()
    return grupo.to_dict()


def excluir_grupo(grupo_id: int):
    grupo = db.session.get(PessoalGrupoAnalise, grupo_id)
    if not grupo:
        raise ValueError('Grupo nao encontrado.')
    db.session.delete(grupo)
    db.session.commit()
    return True


def obter_grupo(grupo_id: int):
    grupo = db.session.get(PessoalGrupoAnalise, grupo_id)
    if not grupo:
        return None
    return grupo.to_dict()

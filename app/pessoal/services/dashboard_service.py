"""Service do dashboard pessoal — queries de agregacao on-the-fly."""
from datetime import date

from sqlalchemy import func, select

from app import db
from app.pessoal.models import PessoalTransacao, PessoalOrcamento, PessoalCategoria


# Grupos excluidos do orcamento (nao sao despesas)
GRUPOS_EXCLUIDOS = {'Receitas'}

MESES_PT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
            'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']


def _mes_label(ano, mes):
    """'Abr/2026' (portugues, independente do locale do SO)."""
    return f'{MESES_PT[mes - 1]}/{ano}'


def _janela_meses(ano_ref, mes_ref, meses):
    """Lista crescente de meses terminando em (ano_ref, mes_ref) com ranges ja calculados."""
    janela = []
    for i in range(meses - 1, -1, -1):
        m = mes_ref - i
        a = ano_ref
        while m <= 0:
            m += 12
            a -= 1
        inicio, proximo = _range_mes(a, m)
        janela.append({
            'ano': a,
            'mes': m,
            'inicio': inicio,
            'proximo': proximo,
            'mes_str': inicio.strftime('%Y-%m'),
            'mes_label': _mes_label(a, m),
        })
    return janela


def _range_mes(ano, mes):
    """Retorna (inicio, proximo_mes) para filtro de datas."""
    inicio = date(ano, mes, 1)
    if mes == 12:
        proximo = date(ano + 1, 1, 1)
    else:
        proximo = date(ano, mes + 1, 1)
    return inicio, proximo


def calcular_resumo_mensal(ano, mes):
    """KPIs: total despesas/receitas, limite global, saldo, %, delta mes anterior.

    Returns:
        dict com: total_despesas, total_receitas, limite_global, saldo,
                  percentual_usado, delta_despesas, delta_receitas
    """
    inicio, proximo = _range_mes(ano, mes)

    # Mes anterior
    if mes == 1:
        ano_ant, mes_ant = ano - 1, 12
    else:
        ano_ant, mes_ant = ano, mes - 1
    inicio_ant, proximo_ant = _range_mes(ano_ant, mes_ant)

    # Totais do mes atual
    totais = db.session.query(
        PessoalTransacao.tipo,
        func.sum(PessoalTransacao.valor),
    ).filter(
        PessoalTransacao.excluir_relatorio.is_(False),
        PessoalTransacao.data >= inicio,
        PessoalTransacao.data < proximo,
    ).group_by(PessoalTransacao.tipo).all()

    total_despesas = 0
    total_receitas = 0
    for tipo, soma in totais:
        if tipo == 'debito':
            total_despesas = float(soma or 0)
        elif tipo == 'credito':
            total_receitas = float(soma or 0)

    # Totais do mes anterior
    totais_ant = db.session.query(
        PessoalTransacao.tipo,
        func.sum(PessoalTransacao.valor),
    ).filter(
        PessoalTransacao.excluir_relatorio.is_(False),
        PessoalTransacao.data >= inicio_ant,
        PessoalTransacao.data < proximo_ant,
    ).group_by(PessoalTransacao.tipo).all()

    despesas_ant = 0
    receitas_ant = 0
    for tipo, soma in totais_ant:
        if tipo == 'debito':
            despesas_ant = float(soma or 0)
        elif tipo == 'credito':
            receitas_ant = float(soma or 0)

    # Orcamento global
    orc_global = PessoalOrcamento.query.filter_by(
        ano_mes=inicio, categoria_id=None,
    ).first()
    limite_global = float(orc_global.valor_limite) if orc_global else None

    # Calcular percentual e saldo
    saldo = None
    percentual_usado = None
    if limite_global and limite_global > 0:
        saldo = limite_global - total_despesas
        percentual_usado = round((total_despesas / limite_global) * 100, 1)

    # Delta vs mes anterior (absoluto em R$; zero genuino produz delta correto)
    delta_despesas = total_despesas - despesas_ant
    delta_receitas = total_receitas - receitas_ant

    return {
        'total_despesas': total_despesas,
        'total_receitas': total_receitas,
        'limite_global': limite_global,
        'saldo': saldo,
        'percentual_usado': percentual_usado,
        'delta_despesas': delta_despesas,
        'delta_receitas': delta_receitas,
        'despesas_mes_anterior': despesas_ant,
    }


def gastos_por_categoria(ano, mes):
    """Breakdown de gastos por categoria + limites do orcamento.

    Returns:
        list[dict] com: categoria_id, categoria, grupo, icone, gasto, limite, percentual
    """
    inicio, proximo = _range_mes(ano, mes)

    # Gastos agrupados por categoria
    gastos = dict(
        db.session.query(
            PessoalTransacao.categoria_id,
            func.sum(PessoalTransacao.valor),
        ).filter(
            PessoalTransacao.tipo == 'debito',
            PessoalTransacao.excluir_relatorio.is_(False),
            PessoalTransacao.data >= inicio,
            PessoalTransacao.data < proximo,
        ).group_by(PessoalTransacao.categoria_id).all()
    )

    # Limites do orcamento por categoria
    limites = dict(
        db.session.query(
            PessoalOrcamento.categoria_id,
            PessoalOrcamento.valor_limite,
        ).filter(
            PessoalOrcamento.ano_mes == inicio,
            PessoalOrcamento.categoria_id.isnot(None),
        ).all()
    )

    # Categorias ativas (excluindo Receitas)
    categorias = PessoalCategoria.query.filter(
        PessoalCategoria.ativa.is_(True),
        ~PessoalCategoria.grupo.in_(GRUPOS_EXCLUIDOS),
    ).order_by(PessoalCategoria.grupo, PessoalCategoria.nome).all()

    resultado = []
    for cat in categorias:
        gasto = float(gastos.get(cat.id, 0) or 0)
        if gasto == 0:
            continue  # Omitir categorias sem gasto no mes

        limite = float(limites.get(cat.id, 0) or 0) if cat.id in limites else None
        percentual = None
        if limite and limite > 0:
            percentual = round((gasto / limite) * 100, 1)

        resultado.append({
            'categoria_id': cat.id,
            'categoria': cat.nome,
            'grupo': cat.grupo,
            'icone': cat.icone or 'fa-tag',
            'gasto': gasto,
            'limite': limite,
            'percentual': percentual,
        })

    # Ordenar por gasto (maior primeiro)
    resultado.sort(key=lambda x: x['gasto'], reverse=True)
    return resultado


def tendencia_mensal(ano_ref, mes_ref, meses=6):
    """Totais mensais dos ultimos N meses ate (ano_ref, mes_ref) + limite global.

    Args:
        ano_ref, mes_ref: ponto final (inclusivo) da janela historica
        meses: quantidade de meses a retornar (2..24)

    Returns:
        list[dict] com: mes (YYYY-MM), despesas, receitas, limite
    """
    janela = _janela_meses(ano_ref, mes_ref, meses)
    if not janela:
        return []

    primeiro_dia = janela[0]['inicio']
    apos_ultimo = janela[-1]['proximo']

    # Query unica: agrega por (mes, tipo) em todo o intervalo
    mes_col = func.date_trunc('month', PessoalTransacao.data)
    rows = db.session.query(
        mes_col.label('mes'),
        PessoalTransacao.tipo,
        func.sum(PessoalTransacao.valor),
    ).filter(
        PessoalTransacao.excluir_relatorio.is_(False),
        PessoalTransacao.data >= primeiro_dia,
        PessoalTransacao.data < apos_ultimo,
    ).group_by(mes_col, PessoalTransacao.tipo).all()

    # Mapa: {'YYYY-MM': {'debito': x, 'credito': y}}
    totais_por_mes = {}
    for mes_trunc, tipo, soma in rows:
        mes_str = mes_trunc.strftime('%Y-%m')
        if mes_str not in totais_por_mes:
            totais_por_mes[mes_str] = {'debito': 0.0, 'credito': 0.0}
        totais_por_mes[mes_str][tipo] = float(soma or 0)

    # Limites globais de cada mes (query unica)
    datas_inicio = [m['inicio'] for m in janela]
    orc_rows = db.session.query(
        PessoalOrcamento.ano_mes,
        PessoalOrcamento.valor_limite,
    ).filter(
        PessoalOrcamento.ano_mes.in_(datas_inicio),
        PessoalOrcamento.categoria_id.is_(None),
    ).all()
    limites_por_mes = {d.strftime('%Y-%m'): float(v) for d, v in orc_rows}

    resultado = []
    for m in janela:
        totais_mes = totais_por_mes.get(m['mes_str'], {'debito': 0.0, 'credito': 0.0})
        resultado.append({
            'mes': m['mes_str'],
            'mes_label': m['mes_label'],
            'despesas': totais_mes.get('debito', 0.0),
            'receitas': totais_mes.get('credito', 0.0),
            'limite': limites_por_mes.get(m['mes_str']),
        })

    return resultado


# =============================================================================
# EVOLUCAO POR CATEGORIA (Fase 2)
# =============================================================================
def evolucao_por_categoria(ano_ref, mes_ref, meses=6, categoria_ids=None, top_n=5):
    """Evolucao mensal de gastos por categoria ao longo dos ultimos N meses.

    Args:
        ano_ref, mes_ref: ponto final da janela
        meses: quantidade de meses (2..24)
        categoria_ids: lista de ids a exibir; se vazia, usa Top N por gasto total
        top_n: quantas categorias retornar quando categoria_ids nao e fornecido

    Returns:
        {
          'meses': [{'mes': 'YYYY-MM', 'mes_label': 'Abr/2026'}, ...],
          'series': [{'categoria_id', 'categoria', 'grupo', 'icone', 'valores': [..]}, ...]
        }
    """
    janela = _janela_meses(ano_ref, mes_ref, meses)
    if not janela:
        return {'meses': [], 'series': []}

    primeiro_dia = janela[0]['inicio']
    apos_ultimo = janela[-1]['proximo']

    # Query unica agregada por (mes, categoria_id)
    mes_col = func.date_trunc('month', PessoalTransacao.data)
    rows = db.session.query(
        mes_col.label('mes'),
        PessoalTransacao.categoria_id,
        func.sum(PessoalTransacao.valor),
    ).filter(
        PessoalTransacao.tipo == 'debito',
        PessoalTransacao.excluir_relatorio.is_(False),
        PessoalTransacao.data >= primeiro_dia,
        PessoalTransacao.data < apos_ultimo,
        PessoalTransacao.categoria_id.isnot(None),
    ).group_by(mes_col, PessoalTransacao.categoria_id).all()

    # Organiza {categoria_id: {mes_str: valor}}
    gastos = {}
    totais_cat = {}
    for mes_trunc, cat_id, soma in rows:
        mes_str = mes_trunc.strftime('%Y-%m')
        valor = float(soma or 0)
        gastos.setdefault(cat_id, {})[mes_str] = valor
        totais_cat[cat_id] = totais_cat.get(cat_id, 0.0) + valor

    # Determinar categorias alvo
    if categoria_ids:
        categoria_ids = [int(c) for c in categoria_ids if c]
    else:
        # Top N por gasto total no periodo (excluindo grupos fora do orcamento)
        ids_validos = set(
            db.session.scalars(
                select(PessoalCategoria.id).where(
                    ~PessoalCategoria.grupo.in_(GRUPOS_EXCLUIDOS),
                )
            ).all()
        )
        top = sorted(
            ((cid, t) for cid, t in totais_cat.items() if cid in ids_validos),
            key=lambda x: x[1], reverse=True,
        )[:top_n]
        categoria_ids = [cid for cid, _ in top]

    if not categoria_ids:
        return {
            'meses': [{'mes': m['mes_str'], 'mes_label': m['mes_label']} for m in janela],
            'series': [],
        }

    # Metadata das categorias
    categorias = {
        c.id: c for c in PessoalCategoria.query.filter(
            PessoalCategoria.id.in_(categoria_ids),
        ).all()
    }

    series = []
    for cat_id in categoria_ids:
        cat = categorias.get(cat_id)
        if not cat:
            continue
        valores = [
            gastos.get(cat_id, {}).get(m['mes_str'], 0.0)
            for m in janela
        ]
        series.append({
            'categoria_id': cat.id,
            'categoria': cat.nome,
            'grupo': cat.grupo,
            'icone': cat.icone or 'fa-tag',
            'total': sum(valores),
            'valores': valores,
        })

    return {
        'meses': [{'mes': m['mes_str'], 'mes_label': m['mes_label']} for m in janela],
        'series': series,
    }


def listar_categorias_ativas():
    """Retorna categorias ativas (excluindo grupo Receitas) para popular filtros."""
    cats = PessoalCategoria.query.filter(
        PessoalCategoria.ativa.is_(True),
        ~PessoalCategoria.grupo.in_(GRUPOS_EXCLUIDOS),
    ).order_by(PessoalCategoria.grupo, PessoalCategoria.nome).all()
    return [
        {
            'id': c.id,
            'nome': c.nome,
            'grupo': c.grupo,
            'icone': c.icone or 'fa-tag',
        }
        for c in cats
    ]


# =============================================================================
# COMPARATIVO ANUAL (Fase 2)
# =============================================================================
def comparativo_anual(ano_ref):
    """Totais mensais de despesas e receitas do ano de referencia vs ano anterior.

    Returns:
        {
          'ano_atual': int, 'ano_anterior': int,
          'meses': ['Jan', 'Fev', ..., 'Dez'],
          'despesas_atual': [..12..], 'despesas_anterior': [..12..],
          'receitas_atual': [..12..], 'receitas_anterior': [..12..],
          'totais': {
             'despesas_atual': ..., 'despesas_anterior': ...,
             'receitas_atual': ..., 'receitas_anterior': ...,
             'delta_despesas_pct': ..., 'delta_receitas_pct': ...,
          }
        }
    """
    ano_anterior = ano_ref - 1
    inicio = date(ano_anterior, 1, 1)
    fim = date(ano_ref + 1, 1, 1)

    ano_col = func.extract('year', PessoalTransacao.data)
    mes_col = func.extract('month', PessoalTransacao.data)
    rows = db.session.query(
        ano_col.label('ano'),
        mes_col.label('mes'),
        PessoalTransacao.tipo,
        func.sum(PessoalTransacao.valor),
    ).filter(
        PessoalTransacao.excluir_relatorio.is_(False),
        PessoalTransacao.data >= inicio,
        PessoalTransacao.data < fim,
    ).group_by(ano_col, mes_col, PessoalTransacao.tipo).all()

    # Inicializa arrays com 12 zeros
    despesas_atual = [0.0] * 12
    despesas_anterior = [0.0] * 12
    receitas_atual = [0.0] * 12
    receitas_anterior = [0.0] * 12

    for ano, mes, tipo, soma in rows:
        idx = int(mes) - 1
        valor = float(soma or 0)
        if int(ano) == ano_ref:
            if tipo == 'debito':
                despesas_atual[idx] = valor
            elif tipo == 'credito':
                receitas_atual[idx] = valor
        elif int(ano) == ano_anterior:
            if tipo == 'debito':
                despesas_anterior[idx] = valor
            elif tipo == 'credito':
                receitas_anterior[idx] = valor

    tot_desp_atual = sum(despesas_atual)
    tot_desp_ant = sum(despesas_anterior)
    tot_rec_atual = sum(receitas_atual)
    tot_rec_ant = sum(receitas_anterior)

    def _delta_pct(atual, anterior):
        if anterior <= 0:
            return None
        return round(((atual - anterior) / anterior) * 100, 1)

    return {
        'ano_atual': ano_ref,
        'ano_anterior': ano_anterior,
        'meses': MESES_PT[:],
        'despesas_atual': despesas_atual,
        'despesas_anterior': despesas_anterior,
        'receitas_atual': receitas_atual,
        'receitas_anterior': receitas_anterior,
        'totais': {
            'despesas_atual': tot_desp_atual,
            'despesas_anterior': tot_desp_ant,
            'receitas_atual': tot_rec_atual,
            'receitas_anterior': tot_rec_ant,
            'delta_despesas_pct': _delta_pct(tot_desp_atual, tot_desp_ant),
            'delta_receitas_pct': _delta_pct(tot_rec_atual, tot_rec_ant),
        },
    }


# =============================================================================
# EXPORTACAO DE HISTORICO (Fase 2)
# =============================================================================
def historico_completo(ano_ref, mes_ref, meses=6):
    """Historico consolidado (tendencia + breakdown categoria por mes) para exportacao.

    Returns:
        {
          'meses': [{'mes': 'YYYY-MM', 'mes_label': 'Abr/2026'}, ...],
          'tendencia': [{'mes', 'despesas', 'receitas', 'limite', 'saldo'}, ...],
          'categorias': [{'categoria_id', 'categoria', 'grupo', 'valores': [..por mes..]}, ...]
        }
    """
    tend = tendencia_mensal(ano_ref, mes_ref, meses)
    # Adiciona saldo no tendencia
    for t in tend:
        t['saldo'] = (t['limite'] - t['despesas']) if t['limite'] is not None else None

    # Breakdown: TODAS as categorias com gasto no periodo (nao so top N)
    evol = evolucao_por_categoria(ano_ref, mes_ref, meses, categoria_ids=None, top_n=999)

    return {
        'meses': evol['meses'],
        'tendencia': tend,
        'categorias': evol['series'],
    }

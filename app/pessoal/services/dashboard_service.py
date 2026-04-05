"""Service do dashboard pessoal — queries de agregacao on-the-fly."""
from datetime import date

from sqlalchemy import func

from app import db
from app.pessoal.models import PessoalTransacao, PessoalOrcamento, PessoalCategoria


# Grupos excluidos do orcamento (nao sao despesas)
GRUPOS_EXCLUIDOS = {'Receitas'}


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

    # Delta vs mes anterior
    delta_despesas = total_despesas - despesas_ant if despesas_ant > 0 else 0
    delta_receitas = total_receitas - receitas_ant if receitas_ant > 0 else 0

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


def tendencia_mensal(meses=6):
    """Totais mensais dos ultimos N meses + limite global de cada mes.

    Returns:
        list[dict] com: mes (YYYY-MM), despesas, receitas, limite
    """
    hoje = date.today()

    resultado = []
    for i in range(meses - 1, -1, -1):  # Do mais antigo ao mais recente
        # Calcular ano/mes
        m = hoje.month - i
        a = hoje.year
        while m <= 0:
            m += 12
            a -= 1

        inicio, proximo = _range_mes(a, m)

        # Totais
        totais = db.session.query(
            PessoalTransacao.tipo,
            func.sum(PessoalTransacao.valor),
        ).filter(
            PessoalTransacao.excluir_relatorio.is_(False),
            PessoalTransacao.data >= inicio,
            PessoalTransacao.data < proximo,
        ).group_by(PessoalTransacao.tipo).all()

        despesas = 0
        receitas = 0
        for tipo, soma in totais:
            if tipo == 'debito':
                despesas = float(soma or 0)
            elif tipo == 'credito':
                receitas = float(soma or 0)

        # Limite global do mes
        orc = PessoalOrcamento.query.filter_by(
            ano_mes=inicio, categoria_id=None,
        ).first()
        limite = float(orc.valor_limite) if orc else None

        resultado.append({
            'mes': inicio.strftime('%Y-%m'),
            'mes_label': inicio.strftime('%b/%Y'),
            'despesas': despesas,
            'receitas': receitas,
            'limite': limite,
        })

    return resultado

"""Galeria de relatórios pré-definidos + builder curado + export.

O builder monta agregações APENAS a partir dos fragmentos do catálogo
(relatorio_catalogo) — nunca SQL livre. Grão = item-moto de venda FATURADA;
escopo de loja sempre reaplicado no servidor via _cond_venda.
"""
from __future__ import annotations

from sqlalchemy import case, func

from app import db
from app.hora.models import (
    HoraLoja, HoraModelo, HoraMoto, HoraVenda, HoraVendaItem,
)
from app.hora.services.gerencial.filtros import Filtros
from app.hora.services.gerencial.kpi_service import (
    _cond_venda, _custo_por_chassi_sq, _D,
)
from app.hora.services.gerencial.relatorio_catalogo import (
    DIMENSOES, METRICAS, validar_selecao,
)

RELATORIOS_PREDEFINIDOS = [
    {'slug': 'vendas_por_loja', 'label': 'Vendas por loja',
     'descricao': 'Unidades, receita e desconto por loja física.',
     'icone': 'fa-store', 'dims': ['loja'], 'metricas': ['unidades', 'receita', 'desconto_rs']},
    {'slug': 'margem_por_modelo', 'label': 'Margem por modelo',
     'descricao': 'Margem bruta e unidades por modelo de moto.',
     'icone': 'fa-motorcycle', 'dims': ['modelo'], 'metricas': ['unidades', 'receita', 'margem_rs']},
    {'slug': 'vendas_por_vendedor', 'label': 'Vendas por vendedor',
     'descricao': 'Receita e volume por vendedor.',
     'icone': 'fa-user-tie', 'dims': ['vendedor'], 'metricas': ['unidades', 'receita']},
    {'slug': 'vendas_por_periodo', 'label': 'Vendas por período',
     'descricao': 'Evolução de receita e unidades no tempo.',
     'icone': 'fa-calendar-alt', 'dims': ['periodo'], 'metricas': ['unidades', 'receita']},
    # Relatórios de grão NÃO-venda-item (chamam services dedicados, não o builder).
    {'slug': 'comissao_por_vendedor', 'label': 'Comissão por vendedor',
     'descricao': 'Comissão calculada por vendedor (config vigente, por faturamento).',
     'icone': 'fa-hand-holding-usd', 'especial': True},
    {'slug': 'aging_estoque', 'label': 'Aging de estoque',
     'descricao': 'Distribuição do estoque parado por faixa de dias.',
     'icone': 'fa-hourglass-half', 'especial': True},
    {'slug': 'divergencias_recebimento', 'label': 'Divergências de recebimento',
     'descricao': 'Divergências na conferência por tipo, no período.',
     'icone': 'fa-exclamation-triangle', 'especial': True},
]


def gerar_predefinido(slug: str, filtros: Filtros) -> dict:
    rel = next((r for r in RELATORIOS_PREDEFINIDOS if r['slug'] == slug), None)
    if rel is None:
        raise ValueError(f'Relatório desconhecido: {slug}')
    res = _gerar_especial(slug, filtros) if rel.get('especial') else gerar_builder(
        rel['dims'], rel['metricas'], filtros
    )
    res['titulo'] = rel['label']
    return res


def _gerar_especial(slug: str, filtros: Filtros) -> dict:
    """Relatórios pré-definidos com grão diferente de venda-item (reusam services)."""
    from app.hora.services.gerencial import (
        comercial_kpi_service, estoque_kpi_service, suprimento_kpi_service,
    )
    if slug == 'comissao_por_vendedor':
        rows = comercial_kpi_service.comissao_por_vendedor(filtros)
        colunas = [
            {'key': 'vendedor', 'label': 'Vendedor', 'tipo': 'texto'},
            {'key': 'qtd_vendas', 'label': 'Vendas', 'tipo': 'inteiro'},
            {'key': 'total', 'label': 'Comissão', 'tipo': 'moeda'},
        ]
        linhas = [{'vendedor': r['vendedor'], 'qtd_vendas': r['qtd_vendas'], 'total': r['total']} for r in rows]
    elif slug == 'aging_estoque':
        aging = estoque_kpi_service.aging_estoque(filtros)
        colunas = [
            {'key': 'faixa', 'label': 'Faixa (dias)', 'tipo': 'texto'},
            {'key': 'qtd', 'label': 'Motos', 'tipo': 'inteiro'},
        ]
        linhas = [{'faixa': f, 'qtd': q} for f, q in aging['faixas'].items()]
    elif slug == 'divergencias_recebimento':
        divs = suprimento_kpi_service.taxa_divergencia(filtros)
        colunas = [
            {'key': 'tipo', 'label': 'Tipo', 'tipo': 'texto'},
            {'key': 'qtd', 'label': 'Qtd', 'tipo': 'inteiro'},
            {'key': 'pct', 'label': '%', 'tipo': 'inteiro'},
        ]
        linhas = [{'tipo': d['tipo'], 'qtd': d['qtd'], 'pct': d['pct']} for d in divs]
    else:
        raise ValueError(f'Relatório especial desconhecido: {slug}')
    return {'colunas': colunas, 'linhas': linhas, 'dim': slug, 'metricas': []}


def gerar_builder(dimensoes, metricas, filtros: Filtros) -> dict:
    """Monta a tabela agregada para 1 dimensão + N métricas (curadas)."""
    ok, erro = validar_selecao(dimensoes, metricas)
    if not ok:
        raise ValueError(erro)
    dim = dimensoes[0]  # v1: uma dimensão por relatório
    custo_sq = _custo_por_chassi_sq()
    metric_exprs = {
        'unidades': func.count(HoraVendaItem.id),
        'receita': func.coalesce(func.sum(HoraVendaItem.preco_final), 0),
        'desconto_rs': func.coalesce(func.sum(HoraVendaItem.desconto_aplicado), 0),
        'desconto_pct': func.coalesce(func.avg(HoraVendaItem.desconto_percentual), 0),
        'margem_rs': func.coalesce(
            func.sum(case(
                (custo_sq.c.preco_real.isnot(None), HoraVendaItem.preco_final - custo_sq.c.preco_real),
                else_=0,
            )), 0,
        ),
    }
    trunc = {'dia': 'day', 'semana': 'week', 'mes': 'month'}.get(filtros.granularidade, 'day')
    if dim == 'loja':
        dim_expr = HoraVenda.loja_id
    elif dim == 'vendedor':
        dim_expr = HoraVenda.vendedor
    elif dim == 'modelo':
        dim_expr = HoraModelo.nome_modelo
    elif dim == 'cor':
        dim_expr = HoraMoto.cor
    else:  # periodo
        dim_expr = func.date_trunc(trunc, HoraVenda.data_venda)

    cols = [dim_expr.label('dimv')] + [metric_exprs[m].label(m) for m in metricas]
    q = (
        db.session.query(*cols)
        .select_from(HoraVendaItem)
        .join(HoraVenda, HoraVendaItem.venda_id == HoraVenda.id)
        .outerjoin(custo_sq, custo_sq.c.chassi == HoraVendaItem.numero_chassi)
    )
    if dim in ('modelo', 'cor'):
        q = q.join(HoraMoto, HoraMoto.numero_chassi == HoraVendaItem.numero_chassi)
    if dim == 'modelo':
        q = q.join(HoraModelo, HoraModelo.id == HoraMoto.modelo_id)
    q = q.filter(*_cond_venda(filtros)).group_by(dim_expr).order_by(dim_expr)
    rows = q.all()

    nomes_loja = (
        dict(db.session.query(HoraLoja.id, HoraLoja.apelido).all()) if dim == 'loja' else {}
    )
    linhas = []
    for row in rows:
        linha = {'_dim': _label_dim(dim, row[0], nomes_loja)}
        for i, m in enumerate(metricas):
            v = row[i + 1]
            linha[m] = int(v or 0) if m == 'unidades' else _D(v)
        linhas.append(linha)

    colunas = [{'key': '_dim', 'label': DIMENSOES[dim]['label'], 'tipo': 'texto'}]
    colunas += [{'key': m, 'label': METRICAS[m]['label'], 'tipo': METRICAS[m]['tipo']} for m in metricas]
    return {'colunas': colunas, 'linhas': linhas, 'dim': dim, 'metricas': list(metricas)}


def _label_dim(dim, valor, nomes_loja):
    if dim == 'loja':
        return nomes_loja.get(valor, '(sem loja)') if valor else '(sem loja)'
    if dim == 'periodo':
        return valor.date().isoformat() if hasattr(valor, 'date') else str(valor)
    return valor if valor is not None else '(não informado)'


def exportar(resultado: dict, formato: str = 'xlsx') -> bytes:
    """Serializa o resultado do relatório em xlsx (default) ou csv."""
    colunas = resultado['colunas']
    linhas = resultado['linhas']
    if formato == 'csv':
        import csv
        import io
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=';')
        writer.writerow([c['label'] for c in colunas])
        for linha in linhas:
            writer.writerow([linha.get(c['key'], '') for c in colunas])
        return buf.getvalue().encode('utf-8-sig')

    import io
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = 'Relatorio'
    ws.append([c['label'] for c in colunas])
    for linha in linhas:
        out_row = []
        for c in colunas:
            v = linha.get(c['key'])
            if c['tipo'] in ('moeda',) and v is not None:
                v = float(v)
            out_row.append(v)
        ws.append(out_row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

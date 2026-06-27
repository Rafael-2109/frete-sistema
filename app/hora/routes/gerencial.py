"""Seção Gerencial HORA — dashboards (Executivo/Comercial/Estoque/Suprimento)
+ área de relatórios (galeria + builder).

Fonte exclusiva `hora_*`. KPIs em SQL agregado (services em
`app/hora/services/gerencial/`). Escopo por loja aplicado no WHERE via
`lojas_permitidas_ids()` → `parse_filtros(...).lojas`. Dois slugs de permissão:
`gerencial` (dashboards) e `gerencial_relatorios` (relatórios).
"""
from __future__ import annotations

from flask import redirect, render_template, request, url_for

from app.hora.decorators import require_hora_perm
from app.hora.routes import hora_bp
from app.hora.services.auth_helper import lojas_permitidas_ids
from app.hora.services.gerencial.filtros import parse_filtros


def _lojas_disponiveis(lojas_permitidas):
    """Lojas ativas visíveis ao usuário (todas se irrestrito; só as do escopo)."""
    from app.hora.models import HoraLoja
    q = HoraLoja.query.filter_by(ativa=True)
    if lojas_permitidas is not None:
        if not lojas_permitidas:
            return []
        q = q.filter(HoraLoja.id.in_(lojas_permitidas))
    return q.order_by(HoraLoja.apelido).all()


def _contexto_base(aba_ativa: str) -> dict:
    """Contexto comum a todas as telas: filtros resolvidos + lojas + aba ativa."""
    lojas_permitidas = lojas_permitidas_ids()
    filtros = parse_filtros(request.args, lojas_permitidas=lojas_permitidas)
    return {
        'filtros': filtros,
        'lojas_disponiveis': _lojas_disponiveis(lojas_permitidas),
        'aba_ativa': aba_ativa,
    }


@hora_bp.route('/gerencial')
@require_hora_perm('gerencial', 'ver')
def gerencial_index():
    """Entrada da seção — redireciona para a Visão Executiva preservando filtros."""
    return redirect(url_for('hora.gerencial_executivo', **request.args))


def _serie_xy(items, label_key, val_key):
    """Empacota lista de dicts em {labels, data} com data em float (p/ Chart.js)."""
    return {
        'labels': [i[label_key] for i in items],
        'data': [float(i[val_key]) for i in items],
    }


@hora_bp.route('/gerencial/executivo')
@require_hora_perm('gerencial', 'ver')
def gerencial_executivo():
    from app.hora.services.gerencial import kpi_service
    ctx = _contexto_base('executivo')
    kpis = kpi_service.kpis_executivo(ctx['filtros'])
    ctx['kpis'] = kpis
    ctx['chart_receita'] = _serie_xy(kpis['serie_receita'], 'periodo', 'valor')
    ctx['chart_ranking'] = _serie_xy(kpis['ranking_lojas'], 'loja_nome', 'receita')
    return render_template('hora/gerencial/executivo.html', **ctx)


@hora_bp.route('/gerencial/comercial')
@require_hora_perm('gerencial', 'ver')
def gerencial_comercial():
    from app.hora.services.gerencial import comercial_kpi_service as cks
    ctx = _contexto_base('comercial')
    kpis = cks.kpis_comercial(ctx['filtros'])
    # enriquece o ranking de vendedores com a comissão calculada
    comissao_por_vend = {c['vendedor']: c['total'] for c in kpis['comissao']}
    for v in kpis['vendedores']:
        v['comissao'] = comissao_por_vend.get(v['vendedor'], 0)
    ctx['kpis'] = kpis
    ctx['chart_mix'] = _serie_xy(kpis['mix_pagamento'], 'forma', 'valor')
    return render_template('hora/gerencial/comercial.html', **ctx)


@hora_bp.route('/gerencial/estoque')
@require_hora_perm('gerencial', 'ver')
def gerencial_estoque():
    from app.hora.services.gerencial import estoque_kpi_service as eks
    ctx = _contexto_base('estoque')
    kpis = eks.kpis_estoque(ctx['filtros'])
    ctx['kpis'] = kpis
    ctx['chart_giro'] = _serie_xy(kpis['giro'], 'modelo', 'dias_medios')
    ctx['chart_aging'] = {
        'labels': list(kpis['aging']['faixas'].keys()),
        'data': list(kpis['aging']['faixas'].values()),
    }
    return render_template('hora/gerencial/estoque.html', **ctx)


@hora_bp.route('/gerencial/suprimento')
@require_hora_perm('gerencial', 'ver')
def gerencial_suprimento():
    from app.hora.services.gerencial import suprimento_kpi_service as sks
    ctx = _contexto_base('suprimento')
    kpis = sks.kpis_suprimento(ctx['filtros'])
    ctx['kpis'] = kpis
    ctx['chart_divergencia'] = _serie_xy(kpis['divergencias'], 'tipo', 'qtd')
    return render_template('hora/gerencial/suprimento.html', **ctx)


@hora_bp.route('/gerencial/relatorios')
@require_hora_perm('gerencial_relatorios', 'ver')
def gerencial_relatorios():
    ctx = _contexto_base('relatorios')
    return render_template('hora/gerencial/relatorios.html', **ctx)

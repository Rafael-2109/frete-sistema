"""Rotas do dashboard pessoal — KPIs, graficos e tabela resumo."""
import csv
import io
from datetime import date

from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required, current_user

from app.pessoal import pode_acessar_pessoal
from app.pessoal.services.dashboard_service import (
    calcular_resumo_mensal, gastos_por_categoria, tendencia_mensal,
    evolucao_por_categoria, listar_categorias_ativas, comparativo_anual,
    historico_completo,
)

dashboard_bp = Blueprint('pessoal_dashboard', __name__)


def _parse_mes(mes_str):
    """Extrai (ano, mes) validos de 'YYYY-MM'. Fallback: mes atual."""
    try:
        partes = mes_str.split('-')
        ano, mes = int(partes[0]), int(partes[1])
        # Valida que a data e construivel (rejeita mes=13, ano=0, etc.)
        date(ano, mes, 1)
        return ano, mes
    except (ValueError, IndexError, AttributeError, TypeError):
        hoje = date.today()
        return hoje.year, hoje.month


@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Pagina principal do dashboard pessoal."""
    if not pode_acessar_pessoal(current_user):
        return 'Acesso restrito.', 403

    return render_template('pessoal/dashboard.html')


@dashboard_bp.route('/api/dashboard/resumo')
@login_required
def api_resumo():
    """KPIs do mes selecionado."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False}), 403

    ano, mes = _parse_mes(request.args.get('mes'))
    resumo = calcular_resumo_mensal(ano, mes)
    return jsonify({'sucesso': True, **resumo})


@dashboard_bp.route('/api/dashboard/categorias')
@login_required
def api_categorias():
    """Gastos por categoria do mes selecionado."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False}), 403

    ano, mes = _parse_mes(request.args.get('mes'))
    categorias = gastos_por_categoria(ano, mes)
    return jsonify({'sucesso': True, 'categorias': categorias})


@dashboard_bp.route('/api/dashboard/tendencia')
@login_required
def api_tendencia():
    """Tendencia mensal dos ultimos N meses ancorada no mes selecionado."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False}), 403

    ano, mes = _parse_mes(request.args.get('mes'))
    n_meses = _clamp_meses(request.args.get('meses', 6, type=int))
    dados = tendencia_mensal(ano, mes, n_meses)
    return jsonify({'sucesso': True, 'tendencia': dados})


def _clamp_meses(n):
    """Garante 2 <= meses <= 24."""
    if n is None or n < 2:
        return 2
    if n > 24:
        return 24
    return n


def _parse_categoria_ids(raw):
    """'1,2,3' -> [1, 2, 3]. Ignora valores invalidos."""
    if not raw:
        return []
    ids = []
    for parte in raw.split(','):
        parte = parte.strip()
        if not parte:
            continue
        try:
            ids.append(int(parte))
        except ValueError:
            continue
    return ids


@dashboard_bp.route('/api/dashboard/categorias-lista')
@login_required
def api_categorias_lista():
    """Lista de categorias ativas para popular multi-select."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False}), 403

    return jsonify({'sucesso': True, 'categorias': listar_categorias_ativas()})


@dashboard_bp.route('/api/dashboard/evolucao-categorias')
@login_required
def api_evolucao_categorias():
    """Evolucao mensal de gastos por categoria (top N ou ids especificos)."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False}), 403

    ano, mes = _parse_mes(request.args.get('mes'))
    n_meses = _clamp_meses(request.args.get('meses', 6, type=int))
    cat_ids = _parse_categoria_ids(request.args.get('categorias'))
    top_n = request.args.get('top', 5, type=int)
    if top_n < 1:
        top_n = 1
    elif top_n > 15:
        top_n = 15

    dados = evolucao_por_categoria(ano, mes, n_meses, cat_ids, top_n)
    return jsonify({'sucesso': True, **dados})


@dashboard_bp.route('/api/dashboard/comparativo-anual')
@login_required
def api_comparativo_anual():
    """Compara totais mensais do ano de referencia vs ano anterior."""
    if not pode_acessar_pessoal(current_user):
        return jsonify({'sucesso': False}), 403

    ano, _ = _parse_mes(request.args.get('mes'))
    dados = comparativo_anual(ano)
    return jsonify({'sucesso': True, **dados})


@dashboard_bp.route('/api/dashboard/exportar-historico')
@login_required
def api_exportar_historico():
    """Exporta historico (tendencia + breakdown categoria por mes) como CSV.

    Query params: mes=YYYY-MM, meses=N (2..24)
    """
    if not pode_acessar_pessoal(current_user):
        return 'Acesso restrito.', 403

    ano, mes = _parse_mes(request.args.get('mes'))
    n_meses = _clamp_meses(request.args.get('meses', 6, type=int))
    dados = historico_completo(ano, mes, n_meses)

    output = io.StringIO()
    # BOM para Excel abrir UTF-8 corretamente
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')

    meses_labels = [m['mes_label'] for m in dados['meses']]

    # ---- Secao 1: Resumo mensal (tendencia) ----
    writer.writerow(['RESUMO MENSAL'])
    writer.writerow(['Mes', 'Despesas', 'Receitas', 'Orcamento', 'Saldo'])
    for t in dados['tendencia']:
        writer.writerow([
            t['mes_label'],
            _fmt_brl(t['despesas']),
            _fmt_brl(t['receitas']),
            _fmt_brl(t['limite']) if t['limite'] is not None else '',
            _fmt_brl(t['saldo']) if t['saldo'] is not None else '',
        ])
    writer.writerow([])

    # ---- Secao 2: Breakdown por categoria (linha = categoria, coluna = mes) ----
    writer.writerow(['GASTOS POR CATEGORIA'])
    writer.writerow(['Grupo', 'Categoria'] + meses_labels + ['Total'])
    for s in dados['categorias']:
        linha = [s['grupo'], s['categoria']]
        linha.extend(_fmt_brl(v) for v in s['valores'])
        linha.append(_fmt_brl(s['total']))
        writer.writerow(linha)

    csv_bytes = output.getvalue().encode('utf-8')
    filename = f'historico_pessoal_{ano:04d}-{mes:02d}_{n_meses}meses.csv'
    return Response(
        csv_bytes,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


def _fmt_brl(valor):
    """Formata numero no padrao brasileiro: 1.234,56"""
    if valor is None:
        return ''
    return f'{float(valor):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

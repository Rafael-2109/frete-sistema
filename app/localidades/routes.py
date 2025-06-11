from flask import request, render_template, Blueprint, send_file, jsonify

from flask_login import login_required

from app.localidades.forms import CidadeForm

from app.localidades.models import Cidade

from io import BytesIO

import openpyxl

from datetime import datetime

localidades_bp = Blueprint('localidades', __name__,url_prefix='/localidades')

@localidades_bp.route('/cidades', methods=['GET'])
@login_required
def cadastrar_cidade():
    form = CidadeForm()
    uf = request.args.get('uf')
    cidade_nome = request.args.get('cidade')
    microrregiao = request.args.get('microrregiao')
    mesorregiao = request.args.get('mesorregiao')

    # Iniciar a query para cidades
    query = Cidade.query.order_by(Cidade.uf).order_by(Cidade.nome)

    # Aplicar filtros conforme parâmetros enviados
    if uf:
        query = query.filter(Cidade.uf == uf)

    if cidade_nome:
        query = query.filter(Cidade.nome == cidade_nome)

    if microrregiao:
        query = query.filter(Cidade.microrregiao == microrregiao)

    if mesorregiao:
        query = query.filter(Cidade.mesorregiao == mesorregiao)

    # Executar a query após filtros
    cidades = query.order_by(Cidade.nome).all()

    # Populando selects corretamente
    cidade_nome = Cidade.query.filter_by(uf=uf).order_by(Cidade.nome).all() if uf else []
    microrregioes = sorted({c.microrregiao for c in Cidade.query.filter_by(uf=uf).all() if c.microrregiao}) if uf else []
    mesorregioes = sorted({c.mesorregiao for c in Cidade.query.filter_by(uf=uf).all() if c.mesorregiao}) if uf else []

    return render_template('localidades/cidades.html',
                           cidades=cidades,
                           form=form,
                           microrregioes=microrregioes,
                           mesorregioes=mesorregioes,
                           filtros=request.args)


    
@localidades_bp.route('/exportar_cidades', methods=['GET'])
@login_required
def exportar_cidades():
    form = CidadeForm()
    uf = request.args.get('uf')
    microrregiao = request.args.get('microrregiao')
    mesorregiao = request.args.get('mesorregiao')

    query = Cidade.query
    if uf:
        query = query.filter_by(uf=uf)
    if microrregiao:
        query = query.filter_by(microrregiao=microrregiao)
    if mesorregiao:
        query = query.filter_by(mesorregiao=mesorregiao)

    cidades = query.all()

    output = BytesIO()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(['Transportadora', 'Cidade', 'UF', 'Codigo IBGE', 'Tabela', 'Lead Time', 'Microrregião', 'Mesorregião'])

    for c in cidades:
        sheet.append(['', c.nome, c.uf, c.codigo_ibge, '', '', c.microrregiao, c.mesorregiao])

    workbook.save(output)
    output.seek(0)

    filename = f"export_cidades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@localidades_bp.route('/ajax/cidades_por_uf/<uf>')
@login_required
def cidades_por_uf(uf):
    cidades = Cidade.query.filter_by(uf=uf).order_by(Cidade.nome).all()
    return jsonify([cidade.nome for cidade in cidades])

@localidades_bp.route('/ajax/microrregioes_por_uf/<uf>')
@login_required
def microrregioes_por_uf(uf):
    microrregioes = Cidade.query.filter_by(uf=uf).distinct(Cidade.microrregiao).all()
    micros = sorted(set(c.microrregiao for c in microrregioes if c.microrregiao))
    return jsonify(micros)

@localidades_bp.route('/ajax/mesorregioes_por_uf/<uf>')
@login_required
def mesorregioes_por_uf(uf):
    mesorregioes = Cidade.query.filter_by(uf=uf).distinct(Cidade.mesorregiao).all()
    mesos = sorted(set(c.mesorregiao for c in mesorregioes if c.mesorregiao))
    return jsonify(mesos)

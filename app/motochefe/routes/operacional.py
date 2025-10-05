"""
Rotas Operacionais (Custos e Despesas) - MotoChefe
"""
from flask import render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from decimal import Decimal
import pandas as pd
from io import BytesIO
from datetime import datetime, date

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.routes.cadastros import requer_motochefe
from app.motochefe.models import CustosOperacionais, DespesaMensal

@motochefe_bp.route('/custos')
@login_required
@requer_motochefe
def custos_operacionais():
    """Exibe e edita custos operacionais"""
    custos = CustosOperacionais.get_custos_vigentes()

    if not custos:
        # Criar registro inicial se não existir
        custos = CustosOperacionais(
            custo_montagem=Decimal('70.00'),
            custo_movimentacao_rj=Decimal('40.00'),
            custo_movimentacao_nacom=Decimal('50.00'),
            valor_comissao_fixa=Decimal('80.00'),
            criado_por=current_user.nome
        )
        db.session.add(custos)
        db.session.commit()

    return render_template('motochefe/operacional/custos.html', custos=custos)

@motochefe_bp.route('/custos/atualizar', methods=['POST'])
@login_required
@requer_motochefe
def atualizar_custos():
    """Atualiza custos operacionais"""
    custos = CustosOperacionais.get_custos_vigentes()

    if not custos:
        flash('Custos não encontrados', 'danger')
        return redirect(url_for('motochefe.custos_operacionais'))

    try:
        custos.custo_montagem = Decimal(request.form.get('custo_montagem'))
        custos.custo_movimentacao_rj = Decimal(request.form.get('custo_movimentacao_rj'))
        custos.custo_movimentacao_nacom = Decimal(request.form.get('custo_movimentacao_nacom'))
        custos.valor_comissao_fixa = Decimal(request.form.get('valor_comissao_fixa'))
        custos.atualizado_por = current_user.nome

        db.session.commit()
        flash('Custos atualizados com sucesso!', 'success')

    except Exception as e:
        flash(f'Erro ao atualizar custos: {str(e)}', 'danger')

    return redirect(url_for('motochefe.custos_operacionais'))

# ===== DESPESA MENSAL =====

@motochefe_bp.route('/despesas')
@login_required
@requer_motochefe
def listar_despesas():
    """Lista despesas mensais"""
    # Filtros opcionais
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)

    query = DespesaMensal.query.filter_by(ativo=True)

    if mes:
        query = query.filter_by(mes_competencia=mes)
    if ano:
        query = query.filter_by(ano_competencia=ano)

    despesas = query.order_by(
        DespesaMensal.ano_competencia.desc(),
        DespesaMensal.mes_competencia.desc(),
        DespesaMensal.tipo_despesa
    ).all()

    # Totalizadores
    total_geral = sum(d.valor for d in despesas)
    total_pago = sum(d.valor_pago or 0 for d in despesas)
    total_aberto = total_geral - total_pago

    return render_template('motochefe/operacional/despesas/listar.html',
                         despesas=despesas,
                         total_geral=total_geral,
                         total_pago=total_pago,
                         total_aberto=total_aberto,
                         mes_filtro=mes,
                         ano_filtro=ano)

@motochefe_bp.route('/despesas/adicionar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def adicionar_despesa():
    """Adiciona nova despesa"""
    if request.method == 'POST':
        tipo = request.form.get('tipo_despesa')
        valor = request.form.get('valor')
        mes = request.form.get('mes_competencia')
        ano = request.form.get('ano_competencia')

        if not all([tipo, valor, mes, ano]):
            flash('Tipo, valor, mês e ano são obrigatórios', 'danger')
            return redirect(url_for('motochefe.adicionar_despesa'))

        despesa = DespesaMensal(
            tipo_despesa=tipo,
            descricao=request.form.get('descricao'),
            valor=Decimal(valor),
            mes_competencia=int(mes),
            ano_competencia=int(ano),
            data_vencimento=request.form.get('data_vencimento') or None,
            status=request.form.get('status', 'PENDENTE'),
            criado_por=current_user.nome
        )

        db.session.add(despesa)
        db.session.commit()

        flash(f'Despesa "{tipo}" cadastrada com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_despesas'))

    # Valores padrão
    hoje = date.today()
    return render_template('motochefe/operacional/despesas/form.html',
                         despesa=None,
                         mes_atual=hoje.month,
                         ano_atual=hoje.year)

@motochefe_bp.route('/despesas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def editar_despesa(id):
    """Edita despesa existente"""
    despesa = DespesaMensal.query.get_or_404(id)

    if request.method == 'POST':
        despesa.tipo_despesa = request.form.get('tipo_despesa')
        despesa.descricao = request.form.get('descricao')
        despesa.valor = Decimal(request.form.get('valor'))
        despesa.mes_competencia = int(request.form.get('mes_competencia'))
        despesa.ano_competencia = int(request.form.get('ano_competencia'))
        despesa.data_vencimento = request.form.get('data_vencimento') or None
        despesa.status = request.form.get('status')
        despesa.atualizado_por = current_user.nome

        db.session.commit()
        flash('Despesa atualizada com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_despesas'))

    hoje = date.today()
    return render_template('motochefe/operacional/despesas/form.html',
                         despesa=despesa,
                         mes_atual=hoje.month,
                         ano_atual=hoje.year)

@motochefe_bp.route('/despesas/<int:id>/pagar', methods=['POST'])
@login_required
@requer_motochefe
def pagar_despesa(id):
    """Registra pagamento de despesa"""
    despesa = DespesaMensal.query.get_or_404(id)

    valor_pago = request.form.get('valor_pago')
    data_pagamento = request.form.get('data_pagamento') or date.today()

    if not valor_pago:
        flash('Informe o valor pago', 'danger')
        return redirect(url_for('motochefe.listar_despesas'))

    despesa.valor_pago = Decimal(valor_pago)
    despesa.data_pagamento = data_pagamento
    despesa.status = 'PAGO' if despesa.saldo_aberto <= 0 else 'PENDENTE'
    despesa.atualizado_por = current_user.nome

    db.session.commit()
    flash('Pagamento registrado com sucesso!', 'success')
    return redirect(url_for('motochefe.listar_despesas'))

@motochefe_bp.route('/despesas/<int:id>/remover', methods=['POST'])
@login_required
@requer_motochefe
def remover_despesa(id):
    """Remove (desativa) despesa"""
    despesa = DespesaMensal.query.get_or_404(id)
    despesa.ativo = False
    despesa.atualizado_por = current_user.nome
    db.session.commit()

    flash('Despesa removida com sucesso!', 'success')
    return redirect(url_for('motochefe.listar_despesas'))

@motochefe_bp.route('/despesas/exportar')
@login_required
@requer_motochefe
def exportar_despesas():
    """Exporta despesas para Excel"""
    despesas = DespesaMensal.query.filter_by(ativo=True).order_by(
        DespesaMensal.ano_competencia.desc(),
        DespesaMensal.mes_competencia.desc()
    ).all()

    data = [{
        'ID': d.id,
        'Tipo': d.tipo_despesa,
        'Descrição': d.descricao or '',
        'Valor': float(d.valor),
        'Mês': d.mes_competencia,
        'Ano': d.ano_competencia,
        'Vencimento': d.data_vencimento.strftime('%d/%m/%Y') if d.data_vencimento else '',
        'Data Pagamento': d.data_pagamento.strftime('%d/%m/%Y') if d.data_pagamento else '',
        'Valor Pago': float(d.valor_pago or 0),
        'Saldo Aberto': float(d.saldo_aberto),
        'Status': d.status,
        'Atrasada': 'Sim' if d.atrasada else 'Não'
    } for d in despesas]

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Despesas')

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'despesas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@motochefe_bp.route('/despesas/importar', methods=['POST'])
@login_required
@requer_motochefe
def importar_despesas():
    """Importa despesas de Excel"""
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('motochefe.listar_despesas'))

    file = request.files['arquivo']
    if file.filename == '':
        flash('Arquivo inválido', 'danger')
        return redirect(url_for('motochefe.listar_despesas'))

    try:
        df = pd.read_excel(file)

        # Validar colunas obrigatórias
        required_cols = ['Tipo', 'Valor', 'Mês', 'Ano']
        if not all(col in df.columns for col in required_cols):
            flash(f'Planilha deve conter colunas: {", ".join(required_cols)}', 'danger')
            return redirect(url_for('motochefe.listar_despesas'))

        importados = 0
        for _, row in df.iterrows():
            tipo = row['Tipo']
            valor = row['Valor']
            mes = row['Mês']
            ano = row['Ano']

            if pd.isna(tipo) or pd.isna(valor) or pd.isna(mes) or pd.isna(ano):
                continue

            despesa = DespesaMensal(
                tipo_despesa=str(tipo),
                descricao=row.get('Descrição') if 'Descrição' in df.columns and not pd.isna(row.get('Descrição')) else None,
                valor=Decimal(str(valor)),
                mes_competencia=int(mes),
                ano_competencia=int(ano),
                status=row.get('Status', 'PENDENTE') if 'Status' in df.columns else 'PENDENTE',
                criado_por=current_user.nome
            )
            db.session.add(despesa)
            importados += 1

        db.session.commit()
        flash(f'{importados} despesas importadas com sucesso!', 'success')

    except Exception as e:
        flash(f'Erro ao importar: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_despesas'))

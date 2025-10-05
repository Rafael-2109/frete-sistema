"""
Rotas de Produtos (ModeloMoto e Moto) - MotoChefe
"""
from flask import render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required, current_user
from decimal import Decimal
import pandas as pd
from io import BytesIO
from datetime import datetime, date

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.routes.cadastros import requer_motochefe
from app.motochefe.models import ModeloMoto, Moto
from app.utils.valores_brasileiros import converter_valor_brasileiro

@motochefe_bp.route('/modelos')
@login_required
@requer_motochefe
def listar_modelos():
    """Lista modelos de motos"""
    modelos = ModeloMoto.query.filter_by(ativo=True).order_by(ModeloMoto.nome_modelo).all()
    return render_template('motochefe/produtos/modelos/listar.html', modelos=modelos)

@motochefe_bp.route('/modelos/adicionar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def adicionar_modelo():
    """Adiciona novo modelo"""
    if request.method == 'POST':
        nome = request.form.get('nome_modelo')
        potencia = request.form.get('potencia_motor')
        preco = request.form.get('preco_tabela')

        if not nome or not potencia or not preco:
            flash('Nome, potência e preço são obrigatórios', 'danger')
            return redirect(url_for('motochefe.adicionar_modelo'))

        # Verificar duplicidade
        existe = ModeloMoto.query.filter_by(nome_modelo=nome, ativo=True).first()
        if existe:
            flash('Modelo já cadastrado', 'warning')
            return redirect(url_for('motochefe.listar_modelos'))

        modelo = ModeloMoto(
            nome_modelo=nome,
            descricao=request.form.get('descricao'),
            potencia_motor=potencia,
            autopropelido=bool(request.form.get('autopropelido')),
            preco_tabela=Decimal(preco),
            criado_por=current_user.nome
        )
        db.session.add(modelo)
        db.session.commit()

        flash(f'Modelo "{nome}" cadastrado com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_modelos'))

    return render_template('motochefe/produtos/modelos/form.html', modelo=None)

@motochefe_bp.route('/modelos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def editar_modelo(id):
    """Edita modelo existente"""
    modelo = ModeloMoto.query.get_or_404(id)

    if request.method == 'POST':
        modelo.nome_modelo = request.form.get('nome_modelo')
        modelo.descricao = request.form.get('descricao')
        modelo.potencia_motor = request.form.get('potencia_motor')
        modelo.autopropelido = bool(request.form.get('autopropelido'))
        modelo.preco_tabela = Decimal(request.form.get('preco_tabela'))
        modelo.atualizado_por = current_user.nome
        db.session.commit()

        flash('Modelo atualizado com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_modelos'))

    return render_template('motochefe/produtos/modelos/form.html', modelo=modelo)

@motochefe_bp.route('/modelos/<int:id>/remover', methods=['POST'])
@login_required
@requer_motochefe
def remover_modelo(id):
    """Remove (desativa) modelo"""
    modelo = ModeloMoto.query.get_or_404(id)
    modelo.ativo = False
    modelo.atualizado_por = current_user.nome
    db.session.commit()

    flash('Modelo removido com sucesso!', 'success')
    return redirect(url_for('motochefe.listar_modelos'))

@motochefe_bp.route('/modelos/exportar')
@login_required
@requer_motochefe
def exportar_modelos():
    """Exporta modelos para Excel"""
    modelos = ModeloMoto.query.filter_by(ativo=True).all()

    data = [{
        'ID': m.id,
        'Modelo': m.nome_modelo,
        'Descrição': m.descricao or '',
        'Potência': m.potencia_motor,
        'Autopropelido': 'Sim' if m.autopropelido else 'Não',
        'Preço Tabela': float(m.preco_tabela),
        'Criado Em': m.criado_em.strftime('%d/%m/%Y %H:%M') if m.criado_em else '',
        'Criado Por': m.criado_por or ''
    } for m in modelos]

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Modelos')

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'modelos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@motochefe_bp.route('/modelos/modelo')
@login_required
@requer_motochefe
def baixar_modelo_modelos():
    """Baixa modelo de importação para Modelos de Motos"""
    from app.motochefe.services.modelo_importacao_service import gerar_modelo_modelos

    output = gerar_modelo_modelos()
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'modelo_importacao_modelos_motos_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )

@motochefe_bp.route('/modelos/importar', methods=['POST'])
@login_required
@requer_motochefe
def importar_modelos():
    """Importa modelos de Excel"""
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('motochefe.listar_modelos'))

    file = request.files['arquivo']
    if file.filename == '':
        flash('Arquivo inválido', 'danger')
        return redirect(url_for('motochefe.listar_modelos'))

    try:
        df = pd.read_excel(file)

        # Validar colunas obrigatórias
        required_cols = ['Modelo', 'Potência', 'Preço Tabela']
        if not all(col in df.columns for col in required_cols):
            flash(f'Planilha deve conter colunas: {", ".join(required_cols)}', 'danger')
            return redirect(url_for('motochefe.listar_modelos'))

        importados = 0
        for _, row in df.iterrows():
            nome = row['Modelo']
            potencia = row['Potência']
            preco = row['Preço Tabela']

            if pd.isna(nome) or pd.isna(potencia) or pd.isna(preco):
                continue

            # Verificar se já existe
            existe = ModeloMoto.query.filter_by(nome_modelo=nome, ativo=True).first()
            if existe:
                continue

            autopropelido = False
            if 'Autopropelido' in df.columns and not pd.isna(row['Autopropelido']):
                autopropelido = str(row['Autopropelido']).strip().lower() in ['sim', 'yes', 'true', '1']

            # Converter preço brasileiro (vírgula como decimal)
            preco_convertido = converter_valor_brasileiro(str(preco))

            modelo = ModeloMoto(
                nome_modelo=nome,
                descricao=row.get('Descrição') if 'Descrição' in df.columns else None,
                potencia_motor=potencia,
                autopropelido=autopropelido,
                preco_tabela=Decimal(str(preco_convertido)),
                criado_por=current_user.nome
            )
            db.session.add(modelo)
            importados += 1

        db.session.commit()
        flash(f'{importados} modelos importados com sucesso!', 'success')

    except Exception as e:
        flash(f'Erro ao importar: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_modelos'))

# ===== MOTO (CHASSI) =====

@motochefe_bp.route('/motos')
@login_required
@requer_motochefe
def listar_motos():
    """Lista motos (chassi)"""
    # Filtros opcionais
    status = request.args.get('status')
    modelo_id = request.args.get('modelo_id', type=int)

    query = Moto.query.filter_by(ativo=True)

    if status:
        query = query.filter_by(status=status)
    if modelo_id:
        query = query.filter_by(modelo_id=modelo_id)

    motos = query.order_by(Moto.data_entrada.desc()).all()

    # Buscar modelos para filtro
    modelos = ModeloMoto.query.filter_by(ativo=True).order_by(ModeloMoto.nome_modelo).all()

    # Estatísticas
    total_motos = len(motos)
    disponiveis = sum(1 for m in motos if m.status == 'DISPONIVEL')
    reservadas = sum(1 for m in motos if m.status == 'RESERVADA')
    vendidas = sum(1 for m in motos if m.status == 'VENDIDA')

    return render_template('motochefe/produtos/motos/listar.html',
                         motos=motos,
                         modelos=modelos,
                         total_motos=total_motos,
                         disponiveis=disponiveis,
                         reservadas=reservadas,
                         vendidas=vendidas,
                         status_filtro=status,
                         modelo_filtro=modelo_id)

@motochefe_bp.route('/motos/adicionar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def adicionar_moto():
    """Adiciona nova moto (chassi único)"""
    if request.method == 'POST':
        chassi = request.form.get('numero_chassi')
        motor = request.form.get('numero_motor')
        modelo_id = request.form.get('modelo_id')

        if not all([chassi, motor, modelo_id]):
            flash('Chassi, motor e modelo são obrigatórios', 'danger')
            return redirect(url_for('motochefe.adicionar_moto'))

        # Verificar duplicidade de chassi
        existe_chassi = Moto.query.filter_by(numero_chassi=chassi).first()
        if existe_chassi:
            flash('Chassi já cadastrado', 'warning')
            return redirect(url_for('motochefe.listar_motos'))

        # Verificar duplicidade de motor
        existe_motor = Moto.query.filter_by(numero_motor=motor).first()
        if existe_motor:
            flash('Motor já cadastrado', 'warning')
            return redirect(url_for('motochefe.listar_motos'))

        moto = Moto(
            numero_chassi=chassi,
            numero_motor=motor,
            modelo_id=int(modelo_id),
            cor=request.form.get('cor'),
            ano_fabricacao=int(request.form.get('ano_fabricacao')) if request.form.get('ano_fabricacao') else None,
            nf_entrada=request.form.get('nf_entrada'),
            data_nf_entrada=request.form.get('data_nf_entrada'),
            data_entrada=request.form.get('data_entrada') or date.today(),
            fornecedor=request.form.get('fornecedor'),
            custo_aquisicao=Decimal(request.form.get('custo_aquisicao')),
            pallet=request.form.get('pallet'),
            criado_por=current_user.nome
        )

        db.session.add(moto)
        db.session.commit()

        flash(f'Moto chassi "{chassi}" cadastrada com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_motos'))

    # Buscar modelos para o form
    modelos = ModeloMoto.query.filter_by(ativo=True).order_by(ModeloMoto.nome_modelo).all()
    return render_template('motochefe/produtos/motos/form.html', moto=None, modelos=modelos)

@motochefe_bp.route('/motos/<string:chassi>/editar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def editar_moto(chassi):
    """Edita moto existente"""
    moto = Moto.query.get_or_404(chassi)

    if request.method == 'POST':
        # Não permitir alterar chassi (é PK)
        moto.numero_motor = request.form.get('numero_motor')
        moto.modelo_id = int(request.form.get('modelo_id'))
        moto.cor = request.form.get('cor')
        moto.ano_fabricacao = int(request.form.get('ano_fabricacao')) if request.form.get('ano_fabricacao') else None
        moto.nf_entrada = request.form.get('nf_entrada')
        moto.data_nf_entrada = request.form.get('data_nf_entrada')
        moto.data_entrada = request.form.get('data_entrada')
        moto.fornecedor = request.form.get('fornecedor')
        moto.custo_aquisicao = Decimal(request.form.get('custo_aquisicao'))
        moto.pallet = request.form.get('pallet')
        moto.status = request.form.get('status')
        moto.atualizado_por = current_user.nome

        db.session.commit()
        flash('Moto atualizada com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_motos'))

    modelos = ModeloMoto.query.filter_by(ativo=True).order_by(ModeloMoto.nome_modelo).all()
    return render_template('motochefe/produtos/motos/form.html', moto=moto, modelos=modelos)

@motochefe_bp.route('/motos/<string:chassi>/remover', methods=['POST'])
@login_required
@requer_motochefe
def remover_moto(chassi):
    """Remove (desativa) moto"""
    moto = Moto.query.get_or_404(chassi)

    if moto.status == 'VENDIDA':
        flash('Não é possível remover moto já vendida', 'warning')
        return redirect(url_for('motochefe.listar_motos'))

    if moto.reservado:
        flash('Não é possível remover moto reservada. Cancele a reserva primeiro.', 'warning')
        return redirect(url_for('motochefe.listar_motos'))

    moto.ativo = False
    moto.atualizado_por = current_user.nome
    db.session.commit()

    flash('Moto removida com sucesso!', 'success')
    return redirect(url_for('motochefe.listar_motos'))

@motochefe_bp.route('/motos/exportar')
@login_required
@requer_motochefe
def exportar_motos():
    """Exporta motos para Excel"""
    motos = Moto.query.filter_by(ativo=True).order_by(Moto.data_entrada.desc()).all()

    data = [{
        'Chassi': m.numero_chassi,
        'Motor': m.numero_motor,
        'Modelo': m.modelo.nome_modelo,
        'Cor': m.cor,
        'Ano': m.ano_fabricacao or '',
        'NF Entrada': m.nf_entrada,
        'Data NF': m.data_nf_entrada.strftime('%d/%m/%Y') if m.data_nf_entrada else '',
        'Data Entrada': m.data_entrada.strftime('%d/%m/%Y') if m.data_entrada else '',
        'Fornecedor': m.fornecedor,
        'Custo': float(m.custo_aquisicao),
        'Pallet': m.pallet or '',
        'Status': m.status,
        'Reservado': 'Sim' if m.reservado else 'Não',
        'Criado Em': m.criado_em.strftime('%d/%m/%Y %H:%M') if m.criado_em else ''
    } for m in motos]

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Motos')

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'motos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@motochefe_bp.route('/motos/modelo')
@login_required
@requer_motochefe
def baixar_modelo_motos():
    """Baixa modelo de importação para Motos (Chassi)"""
    from app.motochefe.services.modelo_importacao_service import gerar_modelo_motos

    output = gerar_modelo_motos()
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'modelo_importacao_motos_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )

@motochefe_bp.route('/motos/importar', methods=['POST'])
@login_required
@requer_motochefe
def importar_motos():
    """Importa motos de Excel"""
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('motochefe.listar_motos'))

    file = request.files['arquivo']
    if file.filename == '':
        flash('Arquivo inválido', 'danger')
        return redirect(url_for('motochefe.listar_motos'))

    try:
        df = pd.read_excel(file)

        # Validar colunas obrigatórias
        required_cols = ['Chassi', 'Motor', 'Modelo', 'Cor', 'NF Entrada', 'Fornecedor', 'Custo']
        if not all(col in df.columns for col in required_cols):
            flash(f'Planilha deve conter colunas: {", ".join(required_cols)}', 'danger')
            return redirect(url_for('motochefe.listar_motos'))

        importados = 0
        erros = []

        for idx, row in df.iterrows():
            chassi = row['Chassi']
            motor = row['Motor']
            modelo_nome = row['Modelo']

            if pd.isna(chassi) or pd.isna(motor) or pd.isna(modelo_nome):
                continue

            # Verificar duplicidade
            existe = Moto.query.filter_by(numero_chassi=chassi).first()
            if existe:
                erros.append(f'Linha {idx+2}: Chassi {chassi} já existe')
                continue

            # Buscar modelo
            modelo = ModeloMoto.query.filter_by(nome_modelo=modelo_nome, ativo=True).first()
            if not modelo:
                erros.append(f'Linha {idx+2}: Modelo "{modelo_nome}" não encontrado')
                continue

            # Converter custo brasileiro (vírgula como decimal)
            custo_convertido = converter_valor_brasileiro(str(row['Custo']))

            moto = Moto(
                numero_chassi=str(chassi),
                numero_motor=str(motor),
                modelo_id=modelo.id,
                cor=str(row['Cor']),
                ano_fabricacao=int(row['Ano']) if 'Ano' in df.columns and not pd.isna(row['Ano']) else None,
                nf_entrada=str(row['NF Entrada']),
                data_nf_entrada=pd.to_datetime(row['Data NF']).date() if 'Data NF' in df.columns and not pd.isna(row['Data NF']) else date.today(),
                data_entrada=pd.to_datetime(row['Data Entrada']).date() if 'Data Entrada' in df.columns and not pd.isna(row['Data Entrada']) else date.today(),
                fornecedor=str(row['Fornecedor']),
                custo_aquisicao=Decimal(str(custo_convertido)),
                pallet=str(row['Pallet']) if 'Pallet' in df.columns and not pd.isna(row['Pallet']) else None,
                criado_por=current_user.nome
            )
            db.session.add(moto)
            importados += 1

        db.session.commit()

        if erros:
            flash(f'{importados} motos importadas. Erros: {"; ".join(erros[:5])}', 'warning')
        else:
            flash(f'{importados} motos importadas com sucesso!', 'success')

    except Exception as e:
        flash(f'Erro ao importar: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_motos'))

@motochefe_bp.route('/motos/api/disponiveis')
@login_required
@requer_motochefe
def api_motos_disponiveis():
    """API JSON: retorna motos disponíveis por modelo"""
    modelo_id = request.args.get('modelo_id', type=int)

    if not modelo_id:
        return jsonify([])

    motos = Moto.query.filter_by(
        modelo_id=modelo_id,
        status='DISPONIVEL',
        reservado=False,
        ativo=True
    ).order_by(Moto.data_entrada.asc()).all()  # FIFO

    return jsonify([{
        'numero_chassi': m.numero_chassi,
        'numero_motor': m.numero_motor,
        'cor': m.cor,
        'data_entrada': m.data_entrada.strftime('%d/%m/%Y'),
        'pallet': m.pallet
    } for m in motos])

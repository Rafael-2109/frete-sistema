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


def _ativar_motos_rejeitadas(nome_modelo, modelo_id):
    """
    Ativa motos que foram rejeitadas (ativo=False) por falta do modelo

    Args:
        nome_modelo (str): Nome do modelo recém-cadastrado
        modelo_id (int): ID do modelo recém-cadastrado

    Returns:
        int: Quantidade de motos ativadas
    """
    motos_inativas = Moto.query.filter_by(
        ativo=False,
        modelo_rejeitado=nome_modelo
    ).all()

    qtd_ativadas = 0
    for moto in motos_inativas:
        moto.modelo_id = modelo_id  # Atualiza para o modelo correto
        moto.ativo = True  # Ativa a moto
        moto.atualizado_por = 'Sistema (Ativação Automática)'
        qtd_ativadas += 1

    return qtd_ativadas

@motochefe_bp.route('/modelos')
@login_required
@requer_motochefe
def listar_modelos():
    """Lista modelos de motos com paginação"""
    page = request.args.get('page', 1, type=int)
    per_page = 100

    paginacao = ModeloMoto.query.filter_by(ativo=True)\
        .order_by(ModeloMoto.nome_modelo)\
        .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('motochefe/produtos/modelos/listar.html',
                         modelos=paginacao.items,
                         paginacao=paginacao)

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
        db.session.flush()  # Garante que modelo tem ID antes de ativar motos

        # Ativar motos rejeitadas que esperavam este modelo
        motos_ativadas = _ativar_motos_rejeitadas(nome, modelo.id)

        db.session.commit()

        mensagem = f'Modelo "{nome}" cadastrado com sucesso!'
        if motos_ativadas > 0:
            mensagem += f' | {motos_ativadas} motos inativas foram ativadas automaticamente'
        flash(mensagem, 'success')
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
        atualizados = 0

        for _, row in df.iterrows():
            nome = row['Modelo']
            potencia = row['Potência']
            preco = row['Preço Tabela']

            if pd.isna(nome) or pd.isna(potencia) or pd.isna(preco):
                continue

            # Processar autopropelido
            autopropelido = False
            if 'Autopropelido' in df.columns and not pd.isna(row['Autopropelido']):
                autopropelido = str(row['Autopropelido']).strip().lower() in ['sim', 'yes', 'true', '1']

            # Converter preço brasileiro (vírgula como decimal)
            preco_convertido = converter_valor_brasileiro(str(preco))
            descricao = row.get('Descrição') if 'Descrição' in df.columns else None

            # Verificar se já existe
            existe = ModeloMoto.query.filter_by(nome_modelo=nome, ativo=True).first()

            if existe:
                # ✅ ATUALIZAR modelo existente com todos os campos
                existe.potencia_motor = potencia
                existe.preco_tabela = Decimal(str(preco_convertido))
                existe.descricao = descricao
                existe.autopropelido = autopropelido
                existe.atualizado_por = current_user.nome
                db.session.flush()
                atualizados += 1
            else:
                # ✅ CRIAR novo modelo
                modelo = ModeloMoto(
                    nome_modelo=nome,
                    descricao=descricao,
                    potencia_motor=potencia,
                    autopropelido=autopropelido,
                    preco_tabela=Decimal(str(preco_convertido)),
                    criado_por=current_user.nome
                )
                db.session.add(modelo)
                db.session.flush()  # Garante que modelo tem ID

                # Ativar motos rejeitadas que esperavam este modelo
                _ativar_motos_rejeitadas(nome, modelo.id)

                importados += 1

        db.session.commit()

        # Verificar quantas motos foram ativadas
        motos_ativadas = Moto.query.filter_by(
            atualizado_por='Sistema (Ativação Automática)',
            ativo=True
        ).count()

        # Montar mensagem de feedback
        partes_mensagem = []
        if importados > 0:
            partes_mensagem.append(f'{importados} modelo(s) novo(s) criado(s)')
        if atualizados > 0:
            partes_mensagem.append(f'{atualizados} modelo(s) atualizado(s)')
        if motos_ativadas > 0:
            partes_mensagem.append(f'{motos_ativadas} moto(s) inativa(s) ativada(s) automaticamente')

        mensagem = ' | '.join(partes_mensagem) if partes_mensagem else 'Nenhum modelo foi importado'
        flash(mensagem, 'success')

    except Exception as e:
        flash(f'Erro ao importar: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_modelos'))

# ===== MOTO (CHASSI) =====

@motochefe_bp.route('/motos')
@login_required
@requer_motochefe
def listar_motos():
    """Lista motos (chassi) - Com filtro de inativas e paginação"""
    # Filtros opcionais
    status = request.args.get('status')
    modelo_id = request.args.get('modelo_id', type=int)
    mostrar_inativas = request.args.get('inativas', type=int, default=0)  # 0=ativas, 1=inativas
    page = request.args.get('page', 1, type=int)
    per_page = 100

    # Filtro base: ativo ou inativo
    if mostrar_inativas == 1:
        query = Moto.query.filter_by(ativo=False)
    else:
        query = Moto.query.filter_by(ativo=True)

    if status:
        query = query.filter_by(status=status)
    if modelo_id:
        query = query.filter_by(modelo_id=modelo_id)

    paginacao = query.order_by(Moto.data_entrada.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    # Buscar modelos para filtro
    modelos = ModeloMoto.query.filter_by(ativo=True).order_by(ModeloMoto.nome_modelo).all()

    # Estatísticas (calculadas ANTES da paginação)
    query_stats = Moto.query.filter_by(ativo=(False if mostrar_inativas == 1 else True))
    if status:
        query_stats = query_stats.filter_by(status=status)
    if modelo_id:
        query_stats = query_stats.filter_by(modelo_id=modelo_id)

    motos_stats = query_stats.all()
    total_motos = len(motos_stats)
    disponiveis = sum(1 for m in motos_stats if m.status == 'DISPONIVEL')
    reservadas = sum(1 for m in motos_stats if m.status == 'RESERVADA')
    vendidas = sum(1 for m in motos_stats if m.status == 'VENDIDA')
    inativas = Moto.query.filter_by(ativo=False).count()  # Total de inativas

    return render_template('motochefe/produtos/motos/listar.html',
                         motos=paginacao.items,
                         paginacao=paginacao,
                         modelos=modelos,
                         total_motos=total_motos,
                         disponiveis=disponiveis,
                         reservadas=reservadas,
                         vendidas=vendidas,
                         inativas=inativas,
                         status_filtro=status,
                         modelo_filtro=modelo_id,
                         mostrar_inativas=mostrar_inativas)

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

@motochefe_bp.route('/motos/exportar-inativas')
@login_required
@requer_motochefe
def exportar_motos_inativas():
    """Exporta motos INATIVAS (rejeitadas por falta de modelo)"""
    motos_inativas = Moto.query.filter_by(ativo=False).order_by(Moto.data_entrada.desc()).all()

    if not motos_inativas:
        flash('Não há motos inativas para exportar', 'info')
        return redirect(url_for('motochefe.listar_motos'))

    data = [{
        'Chassi': m.numero_chassi,
        'Motor': m.numero_motor,
        'Modelo Rejeitado': m.modelo_rejeitado or 'N/A',  # Modelo que não foi encontrado
        'Cor': m.cor,
        'Ano': m.ano_fabricacao or '',
        'NF Entrada': m.nf_entrada,
        'Data NF': m.data_nf_entrada.strftime('%d/%m/%Y') if m.data_nf_entrada else '',
        'Data Entrada': m.data_entrada.strftime('%d/%m/%Y') if m.data_entrada else '',
        'Fornecedor': m.fornecedor,
        'Custo': float(m.custo_aquisicao),
        'Pallet': m.pallet or '',
        'Criado Em': m.criado_em.strftime('%d/%m/%Y %H:%M') if m.criado_em else ''
    } for m in motos_inativas]

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Motos Inativas')

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'motos_INATIVAS_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
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
    """Importa motos de Excel - Salva rejeitadas como inativas"""
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

        # Buscar ou criar modelo placeholder para motos rejeitadas
        modelo_placeholder = ModeloMoto.query.filter_by(nome_modelo='MODELO_NAO_ENCONTRADO').first()
        if not modelo_placeholder:
            modelo_placeholder = ModeloMoto(
                nome_modelo='MODELO_NAO_ENCONTRADO',
                descricao='Placeholder para motos importadas sem modelo cadastrado',
                potencia_motor='N/A',
                autopropelido=False,
                preco_tabela=Decimal('0.00'),
                criado_por='Sistema',
                ativo=False  # Modelo inativo, apenas para referência técnica
            )
            db.session.add(modelo_placeholder)
            db.session.flush()

        importados = 0
        rejeitados = 0
        erros = []

        for idx, row in df.iterrows():
            chassi_raw = row['Chassi']
            motor = row.get('Motor')  # Agora é opcional
            modelo_nome = row['Modelo']

            # Chassi e Modelo são obrigatórios, Motor é opcional
            if pd.isna(chassi_raw) or pd.isna(modelo_nome):
                continue

            # ✅ LIMPAR E VALIDAR CHASSI
            chassi = str(chassi_raw).strip().upper()  # Remove espaços e converte para maiúscula

            # Validar tamanho máximo (VARCHAR(30) no banco)
            if len(chassi) > 30:
                erros.append(f'Linha {idx+2}: Chassi "{chassi}" muito longo ({len(chassi)} caracteres, máximo 30).')
                continue

            # Verificar duplicidade de chassi
            existe = Moto.query.filter_by(numero_chassi=chassi).first()
            if existe:
                erros.append(f'Linha {idx+2}: Chassi {chassi} já existe')
                continue

            # Verificar duplicidade de motor (se preenchido)
            if not pd.isna(motor):
                motor_existe = Moto.query.filter_by(numero_motor=str(motor)).first()
                if motor_existe:
                    erros.append(f'Linha {idx+2}: Motor {motor} já existe')
                    continue

            # Buscar modelo (case-insensitive)
            from sqlalchemy import func
            modelo = ModeloMoto.query.filter(
                func.upper(ModeloMoto.nome_modelo) == str(modelo_nome).strip().upper(),
                ModeloMoto.ativo == True
            ).first()

            # Converter custo brasileiro (vírgula como decimal)
            custo_convertido = converter_valor_brasileiro(str(row['Custo']))

            if not modelo:
                # MODELO NÃO ENCONTRADO: Salvar moto como INATIVA
                moto = Moto(
                    numero_chassi=chassi,  # ✅ Já limpo e validado
                    numero_motor=str(motor).strip() if not pd.isna(motor) else None,  # Nullable
                    modelo_id=modelo_placeholder.id,  # Usa placeholder
                    modelo_rejeitado=str(modelo_nome),  # Guarda nome do modelo não encontrado
                    cor=str(row['Cor']),
                    ano_fabricacao=int(row['Ano']) if 'Ano' in df.columns and not pd.isna(row['Ano']) else None,
                    nf_entrada=str(row['NF Entrada']),
                    data_nf_entrada=pd.to_datetime(row['Data NF']).date() if 'Data NF' in df.columns and not pd.isna(row['Data NF']) else date.today(),
                    data_entrada=pd.to_datetime(row['Data Entrada']).date() if 'Data Entrada' in df.columns and not pd.isna(row['Data Entrada']) else date.today(),
                    fornecedor=str(row['Fornecedor']),
                    custo_aquisicao=Decimal(str(custo_convertido)),
                    pallet=str(row['Pallet']) if 'Pallet' in df.columns and not pd.isna(row['Pallet']) else None,
                    ativo=False,  # MARCA COMO INATIVA
                    criado_por=current_user.nome
                )
                db.session.add(moto)
                rejeitados += 1
            else:
                # MODELO ENCONTRADO: Salvar moto normalmente
                moto = Moto(
                    numero_chassi=chassi,  # ✅ Já limpo e validado
                    numero_motor=str(motor).strip() if not pd.isna(motor) else None,  # Nullable
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

        # Mensagem de retorno
        mensagem = f'{importados} motos importadas com sucesso'
        if rejeitados > 0:
            mensagem += f' | {rejeitados} motos salvas como INATIVAS (modelo não encontrado)'
        if erros:
            mensagem += f' | Erros: {"; ".join(erros[:5])}'
            flash(mensagem, 'warning')
        else:
            flash(mensagem, 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao importar: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_motos'))

@motochefe_bp.route('/motos/api/agrupamento')
@login_required
@requer_motochefe
def api_motos_agrupamento():
    """API: Retorna motos agrupadas por modelo/cor/potência com filtros em tempo real"""
    from collections import defaultdict

    # Filtros da query string
    autopropelido_sim = request.args.get('autopropelido_sim', 'true') == 'true'
    autopropelido_nao = request.args.get('autopropelido_nao', 'true') == 'true'
    status_filtro = request.args.get('status', '')  # DISPONIVEL, RESERVADA, VENDIDA ou vazio (todos)
    modelo_filtro = request.args.get('modelo', '')
    cor_filtro = request.args.get('cor', '')
    potencia_filtro = request.args.get('potencia', '')

    # Query base: apenas motos ativas
    query = Moto.query.filter_by(ativo=True)

    # Filtro de status
    if status_filtro:
        query = query.filter_by(status=status_filtro)

    # Filtro de autopropelido
    autopropelido_valores = []
    if autopropelido_sim:
        autopropelido_valores.append(True)
    if autopropelido_nao:
        autopropelido_valores.append(False)

    if autopropelido_valores:
        # Filtrar por modelos que são ou não autopropelidos
        modelos_ids = [m.id for m in ModeloMoto.query.filter(
            ModeloMoto.autopropelido.in_(autopropelido_valores),
            ModeloMoto.ativo == True
        ).all()]
        query = query.filter(Moto.modelo_id.in_(modelos_ids))

    # Filtro de modelo
    if modelo_filtro:
        modelo = ModeloMoto.query.filter_by(nome_modelo=modelo_filtro, ativo=True).first()
        if modelo:
            query = query.filter_by(modelo_id=modelo.id)

    # Filtro de cor
    if cor_filtro:
        query = query.filter_by(cor=cor_filtro)

    # Filtro de potência
    if potencia_filtro:
        modelos_potencia = ModeloMoto.query.filter_by(potencia_motor=potencia_filtro, ativo=True).all()
        if modelos_potencia:
            modelos_ids = [m.id for m in modelos_potencia]
            query = query.filter(Moto.modelo_id.in_(modelos_ids))

    motos = query.all()

    # Agrupar dados
    agrupamento = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for moto in motos:
        modelo_nome = moto.modelo.nome_modelo
        potencia = moto.modelo.potencia_motor
        cor = moto.cor

        agrupamento[modelo_nome][cor][potencia].append({
            'chassi': moto.numero_chassi,
            'motor': moto.numero_motor,
            'status': moto.status,
            'reservado': moto.reservado,
            'ano': moto.ano_fabricacao,
            'nf': moto.nf_entrada
        })

    # Converter para estrutura serializable
    resultado = []
    for modelo, cores in sorted(agrupamento.items()):
        modelo_obj = ModeloMoto.query.filter_by(nome_modelo=modelo, ativo=True).first()

        cores_data = []
        total_modelo = 0

        for cor, potencias in sorted(cores.items()):
            potencias_data = []
            total_cor = 0

            for potencia, motos_lista in sorted(potencias.items()):
                qtd = len(motos_lista)
                total_cor += qtd
                total_modelo += qtd

                potencias_data.append({
                    'potencia': potencia,
                    'quantidade': qtd,
                    'motos': motos_lista
                })

            cores_data.append({
                'cor': cor,
                'quantidade': total_cor,
                'potencias': potencias_data
            })

        resultado.append({
            'modelo': modelo,
            'autopropelido': modelo_obj.autopropelido if modelo_obj else False,
            'quantidade': total_modelo,
            'cores': cores_data
        })

    return jsonify(resultado)

@motochefe_bp.route('/motos/api/opcoes-filtros')
@login_required
@requer_motochefe
def api_opcoes_filtros():
    """API: Retorna opções disponíveis para os filtros (modelos, cores, potências)"""
    from sqlalchemy import distinct

    # Buscar apenas de motos ativas
    motos_ativas = Moto.query.filter_by(ativo=True).all()

    # Extrair valores únicos
    modelos = sorted(list(set([m.modelo.nome_modelo for m in motos_ativas])))
    cores = sorted(list(set([m.cor for m in motos_ativas])))
    potencias = sorted(list(set([m.modelo.potencia_motor for m in motos_ativas])))

    return jsonify({
        'modelos': modelos,
        'cores': cores,
        'potencias': potencias
    })

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

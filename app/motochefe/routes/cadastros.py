"""
Rotas de Cadastros Básicos - MotoChefe
CRUD completo para: Equipes, Vendedores, Transportadoras, Clientes
"""
from flask import render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required, current_user
from functools import wraps
import pandas as pd
from io import BytesIO
from datetime import datetime
import requests
import re

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.models import (
    EquipeVendasMoto, VendedorMoto, TransportadoraMoto, ClienteMoto
)

# ============================================================
# DASHBOARD MOTOCHEFE
# ============================================================

@motochefe_bp.route('/')
@motochefe_bp.route('/dashboard')
@login_required
def dashboard_motochefe():
    """Dashboard principal do sistema MotoChefe"""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

    if not current_user.pode_acessar_motochefe():
        if current_user.pode_acessar_logistica():
            return redirect(url_for('main.dashboard'))
        else:
            flash('Você não tem permissão para acessar nenhum sistema.', 'danger')
            return redirect(url_for('auth.login'))

    return render_template('motochefe/dashboard_motochefe.html')

# ============================================================
# DECORATOR PARA VERIFICAR ACESSO AO MOTOCHEFE
# ============================================================

def requer_motochefe(f):
    """Decorator para proteger rotas do sistema MotoChefe"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Você precisa estar autenticado.', 'danger')
            return redirect(url_for('auth.login'))

        if not current_user.pode_acessar_motochefe():
            flash('Acesso negado ao sistema MotoChefe.', 'danger')
            # Redirecionar baseado em permissões
            if current_user.pode_acessar_logistica():
                return redirect(url_for('main.dashboard'))
            else:
                return redirect(url_for('auth.login'))

        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# EQUIPES DE VENDAS
# ============================================================

@motochefe_bp.route('/equipes')
@login_required
@requer_motochefe
def listar_equipes():
    """Lista todas as equipes de vendas com paginação"""
    page = request.args.get('page', 1, type=int)
    per_page = 100

    paginacao = EquipeVendasMoto.query.filter_by(ativo=True)\
        .order_by(EquipeVendasMoto.equipe_vendas)\
        .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('motochefe/cadastros/equipes/listar.html',
                         equipes=paginacao.items,
                         paginacao=paginacao)

@motochefe_bp.route('/equipes/adicionar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def adicionar_equipe():
    """Adiciona nova equipe com configurações de movimentação e comissão"""
    if request.method == 'POST':
        nome = request.form.get('equipe_vendas')

        if not nome:
            flash('Nome da equipe é obrigatório', 'danger')
            return redirect(url_for('motochefe.adicionar_equipe'))

        # Verificar duplicidade
        existe = EquipeVendasMoto.query.filter_by(equipe_vendas=nome, ativo=True).first()
        if existe:
            flash('Equipe já cadastrada', 'warning')
            return redirect(url_for('motochefe.listar_equipes'))

        # Capturar novos campos
        from decimal import Decimal

        # Movimentação
        responsavel_movimentacao = request.form.get('responsavel_movimentacao') or None
        custo_movimentacao = Decimal(request.form.get('custo_movimentacao', '0') or '0')
        incluir_custo_movimentacao = bool(request.form.get('incluir_custo_movimentacao'))

        # Precificação
        tipo_precificacao = request.form.get('tipo_precificacao', 'TABELA')
        markup = Decimal(request.form.get('markup', '0') or '0')

        # Comissão
        tipo_comissao = request.form.get('tipo_comissao', 'FIXA_EXCEDENTE')
        valor_comissao_fixa = Decimal(request.form.get('valor_comissao_fixa', '0') or '0')
        percentual_comissao = Decimal(request.form.get('percentual_comissao', '0') or '0')
        comissao_rateada = bool(request.form.get('comissao_rateada'))

        # Montagem
        permitir_montagem = bool(request.form.get('permitir_montagem'))

        # Prazo e Parcelamento
        permitir_prazo = bool(request.form.get('permitir_prazo'))
        permitir_parcelamento = bool(request.form.get('permitir_parcelamento'))

        equipe = EquipeVendasMoto(
            equipe_vendas=nome,
            # Movimentação
            responsavel_movimentacao=responsavel_movimentacao,
            custo_movimentacao=custo_movimentacao,
            incluir_custo_movimentacao=incluir_custo_movimentacao,
            # Precificação
            tipo_precificacao=tipo_precificacao,
            markup=markup,
            # Comissão
            tipo_comissao=tipo_comissao,
            valor_comissao_fixa=valor_comissao_fixa,
            percentual_comissao=percentual_comissao,
            comissao_rateada=comissao_rateada,
            # Montagem
            permitir_montagem=permitir_montagem,
            # Prazo e Parcelamento
            permitir_prazo=permitir_prazo,
            permitir_parcelamento=permitir_parcelamento,
            criado_por=current_user.nome
        )
        db.session.add(equipe)
        db.session.commit()

        flash(f'Equipe "{nome}" cadastrada com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_equipes'))

    return render_template('motochefe/cadastros/equipes/form.html', equipe=None)

@motochefe_bp.route('/equipes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def editar_equipe(id):
    """Edita equipe existente com configurações"""
    equipe = EquipeVendasMoto.query.get_or_404(id)

    if request.method == 'POST':
        from decimal import Decimal

        equipe.equipe_vendas = request.form.get('equipe_vendas')

        # Movimentação
        equipe.responsavel_movimentacao = request.form.get('responsavel_movimentacao') or None
        equipe.custo_movimentacao = Decimal(request.form.get('custo_movimentacao', '0') or '0')
        equipe.incluir_custo_movimentacao = bool(request.form.get('incluir_custo_movimentacao'))

        # Precificação
        equipe.tipo_precificacao = request.form.get('tipo_precificacao', 'TABELA')
        equipe.markup = Decimal(request.form.get('markup', '0') or '0')

        # Comissão
        equipe.tipo_comissao = request.form.get('tipo_comissao', 'FIXA_EXCEDENTE')
        equipe.valor_comissao_fixa = Decimal(request.form.get('valor_comissao_fixa', '0') or '0')
        equipe.percentual_comissao = Decimal(request.form.get('percentual_comissao', '0') or '0')
        equipe.comissao_rateada = bool(request.form.get('comissao_rateada'))

        # Montagem
        equipe.permitir_montagem = bool(request.form.get('permitir_montagem'))

        # Prazo e Parcelamento
        equipe.permitir_prazo = bool(request.form.get('permitir_prazo'))
        equipe.permitir_parcelamento = bool(request.form.get('permitir_parcelamento'))

        equipe.atualizado_por = current_user.nome

        db.session.commit()

        flash('Equipe atualizada com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_equipes'))

    # GET - Buscar modelos para a sub-tabela de preços
    from app.motochefe.models import ModeloMoto
    modelos = ModeloMoto.query.filter_by(ativo=True).order_by(ModeloMoto.nome_modelo).all()

    return render_template('motochefe/cadastros/equipes/form.html', equipe=equipe, modelos=modelos)

@motochefe_bp.route('/equipes/<int:id>/remover', methods=['POST'])
@login_required
@requer_motochefe
def remover_equipe(id):
    """Remove (desativa) equipe"""
    equipe = EquipeVendasMoto.query.get_or_404(id)
    equipe.ativo = False
    equipe.atualizado_por = current_user.nome
    db.session.commit()

    flash('Equipe removida com sucesso!', 'success')
    return redirect(url_for('motochefe.listar_equipes'))

# ============================================================
# TABELA DE PREÇOS POR EQUIPE
# ============================================================

@motochefe_bp.route('/equipes/<int:equipe_id>/precos/adicionar', methods=['POST'])
@login_required
@requer_motochefe
def adicionar_preco_equipe(equipe_id):
    """Adiciona preço específico de um modelo para uma equipe"""
    from app.motochefe.models import TabelaPrecoEquipe, ModeloMoto
    from decimal import Decimal

    equipe = EquipeVendasMoto.query.get_or_404(equipe_id)

    modelo_id = request.form.get('modelo_id')
    preco_venda = request.form.get('preco_venda')

    if not modelo_id or not preco_venda:
        flash('Modelo e Preço são obrigatórios', 'danger')
        return redirect(url_for('motochefe.editar_equipe', id=equipe_id))

    # Verificar se modelo existe
    modelo = ModeloMoto.query.get(int(modelo_id))
    if not modelo:
        flash('Modelo não encontrado', 'danger')
        return redirect(url_for('motochefe.editar_equipe', id=equipe_id))

    # Verificar duplicidade
    existe = TabelaPrecoEquipe.query.filter_by(
        equipe_vendas_id=equipe_id,
        modelo_id=int(modelo_id),
        ativo=True
    ).first()

    if existe:
        flash(f'Preço para {modelo.nome_modelo} já cadastrado nesta equipe', 'warning')
        return redirect(url_for('motochefe.editar_equipe', id=equipe_id))

    # Criar registro
    tabela_preco = TabelaPrecoEquipe(
        equipe_vendas_id=equipe_id,
        modelo_id=int(modelo_id),
        preco_venda=Decimal(preco_venda),
        criado_por=current_user.nome
    )

    db.session.add(tabela_preco)
    db.session.commit()

    flash(f'Preço para {modelo.nome_modelo} adicionado com sucesso!', 'success')
    return redirect(url_for('motochefe.editar_equipe', id=equipe_id))


@motochefe_bp.route('/equipes/precos/<int:preco_id>/editar', methods=['POST'])
@login_required
@requer_motochefe
def editar_preco_equipe(preco_id):
    """Edita preço específico de um modelo para uma equipe"""
    from app.motochefe.models import TabelaPrecoEquipe
    from decimal import Decimal

    tabela_preco = TabelaPrecoEquipe.query.get_or_404(preco_id)

    preco_venda = request.form.get('preco_venda')

    if not preco_venda:
        flash('Preço é obrigatório', 'danger')
        return redirect(url_for('motochefe.editar_equipe', id=tabela_preco.equipe_vendas_id))

    tabela_preco.preco_venda = Decimal(preco_venda)
    tabela_preco.atualizado_por = current_user.nome

    db.session.commit()

    flash('Preço atualizado com sucesso!', 'success')
    return redirect(url_for('motochefe.editar_equipe', id=tabela_preco.equipe_vendas_id))


@motochefe_bp.route('/equipes/precos/<int:preco_id>/remover', methods=['POST'])
@login_required
@requer_motochefe
def remover_preco_equipe(preco_id):
    """Remove (desativa) preço específico"""
    from app.motochefe.models import TabelaPrecoEquipe

    tabela_preco = TabelaPrecoEquipe.query.get_or_404(preco_id)
    equipe_id = tabela_preco.equipe_vendas_id

    tabela_preco.ativo = False
    tabela_preco.atualizado_por = current_user.nome

    db.session.commit()

    flash('Preço removido com sucesso!', 'success')
    return redirect(url_for('motochefe.editar_equipe', id=equipe_id))


@motochefe_bp.route('/equipes/<int:equipe_id>/gerenciar-precos')
@login_required
@requer_motochefe
def gerenciar_precos_equipe(equipe_id):
    """
    Tela de gerenciamento da tabela de preços da equipe
    Usa modelos cadastrados como esqueleto
    """
    from app.motochefe.models import TabelaPrecoEquipe, ModeloMoto

    equipe = EquipeVendasMoto.query.get_or_404(equipe_id)

    # Verificar se equipe usa tabela de preços
    if equipe.tipo_precificacao != 'TABELA':
        flash(f'Equipe "{equipe.equipe_vendas}" não usa tabela de preços (tipo: {equipe.tipo_precificacao})', 'warning')
        return redirect(url_for('motochefe.listar_equipes'))

    # Buscar todos os modelos ativos
    modelos = ModeloMoto.query.filter_by(ativo=True).order_by(ModeloMoto.nome_modelo).all()

    # Buscar preços existentes da equipe
    precos_existentes = {}
    tabelas = TabelaPrecoEquipe.query.filter_by(
        equipe_vendas_id=equipe_id,
        ativo=True
    ).all()

    for tabela in tabelas:
        precos_existentes[tabela.modelo_id] = tabela

    # Criar lista com dados combinados (modelo + preço se existir)
    dados_tabela = []
    for modelo in modelos:
        preco_cadastrado = precos_existentes.get(modelo.id)
        dados_tabela.append({
            'modelo': modelo,
            'preco_tabela': preco_cadastrado,
            'preco_venda': preco_cadastrado.preco_venda if preco_cadastrado else None,
            'tem_preco': preco_cadastrado is not None
        })

    return render_template('motochefe/cadastros/equipes/gerenciar_precos.html',
                         equipe=equipe,
                         dados_tabela=dados_tabela)


# ============================================================
# EXPORTAÇÃO/IMPORTAÇÃO DE EQUIPES
# ============================================================

@motochefe_bp.route('/equipes/exportar')
@login_required
@requer_motochefe
def exportar_equipes():
    """Exporta equipes para Excel"""
    equipes = EquipeVendasMoto.query.filter_by(ativo=True).all()

    data = [{
        'ID': e.id,
        'Equipe': e.equipe_vendas,
        'Criado Em': e.criado_em.strftime('%d/%m/%Y %H:%M') if e.criado_em else '',
        'Criado Por': e.criado_por or ''
    } for e in equipes]

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Equipes')

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'equipes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@motochefe_bp.route('/equipes/modelo')
@login_required
@requer_motochefe
def baixar_modelo_equipes():
    """Baixa modelo de importação para Equipes"""
    from app.motochefe.services.modelo_importacao_service import gerar_modelo_equipes

    output = gerar_modelo_equipes()
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'modelo_importacao_equipes_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )

@motochefe_bp.route('/equipes/importar', methods=['POST'])
@login_required
@requer_motochefe
def importar_equipes():
    """Importa equipes de Excel"""
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('motochefe.listar_equipes'))

    file = request.files['arquivo']
    if file.filename == '':
        flash('Arquivo inválido', 'danger')
        return redirect(url_for('motochefe.listar_equipes'))

    try:
        df = pd.read_excel(file)

        # Validar colunas obrigatórias
        if 'Equipe' not in df.columns:
            flash('Planilha deve conter coluna "Equipe"', 'danger')
            return redirect(url_for('motochefe.listar_equipes'))

        importados = 0
        for _, row in df.iterrows():
            nome = row['Equipe']
            if pd.isna(nome):
                continue

            # Verificar se já existe
            existe = EquipeVendasMoto.query.filter_by(equipe_vendas=nome, ativo=True).first()
            if existe:
                continue

            equipe = EquipeVendasMoto(
                equipe_vendas=nome,
                criado_por=current_user.nome
            )
            db.session.add(equipe)
            importados += 1

        db.session.commit()
        flash(f'{importados} equipes importadas com sucesso!', 'success')

    except Exception as e:
        flash(f'Erro ao importar: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_equipes'))

# ============================================================
# VENDEDORES
# ============================================================

@motochefe_bp.route('/vendedores')
@login_required
@requer_motochefe
def listar_vendedores():
    """Lista todos os vendedores com paginação"""
    page = request.args.get('page', 1, type=int)
    per_page = 100

    paginacao = VendedorMoto.query.filter_by(ativo=True)\
        .order_by(VendedorMoto.vendedor)\
        .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('motochefe/cadastros/vendedores/listar.html',
                         vendedores=paginacao.items,
                         paginacao=paginacao)

@motochefe_bp.route('/vendedores/adicionar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def adicionar_vendedor():
    """Adiciona novo vendedor"""
    equipes = EquipeVendasMoto.query.filter_by(ativo=True).order_by(EquipeVendasMoto.equipe_vendas).all()

    if request.method == 'POST':
        nome = request.form.get('vendedor')
        equipe_id = request.form.get('equipe_vendas_id')

        if not nome:
            flash('Nome do vendedor é obrigatório', 'danger')
            return redirect(url_for('motochefe.adicionar_vendedor'))

        # VALIDAÇÃO OBRIGATÓRIA: Equipe é obrigatória
        if not equipe_id:
            flash('Equipe de vendas é obrigatória', 'danger')
            return redirect(url_for('motochefe.adicionar_vendedor'))

        vendedor = VendedorMoto(
            vendedor=nome,
            equipe_vendas_id=int(equipe_id),
            criado_por=current_user.nome
        )
        db.session.add(vendedor)
        db.session.commit()

        flash(f'Vendedor "{nome}" cadastrado com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_vendedores'))

    return render_template('motochefe/cadastros/vendedores/form.html', vendedor=None, equipes=equipes)

@motochefe_bp.route('/vendedores/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def editar_vendedor(id):
    """Edita vendedor existente"""
    vendedor = VendedorMoto.query.get_or_404(id)
    equipes = EquipeVendasMoto.query.filter_by(ativo=True).order_by(EquipeVendasMoto.equipe_vendas).all()

    if request.method == 'POST':
        vendedor.vendedor = request.form.get('vendedor')
        equipe_id = request.form.get('equipe_vendas_id')
        vendedor.equipe_vendas_id = equipe_id if equipe_id else None
        vendedor.atualizado_por = current_user.nome
        db.session.commit()

        flash('Vendedor atualizado com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_vendedores'))

    return render_template('motochefe/cadastros/vendedores/form.html', vendedor=vendedor, equipes=equipes)

@motochefe_bp.route('/vendedores/<int:id>/remover', methods=['POST'])
@login_required
@requer_motochefe
def remover_vendedor(id):
    """Remove (desativa) vendedor"""
    vendedor = VendedorMoto.query.get_or_404(id)
    vendedor.ativo = False
    vendedor.atualizado_por = current_user.nome
    db.session.commit()

    flash('Vendedor removido com sucesso!', 'success')
    return redirect(url_for('motochefe.listar_vendedores'))

@motochefe_bp.route('/vendedores/exportar')
@login_required
@requer_motochefe
def exportar_vendedores():
    """Exporta vendedores para Excel"""
    vendedores = VendedorMoto.query.filter_by(ativo=True).all()

    data = [{
        'ID': v.id,
        'Vendedor': v.vendedor,
        'Equipe': v.equipe.equipe_vendas if v.equipe else '',
        'Criado Em': v.criado_em.strftime('%d/%m/%Y %H:%M') if v.criado_em else '',
        'Criado Por': v.criado_por or ''
    } for v in vendedores]

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Vendedores')

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'vendedores_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@motochefe_bp.route('/vendedores/modelo')
@login_required
@requer_motochefe
def baixar_modelo_vendedores():
    """Baixa modelo de importação para Vendedores"""
    from app.motochefe.services.modelo_importacao_service import gerar_modelo_vendedores

    output = gerar_modelo_vendedores()
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'modelo_importacao_vendedores_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )

@motochefe_bp.route('/vendedores/importar', methods=['POST'])
@login_required
@requer_motochefe
def importar_vendedores():
    """Importa vendedores de Excel"""
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('motochefe.listar_vendedores'))

    file = request.files['arquivo']
    if file.filename == '':
        flash('Arquivo inválido', 'danger')
        return redirect(url_for('motochefe.listar_vendedores'))

    try:
        df = pd.read_excel(file)

        # Validar colunas obrigatórias
        if 'Vendedor' not in df.columns:
            flash('Planilha deve conter coluna "Vendedor"', 'danger')
            return redirect(url_for('motochefe.listar_vendedores'))

        importados = 0
        for _, row in df.iterrows():
            nome = row['Vendedor']
            if pd.isna(nome):
                continue

            # Buscar equipe (se especificada)
            equipe_id = None
            if 'Equipe' in df.columns and not pd.isna(row['Equipe']):
                equipe = EquipeVendasMoto.query.filter_by(equipe_vendas=row['Equipe'], ativo=True).first()
                if equipe:
                    equipe_id = equipe.id

            vendedor = VendedorMoto(
                vendedor=nome,
                equipe_vendas_id=equipe_id,
                criado_por=current_user.nome
            )
            db.session.add(vendedor)
            importados += 1

        db.session.commit()
        flash(f'{importados} vendedores importados com sucesso!', 'success')

    except Exception as e:
        flash(f'Erro ao importar: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_vendedores'))

# ============================================================
# TRANSPORTADORAS
# ============================================================

@motochefe_bp.route('/transportadoras')
@login_required
@requer_motochefe
def listar_transportadoras():
    """Lista todas as transportadoras com paginação"""
    page = request.args.get('page', 1, type=int)
    per_page = 100

    paginacao = TransportadoraMoto.query.filter_by(ativo=True)\
        .order_by(TransportadoraMoto.transportadora)\
        .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('motochefe/cadastros/transportadoras/listar.html',
                         transportadoras=paginacao.items,
                         paginacao=paginacao)

@motochefe_bp.route('/transportadoras/adicionar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def adicionar_transportadora():
    """Adiciona nova transportadora"""
    if request.method == 'POST':
        nome = request.form.get('transportadora')
        cnpj = request.form.get('cnpj')
        telefone = request.form.get('telefone')

        if not nome:
            flash('Nome da transportadora é obrigatório', 'danger')
            return redirect(url_for('motochefe.adicionar_transportadora'))

        # Verificar duplicidade
        existe = TransportadoraMoto.query.filter_by(transportadora=nome, ativo=True).first()
        if existe:
            flash('Transportadora já cadastrada', 'warning')
            return redirect(url_for('motochefe.listar_transportadoras'))

        transportadora = TransportadoraMoto(
            transportadora=nome,
            cnpj=cnpj,
            telefone=telefone,
            # Dados bancários
            chave_pix=request.form.get('chave_pix'),
            banco=request.form.get('banco'),
            cod_banco=request.form.get('cod_banco'),
            agencia=request.form.get('agencia'),
            conta=request.form.get('conta'),
            criado_por=current_user.nome
        )
        db.session.add(transportadora)
        db.session.commit()

        flash(f'Transportadora "{nome}" cadastrada com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_transportadoras'))

    return render_template('motochefe/cadastros/transportadoras/form.html', transportadora=None)

@motochefe_bp.route('/transportadoras/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def editar_transportadora(id):
    """Edita transportadora existente"""
    transportadora = TransportadoraMoto.query.get_or_404(id)

    if request.method == 'POST':
        transportadora.transportadora = request.form.get('transportadora')
        transportadora.cnpj = request.form.get('cnpj')
        transportadora.telefone = request.form.get('telefone')
        # Dados bancários
        transportadora.chave_pix = request.form.get('chave_pix')
        transportadora.banco = request.form.get('banco')
        transportadora.cod_banco = request.form.get('cod_banco')
        transportadora.agencia = request.form.get('agencia')
        transportadora.conta = request.form.get('conta')
        transportadora.atualizado_por = current_user.nome
        db.session.commit()

        flash('Transportadora atualizada com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_transportadoras'))

    return render_template('motochefe/cadastros/transportadoras/form.html', transportadora=transportadora)

@motochefe_bp.route('/transportadoras/<int:id>/remover', methods=['POST'])
@login_required
@requer_motochefe
def remover_transportadora(id):
    """Remove (desativa) transportadora"""
    transportadora = TransportadoraMoto.query.get_or_404(id)
    transportadora.ativo = False
    transportadora.atualizado_por = current_user.nome
    db.session.commit()

    flash('Transportadora removida com sucesso!', 'success')
    return redirect(url_for('motochefe.listar_transportadoras'))

@motochefe_bp.route('/transportadoras/exportar')
@login_required
@requer_motochefe
def exportar_transportadoras():
    """Exporta transportadoras para Excel"""
    transportadoras = TransportadoraMoto.query.filter_by(ativo=True).all()

    data = [{
        'ID': t.id,
        'Transportadora': t.transportadora,
        'CNPJ': t.cnpj or '',
        'Telefone': t.telefone or '',
        'Criado Em': t.criado_em.strftime('%d/%m/%Y %H:%M') if t.criado_em else '',
        'Criado Por': t.criado_por or ''
    } for t in transportadoras]

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Transportadoras')

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'transportadoras_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@motochefe_bp.route('/transportadoras/modelo')
@login_required
@requer_motochefe
def baixar_modelo_transportadoras():
    """Baixa modelo de importação para Transportadoras"""
    from app.motochefe.services.modelo_importacao_service import gerar_modelo_transportadoras

    output = gerar_modelo_transportadoras()
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'modelo_importacao_transportadoras_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )

@motochefe_bp.route('/transportadoras/importar', methods=['POST'])
@login_required
@requer_motochefe
def importar_transportadoras():
    """Importa transportadoras de Excel"""
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('motochefe.listar_transportadoras'))

    file = request.files['arquivo']
    if file.filename == '':
        flash('Arquivo inválido', 'danger')
        return redirect(url_for('motochefe.listar_transportadoras'))

    try:
        df = pd.read_excel(file)

        # Validar colunas obrigatórias
        if 'Transportadora' not in df.columns:
            flash('Planilha deve conter coluna "Transportadora"', 'danger')
            return redirect(url_for('motochefe.listar_transportadoras'))

        importados = 0
        for _, row in df.iterrows():
            nome = row['Transportadora']
            if pd.isna(nome):
                continue

            # Verificar se já existe
            existe = TransportadoraMoto.query.filter_by(transportadora=nome, ativo=True).first()
            if existe:
                continue

            transportadora = TransportadoraMoto(
                transportadora=nome,
                cnpj=row.get('CNPJ') if 'CNPJ' in df.columns else None,
                telefone=row.get('Telefone') if 'Telefone' in df.columns else None,
                criado_por=current_user.nome
            )
            db.session.add(transportadora)
            importados += 1

        db.session.commit()
        flash(f'{importados} transportadoras importadas com sucesso!', 'success')

    except Exception as e:
        flash(f'Erro ao importar: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_transportadoras'))

# ============================================================
# API - CONSULTA CNPJ (ReceitaWS)
# ============================================================

@motochefe_bp.route('/api/consultar-cnpj/<cnpj>')
@login_required
@requer_motochefe
def consultar_cnpj(cnpj):
    """
    Consulta dados de CNPJ na API ReceitaWS (gratuita, sem certificado digital)
    Endpoint: https://www.receitaws.com.br/v1/cnpj/{cnpj}
    Limite: ~3 requisições por minuto por IP
    """
    try:
        # Remove caracteres não numéricos do CNPJ
        cnpj_limpo = re.sub(r'\D', '', cnpj)

        # Valida se tem 14 dígitos
        if len(cnpj_limpo) != 14:
            return jsonify({
                'success': False,
                'message': 'CNPJ deve conter 14 dígitos.'
            }), 400

        # Monta URL da API ReceitaWS
        url = f'https://www.receitaws.com.br/v1/cnpj/{cnpj_limpo}'

        # Faz requisição com timeout de 10 segundos
        response = requests.get(url, timeout=10)

        # Verifica status da resposta
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'message': f'Erro na API ReceitaWS. Status: {response.status_code}'
            }), response.status_code

        # Parse do JSON
        dados = response.json()

        # Verifica se houve erro na API (campo "status" == "ERROR")
        if dados.get('status') == 'ERROR':
            return jsonify({
                'success': False,
                'message': dados.get('message', 'CNPJ não encontrado ou inválido.')
            }), 404

        # Mapeia campos da API para os campos do modelo ClienteMoto
        dados_cliente = {
            'cliente': dados.get('nome', ''),  # Razão Social
            'endereco_cliente': dados.get('logradouro', ''),  # Logradouro completo
            'numero_cliente': dados.get('numero', ''),
            'complemento_cliente': dados.get('complemento', ''),
            'bairro_cliente': dados.get('bairro', ''),
            'cidade_cliente': dados.get('municipio', ''),
            'estado_cliente': dados.get('uf', ''),
            'cep_cliente': dados.get('cep', ''),
            'telefone_cliente': dados.get('telefone', ''),
            'email_cliente': dados.get('email', ''),
        }

        # Remove campos vazios/nulos
        dados_cliente = {k: v for k, v in dados_cliente.items() if v}

        return jsonify({
            'success': True,
            'message': 'CNPJ consultado com sucesso!',
            'dados': dados_cliente
        }), 200

    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'message': 'Timeout: A API ReceitaWS demorou muito para responder. Tente novamente.'
        }), 408

    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'message': 'Erro de conexão: Não foi possível conectar à API ReceitaWS. Verifique sua internet.'
        }), 503

    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'message': f'Erro na requisição: {str(e)}'
        }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro inesperado: {str(e)}'
        }), 500

# ============================================================
# CLIENTES
# ============================================================

@motochefe_bp.route('/clientes')
@login_required
@requer_motochefe
def listar_clientes():
    """Lista todos os clientes com paginação"""
    page = request.args.get('page', 1, type=int)
    per_page = 100

    paginacao = ClienteMoto.query.filter_by(ativo=True)\
        .order_by(ClienteMoto.cliente)\
        .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('motochefe/cadastros/clientes/listar.html',
                         clientes=paginacao.items,
                         paginacao=paginacao)

@motochefe_bp.route('/clientes/adicionar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def adicionar_cliente():
    """Adiciona novo cliente"""
    if request.method == 'POST':
        nome = request.form.get('cliente')
        cnpj = request.form.get('cnpj_cliente')
        vendedor_id = request.form.get('vendedor_id')

        # Validações obrigatórias
        if not nome or not cnpj:
            flash('Nome e CNPJ são obrigatórios', 'danger')
            return redirect(url_for('motochefe.adicionar_cliente'))

        if not vendedor_id:
            flash('Vendedor Responsável é obrigatório', 'danger')
            return redirect(url_for('motochefe.adicionar_cliente'))

        # Verificar duplicidade de CNPJ
        existe = ClienteMoto.query.filter_by(cnpj_cliente=cnpj, ativo=True).first()
        if existe:
            flash('CNPJ já cadastrado', 'warning')
            return redirect(url_for('motochefe.listar_clientes'))

        cliente = ClienteMoto(
            vendedor_id=int(vendedor_id),  # ✅ NOVO
            crossdocking=bool(request.form.get('crossdocking')),  # ✅ NOVO
            cliente=nome,
            cnpj_cliente=cnpj,
            endereco_cliente=request.form.get('endereco_cliente'),
            numero_cliente=request.form.get('numero_cliente'),
            complemento_cliente=request.form.get('complemento_cliente'),
            bairro_cliente=request.form.get('bairro_cliente'),
            cidade_cliente=request.form.get('cidade_cliente'),
            estado_cliente=request.form.get('estado_cliente'),
            cep_cliente=request.form.get('cep_cliente'),
            telefone_cliente=request.form.get('telefone_cliente'),
            email_cliente=request.form.get('email_cliente'),
            criado_por=current_user.nome
        )
        db.session.add(cliente)
        db.session.commit()

        flash(f'Cliente "{nome}" cadastrado com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_clientes'))

    # GET: Listar vendedores para o dropdown
    vendedores = VendedorMoto.query.filter_by(ativo=True).order_by(VendedorMoto.vendedor).all()
    return render_template('motochefe/cadastros/clientes/form.html', cliente=None, vendedores=vendedores)

@motochefe_bp.route('/clientes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def editar_cliente(id):
    """Edita cliente existente"""
    cliente = ClienteMoto.query.get_or_404(id)

    if request.method == 'POST':
        vendedor_id = request.form.get('vendedor_id')

        # Validação obrigatória de vendedor
        if not vendedor_id:
            flash('Vendedor Responsável é obrigatório', 'danger')
            return redirect(url_for('motochefe.editar_cliente', id=id))

        cliente.vendedor_id = int(vendedor_id)  # ✅ NOVO
        cliente.crossdocking = bool(request.form.get('crossdocking'))  # ✅ NOVO
        cliente.cliente = request.form.get('cliente')
        cliente.cnpj_cliente = request.form.get('cnpj_cliente')
        cliente.endereco_cliente = request.form.get('endereco_cliente')
        cliente.numero_cliente = request.form.get('numero_cliente')
        cliente.complemento_cliente = request.form.get('complemento_cliente')
        cliente.bairro_cliente = request.form.get('bairro_cliente')
        cliente.cidade_cliente = request.form.get('cidade_cliente')
        cliente.estado_cliente = request.form.get('estado_cliente')
        cliente.cep_cliente = request.form.get('cep_cliente')
        cliente.telefone_cliente = request.form.get('telefone_cliente')
        cliente.email_cliente = request.form.get('email_cliente')
        cliente.atualizado_por = current_user.nome
        db.session.commit()

        flash('Cliente atualizado com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_clientes'))

    # GET: Listar vendedores para o dropdown
    vendedores = VendedorMoto.query.filter_by(ativo=True).order_by(VendedorMoto.vendedor).all()
    return render_template('motochefe/cadastros/clientes/form.html', cliente=cliente, vendedores=vendedores)

@motochefe_bp.route('/clientes/<int:id>/remover', methods=['POST'])
@login_required
@requer_motochefe
def remover_cliente(id):
    """Remove (desativa) cliente"""
    cliente = ClienteMoto.query.get_or_404(id)
    cliente.ativo = False
    cliente.atualizado_por = current_user.nome
    db.session.commit()

    flash('Cliente removido com sucesso!', 'success')
    return redirect(url_for('motochefe.listar_clientes'))

@motochefe_bp.route('/clientes/exportar')
@login_required
@requer_motochefe
def exportar_clientes():
    """Exporta clientes para Excel"""
    clientes = ClienteMoto.query.filter_by(ativo=True).all()

    data = [{
        'ID': c.id,
        'Cliente': c.cliente,
        'CNPJ': c.cnpj_cliente,
        'Endereço': c.endereco_cliente or '',
        'Número': c.numero_cliente or '',
        'Complemento': c.complemento_cliente or '',
        'Bairro': c.bairro_cliente or '',
        'Cidade': c.cidade_cliente or '',
        'Estado': c.estado_cliente or '',
        'CEP': c.cep_cliente or '',
        'Telefone': c.telefone_cliente or '',
        'Email': c.email_cliente or '',
        'Criado Em': c.criado_em.strftime('%d/%m/%Y %H:%M') if c.criado_em else '',
        'Criado Por': c.criado_por or ''
    } for c in clientes]

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Clientes')

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'clientes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@motochefe_bp.route('/clientes/modelo')
@login_required
@requer_motochefe
def baixar_modelo_clientes():
    """Baixa modelo de importação para Clientes"""
    from app.motochefe.services.modelo_importacao_service import gerar_modelo_clientes

    output = gerar_modelo_clientes()
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'modelo_importacao_clientes_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )

@motochefe_bp.route('/clientes/importar', methods=['POST'])
@login_required
@requer_motochefe
def importar_clientes():
    """Importa clientes de Excel"""
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('motochefe.listar_clientes'))

    file = request.files['arquivo']
    if file.filename == '':
        flash('Arquivo inválido', 'danger')
        return redirect(url_for('motochefe.listar_clientes'))

    try:
        df = pd.read_excel(file)

        # Validar colunas obrigatórias
        if 'Cliente' not in df.columns or 'CNPJ' not in df.columns:
            flash('Planilha deve conter colunas "Cliente" e "CNPJ"', 'danger')
            return redirect(url_for('motochefe.listar_clientes'))

        importados = 0
        for _, row in df.iterrows():
            nome = row['Cliente']
            cnpj = row['CNPJ']

            if pd.isna(nome) or pd.isna(cnpj):
                continue

            # Verificar se já existe
            existe = ClienteMoto.query.filter_by(cnpj_cliente=str(cnpj), ativo=True).first()
            if existe:
                continue

            cliente = ClienteMoto(
                cliente=nome,
                cnpj_cliente=str(cnpj),
                endereco_cliente=row.get('Endereço') if 'Endereço' in df.columns else None,
                numero_cliente=row.get('Número') if 'Número' in df.columns else None,
                complemento_cliente=row.get('Complemento') if 'Complemento' in df.columns else None,
                bairro_cliente=row.get('Bairro') if 'Bairro' in df.columns else None,
                cidade_cliente=row.get('Cidade') if 'Cidade' in df.columns else None,
                estado_cliente=row.get('Estado') if 'Estado' in df.columns else None,
                cep_cliente=row.get('CEP') if 'CEP' in df.columns else None,
                telefone_cliente=row.get('Telefone') if 'Telefone' in df.columns else None,
                email_cliente=row.get('Email') if 'Email' in df.columns else None,
                criado_por=current_user.nome
            )
            db.session.add(cliente)
            importados += 1

        db.session.commit()
        flash(f'{importados} clientes importados com sucesso!', 'success')

    except Exception as e:
        flash(f'Erro ao importar: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_clientes'))

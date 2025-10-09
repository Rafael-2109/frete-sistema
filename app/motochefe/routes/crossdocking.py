"""
Rotas de CrossDocking - Sistema MotoCHEFE
CRUD completo para gestão de regras de CrossDocking
"""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from decimal import Decimal

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.routes.cadastros import requer_motochefe
from app.motochefe.models import CrossDocking, TabelaPrecoCrossDocking, ModeloMoto


@motochefe_bp.route('/crossdocking')
@login_required
@requer_motochefe
def listar_crossdocking():
    """
    Lista regras de CrossDocking

    ⚠️ REGRA ESPECIAL: Deve existir apenas 1 CrossDocking genérico
    - Se não existe: Redireciona para criação
    - Se existe apenas 1: Redireciona automaticamente para edição
    """
    total = CrossDocking.query.filter_by(ativo=True).count()

    if total == 0:
        # Não existe: Redirecionar para criação
        flash('Nenhum CrossDocking encontrado. Crie o registro genérico primeiro.', 'info')
        return redirect(url_for('motochefe.adicionar_crossdocking'))

    # Se existe pelo menos 1, pegar o primeiro (único registro genérico)
    crossdocking = CrossDocking.query.filter_by(ativo=True).first()

    # Redirecionar automaticamente para edição do único registro
    return redirect(url_for('motochefe.editar_crossdocking', id=crossdocking.id))


@motochefe_bp.route('/crossdocking/adicionar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def adicionar_crossdocking():
    """
    Adiciona nova regra de CrossDocking

    ⚠️ BLOQUEIO: Permite criar apenas se NÃO existir nenhum registro ativo
    """
    # Verificar se já existe algum CrossDocking ativo
    total_ativos = CrossDocking.query.filter_by(ativo=True).count()

    if total_ativos > 0:
        # ❌ JÁ EXISTE: Bloquear criação e redirecionar para edição
        crossdocking_existente = CrossDocking.query.filter_by(ativo=True).first()
        flash(
            'Já existe um CrossDocking genérico. Apenas 1 registro é permitido. '
            'Use a opção de edição para alterar as configurações.',
            'warning'
        )
        return redirect(url_for('motochefe.editar_crossdocking', id=crossdocking_existente.id))

    # ✅ NÃO EXISTE: Permitir criação do primeiro (único) registro
    if request.method == 'POST':
        nome = request.form.get('nome')

        if not nome:
            flash('Nome é obrigatório', 'danger')
            return redirect(url_for('motochefe.adicionar_crossdocking'))

        crossdocking = CrossDocking(
            nome=nome,
            descricao=request.form.get('descricao'),
            responsavel_movimentacao=request.form.get('responsavel_movimentacao'),
            custo_movimentacao=Decimal(request.form.get('custo_movimentacao') or 0),
            incluir_custo_movimentacao=bool(request.form.get('incluir_custo_movimentacao')),
            tipo_precificacao=request.form.get('tipo_precificacao', 'TABELA'),
            markup=Decimal(request.form.get('markup') or 0),
            tipo_comissao=request.form.get('tipo_comissao', 'FIXA_EXCEDENTE'),
            valor_comissao_fixa=Decimal(request.form.get('valor_comissao_fixa') or 0),
            percentual_comissao=Decimal(request.form.get('percentual_comissao') or 0),
            comissao_rateada=bool(request.form.get('comissao_rateada')),
            permitir_montagem=bool(request.form.get('permitir_montagem')),
            criado_por=current_user.nome
        )

        db.session.add(crossdocking)
        db.session.commit()

        flash(f'CrossDocking "{nome}" cadastrado com sucesso!', 'success')
        return redirect(url_for('motochefe.editar_crossdocking', id=crossdocking.id))

    return render_template('motochefe/cadastros/crossdocking/form.html', crossdocking=None)


@motochefe_bp.route('/crossdocking/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_motochefe
def editar_crossdocking(id):
    """Edita regra de CrossDocking existente"""
    crossdocking = CrossDocking.query.get_or_404(id)

    if request.method == 'POST':
        crossdocking.nome = request.form.get('nome')
        crossdocking.descricao = request.form.get('descricao')
        crossdocking.responsavel_movimentacao = request.form.get('responsavel_movimentacao')
        crossdocking.custo_movimentacao = Decimal(request.form.get('custo_movimentacao') or 0)
        crossdocking.incluir_custo_movimentacao = bool(request.form.get('incluir_custo_movimentacao'))
        crossdocking.tipo_precificacao = request.form.get('tipo_precificacao', 'TABELA')
        crossdocking.markup = Decimal(request.form.get('markup') or 0)
        crossdocking.tipo_comissao = request.form.get('tipo_comissao', 'FIXA_EXCEDENTE')
        crossdocking.valor_comissao_fixa = Decimal(request.form.get('valor_comissao_fixa') or 0)
        crossdocking.percentual_comissao = Decimal(request.form.get('percentual_comissao') or 0)
        crossdocking.comissao_rateada = bool(request.form.get('comissao_rateada'))
        crossdocking.permitir_montagem = bool(request.form.get('permitir_montagem'))
        crossdocking.atualizado_por = current_user.nome

        db.session.commit()

        flash('CrossDocking atualizado com sucesso!', 'success')
        return redirect(url_for('motochefe.listar_crossdocking'))

    return render_template('motochefe/cadastros/crossdocking/form.html', crossdocking=crossdocking)


@motochefe_bp.route('/crossdocking/<int:id>/remover', methods=['POST'])
@login_required
@requer_motochefe
def remover_crossdocking(id):
    """
    Remove (desativa) regra de CrossDocking

    ⚠️ BLOQUEIO: NÃO permite remover se for o único registro ativo
    """
    total_ativos = CrossDocking.query.filter_by(ativo=True).count()

    if total_ativos <= 1:
        # ❌ BLOQUEAR: Não pode remover o único CrossDocking
        flash(
            'Não é possível remover o único CrossDocking genérico do sistema. '
            'Pelo menos 1 registro deve permanecer ativo.',
            'danger'
        )
        return redirect(url_for('motochefe.editar_crossdocking', id=id))

    # ✅ Permitir remoção (caso futuro tenha mais de 1, mas não deveria acontecer)
    crossdocking = CrossDocking.query.get_or_404(id)
    crossdocking.ativo = False
    crossdocking.atualizado_por = current_user.nome

    db.session.commit()

    flash('CrossDocking removido com sucesso!', 'success')
    return redirect(url_for('motochefe.listar_crossdocking'))


@motochefe_bp.route('/crossdocking/<int:id>/precos')
@login_required
@requer_motochefe
def gerenciar_precos_crossdocking(id):
    """Gerencia tabela de preços do CrossDocking"""
    crossdocking = CrossDocking.query.get_or_404(id)
    modelos = ModeloMoto.query.filter_by(ativo=True).order_by(ModeloMoto.nome_modelo).all()
    precos = TabelaPrecoCrossDocking.query.filter_by(
        crossdocking_id=id,
        ativo=True
    ).all()

    return render_template('motochefe/cadastros/crossdocking/precos.html',
                         crossdocking=crossdocking,
                         modelos=modelos,
                         precos=precos)


@motochefe_bp.route('/crossdocking/<int:crossdocking_id>/precos/salvar', methods=['POST'])
@login_required
@requer_motochefe
def salvar_preco_crossdocking(crossdocking_id):
    """Salva ou atualiza preço de um modelo no CrossDocking"""
    modelo_id = request.form.get('modelo_id', type=int)
    preco_venda = request.form.get('preco_venda')

    if not modelo_id or not preco_venda:
        flash('Modelo e preço são obrigatórios', 'danger')
        return redirect(url_for('motochefe.gerenciar_precos_crossdocking', id=crossdocking_id))

    # Verificar se já existe
    preco_existe = TabelaPrecoCrossDocking.query.filter_by(
        crossdocking_id=crossdocking_id,
        modelo_id=modelo_id,
        ativo=True
    ).first()

    if preco_existe:
        # Atualizar
        preco_existe.preco_venda = Decimal(preco_venda)
        preco_existe.atualizado_por = current_user.nome
        flash('Preço atualizado com sucesso!', 'success')
    else:
        # Criar novo
        novo_preco = TabelaPrecoCrossDocking(
            crossdocking_id=crossdocking_id,
            modelo_id=modelo_id,
            preco_venda=Decimal(preco_venda),
            criado_por=current_user.nome
        )
        db.session.add(novo_preco)
        flash('Preço cadastrado com sucesso!', 'success')

    db.session.commit()
    return redirect(url_for('motochefe.gerenciar_precos_crossdocking', id=crossdocking_id))


@motochefe_bp.route('/crossdocking/precos/<int:id>/remover', methods=['POST'])
@login_required
@requer_motochefe
def remover_preco_crossdocking(id):
    """Remove preço da tabela de CrossDocking"""
    preco = TabelaPrecoCrossDocking.query.get_or_404(id)
    crossdocking_id = preco.crossdocking_id

    preco.ativo = False
    preco.atualizado_por = current_user.nome

    db.session.commit()

    flash('Preço removido com sucesso!', 'success')
    return redirect(url_for('motochefe.gerenciar_precos_crossdocking', id=crossdocking_id))

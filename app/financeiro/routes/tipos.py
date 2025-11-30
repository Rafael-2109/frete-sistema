"""
CRUD de Tipos (ContasAReceberTipo)
Tipos para: confirmação, forma_confirmação, ação_necessária, abatimento
"""

from flask import render_template, request, jsonify
from flask_login import login_required, current_user

from app import db
from app.financeiro.routes import financeiro_bp


# ========================================
# CRUD: TIPOS (ContasAReceberTipo)
# ========================================

@financeiro_bp.route('/contas-receber/tipos')
@login_required
def listar_tipos():
    """
    Listagem de Tipos (ContasAReceberTipo)
    """
    from app.financeiro.models import ContasAReceberTipo

    # Filtros
    tabela = request.args.get('tabela', '')
    campo = request.args.get('campo', '')
    ativo = request.args.get('ativo', '')

    query = ContasAReceberTipo.query

    if tabela:
        query = query.filter(ContasAReceberTipo.tabela == tabela)
    if campo:
        query = query.filter(ContasAReceberTipo.campo == campo)
    if ativo:
        query = query.filter(ContasAReceberTipo.ativo == (ativo == 'true'))

    query = query.order_by(ContasAReceberTipo.tabela, ContasAReceberTipo.campo, ContasAReceberTipo.tipo)
    tipos = query.all()

    # Opções de filtro
    tabelas_unicas = db.session.query(ContasAReceberTipo.tabela).distinct().all()
    campos_unicos = db.session.query(ContasAReceberTipo.campo).distinct().all()

    return render_template(
        'financeiro/crud_tipos.html',
        tipos=tipos,
        tabelas=[t[0] for t in tabelas_unicas],
        campos=[c[0] for c in campos_unicos]
    )


@financeiro_bp.route('/contas-receber/tipos/api', methods=['GET'])
@login_required
def api_tipos_crud_list():
    """API para listar tipos com filtros"""
    try:
        from app.financeiro.models import ContasAReceberTipo

        tabela = request.args.get('tabela', '')
        campo = request.args.get('campo', '')

        query = ContasAReceberTipo.query

        if tabela:
            query = query.filter(ContasAReceberTipo.tabela == tabela)
        if campo:
            query = query.filter(ContasAReceberTipo.campo == campo)

        tipos = query.order_by(ContasAReceberTipo.tabela, ContasAReceberTipo.campo, ContasAReceberTipo.tipo).all()

        return jsonify({
            'success': True,
            'tipos': [t.to_dict() for t in tipos]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/tipos/api/<int:tipo_id>', methods=['GET'])
@login_required
def api_tipo_detalhe(tipo_id):
    """API para obter detalhes de um tipo"""
    try:
        from app.financeiro.models import ContasAReceberTipo

        tipo = ContasAReceberTipo.query.get_or_404(tipo_id)
        return jsonify({'success': True, 'tipo': tipo.to_dict()})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/tipos/api', methods=['POST'])
@login_required
def api_criar_tipo():
    """API para criar novo tipo"""
    try:
        from app.financeiro.models import ContasAReceberTipo

        data = request.get_json()

        # Validações
        if not data.get('tipo'):
            return jsonify({'success': False, 'error': 'Nome do tipo é obrigatório'}), 400
        if not data.get('tabela'):
            return jsonify({'success': False, 'error': 'Tabela é obrigatória'}), 400
        if not data.get('campo'):
            return jsonify({'success': False, 'error': 'Campo é obrigatório'}), 400

        # Verificar duplicidade
        existente = ContasAReceberTipo.query.filter_by(
            tipo=data['tipo'],
            tabela=data['tabela'],
            campo=data['campo']
        ).first()

        if existente:
            return jsonify({'success': False, 'error': 'Tipo já existe para esta tabela/campo'}), 400

        tipo = ContasAReceberTipo(
            tipo=data['tipo'],
            tabela=data['tabela'],
            campo=data['campo'],
            considera_a_receber=data.get('considera_a_receber', True),
            explicacao=data.get('explicacao', ''),
            ativo=data.get('ativo', True),
            criado_por=current_user.nome
        )

        db.session.add(tipo)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Tipo criado com sucesso!',
            'tipo': tipo.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/tipos/api/<int:tipo_id>', methods=['PUT'])
@login_required
def api_atualizar_tipo(tipo_id):
    """API para atualizar tipo"""
    try:
        from app.financeiro.models import ContasAReceberTipo

        tipo = ContasAReceberTipo.query.get_or_404(tipo_id)
        data = request.get_json()

        # Verificar duplicidade (se mudou tipo/tabela/campo)
        if (data.get('tipo') != tipo.tipo or
            data.get('tabela') != tipo.tabela or
                data.get('campo') != tipo.campo):

            existente = ContasAReceberTipo.query.filter(
                ContasAReceberTipo.id != tipo_id,
                ContasAReceberTipo.tipo == data.get('tipo', tipo.tipo),
                ContasAReceberTipo.tabela == data.get('tabela', tipo.tabela),
                ContasAReceberTipo.campo == data.get('campo', tipo.campo)
            ).first()

            if existente:
                return jsonify({'success': False, 'error': 'Tipo já existe para esta tabela/campo'}), 400

        tipo.tipo = data.get('tipo', tipo.tipo)
        tipo.tabela = data.get('tabela', tipo.tabela)
        tipo.campo = data.get('campo', tipo.campo)
        tipo.considera_a_receber = data.get('considera_a_receber', tipo.considera_a_receber)
        tipo.explicacao = data.get('explicacao', tipo.explicacao)
        tipo.ativo = data.get('ativo', tipo.ativo)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Tipo atualizado com sucesso!',
            'tipo': tipo.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/tipos/api/<int:tipo_id>', methods=['DELETE'])
@login_required
def api_excluir_tipo(tipo_id):
    """API para excluir tipo (soft delete - desativa)"""
    try:
        from app.financeiro.models import ContasAReceberTipo

        tipo = ContasAReceberTipo.query.get_or_404(tipo_id)

        # Soft delete - apenas desativa
        tipo.ativo = False
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Tipo desativado com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

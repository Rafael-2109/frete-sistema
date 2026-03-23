"""
Rotas de Clientes CarVia — CRUD + Enderecos + CNPJ Lookup
"""

import logging
from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def register_cliente_routes(bp):

    # ==================== LISTAR ====================

    @bp.route('/clientes') # type: ignore
    @login_required
    def listar_clientes(): # type: ignore
        """Lista clientes CarVia"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.cliente_service import CarviaClienteService

        busca = request.args.get('busca', '').strip()
        apenas_ativos = request.args.get('ativos', '1') == '1'

        clientes = CarviaClienteService.listar_clientes(
            apenas_ativos=apenas_ativos,
            busca=busca or None,
        )

        return render_template(
            'carvia/clientes/listar.html',
            clientes=clientes,
            busca=busca,
            apenas_ativos=apenas_ativos,
        )

    # ==================== CRIAR ====================

    @bp.route('/clientes/novo', methods=['GET', 'POST']) # type: ignore
    @login_required
    def criar_cliente(): # type: ignore
        """Cria novo cliente CarVia"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        if request.method == 'GET':
            return render_template('carvia/clientes/criar.html')

        from app.carvia.services.cliente_service import CarviaClienteService

        nome_comercial = request.form.get('nome_comercial', '').strip()
        observacoes = request.form.get('observacoes', '').strip() or None

        try:
            cliente, erro = CarviaClienteService.criar_cliente(
                nome_comercial=nome_comercial,
                criado_por=current_user.email,
                observacoes=observacoes,
            )
            if erro:
                flash(erro, 'danger')
                return render_template('carvia/clientes/criar.html')

            db.session.commit()
            flash(f'Cliente "{cliente.nome_comercial}" criado com sucesso.', 'success')
            return redirect(url_for('carvia.detalhe_cliente', cliente_id=cliente.id))

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar cliente: %s", e)
            flash(f'Erro ao criar cliente: {e}', 'danger')
            return render_template('carvia/clientes/criar.html')

    # ==================== DETALHE / EDITAR ====================

    @bp.route('/clientes/<int:cliente_id>') # type: ignore
    @login_required
    def detalhe_cliente(cliente_id): # type: ignore
        """Detalhe do cliente com enderecos"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.cliente_service import CarviaClienteService

        cliente = CarviaClienteService.buscar_por_id(cliente_id)
        if not cliente:
            flash('Cliente nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_clientes'))

        enderecos = cliente.enderecos.all()

        return render_template(
            'carvia/clientes/detalhe.html',
            cliente=cliente,
            enderecos=enderecos,
        )

    @bp.route('/clientes/<int:cliente_id>/editar', methods=['GET', 'POST']) # type: ignore
    @login_required
    def editar_cliente(cliente_id): # type: ignore
        """Edita dados do cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.cliente_service import CarviaClienteService

        cliente = CarviaClienteService.buscar_por_id(cliente_id)
        if not cliente:
            flash('Cliente nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_clientes'))

        if request.method == 'GET':
            return render_template('carvia/clientes/editar.html', cliente=cliente)

        try:
            sucesso, erro = CarviaClienteService.atualizar_cliente(cliente_id, {
                'nome_comercial': request.form.get('nome_comercial', ''),
                'observacoes': request.form.get('observacoes', '').strip() or None,
                'ativo': request.form.get('ativo') == '1',
            })
            if not sucesso:
                flash(erro, 'danger')
                return render_template('carvia/clientes/editar.html', cliente=cliente)

            db.session.commit()
            flash('Cliente atualizado com sucesso.', 'success')
            return redirect(url_for('carvia.detalhe_cliente', cliente_id=cliente_id))

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao editar cliente #%s: %s", cliente_id, e)
            flash(f'Erro: {e}', 'danger')
            return render_template('carvia/clientes/editar.html', cliente=cliente)

    # ==================== API: ENDERECOS ====================

    @bp.route('/api/clientes/<int:cliente_id>/enderecos', methods=['POST']) # type: ignore
    @login_required
    def api_adicionar_endereco(cliente_id): # type: ignore
        """Adiciona endereco ao cliente (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.cliente_service import CarviaClienteService

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        cnpj = (data.get('cnpj') or '').strip()
        tipo = (data.get('tipo') or '').strip().upper()

        if not cnpj:
            return jsonify({'erro': 'CNPJ e obrigatorio.'}), 400
        if not tipo:
            return jsonify({'erro': 'Tipo (ORIGEM/DESTINO) e obrigatorio.'}), 400

        # Montar dados Receita e Fisico
        dados_receita = {}
        dados_fisico = {}
        for campo in ('uf', 'cidade', 'logradouro', 'numero', 'bairro', 'cep', 'complemento'):
            dados_receita[campo] = data.get(f'receita_{campo}', '')
            dados_fisico[campo] = data.get(f'fisico_{campo}', '')

        try:
            endereco, erro = CarviaClienteService.adicionar_endereco(
                cliente_id=cliente_id,
                cnpj=cnpj,
                tipo=tipo,
                criado_por=current_user.email,
                razao_social=data.get('razao_social'),
                dados_receita=dados_receita,
                dados_fisico=dados_fisico,
                principal=data.get('principal', False),
            )
            if erro:
                return jsonify({'erro': erro}), 400

            db.session.commit()
            return jsonify({
                'sucesso': True,
                'id': endereco.id,
                'mensagem': f'Endereco {tipo} adicionado.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao adicionar endereco: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/enderecos/<int:endereco_id>', methods=['PUT']) # type: ignore
    @login_required
    def api_atualizar_endereco(endereco_id): # type: ignore
        """Atualiza endereco fisico (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.cliente_service import CarviaClienteService

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            sucesso, erro = CarviaClienteService.atualizar_endereco(endereco_id, data)
            if not sucesso:
                return jsonify({'erro': erro}), 400

            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Endereco atualizado.'})

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao atualizar endereco #%s: %s", endereco_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/enderecos/<int:endereco_id>', methods=['DELETE']) # type: ignore
    @login_required
    def api_remover_endereco(endereco_id): # type: ignore
        """Remove endereco (hard delete)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.cliente_service import CarviaClienteService

        try:
            sucesso, erro = CarviaClienteService.remover_endereco(endereco_id)
            if not sucesso:
                return jsonify({'erro': erro}), 404

            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Endereco removido.'})

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao remover endereco #%s: %s", endereco_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== API: BUSCAR CNPJ NA RECEITA ====================

    @bp.route('/api/clientes/buscar-cnpj', methods=['POST']) # type: ignore
    @login_required
    def api_buscar_cnpj(): # type: ignore
        """Busca dados de CNPJ na API da Receita Federal"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.cliente_service import CarviaClienteService

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        cnpj = (data.get('cnpj') or '').strip()
        if not cnpj:
            return jsonify({'erro': 'CNPJ e obrigatorio.'}), 400

        try:
            dados, erro = CarviaClienteService.buscar_cnpj_receita(cnpj)
            if erro:
                return jsonify({'erro': erro}), 400

            # Verificar se CNPJ ja esta cadastrado em algum cliente
            enderecos_existentes = CarviaClienteService.buscar_enderecos_por_cnpj(cnpj)
            aviso = None
            if enderecos_existentes:
                clientes_nomes = set(
                    e.cliente.nome_comercial for e in enderecos_existentes
                    if e.cliente
                )
                aviso = f'CNPJ ja cadastrado em: {", ".join(clientes_nomes)}'

            return jsonify({
                'sucesso': True,
                'dados': dados,
                'aviso': aviso,
            })

        except Exception as e:
            logger.error("Erro ao buscar CNPJ: %s", e)
            return jsonify({'erro': f'Erro na consulta: {e}'}), 500

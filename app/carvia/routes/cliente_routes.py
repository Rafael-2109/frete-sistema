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

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

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

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

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
        """Detalhe do cliente com enderecos.

        Query params:
            mostrar_inativos=1 — inclui enderecos com ativo=False
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        from app.carvia.models import CarviaClienteEndereco

        cliente = CarviaClienteService.buscar_por_id(cliente_id)
        if not cliente:
            flash('Cliente nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_clientes'))

        mostrar_inativos = request.args.get('mostrar_inativos', '0') == '1'

        query = cliente.enderecos
        if not mostrar_inativos:
            query = query.filter(CarviaClienteEndereco.ativo == True)
        enderecos = query.all()

        total_inativos = cliente.enderecos.filter(
            CarviaClienteEndereco.ativo == False
        ).count()

        todos_clientes = CarviaClienteService.listar_clientes(apenas_ativos=True)

        return render_template(
            'carvia/clientes/detalhe.html',
            cliente=cliente,
            enderecos=enderecos,
            todos_clientes=todos_clientes,
            mostrar_inativos=mostrar_inativos,
            total_inativos=total_inativos,
        )

    @bp.route('/clientes/<int:cliente_id>/editar', methods=['GET', 'POST']) # type: ignore
    @login_required
    def editar_cliente(cliente_id): # type: ignore
        """Edita dados do cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

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

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        cnpj = (data.get('cnpj') or '').strip()
        tipo = (data.get('tipo') or '').strip().upper()

        if not cnpj:
            return jsonify({'erro': 'CNPJ/CPF e obrigatorio.'}), 400
        if not tipo:
            return jsonify({'erro': 'Tipo (ORIGEM/DESTINO) e obrigatorio.'}), 400

        # Montar dados Receita e Fisico
        dados_receita = {}
        dados_fisico = {}
        for campo in ('uf', 'cidade', 'logradouro', 'numero', 'bairro', 'cep', 'complemento'):
            dados_receita[campo] = data.get(f'receita_{campo}', '')
            dados_fisico[campo] = data.get(f'fisico_{campo}', '')

        try:
            # Origens sao sempre globais (cliente_id=NULL)
            if tipo == 'ORIGEM':
                endereco, erro = CarviaClienteService.adicionar_origem_global(
                    cnpj=cnpj,
                    razao_social=data.get('razao_social'),
                    criado_por=current_user.email,
                    dados_receita=dados_receita,
                    dados_fisico=dados_fisico,
                )
            else:
                endereco, erro = CarviaClienteService.adicionar_endereco(
                    cliente_id=cliente_id,
                    cnpj=cnpj,
                    tipo=tipo,
                    criado_por=current_user.email,
                    razao_social=data.get('razao_social'),
                    dados_receita=dados_receita,
                    dados_fisico=dados_fisico,
                    # principal removido — conceito descontinuado
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
        """Atualiza endereco fisico (JSON API).

        Se a troca de cliente_id causaria duplicata, retorna 409 com
        {erro, acao_sugerida: 'mesclar', endereco_existente_id, ...}.
        Frontend pode entao oferecer MESCLAR ao usuario.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            sucesso, erro, contexto = CarviaClienteService.atualizar_endereco(
                endereco_id, data
            )
            if not sucesso:
                resp = {'erro': erro}
                status = 400
                if contexto and contexto.get('acao_sugerida') == 'mesclar':
                    resp.update(contexto)
                    status = 409  # Conflict — frontend deve oferecer merge
                elif 'nao encontrado' in (erro or ''):
                    status = 404
                return jsonify(resp), status

            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Endereco atualizado.'})

        except Exception as e:
            db.session.rollback()
            # Race condition: outra request criou duplicado entre validacao e commit.
            # Sentry PYTHON-FLASK-JA rastreava esse erro como 500.
            from sqlalchemy.exc import IntegrityError
            if isinstance(e, IntegrityError) and 'uq_carvia_end_cliente_cnpj_tipo' in str(e):
                logger.warning(
                    "Race UniqueViolation atualizar endereco #%s (concorrencia): %s",
                    endereco_id, str(e)[:200]
                )
                return jsonify({
                    'erro': 'Endereco duplicado: ja existe outro endereco identico para este cliente. Recarregue a pagina.',
                    'acao_sugerida': 'mesclar',
                }), 409
            logger.error("Erro ao atualizar endereco #%s: %s", endereco_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/enderecos/<int:endereco_id>', methods=['DELETE']) # type: ignore
    @login_required
    def api_remover_endereco(endereco_id): # type: ignore
        """Remove endereco (hard delete se sem cotacoes; retorna candidatos senao).

        Retorna 409 com lista de candidatos de migracao se o endereco tiver
        cotacoes vinculadas. Frontend deve oferecer escolher destino e chamar
        /migrar-e-remover/<destino_id>, ou cair para /desativar.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        try:
            sucesso, erro, contexto = CarviaClienteService.remover_endereco(endereco_id)
            if not sucesso:
                resp = {'erro': erro}
                if contexto:
                    resp.update(contexto)
                status = 404 if 'nao encontrado' in (erro or '') else 409
                return jsonify(resp), status

            db.session.commit()
            return jsonify({
                'sucesso': True,
                'mensagem': 'Endereco removido.',
                **(contexto or {}),
            })

        except Exception as e:
            db.session.rollback()
            # FK race: cotacao foi criada referenciando este endereco entre
            # check do service e DELETE. Sentry PYTHON-FLASK-J9 rastreava como 500.
            from sqlalchemy.exc import IntegrityError
            if isinstance(e, IntegrityError) and 'foreign key constraint' in str(e).lower():
                logger.warning(
                    "Race FK violation remover endereco #%s (cotacao concorrente): %s",
                    endereco_id, str(e)[:200]
                )
                return jsonify({
                    'erro': 'Endereco em uso: foi vinculado a uma cotacao apos voce abrir esta tela. Recarregue para ver opcoes de migracao.',
                    'acao_sugerida': 'recarregar',
                }), 409
            logger.error("Erro ao remover endereco #%s: %s", endereco_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route(
        '/api/enderecos/<int:origem_id>/mesclar-com/<int:destino_id>',
        methods=['POST']
    ) # type: ignore
    @login_required
    def api_mesclar_enderecos(origem_id, destino_id): # type: ignore
        """Mescla origem → destino: migra cotacoes + soft delete origem."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        try:
            sucesso, erro, contexto = CarviaClienteService.mesclar_enderecos(
                origem_id, destino_id
            )
            if not sucesso:
                return jsonify({'erro': erro}), 400

            db.session.commit()
            ctx = contexto or {}
            return jsonify({
                'sucesso': True,
                'mensagem': (f'Mesclado: {ctx.get("total_migrado", 0)} cotacao(oes) '
                             f'migrada(s); endereco origem desativado.'),
                **ctx,
            })

        except Exception as e:
            db.session.rollback()
            logger.error(
                "Erro ao mesclar enderecos #%s → #%s: %s",
                origem_id, destino_id, e
            )
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route(
        '/api/enderecos/<int:origem_id>/migrar-e-remover/<int:destino_id>',
        methods=['POST']
    ) # type: ignore
    @login_required
    def api_migrar_e_remover_endereco(origem_id, destino_id): # type: ignore
        """Migra cotacoes para destino e DELETA fisicamente o origem."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        try:
            sucesso, erro, contexto = CarviaClienteService.migrar_e_remover(
                origem_id, destino_id
            )
            if not sucesso:
                return jsonify({'erro': erro}), 400

            db.session.commit()
            ctx = contexto or {}
            return jsonify({
                'sucesso': True,
                'mensagem': (f'Migrado: {ctx.get("total_migrado", 0)} cotacao(oes); '
                             f'endereco origem removido.'),
                **ctx,
            })

        except Exception as e:
            db.session.rollback()
            logger.error(
                "Erro ao migrar+remover endereco #%s → #%s: %s",
                origem_id, destino_id, e
            )
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/enderecos/<int:endereco_id>/desativar', methods=['PATCH']) # type: ignore
    @login_required
    def api_desativar_endereco(endereco_id): # type: ignore
        """Soft-delete: marca endereco como ativo=False (some das opcoes)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        try:
            sucesso, erro, _ = CarviaClienteService.atualizar_endereco(
                endereco_id, {'ativo': False}
            )
            if not sucesso:
                status = 404 if 'nao encontrado' in (erro or '') else 400
                return jsonify({'erro': erro}), status

            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Endereco desativado.'})

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao desativar endereco #%s: %s", endereco_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/enderecos/<int:endereco_id>/reativar', methods=['PATCH']) # type: ignore
    @login_required
    def api_reativar_endereco(endereco_id): # type: ignore
        """Reativa endereco desativado. Bloqueia se ja existir outro ativo com mesmo
        (cliente_id, cnpj, tipo)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        try:
            sucesso, erro, contexto = CarviaClienteService.atualizar_endereco(
                endereco_id, {'ativo': True}
            )
            if not sucesso:
                resp = {'erro': erro}
                if contexto:
                    resp.update(contexto)
                status = (404 if 'nao encontrado' in (erro or '')
                          else 409 if contexto else 400)
                return jsonify(resp), status

            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Endereco reativado.'})

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao reativar endereco #%s: %s", endereco_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== ORIGENS GLOBAIS ====================

    @bp.route('/clientes/origens') # type: ignore
    @login_required
    def origens_globais(): # type: ignore
        """Lista e gerencia origens globais (compartilhadas entre todos os clientes)."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        origens = CarviaClienteService.listar_origens_globais()

        return render_template(
            'carvia/clientes/origens_globais.html',
            origens=origens,
        )

    @bp.route('/api/origens-globais', methods=['POST']) # type: ignore
    @login_required
    def api_criar_origem_global(): # type: ignore
        """Cria origem global (JSON API)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        cnpj = (data.get('cnpj') or '').strip()
        if not cnpj:
            return jsonify({'erro': 'CNPJ/CPF e obrigatorio.'}), 400

        dados_receita = {}
        dados_fisico = {}
        for campo in ('uf', 'cidade', 'logradouro', 'numero', 'bairro', 'cep', 'complemento'):
            dados_receita[campo] = data.get(f'receita_{campo}', '')
            dados_fisico[campo] = data.get(f'fisico_{campo}', '')

        try:
            endereco, erro = CarviaClienteService.adicionar_origem_global(
                cnpj=cnpj,
                razao_social=data.get('razao_social'),
                criado_por=current_user.email,
                dados_receita=dados_receita,
                dados_fisico=dados_fisico,
            )
            if erro:
                return jsonify({'erro': erro}), 400

            db.session.commit()
            return jsonify({
                'sucesso': True,
                'id': endereco.id,
                'mensagem': 'Origem global criada.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar origem global: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== API: BUSCAR CNPJ NA RECEITA ====================

    @bp.route('/api/clientes/buscar-cnpj', methods=['POST']) # type: ignore
    @login_required
    def api_buscar_cnpj(): # type: ignore
        """Busca dados de CNPJ na API da Receita Federal"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

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

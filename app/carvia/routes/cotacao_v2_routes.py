"""
Rotas de Cotacao Comercial CarVia — Fluxo proativo
"""

import logging
from datetime import datetime
from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def register_cotacao_v2_routes(bp):

    # ==================== LISTAR ====================

    @bp.route('/cotacoes') # type: ignore
    @login_required
    def listar_cotacoes_v2(): # type: ignore
        """Lista cotacoes comerciais"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

        status = request.args.get('status')
        cliente_id = request.args.get('cliente_id', type=int)

        cotacoes = CotacaoV2Service.listar_cotacoes(
            status=status,
            cliente_id=cliente_id,
        )

        # Contadores por status
        from app.carvia.models import CarviaCotacao
        from sqlalchemy import func
        contadores = dict(
            db.session.query(
                CarviaCotacao.status,
                func.count(CarviaCotacao.id)
            ).group_by(CarviaCotacao.status).all()
        )

        return render_template(
            'carvia/cotacoes/listar.html',
            cotacoes=cotacoes,
            status_filtro=status,
            cliente_id_filtro=cliente_id,
            contadores=contadores,
        )

    # ==================== CRIAR ====================

    @bp.route('/cotacoes/nova', methods=['GET', 'POST']) # type: ignore
    @login_required
    def criar_cotacao_v2(): # type: ignore
        """Cria nova cotacao comercial"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.cliente_service import CarviaClienteService

        if request.method == 'GET':
            clientes = CarviaClienteService.listar_clientes(apenas_ativos=True)
            return render_template('carvia/cotacoes/criar.html', clientes=clientes)

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

        try:
            # Parse datas
            data_exp = request.form.get('data_expedicao')
            data_ag = request.form.get('data_agenda')

            cotacao, erro = CotacaoV2Service.criar_cotacao(
                cliente_id=int(request.form.get('cliente_id', 0)),
                endereco_origem_id=int(request.form.get('endereco_origem_id', 0)),
                endereco_destino_id=int(request.form.get('endereco_destino_id', 0)),
                tipo_material=request.form.get('tipo_material', 'CARGA_GERAL'),
                criado_por=current_user.email,
                peso=request.form.get('peso', type=float),
                valor_mercadoria=request.form.get('valor_mercadoria', type=float),
                volumes=request.form.get('volumes', type=int),
                dimensao_c=request.form.get('dimensao_c', type=float),
                dimensao_l=request.form.get('dimensao_l', type=float),
                dimensao_a=request.form.get('dimensao_a', type=float),
                data_expedicao=datetime.strptime(data_exp, '%Y-%m-%d').date() if data_exp else None,
                data_agenda=datetime.strptime(data_ag, '%Y-%m-%d').date() if data_ag else None,
                observacoes=request.form.get('observacoes'),
            )

            if erro:
                flash(erro, 'danger')
                clientes = CarviaClienteService.listar_clientes(apenas_ativos=True)
                return render_template('carvia/cotacoes/criar.html', clientes=clientes)

            db.session.commit()
            flash(f'Cotacao {cotacao.numero_cotacao} criada.', 'success')
            return redirect(url_for('carvia.detalhe_cotacao_v2', cotacao_id=cotacao.id))

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar cotacao: %s", e)
            flash(f'Erro: {e}', 'danger')
            clientes = CarviaClienteService.listar_clientes(apenas_ativos=True)
            return render_template('carvia/cotacoes/criar.html', clientes=clientes)

    # ==================== DETALHE ====================

    @bp.route('/cotacoes/<int:cotacao_id>') # type: ignore
    @login_required
    def detalhe_cotacao_v2(cotacao_id): # type: ignore
        """Detalhe da cotacao com motos, pricing e acoes"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaCotacao

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            flash('Cotacao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_cotacoes_v2'))

        motos = cotacao.motos.all() if cotacao.tipo_material == 'MOTO' else []
        pedidos = cotacao.pedidos.all()

        # Modelos disponiveis para adicionar moto
        from app.carvia.models import CarviaModeloMoto
        modelos_moto = CarviaModeloMoto.query.filter_by(ativo=True).order_by(
            CarviaModeloMoto.nome.asc()
        ).all() if cotacao.tipo_material == 'MOTO' and cotacao.status == 'RASCUNHO' else []

        # Limite desconto para UI
        from app.carvia.services.config_service import CarviaConfigService
        limite_desconto = CarviaConfigService.limite_desconto_percentual()

        return render_template(
            'carvia/cotacoes/detalhe.html',
            cotacao=cotacao,
            motos=motos,
            pedidos=pedidos,
            modelos_moto=modelos_moto,
            limite_desconto=limite_desconto,
        )

    # ==================== API: MOTOS ====================

    @bp.route('/api/cotacoes/<int:cotacao_id>/motos', methods=['POST']) # type: ignore
    @login_required
    def api_adicionar_moto_cotacao(cotacao_id): # type: ignore
        """Adiciona moto a cotacao (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            item, erro = CotacaoV2Service.adicionar_moto(
                cotacao_id=cotacao_id,
                modelo_moto_id=int(data.get('modelo_moto_id', 0)),
                quantidade=int(data.get('quantidade', 0)),
                valor_unitario=float(data['valor_unitario']) if data.get('valor_unitario') else None,
            )
            if erro:
                return jsonify({'erro': erro}), 400

            db.session.commit()
            return jsonify({
                'sucesso': True,
                'id': item.id,
                'mensagem': 'Moto adicionada.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao adicionar moto: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacao-motos/<int:item_id>', methods=['DELETE']) # type: ignore
    @login_required
    def api_remover_moto_cotacao(item_id): # type: ignore
        """Remove moto da cotacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaCotacaoMoto

        item = db.session.get(CarviaCotacaoMoto, item_id)
        if not item:
            return jsonify({'erro': 'Item nao encontrado.'}), 404

        if item.cotacao.status != 'RASCUNHO':
            return jsonify({'erro': 'Cotacao nao esta em RASCUNHO.'}), 400

        try:
            db.session.delete(item)
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Moto removida.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== API: PRICING ====================

    @bp.route('/api/cotacoes/<int:cotacao_id>/calcular-preco', methods=['POST']) # type: ignore
    @login_required
    def api_calcular_preco(cotacao_id): # type: ignore
        """Calcula preco da cotacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

        try:
            resultado, erro = CotacaoV2Service.calcular_preco(cotacao_id)
            if erro:
                return jsonify({'erro': erro}), 400

            db.session.commit()
            return jsonify({'sucesso': True, **resultado})

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao calcular preco: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/desconto', methods=['POST']) # type: ignore
    @login_required
    def api_aplicar_desconto(cotacao_id): # type: ignore
        """Aplica desconto na cotacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            sucesso, erro = CotacaoV2Service.aplicar_desconto(
                cotacao_id=cotacao_id,
                percentual_desconto=float(data.get('percentual_desconto', 0)),
                usuario=current_user.email,
            )
            if not sucesso:
                return jsonify({'erro': erro}), 400

            db.session.commit()

            from app.carvia.models import CarviaCotacao
            cotacao = db.session.get(CarviaCotacao, cotacao_id)
            return jsonify({
                'sucesso': True,
                'status': cotacao.status,
                'valor_descontado': float(cotacao.valor_descontado or 0),
                'valor_final_aprovado': float(cotacao.valor_final_aprovado or 0),
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== API: STATUS ====================

    @bp.route('/api/cotacoes/<int:cotacao_id>/enviar', methods=['POST']) # type: ignore
    @login_required
    def api_enviar_cotacao(cotacao_id): # type: ignore
        """Marca como ENVIADO"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

        try:
            sucesso, erro = CotacaoV2Service.marcar_enviado(
                cotacao_id, current_user.email)
            if not sucesso:
                return jsonify({'erro': erro}), 400
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Cotacao enviada.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/aprovar-cliente', methods=['POST']) # type: ignore
    @login_required
    def api_aprovar_cliente(cotacao_id): # type: ignore
        """Registra aprovacao do cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

        try:
            sucesso, erro = CotacaoV2Service.registrar_aprovacao_cliente(
                cotacao_id, current_user.email)
            if not sucesso:
                return jsonify({'erro': erro}), 400
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Cotacao aprovada pelo cliente.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/recusar-cliente', methods=['POST']) # type: ignore
    @login_required
    def api_recusar_cliente(cotacao_id): # type: ignore
        """Registra recusa do cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

        try:
            sucesso, erro = CotacaoV2Service.registrar_recusa_cliente(cotacao_id)
            if not sucesso:
                return jsonify({'erro': erro}), 400
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Cotacao recusada.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/contra-proposta', methods=['POST']) # type: ignore
    @login_required
    def api_contra_proposta(cotacao_id): # type: ignore
        """Registra contra-proposta do cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            sucesso, erro = CotacaoV2Service.registrar_contra_proposta(
                cotacao_id, float(data.get('novo_valor', 0)))
            if not sucesso:
                return jsonify({'erro': erro}), 400
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Contra-proposta registrada.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/cancelar', methods=['POST']) # type: ignore
    @login_required
    def api_cancelar_cotacao(cotacao_id): # type: ignore
        """Cancela cotacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

        try:
            sucesso, erro = CotacaoV2Service.cancelar(cotacao_id)
            if not sucesso:
                return jsonify({'erro': erro}), 400
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Cotacao cancelada.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/admin-aprovar', methods=['POST']) # type: ignore
    @login_required
    def api_admin_aprovar_cotacao(cotacao_id): # type: ignore
        """Admin aprova cotacao pendente"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403
        if not getattr(current_user, 'perfil', '') == 'administrador':
            return jsonify({'erro': 'Apenas administradores.'}), 403

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

        try:
            sucesso, erro = CotacaoV2Service.admin_aprovar(
                cotacao_id, current_user.email)
            if not sucesso:
                return jsonify({'erro': erro}), 400
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Desconto aprovado pelo admin.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/admin-rejeitar', methods=['POST']) # type: ignore
    @login_required
    def api_admin_rejeitar_cotacao(cotacao_id): # type: ignore
        """Admin rejeita cotacao pendente"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403
        if not getattr(current_user, 'perfil', '') == 'administrador':
            return jsonify({'erro': 'Apenas administradores.'}), 403

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

        try:
            sucesso, erro = CotacaoV2Service.admin_rejeitar(cotacao_id)
            if not sucesso:
                return jsonify({'erro': erro}), 400
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Desconto rejeitado.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== API: ENDERECOS DO CLIENTE ====================

    @bp.route('/api/cotacoes/enderecos-cliente/<int:cliente_id>') # type: ignore
    @login_required
    def api_enderecos_cliente_cotacao(cliente_id): # type: ignore
        """Lista enderecos de um cliente (para dropdown na criacao de cotacao)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaClienteEndereco

        enderecos = CarviaClienteEndereco.query.filter_by(
            cliente_id=cliente_id
        ).order_by(
            CarviaClienteEndereco.tipo,
            CarviaClienteEndereco.principal.desc()
        ).all()

        return jsonify({
            'enderecos': [
                {
                    'id': e.id,
                    'cnpj': e.cnpj,
                    'razao_social': e.razao_social,
                    'tipo': e.tipo,
                    'principal': e.principal,
                    'cidade': e.fisico_cidade,
                    'uf': e.fisico_uf,
                    'label': f'{e.cnpj} - {e.razao_social or "Sem razao"} ({e.fisico_cidade}/{e.fisico_uf}) [{e.tipo}]',
                }
                for e in enderecos
            ]
        })

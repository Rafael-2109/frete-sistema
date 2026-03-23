"""
Rotas de Pedidos CarVia — CRUD vinculado a cotacao
"""

import logging
from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def register_pedido_routes(bp):

    @bp.route('/pedidos-carvia')
    @login_required
    def listar_pedidos_carvia():
        """Lista pedidos CarVia"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaPedido

        status = request.args.get('status')
        cotacao_id = request.args.get('cotacao_id', type=int)

        query = CarviaPedido.query
        if status:
            query = query.filter_by(status=status)
        if cotacao_id:
            query = query.filter_by(cotacao_id=cotacao_id)

        pedidos = query.order_by(CarviaPedido.criado_em.desc()).all()

        return render_template(
            'carvia/pedidos/listar.html',
            pedidos=pedidos,
            status_filtro=status,
        )

    @bp.route('/pedidos-carvia/<int:pedido_id>')
    @login_required
    def detalhe_pedido_carvia(pedido_id):
        """Detalhe do pedido com itens"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaPedido

        pedido = db.session.get(CarviaPedido, pedido_id)
        if not pedido:
            flash('Pedido nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_pedidos_carvia'))

        itens = pedido.itens.all()

        return render_template(
            'carvia/pedidos/detalhe.html',
            pedido=pedido,
            itens=itens,
        )

    @bp.route('/api/cotacoes/<int:cotacao_id>/pedidos', methods=['POST'])
    @login_required
    def api_criar_pedido(cotacao_id):
        """Cria pedido vinculado a cotacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaCotacao, CarviaPedido
        from app.utils.timezone import agora_utc_naive

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return jsonify({'erro': 'Cotacao nao encontrada.'}), 404
        if cotacao.status != 'APROVADO':
            return jsonify({'erro': 'Cotacao nao esta APROVADA.'}), 400

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        filial = (data.get('filial') or '').upper()
        if filial not in ('SP', 'RJ'):
            return jsonify({'erro': 'Filial deve ser SP ou RJ.'}), 400

        tipo_sep = 'ESTOQUE' if filial == 'SP' else 'CROSSDOCK'

        try:
            pedido = CarviaPedido(
                numero_pedido=CarviaPedido.gerar_numero_pedido(),
                cotacao_id=cotacao_id,
                filial=filial,
                tipo_separacao=tipo_sep,
                observacoes=data.get('observacoes'),
                criado_por=current_user.email,
                criado_em=agora_utc_naive(),
                atualizado_em=agora_utc_naive(),
            )
            db.session.add(pedido)
            db.session.flush()

            # Adicionar itens: se fornecidos no JSON, usar. Senao, copiar motos da cotacao.
            from app.carvia.models import CarviaPedidoItem
            itens_data = data.get('itens', [])
            if itens_data:
                for item_data in itens_data:
                    item = CarviaPedidoItem(
                        pedido_id=pedido.id,
                        modelo_moto_id=item_data.get('modelo_moto_id'),
                        descricao=item_data.get('descricao'),
                        cor=item_data.get('cor'),
                        quantidade=int(item_data.get('quantidade', 1)),
                        valor_unitario=item_data.get('valor_unitario'),
                        valor_total=item_data.get('valor_total'),
                    )
                    db.session.add(item)
            elif cotacao.tipo_material == 'MOTO':
                # Auto-copiar motos da cotacao como itens do pedido
                # valor_unitario = valor do PRODUTO (nao do frete)
                motos = cotacao.motos.all()
                for moto in motos:
                    modelo = moto.modelo_moto
                    # Usar valor do produto da moto (preenchido na cotacao)
                    vlr_unit = float(moto.valor_unitario) if moto.valor_unitario else None
                    vlr_total = float(moto.valor_total) if moto.valor_total else None

                    item = CarviaPedidoItem(
                        pedido_id=pedido.id,
                        modelo_moto_id=moto.modelo_moto_id,
                        descricao=modelo.nome if modelo else 'Moto',
                        cor=None,
                        quantidade=moto.quantidade,
                        valor_unitario=vlr_unit,
                        valor_total=vlr_total,
                    )
                    db.session.add(item)

            db.session.commit()
            return jsonify({
                'sucesso': True,
                'id': pedido.id,
                'numero_pedido': pedido.numero_pedido,
                'mensagem': f'Pedido {pedido.numero_pedido} criado.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar pedido: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/pedidos-carvia/<int:pedido_id>/nf', methods=['PUT'])
    @login_required
    def api_anexar_nf_pedido(pedido_id):
        """Anexa numero de NF ao pedido CarVia e expande provisorio no embarque.

        Body JSON: { "numero_nf": "123456" }

        Fluxo:
        1. Preenche CarviaPedidoItem.numero_nf para todos itens do pedido
        2. Se cotacao esta em embarque → cria EmbarqueItem real (expansao)
        3. Se TODOS pedidos da cotacao tem NF → remove provisorio
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaPedido, CarviaPedidoItem

        pedido = db.session.get(CarviaPedido, pedido_id)
        if not pedido:
            return jsonify({'erro': 'Pedido nao encontrado.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        numero_nf = (data.get('numero_nf') or '').strip()
        if not numero_nf:
            return jsonify({'erro': 'numero_nf e obrigatorio.'}), 400

        try:
            # 1. Preencher numero_nf nos itens do pedido
            itens = CarviaPedidoItem.query.filter_by(pedido_id=pedido_id).all()
            for item in itens:
                item.numero_nf = numero_nf

            # Atualizar status do pedido (cache para queries DB)
            if pedido.status == 'PENDENTE':
                pedido.status = 'FATURADO'

            db.session.flush()

            # 2. Expandir provisorio no embarque (se cotacao esta em algum)
            resultado_expansao = None
            try:
                from app.carvia.services.embarque_carvia_service import EmbarqueCarViaService
                resultado_expansao = EmbarqueCarViaService.expandir_provisorio(
                    carvia_cotacao_id=pedido.cotacao_id,
                    pedido_id=pedido_id,
                    numero_nf=numero_nf,
                )
            except Exception as e:
                logger.warning(
                    "Erro ao expandir provisorio (nao-bloqueante): %s", e
                )

            db.session.commit()

            resposta = {
                'sucesso': True,
                'mensagem': f'NF {numero_nf} anexada ao pedido {pedido.numero_pedido}.',
                'itens_atualizados': len(itens),
                'status_pedido': pedido.status,
            }
            if resultado_expansao:
                resposta['embarque'] = resultado_expansao

            return jsonify(resposta)

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao anexar NF ao pedido %s: %s", pedido_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

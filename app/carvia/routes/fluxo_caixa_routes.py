"""
Rotas de Fluxo de Caixa CarVia
================================

GET /carvia/fluxo-de-caixa - Tela principal
POST /carvia/api/fluxo-caixa/pagar - Marcar como pago
POST /carvia/api/fluxo-caixa/desfazer - Desfazer pagamento
"""

import logging
from datetime import date, timedelta

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def register_fluxo_caixa_routes(bp):

    @bp.route('/fluxo-de-caixa')
    @login_required
    def fluxo_caixa():
        """Tela de fluxo de caixa consolidado."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        # Parametros de filtro
        hoje = date.today()

        data_inicio_str = request.args.get('data_inicio', '')
        data_fim_str = request.args.get('data_fim', '')
        status = request.args.get('status', 'total')

        # Validar datas
        try:
            data_inicio = date.fromisoformat(data_inicio_str) if data_inicio_str else hoje
        except ValueError:
            data_inicio = hoje

        try:
            data_fim = date.fromisoformat(data_fim_str) if data_fim_str else hoje + timedelta(days=30)
        except ValueError:
            data_fim = hoje + timedelta(days=30)

        # Garantir data_fim >= data_inicio
        if data_fim < data_inicio:
            data_fim = data_inicio + timedelta(days=30)

        # Validar status
        if status not in ('total', 'pendente', 'pago'):
            status = 'total'

        # Buscar dados
        from app.carvia.services.fluxo_caixa_service import FluxoCaixaService
        service = FluxoCaixaService()
        fluxo = service.obter_fluxo(data_inicio, data_fim, status)

        return render_template(
            'carvia/fluxo_caixa.html',
            fluxo=fluxo,
            data_inicio=data_inicio.isoformat(),
            data_fim=data_fim.isoformat(),
            status_filtro=status,
        )

    @bp.route('/api/fluxo-caixa/pagar', methods=['POST'])
    @login_required
    def api_fluxo_caixa_pagar():
        """Marca um lancamento como pago."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        tipo_doc = data.get('tipo_doc')
        doc_id = data.get('id')

        if not tipo_doc or not doc_id:
            return jsonify({'erro': 'tipo_doc e id sao obrigatorios'}), 400

        try:
            from app.carvia.models import (
                CarviaFaturaCliente,
                CarviaFaturaTransportadora,
                CarviaDespesa,
            )
            from app.utils.timezone import agora_utc_naive

            if tipo_doc == 'fatura_cliente':
                doc = db.session.get(CarviaFaturaCliente, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Fatura cliente nao encontrada'}), 404
                if doc.status == 'CANCELADA':
                    return jsonify({'erro': 'Fatura cancelada nao pode ser paga'}), 400
                doc.status = 'PAGA'
                novo_status = 'PAGA'

            elif tipo_doc == 'fatura_transportadora':
                doc = db.session.get(CarviaFaturaTransportadora, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Fatura transportadora nao encontrada'}), 404
                doc.status_pagamento = 'PAGO'
                doc.pago_por = current_user.email
                doc.pago_em = agora_utc_naive()
                novo_status = 'PAGO'

            elif tipo_doc == 'despesa':
                doc = db.session.get(CarviaDespesa, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Despesa nao encontrada'}), 404
                if doc.status == 'CANCELADO':
                    return jsonify({'erro': 'Despesa cancelada nao pode ser paga'}), 400
                doc.status = 'PAGO'
                novo_status = 'PAGO'

            else:
                return jsonify({'erro': f'Tipo de documento invalido: {tipo_doc}'}), 400

            db.session.commit()
            logger.info(f"Fluxo caixa: {tipo_doc} #{doc_id} marcado como {novo_status} por {current_user.email}")

            return jsonify({'sucesso': True, 'novo_status': novo_status})

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao marcar pagamento: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/fluxo-caixa/desfazer', methods=['POST'])
    @login_required
    def api_fluxo_caixa_desfazer():
        """Desfaz marcacao de pagamento."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        tipo_doc = data.get('tipo_doc')
        doc_id = data.get('id')

        if not tipo_doc or not doc_id:
            return jsonify({'erro': 'tipo_doc e id sao obrigatorios'}), 400

        try:
            from app.carvia.models import (
                CarviaFaturaCliente,
                CarviaFaturaTransportadora,
                CarviaDespesa,
            )

            if tipo_doc == 'fatura_cliente':
                doc = db.session.get(CarviaFaturaCliente, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Fatura cliente nao encontrada'}), 404
                doc.status = 'PENDENTE'
                novo_status = 'PENDENTE'

            elif tipo_doc == 'fatura_transportadora':
                doc = db.session.get(CarviaFaturaTransportadora, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Fatura transportadora nao encontrada'}), 404
                doc.status_pagamento = 'PENDENTE'
                doc.pago_por = None
                doc.pago_em = None
                novo_status = 'PENDENTE'

            elif tipo_doc == 'despesa':
                doc = db.session.get(CarviaDespesa, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Despesa nao encontrada'}), 404
                doc.status = 'PENDENTE'
                novo_status = 'PENDENTE'

            else:
                return jsonify({'erro': f'Tipo de documento invalido: {tipo_doc}'}), 400

            db.session.commit()
            logger.info(f"Fluxo caixa: {tipo_doc} #{doc_id} desfeito para {novo_status} por {current_user.email}")

            return jsonify({'sucesso': True, 'novo_status': novo_status})

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao desfazer pagamento: {e}")
            return jsonify({'erro': str(e)}), 500

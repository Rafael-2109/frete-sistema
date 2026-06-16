"""
Rotas de Comprovantes de Pagamento CarVia (AJAX)
================================================

Upload/exclusao/download de comprovantes (N:N com cotacao/nf/operacao/fatura
cliente) + toggle da flag "Cotacao Paga". Delega ao CarviaComprovanteService.

Imports do service sao LAZY (R2). O upload propaga o comprovante pela cadeia
automaticamente (CarviaComprovanteService.criar -> sincronizar_cadeia).
"""

import logging

from flask import request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def register_comprovante_routes(bp):

    @bp.route(
        '/api/comprovante/<entidade_tipo>/<int:entidade_id>/upload',
        methods=['POST'],
    )  # type: ignore
    @login_required
    def upload_comprovante_carvia(entidade_tipo, entidade_id):  # type: ignore
        """Upload de comprovante (multipart) + propagacao pela cadeia, via AJAX."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.documentos.comprovante_service import (
            CarviaComprovanteService,
        )
        file = request.files.get('arquivo')
        try:
            comp = CarviaComprovanteService.criar(
                entidade_tipo=entidade_tipo,
                entidade_id=entidade_id,
                file=file,
                usuario=current_user.email,
                valor=request.form.get('valor'),
                data_pagamento=request.form.get('data_pagamento'),
                cnpj_pagador=request.form.get('cnpj_pagador'),
                descricao=request.form.get('descricao', ''),
            )
            db.session.commit()
            return jsonify({
                'sucesso': True,
                'comprovante': {
                    'id': comp.id,
                    'nome_original': comp.nome_original,
                    'tamanho_bytes': comp.tamanho_bytes,
                    'valor': float(comp.valor) if comp.valor is not None else None,
                    'criado_em': (
                        comp.criado_em.isoformat() if comp.criado_em else None
                    ),
                },
            })
        except ValueError as ve:
            db.session.rollback()
            return jsonify({'erro': str(ve)}), 400
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            logger.error(
                "Erro upload comprovante %s#%s: %s", entidade_tipo, entidade_id, e
            )
            return jsonify({'erro': f'Erro ao salvar arquivo: {e}'}), 500

    @bp.route('/api/comprovante/<int:comprovante_id>/excluir', methods=['POST'])  # type: ignore
    @login_required
    def excluir_comprovante_carvia(comprovante_id):  # type: ignore
        """Soft-delete de comprovante (ativo=False) via AJAX."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.documentos.comprovante_service import (
            CarviaComprovanteService,
        )
        try:
            comp = CarviaComprovanteService.soft_delete(comprovante_id)
            if not comp:
                return jsonify({'erro': 'Comprovante nao encontrado.'}), 404
            db.session.commit()
            return jsonify({'sucesso': True})
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            logger.error("Erro excluir comprovante %s: %s", comprovante_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/comprovante/<int:comprovante_id>/download')  # type: ignore
    @login_required
    def download_comprovante_carvia(comprovante_id):  # type: ignore
        """Redirect para URL presigned S3 do comprovante."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaComprovantePagamento
        from app.carvia.services.documentos.comprovante_service import (
            CarviaComprovanteService,
        )
        comp = db.session.get(CarviaComprovantePagamento, comprovante_id)
        if not comp or not comp.ativo:
            flash('Comprovante nao encontrado.', 'warning')
            return redirect(url_for('carvia.dashboard'))

        try:
            url = CarviaComprovanteService.download_url(comp)
            if url:
                return redirect(url)
            flash('Nao foi possivel gerar URL de download.', 'warning')
        except Exception as e:  # noqa: BLE001
            logger.error("Erro download comprovante %s: %s", comprovante_id, e)
            flash(f'Erro: {e}', 'danger')
        return redirect(url_for('carvia.dashboard'))

    @bp.route('/api/cotacao/<int:cotacao_id>/marcar-pago', methods=['POST'])  # type: ignore
    @login_required
    def marcar_pago_cotacao_carvia(cotacao_id):  # type: ignore
        """Liga/desliga a flag 'Cotacao Paga' (pagamento antecipado) via AJAX."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.documentos.comprovante_service import (
            CarviaComprovanteService,
        )
        pago = str(request.form.get('pago', 'true')).lower() in ('1', 'true', 'on', 'sim')
        try:
            cot = CarviaComprovanteService.marcar_pago_cotacao(
                cotacao_id, pago, current_user.email,
            )
            if not cot:
                return jsonify({'erro': 'Cotacao nao encontrada.'}), 404
            db.session.commit()
            return jsonify({'sucesso': True, 'pago': cot.pago})
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            logger.error("Erro marcar pago cotacao %s: %s", cotacao_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

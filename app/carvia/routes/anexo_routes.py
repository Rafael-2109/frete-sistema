"""
Rotas de Anexos polimorficos CarVia (Frete + Subcontrato)
==========================================================

Endpoints AJAX para upload/exclusao/download de anexos comprovatorios em
CarviaFrete e CarviaSubcontrato. Delega ao CarviaAnexoService.

Paridade Nacom: replica os "locais de anexacao" da tela do frete (comprovante
PDF/imagem + e-mail .msg/.eml), agora disponiveis para Frete e Subcontrato.

Despesas (CarviaCustoEntrega) seguem com suas rotas proprias em
custo_entrega_routes.py — esta rota cobre apenas frete e subcontrato.
"""

import logging

from flask import request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app import db
from app.carvia.models.anexos import CarviaAnexo
from app.carvia.services.documentos.anexo_service import CarviaAnexoService

logger = logging.getLogger(__name__)


def register_anexo_routes(bp):

    @bp.route(
        '/api/anexo/<entidade_tipo>/<int:entidade_id>/upload',
        methods=['POST'],
    )  # type: ignore
    @login_required
    def upload_anexo_carvia(entidade_tipo, entidade_id):  # type: ignore
        """Upload de anexo (multipart) para Frete ou Subcontrato via AJAX."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        file = request.files.get('arquivo')
        descricao = request.form.get('descricao', '')

        try:
            anexo = CarviaAnexoService.criar(
                entidade_tipo=entidade_tipo,
                entidade_id=entidade_id,
                file=file,
                usuario=current_user.email,
                descricao=descricao,
            )
            db.session.commit()
            return jsonify({
                'sucesso': True,
                'anexo': {
                    'id': anexo.id,
                    'nome_original': anexo.nome_original,
                    'tamanho_bytes': anexo.tamanho_bytes,
                    'criado_em': (
                        anexo.criado_em.isoformat() if anexo.criado_em else None
                    ),
                },
            })
        except ValueError as ve:
            db.session.rollback()
            return jsonify({'erro': str(ve)}), 400
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            logger.error(
                "Erro upload anexo %s#%s: %s", entidade_tipo, entidade_id, e
            )
            return jsonify({'erro': f'Erro ao salvar arquivo: {e}'}), 500

    @bp.route('/api/anexo/<int:anexo_id>/excluir', methods=['POST'])  # type: ignore
    @login_required
    def excluir_anexo_carvia(anexo_id):  # type: ignore
        """Soft-delete de anexo (ativo=False) via AJAX."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        try:
            anexo = CarviaAnexoService.soft_delete(anexo_id)
            if not anexo:
                return jsonify({'erro': 'Anexo nao encontrado.'}), 404
            db.session.commit()
            return jsonify({'sucesso': True})
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            logger.error("Erro excluir anexo %s: %s", anexo_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/anexo/<int:anexo_id>/download')  # type: ignore
    @login_required
    def download_anexo_carvia(anexo_id):  # type: ignore
        """Redirect para URL presigned S3 do anexo."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        anexo = db.session.get(CarviaAnexo, anexo_id)
        if not anexo or not anexo.ativo:
            flash('Anexo nao encontrado.', 'warning')
            return redirect(url_for('carvia.dashboard'))

        try:
            url = CarviaAnexoService.download_url(anexo)
            if url:
                return redirect(url)
            flash('Nao foi possivel gerar URL de download.', 'warning')
        except Exception as e:  # noqa: BLE001
            logger.error("Erro download anexo %s: %s", anexo_id, e)
            flash(f'Erro: {e}', 'danger')

        # Fallback: voltar para a tela da entidade
        if anexo.entidade_tipo == CarviaAnexo.ENTIDADE_FRETE:
            return redirect(
                url_for('carvia.detalhe_frete_carvia', id=anexo.entidade_id)
            )
        if anexo.entidade_tipo == CarviaAnexo.ENTIDADE_SUBCONTRATO:
            return redirect(
                url_for('carvia.detalhe_subcontrato', sub_id=anexo.entidade_id)
            )
        return redirect(url_for('carvia.dashboard'))

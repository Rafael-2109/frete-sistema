"""Rotas de Carta de Correção (CCe) CarVia (AJAX). Delega ao
CarviaCartaCorrecaoService. Imports do service são LAZY (R2). Upload propaga
pela cadeia cotacao<->nf automaticamente."""
import logging

from flask import request, redirect, url_for, flash, jsonify, render_template
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def register_carta_correcao_routes(bp):

    @bp.route('/api/carta-correcao/<entidade_tipo>/<int:entidade_id>/upload',
              methods=['POST'])  # type: ignore
    @login_required
    def upload_carta_correcao(entidade_tipo, entidade_id):  # type: ignore
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403
        from app.carvia.services.documentos.carta_correcao_service import (
            CarviaCartaCorrecaoService,
        )
        file = request.files.get('arquivo')
        try:
            carta = CarviaCartaCorrecaoService.criar(
                entidade_tipo=entidade_tipo, entidade_id=entidade_id,
                file=file, usuario=current_user.email,
                descricao=request.form.get('descricao', ''),
            )
            db.session.commit()
            return jsonify({'sucesso': True, 'carta': {
                'id': carta.id, 'nome_original': carta.nome_original,
                'tamanho_bytes': carta.tamanho_bytes,
                'criado_em': carta.criado_em.isoformat() if carta.criado_em else None,
            }})
        except ValueError as ve:
            db.session.rollback()
            return jsonify({'erro': str(ve)}), 400
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            logger.error("Erro upload CCe %s#%s: %s", entidade_tipo, entidade_id, e)
            return jsonify({'erro': f'Erro ao salvar arquivo: {e}'}), 500

    @bp.route('/api/carta-correcao/<int:carta_id>/excluir', methods=['POST'])  # type: ignore
    @login_required
    def excluir_carta_correcao(carta_id):  # type: ignore
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403
        from app.carvia.services.documentos.carta_correcao_service import (
            CarviaCartaCorrecaoService,
        )
        try:
            carta = CarviaCartaCorrecaoService.soft_delete(carta_id)
            if not carta:
                return jsonify({'erro': 'Carta de correcao nao encontrada.'}), 404
            db.session.commit()
            return jsonify({'sucesso': True})
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            logger.error("Erro excluir CCe %s: %s", carta_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/carta-correcao/<int:carta_id>/download')  # type: ignore
    @login_required
    def download_carta_correcao(carta_id):  # type: ignore
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('carvia.dashboard'))
        from app.carvia.models import CarviaCartaCorrecao
        from app.carvia.services.documentos.carta_correcao_service import (
            CarviaCartaCorrecaoService,
        )
        carta = db.session.get(CarviaCartaCorrecao, carta_id)
        if not carta or not carta.ativo:
            flash('Carta de correcao nao encontrada.', 'warning')
            return redirect(url_for('carvia.dashboard'))
        try:
            url = CarviaCartaCorrecaoService.download_url(carta)
            if url:
                return redirect(url)
            flash('Nao foi possivel gerar URL de download.', 'warning')
        except Exception as e:  # noqa: BLE001
            logger.error("Erro download CCe %s: %s", carta_id, e)
            flash(f'Erro: {e}', 'danger')
        return redirect(url_for('carvia.dashboard'))

    @bp.route('/cartas-correcao/imprimir')  # type: ignore
    @login_required
    def imprimir_cce():  # type: ignore
        """Imprime as CCe de uma NF (?nf_id=) como folhas (window.print)."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('carvia.dashboard'))
        nf_id = request.args.get('nf_id', type=int)
        from app.carvia.services.documentos.carta_correcao_service import (
            CarviaCartaCorrecaoService,
        )
        from app.carvia.services.documentos.cce_render import render_cces_para_impressao
        cces = CarviaCartaCorrecaoService.listar('nf', nf_id) if nf_id else []
        paginas = render_cces_para_impressao(cces)
        return render_template('carvia/nfs/imprimir_cce.html',
                               cces=paginas, nf_id=nf_id)

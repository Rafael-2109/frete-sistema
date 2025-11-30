"""
APIs de Pendência Financeira (Modal)
Usado pelo modal na listagem de Contas a Receber
Fluxo: Financeiro cria pendência → Logística responde
"""

from flask import request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from app import db
from app.financeiro.routes import financeiro_bp


# ========================================
# API: PENDÊNCIAS FINANCEIRAS (usadas pelo modal)
# ========================================

@financeiro_bp.route('/contas-receber/api/pendencia-financeira', methods=['POST'])
@login_required
def api_criar_pendencia_financeira():
    """
    Cria uma nova pendência financeira vinculada a uma NF
    """
    try:
        from app.financeiro.models import PendenciaFinanceiraNF, ContasAReceber

        data = request.get_json()
        numero_nf = data.get('numero_nf')
        observacao = data.get('observacao')
        conta_id = data.get('conta_id')

        if not numero_nf and not conta_id:
            return jsonify({'success': False, 'error': 'NF ou conta_id é obrigatório'}), 400

        # Se passou conta_id, buscar a NF
        entrega_id = None
        if conta_id:
            conta = ContasAReceber.query.get(conta_id)
            if conta:
                numero_nf = conta.titulo_nf
                if conta.entrega_monitorada_id:
                    entrega_id = conta.entrega_monitorada_id

        pendencia = PendenciaFinanceiraNF(
            numero_nf=numero_nf,
            observacao=observacao,
            entrega_id=entrega_id,
            criado_por=current_user.nome
        )

        db.session.add(pendencia)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Pendência registrada com sucesso!',
            'pendencia_id': pendencia.id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/api/pendencia-financeira/<int:pendencia_id>/resposta', methods=['POST'])
@login_required
def api_responder_pendencia_financeira(pendencia_id):
    """
    Responde a uma pendência financeira (usado pela logística)
    """
    try:
        from app.financeiro.models import PendenciaFinanceiraNF

        pendencia = PendenciaFinanceiraNF.query.get_or_404(pendencia_id)
        data = request.get_json()

        pendencia.resposta_logistica = data.get('resposta')
        pendencia.respondida_em = datetime.utcnow()
        pendencia.respondida_por = current_user.nome

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Resposta registrada com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/api/<int:conta_id>/pendencias')
@login_required
def api_listar_pendencias_conta(conta_id):
    """
    Lista pendências financeiras de uma conta específica
    """
    try:
        from app.financeiro.models import ContasAReceber, PendenciaFinanceiraNF

        conta = ContasAReceber.query.get_or_404(conta_id)

        # Buscar pendências pela NF
        pendencias = PendenciaFinanceiraNF.query.filter_by(
            numero_nf=conta.titulo_nf
        ).order_by(PendenciaFinanceiraNF.criado_em.desc()).all()

        return jsonify({
            'success': True,
            'titulo_nf': conta.titulo_nf,
            'pendencias': [{
                'id': p.id,
                'observacao': p.observacao,
                'criado_em': p.criado_em.isoformat() if p.criado_em else None,
                'criado_por': p.criado_por,
                'resposta_logistica': p.resposta_logistica,
                'respondida_em': p.respondida_em.isoformat() if p.respondida_em else None,
                'respondida_por': p.respondida_por,
                'tem_resposta': p.respondida_em is not None
            } for p in pendencias]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

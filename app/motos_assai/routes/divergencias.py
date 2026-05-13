"""Rotas de Divergencias (Plano 3 Fase 4).

Spec: §7
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase4-nf-divergencias.md Tasks 14-22

Rotas:
- GET /motos-assai/divergencias              - Lista divergencias com filtros
- POST /motos-assai/divergencias/<id>/resolver - AJAX resolver divergencia

N-B1 fix: decorators (login_required + require_motos_assai) APENAS na rota
GET de tela. Rotas AJAX validam sessao via Flask-Login automaticamente.
"""
from __future__ import annotations

from flask import render_template, request, jsonify
from flask_login import login_required, current_user

from app import db
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.models import (
    AssaiDivergencia, AssaiNfQpa, AssaiSeparacao, AssaiCarregamento,
    DIVERGENCIA_TIPOS_VALIDOS, DIVERGENCIA_RESOLUCAO_VALIDAS,
    DIVERGENCIA_RESOLUCAO_CANCELAR_NF,
    DIVERGENCIA_RESOLUCAO_CCE,
    DIVERGENCIA_RESOLUCAO_ALTERAR_CARREGAMENTO,
    DIVERGENCIA_RESOLUCAO_SUBSTITUIR_CHASSI,
    DIVERGENCIA_RESOLUCAO_IGNORAR,
)
from app.motos_assai.services.divergencia_service import (
    resolver_divergencia, DivergenciaError,
)


@motos_assai_bp.route('/divergencias')
@login_required
@require_motos_assai
def divergencias_lista():
    """Lista divergencias com filtros (status / tipo).

    Filtros via query string:
    - status: pendentes (default) | resolvidas | todas
    - tipo: DIVERGENCIA_TIPO_* (opcional)
    """
    status_filtro = (request.args.get('status') or 'pendentes').lower()
    tipo_filtro = request.args.get('tipo') or ''

    q = AssaiDivergencia.query
    if status_filtro == 'pendentes':
        q = q.filter(AssaiDivergencia.resolvida_em.is_(None))
    elif status_filtro == 'resolvidas':
        q = q.filter(AssaiDivergencia.resolvida_em.isnot(None))

    if tipo_filtro and tipo_filtro in DIVERGENCIA_TIPOS_VALIDOS:
        q = q.filter(AssaiDivergencia.tipo == tipo_filtro)

    divergencias = q.order_by(AssaiDivergencia.criada_em.desc()).limit(500).all()

    # Pre-carregar NFs/Seps/Carregamentos referenciados para evitar N+1 em template
    nf_ids = {d.nf_id for d in divergencias if d.nf_id}
    sep_ids = {d.separacao_id for d in divergencias if d.separacao_id}
    car_ids = {d.carregamento_id for d in divergencias if d.carregamento_id}

    nfs_por_id = {
        nf.id: nf for nf in AssaiNfQpa.query.filter(AssaiNfQpa.id.in_(nf_ids)).all()
    } if nf_ids else {}
    seps_por_id = {
        s.id: s for s in AssaiSeparacao.query.filter(AssaiSeparacao.id.in_(sep_ids)).all()
    } if sep_ids else {}
    cars_por_id = {
        c.id: c for c in AssaiCarregamento.query.filter(AssaiCarregamento.id.in_(car_ids)).all()
    } if car_ids else {}

    contadores = {
        'pendentes': AssaiDivergencia.query.filter(
            AssaiDivergencia.resolvida_em.is_(None)
        ).count(),
        'resolvidas': AssaiDivergencia.query.filter(
            AssaiDivergencia.resolvida_em.isnot(None)
        ).count(),
    }

    return render_template(
        'motos_assai/divergencias/lista.html',
        divergencias=divergencias,
        nfs_por_id=nfs_por_id,
        seps_por_id=seps_por_id,
        cars_por_id=cars_por_id,
        status_filtro=status_filtro,
        tipo_filtro=tipo_filtro,
        contadores=contadores,
        DIVERGENCIA_TIPOS_VALIDOS=sorted(DIVERGENCIA_TIPOS_VALIDOS),
        DIVERGENCIA_RESOLUCAO_VALIDAS=sorted(DIVERGENCIA_RESOLUCAO_VALIDAS),
    )


@motos_assai_bp.route('/divergencias/<int:div_id>/resolver', methods=['POST'])
def divergencias_resolver(div_id):
    """AJAX resolver divergencia (N-B1: sem decorator de tela).

    Body JSON:
        {
            "tipo_resolucao": "IGNORAR" | "CANCELAR_NF" | ...,
            "observacao": "texto",
            "extras": {...}  // opcional, para tipos especificos
        }

    Returns:
        200 {ok: true, divergencia_id: N}
        400 {ok: false, erro: "..."}
        403 {error: "..."}
    """
    if not current_user.is_authenticated:
        return jsonify({'error': 'Sessao expirada'}), 401
    if not current_user.pode_acessar_motos_assai():
        return jsonify({'error': 'Acesso negado'}), 403

    payload = request.get_json(silent=True) or {}
    tipo_resolucao = (payload.get('tipo_resolucao') or '').strip()
    observacao = (payload.get('observacao') or '').strip()
    extras = payload.get('extras') or {}

    try:
        # Operacoes especificas por tipo de resolucao
        if tipo_resolucao == DIVERGENCIA_RESOLUCAO_CANCELAR_NF:
            # Acao: cancelar NF Q.P.A. (cascata completa)
            div = AssaiDivergencia.query.get_or_404(div_id)
            if not div.nf_id:
                return jsonify({
                    'ok': False,
                    'erro': 'Divergencia sem NF associada — nao aplica CANCELAR_NF',
                }), 400
            from app.motos_assai.services.cancelamento_nf_service import (
                cancelar_nf_qpa, CancelamentoValidationError,
            )
            try:
                cancelar_nf_qpa(div.nf_id, motivo=observacao or 'Resolucao via UI divergencias',
                                operador_id=current_user.id)
            except CancelamentoValidationError as e:
                return jsonify({'ok': False, 'erro': str(e)}), 400

        elif tipo_resolucao == DIVERGENCIA_RESOLUCAO_CCE:
            # Placeholder Plano 4 — apenas marca como resolvida (sem swap chassis)
            pass

        elif tipo_resolucao == DIVERGENCIA_RESOLUCAO_ALTERAR_CARREGAMENTO:
            # Acao: alterar carregamento (Plano 2 ja tem service)
            car_id = extras.get('carregamento_id')
            if car_id:
                try:
                    from app.motos_assai.services.carregamento_service import (
                        alterar_carregamento,
                    )
                    novos_chassis = extras.get('chassis') or []
                    motivo = extras.get('motivo') or observacao or 'via divergencias'
                    alterar_carregamento(
                        carregamento_id=car_id,
                        novos_chassis=novos_chassis,
                        motivo=motivo, operador_id=current_user.id,
                    )
                except Exception as e:
                    return jsonify({'ok': False, 'erro': str(e)}), 400

        elif tipo_resolucao == DIVERGENCIA_RESOLUCAO_SUBSTITUIR_CHASSI:
            # Placeholder Plano 4 — apenas marca como resolvida
            pass

        # Comum a todos: marcar divergencia resolvida + S21 re-roda match (se aplicavel)
        resolver_divergencia(
            div_id=div_id, tipo_resolucao=tipo_resolucao,
            observacao=observacao, operador_id=current_user.id,
        )
        db.session.commit()
        return jsonify({'ok': True, 'divergencia_id': div_id})

    except DivergenciaError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).exception(
            'Erro inesperado ao resolver divergencia %s', div_id,
        )
        return jsonify({'ok': False, 'erro': f'Erro interno: {e}'}), 500

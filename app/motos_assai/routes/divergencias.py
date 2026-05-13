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
        return jsonify({'ok': False, 'erro': 'Sessao expirada'}), 401
    if not current_user.pode_acessar_motos_assai():
        return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403

    payload = request.get_json(silent=True) or {}
    tipo_resolucao = (payload.get('tipo_resolucao') or '').strip()
    observacao = (payload.get('observacao') or '').strip()
    extras = payload.get('extras') or {}

    # Code review fix H9 (2026-05-13): validar tipo_resolucao contra set permitido
    # antes de qualquer logica de negocio (defesa em profundidade — service tambem valida).
    if tipo_resolucao not in DIVERGENCIA_RESOLUCAO_VALIDAS:
        return jsonify({
            'ok': False,
            'erro': f'tipo_resolucao invalido: {tipo_resolucao!r}. '
                    f'Validos: {sorted(DIVERGENCIA_RESOLUCAO_VALIDAS)}',
        }), 400

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


@motos_assai_bp.route('/divergencias/<int:div_id>/upload-cce', methods=['POST'])
def divergencias_upload_cce(div_id):
    """Plano 4 Task 10 — Upload PDF CCe + parser deterministico + LLM fallback +
    aplicar_correcao_cce + marcar divergencia como resolvida (tipo=CCE).

    Form data:
        cce_pdf: file upload (PDF)

    N-B1: sem decorator de tela; valida sessao manualmente.

    Aceita resolver divergencias do tipo NF_CHASSI_FORA_CARREGAMENTO ou
    CHASSI_OUTRA_LOJA (ambos podem ser corrigidos via CCe).
    """
    from app.motos_assai.models import (
        AssaiDivergencia,
        DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO,
        DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
        DIVERGENCIA_RESOLUCAO_CCE,
    )

    if not current_user.is_authenticated:
        return jsonify({'ok': False, 'erro': 'Sessao expirada'}), 401
    if not current_user.pode_acessar_motos_assai():
        return jsonify({'ok': False, 'erro': 'Acesso negado'}), 403

    div = AssaiDivergencia.query.get_or_404(div_id)
    if div.resolvida_em is not None:
        return jsonify({
            'ok': False,
            'erro': f'Divergencia ja resolvida em {div.resolvida_em}',
        }), 400

    # Plano 4 spec §7.3: CCe resolve principalmente NF_CHASSI_FORA_CARREGAMENTO,
    # mas tambem pode resolver CHASSI_OUTRA_LOJA (chassi corrigido apontava para
    # outra loja). Outros tipos exigem outra resolucao.
    tipos_validos_cce = {
        DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO,
        DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
    }
    if div.tipo not in tipos_validos_cce:
        return jsonify({
            'ok': False,
            'erro': (
                f'CCe nao resolve divergencia tipo {div.tipo}. '
                f'Tipos validos: {sorted(tipos_validos_cce)}'
            ),
        }), 400

    if not div.nf_id:
        return jsonify({
            'ok': False,
            'erro': 'Divergencia sem NF associada — CCe precisa de NF',
        }), 400

    pdf_file = request.files.get('cce_pdf')
    if not pdf_file or not pdf_file.filename:
        return jsonify({'ok': False, 'erro': 'PDF da CCe obrigatorio'}), 400
    if not pdf_file.filename.lower().endswith('.pdf'):
        return jsonify({'ok': False, 'erro': 'Apenas arquivos PDF'}), 400

    try:
        pdf_bytes = pdf_file.read()
        if not pdf_bytes:
            return jsonify({'ok': False, 'erro': 'PDF vazio'}), 400

        # 1. Parser deterministico
        from app.motos_assai.services.parsers.cce_pdf_extractor import (
            extrair_cce, CceParseError, CONFIANCA_LIMIAR,
        )
        parser_usado = 'DETERMINISTICO'
        try:
            dados = extrair_cce(pdf_bytes)
        except CceParseError as e:
            # Parser falhou criticamente — pular para LLM
            import logging
            logging.getLogger(__name__).info(
                'cce_pdf_extractor falhou (%s) — escalando para LLM', e,
            )
            dados = {'confianca': 0.0, 'chassis_corrigidos': []}

        # 2. Fallback LLM se confianca baixa.
        # Code review fix M2 (2026-05-13): `<` exclui o limite exato (0.80),
        # mas confianca EXATAMENTE no limiar (heuristica deu pontuacao maxima
        # via fallback) deve acionar LLM tambem — borderline e arriscado.
        # Tornado inclusive (`<=`).
        if dados.get('confianca', 0.0) <= CONFIANCA_LIMIAR:
            try:
                from app.motos_assai.services.parsers.cce_llm_fallback import (
                    extrair_cce_via_llm, CceLlmFallbackError,
                )
                dados_llm = extrair_cce_via_llm(pdf_bytes)
                # LLM ganhou confianca?
                if dados_llm.get('confianca', 0) >= dados.get('confianca', 0):
                    dados = dados_llm
                    parser_usado = dados_llm.get('parser_usado', 'LLM')
            except CceLlmFallbackError as e:
                import logging
                logging.getLogger(__name__).warning(
                    'cce_llm_fallback falhou: %s — usando dados deterministicos parciais', e,
                )

        # 3. Validar chassis_corrigidos
        chassis_corrigidos = dados.get('chassis_corrigidos') or []
        if not chassis_corrigidos:
            return jsonify({
                'ok': False,
                'erro': (
                    'CCe nao tem chassis corrigidos identificados. '
                    f'Confianca parser: {dados.get("confianca", 0):.2f}. '
                    'Verifique o PDF ou aplique manualmente.'
                ),
                'confianca': dados.get('confianca', 0),
            }), 400

        # 4. Aplicar correcao na NF (S16: registra vinculo historico antes; S21+A14: re-roda match)
        from app.motos_assai.services.cancelamento_nf_service import (
            aplicar_correcao_cce, CancelamentoValidationError,
        )
        from app.motos_assai.services.divergencia_service import (
            resolver_divergencia, DivergenciaError,
        )

        try:
            aplicar_correcao_cce(
                nf_id=div.nf_id,
                chassis_corrigidos=chassis_corrigidos,
                numero_cce=dados.get('numero_cce') or 'CCE-SEM-NUMERO',
                operador_id=current_user.id,
            )
        except CancelamentoValidationError as e:
            db.session.rollback()
            return jsonify({'ok': False, 'erro': str(e)}), 400

        # 5. Marca divergencia como resolvida tipo=CCE (re-roda _calcular_match via S21)
        try:
            resolver_divergencia(
                div_id=div_id,
                tipo_resolucao=DIVERGENCIA_RESOLUCAO_CCE,
                observacao=(
                    f'CCe {dados.get("numero_cce") or "(sem numero)"} aplicada — '
                    f'{len(chassis_corrigidos)} chassis trocados (parser={parser_usado})'
                ),
                operador_id=current_user.id,
            )
        except DivergenciaError as e:
            db.session.rollback()
            return jsonify({'ok': False, 'erro': str(e)}), 400

        db.session.commit()

        return jsonify({
            'ok': True,
            'numero_cce': dados.get('numero_cce'),
            'numero_nf_referenciada': dados.get('numero_nf_referenciada'),
            'chassis_trocados': len(chassis_corrigidos),
            'chassis_corrigidos_aplicados': chassis_corrigidos,
            'confianca': dados.get('confianca', 0),
            'parser_usado': parser_usado,
            'divergencia_id': div_id,
        })

    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).exception(
            'Erro inesperado ao processar upload CCe (div=%s)', div_id,
        )
        return jsonify({'ok': False, 'erro': f'Erro interno: {e}'}), 500

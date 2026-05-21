"""Rotas de Divergencias (Plano 3 Fase 4).

Spec: §7
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase4-nf-divergencias.md Tasks 14-22

Rotas:
- GET /motos-assai/divergencias              - Lista divergencias com filtros
- POST /motos-assai/divergencias/<id>/resolver - AJAX resolver divergencia

N-B1 fix: decorators (login_required + require_motos_assai) APENAS na rota
GET de tela. Rotas AJAX validam sessao via Flask-Login automaticamente.

2026-05-13: filtros expandidos — status, tipo, chassi, numero_nf, loja_id,
data_inicio, data_fim, resolvida_por_id. Lojas + operadores resolvedores
populados para autocomplete (select).
"""
from __future__ import annotations

from datetime import date, datetime, time

from flask import render_template, request, jsonify
from flask_login import login_required, current_user

from app import db
from app.auth.models import Usuario
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.models import (
    AssaiDivergencia, AssaiNfQpa, AssaiSeparacao, AssaiCarregamento, AssaiLoja,
    AssaiMoto,
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
from app.motos_assai.services.modelo_service import listar_modelos


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), '%Y-%m-%d').date()
    except (ValueError, AttributeError):
        return None


@motos_assai_bp.route('/divergencias')
@login_required
@require_motos_assai
def divergencias_lista():
    """Lista divergencias com filtros amplos.

    Filtros via query string:
    - status: pendentes (default) | resolvidas | todas
    - tipo: DIVERGENCIA_TIPO_* (opcional)
    - chassi: ilike %chassi% em AssaiDivergencia.chassi
    - numero_nf: ilike %numero% em AssaiNfQpa.numero (JOIN via div.nf_id)
    - loja_id: filtra por loja em sep.loja_id OU nf.loja_id (qualquer um)
    - data_inicio / data_fim: AssaiDivergencia.criada_em
    - resolvida_por_id: usuario que resolveu (apenas resolvidas)
    """
    status_filtro = (request.args.get('status') or 'pendentes').lower()
    tipo_filtro = request.args.get('tipo') or ''
    chassi_filtro = (request.args.get('chassi') or '').strip()
    numero_nf_filtro = (request.args.get('numero_nf') or '').strip()
    loja_id_filtro = request.args.get('loja_id', type=int)
    data_inicio_filtro = _parse_date(request.args.get('data_inicio'))
    data_fim_filtro = _parse_date(request.args.get('data_fim'))
    resolvida_por_filtro = request.args.get('resolvida_por_id', type=int)
    modelo_id_filtro = request.args.get('modelo_id', type=int)

    q = AssaiDivergencia.query

    # Status
    if status_filtro == 'pendentes':
        q = q.filter(AssaiDivergencia.resolvida_em.is_(None))
    elif status_filtro == 'resolvidas':
        q = q.filter(AssaiDivergencia.resolvida_em.isnot(None))

    # Tipo
    if tipo_filtro and tipo_filtro in DIVERGENCIA_TIPOS_VALIDOS:
        q = q.filter(AssaiDivergencia.tipo == tipo_filtro)

    # Chassi (ilike)
    if chassi_filtro:
        q = q.filter(AssaiDivergencia.chassi.ilike(f'%{chassi_filtro.upper()}%'))

    # Modelo (2026-05-20): resolve via chassi -> assai_moto. So pega
    # divergencias cujo chassi esta cadastrado em AssaiMoto do modelo informado.
    if modelo_id_filtro:
        chassis_do_modelo = db.session.query(AssaiMoto.chassi).filter(
            AssaiMoto.modelo_id == modelo_id_filtro
        )
        q = q.filter(AssaiDivergencia.chassi.in_(chassis_do_modelo))

    # Datas (criada_em)
    if data_inicio_filtro:
        q = q.filter(
            AssaiDivergencia.criada_em >= datetime.combine(data_inicio_filtro, time.min)
        )
    if data_fim_filtro:
        q = q.filter(
            AssaiDivergencia.criada_em <= datetime.combine(data_fim_filtro, time.max)
        )

    # Resolvido por (apenas para resolvidas)
    if resolvida_por_filtro:
        q = q.filter(AssaiDivergencia.resolvida_por_id == resolvida_por_filtro)

    # NF (numero) e Loja: JOINs opcionais
    if numero_nf_filtro:
        q = (
            q.join(AssaiNfQpa, AssaiDivergencia.nf_id == AssaiNfQpa.id)
            .filter(AssaiNfQpa.numero.ilike(f'%{numero_nf_filtro}%'))
        )

    if loja_id_filtro:
        # Loja pode estar em sep.loja_id OU nf.loja_id — match qualquer um
        sep_ids_da_loja = db.session.query(AssaiSeparacao.id).filter(
            AssaiSeparacao.loja_id == loja_id_filtro,
        ).subquery()
        nf_ids_da_loja = db.session.query(AssaiNfQpa.id).filter(
            AssaiNfQpa.loja_id == loja_id_filtro,
        ).subquery()
        q = q.filter(
            db.or_(
                AssaiDivergencia.separacao_id.in_(db.session.query(sep_ids_da_loja.c.id)),
                AssaiDivergencia.nf_id.in_(db.session.query(nf_ids_da_loja.c.id)),
            )
        )

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

    # Lojas para o filtro: todas as ativas + qualquer uma referenciada por sep/nf
    # (caso loja tenha sido desativada mas tenha divergencias historicas)
    lojas_referenciadas_ids = set()
    for s in seps_por_id.values():
        if getattr(s, 'loja_id', None):
            lojas_referenciadas_ids.add(s.loja_id)
    for n in nfs_por_id.values():
        if getattr(n, 'loja_id', None):
            lojas_referenciadas_ids.add(n.loja_id)
    lojas_q = AssaiLoja.query
    if lojas_referenciadas_ids:
        lojas_q = lojas_q.filter(
            db.or_(AssaiLoja.ativo == True, AssaiLoja.id.in_(lojas_referenciadas_ids))  # noqa: E712
        )
    else:
        lojas_q = lojas_q.filter(AssaiLoja.ativo == True)  # noqa: E712
    lojas_disponiveis = lojas_q.order_by(AssaiLoja.numero).all()

    # Operadores que JA resolveram divergencias (para autocomplete do filtro)
    operadores_ids = (
        db.session.query(AssaiDivergencia.resolvida_por_id)
        .filter(AssaiDivergencia.resolvida_por_id.isnot(None))
        .distinct()
        .all()
    )
    op_ids = [oid for (oid,) in operadores_ids]
    operadores_resolvedores = []
    if op_ids:
        operadores_resolvedores = (
            Usuario.query
            .filter(Usuario.id.in_(op_ids))
            .order_by(Usuario.nome)
            .all()
        )

    contadores = {
        'pendentes': AssaiDivergencia.query.filter(
            AssaiDivergencia.resolvida_em.is_(None)
        ).count(),
        'resolvidas': AssaiDivergencia.query.filter(
            AssaiDivergencia.resolvida_em.isnot(None)
        ).count(),
    }

    filtros_aplicados = {
        'status': status_filtro,
        'tipo': tipo_filtro,
        'chassi': chassi_filtro,
        'modelo_id': modelo_id_filtro,
        'numero_nf': numero_nf_filtro,
        'loja_id': loja_id_filtro,
        'data_inicio': data_inicio_filtro,
        'data_fim': data_fim_filtro,
        'resolvida_por_id': resolvida_por_filtro,
    }

    return render_template(
        'motos_assai/divergencias/lista.html',
        divergencias=divergencias,
        nfs_por_id=nfs_por_id,
        seps_por_id=seps_por_id,
        cars_por_id=cars_por_id,
        # Backwards-compat para template: campos individuais usados antes
        status_filtro=status_filtro,
        tipo_filtro=tipo_filtro,
        # Novos filtros
        filtros_aplicados=filtros_aplicados,
        lojas_disponiveis=lojas_disponiveis,
        operadores_resolvedores=operadores_resolvedores,
        modelos=listar_modelos(somente_ativos=True),
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
            # Pacote C (2026-05-13): impl. real — chama substituir_chassi_entre_seps
            # com via_divergencia=True (permite origem FATURADA/CARREGADA, que e o
            # caso de uso principal desta resolucao).
            sep_origem_id = extras.get('sep_origem_id')
            sep_destino_id = extras.get('sep_destino_id')
            chassi_alvo = (extras.get('chassi') or '').strip()
            if not sep_origem_id or not sep_destino_id:
                return jsonify({
                    'ok': False,
                    'erro': 'sep_origem_id e sep_destino_id obrigatorios em extras',
                }), 400
            if not chassi_alvo:
                # Fallback: usa chassi da propria divergencia
                div_obj = AssaiDivergencia.query.get_or_404(div_id)
                chassi_alvo = (div_obj.chassi or '').strip()
                if not chassi_alvo:
                    return jsonify({
                        'ok': False,
                        'erro': 'Divergencia sem chassi — substituicao requer chassi',
                    }), 400
            from app.motos_assai.services.separacao_service import (
                substituir_chassi_entre_seps, SeparacaoValidationError,
            )
            try:
                substituir_chassi_entre_seps(
                    chassi=chassi_alvo,
                    sep_origem_id=int(sep_origem_id),
                    sep_destino_id=int(sep_destino_id),
                    operador_id=current_user.id,
                    via_divergencia=True,
                )
            except SeparacaoValidationError as e:
                return jsonify({'ok': False, 'erro': str(e)}), 400

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

        # Delega para cce_service — fluxo unificado entre upload via divergencia
        # e upload avulso (2026-05-13).
        # - Registra AssaiCce (idempotente via UNIQUE protocolo_cce)
        # - Resolve NF (chave_44 ou numero), aplica chassis se tipo=CHASSI
        # - Fecha divergencia (tipo=CCE) ao final
        from app.motos_assai.services.cce_service import (
            registrar_cce, CceServiceError,
        )

        try:
            resultado = registrar_cce(
                pdf_bytes=pdf_bytes,
                nome_arquivo=pdf_file.filename or 'cce.pdf',
                operador_id=current_user.id,
                divergencia_id=div_id,
            )
        except CceServiceError as e:
            return jsonify({'ok': False, 'erro': str(e)}), 400

        # Status APLICADA = chassis trocados E divergencia fechada com sucesso
        if resultado['status'] != 'APLICADA':
            tipo = resultado.get('tipo_correcao') or 'OUTRO'
            # Tipos IGNORADA (DUPLICATAS/ENDERECO) — registrado mas nao resolve divergencia
            if tipo in ('DUPLICATAS', 'ENDERECO'):
                erro = (
                    f'CCe e de tipo {tipo} — nao altera chassis. '
                    f'A divergencia continua aberta. '
                    f'{"Aplique manualmente no financeiro." if tipo == "DUPLICATAS" else "Atualize o endereco manualmente."}'
                )
            elif resultado['status'] == 'PENDENTE':
                erro = (
                    'CCe registrada mas a NF referenciada nao corresponde a esta '
                    'divergencia. Verifique se PDF e da NF correta.'
                )
            else:
                erro = resultado.get('mensagem') or 'CCe nao aplicada.'
            return jsonify({
                'ok': False,
                'erro': erro,
                'cce_id': resultado['cce_id'],
                'status': resultado['status'],
                'tipo_correcao': tipo,
                'confianca': resultado.get('confianca', 0),
            }), 400

        return jsonify({
            'ok': True,
            'cce_id': resultado['cce_id'],
            'status': resultado['status'],
            'chassis_trocados': len(resultado.get('chassis_aplicados') or []),
            'chassis_corrigidos_aplicados': resultado.get('chassis_aplicados') or [],
            'confianca': resultado.get('confianca', 0),
            'parser_usado': resultado.get('parser_usado'),
            'divergencia_id': div_id,
            'duplicada': resultado.get('duplicada', False),
        })

    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).exception(
            'Erro inesperado ao processar upload CCe (div=%s)', div_id,
        )
        return jsonify({'ok': False, 'erro': f'Erro interno: {e}'}), 500

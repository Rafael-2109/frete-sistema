"""Rotas de unificacao de modelos:

  /hora/modelos/pendencias               -> listar pendentes
  /hora/modelos/pendencias/<id>/vincular -> vincular a modelo existente (alias)
  /hora/modelos/pendencias/<id>/criar    -> criar modelo novo a partir da pendencia
  /hora/modelos/pendencias/<id>/ignorar  -> marcar como ignorada

  /hora/modelos/unificar                 -> tela de merge (escolher canonico+aliases)
  /hora/modelos/unificar/preview         -> dry-run merge
  /hora/modelos/unificar/executar        -> aplica merge fisico atomico

  /hora/modelos/<id>/aliases             -> listar/adicionar/remover aliases manuais
  /hora/modelos/<id>/aliases/criar       -> POST adiciona alias
  /hora/modelos/<id>/aliases/<aid>/del   -> POST remove alias

Migration hora_29.
"""
from __future__ import annotations

from flask import (
    flash, jsonify, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required

from app import db
from app.hora.decorators import require_hora_perm
from app.hora.models import (
    HoraModelo,
    HoraModeloAlias,
    HoraModeloPendente,
    HoraTagPlusProdutoMap,
    ALIAS_TIPOS_VALIDOS,
    PENDENTE_STATUS_PENDENTE,
    PENDENTE_STATUS_VALIDOS,
)
from app.hora.routes import hora_bp
from app.hora.services.modelo_resolver_service import (
    vincular_pendencia_a_modelo,
    criar_modelo_de_pendencia,
    ignorar_pendencia,
)
from app.hora.services.modelo_merge_service import (
    MergeError,
    merge_modelos,
    preview_merge,
)


# ============================================================================
# Pendencias
# ============================================================================

@hora_bp.route('/modelos/pendencias')
@require_hora_perm('modelos', 'ver')
@login_required
def modelos_pendencias_lista():
    status = (request.args.get('status') or PENDENTE_STATUS_PENDENTE).strip()
    if status not in PENDENTE_STATUS_VALIDOS:
        status = PENDENTE_STATUS_PENDENTE

    query = HoraModeloPendente.query.filter_by(status=status)
    pendencias = query.order_by(
        HoraModeloPendente.qtd_ocorrencias.desc(),
        HoraModeloPendente.ultimo_visto.desc(),
    ).all()

    # Lista modelos ativos para o select de "vincular"
    modelos = (
        HoraModelo.query
        .filter(HoraModelo.ativo.is_(True))
        .filter(HoraModelo.merged_em_id.is_(None))
        .order_by(HoraModelo.nome_modelo)
        .all()
    )

    contadores = {
        s: HoraModeloPendente.query.filter_by(status=s).count()
        for s in PENDENTE_STATUS_VALIDOS
    }

    return render_template(
        'hora/modelos/pendencias.html',
        pendencias=pendencias,
        modelos=modelos,
        status_atual=status,
        contadores=contadores,
        statuses=PENDENTE_STATUS_VALIDOS,
    )


@hora_bp.route('/modelos/pendencias/<int:pendencia_id>/vincular', methods=['POST'])
@require_hora_perm('modelos', 'editar')
@login_required
def modelos_pendencias_vincular(pendencia_id: int):
    modelo_id_raw = (request.form.get('modelo_id') or '').strip()
    if not modelo_id_raw.isdigit():
        flash('modelo_id invalido', 'danger')
        return redirect(url_for('hora.modelos_pendencias_lista'))

    operador = getattr(current_user, 'username', None)
    try:
        resultado = vincular_pendencia_a_modelo(
            pendencia_id=pendencia_id,
            modelo_id=int(modelo_id_raw),
            operador=operador,
        )
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
        return redirect(url_for('hora.modelos_pendencias_lista'))

    motos_criadas = resultado['retroativos'].get('motos_criadas', 0)
    flash(
        f'Pendencia #{resultado["pendencia_id"]} vinculada a '
        f'{resultado["modelo_nome"]!r}.'
        f' {motos_criadas} moto(s) criadas retroativamente.',
        'success',
    )
    return redirect(url_for('hora.modelos_pendencias_lista'))


@hora_bp.route('/modelos/pendencias/<int:pendencia_id>/criar', methods=['POST'])
@require_hora_perm('modelos', 'criar')
@login_required
def modelos_pendencias_criar_modelo(pendencia_id: int):
    nome = (request.form.get('nome_modelo') or '').strip()
    potencia = (request.form.get('potencia_motor') or '').strip() or None
    descricao = (request.form.get('descricao') or '').strip() or None

    if not nome:
        flash('nome_modelo obrigatorio', 'danger')
        return redirect(url_for('hora.modelos_pendencias_lista'))

    operador = getattr(current_user, 'username', None)
    try:
        resultado = criar_modelo_de_pendencia(
            pendencia_id=pendencia_id,
            nome_modelo=nome,
            potencia_motor=potencia,
            descricao=descricao,
            operador=operador,
        )
    except ValueError as exc:
        db.session.rollback()
        flash(f'Erro: {exc}', 'danger')
        return redirect(url_for('hora.modelos_pendencias_lista'))

    motos_criadas = resultado['retroativos'].get('motos_criadas', 0)
    flash(
        f'Modelo {resultado["modelo_nome"]!r} criado (id={resultado["modelo_id"]}).'
        f' {motos_criadas} moto(s) criadas retroativamente.',
        'success',
    )
    return redirect(url_for('hora.modelos_pendencias_lista'))


@hora_bp.route('/modelos/pendencias/<int:pendencia_id>/ignorar', methods=['POST'])
@require_hora_perm('modelos', 'editar')
@login_required
def modelos_pendencias_ignorar(pendencia_id: int):
    motivo = (request.form.get('motivo') or '').strip() or None
    operador = getattr(current_user, 'username', None)
    try:
        ignorar_pendencia(
            pendencia_id=pendencia_id,
            operador=operador,
            motivo=motivo,
        )
        flash(f'Pendencia #{pendencia_id} ignorada.', 'info')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.modelos_pendencias_lista'))


# ============================================================================
# Aliases manuais (por modelo)
# ============================================================================

@hora_bp.route('/modelos/<int:modelo_id>/aliases')
@require_hora_perm('modelos', 'ver')
@login_required
def modelos_aliases_lista(modelo_id: int):
    modelo = HoraModelo.query.get_or_404(modelo_id)
    aliases = (
        HoraModeloAlias.query
        .filter_by(modelo_id=modelo_id)
        .order_by(HoraModeloAlias.tipo, HoraModeloAlias.nome_alias)
        .all()
    )
    tagplus_map = HoraTagPlusProdutoMap.query.filter_by(modelo_id=modelo_id).first()
    return render_template(
        'hora/modelos/aliases.html',
        modelo=modelo,
        aliases=aliases,
        tagplus_map=tagplus_map,
        tipos_validos=ALIAS_TIPOS_VALIDOS,
    )


@hora_bp.route('/modelos/<int:modelo_id>/aliases/criar', methods=['POST'])
@require_hora_perm('modelos', 'editar')
@login_required
def modelos_aliases_criar(modelo_id: int):
    modelo = HoraModelo.query.get_or_404(modelo_id)
    nome = (request.form.get('nome_alias') or '').strip()
    tipo = (request.form.get('tipo') or '').strip()
    obs = (request.form.get('observacao') or '').strip() or None

    if not nome:
        flash('nome_alias obrigatorio', 'danger')
        return redirect(url_for('hora.modelos_aliases_lista', modelo_id=modelo_id))
    if tipo not in ALIAS_TIPOS_VALIDOS:
        flash(f'tipo invalido. Validos: {ALIAS_TIPOS_VALIDOS}', 'danger')
        return redirect(url_for('hora.modelos_aliases_lista', modelo_id=modelo_id))

    # Idempotencia + UNIQUE: bloqueia se alias ja aponta para outro modelo.
    existente = HoraModeloAlias.query.filter_by(tipo=tipo, nome_alias=nome).first()
    if existente:
        if existente.modelo_id == modelo.id:
            flash('Alias ja existe para este modelo.', 'info')
        else:
            flash(
                f'Alias {nome!r} (tipo={tipo}) ja aponta para outro modelo '
                f'(id={existente.modelo_id}).',
                'danger',
            )
        return redirect(url_for('hora.modelos_aliases_lista', modelo_id=modelo_id))

    operador = getattr(current_user, 'username', None)
    db.session.add(HoraModeloAlias(
        modelo_id=modelo.id,
        nome_alias=nome,
        tipo=tipo,
        criado_por=operador,
        observacao=obs,
    ))
    db.session.commit()
    flash(f'Alias {nome!r} ({tipo}) adicionado.', 'success')
    return redirect(url_for('hora.modelos_aliases_lista', modelo_id=modelo_id))


@hora_bp.route('/modelos/<int:modelo_id>/aliases/<int:alias_id>/remover', methods=['POST'])
@require_hora_perm('modelos', 'editar')
@login_required
def modelos_aliases_remover(modelo_id: int, alias_id: int):
    alias = HoraModeloAlias.query.get_or_404(alias_id)
    if alias.modelo_id != modelo_id:
        flash('Alias nao pertence a este modelo.', 'danger')
        return redirect(url_for('hora.modelos_aliases_lista', modelo_id=modelo_id))
    db.session.delete(alias)
    db.session.commit()
    flash(f'Alias {alias.nome_alias!r} removido.', 'info')
    return redirect(url_for('hora.modelos_aliases_lista', modelo_id=modelo_id))


# ============================================================================
# Unificar modelos (merge fisico)
# ============================================================================

@hora_bp.route('/modelos/unificar')
@require_hora_perm('modelos', 'aprovar')
@login_required
def modelos_unificar_form():
    """Tela inicial de merge: lista modelos ativos + sugestoes de duplicacao."""
    modelos = (
        HoraModelo.query
        .filter(HoraModelo.merged_em_id.is_(None))
        .order_by(HoraModelo.nome_modelo)
        .all()
    )

    # Sugestoes: agrupar por hora_tagplus_produto_map.tagplus_produto_id
    # (vide hora_31_sugestoes_merge.py — replica logica para UI direta).
    rows = (
        db.session.query(
            HoraTagPlusProdutoMap.tagplus_produto_id,
            HoraTagPlusProdutoMap.tagplus_codigo,
            HoraTagPlusProdutoMap.modelo_id,
        )
        .all()
    )
    grupos_tagplus: dict[str, list] = {}
    for tagplus_id, codigo, mid in rows:
        grupos_tagplus.setdefault(tagplus_id, []).append({
            'modelo_id': mid,
            'codigo': codigo,
        })
    sugestoes = []
    for tagplus_id, items in grupos_tagplus.items():
        if len(items) > 1:
            modelos_grupo = []
            for it in items:
                m = HoraModelo.query.get(it['modelo_id'])
                if m and not m.merged_em_id:
                    qtd_motos = db.session.execute(
                        db.text('SELECT COUNT(*) FROM hora_moto WHERE modelo_id = :m'),
                        {'m': m.id},
                    ).scalar() or 0
                    modelos_grupo.append({
                        'id': m.id,
                        'nome_modelo': m.nome_modelo,
                        'qtd_motos': qtd_motos,
                        'tagplus_codigo': it['codigo'],
                    })
            if len(modelos_grupo) > 1:
                # Sugere canonico = maior qtd_motos
                modelos_grupo.sort(key=lambda x: x['qtd_motos'], reverse=True)
                sugestoes.append({
                    'tagplus_produto_id': tagplus_id,
                    'tagplus_codigo': modelos_grupo[0]['tagplus_codigo'],
                    'canonico_sugerido_id': modelos_grupo[0]['id'],
                    'modelos': modelos_grupo,
                })

    return render_template(
        'hora/modelos/unificar.html',
        modelos=modelos,
        sugestoes=sugestoes,
    )


@hora_bp.route('/modelos/unificar/preview', methods=['POST'])
@require_hora_perm('modelos', 'aprovar')
@login_required
def modelos_unificar_preview():
    """Dry-run: retorna JSON com impacto do merge (contadores)."""
    canonico_id = (request.form.get('canonico_id') or '').strip()
    aliases_raw = request.form.getlist('alias_ids[]') or request.form.getlist('alias_ids')

    if not canonico_id.isdigit():
        return jsonify({'ok': False, 'erro': 'canonico_id invalido'}), 400

    try:
        alias_ids = [int(a) for a in aliases_raw if str(a).strip().isdigit()]
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'erro': 'alias_ids invalido'}), 400

    if not alias_ids:
        return jsonify({'ok': False, 'erro': 'nenhum alias selecionado'}), 400

    try:
        preview = preview_merge(int(canonico_id), alias_ids)
    except MergeError as exc:
        return jsonify({'ok': False, 'erro': str(exc)}), 400

    return jsonify({'ok': True, 'preview': preview})


@hora_bp.route('/modelos/unificar/executar', methods=['POST'])
@require_hora_perm('modelos', 'aprovar')
@login_required
def modelos_unificar_executar():
    """Aplica merge fisico atomico."""
    canonico_id = (request.form.get('canonico_id') or '').strip()
    aliases_raw = request.form.getlist('alias_ids[]') or request.form.getlist('alias_ids')

    if not canonico_id.isdigit():
        flash('canonico_id invalido', 'danger')
        return redirect(url_for('hora.modelos_unificar_form'))

    try:
        alias_ids = [int(a) for a in aliases_raw if str(a).strip().isdigit()]
    except (TypeError, ValueError):
        flash('alias_ids invalido', 'danger')
        return redirect(url_for('hora.modelos_unificar_form'))

    if not alias_ids:
        flash('Selecione pelo menos 1 alias.', 'danger')
        return redirect(url_for('hora.modelos_unificar_form'))

    operador = getattr(current_user, 'username', None)
    try:
        resultado = merge_modelos(
            canonico_id=int(canonico_id),
            alias_ids=alias_ids,
            operador=operador,
        )
    except MergeError as exc:
        db.session.rollback()
        flash(f'Merge nao executado: {exc}', 'danger')
        return redirect(url_for('hora.modelos_unificar_form'))

    motos = resultado['hora_moto']
    pi = resultado['hora_pedido_item']
    aliases_criados = resultado['aliases_criados']
    aliases_count = len(resultado['aliases_absorvidos'])

    flash(
        f'Merge concluido: {aliases_count} alias(es) absorvidos. '
        f'{motos} moto(s) re-apontada(s), {pi} pedido_item(ns), '
        f'{aliases_criados} alias(es) auto-criados.',
        'success',
    )
    return redirect(url_for('hora.modelos_lista'))


# ============================================================================
# Helper para badge de contagem no menu
# ============================================================================

@hora_bp.app_context_processor
def _hora_pendencias_contador():
    """Injeta `hora_pendencias_qtd` em todos os templates (badge no menu)."""
    if not getattr(current_user, 'is_authenticated', False):
        return {'hora_pendencias_qtd': 0}
    try:
        qtd = HoraModeloPendente.query.filter_by(
            status=PENDENTE_STATUS_PENDENTE,
        ).count()
    except Exception:
        qtd = 0
    return {'hora_pendencias_qtd': qtd}

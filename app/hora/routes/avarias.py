"""Rotas de avaria em moto do estoque HORA."""
from __future__ import annotations

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.hora.decorators import require_hora_perm
from app.hora.models import HoraAvaria, HoraLoja, HoraMoto, HoraMotoEvento
from app.hora.routes import hora_bp
from app.hora.services import avaria_service
from app.hora.services.auth_helper import (
    lojas_permitidas_ids, usuario_tem_acesso_a_loja,
)
from app.hora.services.estoque_service import EVENTOS_EM_ESTOQUE


@hora_bp.route('/avarias')
@require_hora_perm('avarias', 'ver')
def avarias_lista():
    from datetime import datetime as _dt
    from app.hora.models import HoraMoto

    permitidas = lojas_permitidas_ids()
    q = HoraAvaria.query

    status = request.args.get('status')
    if status:
        q = q.filter(HoraAvaria.status == status)
    loja_id = request.args.get('loja_id', type=int)
    if loja_id:
        if not usuario_tem_acesso_a_loja(loja_id):
            flash('Acesso negado a essa loja', 'danger')
            return redirect(url_for('hora.avarias_lista'))
        q = q.filter(HoraAvaria.loja_id == loja_id)
    if permitidas is not None:
        q = q.filter(HoraAvaria.loja_id.in_(permitidas))

    chassi_query = request.args.get('chassi')
    if chassi_query:
        q = q.filter(
            HoraAvaria.numero_chassi.ilike(f"%{chassi_query.strip().upper()}%")
        )

    modelo_id_str = (request.args.get('modelo_id') or '').strip()
    modelo_id = int(modelo_id_str) if modelo_id_str.isdigit() else None
    if modelo_id:
        # Avarias cujo chassi tem esse modelo (join via HoraMoto).
        q = q.join(HoraMoto, HoraMoto.numero_chassi == HoraAvaria.numero_chassi) \
             .filter(HoraMoto.modelo_id == modelo_id)

    data_ini_str = (request.args.get('data_inicio') or '').strip()
    data_fim_str = (request.args.get('data_fim') or '').strip()
    try:
        data_inicio = _dt.strptime(data_ini_str, '%Y-%m-%d') if data_ini_str else None
        data_fim = _dt.strptime(data_fim_str, '%Y-%m-%d') if data_fim_str else None
    except ValueError:
        flash('Data invalida (use formato YYYY-MM-DD).', 'warning')
        data_inicio = None
        data_fim = None
    if data_inicio:
        q = q.filter(HoraAvaria.criado_em >= data_inicio)
    if data_fim:
        from datetime import timedelta
        q = q.filter(HoraAvaria.criado_em <= data_fim + timedelta(days=1))

    descricao = (request.args.get('descricao') or '').strip() or None
    if descricao:
        q = q.filter(HoraAvaria.descricao.ilike(f'%{descricao}%'))

    avarias = q.order_by(HoraAvaria.criado_em.desc()).limit(500).all()
    lojas_q = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        lojas_q = lojas_q.filter(HoraLoja.id.in_(permitidas)) if permitidas else lojas_q.filter(False)
    lojas = lojas_q.order_by(HoraLoja.apelido).all()
    from app.hora.models import HoraModelo
    modelos_ativos = HoraModelo.query.filter_by(ativo=True).order_by(HoraModelo.nome_modelo).all()
    return render_template(
        'hora/avarias_lista.html',
        avarias=avarias,
        lojas=lojas,
        modelos_ativos=modelos_ativos,
        filtros={
            'status': status,
            'loja_id': loja_id,
            'chassi': chassi_query,
            'modelo_id': modelo_id,
            'descricao': descricao,
            'data_inicio': data_ini_str,
            'data_fim': data_fim_str,
        },
    )


@hora_bp.route('/avarias/<int:avaria_id>')
@require_hora_perm('avarias', 'ver')
def avaria_detalhe(avaria_id):
    avaria = HoraAvaria.query.get_or_404(avaria_id)
    if not usuario_tem_acesso_a_loja(avaria.loja_id):
        abort(403)
    return render_template('hora/avaria_detalhe.html', avaria=avaria)


@hora_bp.route('/avarias/nova', methods=['GET', 'POST'])
@require_hora_perm('avarias', 'criar')
def avaria_nova():
    permitidas = lojas_permitidas_ids()

    if request.method == 'POST':
        numero_chassi = (request.form.get('numero_chassi') or '').strip().upper()
        descricao = (request.form.get('descricao') or '').strip()
        loja_id = request.form.get('loja_id', type=int)
        if not loja_id:
            flash('Loja obrigatoria', 'danger')
            return redirect(url_for('hora.avaria_nova'))
        if permitidas is not None and loja_id not in permitidas:
            flash('Loja fora do seu escopo', 'danger')
            return redirect(url_for('hora.avaria_nova'))

        # Upload de fotos: dois canais possiveis (camera ou arquivo). Multi-
        # upload via field name `foto_arquivo`. Foto e opcional desde
        # 2026-05-07 — service aceita lista vazia.
        arquivos = [
            f for f in request.files.getlist('foto_arquivo')
            if f and (f.filename or '').strip()
        ]
        try:
            fotos, ignorados = avaria_service.upload_fotos_temporarias(arquivos)
        except Exception as exc:  # noqa: BLE001 — quer log + mensagem amigavel
            db.session.rollback()
            flash(f'Erro ao salvar foto(s): {exc}', 'danger')
            return redirect(url_for('hora.avaria_nova'))

        # Sinaliza arquivos ignorados (extensao invalida / falha S3) para
        # o operador nao perceber tarde que faltou uma foto.
        if ignorados:
            flash(
                f'{len(ignorados)} arquivo(s) ignorado(s) por tipo invalido '
                f'(aceitos: JPG, PNG, WEBP, HEIC): {", ".join(ignorados[:3])}'
                + ('...' if len(ignorados) > 3 else ''),
                'warning',
            )

        try:
            avaria = avaria_service.registrar_avaria(
                numero_chassi=numero_chassi,
                descricao=descricao,
                fotos=fotos,
                usuario=current_user.nome,
                loja_id=loja_id,
            )
            db.session.commit()
            n_fotos = len(fotos)
            if n_fotos:
                flash(
                    f'Avaria #{avaria.id} registrada com {n_fotos} foto(s).',
                    'success',
                )
            else:
                flash(
                    f'Avaria #{avaria.id} registrada (sem fotos — voce pode '
                    f'anexar fotos depois).',
                    'success',
                )
            return redirect(url_for('hora.avaria_detalhe', avaria_id=avaria.id))
        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'danger')
            return redirect(url_for('hora.avaria_nova'))

    lojas_filtradas = (
        HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.apelido).all()
        if permitidas is None
        else HoraLoja.query.filter(HoraLoja.id.in_(permitidas)).all()
    )
    return render_template('hora/avaria_nova.html', lojas=lojas_filtradas)


@hora_bp.route('/avarias/api/info-chassi')
@require_hora_perm('avarias', 'criar')
def avaria_api_info_chassi():
    """JSON com modelo, cor, loja_id, loja_nome e em_estoque para um chassi.

    Usado pelo template avaria_nova para pre-preencher os campos quando o
    operador digita ou escaneia um chassi via QR. Respeita escopo de
    `lojas_permitidas_ids` — chassis fora do escopo do usuario retornam
    `ok=False` (sem revelar dados).
    """
    chassi = (request.args.get('chassi') or '').strip().upper()
    if not chassi or len(chassi) < 5:
        return jsonify({'ok': False, 'error': 'chassi muito curto'}), 200

    moto = HoraMoto.query.get(chassi)
    if not moto:
        return jsonify({'ok': False, 'error': 'chassi nao cadastrado'}), 200

    # Ultimo evento determina loja atual + status em estoque.
    ultimo = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraMotoEvento.timestamp.desc())
        .first()
    )
    loja_atual_id = ultimo.loja_id if ultimo else None
    em_estoque = bool(ultimo and ultimo.tipo in EVENTOS_EM_ESTOQUE)

    # Escopo: usuario com `lojas_permitidas_ids() != None` (nao-admin) so ve
    # chassi cuja loja atual esta no seu escopo. loja_atual_id=None
    # (chassi sem evento) e estado inconsistente — bloqueia para nao
    # vazar dados em estado anomalo. Admin (permitidas=None) ve tudo.
    permitidas = lojas_permitidas_ids()
    if permitidas is not None:
        if loja_atual_id is None or loja_atual_id not in permitidas:
            return jsonify({
                'ok': False, 'error': 'chassi fora do seu escopo de loja',
            }), 200

    loja_nome = None
    if loja_atual_id:
        loja = HoraLoja.query.get(loja_atual_id)
        if loja:
            loja_nome = (
                getattr(loja, 'rotulo_display', None)
                or loja.apelido
                or getattr(loja, 'nome_fantasia', None)
                or getattr(loja, 'razao_social', None)
                or f'Loja #{loja.id}'
            )

    modelo_nome = (
        moto.modelo.nome_modelo
        if getattr(moto, 'modelo', None) is not None
        else None
    )
    return jsonify({
        'ok': True,
        'chassi': chassi,
        'modelo_id': moto.modelo_id,
        'modelo_nome': modelo_nome,
        'cor': moto.cor,
        'loja_id': loja_atual_id,
        'loja_nome': loja_nome,
        'em_estoque': em_estoque,
        'ultimo_evento_tipo': ultimo.tipo if ultimo else None,
    })


@hora_bp.route('/avarias/<int:avaria_id>/foto', methods=['POST'])
@require_hora_perm('avarias', 'editar')
def avaria_adicionar_foto(avaria_id):
    avaria = HoraAvaria.query.get_or_404(avaria_id)
    if not usuario_tem_acesso_a_loja(avaria.loja_id):
        abort(403)
    foto_s3_key = (request.form.get('foto_s3_key') or '').strip()
    legenda = (request.form.get('legenda') or '').strip() or None
    if not foto_s3_key:
        flash('foto_s3_key obrigatorio', 'danger')
        return redirect(url_for('hora.avaria_detalhe', avaria_id=avaria_id))
    try:
        avaria_service.adicionar_foto(
            avaria_id, foto_s3_key, legenda, usuario=current_user.nome,
        )
        db.session.commit()
        flash('Foto adicionada.', 'success')
    except ValueError as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(url_for('hora.avaria_detalhe', avaria_id=avaria_id))


@hora_bp.route('/avarias/<int:avaria_id>/resolver', methods=['POST'])
@require_hora_perm('avarias', 'editar')
def avaria_resolver(avaria_id):
    avaria = HoraAvaria.query.get_or_404(avaria_id)
    if not usuario_tem_acesso_a_loja(avaria.loja_id):
        abort(403)
    obs = (request.form.get('observacao') or '').strip()
    try:
        avaria_service.resolver_avaria(avaria_id, obs, current_user.nome)
        db.session.commit()
        flash('Avaria resolvida.', 'success')
    except ValueError as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(url_for('hora.avaria_detalhe', avaria_id=avaria_id))


@hora_bp.route('/avarias/<int:avaria_id>/ignorar', methods=['POST'])
@require_hora_perm('avarias', 'editar')
def avaria_ignorar(avaria_id):
    avaria = HoraAvaria.query.get_or_404(avaria_id)
    if not usuario_tem_acesso_a_loja(avaria.loja_id):
        abort(403)
    obs = (request.form.get('observacao') or '').strip()
    try:
        avaria_service.ignorar_avaria(avaria_id, obs, current_user.nome)
        db.session.commit()
        flash('Avaria ignorada.', 'success')
    except ValueError as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(url_for('hora.avaria_detalhe', avaria_id=avaria_id))

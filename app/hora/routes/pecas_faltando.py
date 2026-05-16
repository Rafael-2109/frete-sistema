"""Rotas de pecas faltando + fotos + canibalizacao."""
from __future__ import annotations

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.hora.decorators import require_hora_perm
from app.hora.models import HoraLoja, HoraMoto, HoraMotoEvento, HoraPecaFaltando
from app.hora.routes import hora_bp
from app.hora.services import estoque_service, peca_faltando_service as peca_service
from app.hora.services.auth_helper import (
    lojas_permitidas_ids,
    usuario_tem_acesso_a_loja,
)
from app.hora.services.estoque_service import EVENTOS_EM_ESTOQUE


def _check_acesso_peca(peca: HoraPecaFaltando) -> bool:
    """Retorna True se usuario tem acesso a loja atual do chassi da peca.

    Nao tem loja (histor vazio) = libera (caso limite: moto recem-criada
    sem evento ainda; nao queremos bloquear operacao legitima).
    """
    hist = estoque_service.historico_chassi(peca.numero_chassi)
    loja_id = hist[0]['loja_id'] if hist else None
    if loja_id is None:
        return True
    return usuario_tem_acesso_a_loja(loja_id)


def _redirect_sem_acesso():
    flash('Acesso negado: peca pertence a loja fora do seu escopo.', 'danger')
    return redirect(url_for('hora.pecas_lista'))


@hora_bp.route('/pecas-faltando')
@require_hora_perm('pecas', 'ver')
def pecas_lista():
    from datetime import datetime as _dt
    from app.hora.models import HoraLoja

    permitidas = lojas_permitidas_ids()
    status = (request.args.get('status') or '').strip() or None
    chassi = (request.args.get('chassi') or '').strip() or None
    descricao = (request.args.get('descricao') or '').strip() or None
    loja_id_str = (request.args.get('loja_id') or '').strip()
    loja_id = int(loja_id_str) if loja_id_str.isdigit() else None
    data_ini_str = (request.args.get('data_inicio') or '').strip()
    data_fim_str = (request.args.get('data_fim') or '').strip()

    if loja_id and not usuario_tem_acesso_a_loja(loja_id):
        flash('Acesso negado a essa loja.', 'danger')
        return redirect(url_for('hora.pecas_lista'))

    try:
        data_inicio = _dt.strptime(data_ini_str, '%Y-%m-%d') if data_ini_str else None
        data_fim = _dt.strptime(data_fim_str, '%Y-%m-%d') if data_fim_str else None
    except ValueError:
        flash('Data invalida (use formato YYYY-MM-DD).', 'warning')
        data_inicio = None
        data_fim = None

    pecas = peca_service.listar_pecas(
        chassi=chassi,
        status=status,
        lojas_permitidas_ids=permitidas,
        descricao=descricao,
        loja_id=loja_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    lojas_q = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        lojas_q = lojas_q.filter(HoraLoja.id.in_(permitidas))
    lojas_ativas = lojas_q.order_by(HoraLoja.nome).all()

    return render_template(
        'hora/pecas_faltando_lista.html',
        pecas=pecas,
        filtro_status=status,
        filtro_chassi=chassi,
        filtro_descricao=descricao,
        filtro_loja_id=loja_id,
        filtro_data_inicio=data_ini_str,
        filtro_data_fim=data_fim_str,
        lojas_ativas=lojas_ativas,
    )


@hora_bp.route('/pecas-faltando/novo', methods=['GET', 'POST'])
@require_hora_perm('pecas', 'criar')
def pecas_novo():
    permitidas = lojas_permitidas_ids()

    def _lojas_para_template():
        q = HoraLoja.query.filter_by(ativa=True)
        if permitidas is not None:
            if not permitidas:
                return []
            q = q.filter(HoraLoja.id.in_(permitidas))
        return q.order_by(HoraLoja.apelido).all()

    if request.method == 'POST':
        try:
            chassi = (request.form.get('numero_chassi') or '').strip().upper()
            descricao = (request.form.get('descricao') or '').strip()
            obs = (request.form.get('observacoes') or '').strip() or None
            loja_id = request.form.get('loja_id', type=int)
            if not chassi or not descricao:
                raise ValueError('chassi e descricao sao obrigatorios')
            if not loja_id:
                raise ValueError('loja obrigatoria')
            if permitidas is not None and loja_id not in permitidas:
                flash('Loja fora do seu escopo.', 'danger')
                return render_template(
                    'hora/peca_faltando_novo.html',
                    lojas=_lojas_para_template(),
                )

            # Valida acesso a loja atual da moto (consistencia: a loja indicada
            # no form deve estar no escopo, mas a moto pode estar em outra loja
            # — registramos com a loja informada pelo operador).
            if not usuario_tem_acesso_a_loja(loja_id):
                flash('Acesso negado a essa loja.', 'danger')
                return render_template(
                    'hora/peca_faltando_novo.html',
                    lojas=_lojas_para_template(),
                )

            peca = peca_service.registrar_peca_faltando(
                numero_chassi=chassi,
                descricao=descricao,
                loja_id=loja_id,
                observacoes=obs,
                criado_por=current_user.nome if hasattr(current_user, 'nome') else None,
            )
            flash(f'Pendencia #{peca.id} registrada. Adicione fotos abaixo.', 'success')
            return redirect(url_for('hora.pecas_detalhe', peca_id=peca.id))
        except ValueError as exc:
            flash(f'Erro: {exc}', 'danger')

    return render_template(
        'hora/peca_faltando_novo.html',
        lojas=_lojas_para_template(),
    )


@hora_bp.route('/pecas-faltando/api/info-chassi')
@require_hora_perm('pecas', 'criar')
def pecas_api_info_chassi():
    """JSON com modelo, cor, loja_id, loja_nome e em_estoque para um chassi.

    Usado pelo template peca_faltando_novo para pre-preencher os campos
    quando o operador digita ou escaneia um chassi via QR. Mesmo contrato
    de avaria_api_info_chassi para reuso do JS no front.
    """
    chassi = (request.args.get('chassi') or '').strip().upper()
    if not chassi or len(chassi) < 5:
        return jsonify({'ok': False, 'error': 'chassi muito curto'}), 200

    moto = HoraMoto.query.get(chassi)
    if not moto:
        return jsonify({'ok': False, 'error': 'chassi nao cadastrado'}), 200

    ultimo = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraMotoEvento.timestamp.desc())
        .first()
    )
    loja_atual_id = ultimo.loja_id if ultimo else None
    em_estoque = bool(ultimo and ultimo.tipo in EVENTOS_EM_ESTOQUE)

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


@hora_bp.route('/pecas-faltando/<int:peca_id>')
@require_hora_perm('pecas', 'ver')
def pecas_detalhe(peca_id: int):
    peca = HoraPecaFaltando.query.get_or_404(peca_id)
    if not _check_acesso_peca(peca):
        return _redirect_sem_acesso()

    fotos = [
        {
            'id': f.id,
            'url': peca_service.get_foto_url(f),
            'legenda': f.legenda,
            'criado_em': f.criado_em,
        }
        for f in peca.fotos
    ]
    return render_template(
        'hora/peca_faltando_detalhe.html',
        peca=peca,
        fotos=fotos,
    )


@hora_bp.route('/pecas-faltando/<int:peca_id>/fotos', methods=['POST'])
@require_hora_perm('pecas', 'editar')
def pecas_upload_foto(peca_id: int):
    peca = HoraPecaFaltando.query.get_or_404(peca_id)
    if not _check_acesso_peca(peca):
        return _redirect_sem_acesso()

    arquivo = request.files.get('foto')
    legenda = (request.form.get('legenda') or '').strip() or None
    if not arquivo or not arquivo.filename:
        flash('Selecione uma foto.', 'danger')
        return redirect(url_for('hora.pecas_detalhe', peca_id=peca_id))
    try:
        peca_service.adicionar_foto(
            peca_faltando_id=peca_id,
            file_obj=arquivo,
            legenda=legenda,
            criado_por=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash('Foto enviada.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.pecas_detalhe', peca_id=peca_id))


@hora_bp.route('/pecas-faltando/<int:peca_id>/fotos/<int:foto_id>/remover', methods=['POST'])
@require_hora_perm('pecas', 'apagar')
def pecas_remover_foto(peca_id: int, foto_id: int):
    peca = HoraPecaFaltando.query.get_or_404(peca_id)
    if not _check_acesso_peca(peca):
        return _redirect_sem_acesso()
    try:
        peca_service.remover_foto(peca_id, foto_id)
        flash('Foto removida.', 'info')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.pecas_detalhe', peca_id=peca_id))


@hora_bp.route('/pecas-faltando/<int:peca_id>/canibalizar', methods=['POST'])
@require_hora_perm('pecas', 'editar')
def pecas_canibalizar(peca_id: int):
    peca = HoraPecaFaltando.query.get_or_404(peca_id)
    if not _check_acesso_peca(peca):
        return _redirect_sem_acesso()

    chassi_doador = (request.form.get('chassi_doador') or '').strip().upper()
    if not chassi_doador:
        flash('Chassi doador obrigatorio.', 'danger')
        return redirect(url_for('hora.pecas_detalhe', peca_id=peca_id))

    # Valida tambem acesso a loja do DOADOR (quem cede a peca)
    hist_doador = estoque_service.historico_chassi(chassi_doador)
    loja_doador = hist_doador[0]['loja_id'] if hist_doador else None
    if loja_doador and not usuario_tem_acesso_a_loja(loja_doador):
        flash('Acesso negado a loja do chassi doador.', 'danger')
        return redirect(url_for('hora.pecas_detalhe', peca_id=peca_id))

    try:
        res = peca_service.canibalizar(
            peca_faltando_id=peca_id,
            chassi_doador=chassi_doador,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash(
            f'Peca resolvida com canibalizacao de {chassi_doador}. '
            f'Nova pendencia criada no doador (#{res["peca_nova_id"]}).',
            'success',
        )
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.pecas_detalhe', peca_id=peca_id))


@hora_bp.route('/pecas-faltando/<int:peca_id>/resolver', methods=['POST'])
@require_hora_perm('pecas', 'editar')
def pecas_resolver(peca_id: int):
    peca = HoraPecaFaltando.query.get_or_404(peca_id)
    if not _check_acesso_peca(peca):
        return _redirect_sem_acesso()

    obs = (request.form.get('observacoes') or '').strip() or None
    try:
        peca_service.resolver_peca(
            peca_faltando_id=peca_id,
            observacoes=obs,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash('Pendencia resolvida.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.pecas_detalhe', peca_id=peca_id))


@hora_bp.route('/pecas-faltando/<int:peca_id>/cancelar', methods=['POST'])
@require_hora_perm('pecas', 'apagar')
def pecas_cancelar(peca_id: int):
    peca = HoraPecaFaltando.query.get_or_404(peca_id)
    if not _check_acesso_peca(peca):
        return _redirect_sem_acesso()
    try:
        peca_service.cancelar_peca(
            peca_faltando_id=peca_id,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash('Pendencia cancelada.', 'warning')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.pecas_detalhe', peca_id=peca_id))


@hora_bp.route('/pecas-faltando/autocomplete-chassi')
@require_hora_perm('pecas', 'ver')
def pecas_autocomplete_chassi():
    """Busca parcial de chassis (para campo chassi_doador)."""
    q = (request.args.get('q') or '').strip().upper()
    if not q or len(q) < 3:
        return jsonify([])
    motos = (
        HoraMoto.query
        .filter(HoraMoto.numero_chassi.ilike(f'%{q}%'))
        .limit(20)
        .all()
    )
    return jsonify([
        {
            'chassi': m.numero_chassi,
            'modelo': m.modelo.nome_modelo if m.modelo else '',
            'cor': m.cor,
        }
        for m in motos
    ])

"""Rotas de recebimento físico + conferência por chassi + resolucao."""
from __future__ import annotations

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from app.hora.decorators import require_lojas as login_required

from app.hora.models import (
    HoraLoja,
    HoraNfEntrada,
    HoraRecebimento,
    HoraRecebimentoConferencia,
)
from app.hora.routes import hora_bp
from app.hora.services import (
    devolucao_service,
    recebimento_service,
    resolucao_service,
)
from app.hora.services.cadastro_service import buscar_ou_criar_modelo
from app.hora.services.auth_helper import lojas_permitidas_ids, usuario_tem_acesso_a_loja


@hora_bp.route('/recebimentos')
@login_required
def recebimentos_lista():
    loja_id_str = request.args.get('loja_id') or ''
    status = request.args.get('status') or None
    loja_id = int(loja_id_str) if loja_id_str.isdigit() else None

    permitidas = lojas_permitidas_ids()
    recebimentos = recebimento_service.listar_recebimentos(
        loja_id=loja_id, status=status, limit=200,
        lojas_permitidas_ids=permitidas,
    )
    lojas_query = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        lojas_query = lojas_query.filter(HoraLoja.id.in_(permitidas))
    lojas = lojas_query.order_by(HoraLoja.nome).all()
    return render_template(
        'hora/recebimentos_lista.html',
        recebimentos=recebimentos,
        lojas=lojas,
        filtro_loja_id=loja_id,
        filtro_status=status,
    )


@hora_bp.route('/recebimentos/novo', methods=['GET', 'POST'])
@login_required
def recebimentos_novo():
    """Iniciar recebimento a partir de uma NF existente + loja."""
    if request.method == 'POST':
        try:
            nf_id = int(request.form['nf_id'])
            loja_id = int(request.form['loja_id'])
            rec = recebimento_service.iniciar_recebimento(
                nf_id=nf_id,
                loja_id=loja_id,
                operador=current_user.nome if hasattr(current_user, 'nome') else None,
            )
            flash(f'Recebimento #{rec.id} iniciado.', 'success')
            return redirect(url_for('hora.recebimentos_detalhe', recebimento_id=rec.id))
        except (ValueError, KeyError) as exc:
            flash(f'Erro: {exc}', 'danger')

    nfs = HoraNfEntrada.query.order_by(HoraNfEntrada.data_emissao.desc()).limit(100).all()
    lojas = HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.nome).all()
    return render_template('hora/recebimento_novo.html', nfs=nfs, lojas=lojas)


@hora_bp.route('/recebimentos/<int:recebimento_id>')
@login_required
def recebimentos_detalhe(recebimento_id: int):
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        flash('Acesso negado: recebimento de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.recebimentos_lista'))
    chassis_esperados = recebimento_service.chassis_esperados_mas_nao_conferidos(recebimento_id)
    chassis_extras = recebimento_service.chassis_conferidos_nao_na_nf(recebimento_id)

    return render_template(
        'hora/recebimento_detalhe.html',
        recebimento=rec,
        chassis_esperados_nao_conferidos=chassis_esperados,
        chassis_extras=chassis_extras,
    )


@hora_bp.route('/recebimentos/<int:recebimento_id>/validar-chassi')
@login_required
def recebimentos_validar_chassi(recebimento_id: int):
    """Endpoint AJAX para validação pré-submit de um chassi no recebimento.

    Query param: ?chassi=XXX
    Retorna JSON com na_nf, no_pedido, modelo/cor esperados, ja_conferido,
    divergência sugerida. Usado pelo JS para dar feedback visual ao operador
    ANTES de registrar a conferência.
    """
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        return jsonify({'ok': False, 'erro': 'acesso negado'}), 403

    chassi = request.args.get('chassi', '').strip()
    resultado = recebimento_service.validar_chassi_contra_recebimento(
        recebimento_id=recebimento_id,
        numero_chassi=chassi,
    )
    return jsonify(resultado)


@hora_bp.route('/recebimentos/<int:recebimento_id>/conferir', methods=['POST'])
@login_required
def recebimentos_conferir(recebimento_id: int):
    """Registra conferência de UM chassi. AJAX ou form tradicional."""
    try:
        numero_chassi = request.form['numero_chassi'].strip().upper()
        qr_code_lido = request.form.get('qr_code_lido') == 'on'
        tipo_divergencia = request.form.get('tipo_divergencia') or None
        if tipo_divergencia == '':
            tipo_divergencia = None
        detalhe = request.form.get('detalhe_divergencia') or None

        recebimento_service.registrar_conferencia(
            recebimento_id=recebimento_id,
            numero_chassi=numero_chassi,
            qr_code_lido=qr_code_lido,
            tipo_divergencia=tipo_divergencia,
            detalhe_divergencia=detalhe,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )

        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'ok': True, 'chassi': numero_chassi})

        flash(f'Chassi {numero_chassi} conferido.', 'success')
    except (ValueError, KeyError) as exc:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'ok': False, 'erro': str(exc)}), 400
        flash(f'Erro na conferência: {exc}', 'danger')

    return redirect(url_for('hora.recebimentos_detalhe', recebimento_id=recebimento_id))


@hora_bp.route('/recebimentos/<int:recebimento_id>/finalizar', methods=['POST'])
@login_required
def recebimentos_finalizar(recebimento_id: int):
    """Finaliza. Se houver chassis esperados ainda nao conferidos, comportamento
    depende do checkbox `marcar_faltantes_em_batch`:
        - true  -> marca todos como MOTO_FALTANDO em batch e finaliza
        - false -> finaliza simples (esperados ficam ignorados, alerta mostrado)
    """
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        flash('Acesso negado: recebimento de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.recebimentos_lista'))
    marcar_batch = request.form.get('marcar_faltantes_em_batch') == 'on'
    try:
        if marcar_batch:
            rec = recebimento_service.finalizar_com_faltantes_em_batch(
                recebimento_id,
                operador=current_user.nome if hasattr(current_user, 'nome') else None,
            )
            flash(
                f'Recebimento finalizado com faltantes marcados em batch. '
                f'Status: {rec.status}',
                'success',
            )
        else:
            rec = recebimento_service.finalizar_recebimento(recebimento_id)
            flash(f'Recebimento finalizado. Status: {rec.status}', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.recebimentos_detalhe', recebimento_id=recebimento_id))


# ------------------------------------------------------------------------
# Resolucao pos-recebimento
# ------------------------------------------------------------------------

@hora_bp.route('/recebimentos/<int:recebimento_id>/resolver')
@login_required
def recebimentos_resolver(recebimento_id: int):
    """Tela com lista de divergencias e acoes possiveis."""
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        flash('Acesso negado: recebimento de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.recebimentos_lista'))
    divergencias = resolucao_service.listar_divergencias(recebimento_id)
    # Devolucoes ABERTAS da mesma loja para reusar
    devolucoes_abertas = devolucao_service.listar_devolucoes(
        loja_id=rec.loja_id,
        status='ABERTA',
        limit=20,
    )
    return render_template(
        'hora/recebimento_resolver.html',
        recebimento=rec,
        divergencias=divergencias,
        devolucoes_abertas=devolucoes_abertas,
    )


@hora_bp.route(
    '/recebimentos/<int:recebimento_id>/resolver/<int:conferencia_id>',
    methods=['POST'],
)
@login_required
def recebimentos_resolver_aplicar(recebimento_id: int, conferencia_id: int):
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        flash('Acesso negado: recebimento de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.recebimentos_lista'))
    conf = HoraRecebimentoConferencia.query.get_or_404(conferencia_id)
    if conf.recebimento_id != recebimento_id:
        flash('Conferencia nao pertence a este recebimento.', 'danger')
        return redirect(url_for('hora.recebimentos_resolver', recebimento_id=recebimento_id))

    acao = (request.form.get('acao') or '').strip().upper()
    motivo = (request.form.get('motivo') or '').strip() or None
    obs = (request.form.get('observacoes') or '').strip() or None
    devolucao_id_str = (request.form.get('devolucao_id') or '').strip()
    devolucao_id = int(devolucao_id_str) if devolucao_id_str.isdigit() else None
    descricao_peca = (request.form.get('descricao_peca') or '').strip() or None

    try:
        res = resolucao_service.resolver_divergencia(
            conferencia_id=conferencia_id,
            acao=acao,
            motivo=motivo,
            observacoes=obs,
            devolucao_id=devolucao_id,
            descricao_peca=descricao_peca,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash(f'Acao {acao} aplicada (chassi {conf.numero_chassi}).', 'success')
        if res.get('devolucao_id'):
            return redirect(url_for(
                'hora.devolucoes_detalhe', devolucao_id=res['devolucao_id'],
            ))
        if res.get('peca_faltando_id'):
            return redirect(url_for(
                'hora.pecas_detalhe', peca_id=res['peca_faltando_id'],
            ))
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.recebimentos_resolver', recebimento_id=recebimento_id))


# ------------------------------------------------------------------------
# Criar modelo rapido (inline a partir do recebimento)
# ------------------------------------------------------------------------

@hora_bp.route('/modelos/criar-rapido', methods=['POST'])
@login_required
def modelos_criar_rapido():
    """Endpoint AJAX: cria HoraModelo se nao existe. Retorna id+nome.

    Protegido contra race: se 2 users clicam simultaneamente, o segundo recebe
    IntegrityError na UNIQUE(nome_modelo) — tratamos com rollback e re-get.
    """
    from app import db
    from app.hora.models import HoraModelo
    from sqlalchemy.exc import IntegrityError

    nome = (request.form.get('nome_modelo') or '').strip()
    if not nome:
        return jsonify({'ok': False, 'erro': 'nome_modelo obrigatorio'}), 400
    try:
        modelo = buscar_ou_criar_modelo(nome)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # Outra transacao venceu — re-busca e retorna
        modelo = HoraModelo.query.filter_by(nome_modelo=nome).first()
        if not modelo:
            return jsonify({'ok': False, 'erro': 'falha ao criar/recuperar modelo'}), 500
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(exc)}), 400

    return jsonify({
        'ok': True,
        'modelo_id': modelo.id,
        'nome_modelo': modelo.nome_modelo,
    })

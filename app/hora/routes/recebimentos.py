"""Rotas do recebimento físico HORA (conferência CEGA + auditoria).

Fluxo:
  T1 /recebimentos/novo           (NF + loja)
  T2 /recebimentos/<id>/qtd       (qtd declarada macro)
  T3 /recebimentos/<id>/wizard    (wizard A-B-C-D por moto)
  T4 /recebimentos/<id>           (resumo lado-a-lado + auditoria)
  T5 /recebimentos/<id>/ajustar   (botao ajustar conferencia)
     /recebimentos/<id>/reconferir
     /recebimentos/<id>/alterar-qtd
"""
from __future__ import annotations

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from app import db
from app.hora.decorators import require_hora_perm

from app.hora.models import (
    HoraLoja,
    HoraNfEntrada,
    HoraModelo,
    HoraRecebimento,
    HoraRecebimentoConferencia,
)
from app.hora.routes import hora_bp
from app.hora.services import (
    devolucao_service,
    recebimento_service,
    recebimento_audit,
    resolucao_service,
)
from app.hora.services.cadastro_service import buscar_ou_criar_modelo
from app.hora.services.auth_helper import lojas_permitidas_ids, usuario_tem_acesso_a_loja


def _op_name() -> str | None:
    return current_user.nome if hasattr(current_user, 'nome') else None


# ------------------------------------------------------------------------
# Listagem
# ------------------------------------------------------------------------

@hora_bp.route('/recebimentos')
@require_hora_perm('recebimentos', 'ver')
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


# ------------------------------------------------------------------------
# T1 — Novo recebimento
# ------------------------------------------------------------------------

@hora_bp.route('/recebimentos/novo', methods=['GET', 'POST'])
@require_hora_perm('recebimentos', 'criar')
def recebimentos_novo():
    if request.method == 'POST':
        try:
            nf_id = int(request.form['nf_id'])
            loja_id = int(request.form['loja_id'])
            if not usuario_tem_acesso_a_loja(loja_id):
                flash('Acesso negado a essa loja.', 'danger')
                return redirect(url_for('hora.recebimentos_novo'))
            rec = recebimento_service.iniciar_recebimento(
                nf_id=nf_id, loja_id=loja_id, operador=_op_name(),
            )
            return redirect(url_for('hora.recebimentos_qtd', recebimento_id=rec.id))
        except (ValueError, KeyError) as exc:
            flash(f'Erro: {exc}', 'danger')

    # Somente NFs que AINDA nao tem recebimento aberto: evita que operador
    # inicie outra conferencia para uma NF ja processada.
    # `HoraRecebimento.nf_id` tem UNIQUE(nf_id, loja_id), mas para a tela de
    # "Novo Recebimento" consideramos qualquer recebimento existente como
    # motivo suficiente para ocultar a NF.
    nfs = (
        HoraNfEntrada.query
        .filter(~HoraNfEntrada.recebimentos.any())
        .order_by(HoraNfEntrada.data_emissao.desc())
        .limit(200)
        .all()
    )
    permitidas = lojas_permitidas_ids()
    lojas_q = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        lojas_q = lojas_q.filter(HoraLoja.id.in_(permitidas))
    lojas = lojas_q.order_by(HoraLoja.nome).all()
    return render_template('hora/recebimento_novo.html', nfs=nfs, lojas=lojas)


# ------------------------------------------------------------------------
# T2 — Qtd declarada (conferencia cega macro)
# ------------------------------------------------------------------------

@hora_bp.route('/recebimentos/<int:recebimento_id>/qtd', methods=['GET', 'POST'])
@require_hora_perm('recebimentos', 'editar')
def recebimentos_qtd(recebimento_id: int):
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.recebimentos_lista'))

    if request.method == 'POST':
        try:
            qtd = int(request.form.get('qtd_declarada') or 0)
            recebimento_service.definir_qtd_declarada(
                recebimento_id=rec.id, qtd=qtd, usuario=_op_name(),
            )
            return redirect(url_for('hora.recebimentos_wizard', recebimento_id=rec.id))
        except ValueError as exc:
            flash(f'Erro: {exc}', 'danger')

    return render_template('hora/recebimento_qtd.html', recebimento=rec)


# ------------------------------------------------------------------------
# T3 — Wizard A-B-C-D
# ------------------------------------------------------------------------

@hora_bp.route('/recebimentos/<int:recebimento_id>/wizard')
@require_hora_perm('recebimentos', 'editar')
def recebimentos_wizard(recebimento_id: int):
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.recebimentos_lista'))
    if rec.qtd_declarada is None:
        return redirect(url_for('hora.recebimentos_qtd', recebimento_id=rec.id))

    # Proxima ordem pendente:
    # 1. Preferir uma conferencia ativa com confirmado_em=NULL (reconferencia).
    pendente = (
        HoraRecebimentoConferencia.query
        .filter_by(recebimento_id=rec.id, substituida=False, confirmado_em=None)
        .order_by(HoraRecebimentoConferencia.ordem)
        .first()
    )
    confs_ativas = [c for c in rec.conferencias if not c.substituida]
    confirmadas = sum(1 for c in confs_ativas if c.confirmado_em is not None)

    if pendente is None and confirmadas >= rec.qtd_declarada:
        # Fila esgotada — todos vao para o resumo (conferente ve apenas as
        # linhas das motos que ELE conferiu; supervisor ve comparativo completo).
        return redirect(url_for('hora.recebimentos_detalhe', recebimento_id=rec.id))

    ordem_atual = pendente.ordem if pendente else recebimento_service.proxima_ordem(rec.id)
    modelos = HoraModelo.query.order_by(HoraModelo.nome_modelo).all()

    # Cores sugeridas agregadas (NF + pedido)
    cores = set()
    for i in rec.nf.itens:
        if i.cor_texto_original:
            cores.add(i.cor_texto_original.strip().upper())
    if rec.nf.pedido_id and rec.nf.pedido:
        for pi in rec.nf.pedido.itens:
            if pi.cor:
                cores.add(pi.cor.strip().upper())

    return render_template(
        'hora/recebimento_wizard.html',
        recebimento=rec,
        ordem_atual=ordem_atual,
        confirmadas=confirmadas,
        pendente=pendente,
        modelos=modelos,
        cores_sugeridas=sorted(c for c in cores if c),
    )


@hora_bp.route('/recebimentos/<int:recebimento_id>/motos-nf')
@require_hora_perm('recebimento_motos_nf', 'ver')
def recebimentos_motos_nf(recebimento_id: int):
    """Retorna JSON com as motos da NF deste recebimento.

    Usado pelo painel "Ver motos da NF" no wizard (item 4 do pedido
    2026-04-23). Gate obrigatorio: permissao granular
    `recebimento_motos_nf.ver` — conferentes sem essa perm nem veem o painel.

    Query param `filtro` (opcional):
      - 'todas' (default): lista tudo, cada item vem com conferida True/False
      - 'conferidas': apenas itens com conferencia ativa e confirmada
    """
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        return jsonify({'ok': False, 'erro': 'acesso negado'}), 403

    filtro = (request.args.get('filtro') or 'todas').strip().lower()
    if filtro not in ('todas', 'conferidas'):
        filtro = 'todas'

    confs_ativas = [c for c in rec.conferencias if not c.substituida]
    conf_por_chassi = {c.numero_chassi: c for c in confs_ativas}
    total_conferidas = sum(1 for c in confs_ativas if c.confirmado_em is not None)

    itens = []
    for it in rec.nf.itens:
        conf = conf_por_chassi.get(it.numero_chassi)
        conferida = conf is not None and conf.confirmado_em is not None
        if filtro == 'conferidas' and not conferida:
            continue
        itens.append({
            'chassi': it.numero_chassi,
            'modelo': it.modelo_texto_original,
            'cor': it.cor_texto_original,
            'motor': it.numero_motor_texto_original,
            'conferida': conferida,
            'ordem': conf.ordem if conf else None,
        })

    return jsonify({
        'ok': True,
        'filtro': filtro,
        'total_na_nf': len(rec.nf.itens),
        'total_conferidas': total_conferidas,
        'itens': itens,
    })


@hora_bp.route('/recebimentos/<int:recebimento_id>/validar-chassi')
@require_hora_perm('recebimentos', 'ver')
def recebimentos_validar_chassi(recebimento_id: int):
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        return jsonify({'ok': False, 'erro': 'acesso negado'}), 403
    chassi = request.args.get('chassi', '').strip()
    resultado = recebimento_service.validar_chassi_contra_recebimento(
        recebimento_id=recebimento_id, numero_chassi=chassi,
    )
    return jsonify(resultado)


@hora_bp.route('/recebimentos/<int:recebimento_id>/conferir', methods=['POST'])
@require_hora_perm('recebimentos', 'editar')
def recebimentos_conferir(recebimento_id: int):
    """Recebe submissao do wizard. JSON por padrao."""
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        return jsonify({'ok': False, 'erro': 'acesso negado'}), 403

    data = request.get_json(silent=True) or request.form
    try:
        numero_chassi = (data.get('numero_chassi') or '').strip().upper()
        modelo_id_str = data.get('modelo_id') or ''
        modelo_id = int(modelo_id_str) if str(modelo_id_str).isdigit() else None
        cor = (data.get('cor_conferida') or '').strip().upper() or None
        avaria = str(data.get('avaria_fisica') or '').lower() in ('1', 'true', 'on', 'yes')
        qr = str(data.get('qr_code_lido') or '').lower() in ('1', 'true', 'on', 'yes')
        ordem_raw = data.get('ordem') or ''
        ordem = int(ordem_raw) if str(ordem_raw).isdigit() else None

        conf = recebimento_service.registrar_conferencia_cega(
            recebimento_id=recebimento_id,
            numero_chassi=numero_chassi,
            modelo_id_conferido=modelo_id,
            cor_conferida=cor,
            avaria_fisica=avaria,
            qr_code_lido=qr,
            ordem=ordem,
            operador=_op_name(),
        )
        divergencias = [
            {'tipo': d.tipo, 'esperado': d.valor_esperado, 'conferido': d.valor_conferido,
             'detalhe': d.detalhe}
            for d in conf.divergencias
        ]
        return jsonify({
            'ok': True,
            'conferencia_id': conf.id,
            'chassi': conf.numero_chassi,
            'ordem': conf.ordem,
            'divergencias': divergencias,
            'bate_com_nf': not divergencias,
        })
    except IntegrityError:
        # Race: duas submissoes simultaneas disputaram mesma ordem/chassi.
        db.session.rollback()
        return jsonify({
            'ok': False,
            'erro': 'Conflito de concorrencia: tente novamente.',
            'retry': True,
        }), 409
    except (ValueError, KeyError) as exc:
        return jsonify({'ok': False, 'erro': str(exc)}), 400


# ------------------------------------------------------------------------
# T4 — Resumo (substitui detalhe antigo)
# ------------------------------------------------------------------------

@hora_bp.route('/recebimentos/<int:recebimento_id>')
@require_hora_perm('recebimentos', 'ver')
def recebimentos_detalhe(recebimento_id: int):
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.recebimentos_lista'))

    if rec.qtd_declarada is None:
        return redirect(url_for('hora.recebimentos_qtd', recebimento_id=rec.id))

    # Regra: conferente SEM permissao `recebimento_resumo.ver` tambem ve o
    # resumo, mas limitado as motos que ELE JA conferiu — nao exibimos motos
    # da NF ainda pendentes nem linhas FALTANDO (isso seria "colar" da NF).
    # Supervisor com a permissao ve o comparativo completo (com FALTANDO/EXTRA).
    pode_ver_resumo_completo = current_user.tem_perm_hora('recebimento_resumo', 'ver')
    comparativo = recebimento_service.comparativo_recebimento_nf(
        rec.id,
        apenas_conferidas=not pode_ver_resumo_completo,
    )
    auditorias = recebimento_audit.listar_por_recebimento(rec.id, limit=200)

    # Map conferencia_id -> ordem (inclui substituidas) para que a coluna
    # "Conf." da tabela de auditoria mostre a ordem humana (ex: "CONF. 1"),
    # NAO o id autoincrement (que sobe a cada reconferencia e confunde). Sem
    # isso, reconferir a moto de ordem 1 exibe "CONF. 2/3/..." na auditoria.
    todas_confs = HoraRecebimentoConferencia.query.filter_by(
        recebimento_id=rec.id,
    ).all()
    ordens_por_conf_id = {c.id: c.ordem for c in todas_confs}

    return render_template(
        'hora/recebimento_detalhe.html',
        recebimento=rec,
        comparativo=comparativo,
        auditorias=auditorias,
        ordens_por_conf_id=ordens_por_conf_id,
        pode_ver_resumo_completo=pode_ver_resumo_completo,
    )


# ------------------------------------------------------------------------
# T5 — Ajustar conferencia (alterar qtd / reconferir selecionadas)
# ------------------------------------------------------------------------

@hora_bp.route('/recebimentos/<int:recebimento_id>/alterar-qtd', methods=['POST'])
@require_hora_perm('recebimentos', 'editar')
def recebimentos_alterar_qtd(recebimento_id: int):
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.recebimentos_lista'))
    try:
        qtd = int(request.form.get('qtd_declarada') or 0)
        recebimento_service.definir_qtd_declarada(
            recebimento_id=rec.id, qtd=qtd, usuario=_op_name(),
        )
        flash(f'Qtd total ajustada para {qtd}.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.recebimentos_detalhe', recebimento_id=rec.id))


@hora_bp.route('/recebimentos/<int:recebimento_id>/reconferir', methods=['POST'])
@require_hora_perm('recebimentos', 'editar')
def recebimentos_reconferir(recebimento_id: int):
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.recebimentos_lista'))

    ids = request.form.getlist('conferencia_id[]')
    ids_int = [int(i) for i in ids if str(i).isdigit()]
    if not ids_int:
        flash('Nenhuma moto selecionada para reconferir.', 'warning')
        return redirect(url_for('hora.recebimentos_detalhe', recebimento_id=rec.id))

    try:
        novas = recebimento_service.reiniciar_conferencia_para_chassis(
            recebimento_id=rec.id, conferencia_ids=ids_int, operador=_op_name(),
        )
        flash(f'{len(novas)} moto(s) enfileiradas para reconferencia.', 'success')
        return redirect(url_for('hora.recebimentos_wizard', recebimento_id=rec.id))
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
        return redirect(url_for('hora.recebimentos_detalhe', recebimento_id=rec.id))


# ------------------------------------------------------------------------
# Finalizar
# ------------------------------------------------------------------------

@hora_bp.route('/recebimentos/<int:recebimento_id>/finalizar', methods=['POST'])
@require_hora_perm('recebimentos', 'editar')
def recebimentos_finalizar(recebimento_id: int):
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.recebimentos_lista'))
    try:
        rec = recebimento_service.finalizar_recebimento(
            recebimento_id=rec.id, operador=_op_name(),
        )
        flash(f'Recebimento finalizado. Status: {rec.status}', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.recebimentos_detalhe', recebimento_id=rec.id))


# ------------------------------------------------------------------------
# Resolucao pos-recebimento (mantido)
# ------------------------------------------------------------------------

@hora_bp.route('/recebimentos/<int:recebimento_id>/resolver')
@require_hora_perm('recebimentos', 'ver')
def recebimentos_resolver(recebimento_id: int):
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.recebimentos_lista'))
    # Expor divergencias equivale a "ver resumo" — mesma regra do detalhe,
    # para nao dar ao conferente uma rota alternativa de "colar".
    if not current_user.tem_perm_hora('recebimento_resumo', 'ver'):
        flash(
            'Acesso a divergencias restrito. Peca validacao ao supervisor.',
            'warning',
        )
        return redirect(url_for('hora.recebimentos_lista'))
    divergencias = resolucao_service.listar_divergencias(recebimento_id)
    devolucoes_abertas = devolucao_service.listar_devolucoes(
        loja_id=rec.loja_id, status='ABERTA', limit=20,
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
@require_hora_perm('recebimentos', 'editar')
def recebimentos_resolver_aplicar(recebimento_id: int, conferencia_id: int):
    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.recebimentos_lista'))
    # Mesmo gate do GET: conferente sem permissao de resumo nao pode aplicar.
    if not current_user.tem_perm_hora('recebimento_resumo', 'ver'):
        flash(
            'Acao restrita ao supervisor (resolucao de divergencias).',
            'danger',
        )
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
            acao=acao, motivo=motivo, observacoes=obs,
            devolucao_id=devolucao_id, descricao_peca=descricao_peca,
            operador=_op_name(),
        )
        flash(f'Acao {acao} aplicada (chassi {conf.numero_chassi}).', 'success')
        if res.get('devolucao_id'):
            return redirect(url_for('hora.devolucoes_detalhe', devolucao_id=res['devolucao_id']))
        if res.get('peca_faltando_id'):
            return redirect(url_for('hora.pecas_detalhe', peca_id=res['peca_faltando_id']))
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.recebimentos_resolver', recebimento_id=recebimento_id))


# ------------------------------------------------------------------------
# Criar modelo rapido (mantido)
# ------------------------------------------------------------------------

@hora_bp.route('/modelos/criar-rapido', methods=['POST'])
@require_hora_perm('modelos', 'criar')
def modelos_criar_rapido():
    nome = (request.form.get('nome_modelo') or '').strip()
    if not nome:
        return jsonify({'ok': False, 'erro': 'nome_modelo obrigatorio'}), 400
    try:
        modelo = buscar_ou_criar_modelo(nome)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        modelo = HoraModelo.query.filter_by(nome_modelo=nome).first()
        if not modelo:
            return jsonify({'ok': False, 'erro': 'falha ao criar/recuperar modelo'}), 500
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(exc)}), 400
    return jsonify({'ok': True, 'modelo_id': modelo.id, 'nome_modelo': modelo.nome_modelo})

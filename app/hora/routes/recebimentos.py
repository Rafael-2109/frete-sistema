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
from app.hora.services.auth_helper import lojas_permitidas_ids, usuario_tem_acesso_a_loja


def _op_name() -> str | None:
    return current_user.nome if hasattr(current_user, 'nome') else None


# ------------------------------------------------------------------------
# Listagem
# ------------------------------------------------------------------------

@hora_bp.route('/recebimentos')
@require_hora_perm('recebimentos', 'ver')
def recebimentos_lista():
    from datetime import datetime as _dt

    loja_id_str = request.args.get('loja_id') or ''
    status = request.args.get('status') or None
    loja_id = int(loja_id_str) if loja_id_str.isdigit() else None
    numero_nf = (request.args.get('numero_nf') or '').strip() or None
    data_ini_str = (request.args.get('data_inicio') or '').strip()
    data_fim_str = (request.args.get('data_fim') or '').strip()

    if loja_id and not usuario_tem_acesso_a_loja(loja_id):
        flash('Acesso negado a essa loja.', 'danger')
        return redirect(url_for('hora.recebimentos_lista'))

    try:
        data_inicio = _dt.strptime(data_ini_str, '%Y-%m-%d').date() if data_ini_str else None
        data_fim = _dt.strptime(data_fim_str, '%Y-%m-%d').date() if data_fim_str else None
    except ValueError:
        flash('Data invalida (use formato YYYY-MM-DD).', 'warning')
        data_inicio = None
        data_fim = None

    permitidas = lojas_permitidas_ids()
    recebimentos = recebimento_service.listar_recebimentos(
        loja_id=loja_id, status=status, limit=200,
        lojas_permitidas_ids=permitidas,
        numero_nf=numero_nf,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    # Pre-calcula metricas (qtd_nf, qtd_recebidas, qtd_divergencias, ...) para
    # cada recebimento — evita logica complexa no template.
    linhas = [
        {'rec': r, 'metricas': recebimento_service.metricas_recebimento(r)}
        for r in recebimentos
    ]
    lojas_query = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        lojas_query = lojas_query.filter(HoraLoja.id.in_(permitidas))
    lojas = lojas_query.order_by(HoraLoja.nome).all()
    return render_template(
        'hora/recebimentos_lista.html',
        linhas=linhas,
        lojas=lojas,
        filtro_loja_id=loja_id,
        filtro_status=status,
        filtro_numero_nf=numero_nf,
        filtro_data_inicio=data_ini_str,
        filtro_data_fim=data_fim_str,
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

    # NFs pesquisadas via autocomplete on-demand
    # (endpoint /hora/autocomplete/nf-entrada?sem_recebimento=1, ver
    # `app/hora/services/autocomplete_service.nfs_entrada`). O filtro
    # `~HoraNfEntrada.recebimentos.any()` (evitar abrir 2 conferencias
    # para a mesma NF) e aplicado no service via o parametro
    # `sem_recebimento=True`, garantindo paridade com o select legado.
    permitidas = lojas_permitidas_ids()
    lojas_q = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        lojas_q = lojas_q.filter(HoraLoja.id.in_(permitidas))
    lojas = lojas_q.order_by(HoraLoja.nome).all()
    return render_template('hora/recebimento_novo.html', lojas=lojas)


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

    from app.hora.services.modelo_resolver_service import resolver_modelo
    from app.hora.models import ALIAS_TIPO_NOME_NF, HoraMoto

    confs_ativas = [c for c in rec.conferencias if not c.substituida]
    conf_por_chassi = {c.numero_chassi: c for c in confs_ativas}
    total_conferidas = sum(1 for c in confs_ativas if c.confirmado_em is not None)

    # Pre-carrega motos dos chassis da NF para evitar N+1 ao resolver canonico.
    chassis_nf = [it.numero_chassi for it in rec.nf.itens if it.numero_chassi]
    motos_por_chassi = {
        m.numero_chassi: m
        for m in HoraMoto.query.filter(HoraMoto.numero_chassi.in_(chassis_nf)).all()
    } if chassis_nf else {}

    def _resolver_modelo_canonico(it):
        """Modelo canonico para exibir no modal: prioriza HoraMoto.modelo
        (FK ja segue cadeia merged_em_id apos correcao do recebimento) e
        cai em resolver_modelo do texto NF como fallback. Retorna None se
        ainda nao resolveu (pendencia)."""
        moto = motos_por_chassi.get(it.numero_chassi)
        if moto and moto.modelo:
            return moto.modelo.nome_modelo
        if it.modelo_texto_original:
            mc = (
                resolver_modelo(it.modelo_texto_original, tipo=ALIAS_TIPO_NOME_NF)
                or resolver_modelo(it.modelo_texto_original)
            )
            if mc is not None:
                return mc.nome_modelo
        return None

    itens = []
    for it in rec.nf.itens:
        conf = conf_por_chassi.get(it.numero_chassi)
        conferida = conf is not None and conf.confirmado_em is not None
        if filtro == 'conferidas' and not conferida:
            continue
        itens.append({
            'chassi': it.numero_chassi,
            'modelo': _resolver_modelo_canonico(it),
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

        # Roadmap #8: foto do chassi (multipart) quando digitado manualmente
        # (sem leitura por QR/codigo de barras). Sobe ao S3 antes de registrar;
        # o service revalida a obrigatoriedade (qr_code_lido=False exige foto).
        foto_s3_key = recebimento_service.upload_foto_chassi(
            request.files.get('foto'), recebimento_id,
        )

        conf = recebimento_service.registrar_conferencia_cega(
            recebimento_id=recebimento_id,
            numero_chassi=numero_chassi,
            modelo_id_conferido=modelo_id,
            cor_conferida=cor,
            avaria_fisica=avaria,
            qr_code_lido=qr,
            foto_s3_key=foto_s3_key,
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
# Recebimento automatico de NF inteira (Item 1 — 2026-05-16)
# ------------------------------------------------------------------------

@hora_bp.route('/recebimentos/automatico/nfs-pendentes')
@require_hora_perm('recebimentos', 'criar')
def recebimentos_automatico_listar_nfs():
    """JSON: NFs sem recebimento + agregados (alimenta o modal admin)."""
    if not _exige_admin():
        return jsonify({'ok': False, 'erro': 'apenas administradores'}), 403
    permitidas = lojas_permitidas_ids()
    nfs = recebimento_service.listar_nfs_para_recebimento_automatico(
        lojas_permitidas_ids=permitidas, limit=200,
    )
    return jsonify({'ok': True, 'nfs': nfs, 'total': len(nfs)})


@hora_bp.route('/recebimentos/automatico/criar', methods=['POST'])
@require_hora_perm('recebimentos', 'criar')
def recebimentos_automatico_criar():
    """Cria recebimento automatico para 1..N NFs selecionadas."""
    if not _exige_admin():
        return jsonify({'ok': False, 'erro': 'apenas administradores'}), 403

    data = request.get_json(silent=True) or request.form
    nf_ids_raw = data.get('nf_ids') or data.getlist('nf_ids[]') if hasattr(data, 'getlist') else (data.get('nf_ids') or [])
    if isinstance(nf_ids_raw, str):
        nf_ids_raw = [nf_ids_raw]
    try:
        nf_ids = [int(x) for x in nf_ids_raw if str(x).strip().isdigit()]
    except (TypeError, ValueError):
        nf_ids = []
    if not nf_ids:
        return jsonify({'ok': False, 'erro': 'nenhuma NF selecionada'}), 400

    from app.hora.models import HoraNfEntrada as _HoraNfEntrada
    resultados = []
    erros = []
    for nf_id in nf_ids:
        # Verifica permissao de loja antes de chamar o service
        nf_obj = _HoraNfEntrada.query.get(nf_id)
        if nf_obj and nf_obj.loja_destino_id and not usuario_tem_acesso_a_loja(nf_obj.loja_destino_id):
            erros.append({'nf_id': nf_id, 'erro': 'acesso negado a essa loja'})
            continue
        try:
            res = recebimento_service.criar_recebimento_automatico_da_nf(
                nf_id=nf_id, operador=_op_name(),
            )
            resultados.append(res)
        except ValueError as exc:
            erros.append({'nf_id': nf_id, 'erro': str(exc)})

    return jsonify({
        'ok': len(erros) == 0,
        'criados': resultados,
        'erros': erros,
        'total_pedidos': len(nf_ids),
        'total_criados': len(resultados),
        'total_erros': len(erros),
    })


# ------------------------------------------------------------------------
# Exclusao admin-only (Item 2 — 2026-05-16)
# ------------------------------------------------------------------------

def _exige_admin() -> bool:
    """Defesa em profundidade: alem da perm recebimentos/apagar, exige admin."""
    return getattr(current_user, 'perfil', None) == 'administrador'


@hora_bp.route('/recebimentos/<int:recebimento_id>/pre-check-exclusao')
@require_hora_perm('recebimentos', 'apagar')
def recebimentos_pre_check_exclusao(recebimento_id: int):
    """Endpoint JSON para alimentar o modal de confirmacao de exclusao.

    Retorna bloqueios + efeitos colaterais sem mutar nada.
    """
    if not _exige_admin():
        return jsonify({'ok': False, 'erro': 'apenas administradores podem excluir'}), 403
    info = recebimento_service.verificar_bloqueios_exclusao(recebimento_id)
    if not info['existe']:
        return jsonify({'ok': False, 'erro': 'recebimento nao encontrado'}), 404
    return jsonify({'ok': True, **info})


@hora_bp.route('/recebimentos/<int:recebimento_id>/excluir', methods=['POST'])
@require_hora_perm('recebimentos', 'apagar')
def recebimentos_excluir(recebimento_id: int):
    """Exclui recebimento e suas conexoes pos-recebimento (admin-only).

    Bloqueia se houver:
      - peca faltando ABERTA vinculada a conferencias do recebimento;
      - item de devolucao ao fornecedor vinculado a conferencias.
    """
    if not _exige_admin():
        flash('Apenas administradores podem excluir recebimentos.', 'danger')
        return redirect(url_for('hora.recebimentos_detalhe', recebimento_id=recebimento_id))

    rec = HoraRecebimento.query.get_or_404(recebimento_id)
    if not usuario_tem_acesso_a_loja(rec.loja_id):
        flash('Acesso negado a essa loja.', 'danger')
        return redirect(url_for('hora.recebimentos_lista'))

    confirm = request.form.get('confirm') == '1'
    if not confirm:
        flash('Exclusao nao confirmada.', 'warning')
        return redirect(url_for('hora.recebimentos_detalhe', recebimento_id=rec.id))

    try:
        resultado = recebimento_service.excluir_recebimento(
            recebimento_id=rec.id, operador=_op_name(),
        )
        flash(
            f'Recebimento #{resultado["recebimento_id"]} excluido. '
            f'NF={resultado["nf_numero"]} loja={resultado["loja_nome"]} '
            f'(eventos_deletados={resultado["eventos_deletados"]}, '
            f'confs={resultado["confs_deletadas"]}, divs={resultado["divs_deletadas"]}).',
            'success',
        )
        return redirect(url_for('hora.recebimentos_lista'))
    except ValueError as exc:
        flash(f'Erro ao excluir: {exc}', 'danger')
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
    """Cria um modelo intencionalmente (operador clica "Criar modelo X").

    Antes de criar, consulta hora_modelo_alias (qualquer tipo) e
    hora_modelo.nome_modelo para evitar duplicacao quando o nome digitado
    for sinonimo de um canonico ja existente. Se resolver, devolve o
    canonico com aviso ao inves de criar um novo modelo (regra
    2026-05-06: padronizar nomes na conferencia/recebimento/estoque/venda
    via canonico unico).

    Apenas se nao resolver e que cria HoraModelo + HoraModeloAlias
    NOME_LIVRE (consistencia com seed hora_30).
    """
    from app.hora.services import cadastro_service
    from app.hora.services.modelo_resolver_service import resolver_modelo
    from app.hora.models import HoraModeloAlias, ALIAS_TIPO_NOME_LIVRE

    nome = (request.form.get('nome_modelo') or '').strip()
    if not nome:
        return jsonify({'ok': False, 'erro': 'nome_modelo obrigatorio'}), 400

    # 1. Tenta resolver via aliases ANTES de criar (evita duplicado lateral)
    canonico = resolver_modelo(nome)
    if canonico is not None:
        return jsonify({
            'ok': True,
            'modelo_id': canonico.id,
            'nome_modelo': canonico.nome_modelo,
            'aviso': (
                f'Nome {nome!r} ja vinculado ao modelo canonico '
                f'{canonico.nome_modelo!r} via alias. Reusando.'
            ),
            'reusou_canonico': True,
        })

    # 2. Nao resolveu — cria HoraModelo novo + alias NOME_LIVRE
    try:
        modelo = cadastro_service.criar_modelo(nome_modelo=nome)
        existente = (
            HoraModeloAlias.query
            .filter_by(tipo=ALIAS_TIPO_NOME_LIVRE, nome_alias=nome)
            .first()
        )
        if not existente:
            db.session.add(HoraModeloAlias(
                modelo_id=modelo.id,
                nome_alias=nome,
                tipo=ALIAS_TIPO_NOME_LIVRE,
                criado_por=getattr(current_user, 'username', None),
                observacao='Auto-alias do nome_modelo canonico (criar-rapido)',
            ))
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        # Race: outro request criou entre o resolver e o criar_modelo.
        modelo = HoraModelo.query.filter_by(nome_modelo=nome).first()
        if modelo:
            return jsonify({
                'ok': True,
                'modelo_id': modelo.id,
                'nome_modelo': modelo.nome_modelo,
                'aviso': 'Modelo ja existia.',
            })
        return jsonify({'ok': False, 'erro': str(exc)}), 400
    except IntegrityError:
        db.session.rollback()
        modelo = HoraModelo.query.filter_by(nome_modelo=nome).first()
        if not modelo:
            return jsonify({'ok': False, 'erro': 'falha ao criar/recuperar modelo'}), 500
    return jsonify({'ok': True, 'modelo_id': modelo.id, 'nome_modelo': modelo.nome_modelo})

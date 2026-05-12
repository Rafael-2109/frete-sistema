from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import UploadPedidoVoeForm
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiPedidoVendaLoja,
    AssaiLoja, AssaiModelo,
    AssaiSeparacao, SEPARACAO_STATUS_CANCELADA,
    PEDIDO_STATUS_ABERTO,
)
from app.motos_assai.services import (
    importar_pdf_voe, PedidoVoeJaExisteError, PedidoVoeParserError,
    atualizar_agendamento_loja, criar_separacao_com_saldos,
    saldo_pendente_por_modelo, SeparacaoValidationError,
)


@motos_assai_bp.route('/pedidos/upload', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def pedidos_upload():
    form = UploadPedidoVoeForm()
    if form.validate_on_submit():
        pdf_file = form.pdf.data
        pdf_bytes = pdf_file.read()
        try:
            pedido = importar_pdf_voe(
                pdf_bytes=pdf_bytes,
                nome_arquivo=pdf_file.filename or 'pedido.pdf',
                importado_por_id=current_user.id,
            )
            flash(
                f'Pedido {pedido.numero} importado via {pedido.parser_usado} '
                f'(confiança {float(pedido.parsing_confianca):.0%}).',
                'success',
            )
            return redirect(url_for('motos_assai.pedidos_detalhe', pedido_id=pedido.id))
        except PedidoVoeJaExisteError as e:
            flash(str(e), 'warning')
        except PedidoVoeParserError as e:
            current_app.logger.exception('Erro ao parsear pedido VOE')
            flash(f'Erro ao parsear PDF: {e}', 'danger')
    return render_template('motos_assai/pedidos/upload.html', form=form)


@motos_assai_bp.route('/pedidos/<int:pedido_id>')
@login_required
@require_motos_assai
def pedidos_detalhe(pedido_id):
    pedido = AssaiPedidoVenda.query.get_or_404(pedido_id)

    # Totais por modelo (cross-loja)
    totais_por_modelo = (
        db.session.query(
            AssaiModelo.codigo,
            AssaiModelo.nome,
            func.sum(AssaiPedidoVendaItem.qtd_pedida).label('qtd'),
            func.sum(AssaiPedidoVendaItem.valor_total).label('valor'),
        )
        .join(AssaiPedidoVendaItem, AssaiPedidoVendaItem.modelo_id == AssaiModelo.id)
        .filter(AssaiPedidoVendaItem.pedido_id == pedido_id)
        .group_by(AssaiModelo.id, AssaiModelo.codigo, AssaiModelo.nome)
        .order_by(AssaiModelo.codigo)
        .all()
    )

    # Lojas com seus items
    lojas_items = (
        db.session.query(AssaiLoja, AssaiPedidoVendaItem, AssaiModelo)
        .join(AssaiPedidoVendaItem, AssaiPedidoVendaItem.loja_id == AssaiLoja.id)
        .join(AssaiModelo, AssaiModelo.id == AssaiPedidoVendaItem.modelo_id)
        .filter(AssaiPedidoVendaItem.pedido_id == pedido_id)
        .order_by(AssaiLoja.numero, AssaiModelo.codigo)
        .all()
    )

    # Cabecalhos AssaiPedidoVendaLoja (4 campos de agendamento por loja)
    pvls = AssaiPedidoVendaLoja.query.filter_by(pedido_id=pedido_id).all()
    pvl_por_loja = {p.loja_id: p for p in pvls}

    # Saldo pendente por (loja, modelo) — qtd ja em separacoes nao-canceladas
    saldo_por_loja_modelo: dict = {}
    for loja_obj in {it[0] for it in lojas_items}:
        for s in saldo_pendente_por_modelo(pedido_id, loja_obj.id):
            saldo_por_loja_modelo[(loja_obj.id, s['modelo_id'])] = s

    # Separacoes EM_SEPARACAO ativas por loja (para indicar checkbox/criar nova)
    seps_ativas = (
        AssaiSeparacao.query
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
        )
        .all()
    )
    seps_por_loja: dict = {}
    for s in seps_ativas:
        seps_por_loja.setdefault(s.loja_id, []).append(s)

    # Agrupa por loja para template
    por_loja: dict = {}
    for loja, item, modelo in lojas_items:
        por_loja.setdefault(loja.id, {
            'loja': loja,
            'items': [],
            'pvl': pvl_por_loja.get(loja.id),
            'seps_ativas': seps_por_loja.get(loja.id, []),
        })
        saldo = saldo_por_loja_modelo.get((loja.id, item.modelo_id), {})
        por_loja[loja.id]['items'].append({
            'item': item,
            'modelo': modelo,
            'qtd_separada': saldo.get('qtd_separada', 0),
            'qtd_pendente': saldo.get('qtd_pendente', item.qtd_pedida),
        })

    return render_template(
        'motos_assai/pedidos/detalhe.html',
        pedido=pedido,
        totais_por_modelo=totais_por_modelo,
        por_loja=list(por_loja.values()),
    )


# =====================================================================
# Task #6: agendamento por loja (4 campos)
# =====================================================================

def _parse_data_iso(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        raise SeparacaoValidationError(f'Data invalida (esperado YYYY-MM-DD): {s}')


@motos_assai_bp.route(
    '/pedidos/<int:pedido_id>/loja/<int:loja_id>/agendamento',
    methods=['POST'],
)
@login_required
@require_motos_assai
def pedidos_agendamento_loja(pedido_id, loja_id):
    """Atualiza 4 campos (expedicao/agendamento/protocolo/agendamento_confirmado)
    no cabecalho AssaiPedidoVendaLoja. Propaga para espelhos FECHADOS automaticamente.

    K10 (2026-05-12): PATCH semantics explicito via sentinela `_PRESERVAR`:
    - chave AUSENTE no JSON -> preservar valor atual
    - chave PRESENTE com `''` ou `null` -> LIMPAR (SET NULL/False)
    - chave PRESENTE com valor -> SETAR

    Body JSON: {
        expedicao?: 'YYYY-MM-DD' | '' | null,
        agendamento?: 'YYYY-MM-DD' | '' | null,
        protocolo?: str | '' | null,
        agendamento_confirmado?: bool | null,
    }
    """
    from app.motos_assai.services.separacao_service import _PRESERVAR

    data = request.get_json(silent=True) or {}
    try:
        # Normaliza cada campo. _PRESERVAR se chave ausente; None se vazio; valor caso contrario.
        if 'expedicao' in data:
            v = data['expedicao']
            exp_kwarg = _parse_data_iso(v) if v else None
        else:
            exp_kwarg = _PRESERVAR

        if 'agendamento' in data:
            v = data['agendamento']
            ag_kwarg = _parse_data_iso(v) if v else None
        else:
            ag_kwarg = _PRESERVAR

        if 'protocolo' in data:
            v = data['protocolo']
            prot_kwarg = v if v else None  # '' -> None
        else:
            prot_kwarg = _PRESERVAR

        if 'agendamento_confirmado' in data:
            v = data['agendamento_confirmado']
            conf_kwarg = bool(v) if v is not None else None
        else:
            conf_kwarg = _PRESERVAR

        pvl = atualizar_agendamento_loja(
            pedido_id=pedido_id, loja_id=loja_id,
            expedicao=exp_kwarg,
            agendamento=ag_kwarg,
            protocolo=prot_kwarg,
            agendamento_confirmado=conf_kwarg,
            operador_id=current_user.id,
        )
    except SeparacaoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400

    return jsonify({
        'ok': True,
        'pvl': {
            'pedido_id': pvl.pedido_id,
            'loja_id': pvl.loja_id,
            'expedicao': pvl.expedicao.strftime('%Y-%m-%d') if pvl.expedicao else None,
            'agendamento': pvl.agendamento.strftime('%Y-%m-%d') if pvl.agendamento else None,
            'protocolo': pvl.protocolo,
            'agendamento_confirmado': pvl.agendamento_confirmado,
        },
    })


# =====================================================================
# Task #7: criar separacao via checkbox + qtd
# =====================================================================

@motos_assai_bp.route(
    '/pedidos/<int:pedido_id>/loja/<int:loja_id>/separacao/criar',
    methods=['POST'],
)
@login_required
@require_motos_assai
def pedidos_separacao_criar(pedido_id, loja_id):
    """Cria nova AssaiSeparacao (EM_SEPARACAO) com qtd planejada por modelo.

    Body JSON: {alocacoes: [{modelo_id, qtd}, ...]}

    Retorna a separacao recem criada para redirect ao escaneio.
    """
    data = request.get_json(silent=True) or {}
    alocacoes = data.get('alocacoes') or []
    try:
        sep = criar_separacao_com_saldos(
            pedido_id=pedido_id, loja_id=loja_id,
            alocacoes=alocacoes,
            operador_id=current_user.id,
        )
    except SeparacaoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400

    return jsonify({
        'ok': True,
        'separacao_id': sep.id,
        'redirect': url_for(
            'motos_assai.separacao_tela',
            pedido_id=pedido_id, loja_id=loja_id,
        ),
    })


@motos_assai_bp.route('/pedidos')
@login_required
@require_motos_assai
def pedidos_lista():
    status = request.args.get('status', '').strip() or None
    q = AssaiPedidoVenda.query

    if status:
        q = q.filter_by(status=status)

    pedidos = q.order_by(AssaiPedidoVenda.criado_em.desc()).limit(250).all()

    return render_template(
        'motos_assai/pedidos/lista.html',
        pedidos=pedidos,
        status_filtro=status,
        statuses=['ABERTO', 'EM_PRODUCAO', 'SEPARANDO', 'FATURADO_PARCIAL', 'FATURADO', 'CANCELADO'],
    )

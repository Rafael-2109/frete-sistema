"""Rotas de Devolucao de Venda (cliente final -> HORA).

Distinto de `devolucoes.py` (devolucao ao fornecedor / Motochefe).

Fluxo de telas:
    /hora/devolucoes-venda                    GET  -> lista
    /hora/devolucoes-venda/novo               GET  -> form pesquisa NF
                                              POST -> cria devolucao
    /hora/devolucoes-venda/api/buscar-vendas  GET  -> AJAX, busca NF
    /hora/devolucoes-venda/api/motos-da-venda GET  -> AJAX, motos da NF
    /hora/devolucoes-venda/<id>               GET  -> detalhe + resolver
    /hora/devolucoes-venda/<id>/resolver-item/<item_id>  POST -> aplica resolucao
    /hora/devolucoes-venda/<id>/cancelar      POST -> cancela
"""
from __future__ import annotations

from datetime import datetime as _dt

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.hora.decorators import require_hora_perm
from app.hora.models import (
    DEV_VENDA_ACAO_AVARIA,
    DEV_VENDA_ACAO_DISPONIVEL,
    DEV_VENDA_ACAO_PECA_FALTANDO,
    DEV_VENDA_STATUS_CANCELADA,
    DEV_VENDA_STATUS_PENDENTE,
    DEV_VENDA_STATUS_RESOLVIDA,
    HoraDevolucaoVenda,
    HoraLoja,
)
from app.hora.routes import hora_bp
from app.hora.services import devolucao_venda_service
from app.hora.services.auth_helper import (
    lojas_permitidas_ids,
    usuario_tem_acesso_a_loja,
)


def _operador_atual():
    return getattr(current_user, 'nome', None)


def _redirect_sem_acesso():
    flash('Acesso negado a essa devolucao (loja fora do seu escopo).', 'danger')
    return redirect(url_for('hora.devolucoes_venda_lista'))


def _lojas_permitidas_visiveis():
    permitidas = lojas_permitidas_ids()
    q = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        if not permitidas:
            return []
        q = q.filter(HoraLoja.id.in_(permitidas))
    return q.order_by(HoraLoja.nome).all()


# ---------------------------------------------------------------------------
# Listagem
# ---------------------------------------------------------------------------
@hora_bp.route('/devolucoes-venda')
@require_hora_perm('devolucoes_venda', 'ver')
def devolucoes_venda_lista():
    permitidas = lojas_permitidas_ids()

    status = (request.args.get('status') or '').strip() or None
    loja_id_str = (request.args.get('loja_id') or '').strip()
    loja_id = int(loja_id_str) if loja_id_str.isdigit() else None
    if loja_id and not usuario_tem_acesso_a_loja(loja_id):
        return _redirect_sem_acesso()

    chassi = (request.args.get('chassi') or '').strip() or None
    nf_saida = (request.args.get('nf_saida') or '').strip() or None
    motivo = (request.args.get('motivo') or '').strip() or None
    data_ini_str = (request.args.get('data_inicio') or '').strip()
    data_fim_str = (request.args.get('data_fim') or '').strip()
    try:
        data_inicio = _dt.strptime(data_ini_str, '%Y-%m-%d').date() if data_ini_str else None
        data_fim = _dt.strptime(data_fim_str, '%Y-%m-%d').date() if data_fim_str else None
    except ValueError:
        flash('Data invalida (use formato YYYY-MM-DD).', 'warning')
        data_inicio = None
        data_fim = None

    devolucoes = devolucao_venda_service.listar_devolucoes(
        status=status,
        loja_id=loja_id,
        lojas_permitidas_ids=permitidas,
        chassi=chassi,
        nf_saida=nf_saida,
        motivo=motivo,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    return render_template(
        'hora/devolucao_venda_lista.html',
        devolucoes=devolucoes,
        lojas=_lojas_permitidas_visiveis(),
        filtro_loja_id=loja_id,
        filtro_status=status,
        filtro_chassi=chassi,
        filtro_nf_saida=nf_saida,
        filtro_motivo=motivo,
        filtro_data_inicio=data_ini_str,
        filtro_data_fim=data_fim_str,
        STATUS_OPCOES=[
            (DEV_VENDA_STATUS_PENDENTE, 'Pendente'),
            (DEV_VENDA_STATUS_RESOLVIDA, 'Resolvida'),
            (DEV_VENDA_STATUS_CANCELADA, 'Cancelada'),
        ],
    )


# ---------------------------------------------------------------------------
# Criar (form + submit)
# ---------------------------------------------------------------------------
@hora_bp.route('/devolucoes-venda/novo', methods=['GET', 'POST'])
@require_hora_perm('devolucoes_venda', 'criar')
def devolucoes_venda_novo():
    if request.method == 'POST':
        try:
            venda_id_str = (request.form.get('venda_id') or '').strip()
            if not venda_id_str.isdigit():
                raise ValueError('venda_id ausente ou invalido')
            venda_id = int(venda_id_str)

            motivo = (request.form.get('motivo') or '').strip()

            # Chassis selecionados via checkbox; cada um traz um motivo_especifico.
            chassis_selecionados = request.form.getlist('chassis_selecionados')
            payload = []
            for chassi in chassis_selecionados:
                chassi = (chassi or '').strip().upper()
                if not chassi:
                    continue
                motivo_esp = (
                    request.form.get(f'motivo_especifico__{chassi}') or ''
                ).strip() or None
                payload.append({
                    'numero_chassi': chassi,
                    'motivo_especifico': motivo_esp,
                })

            if not payload:
                raise ValueError('Selecione ao menos 1 chassi.')

            dev = devolucao_venda_service.criar_devolucao_de_venda(
                venda_id=venda_id,
                chassis=payload,
                motivo=motivo,
                criado_por=_operador_atual(),
            )

            if not usuario_tem_acesso_a_loja(dev.loja_id):
                flash(
                    'Devolucao criada, mas a loja da venda esta fora do seu escopo.',
                    'warning',
                )
                return redirect(url_for('hora.devolucoes_venda_lista'))

            flash(f'Devolucao de venda #{dev.id} criada.', 'success')
            return redirect(
                url_for('hora.devolucoes_venda_detalhe', devolucao_id=dev.id)
            )
        except ValueError as exc:
            db.session.rollback()
            flash(f'Erro: {exc}', 'danger')

    return render_template('hora/devolucao_venda_novo.html')


# ---------------------------------------------------------------------------
# AJAX: pesquisa de venda + motos da venda
# ---------------------------------------------------------------------------
@hora_bp.route('/devolucoes-venda/api/buscar-vendas')
@require_hora_perm('devolucoes_venda', 'criar')
def devolucoes_venda_api_buscar_vendas():
    termo = (request.args.get('q') or '').strip()
    if len(termo) < 2:
        return jsonify({'ok': True, 'vendas': []})
    vendas = devolucao_venda_service.buscar_vendas_para_devolucao(
        termo=termo, lojas_permitidas_ids=lojas_permitidas_ids(),
    )
    return jsonify({'ok': True, 'vendas': vendas})


@hora_bp.route('/devolucoes-venda/api/motos-da-venda')
@require_hora_perm('devolucoes_venda', 'criar')
def devolucoes_venda_api_motos_da_venda():
    venda_id_str = (request.args.get('venda_id') or '').strip()
    if not venda_id_str.isdigit():
        return jsonify({'ok': False, 'erro': 'venda_id invalido'}), 400
    motos = devolucao_venda_service.motos_da_venda_devolviveis(int(venda_id_str))
    return jsonify({'ok': True, 'motos': motos})


# ---------------------------------------------------------------------------
# Detalhe + resolucao
# ---------------------------------------------------------------------------
@hora_bp.route('/devolucoes-venda/<int:devolucao_id>')
@require_hora_perm('devolucoes_venda', 'ver')
def devolucoes_venda_detalhe(devolucao_id: int):
    dev = HoraDevolucaoVenda.query.get_or_404(devolucao_id)
    if not usuario_tem_acesso_a_loja(dev.loja_id):
        return _redirect_sem_acesso()
    return render_template(
        'hora/devolucao_venda_detalhe.html',
        devolucao=dev,
        ACAO_DISPONIVEL=DEV_VENDA_ACAO_DISPONIVEL,
        ACAO_AVARIA=DEV_VENDA_ACAO_AVARIA,
        ACAO_PECA_FALTANDO=DEV_VENDA_ACAO_PECA_FALTANDO,
        STATUS_PENDENTE=DEV_VENDA_STATUS_PENDENTE,
        STATUS_RESOLVIDA=DEV_VENDA_STATUS_RESOLVIDA,
        STATUS_CANCELADA=DEV_VENDA_STATUS_CANCELADA,
    )


@hora_bp.route(
    '/devolucoes-venda/<int:devolucao_id>/resolver-item/<int:item_id>',
    methods=['POST'],
)
@require_hora_perm('devolucoes_venda', 'editar')
def devolucoes_venda_resolver_item(devolucao_id: int, item_id: int):
    dev = HoraDevolucaoVenda.query.get_or_404(devolucao_id)
    if not usuario_tem_acesso_a_loja(dev.loja_id):
        return _redirect_sem_acesso()

    try:
        acao = (request.form.get('acao') or '').strip().upper()
        observacoes = (request.form.get('observacoes') or '').strip() or None
        avaria_descricao = (
            request.form.get('avaria_descricao') or ''
        ).strip() or None
        peca_descricao = (
            request.form.get('peca_descricao') or ''
        ).strip() or None

        devolucao_venda_service.resolver_item(
            item_id=item_id,
            acao=acao,
            operador=_operador_atual(),
            observacoes=observacoes,
            avaria_descricao=avaria_descricao,
            peca_descricao=peca_descricao,
        )
        flash(f'Item resolvido como {acao}.', 'success')
    except ValueError as exc:
        db.session.rollback()
        flash(f'Erro: {exc}', 'danger')
    return redirect(
        url_for('hora.devolucoes_venda_detalhe', devolucao_id=devolucao_id)
    )


@hora_bp.route('/devolucoes-venda/<int:devolucao_id>/cancelar', methods=['POST'])
@require_hora_perm('devolucoes_venda', 'apagar')
def devolucoes_venda_cancelar(devolucao_id: int):
    dev = HoraDevolucaoVenda.query.get_or_404(devolucao_id)
    if not usuario_tem_acesso_a_loja(dev.loja_id):
        return _redirect_sem_acesso()
    motivo = (request.form.get('motivo_cancelamento') or '').strip()
    try:
        devolucao_venda_service.cancelar_devolucao(
            devolucao_id=devolucao_id,
            motivo_cancelamento=motivo,
            operador=_operador_atual(),
        )
        flash('Devolucao cancelada. Motos elegiveis voltaram ao estoque.', 'warning')
    except ValueError as exc:
        db.session.rollback()
        flash(f'Erro: {exc}', 'danger')
    return redirect(
        url_for('hora.devolucoes_venda_detalhe', devolucao_id=devolucao_id)
    )

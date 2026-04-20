"""Rotas de devolucao ao fornecedor (HORA -> Motochefe)."""
from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.hora.decorators import require_lojas as login_required
from app.hora.models import (
    HoraDevolucaoFornecedor,
    HoraLoja,
    HoraNfEntrada,
)
from app.hora.routes import hora_bp
from app.hora.services import devolucao_service
from app.hora.services.auth_helper import (
    lojas_permitidas_ids,
    usuario_tem_acesso_a_loja,
)


def _redirect_sem_acesso_devolucao(devolucao_id=None):
    flash('Acesso negado a essa devolucao (loja fora do seu escopo).', 'danger')
    if devolucao_id:
        # tenta voltar para detalhe (se user ainda tem acesso) ou para lista
        return redirect(url_for('hora.devolucoes_lista'))
    return redirect(url_for('hora.devolucoes_lista'))


def _lojas_permitidas():
    permitidas = lojas_permitidas_ids()
    q = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        if not permitidas:
            return []
        q = q.filter(HoraLoja.id.in_(permitidas))
    return q.order_by(HoraLoja.nome).all()


@hora_bp.route('/devolucoes')
@login_required
def devolucoes_lista():
    permitidas = lojas_permitidas_ids()
    status = (request.args.get('status') or '').strip() or None
    loja_id_str = (request.args.get('loja_id') or '').strip()
    loja_id = int(loja_id_str) if loja_id_str.isdigit() else None
    if loja_id and not usuario_tem_acesso_a_loja(loja_id):
        return _redirect_sem_acesso_devolucao()
    devolucoes = devolucao_service.listar_devolucoes(
        loja_id=loja_id,
        status=status,
        lojas_permitidas_ids=permitidas,
    )
    return render_template(
        'hora/devolucoes_lista.html',
        devolucoes=devolucoes,
        lojas=_lojas_permitidas(),
        filtro_loja_id=loja_id,
        filtro_status=status,
    )


@hora_bp.route('/devolucoes/novo', methods=['GET', 'POST'])
@login_required
def devolucoes_novo():
    lojas = _lojas_permitidas()
    permitidas = lojas_permitidas_ids()
    # Filtro de loja na query SQL (nao pos-limit) para nao zerar a lista
    # para usuarios restritos quando as 100 NFs mais recentes sao de outras lojas.
    q = HoraNfEntrada.query
    if permitidas is not None:
        if not permitidas:
            nfs_entrada = []
        else:
            nfs_entrada = (
                q.filter(HoraNfEntrada.loja_destino_id.in_(permitidas))
                .order_by(HoraNfEntrada.data_emissao.desc())
                .limit(100)
                .all()
            )
    else:
        nfs_entrada = (
            q.order_by(HoraNfEntrada.data_emissao.desc()).limit(100).all()
        )

    if request.method == 'POST':
        try:
            loja_id = int(request.form['loja_id'])
            motivo = request.form['motivo'].strip().upper()
            nf_str = (request.form.get('nf_entrada_id') or '').strip()
            nf_id = int(nf_str) if nf_str.isdigit() else None
            obs = (request.form.get('observacoes') or '').strip() or None

            if not usuario_tem_acesso_a_loja(loja_id):
                flash('Acesso negado a essa loja.', 'danger')
                return render_template(
                    'hora/devolucao_novo.html',
                    lojas=lojas, nfs=nfs_entrada,
                )

            dev = devolucao_service.criar_devolucao(
                loja_id=loja_id,
                motivo=motivo,
                nf_entrada_id=nf_id,
                observacoes=obs,
                criado_por=current_user.nome if hasattr(current_user, 'nome') else None,
            )
            flash(f'Devolucao #{dev.id} criada.', 'success')
            return redirect(url_for('hora.devolucoes_detalhe', devolucao_id=dev.id))
        except (ValueError, KeyError) as exc:
            flash(f'Erro: {exc}', 'danger')

    return render_template(
        'hora/devolucao_novo.html',
        lojas=lojas,
        nfs=nfs_entrada,
    )


@hora_bp.route('/devolucoes/<int:devolucao_id>')
@login_required
def devolucoes_detalhe(devolucao_id: int):
    dev = HoraDevolucaoFornecedor.query.get_or_404(devolucao_id)
    if not usuario_tem_acesso_a_loja(dev.loja_id):
        return _redirect_sem_acesso_devolucao()
    return render_template('hora/devolucao_detalhe.html', devolucao=dev)


@hora_bp.route('/devolucoes/<int:devolucao_id>/adicionar-item', methods=['POST'])
@login_required
def devolucoes_adicionar_item(devolucao_id: int):
    dev = HoraDevolucaoFornecedor.query.get_or_404(devolucao_id)
    if not usuario_tem_acesso_a_loja(dev.loja_id):
        return _redirect_sem_acesso_devolucao()
    try:
        chassi = (request.form.get('numero_chassi') or '').strip().upper()
        motivo_esp = (request.form.get('motivo_especifico') or '').strip() or None
        if not chassi:
            raise ValueError('chassi vazio')
        devolucao_service.adicionar_item(
            devolucao_id=devolucao_id,
            numero_chassi=chassi,
            motivo_especifico=motivo_esp,
        )
        flash(f'Chassi {chassi} adicionado.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.devolucoes_detalhe', devolucao_id=devolucao_id))


@hora_bp.route('/devolucoes/<int:devolucao_id>/remover-item/<int:item_id>', methods=['POST'])
@login_required
def devolucoes_remover_item(devolucao_id: int, item_id: int):
    dev = HoraDevolucaoFornecedor.query.get_or_404(devolucao_id)
    if not usuario_tem_acesso_a_loja(dev.loja_id):
        return _redirect_sem_acesso_devolucao()
    try:
        devolucao_service.remover_item(devolucao_id, item_id)
        flash('Item removido.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.devolucoes_detalhe', devolucao_id=devolucao_id))


@hora_bp.route('/devolucoes/<int:devolucao_id>/enviar', methods=['POST'])
@login_required
def devolucoes_enviar(devolucao_id: int):
    dev = HoraDevolucaoFornecedor.query.get_or_404(devolucao_id)
    if not usuario_tem_acesso_a_loja(dev.loja_id):
        return _redirect_sem_acesso_devolucao()
    nf_numero = (request.form.get('nf_saida_numero') or '').strip() or None
    nf_chave = (request.form.get('nf_saida_chave_44') or '').strip() or None
    try:
        devolucao_service.enviar_devolucao(
            devolucao_id=devolucao_id,
            nf_saida_numero=nf_numero,
            nf_saida_chave_44=nf_chave,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash('Devolucao enviada. Motos saíram do estoque.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.devolucoes_detalhe', devolucao_id=devolucao_id))


@hora_bp.route('/devolucoes/<int:devolucao_id>/confirmar', methods=['POST'])
@login_required
def devolucoes_confirmar(devolucao_id: int):
    dev = HoraDevolucaoFornecedor.query.get_or_404(devolucao_id)
    if not usuario_tem_acesso_a_loja(dev.loja_id):
        return _redirect_sem_acesso_devolucao()
    try:
        devolucao_service.confirmar_devolucao(devolucao_id)
        flash('Devolucao confirmada pelo fornecedor.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.devolucoes_detalhe', devolucao_id=devolucao_id))


@hora_bp.route('/devolucoes/<int:devolucao_id>/cancelar', methods=['POST'])
@login_required
def devolucoes_cancelar(devolucao_id: int):
    dev = HoraDevolucaoFornecedor.query.get_or_404(devolucao_id)
    if not usuario_tem_acesso_a_loja(dev.loja_id):
        return _redirect_sem_acesso_devolucao()
    try:
        devolucao_service.cancelar_devolucao(
            devolucao_id,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash('Devolucao cancelada.', 'warning')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.devolucoes_detalhe', devolucao_id=devolucao_id))

"""Rotas de Cadastro de Pecas (cadastros)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.hora.decorators import require_hora_perm
from app.hora.models import HoraPeca
from app.hora.routes import hora_bp
from app.hora.services import peca_service


def _operador() -> str:
    if hasattr(current_user, 'nome'):
        return current_user.nome
    return getattr(current_user, 'email', 'desconhecido')


@hora_bp.route('/pecas/cadastro')
@require_hora_perm('pecas_cadastro', 'ver')
def pecas_cadastro_lista():
    busca = (request.args.get('busca') or '').strip() or None
    apenas_ativos = request.args.get('apenas_ativos') == '1'
    sem_tagplus = request.args.get('sem_tagplus') == '1'

    pecas = peca_service.listar_pecas(
        busca=busca,
        ativo=True if apenas_ativos else None,
        sem_tagplus=sem_tagplus,
    )
    rows = []
    for p in pecas:
        rows.append({
            'peca': p,
            'foto_url': peca_service.get_foto_url(p),
            'tagplus_map': p.tagplus_map,
        })
    return render_template(
        'hora/pecas_cadastro_lista.html',
        rows=rows,
        filtro_busca=busca,
        filtro_apenas_ativos=apenas_ativos,
        filtro_sem_tagplus=sem_tagplus,
    )


@hora_bp.route('/pecas/cadastro/novo', methods=['GET', 'POST'])
@require_hora_perm('pecas_cadastro', 'criar')
def pecas_cadastro_novo():
    if request.method == 'POST':
        try:
            preco = (request.form.get('preco_venda_padrao') or '0').replace(',', '.')
            custo = (request.form.get('custo') or '0').replace(',', '.')
            p = peca_service.criar_peca(
                codigo_interno=(request.form.get('codigo_interno') or ''),
                descricao=(request.form.get('descricao') or ''),
                ncm=(request.form.get('ncm') or '') or None,
                cfop_default=(request.form.get('cfop_default') or '5.102'),
                unidade=(request.form.get('unidade') or 'UN'),
                preco_venda_padrao=Decimal(preco),
                custo=Decimal(custo),
                ativo=request.form.get('ativo') == '1',
            )
            tp_id = (request.form.get('tagplus_produto_id') or '').strip()
            if tp_id:
                peca_service.set_tagplus_map(
                    peca_id=p.id,
                    tagplus_produto_id=tp_id,
                    tagplus_codigo=(request.form.get('tagplus_codigo') or '') or None,
                    cfop_default=(request.form.get('tagplus_cfop_default') or '') or None,
                )
            flash(f'Peca {p.codigo_interno} criada.', 'success')
            return redirect(url_for('hora.pecas_cadastro_detalhe', peca_id=p.id))
        except (ValueError, InvalidOperation) as exc:
            flash(f'Erro: {exc}', 'danger')

    return render_template(
        'hora/pecas_cadastro_form.html',
        peca=None, tagplus_map=None,
        pode_editar_tagplus=current_user.tem_perm_hora('tagplus', 'editar'),
    )


@hora_bp.route('/pecas/cadastro/<int:peca_id>')
@require_hora_perm('pecas_cadastro', 'ver')
def pecas_cadastro_detalhe(peca_id: int):
    p = HoraPeca.query.get_or_404(peca_id)
    return render_template(
        'hora/pecas_cadastro_detalhe.html',
        peca=p,
        foto_url=peca_service.get_foto_url(p),
        tagplus_map=p.tagplus_map,
    )


@hora_bp.route('/pecas/cadastro/<int:peca_id>/editar', methods=['GET', 'POST'])
@require_hora_perm('pecas_cadastro', 'editar')
def pecas_cadastro_editar(peca_id: int):
    p = HoraPeca.query.get_or_404(peca_id)
    if request.method == 'POST':
        try:
            preco = (request.form.get('preco_venda_padrao') or '0').replace(',', '.')
            custo = (request.form.get('custo') or '0').replace(',', '.')
            peca_service.editar_peca(
                peca_id=p.id,
                descricao=(request.form.get('descricao') or '').strip(),
                ncm=(request.form.get('ncm') or '') or None,
                cfop_default=(request.form.get('cfop_default') or '5.102'),
                unidade=(request.form.get('unidade') or 'UN'),
                preco_venda_padrao=Decimal(preco),
                custo=Decimal(custo),
                ativo=request.form.get('ativo') == '1',
            )
            tp_id = (request.form.get('tagplus_produto_id') or '').strip()
            if tp_id:
                peca_service.set_tagplus_map(
                    peca_id=p.id,
                    tagplus_produto_id=tp_id,
                    tagplus_codigo=(request.form.get('tagplus_codigo') or '') or None,
                    cfop_default=(request.form.get('tagplus_cfop_default') or '') or None,
                )
            elif p.tagplus_map:
                peca_service.remover_tagplus_map(p.id)
            flash(f'Peca {p.codigo_interno} atualizada.', 'success')
            return redirect(url_for('hora.pecas_cadastro_detalhe', peca_id=p.id))
        except (ValueError, InvalidOperation) as exc:
            flash(f'Erro: {exc}', 'danger')

    return render_template(
        'hora/pecas_cadastro_form.html',
        peca=p, tagplus_map=p.tagplus_map,
        pode_editar_tagplus=current_user.tem_perm_hora('tagplus', 'editar'),
    )


@hora_bp.route('/pecas/cadastro/<int:peca_id>/foto', methods=['POST'])
@require_hora_perm('pecas_cadastro', 'editar')
def pecas_cadastro_upload_foto(peca_id: int):
    arquivo = request.files.get('foto')
    if not arquivo or not arquivo.filename:
        flash('Selecione uma foto.', 'danger')
        return redirect(url_for('hora.pecas_cadastro_detalhe', peca_id=peca_id))
    try:
        peca_service.upload_foto(peca_id, arquivo, criado_por=_operador())
        flash('Foto atualizada.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.pecas_cadastro_detalhe', peca_id=peca_id))


@hora_bp.route('/pecas/cadastro/<int:peca_id>/toggle-ativo', methods=['POST'])
@require_hora_perm('pecas_cadastro', 'apagar')
def pecas_cadastro_toggle_ativo(peca_id: int):
    p = HoraPeca.query.get_or_404(peca_id)
    if p.ativo:
        peca_service.inativar_peca(p.id)
        flash(f'Peca {p.codigo_interno} inativada.', 'warning')
    else:
        peca_service.ativar_peca(p.id)
        flash(f'Peca {p.codigo_interno} ativada.', 'success')
    return redirect(url_for('hora.pecas_cadastro_lista'))


@hora_bp.route('/pecas/cadastro/autocomplete')
@require_hora_perm('pecas_cadastro', 'ver')
def pecas_cadastro_autocomplete():
    """Autocomplete de pecas para forms (pedido compra/venda)."""
    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify([])
    pecas = peca_service.listar_pecas(busca=q, ativo=True, limit=20)
    return jsonify([
        {
            'id': p.id,
            'codigo_interno': p.codigo_interno,
            'descricao': p.descricao,
            'unidade': p.unidade,
            'preco_venda_padrao': str(p.preco_venda_padrao),
        }
        for p in pecas
    ])

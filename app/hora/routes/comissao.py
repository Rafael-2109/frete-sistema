"""Rotas de configuracao de comissao — roadmap #28 (Fatia 1: cadastro).

Tela unica /hora/comissao com:
  - comissao base por moto;
  - faixas de desconto (R$) -> reducao da comissao (R$);
  - comissao por peca (inline);
  - teto de desconto por modelo (inline).

Aprovacao de desconto (Fatia 2) e calculo/relatorio (Fatia 3) virao depois.
"""
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.hora.decorators import require_hora_perm
from app.hora.routes import hora_bp
from app.hora.services import comissao_service


def _op() -> str:
    return getattr(current_user, 'nome', None) or 'desconhecido'


@hora_bp.route('/comissao')
@require_hora_perm('comissao', 'ver')
def comissao_config():
    from app.hora.models import HoraPeca, HoraModelo
    cfg = comissao_service.get_config()
    faixas = comissao_service.listar_faixas()
    pecas = HoraPeca.query.filter_by(ativo=True).order_by(HoraPeca.descricao).all()
    modelos = (
        HoraModelo.query
        .filter(HoraModelo.merged_em_id.is_(None))
        .order_by(HoraModelo.nome_modelo)
        .all()
    )
    return render_template(
        'hora/comissao.html', cfg=cfg, faixas=faixas, pecas=pecas, modelos=modelos,
    )


@hora_bp.route('/comissao/base', methods=['POST'])
@require_hora_perm('comissao', 'editar')
def comissao_set_base():
    try:
        comissao_service.set_comissao_base_moto(
            request.form.get('comissao_base_moto'), usuario=_op(),
        )
        flash('Comissão base por moto atualizada.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.comissao_config'))


@hora_bp.route('/comissao/faixa', methods=['POST'])
@require_hora_perm('comissao', 'editar')
def comissao_criar_faixa():
    try:
        comissao_service.criar_faixa(
            request.form.get('desconto_min'),
            request.form.get('desconto_max'),
            request.form.get('reducao_comissao'),
        )
        flash('Faixa de desconto criada.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.comissao_config'))


@hora_bp.route('/comissao/faixa/<int:faixa_id>/remover', methods=['POST'])
@require_hora_perm('comissao', 'editar')
def comissao_remover_faixa(faixa_id: int):
    try:
        comissao_service.remover_faixa(faixa_id)
        flash('Faixa removida.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.comissao_config'))


@hora_bp.route('/comissao/peca/<int:peca_id>', methods=['POST'])
@require_hora_perm('comissao', 'editar')
def comissao_set_peca(peca_id: int):
    try:
        comissao_service.set_comissao_peca(peca_id, request.form.get('valor_comissao'))
        flash('Comissão da peça atualizada.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.comissao_config'))


@hora_bp.route('/comissao/modelo/<int:modelo_id>', methods=['POST'])
@require_hora_perm('comissao', 'editar')
def comissao_set_modelo(modelo_id: int):
    try:
        comissao_service.set_teto_modelo(modelo_id, request.form.get('desconto_maximo'))
        flash('Teto de desconto do modelo atualizado.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.comissao_config'))


# ------------------------------------------------------------------------
# Aprovacao de desconto acima do teto (#28, Fatia 2) — fila + log
# ------------------------------------------------------------------------

@hora_bp.route('/comissao/aprovacoes')
@require_hora_perm('comissao', 'ver')
def comissao_aprovacoes():
    from app.hora.services import aprovacao_desconto_service
    from app.hora.models import APROVACAO_STATUS_PENDENTE
    pendentes = aprovacao_desconto_service.listar(status=APROVACAO_STATUS_PENDENTE)
    historico = [a for a in aprovacao_desconto_service.listar() if a.status != APROVACAO_STATUS_PENDENTE]
    return render_template(
        'hora/comissao_aprovacoes.html', pendentes=pendentes, historico=historico,
    )


@hora_bp.route('/comissao/aprovacao/<int:aprovacao_id>/aprovar', methods=['POST'])
@require_hora_perm('comissao', 'aprovar')
def comissao_aprovar_desconto(aprovacao_id: int):
    from app.hora.services import aprovacao_desconto_service
    try:
        aprovacao_desconto_service.aprovar(aprovacao_id, usuario=_op())
        flash('Desconto aprovado — a venda já pode ser confirmada.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.comissao_aprovacoes'))


@hora_bp.route('/comissao/aprovacao/<int:aprovacao_id>/rejeitar', methods=['POST'])
@require_hora_perm('comissao', 'aprovar')
def comissao_rejeitar_desconto(aprovacao_id: int):
    from app.hora.services import aprovacao_desconto_service
    motivo = (request.form.get('motivo') or '').strip() or None
    try:
        aprovacao_desconto_service.rejeitar(aprovacao_id, usuario=_op(), motivo=motivo)
        flash('Desconto rejeitado.', 'warning')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.comissao_aprovacoes'))

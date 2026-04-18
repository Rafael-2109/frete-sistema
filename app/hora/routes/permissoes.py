"""Gestão de usuários com acesso ao módulo HORA.

Somente administradores. Atalho para habilitar sistema_lojas + segregação
por loja sem sair do módulo HORA.
"""
from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.auth.models import Usuario
from app.hora.decorators import require_admin_lojas
from app.hora.models import HoraLoja
from app.hora.routes import hora_bp


@hora_bp.route('/permissoes')
@require_admin_lojas
def permissoes_lista():
    """Lista usuários com acesso a Lojas HORA + loja vinculada."""
    usuarios = (
        Usuario.query
        .order_by(Usuario.sistema_lojas.desc(), Usuario.nome)
        .all()
    )
    lojas = HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.nome).all()
    lojas_por_id = {l.id: l for l in lojas}
    return render_template(
        'hora/permissoes_lista.html',
        usuarios=usuarios,
        lojas=lojas,
        lojas_por_id=lojas_por_id,
    )


@hora_bp.route('/permissoes/<int:user_id>/toggle', methods=['POST'])
@require_admin_lojas
def permissoes_toggle(user_id: int):
    """Liga/desliga sistema_lojas para um usuário (operação rápida)."""
    usuario = Usuario.query.get_or_404(user_id)
    usuario.sistema_lojas = not usuario.sistema_lojas
    # Se desligou, limpa loja vinculada.
    if not usuario.sistema_lojas:
        usuario.loja_hora_id = None
    db.session.commit()
    estado = 'habilitado' if usuario.sistema_lojas else 'desabilitado'
    flash(f'{usuario.nome}: acesso {estado}.', 'success')
    return redirect(url_for('hora.permissoes_lista'))


@hora_bp.route('/permissoes/<int:user_id>/loja', methods=['POST'])
@require_admin_lojas
def permissoes_set_loja(user_id: int):
    """Define loja_hora_id do usuário (segregação por loja)."""
    usuario = Usuario.query.get_or_404(user_id)
    loja_id_str = (request.form.get('loja_hora_id') or '').strip()

    if not loja_id_str:
        usuario.loja_hora_id = None
        mensagem = 'Acesso a TODAS as lojas'
    elif loja_id_str.isdigit():
        loja_id = int(loja_id_str)
        if not HoraLoja.query.get(loja_id):
            flash('Loja inválida.', 'danger')
            return redirect(url_for('hora.permissoes_lista'))
        usuario.loja_hora_id = loja_id
        mensagem = f'Restrito à loja {loja_id}'
    else:
        flash('Valor inválido.', 'danger')
        return redirect(url_for('hora.permissoes_lista'))

    db.session.commit()
    flash(f'{usuario.nome}: {mensagem}.', 'success')
    return redirect(url_for('hora.permissoes_lista'))

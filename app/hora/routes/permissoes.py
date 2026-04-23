"""Gestao de usuarios e permissoes granulares do modulo HORA.

3 telas:
  GET  /hora/permissoes               - Lista usuarios + matriz Ver/Criar/Editar/Apagar
                                         por modulo (10 modulos x 4 acoes).
  POST /hora/permissoes/<id>/toggle   - Liga/desliga sistema_lojas (atalho).
  POST /hora/permissoes/<id>/loja     - Define loja_hora_id (segregacao por loja).
  POST /hora/permissoes/<id>/granular - Salva matriz completa em batch.

Acesso protegido por (modulo='usuarios', acao=...) — admin sempre passa.
"""
from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.auth.models import Usuario
from app.hora.decorators import require_hora_perm
from app.hora.models import HoraLoja
from app.hora.routes import hora_bp
from app.hora.services import permissao_service
from app.utils.timezone import agora_utc_naive


def _bloqueia_se_alvo_invalido(alvo: Usuario) -> str | None:
    """Guarda contra IDOR/escalada: nao permite mexer em si mesmo nem em admin
    se o ator atual nao for admin. Retorna mensagem de bloqueio ou None se OK.
    """
    if alvo.id == getattr(current_user, 'id', None):
        return 'Voce nao pode alterar suas proprias permissoes HORA.'
    if alvo.perfil == 'administrador' and getattr(current_user, 'perfil', None) != 'administrador':
        return 'Apenas administradores podem alterar outros administradores.'
    return None


@hora_bp.route('/permissoes')
@require_hora_perm('usuarios', 'ver')
def permissoes_lista():
    """Lista pendentes de aprovacao + usuarios com acesso a Lojas HORA + matriz granular."""
    # Pendentes = status='pendente' (aguardando aprovacao para o sistema HORA)
    pendentes = (
        Usuario.query
        .filter(Usuario.status == 'pendente')
        .order_by(Usuario.criado_em.desc())
        .all()
    )

    # Demais usuarios: apenas os com acesso a Lojas HORA (sistema_lojas=True) e
    # que NAO sao administradores. Admin ja tem acesso total por bypass (ver
    # Usuario.tem_perm_hora) e nao faz sentido gerenciar permissoes granulares
    # para quem ignora todas as restricoes. Usuarios sem sistema_lojas nao
    # pertencem ao escopo deste modulo — aprovar primeiro no card "Pendentes".
    usuarios = (
        Usuario.query
        .filter(Usuario.status != 'pendente')
        .filter(Usuario.sistema_lojas.is_(True))
        .filter(Usuario.perfil != 'administrador')
        .order_by(Usuario.nome)
        .all()
    )
    lojas = HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.nome).all()
    lojas_por_id = {l.id: l for l in lojas}

    # Carrega matriz granular para todos em 1 query (perf).
    matrizes = permissao_service.get_matrizes_batch([u.id for u in usuarios])

    return render_template(
        'hora/permissoes_lista.html',
        pendentes=pendentes,
        usuarios=usuarios,
        lojas=lojas,
        lojas_por_id=lojas_por_id,
        modulos=permissao_service.listar_modulos(),
        acoes=permissao_service.listar_acoes(),
        matrizes=matrizes,
        modulos_so_ver=permissao_service.modulos_so_ver(),
    )


@hora_bp.route('/permissoes/<int:user_id>/aprovar', methods=['POST'])
@require_hora_perm('usuarios', 'aprovar')
def permissoes_aprovar(user_id: int):
    """Aprova usuario pendente para o sistema HORA com escolha de loja.

    Valida loja (vazio = todas; <id> = restrito), liga sistema_lojas,
    seta status='ativo', registra aprovado_por/aprovado_em.
    """
    usuario = Usuario.query.get_or_404(user_id)
    if usuario.id == getattr(current_user, 'id', None):
        flash('Voce nao pode aprovar a si mesmo.', 'danger')
        return redirect(url_for('hora.permissoes_lista'))
    if usuario.status != 'pendente':
        flash(f'{usuario.nome} nao esta pendente (status atual: {usuario.status}).', 'warning')
        return redirect(url_for('hora.permissoes_lista'))

    loja_id_str = (request.form.get('loja_hora_id') or '').strip()
    if not loja_id_str:
        loja_id = None  # acesso a todas as lojas
    elif loja_id_str.isdigit():
        loja_id = int(loja_id_str)
        if not HoraLoja.query.get(loja_id):
            flash('Loja invalida.', 'danger')
            return redirect(url_for('hora.permissoes_lista'))
    else:
        flash('Valor de loja invalido.', 'danger')
        return redirect(url_for('hora.permissoes_lista'))

    usuario.sistema_lojas = True
    usuario.loja_hora_id = loja_id
    usuario.status = 'ativo'
    usuario.aprovado_em = agora_utc_naive()
    usuario.aprovado_por = getattr(current_user, 'email', None)
    db.session.commit()

    escopo = 'todas as lojas' if loja_id is None else f'loja {loja_id}'
    flash(
        f'{usuario.nome} aprovado para Lojas HORA ({escopo}). '
        'Defina abaixo as permissoes granulares (Ver/Criar/Editar/Apagar).',
        'success',
    )
    return redirect(url_for('hora.permissoes_lista'))


@hora_bp.route('/permissoes/<int:user_id>/rejeitar', methods=['POST'])
@require_hora_perm('usuarios', 'aprovar')
def permissoes_rejeitar(user_id: int):
    """Rejeita usuario pendente (status='rejeitado')."""
    usuario = Usuario.query.get_or_404(user_id)
    if usuario.id == getattr(current_user, 'id', None):
        flash('Voce nao pode rejeitar a si mesmo.', 'danger')
        return redirect(url_for('hora.permissoes_lista'))
    if usuario.status != 'pendente':
        flash(f'{usuario.nome} nao esta pendente.', 'warning')
        return redirect(url_for('hora.permissoes_lista'))

    motivo = (request.form.get('motivo') or '').strip() or 'Rejeitado via tela HORA'
    usuario.rejeitar(motivo=motivo)
    db.session.commit()
    flash(f'{usuario.nome} rejeitado.', 'warning')
    return redirect(url_for('hora.permissoes_lista'))


@hora_bp.route('/permissoes/<int:user_id>/toggle', methods=['POST'])
@require_hora_perm('usuarios', 'editar')
def permissoes_toggle(user_id: int):
    """Liga/desliga sistema_lojas para um usuario (operacao rapida).

    Bloqueia se nao-ativo (precisa aprovar antes), self-edit ou alterar admin.
    """
    usuario = Usuario.query.get_or_404(user_id)
    bloqueio = _bloqueia_se_alvo_invalido(usuario)
    if bloqueio:
        flash(bloqueio, 'danger')
        return redirect(url_for('hora.permissoes_lista'))
    if not usuario.sistema_lojas and usuario.status != 'ativo':
        flash(
            f'Nao e possivel habilitar acesso para usuario com status "{usuario.status}". '
            'Aprove o cadastro primeiro.',
            'warning',
        )
        return redirect(url_for('hora.permissoes_lista'))

    usuario.sistema_lojas = not usuario.sistema_lojas
    if not usuario.sistema_lojas:
        usuario.loja_hora_id = None
    db.session.commit()
    estado = 'habilitado' if usuario.sistema_lojas else 'desabilitado'
    flash(f'{usuario.nome}: acesso {estado}.', 'success')
    return redirect(url_for('hora.permissoes_lista'))


@hora_bp.route('/permissoes/<int:user_id>/loja', methods=['POST'])
@require_hora_perm('usuarios', 'editar')
def permissoes_set_loja(user_id: int):
    """Define loja_hora_id do usuario (segregacao por loja)."""
    usuario = Usuario.query.get_or_404(user_id)
    bloqueio = _bloqueia_se_alvo_invalido(usuario)
    if bloqueio:
        flash(bloqueio, 'danger')
        return redirect(url_for('hora.permissoes_lista'))
    loja_id_str = (request.form.get('loja_hora_id') or '').strip()

    if not loja_id_str:
        usuario.loja_hora_id = None
        mensagem = 'Acesso a TODAS as lojas'
    elif loja_id_str.isdigit():
        loja_id = int(loja_id_str)
        if not HoraLoja.query.get(loja_id):
            flash('Loja invalida.', 'danger')
            return redirect(url_for('hora.permissoes_lista'))
        usuario.loja_hora_id = loja_id
        mensagem = f'Restrito a loja {loja_id}'
    else:
        flash('Valor invalido.', 'danger')
        return redirect(url_for('hora.permissoes_lista'))

    db.session.commit()
    flash(f'{usuario.nome}: {mensagem}.', 'success')
    return redirect(url_for('hora.permissoes_lista'))


@hora_bp.route('/permissoes/<int:user_id>/granular', methods=['POST'])
@require_hora_perm('usuarios', 'editar')
def permissoes_salvar_granular(user_id: int):
    """Salva matriz completa de permissoes (10 modulos x 4 acoes) em batch.

    Form fields esperados (checkbox = "1" se marcado, ausente se nao):
      perm_<modulo>_ver, perm_<modulo>_criar, perm_<modulo>_editar, perm_<modulo>_apagar

    Para cada um dos 10 modulos da lista canonica.
    """
    usuario = Usuario.query.get_or_404(user_id)
    bloqueio = _bloqueia_se_alvo_invalido(usuario)
    if bloqueio:
        flash(bloqueio, 'danger')
        return redirect(url_for('hora.permissoes_lista'))

    # Garantia: usuario precisa ter sistema_lojas ligado para fazer sentido.
    if not usuario.sistema_lojas:
        flash(
            f'{usuario.nome} nao tem acesso ao modulo Lojas HORA. '
            'Habilite "Acesso" antes de definir permissoes granulares.',
            'warning',
        )
        return redirect(url_for('hora.permissoes_lista'))

    # Checkbox HTML so envia se marcado. Presenca da chave = True; ausencia = False.
    matriz: dict[str, dict[str, bool]] = {}
    for modulo, _ in permissao_service.listar_modulos():
        matriz[modulo] = {
            acao: f'perm_{modulo}_{acao}' in request.form
            for acao, _ in permissao_service.listar_acoes()
        }

    salvos = permissao_service.salvar_matriz_completa(
        user_id=user_id,
        matriz=matriz,
        atualizado_por_id=getattr(current_user, 'id', None),
    )
    flash(
        f'{usuario.nome}: permissoes granulares salvas ({salvos} modulos).',
        'success',
    )
    return redirect(url_for('hora.permissoes_lista'))

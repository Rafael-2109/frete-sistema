"""CRUD de Perfis de permissao das Lojas HORA.

Um perfil HORA e um template reutilizavel de permissoes (ver
`app/hora/services/perfil_service.py`). Telas:

  GET  /hora/permissoes/perfis            - Lista perfis + form "novo perfil".
  POST /hora/permissoes/perfis/novo       - Cria perfil (so o nome; slug derivado).
  GET  /hora/permissoes/perfis/<id>       - Edita nome + esqueleto (matriz modulo x acao).
  POST /hora/permissoes/perfis/<id>/salvar- Salva nome + esqueleto em batch.
  POST /hora/permissoes/perfis/<id>/ativo - Ativa/desativa o perfil.

Acesso protegido por (modulo='usuarios', acao=...) — admin sempre passa. Espelha o
gating de permissoes.py: 'ver' para abrir, 'criar' para novo, 'editar' para salvar.
"""
from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.hora.decorators import require_hora_perm
from app.hora.routes import hora_bp
from app.hora.services import perfil_service, permissao_service


@hora_bp.route('/permissoes/perfis')
@require_hora_perm('usuarios', 'ver')
def perfis_lista():
    """Lista perfis HORA (ativos + inativos) com contagem de modulos concedidos."""
    perfis = perfil_service.listar_perfis(incluir_inativos=True)
    contagem = perfil_service.contar_modulos_concedidos_batch([p.id for p in perfis])
    return render_template(
        'hora/perfis_lista.html',
        perfis=perfis,
        contagem=contagem,
        total_modulos=len(permissao_service.listar_modulos()),
        pode_criar=current_user.tem_perm_hora('usuarios', 'criar'),
        pode_editar=current_user.tem_perm_hora('usuarios', 'editar'),
    )


@hora_bp.route('/permissoes/perfis/novo', methods=['POST'])
@require_hora_perm('usuarios', 'criar')
def perfis_novo():
    """Cria um perfil HORA a partir do nome (slug derivado automaticamente)."""
    nome = (request.form.get('nome') or '').strip()
    try:
        perfil = perfil_service.criar_perfil(
            nome, criado_por_id=getattr(current_user, 'id', None),
        )
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('hora.perfis_lista'))

    flash(
        f'Perfil "{perfil.nome}" criado. Defina abaixo as permissoes do esqueleto.',
        'success',
    )
    return redirect(url_for('hora.perfis_editar', perfil_id=perfil.id))


@hora_bp.route('/permissoes/perfis/<int:perfil_id>')
@require_hora_perm('usuarios', 'ver')
def perfis_editar(perfil_id: int):
    """Tela de edicao do nome + esqueleto (matriz modulo x acao) do perfil."""
    perfil = perfil_service.get_perfil(perfil_id)
    if perfil is None:
        flash('Perfil nao encontrado.', 'danger')
        return redirect(url_for('hora.perfis_lista'))

    return render_template(
        'hora/perfil_form.html',
        perfil=perfil,
        matriz_flags=perfil_service.get_skeleton(perfil.id),
        modulos=permissao_service.listar_modulos(),
        acoes=permissao_service.listar_acoes(),
        modulos_so_ver=permissao_service.modulos_so_ver(),
        modulos_com_aprovar=permissao_service.modulos_com_aprovar(),
        pode_editar=current_user.tem_perm_hora('usuarios', 'editar'),
    )


@hora_bp.route('/permissoes/perfis/<int:perfil_id>/salvar', methods=['POST'])
@require_hora_perm('usuarios', 'editar')
def perfis_salvar(perfil_id: int):
    """Salva nome + esqueleto completo (modulos x acoes) do perfil em batch."""
    perfil = perfil_service.get_perfil(perfil_id)
    if perfil is None:
        flash('Perfil nao encontrado.', 'danger')
        return redirect(url_for('hora.perfis_lista'))

    # Renomear (opcional — so se mudou).
    nome = (request.form.get('nome') or '').strip()
    if nome and nome != perfil.nome:
        try:
            perfil_service.renomear_perfil(perfil_id, nome)
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(url_for('hora.perfis_editar', perfil_id=perfil_id))

    # Esqueleto: checkbox HTML so envia se marcado (presenca = True).
    matriz: dict[str, dict[str, bool]] = {}
    for modulo, _ in permissao_service.listar_modulos():
        matriz[modulo] = {
            acao: f'perm_{modulo}_{acao}' in request.form
            for acao, _ in permissao_service.listar_acoes()
        }

    salvos = perfil_service.salvar_skeleton(perfil_id, matriz)
    flash(f'Esqueleto do perfil "{perfil.nome}" salvo ({salvos} modulos).', 'success')
    return redirect(url_for('hora.perfis_editar', perfil_id=perfil_id))


@hora_bp.route('/permissoes/perfis/<int:perfil_id>/ativo', methods=['POST'])
@require_hora_perm('usuarios', 'editar')
def perfis_toggle_ativo(perfil_id: int):
    """Ativa/desativa o perfil. Desativar nao mexe nos usuarios que ja o usam."""
    perfil = perfil_service.get_perfil(perfil_id)
    if perfil is None:
        flash('Perfil nao encontrado.', 'danger')
        return redirect(url_for('hora.perfis_lista'))
    try:
        perfil_service.set_ativo(perfil_id, not perfil.ativo)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('hora.perfis_lista'))
    estado = 'ativado' if perfil.ativo else 'desativado'
    flash(f'Perfil "{perfil.nome}" {estado}.', 'success')
    return redirect(url_for('hora.perfis_lista'))

"""
Rotas Admin CarVia — Exclusao permanente, auditoria e correcao de dados
========================================================================

Todas as rotas requerem @login_required + @require_admin.
"""

import logging

from flask import flash, redirect, url_for, request, render_template, jsonify
from flask_login import login_required, current_user

from app.utils.auth_decorators import require_admin

logger = logging.getLogger(__name__)

# Mapeamento tipo URL → (metodo do service, redirect_endpoint, label)
# para ACAO admin_excluir (dispatch de hard delete).
#
# REMOVIDOS (Sprint 0 — CRITICO + MEDIO):
#   - 'nf'               (excluir_nf — sem guards, bypass total)
#   - 'operacao'         (excluir_operacao — bypass CarviaFrete e filhos)
#   - 'subcontrato'      (excluir_subcontrato — bypass CarviaFrete)
#   - 'cte-complementar' (excluir_cte_complementar — cascade sem guards)
#   - 'custo-entrega'    (excluir_custo_entrega — bypass CTe Comp vinculado)
#   - 'despesa'          (excluir_despesa — bypass COMISSAO)
#
# Hard delete bypassava o fluxo unidirecional. Para remover estas entidades,
# use o fluxo normal: cancelar (status=CANCELADO) apos reverter dependencias.
_TIPO_CONFIG = {
    'fatura-cliente': {
        'metodo': 'excluir_fatura_cliente',
        'redirect': 'carvia.listar_faturas_cliente',
        'label': 'Fatura Cliente',
    },
    'fatura-transportadora': {
        'metodo': 'excluir_fatura_transportadora',
        'redirect': 'carvia.listar_faturas_transportadora',
        'label': 'Fatura Transportadora',
    },
    'receita': {
        'metodo': 'excluir_receita',
        'redirect': 'carvia.listar_receitas',
        'label': 'Receita',
    },
    # Caso especial: hard delete restrito a subcontratos ORFAOS do fluxo legado
    # (anteriores ao pipeline portaria -> CarviaFrete). O service aplica guards
    # rigorosos — NAO e um bypass generico do cancel path (soft-delete segue
    # sendo a via oficial para subs do fluxo atual).
    'subcontrato-orfao': {
        'metodo': 'excluir_subcontrato_orfao',
        'redirect': 'carvia.listar_subcontratos',
        'label': 'Subcontrato Orfao (Legado)',
    },
}

# Review Sprint 0 ALTO #3: mapa separado para redirect de admin_converter.
# Cobre todos os tipos suportados pelo converter (inclui nf, operacao,
# subcontrato, cte-complementar, custo-entrega, despesa que foram removidos
# do _TIPO_CONFIG principal mas ainda sao destinos validos de conversao).
_TIPO_REDIRECT_MAP = {
    'nf': 'carvia.listar_nfs',
    'operacao': 'carvia.listar_operacoes',
    'subcontrato': 'carvia.listar_subcontratos',
    'fatura-cliente': 'carvia.listar_faturas_cliente',
    'fatura-transportadora': 'carvia.listar_faturas_transportadora',
    'cte-complementar': 'carvia.listar_ctes_complementares',
    'custo-entrega': 'carvia.listar_custos_entrega',
    'despesa': 'carvia.listar_despesas',
    'receita': 'carvia.listar_receitas',
}


def register_admin_routes(bp):

    @bp.route('/admin/<tipo>/<int:id>/excluir', methods=['POST'])
    @login_required
    @require_admin
    def admin_excluir(tipo, id):
        """Exclusao permanente (hard delete) de qualquer entidade CarVia."""
        config = _TIPO_CONFIG.get(tipo)
        if not config:
            flash(f'Tipo de entidade invalido: {tipo}', 'danger')
            return redirect(url_for('carvia.dashboard'))

        motivo = request.form.get('motivo', '').strip()
        if not motivo or len(motivo) < 10:
            flash('Motivo obrigatorio (minimo 10 caracteres).', 'danger')
            return redirect(request.referrer or url_for(config['redirect']))

        from app.carvia.services.admin.admin_service import AdminService
        service = AdminService()

        metodo = getattr(service, config['metodo'])
        resultado = metodo(id, motivo, current_user.email)

        if resultado['sucesso']:
            flash(
                f'{resultado["mensagem"]} (Auditoria #{resultado["auditoria_id"]})',
                'success',
            )
            return redirect(url_for(config['redirect']))
        else:
            flash(resultado['mensagem'], 'danger')
            return redirect(request.referrer or url_for(config['redirect']))

    # ------------------------------------------------------------------ #
    #  REMOVIDO (Sprint 0 — CRITICO): admin_editar (FIELD_EDIT)
    #
    #  A rota permitia setar qualquer campo em qualquer entidade,
    #  bypassando TODOS os guards de bloqueio. Para editar campos,
    #  use as rotas especificas da entidade (ex: editar_cte_valor,
    #  editar_despesa, editar_vencimento).
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  Re-link NF ↔ CTe (Fase 6.1)
    # ------------------------------------------------------------------ #

    @bp.route('/admin/operacao/<int:id>/relink-nfs', methods=['POST'])
    @login_required
    @require_admin
    def admin_relink_nfs(id):
        """Re-vincula/desvincula NFs de uma operacao."""
        from app.carvia.services.admin.admin_service import AdminService
        service = AdminService()

        motivo = request.form.get('motivo', '').strip()
        if not motivo or len(motivo) < 10:
            flash('Motivo obrigatorio (minimo 10 caracteres).', 'danger')
            return redirect(request.referrer or url_for('carvia.detalhe_operacao', operacao_id=id))

        # Coletar IDs dos checkboxes
        nf_ids_vincular = request.form.getlist('vincular_nf_ids', type=int)
        nf_ids_desvincular = request.form.getlist('desvincular_nf_ids', type=int)

        resultado = service.relink_operacao_nfs(
            id, nf_ids_vincular, nf_ids_desvincular, motivo, current_user.email
        )

        if resultado['sucesso']:
            flash(f'{resultado["mensagem"]} (Auditoria #{resultado["auditoria_id"]})', 'success')
        else:
            flash(resultado['mensagem'], 'warning')

        return redirect(url_for('carvia.detalhe_operacao', operacao_id=id))

    # ------------------------------------------------------------------ #
    #  Conversao de Tipo (Fase 5)
    # ------------------------------------------------------------------ #

    @bp.route('/admin/converter/<tipo_origem>/<int:id>', methods=['GET', 'POST'])
    @login_required
    @require_admin
    def admin_converter(tipo_origem, id):
        """Converter uma entidade de um tipo para outro."""
        from app.carvia.services.admin.admin_service import AdminService
        service = AdminService()

        # Determinar tipo destino
        conversoes = {
            'operacao': 'subcontrato',
            'subcontrato': 'operacao',
            'fatura-cliente': 'fatura-transportadora',
            'fatura-transportadora': 'fatura-cliente',
        }
        tipo_destino = request.args.get('destino') or conversoes.get(tipo_origem)
        if not tipo_destino or not service.conversao_suportada(tipo_origem, tipo_destino):
            flash(f'Conversao de {tipo_origem} nao suportada.', 'danger')
            return redirect(url_for('carvia.dashboard'))

        ModelClass = service._get_model_class(tipo_origem)
        if not ModelClass:
            flash(f'Tipo invalido: {tipo_origem}', 'danger')
            return redirect(url_for('carvia.dashboard'))

        entity = ModelClass.query.get_or_404(id)

        if request.method == 'POST':
            motivo = request.form.get('motivo', '').strip()
            if not motivo or len(motivo) < 10:
                flash('Motivo obrigatorio (minimo 10 caracteres).', 'danger')
                return redirect(request.url)

            campos_form = {}
            for key in request.form:
                if key not in ('csrf_token', 'motivo', 'tipo_destino'):
                    campos_form[key] = request.form[key]

            resultado = service.converter_documento(
                tipo_origem, id, tipo_destino, campos_form, motivo, current_user.email
            )

            if resultado['sucesso']:
                flash(
                    f'{resultado["mensagem"]} (Auditoria #{resultado["auditoria_id"]})',
                    'success',
                )
                # Review Sprint 0 ALTO #3: usar _TIPO_REDIRECT_MAP que cobre
                # todos os tipos (inclui os removidos do _TIPO_CONFIG)
                redirect_endpoint = _TIPO_REDIRECT_MAP.get(
                    tipo_destino, 'carvia.dashboard'
                )
                return redirect(url_for(redirect_endpoint))
            else:
                flash(resultado['mensagem'], 'danger')
                return redirect(request.url)

        # GET: mostrar formulario de conversao
        campos_origem, campos_destino, mapeamento = service.obter_mapeamento_conversao(
            tipo_origem, tipo_destino, entity
        )
        tipo_origem_label = _TIPO_CONFIG.get(tipo_origem, {}).get('label', tipo_origem)
        tipo_destino_label = _TIPO_CONFIG.get(tipo_destino, {}).get('label', tipo_destino)

        return render_template(
            'carvia/admin/converter.html',
            tipo_origem=tipo_origem,
            tipo_destino=tipo_destino,
            entity=entity,
            campos_origem=campos_origem,
            campos_destino=campos_destino,
            mapeamento_campos=mapeamento,
            tipo_origem_label=f'{tipo_origem_label} #{id}',
            tipo_destino_label=tipo_destino_label,
            url_referrer=request.referrer or url_for('carvia.dashboard'),
        )

    # ------------------------------------------------------------------ #
    #  Auditoria
    # ------------------------------------------------------------------ #

    @bp.route('/admin/auditoria')
    @login_required
    @require_admin
    def admin_auditoria():
        """Visualizador de registros de auditoria admin."""
        from app.carvia.services.admin.admin_service import AdminService
        service = AdminService()

        page = request.args.get('page', 1, type=int)
        acao = request.args.get('acao', None)
        entidade_tipo = request.args.get('entidade_tipo', None)

        pagination = service.listar_auditoria(
            page=page,
            acao=acao,
            entidade_tipo=entidade_tipo,
        )

        return render_template(
            'carvia/admin/auditoria.html',
            registros=pagination.items,
            pagination=pagination,
            acao_filtro=acao,
            entidade_tipo_filtro=entidade_tipo,
        )

    @bp.route('/admin/auditoria/<int:audit_id>')
    @login_required
    @require_admin
    def admin_auditoria_detalhe(audit_id):
        """Retorna detalhes de um registro de auditoria (JSON)."""
        from app.carvia.models import CarviaAdminAudit

        audit = CarviaAdminAudit.query.get_or_404(audit_id)
        return jsonify({
            'id': audit.id,
            'acao': audit.acao,
            'entidade_tipo': audit.entidade_tipo,
            'entidade_id': audit.entidade_id,
            'dados_snapshot': audit.dados_snapshot,
            'dados_relacionados': audit.dados_relacionados,
            'motivo': audit.motivo,
            'executado_por': audit.executado_por,
            'executado_em': audit.executado_em.isoformat() if audit.executado_em else None,
            'detalhes': audit.detalhes,
        })

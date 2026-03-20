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
_TIPO_CONFIG = {
    'nf': {
        'metodo': 'excluir_nf',
        'redirect': 'carvia.listar_nfs',
        'label': 'NF',
    },
    'operacao': {
        'metodo': 'excluir_operacao',
        'redirect': 'carvia.listar_operacoes',
        'label': 'Operacao',
    },
    'subcontrato': {
        'metodo': 'excluir_subcontrato',
        'redirect': 'carvia.listar_subcontratos',
        'label': 'Subcontrato',
    },
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
    'cte-complementar': {
        'metodo': 'excluir_cte_complementar',
        'redirect': 'carvia.listar_ctes_complementares',
        'label': 'CTe Complementar',
    },
    'custo-entrega': {
        'metodo': 'excluir_custo_entrega',
        'redirect': 'carvia.listar_custos_entrega',
        'label': 'Custo Entrega',
    },
    'despesa': {
        'metodo': 'excluir_despesa',
        'redirect': 'carvia.listar_despesas',
        'label': 'Despesa',
    },
    'receita': {
        'metodo': 'excluir_receita',
        'redirect': 'carvia.listar_receitas',
        'label': 'Receita',
    },
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

        from app.carvia.services.admin_service import AdminService
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
    #  Edicao Completa (Fase 4)
    # ------------------------------------------------------------------ #

    @bp.route('/admin/editar/<tipo>/<int:id>', methods=['GET', 'POST'])
    @login_required
    @require_admin
    def admin_editar(tipo, id):
        """Edicao completa de qualquer entidade CarVia (todos os campos)."""
        from app.carvia.services.admin_service import AdminService
        service = AdminService()

        ModelClass = service._get_model_class(tipo)
        if not ModelClass:
            flash(f'Tipo invalido: {tipo}', 'danger')
            return redirect(url_for('carvia.dashboard'))

        entity = ModelClass.query.get_or_404(id)

        if request.method == 'POST':
            motivo = request.form.get('motivo', '').strip()
            if not motivo or len(motivo) < 10:
                flash('Motivo obrigatorio (minimo 10 caracteres).', 'danger')
                return redirect(request.url)

            # Coletar campos do form
            campos_form = {}
            for col in entity.__table__.columns:
                if col.name in request.form:
                    campos_form[col.name] = request.form[col.name]

            resultado = service.editar_entidade(tipo, id, campos_form, motivo, current_user.email)

            if resultado['sucesso']:
                flash(
                    f'{resultado["mensagem"]} (Auditoria #{resultado["auditoria_id"]})',
                    'success',
                )
                # Redirect para detalhe da entidade
                config = _TIPO_CONFIG.get(tipo, {})
                return redirect(request.referrer or url_for(config.get('redirect', 'carvia.dashboard')))
            else:
                flash(resultado['mensagem'], 'warning')
                return redirect(request.url)

        # GET: mostrar formulario
        campos = service.obter_campos_editaveis(tipo, entity)
        tipo_label = _TIPO_CONFIG.get(tipo, {}).get('label', tipo)

        return render_template(
            'carvia/admin/editar_completo.html',
            tipo=tipo,
            entity=entity,
            campos=campos,
            tipo_label=f'{tipo_label} #{id}',
            url_referrer=request.referrer or url_for('carvia.dashboard'),
        )

    # ------------------------------------------------------------------ #
    #  Re-link NF ↔ CTe (Fase 6.1)
    # ------------------------------------------------------------------ #

    @bp.route('/admin/operacao/<int:id>/relink-nfs', methods=['POST'])
    @login_required
    @require_admin
    def admin_relink_nfs(id):
        """Re-vincula/desvincula NFs de uma operacao."""
        from app.carvia.services.admin_service import AdminService
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
        from app.carvia.services.admin_service import AdminService
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
                config_dest = _TIPO_CONFIG.get(tipo_destino, {})
                return redirect(url_for(config_dest.get('redirect', 'carvia.dashboard')))
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
        from app.carvia.services.admin_service import AdminService
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

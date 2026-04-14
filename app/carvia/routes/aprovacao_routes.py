"""Rotas de Aprovacao de CarviaFrete.

Fila de tratativas pendentes + tela de processamento. Espelha o padrao
Nacom `app/fretes/routes.py:3127-3225` (listar_aprovacoes / processar_aprovacao),
com toda logica delegada ao `AprovacaoFreteService`.

Ref: docs/superpowers/plans/2026-04-14-carvia-frete-conferencia-migration.md
"""

import logging

from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user

from app import db
from app.carvia.models import (
    CarviaAprovacaoFrete,
    CarviaFrete,
    CarviaOperacao,
    CarviaFaturaTransportadora,
)
from app.carvia.services.documentos.aprovacao_frete_service import (
    AprovacaoFreteService,
    TOLERANCIA_APROVACAO,
)

logger = logging.getLogger(__name__)


def register_aprovacao_routes(bp):

    # ==================================================================
    # Fila de aprovacoes pendentes
    # ==================================================================
    # URL preservada: /subcontratos/aprovacoes (nao quebrar bookmarks)
    @bp.route('/subcontratos/aprovacoes')  # type: ignore
    @login_required
    def listar_aprovacoes_subcontrato():  # type: ignore
        """Fila de tratativas PENDENTE — com filtros opcionais ilike."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        filtro_transportadora = (request.args.get('transportadora') or '').strip()
        filtro_cte_numero = (request.args.get('cte_numero') or '').strip()
        filtro_nf_numero = (request.args.get('nf_numero') or '').strip()

        svc = AprovacaoFreteService()
        pendentes_raw = svc.listar_pendentes(
            transportadora=filtro_transportadora or None,
            cte_numero=filtro_cte_numero or None,
            nf_numero=filtro_nf_numero or None,
        )

        linhas = []
        for aprovacao, frete in pendentes_raw:
            operacao = (
                db.session.get(CarviaOperacao, frete.operacao_id)
                if frete.operacao_id else None
            )
            # cte_numero via primeiro subcontrato do frete (UI only)
            primary_sub = frete.subcontratos.first()
            sub_cte_numero = primary_sub.cte_numero if primary_sub else None
            linhas.append({
                'aprovacao': aprovacao,
                'frete': frete,
                'sub_cte_numero': sub_cte_numero,
                'operacao': operacao,
                'transportadora_nome': (
                    frete.transportadora.razao_social
                    if frete.transportadora else '-'
                ),
            })

        return render_template(
            'carvia/aprovacoes/listar.html',
            linhas=linhas,
            total=len(linhas),
            tolerancia=TOLERANCIA_APROVACAO,
            filtros={
                'transportadora': filtro_transportadora,
                'cte_numero': filtro_cte_numero,
                'nf_numero': filtro_nf_numero,
            },
        )

    # ==================================================================
    # Processar aprovacao (tela)
    # ==================================================================
    @bp.route('/subcontratos/aprovacoes/<int:aprovacao_id>')  # type: ignore
    @login_required
    def processar_aprovacao_subcontrato(aprovacao_id):  # type: ignore
        """Tela de processamento de uma aprovacao (opera em Frete)."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        aprovacao = db.session.get(CarviaAprovacaoFrete, aprovacao_id)
        if not aprovacao:
            flash('Aprovacao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_aprovacoes_subcontrato'))

        frete = db.session.get(CarviaFrete, aprovacao.frete_id)
        if not frete:
            flash('Frete nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_aprovacoes_subcontrato'))

        operacao = (
            db.session.get(CarviaOperacao, frete.operacao_id)
            if frete.operacao_id else None
        )
        fatura = (
            db.session.get(CarviaFaturaTransportadora, frete.fatura_transportadora_id)
            if frete.fatura_transportadora_id else None
        )

        # Calculo dos 2 casos Nacom (A: considerado vs cotado, B: pago vs cotado)
        valor_cotado = float(frete.valor_cotado or 0)
        valor_considerado = (
            float(frete.valor_considerado) if frete.valor_considerado is not None else None
        )
        valor_pago = float(frete.valor_pago) if frete.valor_pago is not None else None

        caso_a = None
        if valor_considerado is not None:
            diff_a = valor_considerado - valor_cotado
            caso_a = {
                'valor_considerado': valor_considerado,
                'valor_cotado': valor_cotado,
                'diferenca': diff_a,
                'diferenca_abs': abs(diff_a),
                'acima_tolerancia': abs(diff_a) > float(TOLERANCIA_APROVACAO),
            }

        caso_b = None
        if valor_pago is not None:
            diff_b = valor_pago - valor_cotado
            caso_b = {
                'valor_pago': valor_pago,
                'valor_cotado': valor_cotado,
                'diferenca': diff_b,
                'diferenca_abs': abs(diff_b),
                'acima_tolerancia': abs(diff_b) > float(TOLERANCIA_APROVACAO),
            }

        # Diferenca pago vs considerado (base para CC)
        # pago > considerado -> DEBITO (transp nos deve)
        # pago < considerado -> CREDITO (devemos a transp)
        diff_pago_considerado = None
        if valor_pago is not None and valor_considerado is not None:
            diff = valor_pago - valor_considerado
            diff_pago_considerado = {
                'valor': diff,
                'abs': abs(diff),
                'tipo_cc': 'DEBITO' if diff > 0 else 'CREDITO' if diff < 0 else 'ZERO',
                'descricao_cc': (
                    'CarVia pagou MAIS — transportadora nos deve (DEBITO)'
                    if diff > 0 else
                    'CarVia pagou MENOS — devemos a transportadora (CREDITO)'
                    if diff < 0 else
                    'Sem diferenca'
                ),
            }

        return render_template(
            'carvia/aprovacoes/processar.html',
            aprovacao=aprovacao,
            frete=frete,
            operacao=operacao,
            fatura=fatura,
            caso_a=caso_a,
            caso_b=caso_b,
            diff_pago_considerado=diff_pago_considerado,
            tolerancia=TOLERANCIA_APROVACAO,
        )

    # ==================================================================
    # Aprovar (POST)
    # ==================================================================
    @bp.route(
        '/subcontratos/aprovacoes/<int:aprovacao_id>/aprovar',
        methods=['POST'],
    )  # type: ignore
    @login_required
    def aprovar_subcontrato(aprovacao_id):  # type: ignore
        """Aprova tratativa.

        Validacao inline: sistema_carvia=True OR perfil in ('financeiro', 'administrador').
        """
        tem_carvia = getattr(current_user, 'sistema_carvia', False)
        if not (tem_carvia or current_user.perfil in ('financeiro', 'administrador')):
            flash(
                'Acesso negado. Apenas Financeiro/Administrador ou usuarios '
                'com sistema CarVia habilitado podem aprovar.',
                'danger',
            )
            return redirect(url_for('carvia.listar_aprovacoes_subcontrato'))

        observacoes = (request.form.get('observacoes') or '').strip()
        lancar_diferenca = request.form.get('lancar_diferenca') == 'on'

        if not observacoes:
            flash('Observacoes obrigatorias ao aprovar.', 'warning')
            return redirect(
                url_for(
                    'carvia.processar_aprovacao_subcontrato',
                    aprovacao_id=aprovacao_id,
                )
            )

        svc = AprovacaoFreteService()
        resultado = svc.aprovar(
            aprovacao_id=aprovacao_id,
            lancar_diferenca=lancar_diferenca,
            observacoes=observacoes,
            usuario=current_user.email,
        )

        if resultado.get('sucesso'):
            msg = 'Tratativa aprovada.'
            flash(msg, 'success')
        else:
            flash(f'Erro ao aprovar: {resultado.get("erro")}', 'danger')

        return redirect(url_for('carvia.listar_aprovacoes_subcontrato'))

    # ==================================================================
    # Rejeitar (POST)
    # ==================================================================
    @bp.route(
        '/subcontratos/aprovacoes/<int:aprovacao_id>/rejeitar',
        methods=['POST'],
    )  # type: ignore
    @login_required
    def rejeitar_subcontrato(aprovacao_id):  # type: ignore
        """Rejeita tratativa."""
        tem_carvia = getattr(current_user, 'sistema_carvia', False)
        if not (tem_carvia or current_user.perfil in ('financeiro', 'administrador')):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('carvia.listar_aprovacoes_subcontrato'))

        observacoes = (request.form.get('observacoes') or '').strip()
        if not observacoes:
            flash('Observacoes obrigatorias ao rejeitar.', 'warning')
            return redirect(
                url_for(
                    'carvia.processar_aprovacao_subcontrato',
                    aprovacao_id=aprovacao_id,
                )
            )

        svc = AprovacaoFreteService()
        resultado = svc.rejeitar(
            aprovacao_id=aprovacao_id,
            observacoes=observacoes,
            usuario=current_user.email,
        )

        if resultado.get('sucesso'):
            flash('Tratativa rejeitada. Frete marcado como DIVERGENTE.', 'info')
        else:
            flash(f'Erro ao rejeitar: {resultado.get("erro")}', 'danger')

        return redirect(url_for('carvia.listar_aprovacoes_subcontrato'))

    # ==================================================================
    # Solicitar aprovacao manual (POST)
    # ==================================================================
    # URL mantem /subcontratos/<sub_id>/... mas resolve frete via sub.frete_id
    @bp.route(
        '/subcontratos/<int:sub_id>/solicitar-aprovacao',
        methods=['POST'],
    )  # type: ignore
    @login_required
    def solicitar_aprovacao_subcontrato_manual(sub_id):  # type: ignore
        """Abre tratativa manualmente — resolve frete_id via sub."""
        from app.carvia.models import CarviaSubcontrato

        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        motivo = (request.form.get('motivo') or '').strip()
        if not motivo:
            return jsonify(
                {'sucesso': False, 'erro': 'Motivo e obrigatorio'}
            ), 400

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub:
            return jsonify(
                {'sucesso': False, 'erro': 'Subcontrato nao encontrado'}
            ), 404

        if not sub.frete_id:
            return jsonify(
                {'sucesso': False, 'erro': 'Subcontrato nao tem frete vinculado'}
            ), 400

        svc = AprovacaoFreteService()
        resultado = svc.solicitar_aprovacao(
            frete_id=sub.frete_id,
            motivo=f'[Manual] {motivo}',
            usuario=current_user.email,
        )

        if resultado.get('sucesso'):
            db.session.commit()
            return jsonify(resultado)

        db.session.rollback()
        return jsonify(resultado), 400

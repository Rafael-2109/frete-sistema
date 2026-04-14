"""Rotas de Aprovacao de Subcontratos CarVia.

Fila de tratativas pendentes + tela de processamento. Espelha o padrao
Nacom `app/fretes/routes.py:3127-3225` (listar_aprovacoes / processar_aprovacao),
mas com toda logica delegada ao `AprovacaoSubcontratoService`.

Ref: .claude/plans/wobbly-tumbling-treasure.md
"""

import logging

from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user

from app import db
from app.carvia.models import (
    CarviaAprovacaoSubcontrato,
    CarviaSubcontrato,
    CarviaOperacao,
    CarviaFaturaTransportadora,
)
from app.carvia.services.documentos.aprovacao_subcontrato_service import (
    AprovacaoSubcontratoService,
    TOLERANCIA_APROVACAO,
)

logger = logging.getLogger(__name__)


def register_aprovacao_routes(bp):

    # ==================================================================
    # Fila de aprovacoes pendentes
    # ==================================================================
    @bp.route('/subcontratos/aprovacoes')  # type: ignore
    @login_required
    def listar_aprovacoes_subcontrato():  # type: ignore
        """Fila de tratativas PENDENTE — com filtros opcionais ilike."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        # Filtros (padrao Nacom listar_aprovacoes)
        filtro_transportadora = (request.args.get('transportadora') or '').strip()
        filtro_cte_numero = (request.args.get('cte_numero') or '').strip()
        filtro_nf_numero = (request.args.get('nf_numero') or '').strip()

        svc = AprovacaoSubcontratoService()
        pendentes_raw = svc.listar_pendentes(
            transportadora=filtro_transportadora or None,
            cte_numero=filtro_cte_numero or None,
            nf_numero=filtro_nf_numero or None,
        )

        # Monta linhas enriquecidas para a tela
        linhas = []
        for aprovacao, sub in pendentes_raw:
            operacao = (
                db.session.get(CarviaOperacao, sub.operacao_id)
                if sub.operacao_id else None
            )
            linhas.append({
                'aprovacao': aprovacao,
                'sub': sub,
                'operacao': operacao,
                'transportadora_nome': (
                    sub.transportadora.razao_social
                    if sub.transportadora else '-'
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
        """Tela de processamento de uma aprovacao."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        aprovacao = db.session.get(CarviaAprovacaoSubcontrato, aprovacao_id)
        if not aprovacao:
            flash('Aprovacao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_aprovacoes_subcontrato'))

        sub = db.session.get(CarviaSubcontrato, aprovacao.subcontrato_id)
        if not sub:
            flash('Subcontrato nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_aprovacoes_subcontrato'))

        operacao = (
            db.session.get(CarviaOperacao, sub.operacao_id)
            if sub.operacao_id else None
        )
        fatura = (
            db.session.get(CarviaFaturaTransportadora, sub.fatura_transportadora_id)
            if sub.fatura_transportadora_id else None
        )

        # Calculo dos 2 casos Nacom (A: considerado vs cotado, B: pago vs cotado)
        valor_cotado = float(sub.valor_cotado or 0)
        valor_considerado = (
            float(sub.valor_considerado) if sub.valor_considerado is not None else None
        )
        valor_pago = float(sub.valor_pago) if sub.valor_pago is not None else None

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
        # CONVENCAO CORRIGIDA:
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
            sub=sub,
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

        Validacao inline (nao usa @require_carvia_aprovador para permitir
        flash customizado antes do redirect). Regra identica ao decorator:
        sistema_carvia=True OR perfil in ('financeiro', 'administrador').
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

        svc = AprovacaoSubcontratoService()
        resultado = svc.aprovar(
            aprovacao_id=aprovacao_id,
            lancar_diferenca=lancar_diferenca,
            observacoes=observacoes,
            usuario=current_user.email,
        )

        if resultado.get('sucesso'):
            msg = 'Tratativa aprovada.'
            if resultado.get('cc_id'):
                msg += f' Movimentacao CC #{resultado["cc_id"]} criada.'
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

        svc = AprovacaoSubcontratoService()
        resultado = svc.rejeitar(
            aprovacao_id=aprovacao_id,
            observacoes=observacoes,
            usuario=current_user.email,
        )

        if resultado.get('sucesso'):
            flash('Tratativa rejeitada. Subcontrato marcado como DIVERGENTE.', 'info')
        else:
            flash(f'Erro ao rejeitar: {resultado.get("erro")}', 'danger')

        return redirect(url_for('carvia.listar_aprovacoes_subcontrato'))

    # ==================================================================
    # Solicitar aprovacao manual (POST)
    # ==================================================================
    @bp.route(
        '/subcontratos/<int:sub_id>/solicitar-aprovacao',
        methods=['POST'],
    )  # type: ignore
    @login_required
    def solicitar_aprovacao_subcontrato_manual(sub_id):  # type: ignore
        """Permite ao operador abrir tratativa manualmente (sem divergencia
        automaticamente detectada)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        motivo = (request.form.get('motivo') or '').strip()
        if not motivo:
            return jsonify(
                {'sucesso': False, 'erro': 'Motivo e obrigatorio'}
            ), 400

        svc = AprovacaoSubcontratoService()
        resultado = svc.solicitar_aprovacao(
            sub_id=sub_id,
            motivo=f'[Manual] {motivo}',
            usuario=current_user.email,
        )

        if resultado.get('sucesso'):
            db.session.commit()
            return jsonify(resultado)

        db.session.rollback()
        return jsonify(resultado), 400

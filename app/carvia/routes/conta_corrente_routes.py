"""Rotas de Conta Corrente Transportadoras CarVia.

Lista de transportadoras com saldo ativo + extrato detalhado + export Excel.

Ref: .claude/plans/wobbly-tumbling-treasure.md
"""

import logging
from datetime import datetime, timedelta
from io import BytesIO

from flask import (
    render_template, request, flash, redirect, url_for, jsonify, send_file,
)
from flask_login import login_required, current_user

from app import db
from app.carvia.services.financeiro.conta_corrente_service import (
    ContaCorrenteService,
)

logger = logging.getLogger(__name__)


def register_conta_corrente_routes(bp):

    # ==================================================================
    # Lista de transportadoras com saldo
    # ==================================================================
    @bp.route('/contas-correntes')  # type: ignore
    @login_required
    def listar_contas_correntes_carvia():  # type: ignore
        """Lista de transportadoras com saldo CC ATIVO."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        saldos = ContaCorrenteService.listar_saldos_todas_transportadoras()

        total_geral = {
            'total_debito': round(sum(s['total_debito'] for s in saldos), 2),
            'total_credito': round(sum(s['total_credito'] for s in saldos), 2),
        }
        total_geral['saldo'] = round(
            total_geral['total_debito'] - total_geral['total_credito'], 2
        )

        return render_template(
            'carvia/conta_corrente/listar.html',
            saldos=saldos,
            total_geral=total_geral,
        )

    # ==================================================================
    # Extrato de uma transportadora
    # ==================================================================
    @bp.route('/contas-correntes/<int:transportadora_id>')  # type: ignore
    @login_required
    def extrato_conta_corrente_carvia(transportadora_id):  # type: ignore
        """Extrato detalhado com filtros de data e status."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.transportadoras.models import Transportadora

        transp = db.session.get(Transportadora, transportadora_id)
        if not transp:
            flash('Transportadora nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_contas_correntes_carvia'))

        # Filtros
        data_inicio_str = request.args.get('data_inicio', '')
        data_fim_str = request.args.get('data_fim', '')
        status_filtro = request.args.get('status', 'ATIVO')

        data_inicio = None
        data_fim = None
        try:
            if data_inicio_str:
                data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        except ValueError:
            pass
        try:
            if data_fim_str:
                data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
                data_fim = data_fim + timedelta(days=1)  # inclusivo
        except ValueError:
            pass

        movs = ContaCorrenteService.listar_extrato(
            transportadora_id=transportadora_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            status=status_filtro if status_filtro != 'TODOS' else None,
        )

        saldo = ContaCorrenteService.calcular_saldo(transportadora_id)

        # Totais do extrato filtrado
        total_debito_filtro = round(sum(m['valor_debito'] for m in movs), 2)
        total_credito_filtro = round(sum(m['valor_credito'] for m in movs), 2)
        saldo_filtro = round(total_debito_filtro - total_credito_filtro, 2)

        return render_template(
            'carvia/conta_corrente/extrato.html',
            transportadora=transp,
            movs=movs,
            saldo=saldo,
            total_debito_filtro=total_debito_filtro,
            total_credito_filtro=total_credito_filtro,
            saldo_filtro=saldo_filtro,
            data_inicio=data_inicio_str,
            data_fim=data_fim_str,
            status_filtro=status_filtro,
        )

    # ==================================================================
    # Export Excel
    # ==================================================================
    @bp.route('/contas-correntes/<int:transportadora_id>/excel')  # type: ignore
    @login_required
    def exportar_conta_corrente_excel(transportadora_id):  # type: ignore
        """Gera Excel do extrato com filtros aplicados."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.transportadoras.models import Transportadora

        transp = db.session.get(Transportadora, transportadora_id)
        if not transp:
            flash('Transportadora nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_contas_correntes_carvia'))

        data_inicio_str = request.args.get('data_inicio', '')
        data_fim_str = request.args.get('data_fim', '')
        status_filtro = request.args.get('status', 'ATIVO')

        data_inicio = None
        data_fim = None
        try:
            if data_inicio_str:
                data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        except ValueError:
            pass
        try:
            if data_fim_str:
                data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
                data_fim = data_fim + timedelta(days=1)
        except ValueError:
            pass

        try:
            conteudo = ContaCorrenteService.exportar_excel(
                transportadora_id=transportadora_id,
                data_inicio=data_inicio,
                data_fim=data_fim,
                status=status_filtro if status_filtro != 'TODOS' else None,
            )
        except Exception as e:
            logger.exception(f'Erro export CC transp {transportadora_id}: {e}')
            flash(f'Erro ao gerar Excel: {e}', 'danger')
            return redirect(
                url_for(
                    'carvia.extrato_conta_corrente_carvia',
                    transportadora_id=transportadora_id,
                )
            )

        razao = (transp.razao_social or f'transp{transportadora_id}').replace(' ', '_')
        filename = f'cc_carvia_{razao}_{datetime.now().strftime("%Y%m%d")}.xlsx'

        return send_file(
            BytesIO(conteudo),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename,
        )

    # ==================================================================
    # Desconsiderar movimentacao
    # ==================================================================
    @bp.route(
        '/contas-correntes/<int:mov_id>/desconsiderar',
        methods=['POST'],
    )  # type: ignore
    @login_required
    def desconsiderar_mov_carvia(mov_id):  # type: ignore
        """Marca uma movimentacao como DESCONSIDERADO (reservado para aprovadores)."""
        tem_carvia = getattr(current_user, 'sistema_carvia', False)
        if not (tem_carvia or current_user.perfil in ('financeiro', 'administrador')):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        # Aceita motivo via form OU JSON (silent=True evita AttributeError
        # com body vazio + Content-Type JSON)
        data = request.get_json(silent=True) or {}
        motivo = (request.form.get('motivo') or data.get('motivo') or '').strip()
        if not motivo:
            return jsonify({'sucesso': False, 'erro': 'Motivo e obrigatorio'}), 400

        resultado = ContaCorrenteService.desconsiderar_movimentacao(
            mov_id=mov_id,
            motivo=motivo,
            usuario=current_user.email,
        )

        if resultado.get('sucesso'):
            return jsonify(resultado)
        return jsonify(resultado), 400

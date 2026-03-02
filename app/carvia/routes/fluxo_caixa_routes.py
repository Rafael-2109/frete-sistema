"""
Rotas de Fluxo de Caixa CarVia
================================

GET  /carvia/fluxo-de-caixa              - Tela principal
POST /carvia/api/fluxo-caixa/pagar       - Marcar como pago + criar movimentacao
POST /carvia/api/fluxo-caixa/desfazer    - Desfazer pagamento + remover movimentacao
GET  /carvia/extrato-conta               - Extrato da conta
POST /carvia/api/extrato-conta/saldo-inicial - Definir/alterar saldo inicial
"""

import logging
from datetime import date, timedelta

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app import db

logger = logging.getLogger(__name__)

# Mapeamento tipo_doc -> tipo_movimento na conta
TIPO_MOVIMENTO_MAP = {
    'fatura_cliente': 'CREDITO',
    'fatura_transportadora': 'DEBITO',
    'despesa': 'DEBITO',
}


def _criar_movimentacao(tipo_doc, doc_id, valor, descricao, usuario):
    """Cria registro de movimentacao na conta CarVia.

    Returns:
        CarviaContaMovimentacao criada

    Raises:
        IntegrityError se movimentacao duplicada (UNIQUE tipo_doc+doc_id)
    """
    from app.carvia.models import CarviaContaMovimentacao
    from app.utils.timezone import agora_utc_naive

    tipo_movimento = TIPO_MOVIMENTO_MAP[tipo_doc]

    mov = CarviaContaMovimentacao(
        tipo_doc=tipo_doc,
        doc_id=int(doc_id),
        tipo_movimento=tipo_movimento,
        valor=abs(float(valor)),
        descricao=descricao,
        criado_por=usuario,
        criado_em=agora_utc_naive(),
    )
    db.session.add(mov)
    return mov


def _remover_movimentacao(tipo_doc, doc_id):
    """Remove movimentacao da conta CarVia.

    Returns:
        True se removida, False se nao existia (pagamento pre-feature)
    """
    from app.carvia.models import CarviaContaMovimentacao

    mov = db.session.query(CarviaContaMovimentacao).filter_by(
        tipo_doc=tipo_doc,
        doc_id=int(doc_id),
    ).first()

    if mov:
        db.session.delete(mov)
        return True
    return False


def _obter_saldo_atual():
    """Helper para obter saldo atual da conta."""
    from app.carvia.services.fluxo_caixa_service import FluxoCaixaService
    return FluxoCaixaService().obter_saldo_conta()


def _gerar_descricao(tipo_doc, doc):
    """Gera descricao legivel para a movimentacao."""
    if tipo_doc == 'fatura_cliente':
        nome = doc.nome_cliente or doc.cnpj_cliente or ''
        return f"Fatura CarVia #{doc.numero_fatura} - {nome}".strip(' -')
    elif tipo_doc == 'fatura_transportadora':
        nome = ''
        if doc.transportadora:
            nome = doc.transportadora.razao_social or ''
        return f"Fatura Subcontrato #{doc.numero_fatura} - {nome}".strip(' -')
    elif tipo_doc == 'despesa':
        tipo = doc.tipo_despesa or 'Despesa'
        desc = doc.descricao or ''
        return f"{tipo} #{doc.id} - {desc}".strip(' -')
    return ''


def register_fluxo_caixa_routes(bp):

    @bp.route('/fluxo-de-caixa')
    @login_required
    def fluxo_caixa():
        """Tela de fluxo de caixa consolidado."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        # Parametros de filtro
        hoje = date.today()

        data_inicio_str = request.args.get('data_inicio', '')
        data_fim_str = request.args.get('data_fim', '')
        status = request.args.get('status', 'total')

        # Validar datas
        try:
            data_inicio = date.fromisoformat(data_inicio_str) if data_inicio_str else hoje
        except ValueError:
            data_inicio = hoje

        try:
            data_fim = date.fromisoformat(data_fim_str) if data_fim_str else hoje + timedelta(days=30)
        except ValueError:
            data_fim = hoje + timedelta(days=30)

        # Garantir data_fim >= data_inicio
        if data_fim < data_inicio:
            data_fim = data_inicio + timedelta(days=30)

        # Validar status
        if status not in ('total', 'pendente', 'pago'):
            status = 'total'

        # Buscar dados
        from app.carvia.services.fluxo_caixa_service import FluxoCaixaService
        service = FluxoCaixaService()
        fluxo = service.obter_fluxo(data_inicio, data_fim, status)
        saldo_conta = service.obter_saldo_conta()

        return render_template(
            'carvia/fluxo_caixa.html',
            fluxo=fluxo,
            data_inicio=data_inicio.isoformat(),
            data_fim=data_fim.isoformat(),
            status_filtro=status,
            saldo_conta=saldo_conta,
        )

    @bp.route('/api/fluxo-caixa/pagar', methods=['POST'])
    @login_required
    def api_fluxo_caixa_pagar():
        """Marca um lancamento como pago e cria movimentacao na conta."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        tipo_doc = data.get('tipo_doc')
        doc_id = data.get('id')

        if not tipo_doc or not doc_id:
            return jsonify({'erro': 'tipo_doc e id sao obrigatorios'}), 400

        try:
            from app.carvia.models import (
                CarviaFaturaCliente,
                CarviaFaturaTransportadora,
                CarviaDespesa,
            )
            from app.utils.timezone import agora_utc_naive

            agora = agora_utc_naive()
            usuario = current_user.email

            if tipo_doc == 'fatura_cliente':
                doc = db.session.get(CarviaFaturaCliente, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Fatura cliente nao encontrada'}), 404
                if doc.status == 'CANCELADA':
                    return jsonify({'erro': 'Fatura cancelada nao pode ser paga'}), 400
                doc.status = 'PAGA'
                doc.pago_por = usuario
                doc.pago_em = agora
                novo_status = 'PAGA'
                valor_mov = float(doc.valor_total or 0)

            elif tipo_doc == 'fatura_transportadora':
                doc = db.session.get(CarviaFaturaTransportadora, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Fatura transportadora nao encontrada'}), 404
                doc.status_pagamento = 'PAGO'
                doc.pago_por = usuario
                doc.pago_em = agora
                novo_status = 'PAGO'
                valor_mov = float(doc.valor_total or 0)

            elif tipo_doc == 'despesa':
                doc = db.session.get(CarviaDespesa, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Despesa nao encontrada'}), 404
                if doc.status == 'CANCELADO':
                    return jsonify({'erro': 'Despesa cancelada nao pode ser paga'}), 400
                doc.status = 'PAGO'
                doc.pago_por = usuario
                doc.pago_em = agora
                novo_status = 'PAGO'
                valor_mov = float(doc.valor or 0)

            else:
                return jsonify({'erro': f'Tipo de documento invalido: {tipo_doc}'}), 400

            # Criar movimentacao na conta
            descricao = _gerar_descricao(tipo_doc, doc)
            _criar_movimentacao(tipo_doc, doc_id, valor_mov, descricao, usuario)

            db.session.commit()
            saldo_atual = _obter_saldo_atual()

            logger.info(
                f"Fluxo caixa: {tipo_doc} #{doc_id} marcado como {novo_status} "
                f"por {usuario} (saldo: {saldo_atual:.2f})"
            )

            return jsonify({
                'sucesso': True,
                'novo_status': novo_status,
                'saldo_atual': saldo_atual,
            })

        except IntegrityError:
            db.session.rollback()
            logger.warning(f"Movimentacao duplicada: {tipo_doc} #{doc_id}")
            return jsonify({'erro': 'Este lancamento ja foi processado'}), 409

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao marcar pagamento: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/fluxo-caixa/desfazer', methods=['POST'])
    @login_required
    def api_fluxo_caixa_desfazer():
        """Desfaz marcacao de pagamento e remove movimentacao da conta."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        tipo_doc = data.get('tipo_doc')
        doc_id = data.get('id')

        if not tipo_doc or not doc_id:
            return jsonify({'erro': 'tipo_doc e id sao obrigatorios'}), 400

        try:
            from app.carvia.models import (
                CarviaFaturaCliente,
                CarviaFaturaTransportadora,
                CarviaDespesa,
            )

            if tipo_doc == 'fatura_cliente':
                doc = db.session.get(CarviaFaturaCliente, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Fatura cliente nao encontrada'}), 404
                doc.status = 'PENDENTE'
                doc.pago_por = None
                doc.pago_em = None
                novo_status = 'PENDENTE'

            elif tipo_doc == 'fatura_transportadora':
                doc = db.session.get(CarviaFaturaTransportadora, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Fatura transportadora nao encontrada'}), 404
                doc.status_pagamento = 'PENDENTE'
                doc.pago_por = None
                doc.pago_em = None
                novo_status = 'PENDENTE'

            elif tipo_doc == 'despesa':
                doc = db.session.get(CarviaDespesa, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Despesa nao encontrada'}), 404
                doc.status = 'PENDENTE'
                doc.pago_por = None
                doc.pago_em = None
                novo_status = 'PENDENTE'

            else:
                return jsonify({'erro': f'Tipo de documento invalido: {tipo_doc}'}), 400

            # Remover movimentacao da conta (se existir)
            removida = _remover_movimentacao(tipo_doc, doc_id)
            if not removida:
                logger.warning(
                    f"Movimentacao nao encontrada ao desfazer {tipo_doc} #{doc_id} "
                    f"(pagamento pre-feature)"
                )

            db.session.commit()
            saldo_atual = _obter_saldo_atual()

            logger.info(
                f"Fluxo caixa: {tipo_doc} #{doc_id} desfeito para {novo_status} "
                f"por {current_user.email} (saldo: {saldo_atual:.2f})"
            )

            return jsonify({
                'sucesso': True,
                'novo_status': novo_status,
                'saldo_atual': saldo_atual,
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao desfazer pagamento: {e}")
            return jsonify({'erro': str(e)}), 500

    # ===================================================================
    # Extrato da Conta
    # ===================================================================

    @bp.route('/extrato-conta')
    @login_required
    def extrato_conta():
        """Tela de extrato da conta CarVia."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        hoje = date.today()

        # Filtros: default = mes atual
        data_inicio_str = request.args.get('data_inicio', '')
        data_fim_str = request.args.get('data_fim', '')

        try:
            data_inicio = date.fromisoformat(data_inicio_str) if data_inicio_str else hoje.replace(day=1)
        except ValueError:
            data_inicio = hoje.replace(day=1)

        try:
            data_fim = date.fromisoformat(data_fim_str) if data_fim_str else hoje
        except ValueError:
            data_fim = hoje

        if data_fim < data_inicio:
            data_fim = data_inicio

        from app.carvia.services.fluxo_caixa_service import FluxoCaixaService
        service = FluxoCaixaService()
        extrato = service.obter_extrato(data_inicio, data_fim)
        saldo_conta = service.obter_saldo_conta()

        return render_template(
            'carvia/extrato_conta.html',
            extrato=extrato,
            data_inicio=data_inicio.isoformat(),
            data_fim=data_fim.isoformat(),
            saldo_conta=saldo_conta,
        )

    @bp.route('/api/extrato-conta/saldo-inicial', methods=['POST'])
    @login_required
    def api_saldo_inicial():
        """Define ou altera o saldo inicial da conta."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data or 'valor' not in data:
            return jsonify({'erro': 'Campo valor e obrigatorio'}), 400

        try:
            valor = float(data['valor'])
        except (ValueError, TypeError):
            return jsonify({'erro': 'Valor invalido'}), 400

        try:
            from app.carvia.models import CarviaContaMovimentacao
            from app.utils.timezone import agora_utc_naive

            # Remover saldo inicial existente (se houver)
            existente = db.session.query(CarviaContaMovimentacao).filter_by(
                tipo_doc='saldo_inicial',
                doc_id=0,
            ).first()

            if existente:
                db.session.delete(existente)
                db.session.flush()

            # Inserir novo saldo inicial
            if valor != 0:
                tipo_movimento = 'CREDITO' if valor >= 0 else 'DEBITO'
                mov = CarviaContaMovimentacao(
                    tipo_doc='saldo_inicial',
                    doc_id=0,
                    tipo_movimento=tipo_movimento,
                    valor=abs(valor),
                    descricao='Saldo inicial da conta',
                    criado_por=current_user.email,
                    criado_em=agora_utc_naive(),
                )
                db.session.add(mov)

            db.session.commit()
            saldo_atual = _obter_saldo_atual()

            logger.info(
                f"Saldo inicial definido: R$ {valor:.2f} por {current_user.email} "
                f"(saldo atual: {saldo_atual:.2f})"
            )

            return jsonify({
                'sucesso': True,
                'saldo_atual': saldo_atual,
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao definir saldo inicial: {e}")
            return jsonify({'erro': str(e)}), 500

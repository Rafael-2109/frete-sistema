"""
Rotas de Fluxo de Caixa CarVia
================================

GET  /carvia/fluxo-de-caixa              - Tela principal (visao dias ou lista)
POST /carvia/api/fluxo-caixa/pagar       - Marca como pago (via CarviaPagamentoService)
POST /carvia/api/fluxo-caixa/desfazer    - Desfaz pagamento (via CarviaPagamentoService)
POST /carvia/api/fluxo-caixa/alterar-vencimento - Altera data de vencimento
GET  /carvia/extrato-conta               - Extrato da conta (movimentacoes + linhas MANUAL)
POST /carvia/api/extrato-conta/saldo-inicial - Define/altera o saldo inicial

W10 Nivel 2 (Sprint 4): pagamentos agora sao orquestrados por
CarviaPagamentoService (SOT). CarviaContaMovimentacao permanece como
fonte unica do `saldo_inicial`.
"""

import logging
from datetime import date, timedelta

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app import db

logger = logging.getLogger(__name__)


def _obter_saldo_atual():
    """Helper para obter saldo atual da conta."""
    from app.carvia.services.financeiro.fluxo_caixa_service import FluxoCaixaService
    return FluxoCaixaService().obter_saldo_conta()


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
        visao = request.args.get('visao', 'dias')
        direcao = request.args.get('direcao', 'todos')

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

        # Validar visao e direcao
        if visao not in ('dias', 'lista'):
            visao = 'dias'
        if direcao not in ('todos', 'receber', 'pagar'):
            direcao = 'todos'

        # Buscar dados
        from app.carvia.services.financeiro.fluxo_caixa_service import FluxoCaixaService
        service = FluxoCaixaService()
        saldo_conta = service.obter_saldo_conta()

        template_vars = {
            'data_inicio': data_inicio.isoformat(),
            'data_fim': data_fim.isoformat(),
            'status_filtro': status,
            'saldo_conta': saldo_conta,
            'visao': visao,
            'direcao': direcao,
        }

        if visao == 'lista':
            resultado = service.obter_lista_corrida(data_inicio, data_fim, status, direcao)
            template_vars['fluxo'] = resultado
            template_vars['lancamentos'] = resultado['lancamentos']
        else:
            fluxo = service.obter_fluxo(data_inicio, data_fim, status)
            template_vars['fluxo'] = fluxo
            template_vars['lancamentos'] = []

        return render_template('carvia/fluxo_caixa.html', **template_vars)

    @bp.route('/api/fluxo-caixa/pagar', methods=['POST'])
    @login_required
    def api_fluxo_caixa_pagar():
        """Marca um lancamento como pago via CarviaPagamentoService.

        Dois modos (mutuamente exclusivos):

        1. Com conciliacao (extrato_linha_id presente):
           Concilia com uma linha OFX/CSV existente.
           Payload: {tipo_doc, id, data_pagamento, extrato_linha_id}

        2. Manual (extrato_linha_id ausente):
           Cria linha origem='MANUAL' com conta_origem + descricao_pagamento
           e concilia. Usado quando pagamento e feito por outra conta
           (pessoal, empresa parceira, dinheiro, etc.).
           Payload: {tipo_doc, id, data_pagamento, conta_origem, descricao_pagamento}

        W10 Nivel 2 (Sprint 4): Conciliacao e SOT unica para pagamento.
        Esta rota e apenas um wrapper do CarviaPagamentoService.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        tipo_doc = data.get('tipo_doc')
        doc_id = data.get('id')
        data_pagamento_str = data.get('data_pagamento', '')
        extrato_linha_id = data.get('extrato_linha_id')  # opcional
        conta_origem = data.get('conta_origem')  # obrigatorio em modo manual
        descricao_pagamento = data.get('descricao_pagamento')  # obrigatorio em modo manual

        if not tipo_doc or not doc_id:
            return jsonify({'erro': 'tipo_doc e id sao obrigatorios'}), 400

        if not data_pagamento_str:
            return jsonify({'erro': 'Data de pagamento e obrigatoria'}), 400
        try:
            data_pagamento = date.fromisoformat(data_pagamento_str)
        except ValueError:
            return jsonify({'erro': 'Data de pagamento invalida'}), 400

        from app.carvia.services.financeiro.carvia_pagamento_service import (
            CarviaPagamentoService,
            DocumentoJaPagoError,
            DocumentoCanceladoError,
            DocumentoNaoEncontradoError,
            JaConciliadoError,
            ParametroInvalidoError,
            PagamentoError,
        )

        usuario = current_user.email

        try:
            if extrato_linha_id:
                resultado = CarviaPagamentoService.pagar_com_conciliacao(
                    tipo_doc=tipo_doc,
                    doc_id=doc_id,
                    data_pagamento=data_pagamento,
                    extrato_linha_id=extrato_linha_id,
                    usuario=usuario,
                )
            else:
                resultado = CarviaPagamentoService.pagar_manual(
                    tipo_doc=tipo_doc,
                    doc_id=doc_id,
                    data_pagamento=data_pagamento,
                    conta_origem=conta_origem,
                    descricao_pagamento=descricao_pagamento,
                    usuario=usuario,
                )

            db.session.commit()
            saldo_atual = _obter_saldo_atual()

            logger.info(
                "Fluxo caixa: %s #%s marcado como %s por %s (saldo: %.2f)",
                tipo_doc, doc_id, resultado['novo_status'], usuario, saldo_atual,
            )

            return jsonify({
                'sucesso': True,
                'novo_status': resultado['novo_status'],
                'saldo_atual': saldo_atual,
                'conciliado': resultado.get('conciliou', False),
                'modo': resultado.get('modo'),
                'extrato_linha_id': resultado.get('extrato_linha_id'),
            })

        except DocumentoNaoEncontradoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 404
        except DocumentoCanceladoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except DocumentoJaPagoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 409
        except JaConciliadoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except ParametroInvalidoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except PagamentoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except IntegrityError:
            db.session.rollback()
            logger.warning(f"Movimentacao duplicada: {tipo_doc} #{doc_id}")
            return jsonify({'erro': 'Este lancamento ja foi processado'}), 409
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erro ao marcar pagamento: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/fluxo-caixa/desfazer', methods=['POST'])
    @login_required
    def api_fluxo_caixa_desfazer():
        """Desfaz marcacao de pagamento via CarviaPagamentoService.

        W10 Nivel 2 (Sprint 4): Conciliacao e SOT.
        - Se doc esta conciliado com linha REAL (OFX/CSV): BLOQUEIA,
          usuario deve desconciliar via Extrato Bancario.
        - Se doc esta conciliado com linhas MANUAL: desconcilia e remove
          as linhas MANUAL orfas.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        tipo_doc = data.get('tipo_doc')
        doc_id = data.get('id')

        if not tipo_doc or not doc_id:
            return jsonify({'erro': 'tipo_doc e id sao obrigatorios'}), 400

        from app.carvia.services.financeiro.carvia_pagamento_service import (
            CarviaPagamentoService,
            DocumentoNaoEncontradoError,
            ParametroInvalidoError,
            PagamentoError,
        )

        try:
            resultado = CarviaPagamentoService.desfazer_pagamento(
                tipo_doc=tipo_doc,
                doc_id=doc_id,
                usuario=current_user.email,
            )
            # Compat historico (ContaMovimentacao legada) e feito
            # INTERNAMENTE por CarviaPagamentoService.desfazer_pagamento.

            db.session.commit()
            saldo_atual = _obter_saldo_atual()

            logger.info(
                "Fluxo caixa: %s #%s desfeito para %s por %s (saldo: %.2f)",
                tipo_doc, doc_id, resultado['novo_status'],
                current_user.email, saldo_atual,
            )

            return jsonify({
                'sucesso': True,
                'novo_status': resultado['novo_status'],
                'saldo_atual': saldo_atual,
                'linhas_manuais_removidas': resultado.get(
                    'linhas_manuais_removidas', 0
                ),
            })

        except DocumentoNaoEncontradoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 404
        except ParametroInvalidoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except PagamentoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erro ao desfazer pagamento: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/api/fluxo-caixa/alterar-vencimento', methods=['POST'])
    @login_required
    def api_fluxo_caixa_alterar_vencimento():
        """Altera a data de vencimento de um lancamento."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados nao fornecidos'}), 400

        tipo_doc = data.get('tipo_doc')
        doc_id = data.get('id')
        novo_vencimento_str = data.get('novo_vencimento', '')

        if not tipo_doc or not doc_id:
            return jsonify({'erro': 'tipo_doc e id sao obrigatorios'}), 400

        if not novo_vencimento_str:
            return jsonify({'erro': 'novo_vencimento e obrigatorio'}), 400

        try:
            novo_vencimento = date.fromisoformat(novo_vencimento_str)
        except ValueError:
            return jsonify({'erro': 'Data de vencimento invalida'}), 400

        try:
            from app.carvia.models import (
                CarviaFaturaCliente,
                CarviaFaturaTransportadora,
                CarviaDespesa,
                CarviaCustoEntrega,
                CarviaReceita,
            )

            if tipo_doc == 'fatura_cliente':
                doc = db.session.get(CarviaFaturaCliente, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Fatura cliente nao encontrada'}), 404
                if doc.status in ('PAGA', 'CANCELADA'):
                    return jsonify({'erro': f'Fatura com status {doc.status} nao pode ter vencimento alterado'}), 400
                doc.vencimento = novo_vencimento

            elif tipo_doc == 'fatura_transportadora':
                doc = db.session.get(CarviaFaturaTransportadora, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Fatura transportadora nao encontrada'}), 404
                if doc.status_pagamento == 'PAGO':
                    return jsonify({'erro': 'Fatura paga nao pode ter vencimento alterado'}), 400
                if doc.status_conferencia == 'CONFERIDO':
                    return jsonify({'erro': 'Fatura conferida nao pode ter vencimento alterado'}), 400
                doc.vencimento = novo_vencimento

            elif tipo_doc == 'despesa':
                doc = db.session.get(CarviaDespesa, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Despesa nao encontrada'}), 404
                if doc.status in ('PAGO', 'CANCELADO'):
                    return jsonify({'erro': f'Despesa com status {doc.status} nao pode ter vencimento alterado'}), 400
                # W13 (Sprint 1 followup): Despesa COMISSAO e imutavel
                if doc.tipo_despesa == 'COMISSAO':
                    return jsonify({
                        'erro': (
                            'Vencimento de Despesa COMISSAO e gerenciado '
                            'pelo Fechamento de Comissao (data_fim).'
                        ),
                    }), 400
                doc.data_vencimento = novo_vencimento

            elif tipo_doc == 'custo_entrega':
                doc = db.session.get(CarviaCustoEntrega, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Custo de entrega nao encontrado'}), 404
                if doc.status in ('PAGO', 'CANCELADO'):
                    return jsonify({'erro': f'Custo com status {doc.status} nao pode ter vencimento alterado'}), 400
                doc.data_vencimento = novo_vencimento

            elif tipo_doc == 'receita':
                doc = db.session.get(CarviaReceita, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Receita nao encontrada'}), 404
                if doc.status in ('RECEBIDO', 'CANCELADO'):
                    return jsonify({'erro': f'Receita com status {doc.status} nao pode ter vencimento alterado'}), 400
                doc.data_vencimento = novo_vencimento

            else:
                return jsonify({'erro': f'Tipo de documento invalido: {tipo_doc}'}), 400

            db.session.commit()

            logger.info(
                f"Vencimento alterado: {tipo_doc} #{doc_id} -> {novo_vencimento.isoformat()} "
                f"por {current_user.email}"
            )

            return jsonify({
                'sucesso': True,
                'novo_vencimento': novo_vencimento.strftime('%d/%m/%Y'),
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao alterar vencimento: {e}")
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

        from app.carvia.services.financeiro.fluxo_caixa_service import FluxoCaixaService
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

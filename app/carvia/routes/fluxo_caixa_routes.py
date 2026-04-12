"""
Rotas de Fluxo de Caixa CarVia
================================

GET  /carvia/fluxo-de-caixa              - Tela principal (visao dias ou lista)
POST /carvia/api/fluxo-caixa/pagar       - Marcar como pago + criar movimentacao
POST /carvia/api/fluxo-caixa/desfazer    - Desfazer pagamento + remover movimentacao
POST /carvia/api/fluxo-caixa/alterar-vencimento - Alterar data de vencimento
GET  /carvia/extrato-conta               - Extrato da conta
POST /carvia/api/extrato-conta/saldo-inicial - Definir/alterar saldo inicial
"""

import logging
from datetime import date, datetime, timedelta

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
    'custo_entrega': 'DEBITO',
    'receita': 'CREDITO',
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
    from app.carvia.services.financeiro.fluxo_caixa_service import FluxoCaixaService
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
    elif tipo_doc == 'custo_entrega':
        desc = doc.descricao or doc.tipo_custo
        return f"Custo Entrega #{doc.numero_custo} - {desc}".strip(' -')
    elif tipo_doc == 'receita':
        tipo = doc.tipo_receita or 'Receita'
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
        """Marca um lancamento como pago e cria movimentacao na conta.

        Aceita extrato_linha_id opcional — se presente, tambem concilia
        o documento com a linha de extrato via CarviaConciliacaoService.

        W10 (Sprint 2): Conciliacao e SOT para pagamento. Se o documento
        ja tem CarviaConciliacao, FC deve bloquear — o status financeiro
        e gerenciado pelo Extrato Bancario, nao pelo FC.
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

        if not tipo_doc or not doc_id:
            return jsonify({'erro': 'tipo_doc e id sao obrigatorios'}), 400

        # W10: Bloquear se ja tem conciliacao bancaria — Conciliacao e SOT.
        # Excecao: quando o proprio FC vai criar a conciliacao agora
        # (extrato_linha_id presente), pular o guard.
        if not extrato_linha_id:
            from app.carvia.models import CarviaConciliacao
            ja_conciliado = CarviaConciliacao.query.filter_by(
                tipo_documento=tipo_doc,
                documento_id=int(doc_id),
            ).first()
            if ja_conciliado:
                return jsonify({
                    'erro': (
                        'Este documento ja possui conciliacao bancaria. '
                        'Use a tela de Extrato Bancario para gerenciar o pagamento.'
                    ),
                }), 400

        # Validar data de pagamento (obrigatoria)
        if not data_pagamento_str:
            return jsonify({'erro': 'Data de pagamento e obrigatoria'}), 400
        try:
            data_pagamento = date.fromisoformat(data_pagamento_str)
        except ValueError:
            return jsonify({'erro': 'Data de pagamento invalida'}), 400

        pago_em_dt = datetime.combine(data_pagamento, datetime.min.time())

        try:
            from app.carvia.models import (
                CarviaFaturaCliente,
                CarviaFaturaTransportadora,
                CarviaDespesa,
                CarviaCustoEntrega,
                CarviaReceita,
            )

            usuario = current_user.email

            if tipo_doc == 'fatura_cliente':
                doc = db.session.get(CarviaFaturaCliente, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Fatura cliente nao encontrada'}), 404
                if doc.status == 'CANCELADA':
                    return jsonify({'erro': 'Fatura cancelada nao pode ser paga'}), 400
                # GAP-14: Verificar se ja esta PAGA
                if doc.status == 'PAGA':
                    return jsonify({'erro': 'Fatura ja esta paga'}), 409
                doc.status = 'PAGA'
                doc.pago_por = usuario
                doc.pago_em = pago_em_dt
                novo_status = 'PAGA'
                valor_mov = float(doc.valor_total or 0)

            elif tipo_doc == 'fatura_transportadora':
                doc = db.session.get(CarviaFaturaTransportadora, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Fatura transportadora nao encontrada'}), 404
                # GAP-14: Verificar se ja esta PAGO
                if doc.status_pagamento == 'PAGO':
                    return jsonify({'erro': 'Fatura transportadora ja esta paga'}), 409
                doc.status_pagamento = 'PAGO'
                doc.pago_por = usuario
                doc.pago_em = pago_em_dt
                novo_status = 'PAGO'
                valor_mov = float(doc.valor_total or 0)

            elif tipo_doc == 'despesa':
                doc = db.session.get(CarviaDespesa, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Despesa nao encontrada'}), 404
                if doc.status == 'CANCELADO':
                    return jsonify({'erro': 'Despesa cancelada nao pode ser paga'}), 400
                # GAP-14: Verificar se ja esta PAGO
                if doc.status == 'PAGO':
                    return jsonify({'erro': 'Despesa ja esta paga'}), 409
                doc.status = 'PAGO'
                doc.pago_por = usuario
                doc.pago_em = pago_em_dt
                novo_status = 'PAGO'
                valor_mov = float(doc.valor or 0)

            elif tipo_doc == 'custo_entrega':
                doc = db.session.get(CarviaCustoEntrega, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Custo de entrega nao encontrado'}), 404
                if doc.status == 'CANCELADO':
                    return jsonify({'erro': 'Custo cancelado nao pode ser pago'}), 400
                # GAP-14: Verificar se ja esta PAGO
                if doc.status == 'PAGO':
                    return jsonify({'erro': 'Custo de entrega ja esta pago'}), 409
                doc.status = 'PAGO'
                doc.pago_por = usuario
                doc.pago_em = pago_em_dt
                novo_status = 'PAGO'
                valor_mov = float(doc.valor or 0)

            elif tipo_doc == 'receita':
                doc = db.session.get(CarviaReceita, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Receita nao encontrada'}), 404
                if doc.status == 'CANCELADO':
                    return jsonify({'erro': 'Receita cancelada nao pode ser recebida'}), 400
                if doc.status == 'RECEBIDO':
                    return jsonify({'erro': 'Receita ja foi recebida'}), 409
                doc.status = 'RECEBIDO'
                doc.recebido_por = usuario
                doc.recebido_em = pago_em_dt
                novo_status = 'RECEBIDO'
                valor_mov = float(doc.valor or 0)

            else:
                return jsonify({'erro': f'Tipo de documento invalido: {tipo_doc}'}), 400

            # W10 Nivel 2 (Sprint 3): Dois fluxos distintos
            # ------------------------------------------------
            # (a) COM extrato_linha_id: pagamento via Extrato Bancario real.
            #     Concilia diretamente, sem criar ContaMovimentacao nem
            #     linha virtual. Conciliacao e SOT.
            # (b) SEM extrato_linha_id: pagamento avulso via FC.
            #     Cria CarviaExtratoLinha VIRTUAL (origem='FC_VIRTUAL')
            #     e concilia atraves dela. ContaMovimentacao vira legado —
            #     nao e mais criado neste fluxo.

            from app.carvia.services.financeiro.carvia_conciliacao_service import (
                CarviaConciliacaoService,
            )
            from app.carvia.models import CarviaConciliacao, CarviaExtratoLinha

            conciliou = False

            if extrato_linha_id:
                # Fluxo (a): concilia com linha bancaria real
                try:
                    ja_existe = db.session.query(CarviaConciliacao).filter_by(
                        extrato_linha_id=int(extrato_linha_id),
                        tipo_documento=tipo_doc,
                        documento_id=int(doc_id),
                    ).first()

                    if not ja_existe:
                        CarviaConciliacaoService.conciliar(
                            int(extrato_linha_id),
                            [{
                                'tipo_documento': tipo_doc,
                                'documento_id': int(doc_id),
                                'valor_alocado': valor_mov,
                            }],
                            usuario,
                        )
                    conciliou = True
                    logger.info(
                        f"FC: {tipo_doc} #{doc_id} conciliado com linha "
                        f"real #{extrato_linha_id}"
                    )
                except (ValueError, Exception) as e:
                    db.session.rollback()
                    logger.error(
                        f"Conciliacao falhou para {tipo_doc} #{doc_id} "
                        f"(linha #{extrato_linha_id}): {e}"
                    )
                    return jsonify({'erro': f'Conciliacao falhou: {e}'}), 500
            else:
                # Fluxo (b): cria linha VIRTUAL + concilia
                # fitid unico: FC-{tipo}-{doc_id}-{timestamp}
                import time
                fitid_virtual = f"FC-{tipo_doc}-{doc_id}-{int(time.time() * 1000)}"
                # Tipo bancario: DEBITO se e pagamento que sai da conta,
                # CREDITO se e recebimento (receita, fatura cliente)
                tipo_linha = 'CREDITO' if tipo_doc in (
                    'fatura_cliente', 'receita'
                ) else 'DEBITO'

                linha_virtual = CarviaExtratoLinha(
                    fitid=fitid_virtual,
                    data=data_pagamento,
                    valor=valor_mov,
                    tipo=tipo_linha,
                    descricao=_gerar_descricao(tipo_doc, doc),
                    memo='Pagamento via Fluxo de Caixa (Outros Extratos)',
                    status_conciliacao='PENDENTE',
                    total_conciliado=0,
                    arquivo_ofx='FC_VIRTUAL',
                    origem='FC_VIRTUAL',
                    criado_por=usuario,
                )
                db.session.add(linha_virtual)
                db.session.flush()  # obter id

                # Conciliar o doc com a linha virtual
                CarviaConciliacaoService.conciliar(
                    linha_virtual.id,
                    [{
                        'tipo_documento': tipo_doc,
                        'documento_id': int(doc_id),
                        'valor_alocado': valor_mov,
                    }],
                    usuario,
                )
                conciliou = True
                logger.info(
                    f"FC: {tipo_doc} #{doc_id} pago via linha virtual "
                    f"#{linha_virtual.id} ({fitid_virtual})"
                )

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
                'conciliado': conciliou,
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
        """Desfaz marcacao de pagamento.

        W10 (Sprint 2/3): Conciliacao e SOT.
        - Se doc esta conciliado com linha REAL (OFX/CSV): BLOQUEIA,
          usuario deve desconciliar via Extrato Bancario.
        - Se doc esta conciliado com linha VIRTUAL (FC_VIRTUAL): FC pode
          desfazer — ele proprio criou a linha. Desconcilia e remove a
          linha virtual se ela ficou orfa.
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

        # W10: Analisar conciliacoes — bloquear apenas se REAL (nao FC_VIRTUAL)
        from app.carvia.models import CarviaConciliacao, CarviaExtratoLinha
        conciliacoes = db.session.query(CarviaConciliacao).join(
            CarviaExtratoLinha,
            CarviaExtratoLinha.id == CarviaConciliacao.extrato_linha_id,
        ).filter(
            CarviaConciliacao.tipo_documento == tipo_doc,
            CarviaConciliacao.documento_id == int(doc_id),
        ).all()

        if conciliacoes:
            # Separar reais (OFX/CSV) de virtuais (FC_VIRTUAL)
            conciliacoes_reais = [
                c for c in conciliacoes
                if c.extrato_linha and c.extrato_linha.origem != 'FC_VIRTUAL'
            ]
            if conciliacoes_reais:
                return jsonify({
                    'erro': (
                        f'Documento possui {len(conciliacoes_reais)} conciliacao(oes) '
                        'bancaria(s) real(is). Desconcilie via Extrato Bancario primeiro.'
                    ),
                }), 400
            # Todas sao FC_VIRTUAL — FC pode desfazer
            # Desconciliar e remover linhas virtuais abaixo (apos reverter status)

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

            elif tipo_doc == 'custo_entrega':
                doc = db.session.get(CarviaCustoEntrega, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Custo de entrega nao encontrado'}), 404
                doc.status = 'PENDENTE'
                doc.pago_por = None
                doc.pago_em = None
                novo_status = 'PENDENTE'

            elif tipo_doc == 'receita':
                doc = db.session.get(CarviaReceita, int(doc_id))
                if not doc:
                    return jsonify({'erro': 'Receita nao encontrada'}), 404
                doc.status = 'PENDENTE'
                doc.recebido_por = None
                doc.recebido_em = None
                novo_status = 'PENDENTE'

            else:
                return jsonify({'erro': f'Tipo de documento invalido: {tipo_doc}'}), 400

            # W10 Nivel 2: Desconciliar linhas virtuais (FC_VIRTUAL)
            # Se ha conciliacoes FC_VIRTUAL, precisamos desconcilia-las
            # e remover as linhas virtuais orfas.
            from app.carvia.services.financeiro.carvia_conciliacao_service import (
                CarviaConciliacaoService,
            )
            linhas_virtuais_ids = set()
            for conc in conciliacoes:
                # Guarda o id da linha virtual antes de desconciliar
                if conc.extrato_linha and conc.extrato_linha.origem == 'FC_VIRTUAL':
                    linhas_virtuais_ids.add(conc.extrato_linha_id)
                # W10 N2 fix (Sprint 3 followup): NAO silenciar excecao —
                # se desconciliar falha, aborta o desfazer completo para
                # evitar estado inconsistente (linha virtual + conciliacao
                # parcialmente removidas).
                try:
                    CarviaConciliacaoService.desconciliar(
                        conc.id, current_user.email
                    )
                except Exception as e:
                    db.session.rollback()
                    logger.error(
                        f"Erro ao desconciliar #{conc.id} em desfazer FC: {e}"
                    )
                    return jsonify({
                        'erro': (
                            f'Falha ao desconciliar #{conc.id}: {e}. '
                            f'Operacao abortada para preservar integridade.'
                        ),
                    }), 500

            # Remover linhas virtuais orfas (sem outras conciliacoes)
            for linha_id in linhas_virtuais_ids:
                restantes = CarviaConciliacao.query.filter_by(
                    extrato_linha_id=linha_id
                ).count()
                if restantes == 0:
                    linha = db.session.get(CarviaExtratoLinha, linha_id)
                    if linha:
                        db.session.delete(linha)
                        logger.info(
                            f"Linha virtual FC #{linha_id} removida (orfa)"
                        )

            # Remover movimentacao legada (ContaMovimentacao) se existir
            # — apenas para compat com dados historicos
            removida = _remover_movimentacao(tipo_doc, doc_id)
            if not removida:
                logger.debug(
                    f"Movimentacao legada nao encontrada ao desfazer "
                    f"{tipo_doc} #{doc_id} (esperado para novos pagamentos)"
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

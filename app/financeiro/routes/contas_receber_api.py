"""
APIs de Contas a Receber
CRUD: detalhes, observação, alerta, confirmação, ação necessária
APIs: lembretes, tipos, snapshots
"""

from flask import request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date

from app import db
from app.utils.timezone import agora_utc_naive
from app.financeiro.routes import financeiro_bp


# ========================================
# ROTAS API: CONTAS A RECEBER - CRUD
# ========================================

@financeiro_bp.route('/contas-receber/api/<int:conta_id>/detalhes')
@login_required
def api_conta_detalhes(conta_id):
    """
    Retorna detalhes completos de uma conta a receber
    Inclui dados de EntregaMonitorada via relacionamento
    """
    try:
        from app.financeiro.models import ContasAReceber

        conta = ContasAReceber.query.get_or_404(conta_id)

        # Dados base
        dados = conta.to_dict()

        # Enriquecer com dados da EntregaMonitorada (se existir)
        if conta.entrega_monitorada:
            em = conta.entrega_monitorada
            dados['entrega'] = {
                'id': em.id,
                'status_finalizacao': em.status_finalizacao,
                'data_hora_entrega_realizada': em.data_hora_entrega_realizada.isoformat() if em.data_hora_entrega_realizada else None,
                'canhoto_arquivo': em.canhoto_arquivo,
                'possui_canhoto': em.possui_canhoto,
                'nova_nf': em.nova_nf,
                'nf_cd': em.nf_cd,
                'reagendar': em.reagendar,
                'data_embarque': em.data_embarque.isoformat() if em.data_embarque else None,
                'data_entrega_prevista': em.data_entrega_prevista.isoformat() if em.data_entrega_prevista else None,
                'transportadora': em.transportadora,
                'vendedor': em.vendedor
            }

            # Último agendamento
            if em.agendamentos:
                ultimo_ag = sorted(em.agendamentos, key=lambda x: x.criado_em, reverse=True)[0] if em.agendamentos else None
                if ultimo_ag:
                    dados['entrega']['ultimo_agendamento'] = {
                        'data': ultimo_ag.data_agendada.isoformat() if ultimo_ag.data_agendada else None,
                        'status': ultimo_ag.status,
                        'protocolo': ultimo_ag.protocolo_agendamento
                    }

        return jsonify({'success': True, 'conta': dados})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/api/<int:conta_id>/observacao', methods=['POST'])
@login_required
def api_atualizar_observacao(conta_id):
    """
    Atualiza observação de uma conta a receber
    """
    try:
        from app.financeiro.models import ContasAReceber

        conta = ContasAReceber.query.get_or_404(conta_id)
        data = request.get_json()

        conta.observacao = data.get('observacao', '')
        conta.atualizado_por = current_user.nome
        conta.atualizado_em = agora_utc_naive()

        db.session.commit()

        return jsonify({'success': True, 'message': 'Observação atualizada com sucesso!'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/api/<int:conta_id>/alerta', methods=['POST'])
@login_required
def api_toggle_alerta(conta_id):
    """
    Toggle alerta de uma conta a receber
    """
    try:
        from app.financeiro.models import ContasAReceber

        conta = ContasAReceber.query.get_or_404(conta_id)

        conta.alerta = not conta.alerta
        conta.atualizado_por = current_user.nome
        conta.atualizado_em = agora_utc_naive()

        db.session.commit()

        return jsonify({
            'success': True,
            'alerta': conta.alerta,
            'message': 'Alerta ativado!' if conta.alerta else 'Alerta desativado!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/api/<int:conta_id>/confirmacao', methods=['GET', 'POST'])
@login_required
def api_confirmacao(conta_id):
    """
    GET: Retorna dados de confirmação
    POST: Atualiza dados de confirmação
    """
    try:
        from app.financeiro.models import ContasAReceber, ContasAReceberTipo

        conta = ContasAReceber.query.get_or_404(conta_id)

        if request.method == 'GET':
            # Buscar tipos disponíveis
            tipos_confirmacao = ContasAReceberTipo.query.filter_by(
                tabela='contas_a_receber',
                campo='confirmacao',
                ativo=True
            ).all()

            tipos_forma = ContasAReceberTipo.query.filter_by(
                tabela='contas_a_receber',
                campo='forma_confirmacao',
                ativo=True
            ).all()

            return jsonify({
                'success': True,
                'confirmacao': {
                    'confirmacao_tipo_id': conta.confirmacao_tipo_id,
                    'confirmacao_tipo_nome': conta.confirmacao_tipo.tipo if conta.confirmacao_tipo else None,
                    'forma_confirmacao_tipo_id': conta.forma_confirmacao_tipo_id,
                    'forma_confirmacao_tipo_nome': conta.forma_confirmacao_tipo.tipo if conta.forma_confirmacao_tipo else None,
                    'data_confirmacao': conta.data_confirmacao.isoformat() if conta.data_confirmacao else None,
                    'confirmado_por': conta.confirmado_por,
                    'confirmacao_entrega': conta.confirmacao_entrega
                },
                'tipos_confirmacao': [{'id': t.id, 'tipo': t.tipo} for t in tipos_confirmacao],
                'tipos_forma': [{'id': t.id, 'tipo': t.tipo} for t in tipos_forma]
            })

        # POST - Atualizar
        data = request.get_json()

        # Se está definindo confirmação pela primeira vez, registrar log
        if not conta.data_confirmacao and (data.get('confirmacao_tipo_id') or data.get('confirmacao_entrega')):
            conta.data_confirmacao = agora_utc_naive()
            conta.confirmado_por = current_user.nome

        tipo_id = data.get('confirmacao_tipo_id')
        conta.confirmacao_tipo_id = tipo_id
        conta.forma_confirmacao_tipo_id = data.get('forma_confirmacao_tipo_id')
        conta.confirmacao_entrega = data.get('confirmacao_entrega', '')
        conta.atualizado_por = current_user.nome
        conta.atualizado_em = agora_utc_naive()

        db.session.commit()

        # Buscar nome do tipo para retornar
        tipo_nome = None
        if tipo_id:
            tipo_obj = db.session.get(ContasAReceberTipo,tipo_id) if tipo_id else None
            tipo_nome = tipo_obj.tipo if tipo_obj else None

        return jsonify({
            'success': True,
            'message': 'Confirmação atualizada com sucesso!',
            'confirmacao_tipo_nome': tipo_nome
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/api/<int:conta_id>/acao-necessaria', methods=['GET', 'POST'])
@login_required
def api_acao_necessaria(conta_id):
    """
    GET: Retorna dados de ação necessária
    POST: Atualiza dados de ação necessária
    """
    try:
        from app.financeiro.models import ContasAReceber, ContasAReceberTipo

        conta = ContasAReceber.query.get_or_404(conta_id)

        if request.method == 'GET':
            # Buscar tipos disponíveis
            tipos_acao = ContasAReceberTipo.query.filter_by(
                tabela='contas_a_receber',
                campo='acao_necessaria',
                ativo=True
            ).all()

            return jsonify({
                'success': True,
                'acao': {
                    'acao_necessaria_tipo_id': conta.acao_necessaria_tipo_id,
                    'acao_necessaria_tipo_nome': conta.acao_necessaria_tipo.tipo if conta.acao_necessaria_tipo else None,
                    'obs_acao_necessaria': conta.obs_acao_necessaria,
                    'data_lembrete': conta.data_lembrete.isoformat() if conta.data_lembrete else None
                },
                'tipos_acao': [{'id': t.id, 'tipo': t.tipo} for t in tipos_acao]
            })

        # POST - Atualizar
        data = request.get_json()

        conta.acao_necessaria_tipo_id = data.get('acao_necessaria_tipo_id')
        conta.obs_acao_necessaria = data.get('obs_acao_necessaria', '')

        # Converter data_lembrete
        data_lembrete_str = data.get('data_lembrete')
        if data_lembrete_str:
            conta.data_lembrete = datetime.strptime(data_lembrete_str, '%Y-%m-%d').date()
        else:
            conta.data_lembrete = None

        conta.atualizado_por = current_user.nome
        conta.atualizado_em = agora_utc_naive()

        db.session.commit()

        return jsonify({'success': True, 'message': 'Ação necessária atualizada com sucesso!'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ========================================
# ROTAS API: LEMBRETES
# ========================================

@financeiro_bp.route('/contas-receber/api/lembretes')
@login_required
def api_listar_lembretes():
    """
    Lista lembretes agrupados por data (D-7 a D+7)
    Formato compacto para exibição no cabeçalho
    """
    try:
        from app.financeiro.models import ContasAReceber

        hoje = date.today()

        # Buscar contas com data_lembrete definida (nf_cancelada é property, filtrar em Python)
        contas_com_lembrete_query = ContasAReceber.query.filter(
            ContasAReceber.data_lembrete.isnot(None),
            ContasAReceber.parcela_paga == False
        ).all()

        # Filtrar nf_cancelada em Python (é uma property que busca em FaturamentoProduto)
        contas_com_lembrete = [c for c in contas_com_lembrete_query if not c.nf_cancelada]

        # Agrupar por data
        lembretes_por_data = {}
        antes_d7 = 0
        depois_d7 = 0

        for conta in contas_com_lembrete:
            diff_dias = (conta.data_lembrete - hoje).days

            if diff_dias < -7:
                antes_d7 += 1
            elif diff_dias > 7:
                depois_d7 += 1
            else:
                data_str = conta.data_lembrete.strftime('%d/%m')
                if data_str not in lembretes_por_data:
                    lembretes_por_data[data_str] = {
                        'data': conta.data_lembrete.isoformat(),
                        'data_display': data_str,
                        'diff_dias': diff_dias,
                        'count': 0,
                        'contas': []
                    }
                lembretes_por_data[data_str]['count'] += 1
                lembretes_por_data[data_str]['contas'].append({
                    'id': conta.id,
                    'titulo_nf': conta.titulo_nf,
                    'parcela': conta.parcela,
                    'cliente': conta.raz_social_red or conta.raz_social,
                    'valor': conta.valor_titulo
                })

        # Ordenar por data
        lembretes_ordenados = sorted(
            lembretes_por_data.values(),
            key=lambda x: x['data']
        )

        return jsonify({
            'success': True,
            'lembretes': lembretes_ordenados,
            'antes_d7': antes_d7,
            'depois_d7': depois_d7,
            'total': len(contas_com_lembrete)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/api/tipos')
@login_required
def api_listar_tipos():
    """
    Lista todos os tipos disponíveis para os selects
    """
    try:
        from app.financeiro.models import ContasAReceberTipo

        tipos = ContasAReceberTipo.query.filter_by(ativo=True).all()

        resultado = {}
        for tipo in tipos:
            chave = f"{tipo.tabela}_{tipo.campo}"
            if chave not in resultado:
                resultado[chave] = []
            resultado[chave].append({
                'id': tipo.id,
                'tipo': tipo.tipo,
                'explicacao': tipo.explicacao,
                'considera_a_receber': tipo.considera_a_receber
            })

        return jsonify({'success': True, 'tipos': resultado})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========================================
# ROTAS API: SNAPSHOTS (HISTÓRICO)
# ========================================

@financeiro_bp.route('/contas-receber/api/<int:conta_id>/snapshots')
@login_required
def api_listar_snapshots(conta_id):
    """
    Lista histórico de alterações (snapshots) de uma conta a receber
    """
    try:
        from app.financeiro.models import ContasAReceber, ContasAReceberSnapshot

        conta = ContasAReceber.query.get_or_404(conta_id)

        snapshots = ContasAReceberSnapshot.query.filter_by(
            conta_a_receber_id=conta_id
        ).order_by(ContasAReceberSnapshot.alterado_em.desc()).all()

        return jsonify({
            'success': True,
            'titulo_nf': conta.titulo_nf,
            'parcela': conta.parcela,
            'snapshots': [s.to_dict() for s in snapshots]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========================================
# ROTAS API: BAIXAS / RECONCILIAÇÕES
# ========================================
# NOTA: Rota api_listar_baixas REMOVIDA em 2025-11-28
# Motivo: Rota órfã que usava tabelas deprecated (Pagamento, Documento, LinhaCredito)
# O modal comparativo usa apenas ContasAReceberReconciliacao via api_comparativo_abatimentos


@financeiro_bp.route('/contas-receber/api/<int:conta_id>/importar-baixas', methods=['POST'])
@login_required
def api_importar_baixas(conta_id):
    """
    Importa baixas do Odoo para uma conta específica.
    Executa a importação on-demand para um título específico.
    """
    try:
        from app.financeiro.models import ContasAReceber
        from app.odoo.utils.connection import get_odoo_connection

        conta = ContasAReceber.query.get_or_404(conta_id)

        # Conectar ao Odoo
        connection = get_odoo_connection()
        if not connection.authenticate():
            return jsonify({'success': False, 'error': 'Falha na autenticação com Odoo'}), 500

        # Importar usando o serviço
        from scripts.importar_baixas_odoo import ImportadorBaixasOdoo

        importador = ImportadorBaixasOdoo(connection)
        qtd_importada = importador.importar_titulo(conta)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{qtd_importada} reconciliações importadas',
            'quantidade': qtd_importada,
            'estatisticas': importador.estatisticas
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ========================================
# ROTAS API: ABATIMENTOS + COMPARATIVO
# Sistema de Dupla Conferência
# ========================================

@financeiro_bp.route('/contas-receber/api/<int:conta_id>/comparativo')
@login_required
def api_comparativo_abatimentos(conta_id):
    """
    Retorna o comparativo completo entre Sistema e Odoo.

    Inclui:
    - Abatimentos do SISTEMA (com status de vinculação)
    - Baixas do ODOO (abatimentos e pagamentos separados)
    - Comparativo de totais (tolerância 0.02)
    - Flag de status (OK/DIVERGENTE)
    """
    try:
        from app.financeiro.models import ContasAReceber
        from app.financeiro.services import ComparativoAbatimentosService

        conta = ContasAReceber.query.get_or_404(conta_id)

        # Calcular comparativo
        comparativo = ComparativoAbatimentosService.calcular_comparativo(conta_id)

        # Listar abatimentos do sistema com vinculação
        abatimentos_sistema = ComparativoAbatimentosService.listar_abatimentos_com_vinculacao(conta_id)

        # Listar reconciliações do Odoo (abatimentos)
        reconciliacoes_odoo = ComparativoAbatimentosService.listar_reconciliacoes_disponiveis(conta_id)

        # Listar pagamentos do Odoo (separado)
        pagamentos_odoo = ComparativoAbatimentosService.listar_pagamentos_odoo(conta_id)

        # Buscar tipos de abatimento para o formulário
        from app.financeiro.models import ContasAReceberTipo
        tipos_abatimento = ContasAReceberTipo.query.filter_by(
            tabela='contas_a_receber_abatimento',
            campo='tipo',
            ativo=True
        ).order_by(ContasAReceberTipo.tipo).all()

        return jsonify({
            'success': True,
            'conta': {
                'id': conta.id,
                'titulo_nf': conta.titulo_nf,
                'parcela': conta.parcela,
                'empresa': conta.empresa,
                'empresa_nome': conta.empresa_nome,
                'cnpj': conta.cnpj,
                'raz_social': conta.raz_social,
                'raz_social_red': conta.raz_social_red,
                'valor_original': conta.valor_original,
                'valor_titulo': conta.valor_titulo,
                'desconto': conta.desconto,
                'parcela_paga': conta.parcela_paga,
                'status_pagamento_odoo': conta.status_pagamento_odoo,
                'vencimento': conta.vencimento.isoformat() if conta.vencimento else None,
                'emissao': conta.emissao.isoformat() if conta.emissao else None,
            },
            # Comparativo
            'comparativo': comparativo,
            # Sistema
            'abatimentos_sistema': abatimentos_sistema,
            # Odoo - Abatimentos
            'abatimentos_odoo': reconciliacoes_odoo,
            # Odoo - Pagamentos (separado)
            'pagamentos_odoo': pagamentos_odoo,
            # Tipos para formulário de novo abatimento
            'tipos_abatimento': [t.to_dict() for t in tipos_abatimento],
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/api/abatimento/<int:abatimento_id>/vincular', methods=['POST'])
@login_required
def api_vincular_abatimento(abatimento_id):
    """
    Vincula manualmente um abatimento do sistema a uma reconciliação do Odoo.

    Body JSON:
    {
        "reconciliacao_id": 123
    }
    """
    try:
        from flask import request
        from flask_login import current_user
        from app.financeiro.services import VinculacaoAbatimentosService

        data = request.get_json() or {}
        reconciliacao_id = data.get('reconciliacao_id')

        if not reconciliacao_id:
            return jsonify({'success': False, 'error': 'reconciliacao_id é obrigatório'}), 400

        usuario = current_user.nome if current_user and hasattr(current_user, 'nome') else 'Sistema'

        sucesso, mensagem = VinculacaoAbatimentosService.vincular_manual(
            abatimento_id=abatimento_id,
            reconciliacao_id=reconciliacao_id,
            usuario=usuario
        )

        if sucesso:
            db.session.commit()

        return jsonify({
            'success': sucesso,
            'message': mensagem
        }), 200 if sucesso else 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/api/abatimento/<int:abatimento_id>/desvincular', methods=['POST'])
@login_required
def api_desvincular_abatimento(abatimento_id):
    """
    Remove a vinculação de um abatimento com reconciliação do Odoo.
    """
    try:
        from flask_login import current_user
        from app.financeiro.services import VinculacaoAbatimentosService

        usuario = current_user.nome if current_user and hasattr(current_user, 'nome') else 'Sistema'

        sucesso, mensagem = VinculacaoAbatimentosService.desvincular(
            abatimento_id=abatimento_id,
            usuario=usuario
        )

        if sucesso:
            db.session.commit()

        return jsonify({
            'success': sucesso,
            'message': mensagem
        }), 200 if sucesso else 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/api/<int:conta_id>/vincular-pendentes', methods=['POST'])
@login_required
def api_vincular_pendentes(conta_id):
    """
    Tenta vincular automaticamente todos os abatimentos pendentes de uma conta.
    """
    try:
        from app.financeiro.models import ContasAReceber
        from app.financeiro.services import VinculacaoAbatimentosService

        conta = ContasAReceber.query.get_or_404(conta_id)

        stats = VinculacaoAbatimentosService.vincular_todos_pendentes(conta_id)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{stats["vinculados"]} abatimentos vinculados automaticamente',
            'estatisticas': stats
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@financeiro_bp.route('/contas-receber/api/<int:conta_id>/reconciliacoes-disponiveis')
@login_required
def api_reconciliacoes_disponiveis(conta_id):
    """
    Lista reconciliações do Odoo disponíveis para vinculação manual.

    Query params:
    - abatimento_id: Se informado, considera este abatimento como "disponível" mesmo se vinculado
    """
    try:
        from flask import request
        from app.financeiro.models import ContasAReceber
        from app.financeiro.services import ComparativoAbatimentosService

        conta = ContasAReceber.query.get_or_404(conta_id)
        abatimento_id = request.args.get('abatimento_id', type=int)

        reconciliacoes = ComparativoAbatimentosService.listar_reconciliacoes_disponiveis(
            conta_id=conta_id,
            abatimento_id=abatimento_id
        )

        return jsonify({
            'success': True,
            'reconciliacoes': reconciliacoes
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# NOTA: As rotas de criar/excluir abatimento já existem em abatimentos.py
# POST /contas-receber/api/<conta_id>/abatimentos -> api_criar_abatimento
# DELETE /contas-receber/api/abatimentos/<abatimento_id> -> api_excluir_abatimento
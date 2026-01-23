"""
Rotas para Recebimento Fisico (Fase 4)
========================================

Tela principal: preencher lotes + quality checks
Tela de status: acompanhar processamento no Odoo
APIs: buscar pickings, salvar, retry
"""

from flask import Blueprint, render_template, request, jsonify
import logging

logger = logging.getLogger(__name__)

recebimento_fisico_bp = Blueprint(
    'recebimento_fisico_views',
    __name__,
    url_prefix='/recebimento/fisico'
)


# =====================================================
# VIEWS (Telas HTML)
# =====================================================


@recebimento_fisico_bp.route('/')
def index():
    """Tela principal de recebimento fisico."""
    return render_template('recebimento/recebimento_fisico.html')


@recebimento_fisico_bp.route('/status')
def status():
    """Tela de status dos recebimentos."""
    return render_template('recebimento/status_recebimento.html')


# =====================================================
# APIs
# =====================================================


@recebimento_fisico_bp.route('/pickings')
def api_pickings():
    """
    API: Buscar pickings disponiveis para recebimento.

    Query params:
        company_id: ID da empresa (obrigatorio)
        filtro_nf: Filtrar por NF/origin
        filtro_fornecedor: Filtrar por nome fornecedor
    """
    try:
        from app.recebimento.services.recebimento_fisico_service import RecebimentoFisicoService

        company_id = request.args.get('company_id', type=int)
        if not company_id:
            return jsonify({'error': 'company_id obrigatorio'}), 400

        filtro_nf = request.args.get('filtro_nf', '').strip() or None
        filtro_fornecedor = request.args.get('filtro_fornecedor', '').strip() or None

        service = RecebimentoFisicoService()
        resultado = service.buscar_pickings_disponiveis(
            company_id=company_id,
            filtro_nf=filtro_nf,
            filtro_fornecedor=filtro_fornecedor,
        )

        return jsonify({
            'pickings': resultado['pickings'],
            'total': len(resultado['pickings']),
            'ultima_sincronizacao': resultado.get('ultima_sincronizacao'),
        })

    except Exception as e:
        logger.error(f"Erro ao buscar pickings: {e}")
        return jsonify({'error': str(e)}), 500


@recebimento_fisico_bp.route('/picking/<int:picking_id>/detalhes')
def api_detalhes_picking(picking_id):
    """
    API: Buscar detalhes completos de um picking.

    Retorna produtos com quantidades, tracking, e quality checks.
    """
    try:
        from app.recebimento.services.recebimento_fisico_service import RecebimentoFisicoService

        service = RecebimentoFisicoService()
        detalhes = service.buscar_detalhes_picking(picking_id)

        return jsonify(detalhes)

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do picking {picking_id}: {e}")
        return jsonify({'error': str(e)}), 500


@recebimento_fisico_bp.route('/salvar', methods=['POST'])
def api_salvar():
    """
    API: Salvar recebimento localmente e enfileirar job RQ.

    Body JSON:
        picking_id, picking_name, purchase_order_id, purchase_order_name,
        partner_id, partner_name, company_id, numero_nf, validacao_id,
        lotes: [{product_id, product_name, move_line_id, move_id,
                 lote_nome, quantidade, data_validade, tracking}],
        quality_checks: [{check_id, point_id, product_id, test_type,
                          titulo, resultado, valor_medido, unidade,
                          tolerancia_min, tolerancia_max}]
    """
    try:
        from app.recebimento.services.recebimento_fisico_service import RecebimentoFisicoService

        dados = request.get_json()
        if not dados:
            return jsonify({'error': 'Body JSON obrigatorio'}), 400

        # Validacoes basicas
        if not dados.get('picking_id'):
            return jsonify({'error': 'picking_id obrigatorio'}), 400
        if not dados.get('company_id'):
            return jsonify({'error': 'company_id obrigatorio'}), 400
        if not dados.get('lotes'):
            return jsonify({'error': 'lotes obrigatorio (pelo menos 1)'}), 400

        # Validar que soma dos lotes = qtd esperada
        service = RecebimentoFisicoService()

        # Agrupar lotes por produto para validacao
        produtos_lotes = {}
        for lote in dados['lotes']:
            pid = lote['product_id']
            if pid not in produtos_lotes:
                produtos_lotes[pid] = {
                    'product_id': pid,
                    'product_name': lote.get('product_name', ''),
                    'qtd_esperada': lote.get('qtd_esperada', 0),
                    'lotes': [],
                }
            produtos_lotes[pid]['lotes'].append({
                'nome': lote['lote_nome'],
                'quantidade': lote['quantidade'],
            })

        valido, erros = service.validar_lotes(list(produtos_lotes.values()))
        if not valido:
            return jsonify({
                'error': 'Validacao de lotes falhou',
                'erros_lotes': erros
            }), 400

        # Salvar + enqueue
        usuario = dados.get('usuario', 'sistema')
        recebimento = service.salvar_recebimento(dados, usuario=usuario)

        return jsonify({
            'success': True,
            'recebimento_id': recebimento.id,
            'status': recebimento.status,
            'job_id': recebimento.job_id,
            'message': (
                f'Recebimento salvo! Picking {recebimento.odoo_picking_name} '
                'sera processado em breve.'
            ),
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao salvar recebimento: {e}")
        return jsonify({'error': str(e)}), 500


@recebimento_fisico_bp.route('/status/listar')
def api_listar_status():
    """
    API: Listar recebimentos com status.

    Query params:
        company_id: Filtrar por empresa
        status: Filtrar por status (pendente, processando, processado, erro)
        limit: Limite de resultados (padrao 50)
    """
    try:
        from app.recebimento.services.recebimento_fisico_service import RecebimentoFisicoService

        company_id = request.args.get('company_id', type=int)
        status_filtro = request.args.get('status', '').strip() or None
        limit = request.args.get('limit', 50, type=int)

        service = RecebimentoFisicoService()
        recebimentos = service.listar_recebimentos(
            company_id=company_id,
            status=status_filtro,
            limit=limit,
        )

        return jsonify({
            'recebimentos': recebimentos,
            'total': len(recebimentos),
        })

    except Exception as e:
        logger.error(f"Erro ao listar recebimentos: {e}")
        return jsonify({'error': str(e)}), 500


@recebimento_fisico_bp.route('/status/<int:recebimento_id>/retry', methods=['POST'])
def api_retry(recebimento_id):
    """API: Retentar processamento de recebimento com erro."""
    try:
        from app.recebimento.services.recebimento_fisico_service import RecebimentoFisicoService

        service = RecebimentoFisicoService()
        recebimento = service.retry_recebimento(recebimento_id)

        return jsonify({
            'success': True,
            'recebimento_id': recebimento.id,
            'status': recebimento.status,
            'tentativas': recebimento.tentativas,
            'message': 'Recebimento re-enfileirado para processamento.',
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao retentar recebimento {recebimento_id}: {e}")
        return jsonify({'error': str(e)}), 500


@recebimento_fisico_bp.route('/status/<int:recebimento_id>/consultar-odoo')
def api_consultar_odoo(recebimento_id):
    """API: Consultar estado real do picking no Odoo."""
    try:
        from app.recebimento.services.recebimento_fisico_service import RecebimentoFisicoService

        service = RecebimentoFisicoService()
        resultado = service.consultar_status_odoo(recebimento_id)

        return jsonify(resultado)

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Erro ao consultar Odoo para recebimento {recebimento_id}: {e}")
        return jsonify({'error': str(e)}), 500


@recebimento_fisico_bp.route('/sincronizar', methods=['POST'])
def api_sincronizar_manual():
    """
    API: Executar sincronizacao manual de pickings com periodo customizado.

    Body JSON:
        data_de: Data inicial (formato YYYY-MM-DD)
        data_ate: Data final (formato YYYY-MM-DD)
    """
    try:
        from app.recebimento.services.picking_recebimento_sync_service import PickingRecebimentoSyncService

        dados = request.get_json()
        if not dados:
            return jsonify({'error': 'Body JSON obrigatorio'}), 400

        data_de = dados.get('data_de')
        data_ate = dados.get('data_ate')

        if not data_de or not data_ate:
            return jsonify({'error': 'data_de e data_ate obrigatorios'}), 400

        # Validar formato de datas
        from datetime import datetime
        try:
            datetime.strptime(data_de, '%Y-%m-%d')
            datetime.strptime(data_ate, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Formato de data invalido. Use YYYY-MM-DD'}), 400

        # Validar que data_de <= data_ate
        if data_de > data_ate:
            return jsonify({'error': 'data_de deve ser menor ou igual a data_ate'}), 400

        # Validar periodo maximo (90 dias)
        from datetime import timedelta
        dt_de = datetime.strptime(data_de, '%Y-%m-%d')
        dt_ate = datetime.strptime(data_ate, '%Y-%m-%d')
        if (dt_ate - dt_de).days > 90:
            return jsonify({'error': 'Periodo maximo de 90 dias'}), 400

        # Executar sincronizacao
        service = PickingRecebimentoSyncService()
        resultado = service.sincronizar_por_periodo(data_de, data_ate)

        if resultado.get('sucesso'):
            return jsonify({
                'success': True,
                'novos': resultado.get('novos', 0),
                'atualizados': resultado.get('atualizados', 0),
                'tempo_execucao': round(resultado.get('tempo_execucao', 0), 2),
                'message': (
                    f"Sincronizacao concluida: {resultado.get('novos', 0)} novos, "
                    f"{resultado.get('atualizados', 0)} atualizados"
                ),
            })
        else:
            return jsonify({
                'success': False,
                'error': resultado.get('erro', 'Erro desconhecido'),
            }), 500

    except Exception as e:
        logger.error(f"Erro na sincronizacao manual: {e}")
        return jsonify({'error': str(e)}), 500

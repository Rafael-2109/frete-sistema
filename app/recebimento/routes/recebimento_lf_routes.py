"""
Rotas para Recebimento LF (La Famiglia -> Nacom Goya)
=======================================================

Views (Telas HTML):
    GET /recebimento/lf/           -> Tela principal (selecao NF + preenchimento lotes)
    GET /recebimento/lf/status     -> Tela de status/progresso

APIs:
    GET  /recebimento/lf/dfes                   -> Lista DFes da LF disponiveis
    GET  /recebimento/lf/dfe/<id>/detalhes      -> Linhas do DFe separadas por CFOP
    POST /recebimento/lf/salvar                 -> Salvar recebimento + enqueue job
    GET  /recebimento/lf/status/listar          -> Listar recebimentos com status
    GET  /recebimento/lf/status/<id>/progresso  -> Progresso via Redis
    POST /recebimento/lf/status/<id>/retry      -> Retry de recebimento com erro
"""

from flask import Blueprint, render_template, request, jsonify
import logging
import json
import os

logger = logging.getLogger(__name__)

recebimento_lf_bp = Blueprint(
    'recebimento_lf_views',
    __name__,
    url_prefix='/recebimento/lf'
)


# =====================================================
# VIEWS (Telas HTML)
# =====================================================


@recebimento_lf_bp.route('/')
def index():
    """Tela principal de Recebimento LF (selecao NF + preenchimento lotes)."""
    return render_template('recebimento/recebimento_lf.html')


@recebimento_lf_bp.route('/status')
def status():
    """Tela de status dos recebimentos LF."""
    return render_template('recebimento/status_recebimento_lf.html')


# =====================================================
# APIs
# =====================================================


@recebimento_lf_bp.route('/dfes')
def api_dfes():
    """
    API: Lista DFes da LF disponiveis para recebimento.

    Query params:
        minutos: Janela temporal em minutos (default 60)
        data_inicio: Data inicio do range (YYYY-MM-DD). Se presente, ignora minutos.
        data_fim: Data fim do range (YYYY-MM-DD). Se presente, ignora minutos.

    Retorna DFes emitidos pela La Famiglia (CNPJ 18467441000163)
    para Nacom Goya FB (company_id=1) que nao foram processados.
    """
    try:
        from app.recebimento.services.recebimento_lf_service import RecebimentoLfService

        minutos = request.args.get('minutos', 60, type=int)
        data_inicio = request.args.get('data_inicio', '').strip() or None
        data_fim = request.args.get('data_fim', '').strip() or None

        service = RecebimentoLfService()
        resultado = service.buscar_dfes_lf_disponiveis(
            minutos=minutos,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro ao buscar DFes LF: {e}")
        return jsonify({'error': str(e)}), 500


@recebimento_lf_bp.route('/dfe/<int:dfe_id>/detalhes')
def api_detalhes_dfe(dfe_id):
    """
    API: Buscar detalhes de um DFe da LF.

    Retorna linhas separadas por CFOP:
    - linhas_manuais (CFOP != 1902): usuario preenche lote + quantidade
    - linhas_auto (CFOP = 1902): lotes copiados do faturamento da LF
    """
    try:
        from app.recebimento.services.recebimento_lf_service import RecebimentoLfService

        service = RecebimentoLfService()
        detalhes = service.buscar_detalhes_dfe(dfe_id)

        return jsonify(detalhes)

    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes DFe {dfe_id}: {e}")
        return jsonify({'error': str(e)}), 500


@recebimento_lf_bp.route('/salvar', methods=['POST'])
def api_salvar():
    """
    API: Salvar recebimento LF localmente e enfileirar job RQ.

    Body JSON:
        dfe_id: ID do DFe no Odoo (obrigatorio)
        numero_nf: Numero da NF
        chave_nfe: Chave de acesso da NF-e
        cnpj_emitente: CNPJ do emitente (default LF)
        lotes_manuais: [{product_id, product_name, dfe_line_id, cfop,
                         lote_nome, quantidade, data_validade, produto_tracking}]
        lotes_auto: [{product_id, product_name, dfe_line_id, cfop,
                      lote_nome, quantidade, data_validade, produto_tracking}]
    """
    try:
        from app.recebimento.services.recebimento_lf_service import RecebimentoLfService

        dados = request.get_json()
        if not dados:
            return jsonify({'error': 'Body JSON obrigatorio'}), 400

        # Validacoes basicas
        if not dados.get('dfe_id'):
            return jsonify({'error': 'dfe_id obrigatorio'}), 400

        if not dados.get('lotes_manuais') and not dados.get('lotes_auto'):
            return jsonify({'error': 'Deve haver pelo menos 1 lote (manual ou auto)'}), 400

        # Validar lotes manuais
        for lote in dados.get('lotes_manuais', []):
            if not lote.get('product_id'):
                return jsonify({'error': 'product_id obrigatorio em todos os lotes manuais'}), 400
            if not lote.get('lote_nome'):
                return jsonify({'error': f"lote_nome obrigatorio para produto {lote.get('product_name', lote['product_id'])}"}), 400
            try:
                qtd = float(lote.get('quantidade', 0))
                if qtd <= 0:
                    return jsonify({'error': f"quantidade invalida para produto {lote.get('product_name', lote['product_id'])}"}), 400
            except (ValueError, TypeError):
                return jsonify({'error': f"quantidade nao numerica para produto {lote.get('product_name', lote['product_id'])}"}), 400

        # Validar lotes auto
        for lote in dados.get('lotes_auto', []):
            if not lote.get('product_id'):
                return jsonify({'error': 'product_id obrigatorio em todos os lotes auto'}), 400
            try:
                qtd = float(lote.get('quantidade', 0))
                if qtd <= 0:
                    return jsonify({'error': f"quantidade invalida para produto auto {lote.get('product_name', lote['product_id'])}"}), 400
            except (ValueError, TypeError):
                return jsonify({'error': f"quantidade nao numerica para produto auto {lote.get('product_name', lote['product_id'])}"}), 400

        # Salvar + enqueue
        usuario = dados.get('usuario', 'sistema')
        service = RecebimentoLfService()
        recebimento = service.salvar_recebimento(dados, usuario=usuario)

        return jsonify({
            'success': True,
            'recebimento_id': recebimento.id,
            'status': recebimento.status,
            'job_id': recebimento.job_id,
            'message': (
                f'Recebimento LF salvo! NF {recebimento.numero_nf} '
                'sera processada em breve.'
            ),
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao salvar recebimento LF: {e}")
        return jsonify({'error': str(e)}), 500


@recebimento_lf_bp.route('/status/listar')
def api_listar_status():
    """
    API: Listar recebimentos LF com status.

    Query params:
        status: Filtrar por status (pendente, processando, processado, erro)
        limit: Limite de resultados (padrao 50)
    """
    try:
        from app.recebimento.services.recebimento_lf_service import RecebimentoLfService

        status_filtro = request.args.get('status', '').strip() or None
        limit = request.args.get('limit', 50, type=int)

        service = RecebimentoLfService()
        recebimentos = service.listar_recebimentos(
            status=status_filtro,
            limit=limit,
        )

        return jsonify({
            'recebimentos': recebimentos,
            'total': len(recebimentos),
        })

    except Exception as e:
        logger.error(f"Erro ao listar recebimentos LF: {e}")
        return jsonify({'error': str(e)}), 500


@recebimento_lf_bp.route('/status/<int:recebimento_id>/progresso')
def api_progresso(recebimento_id):
    """
    API: Consultar progresso do processamento via Redis.

    Retorna fase, etapa, percentual e mensagem de progresso.
    Usado pelo polling JS a cada 3 segundos na tela de status.
    """
    try:
        from redis import Redis

        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_conn = Redis.from_url(redis_url)

        chave = f'recebimento_lf_progresso:{recebimento_id}'
        dados = redis_conn.get(chave)

        if dados:
            progresso = json.loads(dados)
            return jsonify(progresso)
        else:
            # Sem dados no Redis — verificar no banco
            from app.recebimento.models import RecebimentoLf
            recebimento = RecebimentoLf.query.get(recebimento_id)
            if not recebimento:
                return jsonify({'error': 'Recebimento nao encontrado'}), 404

            return jsonify({
                'recebimento_id': recebimento_id,
                'fase': recebimento.fase_atual,
                'etapa': recebimento.etapa_atual,
                'total_etapas': recebimento.total_etapas,
                'percentual': int((recebimento.etapa_atual / recebimento.total_etapas) * 100) if recebimento.total_etapas > 0 else 0,
                'mensagem': recebimento.erro_mensagem or f'Fase {recebimento.fase_atual}/6',
                'status': recebimento.status,
                'transfer_status': recebimento.transfer_status,
            })

    except Exception as e:
        logger.error(f"Erro ao consultar progresso {recebimento_id}: {e}")
        return jsonify({'error': str(e)}), 500


@recebimento_lf_bp.route('/status/<int:recebimento_id>/retry', methods=['POST'])
def api_retry(recebimento_id):
    """API: Retentar processamento de recebimento LF com erro."""
    try:
        from app.recebimento.services.recebimento_lf_service import RecebimentoLfService

        service = RecebimentoLfService()
        recebimento = service.retry_recebimento(recebimento_id)

        return jsonify({
            'success': True,
            'recebimento_id': recebimento.id,
            'status': recebimento.status,
            'tentativas': recebimento.tentativas,
            'message': 'Recebimento LF re-enfileirado para processamento.',
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao retentar recebimento LF {recebimento_id}: {e}")
        return jsonify({'error': str(e)}), 500


@recebimento_lf_bp.route('/status/<int:recebimento_id>/retry-transfer', methods=['POST'])
def api_retry_transfer(recebimento_id):
    """
    API: Retentar apenas a fase de transferencia FB -> CD.

    Pre-requisito: recebimento com status='processado' e transfer_status='erro'.
    """
    try:
        from app.recebimento.services.recebimento_lf_service import RecebimentoLfService

        service = RecebimentoLfService()
        recebimento = service.retry_transfer(recebimento_id)

        return jsonify({
            'success': True,
            'recebimento_id': recebimento.id,
            'transfer_status': recebimento.transfer_status,
            'message': 'Transferencia FB->CD re-enfileirada para processamento.',
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao retry transfer {recebimento_id}: {e}")
        return jsonify({'error': str(e)}), 500

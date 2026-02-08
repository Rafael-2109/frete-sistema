# -*- coding: utf-8 -*-
"""
Rotas de Correção de Datas - NFs de Crédito
============================================

Endpoints:
- /correcao-datas/ - Tela principal
- /correcao-datas/api/listar - Lista registros
- /correcao-datas/api/diagnosticar - Executa diagnóstico
- /correcao-datas/api/corrigir - Executa correção
- /correcao-datas/api/exportar - Exporta Excel

Autor: Sistema de Fretes - Análise CIEL IT
Data: 11/12/2025
"""

from datetime import datetime
from flask import render_template, request, jsonify, session, send_file
from flask_login import login_required, current_user
import io
from app.utils.timezone import agora_utc_naive
import logging

from app.financeiro.routes import financeiro_bp
from app.financeiro.services.correcao_datas_service import CorrecaoDatasService

logger = logging.getLogger(__name__)


# =============================================================================
# TELA PRINCIPAL
# =============================================================================

@financeiro_bp.route('/correcao-datas/')
@login_required
def correcao_datas_index():
    """Tela principal de correção de datas"""
    service = CorrecaoDatasService()
    stats = service.obter_estatisticas()

    return render_template(
        'financeiro/correcao_datas.html',
        stats=stats
    )


# =============================================================================
# APIS
# =============================================================================

@financeiro_bp.route('/correcao-datas/api/listar')
@login_required
def correcao_datas_api_listar():
    """Lista registros com filtros"""
    try:
        status = request.args.get('status')
        mes = request.args.get('mes')
        documento = request.args.get('documento')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))

        service = CorrecaoDatasService()

        items, total = service.listar_todos(
            status=status,
            mes=mes,
            documento=documento,
            page=page,
            per_page=per_page
        )

        return jsonify({
            'sucesso': True,
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        })

    except Exception as e:
        logger.error(f"Erro ao listar: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@financeiro_bp.route('/correcao-datas/api/estatisticas')
@login_required
def correcao_datas_api_estatisticas():
    """Retorna estatísticas"""
    try:
        service = CorrecaoDatasService()
        stats = service.obter_estatisticas()
        return jsonify({'sucesso': True, 'stats': stats})
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@financeiro_bp.route('/correcao-datas/api/resetar-erros', methods=['POST'])
@login_required
def correcao_datas_api_resetar_erros():
    """Reseta registros com erro para pendente"""
    try:
        service = CorrecaoDatasService()
        resultado = service.resetar_erros()
        return jsonify(resultado)
    except Exception as e:
        logger.error(f"Erro ao resetar: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@financeiro_bp.route('/correcao-datas/api/diagnosticar', methods=['POST'])
@login_required
def correcao_datas_api_diagnosticar():
    """Executa diagnóstico - busca NFs com problema no Odoo"""
    try:
        data = request.get_json() or {}
        data_inicio = None
        data_fim = None

        if data.get('data_inicio'):
            data_inicio = datetime.strptime(data['data_inicio'], '%Y-%m-%d').date()
        if data.get('data_fim'):
            data_fim = datetime.strptime(data['data_fim'], '%Y-%m-%d').date()

        service = CorrecaoDatasService()
        resultado = service.diagnosticar(data_inicio, data_fim)

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro no diagnóstico: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@financeiro_bp.route('/correcao-datas/api/corrigir', methods=['POST'])
@login_required
def correcao_datas_api_corrigir():
    """Executa correção dos documentos selecionados"""
    try:
        data = request.get_json()
        if not data or not data.get('ids'):
            return jsonify({'sucesso': False, 'erro': 'IDs não informados'}), 400

        ids = data['ids']
        usuario = current_user.nome if current_user else 'sistema'

        service = CorrecaoDatasService()
        resultado = service.corrigir(ids, usuario)

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro na correção: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@financeiro_bp.route('/correcao-datas/api/exportar')
@login_required
def correcao_datas_api_exportar():
    """Exporta registros para Excel"""
    try:
        import pandas as pd
        from app.financeiro.models_correcao_datas import CorrecaoDataNFCredito
        from app import db

        status = request.args.get('status')

        query = CorrecaoDataNFCredito.query

        if status:
            query = query.filter(CorrecaoDataNFCredito.status == status)

        query = query.order_by(CorrecaoDataNFCredito.data_emissao.desc())
        items = query.all()

        # Preparar dados para Excel
        dados = []
        for item in items:
            dados.append({
                'ID Odoo': item.odoo_move_id,
                'Documento': item.nome_documento,
                'NF': item.numero_nf,
                'Parceiro': item.nome_parceiro,
                'Data Emissão': item.data_emissao,
                'Data Lançamento (Antes)': item.data_lancamento_antes,
                'Data Linhas (Antes)': item.data_lancamento_linhas_antes,
                'Data Correta': item.data_correta,
                'Data Lançamento (Depois)': item.data_lancamento_depois,
                'Status': item.status,
                'Erro': item.erro_mensagem,
                'Diagnosticado Em': item.diagnosticado_em,
                'Corrigido Em': item.corrigido_em,
                'Corrigido Por': item.corrigido_por
            })

        df = pd.DataFrame(dados)

        # Criar Excel em memória
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Correções')

        output.seek(0)

        # Marcar como exportados
        for item in items:
            item.exportado_em = agora_utc_naive()
        db.session.commit()

        filename = f"correcao_datas_nf_credito_{agora_utc_naive().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Erro na exportação: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

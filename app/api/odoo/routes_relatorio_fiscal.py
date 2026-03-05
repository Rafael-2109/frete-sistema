"""
Rotas API para Relatório Fiscal IBS/CBS
=======================================

Endpoint para geração de relatório fiscal com campos IBS/CBS
da reforma tributária. Integrado com wizard do Odoo.

Autor: Sistema de Fretes
Data: 2026-01-14
"""

from flask import Blueprint, request, send_file, jsonify
from datetime import datetime, timedelta
import tempfile
import os
import logging
from app.utils.timezone import agora_utc_naive
# Configurar logging
logger = logging.getLogger(__name__)

# Definir o blueprint
# Registrado em api_bp que já tem /api/v1, então o path final será:
# /api/v1/relatorio-fiscal/ibscbs
relatorio_fiscal_bp = Blueprint(
    'relatorio_fiscal',
    __name__,
    url_prefix='/relatorio-fiscal'
)


@relatorio_fiscal_bp.route('/ibscbs', methods=['GET', 'POST'])
def gerar_relatorio_ibscbs():
    """
    Gera relatório fiscal com campos IBS/CBS

    Parâmetros (GET query ou POST JSON):
        - data_ini: Data inicial (YYYY-MM-DD)
        - data_fim: Data final (YYYY-MM-DD)
        - tipos: Lista de tipos ['out_invoice', 'in_invoice', etc.]
        - export_excel: bool (default True)
        - export_cfop: bool - agrupar por CFOP

    Retorna:
        - Arquivo Excel para download
        - OU JSON com dados se export_excel=false

    Exemplo de uso:
        GET /api/relatorio-fiscal/ibscbs?data_ini=2026-01-01&data_fim=2026-01-14
        POST /api/relatorio-fiscal/ibscbs
            {"data_ini": "2026-01-01", "data_fim": "2026-01-14"}
    """
    try:
        # Obter parâmetros (GET ou POST)
        if request.method == 'POST':
            params = request.get_json() or {}
        else:
            params = request.args.to_dict()

        # Parâmetros com defaults
        data_ini_str = params.get('data_ini')
        data_fim_str = params.get('data_fim')
        export_excel = params.get('export_excel', 'true').lower() in ['true', '1', 'yes']

        # Tipos de documento
        tipos = params.get('tipos')
        if isinstance(tipos, str):
            tipos = tipos.split(',')
        elif not tipos:
            tipos = None  # Usa default da função

        # Montar lista de tipos baseado nos checkboxes do wizard
        tipos_lista = []
        if params.get('export_saida_nfe', 'true').lower() in ['true', '1']:
            tipos_lista.append('out_invoice')
        if params.get('export_saida_fat', 'true').lower() in ['true', '1']:
            tipos_lista.append('out_invoice')  # Fatura também é out_invoice
        if params.get('export_entrada_nfe', 'true').lower() in ['true', '1']:
            tipos_lista.append('in_invoice')
        if params.get('export_entrada_fat', 'true').lower() in ['true', '1']:
            tipos_lista.append('in_invoice')  # Fatura também é in_invoice
        if params.get('export_saida_nfse', 'false').lower() in ['true', '1']:
            tipos_lista.extend(['out_invoice'])  # NFSe usa mesmo tipo
        if params.get('export_entrada_nfse', 'false').lower() in ['true', '1']:
            tipos_lista.extend(['in_invoice'])

        # Devoluções (fluxo de mercadoria):
        # - out_refund (devolução de venda) = mercadoria ENTRA → Entradas
        # - in_refund (devolução de compra) = mercadoria SAI → Saídas
        if 'in_invoice' in tipos_lista:
            tipos_lista.append('out_refund')
        if 'out_invoice' in tipos_lista:
            tipos_lista.append('in_refund')

        # Remover duplicatas e usar default se vazio
        tipos_lista = list(set(tipos_lista)) if tipos_lista else tipos

        # Calcular datas
        if data_fim_str:
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        else:
            data_fim = agora_utc_naive().date()

        if data_ini_str:
            data_ini = datetime.strptime(data_ini_str, '%Y-%m-%d').date()
        else:
            # Default: últimos 30 dias
            data_ini = data_fim - timedelta(days=30)

        logger.info(f"📊 Gerando relatório IBS/CBS: {data_ini} a {data_fim}")

        # Importar função de geração (evita import circular)
        from scripts.relatorio_fiscal_ibscbs import extrair_relatorio_fiscal_datas

        # Gerar relatório
        arquivo = extrair_relatorio_fiscal_datas(
            data_ini=data_ini,
            data_fim=data_fim,
            tipos=tipos_lista
        )

        if not arquivo:
            return jsonify({
                'success': False,
                'message': 'Nenhum dado encontrado no período especificado'
            }), 404

        if export_excel:
            # Retornar arquivo para download
            nome_arquivo = f"relatorio_fiscal_ibscbs_{data_ini.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.xlsx"
            return send_file(
                arquivo,
                as_attachment=True,
                download_name=nome_arquivo,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            # Retornar JSON com caminho do arquivo
            return jsonify({
                'success': True,
                'message': 'Relatório gerado com sucesso',
                'arquivo': arquivo,
                'periodo': {
                    'data_ini': data_ini.isoformat(),
                    'data_fim': data_fim.isoformat()
                }
            })

    except ValueError as e:
        logger.error(f"Erro de validação: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro de validação: {str(e)}'
        }), 400

    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500


@relatorio_fiscal_bp.route('/ibscbs/info', methods=['GET'])
def info_relatorio():
    """Retorna informações sobre o endpoint do relatório"""
    return jsonify({
        'success': True,
        'endpoint': '/api/relatorio-fiscal/ibscbs',
        'metodos': ['GET', 'POST'],
        'parametros': {
            'data_ini': 'Data inicial (YYYY-MM-DD)',
            'data_fim': 'Data final (YYYY-MM-DD)',
            'export_excel': 'Exportar como Excel (default: true)',
            'export_saida_nfe': 'Incluir NF-e de saída (default: true)',
            'export_entrada_nfe': 'Incluir NF-e de entrada (default: true)',
            'export_saida_fat': 'Incluir faturas de saída (default: true)',
            'export_entrada_fat': 'Incluir faturas de entrada (default: true)',
            'export_saida_nfse': 'Incluir NFS-e de saída (default: false)',
            'export_entrada_nfse': 'Incluir NFS-e de entrada (default: false)',
        },
        'campos_ibscbs': [
            'CST IBS/CBS',
            'Código Class. Trib. IBS/CBS',
            'Nome Class. Trib. IBS/CBS',
            'Base IBS/CBS',
            '% Redução IBS/CBS',
            '% Diferimento IBS/CBS',
            '% IBS UF',
            '% Redução IBS UF',
            'R$ IBS UF',
            '% IBS Município',
            '% Redução IBS Município',
            'R$ IBS Município',
            'R$ IBS Total',
            '% CBS',
            '% Redução CBS',
            'R$ CBS',
            'Total R$ IBS/CBS Cabeçalho'
        ]
    })

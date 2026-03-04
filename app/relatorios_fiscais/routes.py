"""
Rotas do Módulo de Relatórios Fiscais
=====================================

Página web para geração de relatórios fiscais com campos IBS/CBS.

Autor: Sistema de Fretes
Data: 2026-01-14
"""

from flask import render_template, request, send_file, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import logging
from app.utils.timezone import agora_utc_naive

from . import relatorios_fiscais_bp

logger = logging.getLogger(__name__)


@relatorios_fiscais_bp.route('/ibscbs')
@login_required
def pagina_relatorio_ibscbs():
    """
    Página principal do relatório fiscal IBS/CBS

    Exibe formulário com filtros para geração do relatório.
    """
    # Datas padrão: últimos 30 dias
    data_fim = agora_utc_naive().date()
    data_ini = data_fim - timedelta(days=30)

    return render_template(
        'relatorios_fiscais/ibscbs.html',
        data_ini=data_ini.strftime('%Y-%m-%d'),
        data_fim=data_fim.strftime('%Y-%m-%d'),
        titulo='Relatório Documentos Fiscais C/ IBS/CBS'
    )


@relatorios_fiscais_bp.route('/ibscbs/gerar', methods=['POST'])
@login_required
def gerar_relatorio_ibscbs():
    """
    Gera o relatório fiscal IBS/CBS e retorna Excel para download

    Processa os filtros do formulário e gera o arquivo.
    """
    try:
        # Obter parâmetros do formulário
        data_ini_str = request.form.get('data_ini')
        data_fim_str = request.form.get('data_fim')

        # Validar datas
        if not data_ini_str or not data_fim_str:
            flash('Datas inicial e final são obrigatórias', 'error')
            return redirect(url_for('relatorios_fiscais.pagina_relatorio_ibscbs'))

        data_ini = datetime.strptime(data_ini_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()

        if data_ini > data_fim:
            flash('Data inicial não pode ser maior que data final', 'error')
            return redirect(url_for('relatorios_fiscais.pagina_relatorio_ibscbs'))

        # Montar lista de tipos baseado nos checkboxes
        tipos_lista = []

        if request.form.get('export_saida_nfe'):
            tipos_lista.append('out_invoice')
        if request.form.get('export_entrada_nfe'):
            tipos_lista.append('in_invoice')

        # Incluir devoluções se houver saídas ou entradas
        if 'out_invoice' in tipos_lista:
            tipos_lista.append('out_refund')
        if 'in_invoice' in tipos_lista:
            tipos_lista.append('in_refund')

        # Default: todos os tipos se nenhum selecionado
        if not tipos_lista:
            tipos_lista = ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']

        # Opção: incluir NCs em rascunho
        incluir_nc_draft = bool(request.form.get('incluir_nc_draft'))

        logger.info(
            f"📊 Gerando relatório IBS/CBS: {data_ini} a {data_fim} "
            f"| Tipos: {tipos_lista} | NC draft: {incluir_nc_draft} | Usuário: {current_user.nome}"
        )

        # Importar função de geração
        from scripts.relatorio_fiscal_ibscbs import extrair_relatorio_fiscal_datas

        # Gerar relatório
        arquivo = extrair_relatorio_fiscal_datas(
            data_ini=data_ini,
            data_fim=data_fim,
            tipos=tipos_lista,
            incluir_nc_draft=incluir_nc_draft
        )

        if not arquivo:
            flash('Nenhum dado encontrado no período especificado', 'warning')
            return redirect(url_for('relatorios_fiscais.pagina_relatorio_ibscbs'))

        # Retornar arquivo para download
        nome_arquivo = f"relatorio_fiscal_ibscbs_{data_ini.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.xlsx"

        logger.info(f"✅ Relatório gerado: {nome_arquivo}")

        return send_file(
            arquivo,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except ValueError as e:
        logger.error(f"Erro de validação: {e}")
        flash(f'Erro de validação: {str(e)}', 'error')
        return redirect(url_for('relatorios_fiscais.pagina_relatorio_ibscbs'))

    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {e}")
        flash(f'Erro ao gerar relatório: {str(e)}', 'error')
        return redirect(url_for('relatorios_fiscais.pagina_relatorio_ibscbs'))


@relatorios_fiscais_bp.route('/ibscbs/status')
@login_required
def status_conexao_odoo():
    """
    Verifica status da conexão com Odoo

    Endpoint AJAX para verificar se a conexão está funcionando.
    """
    try:
        from app.odoo.utils.connection import get_odoo_connection

        odoo = get_odoo_connection()
        resultado = odoo.test_connection()

        if resultado.get('success'):
            return jsonify({
                'success': True,
                'message': 'Conexão com Odoo OK',
                'version': resultado.get('data', {}).get('version', {}).get('server_version', 'N/A'),
                'database': resultado.get('data', {}).get('database', 'N/A')
            })
        else:
            return jsonify({
                'success': False,
                'message': resultado.get('message', 'Falha na conexão')
            }), 503

    except Exception as e:
        logger.error(f"Erro ao verificar conexão Odoo: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro: {str(e)}'
        }), 500


# ================================================================
# RAZÃO GERAL (General Ledger)
# ================================================================

@relatorios_fiscais_bp.route('/razao-geral')
@login_required
def razao_geral():
    """
    Página principal do relatório Razão Geral.

    Exibe formulário com filtros: período, empresa e conta contábil.
    """
    from app.relatorios_fiscais.services.razao_geral_service import EMPRESAS_RAZAO_GERAL

    # Datas padrão: último mês
    data_fim = agora_utc_naive().date()
    data_ini = data_fim - timedelta(days=30)

    return render_template(
        'relatorios_fiscais/razao_geral.html',
        data_ini=data_ini.strftime('%Y-%m-%d'),
        data_fim=data_fim.strftime('%Y-%m-%d'),
        empresas=EMPRESAS_RAZAO_GERAL,
        titulo='Razão Geral (General Ledger)'
    )


@relatorios_fiscais_bp.route('/razao-geral/gerar', methods=['POST'])
@login_required
def gerar_razao_geral():
    """
    Gera o relatório Razão Geral e retorna Excel para download.

    Recebe filtros do formulário:
    - data_ini / data_fim: período
    - company_ids[]: empresas selecionadas
    - conta_contabil: código parcial da conta (opcional)
    """
    try:
        from app.odoo.utils.connection import get_odoo_connection
        from app.relatorios_fiscais.services.razao_geral_service import (
            buscar_movimentos_razao,
            gerar_excel_razao
        )

        # Obter parâmetros do formulário
        data_ini_str = request.form.get('data_ini')
        data_fim_str = request.form.get('data_fim')
        company_ids_str = request.form.getlist('company_ids')
        conta_contabil = request.form.get('conta_contabil', '').strip()

        # Validar datas
        if not data_ini_str or not data_fim_str:
            flash('Datas inicial e final são obrigatórias', 'error')
            return redirect(url_for('relatorios_fiscais.razao_geral'))

        data_ini = datetime.strptime(data_ini_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()

        if data_ini > data_fim:
            flash('Data inicial não pode ser maior que data final', 'error')
            return redirect(url_for('relatorios_fiscais.razao_geral'))

        # Validar empresas
        company_ids = [int(cid) for cid in company_ids_str if cid.isdigit()]
        if not company_ids:
            flash('Selecione pelo menos uma empresa', 'error')
            return redirect(url_for('relatorios_fiscais.razao_geral'))

        logger.info(
            f"📊 Gerando Razão Geral: {data_ini} a {data_fim} "
            f"| Empresas: {company_ids} | Conta: {conta_contabil or 'Todas'} "
            f"| Usuário: {current_user.nome}"
        )

        # Conectar ao Odoo
        connection = get_odoo_connection()
        if not connection.authenticate():
            flash('Falha na conexão com o Odoo. Tente novamente.', 'error')
            return redirect(url_for('relatorios_fiscais.razao_geral'))

        # Buscar movimentos (ID-cursor + transformacao inline)
        dados_agrupados, contas_info, saldos_iniciais, total_registros = buscar_movimentos_razao(
            connection,
            data_ini=data_ini_str,
            data_fim=data_fim_str,
            company_ids=company_ids,
            conta_filter=conta_contabil if conta_contabil else None
        )

        if not total_registros:
            flash('Nenhum dado encontrado para os filtros selecionados', 'warning')
            return redirect(url_for('relatorios_fiscais.razao_geral'))

        # Gerar Excel (xlsxwriter constant_memory)
        excel_buffer = gerar_excel_razao(
            dados_agrupados, contas_info, saldos_iniciais,
            data_ini=data_ini_str, data_fim=data_fim_str, company_ids=company_ids
        )

        # Retornar arquivo para download
        nome_arquivo = f"razao_geral_{data_ini.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.xlsx"

        logger.info(f"✅ Razão Geral gerado: {nome_arquivo} ({total_registros} linhas)")

        return send_file(
            excel_buffer,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except ValueError as e:
        logger.error(f"Erro de validação no Razão Geral: {e}")
        flash(f'Erro de validação: {str(e)}', 'error')
        return redirect(url_for('relatorios_fiscais.razao_geral'))

    except Exception as e:
        logger.error(f"Erro ao gerar Razão Geral: {e}")
        flash(f'Erro ao gerar relatório: {str(e)}', 'error')
        return redirect(url_for('relatorios_fiscais.razao_geral'))

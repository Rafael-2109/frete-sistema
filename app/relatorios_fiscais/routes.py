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
from app.financeiro.routes.dashboard import requires_financeiro

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

        # Devoluções (fluxo de mercadoria):
        # - out_refund (devolução de venda) = mercadoria ENTRA → Entradas
        # - in_refund (devolução de compra) = mercadoria SAI → Saídas
        if 'in_invoice' in tipos_lista:
            tipos_lista.append('out_refund')
        if 'out_invoice' in tipos_lista:
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


# ================================================================
# SPED ECD CENTRALIZADO (NACOM GOYA — 3 filiais consolidadas)
# ================================================================

@relatorios_fiscais_bp.route('/sped-ecd')
@login_required
@requires_financeiro
def sped_ecd():
    """
    Pagina principal do SPED ECD Centralizado.
    Form com filtros: periodo (datas livres) + dados signatarios.
    """
    from app.relatorios_fiscais.services.sped_ecd_constantes import (
        CONTADOR_NOME, CONTADOR_CPF, CONTADOR_EMAIL, CONTADOR_CRC, CONTADOR_NUM_SEQ_CRC,
        SOCIO_NOME, SOCIO_CPF, QUALIFICACOES_J930,
    )

    # Datas padrao: ano calendario corrente
    hoje = agora_utc_naive().date()
    data_fim = hoje
    data_ini = hoje.replace(month=1, day=1)

    return render_template(
        'relatorios_fiscais/sped_ecd.html',
        data_ini=data_ini.strftime('%Y-%m-%d'),
        data_fim=data_fim.strftime('%Y-%m-%d'),
        contador_nome=CONTADOR_NOME,
        contador_cpf=CONTADOR_CPF,                           # V1.2: fixo
        contador_email=CONTADOR_EMAIL,                       # V1.2: fixo
        contador_crc=CONTADOR_CRC,
        contador_num_seq=CONTADOR_NUM_SEQ_CRC,
        socio_nome=SOCIO_NOME,
        socio_cpf=SOCIO_CPF,
        qualificacoes=QUALIFICACOES_J930,
        titulo='SPED ECD Centralizado (NACOM GOYA — 3 filiais)'
    )


@relatorios_fiscais_bp.route('/sped-ecd/gerar', methods=['POST'])
@login_required
@requires_financeiro
def gerar_sped_ecd():
    """
    Enfileira job RQ para geracao assincrona do SPED ECD.
    Retorna JSON com job_id para o frontend fazer polling.
    """
    try:
        from app.portal.workers import enqueue_job
        from app.relatorios_fiscais.workers.sped_ecd_worker import gerar_sped_ecd_async
        from app.relatorios_fiscais.services.sped_ecd_constantes import (
            QUEUE_NAME, JOB_TIMEOUT,
        )

        # Obter parametros do form (V1.2: CPF e email vem das constantes, nao do form)
        data_ini_str = (request.form.get('data_ini') or '').strip()
        data_fim_str = (request.form.get('data_fim') or '').strip()
        qualif_socio = (request.form.get('qualif_socio') or '').strip()
        notas_explicativas = (request.form.get('notas_explicativas') or '').strip()

        # Validacoes
        if not data_ini_str or not data_fim_str:
            return jsonify({'success': False, 'error': 'Datas inicial e final sao obrigatorias'}), 400

        if not qualif_socio:
            return jsonify({'success': False, 'error': 'Qualificacao do socio e obrigatoria'}), 400

        # Validar datas
        try:
            data_ini = datetime.strptime(data_ini_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Formato de data invalido (YYYY-MM-DD)'}), 400

        if data_ini > data_fim:
            return jsonify({'success': False, 'error': 'Data inicial nao pode ser maior que data final'}), 400

        # Limite Receita: ECD a partir de 2010
        if data_ini.year < 2010:
            return jsonify({'success': False, 'error': 'ECD valido apenas a partir de 2010'}), 400

        logger.info(
            f'[SPED ECD] Enfileirando job: {data_ini} a {data_fim} | '
            f'Usuario: {current_user.nome}'
        )

        # Enfileirar job RQ (mitigacao R4 — assincrono, sem timeout HTTP)
        # V1.2: cpf_contador e email_contato vem das constantes (sped_ecd_constantes.py)
        job = enqueue_job(
            gerar_sped_ecd_async,
            data_ini.strftime('%Y-%m-%d'),
            data_fim.strftime('%Y-%m-%d'),
            qualif_socio,
            current_user.id,
            current_user.nome,
            notas_explicativas,
            queue_name=QUEUE_NAME,
            timeout=JOB_TIMEOUT,
        )

        return jsonify({
            'success': True,
            'job_id': job.id,
            'status_url': url_for('relatorios_fiscais.sped_ecd_status', job_id=job.id),
            'progress_url': url_for('relatorios_fiscais.sped_ecd_progress', job_id=job.id),
        })

    except Exception as e:
        logger.error(f'[SPED ECD] Erro ao enfileirar job: {e}', exc_info=True)
        return jsonify({'success': False, 'error': f'Erro: {str(e)[:200]}'}), 500


@relatorios_fiscais_bp.route('/sped-ecd/status/<job_id>')
@login_required
@requires_financeiro
def sped_ecd_status(job_id):
    """
    Endpoint AJAX de polling — retorna progresso do job.
    Frontend chama a cada 3-5s ate status='concluido' ou 'erro'.
    """
    try:
        from app.relatorios_fiscais.workers.sped_ecd_worker import obter_progresso_sped

        progresso = obter_progresso_sped(job_id)
        if not progresso:
            return jsonify({
                'success': False,
                'status': 'unknown',
                'error': 'Job nao encontrado ou expirado'
            }), 404

        # Se concluido (com ou sem erros de validacao), gerar URL de download.
        # 'concluido_com_erros' indica que o arquivo foi gerado e uploadado para S3 mas
        # falhou validacao pre-PVA — usuario ainda precisa baixar para investigar/corrigir.
        status_atual = progresso.get('status')
        if status_atual in ('concluido', 'concluido_com_erros') and progresso.get('s3_key'):
            progresso['download_url'] = url_for(
                'relatorios_fiscais.sped_ecd_download', job_id=job_id
            )

        return jsonify({'success': True, 'progresso': progresso})

    except Exception as e:
        logger.error(f'[SPED ECD] Erro ao obter status {job_id}: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@relatorios_fiscais_bp.route('/sped-ecd/download/<job_id>')
@login_required
@requires_financeiro
def sped_ecd_download(job_id):
    """
    Faz download do arquivo SPED gerado.
    - Se S3 ativo: redireciona para presigned URL
    - Se local: send_file direto
    """
    try:
        from app.relatorios_fiscais.workers.sped_ecd_worker import obter_progresso_sped
        from app.relatorios_fiscais.services.sped_ecd_service import gerar_presigned_url_sped

        progresso = obter_progresso_sped(job_id)
        # Aceitar tambem 'concluido_com_erros' — arquivo foi gerado e uploadado mesmo
        # reprovando validacao pre-PVA; usuario precisa baixar para investigar/corrigir.
        if not progresso or progresso.get('status') not in ('concluido', 'concluido_com_erros'):
            flash('Arquivo ainda nao disponivel ou job expirado', 'warning')
            return redirect(url_for('relatorios_fiscais.sped_ecd'))

        s3_key = progresso.get('s3_key')
        if not s3_key:
            flash('Arquivo nao encontrado', 'error')
            return redirect(url_for('relatorios_fiscais.sped_ecd'))

        # Tentar presigned URL (S3)
        presigned = gerar_presigned_url_sped(s3_key, expires_in=3600)
        if presigned:
            return redirect(presigned)

        # Fallback: arquivo local
        import os
        if os.path.exists(s3_key):
            return send_file(
                s3_key,
                as_attachment=True,
                download_name=os.path.basename(s3_key),
                mimetype='application/octet-stream',
            )

        flash('Arquivo nao encontrado em storage', 'error')
        return redirect(url_for('relatorios_fiscais.sped_ecd'))

    except Exception as e:
        logger.error(f'[SPED ECD] Erro ao baixar {job_id}: {e}', exc_info=True)
        flash(f'Erro ao baixar arquivo: {str(e)[:200]}', 'error')
        return redirect(url_for('relatorios_fiscais.sped_ecd'))


@relatorios_fiscais_bp.route('/sped-ecd/progress/<job_id>')
@login_required
@requires_financeiro
def sped_ecd_progress(job_id):
    """
    Pagina de progresso — usuario eh redirecionado aqui apos enfileirar job.
    Faz polling em /status/<job_id> e exibe progresso visual.
    """
    return render_template(
        'relatorios_fiscais/sped_ecd_progress.html',
        job_id=job_id,
        titulo='Gerando SPED ECD Centralizado'
    )


@relatorios_fiscais_bp.route('/sped-ecd/historico')
@login_required
@requires_financeiro
def sped_ecd_historico():
    """
    Lista historico de SPED ECDs gerados pelo usuario (S3).
    Permite re-download de arquivos antigos.
    """
    try:
        from app.relatorios_fiscais.services.sped_ecd_service import listar_historico_sped
        arquivos = listar_historico_sped(current_user.id, limite=50)
        return render_template(
            'relatorios_fiscais/sped_ecd_historico.html',
            arquivos=arquivos,
            titulo='Historico de SPED ECD Gerados'
        )
    except Exception as e:
        logger.error(f'[SPED ECD] Erro listar historico: {e}', exc_info=True)
        flash(f'Erro ao listar historico: {str(e)[:200]}', 'error')
        return redirect(url_for('relatorios_fiscais.sped_ecd'))


@relatorios_fiscais_bp.route('/sped-ecd/download-direto')
@login_required
@requires_financeiro
def sped_ecd_download_direto():
    """
    Download direto de arquivo SPED por s3_key (querystring ?s3_key=...).
    Usado pela tela de historico.
    """
    s3_key = (request.args.get('s3_key') or '').strip()
    if not s3_key:
        flash('S3 key nao informado', 'error')
        return redirect(url_for('relatorios_fiscais.sped_ecd_historico'))

    # Validar que s3_key pertence ao usuario logado (seguranca)
    # Mitigacao code-review HIGH #7: bloquear path traversal local
    expected_prefix = f'sped_ecd/user_{current_user.id}/'
    is_s3 = s3_key.startswith(expected_prefix)
    is_local = s3_key.startswith('/tmp/sped_ecd_')

    if is_local:
        # Validar realpath para evitar /tmp/sped_ecd_../../etc/passwd
        import os
        real = os.path.realpath(s3_key)
        if not real.startswith('/tmp/') or '..' in s3_key:
            logger.warning(f'[SPED ECD] Path traversal blocked user {current_user.id}: {s3_key}')
            flash('Path invalido', 'error')
            return redirect(url_for('relatorios_fiscais.sped_ecd_historico'))

    if not (is_s3 or is_local):
        logger.warning(f'[SPED ECD] Tentativa download nao autorizado por user {current_user.id}: {s3_key}')
        flash('Arquivo nao pertence ao seu usuario', 'error')
        return redirect(url_for('relatorios_fiscais.sped_ecd_historico'))

    try:
        from app.relatorios_fiscais.services.sped_ecd_service import gerar_presigned_url_sped
        presigned = gerar_presigned_url_sped(s3_key, expires_in=3600)
        if presigned:
            return redirect(presigned)

        # Fallback local
        import os
        if os.path.exists(s3_key):
            return send_file(
                s3_key,
                as_attachment=True,
                download_name=os.path.basename(s3_key),
                mimetype='application/octet-stream',
            )

        flash('Arquivo nao encontrado em storage', 'error')
        return redirect(url_for('relatorios_fiscais.sped_ecd_historico'))

    except Exception as e:
        logger.error(f'[SPED ECD] Erro download direto: {e}', exc_info=True)
        flash(f'Erro: {str(e)[:200]}', 'error')
        return redirect(url_for('relatorios_fiscais.sped_ecd_historico'))

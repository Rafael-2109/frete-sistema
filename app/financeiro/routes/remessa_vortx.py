# -*- coding: utf-8 -*-
"""
Rotas de Remessa VORTX (CNAB 400)
==================================

Geracao de remessa de cobranca escritural para banco VORTX (310).
Fluxo: buscar titulos no Odoo -> selecionar -> gerar CNAB 400 -> injetar no Odoo.

Rotas:
- /remessa-vortx              -> Historico de remessas
- /remessa-vortx/titulos      -> Lista titulos pendentes (Odoo)
- /remessa-vortx/gerar        -> Gerar remessa (POST)
- /remessa-vortx/<id>/retomar -> Retomar injecao em falha (POST)
- /remessa-vortx/<id>/download -> Download arquivo .rem
"""

import logging
from io import BytesIO

from flask import render_template, request, flash, redirect, url_for, send_file, abort
from flask_login import login_required, current_user

from app import db
from app.utils.timezone import agora_utc_naive
from app.financeiro.routes import financeiro_bp
from app.utils.auth_decorators import require_remessa_vortx

logger = logging.getLogger(__name__)


# =============================================================================
# HISTORICO
# =============================================================================

@financeiro_bp.route('/remessa-vortx')
@login_required
@require_remessa_vortx()
def remessa_vortx_historico():
    """Lista historico de remessas VORTX geradas."""
    from app.financeiro.models import RemessaVortxCache

    remessas = (
        RemessaVortxCache.query
        .order_by(RemessaVortxCache.id.desc())
        .limit(50)
        .all()
    )
    return render_template(
        'financeiro/remessa_vortx/historico.html',
        remessas=remessas,
    )


# =============================================================================
# LISTAR TITULOS PENDENTES
# =============================================================================

@financeiro_bp.route('/remessa-vortx/titulos')
@login_required
@require_remessa_vortx()
def remessa_vortx_titulos():
    """Busca titulos pendentes de remessa no Odoo."""
    from app.odoo.utils.connection import get_odoo_connection
    from app.financeiro.services.remessa_vortx.odoo_injector import buscar_titulos_pendentes
    from app.financeiro.services.remessa_vortx.layout_vortx import TIPO_COBRANCA_IDS, COMPANY_NAMES

    company_id = request.args.get('company_id', 4, type=int)
    titulos = []
    erro = None

    if company_id not in TIPO_COBRANCA_IDS:
        flash(f'Empresa {company_id} nao configurada para VORTX.', 'danger')
    else:
        try:
            odoo = get_odoo_connection()
            odoo.authenticate()
            titulos = buscar_titulos_pendentes(odoo, company_id)
        except Exception as e:
            erro = str(e)[:300]
            logger.error(f'Erro ao buscar titulos VORTX (company={company_id}): {e}')
            flash(f'Erro ao buscar titulos no Odoo: {erro}', 'danger')

    return render_template(
        'financeiro/remessa_vortx/listar_titulos.html',
        titulos=titulos,
        company_id=company_id,
        company_names=COMPANY_NAMES,
        tipo_cobranca_ids=TIPO_COBRANCA_IDS,
        erro=erro,
    )


# =============================================================================
# GERAR REMESSA
# =============================================================================

@financeiro_bp.route('/remessa-vortx/gerar', methods=['POST'])
@login_required
@require_remessa_vortx()
def remessa_vortx_gerar():
    """Gera arquivo CNAB 400 e injeta no Odoo."""
    from app.odoo.utils.connection import get_odoo_connection
    from app.financeiro.models import RemessaVortxCache
    from app.financeiro.services.remessa_vortx.cnab_generator import CnabVortxGenerator
    from app.financeiro.services.remessa_vortx.nosso_numero_service import alocar_nossos_numeros
    from app.financeiro.services.remessa_vortx.odoo_injector import (
        OdooInjector, buscar_dados_sacado,
    )
    from app.financeiro.services.remessa_vortx.layout_vortx import TIPO_COBRANCA_IDS

    company_id = request.form.get('company_id', type=int)
    move_line_ids = request.form.getlist('move_line_ids', type=int)

    # Validacao
    if not move_line_ids:
        flash('Selecione pelo menos um titulo.', 'warning')
        return redirect(url_for('financeiro.remessa_vortx_titulos', company_id=company_id or 4))

    if company_id not in TIPO_COBRANCA_IDS:
        flash(f'Empresa {company_id} nao configurada para VORTX.', 'danger')
        return redirect(url_for('financeiro.remessa_vortx_titulos'))

    try:
        # 1. Buscar dados dos titulos selecionados no Odoo
        odoo = get_odoo_connection()
        odoo.authenticate()

        titulos = odoo.execute_kw(
            'account.move.line', 'read',
            [move_line_ids],
            {'fields': [
                'id', 'move_id', 'name', 'date_maturity', 'debit',
                'partner_id', 'l10n_br_cobranca_nossonumero',
            ]},
        )

        if not titulos:
            flash('Nenhum titulo encontrado no Odoo.', 'danger')
            return redirect(url_for('financeiro.remessa_vortx_titulos', company_id=company_id))

        # 2. Alocar nossos numeros
        nossos_numeros = alocar_nossos_numeros(len(titulos))

        # 3. Gerar CNAB
        agora = agora_utc_naive()
        data_geracao = agora.strftime('%d%m%y')
        gen = CnabVortxGenerator(data_geracao=data_geracao)

        mapa_nn_move_line = {}
        valor_total = 0

        for i, titulo in enumerate(titulos):
            nn = nossos_numeros[i]
            partner_id = titulo['partner_id'][0] if isinstance(titulo.get('partner_id'), (list, tuple)) else titulo.get('partner_id')
            sacado = buscar_dados_sacado(odoo, partner_id) if partner_id else {}

            # Converter vencimento YYYY-MM-DD -> DDMMYY
            dt_venc = titulo.get('date_maturity') or ''
            if dt_venc and len(dt_venc) >= 10:
                vencimento = dt_venc[8:10] + dt_venc[5:7] + dt_venc[2:4]
            else:
                vencimento = '000000'

            # Converter valor para centavos (zfill 13)
            valor_float = float(titulo.get('debit') or 0)
            valor_centavos = str(int(round(valor_float * 100))).zfill(13)
            valor_total += valor_float

            # NF/Documento do nome do move line
            nf_doc = (titulo.get('name') or '')[:10]

            boleto = {
                'nosso_numero': nn['nosso_numero'],
                'nosso_numero_dac': nn['dac'],
                'nosso_antigo': titulo.get('l10n_br_cobranca_nossonumero') or '',
                'nf_documento': nf_doc,
                'vencimento': vencimento,
                'valor_centavos': valor_centavos,
                'emissao': data_geracao,
                'nome_sacado': sacado.get('nome', ''),
                'endereco': sacado.get('endereco', ''),
                'cep_prefixo': sacado.get('cep_prefixo', '00000'),
                'cep_sufixo': sacado.get('cep_sufixo', '000'),
                'cnpj_cpf': sacado.get('cnpj_cpf', ''),
                'tipo_inscricao': sacado.get('tipo_inscricao', '02'),
                'email': sacado.get('email', ''),
            }
            gen.adicionar_boleto(boleto)
            mapa_nn_move_line[str(titulo['id'])] = nn['completo']

        arquivo_bytes = gen.gerar_bytes()
        nome_arquivo = f'REM_VORTX_{agora.strftime("%Y%m%d_%H%M%S")}.rem'

        # 4. Criar registro cache
        cache = RemessaVortxCache(
            etapa='CNAB_GERADO',
            company_id_odoo=company_id,
            tipo_cobranca_id_odoo=TIPO_COBRANCA_IDS[company_id],
            nome_arquivo=nome_arquivo,
            qtd_boletos=len(titulos),
            valor_total=round(valor_total, 2),
            nosso_numero_inicial=nossos_numeros[0]['seq'],
            nosso_numero_final=nossos_numeros[-1]['seq'],
            arquivo_cnab=arquivo_bytes,
            criado_por_id=current_user.id,
        )
        cache.set_move_line_ids_marcados([])
        cache.set_move_line_ids_pendentes(move_line_ids)
        cache.set_mapa_nn_move_line(mapa_nn_move_line)

        db.session.add(cache)
        db.session.commit()

        # 5. Injetar no Odoo (state machine)
        resultado = OdooInjector(cache).executar()

        if resultado.get('success'):
            flash(
                f'Remessa {nome_arquivo} gerada e injetada no Odoo com sucesso! '
                f'{len(titulos)} boleto(s), R$ {valor_total:,.2f}',
                'success',
            )
        else:
            flash(
                f'Remessa {nome_arquivo} gerada, mas injecao parou na etapa '
                f'{resultado.get("etapa")}. Use "Retomar" para continuar. '
                f'Erro: {resultado.get("error", "desconhecido")[:200]}',
                'warning',
            )

    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao gerar remessa VORTX: {e}', exc_info=True)
        flash(f'Erro ao gerar remessa: {str(e)[:300]}', 'danger')

    return redirect(url_for('financeiro.remessa_vortx_historico'))


# =============================================================================
# RETOMAR INJECAO
# =============================================================================

@financeiro_bp.route('/remessa-vortx/<int:cache_id>/retomar', methods=['POST'])
@login_required
@require_remessa_vortx()
def remessa_vortx_retomar(cache_id):
    """Retoma injecao de uma remessa em estado de falha."""
    from app.financeiro.models import RemessaVortxCache
    from app.financeiro.services.remessa_vortx.odoo_injector import OdooInjector

    cache = RemessaVortxCache.query.get_or_404(cache_id)

    if not cache.pode_retomar:
        flash(f'Remessa #{cache_id} nao esta em estado de falha (etapa={cache.etapa}).', 'warning')
        return redirect(url_for('financeiro.remessa_vortx_historico'))

    resultado = OdooInjector(cache).executar()

    if resultado.get('success'):
        flash(f'Remessa #{cache_id} retomada com sucesso! Etapa: {resultado["etapa"]}', 'success')
    else:
        flash(
            f'Falha ao retomar remessa #{cache_id}. '
            f'Etapa: {resultado.get("etapa")}, Erro: {resultado.get("error", "")[:200]}',
            'danger',
        )

    return redirect(url_for('financeiro.remessa_vortx_historico'))


# =============================================================================
# DOWNLOAD ARQUIVO
# =============================================================================

@financeiro_bp.route('/remessa-vortx/<int:cache_id>/download')
@login_required
@require_remessa_vortx()
def remessa_vortx_download(cache_id):
    """Download do arquivo CNAB .rem."""
    from app.financeiro.models import RemessaVortxCache

    cache = RemessaVortxCache.query.get_or_404(cache_id)

    if not cache.arquivo_cnab:
        abort(404, description='Arquivo CNAB nao encontrado neste registro.')

    return send_file(
        BytesIO(cache.arquivo_cnab),
        mimetype='application/octet-stream',
        as_attachment=True,
        download_name=cache.nome_arquivo or f'remessa_vortx_{cache_id}.rem',
    )

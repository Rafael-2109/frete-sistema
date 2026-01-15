"""
Views de Validacao Fiscal - Telas HTML
======================================

Rotas:
- GET /operacional/compras/divergencias - Tela de divergencias
- GET /operacional/compras/primeira-compra - Tela de primeira compra
- GET /operacional/compras/perfis-fiscais - Tela de perfis fiscais
- GET /operacional/compras/ncm-ibscbs - Cadastro de NCMs IBS/CBS
- GET /operacional/compras/pendencias-ibscbs - Pendencias IBS/CBS

Referencia: .claude/references/RECEBIMENTO_MATERIAIS.md
"""

import json
from decimal import Decimal
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

from app.recebimento.models import (
    DivergenciaFiscal,
    CadastroPrimeiraCompra,
    PerfilFiscalProdutoFornecedor,
    NcmIbsCbsValidado,
    PendenciaFiscalIbsCbs
)
from app import db


def _serializar_item_primeira_compra(item):
    """Serializa item de primeira compra para JSON"""
    def to_float(val):
        if val is None:
            return None
        if isinstance(val, Decimal):
            return float(val)
        return val

    def to_str(val):
        if val is None:
            return None
        if isinstance(val, datetime):
            return val.isoformat()
        return str(val)

    return {
        'id': item.id,
        'odoo_dfe_id': item.odoo_dfe_id,
        'odoo_dfe_line_id': item.odoo_dfe_line_id,
        # Dados da NF
        'numero_nf': item.numero_nf,
        'serie_nf': item.serie_nf,
        'chave_nfe': item.chave_nfe,
        # Produto e fornecedor
        'cod_produto': item.cod_produto,
        'nome_produto': item.nome_produto,
        'cnpj_fornecedor': item.cnpj_fornecedor,
        'razao_fornecedor': item.razao_fornecedor,
        # Localizacao do fornecedor
        'uf_fornecedor': item.uf_fornecedor,
        'cidade_fornecedor': item.cidade_fornecedor,
        # Regime tributario (CRT)
        'regime_tributario': item.regime_tributario,
        # Quantidade e valores
        'quantidade': to_float(item.quantidade),
        'unidade_medida': item.unidade_medida,
        'valor_unitario': to_float(item.valor_unitario),
        'valor_total': to_float(item.valor_total),
        # Dados fiscais
        'ncm': item.ncm,
        'cfop': item.cfop,
        'cst_icms': item.cst_icms,
        # ICMS
        'aliquota_icms': to_float(item.aliquota_icms),
        'valor_icms': to_float(item.valor_icms),
        'bc_icms': to_float(item.bc_icms),
        # ICMS ST
        'aliquota_icms_st': to_float(item.aliquota_icms_st),
        'valor_icms_st': to_float(item.valor_icms_st),
        'bc_icms_st': to_float(item.bc_icms_st),
        # IPI
        'aliquota_ipi': to_float(item.aliquota_ipi),
        'valor_ipi': to_float(item.valor_ipi),
        # PIS
        'cst_pis': item.cst_pis,
        'aliquota_pis': to_float(item.aliquota_pis),
        'bc_pis': to_float(item.bc_pis),
        'valor_pis': to_float(item.valor_pis),
        # COFINS
        'cst_cofins': item.cst_cofins,
        'aliquota_cofins': to_float(item.aliquota_cofins),
        'bc_cofins': to_float(item.bc_cofins),
        'valor_cofins': to_float(item.valor_cofins),
        # Status e auditoria
        'status': item.status,
        'validado_por': item.validado_por,
        'validado_em': to_str(item.validado_em),
        'observacao': item.observacao,
        'criado_em': to_str(item.criado_em)
    }

recebimento_views_bp = Blueprint(
    'recebimento_views',
    __name__,
    url_prefix='/operacional/compras',
    template_folder='../../templates/recebimento'
)


# =============================================================================
# TELA 1: DIVERGENCIAS FISCAIS
# =============================================================================

@recebimento_views_bp.route('/divergencias')
@login_required
def divergencias():
    """
    Tela de divergencias fiscais.
    Lista divergencias com filtros e acoes de aprovar/rejeitar.
    """
    # Parametros de filtro
    status = request.args.get('status', '')
    cnpj = request.args.get('cnpj', '')
    data_ini = request.args.get('data_ini', '')
    data_fim = request.args.get('data_fim', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Query base
    query = DivergenciaFiscal.query

    # Aplicar filtros
    if status:
        query = query.filter_by(status=status)
    if cnpj:
        query = query.filter(DivergenciaFiscal.cnpj_fornecedor.ilike(f'%{cnpj}%'))
    if data_ini:
        query = query.filter(DivergenciaFiscal.criado_em >= data_ini)
    if data_fim:
        query = query.filter(DivergenciaFiscal.criado_em <= data_fim)

    # Ordenar por DFE (agrupamento visual) e depois por data decrescente
    paginacao = query.order_by(
        DivergenciaFiscal.odoo_dfe_id.desc(),  # Agrupar por NF
        DivergenciaFiscal.criado_em.desc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # Estatisticas
    stats = {
        'total': DivergenciaFiscal.query.count(),
        'pendente': DivergenciaFiscal.query.filter_by(status='pendente').count(),
        'aprovada': DivergenciaFiscal.query.filter_by(status='aprovada').count(),
        'rejeitada': DivergenciaFiscal.query.filter_by(status='rejeitada').count()
    }

    return render_template(
        'divergencias.html',
        paginacao=paginacao,
        stats=stats,
        filtros={
            'status': status,
            'cnpj': cnpj,
            'data_ini': data_ini,
            'data_fim': data_fim
        },
        opcoes_status=[
            ('', 'Todos'),
            ('pendente', 'Pendente'),
            ('aprovada', 'Aprovada'),
            ('rejeitada', 'Rejeitada')
        ]
    )


# =============================================================================
# TELA 2: PRIMEIRA COMPRA
# =============================================================================

@recebimento_views_bp.route('/primeira-compra')
@login_required
def primeira_compra():
    """
    Tela de primeira compra.
    Lista cadastros de primeira compra pendentes de validacao.
    """
    # Parametros de filtro
    status = request.args.get('status', '')
    cnpj = request.args.get('cnpj', '')
    produto = request.args.get('produto', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Query base
    query = CadastroPrimeiraCompra.query

    # Aplicar filtros
    if status:
        query = query.filter_by(status=status)
    if cnpj:
        query = query.filter(CadastroPrimeiraCompra.cnpj_fornecedor.ilike(f'%{cnpj}%'))
    if produto:
        query = query.filter(
            db.or_(
                CadastroPrimeiraCompra.cod_produto.ilike(f'%{produto}%'),
                CadastroPrimeiraCompra.nome_produto.ilike(f'%{produto}%')
            )
        )

    # Ordenar por DFE (agrupamento visual) e depois por data decrescente
    paginacao = query.order_by(
        CadastroPrimeiraCompra.odoo_dfe_id.desc(),  # Agrupar por NF
        CadastroPrimeiraCompra.criado_em.desc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # Estatisticas
    stats = {
        'pendente': CadastroPrimeiraCompra.query.filter_by(status='pendente').count(),
        'validado': CadastroPrimeiraCompra.query.filter_by(status='validado').count(),
        'rejeitado': CadastroPrimeiraCompra.query.filter_by(status='rejeitado').count()
    }

    # Serializar itens para JSON (usado no modal de detalhes)
    itens_json = json.dumps([
        _serializar_item_primeira_compra(item)
        for item in paginacao.items
    ])

    return render_template(
        'primeira_compra.html',
        paginacao=paginacao,
        stats=stats,
        filtros={
            'status': status,
            'cnpj': cnpj,
            'produto': produto
        },
        itens_json=itens_json
    )


# =============================================================================
# TELA 3: PERFIS FISCAIS
# =============================================================================

@recebimento_views_bp.route('/perfis-fiscais')
@login_required
def perfis_fiscais():
    """
    Tela de perfis fiscais (baselines).
    Lista e consulta perfis cadastrados.
    """
    # Parametros de filtro
    cod_produto = request.args.get('cod_produto', '')
    cnpj = request.args.get('cnpj', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Query base (somente ativos)
    query = PerfilFiscalProdutoFornecedor.query.filter_by(ativo=True)

    # Aplicar filtros
    if cod_produto:
        query = query.filter(
            PerfilFiscalProdutoFornecedor.cod_produto.ilike(f'%{cod_produto}%')
        )
    if cnpj:
        query = query.filter(
            PerfilFiscalProdutoFornecedor.cnpj_fornecedor.ilike(f'%{cnpj}%')
        )

    # Ordenar por data decrescente e paginar
    paginacao = query.order_by(
        PerfilFiscalProdutoFornecedor.criado_em.desc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # Estatisticas
    total_ativos = PerfilFiscalProdutoFornecedor.query.filter_by(ativo=True).count()
    total_auto = PerfilFiscalProdutoFornecedor.query.filter(
        PerfilFiscalProdutoFornecedor.criado_por == 'SISTEMA_AUTO_HISTORICO'
    ).count()
    total_manual = total_ativos - total_auto

    stats = {
        'total': total_ativos,
        'automatico': total_auto,
        'manual': total_manual
    }

    return render_template(
        'perfis_fiscais.html',
        paginacao=paginacao,
        stats=stats,
        filtros={
            'cod_produto': cod_produto,
            'cnpj': cnpj
        }
    )


# =============================================================================
# TELA 4: CADASTRO NCM IBS/CBS (Reforma Tributaria 2026)
# =============================================================================

def _serializar_ncm_ibscbs(item):
    """Serializa item NCM IBS/CBS para JSON"""
    def to_float(val):
        if val is None:
            return None
        if isinstance(val, Decimal):
            return float(val)
        return val

    def to_str(val):
        if val is None:
            return None
        if isinstance(val, datetime):
            return val.isoformat()
        return str(val)

    return {
        'id': item.id,
        'ncm_prefixo': item.ncm_prefixo,
        'descricao_ncm': item.descricao_ncm,
        'cst_esperado': item.cst_esperado,
        'class_trib_codigo': item.class_trib_codigo,
        'aliquota_ibs_uf': to_float(item.aliquota_ibs_uf),
        'aliquota_ibs_mun': to_float(item.aliquota_ibs_mun),
        'aliquota_cbs': to_float(item.aliquota_cbs),
        'reducao_aliquota': to_float(item.reducao_aliquota),
        'observacao': item.observacao,
        'ativo': item.ativo,
        'validado_por': item.validado_por,
        'validado_em': to_str(item.validado_em),
        'criado_em': to_str(item.criado_em)
    }


@recebimento_views_bp.route('/ncm-ibscbs')
@login_required
def ncm_ibscbs():
    """
    Tela CRUD de NCMs validados para IBS/CBS.
    Cadastro dos 4 primeiros digitos do NCM com aliquotas esperadas.
    """
    # Parametros de filtro
    ncm = request.args.get('ncm', '')
    apenas_ativos = request.args.get('apenas_ativos', '1') == '1'
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Query base
    query = NcmIbsCbsValidado.query

    # Aplicar filtros
    if apenas_ativos:
        query = query.filter_by(ativo=True)
    if ncm:
        query = query.filter(
            db.or_(
                NcmIbsCbsValidado.ncm_prefixo.ilike(f'%{ncm}%'),
                NcmIbsCbsValidado.descricao_ncm.ilike(f'%{ncm}%')
            )
        )

    # Ordenar por NCM
    paginacao = query.order_by(
        NcmIbsCbsValidado.ncm_prefixo.asc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # Estatisticas
    stats = {
        'total': NcmIbsCbsValidado.query.count(),
        'ativos': NcmIbsCbsValidado.query.filter_by(ativo=True).count(),
        'inativos': NcmIbsCbsValidado.query.filter_by(ativo=False).count()
    }

    # Serializar itens para JSON (usado nos modais)
    itens_json = json.dumps([
        _serializar_ncm_ibscbs(item)
        for item in paginacao.items
    ])

    return render_template(
        'ncm_ibscbs.html',
        paginacao=paginacao,
        stats=stats,
        filtros={
            'ncm': ncm,
            'apenas_ativos': apenas_ativos
        },
        itens_json=itens_json
    )


@recebimento_views_bp.route('/ncm-ibscbs/salvar', methods=['POST'])
@login_required
def ncm_ibscbs_salvar():
    """Salva (cria ou atualiza) um cadastro NCM IBS/CBS"""
    try:
        ncm_id = request.form.get('id')
        ncm_prefixo = request.form.get('ncm_prefixo', '').strip()

        if not ncm_prefixo or len(ncm_prefixo) != 4:
            flash('NCM prefixo deve ter exatamente 4 digitos', 'danger')
            return redirect(url_for('recebimento_views.ncm_ibscbs'))

        # Verificar se é edição ou novo
        if ncm_id:
            ncm = NcmIbsCbsValidado.query.get(int(ncm_id))
            if not ncm:
                flash('NCM nao encontrado', 'danger')
                return redirect(url_for('recebimento_views.ncm_ibscbs'))
        else:
            # Verificar se já existe
            existente = NcmIbsCbsValidado.query.filter_by(ncm_prefixo=ncm_prefixo).first()
            if existente:
                flash(f'NCM {ncm_prefixo} ja cadastrado', 'warning')
                return redirect(url_for('recebimento_views.ncm_ibscbs'))
            ncm = NcmIbsCbsValidado(ncm_prefixo=ncm_prefixo)

        # Atualizar campos
        ncm.descricao_ncm = request.form.get('descricao_ncm', '').strip() or None
        ncm.cst_esperado = request.form.get('cst_esperado', '').strip() or None
        ncm.class_trib_codigo = request.form.get('class_trib_codigo', '').strip() or None

        # Aliquotas
        def parse_decimal(val):
            if not val:
                return None
            try:
                return Decimal(str(val).replace(',', '.'))
            except:
                return None

        ncm.aliquota_ibs_uf = parse_decimal(request.form.get('aliquota_ibs_uf'))
        ncm.aliquota_ibs_mun = parse_decimal(request.form.get('aliquota_ibs_mun'))
        ncm.aliquota_cbs = parse_decimal(request.form.get('aliquota_cbs'))
        ncm.reducao_aliquota = parse_decimal(request.form.get('reducao_aliquota'))

        ncm.observacao = request.form.get('observacao', '').strip() or None
        ncm.ativo = request.form.get('ativo') == '1'
        ncm.validado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        ncm.validado_em = datetime.utcnow()

        if not ncm_id:
            db.session.add(ncm)

        db.session.commit()

        acao = 'atualizado' if ncm_id else 'cadastrado'
        flash(f'NCM {ncm_prefixo} {acao} com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao salvar: {str(e)}', 'danger')

    return redirect(url_for('recebimento_views.ncm_ibscbs'))


@recebimento_views_bp.route('/ncm-ibscbs/<int:ncm_id>/excluir', methods=['POST'])
@login_required
def ncm_ibscbs_excluir(ncm_id):
    """Exclui (desativa) um cadastro NCM IBS/CBS"""
    try:
        ncm = NcmIbsCbsValidado.query.get(ncm_id)
        if not ncm:
            flash('NCM nao encontrado', 'danger')
            return redirect(url_for('recebimento_views.ncm_ibscbs'))

        # Soft delete - apenas desativa
        ncm.ativo = False
        ncm.atualizado_em = datetime.utcnow()
        db.session.commit()

        flash(f'NCM {ncm.ncm_prefixo} desativado com sucesso', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {str(e)}', 'danger')

    return redirect(url_for('recebimento_views.ncm_ibscbs'))


# =============================================================================
# TELA 5: PENDENCIAS IBS/CBS
# =============================================================================

@recebimento_views_bp.route('/pendencias-ibscbs')
@login_required
def pendencias_ibscbs():
    """
    Tela de pendencias fiscais IBS/CBS.
    Lista CTes e NF-es de fornecedores Regime Normal que nao destacaram IBS/CBS.
    """
    # Parametros de filtro
    tipo_doc = request.args.get('tipo_doc', '')
    status = request.args.get('status', '')
    cnpj = request.args.get('cnpj', '')
    motivo = request.args.get('motivo', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Query base
    query = PendenciaFiscalIbsCbs.query

    # Aplicar filtros
    if tipo_doc:
        query = query.filter_by(tipo_documento=tipo_doc)
    if status:
        query = query.filter_by(status=status)
    if cnpj:
        query = query.filter(PendenciaFiscalIbsCbs.cnpj_fornecedor.ilike(f'%{cnpj}%'))
    if motivo:
        query = query.filter_by(motivo_pendencia=motivo)

    # Ordenar por data decrescente
    paginacao = query.order_by(
        PendenciaFiscalIbsCbs.criado_em.desc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # Estatisticas
    stats = {
        'total': PendenciaFiscalIbsCbs.query.count(),
        'pendente': PendenciaFiscalIbsCbs.query.filter_by(status='pendente').count(),
        'aprovado': PendenciaFiscalIbsCbs.query.filter_by(status='aprovado').count(),
        'rejeitado': PendenciaFiscalIbsCbs.query.filter_by(status='rejeitado').count(),
        'cte': PendenciaFiscalIbsCbs.query.filter_by(tipo_documento='CTe').count(),
        'nfe': PendenciaFiscalIbsCbs.query.filter_by(tipo_documento='NF-e').count()
    }

    # Opcoes de filtros
    opcoes_tipo_doc = [
        ('', 'Todos'),
        ('CTe', 'CTe'),
        ('NF-e', 'NF-e')
    ]
    opcoes_status = [
        ('', 'Todos'),
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado')
    ]
    opcoes_motivo = [
        ('', 'Todos'),
        ('nao_destacou', 'Nao destacou IBS/CBS'),
        ('cst_incorreto', 'CST incorreto'),
        ('aliquota_divergente', 'Aliquota divergente'),
        ('valor_zerado', 'Valor zerado')
    ]

    return render_template(
        'pendencias_ibscbs.html',
        paginacao=paginacao,
        stats=stats,
        filtros={
            'tipo_doc': tipo_doc,
            'status': status,
            'cnpj': cnpj,
            'motivo': motivo
        },
        opcoes_tipo_doc=opcoes_tipo_doc,
        opcoes_status=opcoes_status,
        opcoes_motivo=opcoes_motivo
    )


@recebimento_views_bp.route('/pendencias-ibscbs/<int:pendencia_id>/resolver', methods=['POST'])
@login_required
def pendencia_ibscbs_resolver(pendencia_id):
    """Resolve uma pendencia IBS/CBS"""
    try:
        pendencia = PendenciaFiscalIbsCbs.query.get(pendencia_id)
        if not pendencia:
            return jsonify({'sucesso': False, 'mensagem': 'Pendencia nao encontrada'}), 404

        resolucao = request.json.get('resolucao')
        justificativa = request.json.get('justificativa', '').strip()

        if not justificativa:
            return jsonify({'sucesso': False, 'mensagem': 'Justificativa obrigatoria'}), 400

        # Determinar status baseado na resolucao
        if resolucao in ['fornecedor_isento', 'ncm_nao_tributa', 'erro_sistema']:
            pendencia.status = 'aprovado'
        elif resolucao == 'devolvido_fornecedor':
            pendencia.status = 'rejeitado'
        else:
            pendencia.status = 'aprovado'

        pendencia.resolucao = resolucao
        pendencia.justificativa = justificativa
        pendencia.resolvido_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        pendencia.resolvido_em = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': f'Pendencia {pendencia_id} resolvida com sucesso'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


# =============================================================================
# API NCM IBS/CBS - INTEGRACAO ODOO
# =============================================================================

def _get_odoo_connection():
    """Obtem conexao com Odoo"""
    try:
        from app.odoo.utils.connection import get_odoo_connection
        return get_odoo_connection()
    except Exception as e:
        return None


@recebimento_views_bp.route('/ncm-ibscbs/buscar-odoo/<prefixo>')
@login_required
def ncm_ibscbs_buscar_odoo(prefixo):
    """
    Busca NCMs no Odoo que comecam com o prefixo informado.
    Retorna lista de NCMs com campos IBS/CBS para exibir ao usuario.
    """
    try:
        if not prefixo or len(prefixo) != 4:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Prefixo deve ter 4 digitos'
            }), 400

        odoo = _get_odoo_connection()
        if not odoo:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Erro ao conectar com Odoo'
            }), 500

        # Buscar NCMs que comecam com o prefixo
        ncms = odoo.search_read(
            'l10n_br_ciel_it_account.ncm',
            [['codigo', '=like', f'{prefixo}%']],
            [
                'id',
                'codigo',
                'name',
                'l10n_br_ibscbs_cst',
                'l10n_br_ibscbs_classtrib_id',
                'l10n_br_ibs_uf_aliquota',
                'l10n_br_ibs_mun_aliquota',
                'l10n_br_cbs_aliquota',
                'l10n_br_ibscbs_reducao_aliquota'
            ],
            order='codigo'
        )

        if not ncms:
            return jsonify({
                'sucesso': True,
                'ncms': [],
                'mensagem': f'Nenhum NCM encontrado com prefixo {prefixo} no Odoo'
            })

        # Processar NCMs - buscar codigo da classificacao tributaria
        ncms_processados = []
        for ncm in ncms:
            classtrib_codigo = None
            classtrib_nome = None

            # Extrair codigo da classificacao tributaria
            if ncm.get('l10n_br_ibscbs_classtrib_id'):
                classtrib_id = ncm['l10n_br_ibscbs_classtrib_id']
                if isinstance(classtrib_id, (list, tuple)) and len(classtrib_id) >= 2:
                    # Formato [id, nome] - buscar codigo
                    try:
                        classtrib = odoo.search_read(
                            'l10n_br_ciel_it_account.classificacao.tributaria.ibscbs',
                            [['id', '=', classtrib_id[0]]],
                            ['codigo', 'name']
                        )
                        if classtrib:
                            classtrib_codigo = classtrib[0].get('codigo')
                            classtrib_nome = classtrib[0].get('name')
                    except:
                        classtrib_nome = classtrib_id[1] if len(classtrib_id) > 1 else None

            ncms_processados.append({
                'id': ncm['id'],
                'codigo': ncm.get('codigo'),
                'name': ncm.get('name'),
                'cst': ncm.get('l10n_br_ibscbs_cst'),
                'classtrib_codigo': classtrib_codigo,
                'classtrib_nome': classtrib_nome,
                'ibs_uf': ncm.get('l10n_br_ibs_uf_aliquota'),
                'ibs_mun': ncm.get('l10n_br_ibs_mun_aliquota'),
                'cbs': ncm.get('l10n_br_cbs_aliquota'),
                'reducao': ncm.get('l10n_br_ibscbs_reducao_aliquota')
            })

        return jsonify({
            'sucesso': True,
            'ncms': ncms_processados,
            'total': len(ncms_processados),
            'mensagem': f'{len(ncms_processados)} NCM(s) encontrado(s) com prefixo {prefixo}'
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao buscar NCMs no Odoo: {str(e)}'
        }), 500


@recebimento_views_bp.route('/ncm-ibscbs/atualizar-odoo', methods=['POST'])
@login_required
def ncm_ibscbs_atualizar_odoo():
    """
    Atualiza NCMs no Odoo com os valores do padrao cadastrado.
    Recebe lista de IDs de NCMs do Odoo e os novos valores.
    """
    try:
        dados = request.json
        if not dados:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Dados nao informados'
            }), 400

        ncm_ids = dados.get('ncm_ids', [])
        novos_valores = dados.get('novos_valores', {})

        if not ncm_ids:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Nenhum NCM selecionado'
            }), 400

        odoo = _get_odoo_connection()
        if not odoo:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Erro ao conectar com Odoo'
            }), 500

        # Buscar ID da classificacao tributaria pelo codigo
        classtrib_id = None
        if novos_valores.get('class_trib_codigo'):
            classtrib = odoo.search_read(
                'l10n_br_ciel_it_account.classificacao.tributaria.ibscbs',
                [['codigo', '=', novos_valores['class_trib_codigo']]],
                ['id']
            )
            if classtrib:
                classtrib_id = classtrib[0]['id']

        # Preparar valores para atualizacao
        valores_odoo = {}

        if novos_valores.get('cst_esperado'):
            valores_odoo['l10n_br_ibscbs_cst'] = novos_valores['cst_esperado']

        if classtrib_id:
            valores_odoo['l10n_br_ibscbs_classtrib_id'] = classtrib_id

        if novos_valores.get('aliquota_ibs_uf') is not None:
            valores_odoo['l10n_br_ibs_uf_aliquota'] = float(novos_valores['aliquota_ibs_uf'])

        if novos_valores.get('aliquota_ibs_mun') is not None:
            valores_odoo['l10n_br_ibs_mun_aliquota'] = float(novos_valores['aliquota_ibs_mun'])

        if novos_valores.get('aliquota_cbs') is not None:
            valores_odoo['l10n_br_cbs_aliquota'] = float(novos_valores['aliquota_cbs'])

        if novos_valores.get('reducao_aliquota') is not None:
            valores_odoo['l10n_br_ibscbs_reducao_aliquota'] = float(novos_valores['reducao_aliquota'])

        if not valores_odoo:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Nenhum valor para atualizar'
            }), 400

        # Atualizar cada NCM
        atualizados = 0
        erros = []

        for ncm_id in ncm_ids:
            try:
                odoo.write(
                    'l10n_br_ciel_it_account.ncm',
                    [int(ncm_id)],
                    valores_odoo
                )
                atualizados += 1
            except Exception as e:
                erros.append(f'NCM {ncm_id}: {str(e)}')

        return jsonify({
            'sucesso': True,
            'atualizados': atualizados,
            'total': len(ncm_ids),
            'erros': erros,
            'mensagem': f'{atualizados} de {len(ncm_ids)} NCM(s) atualizado(s) no Odoo'
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao atualizar NCMs no Odoo: {str(e)}'
        }), 500


@recebimento_views_bp.route('/ncm-ibscbs/salvar-ajax', methods=['POST'])
@login_required
def ncm_ibscbs_salvar_ajax():
    """
    Salva (cria ou atualiza) um cadastro NCM IBS/CBS via AJAX.
    Retorna os dados salvos para uso no modal de confirmacao Odoo.
    """
    try:
        dados = request.json
        if not dados:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Dados nao informados'
            }), 400

        ncm_id = dados.get('id')
        ncm_prefixo = (dados.get('ncm_prefixo') or '').strip()

        if not ncm_prefixo or len(ncm_prefixo) != 4:
            return jsonify({
                'sucesso': False,
                'mensagem': 'NCM prefixo deve ter exatamente 4 digitos'
            }), 400

        # Verificar se é edição ou novo
        if ncm_id:
            ncm = NcmIbsCbsValidado.query.get(int(ncm_id))
            if not ncm:
                return jsonify({
                    'sucesso': False,
                    'mensagem': 'NCM nao encontrado'
                }), 404
        else:
            # Verificar se já existe
            existente = NcmIbsCbsValidado.query.filter_by(ncm_prefixo=ncm_prefixo).first()
            if existente:
                return jsonify({
                    'sucesso': False,
                    'mensagem': f'NCM {ncm_prefixo} ja cadastrado'
                }), 400
            ncm = NcmIbsCbsValidado(ncm_prefixo=ncm_prefixo)

        # Funcao para converter valores decimais
        def parse_decimal(val):
            if val is None or val == '':
                return None
            try:
                return Decimal(str(val).replace(',', '.'))
            except:
                return None

        # Atualizar campos
        ncm.descricao_ncm = (dados.get('descricao_ncm') or '').strip() or None
        ncm.cst_esperado = (dados.get('cst_esperado') or '').strip() or None
        ncm.class_trib_codigo = (dados.get('class_trib_codigo') or '').strip() or None
        ncm.aliquota_ibs_uf = parse_decimal(dados.get('aliquota_ibs_uf'))
        ncm.aliquota_ibs_mun = parse_decimal(dados.get('aliquota_ibs_mun'))
        ncm.aliquota_cbs = parse_decimal(dados.get('aliquota_cbs'))
        ncm.reducao_aliquota = parse_decimal(dados.get('reducao_aliquota'))
        ncm.observacao = (dados.get('observacao') or '').strip() or None
        ncm.ativo = dados.get('ativo', True)
        ncm.validado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        ncm.validado_em = datetime.utcnow()

        if not ncm_id:
            db.session.add(ncm)

        db.session.commit()

        acao = 'atualizado' if ncm_id else 'cadastrado'

        return jsonify({
            'sucesso': True,
            'mensagem': f'NCM {ncm_prefixo} {acao} com sucesso!',
            'ncm': {
                'id': ncm.id,
                'ncm_prefixo': ncm.ncm_prefixo,
                'descricao_ncm': ncm.descricao_ncm,
                'cst_esperado': ncm.cst_esperado,
                'class_trib_codigo': ncm.class_trib_codigo,
                'aliquota_ibs_uf': float(ncm.aliquota_ibs_uf) if ncm.aliquota_ibs_uf else None,
                'aliquota_ibs_mun': float(ncm.aliquota_ibs_mun) if ncm.aliquota_ibs_mun else None,
                'aliquota_cbs': float(ncm.aliquota_cbs) if ncm.aliquota_cbs else None,
                'reducao_aliquota': float(ncm.reducao_aliquota) if ncm.reducao_aliquota else None
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao salvar: {str(e)}'
        }), 500

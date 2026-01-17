"""
Views de Recebimento de Materiais - Telas HTML
==============================================

FASE 1 - Validacao Fiscal:
- GET /operacional/compras/divergencias - Tela de divergencias fiscais
- GET /operacional/compras/primeira-compra - Tela de primeira compra
- GET /operacional/compras/perfis-fiscais - Tela de perfis fiscais
- GET /operacional/compras/ncm-ibscbs - Cadastro de NCMs IBS/CBS
- GET /operacional/compras/pendencias-ibscbs - Pendencias IBS/CBS

FASE 2 - Vinculacao NF x PO:
- GET /operacional/compras/depara-fornecedor - Tela de De-Para Produto/Fornecedor
- GET /operacional/compras/divergencias-nf-po - Tela de divergencias NF x PO
- GET /operacional/compras/validacoes-nf-po - Tela de validacoes NF x PO

Referencia:
- .claude/references/RECEBIMENTO_MATERIAIS.md
- .claude/plans/wiggly-plotting-newt.md
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
            ncm = db.session.get(NcmIbsCbsValidado,int(ncm_id)) if int(ncm_id) else None
            if not ncm:
                flash('NCM nao encontrado', 'danger')
                return redirect(url_for('recebimento_views.ncm_ibscbs'))
        else:
            # Verificar se já existe
            existente = db.session.query(NcmIbsCbsValidado).filter_by(ncm_prefixo=ncm_prefixo).first()
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
            except Exception as e:
                print(f"[DEBUG] Erro ao converter decimal: {e}")
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
        ncm = db.session.get(NcmIbsCbsValidado,ncm_id) if ncm_id else None
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
    query = db.session.query(PendenciaFiscalIbsCbs)

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
        ('nao_destacou', 'Divergencia (NCM cadastrado)'),
        ('falta_cadastro', 'Falta Cadastro NCM'),
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
        pendencia = db.session.get(PendenciaFiscalIbsCbs,pendencia_id) if pendencia_id else None
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


@recebimento_views_bp.route('/pendencias-ibscbs/<int:pendencia_id>/detalhes')
@login_required
def pendencia_ibscbs_detalhes(pendencia_id):
    """Retorna detalhes completos de uma pendencia IBS/CBS"""
    pendencia = db.session.get(PendenciaFiscalIbsCbs,pendencia_id) if pendencia_id else None
    if not pendencia:
        return jsonify({'sucesso': False, 'mensagem': 'Pendencia nao encontrada'}), 404

    return jsonify({
        'sucesso': True,
        'pendencia': pendencia.to_dict(),
        'ibscbs': {
            'cst': pendencia.ibscbs_cst,
            'class_trib': pendencia.ibscbs_class_trib,
            'base': float(pendencia.ibscbs_base) if pendencia.ibscbs_base else None,
            'ibs_uf_aliq': float(pendencia.ibs_uf_aliq) if pendencia.ibs_uf_aliq else None,
            'ibs_uf_valor': float(pendencia.ibs_uf_valor) if pendencia.ibs_uf_valor else None,
            'ibs_mun_aliq': float(pendencia.ibs_mun_aliq) if pendencia.ibs_mun_aliq else None,
            'ibs_mun_valor': float(pendencia.ibs_mun_valor) if pendencia.ibs_mun_valor else None,
            'ibs_total': float(pendencia.ibs_total) if pendencia.ibs_total else None,
            'cbs_aliq': float(pendencia.cbs_aliq) if pendencia.cbs_aliq else None,
            'cbs_valor': float(pendencia.cbs_valor) if pendencia.cbs_valor else None
        }
    })


@recebimento_views_bp.route('/ncm-ibscbs/cadastro/<prefixo>')
@login_required
def ncm_ibscbs_cadastro_local(prefixo):
    """
    Busca cadastro local do NCM pelo prefixo.
    Usado pelo modal de detalhes para verificar se NCM esta cadastrado.

    Returns:
        {
            'sucesso': True,
            'cadastrado': True/False,
            'ncm': { dados do cadastro } ou null
        }
    """
    from app.recebimento.models import NcmIbsCbsValidado

    try:
        if not prefixo or len(prefixo) != 4:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Prefixo deve ter 4 digitos'
            }), 400

        ncm = NcmIbsCbsValidado.query.filter_by(
            ncm_prefixo=prefixo,
            ativo=True
        ).first()

        if ncm:
            return jsonify({
                'sucesso': True,
                'cadastrado': True,
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
        else:
            return jsonify({
                'sucesso': True,
                'cadastrado': False,
                'ncm': None
            })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'mensagem': str(e)
        }), 500


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
                    except Exception as e:
                        print(f"[DEBUG] Erro ao buscar classificacao tributaria: {e}")
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
            ncm = db.session.get(NcmIbsCbsValidado,int(ncm_id)) if int(ncm_id) else None
            if not ncm:
                return jsonify({
                    'sucesso': False,
                    'mensagem': 'NCM nao encontrado'
                }), 404
        else:
            # Verificar se já existe
            existente = db.session.query(NcmIbsCbsValidado).filter_by(ncm_prefixo=ncm_prefixo).first()
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
            except Exception as e:
                print(f"[DEBUG] Erro ao converter decimal: {e}")
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


# =============================================================================
# SINCRONIZACAO MANUAL IBS/CBS
# =============================================================================

@recebimento_views_bp.route('/pendencias-ibscbs/sincronizar', methods=['POST'])
@login_required
def pendencias_ibscbs_sincronizar():
    """
    Executa sincronizacao manual de pendencias IBS/CBS.

    Acoes:
    1. Executa o job de validacao IBS/CBS (buscar novas NF-es e CTes)
    2. Reprocessa pendencias existentes com motivo 'falta_cadastro'
       para verificar se NCM foi cadastrado posteriormente

    Returns:
        JSON com estatisticas da sincronizacao
    """
    import logging
    logger = logging.getLogger(__name__)

    resultado = {
        'sucesso': True,
        'mensagem': '',
        'estatisticas': {
            'ctes_processados': 0,
            'ctes_pendencias': 0,
            'nfes_processadas': 0,
            'nfes_pendencias': 0,
            'pendencias_reprocessadas': 0,
            'pendencias_atualizadas': 0,
            'erros': 0
        }
    }

    try:
        # 1. Executar job de validacao IBS/CBS para buscar novos documentos
        from app.recebimento.jobs.validacao_ibscbs_job import executar_validacao_ibscbs

        logger.info("Iniciando sincronizacao manual de pendencias IBS/CBS...")

        res_job = executar_validacao_ibscbs(minutos_janela=1440)  # Ultimas 24 horas

        resultado['estatisticas']['ctes_processados'] = res_job.get('ctes_processados', 0)
        resultado['estatisticas']['ctes_pendencias'] = res_job.get('ctes_pendencias', 0)
        resultado['estatisticas']['nfes_processadas'] = res_job.get('nfes_processadas', 0)
        resultado['estatisticas']['nfes_pendencias'] = res_job.get('nfes_pendencias', 0)
        resultado['estatisticas']['erros'] = res_job.get('erros', 0)

        # 2. Reprocessar pendencias com 'falta_cadastro' para verificar se NCM foi cadastrado
        pendencias_falta_cadastro = db.session.query(PendenciaFiscalIbsCbs).filter_by(
            status='pendente',
            motivo_pendencia='falta_cadastro'
        ).all()

        resultado['estatisticas']['pendencias_reprocessadas'] = len(pendencias_falta_cadastro)

        for pendencia in pendencias_falta_cadastro:
            if not pendencia.ncm_prefixo:
                continue

            # Verificar se NCM foi cadastrado
            ncm = db.session.query(NcmIbsCbsValidado).filter_by(
                ncm_prefixo=pendencia.ncm_prefixo,
                ativo=True
            ).first()

            if ncm:
                # NCM agora esta cadastrado - atualizar motivo para 'nao_destacou'
                pendencia.motivo_pendencia = 'nao_destacou'
                pendencia.detalhes_pendencia = (
                    f'NCM {pendencia.ncm_prefixo} esta cadastrado com IBS/CBS obrigatorio, '
                    f'mas o fornecedor nao destacou no XML. '
                    f'Aliquotas esperadas: IBS UF={ncm.aliquota_ibs_uf}%, '
                    f'IBS Mun={ncm.aliquota_ibs_mun}%, CBS={ncm.aliquota_cbs}%'
                )
                resultado['estatisticas']['pendencias_atualizadas'] += 1

        db.session.commit()

        # Montar mensagem de resultado
        msgs = []
        if resultado['estatisticas']['ctes_processados'] > 0:
            msgs.append(f"{resultado['estatisticas']['ctes_processados']} CTe(s) processados")
        if resultado['estatisticas']['nfes_processadas'] > 0:
            msgs.append(f"{resultado['estatisticas']['nfes_processadas']} NF-e(s) processadas")
        if resultado['estatisticas']['ctes_pendencias'] > 0:
            msgs.append(f"{resultado['estatisticas']['ctes_pendencias']} novas pendencias CTe")
        if resultado['estatisticas']['nfes_pendencias'] > 0:
            msgs.append(f"{resultado['estatisticas']['nfes_pendencias']} novas pendencias NF-e")
        if resultado['estatisticas']['pendencias_atualizadas'] > 0:
            msgs.append(f"{resultado['estatisticas']['pendencias_atualizadas']} pendencias atualizadas (NCM cadastrado)")

        if msgs:
            resultado['mensagem'] = 'Sincronizacao concluida: ' + ', '.join(msgs)
        else:
            resultado['mensagem'] = 'Sincronizacao concluida. Nenhum documento novo encontrado.'

        logger.info(resultado['mensagem'])

    except Exception as e:
        logger.error(f"Erro na sincronizacao IBS/CBS: {e}")
        db.session.rollback()
        resultado['sucesso'] = False
        resultado['mensagem'] = f'Erro na sincronizacao: {str(e)}'

    return jsonify(resultado)


# =============================================================================
# FASE 2: DE-PARA PRODUTO/FORNECEDOR
# =============================================================================

@recebimento_views_bp.route('/depara-fornecedor')
@login_required
def depara_fornecedor():
    """
    Tela de gerenciamento de De-Para Produto/Fornecedor.
    CRUD completo + sincronizacao com Odoo.
    """
    from app.recebimento.models import ProdutoFornecedorDepara

    # Filtros
    filtros = {
        'cnpj': request.args.get('cnpj', ''),
        'cod_produto': request.args.get('cod_produto', ''),
        'ativo': request.args.get('ativo', 'true')
    }

    # Query base
    query = db.session.query(ProdutoFornecedorDepara)

    # Aplicar filtros
    if filtros['cnpj']:
        query = query.filter(
            ProdutoFornecedorDepara.cnpj_fornecedor.ilike(f"%{filtros['cnpj']}%")
        )

    if filtros['cod_produto']:
        query = query.filter(
            db.or_(
                ProdutoFornecedorDepara.cod_produto_fornecedor.ilike(f"%{filtros['cod_produto']}%"),
                ProdutoFornecedorDepara.cod_produto_interno.ilike(f"%{filtros['cod_produto']}%")
            )
        )

    if filtros['ativo'] != 'todos':
        query = query.filter(
            ProdutoFornecedorDepara.ativo == (filtros['ativo'] == 'true')
        )

    # Ordenar
    query = query.order_by(
        ProdutoFornecedorDepara.razao_fornecedor,
        ProdutoFornecedorDepara.cod_produto_fornecedor
    )

    # Paginacao
    page = request.args.get('page', 1, type=int)
    per_page = 50
    paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

    # Estatisticas
    stats = {
        'total': ProdutoFornecedorDepara.query.filter_by(ativo=True).count(),
        'sincronizados': ProdutoFornecedorDepara.query.filter_by(
            ativo=True, sincronizado_odoo=True
        ).count(),
        'pendentes': ProdutoFornecedorDepara.query.filter_by(
            ativo=True, sincronizado_odoo=False
        ).count()
    }

    return render_template(
        'recebimento/depara_fornecedor.html',
        items=paginacao.items,
        paginacao={
            'page': paginacao.page,
            'pages': paginacao.pages,
            'total': paginacao.total,
            'per_page': per_page,
            'items': paginacao.items
        },
        filtros=filtros,
        stats=stats
    )


# =============================================================================
# FASE 2: DIVERGENCIAS NF x PO
# =============================================================================

@recebimento_views_bp.route('/divergencias-nf-po')
@login_required
def divergencias_nf_po():
    """
    Tela de divergencias NF x PO para resolucao manual.
    """
    from app.recebimento.models import DivergenciaNfPo, ValidacaoNfPoDfe, MatchNfPoItem

    # Filtros
    filtros = {
        'status': request.args.get('status', 'pendente'),
        'tipo': request.args.get('tipo', ''),
        'cnpj': request.args.get('cnpj', '')
    }

    # Query base com JOIN para pegar dados da validacao (numero_nf)
    query = db.session.query(DivergenciaNfPo).outerjoin(
        ValidacaoNfPoDfe,
        DivergenciaNfPo.validacao_id == ValidacaoNfPoDfe.id
    )

    # Aplicar filtros
    if filtros['status'] and filtros['status'] != 'todas':
        query = query.filter(DivergenciaNfPo.status == filtros['status'])

    if filtros['tipo']:
        query = query.filter(DivergenciaNfPo.tipo_divergencia == filtros['tipo'])

    if filtros['cnpj']:
        query = query.filter(
            DivergenciaNfPo.cnpj_fornecedor.ilike(f"%{filtros['cnpj']}%")
        )

    # Ordenar
    query = query.order_by(DivergenciaNfPo.criado_em.desc())

    # Paginacao
    page = request.args.get('page', 1, type=int)
    per_page = 50
    paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

    # Funcao helper para formatar CNPJ
    def formatar_cnpj(cnpj):
        """Formata CNPJ como XX.XXX.XXX/XXXX-XX"""
        if not cnpj:
            return None
        # Limpar apenas digitos
        cnpj_limpo = ''.join(c for c in str(cnpj) if c.isdigit())
        if len(cnpj_limpo) == 14:
            return f'{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}'
        return cnpj  # Retorna original se nao for 14 digitos

    # Enriquecer itens com dados adicionais
    items_enriquecidos = []
    for div in paginacao.items:
        item = {
            'id': div.id,
            'validacao_id': div.validacao_id,
            'odoo_dfe_id': div.odoo_dfe_id,
            'odoo_dfe_line_id': div.odoo_dfe_line_id,
            'cnpj_fornecedor': formatar_cnpj(div.cnpj_fornecedor),
            'razao_fornecedor': div.razao_fornecedor,
            'cod_produto_fornecedor': div.cod_produto_fornecedor,
            'cod_produto_interno': div.cod_produto_interno,
            'nome_produto': div.nome_produto,
            'tipo_divergencia': div.tipo_divergencia,
            'campo_label': div.campo_label,
            'valor_nf': div.valor_nf,
            'valor_po': div.valor_po,
            'diferenca_percentual': div.diferenca_percentual,
            'odoo_po_id': div.odoo_po_id,
            'odoo_po_name': div.odoo_po_name,
            'odoo_po_line_id': div.odoo_po_line_id,
            'status': div.status,
            'resolucao': div.resolucao,
            'justificativa': div.justificativa,
            'resolvido_por': div.resolvido_por,
            'resolvido_em': div.resolvido_em,
            'criado_em': div.criado_em,
            # Campos que serao preenchidos abaixo
            'qtd_nf': None,
            'preco_nf': None,
            'um_nf': None,
            'fator_conversao': 1
        }

        # Buscar dados da validacao (numero_nf, data_nf)
        if div.validacao_id:
            validacao = db.session.get(ValidacaoNfPoDfe,div.validacao_id) if div.validacao_id else None
            if validacao:
                item['numero_nf'] = validacao.numero_nf
                item['data_nf'] = validacao.data_nf
                item['valor_total_nf'] = validacao.valor_total_nf

        # Buscar dados do match (qtd, preco, um)
        match_encontrado = False
        if div.odoo_dfe_line_id and div.validacao_id:
            match = db.session.query(MatchNfPoItem).filter_by(
                validacao_id=div.validacao_id,
                odoo_dfe_line_id=div.odoo_dfe_line_id
            ).first()
            if match:
                match_encontrado = True
                item['qtd_nf'] = float(match.qtd_nf) if match.qtd_nf else None
                item['preco_nf'] = float(match.preco_nf) if match.preco_nf else None
                item['um_nf'] = match.um_nf
                item['fator_conversao'] = float(match.fator_conversao) if match.fator_conversao else 1

        # Se nao encontrou match, buscar qualquer match da mesma validacao
        # com o mesmo codigo de produto fornecedor
        if not match_encontrado and div.validacao_id and div.cod_produto_fornecedor:
            match = db.session.query(MatchNfPoItem).filter_by(
                validacao_id=div.validacao_id,
                cod_produto_fornecedor=div.cod_produto_fornecedor
            ).first()
            if match:
                match_encontrado = True
                item['qtd_nf'] = float(match.qtd_nf) if match.qtd_nf else None
                item['preco_nf'] = float(match.preco_nf) if match.preco_nf else None
                item['um_nf'] = match.um_nf
                item['fator_conversao'] = float(match.fator_conversao) if match.fator_conversao else 1

        # Se ainda nao encontrou, marcar para buscar do Odoo
        # (sera feito em batch depois para performance)
        if not match_encontrado:
            item['_buscar_odoo'] = True
            item['_odoo_dfe_line_id'] = div.odoo_dfe_line_id

        items_enriquecidos.append(item)

    # Buscar dados do Odoo para itens sem match (em batch)
    itens_para_buscar = [i for i in items_enriquecidos if i.get('_buscar_odoo')]
    if itens_para_buscar:
        try:
            from app.odoo.utils.connection import get_odoo_connection
            odoo = get_odoo_connection()
            if odoo.authenticate():
                dfe_line_ids = [i['_odoo_dfe_line_id'] for i in itens_para_buscar if i.get('_odoo_dfe_line_id')]
                if dfe_line_ids:
                    lines = odoo.read(
                        'l10n_br_ciel_it_account.dfe.line',
                        dfe_line_ids,
                        ['id', 'det_prod_qcom', 'det_prod_vuncom', 'det_prod_ucom']
                    )
                    # Mapear por ID
                    lines_map = {line['id']: line for line in lines} if lines else {}

                    for item in itens_para_buscar:
                        line_id = item.get('_odoo_dfe_line_id')
                        if line_id and line_id in lines_map:
                            line = lines_map[line_id]
                            item['qtd_nf'] = float(line.get('det_prod_qcom') or 0)
                            item['preco_nf'] = float(line.get('det_prod_vuncom') or 0)
                            item['um_nf'] = line.get('det_prod_ucom')
        except Exception as e:
            # Se falhar, apenas loga - os dados ficarao vazios
            import logging
            logging.getLogger(__name__).warning(f"Erro ao buscar dados do Odoo: {e}")

    # Limpar campos internos
    for item in items_enriquecidos:
        item.pop('_buscar_odoo', None)
        item.pop('_odoo_dfe_line_id', None)

    # Estatisticas
    stats = {
        'pendente': db.session.query(DivergenciaNfPo).filter_by(status='pendente').count(),
        'aprovada': db.session.query(DivergenciaNfPo).filter_by(status='aprovada').count(),
        'rejeitada': db.session.query(DivergenciaNfPo).filter_by(status='rejeitada').count()
    }

    # Tipos de divergencia para filtro
    tipos_divergencia = [
        {'valor': 'sem_depara', 'label': 'Sem De-Para'},
        {'valor': 'sem_po', 'label': 'Sem Pedido de Compra'},
        {'valor': 'preco', 'label': 'Preco Divergente'},
        {'valor': 'quantidade', 'label': 'Quantidade Divergente'},
        {'valor': 'data_entrega', 'label': 'Data Fora do Prazo'}
    ]

    # URL base do Odoo para links externos
    odoo_base_url = 'https://odoo.nacomgoya.com.br/web'

    return render_template(
        'recebimento/divergencias_nf_po.html',
        items=items_enriquecidos,
        paginacao={
            'page': paginacao.page,
            'pages': paginacao.pages,
            'total': paginacao.total,
            'per_page': per_page
        },
        filtros=filtros,
        stats=stats,
        tipos_divergencia=tipos_divergencia,
        odoo_base_url=odoo_base_url
    )


# =============================================================================
# FASE 2: HISTORICO DE APROVACOES NF x PO
# =============================================================================

@recebimento_views_bp.route('/historico-aprovacoes-nf-po')
@login_required
def historico_aprovacoes_nf_po():
    """
    Tela de historico de aprovacoes/rejeicoes de divergencias NF x PO.
    Mostra apenas divergencias ja resolvidas (aprovadas ou rejeitadas).
    """
    from app.recebimento.models import DivergenciaNfPo, ValidacaoNfPoDfe

    # Filtros
    filtros = {
        'status': request.args.get('status', ''),  # aprovada, rejeitada
        'tipo': request.args.get('tipo', ''),
        'cnpj': request.args.get('cnpj', ''),
        'data_ini': request.args.get('data_ini', ''),
        'data_fim': request.args.get('data_fim', ''),
        'resolvido_por': request.args.get('resolvido_por', '')
    }

    # Query base - apenas resolvidas
    query = db.session.query(DivergenciaNfPo).filter(
        DivergenciaNfPo.status.in_(['aprovada', 'rejeitada'])
    )

    # Aplicar filtros
    if filtros['status']:
        query = query.filter(DivergenciaNfPo.status == filtros['status'])

    if filtros['tipo']:
        query = query.filter(DivergenciaNfPo.tipo_divergencia == filtros['tipo'])

    if filtros['cnpj']:
        query = query.filter(
            DivergenciaNfPo.cnpj_fornecedor.ilike(f"%{filtros['cnpj']}%")
        )

    if filtros['resolvido_por']:
        query = query.filter(
            DivergenciaNfPo.resolvido_por.ilike(f"%{filtros['resolvido_por']}%")
        )

    if filtros['data_ini']:
        try:
            from datetime import datetime
            data_ini = datetime.strptime(filtros['data_ini'], '%Y-%m-%d')
            query = query.filter(DivergenciaNfPo.resolvido_em >= data_ini)
        except ValueError:
            pass

    if filtros['data_fim']:
        try:
            from datetime import datetime, timedelta
            data_fim = datetime.strptime(filtros['data_fim'], '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(DivergenciaNfPo.resolvido_em < data_fim)
        except ValueError:
            pass

    # Ordenar por data de resolucao desc
    query = query.order_by(DivergenciaNfPo.resolvido_em.desc())

    # Paginacao
    page = request.args.get('page', 1, type=int)
    per_page = 50
    paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

    # Funcao helper para formatar CNPJ
    def formatar_cnpj(cnpj):
        """Formata CNPJ como XX.XXX.XXX/XXXX-XX"""
        if not cnpj:
            return None
        # Limpar apenas digitos
        cnpj_limpo = ''.join(c for c in str(cnpj) if c.isdigit())
        if len(cnpj_limpo) == 14:
            return f'{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}'
        return cnpj  # Retorna original se nao for 14 digitos

    # Enriquecer itens com dados adicionais
    items_enriquecidos = []
    for div in paginacao.items:
        item = {
            'id': div.id,
            'validacao_id': div.validacao_id,
            'odoo_dfe_id': div.odoo_dfe_id,
            'cnpj_fornecedor': formatar_cnpj(div.cnpj_fornecedor),
            'razao_fornecedor': div.razao_fornecedor,
            'cod_produto_fornecedor': div.cod_produto_fornecedor,
            'cod_produto_interno': div.cod_produto_interno,
            'nome_produto': div.nome_produto,
            'tipo_divergencia': div.tipo_divergencia,
            'valor_nf': div.valor_nf,
            'valor_po': div.valor_po,
            'diferenca_percentual': div.diferenca_percentual,
            'odoo_po_name': div.odoo_po_name,
            'status': div.status,
            'resolucao': div.resolucao,
            'justificativa': div.justificativa,
            'resolvido_por': div.resolvido_por,
            'resolvido_em': div.resolvido_em,
            'criado_em': div.criado_em
        }

        # Buscar dados da validacao (numero_nf)
        if div.validacao_id:
            validacao = db.session.get(ValidacaoNfPoDfe,div.validacao_id) if div.validacao_id else None
            if validacao:
                item['numero_nf'] = validacao.numero_nf
                item['data_nf'] = validacao.data_nf

        items_enriquecidos.append(item)

    # Estatisticas
    stats = {
        'total': db.session.query(DivergenciaNfPo).filter(
            DivergenciaNfPo.status.in_(['aprovada', 'rejeitada'])
        ).count(),
        'aprovada': db.session.query(DivergenciaNfPo).filter_by(status='aprovada').count(),
        'rejeitada': db.session.query(DivergenciaNfPo).filter_by(status='rejeitada').count()
    }

    # Usuarios que resolveram (para filtro)
    usuarios_resolvedores = db.session.query(
        DivergenciaNfPo.resolvido_por
    ).filter(
        DivergenciaNfPo.resolvido_por.isnot(None)
    ).distinct().all()
    usuarios_resolvedores = [u[0] for u in usuarios_resolvedores if u[0]]

    # Tipos de divergencia para filtro
    tipos_divergencia = [
        {'valor': 'sem_depara', 'label': 'Sem De-Para'},
        {'valor': 'sem_po', 'label': 'Sem Pedido de Compra'},
        {'valor': 'preco', 'label': 'Preco Divergente'},
        {'valor': 'quantidade', 'label': 'Quantidade Divergente'},
        {'valor': 'data_entrega', 'label': 'Data Fora do Prazo'}
    ]

    # URL base do Odoo para links externos
    odoo_base_url = 'https://odoo.nacomgoya.com.br/web'

    return render_template(
        'recebimento/historico_aprovacoes_nf_po.html',
        items=items_enriquecidos,
        paginacao={
            'page': paginacao.page,
            'pages': paginacao.pages,
            'total': paginacao.total,
            'per_page': per_page
        },
        filtros=filtros,
        stats=stats,
        tipos_divergencia=tipos_divergencia,
        usuarios_resolvedores=usuarios_resolvedores,
        odoo_base_url=odoo_base_url
    )


# =============================================================================
# FASE 2: VALIDACOES NF x PO
# =============================================================================

@recebimento_views_bp.route('/validacoes-nf-po')
@login_required
def validacoes_nf_po():
    """
    Tela de validacoes NF x PO.
    Mostra status de cada NF processada.
    """
    from app.recebimento.models import ValidacaoNfPoDfe

    # Filtros
    filtros = {
        'status': request.args.get('status', ''),
        'cnpj': request.args.get('cnpj', '')
    }

    # Query base
    query = db.session.query(ValidacaoNfPoDfe)

    # Aplicar filtros
    if filtros['status']:
        query = query.filter(ValidacaoNfPoDfe.status == filtros['status'])

    if filtros['cnpj']:
        query = query.filter(
            ValidacaoNfPoDfe.cnpj_fornecedor.ilike(f"%{filtros['cnpj']}%")
        )

    # Ordenar
    query = query.order_by(ValidacaoNfPoDfe.criado_em.desc())

    # Paginacao
    page = request.args.get('page', 1, type=int)
    per_page = 50
    paginacao = query.paginate(page=page, per_page=per_page, error_out=False)

    # Estatisticas
    stats = {
        'pendente': db.session.query(ValidacaoNfPoDfe).filter_by(status='pendente').count(),
        'aprovado': db.session.query(ValidacaoNfPoDfe).filter_by(status='aprovado').count(),
        'bloqueado': db.session.query(ValidacaoNfPoDfe).filter_by(status='bloqueado').count(),
        'consolidado': db.session.query(ValidacaoNfPoDfe).filter_by(status='consolidado').count()
    }

    # Status para filtro
    status_opcoes = [
        {'valor': 'pendente', 'label': 'Pendente'},
        {'valor': 'validando', 'label': 'Validando'},
        {'valor': 'aprovado', 'label': 'Aprovado'},
        {'valor': 'bloqueado', 'label': 'Bloqueado'},
        {'valor': 'consolidado', 'label': 'Consolidado'},
        {'valor': 'erro', 'label': 'Erro'}
    ]

    return render_template(
        'recebimento/validacoes_nf_po.html',
        items=paginacao.items,
        paginacao={
            'page': paginacao.page,
            'pages': paginacao.pages,
            'total': paginacao.total,
            'per_page': per_page,
            'items': paginacao.items
        },
        filtros=filtros,
        stats=stats,
        status_opcoes=status_opcoes
    )


# =============================================================================
# FASE 2: PREVIEW DE CONSOLIDACAO
# =============================================================================

@recebimento_views_bp.route('/preview-consolidacao/<int:validacao_id>')
@login_required
def preview_consolidacao(validacao_id):
    """
    Tela de preview de consolidacao.
    Mostra TODAS as acoes que serao executadas no Odoo antes da aprovacao.
    """
    from app.recebimento.models import ValidacaoNfPoDfe, MatchNfPoItem
    from app.recebimento.services.odoo_po_service import OdooPoService

    # Buscar validacao
    validacao = db.session.get(ValidacaoNfPoDfe,validacao_id) if validacao_id else None
    if not validacao:
        flash('Validacao nao encontrada', 'danger')
        return redirect(url_for('recebimento_views.validacoes_nf_po'))

    if validacao.status != 'aprovado':
        flash('Apenas validacoes aprovadas podem ser consolidadas', 'warning')
        return redirect(url_for('recebimento_views.validacoes_nf_po'))

    # Buscar matches
    matches = db.session.query(MatchNfPoItem).filter_by(validacao_id=validacao_id).all()

    # Simular consolidacao para obter preview das acoes
    try:
        odoo_po_service = OdooPoService()
        preview = odoo_po_service.simular_consolidacao(validacao_id)
    except Exception as e:
        preview = {'erro': str(e), 'acoes': []}

    # Agrupar matches por PO
    pos_envolvidos = {}
    for match in matches:
        if match.odoo_po_id:
            po_id = match.odoo_po_id
            if po_id not in pos_envolvidos:
                pos_envolvidos[po_id] = {
                    'id': po_id,
                    'name': match.odoo_po_name,
                    'itens': []
                }
            pos_envolvidos[po_id]['itens'].append({
                'cod_produto': match.cod_produto_interno,
                'nome_produto': match.nome_produto,
                'qtd_nf': float(match.qtd_nf) if match.qtd_nf else 0,
                'qtd_po': float(match.qtd_po) if match.qtd_po else 0,
                'preco_nf': float(match.preco_nf) if match.preco_nf else 0,
                'preco_po': float(match.preco_po) if match.preco_po else 0
            })

    return render_template(
        'recebimento/preview_consolidacao.html',
        validacao=validacao,
        matches=matches,
        preview=preview,
        pos_envolvidos=list(pos_envolvidos.values())
    )

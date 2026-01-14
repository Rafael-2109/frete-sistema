"""
Views de Validacao Fiscal - Telas HTML
======================================

Rotas:
- GET /operacional/compras/divergencias - Tela de divergencias
- GET /operacional/compras/primeira-compra - Tela de primeira compra
- GET /operacional/compras/perfis-fiscais - Tela de perfis fiscais

Referencia: .claude/references/RECEBIMENTO_MATERIAIS.md
"""

import json
from decimal import Decimal
from datetime import datetime

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.recebimento.models import (
    DivergenciaFiscal,
    CadastroPrimeiraCompra,
    PerfilFiscalProdutoFornecedor
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

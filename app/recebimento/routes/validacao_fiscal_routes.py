"""
Routes de Validacao Fiscal - FASE 1
===================================

Endpoints:
- GET /api/recebimento/validar-nf/<dfe_id> - Valida NF
- GET /api/recebimento/divergencias - Lista divergencias pendentes
- POST /api/recebimento/divergencias/<id>/aprovar - Aprova divergencia
- POST /api/recebimento/divergencias/<id>/rejeitar - Rejeita divergencia
- GET /api/recebimento/primeira-compra - Lista 1a compra pendentes
- POST /api/recebimento/primeira-compra/<id>/validar - Valida 1a compra
- POST /api/recebimento/primeira-compra/<id>/rejeitar - Rejeita 1a compra

Referencia: .claude/references/RECEBIMENTO_MATERIAIS.md
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app.recebimento.models import DivergenciaFiscal, CadastroPrimeiraCompra, PerfilFiscalProdutoFornecedor
from app.recebimento.services.validacao_fiscal_service import ValidacaoFiscalService

validacao_fiscal_bp = Blueprint('validacao_fiscal', __name__, url_prefix='/api/recebimento')


# =============================================================================
# VALIDACAO DE NF
# =============================================================================

@validacao_fiscal_bp.route('/validar-nf/<int:dfe_id>', methods=['GET'])
@login_required
def validar_nf(dfe_id):
    """
    Valida uma NF fiscalmente.
    Retorna divergencias ou registros de 1a compra se houver.
    """
    try:
        service = ValidacaoFiscalService()
        resultado = service.validar_nf(dfe_id)

        return jsonify({
            'sucesso': resultado['status'] != 'erro',
            'status': resultado['status'],
            'dfe_id': dfe_id,
            'linhas_validadas': resultado['linhas_validadas'],
            'divergencias': resultado['divergencias'],
            'primeira_compra': resultado['primeira_compra'],
            'erro': resultado.get('erro')
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# DIVERGENCIAS FISCAIS
# =============================================================================

@validacao_fiscal_bp.route('/divergencias', methods=['GET'])
@login_required
def listar_divergencias():
    """Lista divergencias fiscais pendentes"""
    try:
        status = request.args.get('status', 'pendente')
        limit = request.args.get('limit', 50, type=int)

        query = DivergenciaFiscal.query

        if status != 'todas':
            query = query.filter_by(status=status)

        divergencias = query.order_by(DivergenciaFiscal.criado_em.desc()).limit(limit).all()

        return jsonify({
            'sucesso': True,
            'total': len(divergencias),
            'divergencias': [{
                'id': d.id,
                'odoo_dfe_id': d.odoo_dfe_id,
                'cod_produto': d.cod_produto,
                'nome_produto': d.nome_produto,
                'cnpj_fornecedor': d.cnpj_fornecedor,
                'razao_fornecedor': d.razao_fornecedor,
                'campo': d.campo,
                'campo_label': d.campo_label,
                'valor_esperado': d.valor_esperado,
                'valor_encontrado': d.valor_encontrado,
                'diferenca_percentual': str(d.diferenca_percentual) if d.diferenca_percentual else None,
                'status': d.status,
                'analise_ia': d.analise_ia,
                'criado_em': d.criado_em.isoformat() if d.criado_em else None
            } for d in divergencias]
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_fiscal_bp.route('/divergencias/<int:divergencia_id>/aprovar', methods=['POST'])
@login_required
def aprovar_divergencia(divergencia_id):
    """Aprova uma divergencia fiscal"""
    try:
        data = request.get_json() or {}
        atualizar_baseline = data.get('atualizar_baseline', False)
        justificativa = data.get('justificativa', '')

        service = ValidacaoFiscalService()
        resultado = service.aprovar_divergencia(
            divergencia_id=divergencia_id,
            atualizar_baseline=atualizar_baseline,
            justificativa=justificativa,
            usuario=current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        )

        return jsonify(resultado)

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'mensagem': str(e)
        }), 500


@validacao_fiscal_bp.route('/divergencias/<int:divergencia_id>/rejeitar', methods=['POST'])
@login_required
def rejeitar_divergencia(divergencia_id):
    """Rejeita uma divergencia fiscal"""
    try:
        data = request.get_json() or {}
        justificativa = data.get('justificativa', '')

        if not justificativa:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Justificativa obrigatoria para rejeicao'
            }), 400

        service = ValidacaoFiscalService()
        resultado = service.rejeitar_divergencia(
            divergencia_id=divergencia_id,
            justificativa=justificativa,
            usuario=current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        )

        return jsonify(resultado)

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'mensagem': str(e)
        }), 500


# =============================================================================
# PRIMEIRA COMPRA
# =============================================================================

@validacao_fiscal_bp.route('/primeira-compra', methods=['GET'])
@login_required
def listar_primeira_compra():
    """Lista registros de 1a compra pendentes de validacao"""
    try:
        status = request.args.get('status', 'pendente')
        limit = request.args.get('limit', 50, type=int)

        query = CadastroPrimeiraCompra.query

        if status != 'todas':
            query = query.filter_by(status=status)

        cadastros = query.order_by(CadastroPrimeiraCompra.criado_em.desc()).limit(limit).all()

        return jsonify({
            'sucesso': True,
            'total': len(cadastros),
            'cadastros': [{
                'id': c.id,
                'odoo_dfe_id': c.odoo_dfe_id,
                'cod_produto': c.cod_produto,
                'nome_produto': c.nome_produto,
                'cnpj_fornecedor': c.cnpj_fornecedor,
                'razao_fornecedor': c.razao_fornecedor,
                'ncm': c.ncm,
                'cfop': c.cfop,
                'cst_icms': c.cst_icms,
                'aliquota_icms': str(c.aliquota_icms) if c.aliquota_icms else None,
                'aliquota_icms_st': str(c.aliquota_icms_st) if c.aliquota_icms_st else None,
                'aliquota_ipi': str(c.aliquota_ipi) if c.aliquota_ipi else None,
                'bc_icms': str(c.bc_icms) if c.bc_icms else None,
                'bc_icms_st': str(c.bc_icms_st) if c.bc_icms_st else None,
                'valor_tributos_aprox': str(c.valor_tributos_aprox) if c.valor_tributos_aprox else None,
                'info_complementar': c.info_complementar,
                'status': c.status,
                'criado_em': c.criado_em.isoformat() if c.criado_em else None
            } for c in cadastros]
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_fiscal_bp.route('/primeira-compra/<int:cadastro_id>/validar', methods=['POST'])
@login_required
def validar_primeira_compra(cadastro_id):
    """Valida registro de 1a compra e cria perfil fiscal"""
    try:
        data = request.get_json() or {}
        observacao = data.get('observacao', '')

        service = ValidacaoFiscalService()
        resultado = service.validar_primeira_compra(
            cadastro_id=cadastro_id,
            usuario=current_user.nome if hasattr(current_user, 'nome') else str(current_user.id),
            observacao=observacao
        )

        return jsonify(resultado)

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'mensagem': str(e)
        }), 500


@validacao_fiscal_bp.route('/primeira-compra/<int:cadastro_id>/rejeitar', methods=['POST'])
@login_required
def rejeitar_primeira_compra(cadastro_id):
    """Rejeita registro de 1a compra"""
    try:
        data = request.get_json() or {}
        observacao = data.get('observacao', '')

        if not observacao:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Observacao obrigatoria para rejeicao'
            }), 400

        service = ValidacaoFiscalService()
        resultado = service.rejeitar_primeira_compra(
            cadastro_id=cadastro_id,
            usuario=current_user.nome if hasattr(current_user, 'nome') else str(current_user.id),
            observacao=observacao
        )

        return jsonify(resultado)

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'mensagem': str(e)
        }), 500


# =============================================================================
# PERFIS FISCAIS
# =============================================================================

@validacao_fiscal_bp.route('/perfis-fiscais', methods=['GET'])
@login_required
def listar_perfis_fiscais():
    """Lista perfis fiscais cadastrados"""
    try:
        limit = request.args.get('limit', 50, type=int)
        cod_produto = request.args.get('cod_produto')
        cnpj = request.args.get('cnpj')

        query = PerfilFiscalProdutoFornecedor.query.filter_by(ativo=True)

        if cod_produto:
            query = query.filter(PerfilFiscalProdutoFornecedor.cod_produto.ilike(f'%{cod_produto}%'))
        if cnpj:
            query = query.filter(PerfilFiscalProdutoFornecedor.cnpj_fornecedor.ilike(f'%{cnpj}%'))

        perfis = query.order_by(PerfilFiscalProdutoFornecedor.criado_em.desc()).limit(limit).all()

        return jsonify({
            'sucesso': True,
            'total': len(perfis),
            'perfis': [{
                'id': p.id,
                'cod_produto': p.cod_produto,
                'cnpj_fornecedor': p.cnpj_fornecedor,
                'ncm_esperado': p.ncm_esperado,
                'cfop_esperados': p.cfop_esperados,
                'aliquota_icms_esperada': str(p.aliquota_icms_esperada) if p.aliquota_icms_esperada else None,
                'aliquota_icms_st_esperada': str(p.aliquota_icms_st_esperada) if p.aliquota_icms_st_esperada else None,
                'aliquota_ipi_esperada': str(p.aliquota_ipi_esperada) if p.aliquota_ipi_esperada else None,
                'criado_por': p.criado_por,
                'criado_em': p.criado_em.isoformat() if p.criado_em else None,
                'atualizado_por': p.atualizado_por,
                'atualizado_em': p.atualizado_em.isoformat() if p.atualizado_em else None
            } for p in perfis]
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500

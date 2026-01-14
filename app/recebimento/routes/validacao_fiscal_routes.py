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

import base64

from flask import Blueprint, jsonify, request, Response
from flask_login import login_required, current_user

from app.recebimento.models import DivergenciaFiscal, CadastroPrimeiraCompra, PerfilFiscalProdutoFornecedor
from app.recebimento.services.validacao_fiscal_service import ValidacaoFiscalService
from app.odoo.utils.connection import get_odoo_connection

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

        itens = [{
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

        return jsonify({
            'sucesso': True,
            'total': len(perfis),
            'perfis': itens,
            'itens': itens  # Alias para compatibilidade com frontend
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# ACESSO AO PDF DA NF
# =============================================================================

@validacao_fiscal_bp.route('/dfe/<int:dfe_id>/pdf', methods=['GET'])
@login_required
def obter_pdf_nf(dfe_id):
    """
    Retorna o PDF (DANFE) de uma NF do Odoo.
    Busca o campo l10n_br_pdf_dfe do DFE.
    """
    try:
        odoo = get_odoo_connection()
        if not odoo.authenticate():
            return jsonify({
                'sucesso': False,
                'erro': 'Falha na autenticacao com Odoo'
            }), 500

        # Buscar o PDF do DFE
        registros = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            [['id', '=', dfe_id]],
            fields=['id', 'l10n_br_pdf_dfe', 'l10n_br_pdf_dfe_fname', 'nfe_infnfe_ide_nnf', 'nfe_infnfe_ide_serie'],
            limit=1
        )

        if not registros:
            return jsonify({
                'sucesso': False,
                'erro': f'DFE {dfe_id} nao encontrado no Odoo'
            }), 404

        dfe = registros[0]
        pdf_base64 = dfe.get('l10n_br_pdf_dfe')
        nome_arquivo = dfe.get('l10n_br_pdf_dfe_fname') or f'NF_{dfe.get("nfe_infnfe_ide_nnf", dfe_id)}.pdf'

        if not pdf_base64:
            return jsonify({
                'sucesso': False,
                'erro': f'PDF nao disponivel para DFE {dfe_id}'
            }), 404

        # Decodificar PDF de base64
        try:
            pdf_bytes = base64.b64decode(pdf_base64)
        except Exception as decode_err:
            return jsonify({
                'sucesso': False,
                'erro': f'Erro ao decodificar PDF: {str(decode_err)}'
            }), 500

        # Retornar PDF como download
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'inline; filename="{nome_arquivo}"',
                'Content-Length': str(len(pdf_bytes))
            }
        )

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_fiscal_bp.route('/dfe/<int:dfe_id>/info', methods=['GET'])
@login_required
def obter_info_dfe(dfe_id):
    """
    Retorna informacoes basicas do DFE para exibicao.
    """
    try:
        odoo = get_odoo_connection()
        if not odoo.authenticate():
            return jsonify({
                'sucesso': False,
                'erro': 'Falha na autenticacao com Odoo'
            }), 500

        # Buscar informacoes do DFE
        registros = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            [['id', '=', dfe_id]],
            fields=[
                'id', 'name',
                'nfe_infnfe_ide_nnf', 'nfe_infnfe_ide_serie',
                'nfe_infnfe_emit_cnpj', 'nfe_infnfe_emit_xnome',
                'protnfe_infnfe_chnfe',
                'nfe_infnfe_ide_dhemi',
                'nfe_infnfe_total_icmstot_vnf'
            ],
            limit=1
        )

        if not registros:
            return jsonify({
                'sucesso': False,
                'erro': f'DFE {dfe_id} nao encontrado no Odoo'
            }), 404

        dfe = registros[0]

        return jsonify({
            'sucesso': True,
            'dfe': {
                'id': dfe['id'],
                'name': dfe.get('name'),
                'numero_nf': dfe.get('nfe_infnfe_ide_nnf'),
                'serie_nf': dfe.get('nfe_infnfe_ide_serie'),
                'cnpj_fornecedor': dfe.get('nfe_infnfe_emit_cnpj'),
                'razao_fornecedor': dfe.get('nfe_infnfe_emit_xnome'),
                'chave_nfe': dfe.get('protnfe_infnfe_chnfe'),
                'data_emissao': str(dfe.get('nfe_infnfe_ide_dhemi')) if dfe.get('nfe_infnfe_ide_dhemi') else None,
                'valor_total': dfe.get('nfe_infnfe_total_icmstot_vnf')
            }
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500

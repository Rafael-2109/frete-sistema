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
# IMPORTACAO EXCEL DE PERFIS FISCAIS
# =============================================================================

@validacao_fiscal_bp.route('/perfil-fiscal/importar-excel', methods=['POST'])
@login_required
def importar_perfil_fiscal_excel():
    """
    Importa perfis fiscais de um arquivo Excel.

    Colunas obrigatorias:
    - cnpj_empresa_compradora: CNPJ da empresa compradora (14 digitos)
    - cnpj_fornecedor: CNPJ do fornecedor (14 digitos)
    - cod_produto: Codigo interno do produto
    - ncm_esperado: NCM do produto (8 digitos)
    - cfop_esperados: CFOPs validos separados por virgula (ex: "5101,6101")

    Colunas opcionais:
    - cst_icms_esperado, aliquota_icms_esperada, reducao_bc_icms_esperada
    - aliquota_icms_st_esperada, aliquota_ipi_esperada
    - cst_pis_esperado, aliquota_pis_esperada
    - cst_cofins_esperado, aliquota_cofins_esperada

    Retorna:
    - criados: quantidade de perfis criados
    - atualizados: quantidade de perfis atualizados
    - erros: lista de erros por linha
    """
    import pandas as pd
    from decimal import Decimal, InvalidOperation
    from datetime import datetime, timezone
    import json
    import logging

    logger = logging.getLogger(__name__)

    try:
        # 1. Validar arquivo enviado
        if 'arquivo' not in request.files:
            return jsonify({
                'sucesso': False,
                'erro': 'Nenhum arquivo enviado'
            }), 400

        arquivo = request.files['arquivo']

        if arquivo.filename == '':
            return jsonify({
                'sucesso': False,
                'erro': 'Nenhum arquivo selecionado'
            }), 400

        # 2. Validar extensao
        if not arquivo.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({
                'sucesso': False,
                'erro': 'Arquivo deve ser Excel (.xlsx ou .xls)'
            }), 400

        # 3. Ler Excel
        try:
            df = pd.read_excel(arquivo, dtype=str)
            df = df.fillna('')  # Substituir NaN por string vazia
        except Exception as e:
            return jsonify({
                'sucesso': False,
                'erro': f'Erro ao ler arquivo Excel: {str(e)}'
            }), 400

        # 4. Validar colunas obrigatorias
        colunas_obrigatorias = ['cnpj_empresa_compradora', 'cnpj_fornecedor', 'cod_produto', 'ncm_esperado', 'cfop_esperados']
        colunas_faltando = [c for c in colunas_obrigatorias if c not in df.columns]

        if colunas_faltando:
            return jsonify({
                'sucesso': False,
                'erro': f'Colunas obrigatorias faltando: {", ".join(colunas_faltando)}',
                'colunas_encontradas': list(df.columns),
                'colunas_esperadas': colunas_obrigatorias
            }), 400

        # 5. Processar linha por linha
        from app import db

        criados = 0
        atualizados = 0
        erros = []
        usuario = current_user.nome if hasattr(current_user, 'nome') else 'IMPORT_EXCEL'

        for idx, row in df.iterrows():
            linha_num = idx + 2  # +2 porque Excel comeca em 1 e tem header

            try:
                # 5.1 Validar campos obrigatorios
                empresa_compradora_raw = str(row.get('cnpj_empresa_compradora', '')).strip()
                cnpj_raw = str(row.get('cnpj_fornecedor', '')).strip()
                cod_produto = str(row.get('cod_produto', '')).strip()
                ncm = str(row.get('ncm_esperado', '')).strip()
                cfops_raw = str(row.get('cfop_esperados', '')).strip()

                if not empresa_compradora_raw:
                    erros.append({'linha': linha_num, 'erro': 'cnpj_empresa_compradora vazio'})
                    continue

                if not cnpj_raw:
                    erros.append({'linha': linha_num, 'erro': 'cnpj_fornecedor vazio'})
                    continue

                if not cod_produto:
                    erros.append({'linha': linha_num, 'erro': 'cod_produto vazio'})
                    continue

                # 5.2 Converter empresa compradora (aceita nome ou CNPJ)
                # Mapeamento de nomes para CNPJs
                EMPRESAS_COMPRADORAS = {
                    'NACOM GOYA - CD': '61724241000330',
                    'NACOM GOYA - FB': '61724241000178',
                    'NACOM GOYA - SC': '61724241000259',
                    'LA FAMIGLIA - LF': '18467441000163',
                    # Aliases adicionais
                    'CD': '61724241000330',
                    'FB': '61724241000178',
                    'SC': '61724241000259',
                    'LF': '18467441000163',
                }

                # Verificar se e um nome de empresa
                empresa_upper = empresa_compradora_raw.upper()
                if empresa_upper in [k.upper() for k in EMPRESAS_COMPRADORAS.keys()]:
                    # Buscar o CNPJ correspondente (case-insensitive)
                    cnpj_empresa = None
                    for nome, cnpj_val in EMPRESAS_COMPRADORAS.items():
                        if nome.upper() == empresa_upper:
                            cnpj_empresa = cnpj_val
                            break
                else:
                    # Tentar tratar como CNPJ
                    cnpj_empresa = ''.join(c for c in empresa_compradora_raw if c.isdigit())

                    # Verificar se Excel converteu para notacao cientifica (ex: 6.17E+13)
                    if 'E' in empresa_compradora_raw.upper() and any(c.isdigit() for c in empresa_compradora_raw):
                        erros.append({
                            'linha': linha_num,
                            'erro': f'CNPJ Empresa em notacao cientifica: {empresa_compradora_raw}. Formate a coluna como TEXTO no Excel ou use o nome da empresa (ex: NACOM GOYA - CD).'
                        })
                        continue

                    if len(cnpj_empresa) != 14:
                        erros.append({
                            'linha': linha_num,
                            'erro': f'Empresa compradora invalida: {empresa_compradora_raw}. Use o nome (NACOM GOYA - CD, FB, SC ou LA FAMIGLIA - LF) ou CNPJ formatado/apenas numeros.'
                        })
                        continue

                # 5.3 Limpar CNPJ fornecedor (aceita formatado: 52.502.978/0001-55 ou apenas digitos)
                cnpj = ''.join(c for c in cnpj_raw if c.isdigit())

                # Verificar se Excel converteu para notacao cientifica (ex: 5.25E+13)
                if 'E' in cnpj_raw.upper() or 'e' in cnpj_raw:
                    erros.append({
                        'linha': linha_num,
                        'erro': f'CNPJ Fornecedor em notacao cientifica: {cnpj_raw}. Formate a coluna como TEXTO no Excel.'
                    })
                    continue

                if len(cnpj) != 14:
                    erros.append({
                        'linha': linha_num,
                        'erro': f'CNPJ Fornecedor invalido: {cnpj_raw} (encontrado {len(cnpj)} digitos, esperado 14). Aceita formatado (52.502.978/0001-55) ou apenas numeros.'
                    })
                    continue

                # 5.4 Validar NCM
                ncm_limpo = ''.join(c for c in ncm if c.isdigit())
                if len(ncm_limpo) != 8:
                    erros.append({'linha': linha_num, 'erro': f'NCM invalido: {ncm} (deve ter 8 digitos)'})
                    continue

                # 5.5 Converter CFOPs para JSON
                cfops_list = [c.strip() for c in cfops_raw.split(',') if c.strip()]
                for cfop in cfops_list:
                    cfop_limpo = ''.join(c for c in cfop if c.isdigit())
                    if len(cfop_limpo) != 4:
                        erros.append({'linha': linha_num, 'erro': f'CFOP invalido: {cfop} (deve ter 4 digitos)'})
                        continue
                cfops_json = json.dumps(cfops_list)

                # 5.6 Converter aliquotas opcionais
                def parse_decimal(valor, campo):
                    if not valor or valor == '':
                        return None
                    try:
                        # Substituir virgula por ponto
                        valor_limpo = str(valor).replace(',', '.').strip()
                        return Decimal(valor_limpo)
                    except (InvalidOperation, ValueError):
                        raise ValueError(f'{campo} invalido: {valor}')

                try:
                    aliq_icms = parse_decimal(row.get('aliquota_icms_esperada', ''), 'aliquota_icms_esperada')
                    reducao_bc_icms = parse_decimal(row.get('reducao_bc_icms_esperada', ''), 'reducao_bc_icms_esperada')
                    aliq_icms_st = parse_decimal(row.get('aliquota_icms_st_esperada', ''), 'aliquota_icms_st_esperada')
                    aliq_ipi = parse_decimal(row.get('aliquota_ipi_esperada', ''), 'aliquota_ipi_esperada')
                    aliq_pis = parse_decimal(row.get('aliquota_pis_esperada', ''), 'aliquota_pis_esperada')
                    aliq_cofins = parse_decimal(row.get('aliquota_cofins_esperada', ''), 'aliquota_cofins_esperada')
                except ValueError as ve:
                    erros.append({'linha': linha_num, 'erro': str(ve)})
                    continue

                # 5.7 Campos CST opcionais
                cst_icms = str(row.get('cst_icms_esperado', '')).strip() or None
                cst_pis = str(row.get('cst_pis_esperado', '')).strip() or None
                cst_cofins = str(row.get('cst_cofins_esperado', '')).strip() or None

                # 5.8 Buscar ou criar perfil (chave: empresa + fornecedor + produto)
                perfil = PerfilFiscalProdutoFornecedor.query.filter_by(
                    cnpj_empresa_compradora=cnpj_empresa,
                    cnpj_fornecedor=cnpj,
                    cod_produto=cod_produto
                ).first()

                if perfil:
                    # Atualizar existente
                    perfil.ncm_esperado = ncm_limpo
                    perfil.cfop_esperados = cfops_json
                    perfil.cst_icms_esperado = cst_icms
                    perfil.aliquota_icms_esperada = aliq_icms
                    perfil.reducao_bc_icms_esperada = reducao_bc_icms
                    perfil.aliquota_icms_st_esperada = aliq_icms_st
                    perfil.aliquota_ipi_esperada = aliq_ipi
                    perfil.cst_pis_esperado = cst_pis
                    perfil.aliquota_pis_esperada = aliq_pis
                    perfil.cst_cofins_esperado = cst_cofins
                    perfil.aliquota_cofins_esperada = aliq_cofins
                    perfil.atualizado_por = usuario
                    perfil.atualizado_em = datetime.now(timezone.utc)
                    perfil.ativo = True
                    atualizados += 1
                else:
                    # Criar novo
                    perfil = PerfilFiscalProdutoFornecedor(
                        cnpj_empresa_compradora=cnpj_empresa,
                        cnpj_fornecedor=cnpj,
                        cod_produto=cod_produto,
                        ncm_esperado=ncm_limpo,
                        cfop_esperados=cfops_json,
                        cst_icms_esperado=cst_icms,
                        aliquota_icms_esperada=aliq_icms,
                        reducao_bc_icms_esperada=reducao_bc_icms,
                        aliquota_icms_st_esperada=aliq_icms_st,
                        aliquota_ipi_esperada=aliq_ipi,
                        cst_pis_esperado=cst_pis,
                        aliquota_pis_esperada=aliq_pis,
                        cst_cofins_esperado=cst_cofins,
                        aliquota_cofins_esperada=aliq_cofins,
                        criado_por=usuario,
                        criado_em=datetime.now(timezone.utc),
                        ativo=True
                    )
                    db.session.add(perfil)
                    criados += 1

            except Exception as e:
                erros.append({'linha': linha_num, 'erro': str(e)})
                continue

        # 6. Commit
        db.session.commit()

        logger.info(
            f"Importacao de perfis fiscais: {criados} criados, {atualizados} atualizados, "
            f"{len(erros)} erros - Usuario: {usuario}"
        )

        return jsonify({
            'sucesso': True,
            'criados': criados,
            'atualizados': atualizados,
            'total_processados': criados + atualizados,
            'erros': erros[:50]  # Limitar a 50 erros para nao sobrecarregar resposta
        })

    except Exception as e:
        from app import db
        db.session.rollback()
        logger.error(f"Erro na importacao de perfis fiscais: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_fiscal_bp.route('/perfil-fiscal/template-excel', methods=['GET'])
@login_required
def baixar_template_perfil_fiscal():
    """
    Gera e retorna um template Excel para importacao de perfis fiscais.

    Inclui:
    - Aba "PerfisFiscais" com exemplo de dados
    - Aba "Instrucoes" com explicacao de cada campo
    """
    import pandas as pd
    import io
    from flask import send_file
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Dados de exemplo
        dados_exemplo = [
            {
                'cnpj_empresa_compradora': 'NACOM GOYA - FB',
                'cnpj_fornecedor': '52502978000155',
                'cod_produto': '206030034',
                'ncm_esperado': '73241000',
                'cfop_esperados': '5101,6101',
                'cst_icms_esperado': '00',
                'aliquota_icms_esperada': '18.00',
                'reducao_bc_icms_esperada': '',
                'aliquota_icms_st_esperada': '0.00',
                'aliquota_ipi_esperada': '0.00',
                'cst_pis_esperado': '01',
                'aliquota_pis_esperada': '1.65',
                'cst_cofins_esperado': '01',
                'aliquota_cofins_esperada': '7.60'
            },
            {
                'cnpj_empresa_compradora': 'NACOM GOYA - CD',
                'cnpj_fornecedor': '47950361000162',
                'cod_produto': '207030609',
                'ncm_esperado': '20089900',
                'cfop_esperados': '6101',
                'cst_icms_esperado': '20',
                'aliquota_icms_esperada': '18.00',
                'reducao_bc_icms_esperada': '33.33',
                'aliquota_icms_st_esperada': '0.00',
                'aliquota_ipi_esperada': '5.00',
                'cst_pis_esperado': '01',
                'aliquota_pis_esperada': '1.65',
                'cst_cofins_esperado': '01',
                'aliquota_cofins_esperada': '7.60'
            },
            {
                'cnpj_empresa_compradora': 'LA FAMIGLIA - LF',
                'cnpj_fornecedor': '12345678000199',
                'cod_produto': '208040123',
                'ncm_esperado': '20089900',
                'cfop_esperados': '5102',
                'cst_icms_esperado': '00',
                'aliquota_icms_esperada': '12.00',
                'reducao_bc_icms_esperada': '',
                'aliquota_icms_st_esperada': '0.00',
                'aliquota_ipi_esperada': '0.00',
                'cst_pis_esperado': '01',
                'aliquota_pis_esperada': '1.65',
                'cst_cofins_esperado': '01',
                'aliquota_cofins_esperada': '7.60'
            },
            # Linha vazia para usuario preencher
            {
                'cnpj_empresa_compradora': '',
                'cnpj_fornecedor': '',
                'cod_produto': '',
                'ncm_esperado': '',
                'cfop_esperados': '',
                'cst_icms_esperado': '',
                'aliquota_icms_esperada': '',
                'reducao_bc_icms_esperada': '',
                'aliquota_icms_st_esperada': '',
                'aliquota_ipi_esperada': '',
                'cst_pis_esperado': '',
                'aliquota_pis_esperada': '',
                'cst_cofins_esperado': '',
                'aliquota_cofins_esperada': ''
            }
        ]

        df = pd.DataFrame(dados_exemplo)

        # Criar Excel em memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='PerfisFiscais')

            # Aba de instrucoes
            instrucoes = pd.DataFrame([
                ['INSTRUCOES DE PREENCHIMENTO - PERFIS FISCAIS'],
                [''],
                ['Este arquivo serve para cadastrar os dados fiscais esperados por empresa/fornecedor/produto.'],
                ['Com esses dados, as NFs desses produtos NAO cairao em "Primeira Compra".'],
                [''],
                ['================================================================================'],
                ['COLUNAS DE IDENTIFICACAO (OBRIGATORIAS):'],
                ['================================================================================'],
                ['- cnpj_empresa_compradora: Empresa que recebe a NF (aceita nome ou CNPJ):'],
                ['    * NACOM GOYA - CD (ou apenas CD) -> 61.724.241/0003-30'],
                ['    * NACOM GOYA - FB (ou apenas FB) -> 61.724.241/0001-78'],
                ['    * NACOM GOYA - SC (ou apenas SC) -> 61.724.241/0002-59'],
                ['    * LA FAMIGLIA - LF (ou apenas LF) -> 18.467.441/0001-63'],
                ['- cnpj_fornecedor: CNPJ do fornecedor (aceita formatado: 52.502.978/0001-55 ou apenas numeros)'],
                ['- cod_produto: Codigo interno do produto (ex: 206030034)'],
                [''],
                ['================================================================================'],
                ['COLUNAS VALIDADAS NA NF (preencher para evitar divergencias):'],
                ['================================================================================'],
                ['- ncm_esperado: NCM do produto, 8 digitos (ex: 73241000) -> COMPARADO COM NF'],
                ['- cfop_esperados: CFOPs validos separados por virgula (ex: 5101,6101) -> COMPARADO COM NF'],
                ['- aliquota_icms_esperada: Aliquota ICMS % (ex: 18.00) -> COMPARADO COM NF'],
                ['- reducao_bc_icms_esperada: Reducao da BC do ICMS % (ex: 33.33) -> COMPARADO COM NF'],
                ['    * Deixe vazio se nao houver reducao'],
                ['    * ICMS Final = Aliq ICMS * (1 - Red BC / 100). Ex: 18% * (1 - 33.33%) = 12%'],
                [''],
                ['================================================================================'],
                ['COLUNAS ARMAZENADAS (para referencia futura, nao comparadas atualmente):'],
                ['================================================================================'],
                ['- cst_icms_esperado: CST do ICMS (ex: 00, 10, 20, 60)'],
                ['- aliquota_icms_st_esperada: Aliquota ICMS ST % (ex: 0.00)'],
                ['- aliquota_ipi_esperada: Aliquota IPI % (ex: 5.00)'],
                ['- cst_pis_esperado: CST do PIS (ex: 01, 04, 06)'],
                ['- aliquota_pis_esperada: Aliquota PIS % (ex: 1.65)'],
                ['- cst_cofins_esperado: CST do COFINS (ex: 01, 04, 06)'],
                ['- aliquota_cofins_esperada: Aliquota COFINS % (ex: 7.60)'],
                [''],
                ['================================================================================'],
                ['IMPORTANTE - FORMATACAO:'],
                ['================================================================================'],
                ['- CNPJ: Formate a coluna como TEXTO antes de colar para evitar notacao cientifica'],
                ['    * Ou use o nome da empresa (ex: NACOM GOYA - CD)'],
                ['- Use ponto ou virgula como separador decimal (1.65 ou 1,65)'],
                ['- Se o perfil (empresa+fornecedor+produto) ja existir, sera ATUALIZADO'],
                ['- Se nao existir, sera CRIADO'],
                ['- Linhas com erro serao ignoradas e listadas no resultado'],
                [''],
                ['================================================================================'],
                ['CFOPs COMUNS (COMPRA):'],
                ['================================================================================'],
                ['- 1101/2101: Compra para industrializacao (dentro/fora estado)'],
                ['- 1102/2102: Compra para comercializacao (dentro/fora estado)'],
                ['- 1403/2403: Compra para comercializacao com ST (dentro/fora estado)'],
                ['- 1556/2556: Compra de material para uso/consumo (dentro/fora estado)'],
            ], columns=[''])
            instrucoes.to_excel(writer, index=False, sheet_name='Instrucoes', header=False)

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='template_perfis_fiscais.xlsx'
        )

    except Exception as e:
        logger.error(f"Erro ao gerar template Excel de perfis fiscais: {e}")
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

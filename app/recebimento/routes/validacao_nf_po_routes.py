"""
Routes de Validacao NF x PO - FASE 2
====================================

Endpoints:
- De-Para:
  - GET /api/recebimento/depara - Lista De-Para
  - POST /api/recebimento/depara - Cria De-Para
  - PUT /api/recebimento/depara/<id> - Atualiza De-Para
  - DELETE /api/recebimento/depara/<id> - Remove De-Para
  - POST /api/recebimento/depara/sincronizar-odoo - Sincroniza com Odoo
  - POST /api/recebimento/depara/importar-odoo - Importa do Odoo
  - POST /api/recebimento/depara/importar-excel - Importa de arquivo Excel
  - GET /api/recebimento/depara/template-excel - Baixa template Excel

- Validacao NF x PO:
  - POST /api/recebimento/validar-nf-po/<dfe_id> - Valida NF contra POs
  - GET /api/recebimento/validacoes-nf-po - Lista validacoes
  - GET /api/recebimento/validacoes-nf-po/<id> - Detalhe de validacao

- Divergencias NF x PO:
  - GET /api/recebimento/divergencias-nf-po - Lista divergencias
  - POST /api/recebimento/divergencias-nf-po/<id>/aprovar - Aprova divergencia
  - POST /api/recebimento/divergencias-nf-po/<id>/rejeitar - Rejeita divergencia

- Consolidacao:
  - POST /api/recebimento/consolidar-pos/<validacao_id> - Executa consolidacao
  - POST /api/recebimento/reverter-consolidacao/<validacao_id> - Reverte

Referencia: .claude/plans/wiggly-plotting-newt.md
"""

import logging
import io
from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required, current_user
from decimal import Decimal
import pandas as pd

logger = logging.getLogger(__name__)

from app import db # noqa: E402
from app.recebimento.models import ( # noqa: E402
    ProdutoFornecedorDepara,
    ValidacaoNfPoDfe,
    MatchNfPoItem,
    DivergenciaNfPo,
    RecebimentoFisico,
    PickingRecebimento
)
from app.recebimento.services.depara_service import DeparaService # noqa: E402
from app.recebimento.services.validacao_nf_po_service import ValidacaoNfPoService # noqa: E402
from app.recebimento.services.odoo_po_service import OdooPoService # noqa: E402
from sqlalchemy import or_, case, func # noqa: E402

validacao_nf_po_bp = Blueprint('validacao_nf_po', __name__, url_prefix='/api/recebimento')


# =============================================================================
# AUTOCOMPLETE DE PRODUTOS
# =============================================================================

@validacao_nf_po_bp.route('/autocomplete-produtos', methods=['GET'])
@login_required
def autocomplete_produtos_recebimento():
    """
    Autocomplete para busca de produtos no recebimento.
    Busca na tabela ProdutoFornecedorDepara (De-Para de produtos).

    Retorna produtos DISTINTOS por cod_produto_interno para evitar duplicatas
    (mesmo produto pode ter multiplos fornecedores).

    Query params:
    - termo: string (min 2 caracteres)
    - limit: int (default 20)

    Returns:
    - Lista de {cod_produto, nome_produto}
    """
    try:
        termo = request.args.get('termo', '').strip()
        limit = int(request.args.get('limit', 20))

        # Minimo 2 caracteres para buscar
        if not termo or len(termo) < 2:
            return jsonify([])

        # Buscar produtos DISTINTOS na ProdutoFornecedorDepara
        # Agrupa por cod_produto_interno para evitar duplicatas de fornecedores diferentes
        query = db.session.query(
            ProdutoFornecedorDepara.cod_produto_interno.label('cod_produto'),
            func.min(ProdutoFornecedorDepara.nome_produto_interno).label('nome_produto')
        ).filter(
            ProdutoFornecedorDepara.ativo == True,
            or_(
                ProdutoFornecedorDepara.cod_produto_interno.ilike(f'%{termo}%'),
                ProdutoFornecedorDepara.nome_produto_interno.ilike(f'%{termo}%')
            )
        ).group_by(
            ProdutoFornecedorDepara.cod_produto_interno
        ).order_by(
            # Priorizar codigos que comecam com o termo
            case(
                (ProdutoFornecedorDepara.cod_produto_interno.ilike(f'{termo}%'), 0),
                else_=1
            ),
            ProdutoFornecedorDepara.cod_produto_interno
        ).limit(limit).all()

        resultado = [{
            'cod_produto': row.cod_produto,
            'nome_produto': row.nome_produto or ''
        } for row in query]

        logger.debug(f"[AUTOCOMPLETE-RECEB] Termo: '{termo}' -> {len(resultado)} produtos")

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"[AUTOCOMPLETE-RECEB] Erro: {e}", exc_info=True)
        return jsonify({'erro': str(e)}), 500


# =============================================================================
# DE-PARA
# =============================================================================

@validacao_nf_po_bp.route('/depara', methods=['GET'])
@login_required
def listar_depara():
    """Lista mapeamentos De-Para com filtros."""
    try:
        service = DeparaService()

        resultado = service.listar(
            cnpj_fornecedor=request.args.get('cnpj_fornecedor'),
            cod_produto_fornecedor=request.args.get('cod_produto_fornecedor'),
            cod_produto_interno=request.args.get('cod_produto_interno'),
            ativo=request.args.get('ativo', 'true').lower() == 'true',
            sincronizado_odoo=request.args.get('sincronizado_odoo', type=bool),
            page=request.args.get('page', 1, type=int),
            per_page=request.args.get('per_page', 50, type=int)
        )

        return jsonify({
            'sucesso': True,
            **resultado
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/depara/<int:depara_id>', methods=['GET'])
@login_required
def buscar_depara(depara_id):
    """Busca De-Para por ID."""
    try:
        service = DeparaService()
        resultado = service.buscar_por_id(depara_id)

        if not resultado:
            return jsonify({
                'sucesso': False,
                'erro': f'De-Para {depara_id} nao encontrado'
            }), 404

        return jsonify({
            'sucesso': True,
            'depara': resultado
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/depara', methods=['POST'])
@login_required
def criar_depara():
    """Cria novo mapeamento De-Para."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'sucesso': False,
                'erro': 'Dados nao fornecidos'
            }), 400

        # Validar campos obrigatorios
        campos_obrigatorios = ['cnpj_fornecedor', 'cod_produto_fornecedor', 'cod_produto_interno']
        for campo in campos_obrigatorios:
            if not data.get(campo):
                return jsonify({
                    'sucesso': False,
                    'erro': f'Campo obrigatorio: {campo}'
                }), 400

        service = DeparaService()

        # Converter fator se fornecido
        fator = Decimal('1.0000')
        if data.get('fator_conversao'):
            fator = Decimal(str(data['fator_conversao']))

        resultado = service.criar(
            cnpj_fornecedor=data['cnpj_fornecedor'],
            cod_produto_fornecedor=data['cod_produto_fornecedor'],
            cod_produto_interno=data['cod_produto_interno'],
            razao_fornecedor=data.get('razao_fornecedor'),
            descricao_produto_fornecedor=data.get('descricao_produto_fornecedor'),
            nome_produto_interno=data.get('nome_produto_interno'),
            odoo_product_id=data.get('odoo_product_id'),
            um_fornecedor=data.get('um_fornecedor'),
            um_interna=data.get('um_interna', 'UNITS'),
            fator_conversao=fator,
            criado_por=current_user.nome if current_user else None
        )

        return jsonify({
            'sucesso': True,
            'depara': resultado
        }), 201

    except ValueError as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 400

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/depara/<int:depara_id>', methods=['PUT'])
@login_required
def atualizar_depara(depara_id):
    """Atualiza mapeamento De-Para."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'sucesso': False,
                'erro': 'Dados nao fornecidos'
            }), 400

        service = DeparaService()

        # Converter fator se fornecido
        fator = None
        if data.get('fator_conversao') is not None:
            fator = Decimal(str(data['fator_conversao']))

        resultado = service.atualizar(
            depara_id=depara_id,
            cod_produto_interno=data.get('cod_produto_interno'),
            nome_produto_interno=data.get('nome_produto_interno'),
            odoo_product_id=data.get('odoo_product_id'),
            um_fornecedor=data.get('um_fornecedor'),
            um_interna=data.get('um_interna'),
            fator_conversao=fator,
            ativo=data.get('ativo'),
            atualizado_por=current_user.nome if current_user else None
        )

        return jsonify({
            'sucesso': True,
            'depara': resultado
        })

    except ValueError as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 404

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/depara/<int:depara_id>', methods=['DELETE'])
@login_required
def excluir_depara(depara_id):
    """
    Exclui (desativa) mapeamento De-Para.
    Tambem sincroniza a exclusao com o Odoo (remove product.supplierinfo).
    """
    try:
        service = DeparaService()
        resultado = service.excluir(depara_id)

        return jsonify({
            'sucesso': True,
            'mensagem': f'De-Para {depara_id} desativado',
            **resultado
        })

    except ValueError as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 404

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/depara/<int:depara_id>/reativar', methods=['PUT'])
@login_required
def reativar_depara(depara_id):
    """
    Reativa um mapeamento De-Para que estava inativo (soft deleted).
    Tambem tenta sincronizar com Odoo se tiver odoo_product_id.
    """
    try:
        item = db.session.get(ProdutoFornecedorDepara, depara_id)

        if not item:
            return jsonify({
                'sucesso': False,
                'erro': f'De-Para {depara_id} nao encontrado'
            }), 404

        if item.ativo:
            return jsonify({
                'sucesso': False,
                'erro': f'De-Para {depara_id} ja esta ativo'
            }), 400

        # Reativar
        item.ativo = True
        item.sincronizado_odoo = False  # Marcar para re-sincronizar
        item.atualizado_por = current_user.nome if current_user else None
        item.atualizado_em = db.func.now()

        db.session.commit()

        resultado = {
            'sucesso': True,
            'mensagem': f'De-Para {depara_id} reativado com sucesso',
            'depara_id': depara_id,
            'cnpj_fornecedor': item.cnpj_fornecedor,
            'cod_produto_fornecedor': item.cod_produto_fornecedor,
            'cod_produto_interno': item.cod_produto_interno
        }

        # Tentar sincronizar com Odoo se tiver produto vinculado
        if item.odoo_product_id:
            try:
                service = DeparaService()
                sync_result = service.sincronizar_para_odoo(depara_id)
                resultado['odoo_sync'] = sync_result
                logger.info(f"De-Para {depara_id} reativado e sincronizado com Odoo")
            except Exception as sync_error:
                logger.warning(
                    f"De-Para {depara_id} reativado mas falhou sync Odoo: {sync_error}"
                )
                resultado['odoo_sync'] = {'sucesso': False, 'erro': str(sync_error)}
        else:
            resultado['odoo_sync'] = None

        # Reprocessar divergencias relacionadas a este De-Para
        try:
            service = DeparaService()
            reprocess = service._reprocessar_divergencias_relacionadas(
                item.cnpj_fornecedor,
                item.cod_produto_fornecedor
            )
            resultado['reprocessamento'] = reprocess
            if reprocess.get('revalidados', 0) > 0:
                logger.info(
                    f"De-Para {depara_id} reativado - "
                    f"{reprocess['revalidados']} DFE(s) revalidados"
                )
        except Exception as e:
            logger.warning(
                f"Erro ao reprocessar divergencias para De-Para {depara_id}: {e}"
            )
            resultado['reprocessamento'] = {'erro': str(e)}

        return jsonify(resultado)

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao reativar De-Para {depara_id}: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/depara/sincronizar-odoo', methods=['POST'])
@login_required
def sincronizar_depara_odoo():
    """Sincroniza De-Para(s) para o Odoo."""
    try:
        data = request.get_json() or {}
        depara_id = data.get('depara_id')

        if not depara_id:
            return jsonify({
                'sucesso': False,
                'erro': 'depara_id nao fornecido'
            }), 400

        service = DeparaService()
        resultado = service.sincronizar_para_odoo(depara_id)

        return jsonify({
            'sucesso': True,
            **resultado
        })

    except ValueError as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 400

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/depara/importar-odoo', methods=['POST'])
@login_required
def importar_depara_odoo():
    """Importa De-Para do Odoo (product.supplierinfo)."""
    try:
        data = request.get_json() or {}

        service = DeparaService()
        resultado = service.importar_do_odoo(
            cnpj_fornecedor=data.get('cnpj_fornecedor'),
            limit=data.get('limit', 100)
        )

        return jsonify({
            'sucesso': True,
            **resultado
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/depara/sugerir-fator', methods=['GET'])
@login_required
def sugerir_fator_conversao():
    """Sugere fator de conversao com base na UM."""
    try:
        um_fornecedor = request.args.get('um_fornecedor', '')

        service = DeparaService()
        fator = service.sugerir_fator_conversao(um_fornecedor)

        return jsonify({
            'sucesso': True,
            'um_fornecedor': um_fornecedor,
            'fator_sugerido': float(fator),
            'descricao': f'{um_fornecedor} = {fator} unidades' if fator > 1 else 'Sem conversao necessaria'
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/depara/importar-excel', methods=['POST'])
@login_required
def importar_depara_excel():
    """
    Importa De-Para de um arquivo Excel.

    Colunas esperadas:
    - cnpj_fornecedor (obrigatorio)
    - cod_produto_fornecedor (obrigatorio)
    - cod_produto_interno (obrigatorio)
    - descricao_produto_fornecedor (opcional)
    - um_fornecedor (opcional) - Ex: PL, ML, MI, MIL
    - fator_conversao (opcional) - Default: 1.0

    Retorna:
    - total_processados
    - criados
    - atualizados
    - erros (lista com detalhes)
    """
    try:
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

        # Verificar extensao
        if not arquivo.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({
                'sucesso': False,
                'erro': 'Arquivo deve ser Excel (.xlsx ou .xls)'
            }), 400

        # Ler Excel
        try:
            df = pd.read_excel(arquivo, dtype=str)
            df = df.fillna('')  # Substituir NaN por string vazia
        except Exception as e:
            return jsonify({
                'sucesso': False,
                'erro': f'Erro ao ler arquivo Excel: {str(e)}'
            }), 400

        # Validar colunas obrigatorias
        colunas_obrigatorias = ['cnpj_fornecedor', 'cod_produto_fornecedor', 'cod_produto_interno']
        colunas_faltando = [c for c in colunas_obrigatorias if c not in df.columns]
        if colunas_faltando:
            return jsonify({
                'sucesso': False,
                'erro': f'Colunas obrigatorias faltando: {", ".join(colunas_faltando)}',
                'colunas_encontradas': list(df.columns)
            }), 400

        # Converter DataFrame para lista de dicts
        dados = df.to_dict('records')

        if not dados:
            return jsonify({
                'sucesso': False,
                'erro': 'Arquivo vazio ou sem dados validos'
            }), 400

        # Obter parametro de sincronizacao
        auto_sync = request.form.get('auto_sync_odoo', 'true').lower() == 'true'

        # Processar importacao
        service = DeparaService()
        resultado = service.importar_lote_excel(
            dados=dados,
            usuario=current_user.nome if hasattr(current_user, 'nome') else str(current_user.id),
            auto_sync_odoo=auto_sync
        )

        return jsonify({
            'sucesso': True,
            **resultado
        })

    except Exception as e:
        logger.error(f"Erro ao importar De-Para do Excel: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/depara/template-excel', methods=['GET'])
@login_required
def baixar_template_depara_excel():
    """
    Gera e retorna um template Excel para importacao de De-Para.

    Colunas:
    - cnpj_fornecedor (obrigatorio)
    - cod_produto_fornecedor (obrigatorio)
    - cod_produto_interno (obrigatorio)
    - descricao_produto_fornecedor (opcional)
    - um_fornecedor (opcional)
    - fator_conversao (opcional)
    """
    try:
        # Criar DataFrame com exemplo
        dados_exemplo = [
            {
                'cnpj_fornecedor': '61067161001835',
                'cod_produto_fornecedor': '93060201707198',
                'cod_produto_interno': '206200004',
                'descricao_produto_fornecedor': 'PL 2086 PCS POTE AZ200 ALTO',
                'um_fornecedor': 'PL',
                'fator_conversao': 2086
            },
            {
                'cnpj_fornecedor': '',
                'cod_produto_fornecedor': '',
                'cod_produto_interno': '',
                'descricao_produto_fornecedor': '',
                'um_fornecedor': '',
                'fator_conversao': ''
            }
        ]

        df = pd.DataFrame(dados_exemplo)

        # Criar arquivo Excel em memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='DePara')

            # Adicionar aba de instrucoes
            instrucoes = pd.DataFrame([
                ['INSTRUCOES DE PREENCHIMENTO'],
                [''],
                ['Colunas Obrigatorias:'],
                ['- cnpj_fornecedor: CNPJ do fornecedor (apenas numeros ou com pontuacao)'],
                ['- cod_produto_fornecedor: Codigo do produto na NF do fornecedor'],
                ['- cod_produto_interno: Codigo interno do produto (default_code no Odoo)'],
                [''],
                ['Colunas Opcionais:'],
                ['- descricao_produto_fornecedor: Descricao do produto na NF do fornecedor'],
                ['- um_fornecedor: Unidade de medida do fornecedor (ex: PL, ML, MI, KG)'],
                ['- fator_conversao: Quantas unidades internas = 1 unidade do fornecedor'],
                ['  Exemplo: 1 PL = 2086 unidades -> fator_conversao = 2086'],
                [''],
                ['IMPORTANTE:'],
                ['- Se fator_conversao nao for informado, sera usado 1.0'],
                ['- O sistema buscara automaticamente o produto no Odoo pelo cod_produto_interno'],
                ['- Duplicatas (mesmo CNPJ + cod_produto_fornecedor) serao atualizadas'],
            ], columns=[''])
            instrucoes.to_excel(writer, index=False, sheet_name='Instrucoes', header=False)

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='template_depara_fornecedor.xlsx'
        )

    except Exception as e:
        logger.error(f"Erro ao gerar template Excel: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# VALIDACAO NF x PO
# =============================================================================

@validacao_nf_po_bp.route('/validar-nf-po/<int:dfe_id>', methods=['POST'])
@login_required
def validar_nf_po(dfe_id):
    """
    Valida uma NF contra POs do fornecedor.

    Retorna:
    - status: 'aprovado', 'bloqueado', 'erro'
    - Se aprovado: lista de POs para consolidar
    - Se bloqueado: lista de divergencias
    """
    try:
        service = ValidacaoNfPoService()
        resultado = service.validar_dfe(dfe_id)

        return jsonify({
            'sucesso': resultado['status'] != 'erro',
            **resultado
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'status': 'erro',
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/validacoes-nf-po', methods=['GET'])
@login_required
def listar_validacoes_nf_po():
    """Lista validacoes NF x PO com filtros."""
    try:
        service = ValidacaoNfPoService()

        resultado = service.listar_validacoes(
            status=request.args.get('status'),
            cnpj_fornecedor=request.args.get('cnpj_fornecedor'),
            page=request.args.get('page', 1, type=int),
            per_page=request.args.get('per_page', 50, type=int)
        )

        return jsonify({
            'sucesso': True,
            **resultado
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/validacoes-nf-po/<int:validacao_id>', methods=['GET'])
@login_required
def detalhe_validacao_nf_po(validacao_id):
    """Retorna detalhes de uma validacao NF x PO."""
    try:
        validacao = db.session.get(ValidacaoNfPoDfe,validacao_id) if validacao_id else None

        if not validacao:
            return jsonify({
                'sucesso': False,
                'erro': f'Validacao {validacao_id} nao encontrada'
            }), 404

        # Buscar matches
        matches = db.session.query(MatchNfPoItem).filter_by(validacao_id=validacao_id).all()

        # Buscar divergencias
        divergencias = db.session.query(DivergenciaNfPo).filter_by(validacao_id=validacao_id).all()

        # Buscar dados de recebimento fisico
        recebimento = RecebimentoFisico.query.filter_by(
            validacao_id=validacao_id
        ).order_by(RecebimentoFisico.criado_em.desc()).first()

        # Se nao tiver RecebimentoFisico, buscar PickingRecebimento via PO
        picking = None
        if not recebimento:
            po_id = validacao.po_consolidado_id or validacao.odoo_po_vinculado_id
            if po_id:
                picking = PickingRecebimento.query.filter_by(
                    odoo_purchase_order_id=po_id
                ).order_by(PickingRecebimento.write_date.desc()).first()

        # Montar dados de recebimento
        recebimento_data = None
        if recebimento or picking:
            recebimento_data = {
                'tem_recebimento': recebimento is not None,
                'recebimento_id': recebimento.id if recebimento else None,
                'status': recebimento.status if recebimento else None,
                'odoo_status': recebimento.odoo_status if recebimento else (picking.state if picking else None),
                'picking_name': recebimento.odoo_picking_name if recebimento else (picking.odoo_picking_name if picking else None),
                'picking_id': recebimento.odoo_picking_id if recebimento else (picking.odoo_picking_id if picking else None),
                'processado_em': recebimento.processado_em.strftime('%d/%m/%Y %H:%M') if recebimento and recebimento.processado_em else None,
                'erro_mensagem': recebimento.erro_mensagem if recebimento else None
            }

        return jsonify({
            'sucesso': True,
            'validacao': {
                'id': validacao.id,
                'odoo_dfe_id': validacao.odoo_dfe_id,
                'numero_nf': validacao.numero_nf,
                'serie_nf': validacao.serie_nf,
                'chave_nfe': validacao.chave_nfe,
                'cnpj_fornecedor': validacao.cnpj_fornecedor,
                'razao_fornecedor': validacao.razao_fornecedor,
                'data_nf': str(validacao.data_nf) if validacao.data_nf else None,
                'valor_total_nf': float(validacao.valor_total_nf) if validacao.valor_total_nf else None,
                'status': validacao.status,
                'total_itens': validacao.total_itens,
                'itens_match': validacao.itens_match,
                'itens_sem_depara': validacao.itens_sem_depara,
                'itens_sem_po': validacao.itens_sem_po,
                'itens_preco_diverge': validacao.itens_preco_diverge,
                'itens_data_diverge': validacao.itens_data_diverge,
                'itens_qtd_diverge': validacao.itens_qtd_diverge,
                'po_consolidado_id': validacao.po_consolidado_id,
                'po_consolidado_name': validacao.po_consolidado_name,
                'odoo_po_vinculado_id': validacao.odoo_po_vinculado_id,
                'odoo_po_vinculado_name': validacao.odoo_po_vinculado_name,
                'odoo_po_fiscal_id': validacao.odoo_po_fiscal_id,
                'odoo_po_fiscal_name': validacao.odoo_po_fiscal_name,
                'pos_vinculados_importados_em': validacao.pos_vinculados_importados_em.strftime('%d/%m/%Y %H:%M') if validacao.pos_vinculados_importados_em else None,
                'criado_em': validacao.criado_em.isoformat() if validacao.criado_em else None,
                'validado_em': validacao.validado_em.isoformat() if validacao.validado_em else None,
                'consolidado_em': validacao.consolidado_em.isoformat() if validacao.consolidado_em else None
            },
            'matches': [{
                'id': m.id,
                'odoo_dfe_line_id': m.odoo_dfe_line_id,
                'cod_produto_fornecedor': m.cod_produto_fornecedor,
                'cod_produto_interno': m.cod_produto_interno,
                'nome_produto_interno': m.nome_produto_interno,  # Nome interno (nosso nome)
                'nome_produto': m.nome_produto,
                'qtd_nf': float(m.qtd_nf) if m.qtd_nf else None,
                'preco_nf': float(m.preco_nf) if m.preco_nf else None,
                'um_nf': m.um_nf,
                'fator_conversao': float(m.fator_conversao) if m.fator_conversao else None,
                'odoo_po_id': m.odoo_po_id,
                'odoo_po_name': m.odoo_po_name,
                'qtd_po': float(m.qtd_po) if m.qtd_po else None,
                'preco_po': float(m.preco_po) if m.preco_po else None,
                'data_po': m.data_po.strftime('%d/%m/%Y') if m.data_po else None,
                'status_match': m.status_match,
                'motivo_bloqueio': m.motivo_bloqueio
            } for m in matches],
            'divergencias': [{
                'id': d.id,
                'odoo_dfe_line_id': d.odoo_dfe_line_id,
                'cod_produto_fornecedor': d.cod_produto_fornecedor,
                'cod_produto_interno': d.cod_produto_interno,
                'nome_produto': d.nome_produto,
                'tipo_divergencia': d.tipo_divergencia,
                'campo_label': d.campo_label,
                'valor_nf': d.valor_nf,
                'valor_po': d.valor_po,
                'diferenca_percentual': float(d.diferenca_percentual) if d.diferenca_percentual else None,
                'odoo_po_name': d.odoo_po_name,
                'status': d.status,
                'resolucao': d.resolucao,
                'justificativa': d.justificativa
            } for d in divergencias],
            'recebimento': recebimento_data
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# DIVERGENCIAS NF x PO
# =============================================================================

@validacao_nf_po_bp.route('/divergencias-nf-po', methods=['GET'])
@login_required
def listar_divergencias_nf_po():
    """Lista divergencias NF x PO com filtros."""
    try:
        service = ValidacaoNfPoService()

        resultado = service.listar_divergencias(
            validacao_id=request.args.get('validacao_id', type=int),
            status=request.args.get('status', 'pendente'),
            tipo_divergencia=request.args.get('tipo_divergencia'),
            page=request.args.get('page', 1, type=int),
            per_page=request.args.get('per_page', 50, type=int)
        )

        return jsonify({
            'sucesso': True,
            **resultado
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# Tipos de divergencia que podem ser aprovados manualmente
# CRITICO: Outros tipos devem usar acoes especificas (criar De-Para, ajustar PO, etc.)
TIPOS_APROVACAO_PERMITIDA = ['quantidade_tolerancia', 'data_entrega']


@validacao_nf_po_bp.route('/divergencias-nf-po/<int:divergencia_id>/criar-depara', methods=['POST'])
@login_required
def criar_depara_para_divergencia(divergencia_id):
    """
    Cria De-Para para uma divergencia tipo 'sem_depara'.

    IMPORTANTE: Este endpoint NAO aprova a divergencia.
    Apenas cria o mapeamento De-Para e sincroniza com Odoo.
    Apos criar, dispara revalidacao automatica do DFE.

    Body JSON esperado:
    {
        "cod_produto_interno": "ABC123",
        "nome_produto_interno": "Produto XYZ",
        "odoo_product_id": 12345,
        "um_fornecedor": "ML",
        "fator_conversao": 1000,
        "justificativa": "Motivo da criacao"
    }
    """
    try:
        data = request.get_json() or {}

        divergencia = db.session.get(DivergenciaNfPo,divergencia_id) if divergencia_id else None

        if not divergencia:
            return jsonify({
                'sucesso': False,
                'erro': f'Divergencia {divergencia_id} nao encontrada'
            }), 404

        # Validar que e divergencia tipo sem_depara
        if divergencia.tipo_divergencia != 'sem_depara':
            return jsonify({
                'sucesso': False,
                'erro': f'Este endpoint e apenas para divergencias tipo "sem_depara". '
                        f'Tipo atual: {divergencia.tipo_divergencia}'
            }), 400

        # Validar campos obrigatorios
        cod_produto_interno = data.get('cod_produto_interno', '').strip()
        if not cod_produto_interno:
            return jsonify({
                'sucesso': False,
                'erro': 'Campo obrigatorio: cod_produto_interno'
            }), 400

        # Salvar dados da divergencia em variaveis locais ANTES da criacao
        # (o objeto pode ser deletado pela revalidacao interna do service via cascade)
        cnpj_fornecedor = divergencia.cnpj_fornecedor
        cod_produto_fornecedor = divergencia.cod_produto_fornecedor
        razao_fornecedor = divergencia.razao_fornecedor
        nome_produto = divergencia.nome_produto

        # Criar De-Para via service
        # NOTA: depara_service.criar() ja executa revalidacao internamente
        # via _reprocessar_divergencias_relacionadas()
        depara_service = DeparaService()

        try:
            depara = depara_service.criar(
                cnpj_fornecedor=cnpj_fornecedor,
                cod_produto_fornecedor=cod_produto_fornecedor,
                cod_produto_interno=cod_produto_interno,
                razao_fornecedor=razao_fornecedor,
                descricao_produto_fornecedor=nome_produto,
                nome_produto_interno=data.get('nome_produto_interno'),
                odoo_product_id=data.get('odoo_product_id'),
                um_fornecedor=data.get('um_fornecedor'),
                fator_conversao=Decimal(str(data.get('fator_conversao', 1))),
                criado_por=current_user.nome if current_user else None
            )
        except ValueError as e:
            return jsonify({
                'sucesso': False,
                'erro': str(e)
            }), 400

        # Sincronizar com Odoo (product.supplierinfo)
        sync_resultado = None
        try:
            if depara and depara.get('id'):
                sync_resultado = depara_service.sincronizar_para_odoo(depara['id'])
        except Exception as e:
            logging.getLogger(__name__).warning(
                f"Falha ao sincronizar De-Para {depara.get('id')} com Odoo: {e}"
            )

        # Resultado da revalidacao ja veio dentro de depara_service.criar()
        # via _reprocessar_divergencias_relacionadas() -> validar_dfe()
        reprocessamento = depara.get('reprocessamento', {}) if depara else {}
        revalidacao_status = 'nao_executada'
        if reprocessamento.get('resultados'):
            primeiro = reprocessamento['resultados'][0]
            revalidacao_status = primeiro.get('status', primeiro.get('erro', 'nao_executada'))

        return jsonify({
            'sucesso': True,
            'mensagem': 'De-Para criado com sucesso! A NF sera revalidada automaticamente.',
            'depara': depara,
            'sincronizado_odoo': sync_resultado.get('sucesso') if sync_resultado else False,
            'revalidacao': revalidacao_status
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/divergencias-nf-po/<int:divergencia_id>/aprovar', methods=['POST'])
@login_required
def aprovar_divergencia_nf_po(divergencia_id):
    """
    Aprova uma divergencia NF x PO.

    CRITICO: Apenas certos tipos de divergencia podem ser aprovados manualmente.
    Tipos permitidos: quantidade_tolerancia, data_entrega

    Tipos NAO permitidos (devem usar acoes especificas):
    - sem_depara: usar endpoint /criar-depara
    - sem_po: criar PO no Odoo primeiro
    - preco: ajustar preco no PO
    - quantidade (>10%): ajustar quantidade no PO
    """
    try:
        data = request.get_json() or {}

        divergencia = db.session.get(DivergenciaNfPo,divergencia_id) if divergencia_id else None

        if not divergencia:
            return jsonify({
                'sucesso': False,
                'erro': f'Divergencia {divergencia_id} nao encontrada'
            }), 404

        if divergencia.status != 'pendente':
            return jsonify({
                'sucesso': False,
                'erro': f'Divergencia ja foi {divergencia.status}'
            }), 400

        # CRITICO: Validar se tipo pode ser aprovado manualmente
        if divergencia.tipo_divergencia not in TIPOS_APROVACAO_PERMITIDA:
            mensagens_tipo = {
                'sem_depara': 'Use o botao "Criar De-Para" para resolver esta divergencia.',
                'sem_po': 'Crie um Pedido de Compra no Odoo primeiro.',
                'preco': 'Ajuste o preco no Pedido de Compra no Odoo.',
                'quantidade': 'Quantidade excede tolerancia de 10%. Ajuste o PO no Odoo.'
            }
            msg_especifica = mensagens_tipo.get(
                divergencia.tipo_divergencia,
                'Esta divergencia requer acao especifica no sistema.'
            )
            return jsonify({
                'sucesso': False,
                'erro': f'Divergencia tipo "{divergencia.tipo_divergencia}" nao pode ser aprovada manualmente. '
                        f'{msg_especifica}'
            }), 400

        # Validar justificativa (obrigatoria)
        justificativa = data.get('justificativa', '').strip()
        if not justificativa:
            return jsonify({
                'sucesso': False,
                'erro': 'Justificativa e obrigatoria para aprovar divergencia'
            }), 400

        # Atualizar
        divergencia.status = 'aprovada'
        divergencia.resolucao = data.get('resolucao', 'aprovar_manual')
        divergencia.justificativa = justificativa
        divergencia.resolvido_por = current_user.nome if current_user else None
        divergencia.resolvido_em = db.func.now()

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': f'Divergencia {divergencia_id} aprovada'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/divergencias-nf-po/<int:divergencia_id>/rejeitar', methods=['POST'])
@login_required
def rejeitar_divergencia_nf_po(divergencia_id):
    """Rejeita uma divergencia NF x PO."""
    try:
        data = request.get_json() or {}

        divergencia = db.session.get(DivergenciaNfPo,divergencia_id) if divergencia_id else None

        if not divergencia:
            return jsonify({
                'sucesso': False,
                'erro': f'Divergencia {divergencia_id} nao encontrada'
            }), 404

        if divergencia.status != 'pendente':
            return jsonify({
                'sucesso': False,
                'erro': f'Divergencia ja foi {divergencia.status}'
            }), 400

        # Atualizar
        divergencia.status = 'rejeitada'
        divergencia.resolucao = 'rejeitar'
        divergencia.justificativa = data.get('justificativa')
        divergencia.resolvido_por = current_user.nome if current_user else None
        divergencia.resolvido_em = db.func.now()

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': f'Divergencia {divergencia_id} rejeitada'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# CONSOLIDACAO
# =============================================================================

@validacao_nf_po_bp.route('/consolidar-pos/<int:validacao_id>', methods=['POST'])
@login_required
def consolidar_pos(validacao_id):
    """
    Executa consolidacao de POs apos validacao aprovada.

    Requer validacao com status 'aprovado'.
    """
    try:
        data = request.get_json() or {}

        validacao = db.session.get(ValidacaoNfPoDfe,validacao_id) if validacao_id else None

        if not validacao:
            return jsonify({
                'sucesso': False,
                'erro': f'Validacao {validacao_id} nao encontrada'
            }), 404

        if validacao.status != 'aprovado':
            return jsonify({
                'sucesso': False,
                'erro': f'Validacao nao esta aprovada. Status: {validacao.status}'
            }), 400

        # Buscar matches para montar lista de POs
        matches = db.session.query(MatchNfPoItem).filter_by(
            validacao_id=validacao_id,
            status_match='match'
        ).all()

        if not matches:
            return jsonify({
                'sucesso': False,
                'erro': 'Nenhum match encontrado para consolidar'
            }), 400

        # Agrupar por PO
        pos_dict = {}
        for m in matches:
            if not m.odoo_po_id:
                continue

            if m.odoo_po_id not in pos_dict:
                pos_dict[m.odoo_po_id] = {
                    'po_id': m.odoo_po_id,
                    'po_name': m.odoo_po_name,
                    'linhas': [],
                    'valor_total': 0
                }

            pos_dict[m.odoo_po_id]['linhas'].append({
                'po_line_id': m.odoo_po_line_id,
                'qtd_nf': m.qtd_nf,
                'qtd_po': m.qtd_po,
                'preco': m.preco_nf
            })
            pos_dict[m.odoo_po_id]['valor_total'] += (m.qtd_nf or 0) * (m.preco_nf or 0)

        # Ordenar por valor (maior primeiro)
        pos_para_consolidar = sorted(
            pos_dict.values(),
            key=lambda x: x['valor_total'],
            reverse=True
        )

        # Extrair quantidades customizadas (Fase 4 - edicao de qtd)
        quantidades_customizadas = data.get('quantidades')

        # Executar consolidacao
        service = OdooPoService()
        resultado = service.consolidar_pos(
            validacao_id=validacao_id,
            pos_para_consolidar=pos_para_consolidar,
            usuario=current_user.nome if current_user else None,
            quantidades_customizadas=quantidades_customizadas
        )

        if resultado['sucesso']:
            return jsonify({
                'sucesso': True,
                **resultado
            })
        else:
            return jsonify({
                'sucesso': False,
                'erro': resultado.get('erro')
            }), 500

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/reverter-consolidacao/<int:validacao_id>', methods=['POST'])
@login_required
def reverter_consolidacao(validacao_id):
    """
    Reverte uma consolidacao executada.

    CUIDADO: Operacao pode nao ser 100% reversivel.
    """
    try:
        service = OdooPoService()
        resultado = service.reverter_consolidacao(
            validacao_id=validacao_id,
            usuario=current_user.nome if current_user else None
        )

        if resultado['sucesso']:
            return jsonify({
                'sucesso': True,
                **resultado
            })
        else:
            return jsonify({
                'sucesso': False,
                'erro': resultado.get('erro')
            }), 500

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# UTILITARIOS
# =============================================================================

@validacao_nf_po_bp.route('/buscar-produto-odoo', methods=['GET'])
@login_required
def buscar_produto_odoo():
    """Busca produto no Odoo pelo codigo interno."""
    try:
        cod_produto = request.args.get('cod_produto', '')

        if not cod_produto:
            return jsonify({
                'sucesso': False,
                'erro': 'cod_produto nao fornecido'
            }), 400

        service = DeparaService()
        produto = service.buscar_produto_odoo(cod_produto)

        if not produto:
            return jsonify({
                'sucesso': False,
                'erro': f'Produto {cod_produto} nao encontrado no Odoo'
            }), 404

        return jsonify({
            'sucesso': True,
            'produto': produto
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_nf_po_bp.route('/buscar-pos-fornecedor', methods=['GET'])
@login_required
def buscar_pos_fornecedor():
    """Busca POs de um fornecedor."""
    try:
        cnpj = request.args.get('cnpj', '')

        if not cnpj:
            return jsonify({
                'sucesso': False,
                'erro': 'cnpj nao fornecido'
            }), 400

        service = OdooPoService()
        pos = service.buscar_pos_por_fornecedor(
            cnpj_fornecedor=cnpj,
            apenas_com_saldo=request.args.get('apenas_com_saldo', 'true').lower() == 'true'
        )

        return jsonify({
            'sucesso': True,
            'total': len(pos),
            'pos': pos
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# POs CANDIDATOS PARA DFE
# =============================================================================

@validacao_nf_po_bp.route('/dfe/<int:dfe_id>/pos-candidatos', methods=['GET'])
@login_required
def buscar_pos_candidatos_dfe(dfe_id):
    """
    Busca TODOS os POs candidatos para um DFE especifico.

    🚀 REFATORADO: Delega toda lógica para ValidacaoNfPoService.buscar_preview_pos_candidatos()

    OTIMIZAÇÕES:
    - Usa dados LOCAIS (tabela pedido_compras) em vez de 7 chamadas ao Odoo
    - Latência reduzida de 3-5s para <500ms
    - Tolerâncias CORRIGIDAS: qtd 10%, preço 0% (consistente com validação real)

    Returns:
        {
            "sucesso": True,
            "dfe": { dados do DFE },
            "itens_nf": [ itens da NF com codigo convertido ],
            "pos_candidatos": [ POs com suas linhas e status de match ],
            "resumo": { estatísticas }
        }
    """
    try:
        service = ValidacaoNfPoService()
        resultado = service.buscar_preview_pos_candidatos(dfe_id)

        if resultado.get('sucesso'):
            return jsonify(resultado)
        else:
            erro = resultado.get('erro', 'Erro desconhecido')
            status_code = 404 if 'não encontrado' in erro.lower() else 500
            return jsonify(resultado), status_code

    except Exception as e:
        import traceback
        logger.error(f"Erro ao buscar POs candidatos: {e}\n{traceback.format_exc()}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# ENDPOINTS XML/PDF DO DFE
# =============================================================================

@validacao_nf_po_bp.route('/dfe/<int:dfe_id>/xml', methods=['GET'])
@login_required
def download_dfe_xml(dfe_id):
    """
    Download do XML da NF-e.

    Busca o XML do DFE no Odoo e retorna para download.
    Campos Odoo:
    - l10n_br_body_xml_dfe: XML como texto (preferido)
    - l10n_br_xml_dfe: XML binario (base64)
    - l10n_br_xml_dfe_fname: Nome do arquivo
    """
    from flask import Response
    import base64

    try:
        from app.odoo.utils.connection import get_odoo_connection

        odoo = get_odoo_connection()
        if not odoo.authenticate():
            return jsonify({'sucesso': False, 'erro': 'Falha na autenticacao Odoo'}), 500

        # Buscar dados do DFE
        dfe_data = odoo.read(
            'l10n_br_ciel_it_account.dfe',
            [dfe_id],
            ['l10n_br_body_xml_dfe', 'l10n_br_xml_dfe', 'l10n_br_xml_dfe_fname',
             'nfe_infnfe_ide_nnf', 'nfe_infnfe_emit_cnpj']
        )

        if not dfe_data:
            return jsonify({'sucesso': False, 'erro': f'DFE {dfe_id} nao encontrado'}), 404

        dfe = dfe_data[0]
        xml_content = None
        filename = dfe.get('l10n_br_xml_dfe_fname') or f'nfe_{dfe_id}.xml'

        # Tentar pegar XML como texto primeiro
        if dfe.get('l10n_br_body_xml_dfe'):
            xml_content = dfe['l10n_br_body_xml_dfe']
            if isinstance(xml_content, str):
                xml_content = xml_content.encode('utf-8')

        # Se nao tiver texto, tentar binario (base64)
        elif dfe.get('l10n_br_xml_dfe'):
            try:
                xml_content = base64.b64decode(dfe['l10n_br_xml_dfe'])
            except Exception:
                pass

        if not xml_content:
            return jsonify({'sucesso': False, 'erro': 'XML nao disponivel para este DFE'}), 404

        return Response(
            xml_content,
            mimetype='application/xml',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/xml; charset=utf-8'
            }
        )

    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@validacao_nf_po_bp.route('/dfe/<int:dfe_id>/pdf', methods=['GET'])
@login_required
def download_dfe_pdf(dfe_id):
    """
    Download do PDF (DANFE) da NF-e.

    Busca o PDF do DFE no Odoo e retorna para download.
    Campos Odoo:
    - l10n_br_pdf_dfe: PDF binario (base64)
    - l10n_br_pdf_dfe_fname: Nome do arquivo
    """
    from flask import Response
    import base64

    try:
        from app.odoo.utils.connection import get_odoo_connection

        odoo = get_odoo_connection()
        if not odoo.authenticate():
            return jsonify({'sucesso': False, 'erro': 'Falha na autenticacao Odoo'}), 500

        # Buscar dados do DFE
        dfe_data = odoo.read(
            'l10n_br_ciel_it_account.dfe',
            [dfe_id],
            ['l10n_br_pdf_dfe', 'l10n_br_pdf_dfe_fname',
             'nfe_infnfe_ide_nnf', 'nfe_infnfe_emit_cnpj']
        )

        if not dfe_data:
            return jsonify({'sucesso': False, 'erro': f'DFE {dfe_id} nao encontrado'}), 404

        dfe = dfe_data[0]
        pdf_content = None
        filename = dfe.get('l10n_br_pdf_dfe_fname') or f'danfe_{dfe_id}.pdf'

        # PDF vem em base64
        if dfe.get('l10n_br_pdf_dfe'):
            try:
                pdf_content = base64.b64decode(dfe['l10n_br_pdf_dfe'])
            except Exception:
                pass

        if not pdf_content:
            return jsonify({'sucesso': False, 'erro': 'PDF nao disponivel para este DFE'}), 404

        return Response(
            pdf_content,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'inline; filename="{filename}"',
                'Content-Type': 'application/pdf'
            }
        )

    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# EXECUÇÃO MANUAL DA VALIDAÇÃO
# =============================================================================

@validacao_nf_po_bp.route('/executar-validacao', methods=['POST'])
@login_required
def executar_validacao_manual():
    """
    Executa a validacao de recebimento manualmente (como o scheduler faz).

    Executa:
    1. Sync De-Para do Odoo (product.supplierinfo)
    2. Sync POs vinculados (3 caminhos: purchase_id, purchase_fiscal_id, PO.dfe_id)
    3. Busca DFEs de compra pendentes no periodo
    4. Executa validacao Fase 1 (Fiscal) + Fase 2 (NF x PO)

    Body JSON:
        data_de: Data inicial (YYYY-MM-DD) - opcional
        data_ate: Data final (YYYY-MM-DD) - opcional
        Se nao informados, usa janela padrao de 48h.

    Returns:
        JSON com resultado da execucao
    """
    try:
        from app.recebimento.jobs.validacao_recebimento_job import executar_validacao_recebimento
        from datetime import datetime
        from app.utils.timezone import agora_utc_naive

        data = request.get_json(silent=True) or {}
        data_de = data.get('data_de')  # Formato: YYYY-MM-DD
        data_ate = data.get('data_ate')  # Formato: YYYY-MM-DD

        if data_de and data_ate:
            # Converter datas absolutas para minutos_janela
            dt_de = datetime.strptime(data_de, '%Y-%m-%d')
            agora = agora_utc_naive()

            # Janela = diferenca entre agora e data_de (em minutos)
            minutos_janela = int((agora - dt_de).total_seconds() / 60)

            # Validar periodo maximo de 90 dias
            if minutos_janela > 90 * 24 * 60:
                return jsonify({'sucesso': False, 'erro': 'Periodo maximo: 90 dias'}), 400

            # Validar datas
            if minutos_janela < 0:
                return jsonify({'sucesso': False, 'erro': 'Data "De" nao pode ser futura'}), 400

            logger.info(
                f"Executando validacao manual (periodo: {data_de} a {data_ate}, "
                f"janela: {minutos_janela} min) por {current_user.nome}"
            )
        else:
            minutos_janela = 2880  # 48 horas padrao
            logger.info(f"Executando validacao manual (janela padrao: {minutos_janela} min) por {current_user.nome}")

        resultado = executar_validacao_recebimento(minutos_janela=minutos_janela)

        return jsonify({
            'sucesso': resultado.get('sucesso', False),
            'mensagem': 'Validacao executada com sucesso' if resultado.get('sucesso') else 'Erro na validacao',
            'resultado': resultado
        })

    except ValueError as e:
        logger.error(f"Erro de formato na execucao manual: {e}")
        return jsonify({'sucesso': False, 'erro': f'Formato de data invalido: {e}'}), 400
    except Exception as e:
        logger.error(f"Erro na execucao manual da validacao: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

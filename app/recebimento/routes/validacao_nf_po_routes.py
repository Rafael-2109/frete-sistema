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
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from decimal import Decimal

logger = logging.getLogger(__name__)

from app import db
from app.recebimento.models import (
    ProdutoFornecedorDepara,
    ValidacaoNfPoDfe,
    MatchNfPoItem,
    DivergenciaNfPo
)
from app.recebimento.services.depara_service import DeparaService
from app.recebimento.services.validacao_nf_po_service import ValidacaoNfPoService
from app.recebimento.services.odoo_po_service import OdooPoService

validacao_nf_po_bp = Blueprint('validacao_nf_po', __name__, url_prefix='/api/recebimento')


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
    """Exclui (desativa) mapeamento De-Para."""
    try:
        service = DeparaService()
        service.excluir(depara_id)

        return jsonify({
            'sucesso': True,
            'mensagem': f'De-Para {depara_id} desativado'
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
        validacao = ValidacaoNfPoDfe.query.get(validacao_id)

        if not validacao:
            return jsonify({
                'sucesso': False,
                'erro': f'Validacao {validacao_id} nao encontrada'
            }), 404

        # Buscar matches
        matches = MatchNfPoItem.query.filter_by(validacao_id=validacao_id).all()

        # Buscar divergencias
        divergencias = DivergenciaNfPo.query.filter_by(validacao_id=validacao_id).all()

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
                'criado_em': validacao.criado_em.isoformat() if validacao.criado_em else None,
                'validado_em': validacao.validado_em.isoformat() if validacao.validado_em else None,
                'consolidado_em': validacao.consolidado_em.isoformat() if validacao.consolidado_em else None
            },
            'matches': [{
                'id': m.id,
                'odoo_dfe_line_id': m.odoo_dfe_line_id,
                'cod_produto_fornecedor': m.cod_produto_fornecedor,
                'cod_produto_interno': m.cod_produto_interno,
                'nome_produto': m.nome_produto,
                'qtd_nf': m.qtd_nf,
                'preco_nf': m.preco_nf,
                'um_nf': m.um_nf,
                'fator_conversao': m.fator_conversao,
                'odoo_po_id': m.odoo_po_id,
                'odoo_po_name': m.odoo_po_name,
                'qtd_po': m.qtd_po,
                'preco_po': m.preco_po,
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
            } for d in divergencias]
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

        divergencia = DivergenciaNfPo.query.get(divergencia_id)

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

        # Criar De-Para via service
        depara_service = DeparaService()

        try:
            depara = depara_service.criar(
                cnpj_fornecedor=divergencia.cnpj_fornecedor,
                cod_produto_fornecedor=divergencia.cod_produto_fornecedor,
                cod_produto_interno=cod_produto_interno,
                razao_fornecedor=divergencia.razao_fornecedor,
                descricao_produto_fornecedor=divergencia.nome_produto,
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
            # Log mas nao falha - sync pode ser feito depois
            import logging
            logging.getLogger(__name__).warning(
                f"Falha ao sincronizar De-Para {depara.get('id')} com Odoo: {e}"
            )

        # NAO alterar status da divergencia!
        # A divergencia permanece como 'pendente' ate a revalidacao resolver

        # Disparar revalidacao do DFE (opcional - pode ser feito via scheduler)
        revalidacao_resultado = None
        if divergencia.odoo_dfe_id:
            try:
                from app.recebimento.services.validacao_nf_po_service import ValidacaoNfPoService
                validacao_service = ValidacaoNfPoService()
                revalidacao_resultado = validacao_service.validar_dfe(divergencia.odoo_dfe_id)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    f"Falha na revalidacao automatica do DFE {divergencia.odoo_dfe_id}: {e}"
                )

        return jsonify({
            'sucesso': True,
            'mensagem': 'De-Para criado com sucesso! A NF sera revalidada automaticamente.',
            'depara': depara,
            'sincronizado_odoo': sync_resultado.get('sucesso') if sync_resultado else False,
            'revalidacao': revalidacao_resultado.get('status') if revalidacao_resultado else 'nao_executada'
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

        divergencia = DivergenciaNfPo.query.get(divergencia_id)

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

        divergencia = DivergenciaNfPo.query.get(divergencia_id)

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

        validacao = ValidacaoNfPoDfe.query.get(validacao_id)

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
        matches = MatchNfPoItem.query.filter_by(
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

        # Executar consolidacao
        service = OdooPoService()
        resultado = service.consolidar_pos(
            validacao_id=validacao_id,
            pos_para_consolidar=pos_para_consolidar,
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

    Retorna lista de POs com suas linhas e status de match para cada item da NF.
    Permite analise de N POs para 1 NF.

    Returns:
        {
            "sucesso": True,
            "dfe": { dados do DFE },
            "itens_nf": [ itens da NF com codigo convertido ],
            "pos_candidatos": [
                {
                    "po_id": 123,
                    "po_name": "PO00123",
                    "data_pedido": "2025-01-10",
                    "valor_total": 15000.00,
                    "linhas": [
                        {
                            "line_id": 456,
                            "produto": "PROD001",
                            "nome": "Produto X",
                            "qtd_pedida": 100,
                            "qtd_recebida": 0,
                            "saldo": 100,
                            "preco": 10.50,
                            "match_item_nf": "codigo_forn_123" ou null
                        }
                    ]
                }
            ],
            "resumo_match": {
                "itens_nf": 5,
                "itens_com_po": 3,
                "itens_sem_po": 2,
                "pos_envolvidos": 2
            }
        }
    """
    try:
        from app.odoo.utils.connection import get_odoo_connection

        odoo = get_odoo_connection()
        if not odoo.authenticate():
            return jsonify({'sucesso': False, 'erro': 'Falha autenticacao Odoo'}), 500

        # 1. Buscar dados do DFE
        dfe_data = odoo.read(
            'l10n_br_ciel_it_account.dfe',
            [dfe_id],
            [
                'id', 'name', 'nfe_infnfe_ide_nnf', 'nfe_infnfe_ide_serie',
                'nfe_infnfe_emit_cnpj', 'nfe_infnfe_emit_xnome',
                'nfe_infnfe_ide_dhemi', 'nfe_infnfe_total_icmstot_vnf',
                'lines_ids'  # Campo correto para linhas do DFE
            ]
        )

        if not dfe_data:
            return jsonify({'sucesso': False, 'erro': f'DFE {dfe_id} nao encontrado'}), 404

        dfe = dfe_data[0]
        cnpj_fornecedor = ''.join(c for c in (dfe.get('nfe_infnfe_emit_cnpj') or '') if c.isdigit())

        # 2. Buscar linhas do DFE
        line_ids = dfe.get('lines_ids', [])
        itens_nf = []

        if line_ids:
            linhas = odoo.read(
                'l10n_br_ciel_it_account.dfe.line',
                line_ids,
                [
                    'id', 'det_nitem', 'det_prod_cprod', 'det_prod_xprod',
                    'det_prod_qcom', 'det_prod_vuncom', 'det_prod_ucom'
                ]
            )

            # Para cada linha, verificar se tem De-Para
            for linha in linhas:
                cod_forn = linha.get('det_prod_cprod', '')

                # Buscar De-Para diretamente no modelo
                depara = None
                if cod_forn:
                    depara = ProdutoFornecedorDepara.query.filter_by(
                        cnpj_fornecedor=cnpj_fornecedor,
                        cod_produto_fornecedor=cod_forn,
                        ativo=True
                    ).first()

                item = {
                    'dfe_line_id': linha['id'],
                    'nitem': linha.get('det_nitem'),
                    'cod_produto_fornecedor': cod_forn,
                    'nome_produto': linha.get('det_prod_xprod', ''),
                    'qtd_nf': float(linha.get('det_prod_qcom') or 0),
                    'preco_nf': float(linha.get('det_prod_vuncom') or 0),
                    'um_nf': linha.get('det_prod_ucom', ''),
                    'tem_depara': depara is not None,
                    'cod_produto_interno': depara.cod_produto_interno if depara else None,
                    'fator_conversao': float(depara.fator_conversao or 1) if depara else 1,
                }

                # Calcular valores convertidos
                if depara:
                    fator = item['fator_conversao']
                    item['qtd_convertida'] = item['qtd_nf'] * fator
                    item['preco_convertido'] = item['preco_nf'] / fator if fator > 0 else item['preco_nf']
                else:
                    item['qtd_convertida'] = item['qtd_nf']
                    item['preco_convertido'] = item['preco_nf']

                itens_nf.append(item)

        # 3. Buscar partner pelo CNPJ
        # Formatar CNPJ para busca (Odoo armazena formatado: XX.XXX.XXX/XXXX-XX)
        def formatar_cnpj(cnpj: str) -> str:
            """Formata CNPJ limpo para formato com pontuacao."""
            cnpj = ''.join(c for c in cnpj if c.isdigit())
            if len(cnpj) == 14:
                return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
            return cnpj

        cnpj_formatado = formatar_cnpj(cnpj_fornecedor)

        partner_ids = odoo.search(
            'res.partner',
            [('l10n_br_cnpj', '=', cnpj_formatado)],
            limit=1
        )

        pos_candidatos = []
        if partner_ids:
            partner_id = partner_ids[0]

            # 4. Buscar TODOS os POs do fornecedor (status purchase ou done)
            po_ids = odoo.search(
                'purchase.order',
                [
                    ('partner_id', '=', partner_id),
                    ('state', 'in', ['purchase', 'done'])
                ]
            )

            if po_ids:
                pos = odoo.read(
                    'purchase.order',
                    po_ids,
                    [
                        'id', 'name', 'date_order', 'date_planned',
                        'state', 'amount_total', 'order_line'
                    ]
                )

                # Mapear codigos internos dos itens da NF para fazer match
                codigos_nf = {
                    item['cod_produto_interno']: item
                    for item in itens_nf
                    if item.get('cod_produto_interno')
                }

                for po in pos:
                    line_ids = po.get('order_line', [])
                    po_info = {
                        'po_id': po['id'],
                        'po_name': po['name'],
                        'data_pedido': po.get('date_order', '')[:10] if po.get('date_order') else None,
                        'data_prevista': po.get('date_planned', '')[:10] if po.get('date_planned') else None,
                        'estado': po.get('state'),
                        'valor_total': float(po.get('amount_total') or 0),
                        'linhas': [],
                        'qtd_linhas_match': 0
                    }

                    if line_ids:
                        lines = odoo.read(
                            'purchase.order.line',
                            line_ids,
                            [
                                'id', 'product_id', 'name',
                                'product_qty', 'qty_received',
                                'price_unit', 'price_subtotal',
                                'date_planned'
                            ]
                        )

                        for line in lines:
                            product_info = line.get('product_id', [None, 'N/A'])
                            product_id = product_info[0] if product_info else None
                            product_name = product_info[1] if isinstance(product_info, list) and len(product_info) > 1 else 'N/A'

                            # Buscar default_code do produto
                            cod_interno = None
                            if product_id:
                                prod_data = odoo.read('product.product', [product_id], ['default_code'])
                                if prod_data:
                                    cod_interno = prod_data[0].get('default_code')

                            qtd_pedida = float(line.get('product_qty') or 0)
                            qtd_recebida = float(line.get('qty_received') or 0)
                            saldo = qtd_pedida - qtd_recebida
                            preco_po = float(line.get('price_unit') or 0)
                            data_prevista_linha = line.get('date_planned', '')[:10] if line.get('date_planned') else None

                            # Verificar se faz match com algum item da NF
                            match_item = None
                            divergencias = {}
                            if cod_interno and cod_interno in codigos_nf:
                                match_item = codigos_nf[cod_interno]

                                # Calcular divergências quando há match
                                qtd_nf_convertida = match_item.get('qtd_convertida', 0)
                                preco_nf_convertido = match_item.get('preco_convertido', 0)

                                # Divergência de quantidade (NF vs Saldo PO)
                                if saldo > 0:
                                    dif_qtd = qtd_nf_convertida - saldo
                                    dif_qtd_pct = ((qtd_nf_convertida - saldo) / saldo * 100) if saldo else 0
                                else:
                                    dif_qtd = qtd_nf_convertida
                                    dif_qtd_pct = 100

                                # Divergência de preço
                                if preco_po > 0:
                                    dif_preco = preco_nf_convertido - preco_po
                                    dif_preco_pct = ((preco_nf_convertido - preco_po) / preco_po * 100)
                                else:
                                    dif_preco = preco_nf_convertido
                                    dif_preco_pct = 100 if preco_nf_convertido > 0 else 0

                                divergencias = {
                                    'qtd_nf': match_item.get('qtd_nf', 0),
                                    'qtd_nf_convertida': qtd_nf_convertida,
                                    'preco_nf': match_item.get('preco_nf', 0),
                                    'preco_nf_convertido': preco_nf_convertido,
                                    'dif_qtd': round(dif_qtd, 3),
                                    'dif_qtd_pct': round(dif_qtd_pct, 2),
                                    'dif_preco': round(dif_preco, 4),
                                    'dif_preco_pct': round(dif_preco_pct, 2),
                                    'qtd_ok': abs(dif_qtd_pct) <= 5,  # Tolerância 5%
                                    'preco_ok': abs(dif_preco_pct) <= 5,  # Tolerância 5%
                                }

                            linha_info = {
                                'line_id': line['id'],
                                'product_id': product_id,
                                'cod_interno': cod_interno,
                                'nome': product_name[:60] + '...' if len(product_name) > 60 else product_name,
                                'qtd_pedida': qtd_pedida,
                                'qtd_recebida': qtd_recebida,
                                'saldo': saldo,
                                'preco': preco_po,
                                'valor_linha': float(line.get('price_subtotal') or 0),
                                'data_prevista': data_prevista_linha,
                                'match_item_nf': match_item.get('cod_produto_fornecedor') if match_item else None,
                                'tem_saldo': saldo > 0,
                                'divergencias': divergencias if match_item else None
                            }

                            if match_item:
                                po_info['qtd_linhas_match'] += 1

                            po_info['linhas'].append(linha_info)

                    # Adicionar PO se tem pelo menos uma linha com saldo
                    if any(l['tem_saldo'] for l in po_info['linhas']):
                        pos_candidatos.append(po_info)

        # 5. Calcular resumo
        itens_com_po = sum(1 for item in itens_nf if item.get('cod_produto_interno') and
                          any(any(l.get('match_item_nf') == item['cod_produto_fornecedor']
                                  for l in po['linhas'])
                              for po in pos_candidatos))

        resumo = {
            'itens_nf': len(itens_nf),
            'itens_com_depara': sum(1 for item in itens_nf if item.get('tem_depara')),
            'itens_sem_depara': sum(1 for item in itens_nf if not item.get('tem_depara')),
            'itens_com_po': itens_com_po,
            'itens_sem_po': len(itens_nf) - itens_com_po,
            'pos_candidatos': len(pos_candidatos),
            'valor_total_pos': sum(po['valor_total'] for po in pos_candidatos)
        }

        return jsonify({
            'sucesso': True,
            'dfe': {
                'id': dfe['id'],
                'numero_nf': dfe.get('nfe_infnfe_ide_nnf'),
                'serie': dfe.get('nfe_infnfe_ide_serie'),
                'cnpj_fornecedor': cnpj_fornecedor,
                'razao_fornecedor': dfe.get('nfe_infnfe_emit_xnome'),
                'data_emissao': dfe.get('nfe_infnfe_ide_dhemi', '')[:10] if dfe.get('nfe_infnfe_ide_dhemi') else None,
                'valor_total': float(dfe.get('nfe_infnfe_total_icmstot_vnf') or 0)
            },
            'itens_nf': itens_nf,
            'pos_candidatos': pos_candidatos,
            'resumo': resumo
        })

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
    2. Busca DFEs de compra pendentes
    3. Executa validacao Fase 1 (Fiscal) + Fase 2 (NF x PO)

    Query params:
        minutos_janela: Janela de tempo em minutos (default: 120)

    Returns:
        JSON com resultado da execucao
    """
    try:
        from app.recebimento.jobs.validacao_recebimento_job import executar_validacao_recebimento

        minutos_janela = request.args.get('minutos_janela', 2880, type=int)  # 48 horas

        logger.info(f"Executando validacao manual (janela: {minutos_janela} min) por {current_user.nome}")

        resultado = executar_validacao_recebimento(minutos_janela=minutos_janela)

        return jsonify({
            'sucesso': resultado.get('sucesso', False),
            'mensagem': 'Validacao executada com sucesso' if resultado.get('sucesso') else 'Erro na validacao',
            'resultado': resultado
        })

    except Exception as e:
        logger.error(f"Erro na execucao manual da validacao: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

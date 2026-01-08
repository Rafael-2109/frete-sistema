"""
Rotas de Resolucao via IA (Claude Haiku 4.5)
=============================================

APIs para:
- Resolver produto (De-Para inteligente)
- Extrair NF de venda e motivo de observacoes
- Normalizar unidade de medida
- Resolver todas as linhas de uma NFD

Criado em: 30/12/2024
"""

from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user

from app.devolucao.services import get_ai_resolver, get_nfd_service
from app.devolucao.models import (
    NFDevolucao,
    NFDevolucaoLinha,
    DeParaProdutoCliente,
    OcorrenciaDevolucao,
)
from app.monitoramento.models import EntregaMonitorada
from app import db
from app.utils.timezone import agora_brasil

ai_bp = Blueprint(
    'devolucao_ai',
    __name__,
    url_prefix='/ai'
)


# =============================================================================
# PAGINAS HTML
# =============================================================================

@ai_bp.route('/depara')
@login_required
def pagina_depara():
    """
    Pagina de gerenciamento De-Para com sugestoes do Haiku.
    """
    return render_template('devolucao/depara/index.html')


# =============================================================================
# RESOLUCAO DE PRODUTO (De-Para)
# =============================================================================

@ai_bp.route('/api/resolver-produto', methods=['POST'])
@login_required
def api_resolver_produto():
    """
    Resolve codigo do cliente para nosso codigo interno.

    POST /devolucao/ai/api/resolver-produto
    Body:
    {
        "codigo_cliente": "7896",
        "descricao_cliente": "AZEITONA VERDE FATIADA 500G",
        "prefixo_cnpj": "93209760",
        "unidade_cliente": "UN",      // opcional
        "quantidade": 12.0            // opcional
    }

    Returns:
        JSON com sugestoes e nivel de confianca
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'sucesso': False,
                'erro': 'Body JSON obrigatorio'
            }), 400

        codigo_cliente = data.get('codigo_cliente', '')
        descricao_cliente = data.get('descricao_cliente', '')
        prefixo_cnpj = data.get('prefixo_cnpj', '')
        unidade_cliente = data.get('unidade_cliente')
        quantidade = data.get('quantidade')

        if not descricao_cliente and not codigo_cliente:
            return jsonify({
                'sucesso': False,
                'erro': 'codigo_cliente ou descricao_cliente obrigatorio'
            }), 400

        service = get_ai_resolver()
        resultado = service.resolver_produto(
            codigo_cliente=codigo_cliente,
            descricao_cliente=descricao_cliente,
            prefixo_cnpj=prefixo_cnpj,
            unidade_cliente=unidade_cliente,
            quantidade=float(quantidade) if quantidade else None
        )

        # Normalizar unidade para contexto de conversao
        tipo_unidade = None
        fator_conversao = None
        if unidade_cliente:
            try:
                result_unidade = service.normalizar_unidade(unidade_cliente)
                tipo_unidade = result_unidade.tipo
                fator_conversao = result_unidade.fator_conversao
            except Exception:
                pass

        # Calcular conversao para sugestao principal (busca nome no CadastroPalletizacao)
        def calcular_conversao(codigo_interno, nome_fallback):
            from app.producao.models import CadastroPalletizacao

            # Priorizar nome do CadastroPalletizacao
            nome_para_extracao = nome_fallback or ''
            try:
                produto = CadastroPalletizacao.query.filter_by(
                    cod_produto=codigo_interno
                ).first()
                if produto and produto.nome_produto:
                    nome_para_extracao = produto.nome_produto
            except Exception:
                pass

            qtd_por_caixa = service._extrair_qtd_caixa(nome_para_extracao)
            qtd_convertida = None
            if tipo_unidade == 'UNIDADE' and qtd_por_caixa and quantidade:
                qtd_convertida = round(float(quantidade) / qtd_por_caixa, 2)
            return {
                'qtd_por_caixa': qtd_por_caixa,
                'qtd_convertida_caixas': qtd_convertida
            }

        # Preparar resposta da sugestao principal
        sugestao_principal_response = None
        if resultado.sugestao_principal:
            conv = calcular_conversao(
                resultado.sugestao_principal.codigo_interno,
                resultado.sugestao_principal.nome_interno
            )
            sugestao_principal_response = {
                'codigo': resultado.sugestao_principal.codigo_interno,
                'nome': resultado.sugestao_principal.nome_interno,
                'confianca': resultado.sugestao_principal.confianca,
                'justificativa': resultado.sugestao_principal.justificativa,
                'qtd_por_caixa': conv['qtd_por_caixa'],
                'qtd_convertida_caixas': conv['qtd_convertida_caixas']
            }

        # Preparar outras sugestoes com conversao
        outras_sugestoes_response = []
        for s in resultado.outras_sugestoes:
            conv = calcular_conversao(s.codigo_interno, s.nome_interno)
            outras_sugestoes_response.append({
                'codigo': s.codigo_interno,
                'nome': s.nome_interno,
                'confianca': s.confianca,
                'justificativa': s.justificativa,
                'qtd_por_caixa': conv['qtd_por_caixa'],
                'qtd_convertida_caixas': conv['qtd_convertida_caixas']
            })

        return jsonify({
            'sucesso': resultado.sucesso,
            'confianca': resultado.confianca,
            'requer_confirmacao': resultado.requer_confirmacao,
            'mensagem': resultado.mensagem,
            'metodo_resolucao': resultado.metodo_resolucao,
            'unidade_cliente': unidade_cliente,
            'tipo_unidade': tipo_unidade,
            'fator_conversao': fator_conversao,
            'quantidade': float(quantidade) if quantidade else None,
            'sugestao_principal': sugestao_principal_response,
            'outras_sugestoes': outras_sugestoes_response
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# EXTRACAO DE OBSERVACOES
# =============================================================================

@ai_bp.route('/api/extrair-observacao', methods=['POST'])
@login_required
def api_extrair_observacao():
    """
    Extrai NF de venda e motivo das observacoes.

    POST /devolucao/ai/api/extrair-observacao
    Body:
    {
        "texto": "DEVOLUCAO REF NF 123456 - PRODUTO AVARIADO NO TRANSPORTE"
    }

    Returns:
        JSON com NF extraida, motivo e confianca
    """
    try:
        data = request.get_json()

        if not data or 'texto' not in data:
            return jsonify({
                'sucesso': False,
                'erro': 'texto obrigatorio'
            }), 400

        texto = data['texto']

        service = get_ai_resolver()
        resultado = service.extrair_observacao(texto)

        return jsonify({
            'sucesso': True,
            'numero_nf_venda': resultado.numero_nf_venda,
            'motivo_sugerido': resultado.motivo_sugerido,
            'descricao_motivo': resultado.descricao_motivo,
            'confianca': resultado.confianca,
            'texto_original': resultado.texto_original
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# ATUALIZAR MOTIVO DA NFD
# =============================================================================

@ai_bp.route('/api/nfd/<int:nfd_id>/atualizar-motivo', methods=['POST'])
@login_required
def api_atualizar_motivo_nfd(nfd_id: int):
    """
    Atualiza o motivo e NF de venda de uma NFD.

    POST /devolucao/ai/api/nfd/{nfd_id}/atualizar-motivo
    Body:
    {
        "motivo": "AVARIA",
        "descricao_motivo": "Produto avariado no transporte",
        "numero_nf_venda": "123456"
    }

    Returns:
        JSON com sucesso/erro
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'sucesso': False,
                'erro': 'Dados obrigatorios'
            }), 400

        # Buscar NFD
        nfd = NFDevolucao.query.get(nfd_id)
        if not nfd:
            return jsonify({
                'sucesso': False,
                'erro': f'NFD {nfd_id} nao encontrada'
            }), 404

        # Atualizar campos
        if 'motivo' in data and data['motivo']:
            nfd.motivo = data['motivo']

        if 'descricao_motivo' in data and data['descricao_motivo']:
            nfd.descricao_motivo = data['descricao_motivo']

        if 'numero_nf_venda' in data and data['numero_nf_venda']:
            numero_nf = str(data['numero_nf_venda'])
            nfd.numero_nf_venda = numero_nf

            # Vincular à EntregaMonitorada e marcar teve_devolucao = True
            entrega = EntregaMonitorada.query.filter_by(numero_nf=numero_nf).first()
            if entrega:
                # Vincular NFD à entrega se ainda não estiver vinculada
                if not nfd.entrega_monitorada_id:
                    nfd.entrega_monitorada_id = entrega.id

                # Marcar teve_devolucao = True
                if not entrega.teve_devolucao:
                    entrega.teve_devolucao = True

        # Auditoria
        nfd.atualizado_em = agora_brasil()
        nfd.atualizado_por = current_user.username if hasattr(current_user, 'username') else str(current_user.id)

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': 'Motivo atualizado com sucesso',
            'nfd_id': nfd_id,
            'motivo': nfd.motivo,
            'descricao_motivo': nfd.descricao_motivo,
            'numero_nf_venda': nfd.numero_nf_venda
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# NORMALIZACAO DE UNIDADE
# =============================================================================

@ai_bp.route('/api/normalizar-unidade', methods=['POST'])
@login_required
def api_normalizar_unidade():
    """
    Normaliza unidade de medida.

    POST /devolucao/ai/api/normalizar-unidade
    Body:
    {
        "unidade": "CXA1"
    }

    Returns:
        JSON com tipo (CAIXA/UNIDADE/PESO) e fator
    """
    try:
        data = request.get_json()

        if not data or 'unidade' not in data:
            return jsonify({
                'sucesso': False,
                'erro': 'unidade obrigatoria'
            }), 400

        unidade = data['unidade']

        service = get_ai_resolver()
        resultado = service.normalizar_unidade(unidade)

        return jsonify({
            'sucesso': True,
            'unidade_original': resultado.unidade_original,
            'tipo': resultado.tipo,
            'fator_conversao': resultado.fator_conversao,
            'confianca': resultado.confianca
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# RESOLUCAO EM LOTE (NFD COMPLETA)
# =============================================================================

@ai_bp.route('/api/nfd/<int:nfd_id>/resolver-linhas', methods=['POST'])
@login_required
def api_resolver_linhas_nfd(nfd_id: int):
    """
    Resolve todas as linhas pendentes de uma NFD.

    POST /devolucao/ai/api/nfd/<nfd_id>/resolver-linhas
    Body (opcional):
    {
        "auto_gravar_depara": false
    }

    Returns:
        JSON com estatisticas e resultados por linha
    """
    try:
        data = request.get_json() or {}
        auto_gravar_depara = data.get('auto_gravar_depara', False)

        service = get_ai_resolver()
        resultado = service.resolver_linhas_nfd(
            nfd_id=nfd_id,
            auto_gravar_depara=auto_gravar_depara
        )

        return jsonify(resultado)

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@ai_bp.route('/api/nfd/<int:nfd_id>/linhas', methods=['GET'])
@login_required
def api_listar_linhas_nfd(nfd_id: int):
    """
    Lista todas as linhas de produtos de uma NFD.

    GET /devolucao/ai/api/nfd/<nfd_id>/linhas

    Returns:
        JSON com lista de linhas e status de resolucao
    """
    try:
        nfd = NFDevolucao.query.get(nfd_id)
        if not nfd:
            return jsonify({
                'sucesso': False,
                'erro': 'NFD nao encontrada'
            }), 404

        linhas = NFDevolucaoLinha.query.filter_by(
            nf_devolucao_id=nfd_id
        ).order_by(NFDevolucaoLinha.id).all()

        return jsonify({
            'sucesso': True,
            'nfd_id': nfd_id,
            'numero_nfd': nfd.numero_nfd,
            'total_linhas': len(linhas),
            'linhas': [
                {
                    'id': linha.id,
                    'codigo_produto_cliente': linha.codigo_produto_cliente,
                    'descricao_produto_cliente': linha.descricao_produto_cliente,
                    'quantidade': float(linha.quantidade) if linha.quantidade else None,
                    'unidade_medida': linha.unidade_medida,
                    'valor_unitario': float(linha.valor_unitario) if linha.valor_unitario else None,
                    'valor_total': float(linha.valor_total) if linha.valor_total else None,
                    'cfop': linha.cfop,
                    'ncm': linha.ncm,
                    'codigo_produto_interno': linha.codigo_produto_interno,
                    'descricao_produto_interno': linha.descricao_produto_interno,
                    'produto_resolvido': linha.produto_resolvido,
                    'metodo_resolucao': linha.metodo_resolucao
                }
                for linha in linhas
            ]
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@ai_bp.route('/api/linha/<int:linha_id>/confirmar', methods=['POST'])
@login_required
def api_confirmar_resolucao(linha_id: int):
    """
    Confirma resolucao de uma linha (salva De-Para).

    POST /devolucao/ai/api/linha/<linha_id>/confirmar
    Body:
    {
        "codigo_interno": "AZ001",
        "descricao_interno": "AZEITONA VERDE 500G",
        "gravar_depara": true,
        "qtd_por_caixa": 12,
        "quantidade_convertida": 1.0
    }
    """
    try:
        from app.producao.models import CadastroPalletizacao

        data = request.get_json()

        if not data or 'codigo_interno' not in data:
            return jsonify({
                'sucesso': False,
                'erro': 'codigo_interno obrigatorio'
            }), 400

        linha = NFDevolucaoLinha.query.get(linha_id)
        if not linha:
            return jsonify({
                'sucesso': False,
                'erro': 'Linha nao encontrada'
            }), 404

        # Buscar NFD para pegar prefixo CNPJ
        nfd = NFDevolucao.query.get(linha.nf_devolucao_id)
        if not nfd:
            return jsonify({
                'sucesso': False,
                'erro': 'NFD nao encontrada'
            }), 404

        # Atualizar linha
        codigo_interno = data['codigo_interno']
        linha.codigo_produto_interno = codigo_interno
        linha.descricao_produto_interno = data.get('descricao_interno', '')
        linha.produto_resolvido = True
        linha.metodo_resolucao = 'MANUAL'

        # Gravar dados de conversao na linha
        qtd_por_caixa = data.get('qtd_por_caixa')
        quantidade_convertida = data.get('quantidade_convertida')

        if qtd_por_caixa:
            linha.qtd_por_caixa = int(qtd_por_caixa)

        if quantidade_convertida:
            linha.quantidade_convertida = float(quantidade_convertida)

        # =========================================================================
        # CALCULAR PESO: quantidade_convertida * peso_bruto do CadastroPalletizacao
        # =========================================================================
        peso_calculado = None
        produto = CadastroPalletizacao.query.filter_by(cod_produto=codigo_interno).first()
        if produto and produto.peso_bruto:
            # Usar quantidade_convertida (caixas) se disponivel, senao quantidade original
            qtd_para_peso = float(quantidade_convertida) if quantidade_convertida else float(linha.quantidade or 0)
            peso_calculado = qtd_para_peso * float(produto.peso_bruto)
            linha.peso_bruto = peso_calculado

        # Gravar De-Para se solicitado
        if data.get('gravar_depara') and nfd.prefixo_cnpj_emitente:
            prefixo = nfd.prefixo_cnpj_emitente[:8]

            # Verificar se ja existe
            existente = DeParaProdutoCliente.query.filter_by(
                prefixo_cnpj=prefixo,
                codigo_cliente=linha.codigo_produto_cliente
            ).first()

            # Calcular fator de conversao: qtd_por_caixa se unidade for UN, senao 1.0
            fator_conversao = 1.0
            if qtd_por_caixa and linha.unidade_medida:
                unidade_upper = linha.unidade_medida.upper()
                # Se unidade do cliente for UNIDADE, fator = qtd_por_caixa
                if unidade_upper in ['UN', 'UNID', 'UNIDADE', 'UNI', 'UND', 'PC', 'PCS', 'PECA', 'PECAS']:
                    fator_conversao = float(qtd_por_caixa)

            if not existente:
                usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

                depara = DeParaProdutoCliente(
                    prefixo_cnpj=prefixo,
                    codigo_cliente=linha.codigo_produto_cliente,
                    descricao_cliente=linha.descricao_produto_cliente,
                    nosso_codigo=data['codigo_interno'],
                    descricao_nosso=data.get('descricao_interno', ''),
                    fator_conversao=fator_conversao,
                    unidade_medida_cliente=linha.unidade_medida,
                    unidade_medida_nosso='CX',  # Nos vendemos em caixas
                    ativo=True,
                    criado_em=agora_brasil(),
                    criado_por=usuario,
                )
                db.session.add(depara)

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': 'Resolucao confirmada',
            'linha_id': linha_id,
            'codigo_interno': linha.codigo_produto_interno,
            'quantidade_convertida': float(linha.quantidade_convertida) if linha.quantidade_convertida else None,
            'qtd_por_caixa': linha.qtd_por_caixa,
            'peso_bruto': float(linha.peso_bruto) if linha.peso_bruto else None
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# CRUD DE-PARA
# =============================================================================

@ai_bp.route('/api/depara', methods=['GET'])
@login_required
def api_listar_depara():
    """
    Lista De-Para cadastrados.

    GET /devolucao/ai/api/depara?prefixo_cnpj=93209760
    """
    try:
        prefixo_cnpj = request.args.get('prefixo_cnpj')
        codigo_cliente = request.args.get('codigo_cliente')
        nosso_codigo = request.args.get('nosso_codigo')

        query = DeParaProdutoCliente.query.filter_by(ativo=True)

        if prefixo_cnpj:
            query = query.filter_by(prefixo_cnpj=prefixo_cnpj[:8])
        if codigo_cliente:
            query = query.filter(
                DeParaProdutoCliente.codigo_cliente.ilike(f'%{codigo_cliente}%')
            )
        if nosso_codigo:
            query = query.filter(
                DeParaProdutoCliente.nosso_codigo.ilike(f'%{nosso_codigo}%')
            )

        items = query.order_by(DeParaProdutoCliente.prefixo_cnpj).limit(100).all()

        return jsonify({
            'sucesso': True,
            'total': len(items),
            'depara': [item.to_dict() for item in items]
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@ai_bp.route('/api/depara', methods=['POST'])
@login_required
def api_criar_depara():
    """
    Cria novo De-Para.

    POST /devolucao/ai/api/depara
    Body:
    {
        "prefixo_cnpj": "93209760",
        "codigo_cliente": "7896",
        "descricao_cliente": "AZEITONA VERDE",
        "nosso_codigo": "AZ001",
        "descricao_nosso": "AZEITONA VERDE 500G",
        "fator_conversao": 1.0,
        "unidade_medida_cliente": "CXA",
        "unidade_medida_nosso": "UN"
    }
    """
    try:
        data = request.get_json()

        campos_obrigatorios = ['prefixo_cnpj', 'codigo_cliente', 'nosso_codigo']
        for campo in campos_obrigatorios:
            if not data.get(campo):
                return jsonify({
                    'sucesso': False,
                    'erro': f'{campo} obrigatorio'
                }), 400

        prefixo = data['prefixo_cnpj'][:8]
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        # Verificar duplicata (inclui inativos para evitar violacao de constraint)
        existente = DeParaProdutoCliente.query.filter_by(
            prefixo_cnpj=prefixo,
            codigo_cliente=data['codigo_cliente']
        ).first()

        if existente:
            if existente.ativo:
                return jsonify({
                    'sucesso': False,
                    'erro': 'De-Para ja existe para este prefixo/codigo'
                }), 400
            else:
                # Registro inativo - reativar e atualizar
                existente.descricao_cliente = data.get('descricao_cliente')
                existente.nosso_codigo = data['nosso_codigo']
                existente.descricao_nosso = data.get('descricao_nosso')
                existente.fator_conversao = data.get('fator_conversao', 1.0)
                existente.unidade_medida_cliente = data.get('unidade_medida_cliente')
                existente.unidade_medida_nosso = data.get('unidade_medida_nosso')
                existente.nome_grupo = data.get('nome_grupo')
                existente.ativo = True
                existente.atualizado_em = agora_brasil()
                existente.atualizado_por = usuario
                db.session.commit()

                return jsonify({
                    'sucesso': True,
                    'depara': existente.to_dict(),
                    'mensagem': 'Registro inativo reativado e atualizado'
                })

        depara = DeParaProdutoCliente(
            prefixo_cnpj=prefixo,
            codigo_cliente=data['codigo_cliente'],
            descricao_cliente=data.get('descricao_cliente'),
            nosso_codigo=data['nosso_codigo'],
            descricao_nosso=data.get('descricao_nosso'),
            fator_conversao=data.get('fator_conversao', 1.0),
            unidade_medida_cliente=data.get('unidade_medida_cliente'),
            unidade_medida_nosso=data.get('unidade_medida_nosso'),
            nome_grupo=data.get('nome_grupo'),
            ativo=True,
            criado_em=agora_brasil(),
            criado_por=usuario,
        )

        db.session.add(depara)
        db.session.commit()

        return jsonify({
            'sucesso': True,
            'depara': depara.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@ai_bp.route('/api/depara/<int:depara_id>', methods=['PUT'])
@login_required
def api_atualizar_depara(depara_id: int):
    """
    Atualiza De-Para existente.

    PUT /devolucao/ai/api/depara/<depara_id>
    """
    try:
        data = request.get_json()

        depara = DeParaProdutoCliente.query.get(depara_id)
        if not depara:
            return jsonify({
                'sucesso': False,
                'erro': 'De-Para nao encontrado'
            }), 404

        # Atualizar campos
        if 'nosso_codigo' in data:
            depara.nosso_codigo = data['nosso_codigo']
        if 'descricao_nosso' in data:
            depara.descricao_nosso = data['descricao_nosso']
        if 'fator_conversao' in data:
            depara.fator_conversao = data['fator_conversao']
        if 'unidade_medida_cliente' in data:
            depara.unidade_medida_cliente = data['unidade_medida_cliente']
        if 'unidade_medida_nosso' in data:
            depara.unidade_medida_nosso = data['unidade_medida_nosso']
        if 'nome_grupo' in data:
            depara.nome_grupo = data['nome_grupo']

        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        depara.atualizado_em = agora_brasil()
        depara.atualizado_por = usuario

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'depara': depara.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@ai_bp.route('/api/depara/<int:depara_id>', methods=['DELETE'])
@login_required
def api_excluir_depara(depara_id: int):
    """
    Desativa De-Para (soft delete).

    DELETE /devolucao/ai/api/depara/<depara_id>
    """
    try:
        depara = DeParaProdutoCliente.query.get(depara_id)
        if not depara:
            return jsonify({
                'sucesso': False,
                'erro': 'De-Para nao encontrado'
            }), 404

        depara.ativo = False
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        depara.atualizado_em = agora_brasil()
        depara.atualizado_por = usuario

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': 'De-Para desativado'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# AUTOCOMPLETE DE PRODUTOS (CadastroPalletizacao)
# =============================================================================

@ai_bp.route('/api/produtos/buscar', methods=['GET'])
@login_required
def api_buscar_produtos():
    """
    Busca produtos para autocomplete.
    Usa CadastroPalletizacao com produto_vendido=True.

    GET /devolucao/ai/api/produtos/buscar?q=azeitona&limit=10

    Returns:
        Lista de produtos com codigo, nome, embalagem, etc.
    """
    try:
        from app.producao.models import CadastroPalletizacao
        from sqlalchemy import or_

        query_str = request.args.get('q', '').strip()
        limite = min(request.args.get('limit', 20, type=int), 50)

        if not query_str or len(query_str) < 2:
            return jsonify({
                'sucesso': True,
                'produtos': []
            })

        # Buscar em CadastroPalletizacao com produto_vendido=True
        query = CadastroPalletizacao.query.filter(
            CadastroPalletizacao.produto_vendido == True
        )

        # Buscar por codigo ou nome
        if query_str.isdigit():
            # Busca por codigo
            query = query.filter(
                CadastroPalletizacao.cod_produto.like(f'{query_str}%')
            )
        else:
            # Busca por nome
            termos = query_str.upper().split()
            for termo in termos[:3]:
                query = query.filter(
                    CadastroPalletizacao.nome_produto.ilike(f'%{termo}%')
                )

        produtos = query.limit(limite).all()

        resultado = []
        for p in produtos:
            resultado.append({
                'codigo': p.cod_produto,
                'nome': p.nome_produto,
                'embalagem': p.tipo_embalagem,
                'materia_prima': p.tipo_materia_prima,
                'marca': p.categoria_produto,
                'palletizacao': float(p.palletizacao) if p.palletizacao else None,
                'peso_bruto': float(p.peso_bruto) if p.peso_bruto else None
            })

        return jsonify({
            'sucesso': True,
            'total': len(resultado),
            'produtos': resultado
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@ai_bp.route('/api/produtos/<codigo>', methods=['GET'])
@login_required
def api_obter_produto(codigo: str):
    """
    Obtem detalhes de um produto pelo codigo.

    GET /devolucao/ai/api/produtos/4510145

    Returns:
        Dados completos do produto
    """
    try:
        from app.producao.models import CadastroPalletizacao

        produto = CadastroPalletizacao.query.filter_by(
            cod_produto=codigo
        ).first()

        if not produto:
            return jsonify({
                'sucesso': False,
                'erro': 'Produto nao encontrado'
            }), 404

        return jsonify({
            'sucesso': True,
            'produto': {
                'codigo': produto.cod_produto,
                'nome': produto.nome_produto,
                'embalagem': produto.tipo_embalagem,
                'materia_prima': produto.tipo_materia_prima,
                'marca': produto.categoria_produto,
                'palletizacao': float(produto.palletizacao) if produto.palletizacao else None,
                'peso_bruto': float(produto.peso_bruto) if produto.peso_bruto else None,
                'linha_producao': produto.linha_producao,
                'medidas': produto.medidas,
                'produto_vendido': produto.produto_vendido,
                'produto_comprado': produto.produto_comprado
            }
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# ESTATISTICAS DE RESOLUCAO
# =============================================================================

@ai_bp.route('/api/estatisticas', methods=['GET'])
@login_required
def api_estatisticas_resolucao():
    """
    Retorna estatisticas de resolucao de produtos.

    GET /devolucao/ai/api/estatisticas
    """
    try:
        from sqlalchemy import func

        # Total de linhas
        total_linhas = NFDevolucaoLinha.query.count()

        # Linhas resolvidas
        resolvidas = NFDevolucaoLinha.query.filter_by(produto_resolvido=True).count()

        # Por metodo de resolucao
        por_metodo = db.session.query(
            NFDevolucaoLinha.metodo_resolucao,
            func.count(NFDevolucaoLinha.id)
        ).filter(
            NFDevolucaoLinha.produto_resolvido == True
        ).group_by(NFDevolucaoLinha.metodo_resolucao).all()

        # Total De-Para cadastrados
        total_depara = DeParaProdutoCliente.query.filter_by(ativo=True).count()

        # De-Para por origem
        depara_auto = DeParaProdutoCliente.query.filter_by(
            ativo=True,
            criado_por='AIResolverService'
        ).count()

        return jsonify({
            'sucesso': True,
            'estatisticas': {
                'linhas': {
                    'total': total_linhas,
                    'resolvidas': resolvidas,
                    'pendentes': total_linhas - resolvidas,
                    'taxa_resolucao': resolvidas / total_linhas if total_linhas > 0 else 0
                },
                'por_metodo': {
                    metodo or 'PENDENTE': count
                    for metodo, count in por_metodo
                },
                'depara': {
                    'total': total_depara,
                    'auto_haiku': depara_auto,
                    'manual': total_depara - depara_auto
                }
            }
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# IMPORTACAO E EXPORTACAO DE DE-PARA
# =============================================================================

def normalizar_cnpj_para_prefixo(cnpj: str) -> str:
    """
    Normaliza CNPJ para prefixo de 8 digitos.

    Aceita:
    - CNPJ formatado: 00.000.000/0000-00
    - CNPJ inteiro: 00000000000000 (14 digitos)
    - Prefixo: 00000000 (8 digitos)

    Returns:
        Prefixo de 8 digitos (apenas numeros)
    """
    import re
    # Remove tudo que nao for digito
    apenas_digitos = re.sub(r'\D', '', str(cnpj).strip())

    # Retorna os primeiros 8 digitos
    return apenas_digitos[:8].zfill(8)


@ai_bp.route('/api/depara/importar', methods=['POST'])
@login_required
def api_importar_depara():
    """
    Importa De-Para de arquivo XLSX.

    POST /devolucao/ai/api/depara/importar
    Form-data:
        - arquivo: arquivo XLSX
        - atualizar_existentes: 'true' ou 'false'

    Colunas obrigatorias:
        - codigo_cliente
        - prefixo_cnpj (pode ser formatado ou inteiro)
        - nosso_codigo

    Colunas opcionais:
        - fator_conversao (default: 1.0)

    Returns:
        JSON com resultado da importacao
    """
    import pandas as pd
    from io import BytesIO

    try:
        from app.producao.models import CadastroPalletizacao

        # Validar arquivo
        if 'arquivo' not in request.files:
            return jsonify({
                'sucesso': False,
                'erro': 'Nenhum arquivo enviado'
            }), 400

        arquivo = request.files['arquivo']
        if not arquivo.filename:
            return jsonify({
                'sucesso': False,
                'erro': 'Arquivo vazio'
            }), 400

        # Verificar extensao
        extensao = arquivo.filename.rsplit('.', 1)[-1].lower()
        if extensao not in ['xlsx', 'xls']:
            return jsonify({
                'sucesso': False,
                'erro': 'Formato invalido. Use .xlsx ou .xls'
            }), 400

        atualizar_existentes = request.form.get('atualizar_existentes', 'false').lower() == 'true'

        # Ler arquivo
        conteudo = BytesIO(arquivo.read())
        df = pd.read_excel(conteudo)

        # Normalizar nomes de colunas
        df.columns = [col.lower().strip().replace(' ', '_') for col in df.columns]

        # Validar colunas obrigatorias
        colunas_obrigatorias = ['codigo_cliente', 'prefixo_cnpj', 'nosso_codigo']
        colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]
        if colunas_faltantes:
            return jsonify({
                'sucesso': False,
                'erro': f'Colunas obrigatorias faltando: {", ".join(colunas_faltantes)}'
            }), 400

        # Processar linhas
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        criados = 0
        atualizados = 0
        ignorados = 0
        erros = []

        for idx, row in df.iterrows():
            linha_num = idx + 2  # +2 porque idx comeca em 0 e Excel tem header na linha 1

            try:
                codigo_cliente = str(row['codigo_cliente']).strip()
                prefixo_cnpj = normalizar_cnpj_para_prefixo(row['prefixo_cnpj'])
                nosso_codigo = str(row['nosso_codigo']).strip()

                # Ler fator_conversao (opcional)
                fator_conversao = 1.0
                if 'fator_conversao' in df.columns:
                    valor_fator = row.get('fator_conversao')
                    if pd.notna(valor_fator):
                        try:
                            fator_conversao = float(valor_fator)
                        except (ValueError, TypeError):
                            pass  # Manter default 1.0

                # Validar campos
                if not codigo_cliente or codigo_cliente == 'nan':
                    erros.append(f'Linha {linha_num}: codigo_cliente vazio')
                    continue
                if len(prefixo_cnpj) < 8:
                    erros.append(f'Linha {linha_num}: prefixo_cnpj invalido ({row["prefixo_cnpj"]})')
                    continue
                if not nosso_codigo or nosso_codigo == 'nan':
                    erros.append(f'Linha {linha_num}: nosso_codigo vazio')
                    continue

                # Buscar descricao do nosso produto
                produto = CadastroPalletizacao.query.filter_by(
                    cod_produto=nosso_codigo
                ).first()
                descricao_nosso = produto.nome_produto if produto else None

                # Verificar se ja existe (inclui inativos para evitar violacao de constraint)
                existente = DeParaProdutoCliente.query.filter_by(
                    prefixo_cnpj=prefixo_cnpj,
                    codigo_cliente=codigo_cliente
                ).first()

                if existente:
                    if existente.ativo:
                        # Registro ativo - atualizar se permitido
                        if atualizar_existentes:
                            existente.nosso_codigo = nosso_codigo
                            existente.descricao_nosso = descricao_nosso
                            existente.fator_conversao = fator_conversao
                            existente.atualizado_em = agora_brasil()
                            existente.atualizado_por = usuario
                            atualizados += 1
                        else:
                            ignorados += 1
                    else:
                        # Registro inativo - reativar e atualizar
                        existente.nosso_codigo = nosso_codigo
                        existente.descricao_nosso = descricao_nosso
                        existente.fator_conversao = fator_conversao
                        existente.ativo = True
                        existente.atualizado_em = agora_brasil()
                        existente.atualizado_por = usuario
                        atualizados += 1
                else:
                    novo = DeParaProdutoCliente(
                        prefixo_cnpj=prefixo_cnpj,
                        codigo_cliente=codigo_cliente,
                        nosso_codigo=nosso_codigo,
                        descricao_nosso=descricao_nosso,
                        fator_conversao=fator_conversao,
                        ativo=True,
                        criado_por=usuario
                    )
                    db.session.add(novo)
                    criados += 1

            except Exception as e:
                erros.append(f'Linha {linha_num}: {str(e)}')
                continue

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'criados': criados,
            'atualizados': atualizados,
            'ignorados': ignorados,
            'erros': erros
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@ai_bp.route('/api/depara/exportar', methods=['GET'])
@login_required
def api_exportar_depara():
    """
    Exporta De-Para para arquivo XLSX.

    GET /devolucao/ai/api/depara/exportar?prefixo_cnpj=93209760

    Query params:
        - prefixo_cnpj: filtrar por prefixo (opcional)

    Returns:
        Arquivo XLSX para download
    """
    import pandas as pd
    from io import BytesIO
    from flask import send_file

    try:
        prefixo_cnpj = request.args.get('prefixo_cnpj')

        query = DeParaProdutoCliente.query.filter_by(ativo=True)

        if prefixo_cnpj:
            query = query.filter_by(prefixo_cnpj=prefixo_cnpj[:8])

        items = query.order_by(
            DeParaProdutoCliente.prefixo_cnpj,
            DeParaProdutoCliente.codigo_cliente
        ).all()

        if not items:
            return jsonify({
                'sucesso': False,
                'erro': 'Nenhum registro encontrado'
            }), 404

        # Criar DataFrame
        dados = [{
            'codigo_cliente': item.codigo_cliente,
            'descricao_cliente': item.descricao_cliente or '',
            'prefixo_cnpj': item.prefixo_cnpj,
            'nome_grupo': item.nome_grupo or '',
            'nosso_codigo': item.nosso_codigo,
            'descricao_nosso': item.descricao_nosso or '',
            'fator_conversao': float(item.fator_conversao) if item.fator_conversao else 1.0
        } for item in items]

        df = pd.DataFrame(dados)

        # Gerar arquivo XLSX
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='DePara')

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'depara_produtos_{agora_brasil().strftime("%Y%m%d")}.xlsx'
        )

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500

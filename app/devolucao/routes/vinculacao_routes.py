"""
Rotas de Vinculacao de NFDs
===========================

APIs para:
- Importar NFDs do Odoo (sincronizacao)
- Listar NFDs orfas (sem vinculo com monitoramento)
- Vincular NFD manualmente a entrega
- Listar candidatos para vinculacao

Criado em: 30/12/2024
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app.devolucao.services import get_nfd_service
from app.devolucao.models import NFDevolucao, NFDevolucaoNFReferenciada

vinculacao_bp = Blueprint(
    'devolucao_vinculacao',
    __name__,
    url_prefix='/vinculacao'
)


# =============================================================================
# APIs DE SINCRONIZACAO
# =============================================================================

@vinculacao_bp.route('/api/sincronizar', methods=['POST'])
@login_required
def api_sincronizar_nfds():
    """
    Sincroniza NFDs do Odoo

    POST /devolucao/vinculacao/api/sincronizar
    Body (opcional):
    {
        "dias_retroativos": 30,
        "limite": 100,
        "minutos_janela": null
    }

    Returns:
        JSON com estatisticas da sincronizacao
    """
    try:
        data = request.get_json() or {}

        dias_retroativos = data.get('dias_retroativos', 30)
        limite = data.get('limite')
        minutos_janela = data.get('minutos_janela')
        data_inicio = data.get('data_inicio')
        data_fim = data.get('data_fim')

        service = get_nfd_service()
        resultado = service.importar_nfds(
            dias_retroativos=dias_retroativos,
            limite=limite,
            minutos_janela=minutos_janela,
            data_inicio=data_inicio,
            data_fim=data_fim
        )

        return jsonify(resultado)

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@vinculacao_bp.route('/api/sincronizar/incremental', methods=['POST'])
@login_required
def api_sincronizar_incremental():
    """
    Sincronizacao incremental (ultimos 60 minutos)

    POST /devolucao/vinculacao/api/sincronizar/incremental
    """
    try:
        service = get_nfd_service()
        resultado = service.importar_nfds(minutos_janela=60)
        return jsonify(resultado)

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# APIs DE LISTAGEM
# =============================================================================

@vinculacao_bp.route('/api/orfas', methods=['GET'])
@login_required
def api_listar_orfas():
    """
    Lista NFDs orfas (importadas do Odoo sem vinculo no monitoramento)

    GET /devolucao/vinculacao/api/orfas?cnpj_prefixo=12345678

    Query params:
        cnpj_prefixo: Filtrar por prefixo CNPJ (8 digitos)
    """
    try:
        cnpj_prefixo = request.args.get('cnpj_prefixo')

        service = get_nfd_service()
        nfds = service.listar_nfds_orfas(cnpj_prefixo=cnpj_prefixo)

        return jsonify({
            'sucesso': True,
            'total': len(nfds),
            'nfds': nfds
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@vinculacao_bp.route('/api/<int:nfd_id>/candidatos', methods=['GET'])
@login_required
def api_listar_candidatos(nfd_id: int):
    """
    Lista candidatos para vinculacao de uma NFD orfa

    GET /devolucao/vinculacao/api/<nfd_id>/candidatos

    Busca NFDs registradas no monitoramento com mesmo prefixo CNPJ
    que ainda nao foram vinculadas ao Odoo
    """
    try:
        service = get_nfd_service()
        candidatos = service.listar_candidatos_vinculacao(nfd_id)

        return jsonify({
            'sucesso': True,
            'nfd_id': nfd_id,
            'total': len(candidatos),
            'candidatos': candidatos
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@vinculacao_bp.route('/api/<int:nfd_id>', methods=['GET'])
@login_required
def api_obter_nfd(nfd_id: int):
    """
    Obtem detalhes de uma NFD

    GET /devolucao/vinculacao/api/<nfd_id>
    """
    try:
        nfd = NFDevolucao.query.get(nfd_id)

        if not nfd:
            return jsonify({
                'sucesso': False,
                'erro': 'NFD nao encontrada'
            }), 404

        # Obter NFs referenciadas
        nfs_ref = NFDevolucaoNFReferenciada.query.filter_by(
            nf_devolucao_id=nfd_id
        ).all()

        dados = nfd.to_dict()
        dados['nfs_referenciadas'] = [ref.to_dict() for ref in nfs_ref]
        dados['linhas'] = [linha.to_dict() for linha in nfd.linhas.all()]

        # Dados da ocorrencia se existir
        if nfd.ocorrencia:
            dados['ocorrencia'] = nfd.ocorrencia.to_dict()

        return jsonify({
            'sucesso': True,
            'nfd': dados
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# APIs DE VINCULACAO
# =============================================================================

@vinculacao_bp.route('/api/<int:nfd_id>/vincular', methods=['POST'])
@login_required
def api_vincular_manual(nfd_id: int):
    """
    Vincula manualmente uma NFD orfa a uma entrega monitorada

    POST /devolucao/vinculacao/api/<nfd_id>/vincular
    Body:
    {
        "entrega_monitorada_id": 123
    }
    """
    try:
        data = request.get_json()

        if not data or 'entrega_monitorada_id' not in data:
            return jsonify({
                'sucesso': False,
                'erro': 'entrega_monitorada_id e obrigatorio'
            }), 400

        entrega_id = data['entrega_monitorada_id']
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        service = get_nfd_service()
        resultado = service.vincular_nfd_manual(
            nfd_id=nfd_id,
            entrega_monitorada_id=entrega_id,
            usuario=usuario
        )

        if resultado['sucesso']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@vinculacao_bp.route('/api/<int:nfd_id>/nfs-referenciadas', methods=['GET'])
@login_required
def api_listar_nfs_referenciadas(nfd_id: int):
    """
    Lista NFs de venda referenciadas pela NFD

    GET /devolucao/vinculacao/api/<nfd_id>/nfs-referenciadas
    """
    try:
        nfd = NFDevolucao.query.get(nfd_id)
        if not nfd:
            return jsonify({
                'sucesso': False,
                'erro': 'NFD nao encontrada'
            }), 404

        nfs_ref = NFDevolucaoNFReferenciada.query.filter_by(
            nf_devolucao_id=nfd_id
        ).order_by(NFDevolucaoNFReferenciada.criado_em.desc()).all()

        return jsonify({
            'sucesso': True,
            'nfd_id': nfd_id,
            'total': len(nfs_ref),
            'nfs_referenciadas': [{
                'id': nf.id,
                'numero_nf': nf.numero_nf,
                'serie_nf': nf.serie_nf,
                'chave_nf': nf.chave_nf,
                'data_emissao_nf': nf.data_emissao_nf.isoformat() if nf.data_emissao_nf else None,
                'origem': nf.origem,
                'entrega_id': nf.entrega_monitorada_id,
                'criado_em': nf.criado_em.isoformat() if nf.criado_em else None
            } for nf in nfs_ref]
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@vinculacao_bp.route('/api/<int:nfd_id>/nfs-referenciadas', methods=['POST'])
@login_required
def api_adicionar_nf_referenciada(nfd_id: int):
    """
    Adiciona NF referenciada manualmente

    POST /devolucao/vinculacao/api/<nfd_id>/nfs-referenciadas
    Body:
    {
        "numero_nf": "12345",
        "serie_nf": "1",
        "chave_nf": null
    }
    """
    try:
        data = request.get_json()

        if not data or 'numero_nf' not in data:
            return jsonify({
                'sucesso': False,
                'erro': 'numero_nf e obrigatorio'
            }), 400

        # Verificar se NFD existe
        nfd = NFDevolucao.query.get(nfd_id)
        if not nfd:
            return jsonify({
                'sucesso': False,
                'erro': 'NFD nao encontrada'
            }), 404

        # Verificar se ja existe
        existe = NFDevolucaoNFReferenciada.query.filter_by(
            nf_devolucao_id=nfd_id,
            numero_nf=data['numero_nf'],
            serie_nf=data.get('serie_nf')
        ).first()

        if existe:
            return jsonify({
                'sucesso': False,
                'erro': 'NF referenciada ja existe'
            }), 400

        # Criar novo registro
        from app.utils.timezone import agora_brasil
        from app import db

        ref = NFDevolucaoNFReferenciada(
            nf_devolucao_id=nfd_id,
            numero_nf=data['numero_nf'],
            serie_nf=data.get('serie_nf'),
            chave_nf=data.get('chave_nf'),
            origem='MANUAL',
            criado_em=agora_brasil(),
            criado_por=current_user.nome if hasattr(current_user, 'nome') else str(current_user.id),
        )

        db.session.add(ref)
        db.session.commit()

        return jsonify({
            'sucesso': True,
            'nf_referenciada': ref.to_dict()
        })

    except Exception as e:
        from app import db
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@vinculacao_bp.route('/api/<int:nfd_id>/nfs-referenciadas/<int:ref_id>', methods=['DELETE'])
@login_required
def api_remover_nf_referenciada(nfd_id: int, ref_id: int):
    """
    Remove NF referenciada (apenas se foi adicionada manualmente)

    DELETE /devolucao/vinculacao/api/<nfd_id>/nfs-referenciadas/<ref_id>
    """
    try:
        from app import db

        ref = NFDevolucaoNFReferenciada.query.filter_by(
            id=ref_id,
            nf_devolucao_id=nfd_id
        ).first()

        if not ref:
            return jsonify({
                'sucesso': False,
                'erro': 'NF referenciada nao encontrada'
            }), 404

        # Apenas permite remover se foi adicionada manualmente
        if ref.origem != 'MANUAL':
            return jsonify({
                'sucesso': False,
                'erro': 'Apenas NFs adicionadas manualmente podem ser removidas'
            }), 400

        db.session.delete(ref)
        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': 'NF referenciada removida'
        })

    except Exception as e:
        from app import db
        db.session.rollback()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# APIs DE ESTATISTICAS
# =============================================================================

@vinculacao_bp.route('/api/estatisticas', methods=['GET'])
@login_required
def api_estatisticas():
    """
    Retorna estatisticas de NFDs

    GET /devolucao/vinculacao/api/estatisticas
    """
    try:
        from sqlalchemy import func
        from app import db

        # Total de NFDs
        total = NFDevolucao.query.filter_by(ativo=True).count()

        # NFDs orfas (sem entrega_monitorada e origem=ODOO)
        orfas = NFDevolucao.query.filter(
            NFDevolucao.entrega_monitorada_id.is_(None),
            NFDevolucao.origem_registro == 'ODOO',
            NFDevolucao.ativo == True
        ).count()

        # NFDs do monitoramento
        monitoramento = NFDevolucao.query.filter(
            NFDevolucao.origem_registro == 'MONITORAMENTO',
            NFDevolucao.ativo == True
        ).count()

        # NFDs vinculadas (do monitoramento com DFe do Odoo)
        vinculadas = NFDevolucao.query.filter(
            NFDevolucao.origem_registro == 'MONITORAMENTO',
            NFDevolucao.odoo_dfe_id.isnot(None),
            NFDevolucao.ativo == True
        ).count()

        # Aguardando vinculacao (do monitoramento sem DFe)
        aguardando = NFDevolucao.query.filter(
            NFDevolucao.origem_registro == 'MONITORAMENTO',
            NFDevolucao.odoo_dfe_id.is_(None),
            NFDevolucao.ativo == True
        ).count()

        # Por status
        por_status = db.session.query(
            NFDevolucao.status,
            func.count(NFDevolucao.id)
        ).filter(
            NFDevolucao.ativo == True
        ).group_by(NFDevolucao.status).all()

        return jsonify({
            'sucesso': True,
            'estatisticas': {
                'total': total,
                'orfas': orfas,
                'monitoramento': monitoramento,
                'vinculadas': vinculadas,
                'aguardando_vinculacao': aguardando,
                'por_status': {status: count for status, count in por_status}
            }
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500

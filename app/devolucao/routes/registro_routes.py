"""
Rotas de Registro de NFD no Monitoramento
==========================================

Endpoints para registro de notas fiscais de devolucao
pelo time de monitoramento durante a finalizacao de entregas.

Criado em: 30/12/2024
"""
from flask import (
    Blueprint, request, jsonify, render_template,
)
from flask_login import login_required, current_user
from app import db
from app.devolucao.models import NFDevolucao, OcorrenciaDevolucao
from app.monitoramento.models import EntregaMonitorada
from app.utils.timezone import agora_brasil

# Blueprint
registro_bp = Blueprint('devolucao_registro', __name__, url_prefix='/registro')


# =============================================================================
# API Endpoints
# =============================================================================

@registro_bp.route('/api/registrar', methods=['POST'])
@login_required
def api_registrar_nfd():
    """
    Registra uma NFD vinculada a uma entrega

    Body JSON:
    {
        "entrega_id": 123,
        "numero_nfd": "12345",
        "motivo": "AVARIA",
        "descricao_motivo": "Produto chegou danificado",
        "numero_nf_venda": "654321"  # opcional, preenche automatico se entrega_id
    }

    Returns:
        JSON com id da NFD criada
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Dados nao fornecidos'}), 400

        # Validacoes
        entrega_id = data.get('entrega_id')
        numero_nfd = data.get('numero_nfd', '').strip()
        motivo = data.get('motivo', '').strip()
        descricao_motivo = data.get('descricao_motivo', '').strip()

        if not numero_nfd:
            return jsonify({'success': False, 'error': 'Numero da NFD e obrigatorio'}), 400

        if not motivo:
            return jsonify({'success': False, 'error': 'Motivo e obrigatorio'}), 400

        # Validar motivo
        motivos_validos = [m[0] for m in NFDevolucao.MOTIVOS_DEVOLUCAO]
        if motivo not in motivos_validos:
            return jsonify({
                'success': False,
                'error': f'Motivo invalido. Opcoes: {", ".join(motivos_validos)}'
            }), 400

        # Buscar entrega se fornecida
        entrega = None
        numero_nf_venda = data.get('numero_nf_venda')
        cnpj_emitente = None

        if entrega_id:
            entrega = db.session.get(EntregaMonitorada,entrega_id) if entrega_id else None
            if not entrega:
                return jsonify({'success': False, 'error': 'Entrega nao encontrada'}), 404

            # Preencher dados automaticamente
            if not numero_nf_venda:
                numero_nf_venda = entrega.numero_nf
            cnpj_emitente = entrega.cnpj_cliente

            # Marcar entrega como teve_devolucao
            entrega.teve_devolucao = True

        # Verificar se NFD ja existe para esta entrega
        if entrega_id:
            nfd_existente = NFDevolucao.query.filter_by(
                entrega_monitorada_id=entrega_id,
                numero_nfd=numero_nfd,
                ativo=True
            ).first()

            if nfd_existente:
                return jsonify({
                    'success': False,
                    'error': f'NFD {numero_nfd} ja registrada para esta entrega'
                }), 400

        # Criar NFD
        nfd = NFDevolucao(
            entrega_monitorada_id=entrega_id,
            numero_nfd=numero_nfd,
            motivo=motivo,
            descricao_motivo=descricao_motivo if descricao_motivo else None,
            numero_nf_venda=numero_nf_venda,
            cnpj_emitente=cnpj_emitente,
            nome_emitente=entrega.cliente if entrega else None,
            status='REGISTRADA',
            criado_por=current_user.nome if hasattr(current_user, 'nome') else current_user.username
        )

        db.session.add(nfd)
        db.session.flush()  # Para obter o ID

        # Criar ocorrencia automaticamente
        numero_ocorrencia = OcorrenciaDevolucao.gerar_numero_ocorrencia()
        ocorrencia = OcorrenciaDevolucao(
            nf_devolucao_id=nfd.id,
            numero_ocorrencia=numero_ocorrencia,
            criado_por=current_user.nome if hasattr(current_user, 'nome') else current_user.username
        )

        db.session.add(ocorrencia)
        db.session.commit()

        return jsonify({
            'success': True,
            'nfd_id': nfd.id,
            'numero_nfd': nfd.numero_nfd,
            'ocorrencia_id': ocorrencia.id,
            'numero_ocorrencia': ocorrencia.numero_ocorrencia,
            'message': f'NFD {numero_nfd} registrada com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@registro_bp.route('/api/listar/<int:entrega_id>', methods=['GET'])
@login_required
def api_listar_nfds(entrega_id):
    """
    Lista NFDs registradas para uma entrega

    Returns:
        JSON com lista de NFDs
    """
    try:
        nfds = NFDevolucao.query.filter_by(
            entrega_monitorada_id=entrega_id,
            ativo=True
        ).order_by(NFDevolucao.criado_em.desc()).all()

        return jsonify({
            'success': True,
            'nfds': [nfd.to_dict() for nfd in nfds],
            'total': len(nfds)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@registro_bp.route('/api/<int:nfd_id>', methods=['GET'])
@login_required
def api_obter_nfd(nfd_id):
    """
    Obtem detalhes de uma NFD

    Returns:
        JSON com dados da NFD
    """
    try:
        nfd = db.session.get(NFDevolucao,nfd_id) if nfd_id else None

        if not nfd:
            return jsonify({'success': False, 'error': 'NFD nao encontrada'}), 404

        return jsonify({
            'success': True,
            'nfd': nfd.to_dict()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@registro_bp.route('/api/<int:nfd_id>', methods=['PUT'])
@login_required
def api_atualizar_nfd(nfd_id):
    """
    Atualiza dados de uma NFD

    Body JSON:
    {
        "motivo": "FALTA",
        "descricao_motivo": "Nova descricao"
    }
    """
    try:
        nfd = db.session.get(NFDevolucao,nfd_id) if nfd_id else None

        if not nfd:
            return jsonify({'success': False, 'error': 'NFD nao encontrada'}), 404

        data = request.get_json()

        if 'motivo' in data:
            motivos_validos = [m[0] for m in NFDevolucao.MOTIVOS_DEVOLUCAO]
            if data['motivo'] not in motivos_validos:
                return jsonify({
                    'success': False,
                    'error': f'Motivo invalido. Opcoes: {", ".join(motivos_validos)}'
                }), 400
            nfd.motivo = data['motivo']

        if 'descricao_motivo' in data:
            nfd.descricao_motivo = data['descricao_motivo']

        if 'numero_nfd' in data:
            nfd.numero_nfd = data['numero_nfd']

        nfd.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else current_user.username
        nfd.atualizado_em = agora_brasil()

        db.session.commit()

        return jsonify({
            'success': True,
            'nfd': nfd.to_dict(),
            'message': 'NFD atualizada com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@registro_bp.route('/api/<int:nfd_id>', methods=['DELETE'])
@login_required
def api_excluir_nfd(nfd_id):
    """
    Exclui (desativa) uma NFD

    Note: Faz soft delete (ativo=False)
    """
    try:
        nfd = db.session.get(NFDevolucao,nfd_id) if nfd_id else None

        if not nfd:
            return jsonify({'success': False, 'error': 'NFD nao encontrada'}), 404

        # Soft delete
        nfd.ativo = False
        nfd.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else current_user.username
        nfd.atualizado_em = agora_brasil()

        # Desativar ocorrencia tambem
        if nfd.ocorrencia:
            nfd.ocorrencia.ativo = False
            nfd.ocorrencia.atualizado_por = nfd.atualizado_por
            nfd.ocorrencia.atualizado_em = agora_brasil()

        # Verificar se entrega ainda tem outras NFDs ativas
        if nfd.entrega_monitorada:
            outras_nfds = NFDevolucao.query.filter(
                NFDevolucao.entrega_monitorada_id == nfd.entrega_monitorada_id,
                NFDevolucao.id != nfd_id,
                NFDevolucao.ativo == True
            ).count()

            if outras_nfds == 0:
                nfd.entrega_monitorada.teve_devolucao = False

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'NFD excluida com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@registro_bp.route('/api/motivos', methods=['GET'])
@login_required
def api_listar_motivos():
    """
    Lista motivos disponiveis para devolucao

    Returns:
        JSON com lista de motivos
    """
    return jsonify({
        'success': True,
        'motivos': [
            {'valor': m[0], 'descricao': m[1]}
            for m in NFDevolucao.MOTIVOS_DEVOLUCAO
        ]
    })


# =============================================================================
# Rotas de Pagina
# =============================================================================

@registro_bp.route('/modal/<int:entrega_id>')
@login_required
def modal_registro(entrega_id):
    """
    Renderiza modal de registro de NFD

    Returns:
        HTML do modal
    """
    entrega = EntregaMonitorada.query.get_or_404(entrega_id)

    # NFDs ja registradas
    nfds_existentes = NFDevolucao.query.filter_by(
        entrega_monitorada_id=entrega_id,
        ativo=True
    ).order_by(NFDevolucao.criado_em.desc()).all()

    return render_template(
        'devolucao/registro/modal_nfd.html',
        entrega=entrega,
        nfds_existentes=nfds_existentes,
        motivos=NFDevolucao.MOTIVOS_DEVOLUCAO
    )


# Registrar blueprint no modulo principal
def init_app(app):
    """Registra o blueprint no aplicativo Flask"""
    from app.devolucao import devolucao_bp
    devolucao_bp.register_blueprint(registro_bp)

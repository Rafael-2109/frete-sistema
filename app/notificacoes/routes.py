#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROTAS DE NOTIFICACOES
API endpoints para gerenciamento de notificacoes

Endpoints:
- GET /notificacoes/ - Lista notificacoes do usuario
- GET /notificacoes/<id> - Detalhes de uma notificacao
- POST /notificacoes/<id>/lido - Marca como lida
- POST /notificacoes/marcar-todas-lidas - Marca todas como lidas
- GET /notificacoes/api/nao-lidas - Contador de nao lidas (para navbar)
- GET /notificacoes/webhooks - Lista webhooks configurados
- POST /notificacoes/webhooks - Cadastra novo webhook
"""

from flask import jsonify, request
from flask_login import login_required, current_user
from app.notificacoes import notificacoes_bp
from app.notificacoes.models import AlertaNotificacao, WebhookConfig
from app import db
from app.utils.logging_config import logger


@notificacoes_bp.route('/')
@login_required
def listar_notificacoes():
    """Lista notificacoes do usuario logado"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')  # filtro opcional

        query = AlertaNotificacao.query.filter(
            AlertaNotificacao.user_id == current_user.id,
            AlertaNotificacao.canais.contains(['in_app'])
        )

        if status:
            query = query.filter(AlertaNotificacao.status_envio == status)

        notificacoes = query.order_by(
            AlertaNotificacao.criado_em.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'success': True,
            'notificacoes': [n.to_dict() for n in notificacoes.items],
            'total': notificacoes.total,
            'pages': notificacoes.pages,
            'current_page': page,
            'has_next': notificacoes.has_next,
            'has_prev': notificacoes.has_prev,
        })

    except Exception as e:
        logger.error(f"Erro ao listar notificacoes: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Erro ao listar notificacoes'
        }), 500


@notificacoes_bp.route('/<int:id>')
@login_required
def detalhe_notificacao(id):
    """Retorna detalhes de uma notificacao"""
    try:
        notificacao = AlertaNotificacao.query.filter(
            AlertaNotificacao.id == id,
            AlertaNotificacao.user_id == current_user.id
        ).first_or_404()

        return jsonify({
            'success': True,
            'notificacao': notificacao.to_dict()
        })

    except Exception as e:
        logger.error(f"Erro ao buscar notificacao {id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Notificacao nao encontrada'
        }), 404


@notificacoes_bp.route('/<int:id>/lido', methods=['POST'])
@login_required
def marcar_como_lida(id):
    """Marca uma notificacao como lida"""
    try:
        notificacao = AlertaNotificacao.query.filter(
            AlertaNotificacao.id == id,
            AlertaNotificacao.user_id == current_user.id
        ).first_or_404()

        notificacao.marcar_como_lido()

        return jsonify({
            'success': True,
            'message': 'Notificacao marcada como lida'
        })

    except Exception as e:
        logger.error(f"Erro ao marcar notificacao {id} como lida: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Erro ao marcar notificacao como lida'
        }), 500


@notificacoes_bp.route('/marcar-todas-lidas', methods=['POST'])
@login_required
def marcar_todas_como_lidas():
    """Marca todas as notificacoes do usuario como lidas"""
    try:
        from datetime import datetime, timezone

        notificacoes = AlertaNotificacao.query.filter(
            AlertaNotificacao.user_id == current_user.id,
            AlertaNotificacao.status_envio != 'lido',
            AlertaNotificacao.canais.contains(['in_app'])
        ).all()

        agora = datetime.now(timezone.utc)
        for notificacao in notificacoes:
            notificacao.status_envio = 'lido'
            notificacao.lido_em = agora

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{len(notificacoes)} notificacoes marcadas como lidas'
        })

    except Exception as e:
        logger.error(f"Erro ao marcar todas notificacoes como lidas: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao marcar notificacoes como lidas'
        }), 500


@notificacoes_bp.route('/api/nao-lidas')
@login_required
def contar_nao_lidas():
    """Retorna contador de notificacoes nao lidas (para navbar)"""
    try:
        count = AlertaNotificacao.contar_nao_lidos_usuario(current_user.id)

        return jsonify({
            'success': True,
            'count': count
        })

    except Exception as e:
        logger.error(f"Erro ao contar notificacoes nao lidas: {e}", exc_info=True)
        return jsonify({
            'success': True,
            'count': 0
        })


@notificacoes_bp.route('/api/recentes')
@login_required
def listar_recentes():
    """Lista ultimas notificacoes nao lidas (para dropdown navbar)"""
    try:
        limite = request.args.get('limite', 5, type=int)
        notificacoes = AlertaNotificacao.buscar_nao_lidos_usuario(
            current_user.id,
            limite=limite
        )

        return jsonify({
            'success': True,
            'notificacoes': [n.to_dict() for n in notificacoes],
            'total_nao_lidas': AlertaNotificacao.contar_nao_lidos_usuario(current_user.id)
        })

    except Exception as e:
        logger.error(f"Erro ao listar notificacoes recentes: {e}", exc_info=True)
        return jsonify({
            'success': True,
            'notificacoes': [],
            'total_nao_lidas': 0
        })


# =============================================================================
# ROTAS DE ADMINISTRACAO (WEBHOOKS)
# =============================================================================

@notificacoes_bp.route('/webhooks')
@login_required
def listar_webhooks():
    """Lista webhooks configurados (apenas admins)"""
    try:
        # Verificar se e admin
        if current_user.perfil not in ['administrador', 'gerente']:
            return jsonify({
                'success': False,
                'error': 'Acesso negado'
            }), 403

        webhooks = WebhookConfig.query.all()

        return jsonify({
            'success': True,
            'webhooks': [w.to_dict() for w in webhooks]
        })

    except Exception as e:
        logger.error(f"Erro ao listar webhooks: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Erro ao listar webhooks'
        }), 500


@notificacoes_bp.route('/webhooks', methods=['POST'])
@login_required
def criar_webhook():
    """Cadastra novo webhook (apenas admins)"""
    try:
        # Verificar se e admin
        if current_user.perfil not in ['administrador', 'gerente']:
            return jsonify({
                'success': False,
                'error': 'Acesso negado'
            }), 403

        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados nao fornecidos'
            }), 400

        # Validar campos obrigatorios
        if not data.get('nome') or not data.get('url'):
            return jsonify({
                'success': False,
                'error': 'Nome e URL sao obrigatorios'
            }), 400

        webhook = WebhookConfig(
            nome=data['nome'],
            descricao=data.get('descricao'),
            url=data['url'],
            metodo=data.get('metodo', 'POST'),
            headers=data.get('headers'),
            auth_type=data.get('auth_type'),
            auth_token=data.get('auth_token'),
            tipos_alerta=data.get('tipos_alerta'),
            niveis_alerta=data.get('niveis_alerta'),
            ativo=data.get('ativo', True),
        )

        db.session.add(webhook)
        db.session.commit()

        logger.info(f"Webhook {webhook.id} criado por {current_user.nome}")

        return jsonify({
            'success': True,
            'webhook': webhook.to_dict(),
            'message': 'Webhook criado com sucesso'
        }), 201

    except Exception as e:
        logger.error(f"Erro ao criar webhook: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao criar webhook'
        }), 500


@notificacoes_bp.route('/webhooks/<int:id>', methods=['PUT'])
@login_required
def atualizar_webhook(id):
    """Atualiza webhook existente (apenas admins)"""
    try:
        # Verificar se e admin
        if current_user.perfil not in ['administrador', 'gerente']:
            return jsonify({
                'success': False,
                'error': 'Acesso negado'
            }), 403

        webhook = WebhookConfig.query.get_or_404(id)
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados nao fornecidos'
            }), 400

        # Atualizar campos
        if 'nome' in data:
            webhook.nome = data['nome']
        if 'descricao' in data:
            webhook.descricao = data['descricao']
        if 'url' in data:
            webhook.url = data['url']
        if 'metodo' in data:
            webhook.metodo = data['metodo']
        if 'headers' in data:
            webhook.headers = data['headers']
        if 'auth_type' in data:
            webhook.auth_type = data['auth_type']
        if 'auth_token' in data:
            webhook.auth_token = data['auth_token']
        if 'tipos_alerta' in data:
            webhook.tipos_alerta = data['tipos_alerta']
        if 'niveis_alerta' in data:
            webhook.niveis_alerta = data['niveis_alerta']
        if 'ativo' in data:
            webhook.ativo = data['ativo']

        db.session.commit()

        logger.info(f"Webhook {webhook.id} atualizado por {current_user.nome}")

        return jsonify({
            'success': True,
            'webhook': webhook.to_dict(),
            'message': 'Webhook atualizado com sucesso'
        })

    except Exception as e:
        logger.error(f"Erro ao atualizar webhook {id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao atualizar webhook'
        }), 500


@notificacoes_bp.route('/webhooks/<int:id>', methods=['DELETE'])
@login_required
def excluir_webhook(id):
    """Exclui webhook (apenas admins)"""
    try:
        # Verificar se e admin
        if current_user.perfil not in ['administrador', 'gerente']:
            return jsonify({
                'success': False,
                'error': 'Acesso negado'
            }), 403

        webhook = WebhookConfig.query.get_or_404(id)
        nome = webhook.nome

        db.session.delete(webhook)
        db.session.commit()

        logger.info(f"Webhook {id} ({nome}) excluido por {current_user.nome}")

        return jsonify({
            'success': True,
            'message': 'Webhook excluido com sucesso'
        })

    except Exception as e:
        logger.error(f"Erro ao excluir webhook {id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao excluir webhook'
        }), 500


@notificacoes_bp.route('/webhooks/<int:id>/testar', methods=['POST'])
@login_required
def testar_webhook(id):
    """Testa webhook com payload de exemplo (apenas admins)"""
    try:
        # Verificar se e admin
        if current_user.perfil not in ['administrador', 'gerente']:
            return jsonify({
                'success': False,
                'error': 'Acesso negado'
            }), 403

        webhook = WebhookConfig.query.get_or_404(id)

        # Criar alerta de teste
        from app.notificacoes.services import NotificationDispatcher
        dispatcher = NotificationDispatcher()

        alerta_teste = AlertaNotificacao(
            id=0,  # ID ficticio
            tipo='TESTE_WEBHOOK',
            nivel='INFO',
            titulo='Teste de Webhook',
            mensagem='Este e um teste de webhook do Sistema de Frete',
            dados={'teste': True, 'origem': 'manual'},
            criado_em=None,
        )
        from datetime import datetime, timezone
        alerta_teste.criado_em = datetime.now(timezone.utc)

        # Enviar para o webhook
        result = dispatcher._enviar_webhook_single(
            url=webhook.url,
            alerta=alerta_teste,
            config=webhook,
        )

        return jsonify({
            'success': result['success'],
            'resultado': result,
            'message': 'Teste enviado' if result['success'] else f"Teste falhou: {result.get('error')}"
        })

    except Exception as e:
        logger.error(f"Erro ao testar webhook {id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Erro ao testar webhook: {str(e)}'
        }), 500


# =============================================================================
# ROTA DE AUDITORIA (LISTAGEM GERAL)
# =============================================================================

@notificacoes_bp.route('/auditoria')
@login_required
def auditoria_notificacoes():
    """Lista todas as notificacoes para auditoria (apenas admins)"""
    try:
        # Verificar se e admin
        if current_user.perfil not in ['administrador', 'gerente']:
            return jsonify({
                'success': False,
                'error': 'Acesso negado'
            }), 403

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        tipo = request.args.get('tipo')
        nivel = request.args.get('nivel')
        status = request.args.get('status')

        query = AlertaNotificacao.query

        if tipo:
            query = query.filter(AlertaNotificacao.tipo == tipo)
        if nivel:
            query = query.filter(AlertaNotificacao.nivel == nivel)
        if status:
            query = query.filter(AlertaNotificacao.status_envio == status)

        notificacoes = query.order_by(
            AlertaNotificacao.criado_em.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'success': True,
            'notificacoes': [n.to_dict() for n in notificacoes.items],
            'total': notificacoes.total,
            'pages': notificacoes.pages,
            'current_page': page,
        })

    except Exception as e:
        logger.error(f"Erro ao listar auditoria de notificacoes: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Erro ao listar notificacoes'
        }), 500

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOTIFICATION DISPATCHER
Servico centralizado para envio de notificacoes por multiplos canais

Canais suportados:
- in_app: salva no banco para exibicao na UI
- email: envia via SMTP/SES/SendGrid
- webhook: HTTP POST para URLs externas

Uso:
    from app.notificacoes.services import NotificationDispatcher

    dispatcher = NotificationDispatcher()
    resultado = dispatcher.enviar_alerta(
        tipo='SEPARACAO_COTADA_ALTERADA',
        nivel='CRITICO',
        titulo='Separacao Alterada',
        mensagem='A separacao XYZ foi alterada...',
        dados={'pedido': '123', 'produto': 'ABC'},
        canais=['in_app', 'email'],
        email_destinatario='usuario@empresa.com'
    )
"""

import json
import requests
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app import db
from app.utils.logging_config import logger
from app.notificacoes.models import AlertaNotificacao, WebhookConfig
from app.notificacoes.email_sender import email_sender, EmailTemplates, EmailConfig


class NotificationDispatcher:
    """
    Dispatcher centralizado para envio de notificacoes.
    Gerencia multiplos canais de forma unificada.
    """

    # Timeout padrao para webhooks (segundos)
    WEBHOOK_TIMEOUT = 30

    # Maximo de tentativas de reenvio
    MAX_RETRY_ATTEMPTS = 3

    def __init__(self):
        self.email_sender = email_sender
        self.email_templates = EmailTemplates

    def enviar_alerta(
        self,
        tipo: str,
        nivel: str,
        titulo: str,
        mensagem: str,
        dados: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        canais: Optional[List[str]] = None,
        origem: Optional[str] = None,
        referencia_id: Optional[str] = None,
        referencia_tipo: Optional[str] = None,
        email_destinatario: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Envia alerta por todos os canais especificados.

        Args:
            tipo: Tipo do alerta (ex: SEPARACAO_COTADA_ALTERADA)
            nivel: Nivel de severidade (CRITICO, ATENCAO, INFO)
            titulo: Titulo curto do alerta
            mensagem: Mensagem detalhada
            dados: Dicionario com contexto adicional
            user_id: ID do usuario destinatario (para in_app)
            canais: Lista de canais ['in_app', 'email', 'webhook']
            origem: Modulo de origem (ex: sincronizacao_odoo)
            referencia_id: ID do objeto relacionado
            referencia_tipo: Tipo do objeto (ex: pedido, separacao)
            email_destinatario: Email para envio direto
            webhook_url: URL especifica para webhook

        Returns:
            dict: {
                'success': bool,
                'alerta_id': int,
                'resultados': {'in_app': bool, 'email': bool, 'webhook': bool},
                'erros': list
            }
        """
        if canais is None:
            canais = ['in_app']

        resultado = {
            'success': True,
            'alerta_id': None,
            'resultados': {},
            'erros': []
        }

        try:
            # 1. Criar alerta no banco (sempre, para auditoria)
            alerta = AlertaNotificacao.criar_alerta(
                tipo=tipo,
                nivel=nivel,
                titulo=titulo,
                mensagem=mensagem,
                dados=dados,
                user_id=user_id,
                canais=canais,
                origem=origem,
                referencia_id=referencia_id,
                referencia_tipo=referencia_tipo,
                email_destinatario=email_destinatario,
                webhook_url=webhook_url,
            )
            resultado['alerta_id'] = alerta.id

            logger.info(f"Alerta {alerta.id} criado: [{nivel}] {tipo}")

            # 2. Processar cada canal
            if 'in_app' in canais:
                resultado['resultados']['in_app'] = self._enviar_in_app(alerta)

            if 'email' in canais:
                email_result = self._enviar_email(alerta)
                resultado['resultados']['email'] = email_result['success']
                if not email_result['success']:
                    resultado['erros'].append(f"Email: {email_result['error']}")

            if 'webhook' in canais:
                webhook_results = self._enviar_webhooks(alerta)
                resultado['resultados']['webhook'] = any(r['success'] for r in webhook_results)
                for r in webhook_results:
                    if not r['success']:
                        resultado['erros'].append(f"Webhook {r.get('url', 'desconhecido')}: {r['error']}")

            # 3. Atualizar status do alerta
            if not resultado['erros']:
                alerta.marcar_como_enviado()
            else:
                resultado['success'] = False

            return resultado

        except Exception as e:
            logger.error(f"Erro ao enviar alerta: {e}", exc_info=True)
            resultado['success'] = False
            resultado['erros'].append(str(e))
            return resultado

    def _enviar_in_app(self, alerta: AlertaNotificacao) -> bool:
        """
        Processa envio in_app (ja salvo no banco).
        Apenas marca como enviado.
        """
        try:
            alerta.status_envio = 'enviado'
            db.session.commit()
            logger.info(f"Alerta {alerta.id} marcado como enviado (in_app)")
            return True
        except Exception as e:
            logger.error(f"Erro ao marcar alerta como enviado: {e}")
            return False

    def _enviar_email(self, alerta: AlertaNotificacao) -> Dict[str, Any]:
        """
        Envia alerta por email.
        """
        if not EmailConfig.is_configured():
            alerta.marcar_como_falhou('Email nao configurado', canal='email')
            return {
                'success': False,
                'error': 'Email nao configurado. Verifique variaveis de ambiente EMAIL_*'
            }

        destinatario = alerta.email_destinatario
        if not destinatario:
            # Tentar buscar email do usuario
            if alerta.user_id:
                try:
                    from app.auth.models import Usuario
                    user = Usuario.query.get(alerta.user_id)
                    if user and user.email:
                        destinatario = user.email
                except Exception:
                    pass

        if not destinatario:
            alerta.marcar_como_falhou('Email destinatario nao definido', canal='email')
            return {
                'success': False,
                'error': 'Email destinatario nao definido'
            }

        # Escolher template baseado no nivel
        if alerta.nivel == 'CRITICO':
            body_html = self.email_templates.alerta_critico(
                alerta.titulo, alerta.mensagem, alerta.dados
            )
        elif alerta.nivel == 'ATENCAO':
            body_html = self.email_templates.alerta_atencao(
                alerta.titulo, alerta.mensagem, alerta.dados
            )
        else:
            body_html = self.email_templates.info(
                alerta.titulo, alerta.mensagem, alerta.dados
            )

        subject = f"[{alerta.nivel}] {alerta.titulo}"

        result = self.email_sender.send(
            to=destinatario,
            subject=subject,
            body_html=body_html,
            body_text=alerta.mensagem,
        )

        if result['success']:
            alerta.marcar_como_enviado(canal='email')
        else:
            alerta.marcar_como_falhou(result['error'], canal='email')

        return result

    def _enviar_webhooks(self, alerta: AlertaNotificacao) -> List[Dict[str, Any]]:
        """
        Envia alerta para todos os webhooks configurados.
        """
        resultados = []

        # 1. Webhook especifico do alerta
        if alerta.webhook_url:
            result = self._enviar_webhook_single(
                url=alerta.webhook_url,
                alerta=alerta,
            )
            resultados.append(result)

        # 2. Webhooks globais configurados
        webhooks = WebhookConfig.query.filter_by(ativo=True).all()
        for webhook in webhooks:
            if webhook.deve_processar_alerta(alerta.tipo, alerta.nivel):
                result = self._enviar_webhook_single(
                    url=webhook.url,
                    alerta=alerta,
                    config=webhook,
                )
                resultados.append(result)

        # Atualizar status do alerta
        if resultados:
            if any(r['success'] for r in resultados):
                alerta.marcar_como_enviado(canal='webhook')
            else:
                erros = [r['error'] for r in resultados if r.get('error')]
                alerta.marcar_como_falhou('; '.join(erros), canal='webhook')

        return resultados

    def _enviar_webhook_single(
        self,
        url: str,
        alerta: AlertaNotificacao,
        config: Optional[WebhookConfig] = None,
    ) -> Dict[str, Any]:
        """
        Envia alerta para um webhook especifico.
        """
        try:
            # Payload padrao
            payload = {
                'alerta_id': alerta.id,
                'tipo': alerta.tipo,
                'nivel': alerta.nivel,
                'titulo': alerta.titulo,
                'mensagem': alerta.mensagem,
                'dados': alerta.dados,
                'timestamp': alerta.criado_em.isoformat() if alerta.criado_em else None,
                'origem': alerta.origem,
                'referencia_id': alerta.referencia_id,
                'referencia_tipo': alerta.referencia_tipo,
            }

            # Headers
            headers = {'Content-Type': 'application/json'}
            if config:
                if config.headers:
                    headers.update(config.headers)

                # Autenticacao
                if config.auth_type == 'bearer' and config.auth_token:
                    headers['Authorization'] = f'Bearer {config.auth_token}'
                elif config.auth_type == 'api_key' and config.auth_token:
                    headers['X-API-Key'] = config.auth_token
                elif config.auth_type == 'basic' and config.auth_token:
                    import base64
                    encoded = base64.b64encode(config.auth_token.encode()).decode()
                    headers['Authorization'] = f'Basic {encoded}'

            # Enviar request
            metodo = config.metodo if config else 'POST'
            if metodo.upper() == 'POST':
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.WEBHOOK_TIMEOUT
                )
            else:
                response = requests.put(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.WEBHOOK_TIMEOUT
                )

            # Processar resposta
            if response.status_code in [200, 201, 202, 204]:
                logger.info(f"Webhook enviado com sucesso para {url}")
                if config:
                    config.registrar_envio(sucesso=True)

                # Salvar resposta no alerta
                try:
                    alerta.webhook_response = {
                        'status_code': response.status_code,
                        'body': response.text[:1000] if response.text else None,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    db.session.commit()
                except Exception:
                    pass

                return {
                    'success': True,
                    'url': url,
                    'status_code': response.status_code,
                    'error': None
                }
            else:
                error_msg = f"Status {response.status_code}: {response.text[:200]}"
                logger.warning(f"Webhook falhou para {url}: {error_msg}")
                if config:
                    config.registrar_envio(sucesso=False, erro=error_msg)

                return {
                    'success': False,
                    'url': url,
                    'status_code': response.status_code,
                    'error': error_msg
                }

        except requests.Timeout:
            error_msg = f"Timeout apos {self.WEBHOOK_TIMEOUT}s"
            logger.warning(f"Webhook timeout para {url}")
            if config:
                config.registrar_envio(sucesso=False, erro=error_msg)
            return {
                'success': False,
                'url': url,
                'error': error_msg
            }

        except requests.RequestException as e:
            error_msg = str(e)
            logger.error(f"Erro de request para webhook {url}: {e}")
            if config:
                config.registrar_envio(sucesso=False, erro=error_msg)
            return {
                'success': False,
                'url': url,
                'error': error_msg
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Erro inesperado ao enviar webhook {url}: {e}", exc_info=True)
            if config:
                config.registrar_envio(sucesso=False, erro=error_msg)
            return {
                'success': False,
                'url': url,
                'error': error_msg
            }

    def reenviar_pendentes(self, limite: int = 100) -> Dict[str, Any]:
        """
        Reenvia alertas pendentes (com retry).
        Chamado por job de background.
        """
        alertas = AlertaNotificacao.buscar_pendentes(limite=limite)
        resultados = {
            'total': len(alertas),
            'sucesso': 0,
            'falha': 0,
            'detalhes': []
        }

        for alerta in alertas:
            if alerta.tentativas_envio >= self.MAX_RETRY_ATTEMPTS:
                # Desiste apos maximo de tentativas
                alerta.status_envio = 'falhou'
                db.session.commit()
                resultados['falha'] += 1
                resultados['detalhes'].append({
                    'alerta_id': alerta.id,
                    'status': 'maximo_tentativas',
                })
                continue

            # Reprocessar canais pendentes
            if alerta.status_email == 'pendente' and 'email' in (alerta.canais or []):
                result = self._enviar_email(alerta)
                if result['success']:
                    resultados['sucesso'] += 1
                else:
                    resultados['falha'] += 1

            if alerta.status_webhook == 'pendente' and 'webhook' in (alerta.canais or []):
                results = self._enviar_webhooks(alerta)
                if any(r['success'] for r in results):
                    resultados['sucesso'] += 1
                else:
                    resultados['falha'] += 1

            resultados['detalhes'].append({
                'alerta_id': alerta.id,
                'status_email': alerta.status_email,
                'status_webhook': alerta.status_webhook,
            })

        return resultados


# Funcao de conveniencia para uso em outros modulos
def enviar_notificacao(
    tipo: str,
    nivel: str,
    titulo: str,
    mensagem: str,
    dados: Optional[Dict[str, Any]] = None,
    canais: Optional[List[str]] = None,
    email_destinatario: Optional[str] = None,
    origem: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Funcao de conveniencia para enviar notificacoes.

    Uso:
        from app.notificacoes.services import enviar_notificacao

        enviar_notificacao(
            tipo='SEPARACAO_COTADA_ALTERADA',
            nivel='CRITICO',
            titulo='Separacao Alterada',
            mensagem='A separacao foi alterada',
            canais=['in_app', 'email'],
            email_destinatario='usuario@empresa.com'
        )
    """
    dispatcher = NotificationDispatcher()
    return dispatcher.enviar_alerta(
        tipo=tipo,
        nivel=nivel,
        titulo=titulo,
        mensagem=mensagem,
        dados=dados,
        canais=canais,
        email_destinatario=email_destinatario,
        origem=origem,
        **kwargs
    )


# Funcoes especializadas por tipo de alerta
def enviar_alerta_critico(
    titulo: str,
    mensagem: str,
    tipo: str = 'ALERTA_CRITICO',
    dados: Optional[Dict[str, Any]] = None,
    email_destinatario: Optional[str] = None,
    origem: Optional[str] = None,
) -> Dict[str, Any]:
    """Envia alerta critico (in_app apenas)"""
    return enviar_notificacao(
        tipo=tipo,
        nivel='CRITICO',
        titulo=titulo,
        mensagem=mensagem,
        dados=dados,
        canais=['in_app'],
        email_destinatario=email_destinatario,
        origem=origem,
    )


def enviar_alerta_atencao(
    titulo: str,
    mensagem: str,
    tipo: str = 'ALERTA_ATENCAO',
    dados: Optional[Dict[str, Any]] = None,
    email_destinatario: Optional[str] = None,
    origem: Optional[str] = None,
) -> Dict[str, Any]:
    """Envia alerta de atencao (in_app apenas por padrao)"""
    return enviar_notificacao(
        tipo=tipo,
        nivel='ATENCAO',
        titulo=titulo,
        mensagem=mensagem,
        dados=dados,
        canais=['in_app'],
        email_destinatario=email_destinatario,
        origem=origem,
    )


def enviar_info(
    titulo: str,
    mensagem: str,
    tipo: str = 'INFO',
    dados: Optional[Dict[str, Any]] = None,
    origem: Optional[str] = None,
) -> Dict[str, Any]:
    """Envia notificacao informativa (in_app apenas)"""
    return enviar_notificacao(
        tipo=tipo,
        nivel='INFO',
        titulo=titulo,
        mensagem=mensagem,
        dados=dados,
        canais=['in_app'],
        origem=origem,
    )

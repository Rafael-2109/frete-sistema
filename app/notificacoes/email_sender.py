#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EMAIL SENDER
Sistema de envio de emails para notificacoes

Suporta:
- SMTP padrao (Gmail, Outlook, etc)
- AWS SES (via boto3 se disponivel)
- SendGrid (via sendgrid-python se disponivel)

Configuracao via variaveis de ambiente:
- EMAIL_BACKEND: smtp, ses, sendgrid (default: smtp)
- EMAIL_HOST: servidor SMTP (ex: smtp.gmail.com)
- EMAIL_PORT: porta SMTP (default: 587)
- EMAIL_USERNAME: usuario para autenticacao
- EMAIL_PASSWORD: senha/app password
- EMAIL_USE_TLS: usar TLS (default: True)
- EMAIL_FROM: email remetente
- EMAIL_FROM_NAME: nome do remetente (default: Sistema de Frete)
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional, List
from app.utils.logging_config import logger


class EmailConfig:
    """Configuracoes de email carregadas do ambiente"""

    BACKEND = os.environ.get('EMAIL_BACKEND', 'smtp')  # smtp, ses, sendgrid
    HOST = os.environ.get('EMAIL_HOST', '')
    PORT = int(os.environ.get('EMAIL_PORT', '587'))
    USERNAME = os.environ.get('EMAIL_USERNAME', '')
    PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
    USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
    USE_SSL = os.environ.get('EMAIL_USE_SSL', 'False').lower() == 'true'
    FROM_EMAIL = os.environ.get('EMAIL_FROM', '')
    FROM_NAME = os.environ.get('EMAIL_FROM_NAME', 'Sistema de Frete Nacom Goya')

    # AWS SES
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

    # SendGrid
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')

    @classmethod
    def is_configured(cls) -> bool:
        """Verifica se o email esta configurado"""
        if cls.BACKEND == 'smtp':
            return bool(cls.HOST and cls.USERNAME and cls.PASSWORD and cls.FROM_EMAIL)
        elif cls.BACKEND == 'ses':
            return bool(cls.FROM_EMAIL)  # SES usa credenciais AWS do ambiente
        elif cls.BACKEND == 'sendgrid':
            return bool(cls.SENDGRID_API_KEY and cls.FROM_EMAIL)
        return False


class EmailSender:
    """Classe principal para envio de emails"""

    def __init__(self):
        self.config = EmailConfig

    def send(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> dict:
        """
        Envia email usando o backend configurado.

        Args:
            to: Email do destinatario
            subject: Assunto do email
            body_html: Corpo do email em HTML
            body_text: Corpo do email em texto plano (opcional)
            reply_to: Email para resposta (opcional)
            cc: Lista de emails em copia (opcional)
            bcc: Lista de emails em copia oculta (opcional)

        Returns:
            dict: {'success': bool, 'message_id': str, 'error': str}
        """
        if not self.config.is_configured():
            return {
                'success': False,
                'message_id': None,
                'error': 'Email nao configurado. Verifique variaveis de ambiente EMAIL_*'
            }

        try:
            backend = self.config.BACKEND.lower()

            if backend == 'smtp':
                return self._send_smtp(to, subject, body_html, body_text, reply_to, cc, bcc)
            elif backend == 'ses':
                return self._send_ses(to, subject, body_html, body_text, reply_to, cc, bcc)
            elif backend == 'sendgrid':
                return self._send_sendgrid(to, subject, body_html, body_text, reply_to, cc, bcc)
            else:
                return {
                    'success': False,
                    'message_id': None,
                    'error': f'Backend de email nao suportado: {backend}'
                }
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}", exc_info=True)
            return {
                'success': False,
                'message_id': None,
                'error': str(e)
            }

    def _send_smtp(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str],
        reply_to: Optional[str],
        cc: Optional[List[str]],
        bcc: Optional[List[str]],
    ) -> dict:
        """Envia email via SMTP padrao"""

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = formataddr((self.config.FROM_NAME, self.config.FROM_EMAIL))
        msg['To'] = to

        if cc:
            msg['Cc'] = ', '.join(cc)
        if reply_to:
            msg['Reply-To'] = reply_to

        # Corpo em texto plano
        if body_text:
            part_text = MIMEText(body_text, 'plain', 'utf-8')
            msg.attach(part_text)

        # Corpo em HTML
        part_html = MIMEText(body_html, 'html', 'utf-8')
        msg.attach(part_html)

        # Lista completa de destinatarios
        all_recipients = [to]
        if cc:
            all_recipients.extend(cc)
        if bcc:
            all_recipients.extend(bcc)

        try:
            if self.config.USE_SSL:
                server = smtplib.SMTP_SSL(self.config.HOST, self.config.PORT)
            else:
                server = smtplib.SMTP(self.config.HOST, self.config.PORT)
                if self.config.USE_TLS:
                    server.starttls()

            server.login(self.config.USERNAME, self.config.PASSWORD)
            server.sendmail(self.config.FROM_EMAIL, all_recipients, msg.as_string())
            server.quit()

            logger.info(f"Email enviado com sucesso para {to}")
            return {
                'success': True,
                'message_id': msg['Message-ID'],
                'error': None
            }

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Erro de autenticacao SMTP: {e}")
            return {
                'success': False,
                'message_id': None,
                'error': 'Erro de autenticacao SMTP. Verifique usuario e senha.'
            }
        except smtplib.SMTPException as e:
            logger.error(f"Erro SMTP: {e}")
            return {
                'success': False,
                'message_id': None,
                'error': f'Erro SMTP: {str(e)}'
            }

    def _send_ses(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str],
        reply_to: Optional[str],
        cc: Optional[List[str]],
        bcc: Optional[List[str]],
    ) -> dict:
        """Envia email via AWS SES"""
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            return {
                'success': False,
                'message_id': None,
                'error': 'boto3 nao instalado. Execute: pip install boto3'
            }

        ses_client = boto3.client('ses', region_name=self.config.AWS_REGION)

        destination = {'ToAddresses': [to]}
        if cc:
            destination['CcAddresses'] = cc
        if bcc:
            destination['BccAddresses'] = bcc

        message = {
            'Subject': {'Data': subject, 'Charset': 'UTF-8'},
            'Body': {
                'Html': {'Data': body_html, 'Charset': 'UTF-8'}
            }
        }
        if body_text:
            message['Body']['Text'] = {'Data': body_text, 'Charset': 'UTF-8'}

        try:
            response = ses_client.send_email(
                Source=f'{self.config.FROM_NAME} <{self.config.FROM_EMAIL}>',
                Destination=destination,
                Message=message,
                ReplyToAddresses=[reply_to] if reply_to else []
            )

            logger.info(f"Email SES enviado com sucesso para {to}")
            return {
                'success': True,
                'message_id': response['MessageId'],
                'error': None
            }

        except ClientError as e:
            error_msg = e.response['Error']['Message']
            logger.error(f"Erro AWS SES: {error_msg}")
            return {
                'success': False,
                'message_id': None,
                'error': f'Erro AWS SES: {error_msg}'
            }

    def _send_sendgrid(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str],
        reply_to: Optional[str],
        cc: Optional[List[str]],
        bcc: Optional[List[str]],
    ) -> dict:
        """Envia email via SendGrid"""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content, ReplyTo
        except ImportError:
            return {
                'success': False,
                'message_id': None,
                'error': 'sendgrid nao instalado. Execute: pip install sendgrid'
            }

        message = Mail(
            from_email=Email(self.config.FROM_EMAIL, self.config.FROM_NAME),
            to_emails=To(to),
            subject=subject,
            html_content=Content('text/html', body_html)
        )

        if body_text:
            message.add_content(Content('text/plain', body_text))
        if reply_to:
            message.reply_to = ReplyTo(reply_to)

        try:
            sg = SendGridAPIClient(self.config.SENDGRID_API_KEY)
            response = sg.send(message)

            logger.info(f"Email SendGrid enviado com sucesso para {to}")
            return {
                'success': True,
                'message_id': response.headers.get('X-Message-Id'),
                'error': None
            }

        except Exception as e:
            logger.error(f"Erro SendGrid: {e}")
            return {
                'success': False,
                'message_id': None,
                'error': f'Erro SendGrid: {str(e)}'
            }


class EmailTemplates:
    """Templates HTML para emails de notificacao"""

    @staticmethod
    def alerta_critico(titulo: str, mensagem: str, dados: dict = None) -> str:
        """Template para alertas criticos"""
        dados_html = ''
        if dados:
            dados_html = '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">'
            for key, value in dados.items():
                dados_html += f'''
                <tr>
                    <td style="padding: 5px; border: 1px solid #ddd; font-weight: bold;">{key}</td>
                    <td style="padding: 5px; border: 1px solid #ddd;">{value}</td>
                </tr>
                '''
            dados_html += '</table>'

        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #dc3545; color: white; padding: 15px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 20px; border: 1px solid #ddd; }}
                .footer {{ background-color: #f8f9fa; padding: 10px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🚨 ALERTA CRITICO</h2>
                </div>
                <div class="content">
                    <h3>{titulo}</h3>
                    <p>{mensagem}</p>
                    {dados_html}
                </div>
                <div class="footer">
                    Sistema de Frete - Nacom Goya<br>
                    Esta mensagem foi gerada automaticamente, nao responda.
                </div>
            </div>
        </body>
        </html>
        '''

    @staticmethod
    def alerta_atencao(titulo: str, mensagem: str, dados: dict = None) -> str:
        """Template para alertas de atencao"""
        dados_html = ''
        if dados:
            dados_html = '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">'
            for key, value in dados.items():
                dados_html += f'''
                <tr>
                    <td style="padding: 5px; border: 1px solid #ddd; font-weight: bold;">{key}</td>
                    <td style="padding: 5px; border: 1px solid #ddd;">{value}</td>
                </tr>
                '''
            dados_html += '</table>'

        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #ffc107; color: #333; padding: 15px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 20px; border: 1px solid #ddd; }}
                .footer {{ background-color: #f8f9fa; padding: 10px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>⚠️ ATENCAO</h2>
                </div>
                <div class="content">
                    <h3>{titulo}</h3>
                    <p>{mensagem}</p>
                    {dados_html}
                </div>
                <div class="footer">
                    Sistema de Frete - Nacom Goya<br>
                    Esta mensagem foi gerada automaticamente, nao responda.
                </div>
            </div>
        </body>
        </html>
        '''

    @staticmethod
    def info(titulo: str, mensagem: str, dados: dict = None) -> str:
        """Template para alertas informativos"""
        dados_html = ''
        if dados:
            dados_html = '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">'
            for key, value in dados.items():
                dados_html += f'''
                <tr>
                    <td style="padding: 5px; border: 1px solid #ddd; font-weight: bold;">{key}</td>
                    <td style="padding: 5px; border: 1px solid #ddd;">{value}</td>
                </tr>
                '''
            dados_html += '</table>'

        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #17a2b8; color: white; padding: 15px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 20px; border: 1px solid #ddd; }}
                .footer {{ background-color: #f8f9fa; padding: 10px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>ℹ️ INFORMACAO</h2>
                </div>
                <div class="content">
                    <h3>{titulo}</h3>
                    <p>{mensagem}</p>
                    {dados_html}
                </div>
                <div class="footer">
                    Sistema de Frete - Nacom Goya<br>
                    Esta mensagem foi gerada automaticamente, nao responda.
                </div>
            </div>
        </body>
        </html>
        '''


# Singleton para uso global
email_sender = EmailSender()

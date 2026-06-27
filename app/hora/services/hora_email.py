"""Config SMTP propria do HORA — conta financeiro@ Hostinger.

ISOLADA das EMAIL_* genericas do sistema (usadas por app/notificacoes e
app/manufatura, que enviam de OUTRA conta). O HORA manda NF e recibo da caixa
financeiro@motochefesp.com.br via Hostinger; por isso le envs proprias
HORA_EMAIL_* e reusa o EmailSender (config injetavel) com esta config.

Defaults Hostinger/financeiro@ ja embutidos — em PROD basta gravar a senha em
HORA_EMAIL_PASSWORD (as demais HORA_EMAIL_* sobrescrevem o default se preciso).
"""
import os

from app.notificacoes.email_sender import EmailSender


class HoraEmailConfig:
    """Espelha a interface de EmailConfig, porem lendo HORA_EMAIL_* (nao EMAIL_*)."""

    BACKEND = 'smtp'
    HOST = os.environ.get('HORA_EMAIL_HOST', 'smtp.hostinger.com')
    PORT = int(os.environ.get('HORA_EMAIL_PORT', '465'))
    USERNAME = os.environ.get('HORA_EMAIL_USERNAME', 'financeiro@motochefesp.com.br')
    PASSWORD = os.environ.get('HORA_EMAIL_PASSWORD', '')
    USE_TLS = os.environ.get('HORA_EMAIL_USE_TLS', 'False').lower() == 'true'
    USE_SSL = os.environ.get('HORA_EMAIL_USE_SSL', 'True').lower() == 'true'
    # Remetente: reusa HORA_NF_EMAIL_FROM / _FROM_NAME (ja existentes) — financeiro@.
    FROM_EMAIL = os.environ.get('HORA_NF_EMAIL_FROM', 'financeiro@motochefesp.com.br')
    FROM_NAME = os.environ.get('HORA_NF_EMAIL_FROM_NAME', 'Motochefe SP — Financeiro')
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    SENDGRID_API_KEY = ''

    @classmethod
    def is_configured(cls) -> bool:
        return bool(cls.HOST and cls.USERNAME and cls.PASSWORD and cls.FROM_EMAIL)


# Instancia dedicada do HORA (NF + recibo): EmailSender com a config propria acima.
hora_email_sender = EmailSender(HoraEmailConfig)

"""HORA usa conta de e-mail PRÓPRIA (HORA_EMAIL_*), isolada das EMAIL_* do sistema.

O e-mail genérico (app/notificacoes/email_sender) é compartilhado por
notificacoes/manufatura; o HORA manda NF/recibo de financeiro@ Hostinger. Esta
suíte garante que o EmailSender aceita config injetada e que a config do HORA
aponta para a conta certa.
"""


def test_emailsender_aceita_config_injetada():
    from app.notificacoes.email_sender import EmailSender

    class FakeCfg:
        BACKEND = 'smtp'; HOST = 'h'; PORT = 1; USERNAME = 'u'; PASSWORD = 'p'
        USE_TLS = False; USE_SSL = True; FROM_EMAIL = 'f@x'; FROM_NAME = 'N'
        AWS_REGION = 'us-east-1'; SENDGRID_API_KEY = ''

        @classmethod
        def is_configured(cls):
            return True

    assert EmailSender(FakeCfg).config is FakeCfg


def test_emailsender_default_continua_emailconfig():
    from app.notificacoes.email_sender import EmailSender, EmailConfig
    assert EmailSender().config is EmailConfig


def test_hora_email_config_defaults_hostinger_financeiro():
    from app.hora.services.hora_email import HoraEmailConfig
    assert HoraEmailConfig.HOST == 'smtp.hostinger.com'
    assert HoraEmailConfig.PORT == 465
    assert HoraEmailConfig.USE_SSL is True
    assert HoraEmailConfig.USE_TLS is False
    assert HoraEmailConfig.USERNAME == 'financeiro@motochefesp.com.br'
    assert HoraEmailConfig.FROM_EMAIL == 'financeiro@motochefesp.com.br'


def test_hora_email_config_is_configured_exige_senha():
    from app.hora.services.hora_email import HoraEmailConfig

    class SemSenha(HoraEmailConfig):
        PASSWORD = ''

    class ComSenha(HoraEmailConfig):
        PASSWORD = 'segredo'

    assert SemSenha.is_configured() is False
    assert ComSenha.is_configured() is True

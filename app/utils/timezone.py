"""
Utilitarios para gerenciamento de timezone brasileiro
====================================================

CONVENCAO DO SISTEMA (atualizada 2026-02-12):
- Armazenamento: Sempre BRASIL naive via agora_utc_naive() (retorna horario de Brasilia)
- Display: Filtros Jinja2 (formatar_data_segura, formatar_data_hora_brasil) formatam direto (sem conversao)
- Model defaults: default=agora_utc_naive, onupdate=agora_utc_naive
- NUNCA usar datetime.utcnow() (deprecated Python 3.12+)
- Boundary Odoo: usar odoo_para_local() para converter UTC do Odoo → Brasil naive
- Boundary Odoo (envio): usar agora_utc() para queries de write_date (Odoo armazena UTC)

NOTA: agora_utc_naive() mantém o nome por compatibilidade (235+ usos).
      Para código novo, usar o alias agora_brasil_naive().
"""

import pytz
from datetime import datetime, timedelta, timezone


# Timezone do Brasil (Brasília)
BRASIL_TZ = pytz.timezone("America/Sao_Paulo")
UTC_TZ = pytz.UTC


def agora_utc_naive():
    """
    Retorna datetime Brasil naive (sem tzinfo).
    NOTA: Nome mantido por compatibilidade (235+ usos). Retorna horario de Brasilia.
    Use agora_brasil_naive() para codigo novo.
    Compativel com TIMESTAMP WITHOUT TIME ZONE do PostgreSQL.
    """
    return datetime.now(BRASIL_TZ).replace(tzinfo=None)


# Alias preferencial para codigo novo
agora_brasil_naive = agora_utc_naive


def agora_brasil():
    """
    Retorna datetime atual no timezone do Brasil.
    Usar APENAS para lógica de negócio que precisa do horário local
    (ex: "hoje em SP", comparação com horário comercial).
    NUNCA usar como default de model SQLAlchemy.
    """
    return datetime.now(BRASIL_TZ)


def utc_para_brasil(dt_utc):
    """
    Converte datetime UTC para timezone brasileiro

    Args:
        dt_utc: datetime em UTC (pode ser naive ou timezone-aware)

    Returns:
        datetime no timezone brasileiro
    """
    if dt_utc is None:
        return None

    # Se for naive datetime, assume que é UTC
    if dt_utc.tzinfo is None:
        dt_utc = UTC_TZ.localize(dt_utc)

    # Converte para timezone brasileiro
    return dt_utc.astimezone(BRASIL_TZ)


def brasil_para_utc(dt_brasil):
    """
    Converte datetime brasileiro para UTC

    Args:
        dt_brasil: datetime no timezone brasileiro (pode ser naive ou timezone-aware)

    Returns:
        datetime em UTC
    """
    if dt_brasil is None:
        return None

    # Se for naive datetime, assume que é timezone brasileiro
    if dt_brasil.tzinfo is None:
        dt_brasil = BRASIL_TZ.localize(dt_brasil)

    # Converte para UTC
    return dt_brasil.astimezone(UTC_TZ)


def formatar_data_hora_brasil(dt, formato="%d/%m/%Y %H:%M"):
    """
    Formata datetime para exibicao no padrao brasileiro.
    Datetime ja esta em horario Brasil (armazenado naive).

    Args:
        dt: datetime (ja em horario Brasil)
        formato: formato de saida

    Returns:
        string formatada
    """
    if dt is None:
        return ""

    try:
        if hasattr(dt, 'strftime'):
            return dt.strftime(formato)
        return ""
    except Exception:
        return ""


def formatar_data_brasil(dt, formato="%d/%m/%Y"):
    """
    Formata data para exibicao no padrao brasileiro.
    Datetime ja esta em horario Brasil (armazenado naive).

    Args:
        dt: date ou datetime (ja em horario Brasil)
        formato: formato de saida

    Returns:
        string formatada
    """
    if dt is None:
        return ""

    try:
        if hasattr(dt, 'strftime'):
            return dt.strftime(formato)
        return ""
    except Exception:
        return ""


def agora_utc():
    """
    Retorna datetime atual em UTC (aware).
    Usar APENAS para boundary Odoo (queries write_date, create_date).
    NAO usar para armazenamento local — usar agora_utc_naive() em vez disso.
    """
    return datetime.now(UTC_TZ)


def odoo_para_local(dt_str):
    """
    Converte datetime string UTC do Odoo para Brasil naive.
    Usar na fronteira de recebimento de dados do Odoo.

    Args:
        dt_str: string no formato '%Y-%m-%d %H:%M:%S' ou datetime UTC

    Returns:
        datetime naive em horario Brasil, ou None
    """
    if not dt_str:
        return None
    try:
        if isinstance(dt_str, str):
            dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        elif isinstance(dt_str, datetime):
            dt = dt_str if dt_str.tzinfo is None else dt_str.replace(tzinfo=None)
        else:
            return None
        # Odoo retorna UTC → converter para Brasil
        dt_utc = UTC_TZ.localize(dt)
        dt_brasil = dt_utc.astimezone(BRASIL_TZ)
        return dt_brasil.replace(tzinfo=None)
    except Exception:
        return None


def diferenca_horario_brasil():
    """
    Retorna a diferenca de horario entre UTC e Brasil.
    Nota: com armazenamento Brasil, essa diferenca sera ~0.
    Mantida para compatibilidade.
    """
    utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
    brasil_now = agora_utc_naive()  # Agora retorna Brasil

    return brasil_now - utc_now


def criar_datetime_brasil(ano, mes, dia, hora=0, minuto=0, segundo=0):
    """
    Cria datetime no timezone brasileiro
    """
    dt_naive = datetime(ano, mes, dia, hora, minuto, segundo)
    return BRASIL_TZ.localize(dt_naive)


def eh_horario_verao_brasil(dt=None):
    """
    Verifica se uma data está em horário de verão no Brasil
    """
    if dt is None:
        dt = agora_brasil()

    if dt.tzinfo is None:
        dt = BRASIL_TZ.localize(dt)

    return dt.dst() != timedelta(0)

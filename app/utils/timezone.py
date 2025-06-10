"""
Utilitários para gerenciamento de timezone brasileiro
====================================================
"""

import pytz
from datetime import datetime, timezone, timedelta


# Timezone do Brasil (Brasília)
BRASIL_TZ = pytz.timezone('America/Sao_Paulo')
UTC_TZ = pytz.UTC


def agora_brasil():
    """
    Retorna datetime atual no timezone do Brasil
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


def formatar_data_hora_brasil(dt, formato='%d/%m/%Y %H:%M'):
    """
    Formata datetime para exibição no padrão brasileiro
    
    Args:
        dt: datetime (UTC ou timezone-aware)
        formato: formato de saída
    
    Returns:
        string formatada
    """
    if dt is None:
        return ''
    
    try:
        # Converte para timezone brasileiro
        dt_brasil = utc_para_brasil(dt)
        return dt_brasil.strftime(formato)
    except Exception:
        return ''


def formatar_data_brasil(dt, formato='%d/%m/%Y'):
    """
    Formata data para exibição no padrão brasileiro
    
    Args:
        dt: date ou datetime
        formato: formato de saída
    
    Returns:
        string formatada
    """
    if dt is None:
        return ''
    
    try:
        # Se for datetime, converte para timezone brasileiro primeiro
        if hasattr(dt, 'hour'):  # É datetime
            dt_brasil = utc_para_brasil(dt)
            return dt_brasil.strftime(formato)
        else:  # É date
            return dt.strftime(formato)
    except Exception:
        return ''


def agora_utc():
    """
    Retorna datetime atual em UTC (para salvar no banco)
    """
    return datetime.utcnow()


def diferenca_horario_brasil():
    """
    Retorna a diferença de horário entre UTC e Brasil
    """
    agora_utc = datetime.utcnow()
    agora_brasil_dt = agora_brasil()
    
    # Converte para naive datetime para comparação
    agora_utc_naive = agora_utc.replace(tzinfo=None)
    agora_brasil_naive = agora_brasil_dt.replace(tzinfo=None)
    
    return agora_brasil_naive - agora_utc_naive


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
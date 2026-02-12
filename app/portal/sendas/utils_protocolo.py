"""
Utilidades para geração e gestão de protocolos do portal Sendas
Centraliza a lógica de geração de protocolo para garantir consistência
"""

from datetime import datetime
import logging
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

def gerar_protocolo_sendas(cnpj: str, data_agendamento, timestamp: datetime = None) -> str:
    """
    Gera o protocolo padrão do Sendas com a máscara:
    AG_(cnpj posições 7 até 4)_ddmmyyyy_ddmmyyyy

    Formato: AG_CNPJ_DataAgendamento_DataGeracao

    ✅ NOTA: Mudança de máscara para evitar problemas com diferença de minutos
    Antes: AG_CNPJ_DATA_HHMM (causava protocolos diferentes por minutos)
    Agora: AG_CNPJ_DATA_DATA (mesmo protocolo se gerado no mesmo dia)

    Args:
        cnpj: CNPJ do cliente (será limpo automaticamente)
        data_agendamento: Data do agendamento (date ou datetime)
        timestamp: Timestamp para usar na geração (opcional, DEPRECATED - mantido para compatibilidade)

    Returns:
        String com o protocolo formatado

    Exemplo:
        cnpj = "06.057.223/0001-95"
        data = date(2025, 1, 15)
        protocolo = gerar_protocolo_sendas(cnpj, data)
        # Retorna: "AG_0001_15012025_13012025"
        #          AG_CNPJ_DataAgend_DataHoje
    """
    try:
        # ✅ PEGAR DIRETO DO CNPJ SEM LIMPAR
        # Exemplo: "12.345.678/9012-34" -> posições [-7:-3] = "9012"
        cnpj_parte = str(cnpj)[-7:-3]

        # Se não conseguiu pegar 4 dígitos, logar erro
        if len(cnpj_parte) != 4:
            logger.error(f"CNPJ parte inválida: '{cnpj_parte}' do CNPJ '{cnpj}'")
            raise ValueError(f"Não foi possível extrair 4 dígitos do CNPJ")

        # Garantir que data_agendamento seja um objeto date
        if hasattr(data_agendamento, 'date'):
            # É um datetime, converter para date
            data_agendamento = data_agendamento.date()
        elif isinstance(data_agendamento, str):
            # É uma string, fazer parse
            from dateutil import parser
            data_agendamento = parser.parse(data_agendamento).date()
        # Se já é date, não precisa fazer nada

        # Formatar data como ddmmyyyy
        data_formatada = data_agendamento.strftime('%d%m%Y')

        # Obter timestamp (usar atual se não fornecido)
        if timestamp is None:
            timestamp = agora_utc_naive()

        # Formatar data de hoje como ddmmyyyy
        data_hoje = agora_utc_naive().strftime('%d%m%Y')

        # Montar protocolo: AG_CNPJ_DataAgendamento_DataGeracao
        protocolo = f"AG_{cnpj_parte}_{data_formatada}_{data_hoje}"

        logger.debug(f"Protocolo gerado: {protocolo} para CNPJ {cnpj}")

        return protocolo

    except Exception as e:
        logger.error(f"ERRO CRÍTICO ao gerar protocolo para CNPJ '{cnpj}', data {data_agendamento}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Fallback para formato simplificado em caso de erro
        return f"AG_ERR_{agora_utc_naive().strftime('%Y%m%d%H%M%S')}"


def extrair_dados_protocolo(protocolo: str) -> dict:
    """
    Extrai os dados de um protocolo Sendas

    ✅ COMPATÍVEL COM AMBOS OS FORMATOS:
    - Novo formato: AG_xxxx_ddmmyyyy_ddmmyyyy (data agendamento + data geração)
    - Formato antigo: AG_xxxx_ddmmyyyy_HHMM (data agendamento + hora)

    Args:
        protocolo: String do protocolo no formato AG_xxxx_ddmmyyyy_ddmmyyyy ou AG_xxxx_ddmmyyyy_HHMM

    Returns:
        Dicionário com os dados extraídos ou None se formato inválido
    """
    try:
        if not protocolo or not protocolo.startswith('AG_'):
            return None # type: ignore

        partes = protocolo.split('_')
        if len(partes) != 4:
            return None # type: ignore

        cnpj_parte = partes[1]
        data_agend_str = partes[2]
        quarto_campo = partes[3]

        # Converter data de agendamento de ddmmyyyy para datetime
        data_agendamento = datetime.strptime(data_agend_str, '%d%m%Y').date()

        # ✅ DETECTAR FORMATO: tentar como data (8 dígitos) ou hora (4 dígitos)
        if len(quarto_campo) == 8:
            # Novo formato: data de geração (ddmmyyyy)
            try:
                data_geracao = datetime.strptime(quarto_campo, '%d%m%Y').date()
                return {
                    'cnpj_parte': cnpj_parte,
                    'data_agendamento': data_agendamento,
                    'data_geracao': data_geracao,
                    'hora_geracao': None,  # Não tem hora no novo formato
                    'formato': 'novo',
                    'protocolo_completo': protocolo
                }
            except ValueError:
                # Se falhar, tratar como formato desconhecido
                logger.warning(f"Protocolo com formato desconhecido (4º campo com 8 dígitos mas não é data): {protocolo}")
                return None # type: ignore

        elif len(quarto_campo) == 4:
            # Formato antigo: hora de geração (HHMM)
            try:
                hora = datetime.strptime(quarto_campo, '%H%M').time()
                return {
                    'cnpj_parte': cnpj_parte,
                    'data_agendamento': data_agendamento,
                    'data_geracao': None,  # Não tem data de geração no formato antigo
                    'hora_geracao': hora,
                    'formato': 'antigo',
                    'protocolo_completo': protocolo
                }
            except ValueError:
                # Se falhar, tratar como formato desconhecido
                logger.warning(f"Protocolo com formato desconhecido (4º campo com 4 dígitos mas não é hora): {protocolo}")
                return None # type: ignore
        else:
            # Formato desconhecido
            logger.warning(f"Protocolo com formato desconhecido (4º campo com {len(quarto_campo)} dígitos): {protocolo}")
            return None # type: ignore

    except Exception as e:
        logger.error(f"Erro ao extrair dados do protocolo {protocolo}: {e}")
        return None # type: ignore

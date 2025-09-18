"""
Utilidades para geração e gestão de protocolos do portal Sendas
Centraliza a lógica de geração de protocolo para garantir consistência
"""

from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def gerar_protocolo_sendas(cnpj: str, data_agendamento, timestamp: datetime = None) -> str:
    """
    Gera o protocolo padrão do Sendas com a máscara:
    AG_(cnpj posições 7 até 4)_ddmmyyyy_HHMM

    Args:
        cnpj: CNPJ do cliente (será limpo automaticamente)
        data_agendamento: Data do agendamento (date ou datetime)
        timestamp: Timestamp para usar na geração (opcional, usa datetime.now() se não fornecido)

    Returns:
        String com o protocolo formatado

    Exemplo:
        cnpj = "06.057.223/0001-95"
        data = date(2025, 1, 15)
        protocolo = gerar_protocolo_sendas(cnpj, data)
        # Retorna: "AG_0001_15012025_1430"
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
            timestamp = datetime.now()

        # Formatar hora como HHMM
        hora_formatada = timestamp.strftime('%H%M')

        # Montar protocolo
        protocolo = f"AG_{cnpj_parte}_{data_formatada}_{hora_formatada}"

        logger.debug(f"Protocolo gerado: {protocolo} para CNPJ {cnpj}")

        return protocolo

    except Exception as e:
        logger.error(f"ERRO CRÍTICO ao gerar protocolo para CNPJ '{cnpj}', data {data_agendamento}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Fallback para formato simplificado em caso de erro
        return f"AG_ERR_{datetime.now().strftime('%Y%m%d%H%M%S')}"


def extrair_dados_protocolo(protocolo: str) -> dict:
    """
    Extrai os dados de um protocolo Sendas

    Args:
        protocolo: String do protocolo no formato AG_xxxx_ddmmyyyy_HHMM

    Returns:
        Dicionário com os dados extraídos ou None se formato inválido
    """
    try:
        if not protocolo or not protocolo.startswith('AG_'):
            return None

        partes = protocolo.split('_')
        if len(partes) != 4:
            return None

        cnpj_parte = partes[1]
        data_str = partes[2]
        hora_str = partes[3]

        # Converter data de ddmmyyyy para datetime
        data = datetime.strptime(data_str, '%d%m%Y').date()

        # Converter hora de HHMM para time
        hora = datetime.strptime(hora_str, '%H%M').time()

        return {
            'cnpj_parte': cnpj_parte,
            'data_agendamento': data,
            'hora_geracao': hora,
            'protocolo_completo': protocolo
        }

    except Exception as e:
        logger.error(f"Erro ao extrair dados do protocolo {protocolo}: {e}")
        return None
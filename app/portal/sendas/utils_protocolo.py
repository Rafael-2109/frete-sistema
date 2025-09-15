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
        # Limpar CNPJ (remover caracteres não numéricos)
        cnpj_limpo = ''.join(filter(str.isdigit, str(cnpj)))

        # Validar tamanho do CNPJ
        if len(cnpj_limpo) < 8:
            logger.warning(f"CNPJ muito curto: {cnpj_limpo}")
            cnpj_parte = cnpj_limpo[-4:].zfill(4)
        else:
            # Pegar posições 7 até 4 (índices 6 até 10 em Python, contando do início)
            # Exemplo: 06057223000195 -> posições 7-4 = "0001"
            cnpj_parte = cnpj_limpo[6:10]

        # Garantir que data_agendamento seja um objeto date
        if hasattr(data_agendamento, 'date'):
            data_agendamento = data_agendamento.date()

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
        logger.error(f"Erro ao gerar protocolo: {e}")
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
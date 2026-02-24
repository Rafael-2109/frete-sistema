"""
Utilitarios de Sanitizacao de Dados de Faturamento
===================================================

Funcoes puras (sem dependencia de instancia) para sanitizar dados
de faturamento antes da insercao no banco.

Reutilizado por:
- FaturamentoService._sanitizar_dados_faturamento()
- ImportacaoFallbackService (batch e single NF paths)

Campos varchar(20) no schema faturamento_produto:
  numero_nf, cnpj_cliente, incoterm, origem, status_nf
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def extrair_incoterm_codigo(texto: str) -> str:
    """
    Extrai codigo do incoterm de texto bruto do Odoo.

    Exemplos:
        '[CIF] COST, INSURANCE AND FREIGHT' -> 'CIF'
        '[FOB] FREE ON BOARD'               -> 'FOB'
        '[RED] REDESPACHO'                  -> 'RED'
        'CIF'                               -> 'CIF'
        ''                                  -> ''
        None                                -> ''

    Returns:
        Codigo do incoterm (max 20 chars) ou string vazia.
    """
    if not texto:
        return ''

    texto = str(texto).strip()

    # Padrao Odoo: [CODIGO] DESCRICAO LONGA
    if '[' in texto and ']' in texto:
        inicio = texto.find('[')
        fim = texto.find(']')
        if inicio >= 0 and fim > inicio:
            return texto[inicio + 1:fim].strip()

    # Sem colchetes: truncar para caber no varchar(20)
    return texto[:20]


def sanitizar_dados_faturamento(dados_faturamento: List[Dict]) -> List[Dict]:
    """
    Sanitiza e corrige dados de faturamento antes da insercao.
    Garante que campos nao excedam os limites do banco.

    Tratamentos aplicados (nesta ordem):
    1. Incoterm: extrai codigo entre colchetes (ANTES do truncamento generico)
    2. Campos varchar(20): trunca para 20 caracteres
    3. Municipio com formato 'Cidade (UF)': separa cidade e estado
    4. Estado: garante string de 2 caracteres

    Args:
        dados_faturamento: Lista de dicts com dados de faturamento.

    Returns:
        Lista de dicts sanitizados (copias, originais nao alterados).
    """
    dados_sanitizados = []

    for item in dados_faturamento:
        item_sanitizado = item.copy()

        # 1. Incoterm: extrair codigo ANTES do truncamento generico
        #    (ex: '[CIF] COST, INSURANCE AND FREIGHT' = 33 chars → 'CIF')
        #    Deve acontecer primeiro pois o truncamento generico corromperia o texto
        if 'incoterm' in item_sanitizado and item_sanitizado['incoterm']:
            item_sanitizado['incoterm'] = extrair_incoterm_codigo(
                str(item_sanitizado['incoterm'])
            )

        # 2. Campos com limite de 20 caracteres (truncamento generico)
        campos_varchar20 = ['numero_nf', 'cnpj_cliente', 'incoterm', 'origem', 'status_nf']
        for campo in campos_varchar20:
            if campo in item_sanitizado and item_sanitizado[campo]:
                valor = str(item_sanitizado[campo])
                if len(valor) > 20:
                    item_sanitizado[campo] = valor[:20]

        # 3. Tratar municipio com formato "Cidade (UF)"
        if 'municipio' in item_sanitizado and item_sanitizado['municipio']:
            municipio = str(item_sanitizado['municipio'])
            if '(' in municipio and ')' in municipio:
                # Extrair cidade e estado
                partes = municipio.split('(')
                item_sanitizado['municipio'] = partes[0].strip()
                if len(partes) > 1:
                    estado = partes[1].replace(')', '').strip()
                    # Garantir que estado tem apenas 2 caracteres
                    if len(estado) > 2:
                        estado = estado[:2]
                    item_sanitizado['estado'] = estado

        # 4. Garantir que estado e string de 2 caracteres
        if 'estado' in item_sanitizado:
            estado_valor = item_sanitizado['estado']
            if isinstance(estado_valor, (int, float)):
                # Se for numero, limpar
                item_sanitizado['estado'] = ''
            elif estado_valor and len(str(estado_valor)) > 2:
                item_sanitizado['estado'] = str(estado_valor)[:2]

        dados_sanitizados.append(item_sanitizado)

    return dados_sanitizados

"""
Entity Mapper - Mapeia entidades extraídas pelo Claude para campos do sistema.

FILOSOFIA v4.0:
- O Claude decide TUDO: domínio, intenção, entidades
- Este módulo APENAS traduz nomes de campos (sinônimos → nomes técnicos)
- NÃO inferimos, NÃO sobrescrevemos, NÃO "corrigimos" o Claude

É um TRADUTOR PURO de campos, não um decisor.

Criado em: 24/11/2025
Atualizado: 26/11/2025 - Removida toda inferência de domínio/intenção
Atualizado: 26/11/2025 - Adicionada normalização UPPERCASE para campos texto
"""

import logging
from typing import Dict, Any
from datetime import datetime, date

logger = logging.getLogger(__name__)


# =============================================================================
# MAPEAMENTO DE SINÔNIMOS → CAMPOS TÉCNICOS
# =============================================================================
# O Claude pode usar termos de negócio. Traduzimos para nomes do banco.
# Se o Claude já usar o nome técnico, não faz nada (passa direto).

MAPEAMENTO_CAMPOS = {
    # === CLIENTE ===
    'cliente': 'raz_social_red',
    'razao_social': 'raz_social_red',
    'empresa': 'raz_social_red',
    'cnpj': 'cnpj_cpf',
    'cpf': 'cnpj_cpf',

    # === PEDIDO ===
    'pedido': 'num_pedido',
    'numero_pedido': 'num_pedido',
    'codigo_pedido': 'num_pedido',
    'pedido_cliente': 'pedido_cliente',
    'pedido_compra': 'pedido_cliente',

    # === PRODUTO ===
    'codigo_produto': 'cod_produto',
    'produto': 'nome_produto',
    'item': 'nome_produto',
    'des_produto': 'nome_produto',
    'descricao_produto': 'nome_produto',

    # === DATAS ===
    'data_expedicao': 'expedicao',
    'data_de_expedicao': 'expedicao',
    'data_separacao': 'expedicao',
    'data_nova': 'expedicao',
    'nova_data': 'expedicao',
    'data_desejada': 'expedicao',
    'data_solicitada': 'expedicao',
    'data_envio': 'expedicao',

    'data_agendamento': 'agendamento',
    'data_de_agendamento': 'agendamento',
    'data_entrega': 'data_entrega_pedido',

    # === LOCALIZAÇÃO ===
    'uf': 'cod_uf',
    'estado': 'cod_uf',
    'cidade': 'nome_cidade',
    'municipio': 'nome_cidade',
    'regiao': 'sub_rota',

    # === QUANTIDADES ===
    'quantidade': 'qtd_saldo',
    'qtd': 'qtd_saldo',
    'valor': 'valor_saldo',

    # === TRANSPORTE ===
    'transportadora': 'roteirizacao',

    # === OPÇÃO ===
    'escolha': 'opcao',
    'opcao_escolhida': 'opcao',
}

# =============================================================================
# CAMPOS QUE DEVEM SER NORMALIZADOS PARA UPPERCASE
# =============================================================================
# Esses campos são armazenados em MAIÚSCULO no banco de dados.
# Normalizamos para garantir que a busca funcione (ilike é case-insensitive,
# mas consistência ajuda na verificação de correspondência).

CAMPOS_NORMALIZAR_UPPERCASE = {
    'raz_social_red',   # Nome do cliente
    'cliente',          # Sinônimo de raz_social_red
    'nome_cidade',      # Cidade
    'cod_uf',           # UF (SP, RJ, MG...)
    'rota',             # Rota
    'sub_rota',         # Sub-rota
}


def mapear_extracao(extracao: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mapeia extração do Claude para formato do sistema.

    FILOSOFIA v4.0:
    - domínio e intenção vêm DIRETO do Claude (não inferimos)
    - Apenas traduzimos nomes de campos nas entidades
    - Normalizamos formato de datas

    Args:
        extracao: Dict retornado pelo IntelligentExtractor
                  Esperado: {dominio, intencao, tipo, entidades, ambiguidade, confianca}

    Returns:
        Dict com dominio, intencao, entidades traduzidas
    """
    # === DOMÍNIO E INTENÇÃO: Direto do Claude ===
    dominio = extracao.get('dominio', 'geral')
    intencao = extracao.get('intencao', 'outro')
    tipo = extracao.get('tipo', 'outro')
    entidades_raw = extracao.get('entidades', {})
    ambiguidade = extracao.get('ambiguidade', {})

    # Se há ambiguidade, retorna para clarificação
    if tipo == 'clarificacao' or (ambiguidade and ambiguidade.get('existe')):
        return {
            'dominio': 'clarificacao',
            'intencao': 'esclarecer',
            'entidades': _mapear_entidades(entidades_raw),
            'ambiguidade': ambiguidade,
            'confianca': extracao.get('confianca', 0.5),
            '_extracao_original': extracao
        }

    # Traduz entidades (sinônimos → campos técnicos)
    entidades = _mapear_entidades(entidades_raw)

    # Normaliza formato de datas
    entidades = _normalizar_datas(entidades)

    resultado = {
        'dominio': dominio,
        'intencao': intencao,
        'tipo': tipo,
        'entidades': entidades,
        'confianca': extracao.get('confianca', 0.8),
        '_extracao_original': extracao
    }

    logger.info(f"[ENTITY_MAPPER] Passthrough: dominio={dominio}, intencao={intencao}, "
               f"entidades={list(entidades.keys())}")

    return resultado


def _mapear_entidades(entidades_raw: Dict) -> Dict:
    """
    Traduz nomes de campos para nomes técnicos do banco.

    Se o Claude usou 'cliente', traduz para 'raz_social_red'.
    Se o Claude já usou 'raz_social_red', mantém.

    Também normaliza campos texto para UPPERCASE quando necessário.
    """
    entidades = {}

    for campo_original, valor in entidades_raw.items():
        if valor is None or str(valor).lower() in ('null', 'none', ''):
            continue

        # Normaliza nome do campo
        campo_normalizado = campo_original.lower().replace(' ', '_')

        # Traduz se tiver mapeamento, senão mantém original
        campo_destino = MAPEAMENTO_CAMPOS.get(campo_normalizado, campo_original)

        # Normaliza valor para UPPERCASE se for campo de texto que exige
        valor_final = _normalizar_uppercase(campo_destino, valor)

        # Evita sobrescrever valor existente
        if campo_destino not in entidades:
            entidades[campo_destino] = valor_final

    return entidades


def _normalizar_uppercase(campo: str, valor: Any) -> Any:
    """
    Normaliza valor para UPPERCASE se o campo exigir.

    Os dados no banco estão em MAIÚSCULO para campos como raz_social_red.
    Isso garante consistência na busca e verificação de correspondência.
    """
    if campo in CAMPOS_NORMALIZAR_UPPERCASE and isinstance(valor, str):
        return valor.upper()
    return valor


def _normalizar_datas(entidades: Dict) -> Dict:
    """
    Normaliza campos de data para formato ISO (YYYY-MM-DD).

    O Claude deveria retornar em ISO, mas se vier DD/MM/YYYY, convertemos.
    """
    campos_data = [
        'expedicao', 'agendamento', 'data_expedicao', 'data_agendamento',
        'data_entrega_pedido', 'data', 'data_pedido', 'data_inicio', 'data_fim'
    ]

    for campo in campos_data:
        valor = entidades.get(campo)
        if not valor:
            continue

        # Se já está em formato ISO (YYYY-MM-DD), mantém
        if isinstance(valor, str) and len(valor) == 10 and valor[4] == '-':
            continue

        # Tenta converter de DD/MM/YYYY para YYYY-MM-DD
        if isinstance(valor, str) and '/' in valor:
            try:
                partes = valor.split('/')
                if len(partes) >= 2:
                    dia = int(partes[0])
                    mes = int(partes[1])
                    ano = int(partes[2]) if len(partes) > 2 else datetime.now().year
                    if ano < 100:
                        ano = 2000 + ano
                    data_obj = date(ano, mes, dia)
                    entidades[campo] = data_obj.isoformat()
            except (ValueError, IndexError):
                pass

    return entidades

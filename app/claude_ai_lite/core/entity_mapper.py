"""
Entity Mapper - Mapeia entidades extraídas pelo Claude para campos do sistema.

FILOSOFIA:
O Claude extrai livremente. Este módulo traduz para os campos do sistema
SEM restringir o que o Claude pode extrair.

É um TRADUTOR, não um FILTRO.

Criado em: 24/11/2025
"""

import logging
from typing import Dict, Any
from datetime import datetime, date

logger = logging.getLogger(__name__)


# Mapeamento de sinônimos para campos do sistema
# O Claude pode usar qualquer termo, nós traduzimos
# IMPORTANTE: Adicionar TODOS os sinônimos que o Claude pode usar
MAPEAMENTO_CAMPOS = {
    # Cliente
    'cliente': 'raz_social_red',
    'razao_social': 'raz_social_red',
    'empresa': 'raz_social_red',
    'cnpj': 'cnpj_cpf',
    'cpf': 'cnpj_cpf',
    'documento': 'cnpj_cpf',

    # Pedido
    'pedido': 'num_pedido',
    'numero_pedido': 'num_pedido',
    'numero': 'num_pedido',
    'codigo_pedido': 'num_pedido',
    'pedido_cliente': 'pedido_cliente',
    'pedido_compra': 'pedido_cliente',

    # Produto
    'codigo_produto': 'cod_produto',
    'produto': 'nome_produto',
    'item': 'nome_produto',

    # Datas - TODOS os sinônimos que o Claude pode usar
    'data_expedicao': 'expedicao',
    'expedicao': 'expedicao',
    'data_de_expedicao': 'expedicao',
    'data_separacao': 'expedicao',           # Claude usa para separação
    'data_nova': 'expedicao',                 # Claude usa para modificação
    'nova_data': 'expedicao',
    'data_desejada': 'expedicao',
    'data_solicitada': 'expedicao',
    'data_envio': 'expedicao',
    'data_mencionada_original': 'expedicao',  # Extração original
    'data_original_mencionada': 'expedicao',
    'data': 'expedicao',                      # Genérico
    'periodo': 'expedicao',                   # "semana que vem" vira período

    'data_agendamento': 'agendamento',
    'agendamento': 'agendamento',
    'data_de_agendamento': 'agendamento',
    'data_entrega': 'data_entrega_pedido',

    # Localização
    'uf': 'cod_uf',
    'estado': 'cod_uf',
    'cidade': 'nome_cidade',
    'municipio': 'nome_cidade',
    'rota': 'rota',
    'sub_rota': 'sub_rota',

    # Quantidades
    'quantidade': 'qtd_saldo',
    'qtd': 'qtd_saldo',
    'valor': 'valor_saldo',

    # Transportadora
    'transportadora': 'roteirizacao',

    # Opção (para separação)
    'opcao': 'opcao',
    'escolha': 'opcao',
    'opcao_escolhida': 'opcao',
}


# Mapeamento de intenções para domínios
MAPEAMENTO_INTENCOES = {
    # Ações de separação
    'criar_separacao': ('acao', 'criar_separacao'),
    'criar separação': ('acao', 'criar_separacao'),
    'criar separacao': ('acao', 'criar_separacao'),
    'gerar_separacao': ('acao', 'criar_separacao'),
    'separar': ('acao', 'criar_separacao'),
    'separar_disponiveis': ('acao', 'separar_disponiveis'),
    'separar disponíveis': ('acao', 'separar_disponiveis'),
    'separar disponiveis': ('acao', 'separar_disponiveis'),

    # Modificações
    'alterar_data': ('acao', 'alterar_expedicao'),
    'alterar data': ('acao', 'alterar_expedicao'),
    'mudar_data': ('acao', 'alterar_expedicao'),
    'mudar data': ('acao', 'alterar_expedicao'),
    'alterar_expedicao': ('acao', 'alterar_expedicao'),
    'alterar expedição': ('acao', 'alterar_expedicao'),
    'alterar_quantidade': ('acao', 'alterar_quantidade'),

    # Inclusão/Exclusão
    'incluir_item': ('acao', 'incluir_item'),
    'incluir item': ('acao', 'incluir_item'),
    'adicionar_item': ('acao', 'incluir_item'),
    'adicionar item': ('acao', 'incluir_item'),
    'excluir_item': ('acao', 'excluir_item'),
    'excluir item': ('acao', 'excluir_item'),
    'remover_item': ('acao', 'excluir_item'),
    'remover item': ('acao', 'excluir_item'),

    # Confirmação
    'confirmar': ('acao', 'confirmar_acao'),
    'confirmar_acao': ('acao', 'confirmar_acao'),
    'aceitar': ('acao', 'confirmar_acao'),

    # Cancelamento
    'cancelar': ('acao', 'cancelar'),
    'cancelar_rascunho': ('acao', 'cancelar'),
    'desistir': ('acao', 'cancelar'),

    # Escolha de opção
    'escolher_opcao': ('acao', 'escolher_opcao'),
    'escolher opção': ('acao', 'escolher_opcao'),
    'selecionar_opcao': ('acao', 'escolher_opcao'),

    # Visualização
    'ver_rascunho': ('acao', 'ver_rascunho'),
    'ver rascunho': ('acao', 'ver_rascunho'),
    'mostrar_rascunho': ('acao', 'ver_rascunho'),

    # Consultas
    'consultar_status': ('carteira', 'consultar_status'),
    'consultar status': ('carteira', 'consultar_status'),
    'verificar_pedido': ('carteira', 'consultar_status'),
    'analisar_disponibilidade': ('carteira', 'analisar_disponibilidade'),
    'quando_posso_enviar': ('carteira', 'analisar_disponibilidade'),
    'consultar_estoque': ('estoque', 'consultar_estoque'),
    'analisar_gargalo': ('carteira', 'analisar_gargalo'),
}


def mapear_extracao(extracao: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mapeia extração livre do Claude para formato esperado pelo sistema.

    Args:
        extracao: Dict retornado pelo IntelligentExtractor

    Returns:
        Dict com dominio, intencao e entidades no formato do sistema
    """
    tipo = extracao.get('tipo', 'outro')
    intencao_raw = extracao.get('intencao', '').lower()
    entidades_raw = extracao.get('entidades', {})
    ambiguidade = extracao.get('ambiguidade', {})

    # NOVO: Se há ambiguidade, retorna para clarificação
    if tipo == 'clarificacao' or (ambiguidade and ambiguidade.get('existe')):
        return {
            'dominio': 'clarificacao',
            'intencao': 'esclarecer',
            'entidades': _mapear_entidades(entidades_raw),
            'ambiguidade': ambiguidade,
            'confianca': extracao.get('confianca', 0.5),
            '_extracao_original': extracao
        }

    # 1. Determina domínio e intenção
    dominio, intencao = _determinar_dominio_intencao(tipo, intencao_raw, entidades_raw)

    # 2. Mapeia entidades
    entidades = _mapear_entidades(entidades_raw)

    # 3. Normaliza datas
    entidades = _normalizar_datas(entidades)

    # 4. Preserva metadados úteis
    resultado = {
        'dominio': dominio,
        'intencao': intencao,
        'entidades': entidades,
        'confianca': extracao.get('confianca', 0.8),
        '_extracao_original': extracao  # Preserva para debug
    }

    logger.info(f"[ENTITY_MAPPER] Mapeado: dominio={dominio}, intencao={intencao}, "
               f"entidades={list(entidades.keys())}")

    return resultado


def _determinar_dominio_intencao(tipo: str, intencao_raw: str, entidades: Dict) -> tuple:
    """Determina domínio e intenção baseado no tipo e intenção extraídos."""

    # REGRA 1: Se tem 'opcao' nas entidades, é escolher_opcao
    if entidades.get('opcao'):
        return ('acao', 'escolher_opcao')

    # Verifica se tem mapeamento direto
    intencao_normalizada = intencao_raw.replace(' ', '_').lower()
    if intencao_normalizada in MAPEAMENTO_INTENCOES:
        return MAPEAMENTO_INTENCOES[intencao_normalizada]

    # Verifica palavras-chave na intenção
    for chave, (dom, intent) in MAPEAMENTO_INTENCOES.items():
        if chave.replace('_', ' ') in intencao_raw or chave in intencao_raw:
            return (dom, intent)

    # Baseado no tipo
    if tipo == 'acao':
        # Tenta inferir ação específica
        if any(p in intencao_raw for p in ['separ', 'criar']):
            return ('acao', 'criar_separacao')
        if any(p in intencao_raw for p in ['confirm', 'aceit', 'sim']):
            return ('acao', 'confirmar_acao')
        if any(p in intencao_raw for p in ['cancel', 'desist']):
            return ('acao', 'cancelar')
        if 'opcao' in intencao_raw or 'opção' in intencao_raw or 'escolh' in intencao_raw:
            return ('acao', 'escolher_opcao')
        if any(p in intencao_raw for p in ['alter', 'mudar', 'modific']):
            if 'data' in intencao_raw or 'expedi' in intencao_raw:
                return ('acao', 'alterar_expedicao')
            if 'quant' in intencao_raw:
                return ('acao', 'alterar_quantidade')
        return ('acao', 'criar_separacao')  # Default para ação

    if tipo == 'confirmacao':
        # Se tem opção, é escolher_opcao (não confirmação)
        if entidades.get('opcao'):
            return ('acao', 'escolher_opcao')
        return ('acao', 'confirmar_acao')

    if tipo == 'cancelamento':
        return ('acao', 'cancelar')

    if tipo == 'modificacao':
        # Verifica o que está sendo modificado
        # Verifica vários nomes que o Claude pode usar para data
        tem_data = any(entidades.get(k) for k in [
            'data_expedicao', 'expedicao', 'data_nova', 'nova_data',
            'data_separacao', 'data', 'data_desejada'
        ])
        if tem_data:
            return ('acao', 'alterar_expedicao')
        if entidades.get('quantidade'):
            return ('acao', 'alterar_quantidade')
        # Se é modificação com opção, é escolher opção
        if entidades.get('opcao'):
            return ('acao', 'escolher_opcao')
        return ('acao', 'alterar_expedicao')

    if tipo == 'consulta':
        if entidades.get('num_pedido') or entidades.get('pedido'):
            return ('carteira', 'consultar_status')
        if entidades.get('cliente') or entidades.get('raz_social_red'):
            return ('carteira', 'buscar_pedido')
        return ('carteira', 'consultar_status')

    # Default
    return ('geral', 'outro')


def _mapear_entidades(entidades_raw: Dict) -> Dict:
    """Mapeia entidades para campos do sistema."""
    entidades = {}

    for campo_original, valor in entidades_raw.items():
        if valor is None or str(valor).lower() in ('null', 'none', ''):
            continue

        # Normaliza nome do campo
        campo_normalizado = campo_original.lower().replace(' ', '_')

        # Verifica se tem mapeamento
        campo_destino = MAPEAMENTO_CAMPOS.get(campo_normalizado, campo_original)

        # Evita sobrescrever valor existente
        if campo_destino not in entidades:
            entidades[campo_destino] = valor

        # Se campo original é diferente do destino, preserva ambos
        # (para casos onde o sistema usa nomes diferentes)
        if campo_original != campo_destino and campo_original not in entidades:
            entidades[campo_original] = valor

    return entidades


def _normalizar_datas(entidades: Dict) -> Dict:
    """Normaliza campos de data para formato esperado."""
    campos_data = ['expedicao', 'agendamento', 'data_expedicao', 'data_agendamento',
                   'data_entrega_pedido', 'data', 'data_pedido']

    for campo in campos_data:
        valor = entidades.get(campo)
        if not valor:
            continue

        # Se já está em formato ISO (YYYY-MM-DD), mantém
        if isinstance(valor, str) and len(valor) == 10 and valor[4] == '-':
            continue

        # Tenta converter de DD/MM/YYYY para YYYY-MM-DD
        if isinstance(valor, str):
            try:
                if '/' in valor:
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

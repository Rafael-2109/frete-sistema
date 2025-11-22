"""
Core do Claude AI Lite.
Orquestra o fluxo: identificar intencao -> buscar dados -> gerar resposta.

REGRA: Maximo 100 linhas. Se crescer, algo esta errado.
"""

import logging
from typing import Dict, Any

from .claude_client import get_claude_client
from .domains import get_loader, listar_dominios

logger = logging.getLogger(__name__)


def processar_consulta(consulta: str, usar_claude_resposta: bool = True) -> str:
    """
    Processa consulta em linguagem natural.

    Fluxo:
    1. Claude identifica dominio e entidades
    2. Roteia para loader correto
    3. Loader busca dados
    4. Claude elabora resposta (opcional)
    """
    if not consulta or not consulta.strip():
        return "Por favor, informe sua consulta."

    client = get_claude_client()

    # 1. Identificar intencao
    intencao = client.identificar_intencao(consulta)
    dominio_base = intencao.get("dominio", "geral")
    intencao_tipo = intencao.get("intencao", "")
    entidades = intencao.get("entidades", {})

    logger.info(f"Intencao: dominio={dominio_base}, tipo={intencao_tipo}, entidades={entidades}")

    # 2. Rotear para loader especifico
    dominio = _rotear_dominio(dominio_base, intencao_tipo, entidades)
    loader_class = get_loader(dominio)

    if not loader_class:
        # Fallback para dominio base
        loader_class = get_loader(dominio_base)
        if not loader_class:
            return f"Dominio '{dominio}' nao suportado. Disponiveis: {listar_dominios()}"

    loader = loader_class()

    # 3. Extrair campo e valor de busca
    campo, valor = _extrair_criterio(entidades, loader.CAMPOS_BUSCA)
    if not campo or not valor:
        return (
            f"Nao consegui identificar o criterio de busca.\n"
            f"Campos aceitos: {loader.CAMPOS_BUSCA}"
        )

    # 4. Buscar dados
    dados = loader.buscar(valor, campo)

    if not dados.get("sucesso"):
        return f"Erro: {dados.get('erro', 'Erro desconhecido')}"

    if dados["total_encontrado"] == 0:
        return dados.get("mensagem", f"Nenhum resultado para {campo}={valor}")

    # 5. Gerar resposta
    contexto = loader.formatar_contexto(dados)

    if usar_claude_resposta:
        return client.responder_com_contexto(consulta, contexto, dominio_base)
    else:
        return contexto


def _rotear_dominio(dominio_base: str, intencao: str, entidades: Dict) -> str:
    """Roteia para subdominio correto baseado na intencao."""
    if dominio_base != "carteira":
        return dominio_base

    # Roteia dentro do dominio carteira
    if intencao == "buscar_produto" or entidades.get("produto"):
        return "carteira_produto"
    elif intencao == "analisar_disponibilidade" or "quando" in str(entidades).lower():
        return "carteira_disponibilidade"

    return "carteira"  # Default: PedidosLoader


def _extrair_criterio(entidades: Dict, campos_aceitos: list) -> tuple:
    """Extrai campo e valor das entidades identificadas."""
    mapeamento = {
        "num_pedido": "num_pedido",
        "cnpj": "cnpj_cpf",
        "cliente": "raz_social_red",
        "pedido_cliente": "pedido_cliente",
        "produto": "nome_produto",
        "cod_produto": "cod_produto",
    }

    for entidade, campo in mapeamento.items():
        if campo not in campos_aceitos:
            continue
        valor = entidades.get(entidade)
        if valor and str(valor).lower() not in ("null", "none", ""):
            return campo, str(valor)

    return None, None

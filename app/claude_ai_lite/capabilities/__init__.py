"""
Registry automático de Capacidades.

Descobre e registra automaticamente todas as capacidades
dos subdiretórios (carteira/, estoque/, fretes/, etc).

Uso:
    from .capabilities import find_capability, get_all_capabilities

Limite: 120 linhas
"""

import os
import importlib
import pkgutil
import logging
from typing import Dict, List, Optional, Type

from .base import BaseCapability

logger = logging.getLogger(__name__)

# Registry global de capacidades
_CAPABILITIES: Dict[str, BaseCapability] = {}
_LOADED = False


def _auto_discover():
    """
    Descobre e registra todas as capacidades automaticamente.

    Percorre subdiretórios (carteira/, estoque/, etc) e importa
    todos os módulos .py que contenham classes BaseCapability.
    """
    global _LOADED
    if _LOADED:
        return

    pasta_atual = os.path.dirname(__file__)

    for item in os.listdir(pasta_atual):
        caminho = os.path.join(pasta_atual, item)

        # Ignora arquivos e pastas especiais
        if not os.path.isdir(caminho) or item.startswith('_'):
            continue

        # Importa cada módulo .py do subdiretório
        for module_info in pkgutil.iter_modules([caminho]):
            try:
                module = importlib.import_module(
                    f".{item}.{module_info.name}",
                    package="app.claude_ai_lite.capabilities"
                )

                # Busca classes que herdam de BaseCapability
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)

                    if (isinstance(attr, type) and
                        issubclass(attr, BaseCapability) and
                        attr is not BaseCapability and
                        attr.NOME):  # Só registra se tiver NOME definido

                        cap = attr()
                        _CAPABILITIES[cap.NOME] = cap
                        logger.debug(f"[CAPABILITIES] Registrada: {cap.NOME} ({cap.DOMINIO})")

            except Exception as e:
                logger.warning(f"[CAPABILITIES] Erro ao carregar {item}.{module_info.name}: {e}")

    _LOADED = True
    logger.info(f"[CAPABILITIES] {len(_CAPABILITIES)} capacidades carregadas")


def get_capability(nome: str) -> Optional[BaseCapability]:
    """Retorna capacidade pelo nome."""
    _auto_discover()
    return _CAPABILITIES.get(nome)


def get_all_capabilities() -> List[BaseCapability]:
    """Retorna todas as capacidades registradas."""
    _auto_discover()
    return list(_CAPABILITIES.values())


def get_capabilities_by_domain(dominio: str) -> List[BaseCapability]:
    """Retorna capacidades de um domínio específico."""
    _auto_discover()
    return [c for c in _CAPABILITIES.values() if c.DOMINIO == dominio]


def find_capability(intencao: str, entidades: Dict) -> Optional[BaseCapability]:
    """
    Encontra a capacidade certa para processar uma requisição.

    v4.0: O Claude já retorna a intenção correta, então:
    1. Primeiro tenta match direto pelo NOME da capability
    2. Depois verifica pode_processar() de cada uma
    3. Fallback para consulta_generica se tiver dados suficientes

    Args:
        intencao: Intenção retornada pelo Claude (deve mapear para capability)
        entidades: Entidades extraídas

    Returns:
        Capacidade encontrada ou None
    """
    _auto_discover()

    # 1. Match direto pelo NOME da capability (mais eficiente)
    # Ex: intencao="criar_separacao" → capability NOME="criar_separacao"
    if intencao in _CAPABILITIES:
        logger.info(f"[CAPABILITIES] Match direto: {intencao}")
        return _CAPABILITIES[intencao]

    # 2. Busca por pode_processar() (verifica INTENCOES de cada uma)
    for cap in _CAPABILITIES.values():
        if cap.NOME == 'consulta_generica':
            continue  # Pula a genérica na segunda passada
        if cap.pode_processar(intencao, entidades):
            logger.info(f"[CAPABILITIES] Match por pode_processar: {cap.NOME} para {intencao}")
            return cap

    # 3. Fallback para consulta_generica se tiver dados
    generica = _CAPABILITIES.get('consulta_generica')
    if generica:
        tem_tabela = entidades.get('tabela')
        tem_data = entidades.get('data_inicio') or entidades.get('data_fim') or entidades.get('data')
        tem_campo = entidades.get('campo_filtro')
        tem_valor = entidades.get('valor_filtro')

        if tem_tabela or tem_data or (tem_campo and tem_valor):
            logger.info(f"[CAPABILITIES] Usando consulta_generica como fallback para: {intencao}")
            return generica

    logger.warning(f"[CAPABILITIES] Nenhuma capability encontrada para: {intencao}")
    return None


def listar_dominios() -> List[str]:
    """Lista domínios únicos disponíveis."""
    _auto_discover()
    return list(set(c.DOMINIO for c in _CAPABILITIES.values()))


def listar_intencoes() -> List[str]:
    """Lista todas as intenções suportadas."""
    _auto_discover()
    intencoes = set()
    for cap in _CAPABILITIES.values():
        intencoes.update(cap.INTENCOES)
    return sorted(list(intencoes))


def gerar_exemplos_para_prompt() -> str:
    """
    Gera exemplos de todas as capacidades para o prompt de classificação.
    Usado pelo classifier para gerar o prompt dinamicamente.

    IMPORTANTE: Mostra TODOS os exemplos de cada capability (não truncar!)
    Cada exemplo é mapeado para a intenção mais adequada da capability.
    """
    _auto_discover()
    linhas = []

    for cap in _CAPABILITIES.values():
        # TODOS os exemplos (não truncar!) - corrigido em 27/11/2025
        for i, exemplo in enumerate(cap.EXEMPLOS):
            # Usa a primeira intenção como padrão, mas se há múltiplas
            # e o índice existe, usa a intenção correspondente
            if cap.INTENCOES:
                # Tenta mapear exemplo para intenção pelo índice (se possível)
                idx = min(i, len(cap.INTENCOES) - 1)
                intencao = cap.INTENCOES[idx]
            else:
                intencao = "outro"
            linhas.append(f'- "{exemplo}" -> {cap.DOMINIO}, {intencao}')

    return "\n".join(linhas)


# Garante carregamento no import
_auto_discover()

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

    Percorre todas as capacidades e retorna a primeira que
    pode processar a intenção/entidades.

    Args:
        intencao: Intenção identificada pelo classificador
        entidades: Entidades extraídas

    Returns:
        Capacidade encontrada ou None
    """
    _auto_discover()

    for cap in _CAPABILITIES.values():
        if cap.pode_processar(intencao, entidades):
            return cap

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
    """
    _auto_discover()
    linhas = []

    for cap in _CAPABILITIES.values():
        for exemplo in cap.EXEMPLOS[:2]:  # Máximo 2 exemplos por capacidade
            intencao = cap.INTENCOES[0] if cap.INTENCOES else "outro"
            linhas.append(f'- "{exemplo}" -> {cap.DOMINIO}, {intencao}')

    return "\n".join(linhas)


# Garante carregamento no import
_auto_discover()

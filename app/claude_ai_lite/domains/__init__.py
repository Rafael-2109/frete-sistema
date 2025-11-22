"""
Registro automatico de dominios.
Cada dominio se auto-registra ao ser importado.
"""

from typing import Dict, Type, Optional
import logging

logger = logging.getLogger(__name__)

# Registro global de dominios
_DOMINIOS: Dict[str, Type] = {}


def registrar(nome: str, loader_class: Type):
    """Registra um dominio. Chamado pelo __init__.py de cada dominio."""
    _DOMINIOS[nome] = loader_class
    logger.debug(f"Dominio registrado: {nome}")


def get_loader(nome: str) -> Optional[Type]:
    """Retorna a classe loader do dominio."""
    return _DOMINIOS.get(nome)


def listar_dominios() -> list:
    """Lista dominios disponiveis."""
    return list(_DOMINIOS.keys())


# Auto-importa todos os dominios da pasta
def _carregar_dominios():
    """Importa automaticamente todos os subdiretorios com __init__.py"""
    import os
    import importlib

    pasta_atual = os.path.dirname(__file__)

    for item in os.listdir(pasta_atual):
        caminho = os.path.join(pasta_atual, item)
        if os.path.isdir(caminho) and not item.startswith('_'):
            init_file = os.path.join(caminho, '__init__.py')
            if os.path.exists(init_file):
                try:
                    importlib.import_module(f'.{item}', package=__name__)
                except Exception as e:
                    logger.warning(f"Erro ao carregar dominio {item}: {e}")


_carregar_dominios()

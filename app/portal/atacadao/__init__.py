"""
Módulo de integração com portal Atacadão (Hodie Booking)
"""

from .config import ATACADAO_CONFIG
from .playwright_client import AtacadaoPlaywrightClient
from .models import ProdutoDeParaAtacadao
from .playwright_client_simple import AtacadaoPlaywrightSimple

__all__ = ['ATACADAO_CONFIG', 'AtacadaoPlaywrightClient', 'ProdutoDeParaAtacadao', 'AtacadaoPlaywrightSimple']
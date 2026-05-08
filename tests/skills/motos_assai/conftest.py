"""Conftest compartilhado para testes de skills motos_assai.

Reutiliza fixtures do conftest principal (tests/motos_assai/conftest.py).
"""
import sys
from pathlib import Path

# Adiciona path do projeto para imports `from app import ...`
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Reutiliza fixtures de tests/motos_assai/conftest.py
pytest_plugins = ['tests.motos_assai.conftest']

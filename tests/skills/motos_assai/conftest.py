"""Conftest compartilhado para testes de skills motos_assai.

Reutiliza fixtures do conftest principal (tests/motos_assai/conftest.py).

NOTA: `pytest_plugins` foi movido para `tests/conftest.py` (raiz) em 2026-05-11
porque pytest 8.4+ nao aceita mais a declaracao em conftest nao top-level.
Aqui mantemos apenas o path-setup.
"""
import sys
from pathlib import Path

# Adiciona path do projeto para imports `from app import ...`
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

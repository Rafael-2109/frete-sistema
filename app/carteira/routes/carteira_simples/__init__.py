"""
Pacote de rotas da Carteira Simplificada
Carteira compacta com edicao inline e calculos dinamicos

Split do monolito carteira_simples_api.py (2.1K LOC) em:
  - helpers.py      — funcoes auxiliares (validacao, conversao, sync embarque, saidas)
  - dados_api.py    — rotas de consulta (dados, autocomplete, rastrear, totais)
  - separacao_api.py — rotas de CRUD de separacoes (criar, atualizar, lote, verificar, adicionar)
"""

from flask import Blueprint

# Blueprint
# url_prefix='/simples' porque este blueprint e registrado DENTRO de carteira_bp (/carteira)
# URL final: /carteira + /simples = /carteira/simples
carteira_simples_bp = Blueprint('carteira_simples', __name__, url_prefix='/simples')

# Importar rotas depois de criar o blueprint (registra decorators)
from . import dados_api  # noqa: E402, F401
from . import separacao_api  # noqa: E402, F401

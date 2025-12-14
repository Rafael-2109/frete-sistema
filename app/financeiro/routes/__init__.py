"""
Módulo de rotas do Financeiro - Modularizado

Blueprint: financeiro_bp
Prefix: /financeiro

Estrutura:
- pendencias.py          - Pendências antigas (importação, consulta, etc)
- contas_receber.py      - Hub, listagem, exportação, sincronização
- contas_receber_api.py  - APIs de CRUD (detalhes, obs, alerta, confirmação, ação)
- contas_pagar.py        - Hub, listagem, sincronização de contas a pagar (NEW)
- abatimentos.py         - APIs de abatimentos + listagem geral
- tipos.py               - CRUD de tipos
- liberacao.py           - CRUD de liberação antecipação
- pendencias_modal.py    - APIs do modal de pendência financeira
- baixas.py              - Baixa de títulos via Excel (NEW)
- extrato.py             - Conciliação via extrato bancário (NEW)
- pagamentos_baixas.py   - Baixa de pagamentos via extrato (NEW)
"""

import os
from flask import Blueprint

# Criar Blueprint principal
financeiro_bp = Blueprint('financeiro', __name__, url_prefix='/financeiro')

# Configuração de upload
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, '..', '..', '..', 'uploads', 'financeiro')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Importar módulos de rotas (registra as rotas no blueprint)
from app.financeiro.routes import pendencias
from app.financeiro.routes import contas_receber
from app.financeiro.routes import contas_receber_api
from app.financeiro.routes import abatimentos
from app.financeiro.routes import tipos
from app.financeiro.routes import liberacao
from app.financeiro.routes import pendencias_modal
from app.financeiro.routes import baixas
from app.financeiro.routes import extrato
from app.financeiro.routes import correcao_datas
from app.financeiro.routes import pagamentos_baixas
from app.financeiro.routes import contas_pagar

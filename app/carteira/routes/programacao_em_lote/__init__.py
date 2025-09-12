"""
Módulo de Programação em Lote para Redes SP
Gerencia agendamento em massa para Atacadão e Sendas em São Paulo
"""

from flask import Blueprint

# Criar o blueprint
programacao_em_lote_bp = Blueprint(
    'programacao_em_lote',
    __name__,
    url_prefix='/programacao-lote'
)

# Importar rotas depois de criar o blueprint - FORÇA IMPORTAÇÃO
from .routes import (
    listar,
    analisar_estoques, 
    sugerir_datas,
    analisar_ruptura_lote,
    processar_lote
)

# Importar rota de importação de agendamentos Assai
from .importar_agendamentos import importar_agendamentos_assai
"""SHIM de compatibilidade — movido para app/odoo/estoque/scripts/quant.py.

Mantido para os consumidores ativos da operação viva (scripts de inventário,
transferencia_saldo_codigo_service, testes) que importam deste caminho. NÃO
adicionar lógica aqui — editar app/odoo/estoque/scripts/quant.py. Quando todos
os imports apontarem para o novo caminho (checklist C9 do ROADMAP), remover este shim.

Ver app/odoo/estoque/CLAUDE.md.
"""
from app.odoo.estoque.scripts.quant import *  # noqa: F401,F403
from app.odoo.estoque.scripts.quant import (  # noqa: F401
    StockQuantAdjustmentService, # type: ignore
    TOL_ARREDONDAMENTO, # type: ignore
)

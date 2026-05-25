"""SHIM de compatibilidade — movido para app/odoo/estoque/scripts/transfer.py.

Mantido para os consumidores ativos da operação viva (scripts de inventário,
mover_migracao_para_indisponivel, padronizar_migracao, 10/13/15/15r/consolidar,
testes) que importam deste caminho. NÃO adicionar lógica aqui — editar
app/odoo/estoque/scripts/transfer.py. Quando todos os imports apontarem para o
novo caminho (checklist C9 do ROADMAP), remover este shim.

Ver app/odoo/estoque/CLAUDE.md.
"""
from app.odoo.estoque.scripts.transfer import *  # noqa: F401,F403
from app.odoo.estoque.scripts.transfer import (  # noqa: F401
    LOTES_MIGRACAO_VARIANTES,
    LOTE_MIGRACAO_CANONICO,
    StockInternalTransferService,
    TOL_ARREDONDAMENTO,
    is_migracao,  # CR1#5 (2026-05-24): re-export explicito do helper publico
)

"""SHIM de compatibilidade — movido para app/odoo/estoque/scripts/picking.py.

Mantido para os consumidores ativos da operacao viva
(`inventario_pipeline_service`, scripts 09/16/teste_210030325/fat_lf_05,
testes) que importam deste caminho. NAO adicionar logica aqui — editar
`app/odoo/estoque/scripts/picking.py`. Quando todos os imports apontarem
para o novo caminho (checklist C9 do ROADMAP), remover este shim.

Ver `app/odoo/estoque/CLAUDE.md`.
"""
from app.odoo.estoque.scripts.picking import *  # noqa: F401,F403
from app.odoo.estoque.scripts.picking import (  # noqa: F401
    StockPickingService,
)

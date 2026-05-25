"""SHIM de compatibilidade — service vive em app/odoo/estoque/scripts/mo.py.

NACOM/Nacom Goya Skill 4 `operando-mo-odoo` (criada 2026-05-24 v5).
Nao havia service legado em services/ antes — este shim e PREVENTIVO para
quem importar `from app.odoo.services.stock_mo_service import ...`.

NAO adicionar logica aqui — editar `app/odoo/estoque/scripts/mo.py`.
Ver `app/odoo/estoque/CLAUDE.md`.
"""
from app.odoo.estoque.scripts.mo import *  # noqa: F401,F403
from app.odoo.estoque.scripts.mo import StockMOService  # noqa: F401

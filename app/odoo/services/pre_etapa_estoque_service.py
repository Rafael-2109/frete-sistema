"""SHIM de compatibilidade — movido para app/odoo/estoque/scripts/pre_etapa.py.

Mantido para 03b_planejar_pre_etapa_cd.py + 04b_propor_pre_etapa_cd.py +
test_pre_etapa_estoque_service.py que importam deste caminho. NAO adicionar
logica aqui — editar `app/odoo/estoque/scripts/pre_etapa.py`. Quando todos
os imports apontarem para o novo caminho (checklist C9 do ROADMAP), remover
este shim.

NACOM/Nacom Goya Skill 6 `planejando-pre-etapa-odoo` (capinada 2026-05-24).

Ver `app/odoo/estoque/CLAUDE.md`.
"""
from app.odoo.estoque.scripts.pre_etapa import *  # noqa: F401,F403
from app.odoo.estoque.scripts.pre_etapa import (  # noqa: F401
    AjustePositivoPuroPlanejado,
    PlanoPreEtapa,
    PreEtapaEstoqueService,
    ResidualFbCdPlanejado,
    TransferenciaInternaPlanejada,
)

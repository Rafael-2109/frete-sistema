"""
Jobs de Integração Odoo
========================

Jobs agendados para sincronização com Odoo ERP.

Autor: Sistema de Fretes
Data: 2025-08-10
"""

from app.odoo.jobs.manufatura_jobs import (
    job_importar_requisicoes_compras,
    job_importar_pedidos_compras,
    job_sincronizar_producao,
    job_gerar_ordens_mto,
    job_importar_historico_mensal,
    registrar_jobs_manufatura
)

__all__ = [
    'job_importar_requisicoes_compras',
    'job_importar_pedidos_compras',
    'job_sincronizar_producao',
    'job_gerar_ordens_mto',
    'job_importar_historico_mensal',
    'registrar_jobs_manufatura'
]
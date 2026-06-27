"""Services da seção Gerencial HORA (dashboards + relatórios).

Fonte exclusiva `hora_*`. KPIs agregados em SQL único (anti-N+1). Estado da moto
por MAX(id) em hora_moto_evento. Receita só FATURADO. Escopo por loja aplicado no
WHERE via filtros.lojas_efetivas.
"""
from app.hora.services.gerencial.filtros import Filtros, parse_filtros, lojas_efetivas

__all__ = ['Filtros', 'parse_filtros', 'lojas_efetivas']

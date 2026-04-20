"""Utilidades de autorizacao/roteamento por dominio.

Regra: sistema e 100% Nacom exceto os 5 dominios isolados (Lojas HORA, Motochefe,
CarVia, Comercial, Pessoal). Quem nao tem `sistema_logistica` (Nacom) deve cair
direto no dashboard do modulo ao qual pertence.
"""
from __future__ import annotations

from flask import url_for


def url_primeiro_dashboard_disponivel(user):
    """Retorna URL do primeiro dashboard de dominio que o usuario pode acessar.

    Ordem de prioridade: lojas -> motochefe -> carvia -> comercial -> pessoal.
    Retorna None se o usuario nao tem acesso a nenhum dominio.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return None

    # 1. Lojas HORA
    if getattr(user, 'sistema_lojas', False):
        return url_for('hora.dashboard')

    # 2. Motochefe
    if getattr(user, 'sistema_motochefe', False):
        return url_for('motochefe.dashboard_motochefe')

    # 3. CarVia
    if getattr(user, 'sistema_carvia', False):
        return url_for('carvia.dashboard')

    # 4. Comercial: tem vinculo UserVendedor/UserEquipe OU perfil comercial
    try:
        vendedores = user.get_vendedores_autorizados() or []
        equipes = user.get_equipes_autorizadas() or []
    except Exception:
        vendedores, equipes = [], []

    if vendedores or equipes or getattr(user, 'perfil', None) in ('gerente_comercial', 'vendedor'):
        return url_for('comercial.dashboard_diretoria')

    # 5. Pessoal: whitelist em app/pessoal/__init__.py
    try:
        from app.pessoal import pode_acessar_pessoal
        if pode_acessar_pessoal(user):
            return url_for('pessoal.pessoal_dashboard.index')
    except Exception:
        pass

    return None

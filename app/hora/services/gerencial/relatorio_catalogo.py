"""Camada semântica (whitelist) da área de relatórios da seção Gerencial.

O builder de relatórios opera SOMENTE sobre estas dimensões e métricas curadas —
nunca SQL livre do usuário. Cada slug mapeia para um fragmento SQL seguro
montado em relatorio_service.
"""
from __future__ import annotations

# Dimensões disponíveis para agrupar (grão = item-moto da venda FATURADA).
DIMENSOES = {
    'loja': {'label': 'Loja'},
    'vendedor': {'label': 'Vendedor'},
    'modelo': {'label': 'Modelo'},
    'periodo': {'label': 'Período'},
}

# Métricas disponíveis. `tipo` controla formatação no template/export.
METRICAS = {
    'unidades': {'label': 'Unidades', 'tipo': 'inteiro'},
    'receita': {'label': 'Receita (motos)', 'tipo': 'moeda'},
    'desconto_rs': {'label': 'Desconto R$', 'tipo': 'moeda'},
    'margem_rs': {'label': 'Margem R$', 'tipo': 'moeda'},
}


def validar_selecao(dimensoes, metricas) -> tuple[bool, str | None]:
    """Valida a seleção do usuário contra a whitelist. NÃO aceita slug livre."""
    if not dimensoes:
        return False, 'Selecione ao menos uma dimensão.'
    if not metricas:
        return False, 'Selecione ao menos uma métrica.'
    for d in dimensoes:
        if d not in DIMENSOES:
            return False, f'Dimensão inválida: {d}'
    for m in metricas:
        if m not in METRICAS:
            return False, f'Métrica inválida: {m}'
    return True, None

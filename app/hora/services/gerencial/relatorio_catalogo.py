"""Camada semântica (whitelist) da área de relatórios da seção Gerencial.

O builder de relatórios opera SOMENTE sobre estas dimensões e métricas curadas —
nunca SQL livre do usuário. Cada slug mapeia para um fragmento SQL seguro
montado em relatorio_service.
"""
from __future__ import annotations

# Dimensões disponíveis para agrupar (grão = item-moto da venda FATURADA).
# De-scope v2 (grão/joins diferentes): forma_pagamento (1:N via hora_venda_pagamento)
# e canal/origem_lead (cobertura parcial).
DIMENSOES = {
    'loja': {'label': 'Loja'},
    'vendedor': {'label': 'Vendedor'},
    'modelo': {'label': 'Modelo'},
    'cor': {'label': 'Cor'},
    'periodo': {'label': 'Período'},
}

# Métricas disponíveis. `tipo` controla formatação no template/export.
# De-scope v2 (grão venda, não item): ticket médio e margem %.
METRICAS = {
    'unidades': {'label': 'Unidades', 'tipo': 'inteiro'},
    'receita': {'label': 'Receita (motos)', 'tipo': 'moeda'},
    'desconto_rs': {'label': 'Desconto R$', 'tipo': 'moeda'},
    'desconto_pct': {'label': 'Desconto % (médio)', 'tipo': 'percentual'},
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

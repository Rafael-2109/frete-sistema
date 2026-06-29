"""Regressao da tabela de precos (B8 — spec handoff-sessao 2026-06-28).

Haiku 4.5 estava a $0.25/$1.25 (subestimava 4x). Pricing autoritativo da skill
`claude-api`: Haiku 4.5 = $1/$5. Opus 4.x = $5/$25, Sonnet 4.x = $3/$15.
"""
from app.agente.sdk.pricing import MODEL_PRICING, calculate_cost_with_cache


def test_haiku_4_5_corrigido_1_por_5():
    # B8: era (0.25, 1.25) — subestimava Haiku 4x.
    assert MODEL_PRICING['claude-haiku-4-5-20251001'] == (1.00, 5.00)


def test_opus_e_sonnet_inalterados():
    assert MODEL_PRICING['claude-opus-4-8'] == (5.00, 25.00)
    assert MODEL_PRICING['claude-sonnet-4-6'] == (3.00, 15.00)


def test_calculo_haiku_usa_preco_corrigido():
    # 1M input @ $1 + 1M output @ $5 = $6.00 exatos.
    custo = calculate_cost_with_cache(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        model='claude-haiku-4-5-20251001',
    )
    assert custo == 6.0

"""
Tabela de preços Anthropic + helper `calculate_cost_with_cache()`.

Separado de `config/settings.py:MODEL_PRICING` (que cobre apenas input/output
simples) porque o calculo correto de custo de subagente precisa distinguir
3 categorias de input tokens:

- **input_tokens** não cacheados → preço base
- **cache_creation_input_tokens** → preço base × 1.25 (escrita no cache)
- **cache_read_input_tokens** → preço base × 0.10 (leitura do cache)

Ref: https://www.anthropic.com/news/prompt-caching e pricing 2026.

Nota: `config/settings.py:MODEL_PRICING` e mantido para compat (usado em
cost_tracker.record_cost). Esta tabela e a fonte unica para subagent cost
granular calculado a partir do JSONL.
"""
from __future__ import annotations

import logging

logger = logging.getLogger('sistema_fretes')

# Preços por 1M tokens em USD [input_base, output_base].
# Cache: derivado como base × 1.25 (creation) e base × 0.10 (read).
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # Default atual (Opus 4.7, Abr/2026)
    'claude-opus-4-7': (5.00, 25.00),
    # Legacy mantidos para sessões antigas
    'claude-opus-4-6': (5.00, 25.00),
    'claude-opus-4-5-20251101': (5.00, 25.00),
    'claude-opus-4-1-20250805': (15.00, 75.00),   # Opus 4.1 legacy
    'claude-sonnet-4-6': (3.00, 15.00),
    'claude-sonnet-4-5-20250929': (3.00, 15.00),
    'claude-haiku-4-5-20251001': (0.25, 1.25),
    'claude-haiku-3-5-20241022': (0.80, 4.00),
}

# Multiplicadores cache (fração do preço de input base)
_CACHE_CREATION_MULTIPLIER = 1.25   # cache write: 125% do input base
_CACHE_READ_MULTIPLIER = 0.10       # cache read: 10% do input base

# Modelo default quando não identificado
DEFAULT_MODEL = 'claude-opus-4-7'

# Sentinela para warnings de modelo desconhecido (log 1x por modelo).
_warned_models: set[str] = set()


def calculate_cost_with_cache(
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
    model: str | None = None,
) -> float:
    """
    Calcula custo USD de uma mensagem considerando cache tokens.

    Args:
        input_tokens: Tokens de input NÃO cacheados
        output_tokens: Tokens de output gerados
        cache_creation_tokens: Tokens escritos no cache (1.25x input price)
        cache_read_tokens: Tokens lidos do cache (0.10x input price)
        model: Modelo usado. Se None ou desconhecido, usa fallback Opus 4.7.

    Returns:
        Custo total em USD, arredondado a 6 casas decimais.

    Example:
        >>> calculate_cost_with_cache(
        ...     input_tokens=1000, output_tokens=500,
        ...     cache_creation_tokens=200, cache_read_tokens=800,
        ...     model='claude-opus-4-7'
        ... )
        0.02105  # (1000*$5 + 500*$25 + 200*$5*1.25 + 800*$5*0.10) / 1M
    """
    model_id = model or DEFAULT_MODEL
    prices = MODEL_PRICING.get(model_id)
    if prices is None:
        # Modelo desconhecido: fallback Opus 4.7, log warning 1x
        if model_id not in _warned_models:
            logger.warning(
                f"[pricing] Modelo desconhecido '{model_id}' — "
                f"usando fallback '{DEFAULT_MODEL}' ${MODEL_PRICING[DEFAULT_MODEL]}. "
                f"Adicionar em MODEL_PRICING para precisao."
            )
            _warned_models.add(model_id)
        prices = MODEL_PRICING[DEFAULT_MODEL]

    input_price, output_price = prices

    # Somar componentes
    cost = (
        (max(0, input_tokens) / 1_000_000) * input_price
        + (max(0, output_tokens) / 1_000_000) * output_price
        + (max(0, cache_creation_tokens) / 1_000_000) * input_price * _CACHE_CREATION_MULTIPLIER
        + (max(0, cache_read_tokens) / 1_000_000) * input_price * _CACHE_READ_MULTIPLIER
    )
    return round(cost, 6)


def get_known_models() -> list[str]:
    """Retorna lista de modelos conhecidos (para validação/tests)."""
    return sorted(MODEL_PRICING.keys())

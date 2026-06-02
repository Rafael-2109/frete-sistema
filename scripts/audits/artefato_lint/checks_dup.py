from __future__ import annotations
from difflib import SequenceMatcher
from itertools import combinations
from .findings import Finding

def compare_blocks(blocks: dict[str, str], cfg) -> list[Finding]:
    out: list[Finding] = []
    items = list(blocks.items())
    for (pa, ta), (pb, tb) in combinations(items, 2):
        ratio = SequenceMatcher(None, ta, tb).ratio()
        if ratio >= cfg.dup_textual_block:
            out.append(Finding("D5", pa, 1, f"near-duplicate textual {ratio:.2f} vs {pb} (use --override+justificativa)", "block"))
        elif ratio >= cfg.dup_textual_report:
            out.append(Finding("D5", pa, 1, f"near-duplicate textual {ratio:.2f} vs {pb}", "report"))
    return out

def semantic_compare(blocks: dict[str, str], cfg) -> list[Finding]:
    """Interface da faixa semantica (Voyage/pgvector). Onda 0: no-op.

    Ativacao on-demand (memoria feedback_evals_llm_caros_preferir_pytest:
    NUNCA trigger automatico). Implementacao real em onda posterior usa
    embeddings ja existentes (~$0.90/mes) com cosseno >= cfg.dup_semantic_block.
    """
    return []

"""Eval set — qualidade do retrieval de regras SPED ECD.

Golden dataset construido a partir de:
- Erros reais reportados pelo PVA (categorias V18-V31 em SPED_ECD_PLANO.md)
- Top erros mais comuns (manual_ecd/04_regras_validacao.md secao "Top Erros")
- Regras do Manual ECD Leiaute 9 (manual_ecd/bloco_*.md)

Testes:
- precision@1 para queries com REGRA_X explicito (hybrid exact)
- recall@5 para queries em linguagem natural (semantico)
- autodetect de codigo de registro (`I050`, `J930` etc)
- filtros por chunk_type / bloco / registro
- threshold de similarity respeitado

Skipped quando VOYAGE_API_KEY nao configurada (CI offline).
"""

from __future__ import annotations

import pytest


# ============================================================
# GOLDEN DATASET — queries vs resultado esperado
# ============================================================

EXACT_REGRA_QUERIES = [
    # (query, regra_name_esperada_no_top_1)
    ("REGRA_HIERARQUIA_ARQUIVO falhou no upload", "REGRA_HIERARQUIA_ARQUIVO"),
    ("REGRA_COD_CTA_DUPLICADO", "REGRA_COD_CTA_DUPLICADO"),
    ("erro REGRA_TABELA_NATUREZA na conta", "REGRA_TABELA_NATUREZA"),
    ("REGRA_VALIDA_NIVEL_CONTAS - hierarquia errada", "REGRA_VALIDA_NIVEL_CONTAS"),
    ("Pq REGRA_NATUREZA_CONTA diz que filho difere?", "REGRA_NATUREZA_CONTA"),
]

SEMANTIC_QUERIES = [
    # (query, lista_de_keywords_que_devem_aparecer_em_top_5)
    (
        "conta sem natureza definida no plano",
        ["natureza", "COD_NAT"],
    ),
    (
        "saldo final do I155 nao bate com debitos e creditos",
        ["saldo", "I155"],
    ),
    (
        "codigo de aglutinacao I052 emitido em conta sintetica",
        ["I052", "aglutinacao"],
    ),
    (
        "contador no J930 sem CPF preenchido",
        ["J930", "contador"],
    ),
    (
        "termo de abertura com NIRE invalido",
        ["I030", "NIRE"],
    ),
]

REGISTRO_AUTODETECT_QUERIES = [
    # (query_contendo_codigo_registro, registro_esperado_autodetectado)
    ("I050 codigo duplicado", "I050"),
    ("J930 quantos signatarios obrigatorios", "J930"),
    ("I250 partidas com VL_DC negativo", "I250"),
]


# ============================================================
# TESTES — precision @ 1 para hybrid exact
# ============================================================

@pytest.mark.voyage_api
@pytest.mark.parametrize("query,expected_regra", EXACT_REGRA_QUERIES)
def test_exact_lookup_top_1(app, chunk_count_baseline, query, expected_regra):
    """Query contendo REGRA_X retorna chunk dessa regra como top-1 exato."""
    from app.embeddings.sped_rules_search import buscar_regras_semantico

    results = buscar_regras_semantico(query, limit=5)
    assert results, f"Sem resultados para query={query!r}"
    top = results[0]
    assert top["match_type"] == "exact", (
        f"Top-1 deveria ser exato, foi {top['match_type']!r}. "
        f"regra_name={top.get('regra_name')!r}"
    )
    assert top["regra_name"] == expected_regra, (
        f"Top-1 regra_name={top['regra_name']!r}, esperado {expected_regra!r}"
    )
    assert top["similarity"] == 1.0


# ============================================================
# TESTES — recall @ 5 para semantico
# ============================================================

@pytest.mark.voyage_api
@pytest.mark.parametrize("query,expected_keywords", SEMANTIC_QUERIES)
def test_semantic_recall_at_5(app, chunk_count_baseline, query, expected_keywords):
    """Top-5 contem pelo menos 1 chunk mencionando keywords esperadas."""
    from app.embeddings.sped_rules_search import buscar_regras_semantico

    results = buscar_regras_semantico(query, limit=5)
    assert results, f"Sem resultados para query={query!r}"

    # Concat content + regra_name dos top-5 para keyword search
    haystack = " ".join(
        f"{r.get('regra_name') or ''} {r.get('content') or ''}"
        for r in results
    ).lower()

    missing = [kw for kw in expected_keywords if kw.lower() not in haystack]
    assert not missing, (
        f"Top-5 para query={query!r} nao contem {missing!r}. "
        f"Top-5 regra_names: {[r.get('regra_name') for r in results]}"
    )


# ============================================================
# TESTES — autodetect de codigo de registro
# ============================================================

@pytest.mark.voyage_api
@pytest.mark.parametrize("query,expected_registro", REGISTRO_AUTODETECT_QUERIES)
def test_autodetect_registro_filter(app, chunk_count_baseline, query, expected_registro):
    """Query contendo codigo de registro filtra automaticamente."""
    from app.embeddings.sped_rules_search import buscar_regras_semantico

    results = buscar_regras_semantico(query, limit=10)
    assert results, f"Sem resultados para query={query!r}"

    # Todos resultados com registro definido devem ser do registro esperado
    wrong_registro = [
        r for r in results
        if r.get("registro") and r["registro"] != expected_registro
    ]
    assert not wrong_registro, (
        f"Query {query!r} retornou chunks de outros registros: "
        f"{[r['registro'] for r in wrong_registro]}"
    )


# ============================================================
# TESTES — comportamento de filtros e threshold
# ============================================================

@pytest.mark.voyage_api
def test_filtro_chunk_type_so_regras(app, chunk_count_baseline):
    """Filtro chunk_type='regra' retorna so chunks de regras nomeadas."""
    from app.embeddings.sped_rules_search import buscar_regras_semantico

    results = buscar_regras_semantico(
        "natureza da conta",
        chunk_type="regra",
        limit=10,
    )
    for r in results:
        assert r["chunk_type"] == "regra", (
            f"Esperado chunk_type='regra', obtido {r['chunk_type']!r}"
        )
        assert r["regra_name"], "Chunk de regra deveria ter regra_name"


@pytest.mark.voyage_api
def test_filtro_bloco_I(app, chunk_count_baseline):
    """Filtro bloco='I' retorna so chunks do Bloco I (Lancamentos)."""
    from app.embeddings.sped_rules_search import buscar_regras_semantico

    results = buscar_regras_semantico(
        "saldo conta",
        bloco="I",
        limit=10,
    )
    for r in results:
        if r.get("bloco"):  # chunks sem bloco (capitulos, gotchas) ignoram filtro
            assert r["bloco"] == "I", (
                f"Esperado bloco='I', obtido {r['bloco']!r}"
            )


@pytest.mark.voyage_api
def test_rerank_match_type_aparece_quando_habilitado(app, chunk_count_baseline, monkeypatch):
    """P1-2: query natural sem REGRA_X com rerank ON -> match_type='rerank'."""
    import app.embeddings.sped_rules_search as srs
    from app.embeddings.sped_rules_search import buscar_regras_semantico

    # Force rerank ON (mesmo se env ja for true, garante semantica do teste)
    monkeypatch.setattr(srs, "RERANK_SPED_RULES", True)

    # Query natural ambigua, sem REGRA_X — entra no caminho de rerank
    results = buscar_regras_semantico(
        "saldo da conta ficou negativo apos lancamento de encerramento",
        limit=10,
    )
    assert results, "Sem resultados — golden query falhou"

    match_types = {r["match_type"] for r in results}
    assert "rerank" in match_types, (
        f"Esperado pelo menos 1 resultado com match_type='rerank'. "
        f"Tipos retornados: {match_types}"
    )


@pytest.mark.voyage_api
def test_rerank_skip_quando_regra_x_exato(app, chunk_count_baseline, monkeypatch):
    """P1-2: query com REGRA_X explicito -> P1-3 cobre, rerank nao roda."""
    import app.embeddings.sped_rules_search as srs
    from app.embeddings.sped_rules_search import buscar_regras_semantico

    monkeypatch.setattr(srs, "RERANK_SPED_RULES", True)

    results = buscar_regras_semantico("REGRA_HIERARQUIA_ARQUIVO falhou", limit=5)
    assert results
    # Top-1 deve ser exato (P1-3), nao rerank
    assert results[0]["match_type"] == "exact"
    # Outros podem ser semantic (cosine puro), mas NUNCA rerank quando ha exact
    for r in results:
        assert r["match_type"] != "rerank", (
            f"Rerank rodou indevidamente em query com REGRA_X: {r}"
        )


@pytest.mark.voyage_api
def test_rerank_off_volta_para_semantic(app, chunk_count_baseline, monkeypatch):
    """P1-2: com flag OFF, match_type volta a 'semantic'."""
    import app.embeddings.sped_rules_search as srs
    from app.embeddings.sped_rules_search import buscar_regras_semantico

    monkeypatch.setattr(srs, "RERANK_SPED_RULES", False)

    results = buscar_regras_semantico(
        "saldo da conta ficou negativo apos lancamento de encerramento",
        limit=10,
    )
    assert results
    match_types = {r["match_type"] for r in results}
    assert "rerank" not in match_types, (
        f"Rerank rodou com flag OFF. Tipos: {match_types}"
    )
    assert "semantic" in match_types


@pytest.mark.voyage_api
def test_min_similarity_respeitado(app, chunk_count_baseline):
    """Resultados semanticos nunca abaixo do threshold."""
    from app.embeddings.sped_rules_search import buscar_regras_semantico

    threshold = 0.7  # mais estrito que default
    results = buscar_regras_semantico(
        "qualquer coisa nao relacionada blockchain",
        min_similarity=threshold,
        limit=10,
    )
    for r in results:
        if r["match_type"] == "semantic":
            assert r["similarity"] >= threshold, (
                f"Resultado semantico com sim={r['similarity']:.3f} < {threshold}"
            )


# ============================================================
# TESTE — integridade do indice
# ============================================================

def test_baseline_chunks_indexados(app, chunk_count_baseline):
    """Tabela tem pelo menos N chunks (sanity vs accidentally truncated)."""
    # Apos os fixes P0 + P1-1, esperamos ~449 chunks. Margem de seguranca: 350.
    assert chunk_count_baseline >= 350, (
        f"Apenas {chunk_count_baseline} chunks indexados — "
        f"esperado >=350 (re-rode indexer)"
    )


def test_claude_md_subtipos_p2_3():
    """P2-3: _classify_claude_md_section mapeia titulos para tipos corretos.

    Teste unitario do classificador — nao depende do DB nem de Voyage.
    """
    from app.embeddings.indexers.sped_ecd_rules_indexer import (
        _classify_claude_md_section,
    )

    casos = [
        ("GOTCHAS — VOCE PRECISA SABER", "gotcha"),
        ("HISTORICO DE VERSOES E DECISOES CRITICAS", "decisao"),
        ("PROTOCOLO DE NOVA VERSAO", "procedimento"),
        ("COMO ITERAR EM CORRECOES (FLUXO)", "procedimento"),
        ("ARQUITETURA — 5 SERVICES", "arquitetura"),
        ("TECH STACK ESPECIFICO", "arquitetura"),
        ("ROTAS (routes.py — Blueprint `relatorios_fiscais`)", "arquitetura"),
        ("CONSTANTES CRITICAS (constantes.py)", "arquitetura"),
        ("REFERENCIAS", "referencia"),
        ("CONTEXTO CRITICO PARA NOVA SESSAO", "contexto"),
        ("TITULO INVENTADO QUE NAO BATE", "gotcha"),  # fallback conservador
    ]
    for titulo, esperado in casos:
        got = _classify_claude_md_section(titulo)
        assert got == esperado, (
            f"_classify_claude_md_section({titulo!r}) = {got!r}, "
            f"esperado {esperado!r}"
        )


def test_chunk_type_distribution(app, chunk_count_baseline):
    """Distribuicao por tipo cobre os tipos do indice (incluindo sub-tipos
    P2-3 do CLAUDE.md: gotcha/decisao/procedimento/arquitetura/contexto)."""
    from app import db
    from sqlalchemy import text

    rows = db.session.execute(text(
        "SELECT chunk_type, COUNT(*) AS c FROM sped_ecd_rule_embeddings GROUP BY chunk_type"
    )).all()
    types = {row.chunk_type for row in rows}

    # Tipos vindos do Manual ECD + PLANO (estaveis)
    expected_core = {
        "regra", "registro", "manual_capitulo", "regra_pva",
        "plano_iteracao", "categoria_erro",
    }
    missing_core = expected_core - types
    assert not missing_core, (
        f"Chunk types core faltando: {missing_core}. "
        f"Re-rode: python -m app.embeddings.indexers.sped_ecd_rules_indexer --reindex"
    )

    # Tipos vindos do CLAUDE.md (sub-tipados P2-3). Pelo menos 2 dos sub-tipos
    # devem aparecer — se so 'gotcha' existir, a classificacao quebrou.
    claude_md_subtypes = types & {
        "gotcha", "decisao", "procedimento", "arquitetura", "referencia", "contexto",
    }
    assert len(claude_md_subtypes) >= 2, (
        f"Sub-tipos do CLAUDE.md degenerados: {claude_md_subtypes}. "
        f"Classificacao _classify_claude_md_section() pode ter regredido."
    )

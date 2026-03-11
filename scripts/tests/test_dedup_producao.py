#!/usr/bin/env python3
"""
Diagnóstico de dedup de memórias — roda em produção (read-only).

Testa AMBAS as camadas do dedup:
- Layer 0: Text overlap (overlap coefficient de palavras normalizadas)
- Layer 1: dedup_embedding (embedding de texto limpo, threshold 0.85)
  + fallback para embedding contextualizado (threshold 0.70)

Uso:
    source .venv/bin/activate
    python scripts/tests/test_dedup_producao.py

Requer: VOYAGE_API_KEY, DATABASE_URL (produção via Render shell)
Não grava nada — apenas lê embeddings e gera novos para comparação.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app # type: ignore # noqa: E402
from app.agente.services.knowledge_graph_service import strip_xml_tags # type: ignore # noqa: E402


# ── Cenários de teste ──────────────────────────────────────────────
CENARIOS = [
    {
        "nome": "Atacadão NF completa (variante)",
        "conteudo_novo": (
            '<regra>\n'
            '  <descricao>O cliente Atacadão exige nota fiscal completa em todas as entregas</descricao>\n'
            '  <contexto>Emissão de NF para entregas ao Atacadão</contexto>\n'
            '</regra>'
        ),
        "duplicata_esperada_path": "/memories/empresa/regras/atacadao-sempre-pede-nf-completa.xml",
    },
    {
        "nome": "Dry-run Odoo (variante)",
        "conteudo_novo": (
            '<regra>\n'
            '  <descricao>Sempre realizar dry-run antes de executar ações em massa no Odoo</descricao>\n'
            '  <contexto>Operações em lote no Odoo</contexto>\n'
            '</regra>'
        ),
        "duplicata_esperada_path": "/memories/empresa/regras/antes-de-executar-acoes-em-lote-no-odoo.xml",
    },
    {
        "nome": "Assaí confirmação manual (variante)",
        "conteudo_novo": (
            '<regra>\n'
            '  <descricao>Cotações da rede Assaí no Odoo precisam confirmação manual</descricao>\n'
            '  <contexto>Processamento de pedidos Assaí</contexto>\n'
            '</regra>'
        ),
        "duplicata_esperada_path": "/memories/empresa/regras/cotacoes-para-a-rede-assai-no-odoo-preci.xml",
    },
    {
        "nome": "Assaí múltiplas lojas (variante)",
        "conteudo_novo": (
            '<regra>\n'
            '  <descricao>A rede Assaí trabalha com várias lojas identificadas por número</descricao>\n'
            '  <contexto>Identificação de pedidos por loja Assaí</contexto>\n'
            '</regra>'
        ),
        "duplicata_esperada_path": "/memories/empresa/regras/a-rede-assai-opera-com-multiplas-lojas-i.xml",
    },
    {
        "nome": "Fato NOVO (NÃO deve detectar duplicata)",
        "conteudo_novo": (
            '<regra>\n'
            '  <descricao>Transportadora Rodonaves tem prazo de 5 dias para entregas em Manaus</descricao>\n'
            '  <contexto>Prazos de entrega região Norte</contexto>\n'
            '</regra>'
        ),
        "duplicata_esperada_path": None,
    },
]


def run_diagnostico():
    app = create_app()

    with app.app_context():
        from app.embeddings.config import MEMORY_SEMANTIC_SEARCH, EMBEDDINGS_ENABLED # type: ignore # noqa: E402
        from app.embeddings.service import EmbeddingService # type: ignore # noqa: E402
        from app import db # type: ignore # noqa: E402
        from sqlalchemy import text
        from app.agente.tools.memory_mcp_tool import ( #type: ignore # noqa: E402
            _text_overlap_check,
            _normalize_words_for_dedup,
        )

        print("=" * 72)
        print("DIAGNÓSTICO DE DEDUP DE MEMÓRIAS (Layer 0 + Layer 1)")
        print("=" * 72)
        print(f"EMBEDDINGS_ENABLED: {EMBEDDINGS_ENABLED}")
        print(f"MEMORY_SEMANTIC_SEARCH: {MEMORY_SEMANTIC_SEARCH}")

        # Verificar se dedup_embedding existe
        has_dedup_col = False
        try:
            col_check = db.session.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'agent_memory_embeddings'
                  AND column_name = 'dedup_embedding'
            """)).fetchone()
            has_dedup_col = col_check is not None
        except Exception:
            pass

        dedup_count = 0
        if has_dedup_col:
            dedup_count = db.session.execute(text("""
                SELECT COUNT(*) FROM agent_memory_embeddings
                WHERE dedup_embedding IS NOT NULL
            """)).scalar()

        print(f"Coluna dedup_embedding: {'SIM' if has_dedup_col else 'NÃO (migration pendente)'}")
        if has_dedup_col:
            total_emb = db.session.execute(text(
                "SELECT COUNT(*) FROM agent_memory_embeddings"
            )).scalar()
            print(f"  Populados: {dedup_count}/{total_emb}")

        svc = EmbeddingService() if EMBEDDINGS_ENABLED and MEMORY_SEMANTIC_SEARCH else None
        if svc:
            print(f"Modelo: {svc.model}")
        print()

        resultados = []

        for i, cenario in enumerate(CENARIOS, 1):
            print(f"─── Cenário {i}: {cenario['nome']} ───")

            clean_content = strip_xml_tags(cenario['conteudo_novo'])
            print(f"  Query (stripped): \"{clean_content[:80]}...\"")

            esperada = cenario['duplicata_esperada_path']
            detectou_layer0 = False
            detectou_layer1_dedup = False
            detectou_layer1_fallback = False

            # ── Layer 0: Text overlap ──
            print(f"  [Layer 0 — Text Overlap]")
            words_new = _normalize_words_for_dedup(clean_content)
            print(f"    Palavras: {sorted(words_new)}")

            try:
                text_dup = _text_overlap_check(
                    user_id=0, clean_content=clean_content,
                    current_path='/memories/test-dedup-diagnostico'
                )
                if text_dup:
                    print(f"    ✓ Detectou: {text_dup}")
                    detectou_layer0 = True
                else:
                    print(f"    Nenhuma duplicata")
            except Exception as e:
                print(f"    ⚠ Erro: {e}")

            # ── Layer 1: dedup_embedding + fallback ──
            if svc:
                # DEDUP: input_type="document" (mesmo tipo do armazenado)
                query_embedding = svc.embed_texts([clean_content], input_type="document")[0]
                embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
                svc._enable_iterative_scan()

                # 1A. dedup_embedding (threshold 0.85)
                if has_dedup_col and dedup_count is not None and dedup_count > 0:
                    print(f"  [Layer 1A — dedup_embedding (threshold 0.85)]")
                    result = db.session.execute(text("""
                        SELECT
                            path,
                            1 - (dedup_embedding <=> CAST(:query AS vector)) AS similarity
                        FROM agent_memory_embeddings
                        WHERE user_id = ANY(:user_ids)
                          AND dedup_embedding IS NOT NULL
                        ORDER BY dedup_embedding <=> CAST(:query AS vector)
                        LIMIT 5
                    """), {"query": embedding_str, "user_ids": [0]})

                    for row in result.fetchall():
                        sim = float(row.similarity)
                        marker = " ◄ ESPERADO" if row.path == esperada else ""
                        status = "✓ ACIMA 0.85" if sim >= 0.85 else "  abaixo 0.85"
                        print(f"    {sim:.4f} | {status} | {row.path}{marker}")
                        if row.path == esperada and sim >= 0.85:
                            detectou_layer1_dedup = True
                else:
                    print(f"  [Layer 1A — dedup_embedding: N/A (não populado)]")

                # 1B. fallback embedding contextualizado (threshold 0.70)
                print(f"  [Layer 1B — embedding contextualizado (fallback 0.70)]")
                results = svc.search_memories(
                    clean_content, user_id=0, limit=5, min_similarity=0.50
                )
                if results:
                    for r in results:
                        path = r.get('path', '')
                        sim = r.get('similarity', 0)
                        marker = " ◄ ESPERADO" if path == esperada else ""
                        status = "✓ ACIMA 0.70" if sim >= 0.70 else "  abaixo 0.70"
                        print(f"    {sim:.4f} | {status} | {path}{marker}")
                        if path == esperada and sim >= 0.70:
                            detectou_layer1_fallback = True
                else:
                    print(f"    Nenhum resultado (similarity < 0.50)")

            # ── Veredicto ──
            if esperada is None:
                if detectou_layer0:
                    resultados.append(('FALSO_POS', cenario['nome'], 'L0'))
                    print(f"  VEREDICTO: ✗ FALSO POSITIVO")
                else:
                    resultados.append(('OK', cenario['nome'], '-'))
                    print(f"  VEREDICTO: ✓ OK (fato novo)")
            else:
                if detectou_layer0:
                    resultados.append(('OK', cenario['nome'], 'L0'))
                    print(f"  VEREDICTO: ✓ DETECTADO (Layer 0 — text overlap)")
                elif detectou_layer1_dedup:
                    resultados.append(('OK', cenario['nome'], 'L1A'))
                    print(f"  VEREDICTO: ✓ DETECTADO (Layer 1A — dedup_embedding ≥0.85)")
                elif detectou_layer1_fallback:
                    resultados.append(('OK', cenario['nome'], 'L1B'))
                    print(f"  VEREDICTO: ✓ DETECTADO (Layer 1B — fallback ≥0.70)")
                else:
                    resultados.append(('FALSO_NEG', cenario['nome'], '-'))
                    print(f"  VEREDICTO: ✗ FALSO NEGATIVO")

            print()

        # ── Resumo ──────────────────────────────────────────────────
        print("=" * 72)
        print("RESUMO")
        print("=" * 72)
        ok = sum(1 for r in resultados if r[0] == 'OK')
        falso_neg = sum(1 for r in resultados if r[0] == 'FALSO_NEG')
        falso_pos = sum(1 for r in resultados if r[0] == 'FALSO_POS')
        total = len(resultados)

        for status, nome, layer in resultados:
            icon = {'OK': '✓', 'FALSO_NEG': '✗', 'FALSO_POS': '⚠'}[status]
            layer_info = f" [{layer}]" if layer != '-' else ""
            print(f"  {icon} {nome}{layer_info}")

        print()
        print(f"  Resultado: {ok}/{total} OK | {falso_neg} falsos negativos | {falso_pos} falsos positivos")

        if ok == total:
            print("\n  ✓ Dedup funcionando corretamente!")
        if falso_neg > 0 and not has_dedup_col:
            print("\n  ℹ Layer 1A indisponível — rode a migration:")
            print("    python scripts/migrations/adicionar_dedup_embedding.py")
            print("    python scripts/migrations/backfill_dedup_embedding.py")
        elif falso_neg > 0 and dedup_count == 0:
            print("\n  ℹ dedup_embedding não populado — rode o backfill:")
            print("    python scripts/migrations/backfill_dedup_embedding.py")

        print()


if __name__ == '__main__':
    run_diagnostico()

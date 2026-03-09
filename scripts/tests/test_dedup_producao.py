#!/usr/bin/env python3
"""
Diagnóstico de dedup de memórias — roda em produção (read-only).

Simula _check_memory_duplicate() com conteúdos variantes de memórias
existentes e reporta se o dedup detectaria a duplicata.

Uso:
    source .venv/bin/activate
    python scripts/tests/test_dedup_producao.py

Requer: VOYAGE_API_KEY, DATABASE_URL (produção via Render shell)
Não grava nada — apenas lê embeddings e gera novos para comparação.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app
from app.agente.services.knowledge_graph_service import strip_xml_tags


# ── Cenários de teste ──────────────────────────────────────────────
# Cada cenário: conteúdo XML que o Agent tentaria salvar,
# com a memória existente que DEVERIA ser detectada como duplicata.
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
        "duplicata_esperada_id": 139,
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
        "duplicata_esperada_id": 112,
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
        "duplicata_esperada_id": 141,
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
        "duplicata_esperada_id": 111,
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
        "duplicata_esperada_id": None,
    },
]


def run_diagnostico():
    app = create_app()

    with app.app_context():
        from app.embeddings.config import MEMORY_SEMANTIC_SEARCH, EMBEDDINGS_ENABLED
        from app.embeddings.service import EmbeddingService

        print("=" * 72)
        print("DIAGNÓSTICO DE DEDUP DE MEMÓRIAS")
        print("=" * 72)
        print(f"EMBEDDINGS_ENABLED: {EMBEDDINGS_ENABLED}")
        print(f"MEMORY_SEMANTIC_SEARCH: {MEMORY_SEMANTIC_SEARCH}")

        if not EMBEDDINGS_ENABLED or not MEMORY_SEMANTIC_SEARCH:
            print("\n⚠ Embeddings desabilitados — dedup semântico NÃO funciona!")
            return

        svc = EmbeddingService()
        print(f"Modelo: {svc.model}")
        print(f"Dimensões: {svc.dimensions}")
        print()

        resultados = []

        for i, cenario in enumerate(CENARIOS, 1):
            print(f"─── Cenário {i}: {cenario['nome']} ───")

            # 1. Strip XML (exatamente como _check_memory_duplicate faz)
            clean_content = strip_xml_tags(cenario['conteudo_novo'])
            print(f"  Query (stripped): \"{clean_content[:80]}...\"")

            # 2. Buscar via search_memories (exatamente como _check_memory_duplicate faz)
            # user_id=0 = memórias empresa
            results = svc.search_memories(
                clean_content, user_id=0, limit=5, min_similarity=0.50
            )

            if not results:
                print(f"  Resultados: NENHUM (similarity < 0.50)")
                detectou = cenario['duplicata_esperada_path'] is None
                resultados.append(('OK' if detectou else 'FALHOU', cenario['nome'], None, None))
                print(f"  Veredicto: {'✓ OK (fato novo, sem match)' if detectou else '✗ FALHOU (deveria ter encontrado)'}")
                print()
                continue

            # 3. Mostrar top resultados
            print(f"  Top {len(results)} resultados:")
            melhor_match = None
            for r in results:
                path = r.get('path', '')
                sim = r.get('similarity', 0)
                marker = ""
                if path == cenario.get('duplicata_esperada_path'):
                    marker = " ◄ ESPERADO"
                    melhor_match = sim
                acima_threshold = "✓ ACIMA 0.85" if sim >= 0.85 else "✗ ABAIXO 0.85"
                print(f"    {sim:.4f} | {acima_threshold} | {path}{marker}")

            # 4. Verificar se dedup detectaria
            if cenario['duplicata_esperada_path'] is None:
                # Fato novo — nenhum match deve estar acima de 0.85
                falsos_positivos = [r for r in results if r.get('similarity', 0) >= 0.85]
                if falsos_positivos:
                    print(f"  Veredicto: ✗ FALSO POSITIVO — {len(falsos_positivos)} match(es) acima de 0.85")
                    resultados.append(('FALSO_POS', cenario['nome'], falsos_positivos[0]['similarity'], falsos_positivos[0]['path']))
                else:
                    print(f"  Veredicto: ✓ OK — nenhum falso positivo")
                    resultados.append(('OK', cenario['nome'], results[0]['similarity'] if results else None, None))
            else:
                # Duplicata esperada — deve estar acima de 0.85
                if melhor_match is not None and melhor_match >= 0.85:
                    print(f"  Veredicto: ✓ DEDUP FUNCIONA — duplicata detectada (sim={melhor_match:.4f})")
                    resultados.append(('OK', cenario['nome'], melhor_match, cenario['duplicata_esperada_path']))
                elif melhor_match is not None:
                    print(f"  Veredicto: ✗ FALSO NEGATIVO — duplicata encontrada mas sim={melhor_match:.4f} < 0.85")
                    resultados.append(('FALSO_NEG', cenario['nome'], melhor_match, cenario['duplicata_esperada_path']))
                else:
                    # A duplicata esperada nem apareceu no top 5
                    print(f"  Veredicto: ✗ FALSO NEGATIVO — duplicata esperada nem apareceu nos resultados")
                    resultados.append(('FALSO_NEG', cenario['nome'], 0, cenario['duplicata_esperada_path']))

            print()

        # ── Resumo ──────────────────────────────────────────────────
        print("=" * 72)
        print("RESUMO")
        print("=" * 72)
        ok = sum(1 for r in resultados if r[0] == 'OK')
        falso_neg = sum(1 for r in resultados if r[0] == 'FALSO_NEG')
        falso_pos = sum(1 for r in resultados if r[0] == 'FALSO_POS')
        total = len(resultados)

        for status, nome, sim, path in resultados:
            icon = {'OK': '✓', 'FALSO_NEG': '✗', 'FALSO_POS': '⚠', 'FALHOU': '✗'}[status]
            sim_str = f" (sim={sim:.4f})" if sim is not None else ""
            print(f"  {icon} {nome}{sim_str}")

        print()
        print(f"  Resultado: {ok}/{total} OK | {falso_neg} falsos negativos | {falso_pos} falsos positivos")

        if falso_neg > 0:
            print()
            print("  ⚠ FALSOS NEGATIVOS = dedup NÃO está pegando duplicatas!")
            print("  O threshold 0.85 está alto demais para a lacuna de representação")
            print("  entre query (texto limpo) e embedding armazenado (contexto Sonnet + XML).")
        elif ok == total:
            print()
            print("  ✓ Dedup está funcionando corretamente para todos os cenários!")

        print()


if __name__ == '__main__':
    run_diagnostico()

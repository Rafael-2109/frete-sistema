"""
Indexer de templates SQL para few-shot retrieval.

Coleta queries SQL bem-sucedidas e gera embeddings das perguntas
para busca semantica posterior no text_to_sql pipeline.

Duas fontes de dados:
1. Seed: Templates pre-definidos (padroes comuns do sistema)
2. Runtime: Queries bem-sucedidas salvas pelo pipeline

Executar:
    source .venv/bin/activate
    python -m app.embeddings.indexers.sql_template_indexer [--dry-run] [--seed] [--stats]
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, List

from sqlalchemy import text

logger = logging.getLogger(__name__)


# =====================================================================
# TEMPLATES SEED — Padroes comuns do sistema
# =====================================================================

SEED_TEMPLATES = [
    {
        "question_text": "top 10 clientes por faturamento",
        "sql_text": """SELECT nome_cliente, cnpj_cliente,
            COUNT(DISTINCT numero_nf) AS qtd_nfs,
            ROUND(SUM(valor_total_nf)::numeric, 2) AS total_faturado
        FROM faturamento_produto
        WHERE status_nf = 'Lancado' AND revertida = False
        GROUP BY nome_cliente, cnpj_cliente
        ORDER BY total_faturado DESC
        LIMIT 10""",
        "tables_used": "faturamento_produto",
    },
    {
        "question_text": "pedidos pendentes por estado",
        "sql_text": """SELECT cod_uf, COUNT(DISTINCT num_pedido) AS qtd_pedidos,
            SUM(qtd_saldo_produto_pedido) AS qtd_pendente
        FROM carteira_principal
        WHERE qtd_saldo_produto_pedido > 0 AND ativo = True
        GROUP BY cod_uf
        ORDER BY qtd_pedidos DESC""",
        "tables_used": "carteira_principal",
    },
    {
        "question_text": "faturamento por mes",
        "sql_text": """SELECT
            TO_CHAR(data_emissao, 'YYYY-MM') AS mes,
            COUNT(DISTINCT numero_nf) AS qtd_nfs,
            ROUND(SUM(valor_total_nf)::numeric, 2) AS total_faturado
        FROM faturamento_produto
        WHERE status_nf = 'Lancado' AND revertida = False
        GROUP BY TO_CHAR(data_emissao, 'YYYY-MM')
        ORDER BY mes DESC
        LIMIT 24""",
        "tables_used": "faturamento_produto",
    },
    {
        "question_text": "estoque atual por produto",
        "sql_text": """SELECT cod_produto, nome_produto,
            SUM(qtd_movimentacao) AS saldo_estoque
        FROM movimentacao_estoque
        WHERE ativo = True
        GROUP BY cod_produto, nome_produto
        HAVING SUM(qtd_movimentacao) > 0
        ORDER BY saldo_estoque DESC
        LIMIT 100""",
        "tables_used": "movimentacao_estoque",
    },
    {
        "question_text": "contas a receber vencidas",
        "sql_text": """SELECT numero_nf, nome_cliente, cnpj_raiz,
            parcela, valor_titulo, vencimento,
            CURRENT_DATE - vencimento AS dias_atraso
        FROM contas_a_receber
        WHERE vencimento < CURRENT_DATE AND parcela_paga = False
        ORDER BY dias_atraso DESC
        LIMIT 200""",
        "tables_used": "contas_a_receber",
    },
    {
        "question_text": "separacoes pendentes de faturamento",
        "sql_text": """SELECT s.num_pedido, s.cod_produto, s.nome_produto,
            s.qtd_saldo, s.nome_cidade, s.cod_uf
        FROM separacao s
        WHERE s.sincronizado_nf = False AND s.qtd_saldo > 0
        ORDER BY s.data_separacao
        LIMIT 500""",
        "tables_used": "separacao",
    },
    {
        "question_text": "entregas pendentes de canhoto",
        "sql_text": """SELECT em.numero_nf, em.nome_cliente,
            em.data_embarque, em.transportadora,
            em.status_entrega
        FROM entregas_monitoradas em
        WHERE em.status_entrega NOT IN ('ENTREGUE', 'DEVOLVIDA')
            AND em.data_embarque IS NOT NULL
        ORDER BY em.data_embarque
        LIMIT 200""",
        "tables_used": "entregas_monitoradas",
    },
    {
        "question_text": "devolucoes por motivo",
        "sql_text": """SELECT motivo, COUNT(*) AS qtd,
            ROUND(SUM(valor_total)::numeric, 2) AS valor_total
        FROM nf_devolucao
        GROUP BY motivo
        ORDER BY qtd DESC""",
        "tables_used": "nf_devolucao",
    },
    {
        "question_text": "fretes por transportadora",
        "sql_text": """SELECT nome_transportadora, cnpj_transportadora,
            COUNT(*) AS qtd_ctes,
            ROUND(SUM(valor_frete)::numeric, 2) AS total_frete
        FROM faturamento_produto
        WHERE status_nf = 'Lancado' AND revertida = False
            AND nome_transportadora IS NOT NULL
        GROUP BY nome_transportadora, cnpj_transportadora
        ORDER BY total_frete DESC
        LIMIT 30""",
        "tables_used": "faturamento_produto",
    },
    {
        "question_text": "producao programada vs realizada",
        "sql_text": """SELECT cod_produto, nome_produto,
            SUM(qtd_programada) AS programada,
            SUM(qtd_produzida) AS produzida,
            ROUND((SUM(qtd_produzida) / NULLIF(SUM(qtd_programada), 0) * 100)::numeric, 1) AS pct_cumprido
        FROM programacao_producao
        GROUP BY cod_produto, nome_produto
        ORDER BY pct_cumprido ASC NULLS FIRST
        LIMIT 50""",
        "tables_used": "programacao_producao",
    },
]


def _has_app_context() -> bool:
    """Verifica se esta dentro de um Flask app_context."""
    try:
        from flask import current_app
        _ = current_app.name
        return True
    except (RuntimeError, ImportError):
        return False


def _content_hash(text_str: str) -> str:
    """Gera MD5 do texto para dedup."""
    return hashlib.md5(text_str.strip().lower().encode('utf-8')).hexdigest()


# =====================================================================
# COLETA
# =====================================================================

def collect_seed_templates() -> List[Dict[str, Any]]:
    """
    Retorna templates seed pre-definidos.

    Returns:
        Lista de dicts com question_text, sql_text, tables_used, texto_embedado
    """
    results = []
    for t in SEED_TEMPLATES:
        texto = f"Pergunta: {t['question_text']}\nTabelas: {t['tables_used']}"
        results.append({
            "question_text": t["question_text"],
            "sql_text": t["sql_text"],
            "tables_used": t["tables_used"],
            "texto_embedado": texto,
            "content_hash": _content_hash(t["question_text"]),
        })
    return results


def collect_runtime_templates() -> List[Dict[str, Any]]:
    """
    Coleta templates do banco (queries salvas pelo pipeline).

    Returns:
        Lista de dicts prontos para indexacao
    """
    from app import db as _db
    from app.embeddings.models import SqlTemplateEmbedding

    existing = SqlTemplateEmbedding.query.all()
    results = []
    for t in existing:
        if t.embedding is not None:
            continue  # Ja tem embedding
        results.append({
            "id": t.id,
            "question_text": t.question_text,
            "sql_text": t.sql_text,
            "tables_used": t.tables_used,
            "texto_embedado": t.texto_embedado,
            "content_hash": t.content_hash,
        })
    return results


# =====================================================================
# INDEXACAO
# =====================================================================

def index_sql_templates(
    templates: List[Dict[str, Any]],
    reindex: bool = False,
) -> Dict[str, Any]:
    """
    Gera embeddings e salva/atualiza templates no banco.

    Args:
        templates: Lista de templates para indexar
        reindex: Se True, re-embeda mesmo que ja exista

    Returns:
        Estatisticas: {embedded, skipped, errors, total_tokens_est}
    """
    from app import db as _db
    from app.embeddings.service import EmbeddingService
    from app.embeddings.config import VOYAGE_DEFAULT_MODEL

    svc = EmbeddingService()
    stats = {"embedded": 0, "skipped": 0, "errors": 0, "total_tokens_est": 0}

    if not templates:
        return stats

    # Verificar existentes
    existing_hashes = set()
    if not reindex:
        result = _db.session.execute(
            text("SELECT content_hash FROM sql_template_embeddings WHERE embedding IS NOT NULL")
        )
        existing_hashes = {row[0] for row in result.fetchall()}

    # Filtrar novos
    to_embed = []
    for t in templates:
        if not reindex and t.get("content_hash") in existing_hashes:
            stats["skipped"] += 1
            continue
        to_embed.append(t)

    if not to_embed:
        logger.info(f"[SQL_TEMPLATE_INDEXER] Nada novo para indexar (skipped={stats['skipped']})")
        return stats

    # Batch embedding
    batch_size = 128
    for i in range(0, len(to_embed), batch_size):
        batch = to_embed[i:i + batch_size]
        texts = [t["texto_embedado"] for t in batch]

        try:
            embeddings = svc.embed_texts(texts, input_type="document")
        except Exception as e:
            logger.error(f"[SQL_TEMPLATE_INDEXER] Erro batch {i}: {e}")
            stats["errors"] += len(batch)
            continue

        for j, (template, embedding) in enumerate(zip(batch, embeddings)):
            try:
                embedding_json = json.dumps(embedding)
                tokens_est = max(1, len(template["texto_embedado"]) // 4)
                stats["total_tokens_est"] += tokens_est

                _db.session.execute(
                    text("""
                        INSERT INTO sql_template_embeddings
                            (question_text, sql_text, tables_used, execution_count,
                             texto_embedado, embedding, model_used, content_hash,
                             created_at, updated_at)
                        VALUES
                            (:question_text, :sql_text, :tables_used, :execution_count,
                             :texto_embedado, :embedding, :model_used, :content_hash,
                             NOW(), NOW())
                        ON CONFLICT (content_hash) WHERE content_hash IS NOT NULL
                        DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            model_used = EXCLUDED.model_used,
                            updated_at = NOW()
                    """),
                    {
                        "question_text": template["question_text"],
                        "sql_text": template["sql_text"],
                        "tables_used": template.get("tables_used", ""),
                        "execution_count": 1,
                        "texto_embedado": template["texto_embedado"],
                        "embedding": embedding_json,
                        "model_used": VOYAGE_DEFAULT_MODEL,
                        "content_hash": template["content_hash"],
                    }
                )
                stats["embedded"] += 1

            except Exception as e:
                logger.error(f"[SQL_TEMPLATE_INDEXER] Erro salvando template: {e}")
                stats["errors"] += 1

        _db.session.commit()
        if i + batch_size < len(to_embed):
            time.sleep(0.5)

    logger.info(f"[SQL_TEMPLATE_INDEXER] Concluido: {stats}")
    return stats


# =====================================================================
# FUNCAO DE SAVE ON-SUCCESS (chamada pelo text_to_sql pipeline)
# =====================================================================

def save_successful_query(question: str, sql: str, tables_used: list) -> bool:
    """
    Salva uma query bem-sucedida como template para few-shot futuro.

    Dedup: Se ja existe template com mesma pergunta (por content_hash),
    incrementa execution_count e atualiza last_used_at.

    Args:
        question: Pergunta original
        sql: SQL que executou com sucesso
        tables_used: Lista de tabelas usadas

    Returns:
        True se salvou/atualizou, False se erro
    """
    from app.embeddings.config import SQL_TEMPLATE_SEARCH, EMBEDDINGS_ENABLED

    if not EMBEDDINGS_ENABLED or not SQL_TEMPLATE_SEARCH:
        return False

    try:
        from app import db as _db
        from app.embeddings.service import EmbeddingService
        from app.embeddings.config import VOYAGE_DEFAULT_MODEL

        ch = _content_hash(question)
        tables_str = ",".join(tables_used) if tables_used else ""
        texto = f"Pergunta: {question}\nTabelas: {tables_str}"

        # Verificar se ja existe
        existing = _db.session.execute(
            text("SELECT id, execution_count FROM sql_template_embeddings WHERE content_hash = :ch"),
            {"ch": ch}
        ).fetchone()

        if existing:
            # Incrementar usage
            _db.session.execute(
                text("""
                    UPDATE sql_template_embeddings
                    SET execution_count = execution_count + 1,
                        last_used_at = NOW(),
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {"id": existing[0]}
            )
            _db.session.commit()
            return True

        # Novo template — gerar embedding
        svc = EmbeddingService()
        embedding = svc.embed_query(texto)
        embedding_json = json.dumps(embedding)

        _db.session.execute(
            text("""
                INSERT INTO sql_template_embeddings
                    (question_text, sql_text, tables_used, execution_count,
                     texto_embedado, embedding, model_used, content_hash,
                     last_used_at, created_at, updated_at)
                VALUES
                    (:question_text, :sql_text, :tables_used, 1,
                     :texto_embedado, :embedding, :model_used, :content_hash,
                     NOW(), NOW(), NOW())
            """),
            {
                "question_text": question,
                "sql_text": sql,
                "tables_used": tables_str,
                "texto_embedado": texto,
                "embedding": embedding_json,
                "model_used": VOYAGE_DEFAULT_MODEL,
                "content_hash": ch,
            }
        )
        _db.session.commit()
        logger.info(f"[SQL_TEMPLATE_INDEXER] Template salvo: {question[:60]}")
        return True

    except Exception as e:
        logger.error(f"[SQL_TEMPLATE_INDEXER] Erro salvando template: {e}")
        try:
            from app import db as _db
            _db.session.rollback()
        except Exception:
            pass
        return False


# =====================================================================
# CLI
# =====================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Indexer de templates SQL')
    parser.add_argument('--dry-run', action='store_true', help='Simula sem salvar')
    parser.add_argument('--seed', action='store_true', help='Indexa apenas templates seed')
    parser.add_argument('--reindex', action='store_true', help='Re-embeda todos')
    parser.add_argument('--stats', action='store_true', help='Mostra estatisticas')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(message)s')

    from app import create_app, db as _db
    app = create_app()

    with app.app_context():
        if args.stats:
            result = _db.session.execute(text("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(embedding) AS com_embedding,
                    SUM(execution_count) AS total_execucoes,
                    MAX(last_used_at) AS ultimo_uso
                FROM sql_template_embeddings
            """)).fetchone()
            print(f"\n=== SQL Template Embeddings ===")
            print(f"Total: {result[0]}")
            print(f"Com embedding: {result[1]}")
            print(f"Execucoes totais: {result[2]}")
            print(f"Ultimo uso: {result[3]}")
            return

        # Coletar templates
        if args.seed:
            templates = collect_seed_templates()
            print(f"Templates seed: {len(templates)}")
        else:
            seed = collect_seed_templates()
            runtime = collect_runtime_templates()
            templates = seed + runtime
            print(f"Templates: {len(seed)} seed + {len(runtime)} runtime = {len(templates)}")

        if args.dry_run:
            total_chars = sum(len(t["texto_embedado"]) for t in templates)
            tokens_est = total_chars // 4
            cost_est = tokens_est * 0.02 / 1_000_000
            print(f"\n[DRY-RUN]")
            print(f"Templates a indexar: {len(templates)}")
            print(f"Tokens estimados: {tokens_est:,}")
            print(f"Custo estimado: ${cost_est:.6f}")
            for t in templates[:5]:
                print(f"  - {t['question_text'][:80]}")
            if len(templates) > 5:
                print(f"  ... +{len(templates) - 5} templates")
            return

        # Indexar
        stats = index_sql_templates(templates, reindex=args.reindex)
        print(f"\n=== Resultado ===")
        print(f"Embedded: {stats['embedded']}")
        print(f"Skipped: {stats['skipped']}")
        print(f"Errors: {stats['errors']}")
        print(f"Tokens est: {stats['total_tokens_est']:,}")


if __name__ == '__main__':
    main()

"""
Indexer de categorias de pagamento para classificacao semantica.

Popula a tabela payment_category_embeddings com categorias de pagamento
e exemplos reais de payment_ref para matching semantico.

As categorias sao pre-definidas (seed) e nao tem coleta runtime —
o volume e fixo (~10-15 categorias).

Executar:
    source .venv/bin/activate
    python -m app.embeddings.indexers.payment_category_indexer [--dry-run] [--stats]
"""

import json
import logging
from typing import Any, Dict, List

from sqlalchemy import text

logger = logging.getLogger(__name__)


# =====================================================================
# CATEGORIAS DE PAGAMENTO — Dados Seed
# =====================================================================

PAYMENT_CATEGORIES = [
    {
        "category_name": "IMPOSTO",
        "description": "Pagamentos de impostos e tributos federais, estaduais e municipais",
        "examples": [
            "PAGTO ELETRONICO TRIBUTO",
            "DARF SIMPLES NACIONAL",
            "GNRE ICMS",
            "GPS INSS",
            "SEFAZ DARE",
            "DAS SIMPLES NACIONAL",
            "IRPJ RETIDO",
            "CSLL",
            "PIS COFINS",
            "ISS PREFEITURA",
            "IPTU PARCELA",
            "PAGAMENTO TRIBUTO FEDERAL",
        ],
    },
    {
        "category_name": "TARIFA",
        "description": "Tarifas bancarias: manutencao de conta, DOC, TED, PIX, pacote servicos",
        "examples": [
            "TARIFA BANCARIA",
            "TAR. MANUTENCAO",
            "TARIFA DOC/TED",
            "TARIFA PIX",
            "TAR. PACOTE SERVICOS",
            "TARIFA COBRANCA",
            "TAR. BOLETO",
            "TARIFA EXTRATO",
            "TARIFA CHEQUE",
        ],
    },
    {
        "category_name": "JUROS",
        "description": "Juros bancarios, emprestimos, conta garantida, financiamentos",
        "examples": [
            "JUROS EMPRESTIMO",
            "CONTA GARANTIDA",
            "JUROS FINANCIAMENTO",
            "ENCARGOS EMPRESTIMO",
            "JUROS CHEQUE ESPECIAL",
            "JUROS ROTATIVO",
            "ENCARGOS FINANCEIROS",
        ],
    },
    {
        "category_name": "IOF",
        "description": "Imposto sobre Operacoes Financeiras (emprestimos, cambio, seguros)",
        "examples": [
            "IOF EMPRESTIMO",
            "IOF FINANCIAMENTO",
            "IOF CAMBIO",
            "IOF OPERACAO CREDITO",
        ],
    },
    {
        "category_name": "FOLHA",
        "description": "Pagamentos de folha salarial, salarios, beneficios trabalhistas",
        "examples": [
            "FOLHA PAGAMENTO",
            "SALARIO FUNCIONARIOS",
            "SALÁRIO",
            "ADIANTAMENTO SALARIAL",
            "13O SALARIO",
            "FERIAS FUNCIONARIO",
            "RESCISAO TRABALHISTA",
            "FGTS",
            "VALE TRANSPORTE",
            "VALE ALIMENTACAO",
        ],
    },
    {
        "category_name": "FRETE",
        "description": "Pagamentos de frete, transporte, CTE, carreto, entrega",
        "examples": [
            "PAGTO FRETE",
            "CTE TRANSPORTE",
            "FRETE RODOVIARIO",
            "CARRETO",
            "PAGAMENTO TRANSPORTADORA",
            "FRETE ENTREGA",
            "COLETA E ENTREGA",
        ],
    },
    {
        "category_name": "ALUGUEL",
        "description": "Pagamentos de aluguel, locacao de imoveis, condominio",
        "examples": [
            "ALUGUEL",
            "LOCACAO IMOVEL",
            "CONDOMINIO",
            "ALUGUEL GALPAO",
            "ALUGUEL SALA COMERCIAL",
        ],
    },
    {
        "category_name": "ENERGIA",
        "description": "Pagamentos de energia eletrica, gas, agua",
        "examples": [
            "ENERGIA ELETRICA",
            "CPFL ENERGIA",
            "CEMIG",
            "ENEL",
            "LIGHT",
            "CONTA ENERGIA",
            "CONTA LUZ",
            "GAS ENCANADO",
            "SABESP AGUA",
            "CONTA AGUA",
        ],
    },
    {
        "category_name": "TELEFONE",
        "description": "Pagamentos de telefonia, internet, comunicacao",
        "examples": [
            "TELEFONE",
            "VIVO",
            "CLARO",
            "TIM",
            "OI",
            "INTERNET",
            "BANDA LARGA",
            "CONTA TELEFONE",
        ],
    },
    {
        "category_name": "SEGURO",
        "description": "Pagamentos de seguros: veicular, patrimonial, saude, vida",
        "examples": [
            "SEGURO VEICULAR",
            "SEGURO PATRIMONIAL",
            "SEGURO SAUDE",
            "PLANO SAUDE",
            "SEGURO VIDA",
            "SEGURO CARGA",
            "APOLICE SEGURO",
        ],
    },
    {
        "category_name": "FORNECEDOR",
        "description": "Pagamentos a fornecedores de materia-prima, insumos, mercadorias",
        "examples": [
            "PAGTO FORNECEDOR",
            "NF COMPRA",
            "MATERIA PRIMA",
            "INSUMOS",
            "COMPRA MERCADORIA",
            "PAGAMENTO DUPLICATA",
        ],
    },
    {
        "category_name": "OUTRO",
        "description": "Pagamentos nao classificados nas categorias anteriores",
        "examples": [
            "DIVERSOS",
            "PAGAMENTO DIVERSO",
            "TRANSFERENCIA INTERNA",
            "DESPESA DIVERSA",
        ],
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


# =====================================================================
# COLETA
# =====================================================================

def collect_categories() -> List[Dict[str, Any]]:
    """
    Retorna categorias de pagamento com texto para embedding.

    Returns:
        Lista de dicts com category_name, description, examples, texto_embedado
    """
    results = []
    for cat in PAYMENT_CATEGORIES:
        examples_str = " | ".join(cat["examples"])
        texto = (
            f"Categoria: {cat['category_name']}\n"
            f"Descricao: {cat['description']}\n"
            f"Exemplos: {examples_str}"
        )
        results.append({
            "category_name": cat["category_name"],
            "description": cat["description"],
            "examples": json.dumps(cat["examples"], ensure_ascii=False),
            "texto_embedado": texto,
        })
    return results


# =====================================================================
# INDEXACAO
# =====================================================================

def index_payment_categories(
    categories: List[Dict[str, Any]],
    reindex: bool = False,
) -> Dict[str, Any]:
    """
    Gera embeddings e salva categorias de pagamento.

    Args:
        categories: Lista de categorias para indexar
        reindex: Se True, re-embeda todas

    Returns:
        Estatisticas
    """
    from app import db as _db
    from app.embeddings.service import EmbeddingService
    from app.embeddings.config import VOYAGE_FINANCE_MODEL

    svc = EmbeddingService()
    stats = {"embedded": 0, "skipped": 0, "errors": 0, "total_tokens_est": 0}

    if not categories:
        return stats

    # Verificar existentes
    existing_cats = set()
    if not reindex:
        result = _db.session.execute(
            text("SELECT category_name FROM payment_category_embeddings WHERE embedding IS NOT NULL")
        )
        existing_cats = {row[0] for row in result.fetchall()}

    # Filtrar
    to_embed = []
    for cat in categories:
        if not reindex and cat["category_name"] in existing_cats:
            stats["skipped"] += 1
            continue
        to_embed.append(cat)

    if not to_embed:
        logger.info(f"[PAYMENT_CAT_INDEXER] Nada novo (skipped={stats['skipped']})")
        return stats

    # Embed todas de uma vez (~12 categorias, cabe em 1 batch)
    texts = [c["texto_embedado"] for c in to_embed]

    try:
        embeddings = svc.embed_texts(texts, input_type="document", model=VOYAGE_FINANCE_MODEL)
    except Exception as e:
        logger.error(f"[PAYMENT_CAT_INDEXER] Erro embedding: {e}")
        stats["errors"] = len(to_embed)
        return stats

    for cat, embedding in zip(to_embed, embeddings):
        try:
            embedding_json = json.dumps(embedding)
            tokens_est = max(1, len(cat["texto_embedado"]) // 4)
            stats["total_tokens_est"] += tokens_est

            _db.session.execute(
                text("""
                    INSERT INTO payment_category_embeddings
                        (category_name, description, examples,
                         texto_embedado, embedding, model_used,
                         created_at, updated_at)
                    VALUES
                        (:category_name, :description, :examples,
                         :texto_embedado, :embedding, :model_used,
                         NOW(), NOW())
                    ON CONFLICT (category_name)
                    DO UPDATE SET
                        description = EXCLUDED.description,
                        examples = EXCLUDED.examples,
                        texto_embedado = EXCLUDED.texto_embedado,
                        embedding = EXCLUDED.embedding,
                        model_used = EXCLUDED.model_used,
                        updated_at = NOW()
                """),
                {
                    "category_name": cat["category_name"],
                    "description": cat["description"],
                    "examples": cat["examples"],
                    "texto_embedado": cat["texto_embedado"],
                    "embedding": embedding_json,
                    "model_used": VOYAGE_FINANCE_MODEL,
                }
            )
            stats["embedded"] += 1

        except Exception as e:
            logger.error(f"[PAYMENT_CAT_INDEXER] Erro salvando {cat['category_name']}: {e}")
            stats["errors"] += 1

    _db.session.commit()
    logger.info(f"[PAYMENT_CAT_INDEXER] Concluido: {stats}")
    return stats


# =====================================================================
# CLI
# =====================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Indexer de categorias de pagamento')
    parser.add_argument('--dry-run', action='store_true', help='Simula sem salvar')
    parser.add_argument('--reindex', action='store_true', help='Re-embeda todas')
    parser.add_argument('--stats', action='store_true', help='Mostra estatisticas')

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    from app import create_app, db as _db
    app = create_app()

    with app.app_context():
        if args.stats:
            result = _db.session.execute(text("""
                SELECT COUNT(*), COUNT(embedding)
                FROM payment_category_embeddings
            """)).fetchone()
            print(f"\n=== Payment Category Embeddings ===")
            print(f"Total: {result[0]}")
            print(f"Com embedding: {result[1]}")
            return

        categories = collect_categories()
        print(f"Categorias: {len(categories)}")

        if args.dry_run:
            total_chars = sum(len(c["texto_embedado"]) for c in categories)
            tokens_est = total_chars // 4
            cost_est = tokens_est * 0.02 / 1_000_000
            print(f"\n[DRY-RUN]")
            print(f"Categorias a indexar: {len(categories)}")
            print(f"Tokens estimados: {tokens_est:,}")
            print(f"Custo estimado: ${cost_est:.6f}")
            for c in categories:
                print(f"  - {c['category_name']}: {c['description'][:60]}")
            return

        stats = index_payment_categories(categories, reindex=args.reindex)
        print(f"\nEmbedded: {stats['embedded']} | Skipped: {stats['skipped']} | Errors: {stats['errors']}")


if __name__ == '__main__':
    main()

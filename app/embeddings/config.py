"""
Configuracao centralizada do modulo de embeddings.

Todas as configuracoes vem de variaveis de ambiente com defaults sensiveis.
"""

import os


# ============================================================
# VOYAGE AI
# ============================================================

# API key — obrigatoria para operacoes de embedding
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")

# Modelo default para embeddings de texto geral
VOYAGE_DEFAULT_MODEL = os.environ.get("VOYAGE_DEFAULT_MODEL", "voyage-4-lite")

# Modelo para embeddings financeiros
VOYAGE_FINANCE_MODEL = os.environ.get("VOYAGE_FINANCE_MODEL", "voyage-finance-2")

# Modelo para reranking
VOYAGE_RERANK_MODEL = os.environ.get("VOYAGE_RERANK_MODEL", "rerank-2.5-lite")

# Dimensoes do embedding (default 1024 para voyage-4-lite)
# Suporta Matryoshka: 256, 512, 1024, 2048
VOYAGE_EMBEDDING_DIMENSIONS = int(os.environ.get("VOYAGE_EMBEDDING_DIMENSIONS", "1024"))

# ============================================================
# BATCH SETTINGS
# ============================================================

# Maximo de textos por chamada de embedding (Voyage AI limit = 128)
EMBEDDING_BATCH_SIZE = int(os.environ.get("EMBEDDING_BATCH_SIZE", "128"))

# Maximo de tokens por chamada (varia por modelo, 320K para voyage-4-lite)
EMBEDDING_MAX_TOKENS_PER_BATCH = int(os.environ.get("EMBEDDING_MAX_TOKENS_PER_BATCH", "320000"))

# ============================================================
# SEARCH SETTINGS
# ============================================================

# Numero default de resultados na busca semantica
SEARCH_DEFAULT_LIMIT = int(os.environ.get("SEARCH_DEFAULT_LIMIT", "10"))

# Score minimo de similaridade (cosine) para considerar match
SEARCH_MIN_SIMILARITY = float(os.environ.get("SEARCH_MIN_SIMILARITY", "0.3"))

# Top-K para reranking (candidatos antes do rerank)
RERANK_CANDIDATES = int(os.environ.get("RERANK_CANDIDATES", "50"))

# Top-K apos reranking
RERANK_TOP_K = int(os.environ.get("RERANK_TOP_K", "10"))

# ============================================================
# FEATURE FLAGS
# ============================================================

# Habilita busca semantica (False = fallback para regex)
EMBEDDINGS_ENABLED = os.environ.get("EMBEDDINGS_ENABLED", "true").lower() == "true"

# Habilita reranking apos busca semantica
RERANKING_ENABLED = os.environ.get("RERANKING_ENABLED", "false").lower() == "true"

# Habilita busca semantica de produtos no AI Resolver (devolucoes)
# Quando True, substitui chamada Haiku de extracao de termos por busca por embeddings
PRODUCT_SEMANTIC_SEARCH = os.environ.get("PRODUCT_SEMANTIC_SEARCH", "true").lower() == "true"

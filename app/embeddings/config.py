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

# Score minimo de similaridade (cosine) — default global
SEARCH_MIN_SIMILARITY = float(os.environ.get("SEARCH_MIN_SIMILARITY", "0.3"))

# Thresholds por dominio (P1.2 — centralizados, com env var override)
# Documentacao: busca ampla, threshold baixo
THRESHOLD_SSW = float(os.environ.get("THRESHOLD_SSW", "0.30"))
# Produtos: sinonimia (COGUMELO ≈ CHAMPIGNON), precisa de margem
THRESHOLD_PRODUCT = float(os.environ.get("THRESHOLD_PRODUCT", "0.35"))
# Entidades financeiras: nomes truncados (MEZZANI ALIM → MEZZANI ALIMENTOS)
THRESHOLD_ENTITY = float(os.environ.get("THRESHOLD_ENTITY", "0.50"))
# Sessoes do agente: busca historica
THRESHOLD_SESSION = float(os.environ.get("THRESHOLD_SESSION", "0.40"))
# Memorias do agente: relevancia contextual
THRESHOLD_MEMORY = float(os.environ.get("THRESHOLD_MEMORY", "0.40"))
# SQL templates: few-shot precision alta
THRESHOLD_SQL_TEMPLATE = float(os.environ.get("THRESHOLD_SQL_TEMPLATE", "0.50"))
# Categorias de pagamento: classificacao por similaridade
THRESHOLD_PAYMENT_CATEGORY = float(os.environ.get("THRESHOLD_PAYMENT_CATEGORY", "0.50"))
# Motivos de devolucao: classificacao (votacao com consenso)
THRESHOLD_DEVOLUCAO = float(os.environ.get("THRESHOLD_DEVOLUCAO", "0.60"))
# Transportadoras: nome fuzzy
THRESHOLD_CARRIER = float(os.environ.get("THRESHOLD_CARRIER", "0.40"))

# Top-K para reranking (candidatos antes do rerank)
RERANK_CANDIDATES = int(os.environ.get("RERANK_CANDIDATES", "50"))

# Top-K apos reranking
RERANK_TOP_K = int(os.environ.get("RERANK_TOP_K", "10"))

# ============================================================
# FEATURE FLAGS
# ============================================================

# Habilita busca semantica (False = fallback para regex)
EMBEDDINGS_ENABLED = os.environ.get("EMBEDDINGS_ENABLED", "true").lower() == "true"

# Habilita reranking apos busca semantica (Voyage AI rerank-2.5-lite)
# DESABILITADO por default: adiciona ~2s latencia + ~$0.01/100 docs.
# Implementacao completa em service.py._rerank_results() — pronta para ativar
# quando o trade-off latencia/custo for aceitavel.
RERANKING_ENABLED = os.environ.get("RERANKING_ENABLED", "false").lower() == "true"

# Habilita busca semantica de produtos no AI Resolver (devolucoes)
# Quando True, substitui chamada Haiku de extracao de termos por busca por embeddings
PRODUCT_SEMANTIC_SEARCH = os.environ.get("PRODUCT_SEMANTIC_SEARCH", "true").lower() == "true"

# Habilita busca semantica de entidades financeiras (fornecedores/clientes)
# Quando True, FavorecidoResolverService e ExtratoMatchingService usam embeddings
# como complemento a tokenizacao ILIKE para nomes truncados/abreviados
FINANCIAL_SEMANTIC_SEARCH = os.environ.get("FINANCIAL_SEMANTIC_SEARCH", "true").lower() == "true"

# Habilita busca semantica em sessoes do agente
# Consumers: session_search_tool.py (semantic_search_sessions), routes.py (on-save trigger)
SESSION_SEMANTIC_SEARCH = os.environ.get("SESSION_SEMANTIC_SEARCH", "true").lower() == "true"

# Habilita busca semantica em memorias do agente
# Consumers: client.py (_load_user_memories_for_context), memory_mcp_tool.py (on-save trigger)
MEMORY_SEMANTIC_SEARCH = os.environ.get("MEMORY_SEMANTIC_SEARCH", "true").lower() == "true"

# Habilita retrieval de templates SQL para few-shot no text_to_sql
# Consumers: text_to_sql.py (template retrieval antes do Generator)
SQL_TEMPLATE_SEARCH = os.environ.get("SQL_TEMPLATE_SEARCH", "true").lower() == "true"

# Habilita classificacao semantica de categorias de pagamento
# Consumers: favorecido_resolver_service.py (fallback apos regex no Layer 5)
PAYMENT_CATEGORY_SEMANTIC = os.environ.get("PAYMENT_CATEGORY_SEMANTIC", "true").lower() == "true"

# Habilita classificacao de motivos de devolucao por similaridade
# Consumers: ai_resolver_service.py (substitui/complementa chamada Haiku)
DEVOLUCAO_REASON_SEMANTIC = os.environ.get("DEVOLUCAO_REASON_SEMANTIC", "true").lower() == "true"

# Habilita busca semantica de transportadoras por nome
# Consumers: carrier_search.py, resolver_transportadora.py
CARRIER_SEMANTIC_SEARCH = os.environ.get("CARRIER_SEMANTIC_SEARCH", "true").lower() == "true"

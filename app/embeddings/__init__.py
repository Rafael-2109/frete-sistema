"""
Modulo de Embeddings — Busca Semantica via Voyage AI + pgvector.

Fornece:
- client.py: Singleton do Voyage AI client
- service.py: API de alto nivel (embed, search, rerank)
- models.py: Modelos SQLAlchemy com colunas vector (pgvector)
- config.py: Configuracao centralizada
- indexers/: Scripts de indexacao por dominio (SSW, produtos, etc.)
"""

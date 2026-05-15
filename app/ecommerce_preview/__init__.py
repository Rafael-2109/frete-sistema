"""
E-commerce Preview — serve XEROX local do site Motochefe Maringa via Flask.

Modulo TEMPORARIO: existe apenas enquanto a migracao para Bagy esta em andamento.
Pode ser removido apos o cutover.

Origem dos arquivos: scripts/ecommerce/mirror/ (gerado por xerox_site.sh).
NAO esta versionado no git (ver .gitignore).

Endpoint: /ecommerce-preview/
Acesso: requer login (qualquer usuario autenticado).
"""

from app.ecommerce_preview.routes import ecommerce_preview_bp  # noqa: F401

__all__ = ["ecommerce_preview_bp"]

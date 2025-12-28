"""
Rotas do modulo de Custeio
"""
from app.custeio.routes.custeio_routes import register_custeio_routes


def register_routes(bp):
    """Registra todas as rotas do modulo"""
    register_custeio_routes(bp)

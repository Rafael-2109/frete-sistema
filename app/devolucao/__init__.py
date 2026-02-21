"""
Modulo de Gestao de Devolucoes

Sistema completo para gerenciar devolucoes de mercadorias:
- Registro de NFD pelo monitoramento
- Tratativas Comercial/Logistica
- Cotacao de frete de retorno
- Importacao de NFD do Odoo (DFe finnfe=4)
- De-Para de produtos por prefixo CNPJ
- Contagem e inspecao de mercadorias
- Lancamento no Odoo

Criado em: 30/12/2024
"""
from flask import Blueprint

# Blueprint principal do modulo
devolucao_bp = Blueprint('devolucao', __name__, url_prefix='/devolucao')

# Registrar sub-blueprints
from app.devolucao.routes.registro_routes import registro_bp  # noqa: E402
from app.devolucao.routes.ocorrencia_routes import ocorrencia_bp  # noqa: E402
from app.devolucao.routes.vinculacao_routes import vinculacao_bp  # noqa: E402
from app.devolucao.routes.ai_routes import ai_bp  # noqa: E402
from app.devolucao.routes.frete_routes import frete_bp  # noqa: E402
from app.devolucao.routes.cadastro_routes import cadastro_bp  # noqa: E402

devolucao_bp.register_blueprint(registro_bp)
devolucao_bp.register_blueprint(ocorrencia_bp)
devolucao_bp.register_blueprint(vinculacao_bp)
devolucao_bp.register_blueprint(ai_bp)
devolucao_bp.register_blueprint(frete_bp)
devolucao_bp.register_blueprint(cadastro_bp)


def init_app(app):
    """Registra o blueprint no aplicativo Flask"""
    app.register_blueprint(devolucao_bp)

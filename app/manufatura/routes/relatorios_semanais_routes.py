"""
Rotas dos Relatórios Semanais de Manufatura.

Página (hub de manufatura) + endpoint de geração que devolve um .zip com os
3 relatórios (.xlsx) num único clique. Geração síncrona (gunicorn-sistema
timeout=1800s; o serviço retorna bytes e pode migrar para RQ sem refatorar).
"""
import logging

from flask import Blueprint, render_template, make_response, jsonify
from flask_login import login_required

from app.utils.timezone import agora_utc_naive
from app.manufatura.services.relatorios_semanais_service import (
    RelatoriosSemanaisService,
)

logger = logging.getLogger(__name__)

relatorios_semanais_bp = Blueprint(
    "relatorios_semanais",
    __name__,
    url_prefix="/manufatura/relatorios-semanais",
)


@relatorios_semanais_bp.route("/")
@login_required
def index():
    """Página com o botão de geração dos 3 relatórios."""
    return render_template("manufatura/relatorios_semanais/index.html")


@relatorios_semanais_bp.route("/gerar")
@login_required
def gerar():
    """Gera os 3 relatórios e devolve um .zip para download."""
    try:
        conteudo = RelatoriosSemanaisService.gerar_zip()
        data = agora_utc_naive().date().strftime("%Y%m%d")
        response = make_response(conteudo)
        response.headers["Content-Type"] = "application/zip"
        response.headers["Content-Disposition"] = (
            f"attachment; filename=relatorios_semanais_manufatura_{data}.zip"
        )
        # Não cachear: cada clique deve regenerar com dados frescos.
        response.headers["Cache-Control"] = "no-store"
        return response
    except Exception as e:  # noqa: BLE001 — superfície única; loga e responde JSON
        logger.exception("Erro ao gerar relatórios semanais de manufatura")
        return jsonify({"sucesso": False, "erro": str(e)}), 500

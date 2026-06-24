# -*- coding: utf-8 -*-
"""
Rotas do Validador de Titulos x Bancos.

Tela onde o operador sobe as bases dos 4 bancos (SRM, GRAFENO, AGIS, VORTX) e o
Contas a Pagar (aba CP-NACOM, para recompras). O faturamento vem do sistema
(contas_a_receber). Gera os 3 comparativos na tela e em Excel:

1. Titulos em mais de um banco (com validacao de recompra no CP)
2. Notas faturadas sem boleto
3. Boletos sem nota faturada

Blueprint: financeiro_bp (prefix /financeiro) -> /financeiro/validador-titulos/
"""

import os
import time
import uuid

from flask import (
    render_template, request, send_file, flash, redirect, url_for, abort,
)
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.financeiro.routes import financeiro_bp, UPLOAD_FOLDER
from app.financeiro.services.validador_titulos.parsers_bancos import BANCOS_SUPORTADOS
from app.financeiro.services.validador_titulos.service import processar_validacao
from app.financeiro.services.validador_titulos.exportador import gerar_excel

# Pasta para os arquivos temporarios desta tela (uploads + Excel gerado)
_PASTA_TMP = os.path.join(UPLOAD_FOLDER, "validador_titulos")
os.makedirs(_PASTA_TMP, exist_ok=True)

# Tempo de vida dos arquivos temporarios (24h)
_TTL_SEGUNDOS = 24 * 60 * 60


def _limpar_temporarios_antigos():
    """Remove arquivos temporarios com mais de 24h (housekeeping best-effort)."""
    try:
        agora = time.time()
        for nome in os.listdir(_PASTA_TMP):
            caminho = os.path.join(_PASTA_TMP, nome)
            if os.path.isfile(caminho) and agora - os.path.getmtime(caminho) > _TTL_SEGUNDOS:
                os.remove(caminho)
    except OSError:
        pass


@financeiro_bp.route("/validador-titulos/", methods=["GET"])
@login_required
def validador_titulos():
    """Tela inicial: formulario de upload das bases."""
    return render_template(
        "financeiro/validador_titulos.html",
        bancos=BANCOS_SUPORTADOS,
        resultado=None,
    )


@financeiro_bp.route("/validador-titulos/processar", methods=["POST"])
@login_required
def validador_titulos_processar():
    """Recebe os uploads, roda os comparativos e mostra o resultado."""
    _limpar_temporarios_antigos()

    caminhos_bancos = {}
    arquivos_salvos = []

    # Bases dos bancos (campos arquivo_SRM, arquivo_GRAFENO, ...)
    for banco in BANCOS_SUPORTADOS:
        arquivo = request.files.get(f"arquivo_{banco}")
        if arquivo and arquivo.filename:
            caminho = _salvar_upload(arquivo)
            caminhos_bancos[banco] = caminho
            arquivos_salvos.append(caminho)

    if not caminhos_bancos:
        flash("Envie pelo menos a base de um banco.", "warning")
        return redirect(url_for("financeiro.validador_titulos"))

    # Contas a pagar (opcional, para validar recompra)
    caminho_cp = None
    arquivo_cp = request.files.get("arquivo_CP")
    if arquivo_cp and arquivo_cp.filename:
        caminho_cp = _salvar_upload(arquivo_cp)
        arquivos_salvos.append(caminho_cp)

    try:
        rv = processar_validacao(caminhos_bancos, caminho_cp)
    finally:
        # uploads ja foram lidos; nao precisamos mante-los
        for caminho in arquivos_salvos:
            _remover_silencioso(caminho)

    # Gera o Excel e guarda para download por token
    token = uuid.uuid4().hex
    caminho_excel = os.path.join(_PASTA_TMP, f"resultado_{token}.xlsx")
    with open(caminho_excel, "wb") as f:
        f.write(gerar_excel(rv).getvalue())

    if not caminho_cp:
        flash("Contas a Pagar nao enviado — a validacao de recompra ficou de fora.", "info")
    for banco, erro in rv.erros.items():
        flash(f"Falha ao ler {banco}: {erro}", "danger")

    return render_template(
        "financeiro/validador_titulos.html",
        bancos=BANCOS_SUPORTADOS,
        resultado=rv,
        token_download=token,
    )


@financeiro_bp.route("/validador-titulos/download/<token>", methods=["GET"])
@login_required
def validador_titulos_download(token):
    """Baixa o Excel gerado no ultimo processamento (por token)."""
    nome = secure_filename(f"resultado_{token}.xlsx")
    caminho = os.path.join(_PASTA_TMP, nome)
    if not os.path.isfile(caminho):
        abort(404)
    return send_file(
        caminho,
        as_attachment=True,
        download_name="validador_titulos_bancos.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _salvar_upload(arquivo):
    """Salva um upload com nome unico e devolve o caminho."""
    nome = secure_filename(arquivo.filename) or "upload"
    caminho = os.path.join(_PASTA_TMP, f"{uuid.uuid4().hex}_{nome}")
    arquivo.save(caminho)
    return caminho


def _remover_silencioso(caminho):
    try:
        os.remove(caminho)
    except OSError:
        pass

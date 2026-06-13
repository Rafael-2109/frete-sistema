"""
Conversor de Extrato SRM Bank (PDF -> OFX) — utilitario do Hub Financeiro.

Recebe um ou mais extratos do SRM Bank em PDF (que NAO possuem FITID) e devolve
arquivos OFX prontos para importacao nativa no Odoo, com FITID sintetico
deterministico (dedup via unique_import_id). Stateless: nada e' gravado em banco
nem em disco — o PDF e' lido em memoria e o OFX volta em base64 no JSON para
download no cliente.

Rotas:
- GET  /financeiro/conversor-srm            -> tela de upload
- POST /financeiro/conversor-srm/converter  -> processa (AJAX), devolve relatorio
"""
import base64
import io
import os
from decimal import Decimal

from flask import render_template, request, jsonify
from flask_login import login_required

from app.financeiro.routes import financeiro_bp
from app.financeiro.routes.dashboard import requires_financeiro
from app.financeiro.services.extrato_pdf_srm_service import (
    parse_pdf, validar, gerar_ofx, analisar_continuidade,
)

# Limites defensivos do endpoint
MAX_ARQUIVOS = 24
MAX_BYTES_POR_ARQUIVO = 20 * 1024 * 1024  # 20 MB por PDF (extratos reais ~80 KB)


def _dec_str(valor):
    """Decimal -> str com 2 casas (ou None). Normaliza -0,00 -> 0.00."""
    if valor is None:
        return None
    if valor == 0:
        valor = Decimal('0')
    return f'{valor:.2f}'


def _resumo_json(resumo):
    """Converte Decimals do resumo em strings para serializar."""
    if not resumo:
        return {}
    out = dict(resumo)
    for campo in ('saldo_anterior', 'saldo_final', 'creditos', 'debitos'):
        if campo in out:
            out[campo] = _dec_str(out[campo])
    return out


@financeiro_bp.route('/conversor-srm')
@login_required
@requires_financeiro
def conversor_srm():
    """Tela do conversor de extrato SRM (PDF -> OFX)."""
    return render_template('financeiro/conversor_srm.html')


@financeiro_bp.route('/conversor-srm/converter', methods=['POST'])
@login_required
@requires_financeiro
def conversor_srm_converter():
    """
    Recebe PDFs (campo 'arquivos'), valida e converte cada um para OFX.

    Resposta JSON:
        {
          "arquivos": [
             {"nome", "ok", "resumo", "erros": [], "warnings": [],
              "ofx_nome", "ofx_base64"}  # ofx_* so quando ok=True
          ],
          "continuidade": [
             {"de", "para", "fim", "ini", "continuo", "gap"}  # so entre validos
          ]
        }
    """
    arquivos = request.files.getlist('arquivos')
    arquivos = [a for a in arquivos if a and a.filename]
    if not arquivos:
        return jsonify({'erro': 'Nenhum arquivo enviado.'}), 400
    if len(arquivos) > MAX_ARQUIVOS:
        return jsonify({'erro': f'Maximo de {MAX_ARQUIVOS} arquivos por vez.'}), 400

    resultados = []
    validos = []  # parsed dicts dos arquivos integros (para continuidade)

    for arquivo in arquivos:
        nome = arquivo.filename
        if not nome.lower().endswith('.pdf'):
            resultados.append({
                'nome': nome, 'ok': False, 'resumo': {},
                'erros': ['Arquivo nao e PDF (.pdf).'], 'warnings': [],
            })
            continue

        conteudo = arquivo.read()
        if not conteudo:
            resultados.append({
                'nome': nome, 'ok': False, 'resumo': {},
                'erros': ['Arquivo vazio.'], 'warnings': [],
            })
            continue
        if len(conteudo) > MAX_BYTES_POR_ARQUIVO:
            resultados.append({
                'nome': nome, 'ok': False, 'resumo': {},
                'erros': [f'Arquivo excede {MAX_BYTES_POR_ARQUIVO // (1024 * 1024)} MB.'],
                'warnings': [],
            })
            continue

        try:
            parsed = parse_pdf(io.BytesIO(conteudo), nome=nome)
            ok, erros, warnings, resumo = validar(parsed)
        except Exception as exc:  # noqa: BLE001 — qualquer falha vira erro do arquivo
            resultados.append({
                'nome': nome, 'ok': False, 'resumo': {},
                'erros': [f'Falha ao ler o PDF: {exc}'], 'warnings': [],
            })
            continue

        item = {
            'nome': nome, 'ok': ok, 'resumo': _resumo_json(resumo),
            'erros': erros, 'warnings': warnings,
        }
        if ok:
            ofx = gerar_ofx(parsed)
            base = os.path.splitext(nome)[0]
            item['ofx_nome'] = base + '.ofx'
            item['ofx_base64'] = base64.b64encode(
                ofx.encode('latin-1')).decode('ascii')
            validos.append(parsed)
        resultados.append(item)

    # Continuidade entre os arquivos validos (saldo final -> SALDO ANTERIOR)
    continuidade = []
    if len(validos) > 1:
        for c in analisar_continuidade(validos):
            continuidade.append({
                'de': c['de'], 'para': c['para'],
                'fim': _dec_str(c['fim']), 'ini': _dec_str(c['ini']),
                'continuo': c['continuo'], 'gap': _dec_str(c['gap']),
            })

    return jsonify({'arquivos': resultados, 'continuidade': continuidade})

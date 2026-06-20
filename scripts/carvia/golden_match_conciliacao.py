# -*- coding: utf-8 -*-
"""
GOLDEN TEST do motor de match da conciliacao CarVia (ferramenta de regressao).
================================================================================

Mede a qualidade do ranking de sugestao de match (`carvia_sugestao_service`)
contra o GROUND-TRUTH de conciliacoes ja feitas, rodando o ALGORITMO REAL e
medindo em que POSICAO (rank) o documento correto aparece. Serve para validar
mudancas no motor ANTES de deploy (measurement-first).

Compara a formula de VALOR ANTIGA (pre-2026-06-19, divergencia>30% -> ~0) com a
ATUAL importada do codigo (cobertura: agrupado nao penaliza). Resultado de
referencia (286 conciliacoes fatura_cliente, 2026-06-19):

    VERSAO        top1%   top3%   ALTO%  NENHUM%  rank_med
    V0_ANTIGA     48.3%   57.7%   53.1%    14.0%       2.0
    ATUAL_COBERT  47.9%   64.0%   53.1%     2.8%       2.0   <- top3 +6.3pp, sem-label 14->2.8%

--------------------------------------------------------------------------------
COMO GERAR OS DATASETS (dados de PRODUCAO via MCP Render — ver INFRAESTRUTURA.md;
postgresId=dpg-d13m38vfte5s738t6p50-a). Salve a saida de cada query (json_agg)
em DATA_DIR (default /tmp/subagent-findings/):

  carvia_match_groundtruth.json  (286 pares linha<->fatura conciliados):
    SELECT json_agg(t) FROM (
      SELECT c.documento_id AS doc_id, l.id AS lid,
             left(coalesce(l.descricao,''),200) AS descricao,
             left(coalesce(l.memo,''),200) AS memo, l.razao_social,
             ABS(l.valor)::float AS valor, to_char(l.data,'YYYY-MM-DD') AS data
      FROM carvia_conciliacoes c
      JOIN carvia_extrato_linhas l ON l.id=c.extrato_linha_id
      WHERE c.tipo_documento='fatura_cliente') t;

  carvia_match_faturas.json  (faturas candidatas, nao-canceladas):
    SELECT json_agg(t) FROM (
      SELECT id, valor_total::float AS valor_total,
             to_char(vencimento,'DD/MM/YYYY') AS vencimento,
             to_char(data_emissao,'DD/MM/YYYY') AS data_emissao_br,
             to_char(data_emissao,'YYYY-MM-DD') AS data_emissao_iso,
             nome_cliente, cnpj_cliente
      FROM carvia_faturas_cliente WHERE status != 'CANCELADA') t;

RODAR:  PYTHONPATH=. python scripts/carvia/golden_match_conciliacao.py
"""
import json
import os
import re
import types
from datetime import date, timedelta

from app.carvia.services.financeiro.carvia_sugestao_service import (
    _score_valor, _score_data, _score_nome,
    extrair_nome_pagador, extrair_cnpjs_da_descricao,
    extrair_raizes_cnpj_da_descricao, SCORE_NEUTRO,
)

DATA_DIR = os.environ.get("CARVIA_GOLDEN_DIR", "/tmp/subagent-findings")
JANELA_ANTES, JANELA_DEPOIS = 90, 30


def _load(name):
    with open(os.path.join(DATA_DIR, name)) as fh:
        return json.load(fh)


def score_valor_antigo(valor_extrato, saldo_doc):
    """Formula PRE-2026-06-19 (referencia de regressao)."""
    if valor_extrato <= 0 or saldo_doc <= 0:
        return SCORE_NEUTRO
    maior = max(valor_extrato, saldo_doc)
    diff = abs(valor_extrato - saldo_doc) / maior
    if diff < 0.001:
        return 1.0
    if diff <= 0.01:
        return 0.95
    if diff <= 0.05:
        return 0.80
    if diff <= 0.15:
        return 0.50
    if diff <= 0.30:
        return 0.25
    return max(0.0, 0.15 - diff * 0.1)


def parse_iso(s):
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def texto_extrato_de(linha):
    if linha.razao_social:
        return linha.razao_social
    return (extrair_nome_pagador(linha.descricao or linha.memo or "")
            or linha.descricao or linha.memo or "")


def cnpj_floor(linha, doc, score):
    """Mesmo sinal deterministico do motor (CNPJ completo 0.95 / raiz 0.80)."""
    txt = ((linha.descricao or "") + " " + (linha.memo or "")
           + " " + (linha.razao_social or ""))
    cnpjs = extrair_cnpjs_da_descricao(txt)
    raizes = extrair_raizes_cnpj_da_descricao(txt)
    cd = re.sub(r"\D", "", doc.get("cnpj_cliente") or "")
    if cd:
        if cd in cnpjs:
            return max(score, 0.95)
        if cd[:8] in raizes:
            return max(score, 0.80)
    return score


def label_de(s):
    if s >= 0.80:
        return "ALTO"
    if s >= 0.55:
        return "MEDIO"
    if s >= 0.30:
        return "BAIXO"
    return None


def score(linha, doc, valor_fn):
    sv = valor_fn(abs(float(linha.valor or 0)), float(doc.get("saldo", 0)))
    sd = _score_data(linha.data, doc.get("vencimento", ""), doc.get("data", ""))
    sn = _score_nome(texto_extrato_de(linha), doc.get("nome", ""))
    return cnpj_floor(linha, doc, sv * 0.50 + sd * 0.30 + sn * 0.20)


def median(xs):
    xs = sorted(xs)
    m = len(xs)
    if not m:
        return 0
    return xs[m // 2] if m % 2 else (xs[m // 2 - 1] + xs[m // 2]) / 2


def main():
    gt = _load("carvia_match_groundtruth.json")
    fat = _load("carvia_match_faturas.json")
    docs_all = [{
        "id": f["id"], "saldo": f["valor_total"], "vencimento": f["vencimento"],
        "data": f["data_emissao_br"], "nome": f["nome_cliente"] or "",
        "cnpj_cliente": f["cnpj_cliente"] or "", "_iso": f["data_emissao_iso"],
    } for f in fat]
    by_id = {d["id"]: d for d in docs_all}

    versoes = {"V0_ANTIGA": score_valor_antigo, "ATUAL_COBERT": _score_valor}
    stats = {v: {"top1": 0, "top3": 0, "alto": 0, "nenhum": 0, "ranks": []}
             for v in versoes}
    n = 0
    for g in gt:
        doc_id = g["doc_id"]
        linha = types.SimpleNamespace(
            valor=g["valor"], data=parse_iso(g["data"]),
            descricao=g["descricao"], memo=g["memo"],
            razao_social=g["razao_social"])
        lo, hi = linha.data - timedelta(days=JANELA_ANTES), linha.data + timedelta(days=JANELA_DEPOIS)
        ids = {d["id"] for d in docs_all if lo <= parse_iso(d["_iso"]) <= hi}
        ids.add(doc_id)
        cands = [by_id[i] for i in ids]
        n += 1
        for vname, vfn in versoes.items():
            scored = sorted(((d["id"], score(linha, d, vfn)) for d in cands),
                            key=lambda x: x[1], reverse=True)
            rank = next(i for i, (did, _) in enumerate(scored, 1) if did == doc_id)
            sc = next(s for did, s in scored if did == doc_id)
            st = stats[vname]
            st["ranks"].append(rank)
            if rank == 1:
                st["top1"] += 1
            if rank <= 3:
                st["top3"] += 1
            lab = label_de(sc)
            if lab == "ALTO":
                st["alto"] += 1
            if lab is None:
                st["nenhum"] += 1

    hdr = f"{'VERSAO':<14} {'top1%':>7} {'top3%':>7} {'ALTO%':>7} {'NENHUM%':>8} {'rank_med':>9}"
    print(f"N={n}\n")
    print(hdr)
    print("-" * len(hdr))
    for v in versoes:
        s = stats[v]
        print(f"{v:<14} {100*s['top1']/n:>6.1f}% {100*s['top3']/n:>6.1f}% "
              f"{100*s['alto']/n:>6.1f}% {100*s['nenhum']/n:>7.1f}% {median(s['ranks']):>9.1f}")


if __name__ == "__main__":
    main()

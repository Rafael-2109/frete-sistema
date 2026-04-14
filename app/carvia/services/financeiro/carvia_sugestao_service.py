# -*- coding: utf-8 -*-
"""
Motor de Sugestao de Match — Conciliacao CarVia
================================================

Scoring puro (sem acesso DB) para ranquear documentos elegiveis
em relacao a uma linha do extrato bancario.

3 sinais ponderados:
  - VALOR (peso 0.50): diferenca percentual abs(extrato) vs doc.saldo
  - DATA  (peso 0.30): proximidade extrato.data vs doc.vencimento/data
  - NOME  (peso 0.20): jaccard tokens normalizados (descricao vs nome)

Thresholds calibrados via analise de 71 conciliacoes existentes
(scripts/analise_padroes_conciliacao.py, 2026-04-03).

R17 (historico aprendido): quando `cnpjs_historico` e fornecido
(dict {cnpj: ocorrencias}), `pontuar_documentos` aplica boost
multiplicativo 1.4x no score dos documentos cujo cnpj_cliente aparece
no dict. Preserva calibracao dos 3 sinais — apenas potencializa docs
que ja foram conciliados antes para a mesma descricao de extrato.
"""

import re
import unicodedata
from datetime import date

# Pesos dos sinais
PESOS = {
    'valor': 0.50,
    'data': 0.30,
    'nome': 0.20,
}

# Score neutro quando campo nao disponivel (nao penaliza)
SCORE_NEUTRO = 0.3

# Stopwords juridicas/genericas BR (removidas na normalizacao)
_STOPWORDS = frozenset({
    'sa', 'ltda', 'me', 'eireli', 'epp', 'sas', 'ss',
    'de', 'da', 'do', 'das', 'dos', 'e', 'a', 'o', 'em',
    'por', 'para', 'com', 'ao', 'ou', 'no', 'na',
    'ind', 'com', 'transportes', 'servicos', 'comercio',
    'distribuicao', 'importacao', 'exportacao',
    'pix', 'recebido', 'transferencia', 'cp',
})


def pontuar_documentos(linha, docs, cnpjs_historico=None):
    """Pontua cada documento elegivel em relacao a uma linha do extrato.

    Args:
        linha: CarviaExtratoLinha (objeto SQLAlchemy)
        docs: list[dict] — retorno de obter_documentos_elegiveis()
        cnpjs_historico: dict[str, int]|None — {cnpj: ocorrencias} vindo de
            CarviaHistoricoMatchService.cnpjs_aprendidos(linha). Quando um
            doc tem cnpj_cliente presente no dict, aplica boost 1.4x no
            score final (cap em 1.0). Parametro opcional — callsites que
            nao informam mantem comportamento original pre-R17.

    Returns:
        list[dict] — mesma lista com campos adicionais:
            score (float 0-1), score_label (str|None),
            score_detalhes (dict com valor/data/nome),
            score_historico (bool), score_historico_ocorrencias (int),
            score_pre_boost (float, apenas se boost aplicado)
        Ordenada por score descrescente.
    """
    valor_extrato = abs(float(linha.valor or 0))
    data_extrato = linha.data  # date ou None
    texto_extrato = linha.razao_social or linha.descricao or linha.memo or ''

    cnpjs_historico = cnpjs_historico or {}

    for doc in docs:
        sv = _score_valor(valor_extrato, float(doc.get('saldo', 0)))
        sd = _score_data(data_extrato, doc.get('vencimento', ''), doc.get('data', ''))
        sn = _score_nome(texto_extrato, doc.get('nome', ''))

        score = (
            sv * PESOS['valor']
            + sd * PESOS['data']
            + sn * PESOS['nome']
        )

        # R17: boost por historico aprendido (padrao descricao+CNPJ)
        cnpj_doc = (doc.get('cnpj_cliente') or '').strip()
        ocorrencias_hist = cnpjs_historico.get(cnpj_doc, 0) if cnpj_doc else 0
        if ocorrencias_hist > 0:
            score_pre_boost = score
            # FIX M1: floor 0.30 garante que docs com CNPJ aprendido mas com
            # score base < 0.30 (sem match de valor/data/nome — PIX generico,
            # descricao pobre, valor parcial fora da margem) ainda atinjam
            # pelo menos BAIXO (>= 0.30 apos boost), ganhando a primeira
            # estrela visual. Sem floor, 0 * 1.4 = 0 e o historico seria
            # completamente inutil exatamente quando mais importa.
            # - score base 0.0 → max(0, 0.30)*1.4 = 0.42 → BAIXO
            # - score base 0.3 → max(0.3, 0.30)*1.4 = 0.42 → BAIXO (igual)
            # - score base 0.57 → max(0.57, 0.30)*1.4 = 0.798 → MEDIO
            # - score base 0.65 → max(0.65, 0.30)*1.4 = 0.91 → ALTO
            # Floor nao altera scores ja >= 0.30 (preserva calibracao).
            base_boost = max(score, 0.30)
            score = min(1.0, base_boost * 1.4)
            doc['score_historico'] = True
            doc['score_historico_ocorrencias'] = ocorrencias_hist
            doc['score_pre_boost'] = round(score_pre_boost, 4)
        else:
            doc['score_historico'] = False
            doc['score_historico_ocorrencias'] = 0

        # Label (thresholds aplicados APOS boost — boost pode mudar tier)
        if score >= 0.80:
            label = 'ALTO'
        elif score >= 0.55:
            label = 'MEDIO'
        elif score >= 0.30:
            label = 'BAIXO'
        else:
            label = None

        doc['score'] = round(score, 4)
        doc['score_label'] = label
        doc['score_detalhes'] = {
            'valor': round(sv, 4),
            'data': round(sd, 4),
            'nome': round(sn, 4),
        }

    docs.sort(key=lambda d: d.get('score', 0), reverse=True)
    return docs


def _score_valor(valor_extrato, saldo_doc):
    """Score de proximidade de valor (0.0 a 1.0).

    Calibrado: ~50% das conciliacoes existentes sao match exato (1:1).
    """
    if valor_extrato <= 0 or saldo_doc <= 0:
        return SCORE_NEUTRO

    maior = max(valor_extrato, saldo_doc)
    diff_pct = abs(valor_extrato - saldo_doc) / maior

    if diff_pct < 0.001:    # match exato (< 0.1%)
        return 1.0
    elif diff_pct <= 0.01:  # < 1%
        return 0.95
    elif diff_pct <= 0.05:  # < 5%
        return 0.80
    elif diff_pct <= 0.15:  # < 15%
        return 0.50
    elif diff_pct <= 0.30:  # < 30%
        return 0.25
    else:
        return max(0.0, 0.15 - diff_pct * 0.1)


def _score_data(data_extrato, vencimento_str, data_str):
    """Score de proximidade de data (0.0 a 1.0).

    Prioriza vencimento sobre data_emissao.
    Calibrado: +-7d cobre ~40%, +-15d ~60%, +-30d ~85%.
    """
    if not data_extrato:
        return SCORE_NEUTRO

    data_doc = _parse_data_br(vencimento_str) or _parse_data_br(data_str)
    if not data_doc:
        return SCORE_NEUTRO

    dias = abs((data_extrato - data_doc).days)

    if dias <= 3:
        return 1.0
    elif dias <= 7:
        return 0.80
    elif dias <= 15:
        return 0.60
    elif dias <= 30:
        return 0.40
    elif dias <= 60:
        return 0.20
    else:
        return 0.05


def _score_nome(texto_extrato, nome_doc):
    """Score de similaridade de nome por token overlap (Jaccard).

    Calibrado: funciona bem para pagador direto, neutro para terceiros.
    """
    tokens_ext = _normalizar(texto_extrato)
    tokens_doc = _normalizar(nome_doc)

    if not tokens_ext or not tokens_doc:
        return SCORE_NEUTRO

    intersecao = tokens_ext & tokens_doc
    uniao = tokens_ext | tokens_doc

    if not uniao:
        return SCORE_NEUTRO

    jaccard = len(intersecao) / len(uniao)

    # Boost: qualquer token em comum ja e um sinal positivo
    if intersecao:
        return min(1.0, jaccard * 2.0 + 0.3)
    else:
        return 0.0


def _normalizar(texto):
    """Normaliza texto para tokens comparaveis.

    Remove acentos, lowercase, pontuacao, stopwords juridicas.
    Retorna set de tokens.
    """
    if not texto:
        return set()

    # NFKD strip accents
    nfkd = unicodedata.normalize('NFKD', texto.lower())
    ascii_str = ''.join(c for c in nfkd if not unicodedata.combining(c))

    # Remove pontuacao, manter alfanumerico + espacos
    limpo = re.sub(r'[^a-z0-9\s]', ' ', ascii_str)

    # Tokenize + filtrar
    tokens = {
        t for t in limpo.split()
        if len(t) > 2 and t not in _STOPWORDS
    }
    return tokens


def _parse_data_br(data_str):
    """Parse data DD/MM/YYYY para date. Retorna None se invalida."""
    if not data_str or not isinstance(data_str, str):
        return None

    parts = data_str.strip().split('/')
    if len(parts) != 3:
        return None

    try:
        return date(int(parts[2]), int(parts[1]), int(parts[0]))
    except (ValueError, IndexError):
        return None

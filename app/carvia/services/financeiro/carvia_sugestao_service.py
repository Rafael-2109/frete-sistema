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
            score_pre_boost (float, apenas se boost aplicado),
            score_cnpj_direto (bool) — True se CNPJ literal da descricao
              bate com o CNPJ do doc (sinal deterministico).
        Ordenada por score descrescente.
    """
    valor_extrato = abs(float(linha.valor or 0))
    data_extrato = linha.data  # date ou None
    # REFINO 2026-04-19: priorizar razao_social se setada; senao extrair
    # nome do pagador do prefixo " - " antes de "Pix recebido"/"Transferencia"/etc.
    # Analise de 178 linhas OFX reais: 100% seguem esse padrao.
    if linha.razao_social:
        texto_extrato = linha.razao_social
    else:
        texto_extrato = (
            extrair_nome_pagador(linha.descricao or linha.memo or '')
            or linha.descricao or linha.memo or ''
        )
    # REFINO 2026-04-20: extracao deterministica de CNPJ/raizes da descricao
    # completa (nao so do prefixo — "Cp :08561701" tem a raiz 08561701).
    texto_completo = (
        (linha.descricao or '') + ' ' + (linha.memo or '')
        + ' ' + (linha.razao_social or '')
    )
    cnpjs_extraidos = extrair_cnpjs_da_descricao(texto_completo)
    raizes_extraidas = extrair_raizes_cnpj_da_descricao(texto_completo)

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

        # REFINO 2026-04-20: sinal DETERMINISTICO de CNPJ direto na descricao
        # Prioridade ABSOLUTA se casar — score minimo 0.95 (quase match).
        # Compara contra ambos os campos (cnpj_cliente e cnpj_transportadora
        # quando presentes no doc, para cobrir fatura_transportadora).
        cnpj_doc = (doc.get('cnpj_cliente') or doc.get('cnpj_transportadora') or '').strip()
        cnpj_doc_limpo = re.sub(r'\D', '', cnpj_doc) if cnpj_doc else ''
        cnpj_match_direto = False
        raiz_match_direto = False
        if cnpj_doc_limpo:
            if cnpj_doc_limpo in cnpjs_extraidos:
                cnpj_match_direto = True
            elif cnpj_doc_limpo[:8] in raizes_extraidas:
                raiz_match_direto = True

        if cnpj_match_direto:
            # Match exato de CNPJ — score minimo 0.95 (supera boost historico)
            doc['score_cnpj_direto'] = True
            doc['score_cnpj_direto_tipo'] = 'CNPJ_COMPLETO'
            score = max(score, 0.95)
        elif raiz_match_direto:
            # Raiz de CNPJ (8 primeiros digitos) — score minimo 0.80
            doc['score_cnpj_direto'] = True
            doc['score_cnpj_direto_tipo'] = 'RAIZ_CNPJ'
            score = max(score, 0.80)
        else:
            doc['score_cnpj_direto'] = False

        # R17: boost por historico aprendido (padrao descricao+CNPJ)
        ocorrencias_hist = cnpjs_historico.get(cnpj_doc, 0) if cnpj_doc else 0
        if ocorrencias_hist > 0:
            score_pre_boost = score
            # REFINO 2026-04-19: BOOST ADAPTATIVO por volume de evidencia.
            # Antes: fator fixo 1.4x (ate com 1 unica ocorrencia no historico).
            # Problema real: base com apenas 16 eventos globais e 3 descricoes
            # com CNPJs ambiguos — boost 1.4x era agressivo demais com pouca
            # massa critica.
            # Agora: fator = 1 + min(0.4, ocorrencias * 0.15)
            #   1 ocorrencia  -> 1.15x (cautela)
            #   2 ocorrencias -> 1.30x
            #   3 ocorrencias -> 1.45x (cap em 1.40x via min)
            # Preserva semantica: historico confirma, mas nao atropela sinais
            # de valor/data/nome quando evidencia e rasa.
            fator_boost = 1.0 + min(0.4, ocorrencias_hist * 0.15)
            # Floor 0.30 preservado (garante tier BAIXO em descricoes pobres
            # mas com historico).
            base_boost = max(score, 0.30)
            score = min(1.0, base_boost * fator_boost)
            doc['score_historico'] = True
            doc['score_historico_ocorrencias'] = ocorrencias_hist
            doc['score_historico_fator'] = round(fator_boost, 3)
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

    REFINO 2026-04-19 (baseado em analise de 178 linhas reais OFX):
    - Filtra tokens NUMERICOS com 5+ digitos (IDs transacionais: "474055892",
      "08561701"). Numeros curtos (< 5 digitos) como "2026" ainda vazam,
      mas sao raros o suficiente e podem ser uteis em contextos de numero
      de fatura curto.
    """
    if not texto:
        return set()

    # NFKD strip accents
    nfkd = unicodedata.normalize('NFKD', texto.lower())
    ascii_str = ''.join(c for c in nfkd if not unicodedata.combining(c))

    # Remove pontuacao, manter alfanumerico + espacos
    limpo = re.sub(r'[^a-z0-9\s]', ' ', ascii_str)

    # Tokenize + filtrar
    # - descartar tokens com <= 2 chars
    # - descartar stopwords
    # - descartar IDs transacionais (numero puro com 5+ digitos)
    tokens = set()
    for t in limpo.split():
        if len(t) <= 2:
            continue
        if t in _STOPWORDS:
            continue
        if t.isdigit() and len(t) >= 5:
            continue  # ID transacional, nao semantica
        tokens.add(t)
    return tokens


# REFINO 2026-04-20: regex para CNPJ literal na descricao.
# Formatos aceitos:
#   - 14 digitos contiguos (ex: "18467441000123")
#   - Formatado (ex: "18.467.441/0001-23")
# Nao captura sequencias gigantes (>14 digitos) — limita com lookarounds.
_RE_CNPJ_FORMATADO = re.compile(
    r'(?<!\d)(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})(?!\d)'
)
_RE_CNPJ_14_DIGITOS = re.compile(r'(?<!\d)(\d{14})(?!\d)')
# Raiz de CNPJ: 8 digitos isolados (padrao "Cp :08561701-..." visto em OFX).
# Requer nao-digito antes (ou inicio) E depois (para nao pegar metade de ID).
_RE_RAIZ_CNPJ_8 = re.compile(r'(?<!\d)(\d{8})(?!\d)')


def extrair_cnpjs_da_descricao(texto):
    """Extrai CNPJs completos (14 digitos) da descricao.

    REFINO 2026-04-20: quando extrato traz CNPJ literal (raro mas
    determinante), devemos usar DIRETO em vez de depender de scoring
    fuzzy de nome. CNPJ unico na base = match garantido.

    Args:
        texto: str — descricao completa (descricao + memo + razao_social)

    Returns:
        set[str] — CNPJs normalizados (apenas digitos, 14 chars).
    """
    if not texto:
        return set()
    cnpjs = set()
    # Formatado (prioritario, mais confiavel — separadores cerram dupla
    # leitura de outros IDs numericos)
    for m in _RE_CNPJ_FORMATADO.finditer(texto):
        cnpjs.add(re.sub(r'\D', '', m.group(1)))
    # 14 digitos puros — pode dar falso positivo com IDs contabeis longos,
    # mas limitado a 14 reduz ruido.
    for m in _RE_CNPJ_14_DIGITOS.finditer(texto):
        cnpjs.add(m.group(1))
    return cnpjs


def extrair_raizes_cnpj_da_descricao(texto):
    """Extrai raizes de CNPJ (8 digitos) da descricao.

    OFX de PIX frequentemente vem com padrao "Cp :08561701-..." onde
    08561701 e a RAIZ do CNPJ do pagador (8 primeiros digitos).
    Analise real: 147/178 linhas reais (82%) tem padrao "Cp :".

    Args:
        texto: str

    Returns:
        set[str] — raizes (8 digitos cada).
    """
    if not texto:
        return set()
    # Exclui CNPJs completos ja extraidos (evita dupla contagem)
    cnpjs_completos = extrair_cnpjs_da_descricao(texto)
    texto_limpo = texto
    for cnpj in cnpjs_completos:
        texto_limpo = texto_limpo.replace(cnpj, '')
    raizes = set()
    for m in _RE_RAIZ_CNPJ_8.finditer(texto_limpo):
        digito8 = m.group(1)
        # Descartar "00000000" e datas tipo "20260420" (comecando 19/20)
        if digito8 == '00000000':
            continue
        if digito8.startswith('19') or digito8.startswith('20'):
            continue
        raizes.add(digito8)
    return raizes


def extrair_nome_pagador(descricao):
    """Extrai o NOME do pagador do prefixo antes do primeiro " - ".

    REFINO 2026-04-19: analise de 178 linhas OFX reais mostra que 100%
    seguem o padrao: `<Nome Pagador> - <Tipo Operacao>: "<detalhes>"`.
    Exemplos:
      "D.a. De Mattos & Cia Ltda - Pix recebido: ..." -> "D.a. De Mattos & Cia Ltda"
      "CAZAN TRANSPORTES LTDA - Pagamento efetuado: ..." -> "CAZAN TRANSPORTES LTDA"
      "Rafael Nascimento - Transferencia recebida: ..." -> "Rafael Nascimento"

    Se nao ha " - ", retorna a descricao completa (fallback seguro).

    Args:
        descricao: str|None

    Returns:
        str: nome extraido ou string vazia
    """
    if not descricao:
        return ''
    # Limita busca aos primeiros 200 chars (nome raramente ultrapassa 80)
    head = descricao[:200]
    idx = head.find(' - ')
    if idx <= 0:
        return descricao.strip()
    return head[:idx].strip()


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

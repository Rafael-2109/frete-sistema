"""Cores das motos HORA — agregacao + anti-duplicacao de grafia (sem catalogo).

Decisao 2026-04-23 (mantida): cor NAO tem tabela propria; vive como texto livre
em `hora_moto.cor`, `hora_nf_entrada_item.cor_texto_original`,
`hora_pedido_item.cor` e `hora_recebimento_conferencia.cor_conferida`.

Este service NAO cria catalogo. Ele apenas:
  (a) `listar_cores_existentes()` — agrega as grafias JA usadas na base, para o
      recebimento oferecer reaproveitamento (em vez de o operador redigitar e
      criar uma variante);
  (b) `sugerir_similares(nome)` — ao criar uma cor manual, detecta grafias
      semelhantes ja existentes (BRANCA / BRANCO / BRANCCA / BRANA) para um
      aviso **NAO-bloqueante**: o operador decide reaproveitar ou criar mesmo
      assim (preserva pares legitimos como PRETA / PRATA, que tambem disparam
      o aviso, sem nunca impedir a criacao).

Espelha a intencao do §12 (unificacao de modelos) na superficie de cor, mas sem
o peso de tabela canonica/alias — escopo "prevencao leve".
"""
from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher
from typing import List, Optional

from app import db
from app.hora.models import HoraMoto, HoraNfEntradaItem, HoraPedidoItem

# Limiar de similaridade para o aviso. Calibrado para o caso real de cor de
# moto: BRANCO/BRANCA (~0.83), BRANCCA/BRANCA (~0.92), BRANA/BRANCA (~0.91) e
# PRATA/PRETA (0.80) entram; pares de cores claramente distintas (AZUL/ANIL ~0.5)
# ficam de fora. Por ser AVISO (nao bloqueia), preferimos pegar a mais.
_SIMILARIDADE_MIN = 0.8


def normalizar_cor(v: Optional[str]) -> Optional[str]:
    """Forma de EXIBICAO/persistencia: upper + espacos colapsados. None se vazio.

    Mantem acentos (a grafia oficial pode te-los); a remocao de acento ocorre so
    na chave de comparacao interna.
    """
    if v is None:
        return None
    s = ' '.join(v.split()).upper()
    return s or None


def _chave_comparacao(v: Optional[str]) -> str:
    """Chave usada SO para medir similaridade: sem acento, so alfanumerico, upper.

    Nunca e gravada. Faz 'AZUL BEBÊ' e 'AZUL BEBE' compararem como iguais.
    """
    if not v:
        return ''
    decomp = unicodedata.normalize('NFKD', v)
    sem_acento = ''.join(c for c in decomp if not unicodedata.combining(c))
    return ''.join(c for c in sem_acento if c.isalnum()).upper()


def listar_cores_existentes() -> List[str]:
    """Todas as grafias de cor ja usadas na base, normalizadas, deduplicadas e
    ordenadas. Une as 3 fontes de texto livre (moto + NF de entrada + pedido)."""
    valores: set[str] = set()
    fontes = (
        db.session.query(HoraMoto.cor).filter(HoraMoto.cor.isnot(None)),
        db.session.query(HoraNfEntradaItem.cor_texto_original)
        .filter(HoraNfEntradaItem.cor_texto_original.isnot(None)),
        db.session.query(HoraPedidoItem.cor).filter(HoraPedidoItem.cor.isnot(None)),
    )
    for q in fontes:
        for (raw,) in q.distinct():
            n = normalizar_cor(raw)
            if n:
                valores.add(n)
    return sorted(valores)


def sugerir_similares(
    nome: str,
    existentes: Optional[List[str]] = None,
    limite: int = 5,
) -> List[str]:
    """Cores existentes graficamente semelhantes a `nome` (aviso anti-duplicata).

    - Compara pela chave (sem acento/pontuacao).
    - Exclui as identicas apos normalizar (mesma cor, nao ha duplicata a evitar).
    - Ordena por similaridade desc; corta em `limite`.
    Quando `existentes` e None, consulta `listar_cores_existentes()` (toca o DB).
    """
    alvo = normalizar_cor(nome)
    if not alvo:
        return []
    if existentes is None:
        existentes = listar_cores_existentes()

    chave_alvo = _chave_comparacao(alvo)
    if not chave_alvo:
        return []

    candidatos = []
    for c in existentes:
        c_norm = normalizar_cor(c)
        if not c_norm or c_norm == alvo:
            continue  # vazio ou exatamente a mesma grafia
        ratio = SequenceMatcher(None, chave_alvo, _chave_comparacao(c_norm)).ratio()
        if ratio >= _SIMILARIDADE_MIN:
            candidatos.append((ratio, c_norm))

    candidatos.sort(key=lambda t: (-t[0], t[1]))
    return [c for _, c in candidatos[:limite]]

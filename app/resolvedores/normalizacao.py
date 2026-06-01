"""Normalizacao de texto para resolucao de entidades (funcoes puras, sem I/O).

Port fiel de gerindo-expedicao/scripts/resolver_entidades.py:
- normalizar_texto (:61)  — NFD + remove combining + lower + strip
- _normalizar_token (:1117) — stemming-s simples (remove 's' final em tokens >= 5 chars)
"""
import unicodedata


def normalizar_texto(texto: str) -> str:
    """Normaliza texto removendo acentos e convertendo para minusculas.

    Util para comparacoes de cidades, clientes, produtos onde podem haver
    variacoes de acentuacao e case.

    Exemplos:
        normalizar_texto("Itanhaém") -> "itanhaem"
        normalizar_texto("São Paulo") -> "sao paulo"
        normalizar_texto("PERUÍBE")  -> "peruibe"
    """
    if not texto:
        return ""
    # Remove acentos via NFD (decomposicao) e remove combining characters
    texto_sem_acento = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return texto_sem_acento.lower().strip()


def _normalizar_token(t: str) -> str:
    """Stemming-s simples: remove 's' final em tokens com >= 5 chars.

    Resolve plural ('azeitonas' -> 'azeitona'). Tokens curtos preservados
    para nao quebrar abreviacoes/embalagens (ex: 'br', 'bd', 'gl').
    """
    t = t.strip().lower()
    if len(t) >= 5 and t.endswith('s'):
        return t[:-1]
    return t

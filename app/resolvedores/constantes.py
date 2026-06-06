"""Constantes do dominio de resolucao de entidades — 1 fonte unica.

GRUPOS_EMPRESARIAIS: prefixos CNPJ no formato do monolito (curto, sem barra; usados com LIKE 'prefixo%').
    NAO confundir com app/utils/grupo_empresarial.py (formato 'XX.XXX.XXX/' + 9 grupos — INCOMPATIVEL,
    outro dominio). Reusar aquele mudaria o matching (regressao silenciosa) — por isso mantido aqui.
UFS_VALIDAS: 27 UFs (antes inline em resolver_entidades.py:413).
ABREVIACOES_PRODUTO: reexportado de app.embeddings.product_search (SoT de runtime) — sem 3a copia.
"""
# Dedup: reexporta o MESMO dict de product_search (que e quem usa em runtime via _buscar_texto).
from app.embeddings.product_search import ABREVIACOES_PRODUTO  # noqa: F401

# Port de resolver_entidades.py:93
GRUPOS_EMPRESARIAIS = {
    'atacadao': ['93.209.76', '75.315.33', '00.063.96'],
    'assai': ['06.057.22'],
    'tenda': ['01.157.55'],
}

# Port de resolver_entidades.py:413 (extraido de dentro de resolver_uf para constante unica)
UFS_VALIDAS = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
    'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
    'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
]

"""Constantes da flag `local_cd` — CD de expedicao (Victorio Marchezine / Tenente Marques).

Flag cross-modulo que identifica em qual CD fisico um pedido/NF/embarque/entrega e
expedido. Regras de negocio (ver `.claire/rascunho.md` topico 4):

- Pedidos Nacom sao SEMPRE `VICTORIO_MARCHEZINE` (default historico e novo).
- Pedidos CarVia podem ter os dois CDs (a flag nasce na Coleta — stream Coletas).
- Cores PADRONIZADAS em todos os locais (macro `badge_local_cd` em
  `app/templates/shared/_macros_badges.html`):
    * VICTORIO_MARCHEZINE -> fundo amarelo, texto preto
    * TENENTE_MARQUES     -> fundo roxo,   texto branco

Modulo colocado em `app/utils/` para ser importavel por TODOS os modulos, inclusive
CarVia (que so pode importar de `app/utils`, `app/transportadoras`, `app/tabelas` e
`app/odoo/utils` — ver `app/carvia/CLAUDE.md` R1).
"""

# Valores canonicos (armazenados em VARCHAR(20) nas colunas local_cd)
LOCAL_CD_VICTORIO_MARCHEZINE = 'VICTORIO_MARCHEZINE'
LOCAL_CD_TENENTE_MARQUES = 'TENENTE_MARQUES'

# Default universal (Nacom + historico)
LOCAL_CD_DEFAULT = LOCAL_CD_VICTORIO_MARCHEZINE

# Rotulos por extenso
LOCAL_CD_LABELS = {
    LOCAL_CD_VICTORIO_MARCHEZINE: 'Victorio Marchezine',
    LOCAL_CD_TENENTE_MARQUES: 'Tenente Marques',
}

# Rotulos curtos (badges em tabelas densas)
LOCAL_CD_LABELS_CURTO = {
    LOCAL_CD_VICTORIO_MARCHEZINE: 'V. Marchezine',
    LOCAL_CD_TENENTE_MARQUES: 'T. Marques',
}

# Para WTForms SelectField / choices de UI
LOCAL_CD_CHOICES = [
    (LOCAL_CD_VICTORIO_MARCHEZINE, LOCAL_CD_LABELS[LOCAL_CD_VICTORIO_MARCHEZINE]),
    (LOCAL_CD_TENENTE_MARQUES, LOCAL_CD_LABELS[LOCAL_CD_TENENTE_MARQUES]),
]

LOCAL_CD_VALORES = frozenset({LOCAL_CD_VICTORIO_MARCHEZINE, LOCAL_CD_TENENTE_MARQUES})


def normalizar_local_cd(valor):
    """Normaliza entrada livre (form, planilha, import) para um valor canonico ou None.

    Aceita os codigos canonicos, abreviacoes ('VM'/'TM') e o nome por extenso
    (com/sem acento, maiusc/minusc). Retorna None se nao reconhecer.
    """
    if not valor:
        return None
    bruto = str(valor).strip()
    canonico = bruto.upper().replace(' ', '_').replace('.', '')
    if canonico in LOCAL_CD_VALORES:
        return canonico
    low = bruto.lower()
    if 'tenente' in low or 'marques' in low or canonico in ('TM', 'T_MARQUES'):
        return LOCAL_CD_TENENTE_MARQUES
    if 'victorio' in low or 'vitorio' in low or 'marchezine' in low or canonico in ('VM', 'V_MARCHEZINE'):
        return LOCAL_CD_VICTORIO_MARCHEZINE
    return None


def label_local_cd(valor, curto=False):
    """Rotulo de exibicao de um valor de local_cd (string vazia se desconhecido)."""
    if curto:
        return LOCAL_CD_LABELS_CURTO.get(valor, '')
    return LOCAL_CD_LABELS.get(valor, '')

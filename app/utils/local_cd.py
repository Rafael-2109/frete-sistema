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

# Endereco fisico de coleta de cada CD (usado na solicitacao de coleta a transportadora).
LOCAL_CD_ENDERECOS = {
    LOCAL_CD_VICTORIO_MARCHEZINE: 'Rua Victorio Marchezine, nº 61 – Santana de Parnaíba/SP',
    LOCAL_CD_TENENTE_MARQUES: 'Est. Tenente Marques, nº 6609 – Santana de Parnaíba/SP',
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


def endereco_local_cd(valor):
    """Endereco fisico de coleta de um CD (string vazia se desconhecido)."""
    return LOCAL_CD_ENDERECOS.get(valor or LOCAL_CD_DEFAULT, '')


# ---------------------------------------------------------------------------
# Saida por CD — gate do "frete dispara na ULTIMA saida"
# ---------------------------------------------------------------------------
# Um Embarque pode ter itens dos 2 CDs (VM + TM); a portaria de cada CD da saida
# SOMENTE dos seus itens (1 ControlePortaria por CD). O frete (Nacom E CarVia) so
# pode disparar quando TODOS os CDs com itens ativos ja registraram saida — senao
# o frete nasceria sem os itens do CD que ainda nao saiu.
#
# As funcoes operam por duck-typing sobre o objeto Embarque (atributos `.itens` e
# `.registros_portaria`), sem importar app/embarques nem app/portaria — assim o
# modulo permanece importavel por TODOS (inclusive CarVia, que so pode importar de
# app/utils — ver app/carvia/CLAUDE.md R1).

def locais_cd_com_itens_ativos(embarque):
    """Conjunto de local_cd dos EmbarqueItem ATIVOS do embarque.

    Itens sem flag contam como `LOCAL_CD_DEFAULT` (VM). Itens nao-ativos ignorados.
    """
    return {
        (getattr(it, 'local_cd', None) or LOCAL_CD_DEFAULT)
        for it in (getattr(embarque, 'itens', None) or [])
        if getattr(it, 'status', None) == 'ativo'
    }


def locais_cd_com_saida(embarque):
    """Conjunto de local_cd dos ControlePortaria do embarque que JA deram saida.

    Considera "saiu" quando `data_saida` esta preenchido. Registro sem flag conta
    como `LOCAL_CD_DEFAULT` (VM).
    """
    return {
        (getattr(cp, 'local_cd', None) or LOCAL_CD_DEFAULT)
        for cp in (getattr(embarque, 'registros_portaria', None) or [])
        if getattr(cp, 'data_saida', None) is not None
    }


def cds_pendentes_de_saida(embarque):
    """CDs com itens ativos que AINDA NAO deram saida — gate do disparo de frete.

    Regra de negocio (item 2, decisao Rafael 2026-06-18): o frete so muda de
    comportamento para embarque MISTO (itens em >1 CD). Nesse caso, retorna os CDs
    cuja saida ainda falta — conjunto NAO-vazio significa "aguardar a ultima saida".

    Para embarque de 1 unico CD (Nacom puro / Op. Assai / CarVia 1 destino), retorna
    sempre conjunto VAZIO: mantem o comportamento legado (o `data_embarque`, checado a
    montante, ja garante a saida desse CD) e NAO exige registro de portaria — evita
    regressao em embarques cujo `data_embarque` foi preenchido sem ControlePortaria.

    Embarque None / sem itens ativos: conjunto vazio (nao restringe; os requisitos
    seguintes do fluxo tratam a ausencia de itens).
    """
    if embarque is None:
        return set()
    locais_itens = locais_cd_com_itens_ativos(embarque)
    if len(locais_itens) <= 1:
        return set()  # nao-misto: comportamento legado, sem restricao por CD
    return locais_itens - locais_cd_com_saida(embarque)

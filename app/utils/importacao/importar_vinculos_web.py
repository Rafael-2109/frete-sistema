import re
import math
import unicodedata
import pandas as pd
from app import db
from app.localidades.models import Cidade
from app.transportadoras.models import Transportadora
from app.vinculos.models import CidadeAtendida
from app.utils.string_utils import normalizar_nome_corporativo, colapsar_espacos


_RE_ESPACOS = re.compile(r'\s+')


def _unaccent(texto):
    """
    Espelha `f_unaccent` do PostgreSQL: remove APENAS diacriticos
    (acentos, cedilha) preservando os demais caracteres (&, ., /, etc.).

    NAO trocar por `remover_acentos`/`chave_comparacao_nome` de string_utils:
    aquelas tambem removem caracteres especiais, divergindo do match SQL
    original e mudando o resultado para razoes como "J & F" ou "S.A.".
    """
    if texto is None:
        return ''
    nfkd = unicodedata.normalize('NFKD', str(texto))
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def _chave_match(texto):
    """
    Espelha em memoria a normalizacao usada no SQL original:
        btrim(regexp_replace(f_unaccent(X), '\\s+', ' ', 'g'))
    => unaccent + colapsa espacos internos + trim.
    """
    return _RE_ESPACOS.sub(' ', _unaccent(texto)).strip()


def _limpar_lead_time(valor):
    """Converte lead_time para int ou None, tratando nan/NaN do pandas."""
    if valor is None:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    if pd.isna(valor):
        return None
    try:
        return int(valor)
    except (ValueError, TypeError):
        return None


def validar_vinculos(caminho):
    """
    Valida as linhas de um Excel de vinculos de cidades atendidas.

    Performance: pre-carrega transportadoras, cidades e vinculos existentes
    em memoria (3 queries no total) e faz o match localmente, eliminando o
    padrao N+1 (2-3 queries por linha, cada uma com f_unaccent/full scan) que
    travava a importacao de planilhas grandes (ex: regioes.xlsx).
    Ver app/vinculos/routes.py::importar_vinculos.

    O resultado e identico ao da validacao linha-a-linha anterior: cada item
    da lista mantem as mesmas chaves (transportadora_nome, cidade_nome, uf,
    codigo_ibge, nome_tabela, lead_time, erro) e os ids quando encontrados.
    """
    df = pd.read_excel(caminho)
    df.columns = df.columns.str.strip().str.upper()

    # ── Pre-carga em batch (substitui o N+1) ───────────────────────────
    # 1. Transportadoras por chave normalizada. O match original era ILIKE
    #    sem wildcard => igualdade case-insensitive (por isso .lower()).
    #    order_by(id) + setdefault torna deterministico o desempate quando
    #    ha razoes sociais normalizadas iguais (aproxima o antigo .first()).
    transportadoras_por_chave = {}
    for tid, razao in (
        db.session.query(Transportadora.id, Transportadora.razao_social)
        .order_by(Transportadora.id)
        .all()
    ):
        transportadoras_por_chave.setdefault(_chave_match(razao).lower(), tid)

    # 2. Cidades por codigo_ibge. A chave e o valor cru da coluna, igual ao
    #    comportamento de `Cidade.codigo_ibge == codigo_ibge` (str do Excel).
    cidades_por_ibge = {}
    for cid, ibge in (
        db.session.query(Cidade.id, Cidade.codigo_ibge)
        .order_by(Cidade.id)
        .all()
    ):
        if ibge is not None:
            cidades_por_ibge.setdefault(ibge, cid)

    # 3. Vinculos ja existentes (deteccao de duplicata):
    #    set de (cidade_id, transportadora_id, chave_tabela_normalizada).
    vinculos_existentes = set()
    for c_id, t_id, n_tab in db.session.query(
        CidadeAtendida.cidade_id,
        CidadeAtendida.transportadora_id,
        CidadeAtendida.nome_tabela,
    ).all():
        vinculos_existentes.add((c_id, t_id, _chave_match(n_tab)))

    # ── Validacao linha a linha (somente memoria, lookups O(1)) ────────
    linhas = []

    for _, row in df.iterrows():
        erro = None

        # Normalizacoes: trim + colapsa espacos internos
        transportadora_nome = colapsar_espacos(str(row['TRANSPORTADORA'])) or ''
        cidade_nome = colapsar_espacos(str(row['CIDADE'])) or ''
        uf = str(row['UF']).strip()
        codigo_ibge = str(row['CODIGO IBGE']).strip()
        # nome_tabela: trim + colapsa espacos + UPPER
        nome_tabela = normalizar_nome_corporativo(str(row['TABELA'])) or ''
        lead_time = _limpar_lead_time(row.get('LEAD TIME', None))

        transportadora_id = transportadoras_por_chave.get(
            _chave_match(transportadora_nome).lower()
        )
        cidade_id = cidades_por_ibge.get(codigo_ibge)

        if not transportadora_id:
            erro = "Transportadora não encontrada"
        elif not cidade_id:
            erro = "Cidade (IBGE) não encontrada"
        elif not nome_tabela:
            erro = "Tabela não informada"
        elif (cidade_id, transportadora_id, _chave_match(nome_tabela)) in vinculos_existentes:
            erro = "Vínculo já existente"

        linha = {
            'transportadora_nome': transportadora_nome,
            'cidade_nome': cidade_nome,
            'uf': uf,
            'codigo_ibge': codigo_ibge,
            'nome_tabela': nome_tabela,
            'lead_time': lead_time,
            'erro': erro,
        }

        if transportadora_id:
            linha['transportadora_id'] = transportadora_id
        if cidade_id:
            linha['cidade_id'] = cidade_id

        linhas.append(linha)

    return linhas

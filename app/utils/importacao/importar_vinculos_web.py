import pandas as pd
import math
from sqlalchemy import func
from app.localidades.models import Cidade
from app.transportadoras.models import Transportadora
from app.vinculos.models import CidadeAtendida
from app.utils.string_utils import normalizar_nome_corporativo, colapsar_espacos


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
    df = pd.read_excel(caminho)
    df.columns = df.columns.str.strip().str.upper()

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

        # Match insensivel a acento, cedilha e variacoes de espaco.
        # 1. f_unaccent: remove acentos/cedilha
        # 2. regexp_replace(\s+, ' '): colapsa espacos internos
        # 3. btrim: remove espacos no inicio/fim
        # Tolerante a dados antigos no banco que podem ter espaco extra.
        razao_db_norm = func.btrim(
            func.regexp_replace(
                func.f_unaccent(Transportadora.razao_social),
                r'\s+', ' ', 'g'
            )
        )
        razao_excel_norm = func.btrim(
            func.regexp_replace(
                func.f_unaccent(transportadora_nome),
                r'\s+', ' ', 'g'
            )
        )
        transportadora = Transportadora.query.filter(
            razao_db_norm.ilike(razao_excel_norm)
        ).first()

        cidade = Cidade.query.filter(
            Cidade.codigo_ibge == codigo_ibge
        ).first()

        if not transportadora:
            erro = "Transportadora não encontrada"
        elif not cidade:
            erro = "Cidade (IBGE) não encontrada"
        elif not nome_tabela:
            erro = "Tabela não informada"
        elif CidadeAtendida.query.filter(
            CidadeAtendida.cidade_id == cidade.id,
            CidadeAtendida.transportadora_id == transportadora.id,
            func.btrim(
                func.regexp_replace(
                    func.f_unaccent(CidadeAtendida.nome_tabela),
                    r'\s+', ' ', 'g'
                )
            ) == func.btrim(
                func.regexp_replace(
                    func.f_unaccent(nome_tabela),
                    r'\s+', ' ', 'g'
                )
            )
        ).first():
            erro = "Vínculo já existente"

        linha = {
            'transportadora_nome': transportadora_nome,
            'cidade_nome': cidade_nome,
            'uf': uf,
            'codigo_ibge': codigo_ibge,
            'nome_tabela': nome_tabela,
            'lead_time': lead_time,
            'erro': erro
        }

        if transportadora:
            linha['transportadora_id'] = transportadora.id
        if cidade:
            linha['cidade_id'] = cidade.id

        linhas.append(linha)

    return linhas

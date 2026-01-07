import pandas as pd
import math
from app.localidades.models import Cidade
from app.transportadoras.models import Transportadora
from app.vinculos.models import CidadeAtendida
from app import db


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

        transportadora_nome = str(row['TRANSPORTADORA']).strip()
        cidade_nome = str(row['CIDADE']).strip()
        uf = str(row['UF']).strip()
        codigo_ibge = str(row['CODIGO IBGE']).strip()
        nome_tabela = str(row['TABELA']).strip().upper()  # ✅ NORMALIZADO PARA MAIÚSCULA
        lead_time = _limpar_lead_time(row.get('LEAD TIME', None))

        transportadora = Transportadora.query.filter(
            Transportadora.razao_social.ilike(transportadora_nome)
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
        elif CidadeAtendida.query.filter_by(
            cidade_id=cidade.id,
            transportadora_id=transportadora.id,
            nome_tabela=nome_tabela
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

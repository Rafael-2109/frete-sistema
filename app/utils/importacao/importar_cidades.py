import pandas as pd
from app import db
from app.localidades.models import Cidade

def importar_cidades(caminho_arquivo):
    df = pd.read_excel(caminho_arquivo, dtype=str)
    df.columns = df.columns.str.strip().str.upper()

    for _, row in df.iterrows():
        icms_str = row['ICMS'].replace(',', '.').replace('%', '').strip()
        try:
            icms = float(icms_str) / 100  # Ex: '7,00%' → '7.00' → 0.07
        except ValueError:
            icms = 0.0

        cidade = Cidade(
            nome=row['CIDADE'].strip(),
            uf=row['UF'].strip().upper(),
            codigo_ibge=row['IBGE'].strip(),
            icms=icms,
            substitui_icms_por_iss=str(row.get('ISS', '')).strip().upper() == 'SIM'
        )
        db.session.add(cidade)

    db.session.commit()
    print(f"{len(df)} cidades importadas com sucesso.")

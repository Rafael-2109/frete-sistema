from app import db
from sqlalchemy import text
from app.financeiro.services.remessa_vortx.dac_calculator import calcular_dac_nosso_numero
from app.financeiro.services.remessa_vortx.layout_vortx import CARTEIRA


def alocar_nossos_numeros(qtd: int) -> list:
    if qtd <= 0:
        raise ValueError('qtd deve ser positivo')
    resultado = []
    for _ in range(qtd):
        row = db.session.execute(text("SELECT nextval('nosso_numero_vortx_seq')"))
        seq = row.scalar()
        nn = str(seq).zfill(11)
        dac = calcular_dac_nosso_numero(CARTEIRA, nn)
        resultado.append({'seq': seq, 'nosso_numero': nn, 'dac': dac, 'completo': f'{nn}-{dac}'})
    return resultado


def consultar_proximo():
    row = db.session.execute(text("SELECT last_value FROM nosso_numero_vortx_seq"))
    return row.scalar()


def ajustar_sequence(novo_valor: int):
    db.session.execute(text("SELECT setval('nosso_numero_vortx_seq', :val, true)"), {'val': novo_valor})
    db.session.commit()

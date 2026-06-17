from sqlalchemy import inspect
from app.veiculos.models import Veiculo


def test_veiculo_tem_colunas_de_custo(db):
    cols = {c['name'] for c in inspect(db.engine).get_columns('veiculos')}
    esperadas = {
        'custo_km', 'custo_motorista_dia', 'custo_fixo_dia', 'depreciacao_mensal',
        'capacidade_pallets', 'capacidade_m3', 'velocidade_media_kmh', 'ativo',
    }
    assert esperadas.issubset(cols), f"faltando: {esperadas - cols}"


def test_veiculo_model_aceita_novos_campos(db):
    v = Veiculo(nome='TESTE_TOCO', peso_maximo=6500, custo_km=3.20,
                custo_motorista_dia=180, custo_fixo_dia=50,
                depreciacao_mensal=1500, capacidade_pallets=14,
                capacidade_m3=42.0, velocidade_media_kmh=55.0, ativo=True)
    db.session.add(v)
    db.session.flush()
    assert v.id is not None
    assert float(v.custo_km) == 3.20
    assert v.ativo is True

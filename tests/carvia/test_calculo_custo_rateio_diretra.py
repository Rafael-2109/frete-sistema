"""Rateio DIRETA do custo CarVia: um item de peso 0 NAO pode levar o frete do
caminhao inteiro.

Bug E-VIBE (embarque 6008, NF 2044, 2026-06-24): a NF sem motos reconhecidas
(peso_cubado=0) caia no ramo `else: proporcao = 1.0` de
`CarviaFreteService._calcular_custo_rateio` e recebia o frete do caminhao todo
(R$12.000). Fix: `proporcao = peso_grupo / peso_embarque_real` sempre que o
embarque tem peso agregado (peso_grupo=0 -> proporcao 0); o `else=1.0` so vale
quando o embarque inteiro nao tem peso.
"""


def _embarque_direta(db):
    from app.embarques.models import Embarque
    e = Embarque(
        status='ativo',
        criado_por='test@bot',
        tipo_carga='DIRETA',
        peso_total=1000.0,
        valor_total=50000.0,
    )
    db.session.add(e)
    db.session.flush()
    return e


def test_rateio_peso_zero_nao_leva_frete_inteiro(db, monkeypatch):
    from app.carvia.services.documentos.carvia_frete_service import CarviaFreteService
    from app.utils.calculadora_frete import CalculadoraFrete
    from app.utils.tabela_frete_manager import TabelaFreteManager

    e = _embarque_direta(db)  # sem EmbarqueItem -> peso_embarque_real = peso_total = 1000

    # Isola o frete do CAMINHAO em 12.000 (sem depender de tabela real)
    monkeypatch.setattr(
        TabelaFreteManager, 'preparar_dados_tabela',
        staticmethod(lambda emb: {'nome_tabela': 'TESTE'}),
    )
    monkeypatch.setattr(
        CalculadoraFrete, 'calcular_frete_unificado',
        lambda self, **kw: {'valor_com_icms': 12000},
    )

    # peso_grupo=0 (NF sem motos reconhecidas) -> 0, NUNCA 12.000 (o bug)
    assert CarviaFreteService._calcular_custo_rateio(e, 0, 100) == 0

    # peso_grupo=500 de 1000 -> fatia 50% = 6.000 (rateio por peso preservado)
    assert CarviaFreteService._calcular_custo_rateio(e, 500, 25000) == 6000

    # peso_grupo=1000 (frete inteiro do caminhao) -> 12.000
    assert CarviaFreteService._calcular_custo_rateio(e, 1000, 50000) == 12000

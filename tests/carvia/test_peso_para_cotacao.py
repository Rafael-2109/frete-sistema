"""
Testes da property canonica CarviaCotacao.peso_para_cotacao (Correcao B).

Convencao do sistema (verificada em producao): para MOTO a fonte de verdade
do peso e a property `peso_total_motos` (SUM de CarviaCotacaoMoto.peso_cubado_total);
o campo `peso_cubado` e para CARGA_GERAL. A regra
"MOTO -> peso_total_motos / CARGA_GERAL -> peso_cubado ou peso bruto" estava
duplicada em cotacao_v2_service._calcular_preco e margem_service. A property
consolida a regra num unico acessor.

Ref: CarviaCotacao.peso_para_cotacao
"""

from unittest.mock import PropertyMock, patch

import pytest

from app.carvia.models import CarviaCotacao


@pytest.fixture(autouse=True)
def _app_ctx(app):
    """App context para inicializar os mappers SQLAlchemy (Transportadora etc.)."""
    with app.app_context():
        yield


class TestPesoParaCotacao:

    def test_moto_usa_peso_total_motos(self):
        cot = CarviaCotacao(tipo_material='MOTO', peso_cubado=None, peso=905)
        with patch.object(
            type(cot), 'peso_total_motos',
            new_callable=PropertyMock, return_value=1894.158,
        ):
            assert cot.peso_para_cotacao == 1894.158

    def test_moto_ignora_campo_peso_cubado_stale(self):
        # Mesmo com campo peso_cubado preenchido (stale), MOTO usa a property
        cot = CarviaCotacao(tipo_material='MOTO', peso_cubado=999, peso=905)
        with patch.object(
            type(cot), 'peso_total_motos',
            new_callable=PropertyMock, return_value=1894.158,
        ):
            assert cot.peso_para_cotacao == 1894.158

    def test_carga_geral_usa_peso_cubado(self):
        cot = CarviaCotacao(tipo_material='CARGA_GERAL', peso_cubado=500, peso=300)
        assert cot.peso_para_cotacao == 500.0

    def test_carga_geral_sem_cubado_usa_peso_bruto(self):
        cot = CarviaCotacao(tipo_material='CARGA_GERAL', peso_cubado=None, peso=300)
        assert cot.peso_para_cotacao == 300.0

    def test_carga_geral_sem_nada_retorna_zero(self):
        cot = CarviaCotacao(tipo_material='CARGA_GERAL', peso_cubado=None, peso=None)
        assert cot.peso_para_cotacao == 0.0

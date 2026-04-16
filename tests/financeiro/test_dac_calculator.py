import pytest
from app.financeiro.services.remessa_vortx.dac_calculator import calcular_dac_nosso_numero

class TestCalcularDacNossoNumero:
    def test_nn_001_carteira_21_retorna_9(self):
        assert calcular_dac_nosso_numero('21', '00000000001') == '9'

    def test_nn_002_carteira_21_retorna_7(self):
        assert calcular_dac_nosso_numero('21', '00000000002') == '7'

    def test_nn_003_carteira_21_retorna_5(self):
        assert calcular_dac_nosso_numero('21', '00000000003') == '5'

    def test_nn_006_carteira_21_retorna_0(self):
        assert calcular_dac_nosso_numero('21', '00000000006') == '0'

    def test_nn_010_carteira_21_retorna_8(self):
        assert calcular_dac_nosso_numero('21', '00000000010') == '8'

    def test_nn_020_carteira_21_retorna_5(self):
        assert calcular_dac_nosso_numero('21', '00000000020') == '5'

    def test_carteira_invalida_levanta_erro(self):
        with pytest.raises(ValueError, match='carteira deve ter 2 dígitos'):
            calcular_dac_nosso_numero('1', '00000000001')

    def test_nosso_numero_invalido_levanta_erro(self):
        with pytest.raises(ValueError, match='nosso_numero deve ter 11 dígitos'):
            calcular_dac_nosso_numero('21', '123')

    def test_retorno_e_string(self):
        result = calcular_dac_nosso_numero('21', '00000000001')
        assert isinstance(result, str)
        assert len(result) == 1

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


class TestDacCobrePosicoesAltas:
    """Garante que o algoritmo cobre todas as 13 posicoes do array de pesos.

    Os testes acima usam NNs <= 20, que so tem 1-2 digitos significativos
    e cobrem apenas posicoes 0-1 do array invertido. Estes casos validam
    NNs com digitos significativos em posicoes 7-12, capturando regressao
    caso alguem altere `digits.reverse()` ou `weights[i % 6]` por engano.

    Valor de referencia: DAC do NN 00000019762 = 9 — caso real do Marcus
    em 04/05/2026, confirmado contra o validador oficial Vortx em
    https://boleto-parser.vercel.app/validador-nosso-numero/VORTX.
    """

    def test_nn_real_marcus_00000019762_retorna_9(self):
        # Caso real validado byte-a-byte contra portal Vortx (04/05/2026)
        assert calcular_dac_nosso_numero('21', '00000019762') == '9'

    def test_nn_12345678901_retorna_8(self):
        # Cobre todas as 13 posicoes do array de pesos
        assert calcular_dac_nosso_numero('21', '12345678901') == '8'

    def test_nn_99999999999_retorna_6(self):
        # Todos os digitos = 9 — exercita soma maxima
        assert calcular_dac_nosso_numero('21', '99999999999') == '6'

    def test_nn_range_grafeno_90000000001_retorna_0(self):
        # Range >= 90000000000 = Grafeno gera o nosso numero
        assert calcular_dac_nosso_numero('21', '90000000001') == '0'

    def test_nn_12345000000_posicoes_baixas_retorna_5(self):
        # Digitos significativos APENAS nas posicoes 7-12 (lado esquerdo do
        # nosso numero) — exercita o lado oposto do array
        assert calcular_dac_nosso_numero('21', '12345000000') == '5'

    def test_nn_00000012345_posicoes_altas_retorna_5(self):
        # Digitos significativos APENAS nas posicoes 0-4 (lado direito)
        assert calcular_dac_nosso_numero('21', '00000012345') == '5'

"""Testes da Camada 1 do simulador de conservas (palletizacao_service)."""
from app.carteira.services.palletizacao_service import (
    calcular_lastro, calcular_altura,
)


class TestGeometria:
    def test_lastro_caixa_quadrada_4830103(self):
        # caixa 26x26 -> lastro efetivo (100+5)/26=4 x (120+5)/26=4 = 16
        r = calcular_lastro(largura_cm=26, comprimento_cm=26)
        assert r['lastro'] == 16
        assert r['merc_x'] == 104
        assert r['merc_y'] == 104

    def test_lastro_escolhe_melhor_orientacao(self):
        # caixa 40x30: orient A (40 em X,30 em Y)=floor(105/40)*floor(125/30)=2*4=8
        #              orient B (30 em X,40 em Y)=floor(105/30)*floor(125/40)=3*3=9 -> vence
        r = calcular_lastro(largura_cm=40, comprimento_cm=30)
        assert r['lastro'] == 9

    def test_lastro_caixa_invalida(self):
        assert calcular_lastro(0, 26)['lastro'] == 0

    def test_altura_4_camadas(self):
        # 64 caixas / lastro 16 = 4 camadas; 15 + 4*30.5 = 137.0
        r = calcular_altura(caixas=64, lastro=16, altura_cm=30.5)
        assert r['camadas'] == 4
        assert r['altura_total'] == 137.0

    def test_altura_arredonda_para_cima(self):
        # 65 caixas / 16 = 4.06 -> 5 camadas
        assert calcular_altura(caixas=65, lastro=16, altura_cm=30.5)['camadas'] == 5

    def test_altura_lastro_zero(self):
        assert calcular_altura(caixas=10, lastro=0, altura_cm=30)['altura_total'] == 15.0

"""
Testes do matching de modelo de moto NF <-> cotacao via regex_pattern.

Bug origem (NF 37939 / COT-97): o matching por substring simples
(`nome in mod or mod in nome`) NAO casa quando o separador difere entre o
nome cadastrado e o texto da NF. Ex.: cadastro "BIG TRI" (espaco) nao e
substring de "TRI MOTO ELETRICA BIG-TRI" (hifen) -> cubado das 5 BIG TRI
(952,698 kg) era perdido.

A correcao usa o `regex_pattern` ja cadastrado em CarviaModeloMoto
(ex.: "(?i)big[\\s\\-]*tri") que e tolerante ao separador, com word-boundary
e precedencia por tamanho de nome (MIA TRI antes de MIA).

Ref: MotoRecognitionService.resolver_modelo_em_lista
     EmbarqueCarViaService.calcular_cubado_por_modelos
"""

from unittest.mock import MagicMock, patch

import pytest

from app.carvia.services.pricing.moto_recognition_service import (
    MotoRecognitionService,
)
from app.carvia.services.documentos.embarque_carvia_service import (
    EmbarqueCarViaService,
)


def _modelo(nome: str, regex: str = None) -> MagicMock:
    m = MagicMock()
    m.nome = nome
    m.regex_pattern = regex
    m.id = abs(hash(nome)) % 100000
    return m


def _moto(nome: str, regex: str, qtd: int, cub_total: float) -> MagicMock:
    """Mock de CarviaCotacaoMoto (com modelo_moto aninhado)."""
    m = MagicMock()
    m.modelo_moto = _modelo(nome, regex)
    m.modelo_moto_id = m.modelo_moto.id
    m.quantidade = qtd
    m.peso_cubado_total = cub_total
    return m


# ---------------------------------------------------------------------------
# Helper puro: resolver_modelo_em_lista
# ---------------------------------------------------------------------------

class TestResolverModeloEmLista:

    def test_big_tri_hifen_casa_big_tri_espaco(self):
        # Caso real NF 37939: "BIG-TRI" (hifen) deve casar cadastro "BIG TRI"
        modelos = [
            _modelo("BIG TRI", r"(?i)big[\s\-]*tri"),
            _modelo("JOY SUPER", r"(?i)joy[\s\-]*super"),
        ]
        r = MotoRecognitionService.resolver_modelo_em_lista(
            "TRI MOTO ELETRICA BIG-TRI", modelos
        )
        assert r is not None
        assert r.nome == "BIG TRI"

    def test_separador_inverso_espaco_casa_cadastro_com_hifen(self):
        # Cadastro "S8-MINI" (hifen); NF traz "S8 MINI" (espaco)
        modelos = [_modelo("S8-MINI", r"(?i)S8[\s\-]*MINI"), _modelo("S8", r"(?i)s8")]
        r = MotoRecognitionService.resolver_modelo_em_lista(
            "SCOOTER ELETRICA S8 MINI", modelos
        )
        assert r is not None
        assert r.nome == "S8-MINI"

    def test_precedencia_mia_tri_antes_de_mia(self):
        # "MIA TRI" deve ganhar de "MIA" (precedencia por tamanho de nome)
        modelos = [_modelo("MIA", r"(?i)MIA"), _modelo("MIA TRI", r"(?i)mia[\s\-]*tri")]
        r = MotoRecognitionService.resolver_modelo_em_lista(
            "TRI MOTO ELETRICA MIA TRI", modelos
        )
        assert r is not None
        assert r.nome == "MIA TRI"

    def test_word_boundary_evita_falso_positivo(self):
        # "RET" nao deve casar dentro de "PRETA"
        modelos = [_modelo("RET", r"(?i)ret")]
        r = MotoRecognitionService.resolver_modelo_em_lista(
            "MOTO PRETA", modelos
        )
        assert r is None

    def test_match_por_nome_sem_regex(self):
        # Modelo sem regex_pattern: cai no match por nome com boundary
        modelos = [_modelo("JET", None)]
        r = MotoRecognitionService.resolver_modelo_em_lista(
            "MOTO ELETRICA JET", modelos
        )
        assert r is not None
        assert r.nome == "JET"

    def test_texto_vazio_retorna_none(self):
        modelos = [_modelo("BIG TRI", r"(?i)big[\s\-]*tri")]
        assert MotoRecognitionService.resolver_modelo_em_lista("", modelos) is None
        assert MotoRecognitionService.resolver_modelo_em_lista(None, modelos) is None

    def test_nenhum_modelo_casa(self):
        modelos = [_modelo("BIG TRI", r"(?i)big[\s\-]*tri")]
        r = MotoRecognitionService.resolver_modelo_em_lista(
            "CICLOMOTOR ELETRICO GENERICO", modelos
        )
        assert r is None


# ---------------------------------------------------------------------------
# Integracao: calcular_cubado_por_modelos (callsite principal)
# ---------------------------------------------------------------------------

class TestCalcularCubadoPorModelos:

    @patch('app.carvia.models.CarviaCotacaoMoto')
    def test_caso_cot97_inclui_big_tri_com_hifen(self, mock_ccm):
        # COT-97: 5x BIG TRI (952,698) + 10x JOY SUPER (941,460) = 1894,158
        big = _moto("BIG TRI", r"(?i)big[\s\-]*tri", 5, 952.698)
        joy = _moto("JOY SUPER", r"(?i)joy[\s\-]*super", 10, 941.460)
        mock_ccm.query.filter_by.return_value.all.return_value = [big, joy]

        modelos_nf = (
            ["TRI MOTO ELETRICA BIG-TRI"] * 5
            + ["SUPER SCOOTER ELETRICA JOY SUPER"] * 10
        )
        total = EmbarqueCarViaService.calcular_cubado_por_modelos(97, modelos_nf)

        # 5 * (952.698/5) + 10 * (941.460/10) = 952.698 + 941.460 = 1894.158
        assert total == pytest.approx(1894.16, abs=0.01)

    @patch('app.carvia.models.CarviaCotacaoMoto')
    def test_modelo_fora_da_cotacao_nao_soma(self, mock_ccm):
        big = _moto("BIG TRI", r"(?i)big[\s\-]*tri", 5, 952.698)
        mock_ccm.query.filter_by.return_value.all.return_value = [big]

        total = EmbarqueCarViaService.calcular_cubado_por_modelos(
            97, ["SCOOTER ELETRICA DOT"]  # DOT nao esta na cotacao
        )
        assert total == 0.0

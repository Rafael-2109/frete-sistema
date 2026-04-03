"""
Testes para MotoRecognitionService — regex de reconhecimento de motos.

Foco: falsos positivos onde nomes curtos de modelo (RET, DOT, POP, etc.)
aparecem como substring de palavras comuns (PRETA, DOTACAO, POPULAR).
Tambem cobre: gate NCM, persistencia via modelo_moto_id.
"""

from unittest.mock import MagicMock

import pytest

from app.carvia.services.pricing.moto_recognition_service import (
    VEICULO_ELETRICO_MODELOS,
    MotoRecognitionService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_modelo(nome: str, regex_pattern: str = None) -> MagicMock:
    """Cria mock de CarviaModeloMoto para testes sem DB."""
    m = MagicMock()
    m.nome = nome
    m.regex_pattern = regex_pattern
    return m


def _match(
    texto: str,
    modelos_nomes: list[str],
    codigo_produto: str = None,
    ncm: str = None,
) -> str | None:
    """Wrapper para _match_descricao com mocks."""
    modelos = [_fake_modelo(n) for n in modelos_nomes]
    return MotoRecognitionService._match_descricao(
        texto, modelos, codigo_produto, ncm=ncm,
    )


# ---------------------------------------------------------------------------
# Regex VEICULO_ELETRICO_MODELOS — word boundary
# ---------------------------------------------------------------------------

class TestRegexVeiculoEletricoModelos:
    """Garante que \\b impede match dentro de palavras."""

    @pytest.mark.parametrize("texto,esperado", [
        ("RET", "RET"),
        ("MOTO RET", "RET"),
        ("RET 1000W", "RET"),
        ("MODELO RET AZUL", "RET"),
    ])
    def test_match_ret_isolado(self, texto, esperado):
        m = VEICULO_ELETRICO_MODELOS.search(texto)
        assert m is not None
        assert m.group(1).upper() == esperado

    @pytest.mark.parametrize("texto", [
        "PRETA",
        "PRETAO",
        "RETRATO",
        "SECRETARIA",
        "CONCRETO",
        "INTERPRETAR",
    ])
    def test_nao_match_ret_dentro_de_palavra(self, texto):
        m = VEICULO_ELETRICO_MODELOS.search(texto)
        assert m is None, f"Falso positivo: '{texto}' matcheou modelo"

    @pytest.mark.parametrize("texto", [
        "POPULAR",
        "APOPLEJIA",
        "REPOPUTAR",
    ])
    def test_nao_match_pop_dentro_de_palavra(self, texto):
        m = VEICULO_ELETRICO_MODELOS.search(texto)
        assert m is None, f"Falso positivo: '{texto}' matcheou modelo"

    @pytest.mark.parametrize("texto", [
        "DOTACAO",
        "ANTIDOTO",
        "ANEDOTA",
    ])
    def test_nao_match_dot_dentro_de_palavra(self, texto):
        m = VEICULO_ELETRICO_MODELOS.search(texto)
        assert m is None, f"Falso positivo: '{texto}' matcheou modelo"

    @pytest.mark.parametrize("texto", [
        "JETSAM",
        "OBJETIVOS",
        "PROJETAR",
    ])
    def test_nao_match_jet_dentro_de_palavra(self, texto):
        m = VEICULO_ELETRICO_MODELOS.search(texto)
        assert m is None, f"Falso positivo: '{texto}' matcheou modelo"

    @pytest.mark.parametrize("texto", [
        "ROMANO",
        "AROMA",
        "CROMATICO",
    ])
    def test_nao_match_roma_dentro_de_palavra(self, texto):
        m = VEICULO_ELETRICO_MODELOS.search(texto)
        assert m is None, f"Falso positivo: '{texto}' matcheou modelo"

    def test_match_modelos_isolados(self):
        """Todos modelos devem matchear quando isolados."""
        modelos = [
            "X11 MINI", "JOY SUPER", "MIA TRI",
            "X12", "X15", "X11", "B2", "B3", "GRID", "JET",
            "ROMA", "GIGA", "RET", "S8", "BOB", "DOT", "POP", "VED",
        ]
        for modelo in modelos:
            m = VEICULO_ELETRICO_MODELOS.search(modelo)
            assert m is not None, f"Modelo '{modelo}' deveria matchear isolado"


# ---------------------------------------------------------------------------
# _match_descricao — match por nome (evitar falso positivo substring)
# ---------------------------------------------------------------------------

class TestMatchDescricaoNomeFalsoPositivo:
    """Bug NF 146749: 'PRETA' identificada como modelo 'RET'."""

    def test_preta_nao_matcheia_ret(self):
        """Caso original do bug — cor PRETA nao e modelo RET."""
        resultado = _match("MOTO ELETRICA PRETA 1000W", ["RET", "DOT", "JET"])
        assert resultado != "RET", "PRETA nao deve matchear modelo RET"

    def test_ret_isolado_matcheia(self):
        """Modelo RET quando e palavra isolada DEVE matchear."""
        resultado = _match("MOTO RET 1000W", ["RET", "DOT", "JET"])
        assert resultado == "RET"

    @pytest.mark.parametrize("descricao,modelo,deve_matchear", [
        # Cores que contem nomes de modelo como substring
        ("SCOOTER ELETRICA PRETA", "RET", False),
        ("MOTO ELETRICA PRETA 60V", "RET", False),
        ("BIKE PRETA COM PEDAL", "RET", False),
        # Palavras comuns com substring de modelo
        ("MOTO POPULAR 125CC", "POP", False),
        ("MOTO COM DOTACAO ESPECIAL", "DOT", False),
        # Modelo como palavra isolada — DEVE matchear
        ("SCOOTER RET PRETA 1000W", "RET", True),
        ("MOTO DOT BRANCA", "DOT", True),
        ("BIKE POP AZUL", "POP", True),
        # Modelo no inicio/fim da descricao
        ("RET MOTO ELETRICA", "RET", True),
        ("MOTO ELETRICA RET", "RET", True),
        # Modelo seguido de numero (sem letra)
        ("MOTO RET1000 60V", "RET", True),
        # Modelo precedido de hifen/barra (separador, nao letra)
        ("MOTO-RET AZUL", "RET", True),
        ("CODIGO/RET/2024", "RET", True),
    ])
    def test_nome_modelo_word_boundary(self, descricao, modelo, deve_matchear):
        resultado = _match(descricao, [modelo])
        if deve_matchear:
            assert resultado == modelo, (
                f"'{modelo}' deveria matchear em '{descricao}'"
            )
        else:
            assert resultado != modelo, (
                f"'{modelo}' NAO deveria matchear em '{descricao}' (falso positivo)"
            )


# ---------------------------------------------------------------------------
# Gate NCM — rejeitar itens que nao sao motos/veiculos
# ---------------------------------------------------------------------------

class TestGateNCM:
    """NCM 8711* = moto/veiculo. Qualquer outro NCM rejeita match."""

    @pytest.mark.parametrize("ncm,deve_matchear", [
        # NCM de motos — DEVE matchear
        ("87116000", True),       # moto eletrica
        ("87114000", True),       # moto >500cc
        ("8711.60.00", True),     # formatado com pontos
        ("87119000", True),       # outros
        ("8711", True),           # prefixo curto
        # NCM de nao-motos — NAO deve matchear
        ("39269090", False),      # plasticos
        ("84818099", False),      # valvulas
        ("73269090", False),      # ferro/aco
        ("20089900", False),      # conservas (palmito)
        ("9401", False),          # moveis
        # NCM vazio/nulo — DEVE matchear (sem gate)
        (None, True),
        ("", True),
    ])
    def test_gate_ncm(self, ncm, deve_matchear):
        resultado = _match("MOTO RET 1000W", ["RET"], ncm=ncm)
        if deve_matchear:
            assert resultado == "RET", f"NCM {ncm} deveria permitir match"
        else:
            assert resultado is None, f"NCM {ncm} deveria bloquear match"

    def test_ncm_bloqueia_falso_positivo_cor(self):
        """Item de plastico com cor PRETA — NCM bloqueia antes do regex."""
        resultado = _match(
            "CAPA PRETA PARA MOTO", ["RET"],
            ncm="39269090",
        )
        assert resultado is None

    def test_ncm_moto_permite_match_real(self):
        """Item com NCM de moto eletrica DEVE matchear."""
        resultado = _match(
            "SCOOTER RET 1000W PRETA", ["RET"],
            ncm="87116000",
        )
        assert resultado == "RET"


class TestMatchDescricaoConvencional:
    """Motos convencionais (marca + cilindrada)."""

    @pytest.mark.parametrize("descricao,esperado", [
        ("CG 160 TITAN", "CG 160"),
        ("BIZ 125 VERMELHA", "BIZ 125"),
        ("FACTOR 150 ED", "FACTOR 150"),
        ("XRE 300 ADVENTURE", "XRE 300"),
        ("HONDA CG160 PRETA", "CG 160"),
    ])
    def test_match_convencional(self, descricao, esperado):
        resultado = _match(descricao, [])
        assert resultado == esperado

    @pytest.mark.parametrize("descricao", [
        "MESA DE ESCRITORIO 120CM",
        "CAIXA 150 UNIDADES",
        "PALETE 200KG",
    ])
    def test_nao_match_nao_moto(self, descricao):
        resultado = _match(descricao, [])
        assert resultado is None


class TestMatchDescricaoEletrico:
    """Veiculos eletricos — keyword + modelo."""

    def test_moto_com_modelo_conhecido(self):
        """Keyword MOTO + modelo X12 deve matchear."""
        resultado = _match("MOTO ELETRICA X12 60V", [])
        assert resultado == "X12"

    def test_scooter_com_modelo(self):
        resultado = _match("SCOOTER JET 1000W AZUL", [])
        assert resultado == "JET"

    def test_bike_com_modelo(self):
        resultado = _match("BIKE B2 PRETA", [])
        assert resultado == "B2"

    def test_moto_sem_modelo_conhecido(self):
        """Keyword MOTO sem modelo conhecido nao deve matchear."""
        resultado = _match("MOTO ELETRICA PRETA 1000W", [])
        assert resultado is None

    def test_modelo_sem_keyword(self):
        """Modelo eletrico sem keyword MOTO/SCOOTER/BIKE nao matcheia via camada 3."""
        resultado = _match("VEICULO X12 ELETRICO", [])
        assert resultado is None


class TestMatchDescricaoCodigoProduto:
    """Fallback por prefixo MT- no codigo do produto."""

    def test_codigo_mt_jet(self):
        resultado = _match("VEICULO ELETRICO PRETO", [], "MT-JET")
        assert resultado == "JET"

    def test_codigo_mt_x12(self):
        resultado = _match("SCOOTER ELETRICA", [], "MT-X12")
        assert resultado == "X12"

    def test_codigo_sem_prefixo_mt(self):
        resultado = _match("VEICULO ELETRICO", [], "ABC-123")
        assert resultado is None


class TestMatchDescricaoRegexCustom:
    """Patterns regex customizados do banco (camada 1)."""

    def test_regex_custom_tem_prioridade(self):
        modelo = _fake_modelo("GAYA", r"GAYA|GA[YI]A")
        resultado = MotoRecognitionService._match_descricao(
            "MOTO GAYA 3000W PRETA", [modelo]
        )
        assert resultado == "GAYA"

    def test_regex_custom_invalido_nao_quebra(self):
        modelo = _fake_modelo("TEST", r"[invalid")  # regex invalido
        resultado = MotoRecognitionService._match_descricao(
            "MOTO TEST AZUL", [modelo]
        )
        # Deve cair no match por nome
        assert resultado == "TEST"


class TestMatchDescricaoCasosReais:
    """Cenarios reais de descricoes de NF-e."""

    @pytest.mark.parametrize("descricao,modelos_db,esperado", [
        # NF 146749 — bug original
        ("MOTO ELETRICA 1000W PRETA", ["RET", "DOT", "JET"], None),
        # Moto com modelo real + cor
        ("MOTO RET 1000W PRETA", ["RET", "DOT", "JET"], "RET"),
        ("SCOOTER DOT 60V BRANCA", ["RET", "DOT", "JET"], "DOT"),
        # Descricao com cor + modelo
        ("PATINETE ELETRICO VED VERDE", ["VED", "BOB"], "VED"),
        # Modelo curto no meio de descricao longa
        ("TRICICLO ELETRICO GIGA 3000W 72V AZUL METALICO", ["GIGA"], "GIGA"),
        # Sem modelo — apenas descricao generica
        ("PECAS PARA MOTO ELETRICA", ["RET", "DOT"], None),
        # Modelo B2 — potencial falso positivo com "B2B"
        ("TRANSACAO B2B COMERCIAL", ["B2"], None),
        ("MOTO B2 PRETA 48V", ["B2"], "B2"),
        # Modelo S8 — "S8" e palavra isolada, match correto
        ("SETOR S8 DEPOSITO", ["S8"], "S8"),
        ("SCOOTER S8 1500W", ["S8"], "S8"),
    ])
    def test_cenario_real(self, descricao, modelos_db, esperado):
        resultado = _match(descricao, modelos_db)
        assert resultado == esperado, (
            f"Descricao: '{descricao}' → esperado {esperado}, got {resultado}"
        )

    @pytest.mark.parametrize("descricao,ncm,modelos_db,esperado", [
        # Item de alimento com cor — NCM bloqueia
        ("PALMITO PRETA 500G", "20089900", ["RET"], None),
        # Item de moto com cor — NCM permite, word boundary protege
        ("MOTO ELETRICA PRETA 1000W", "87116000", ["RET"], None),
        # Item de moto com modelo real — NCM permite, modelo matcha
        ("MOTO RET 1000W PRETA", "87116000", ["RET"], "RET"),
        # Item sem NCM — match normal (sem gate)
        ("MOTO RET 1000W", None, ["RET"], "RET"),
    ])
    def test_cenario_real_com_ncm(self, descricao, ncm, modelos_db, esperado):
        resultado = _match(descricao, modelos_db, ncm=ncm)
        assert resultado == esperado, (
            f"Descricao: '{descricao}' NCM: {ncm} → esperado {esperado}, got {resultado}"
        )

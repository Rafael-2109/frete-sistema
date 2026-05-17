"""Testa parser SPED ECD — streaming Latin-1, output indexado por registro."""
import sys
from pathlib import Path

# Path do script da skill (nao eh modulo Python instalado)
SKILL_SCRIPT = Path(__file__).parent.parent.parent / ".claude" / "skills" / \
    "parseando-sped-ecd" / "scripts" / "parse_sped.py"

# Adicionar ao sys.path para importar
sys.path.insert(0, str(SKILL_SCRIPT.parent))

from parse_sped import parse_sped_file, parse_sped_line


SPED_MINIMAL = (
    "|0000|LECD|01072024|31122024|EMPRESA TESTE|61724241000178|MG|3106200|||||||0|0|0|0|N|||S|N||\r\n"
    "|0001|0|\r\n"
    "|0990|3|\r\n"
    "|I001|0|\r\n"
    "|I010|G|9.00|\r\n"
    "|I050|01012024|01|S|1|1|||CAIXA|\r\n"
    "|I050|01012024|01|A|2|11|1|11|CAIXA GERAL|\r\n"
    "|I990|4|\r\n"
    "|9001|0|\r\n"
    "|9900|0000|1|\r\n"
    "|9990|3|\r\n"
    "|9999|13|\r\n"
)


def test_parse_sped_line_extracts_fields():
    """Linha SPED split por pipe retorna campos sem o primeiro/ultimo vazios."""
    fields = parse_sped_line("|I010|G|9.00|")
    assert fields == ["I010", "G", "9.00"]


def test_parse_sped_line_empty_field():
    """Campos vazios (|| consecutivo) preservados como string vazia."""
    fields = parse_sped_line("|I050|01012024||S|1|1|||CAIXA|")
    assert len(fields) == 9
    assert fields[2] == ""
    assert fields[6] == ""


def test_parse_sped_file_returns_indexed_dict(tmp_path):
    """Output: dict indexado por REG -> lista de registros (sem REG no payload)."""
    sped_path = tmp_path / "sped_test.txt"
    sped_path.write_bytes(SPED_MINIMAL.encode("latin-1"))

    result = parse_sped_file(str(sped_path))

    assert isinstance(result, dict)
    assert "registros" in result
    assert "metadata" in result

    registros = result["registros"]
    assert "0000" in registros
    assert "I050" in registros
    assert len(registros["I050"]) == 2, "duas linhas I050 esperadas"

    # Primeiro registro I050 (sintetica)
    i050_0 = registros["I050"][0]
    assert i050_0["DT_ALT"] == "01012024"
    assert i050_0["COD_NAT"] == "01"
    assert i050_0["IND_CTA"] == "S"

    # Metadata
    assert result["metadata"]["total_lines"] == 12
    assert result["metadata"]["encoding"] == "latin-1"


def test_parse_sped_file_handles_latin1_chars(tmp_path):
    """Caracteres acentuados Latin-1 preservados."""
    sped_with_accent = (
        "|0000|LECD|01072024|31122024|NACOM GOIÁS|61724241000178|GO|5208707|||||||0|0|0|0|N|||S|N||\r\n"
    )
    sped_path = tmp_path / "sped_accent.txt"
    sped_path.write_bytes(sped_with_accent.encode("latin-1"))

    result = parse_sped_file(str(sped_path))
    nome = result["registros"]["0000"][0]["NOME"]
    assert "GOIÁS" in nome


def test_parse_sped_file_handles_large_sped_correctly(tmp_path):
    """Parser processa corretamente SPED com muitas linhas (1000 lancamentos I250).

    O comportamento de streaming (linha a linha sem carregar o arquivo inteiro)
    eh garantido pelo file iterator do Python em iter_sped_records() — nao testado
    diretamente aqui, mas documentado no corpo da funcao.
    """
    # SPED grande sintetico (1000 lancamentos I250)
    big_sped = SPED_MINIMAL
    for i in range(1000):
        big_sped += f"|I250|{i}|0001|100,00|D|1|HISTORICO {i}||\r\n"

    sped_path = tmp_path / "sped_big.txt"
    sped_path.write_bytes(big_sped.encode("latin-1"))

    result = parse_sped_file(str(sped_path))
    assert len(result["registros"]["I250"]) == 1000

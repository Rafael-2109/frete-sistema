"""Testa diff estrutural SPED nosso vs SPED contadora (ground truth)."""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent.parent / ".claude" / "skills" / \
    "comparando-sped-ground-truth" / "scripts"
sys.path.insert(0, str(SKILL_DIR))

from diff_truth import (
    DiffFinding,
    diff_registros_presentes,
    diff_campos_preenchidos,
    diff_estrutural_completo,
)


def _make(registros: dict) -> dict:
    return {"metadata": {}, "registros": registros}


def test_diff_registros_ausentes_no_nosso():
    """Ground truth tem J932; nosso nao tem -> finding."""
    ground = _make({"J932": [{"IDENT_NOM": "Tamiris"}], "0000": [{"CNPJ": "..."}]})
    nosso = _make({"0000": [{"CNPJ": "..."}]})

    findings = diff_registros_presentes(nosso, ground)
    j932 = [f for f in findings if f.registro == "J932"]
    assert len(j932) == 1
    assert isinstance(j932[0], DiffFinding)  # usa o import
    assert j932[0].tipo == "registro_ausente_nosso"


def test_diff_registros_extras_no_nosso():
    """Nosso tem registro inexistente no ground truth -> warning."""
    ground = _make({"0000": [{"CNPJ": "..."}]})
    nosso = _make({"0000": [{"CNPJ": "..."}], "Z999": [{"X": "Y"}]})

    findings = diff_registros_presentes(nosso, ground)
    assert any(f.tipo == "registro_extra_nosso" and f.registro == "Z999"
               for f in findings)


def test_diff_campos_nao_preenchidos():
    """I030 do ground tem NIRE; nosso tem NIRE vazio -> finding."""
    ground = _make({"I030": [{"NIRE": "12345", "CNPJ": "61724241000178"}]})
    nosso = _make({"I030": [{"NIRE": "", "CNPJ": "61724241000178"}]})

    findings = diff_campos_preenchidos(nosso, ground, registro="I030")
    assert any(f.tipo == "campo_vazio_nosso" and f.contexto.get("campo") == "NIRE"
               for f in findings)


def test_diff_campos_iguais_sem_findings():
    """Campos iguais — sem findings."""
    same = _make({"I030": [{"NIRE": "12345", "CNPJ": "61724241000178"}]})
    findings = diff_campos_preenchidos(same, same, registro="I030")
    assert findings == []


def test_diff_estrutural_completo():
    """Combina diff de registros + campos."""
    ground = _make({
        "0000": [{"CNPJ": "61724241000178"}],
        "I030": [{"NIRE": "12345"}],
        "J932": [{"IDENT_NOM": "Tamiris"}],
    })
    nosso = _make({
        "0000": [{"CNPJ": "61724241000178"}],
        "I030": [{"NIRE": ""}],
    })

    findings = diff_estrutural_completo(nosso, ground)
    tipos = {f.tipo for f in findings}
    assert "registro_ausente_nosso" in tipos
    assert "campo_vazio_nosso" in tipos


def test_diff_registro_obrigatorio_bloqueante():
    """Registro obrigatorio ausente eh BLOQUEANTE."""
    ground = _make({"I030": [{"NIRE": "12345"}], "0000": [{"CNPJ": "..."}]})
    nosso = _make({"0000": [{"CNPJ": "..."}]})

    findings = diff_registros_presentes(nosso, ground)
    i030_findings = [f for f in findings if f.registro == "I030"]
    assert len(i030_findings) == 1
    assert i030_findings[0].severidade == "BLOQUEANTE"


def test_diff_registro_condicional_warning():
    """Registro condicional ausente eh WARNING."""
    ground = _make({"J932": [{"IDENT_NOM": "Tamiris"}], "0000": [{"CNPJ": "..."}]})
    nosso = _make({"0000": [{"CNPJ": "..."}]})

    findings = diff_registros_presentes(nosso, ground)
    j932_findings = [f for f in findings if f.registro == "J932"]
    assert len(j932_findings) == 1
    assert j932_findings[0].severidade == "WARNING"


def test_diff_campos_zero_numerico_nao_ignorado():
    """Campo com valor 0 no ground e vazio no nosso deve gerar finding.

    Regressao do bug onde `if valor_ground` short-circuitava em 0 / False /
    outros falsy non-empty.
    """
    # Ground tem IND_ESC=0 (valor numerico valido), nosso esta vazio
    ground = _make({"I010": [{"IND_ESC": 0, "CNPJ": "61724241000178"}]})
    nosso = _make({"I010": [{"IND_ESC": "", "CNPJ": "61724241000178"}]})
    findings = diff_campos_preenchidos(nosso, ground, registro="I010")
    assert any(f.contexto.get("campo") == "IND_ESC" for f in findings), (
        "Finding deve ser gerado para valor 0 no ground vs vazio no nosso"
    )

    # Caso bool False
    ground_bool = _make({"X": [{"FLAG": False, "OUTRO": "y"}]})
    nosso_bool = _make({"X": [{"FLAG": "", "OUTRO": "y"}]})
    findings_bool = diff_campos_preenchidos(nosso_bool, ground_bool, registro="X")
    assert any(f.contexto.get("campo") == "FLAG" for f in findings_bool)

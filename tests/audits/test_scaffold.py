# tests/audits/test_scaffold.py
import subprocess, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]

def test_scaffold_reference_emite_secoes(tmp_path):
    out = tmp_path / "x.md"
    subprocess.run([sys.executable, "scripts/docs/novo_artefato.py", "--tipo", "reference",
                    "--tema", "frete", "--hub", "docs/INDEX.md", "--out", str(out)], cwd=REPO, check=True)
    txt = out.read_text(encoding="utf-8")
    assert "doc:meta" in txt and "tipo: reference" in txt
    # Onda 4: reference nao exige mais '## Fontes' (calibracao hibrida); Papel permanece.
    assert "**Papel:**" in txt

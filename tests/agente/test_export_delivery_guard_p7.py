"""P7 (#787) — guard determinístico de ENTREGA na skill exportando-arquivos.

A #787 declarou sucesso e entregou uma URL para um arquivo QUEBRADO (404/vazio,
TMPDIR errado). O P1 corrigiu a causa (AGENTE_FILES_ROOT); este guard é a REDE DE
SEGURANÇA: após gerar o arquivo, confirma que ele existe no diretório servido e é
NÃO-VAZIO ANTES de declarar sucesso — coerente com a filosofia do blueprint
(guard-rails determinísticos previnem, verifiers shadow só detectam).

Frente 1 do P7 (calibração do judge GATE-1/E3) tem trabalho separado
(worktree feat+gate1-calibracao-judge) — não coberto aqui.

Roadmap: docs/superpowers/plans/2026-06-04-roadmap-correcoes-agente-787.md (P7)
"""
import importlib.util
import io
import json
import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_EXPORTAR = os.path.join(
    _REPO_ROOT, ".claude", "skills", "exportando-arquivos", "scripts", "exportar.py"
)


@pytest.fixture(scope="module")
def exportar():
    spec = importlib.util.spec_from_file_location("exportar_skill_p7", _EXPORTAR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# =====================================================================
# Guard puro — _verificar_entrega
# =====================================================================

class TestVerificarEntrega:
    def test_existing_nonempty_file_ok(self, exportar, tmp_path):
        f = tmp_path / "ok.xlsx"
        f.write_bytes(b"conteudo real do arquivo")
        ok, motivo = exportar._verificar_entrega(str(f))
        assert ok is True

    def test_missing_file_fails(self, exportar, tmp_path):
        ok, motivo = exportar._verificar_entrega(str(tmp_path / "nao_existe.xlsx"))
        assert ok is False
        assert motivo  # motivo nao-vazio

    def test_empty_file_fails(self, exportar, tmp_path):
        f = tmp_path / "vazio.xlsx"
        f.write_bytes(b"")
        ok, motivo = exportar._verificar_entrega(str(f))
        assert ok is False
        assert "vazio" in motivo.lower()

    def test_none_path_fails(self, exportar):
        ok, _ = exportar._verificar_entrega(None)
        assert ok is False


# =====================================================================
# Wiring no main() — declarar sucesso SO se a entrega passou
# =====================================================================

class TestMainDeliveryGuardWiring:
    def _run_main(self, exportar, monkeypatch, capsys, fake_filepath, fake_name):
        monkeypatch.setattr(exportar, "gerar_excel", lambda *a, **k: (fake_filepath, fake_name))
        monkeypatch.setattr(sys, "argv", ["exportar.py", "--formato", "excel", "--nome", "rel"])
        monkeypatch.setattr(sys, "stdin", io.StringIO('{"dados": [{"a": 1}]}'))
        exportar.main()
        return json.loads(capsys.readouterr().out)

    def test_main_blocks_empty_generated_file(self, exportar, monkeypatch, capsys, tmp_path):
        # gerar_excel produz arquivo VAZIO -> guard bloqueia (sem URL ao usuario).
        vazio = tmp_path / "vazio_rel.xlsx"
        vazio.write_bytes(b"")
        out = self._run_main(exportar, monkeypatch, capsys, str(vazio), vazio.name)
        assert out["sucesso"] is False
        assert out.get("arquivo") is None

    def test_main_accepts_nonempty_generated_file(self, exportar, monkeypatch, capsys, tmp_path):
        # gerar_excel produz arquivo real nao-vazio -> sucesso com URL.
        cheio = tmp_path / "cheio_rel.xlsx"
        cheio.write_bytes(b"xlsx bytes reais aqui")
        out = self._run_main(exportar, monkeypatch, capsys, str(cheio), cheio.name)
        assert out["sucesso"] is True
        assert out["arquivo"]["nome"] == cheio.name

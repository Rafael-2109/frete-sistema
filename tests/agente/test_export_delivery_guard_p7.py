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


# =====================================================================
# Formato md/txt (2026-06-10) — copiar_texto + guard de entrega
# =====================================================================
# Caso real (conversa Rafael 10/06): agente precisou entregar dump .md e a
# skill so gerava Excel/CSV/JSON — workaround manual com risco de TMPDIR.
# O formato 'md' copia um arquivo de texto JA ESCRITO para o diretorio
# servido, com o MESMO guard de entrega dos demais formatos.

class TestCopiarTexto:
    def test_copia_md_para_diretorio_servido(self, exportar, monkeypatch, tmp_path):
        servido = tmp_path / "servido"
        servido.mkdir()
        monkeypatch.setattr(exportar, "get_upload_folder", lambda: str(servido))
        origem = tmp_path / "relatorio.md"
        origem.write_text("# Dump\nconteudo", encoding="utf-8")

        filepath, filename = exportar.copiar_texto(str(origem), "relatorio")
        assert filepath.startswith(str(servido))
        assert filename.endswith(".md")
        ok, _ = exportar._verificar_entrega(filepath)
        assert ok

    def test_txt_tambem_suportado(self, exportar, monkeypatch, tmp_path):
        servido = tmp_path / "servido"
        servido.mkdir()
        monkeypatch.setattr(exportar, "get_upload_folder", lambda: str(servido))
        origem = tmp_path / "notas.txt"
        origem.write_text("texto", encoding="utf-8")
        _, filename = exportar.copiar_texto(str(origem), None)
        assert filename.endswith(".txt")

    def test_extensao_nao_textual_rejeitada(self, exportar, tmp_path):
        origem = tmp_path / "binario.bin"
        origem.write_bytes(b"\x00\x01")
        with pytest.raises(ValueError):
            exportar.copiar_texto(str(origem), "x")

    def test_origem_inexistente_rejeitada(self, exportar):
        with pytest.raises(FileNotFoundError):
            exportar.copiar_texto("/tmp/nao-existe-xyz.md", "x")

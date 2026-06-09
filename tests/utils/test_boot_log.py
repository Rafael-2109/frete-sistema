"""Tests para o helper boot_log (BUG #1 — logs de boot poluindo stdout das tools).

Contrato:
- boot_log() escreve SEMPRE em sys.stderr (NUNCA em stdout — stdout e reservado
  para o resultado de scripts CLI consumidos pelo agente).
- Silenciavel via env NACOM_QUIET_BOOT (1/true/yes/on). O agente seta essa env
  ao rodar comandos Bash, deixando o output limpo.
- force=True ignora o silenciamento (erros de boot que devem sempre aparecer).
"""
import pytest


def test_boot_log_emite_em_stderr_nunca_stdout(monkeypatch, capsys):
    """Sem NACOM_QUIET_BOOT: mensagem vai para stderr, jamais para stdout."""
    monkeypatch.delenv('NACOM_QUIET_BOOT', raising=False)
    from app.utils.boot_log import boot_log

    boot_log('✅ tipos registrados')

    captured = capsys.readouterr()
    assert captured.out == '', 'boot_log NUNCA deve escrever em stdout'
    assert '✅ tipos registrados' in captured.err


def test_boot_log_silenciado_quando_quiet(monkeypatch, capsys):
    """NACOM_QUIET_BOOT=1 suprime totalmente a saida."""
    monkeypatch.setenv('NACOM_QUIET_BOOT', '1')
    from app.utils.boot_log import boot_log

    boot_log('✅ tipos registrados')

    captured = capsys.readouterr()
    assert captured.out == ''
    assert captured.err == ''


@pytest.mark.parametrize('valor', ['1', 'true', 'TRUE', 'yes', 'on', ' on '])
def test_boot_log_silenciado_para_valores_truthy(monkeypatch, capsys, valor):
    """Variacoes truthy da env silenciam."""
    monkeypatch.setenv('NACOM_QUIET_BOOT', valor)
    from app.utils.boot_log import boot_log

    boot_log('boot msg')

    assert capsys.readouterr().err == ''


@pytest.mark.parametrize('valor', ['0', '', 'false', 'no'])
def test_boot_log_emite_para_valores_falsy(monkeypatch, capsys, valor):
    """Valores nao-truthy NAO silenciam (boot_log emite em stderr)."""
    monkeypatch.setenv('NACOM_QUIET_BOOT', valor)
    from app.utils.boot_log import boot_log

    boot_log('boot msg')

    assert 'boot msg' in capsys.readouterr().err


def test_boot_log_force_ignora_silenciamento(monkeypatch, capsys):
    """force=True emite em stderr mesmo com NACOM_QUIET_BOOT=1 (erros de boot)."""
    monkeypatch.setenv('NACOM_QUIET_BOOT', '1')
    from app.utils.boot_log import boot_log

    boot_log('⚠️ erro ao registrar tipos', force=True)

    captured = capsys.readouterr()
    assert captured.out == ''
    assert '⚠️ erro ao registrar tipos' in captured.err

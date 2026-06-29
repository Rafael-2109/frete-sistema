"""
F1.1: helper compartilhado de env do subprocesso CLI do Agent SDK.

Extrai o literal hoje duplicado (web client.py:1629-1635 inline + fork
client.py) para um modulo puro consumido por AMBOS os clients — mata o drift
(o fork ficou sem o env por meses; ver F0).
"""
from app.agente.sdk.sdk_runtime import build_subprocess_env


def test_build_subprocess_env_retorna_chaves_canonicas():
    env = build_subprocess_env()
    assert env['HOME'] == '/tmp'
    assert env['CLAUDE_CODE_STREAM_CLOSE_TIMEOUT'] == '240000'


def test_build_subprocess_env_retorna_dict_novo_a_cada_chamada():
    """Cada client recebe sua propria copia — mutar uma nao afeta a outra."""
    a = build_subprocess_env()
    a['EXTRA'] = 'x'
    b = build_subprocess_env()
    assert 'EXTRA' not in b

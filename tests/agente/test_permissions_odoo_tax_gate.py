"""Testes do Gate R11.1 — BLOQUEIO de action_update_taxes (FASE 2 / T2.1).

Cobre o branch adicionado em app/agente/config/permissions.py:can_use_tool que
BLOQUEIA (deny UNIVERSAL — sem allowlist) qualquer tentativa de executar
`action_update_taxes` em sale.order via Bash/Write/Edit.

Motivacao (R11.1, system_prompt): `action_update_taxes` zera `tax_id` quando a
`fiscal_position` mapeia impostos para vazio (ex.: posicao 49 "SAIDA -
TRANSFERENCIA ENTRE FILIAIS"). O metodo correto e' `onchange_l10n_br_calcular_imposto`.
Anti-padrao real (sessao 4722693c, 14/05/2026): agente zerou impostos de 30 linhas
de um SO ja' faturado.

Premissa verificada (FASE 2): o agente NAO tem skill nomeada para isso — ele executa
via script Python ad-hoc (`execute_kw('sale.order','action_update_taxes',...)`) rodado
por Bash, ou escrito em /tmp via Write/Edit. Por isso o gate intercepta pelo CONTEUDO
(defesa best-effort, evasivel por string dinamica) e roda ANTES dos early-returns de
/tmp do Write/Edit. E' defesa-em-profundidade do principio que permanece no prompt.
"""
import asyncio

import pytest
from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

from app.agente.config.permissions import (
    can_use_tool,
    clear_current_user_id,
    set_current_user_id,
)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _reset_contextvars():
    clear_current_user_id()
    yield
    clear_current_user_id()


@pytest.fixture(autouse=True)
def _force_tax_gate_on(monkeypatch):
    """Forca o gate ON por teste (o kill-switch e' testado explicitamente)."""
    from app.agente.config import feature_flags as ff
    monkeypatch.setattr(ff, "USE_ODOO_TAX_GATE", True, raising=False)
    yield


def _call(tool_name: str, tool_input: dict):
    return _run(can_use_tool(tool_name, tool_input, context=None))


# Vetor real de execucao (do GOTCHAS.md:190 e do anti-padrao 4722693c)
_EXEC_BASH = (
    "python3 -c \"import xmlrpc.client; "
    "models.execute_kw(db, uid, pwd, 'sale.order', 'action_update_taxes', [[72921]])\""
)
_EXEC_SCRIPT = (
    "from app.odoo.utils.connection import OdooConnection\n"
    "odoo = OdooConnection()\n"
    "odoo.execute_kw('sale.order', 'action_update_taxes', [[72921]])\n"
)


# ============================================================================
# DENY: tentativa de EXECUTAR action_update_taxes (bloqueio universal)
# ============================================================================
class TestGateBloqueia:
    def test_bash_inline_execute_kw_aspas_simples(self):
        r = _call('Bash', {'command': _EXEC_BASH})
        assert isinstance(r, PermissionResultDeny)
        assert 'onchange' in r.message.lower() or 'imposto' in r.message.lower()

    def test_bash_inline_aspas_duplas(self):
        cmd = 'python3 -c "odoo.execute_kw(\'sale.order\', \"action_update_taxes\", [[1]])"'
        r = _call('Bash', {'command': cmd})
        assert isinstance(r, PermissionResultDeny)

    def test_write_script_em_tmp(self):
        # O early-return de Write para /tmp NAO pode permitir o script proibido.
        r = _call('Write', {'file_path': '/tmp/fix_taxes.py', 'content': _EXEC_SCRIPT})
        assert isinstance(r, PermissionResultDeny)

    def test_edit_inserindo_metodo_proibido(self):
        r = _call('Edit', {
            'file_path': '/tmp/fix.py',
            'old_string': 'pass',
            'new_string': "odoo.execute_kw('sale.order', 'action_update_taxes', [[1]])",
        })
        assert isinstance(r, PermissionResultDeny)

    def test_bloqueio_e_universal_ate_para_admin(self):
        # Decisao Rafael (FASE 2): deny SEM allowlist — nem o admin executa pelo agente.
        set_current_user_id(1)
        r = _call('Bash', {'command': _EXEC_BASH})
        assert isinstance(r, PermissionResultDeny)


# ============================================================================
# ALLOW: investigacao/leitura e metodo correto NAO sao bloqueados
# ============================================================================
class TestGatePermite:
    def test_grep_do_metodo_e_investigacao(self):
        # Procurar/ler sobre o metodo (sem aspas de chamada, sem execucao) e' permitido.
        r = _call('Bash', {'command': 'grep -rn action_update_taxes app/ | head'})
        assert isinstance(r, PermissionResultAllow)

    def test_metodo_correto_onchange_permitido(self):
        cmd = (
            "python3 -c \"odoo.execute_kw('sale.order', "
            "'onchange_l10n_br_calcular_imposto', [[72921]])\""
        )
        r = _call('Bash', {'command': cmd})
        assert isinstance(r, PermissionResultAllow)

    def test_bash_comum_sem_metodo(self):
        r = _call('Bash', {'command': 'ls -la /tmp/agente_files'})
        assert isinstance(r, PermissionResultAllow)

    def test_write_tmp_comum(self):
        r = _call('Write', {'file_path': '/tmp/agente_files/x.csv', 'content': 'a,b,c\n'})
        assert isinstance(r, PermissionResultAllow)


# ============================================================================
# KILL-SWITCH: flag OFF nao bloqueia (rollback sem deploy)
# ============================================================================
class TestKillSwitch:
    def test_flag_off_permite_execucao(self, monkeypatch):
        from app.agente.config import feature_flags as ff
        monkeypatch.setattr(ff, "USE_ODOO_TAX_GATE", False, raising=False)
        r = _call('Bash', {'command': _EXEC_BASH})
        assert isinstance(r, PermissionResultAllow)

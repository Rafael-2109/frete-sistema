"""Testes da Restricao Estoque (gating de skills WRITE).

Cobre o bloco adicionado em app/agente/config/permissions.py:can_use_tool
que bloqueia para users nao-autorizados:
  - Skill('ajustando-quant-odoo')                                (qualquer modo)
  - Skill('transferindo-interno-odoo') com Indisponivel em args
  - Skill('planejando-pre-etapa-odoo') com executar-onda em args

Bug original (2026-05-26): Alice e outros operadores usavam o agente web para
ajustar estoque indevidamente. Apos este patch, apenas user_ids na whitelist
(default 1 = Rafael web, 55 = Rafael Teams) podem executar essas operacoes.
"""
import asyncio

import pytest
from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

from app.agente.config import permissions as perm_mod
from app.agente.config.permissions import (
    can_use_tool,
    clear_current_user_id,
    set_current_user_id,
)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _reset_contextvars():
    """Garante que cada teste comeca com user_id limpo."""
    clear_current_user_id()
    yield
    clear_current_user_id()


@pytest.fixture(autouse=True)
def _restore_enforcement(monkeypatch):
    """Forca enforcement ON e whitelist default (1, 55) por teste.

    Cada teste pode sobrescrever via monkeypatch para casos especificos.
    """
    from app.agente.config import feature_flags as ff
    monkeypatch.setattr(ff, "USE_ESTOQUE_RESTRICAO_ENFORCEMENT", True, raising=False)
    monkeypatch.setattr(ff, "ESTOQUE_RESTRICAO_ALLOWED_USER_IDS", {1, 55}, raising=False)
    yield


# ============================================================================
# Helpers
# ============================================================================
def _call(tool_name: str, tool_input: dict):
    return _run(can_use_tool(tool_name, tool_input, context=None))


# ============================================================================
# ALLOW: users autorizados
# ============================================================================
class TestUsersAutorizados:
    def test_user_1_pode_ajustar_quant(self):
        set_current_user_id(1)
        r = _call('Skill', {'skill': 'ajustando-quant-odoo', 'args': '--delta 10'})
        assert isinstance(r, PermissionResultAllow)

    def test_user_55_pode_ajustar_quant(self):
        set_current_user_id(55)
        r = _call('Skill', {'skill': 'ajustando-quant-odoo', 'args': '--valor-absoluto 0'})
        assert isinstance(r, PermissionResultAllow)

    def test_user_1_pode_transferir_para_indisponivel(self):
        set_current_user_id(1)
        r = _call('Skill', {
            'skill': 'transferindo-interno-odoo',
            'args': '--para-indisponivel --produto 12345',
        })
        assert isinstance(r, PermissionResultAllow)

    def test_user_1_pode_executar_onda(self):
        set_current_user_id(1)
        r = _call('Skill', {
            'skill': 'planejando-pre-etapa-odoo',
            'args': 'executar-onda 5 --ciclo INVENTARIO_2026_05',
        })
        assert isinstance(r, PermissionResultAllow)


# ============================================================================
# DENY: users nao-autorizados nas skills restritas
# ============================================================================
class TestUsersNaoAutorizados:
    def test_user_5_nao_pode_ajustar_quant_positivo(self):
        set_current_user_id(5)
        r = _call('Skill', {'skill': 'ajustando-quant-odoo', 'args': '--delta 100'})
        assert isinstance(r, PermissionResultDeny)
        assert 'restrita' in r.message.lower() or 'ajuste' in r.message.lower()

    def test_user_5_nao_pode_ajustar_quant_negativo(self):
        set_current_user_id(5)
        r = _call('Skill', {'skill': 'ajustando-quant-odoo', 'args': '--delta -50'})
        assert isinstance(r, PermissionResultDeny)

    def test_user_5_nao_pode_zerar_quant(self):
        set_current_user_id(5)
        r = _call('Skill', {'skill': 'ajustando-quant-odoo', 'args': '--valor-absoluto 0'})
        assert isinstance(r, PermissionResultDeny)

    def test_user_5_bloqueado_transferir_para_indisponivel_flag(self):
        set_current_user_id(5)
        r = _call('Skill', {
            'skill': 'transferindo-interno-odoo',
            'args': '--para-indisponivel --produto 12345',
        })
        assert isinstance(r, PermissionResultDeny)

    def test_user_5_bloqueado_quando_indisponivel_no_loc_destino(self):
        set_current_user_id(5)
        r = _call('Skill', {
            'skill': 'transferindo-interno-odoo',
            'args': '--loc-destino "FB/Indisponivel" --qty 100',
        })
        assert isinstance(r, PermissionResultDeny)

    def test_user_5_bloqueado_quando_indisponivel_acentuado(self):
        """Cobre variantes com acento Indisponível."""
        set_current_user_id(5)
        r = _call('Skill', {
            'skill': 'transferindo-interno-odoo',
            'args': '--loc-origem "FB/Indisponível" --qty 50',
        })
        assert isinstance(r, PermissionResultDeny)

    def test_user_5_bloqueado_quando_indisponivel_uppercase(self):
        set_current_user_id(5)
        r = _call('Skill', {
            'skill': 'transferindo-interno-odoo',
            'args': '--loc-destino "FB/INDISPONIVEL" --qty 50',
        })
        assert isinstance(r, PermissionResultDeny)

    def test_user_5_bloqueado_executar_onda(self):
        set_current_user_id(5)
        r = _call('Skill', {
            'skill': 'planejando-pre-etapa-odoo',
            'args': 'executar-onda 5 --ciclo X',
        })
        assert isinstance(r, PermissionResultDeny)


# ============================================================================
# ALLOW: operacoes permitidas (nao restritas)
# ============================================================================
class TestOperacoesPermitidas:
    def test_user_5_pode_consultar_quant(self):
        """consultando-quant-odoo e READ-only: permitido para todos."""
        set_current_user_id(5)
        r = _call('Skill', {'skill': 'consultando-quant-odoo', 'args': '--produto 123'})
        assert isinstance(r, PermissionResultAllow)

    def test_user_5_pode_transferir_lote_a_lote_sem_indisponivel(self):
        """Modo A da Skill 2 sem Indisponivel: movimentacao legitima."""
        set_current_user_id(5)
        r = _call('Skill', {
            'skill': 'transferindo-interno-odoo',
            'args': '--lote-origem 099/26 --lote-destino 100/26 --produto X',
        })
        assert isinstance(r, PermissionResultAllow)

    def test_user_5_pode_planejar_pre_etapa(self):
        """Modo planejar (banco local apenas, sem WRITE Odoo): permitido."""
        set_current_user_id(5)
        r = _call('Skill', {
            'skill': 'planejando-pre-etapa-odoo',
            'args': 'planejar --filial CD',
        })
        assert isinstance(r, PermissionResultAllow)

    def test_user_5_pode_propor_pre_etapa(self):
        set_current_user_id(5)
        r = _call('Skill', {
            'skill': 'planejando-pre-etapa-odoo',
            'args': 'propor --ciclo INVENTARIO_2026_05',
        })
        assert isinstance(r, PermissionResultAllow)

    def test_user_5_pode_aprovar_onda(self):
        """aprovar-onda altera banco local, nao Odoo: permitido."""
        set_current_user_id(5)
        r = _call('Skill', {
            'skill': 'planejando-pre-etapa-odoo',
            'args': 'aprovar-onda 5 --hash abc123',
        })
        assert isinstance(r, PermissionResultAllow)

    def test_user_5_pode_usar_skill_nao_restrita(self):
        set_current_user_id(5)
        r = _call('Skill', {'skill': 'cotando-frete', 'args': '--destino SP'})
        assert isinstance(r, PermissionResultAllow)

    def test_user_5_pode_chamar_bash_qualquer(self):
        """Restricao NAO se aplica a Bash (escopo confirmado com Rafael)."""
        set_current_user_id(5)
        r = _call('Bash', {
            'command': 'python .claude/skills/ajustando-quant-odoo/scripts/ajustar_quant.py --confirmar',
            'description': 'Roda script direto',
        })
        assert isinstance(r, PermissionResultAllow)


# ============================================================================
# Fail-closed & kill-switch
# ============================================================================
class TestFailClosedEKillSwitch:
    def test_sem_user_id_bloqueia_skill_restrita(self):
        """Fail-closed: sem user_id no contexto, NEGA skill restrita."""
        # Nao seta user_id intencionalmente (fixture limpa antes)
        r = _call('Skill', {'skill': 'ajustando-quant-odoo', 'args': '--delta 10'})
        assert isinstance(r, PermissionResultDeny)

    def test_kill_switch_desliga_tudo(self, monkeypatch):
        """AGENT_ESTOQUE_RESTRICAO_ENFORCEMENT=false -> tudo permitido."""
        from app.agente.config import feature_flags as ff
        monkeypatch.setattr(ff, "USE_ESTOQUE_RESTRICAO_ENFORCEMENT", False, raising=False)

        set_current_user_id(5)
        r = _call('Skill', {'skill': 'ajustando-quant-odoo', 'args': '--delta 10'})
        assert isinstance(r, PermissionResultAllow)

    def test_whitelist_dinamica(self, monkeypatch):
        """Adicionar user_id na whitelist via env var -> passa a permitir."""
        from app.agente.config import feature_flags as ff
        monkeypatch.setattr(ff, "ESTOQUE_RESTRICAO_ALLOWED_USER_IDS", {1, 55, 99}, raising=False)

        set_current_user_id(99)
        r = _call('Skill', {'skill': 'ajustando-quant-odoo', 'args': '--delta 10'})
        assert isinstance(r, PermissionResultAllow)


# ============================================================================
# Classificador puro (sem ContextVar)
# ============================================================================
class TestClassifyEstoqueRestricao:
    def test_skill_irrelevante_retorna_none(self):
        assert perm_mod._classify_estoque_restricao('Skill', {'skill': 'cotando-frete'}) is None

    def test_tool_nao_skill_retorna_none(self):
        assert perm_mod._classify_estoque_restricao('Bash', {'command': 'rm -rf /'}) is None

    def test_ajustar_quant_sempre_restrito(self):
        info = perm_mod._classify_estoque_restricao(
            'Skill', {'skill': 'ajustando-quant-odoo', 'args': ''}
        )
        assert info is not None
        assert info['reason'] == 'ajuste_quant'

    def test_transfer_sem_indisponivel_nao_restrito(self):
        info = perm_mod._classify_estoque_restricao(
            'Skill',
            {'skill': 'transferindo-interno-odoo', 'args': '--lote-origem X --lote-destino Y'},
        )
        assert info is None

    def test_transfer_com_indisponivel_restrito(self):
        info = perm_mod._classify_estoque_restricao(
            'Skill',
            {'skill': 'transferindo-interno-odoo', 'args': '--para-indisponivel'},
        )
        assert info is not None
        assert info['reason'] == 'transfer_indisponivel'

    def test_pre_etapa_executar_restrito(self):
        info = perm_mod._classify_estoque_restricao(
            'Skill',
            {'skill': 'planejando-pre-etapa-odoo', 'args': 'executar-onda 5'},
        )
        assert info is not None
        assert info['reason'] == 'pre_etapa_executar_onda'

    def test_pre_etapa_planejar_nao_restrito(self):
        info = perm_mod._classify_estoque_restricao(
            'Skill',
            {'skill': 'planejando-pre-etapa-odoo', 'args': 'planejar'},
        )
        assert info is None


# ============================================================================
# Parser de env var
# ============================================================================
class TestParserEnvVar:
    def test_parser_csv_simples(self):
        from app.agente.config.feature_flags import _parse_allowed_user_ids_csv
        assert _parse_allowed_user_ids_csv("1,55") == {1, 55}

    def test_parser_csv_com_espacos(self):
        from app.agente.config.feature_flags import _parse_allowed_user_ids_csv
        assert _parse_allowed_user_ids_csv(" 1 , 55 , 99 ") == {1, 55, 99}

    def test_parser_csv_vazio(self):
        from app.agente.config.feature_flags import _parse_allowed_user_ids_csv
        assert _parse_allowed_user_ids_csv("") == set()
        assert _parse_allowed_user_ids_csv(None) == set()  # type: ignore

    def test_parser_csv_ignora_invalido(self):
        from app.agente.config.feature_flags import _parse_allowed_user_ids_csv
        # 'abc' invalido logado e ignorado; numericos passam
        assert _parse_allowed_user_ids_csv("1,abc,55") == {1, 55}

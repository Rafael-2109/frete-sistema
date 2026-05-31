"""Tests para app/utils/odoo_audit_helpers.py — Audit Hook deterministico Odoo.

Cobertura:
- whitelist filtra metodos non-write
- flag desligada nao grava
- sucesso registra status='EXECUTADO'
- falha registra status='FALHA_ODOO' com erro_msg
- ENV vars populam session_id/tool_use_id/agent_type/executado_por
- external_id deterministico cabe em VARCHAR(64)
- sanitize_for_json processa Decimal/datetime
- savepoint isola falha do hook
- odoo_id extraido de args[0][0]
"""
from datetime import datetime
from decimal import Decimal
import os
from unittest.mock import patch

from sqlalchemy import text

from app.utils.odoo_audit_helpers import (
    METODOS_WRITE_AUDITADOS,
    _calcular_external_id,
    _extrair_odoo_id,
    _flag_ativa,
    _resolver_contexto,
    registrar_chamada_odoo,
)


def _count_audit(db, session_id):
    return db.session.execute(
        text(
            "SELECT COUNT(*) FROM operacao_odoo_auditoria WHERE session_id=:sid"
        ),
        {'sid': session_id},
    ).scalar()


def _row_audit(db, session_id):
    return db.session.execute(
        text(
            "SELECT modelo_odoo, metodo_odoo, status, erro_msg, tempo_execucao_ms, "
            "tool_use_id, agent_type, executado_por, odoo_id, payload_json, resposta_json "
            "FROM operacao_odoo_auditoria WHERE session_id=:sid ORDER BY id DESC LIMIT 1"
        ),
        {'sid': session_id},
    ).fetchone()


# ---------------------------------------------------------------------
# Whitelist
# ---------------------------------------------------------------------

def test_whitelist_contem_metodos_criticos():
    """Whitelist deve incluir as primitivas CRUD + acoes Skill 8."""
    criticos = {
        'write', 'create', 'unlink',
        'action_apply_inventory', 'action_assign', 'button_validate',
        'button_confirm', 'button_approve',
        'action_gerar_po_dfe', 'action_processar_arquivo_manual',
        'action_create_invoice', 'action_post',
        'action_liberar_faturamento', 'action_gerar_nfe',
        'action_cancel',
    }
    faltando = criticos - METODOS_WRITE_AUDITADOS
    assert not faltando, f'Metodos criticos faltando na whitelist: {faltando}'


def test_whitelist_NAO_contem_metodos_read():
    """Whitelist NAO deve incluir search/read/fields_get."""
    leitura = {'search', 'read', 'search_read', 'search_count', 'fields_get', 'name_get'}
    intersect = leitura & METODOS_WRITE_AUDITADOS
    assert not intersect, f'Metodos READ no whitelist (false positive): {intersect}'


# ---------------------------------------------------------------------
# Feature flag
# ---------------------------------------------------------------------

def test_flag_default_false_sem_env():
    """Flag default e False quando ENV ausente."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop('AGENT_ODOO_AUDIT_HOOK', None)
        assert _flag_ativa() is False


def test_flag_ativa_com_true():
    with patch.dict(os.environ, {'AGENT_ODOO_AUDIT_HOOK': 'true'}):
        assert _flag_ativa() is True


def test_flag_ativa_com_1():
    with patch.dict(os.environ, {'AGENT_ODOO_AUDIT_HOOK': '1'}):
        assert _flag_ativa() is True


def test_flag_inativa_com_false(db):
    """Quando flag OFF, registrar_chamada_odoo NAO grava nada."""
    sid = 'test-flag-off-001'
    with patch.dict(os.environ, {
        'AGENT_ODOO_AUDIT_HOOK': 'false',
        'AGENT_SESSION_ID': sid,
    }):
        registrar_chamada_odoo(
            model='stock.quant', method='write',
            args=[[1], {'inventory_quantity': 1.0}], kwargs={},
            resultado=True, tempo_ms=10, erro=None,
        )
    assert _count_audit(db, sid) == 0


# ---------------------------------------------------------------------
# External ID
# ---------------------------------------------------------------------

def test_external_id_cabe_em_varchar_64():
    eid = _calcular_external_id(
        'sessao-completa-com-uuid-longo-12345678',
        'toolu_01abcdef_long_id_xpto',
        'stock.move.line', 'write', [[1, 2, 3], {'lot_id': 99}],
    )
    assert len(eid) <= 64, f'external_id muito longo: {len(eid)} chars'
    assert eid.startswith('aud:')


def test_external_id_session_ausente_usa_noctx():
    eid = _calcular_external_id(None, None, 'stock.quant', 'write', [[1]])
    assert 'noctx' in eid
    assert 'notui' in eid


def test_external_id_unico_por_chamada():
    """Mesmos params em momentos diferentes geram external_ids diferentes (ms)."""
    eid1 = _calcular_external_id('s1', 't1', 'stock.quant', 'write', [[1]])
    import time
    time.sleep(0.002)
    eid2 = _calcular_external_id('s1', 't1', 'stock.quant', 'write', [[1]])
    assert eid1 != eid2


# ---------------------------------------------------------------------
# Extrair odoo_id
# ---------------------------------------------------------------------

def test_extrair_odoo_id_lista():
    assert _extrair_odoo_id([[12345], {}]) == 12345


def test_extrair_odoo_id_int_direto():
    assert _extrair_odoo_id([12345]) == 12345


def test_extrair_odoo_id_args_vazios():
    assert _extrair_odoo_id([]) is None
    assert _extrair_odoo_id([[]]) is None


def test_extrair_odoo_id_dict_args_retorna_none():
    """args[0] = dict (create) nao tem ID ainda."""
    assert _extrair_odoo_id([{'product_id': 1, 'qty': 5.0}]) is None


# ---------------------------------------------------------------------
# Contexto via ENV
# ---------------------------------------------------------------------

def test_resolver_contexto_completo():
    with patch.dict(os.environ, {
        'AGENT_SESSION_ID': 'sid-001',
        'AGENT_TOOL_USE_ID': 'tu_abc',
        'AGENT_TYPE': 'gestor-estoque-odoo',
        'AGENT_USER_NAME': 'rafael',
    }):
        ctx = _resolver_contexto()
        assert ctx['session_id'] == 'sid-001'
        assert ctx['tool_use_id'] == 'tu_abc'
        assert ctx['agent_type'] == 'gestor-estoque-odoo'
        assert ctx['executado_por'] == 'rafael'


def test_resolver_contexto_ausente_usa_defaults():
    with patch.dict(os.environ, {}, clear=False):
        for k in ('AGENT_SESSION_ID', 'AGENT_TOOL_USE_ID', 'AGENT_TYPE', 'AGENT_USER_NAME'):
            os.environ.pop(k, None)
        ctx = _resolver_contexto()
        assert ctx['session_id'] is None
        assert ctx['tool_use_id'] is None
        assert ctx['agent_type'] == 'cli'
        assert ctx['executado_por'] == 'odoo_audit_hook'


# ---------------------------------------------------------------------
# Integracao completa registrar_chamada_odoo
# ---------------------------------------------------------------------

def test_registra_sucesso(db):
    sid = 'test-sucesso-001'
    with patch.dict(os.environ, {
        'AGENT_ODOO_AUDIT_HOOK': 'true',
        'AGENT_SESSION_ID': sid,
        'AGENT_TOOL_USE_ID': 'tu_test_001',
        'AGENT_TYPE': 'gestor-estoque-odoo',
        'AGENT_USER_NAME': 'rafael_teste',
    }):
        registrar_chamada_odoo(
            model='stock.quant', method='write',
            args=[[999], {'inventory_quantity': 42.5}],
            kwargs={}, resultado=True, tempo_ms=87, erro=None,
        )
    row = _row_audit(db, sid)
    assert row is not None
    assert row[0] == 'stock.quant'
    assert row[1] == 'write'
    assert row[2] == 'EXECUTADO'
    assert row[3] is None  # erro_msg
    assert row[4] == 87  # tempo_ms
    assert row[5] == 'tu_test_001'
    assert row[6] == 'gestor-estoque-odoo'
    assert row[7] == 'rafael_teste'
    assert row[8] == 999  # odoo_id extraido de args[0][0]


def test_registra_falha(db):
    sid = 'test-falha-001'
    with patch.dict(os.environ, {
        'AGENT_ODOO_AUDIT_HOOK': 'true',
        'AGENT_SESSION_ID': sid,
        'AGENT_TOOL_USE_ID': 'tu_falha',
    }):
        try:
            raise ValueError('Empresas incompatíveis nos registros')
        except ValueError as e:
            registrar_chamada_odoo(
                model='stock.picking', method='button_validate',
                args=[[12345]], kwargs={}, resultado=None,
                tempo_ms=200, erro=e,
            )
    row = _row_audit(db, sid)
    assert row is not None
    assert row[2] == 'FALHA_ODOO'
    assert row[3] is not None and 'Empresas incomp' in row[3]


def test_metodo_fora_whitelist_nao_registra(db):
    """search/read NAO sao auditados."""
    sid = 'test-read-001'
    with patch.dict(os.environ, {
        'AGENT_ODOO_AUDIT_HOOK': 'true',
        'AGENT_SESSION_ID': sid,
    }):
        registrar_chamada_odoo(
            model='stock.quant', method='read',
            args=[[1, 2, 3]], kwargs={'fields': ['quantity']},
            resultado=[{'id': 1, 'quantity': 5.0}],
            tempo_ms=15, erro=None,
        )
        registrar_chamada_odoo(
            model='stock.quant', method='search',
            args=[[('id', '>', 0)]], kwargs={},
            resultado=[1, 2, 3], tempo_ms=12, erro=None,
        )
    assert _count_audit(db, sid) == 0


def test_sanitize_payload_com_decimal(db):
    """Payload com Decimal NAO quebra JSONB."""
    sid = 'test-decimal-001'
    with patch.dict(os.environ, {
        'AGENT_ODOO_AUDIT_HOOK': 'true',
        'AGENT_SESSION_ID': sid,
    }):
        registrar_chamada_odoo(
            model='account.move', method='write',
            args=[[100], {
                'amount_total': Decimal('1234.56'),
                'data_emissao': datetime(2026, 5, 28, 10, 30),
                'lines': [{'qty': Decimal('5.0'), 'price': Decimal('1.99')}],
            }],
            kwargs={}, resultado=True, tempo_ms=50, erro=None,
        )
    row = _row_audit(db, sid)
    assert row is not None
    payload = row[9]  # payload_json
    assert payload is not None
    # Decimal serializado nao quebra JSONB
    args_serial = payload['args']
    assert len(args_serial) == 2


def test_hook_nunca_propaga_excecao(db, monkeypatch):
    """Se OperacaoOdooAuditoria.registrar levantar excecao, helper engole."""
    sid = 'test-engole-001'

    def boom(*_a, **_kw):
        raise RuntimeError('Simulated sanitize failure')

    # Patcheia o symbol DENTRO do modulo helper, nao no de origem
    monkeypatch.setattr('app.utils.json_helpers.sanitize_for_json', boom)
    with patch.dict(os.environ, {
        'AGENT_ODOO_AUDIT_HOOK': 'true',
        'AGENT_SESSION_ID': sid,
    }):
        # NAO deve raise
        registrar_chamada_odoo(
            model='stock.quant', method='write',
            args=[[1], {}], kwargs={},
            resultado=True, tempo_ms=10, erro=None,
        )
    # Nada registrado (savepoint+except)
    assert _count_audit(db, sid) == 0

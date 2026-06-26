"""Testes do handoff de estado entre spawns de subagente (Rota B).

Conserta o elo partido: subagente gravava findings em /tmp (não atravessa
processo) e o principal nem lia nem repassava ao spawn N+1. Agora o findings
do spawn N é persistido em AgentSession.data['subagent_checkpoints'][agent_type]
(SubagentStop) e injetado INLINE no prompt do Task do spawn N+1 (PreToolUse).
"""
import json


# ─────────────────────────────────────────────────────────────────────────
# Ciclo 1: montar_contexto_subagente (função pura — molde montar_contexto_n2)
# ─────────────────────────────────────────────────────────────────────────

def test_montar_contexto_inclui_findings_e_instrucao_nao_refazer():
    """Checkpoint com findings -> bloco <checkpoint_subagente> com a instrução
    de não re-descobrir e os achados do spawn anterior."""
    from app.agente.sdk.subagent_checkpoint import montar_contexto_subagente

    bloco = montar_contexto_subagente(
        'gestor-estoque-odoo',
        {'findings': 'Quant 218550 lote P-15/05 = 17.004 un confirmado ao vivo.',
         'num_turns': 13},
    )

    assert '<checkpoint_subagente>' in bloco
    assert '</checkpoint_subagente>' in bloco
    # nomeia o especialista cujo trabalho está sendo herdado
    assert 'gestor-estoque-odoo' in bloco
    # carrega os achados do spawn anterior
    assert '218550' in bloco
    # instrui a NÃO redescobrir (o cerne da correção)
    assert 'NÃO' in bloco or 'não' in bloco
    # marca como contexto de sistema, não instrução do usuário (anti-injection)
    assert 'sistema' in bloco.lower()


def test_montar_contexto_vazio_retorna_string_vazia():
    """Sem checkpoint ou sem findings -> "" (degradação graciosa, sem injeção)."""
    from app.agente.sdk.subagent_checkpoint import montar_contexto_subagente

    assert montar_contexto_subagente('gestor-estoque-odoo', None) == ''
    assert montar_contexto_subagente('gestor-estoque-odoo', {}) == ''
    assert montar_contexto_subagente('gestor-estoque-odoo', {'findings': ''}) == ''
    assert montar_contexto_subagente('gestor-estoque-odoo', {'findings': '   '}) == ''


# ─────────────────────────────────────────────────────────────────────────
# Ciclo 2: extract_findings_from_transcript (lê o JSONL do path direto)
# ─────────────────────────────────────────────────────────────────────────

def _write_transcript(path, textos):
    """JSONL de subagente: mensagens assistant com blocos text + 1 tool_use."""
    with open(path, 'w') as f:
        for t in textos:
            f.write(json.dumps({
                'type': 'assistant',
                'message': {
                    'role': 'assistant',
                    'content': [
                        {'type': 'text', 'text': t},
                        {'type': 'tool_use', 'id': 'tu1', 'name': 'Bash',
                         'input': {'command': 'echo x'}},
                    ],
                },
            }) + '\n')
        f.write(json.dumps({'type': 'result', 'num_turns': 3}) + '\n')
    return str(path)


def test_extract_concatena_textos_assistant(tmp_path):
    """findings = concatenação dos blocos text das mensagens assistant."""
    from app.agente.sdk.subagent_checkpoint import extract_findings_from_transcript

    p = _write_transcript(tmp_path / 't.jsonl',
                          ['Quant 218550 = 17.004 confirmado.',
                           'Dry-run dos 4 ajustes: exit 4 (OK).'])
    out = extract_findings_from_transcript(p)
    assert '218550' in out
    assert 'Dry-run dos 4 ajustes' in out
    # não inclui o tool_use, só o texto (findings = raciocínio/conclusões)
    assert 'echo x' not in out


def test_extract_path_inexistente_retorna_vazio():
    """Path ausente/efêmero -> "" (sem exceção; degradação graciosa)."""
    from app.agente.sdk.subagent_checkpoint import extract_findings_from_transcript

    assert extract_findings_from_transcript('/tmp/nao-existe-xyz.jsonl') == ''
    assert extract_findings_from_transcript('') == ''
    assert extract_findings_from_transcript(None) == ''


def test_extract_trunca_em_max_chars(tmp_path):
    """findings longo é truncado para caber no orçamento do prompt do Task."""
    from app.agente.sdk.subagent_checkpoint import extract_findings_from_transcript

    p = _write_transcript(tmp_path / 'big.jsonl', ['A' * 5000])
    out = extract_findings_from_transcript(p, max_chars=1000)
    assert len(out) <= 1000


def test_extract_ignora_boot_de_skills_user_messages(tmp_path):
    """REGRESSÃO (bug PROD 2026-06-25): o boot do subagente injeta os SKILL.md
    como mensagens USER (<command-message>... + 'Base directory for this skill').
    Essas mensagens vêm PRIMEIRO e são enormes (24-34KB/skill). O findings deve
    ser SÓ o texto do ASSISTANT (os achados); se pegar o boot user, o checkpoint
    vira 8000 chars de corpo de skill truncado e a injeção não ajuda em nada."""
    from app.agente.sdk.subagent_checkpoint import extract_findings_from_transcript

    p = tmp_path / 'real.jsonl'
    with open(p, 'w') as f:
        # BOOT: o SDK injeta as skills como mensagens role=user (vêm primeiro)
        f.write(json.dumps({'type': 'user', 'message': {'role': 'user', 'content': [
            {'type': 'text', 'text': '<command-message>ajustando-quant-odoo</command-message>'},
            {'type': 'text', 'text': 'Base directory for this skill: /opt/.../skills/ajustando-quant-odoo\n\n# ajustando-quant-odoo (WRITE — átomo C1)...'},
        ]}}) + '\n')
        # ACHADOS REAIS: mensagem role=assistant
        f.write(json.dumps({'type': 'assistant', 'message': {'role': 'assistant', 'content': [
            {'type': 'text', 'text': 'Quant 218550 lote P-15/05 = 17.004 confirmado ao vivo. Dry-run OK.'},
            {'type': 'tool_use', 'id': 't1', 'name': 'Bash', 'input': {'command': 'x'}},
        ]}}) + '\n')
        f.write(json.dumps({'type': 'result', 'num_turns': 5}) + '\n')

    out = extract_findings_from_transcript(str(p))
    assert 'Quant 218550' in out                         # pegou o achado do assistant
    assert 'command-message' not in out                  # NÃO pegou o boot
    assert 'Base directory for this skill' not in out     # NÃO pegou o corpo da skill


# ─────────────────────────────────────────────────────────────────────────
# Ciclo 3: persist_checkpoint (UPSERT atômico) + load_checkpoint
# ─────────────────────────────────────────────────────────────────────────

def _fresh_session(sid):
    """Cria AgentSession limpa (remove run anterior). Chamar dentro de app_context."""
    from app.agente.models import AgentSession
    from app import db
    existing = AgentSession.query.filter_by(session_id=sid).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
    sess = AgentSession(session_id=sid, user_id=1, title='t', data={})
    db.session.add(sess)
    db.session.commit()
    return sess


def test_persist_then_load_roundtrip(app):
    from app.agente.sdk.subagent_checkpoint import (
        persist_checkpoint, load_checkpoint)
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        _fresh_session('sess-ckpt-1')
        ok = persist_checkpoint('sess-ckpt-1', 'gestor-estoque-odoo',
                                'Quant 218550 = 17.004 confirmado.',
                                {'num_turns': 13})
        assert ok is True

        ckpt = load_checkpoint('sess-ckpt-1', 'gestor-estoque-odoo')
        assert ckpt is not None
        assert '218550' in ckpt['findings']
        assert ckpt['num_turns'] == 13
        assert 'ended_at' in ckpt

        db.session.delete(AgentSession.query.filter_by(
            session_id='sess-ckpt-1').first())
        db.session.commit()


def test_persist_nao_apaga_subagent_costs_existente(app):
    """UPSERT do checkpoint usa chave própria — não pisa em subagent_costs (jsonb_set)."""
    from app.agente.sdk.subagent_checkpoint import persist_checkpoint, load_checkpoint
    from app import db
    from sqlalchemy.orm.attributes import flag_modified

    with app.app_context():
        sess = _fresh_session('sess-ckpt-2')
        sess.data['subagent_costs'] = {'version': 2, 'entries': [{'x': 1}]}
        flag_modified(sess, 'data')
        db.session.commit()

        persist_checkpoint('sess-ckpt-2', 'especialista-odoo', 'achei Y', {})

        db.session.refresh(sess)
        # checkpoint gravado E custo preservado
        assert load_checkpoint('sess-ckpt-2', 'especialista-odoo')['findings'] == 'achei Y'
        assert sess.data['subagent_costs']['entries'] == [{'x': 1}]

        db.session.delete(sess)
        db.session.commit()


def test_persist_mesmo_agent_type_sobrescreve_com_mais_recente(app):
    from app.agente.sdk.subagent_checkpoint import persist_checkpoint, load_checkpoint
    from app.agente.models import AgentSession
    from app import db

    with app.app_context():
        _fresh_session('sess-ckpt-3')
        persist_checkpoint('sess-ckpt-3', 'gestor-estoque-odoo', 'spawn 1', {})
        persist_checkpoint('sess-ckpt-3', 'gestor-estoque-odoo', 'spawn 2', {})

        ckpt = load_checkpoint('sess-ckpt-3', 'gestor-estoque-odoo')
        assert ckpt['findings'] == 'spawn 2'  # último vence (queremos o estado mais novo)

        db.session.delete(AgentSession.query.filter_by(
            session_id='sess-ckpt-3').first())
        db.session.commit()


def test_load_inexistente_retorna_none(app):
    from app.agente.sdk.subagent_checkpoint import load_checkpoint
    with app.app_context():
        _fresh_session('sess-ckpt-4')
        assert load_checkpoint('sess-ckpt-4', 'gestor-estoque-odoo') is None
        # session que nem existe -> None, sem exceção
        assert load_checkpoint('sess-nao-existe-zzz', 'x') is None

        from app.agente.models import AgentSession
        from app import db
        db.session.delete(AgentSession.query.filter_by(
            session_id='sess-ckpt-4').first())
        db.session.commit()


def test_persist_session_inexistente_retorna_false(app):
    """Race SubagentStop antes do commit da sessão -> rowcount 0 -> False (sem exceção)."""
    from app.agente.sdk.subagent_checkpoint import persist_checkpoint
    with app.app_context():
        assert persist_checkpoint('sess-nao-existe-yyy', 'x', 'f', {}) is False


# ─────────────────────────────────────────────────────────────────────────
# Ciclo 4: resolve_subagent_checkpoint_mode (flag off/shadow/on/admin)
# ─────────────────────────────────────────────────────────────────────────

def test_checkpoint_mode_default_off(monkeypatch):
    """De-risking: nasce DESLIGADO (sem env -> off)."""
    from app.agente.config.feature_flags import resolve_subagent_checkpoint_mode
    monkeypatch.delenv("AGENT_SUBAGENT_CHECKPOINT", raising=False)
    assert resolve_subagent_checkpoint_mode() == "off"


def test_checkpoint_mode_le_fresh_do_env(monkeypatch):
    """Lido fresh do env (rollout via env sem redeploy)."""
    from app.agente.config.feature_flags import resolve_subagent_checkpoint_mode
    for val in ("off", "shadow", "on"):
        monkeypatch.setenv("AGENT_SUBAGENT_CHECKPOINT", val)
        assert resolve_subagent_checkpoint_mode() == val


def test_checkpoint_mode_admin_canary(monkeypatch):
    """admin -> on para admin, shadow para os demais (canary)."""
    from app.agente.config.feature_flags import resolve_subagent_checkpoint_mode
    monkeypatch.setenv("AGENT_SUBAGENT_CHECKPOINT", "admin")
    assert resolve_subagent_checkpoint_mode(is_admin=True) == "on"
    assert resolve_subagent_checkpoint_mode(is_admin=False) == "shadow"


def test_checkpoint_mode_valor_invalido_vira_off(monkeypatch):
    from app.agente.config.feature_flags import resolve_subagent_checkpoint_mode
    monkeypatch.setenv("AGENT_SUBAGENT_CHECKPOINT", "banana")
    assert resolve_subagent_checkpoint_mode() == "off"


# ─────────────────────────────────────────────────────────────────────────
# Ciclo 5: SubagentStop hook PERSISTE o checkpoint (componente 2 — captura)
# ─────────────────────────────────────────────────────────────────────────

def _make_hooks(user_id=1):
    from app.agente.sdk.hooks import build_hooks
    return build_hooks(
        user_id=user_id, user_name='test_user', tool_failure_counts={},
        get_last_thinking=lambda: None, get_model_name=lambda: 'test-model',
        set_injected_ids=lambda x: None, resume_state=None,
    )


def _find_stop_handler(hooks):
    for ev_key, matchers in hooks.items():
        ev_name = ev_key if isinstance(ev_key, str) else getattr(ev_key, 'name', str(ev_key))
        if 'SubagentStop' in ev_name:
            for matcher in matchers:
                if hasattr(matcher, 'hooks') and matcher.hooks:
                    return matcher.hooks[0]
    return None


def _transcript_com_findings(path):
    """JSONL com texto (findings) + result (cost) — o SubagentStop usa ambos."""
    with open(path, 'w') as f:
        f.write(json.dumps({
            'type': 'assistant',
            'message': {'role': 'assistant', 'content': [
                {'type': 'text', 'text': 'Quant 218550 = 17.004 confirmado ao vivo.'},
            ], 'usage': {'input_tokens': 1200, 'output_tokens': 400}},
        }) + '\n')
        f.write(json.dumps({
            'type': 'result', 'total_cost_usd': 0.012, 'duration_ms': 8000,
            'num_turns': 4, 'usage': {'input_tokens': 1200, 'output_tokens': 400},
            'stop_reason': 'end_turn',
        }) + '\n')
    return str(path)


def test_subagent_stop_persiste_checkpoint_em_shadow(tmp_path, app, monkeypatch):
    """modo shadow -> persiste o findings em data['subagent_checkpoints']."""
    from app.agente.models import AgentSession
    from app import db
    import asyncio
    from unittest.mock import MagicMock

    monkeypatch.setenv("AGENT_SUBAGENT_CHECKPOINT", "shadow")
    with app.app_context():
        _fresh_session('sess-hook-1')
        handler = _find_stop_handler(_make_hooks())
        assert handler is not None
        asyncio.run(handler({
            'agent_id': 'aid-1', 'agent_type': 'gestor-estoque-odoo',
            'agent_transcript_path': _transcript_com_findings(tmp_path / 't.jsonl'),
            'session_id': 'sess-hook-1',
        }, None, MagicMock()))

        sess = AgentSession.query.filter_by(session_id='sess-hook-1').first()
        db.session.refresh(sess)
        ckpts = sess.data.get('subagent_checkpoints', {})
        assert 'gestor-estoque-odoo' in ckpts
        assert '218550' in ckpts['gestor-estoque-odoo']['findings']

        db.session.delete(sess)
        db.session.commit()


def test_subagent_stop_nao_persiste_checkpoint_em_off(tmp_path, app, monkeypatch):
    """modo off (default) -> NÃO grava checkpoint (zero mudança)."""
    from app.agente.models import AgentSession
    from app import db
    import asyncio
    from unittest.mock import MagicMock

    monkeypatch.setenv("AGENT_SUBAGENT_CHECKPOINT", "off")
    with app.app_context():
        _fresh_session('sess-hook-2')
        handler = _find_stop_handler(_make_hooks())
        asyncio.run(handler({
            'agent_id': 'aid-2', 'agent_type': 'gestor-estoque-odoo',
            'agent_transcript_path': _transcript_com_findings(tmp_path / 't2.jsonl'),
            'session_id': 'sess-hook-2',
        }, None, MagicMock()))

        sess = AgentSession.query.filter_by(session_id='sess-hook-2').first()
        db.session.refresh(sess)
        assert sess.data.get('subagent_checkpoints') is None

        db.session.delete(sess)
        db.session.commit()


# ─────────────────────────────────────────────────────────────────────────
# Ciclo 6: PreToolUse Task INJETA o checkpoint inline (componente 3 — injeção)
# ─────────────────────────────────────────────────────────────────────────

def _find_pretool_handler(hooks):
    for ev_key, matchers in hooks.items():
        ev_name = ev_key if isinstance(ev_key, str) else getattr(ev_key, 'name', str(ev_key))
        if ev_name == 'PreToolUse':
            for matcher in matchers:
                if hasattr(matcher, 'hooks') and matcher.hooks:
                    return matcher.hooks[0]  # _keep_stream_open
    return None


def test_pretool_task_injeta_checkpoint_inline_em_on(app, monkeypatch):
    """modo on + checkpoint existe -> updatedInput.prompt ganha o bloco inline."""
    from app.agente.config.permissions import set_current_session_id
    from app.agente.sdk.subagent_checkpoint import persist_checkpoint
    from app.agente.models import AgentSession
    from app import db
    import asyncio
    from unittest.mock import MagicMock

    monkeypatch.setenv("AGENT_SUBAGENT_CHECKPOINT", "on")
    with app.app_context():
        _fresh_session('sess-inj-1')
        persist_checkpoint('sess-inj-1', 'gestor-estoque-odoo',
                           'Quant 218550 = 17.004 confirmado.', {'num_turns': 13})
        set_current_session_id('sess-inj-1')

        handler = _find_pretool_handler(_make_hooks())
        assert handler is not None
        out = asyncio.run(handler({
            'tool_name': 'Task',
            'tool_input': {'subagent_type': 'gestor-estoque-odoo',
                           'prompt': 'Ajuste os 2 itens.'},
        }, None, MagicMock()))

        prompt = out['hookSpecificOutput']['updatedInput']['prompt']
        assert '<checkpoint_subagente>' in prompt
        assert '218550' in prompt
        assert 'Ajuste os 2 itens.' in prompt  # prompt original preservado

        set_current_session_id(None)
        db.session.delete(AgentSession.query.filter_by(session_id='sess-inj-1').first())
        db.session.commit()


def test_pretool_task_nao_injeta_em_shadow(app, monkeypatch):
    """modo shadow -> NÃO injeta (só observa); prompt do Task fica intacto."""
    from app.agente.config.permissions import set_current_session_id
    from app.agente.sdk.subagent_checkpoint import persist_checkpoint
    from app.agente.models import AgentSession
    from app import db
    import asyncio
    from unittest.mock import MagicMock

    monkeypatch.setenv("AGENT_SUBAGENT_CHECKPOINT", "shadow")
    with app.app_context():
        _fresh_session('sess-inj-2')
        persist_checkpoint('sess-inj-2', 'gestor-estoque-odoo', 'achei X', {})
        set_current_session_id('sess-inj-2')

        handler = _find_pretool_handler(_make_hooks())
        out = asyncio.run(handler({
            'tool_name': 'Task',
            'tool_input': {'subagent_type': 'gestor-estoque-odoo', 'prompt': 'faça'},
        }, None, MagicMock()))

        # shadow não muta a tool: sem updatedInput de prompt
        updated = (out or {}).get('hookSpecificOutput', {}).get('updatedInput')
        assert updated is None or 'checkpoint_subagente' not in str(updated)

        set_current_session_id(None)
        db.session.delete(AgentSession.query.filter_by(session_id='sess-inj-2').first())
        db.session.commit()


def test_pretool_task_sem_checkpoint_nao_injeta(app, monkeypatch):
    """modo on mas sem checkpoint p/ o agent_type -> degrada (sem injeção)."""
    from app.agente.config.permissions import set_current_session_id
    from app.agente.models import AgentSession
    from app import db
    import asyncio
    from unittest.mock import MagicMock

    monkeypatch.setenv("AGENT_SUBAGENT_CHECKPOINT", "on")
    with app.app_context():
        _fresh_session('sess-inj-3')
        set_current_session_id('sess-inj-3')

        handler = _find_pretool_handler(_make_hooks())
        out = asyncio.run(handler({
            'tool_name': 'Task',
            'tool_input': {'subagent_type': 'gestor-estoque-odoo', 'prompt': 'faça'},
        }, None, MagicMock()))

        updated = (out or {}).get('hookSpecificOutput', {}).get('updatedInput')
        assert updated is None or 'checkpoint_subagente' not in str(updated)

        set_current_session_id(None)
        db.session.delete(AgentSession.query.filter_by(session_id='sess-inj-3').first())
        db.session.commit()

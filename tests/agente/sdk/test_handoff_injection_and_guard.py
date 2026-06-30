"""8b passo 7: injecao do handoff_context (1x no 1o turno) + guard de tool.

(a) _compose_hook_context ganha o slot handoff_context (apos resume_fallback);
    default '' -> additionalContext byte-equivalente em off/principal.
(b) hooks UserPromptSubmit injeta render_handoff_block UMA vez (flag
    data['handoff_context_injected']); devolver_ao_principal reseta o flag.
(c) guard: PRINCIPAL expoe transferir_para (handoff_server); ESPECIALISTA expoe
    SO' devolver_ao_principal (handoff_devolver_server) — nao re-delega.
"""
import inspect

from app import db
from app.agente.models import AgentSession
from app.agente.sdk.hooks import _compose_hook_context


def test_compose_inclui_handoff_apos_resume_antes_de_session():
    out = _compose_hook_context(resume_fallback='RF', handoff_context='HO',
                                session_context='SC')
    assert out == 'RFHOSC'


def test_compose_sem_handoff_byte_equivalente():
    # default '' nao altera a montagem existente (off/principal).
    assert _compose_hook_context(session_context='SC', main_context='MC') == 'SCMC'


def test_apply_devolver_reseta_flag_de_injecao(app):
    with app.app_context():
        s = AgentSession(session_id='hx-reset', user_id=1, data={
            'agente_ativo': 'gestor-recebimento',
            'handoff_context': {'objetivo': 'x'},
            'handoff_context_injected': True,
        })
        db.session.add(s)
        db.session.commit()
        from app.agente.tools.handoff_mcp_tool import _apply_devolver
        out = _apply_devolver('hx-reset')
        assert out['ok'] is True
        r = AgentSession.query.filter_by(session_id='hx-reset').first()
        assert r.get_agente_ativo() == 'principal'
        assert 'handoff_context' not in (r.data or {})
        assert 'handoff_context_injected' not in (r.data or {})
        AgentSession.query.filter_by(session_id='hx-reset').delete()
        db.session.commit()


def test_dois_servers_de_handoff_distintos():
    from app.agente.tools.handoff_mcp_tool import handoff_server, handoff_devolver_server
    assert handoff_server is not None
    assert handoff_devolver_server is not None
    assert handoff_server is not handoff_devolver_server


def test_client_guard_especialista_so_devolver():
    from app.agente.sdk.client import AgentClient
    src = inspect.getsource(AgentClient._build_options)
    # Fix A (review 2026-06-29): registro do handoff gated por should_register_handoff
    # (principal + 'on' -> transferir_para). should_register_handoff('shadow', None) is
    # False (test_handoff_mcp_tool), logo shadow NAO expoe a tool de troca (medicao pura).
    assert 'should_register_handoff(' in src
    # ESPECIALISTA ('on' + specialist_profile is not None) expoe so' devolver.
    assert 'specialist_profile is not None' in src
    assert 'handoff_devolver_server' in src


def test_client_guard_admin_canary_registra_tools():
    """Fix (re-review 2026-06-30): no modo 'admin' (canary) o caminho do papel e'
    is_admin-aware, mas o registro da tool re-resolvia o modo SEM is_admin -> 'admin'
    colapsava p/ 'shadow' e NENHUMA tool de handoff era registrada (canary infiel ao
    'on' real). Agora: (1) is_admin e' param de _build_options e propaga
    resolve_specialist_handoff_mode(is_admin=is_admin); (2) o ESPECIALISTA registra
    devolver pelo SINAL specialist_profile is not None, sem re-resolver o modo."""
    from app.agente.sdk.client import AgentClient
    import inspect as _i
    src = _i.getsource(AgentClient._build_options)
    assert 'resolve_specialist_handoff_mode(is_admin=is_admin)' in src
    assert 'is_admin' in str(_i.signature(AgentClient._build_options))
    assert 'if specialist_profile is not None:' in src
    # o caller (stream persistente) propaga is_admin = bool(debug_mode)
    psrc = _i.getsource(AgentClient._stream_response_persistent)
    assert 'is_admin=bool(debug_mode)' in psrc


def test_hook_injecao_wiring():
    from app.agente.sdk import hooks
    src = inspect.getsource(hooks.build_hooks)
    assert 'handoff_context_injected' in src
    assert 'render_handoff_block' in src
    # injetado apos resume_fallback, antes de session_context na montagem.
    # (convergencia lojas: loja_context entra entre session_context e main_context,
    #  por isso a ancora e 'session_context + loja_context' e nao '+ main_context')
    csrc = inspect.getsource(hooks._compose_hook_context)
    assert csrc.index('resume_fallback + handoff_context') < csrc.index('session_context + loja_context')

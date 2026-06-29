"""8b passo 5: profile swap (prompt + skills) alimentado pelo papel.

_build_options ja' troca system_prompt + skills quando recebe specialist_profile
(F1). O passo 5 ALIMENTA esse parametro a partir do papel do turno em
_stream_response_persistent (SPECIALIST_PROFILES.get(agent_role)); papel sem
perfil -> None (fallback principal, com WARNING). Prompt faltante -> fallback
transparente (WARNING), nunca quebra o principal.
"""
import inspect

from app.agente.sdk import get_client
from app.agente.sdk.client import AgentClient
from app.agente.sdk.specialist_profiles import SPECIALIST_PROFILES, SpecialistProfile


def test_build_options_especialista_troca_skills():
    client = get_client()
    profile = SPECIALIST_PROFILES['gestor-recebimento']
    opts = client._build_options(specialist_profile=profile)
    assert sorted(opts.skills) == sorted(profile.skills)
    # O principal NAO usa essa allow-list (deny-list de skills delegadas).
    opts_principal = client._build_options()
    assert sorted(opts_principal.skills) != sorted(profile.skills)


def test_build_options_especialista_troca_system_prompt():
    client = get_client()
    profile = SPECIALIST_PROFILES['gestor-recebimento']
    opts = client._build_options(specialist_profile=profile)
    assert 'Recebimento' in (opts.system_prompt or '')


def test_build_options_prompt_faltante_faz_fallback():
    client = get_client()
    fake = SpecialistProfile(role='x', system_prompt_path='/nao/existe.md',
                             skills=['zzz-skill-inexistente'])
    opts = client._build_options(specialist_profile=fake)
    # Fallback ao principal: NAO aplica a allow-list do perfil quebrado.
    assert 'zzz-skill-inexistente' not in (opts.skills or [])


def test_stream_resolve_profile_por_papel():
    src = inspect.getsource(AgentClient._stream_response_persistent)
    assert 'SPECIALIST_PROFILES.get(agent_role)' in src
    assert 'specialist_profile=' in src

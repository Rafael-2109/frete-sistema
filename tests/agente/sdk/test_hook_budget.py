"""F4 PAD-CTX — Hook dinamico: orcamento por bloco + ordem-alvo (governanca).

Cobre o aceite da FASE 4 do plano 2026-06-09-arquitetura-contexto-boot-agente.md:
- 4.3: teto ~300c por memoria Tier 2 (destilado meta WHEN/DO + ponteiro view_memories),
  cap de 4 memorias no bloco Tier 2, ordem de corte no overflow
  (Tier 2 -> directives organicas -> routing_context; NUNCA user_rules/pendencias).
- 4.4: ordem-alvo COMPLETA da tabela PAD-CTX (secao "Hook dinamico — layout, orcamento
  e ordem"): pendencias_acumuladas como bloco separado, por ULTIMO (colado a mensagem).
- 4.6: payload tipico <=15KB por modelo; ausencia de skill_hints/world_model
  (flags default off — decisao R-1).

Setup espelha test_constitutional_directive.py (app_context modulo + mocks de query)
e test_shadow_not_injected.py (DB real para integracao do pipeline completo).
"""
import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app import create_app, db
from app.agente.sdk import memory_injection
from app.utils.timezone import agora_utc_naive


@pytest.fixture(scope='module')
def app_ctx():
    _app = create_app()
    _app.config.update({'TESTING': True, 'SQLALCHEMY_TRACK_MODIFICATIONS': False})
    with _app.app_context():
        yield _app


# =====================================================================
# 4.4b — _compose_hook_context (hooks.py, funcao PURA de montagem)
# =====================================================================

class TestComposeHookContext:
    def _compose(self, **kwargs):
        from app.agente.sdk.hooks import _compose_hook_context
        return _compose_hook_context(**kwargs)

    def test_ordem_alvo_completa(self):
        """Ordem PAD-CTX: resume(1) session(2) main(3-9) correction(10)
        debug(11) sql_admin(11) tail(12-13 — pendencias por ULTIMO)."""
        out = self._compose(
            resume_fallback='[RESUME]',
            session_context='[SESSION]',
            main_context='[MAIN]',
            correction_hint='[CORRECTION]',
            debug_context='[DEBUG]',
            sql_admin_context='[SQLADMIN]',
            tail_context='[TAIL]',
        )
        order = ['[RESUME]', '[SESSION]', '[MAIN]', '[CORRECTION]',
                 '[DEBUG]', '[SQLADMIN]', '[TAIL]']
        idx = [out.index(m) for m in order]
        assert idx == sorted(idx), f"ordem violada: {idx} em {out!r}"
        assert out.rstrip().endswith('[TAIL]'), "tail (recent_sessions+pendencias) deve fechar o payload"

    def test_blocos_vazios_omitidos(self):
        out = self._compose(main_context='[MAIN]')
        assert out == '[MAIN]'

    def test_sem_skill_hints_world_model_por_default(self):
        """Decisao R-1 (PAD-CTX): skill_hints/world_model fora do boot operacional."""
        out = self._compose(
            session_context='[SESSION]', main_context='[MAIN]', tail_context='[TAIL]',
        )
        assert 'skill_hints' not in out
        assert 'world_model' not in out
        # Flags default off (F0.1 — env vars false; default do codigo false)
        from app.agente.config.feature_flags import (
            USE_AGENT_SKILL_RAG, USE_AGENT_WORLD_MODEL_INJECT,
        )
        assert USE_AGENT_SKILL_RAG is False
        assert USE_AGENT_WORLD_MODEL_INJECT is False


# =====================================================================
# 4.3 — Teto por memoria Tier 2 (destilado + ponteiro view_memories)
# =====================================================================

class TestDistillTier2:
    def test_conteudo_curto_passa_intacto(self):
        mem = SimpleNamespace(id=1, path='/memories/empresa/heuristicas/x.xml', meta=None)
        content = 'WHEN: a\nDO: b'
        out = memory_injection._distill_tier2_content(mem, content)
        assert out == content
        assert 'view_memories' not in out

    def test_conteudo_longo_trunca_com_ponteiro(self):
        mem = SimpleNamespace(id=2, path='/memories/empresa/heuristicas/longa.xml', meta=None)
        content = 'X' * 2000
        out = memory_injection._distill_tier2_content(mem, content)
        # corpo destilado respeita o cap (+ folga apenas do ponteiro/reticencias)
        assert len(out) <= memory_injection.TIER2_MEMORY_CHAR_CAP + 120, (
            f"destilado estourou: {len(out)} chars"
        )
        assert 'view_memories' in out, "memoria truncada DEVE apontar para a integra"
        assert '/memories/empresa/heuristicas/longa.xml' in out

    def test_meta_when_do_preferido_ao_content_bruto(self):
        """Memoria com meta canonico (2026-06-08): destilar de when/do, nao do content."""
        mem = SimpleNamespace(
            id=3, path='/memories/empresa/armadilhas/odoo/trap.xml',
            meta={'titulo': 'Trap Odoo', 'when': 'ao consultar quant',
                  'do': 'filtrar company_id', 'kind': 'armadilha', 'nivel': 5},
        )
        content = 'B' * 1000  # content bruto gordo — nao deve ser a base do destilado
        out = memory_injection._distill_tier2_content(mem, content)
        assert 'filtrar company_id' in out, "DO do meta deve estar no destilado"
        assert 'BBBB' not in out, "content bruto nao deve vazar quando meta when/do existe"
        assert 'view_memories' in out


# =====================================================================
# 4.3 — Ordem de corte no overflow (_fit_hook_budget, funcao PURA)
# =====================================================================

class TestFitHookBudget:
    PARTS = {
        'fixed_chars': 1000,
        'tier2': 'X' * 500,
        'directives_full': 'D' * 400,
        'directives_const': 'C' * 100,
        'routing': 'R' * 200,
    }

    def test_sem_overflow_nada_cortado(self):
        resolved, cortes = memory_injection._fit_hook_budget(dict(self.PARTS), target=10_000)
        assert cortes == []
        assert resolved['tier2'] == self.PARTS['tier2']
        assert resolved['directives'] == self.PARTS['directives_full']
        assert resolved['routing'] == self.PARTS['routing']

    def test_overflow_corta_tier2_primeiro(self):
        # total = 1000+500+400+200 = 2100 > 1900; sem tier2: 1600 <= 1900
        resolved, cortes = memory_injection._fit_hook_budget(dict(self.PARTS), target=1900)
        assert cortes == ['tier2']
        assert resolved['tier2'] == ''
        assert resolved['directives'] == self.PARTS['directives_full']
        assert resolved['routing'] == self.PARTS['routing']

    def test_overflow_reduz_directives_a_constitucional_depois(self):
        # sem tier2: 1600 > 1400; directives const-only: 1000+100+200=1300 <= 1400
        resolved, cortes = memory_injection._fit_hook_budget(dict(self.PARTS), target=1400)
        assert cortes == ['tier2', 'directives_organicas']
        assert resolved['directives'] == self.PARTS['directives_const'], (
            "constitucional NUNCA e cortada — so as organicas"
        )

    def test_overflow_corta_routing_por_ultimo(self):
        # const-only: 1300 > 1200; sem routing: 1100 <= 1200
        resolved, cortes = memory_injection._fit_hook_budget(dict(self.PARTS), target=1200)
        assert cortes == ['tier2', 'directives_organicas', 'routing']
        assert resolved['routing'] == ''

    def test_fixed_nunca_cortado(self):
        """user_rules/pendencias/sessions/tier1 (fixed) ficam mesmo estourando o teto."""
        resolved, cortes = memory_injection._fit_hook_budget(dict(self.PARTS), target=500)
        assert cortes == ['tier2', 'directives_organicas', 'routing']
        assert resolved['directives'] == self.PARTS['directives_const']


# =====================================================================
# 4.4a — _build_session_window retorna pendencias como bloco SEPARADO
# =====================================================================

def _mock_sessions(fakes):
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = fakes
    return patch('app.agente.models.AgentSession.query', mock_query)


class TestSessionWindowSplit:
    def test_pendencias_externalizadas(self, app_ctx):
        fake = SimpleNamespace(
            summary={'resumo_geral': 'resolveu fretes', 'tarefas_pendentes': ['conferir NF 99'],
                     'alertas': []},
            updated_at=agora_utc_naive(),
        )
        with _mock_sessions([fake]), \
             patch.object(memory_injection, '_load_resolved_pendencias', return_value=set()):
            sessions_block, pendencias_block = memory_injection._build_session_window(user_id=5)

        assert sessions_block and '<recent_sessions' in sessions_block
        assert 'pendencias_acumuladas' not in sessions_block, (
            "pendencias NAO podem mais vir embutidas no recent_sessions (D3)"
        )
        assert pendencias_block and '<pendencias_acumuladas>' in pendencias_block
        assert 'conferir NF 99' in pendencias_block

    def test_sem_pendencias_retorna_none_no_segundo(self, app_ctx):
        fake = SimpleNamespace(
            summary={'resumo_geral': 'sessao limpa', 'tarefas_pendentes': [], 'alertas': []},
            updated_at=agora_utc_naive(),
        )
        with _mock_sessions([fake]), \
             patch.object(memory_injection, '_load_resolved_pendencias', return_value=set()):
            sessions_block, pendencias_block = memory_injection._build_session_window(user_id=5)
        assert sessions_block and '<recent_sessions' in sessions_block
        assert pendencias_block is None

    def test_pendencia_expirada_por_ttl_fica_fora(self, app_ctx):
        fake = SimpleNamespace(
            summary={'resumo_geral': 'antiga', 'tarefas_pendentes': ['velharia'], 'alertas': []},
            updated_at=agora_utc_naive() - timedelta(days=30),
        )
        with _mock_sessions([fake]), \
             patch.object(memory_injection, '_load_resolved_pendencias', return_value=set()):
            _, pendencias_block = memory_injection._build_session_window(user_id=5)
        assert pendencias_block is None


# =====================================================================
# Integracao: contrato (main, tail, ids) + ordem-alvo + teto 15KB
# (DB real — espelha test_shadow_not_injected.py)
# =====================================================================

@pytest.fixture
def f4_user(app_ctx):
    from app.auth.models import Usuario
    user = Usuario.query.filter_by(email='test_hook_budget_f4@test.com').first()
    if not user:
        user = Usuario(
            email='test_hook_budget_f4@test.com',
            nome='Test Hook Budget F4',
            perfil='agente',
            status='ativo',
        )
        user.set_senha('test_password_123')
        db.session.add(user)
        db.session.commit()
    return user


@pytest.fixture
def f4_mems(app_ctx, f4_user):
    """Coleta ids criados e limpa ao final (+ limpa cache de injecao)."""
    from app.agente.models import AgentMemory
    created = []
    yield created, f4_user.id
    for mid in created:
        obj = db.session.get(AgentMemory, mid)
        if obj:
            db.session.delete(obj)
    db.session.commit()
    memory_injection._SESSION_INJECTION_CACHE.clear()


def _mk_mem(user_id, path, content, created, **extra):
    from app.agente.models import AgentMemory
    mem = AgentMemory.create_file(user_id, path, content)
    for k, v in extra.items():
        setattr(mem, k, v)
    db.session.commit()
    created.append(mem.id)
    return mem


_NO_SEMANTIC = [
    patch('app.embeddings.config.MEMORY_SEMANTIC_SEARCH', True),
    patch('app.embeddings.memory_search.buscar_memorias_semantica', return_value=[]),
    patch('app.agente.services.knowledge_graph_service.query_graph_memories', return_value=[]),
]


class TestLoadUserMemoriesOrdemEBudget:
    def _call(self, user_id, prompt='qual o status?', model='claude-opus-4-8'):
        return memory_injection._load_user_memories_for_context(
            user_id=user_id, prompt=prompt, model_name=model,
        )

    def test_contrato_main_tail_ids(self, app_ctx, f4_mems):
        created, user_id = f4_mems
        _mk_mem(user_id, '/memories/user.xml', '<resumo>perfil teste</resumo>', created)
        with _NO_SEMANTIC[0], _NO_SEMANTIC[1], _NO_SEMANTIC[2]:
            result = self._call(user_id)
        assert isinstance(result, tuple) and len(result) == 3, (
            "contrato F4.4: (main_context, tail_context, mem_ids)"
        )
        main, tail, ids = result
        assert main and '<user_memories>' in main
        assert isinstance(ids, list)

    def test_ordem_main_e_tail(self, app_ctx, f4_mems):
        """Main: user_rules(3) -> user_memories(4-6) -> directives(7) ->
        briefing(8) -> routing(9). Tail: recent_sessions(12) -> pendencias(13)."""
        created, user_id = f4_mems
        _mk_mem(user_id, '/memories/user.xml', '<resumo>perfil</resumo>', created)
        _mk_mem(user_id, '/memories/corrections/regra-f4.xml', 'WHEN: sempre DO: regra dura',
                created, priority='mandatory')

        with patch.object(memory_injection, '_build_session_window',
                          return_value=('<recent_sessions count="1">RS</recent_sessions>',
                                        '<pendencias_acumuladas>P1</pendencias_acumuladas>')), \
             patch('app.agente.services.intersession_briefing.build_intersession_briefing',
                   return_value='<intersession_briefing>BRF</intersession_briefing>'), \
             patch.object(memory_injection, '_build_operational_directives',
                          return_value='<operational_directives priority="critical">OD</operational_directives>'), \
             patch.object(memory_injection, '_build_routing_context',
                          return_value='<routing_context priority="advisory">RC</routing_context>'), \
             patch('app.agente.config.feature_flags.USE_INTERSESSION_BRIEFING', True), \
             _NO_SEMANTIC[0], _NO_SEMANTIC[1], _NO_SEMANTIC[2]:
            main, tail, _ids = self._call(user_id)

        # ordem interna do main (3 -> 9)
        markers = ['<user_rules', '<user_memories>', '<operational_directives',
                   '<intersession_briefing>', '<routing_context']
        idx = [main.index(m) for m in markers]
        assert idx == sorted(idx), f"ordem do main violada: {list(zip(markers, idx))}"
        assert 'pendencias_acumuladas' not in main, "pendencias moram no TAIL (D3)"
        assert '<recent_sessions' not in main, "recent_sessions mora no TAIL (item 12)"

        # tail: recent_sessions antes de pendencias; pendencias por ULTIMO
        assert tail.index('<recent_sessions') < tail.index('<pendencias_acumuladas>')
        assert tail.rstrip().endswith('</pendencias_acumuladas>')

    def test_tier2_cap_4_memorias_e_teto_15kb(self, app_ctx, f4_mems):
        """Backlog do plano: fallback de recencia injetava ~63KB (15 mems empresa
        integrais, budget=unlimited no Opus). Com F4.3: cap 4 x ~300c + teto 15KB."""
        created, user_id = f4_mems
        _mk_mem(user_id, '/memories/user.xml', '<resumo>' + 'p' * 2000 + '</resumo>', created)
        # 15 memorias empresa gordas (4KB cada) — fallback de recencia pegava todas
        for i in range(15):
            _mk_mem(0, f'/memories/empresa/heuristicas/gorda-{uuid.uuid4().hex[:8]}.xml',
                    f'<titulo>gorda {i}</titulo>' + 'Z' * 4000, created)

        with _NO_SEMANTIC[0], _NO_SEMANTIC[1], _NO_SEMANTIC[2]:
            main, tail, ids = self._call(user_id, model='claude-opus-4-8')

        total = len(main or '') + len(tail or '')
        assert total <= memory_injection.HOOK_CONTEXT_TARGET_CHARS, (
            f"payload {total} chars estourou o teto de "
            f"{memory_injection.HOOK_CONTEXT_TARGET_CHARS} (PAD-CTX <=15KB/turno)"
        )
        # cap de QUANTIDADE do bloco Tier 2: max 4 alem das protegidas (user.xml)
        empresa_injetadas = [i for i in ids if i in created[1:]]
        assert len(empresa_injetadas) <= memory_injection.TIER2_MAX_MEMORIES, (
            f"Tier 2 injetou {len(empresa_injetadas)} memorias (cap "
            f"{memory_injection.TIER2_MAX_MEMORIES})"
        )
        # cada memoria tier2 destilada aponta para a integra
        if empresa_injetadas:
            assert 'view_memories' in main

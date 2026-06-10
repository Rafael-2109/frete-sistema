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


class TestSessionWindowResumoCap:
    """F6 (validacao PROD): recent_sessions media ~4K no tail (user 18) vs
    ~1,2KB da tabela PAD-CTX — o docstring de _build_session_window promete
    '~150 chars' por sessao mas nada enforca. Cap por resumo (incortavel:
    destila, nao remove; integra navegavel via search_sessions)."""

    def test_resumo_gordo_e_truncado_por_sessao(self, app_ctx):
        fakes = [
            SimpleNamespace(
                summary={'resumo_geral': f'sessao {i} ' + 'r' * 1000,
                         'tarefas_pendentes': [], 'alertas': []},
                updated_at=agora_utc_naive(),
            ) for i in range(5)
        ]
        with _mock_sessions(fakes), \
             patch.object(memory_injection, '_load_resolved_pendencias', return_value=set()):
            sessions_block, _ = memory_injection._build_session_window(user_id=5)
        assert sessions_block is not None
        assert len(sessions_block) <= 5 * (memory_injection.SESSION_RESUMO_CHAR_CAP + 120), (
            f"recent_sessions estourou: {len(sessions_block)}c"
        )
        assert 'r' * (memory_injection.SESSION_RESUMO_CHAR_CAP + 10) not in sessions_block

    def test_resumo_curto_passa_intacto(self, app_ctx):
        fakes = [SimpleNamespace(
            summary={'resumo_geral': 'resolveu fretes do dia',
                     'tarefas_pendentes': [], 'alertas': []},
            updated_at=agora_utc_naive(),
        )]
        with _mock_sessions(fakes), \
             patch.object(memory_injection, '_load_resolved_pendencias', return_value=set()):
            sessions_block, _ = memory_injection._build_session_window(user_id=5)
        assert 'resolveu fretes do dia' in sessions_block

    def test_flag_off_resumo_integral(self, app_ctx):
        fakes = [SimpleNamespace(
            summary={'resumo_geral': 'g' * 1000, 'tarefas_pendentes': [], 'alertas': []},
            updated_at=agora_utc_naive(),
        )]
        with _mock_sessions(fakes), \
             patch.object(memory_injection, '_load_resolved_pendencias', return_value=set()), \
             patch('app.agente.config.feature_flags.AGENT_FIXED_BLOCKS_CAP', False):
            sessions_block, _ = memory_injection._build_session_window(user_id=5)
        assert 'g' * 1000 in sessions_block, "flag off = resumo integral (legado)"


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


# =====================================================================
# F6 — Cap de blocos FIXOS (tier1 + user_rules): destilar/ponteirar,
# NUNCA cortar (intocaveis PAD-CTX). Evidencia tripla PROD (users 1/18/82):
# rules 6.2K + tier1 7.6-9.1K estouravam sozinhos o teto 15K e a politica
# de overflow zerava TODO o adaptativo (tier2/organicas/routing).
# =====================================================================

class TestDistillFixedBlock:
    def test_conteudo_curto_passa_intacto(self):
        mem = SimpleNamespace(id=10, path='/memories/preferences.xml', meta=None)
        out = memory_injection._distill_fixed_block(mem, 'curto', 1200)
        assert out == 'curto'
        assert 'view_memories' not in out

    def test_conteudo_longo_trunca_em_fronteira_de_linha_com_ponteiro(self):
        mem = SimpleNamespace(id=11, path='/memories/preferences.xml', meta=None)
        lines = '\n'.join(
            f'[preferencia] item {i} ' + 'x' * 80 for i in range(40)
        )
        out = memory_injection._distill_fixed_block(mem, lines, 1200)
        assert len(out) <= 1200 + 120, f"destilado estourou: {len(out)} chars"
        assert 'view_memories' in out, "bloco fixo destilado DEVE apontar para a integra"
        assert '/memories/preferences.xml' in out
        # truncamento preferencial em fronteira de linha: nao termina no meio
        # de um item (a ultima linha antes do ponteiro e um item completo)
        body = out.split('\n[integra]')[0]
        # invariante real da fronteira de linha: a ULTIMA linha do corpo e um
        # item COMPLETO (review F6: endswith('x'*10) passava com corte no meio)
        import re as _re
        last_line = body.rstrip('…').rstrip().splitlines()[-1].strip()
        assert _re.fullmatch(r'\[preferencia\] item \d+ x{80}', last_line), (
            f"corte caiu no meio de item: {last_line!r}"
        )


class TestDistillRuleContent:
    def test_regra_curta_passa_intacta(self):
        mem = SimpleNamespace(id=20, path='/memories/corrections/r.xml', meta=None)
        content = 'WHEN: pedido aberto DO: usar consultar_sql'
        out = memory_injection._distill_rule_content(mem, content)
        assert out == content

    def test_regra_longa_com_meta_preserva_do_integral(self):
        """DO e o nucleo operativo da regra — NUNCA pode ser o primeiro a cair."""
        mem = SimpleNamespace(
            id=21, path='/memories/corrections/juros.xml',
            meta={
                'titulo': 'T' * 200,
                'when': 'W' * 200,
                'do': 'Nunca aplicar juros padrao sem confirmar com o usuario',
                'kind': 'correcao', 'nivel': 5,
            },
        )
        content = 'Z' * 800  # content bruto gordo — base deve ser o meta
        out = memory_injection._distill_rule_content(mem, content)
        assert 'Nunca aplicar juros padrao sem confirmar com o usuario' in out, (
            "DO do meta deve sobreviver INTEGRAL ao destilado"
        )
        assert 'ZZZZ' not in out
        assert 'view_memories' in out
        assert len(out) <= memory_injection.USER_RULE_CHAR_CAP + 120

    def test_regra_longa_sem_meta_trunca_com_ponteiro(self):
        mem = SimpleNamespace(id=22, path='/memories/corrections/semmeta.xml', meta=None)
        content = 'Y' * 900
        out = memory_injection._distill_rule_content(mem, content)
        assert len(out) <= memory_injection.USER_RULE_CHAR_CAP + 120
        assert 'view_memories' in out
        assert '/memories/corrections/semmeta.xml' in out


class TestUserRulesCapEDedupTier1(object):
    """Canal L1 <user_rules>: cap por regra + exclusao dos paths Tier 1."""

    def test_paths_tier1_ficam_fora_do_canal_l1(self, app_ctx, f4_mems):
        """Bug PROD (user 18): preferences.xml com priority=mandatory entrava
        2x no payload — no <user_rules> E no Tier 1. Paths protegidos vivem
        SO no Tier 1 (canal canonico de perfil)."""
        from app.agente.sdk.memory_injection_rules import (
            _build_user_rules, _get_user_rule_ids,
        )
        created, user_id = f4_mems
        prefs = _mk_mem(user_id, '/memories/preferences.xml',
                        '[preferencia] excel sempre', created, priority='mandatory')
        _mk_mem(user_id, '/memories/corrections/regra-real.xml',
                'WHEN: sempre DO: regra dura legitima', created, priority='mandatory')

        block = _build_user_rules(user_id)
        assert block and 'regra dura legitima' in block
        assert '/memories/preferences.xml' not in block, (
            "path Tier 1 NAO pode entrar no <user_rules> (dupla injecao)"
        )
        assert prefs.id not in _get_user_rule_ids(user_id)

    def test_regra_gorda_e_destilada_no_bloco(self, app_ctx, f4_mems):
        created, user_id = f4_mems
        _mk_mem(user_id, '/memories/corrections/gorda.xml',
                'K' * 2000, created, priority='mandatory')
        from app.agente.sdk.memory_injection_rules import _build_user_rules
        block = _build_user_rules(user_id)
        assert block is not None
        assert 'KKKK' in block, "regra destilada mantem o INICIO do conteudo"
        assert len(block) < 1200, (
            f"regra de 2000c deveria sair destilada (~cap {memory_injection.USER_RULE_CHAR_CAP}c); "
            f"bloco veio com {len(block)}c"
        )
        assert 'view_memories' in block

    def test_flag_off_preserva_comportamento_legado(self, app_ctx, f4_mems):
        created, user_id = f4_mems
        _mk_mem(user_id, '/memories/corrections/gorda-legacy.xml',
                'L' * 2000, created, priority='mandatory')
        from app.agente.sdk.memory_injection_rules import _build_user_rules
        with patch('app.agente.config.feature_flags.AGENT_FIXED_BLOCKS_CAP', False):
            block = _build_user_rules(user_id)
        assert block is not None
        assert 'L' * 2000 in block, "flag off = regra integral (legado)"

    def test_dedup_tier1_e_incondicional_a_flag(self, app_ctx, f4_mems):
        """Review F6: a exclusao dos paths Tier 1 do canal L1 e BUG FIX —
        NAO volta com o kill-switch (a dupla injecao nao pode retornar)."""
        from app.agente.sdk.memory_injection_rules import _build_user_rules
        created, user_id = f4_mems
        _mk_mem(user_id, '/memories/preferences.xml',
                '[preferencia] dup-check', created, priority='mandatory')
        _mk_mem(user_id, '/memories/corrections/regra-flagoff.xml',
                'WHEN: x DO: y', created, priority='mandatory')
        with patch('app.agente.config.feature_flags.AGENT_FIXED_BLOCKS_CAP', False):
            block = _build_user_rules(user_id)
        assert block and '/memories/preferences.xml' not in block

    def test_regra_empresa_com_path_protegido_fica_no_canal_l1(self, app_ctx, f4_mems):
        """Edge do review F6: row EMPRESA (user_id=0) com path protegido NAO e
        injetada pelo Tier 1 (query e user-scoped) — exclui-la do canal L1
        tambem a faria sumir dos DOIS canais. A exclusao vale SO para rows do
        proprio usuario (as que o Tier 1 de fato injeta)."""
        from app.agente.sdk.memory_injection_rules import _build_user_rules
        created, user_id = f4_mems
        _mk_mem(0, '/memories/preferences.xml',
                '[empresa] regra global dura', created, priority='mandatory')
        block = _build_user_rules(user_id)
        assert block and 'regra global dura' in block, (
            "regra empresa com path protegido sumiu dos dois canais"
        )


class TestTier1Cap:
    def _call(self, user_id, prompt='qual o status?', model='claude-opus-4-8'):
        return memory_injection._load_user_memories_for_context(
            user_id=user_id, prompt=prompt, model_name=model,
        )

    def test_user_xml_grande_vira_pointer_mode_mesmo_no_opus(self, app_ctx, f4_mems):
        """O pointer-mode legado (USE_USER_XML_POINTER) so disparava com budget
        finito — NUNCA no Opus (budget=None), exatamente o modelo dos users
        afetados. O cap F6 e incondicional ao modelo."""
        created, user_id = f4_mems
        content = (
            '<user_profile>\n<resumo>perfil compacto do usuario</resumo>\n'
            '<contextualizacao>como tratar este usuario</contextualizacao>\n'
            + '<atividades>' + 'a' * 3500 + '</atividades>\n</user_profile>'
        )
        _mk_mem(user_id, '/memories/user.xml', content, created)
        with _NO_SEMANTIC[0], _NO_SEMANTIC[1], _NO_SEMANTIC[2]:
            main, _tail, _ids = self._call(user_id, model='claude-opus-4-8')
        assert main is not None
        assert 'aaaa' not in main, "user.xml gordo nao entra integral no Opus"
        assert 'perfil compacto do usuario' in main, "resumo sobrevive no pointer-mode"
        assert '/memories/user.xml' in main, "ponteiro para a integra presente"

    def test_preferences_e_expertise_grandes_destiladas(self, app_ctx, f4_mems):
        import re
        created, user_id = f4_mems
        _mk_mem(user_id, '/memories/user.xml', '<resumo>ok</resumo>', created)
        _mk_mem(user_id, '/memories/preferences.xml',
                '\n'.join('[preferencia] p%d ' % i + 'b' * 90 for i in range(40)),
                created)
        _mk_mem(user_id, '/memories/user_expertise.xml',
                '\n'.join('[expertise] e%d ' % i + 'c' * 90 for i in range(40)),
                created)
        with _NO_SEMANTIC[0], _NO_SEMANTIC[1], _NO_SEMANTIC[2]:
            main, _tail, _ids = self._call(user_id, model='claude-opus-4-8')
        for path, cap in (
            ('/memories/preferences.xml', memory_injection.TIER1_PATH_CAPS['/memories/preferences.xml']),
            ('/memories/user_expertise.xml', memory_injection.TIER1_PATH_CAPS['/memories/user_expertise.xml']),
        ):
            seg = re.search(
                r'<memory path="%s".*?</memory>' % re.escape(path), main, re.DOTALL
            )
            assert seg, f"{path} deve continuar SEMPRE injetado (incortavel)"
            assert len(seg.group(0)) <= cap + 300, (
                f"{path} estourou o cap: {len(seg.group(0))}c"
            )
            assert 'view_memories' in seg.group(0), f"{path} destilado sem ponteiro"

    def test_pointer_mode_wrapper_nao_e_neutralizado_pelo_sanitize(self, app_ctx, f4_mems):
        """Bug achado na ablacao F6: <user_profile_partial> esta na blocklist
        anti-spoofing — sanitize DEPOIS do pointer neutralizava o wrapper
        LEGITIMO gerado pelo proprio pipeline. Ordem correta: sanitize no
        conteudo BRUTO (user-controlled), cap/pointer por cima."""
        created, user_id = f4_mems
        content = (
            '<user_profile>\n<resumo>resumo legitimo</resumo>\n'
            '<contextualizacao>ctx</contextualizacao>\n'
            + 'z' * 3000 + '\n</user_profile>'
        )
        _mk_mem(user_id, '/memories/user.xml', content, created)
        with _NO_SEMANTIC[0], _NO_SEMANTIC[1], _NO_SEMANTIC[2]:
            main, _tail, _ids = self._call(user_id, model='claude-opus-4-8')
        assert '<user_profile_partial' in main, (
            "wrapper do pointer-mode deve chegar INTACTO ao payload"
        )
        assert '&lt;user_profile_partial' not in main, (
            "sanitize neutralizou o wrapper legitimo do pipeline"
        )

    def test_flag_off_tier1_integral(self, app_ctx, f4_mems):
        """Review F6: kill-switch precisa de cobertura no tier1 (bloco fixo
        MAIOR). Flag off = conteudo INTEGRAL, sem destilado nem ponteiro."""
        created, user_id = f4_mems
        fat_prefs = '\n'.join(
            '[preferencia] p%d ' % i + 'b' * 90 for i in range(40)
        )
        _mk_mem(user_id, '/memories/user.xml', '<resumo>ok</resumo>', created)
        _mk_mem(user_id, '/memories/preferences.xml', fat_prefs, created)
        with patch('app.agente.config.feature_flags.AGENT_FIXED_BLOCKS_CAP', False), \
             _NO_SEMANTIC[0], _NO_SEMANTIC[1], _NO_SEMANTIC[2]:
            main, _tail, _ids = self._call(user_id, model='claude-opus-4-8')
        assert fat_prefs in main, (
            "flag off deve injetar preferences.xml INTEGRAL (rollback legado)"
        )

    def test_cenario_user18_adaptativo_sobrevive(self, app_ctx, f4_mems):
        """O caso da evidencia tripla: blocos fixos gordos NAO podem mais matar
        o adaptativo. Antes do cap: fixed ~15K sozinho -> overflow cortava
        tier2/organicas/routing -> usuario mais ativo = zero retrieval."""
        created, user_id = f4_mems
        # tier1 nos tamanhos REAIS de PROD (hibrido user 83 + user 18)
        _mk_mem(user_id, '/memories/user.xml',
                '<user_profile>\n<resumo>' + 'r' * 600 + '</resumo>\n'
                '<contextualizacao>' + 'k' * 1100 + '</contextualizacao>\n'
                '<atividades>' + 'a' * 2300 + '</atividades>\n</user_profile>',
                created)
        _mk_mem(user_id, '/memories/preferences.xml',
                '\n'.join('[preferencia] p%d ' % i + 'b' * 80 for i in range(28)),
                created, priority='mandatory')  # PROD: prefs do user 18 e mandatory
        _mk_mem(user_id, '/memories/user_expertise.xml',
                '\n'.join('[expertise] e%d ' % i + 'c' * 80 for i in range(30)),
                created)
        # 6 regras mandatory gordas (como o user 18 real: 380-560c)
        for i in range(6):
            _mk_mem(user_id, f'/memories/corrections/regra-{i}-{uuid.uuid4().hex[:6]}.xml',
                    f'WHEN: situacao {i} ' + 'w' * 200 + f' DO: acao {i} ' + 'd' * 200,
                    created, priority='mandatory')
        # 15 memorias empresa gordas (fallback de recencia as pega)
        empresa_ids = []
        for i in range(15):
            m = _mk_mem(0, f'/memories/empresa/heuristicas/f6-{uuid.uuid4().hex[:8]}.xml',
                        f'<titulo>f6 {i}</titulo>' + 'Z' * 3000, created)
            empresa_ids.append(m.id)

        with _NO_SEMANTIC[0], _NO_SEMANTIC[1], _NO_SEMANTIC[2]:
            main, tail, ids = self._call(user_id, model='claude-opus-4-8')

        total = len(main or '') + len(tail or '')
        assert total <= memory_injection.HOOK_CONTEXT_TARGET_CHARS, (
            f"payload {total}c estourou o teto 15K mesmo com caps F6"
        )
        sobreviventes = [i for i in ids if i in empresa_ids]
        assert sobreviventes, (
            "adaptativo (Tier 2) foi cortado: blocos fixos continuam estourando "
            "o orcamento — o cap F6 nao esta limitando tier1/user_rules"
        )


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

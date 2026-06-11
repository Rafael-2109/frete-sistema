"""
T0.1: versionar + verificar o merge do pipeline empresa.

Cobertura:
1. Merge bem-sucedido + verificacao TODOS_PRESERVADOS -> content atualizado E
   AgentMemoryVersion criada com conteudo ANTIGO e changed_by='sonnet'.
2. Verificacao detecta perda -> retry -> retry verifica OK -> merged do retry aceito.
3. Verificacao falha 2x -> _merge_memories_via_sonnet retorna None ->
   caminho append preserva ambos os conteudos (e tambem versiona).
4. Flag USE_MERGE_ENRICHMENT=False (append direto) -> tambem cria versao.
5. Exception na chamada de verificacao -> merged aceito mesmo assim (best-effort).

Convencao: conteudos de teste usam vocabulario DISJUNTO para que overlap < 0.75
e a funcao nao retorne True prematuramente no guard de similaridade.
"""
import pytest
from unittest.mock import patch, MagicMock
from contextlib import ExitStack

from app import db
from app.agente.models import AgentMemory, AgentMemoryVersion
from app.auth.models import Usuario


# Conteudos com vocabulario disjunto: overlap real < 0.75 apos clean_for_comparison
# (que strips tags XML). "alfa/beta/gama" x "delta/epsilon/zeta" nao se intersectam.
OLD_CONTENT = (
    '<heuristica nivel="4">\n'
    '<when>Quando expedicao alfa solicita despacho urgente</when>\n'
    '<do>Verificar janela beta disponivel no transportador gama</do>\n'
    '</heuristica>'
)
NEW_CONTENT = (
    '<heuristica nivel="4">\n'
    '<when>Quando expedicao delta solicita agendamento especial</when>\n'
    '<do>Confirmar janela epsilon no transportador zeta antes de emitir CTe</do>\n'
    '</heuristica>'
)
MERGED_CONTENT = (
    '<heuristica nivel="4">\n'
    '<when>Quando expedicao alfa ou delta solicita despacho urgente ou agendamento</when>\n'
    '<do>Verificar janela beta ou epsilon; confirmar transportador gama ou zeta</do>\n'
    '</heuristica>'
)
MERGED_RETRY_CONTENT = (
    '<heuristica nivel="4">\n'
    '<when>Quando expedicao alfa ou delta requer despacho ou agendamento especial</when>\n'
    '<do>Verificar janela beta/epsilon; confirmar gama/zeta; emitir CTe ao final</do>\n'
    '</heuristica>'
)


# ─── fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def test_user(app):
    """Cria usuario de teste (module scope)."""
    with app.app_context():
        user = Usuario.query.get(99997)
        if not user:
            user = Usuario(
                id=99997,
                email='test-enrich-versioning@test.local',
                nome='Test Versioning',
                senha_hash='dummy_hash_for_test',
            )
            db.session.add(user)
            db.session.commit()
        return user


@pytest.fixture
def cleanup_memories(db):
    """Limpa memorias e versoes criadas no teste."""
    created_ids = []
    yield created_ids
    for mid in created_ids:
        AgentMemoryVersion.query.filter_by(memory_id=mid).delete()
        mem = AgentMemory.query.get(mid)
        if mem:
            db.session.delete(mem)
    db.session.commit()


def _make_memory(path: str, content: str) -> AgentMemory:
    """Cria memoria empresa (user_id=0) com conteudo pre-definido."""
    mem = AgentMemory.create_file(0, path, content)
    db.session.commit()
    return mem


def _make_api_response(text: str) -> MagicMock:
    """Monta resposta simulada da API Anthropic."""
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    return resp


def _call_enrich(mem, path, new_content, descricao, merge_flag=True, merge_result=None):
    """
    Helper que invoca _try_enrich_existing com patches adequados.

    Para controlar o comportamento do merge + verificacao sem chamar API real,
    patchamos _merge_memories_via_sonnet diretamente com o valor desejado.
    Isso evita ter que controlar a sequencia exata de chamadas da API e
    torna os testes mais legíveis e robustos.

    merge_result=None -> usa merge real (para testar caminho completo via mock_anthropic)
    merge_result=<str> -> retorna esse string como resultado do merge
    merge_result=False -> retorna None (simula falha do merge/verificacao)
    """
    patches = [
        patch('app.agente.models.AgentMemory.get_by_path', return_value=mem),
        patch('app.agente.services.pattern_analyzer._find_similar_empresa_memory',
              return_value=None),
        patch('app.agente.config.feature_flags.USE_MERGE_ENRICHMENT', merge_flag),
    ]
    if merge_result is not None:
        # False significa "retornar None" (falha do merge)
        return_val = None if merge_result is False else merge_result
        patches.append(
            patch('app.agente.services.pattern_analyzer._merge_memories_via_sonnet',
                  return_value=return_val)
        )

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        from app.agente.services.pattern_analyzer import _try_enrich_existing
        return _try_enrich_existing(
            path=path,
            new_content=new_content,
            created_by=0,
            descricao=descricao,
        )


# ─── cenario 1: merge OK → content atualizado + versao criada ───────────────

def test_merge_ok_creates_version_and_updates_content(app, db, test_user, cleanup_memories):
    """
    Cenario 1: merge bem-sucedido.
    Espera: content atualizado + AgentMemoryVersion com conteudo antigo e changed_by='sonnet'.
    """
    with app.app_context():
        path = '/memories/empresa/heuristicas/expedicao/test-t01-c1.xml'
        mem = _make_memory(path, OLD_CONTENT)
        cleanup_memories.append(mem.id)

        result = _call_enrich(mem, path, NEW_CONTENT, 'heuristica expedicao',
                              merge_flag=True, merge_result=MERGED_CONTENT)

        assert result is True, "Deve retornar True (enriqueceu)"

        reloaded = AgentMemory.query.get(mem.id)
        assert MERGED_CONTENT in reloaded.content, "Content deve conter merged"

        versions = AgentMemoryVersion.query.filter_by(memory_id=mem.id).all()
        assert len(versions) >= 1, "Deve ter ao menos 1 versao criada"
        latest = max(versions, key=lambda v: v.version)
        assert latest.content == OLD_CONTENT, "Versao deve ter conteudo antigo"
        assert latest.changed_by == 'sonnet', "changed_by deve ser 'sonnet'"


# ─── cenario 2: verificacao detecta perda → retry → retry OK ───────────────

def test_merge_retry_when_facts_lost(app, db, test_user, cleanup_memories):
    """
    Cenario 2: 1a verificacao detecta perda -> retry do merge ->
    2a verificacao OK -> merged do retry aceito.

    Testamos _merge_memories_via_sonnet diretamente com mock da API Anthropic
    para cobrir o caminho retry dentro da funcao.
    """
    with app.app_context():
        path = '/memories/empresa/armadilhas/odoo/test-t01-c2.xml'
        mem = _make_memory(path, OLD_CONTENT)
        cleanup_memories.append(mem.id)

        # Sequencia de chamadas API dentro de _merge_memories_via_sonnet:
        # 1: merge inicial -> merged_v1
        # 2: verificacao 1a -> 'fatos perdidos' (detecta perda)
        # 3: retry merge -> MERGED_RETRY_CONTENT
        # 4: verificacao 2a -> TODOS_PRESERVADOS
        side_effects = [
            _make_api_response(MERGED_CONTENT),             # 1: merge inicial
            _make_api_response('fato delta foi perdido'),    # 2: verificacao 1a: perda
            _make_api_response(MERGED_RETRY_CONTENT),       # 3: retry merge
            _make_api_response('TODOS_PRESERVADOS'),         # 4: verificacao 2a: OK
        ]
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = side_effects
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch('app.agente.models.AgentMemory.get_by_path', return_value=mem), \
             patch('app.agente.services.pattern_analyzer._find_similar_empresa_memory',
                   return_value=None), \
             patch('app.agente.config.feature_flags.USE_MERGE_ENRICHMENT', True), \
             patch('app.agente.services.pattern_analyzer.anthropic', mock_anthropic):
            from app.agente.services.pattern_analyzer import _try_enrich_existing
            result = _try_enrich_existing(
                path=path, new_content=NEW_CONTENT, created_by=0,
                descricao='armadilha odoo',
            )

        assert result is True

        reloaded = AgentMemory.query.get(mem.id)
        assert MERGED_RETRY_CONTENT in reloaded.content, "Deve usar merged do retry"
        assert mock_client.messages.create.call_count == 4, "Deve ter feito 4 chamadas API"


# ─── cenario 3: verificacao falha 2x → None → append preserva ambos ────────

def test_merge_falls_back_to_append_when_verification_fails_twice(app, db, test_user, cleanup_memories):
    """
    Cenario 3: 2a verificacao tambem detecta perda ->
    _merge_memories_via_sonnet retorna None -> fallback append preserva ambos.
    Append tambem cria versao.
    """
    with app.app_context():
        path = '/memories/empresa/heuristicas/logistica/test-t01-c3.xml'
        mem = _make_memory(path, OLD_CONTENT)
        cleanup_memories.append(mem.id)

        # merge_result=False -> _merge_memories_via_sonnet retorna None
        result = _call_enrich(mem, path, NEW_CONTENT, 'heuristica logistica',
                              merge_flag=True, merge_result=False)

        assert result is True, "Fallback append retorna True"

        reloaded = AgentMemory.query.get(mem.id)
        assert OLD_CONTENT in reloaded.content, "Append deve preservar conteudo antigo"
        assert NEW_CONTENT in reloaded.content, "Append deve preservar conteudo novo"
        assert '<!-- Enriquecido em' in reloaded.content, "Marcador de append deve existir"

        # Versao criada mesmo no caminho de append
        versions = AgentMemoryVersion.query.filter_by(memory_id=mem.id).all()
        assert len(versions) >= 1, "Deve ter versao mesmo no caminho append"
        assert any(v.changed_by == 'sonnet' for v in versions), "changed_by deve ser 'sonnet'"


# ─── cenario 4: USE_MERGE_ENRICHMENT=False → append direto + versao ────────

def test_append_direct_also_creates_version(app, db, test_user, cleanup_memories):
    """
    Cenario 4: USE_MERGE_ENRICHMENT=False (append direto) -> versao criada.
    """
    with app.app_context():
        path = '/memories/empresa/protocolos/config/test-t01-c4.xml'
        mem = _make_memory(path, OLD_CONTENT)
        cleanup_memories.append(mem.id)

        # merge_flag=False -> append direto, sem chamar _merge_memories_via_sonnet
        result = _call_enrich(mem, path, NEW_CONTENT, 'protocolo config',
                              merge_flag=False)

        assert result is True

        versions = AgentMemoryVersion.query.filter_by(memory_id=mem.id).all()
        assert len(versions) >= 1, "Append direto tambem deve criar versao"
        latest = max(versions, key=lambda v: v.version)
        assert latest.content == OLD_CONTENT, "Versao deve ter o conteudo antigo"
        assert latest.changed_by == 'sonnet', "changed_by deve ser 'sonnet'"


# ─── cenario 5: exception na verificacao → merged aceito (best-effort) ──────

def test_verification_exception_accepts_merged(app, db, test_user, cleanup_memories):
    """
    Cenario 5: API da verificacao lanca exception -> merged aceito mesmo assim.
    Verificacao e best-effort: nao pode derrubar o pipeline.
    """
    with app.app_context():
        path = '/memories/empresa/heuristicas/operacional/test-t01-c5.xml'
        mem = _make_memory(path, OLD_CONTENT)
        cleanup_memories.append(mem.id)

        call_count = {'n': 0}

        def side_effect(**kw):
            call_count['n'] += 1
            if call_count['n'] == 1:
                return _make_api_response(MERGED_CONTENT)
            raise RuntimeError("API timeout simulado")

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = side_effect
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch('app.agente.models.AgentMemory.get_by_path', return_value=mem), \
             patch('app.agente.services.pattern_analyzer._find_similar_empresa_memory',
                   return_value=None), \
             patch('app.agente.config.feature_flags.USE_MERGE_ENRICHMENT', True), \
             patch('app.agente.services.pattern_analyzer.anthropic', mock_anthropic):
            from app.agente.services.pattern_analyzer import _try_enrich_existing
            result = _try_enrich_existing(
                path=path, new_content=NEW_CONTENT, created_by=0,
                descricao='heuristica operacional',
            )

        assert result is True, "Exception na verificacao NAO deve derrubar o pipeline"

        reloaded = AgentMemory.query.get(mem.id)
        assert MERGED_CONTENT in reloaded.content, "Merged deve ser aceito mesmo com exception"

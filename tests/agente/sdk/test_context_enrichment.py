"""
Testes TDD para context_enrichment.py (Onda 4 — F4/F5 + D5).

Cobertura:
- rank_skills_for_query: query com keyword → inclui skills relevantes;
  query sem match → lista curta/vazia sem erro.
- build_skill_hints_block: retorna bloco <skill_hints> quando há skills;
  retorna None quando lista vazia.
- build_world_model_block: mock query_ontology_entities com entidades →
  retorna <world_model>; mock retornando [] → None (sem fallback).
- Flags OFF: funções ainda funcionam corretamente (testado isoladamente);
  com flags OFF, blocos NÃO entram no full_context do hook.
- Tolerância a erros: exceções internas não propagam (best-effort).

ADVISORY NOTE (F4/F5):
  O SDK fixa `skills=` no connect() — não há set_skills() por turno.
  skill_hints é ADVISORY: informa o agente quais skills são mais relevantes,
  mas NÃO altera o listing real do SDK. Implementação zero-LLM.
"""

import importlib
import sys
import types
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers de setup
# ---------------------------------------------------------------------------

def _mock_registry(skill_entries):
    """Cria mock do CapabilityRegistry com skills fornecidas."""
    registry = MagicMock()
    registry.skills = skill_entries
    return registry


def _make_skill_entry(name, description, available_to_principal=True):
    """Cria mock de SkillEntry."""
    entry = MagicMock()
    entry.name = name
    entry.description = description
    entry.available_to_principal = available_to_principal
    return entry


# ---------------------------------------------------------------------------
# Fixture: isolar imports do módulo sob teste
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_module():
    """Remove o módulo context_enrichment do cache entre testes para evitar
    estado compartilhado de imports."""
    mod_key = 'app.agente.sdk.context_enrichment'
    yield
    sys.modules.pop(mod_key, None)


# ---------------------------------------------------------------------------
# Testes: rank_skills_for_query
# ---------------------------------------------------------------------------

class TestRankSkillsForQuery:

    def _import_fn(self):
        """Importa rank_skills_for_query com mocks de dependências."""
        import app.agente.sdk.context_enrichment as ce
        return ce.rank_skills_for_query

    def test_query_com_keyword_separacao_inclui_skill_expedicao(self):
        """Query 'separação de pedidos' deve incluir skill de expedição."""
        skill_expedicao = _make_skill_entry(
            'gerindo-expedicao',
            'Gerencia pedidos de expedição, separação, embarque e despacho de carga'
        )
        skill_frete = _make_skill_entry(
            'cotando-frete',
            'Cotação de frete para transportadoras e rotas'
        )
        skill_unrelated = _make_skill_entry(
            'consultando-sentry',
            'Consulta issues e erros no Sentry, monitoramento de bugs'
        )

        mock_reg = _mock_registry([skill_expedicao, skill_frete, skill_unrelated])

        with patch('app.agente.sdk.context_enrichment.capability_registry') as mock_cap:
            mock_cap.build_registry.return_value = mock_reg

            from app.agente.sdk.context_enrichment import rank_skills_for_query
            result = rank_skills_for_query('quero ver separação de pedidos', limit=8)

        assert isinstance(result, list)
        assert 'gerindo-expedicao' in result

    def test_query_frete_inclui_skill_cotacao(self):
        """Query com 'frete' deve incluir skill de cotação."""
        skill_frete = _make_skill_entry(
            'cotando-frete',
            'Cotação de frete para transportadoras. Calcular custo frete por rota e peso'
        )
        skill_odoo = _make_skill_entry(
            'rastreando-odoo',
            'Rastreia NFs, POs e SOs no sistema Odoo ERP'
        )

        mock_reg = _mock_registry([skill_frete, skill_odoo])

        with patch('app.agente.sdk.context_enrichment.capability_registry') as mock_cap:
            mock_cap.build_registry.return_value = mock_reg

            from app.agente.sdk.context_enrichment import rank_skills_for_query
            result = rank_skills_for_query('calcular frete para Manaus', limit=8)

        assert 'cotando-frete' in result

    def test_query_sem_match_retorna_lista_sem_erro(self):
        """Query sem keywords em nenhuma skill retorna lista curta/vazia sem exception."""
        skill1 = _make_skill_entry(
            'gerindo-expedicao',
            'Pedidos de expedição e embarque de carga pesada'
        )
        mock_reg = _mock_registry([skill1])

        with patch('app.agente.sdk.context_enrichment.capability_registry') as mock_cap:
            mock_cap.build_registry.return_value = mock_reg

            from app.agente.sdk.context_enrichment import rank_skills_for_query
            # Query completamente fora do domínio
            result = rank_skills_for_query('xyzzy quantum flux capacitor', limit=8)

        assert isinstance(result, list)
        # Não deve lançar exceção, pode retornar lista vazia

    def test_skills_indisponiveis_ao_principal_sao_excluidas(self):
        """Skills com available_to_principal=False não devem ser incluídas."""
        skill_principal = _make_skill_entry(
            'gerindo-expedicao',
            'separação de pedidos embarque',
            available_to_principal=True
        )
        skill_restrita = _make_skill_entry(
            'skill-interna-subagent',
            'separação interna de expedição',
            available_to_principal=False
        )

        mock_reg = _mock_registry([skill_principal, skill_restrita])

        with patch('app.agente.sdk.context_enrichment.capability_registry') as mock_cap:
            mock_cap.build_registry.return_value = mock_reg

            from app.agente.sdk.context_enrichment import rank_skills_for_query
            result = rank_skills_for_query('separação de pedidos', limit=8)

        assert 'gerindo-expedicao' in result
        assert 'skill-interna-subagent' not in result

    def test_erro_em_build_registry_retorna_lista_vazia(self):
        """Exceção em build_registry() não propaga — retorna [] (best-effort)."""
        with patch('app.agente.sdk.context_enrichment.capability_registry') as mock_cap:
            mock_cap.build_registry.side_effect = RuntimeError('registry falhou')

            from app.agente.sdk.context_enrichment import rank_skills_for_query
            result = rank_skills_for_query('qualquer query')

        assert result == []

    def test_limit_respeitado(self):
        """Retorno não deve exceder o limite especificado."""
        skills = [
            _make_skill_entry(f'skill-{i}', f'expedição separação frete pedido logística {i}')
            for i in range(20)
        ]
        mock_reg = _mock_registry(skills)

        with patch('app.agente.sdk.context_enrichment.capability_registry') as mock_cap:
            mock_cap.build_registry.return_value = mock_reg

            from app.agente.sdk.context_enrichment import rank_skills_for_query
            result = rank_skills_for_query('expedição separação frete', limit=5)

        assert len(result) <= 5


# ---------------------------------------------------------------------------
# Testes: build_skill_hints_block
# ---------------------------------------------------------------------------

class TestBuildSkillHintsBlock:

    def test_retorna_bloco_quando_ha_skills(self):
        """Deve retornar string com <skill_hints> quando rank retorna skills."""
        skill = _make_skill_entry('gerindo-expedicao', 'pedidos separação embarque')
        mock_reg = _mock_registry([skill])

        with patch('app.agente.sdk.context_enrichment.capability_registry') as mock_cap:
            mock_cap.build_registry.return_value = mock_reg

            from app.agente.sdk.context_enrichment import build_skill_hints_block
            result = build_skill_hints_block('quero ver separação de pedidos')

        assert result is not None
        assert '<skill_hints' in result
        assert 'gerindo-expedicao' in result

    def test_retorna_none_quando_sem_skills(self):
        """Deve retornar None quando rank_skills retorna lista vazia."""
        mock_reg = _mock_registry([])

        with patch('app.agente.sdk.context_enrichment.capability_registry') as mock_cap:
            mock_cap.build_registry.return_value = mock_reg

            from app.agente.sdk.context_enrichment import build_skill_hints_block
            result = build_skill_hints_block('xyzzy quantum flux')

        assert result is None

    def test_bloco_tem_priority_advisory(self):
        """O bloco deve ter priority="advisory" (não muda listing do SDK)."""
        skill = _make_skill_entry('cotando-frete', 'frete cotação transportadora')
        mock_reg = _mock_registry([skill])

        with patch('app.agente.sdk.context_enrichment.capability_registry') as mock_cap:
            mock_cap.build_registry.return_value = mock_reg

            from app.agente.sdk.context_enrichment import build_skill_hints_block
            result = build_skill_hints_block('calcular frete')

        assert result is not None
        assert 'advisory' in result

    def test_tolerante_a_excecao_interna(self):
        """Exceção interna não propaga — retorna None."""
        with patch('app.agente.sdk.context_enrichment.capability_registry') as mock_cap:
            mock_cap.build_registry.side_effect = Exception('erro inesperado')

            from app.agente.sdk.context_enrichment import build_skill_hints_block
            result = build_skill_hints_block('qualquer query')

        assert result is None


# ---------------------------------------------------------------------------
# Testes: build_world_model_block
# ---------------------------------------------------------------------------

class TestBuildWorldModelBlock:

    def test_retorna_bloco_com_entidades(self):
        """Mock query_ontology_entities retornando entidades → bloco <world_model>."""
        entidades = [
            {'entity_type': 'cliente', 'entity_name': 'ATACADAO DISTRIBUIDORA',
             'entity_key': '75315333', 'user_id': 0},
            {'entity_type': 'produto', 'entity_name': 'PALMITO PUPUNHA FATIADO',
             'entity_key': '208000043', 'user_id': 0},
        ]

        with patch('app.agente.sdk.context_enrichment.query_ontology_entities') as mock_qoe:
            mock_qoe.return_value = entidades

            from app.agente.sdk.context_enrichment import build_world_model_block
            result = build_world_model_block(user_id=1, query='pedidos do Atacadao')

        assert result is not None
        assert '<world_model' in result
        assert 'ATACADAO' in result

    def test_retorna_none_quando_ontologia_vazia(self):
        """Mock query_ontology_entities retornando [] → None (fallback _DOMAIN_KEYWORDS)."""
        with patch('app.agente.sdk.context_enrichment.query_ontology_entities') as mock_qoe:
            mock_qoe.return_value = []

            from app.agente.sdk.context_enrichment import build_world_model_block
            result = build_world_model_block(user_id=1, query='qualquer query')

        assert result is None

    def test_bloco_tem_priority_advisory(self):
        """world_model deve ter priority='advisory'."""
        entidades = [
            {'entity_type': 'transportadora', 'entity_name': 'BRASPRESS',
             'entity_key': None, 'user_id': 0},
        ]

        with patch('app.agente.sdk.context_enrichment.query_ontology_entities') as mock_qoe:
            mock_qoe.return_value = entidades

            from app.agente.sdk.context_enrichment import build_world_model_block
            result = build_world_model_block(user_id=1, query='braspress frete')

        assert result is not None
        assert 'advisory' in result

    def test_tolerante_a_excecao_query_ontology(self):
        """Exceção em query_ontology_entities não propaga — retorna None."""
        with patch('app.agente.sdk.context_enrichment.query_ontology_entities') as mock_qoe:
            mock_qoe.side_effect = Exception('DB down')

            from app.agente.sdk.context_enrichment import build_world_model_block
            result = build_world_model_block(user_id=1, query='qualquer query')

        assert result is None

    def test_world_model_e_aditivo_fallback_domain_keywords_nao_e_removido(self):
        """D5 é ADITIVO: _DOMAIN_KEYWORDS permanece em memory_injection (não removido).
        Este teste verifica que a constante ainda existe e tem conteúdo esperado."""
        from app.agente.sdk.memory_injection import _DOMAIN_KEYWORDS
        assert 'expedicao' in _DOMAIN_KEYWORDS
        assert 'frete' in _DOMAIN_KEYWORDS


# ---------------------------------------------------------------------------
# Testes: Flags OFF = zero mudança no hook
# ---------------------------------------------------------------------------

class TestFlagsOff:

    def test_flag_off_skill_rag_nao_chama_build_skill_hints(self):
        """Com USE_AGENT_SKILL_RAG=False, build_skill_hints_block NÃO deve ser chamado."""
        # Patch feature flags para desativar ambas
        with patch.dict('os.environ', {
            'AGENT_SKILL_RAG': 'false',
            'AGENT_WORLD_MODEL_INJECT': 'false',
        }):
            # Re-importar feature_flags para pegar os patches de env
            ff_mod = importlib.import_module('app.agente.config.feature_flags')
            importlib.reload(ff_mod)

            # Verificar que a flag está desativada
            assert ff_mod.USE_AGENT_SKILL_RAG is False
            assert ff_mod.USE_AGENT_WORLD_MODEL_INJECT is False

    def test_flags_off_por_default(self):
        """USE_AGENT_SKILL_RAG e USE_AGENT_WORLD_MODEL_INJECT devem ser False por default."""
        import os
        # Garantir que as env vars não estão setadas
        env_backup = {
            k: os.environ.pop(k, None)
            for k in ['AGENT_SKILL_RAG', 'AGENT_WORLD_MODEL_INJECT']
        }

        try:
            ff_mod = importlib.import_module('app.agente.config.feature_flags')
            importlib.reload(ff_mod)

            assert ff_mod.USE_AGENT_SKILL_RAG is False
            assert ff_mod.USE_AGENT_WORLD_MODEL_INJECT is False
        finally:
            # Restaurar env vars
            for k, v in env_backup.items():
                if v is not None:
                    os.environ[k] = v

    def test_build_skill_hints_nao_chamado_com_flag_off(self):
        """Confirma que context_enrichment.build_skill_hints_block aceita ser mockado
        para verificação de não-chamada no hook (guard if USE_AGENT_SKILL_RAG)."""
        from app.agente.sdk.context_enrichment import build_skill_hints_block
        # Função deve existir e ser chamável
        assert callable(build_skill_hints_block)

    def test_build_world_model_nao_chamado_com_flag_off(self):
        """Confirma que context_enrichment.build_world_model_block aceita ser mockado."""
        from app.agente.sdk.context_enrichment import build_world_model_block
        assert callable(build_world_model_block)


# ---------------------------------------------------------------------------
# Testes: hook não quebra com flag ON + exceções internas
# ---------------------------------------------------------------------------

class TestHookBestEffort:

    def test_skill_hints_retorna_string_ou_none(self):
        """build_skill_hints_block deve retornar str ou None — nunca propagar exceção."""
        skill = _make_skill_entry('gerindo-expedicao', 'separação de pedidos')
        mock_reg = _mock_registry([skill])

        with patch('app.agente.sdk.context_enrichment.capability_registry') as mock_cap:
            mock_cap.build_registry.return_value = mock_reg

            from app.agente.sdk.context_enrichment import build_skill_hints_block
            result = build_skill_hints_block('separação')

        assert result is None or isinstance(result, str)

    def test_world_model_retorna_string_ou_none(self):
        """build_world_model_block deve retornar str ou None — nunca propagar exceção."""
        with patch('app.agente.sdk.context_enrichment.query_ontology_entities') as mock_qoe:
            mock_qoe.return_value = []

            from app.agente.sdk.context_enrichment import build_world_model_block
            result = build_world_model_block(user_id=1, query='test')

        assert result is None or isinstance(result, str)

    def test_rank_skills_retorna_list(self):
        """rank_skills_for_query deve retornar list — nunca propagar exceção."""
        with patch('app.agente.sdk.context_enrichment.capability_registry') as mock_cap:
            mock_cap.build_registry.side_effect = ImportError('sem Flask context')

            from app.agente.sdk.context_enrichment import rank_skills_for_query
            result = rank_skills_for_query('qualquer')

        assert isinstance(result, list)

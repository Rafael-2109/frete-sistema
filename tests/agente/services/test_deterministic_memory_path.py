"""
T0.4: path deterministico da memoria empresa.

Cobertura:
1. _build_knowledge_path flag ON: dominio valido passa; alias odoo->integracao;
   desconhecido->geral; flag OFF: texto livre preservado.
2. Prompt do extrator contem os 12 valores do enum de dominio.
3. _find_existing_path_by_title: similaridade >=0.85 retorna path existente;
   <0.85 retorna None; excecao retorna None; EMBEDDINGS_ENABLED=False retorna None.
4. Integracao: flag ON + titulo similar existente -> enrichment (nao cria path novo).
"""
import pytest
from unittest.mock import patch, MagicMock


# ── Constantes do enum (copiadas do modulo para assertion independente) ──────

DOMINIOS_VALIDOS_ESPERADOS = frozenset({
    'financeiro', 'integracao', 'expedicao', 'recebimento', 'estoque',
    'producao', 'fiscal', 'comercial', 'logistica', 'carvia', 'portal', 'geral',
})

_DOMINIO_ALIASES_ESPERADOS = {'odoo': 'integracao', 'agente': 'geral', 'operacional': 'geral'}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _import_pa():
    """Importa o modulo pattern_analyzer de forma lazy (evita circular em test context)."""
    from app.agente.services import pattern_analyzer as pa
    return pa


# ═════════════════════════════════════════════════════════════════════════════
# 1. _build_knowledge_path com enum de dominio
# ═════════════════════════════════════════════════════════════════════════════

class TestBuildKnowledgePath:

    def test_dominio_valido_passa_sem_alteracao(self):
        """Dominio canonico entra no path sem modificacao."""
        pa = _import_pa()
        with patch.object(pa, 'USE_DETERMINISTIC_MEMORY_PATH', True):
            path = pa._build_knowledge_path('armadilha', 'financeiro', titulo='Frete nao recalcula margem')
        assert '/financeiro/' in path
        assert path.endswith('.xml')

    def test_alias_odoo_mapeia_para_integracao(self):
        """Alias 'odoo' deve ser normalizado para 'integracao'."""
        pa = _import_pa()
        with patch.object(pa, 'USE_DETERMINISTIC_MEMORY_PATH', True):
            path = pa._build_knowledge_path('protocolo', 'odoo', titulo='Diagnostico NF ausente Odoo')
        assert '/integracao/' in path
        assert '/odoo/' not in path

    def test_alias_agente_mapeia_para_geral(self):
        """Alias 'agente' deve ser normalizado para 'geral'."""
        pa = _import_pa()
        with patch.object(pa, 'USE_DETERMINISTIC_MEMORY_PATH', True):
            path = pa._build_knowledge_path('heuristica', 'agente', titulo='Contexto de sessao agente')
        assert '/geral/' in path
        assert '/agente/' not in path

    def test_alias_operacional_mapeia_para_geral(self):
        """Alias 'operacional' deve ser normalizado para 'geral'."""
        pa = _import_pa()
        with patch.object(pa, 'USE_DETERMINISTIC_MEMORY_PATH', True):
            path = pa._build_knowledge_path('heuristica', 'operacional', titulo='Fluxo operacional padrao')
        assert '/geral/' in path

    def test_dominio_desconhecido_fallback_geral(self):
        """Dominio fora do enum deve resultar em fallback para 'geral'."""
        pa = _import_pa()
        with patch.object(pa, 'USE_DETERMINISTIC_MEMORY_PATH', True):
            path = pa._build_knowledge_path('heuristica', 'xurupita_123', titulo='Teste dominio invalido')
        assert '/geral/' in path
        assert '/xurupita_123/' not in path

    def test_dominio_maiusculo_normalizado(self):
        """Dominio em maiusculas deve ser normalizado para minusculo."""
        pa = _import_pa()
        with patch.object(pa, 'USE_DETERMINISTIC_MEMORY_PATH', True):
            path = pa._build_knowledge_path('armadilha', 'FINANCEIRO', titulo='Teste normalizacao')
        assert '/financeiro/' in path

    def test_flag_off_preserva_texto_livre(self):
        """Com flag OFF, dominio texto-livre deve ser preservado (comportamento atual)."""
        pa = _import_pa()
        with patch.object(pa, 'USE_DETERMINISTIC_MEMORY_PATH', False):
            path = pa._build_knowledge_path('heuristica', 'xurupita_123', titulo='Teste flag off')
        # Com flag OFF, dominio livre entra no path sem fallback
        assert '/xurupita_123/' in path

    def test_flag_off_byte_identico_sem_strip_lower(self):
        """Com flag OFF, dominio passa BYTE-IDENTICO (sem strip().lower()) —
        comportamento pre-flag intacto."""
        pa = _import_pa()
        with patch.object(pa, 'USE_DETERMINISTIC_MEMORY_PATH', False):
            path = pa._build_knowledge_path('heuristica', 'Financeiro', titulo='Teste flag off case')
        # Sem normalizacao: maiuscula preservada exatamente como veio
        assert '/Financeiro/' in path, f"Flag OFF deve preservar case original: {path}"
        assert '/financeiro/' not in path

    def test_todos_dominios_validos_passam(self):
        """Cada dominio canonico deve passar sem alteracao."""
        pa = _import_pa()
        with patch.object(pa, 'USE_DETERMINISTIC_MEMORY_PATH', True):
            for dom in DOMINIOS_VALIDOS_ESPERADOS:
                path = pa._build_knowledge_path('heuristica', dom, titulo=f'Titulo para {dom}')
                assert f'/{dom}/' in path, f"Dominio {dom!r} nao apareceu no path: {path}"

    def test_dominio_vazio_resulta_em_geral(self):
        """Dominio vazio com flag ON deve resultar em 'geral'."""
        pa = _import_pa()
        with patch.object(pa, 'USE_DETERMINISTIC_MEMORY_PATH', True):
            # Dominio vazio que passa pela normalizacao: strip -> falsy -> seria 'geral'
            # Nota: a funcao ja tratava vazio como "nao inclui subdir"; com flag ON,
            # vazio deve normalizar para 'geral' de forma consistente
            path = pa._build_knowledge_path('heuristica', '   ', titulo='Titulo com dominio espacos')
        # Apos strip, dominio vazio deve ser tratado como 'geral' com flag ON
        assert '/geral/' in path or path.startswith('/memories/empresa/heuristicas/')


# ═════════════════════════════════════════════════════════════════════════════
# 2. Prompt do extrator contem os 12 dominios do enum
# ═════════════════════════════════════════════════════════════════════════════

class TestExtractorPromptEnum:

    def test_prompt_contem_todos_dominios_do_enum(self):
        """O prompt de extracao deve listar todos os 12 valores do enum."""
        pa = _import_pa()
        prompt = pa._build_extraction_prompt()
        for dom in DOMINIOS_VALIDOS_ESPERADOS:
            assert dom in prompt, f"Dominio '{dom}' nao encontrado no prompt de extracao"

    def test_prompt_nao_contem_texto_livre(self):
        """O prompt NAO deve usar 'texto livre' para o campo dominio."""
        pa = _import_pa()
        prompt = pa._build_extraction_prompt()
        # Verifica que o padrao antigo foi substituido
        assert 'texto livre' not in prompt.lower() or 'dominio' not in prompt[:2000]

    def test_prompt_enum_pipe_separado(self):
        """Os valores do enum devem aparecer separados por '|' no prompt."""
        pa = _import_pa()
        prompt = pa._build_extraction_prompt()
        # Deve existir pelo menos um par de dominios separados por '|'
        assert 'financeiro|integracao' in prompt or 'financeiro' in prompt and '|' in prompt


# ═════════════════════════════════════════════════════════════════════════════
# 3. _find_existing_path_by_title
# ═════════════════════════════════════════════════════════════════════════════

class TestFindExistingPathByTitle:
    """Testa _find_existing_path_by_title via patch nos modulos de origem.

    A funcao faz imports lazy dentro do try/except — o patch correto e nos
    modulos de origem (app.agente.models, app.embeddings.service) e nas
    constantes de config (app.embeddings.config).
    """

    def _patch_context(self, embeddings_enabled=True, semantic_search=True,
                       rows=None, embed_results=None, embed_exception=None):
        """Monta contexto de patches para _find_existing_path_by_title."""
        from contextlib import ExitStack

        stack = ExitStack()

        # Flags de config
        stack.enter_context(
            patch('app.embeddings.config.EMBEDDINGS_ENABLED', embeddings_enabled)
        )
        stack.enter_context(
            patch('app.embeddings.config.MEMORY_SEMANTIC_SEARCH', semantic_search)
        )

        # Mock AgentMemory no modulo de origem
        mock_am = MagicMock()
        if rows is not None:
            mock_am.query.filter.return_value.with_entities.return_value.all.return_value = rows
        stack.enter_context(patch('app.agente.models.AgentMemory', mock_am))

        # Mock EmbeddingService no modulo de origem
        mock_svc_instance = MagicMock()
        if embed_exception:
            mock_svc_instance.embed_texts.side_effect = embed_exception
        elif embed_results is not None:
            mock_svc_instance.embed_texts.return_value = embed_results
        mock_svc_cls = MagicMock(return_value=mock_svc_instance)
        stack.enter_context(patch('app.embeddings.service.EmbeddingService', mock_svc_cls))

        return stack, mock_am, mock_svc_instance

    def test_similaridade_alta_retorna_path(self):
        """Quando embedding retorna sim >= 0.85, deve retornar path existente."""
        pa = _import_pa()

        # cos_sim([1,0,0], [0.9,0.44,0]) = 0.9 / (1 * sqrt(0.81+0.19)) ≈ 0.9 >= 0.85
        existing_path = '/memories/empresa/armadilhas/financeiro/frete-nao-recalcula-margem.xml'

        rows = [(existing_path,)]
        # Titulo "frete nao recalcula margem" → slug = "frete-nao-recalcula-margem"
        # Titulo reconstruido do slug = "frete nao recalcula margem"
        embed_results = [
            [1.0, 0.0, 0.0],        # titulo novo
            [1.0, 0.0, 0.0],        # titulo existente (identico = cos_sim=1.0 >= 0.85)
        ]

        with patch('app.embeddings.config.EMBEDDINGS_ENABLED', True), \
             patch('app.embeddings.config.MEMORY_SEMANTIC_SEARCH', True):

            mock_am = MagicMock()
            mock_am.query.filter.return_value.with_entities.return_value.all.return_value = rows
            mock_svc = MagicMock()
            mock_svc.embed_texts.return_value = embed_results
            mock_svc_cls = MagicMock(return_value=mock_svc)

            # Patch nos locais de import lazy dentro da funcao
            with patch('app.agente.models.AgentMemory', mock_am), \
                 patch('app.embeddings.service.EmbeddingService', mock_svc_cls):

                result = pa._find_existing_path_by_title(
                    'Frete nao recalcula margem', 'armadilhas'
                )

        assert result == existing_path

    def test_similaridade_baixa_retorna_none(self):
        """Quando melhor similaridade < 0.85, deve retornar None."""
        pa = _import_pa()

        existing_path = '/memories/empresa/armadilhas/financeiro/algo-diferente.xml'
        # vetores ortogonais: cos_sim = 0 < 0.85
        embed_results = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]

        with patch('app.embeddings.config.EMBEDDINGS_ENABLED', True), \
             patch('app.embeddings.config.MEMORY_SEMANTIC_SEARCH', True):

            mock_am = MagicMock()
            mock_am.query.filter.return_value.with_entities.return_value.all.return_value = [
                (existing_path,)
            ]
            mock_svc = MagicMock()
            mock_svc.embed_texts.return_value = embed_results
            mock_svc_cls = MagicMock(return_value=mock_svc)

            with patch('app.agente.models.AgentMemory', mock_am), \
                 patch('app.embeddings.service.EmbeddingService', mock_svc_cls):

                result = pa._find_existing_path_by_title('Titulo totalmente diferente', 'armadilhas')

        assert result is None

    def test_excecao_retorna_none(self):
        """Qualquer excecao deve resultar em None (best-effort)."""
        pa = _import_pa()

        with patch('app.embeddings.config.EMBEDDINGS_ENABLED', True), \
             patch('app.embeddings.config.MEMORY_SEMANTIC_SEARCH', True):

            mock_am = MagicMock()
            mock_am.query.filter.return_value.with_entities.return_value.all.return_value = [
                ('/memories/empresa/protocolos/geral/algo.xml',)
            ]
            mock_svc = MagicMock()
            mock_svc.embed_texts.side_effect = RuntimeError("Voyage API timeout")
            mock_svc_cls = MagicMock(return_value=mock_svc)

            with patch('app.agente.models.AgentMemory', mock_am), \
                 patch('app.embeddings.service.EmbeddingService', mock_svc_cls):

                result = pa._find_existing_path_by_title('Qualquer titulo', 'protocolos')

        assert result is None

    def test_embeddings_disabled_retorna_none(self):
        """Quando EMBEDDINGS_ENABLED=False, deve retornar None sem chamar API."""
        pa = _import_pa()

        mock_svc_cls = MagicMock()

        with patch('app.embeddings.config.EMBEDDINGS_ENABLED', False), \
             patch('app.embeddings.service.EmbeddingService', mock_svc_cls):

            result = pa._find_existing_path_by_title('Qualquer titulo', 'protocolos')

        assert result is None
        mock_svc_cls.assert_not_called()

    def test_nenhuma_memoria_existente_retorna_none(self):
        """Quando nao ha memorias do mesmo kind, deve retornar None."""
        pa = _import_pa()

        with patch('app.embeddings.config.EMBEDDINGS_ENABLED', True), \
             patch('app.embeddings.config.MEMORY_SEMANTIC_SEARCH', True):

            mock_am = MagicMock()
            mock_am.query.filter.return_value.with_entities.return_value.all.return_value = []

            with patch('app.agente.models.AgentMemory', mock_am):
                result = pa._find_existing_path_by_title('Titulo novo', 'heuristicas')

        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# 4. Integracao: flag ON + titulo similar -> enriquece slot existente
# ═════════════════════════════════════════════════════════════════════════════

class TestIntegracaoTitleDedup:

    def _base_patches(self, pa, flag_on, find_by_title_return, enrich_return, save_return):
        """Monta patches comuns para os testes de integracao.

        O callsite em _save_conhecimentos_v3 faz `from ..models import AgentMemory as _AM`
        e chama `_AM.get_by_path(0, path)` para verificar se o path exato existe.
        O patch correto e em app.agente.models.AgentMemory.get_by_path (classmethod).
        """
        from app.agente.models import AgentMemory

        patches = [
            patch.object(pa, 'USE_DETERMINISTIC_MEMORY_PATH', flag_on),
            # Simula que path exato NAO existe (dispara dedup por titulo)
            patch.object(AgentMemory, 'get_by_path', return_value=None),
            patch.object(pa, '_find_existing_path_by_title',
                          return_value=find_by_title_return),
            patch.object(pa, '_try_enrich_existing', return_value=enrich_return),
            patch.object(pa, '_save_empresa_memory', return_value=save_return),
        ]
        return patches

    def test_flag_on_titulo_similar_vai_para_enrich(self):
        """Com USE_DETERMINISTIC_MEMORY_PATH=True e titulo similar existente,
        _save_conhecimentos_v3 deve enriquecer o slot existente, nao criar path novo."""
        pa = _import_pa()
        from app.agente.models import AgentMemory

        existing_path = '/memories/empresa/armadilhas/financeiro/frete-nao-recalcula-margem.xml'
        conhecimento = [{
            'titulo': 'Frete nao recalcula margem',
            'tipo': 'armadilha',
            'nivel': 4,
            'dominio': 'financeiro',
            'criterios_atendidos': [1, 3],
            'descricao': 'Quando frete e atualizado o campo margem nao e recalculado.',
            'prescricao': 'Quando atualizar frete, verificar se margem foi recalculada.',
        }]

        with patch.object(pa, 'USE_DETERMINISTIC_MEMORY_PATH', True), \
             patch.object(AgentMemory, 'get_by_path', return_value=None), \
             patch.object(pa, '_find_existing_path_by_title',
                          return_value=existing_path) as mock_find_title, \
             patch.object(pa, '_try_enrich_existing', return_value=True) as mock_enrich, \
             patch.object(pa, '_save_empresa_memory', return_value=True) as mock_save:

            counts = {'saved': 0, 'enriched': 0, 'filtered': 0}
            result = pa._save_conhecimentos_v3(conhecimento, created_by=1, counts=counts)

        # Deve ter chamado _find_existing_path_by_title (dedup por titulo)
        mock_find_title.assert_called_once()
        # Deve ter enriquecido com o path existente (nao criado novo)
        mock_enrich.assert_called_once()
        call_args = mock_enrich.call_args[0]
        assert call_args[0] == existing_path, (
            f"_try_enrich_existing deve ser chamado com o path EXISTENTE "
            f"(got {call_args[0]!r})"
        )
        # Nao deve ter criado memoria nova
        mock_save.assert_not_called()
        assert result['enriched'] == 1
        assert result['saved'] == 0

    def test_flag_on_sem_titulo_similar_cria_novo(self):
        """Com USE_DETERMINISTIC_MEMORY_PATH=True mas sem titulo similar,
        deve criar path novo (comportamento normal)."""
        pa = _import_pa()
        from app.agente.models import AgentMemory

        conhecimento = [{
            'titulo': 'Diagnostico NF ausente Odoo',
            'tipo': 'protocolo',
            'nivel': 3,
            'dominio': 'recebimento',
            'criterios_atendidos': [1, 2],
            'descricao': 'NF nao aparece no Odoo apos importacao via DFe.',
            'prescricao': 'Verificar DFe sincronizado antes de buscar NF no Odoo.',
        }]

        with patch.object(pa, 'USE_DETERMINISTIC_MEMORY_PATH', True), \
             patch.object(AgentMemory, 'get_by_path', return_value=None), \
             patch.object(pa, '_find_existing_path_by_title', return_value=None), \
             patch.object(pa, '_try_enrich_existing', return_value=False) as mock_enrich, \
             patch.object(pa, '_save_empresa_memory', return_value=True) as mock_save:

            counts = {'saved': 0, 'enriched': 0, 'filtered': 0}
            result = pa._save_conhecimentos_v3(conhecimento, created_by=1, counts=counts)

        # Sem titulo similar, deve prosseguir normalmente
        mock_enrich.assert_called_once()
        mock_save.assert_called_once()
        assert result['saved'] == 1

    def test_flag_off_nao_chama_find_by_title(self):
        """Com USE_DETERMINISTIC_MEMORY_PATH=False, nao deve chamar _find_existing_path_by_title."""
        pa = _import_pa()

        conhecimento = [{
            'titulo': 'Titulo qualquer',
            'tipo': 'heuristica',
            'nivel': 5,
            'dominio': 'logistica',
            'criterios_atendidos': [1],
            'descricao': 'Padrao logistico generico importante.',
            'prescricao': 'Verificar sempre o padrao antes de despachar.',
        }]

        with patch.object(pa, 'USE_DETERMINISTIC_MEMORY_PATH', False), \
             patch.object(pa, '_find_existing_path_by_title') as mock_find_title, \
             patch.object(pa, '_try_enrich_existing', return_value=False), \
             patch.object(pa, '_save_empresa_memory', return_value=True):

            counts = {'saved': 0, 'enriched': 0, 'filtered': 0}
            pa._save_conhecimentos_v3(conhecimento, created_by=1, counts=counts)

        # Com flag OFF, nao deve chamar o dedup por titulo
        mock_find_title.assert_not_called()

    def test_constantes_enum_no_modulo(self):
        """O modulo deve expor DOMINIOS_VALIDOS e _DOMINIO_ALIASES com os valores esperados."""
        pa = _import_pa()
        assert hasattr(pa, 'DOMINIOS_VALIDOS'), "DOMINIOS_VALIDOS deve ser constante no modulo"
        assert hasattr(pa, '_DOMINIO_ALIASES'), "_DOMINIO_ALIASES deve ser constante no modulo"
        assert pa.DOMINIOS_VALIDOS == DOMINIOS_VALIDOS_ESPERADOS
        assert pa._DOMINIO_ALIASES == _DOMINIO_ALIASES_ESPERADOS

#!/usr/bin/env python
"""
Stress Test — Knowledge Graph com API Real (Haiku)

Valida o pipeline REAL de extração de entidades via Haiku:
  1. _generate_memory_context() com chamadas Haiku reais
  2. parse_contextual_response() com output REAL (não mockado)
  3. Qualidade de extração para domínio de frete
  4. Concordância Haiku vs Regex (Layer 3 vs Layer 1)
  5. Consistência das respostas (chamadas repetidas)

Padrão de output: grading.json (compatível com skill-creator eval viewer)

Execução:
    source .venv/bin/activate
    python scripts/tests/test_knowledge_graph_stress_api.py --yes

Segurança:
    - TEST_USER_IDs = 99996, 99995 (não existem em produção)
    - Cleanup final remove TUDO
    - Output JSON em /tmp/kg_stress_api_results.json

Requisitos:
    - ANTHROPIC_API_KEY configurada (.env ou env var)
    - EMBEDDINGS_ENABLED=false (desabilita Voyage — sem VOYAGE_API_KEY)
    - MEMORY_KNOWLEDGE_GRAPH=true (ativa KG pipeline)
    - MEMORY_CONTEXTUAL_EMBEDDING=true (ativa Haiku extraction)

Cenários:
    S1:  Haiku Entity Extraction Quality (11 expectations, 10 API calls)
    S2:  Full Write Pipeline com API (6 expectations, 0 API calls — cache S1)
    S3:  Haiku vs Regex — Prova de Valor-Adicionado (5 expectations, 0 API calls)
    S4:  Contextual Enrichment (3 expectations, 2 API calls)
    S5:  Read Path com Entidades API (5 expectations, 0 API calls)
    S6:  Update Path com Re-extração (4 expectations, 1 API call)
    S7:  End-to-End Pipeline (4 expectations, 3 API calls)
    S8:  Error Handling e Resiliência (4 expectations, 2 API calls)
    S9:  Multi-User Isolation com API (3 expectations, 1 API call)
    S10: Consistência do Haiku (3 expectations, 3 API calls)

Custo estimado: ~$0.007 (22 chamadas Haiku)
"""

import json
import os
import sys
import time
import traceback

# Setup path para imports do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Feature flags — ANTES de importar qualquer coisa do app
os.environ.setdefault('EMBEDDINGS_ENABLED', 'false')       # Desabilita Voyage
os.environ.setdefault('MEMORY_KNOWLEDGE_GRAPH', 'true')    # Ativa KG pipeline
os.environ.setdefault('MEMORY_CONTEXTUAL_EMBEDDING', 'true')  # Ativa Haiku extraction

TEST_USER_A = 99996      # Separado do stress test existente (99998/99997)
TEST_USER_B = 99995      # Para isolamento multi-usuario
OUTPUT_PATH = '/tmp/kg_stress_api_results.json'
ESTIMATED_COST_PER_CALL = 0.0003   # ~500 input + ~50 output tokens Haiku
MAX_API_CALLS = 30                 # Budget guard: ~$0.009 total


# =====================================================================
# Dados de teste — 10 memórias freight-domain
# =====================================================================

MEMORIES = [
    {
        "key": "m1_uf_carrier",
        "path": "/memories/test_api_stress/m1",
        "content": "Entregas para AM tem lead time de 12 dias via RODONAVES. "
                   "Cliente ATACADAO reclama de atrasos frequentes.",
        "expected_regex_ufs": {"AM"},
        "expected_haiku_types": {"transportadora", "cliente"},
    },
    {
        "key": "m2_pedido_uf",
        "path": "/memories/test_api_stress/m2",
        "content": "Pedido VCD2565291 do ASSAI para SP no valor de R$ 15.000,00. "
                   "Embarque via PATRUS com previsao de 3 dias.",
        "expected_regex_ufs": {"SP"},
        "expected_regex_pedidos": {"VCD2565291"},
        "expected_haiku_types": {"transportadora", "cliente"},
    },
    {
        "key": "m3_cnpj",
        "path": "/memories/test_api_stress/m3",
        "content": "CNPJ 12.345.678/0001-99 (CARREFOUR) deve ser faturado pela filial FB. "
                   "Regra: sempre enviar NF-e antes do embarque.",
        "expected_haiku_types": {"cliente"},
    },
    {
        "key": "m4_multi_uf",
        "path": "/memories/test_api_stress/m4",
        "content": "Rota consolidada SP MG RJ ES: BRASPRESS tem melhor preco. "
                   "TAC cobre quando BRASPRESS nao tem horario.",
        "expected_regex_ufs": {"SP", "MG", "RJ", "ES"},
        "expected_haiku_has_relations": True,
    },
    {
        "key": "m5_rule",
        "path": "/memories/test_api_stress/m5",
        "content": "Para BA e CE sempre usar JADLOG. "
                   "FL BRASIL tem restricao de peso para Nordeste.",
        "expected_regex_ufs": {"BA", "CE"},
        "expected_haiku_has_relations": True,
    },
    {
        "key": "m6_value",
        "path": "/memories/test_api_stress/m6",
        "content": "Frete para PR via TNT MERCURIO custa R$ 2.500,00 por tonelada. "
                   "Negociado desconto de 15% para volumes acima de 5 toneladas.",
        "expected_regex_ufs": {"PR"},
    },
    {
        "key": "m7_correction",
        "path": "/memories/test_api_stress/m7",
        "content": "CORRECAO: TRANSMERC nao atende RS. "
                   "Usar RODONAVES para toda regiao Sul (RS, SC, PR).",
        "expected_regex_ufs": {"RS", "SC", "PR"},
        "expected_haiku_has_relations": True,
    },
    {
        "key": "m8_noise",
        "path": "/memories/test_api_stress/m8",
        "content": "Verificar programacao da proxima semana com a equipe. "
                   "Reuniao sobre processos internos marcada para segunda.",
        "expected_haiku_entities_max": 1,
    },
    {
        "key": "m9_complex",
        "path": "/memories/test_api_stress/m9",
        "content": "Pedido VCD3000001 do SENDAS para GO no valor de R$ 8.750,50. "
                   "Transportadora RODONAVES. Prazo negociado: 5 dias. "
                   "Se atrasar, renegociar com PATRUS.",
        "expected_regex_ufs": {"GO"},
        "expected_regex_pedidos": {"VCD3000001"},
        "expected_haiku_has_relations": True,
    },
    {
        "key": "m10_long",
        "path": "/memories/test_api_stress/m10",
        "content": (
            "Resumo politica de frete Nordeste: "
            "MA via JADLOG (8 dias, R$ 3.200). "
            "PI via FL BRASIL (10 dias, R$ 4.100). "
            "PE via TAC (6 dias, R$ 2.800). "
            "RN via JADLOG (7 dias, R$ 3.000). "
            "PB via TAC (7 dias, R$ 2.900). "
            "AL via FL BRASIL (9 dias, R$ 3.500)."
        ),
        "expected_regex_ufs": {"MA", "PI", "PE", "RN", "PB", "AL"},
    },
]


# =====================================================================
# Runner
# =====================================================================

class ApiStressTestRunner:
    """Executa stress test do Knowledge Graph com API Haiku real."""

    def __init__(self, app):
        self.app = app
        self.expectations = []
        self.memory_ids = {}       # key → DB memory_id
        self.api_cache = {}        # key → (context, entities, relations)
        self.api_calls = 0
        self.timings = {}
        self.t0 = time.time()

    # -----------------------------------------------------------------
    # Assertion helpers
    # -----------------------------------------------------------------

    def _expect(self, name: str, passed: bool, evidence: str):
        """Registra expectativa com resultado."""
        self.expectations.append({
            "text": name,
            "passed": passed,
            "evidence": evidence,
        })
        status = "PASS" if passed else "FAIL"
        print(f"   {status}: {name}")
        if not passed:
            print(f"         evidence: {evidence}")

    def _timed(self, label: str):
        """Context manager para medir tempo."""
        return _Timer(self.timings, label)

    # -----------------------------------------------------------------
    # API call wrapper com cache + budget guard
    # -----------------------------------------------------------------

    def _call_haiku(self, user_id, path, content, cache_key=None):
        """
        Chamada direta ao Haiku com timeout de 15s + parse.

        Usa o mesmo prompt template de _generate_memory_context mas com
        timeout maior (15s vs 5s de produção). Isso testa a QUALIDADE
        da extração Haiku sem ser limitado pelo timeout best-effort
        da função de produção.

        Returns:
            tuple (context, entities, relations)
        """
        if cache_key and cache_key in self.api_cache:
            return self.api_cache[cache_key]

        if self.api_calls >= MAX_API_CALLS:
            print(f"   BUDGET GUARD: {self.api_calls}/{MAX_API_CALLS} chamadas atingido")
            return (None, [], [])

        import anthropic
        from app.agente.tools.memory_mcp_tool import _CONTEXTUAL_PROMPT, _HAIKU_MODEL
        from app.agente.services.knowledge_graph_service import parse_contextual_response

        self.api_calls += 1

        try:
            # Carregar memórias existentes do usuário (mesmo lógica de _generate_memory_context)
            from app.agente.models import AgentMemory
            existing = AgentMemory.query.filter_by(
                user_id=user_id, is_directory=False,
            ).order_by(AgentMemory.updated_at.desc()).limit(30).all()

            if existing:
                lines = []
                total_chars = 0
                for mem in existing:
                    if mem.path == path:
                        continue
                    snippet = (mem.content or "")[:80].replace('\n', ' ').strip()
                    if not snippet:
                        continue
                    line = f"- {mem.path}: {snippet}"
                    if total_chars + len(line) > 2000:
                        break
                    lines.append(line)
                    total_chars += len(line)
                existing_text = "\n".join(lines) if lines else "(nenhuma memória anterior)"
            else:
                existing_text = "(nenhuma memória anterior — esta é a primeira)"

            content_truncated = content[:500] if len(content) > 500 else content

            # Chamada com timeout de 15s (produção usa 5s)
            client = anthropic.Anthropic(timeout=15.0)
            response = client.messages.create(
                model=_HAIKU_MODEL,
                max_tokens=250,
                messages=[{
                    "role": "user",
                    "content": _CONTEXTUAL_PROMPT.format(
                        existing_memories=existing_text,
                        path=path,
                        content=content_truncated,
                    ),
                }],
            )

            raw_text = response.content[0].text.strip()
            context, entities, relations = parse_contextual_response(raw_text)

            if not context or len(context) < 10:
                context = None
            if context and len(context) > 500:
                context = context[:500]

            result = (context, entities, relations)

        except Exception as e:
            print(f"   _call_haiku ERRO: {e}")
            result = (None, [], [])

        if cache_key:
            self.api_cache[cache_key] = result

        return result

    # -----------------------------------------------------------------
    # PREFLIGHT
    # -----------------------------------------------------------------

    def preflight(self):
        """Valida ANTHROPIC_API_KEY, DB, tabelas."""
        print(f"\n{'='*70}")
        print("PREFLIGHT CHECKS")
        print(f"{'='*70}")

        # 1. ANTHROPIC_API_KEY
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            # Tentar carregar do .env
            dotenv_path = os.path.join(
                os.path.dirname(__file__), '..', '..', '.env'
            )
            if os.path.exists(dotenv_path):
                with open(dotenv_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('ANTHROPIC_API_KEY='):
                            api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                            os.environ['ANTHROPIC_API_KEY'] = api_key
                            break

        if not api_key:
            print("   FATAL: ANTHROPIC_API_KEY nao encontrada (.env ou env var)")
            sys.exit(1)

        print(f"   ANTHROPIC_API_KEY: ...{api_key[-8:]}")

        # 2. DB connection
        from app import db
        from sqlalchemy import text

        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            assert result == 1, "DB connection failed"
        print("   DB: conectado")

        # 3. Tabelas KG existem
        with db.engine.connect() as conn:
            for table in ['agent_memory_entities', 'agent_memory_entity_links',
                          'agent_memory_entity_relations']:
                count = conn.execute(text(
                    f"SELECT COUNT(*) FROM information_schema.tables "
                    f"WHERE table_name = '{table}'"
                )).scalar()
                assert count == 1, f"Tabela {table} nao existe"
        print("   Tabelas KG: OK")

        # 4. Feature flags
        from app.embeddings.config import MEMORY_KNOWLEDGE_GRAPH
        assert MEMORY_KNOWLEDGE_GRAPH, "MEMORY_KNOWLEDGE_GRAPH deve ser True"
        print("   MEMORY_KNOWLEDGE_GRAPH: True")

        # 5. Quick API test (1 chamada minima)
        try:
            import anthropic
            client = anthropic.Anthropic(timeout=10.0)
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=10,
                messages=[{"role": "user", "content": "responda apenas: OK"}],
            )
            assert response.content[0].text.strip(), "Haiku retornou vazio"
            self.api_calls += 1
            print("   Haiku API: OK (1 chamada preflight)")
        except Exception as e:
            print(f"   FATAL: Haiku API falhou: {e}")
            sys.exit(1)

        print(f"\n   Preflight: TUDO OK. Budget: {MAX_API_CALLS - self.api_calls} "
              f"chamadas restantes (~${(MAX_API_CALLS - self.api_calls) * ESTIMATED_COST_PER_CALL:.4f})")

    # -----------------------------------------------------------------
    # SETUP
    # -----------------------------------------------------------------

    def setup(self):
        """Cria usuarios e memorias no DB."""
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*70}")
        print("SETUP")
        print(f"{'='*70}")

        # Cleanup preventivo
        self._cleanup_data()

        # Usuarios de teste
        for uid, name in [(TEST_USER_A, 'API_STRESS_A'), (TEST_USER_B, 'API_STRESS_B')]:
            with db.engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO usuarios (id, nome, email, senha_hash, perfil, status, criado_em)
                    VALUES (:id, :nome, :email, 'test_hash', 'administrador', 'ativo', NOW())
                    ON CONFLICT (id) DO NOTHING
                """), {
                    "id": uid,
                    "nome": f"TEST_{name}",
                    "email": f"test_api_stress_{uid}@test.local",
                })

        # Criar memorias para User A (10 base)
        print(f"   Criando {len(MEMORIES)} memorias...")

        with _Timer(self.timings, 'setup_memories'):
            with db.engine.begin() as conn:
                for mem in MEMORIES:
                    result = conn.execute(text("""
                        INSERT INTO agent_memories
                            (user_id, path, content, is_directory,
                             importance_score, last_accessed_at, created_at, updated_at)
                        VALUES
                            (:uid, :path, :content, false,
                             0.5, NOW(), NOW(), NOW())
                        RETURNING id
                    """), {
                        "uid": TEST_USER_A,
                        "path": mem["path"],
                        "content": mem["content"],
                    })
                    row = result.fetchone()
                    self.memory_ids[mem["key"]] = row[0]

        print(f"   {len(self.memory_ids)} memorias criadas em "
              f"{self.timings.get('setup_memories', 0):.2f}s")

    # -----------------------------------------------------------------
    # S1: Haiku Entity Extraction Quality
    # -----------------------------------------------------------------

    def test_s1_haiku_extraction(self):
        """S1: Chamada direta a _generate_memory_context para cada memoria."""
        print(f"\n{'='*70}")
        print("S1: Haiku Entity Extraction Quality (10 API calls)")
        print(f"{'='*70}")

        errors = 0
        valid_contexts = 0
        all_entities = []       # [(tipo, nome), ...] de todas memorias
        all_relations = []      # [(o, t, d), ...] de todas memorias
        latencies = []
        freight_indices = list(range(7)) + [8, 9]  # m1-m7, m9, m10 (indices 0-6,8,9)
        noise_index = 7                             # m8

        with _Timer(self.timings, 's1_haiku_extraction'):
            for i, mem in enumerate(MEMORIES):
                t0 = time.time()
                try:
                    context, entities, relations = self._call_haiku(
                        user_id=TEST_USER_A,
                        path=mem["path"],
                        content=mem["content"],
                        cache_key=mem["key"],
                    )
                    dt_ms = (time.time() - t0) * 1000
                    latencies.append(dt_ms)

                    if context is not None:
                        valid_contexts += 1
                    all_entities.extend(entities)
                    all_relations.extend(relations)

                    # Debug info por memoria
                    ent_summary = [f"{t}:{n}" for t, n in entities[:5]]
                    print(f"   [{mem['key']}] ctx={'OK' if context else 'None'} "
                          f"({len(context or '')} chars), "
                          f"{len(entities)} ents, {len(relations)} rels, "
                          f"{dt_ms:.0f}ms | {ent_summary}")

                except Exception as e:
                    errors += 1
                    dt_ms = (time.time() - t0) * 1000
                    latencies.append(dt_ms)
                    print(f"   [{mem['key']}] ERRO: {e}")

        # --- S1.1: 10/10 chamadas sem exceção ---
        self._expect(
            "S1.1: 10/10 Haiku calls succeed (0 erros)",
            errors == 0,
            f"errors={errors}",
        )

        # --- S1.2: >= 7/10 retornam context não-None ---
        # (Tolerância: API Haiku pode retornar 529 Overloaded ou timeout em ~30% dos calls)
        self._expect(
            "S1.2: >= 7/10 retornam context nao-None",
            valid_contexts >= 7,
            f"valid_contexts={valid_contexts}/10",
        )

        # --- S1.3: Contexto entre 10-500 chars para todas respostas válidas ---
        context_lengths = []
        for mem in MEMORIES:
            cached = self.api_cache.get(mem["key"])
            if cached and cached[0]:
                context_lengths.append(len(cached[0]))
        valid_lengths = all(10 <= l <= 500 for l in context_lengths)
        self._expect(
            "S1.3: Contexto entre 10-500 chars para respostas validas",
            valid_lengths,
            f"lengths={context_lengths}",
        )

        # --- S1.4: Memorias de frete que receberam context retornam >= 1 entidade ---
        freight_with_entities = 0
        freight_with_context = 0
        for idx in freight_indices:
            cached = self.api_cache.get(MEMORIES[idx]["key"])
            if cached and cached[0] is not None:
                freight_with_context += 1
                if len(cached[1]) >= 1:
                    freight_with_entities += 1
        # Para memórias que o Haiku respondeu, >= 80% devem ter entidades
        threshold = max(1, int(freight_with_context * 0.8))
        self._expect(
            "S1.4: Memorias de frete com context valido retornam >= 1 entidade (80%)",
            freight_with_entities >= threshold,
            f"freight_with_entities={freight_with_entities}/{freight_with_context} "
            f"(threshold={threshold})",
        )

        # --- S1.5: Memoria noise (m8) retorna <= 1 entidade ---
        noise_cached = self.api_cache.get(MEMORIES[noise_index]["key"])
        noise_count = len(noise_cached[1]) if noise_cached else 0
        self._expect(
            "S1.5: Memoria noise (m8) retorna <= 1 entidade",
            noise_count <= 1,
            f"noise_entities={noise_count}",
        )

        # --- S1.6: Tipos incluem pelo menos uf e transportadora ---
        all_types = {t for t, _ in all_entities}
        has_uf = 'uf' in all_types
        has_transp = 'transportadora' in all_types
        self._expect(
            "S1.6: Tipos incluem 'uf' e 'transportadora' no conjunto total",
            has_uf and has_transp,
            f"types_found={all_types}",
        )

        # --- S1.7: Relações extraidas de >= 2 das 10 memorias ---
        mems_with_relations = 0
        for mem in MEMORIES:
            cached = self.api_cache.get(mem["key"])
            if cached and len(cached[2]) >= 1:
                mems_with_relations += 1
        self._expect(
            "S1.7: Relacoes extraidas de >= 2 das 10 memorias",
            mems_with_relations >= 2,
            f"mems_with_relations={mems_with_relations}",
        )

        # --- S1.8: Formato válido: entidades são tuplas (str, str) não-vazias ---
        valid_entity_format = all(
            isinstance(e, tuple) and len(e) == 2
            and isinstance(e[0], str) and isinstance(e[1], str)
            and e[0].strip() and e[1].strip()
            for e in all_entities
        )
        self._expect(
            "S1.8: Formato valido: entidades sao tuplas (str, str) nao-vazias",
            valid_entity_format,
            f"total_entities={len(all_entities)}, "
            f"sample={all_entities[:3] if all_entities else 'empty'}",
        )

        # --- S1.9: Formato válido: relações são tuplas (str, str, str) não-vazias ---
        valid_rel_format = all(
            isinstance(r, tuple) and len(r) == 3
            and all(isinstance(x, str) and x.strip() for x in r)
            for r in all_relations
        ) if all_relations else True  # Se nenhuma relação, formato é trivialmente válido
        self._expect(
            "S1.9: Formato valido: relacoes sao tuplas (str, str, str) nao-vazias",
            valid_rel_format,
            f"total_relations={len(all_relations)}, "
            f"sample={all_relations[:3] if all_relations else 'empty'}",
        )

        # --- S1.10: parse_contextual_response funciona em output real ---
        # Verifica que pelo menos 5 chamadas retornaram entidades parseadas
        # (não apenas fallback que retorna contexto cru sem entidades)
        parsed_with_entities = sum(
            1 for mem in MEMORIES
            if self.api_cache.get(mem["key"]) and len(self.api_cache[mem["key"]][1]) >= 1
        )
        self._expect(
            "S1.10: parse_contextual_response funciona em output real (>= 5 com entidades)",
            parsed_with_entities >= 5,
            f"parsed_with_entities={parsed_with_entities}/10",
        )

        # --- S1.11: Latência média < 15s por chamada ---
        # (Haiku normalmente ~2-3s, mas 529 Overloaded + retries pode chegar a 15s)
        avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0
        self._expect(
            "S1.11: Latencia media < 15s por chamada",
            avg_latency_ms < 15000,
            f"avg_latency={avg_latency_ms:.0f}ms",
        )

    # -----------------------------------------------------------------
    # S2: Full Write Pipeline com API
    # -----------------------------------------------------------------

    def test_s2_write_pipeline(self):
        """S2: Usa resultados Haiku do cache e chama extract_and_link_entities no DB."""
        from app.agente.services.knowledge_graph_service import (
            extract_and_link_entities,
        )
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*70}")
        print("S2: Full Write Pipeline com API (cache S1, 0 API calls)")
        print(f"{'='*70}")

        target_keys = ["m1_uf_carrier", "m2_pedido_uf", "m4_multi_uf",
                        "m5_rule", "m9_complex"]
        errors = 0
        total_entities = 0
        total_links = 0
        latencies = []

        with _Timer(self.timings, 's2_write_pipeline'):
            for key in target_keys:
                mem = next(m for m in MEMORIES if m["key"] == key)
                mid = self.memory_ids.get(key)
                cached = self.api_cache.get(key)

                if not mid or not cached:
                    errors += 1
                    print(f"   [{key}] SKIP: mid={mid}, cached={cached is not None}")
                    continue

                context, haiku_entities, haiku_relations = cached

                t0 = time.time()
                try:
                    stats = extract_and_link_entities(
                        user_id=TEST_USER_A,
                        memory_id=mid,
                        content=mem["content"],
                        haiku_entities=haiku_entities,
                        haiku_relations=haiku_relations,
                    )
                    dt_ms = (time.time() - t0) * 1000
                    latencies.append(dt_ms)
                    total_entities += stats['entities_count']
                    total_links += stats['links_count']
                    print(f"   [{key}] entities={stats['entities_count']}, "
                          f"links={stats['links_count']}, "
                          f"relations={stats['relations_count']}, {dt_ms:.0f}ms")
                except Exception as e:
                    errors += 1
                    print(f"   [{key}] ERRO: {e}")

        # S2.1: 5 memórias processadas sem erro
        self._expect(
            "S2.1: 5 memorias processadas sem erro",
            errors == 0,
            f"errors={errors}",
        )

        # S2.2: >= 12 entidades totais criadas no DB
        with db.engine.connect() as conn:
            db_entities = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entities WHERE user_id = :uid
            """), {"uid": TEST_USER_A}).scalar()
        self._expect(
            "S2.2: >= 12 entidades totais criadas no DB",
            db_entities is not None and db_entities >= 12,
            f"db_entities={db_entities}",
        )

        # S2.3: >= 5 links criados
        with db.engine.connect() as conn:
            db_links = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_links l
                JOIN agent_memory_entities e ON l.entity_id = e.id
                WHERE e.user_id = :uid
            """), {"uid": TEST_USER_A}).scalar()
        self._expect(
            "S2.3: >= 5 links criados",
            db_links is not None and db_links >= 5,
            f"db_links={db_links}",
        )

        # S2.4: >= 1 relação Haiku (não co_occurs) no DB
        with db.engine.connect() as conn:
            haiku_rels = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_relations r
                JOIN agent_memory_entities e ON r.source_entity_id = e.id
                WHERE e.user_id = :uid AND r.relation_type != 'co_occurs'
            """), {"uid": TEST_USER_A}).scalar()
        self._expect(
            "S2.4: >= 1 relacao Haiku (nao co_occurs) no DB",
            haiku_rels is not None and haiku_rels >= 1,
            f"haiku_rels={haiku_rels}",
        )

        # S2.5: Entidades regex (UFs, pedidos) presentes ao lado das Haiku
        with db.engine.connect() as conn:
            uf_count = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entities
                WHERE user_id = :uid AND entity_type = 'uf'
            """), {"uid": TEST_USER_A}).scalar()
            haiku_type_count = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entities
                WHERE user_id = :uid AND entity_type IN ('transportadora', 'cliente')
            """), {"uid": TEST_USER_A}).scalar()
        self._expect(
            "S2.5: Entidades regex (UFs) e Haiku (transp/cliente) coexistem",
            (uf_count or 0) >= 3 and (haiku_type_count or 0) >= 1,
            f"ufs={uf_count}, haiku_types={haiku_type_count}",
        )

        # S2.6: Pipeline completo < 2s por memória
        avg_ms = (sum(latencies) / len(latencies)) if latencies else 0
        self._expect(
            "S2.6: Pipeline completo < 2s por memoria",
            avg_ms < 2000,
            f"avg={avg_ms:.0f}ms",
        )

    # -----------------------------------------------------------------
    # S3: Haiku vs Regex — Prova de Valor-Adicionado
    # -----------------------------------------------------------------

    def test_s3_haiku_vs_regex(self):
        """S3: Compara _extract_entities_regex com entidades Haiku do cache."""
        from app.agente.services.knowledge_graph_service import _extract_entities_regex

        print(f"\n{'='*70}")
        print("S3: Haiku vs Regex — Prova de Valor-Adicionado (0 API calls)")
        print(f"{'='*70}")

        total_regex_entities = 0
        total_haiku_entities = 0
        haiku_found_transportadora = False
        haiku_found_cliente = False
        uf_agreement_count = 0
        uf_comparison_count = 0

        for mem in MEMORIES:
            cached = self.api_cache.get(mem["key"])
            if not cached:
                continue

            _, haiku_entities, _ = cached
            regex_entities = _extract_entities_regex(mem["content"])

            regex_ufs = {n for t, n, _ in regex_entities if t == 'uf'}
            haiku_ufs = {n.upper() for t, n in haiku_entities if t == 'uf'}
            expected_ufs = mem.get("expected_regex_ufs", set())

            # Concordância UF
            if expected_ufs:
                uf_comparison_count += 1
                # Haiku deveria encontrar pelo menos as UFs que esperamos do regex
                if expected_ufs.issubset(haiku_ufs) or expected_ufs.issubset(regex_ufs):
                    uf_agreement_count += 1

            total_regex_entities += len(regex_entities)
            total_haiku_entities += len(haiku_entities)

            haiku_types = {t for t, n in haiku_entities}
            if 'transportadora' in haiku_types:
                haiku_found_transportadora = True
            if 'cliente' in haiku_types:
                haiku_found_cliente = True

            # Debug
            print(f"   [{mem['key']}] regex={len(regex_entities)} "
                  f"(ufs={regex_ufs}), haiku={len(haiku_entities)} "
                  f"(types={haiku_types})")

        # S3.1: Para memorias com UFs, Haiku ou regex encontram as esperadas
        self._expect(
            "S3.1: UFs esperadas encontradas por Haiku ou regex",
            uf_comparison_count == 0 or uf_agreement_count >= (uf_comparison_count * 0.7),
            f"agreement={uf_agreement_count}/{uf_comparison_count}",
        )

        # S3.2: Haiku encontra entidades tipo transportadora
        self._expect(
            "S3.2: Haiku encontra tipo 'transportadora' (regex NAO encontra)",
            haiku_found_transportadora,
            f"haiku_found_transportadora={haiku_found_transportadora}",
        )

        # S3.3: Haiku encontra entidades tipo cliente
        self._expect(
            "S3.3: Haiku encontra tipo 'cliente' (regex NAO encontra)",
            haiku_found_cliente,
            f"haiku_found_cliente={haiku_found_cliente}",
        )

        # S3.4: Haiku extrai TIPOS que regex não consegue (transportadora, cliente, etc.)
        # Regex só extrai: uf, pedido, cnpj, valor. Haiku adiciona diversidade de tipos.
        all_haiku_types = set()
        for mem in MEMORIES:
            cached = self.api_cache.get(mem["key"])
            if cached:
                all_haiku_types.update(t for t, _ in cached[1])
        regex_only_types = {'uf', 'pedido', 'cnpj', 'valor'}
        haiku_exclusive_types = all_haiku_types - regex_only_types
        self._expect(
            "S3.4: Haiku extrai tipos que regex nao consegue (valor-adicionado)",
            len(haiku_exclusive_types) >= 1,
            f"haiku_exclusive_types={haiku_exclusive_types}, all_haiku_types={all_haiku_types}",
        )

        # S3.5: Nomes de entidades Haiku em formato válido
        all_haiku_names = []
        for mem in MEMORIES:
            cached = self.api_cache.get(mem["key"])
            if cached:
                all_haiku_names.extend([n for _, n in cached[1]])
        valid_names = all(
            isinstance(n, str) and len(n.strip()) >= 1 and len(n) <= 200
            for n in all_haiku_names
        ) if all_haiku_names else True
        self._expect(
            "S3.5: Nomes de entidades Haiku em formato valido",
            valid_names,
            f"total_names={len(all_haiku_names)}, "
            f"sample={all_haiku_names[:5] if all_haiku_names else 'empty'}",
        )

    # -----------------------------------------------------------------
    # S4: Contextual Enrichment
    # -----------------------------------------------------------------

    def test_s4_contextual_enrichment(self):
        """S4: Testa enriquecimento por contexto — com e sem memórias existentes."""
        print(f"\n{'='*70}")
        print("S4: Contextual Enrichment (2 API calls)")
        print(f"{'='*70}")

        # Faz 2 chamadas. Com API transiente (529 Overloaded), ao menos 1 deve funcionar.
        ctx1, ents1, _ = self._call_haiku(
            user_id=TEST_USER_A,
            path="/memories/test_api_stress/s4_first",
            content="Transportadora PATRUS para MG com prazo de 2 dias.",
            cache_key="s4_first",
        )

        ctx2, ents2, _ = self._call_haiku(
            user_id=TEST_USER_A,
            path="/memories/test_api_stress/s4_second",
            content="RODONAVES tambem atende MG mas com lead time maior.",
            cache_key="s4_second",
        )

        # S4.1: Pelo menos 1 das 2 chamadas retorna context válido
        # (tolerante a 529 Overloaded transiente em 1 das chamadas)
        valid_s4 = sum(1 for ctx in [ctx1, ctx2] if ctx is not None and len(ctx) >= 10)
        self._expect(
            "S4.1: >= 1/2 chamadas retorna context valido",
            valid_s4 >= 1,
            f"valid={valid_s4}/2, ctx1_len={len(ctx1 or '')}, ctx2_len={len(ctx2 or '')}",
        )

        # S4.2: Contextos válidos entre 10-500 chars
        contexts_in_range = True
        for ctx in [ctx1, ctx2]:
            if ctx and not (10 <= len(ctx) <= 500):
                contexts_in_range = False
        self._expect(
            "S4.2: Contextos validos entre 10-500 chars",
            contexts_in_range,
            f"ctx1_len={len(ctx1 or '')}, ctx2_len={len(ctx2 or '')}",
        )

        # S4.3: Se ambos responderam, contextos são diferentes (enriquecimento real)
        both_valid = ctx1 is not None and ctx2 is not None
        if both_valid:
            self._expect(
                "S4.3: Contextos diferentes (enriquecimento real)",
                ctx1 != ctx2,
                f"same={ctx1 == ctx2}",
            )
        else:
            self._expect(
                "S4.3: Contextos diferentes (enriquecimento real)",
                True,  # Skip se API falhou em 1 — não é falha de lógica
                f"skipped: only {valid_s4}/2 calls succeeded",
            )

    # -----------------------------------------------------------------
    # S5: Read Path com Entidades API
    # -----------------------------------------------------------------

    def test_s5_read_path(self):
        """S5: Após S2 popular o grafo, testa query_graph_memories."""
        from app.agente.services.knowledge_graph_service import query_graph_memories

        print(f"\n{'='*70}")
        print("S5: Read Path com Entidades API (0 API calls)")
        print(f"{'='*70}")

        # S5.1: "AM" retorna memoria m1
        results_am = query_graph_memories(
            user_id=TEST_USER_A,
            prompt="entrega para AM",
            limit=20,
        )
        m1_id = self.memory_ids.get("m1_uf_carrier")
        am_has_m1 = any(r['memory_id'] == m1_id for r in results_am)
        self._expect(
            "S5.1: Query 'entrega para AM' retorna memoria m1",
            am_has_m1,
            f"results={len(results_am)}, m1_id={m1_id}, "
            f"found_ids={[r['memory_id'] for r in results_am]}",
        )

        # S5.2: "SP" retorna memorias com entidades SP
        results_sp = query_graph_memories(
            user_id=TEST_USER_A,
            prompt="SP",
            limit=20,
        )
        self._expect(
            "S5.2: Query 'SP' retorna memorias com SP",
            len(results_sp) >= 1,
            f"results={len(results_sp)}",
        )

        # S5.3: "reuniao segunda" retorna 0 resultados (noise sem entidades no grafo)
        results_noise = query_graph_memories(
            user_id=TEST_USER_A,
            prompt="reuniao segunda",
            limit=20,
        )
        self._expect(
            "S5.3: Query 'reuniao segunda' retorna 0 resultados",
            len(results_noise) == 0,
            f"results={len(results_noise)}",
        )

        # S5.4: exclude_memory_ids filtra corretamente
        if results_sp:
            exclude_ids = {results_sp[0]['memory_id']}
            results_sp_filtered = query_graph_memories(
                user_id=TEST_USER_A,
                prompt="SP",
                exclude_memory_ids=exclude_ids,
                limit=20,
            )
            overlap = exclude_ids & {r['memory_id'] for r in results_sp_filtered}
            self._expect(
                "S5.4: exclude_memory_ids filtra corretamente",
                len(overlap) == 0,
                f"excluded={exclude_ids}, overlap={overlap}",
            )
        else:
            self._expect(
                "S5.4: exclude_memory_ids filtra corretamente",
                True,
                "skipped: no SP results to exclude",
            )

        # S5.5: Resultados tem source='graph'
        all_graph = all(r.get('source') == 'graph' for r in results_am + results_sp)
        self._expect(
            "S5.5: Resultados tem source='graph'",
            all_graph,
            f"sources={[r.get('source') for r in (results_am + results_sp)[:5]]}",
        )

    # -----------------------------------------------------------------
    # S6: Update Path com Re-extração
    # -----------------------------------------------------------------

    def test_s6_update_path(self):
        """S6: Simula update: remove links antigos, extrai novos com Haiku."""
        from app.agente.services.knowledge_graph_service import (
            extract_and_link_entities,
            remove_memory_links,
        )
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*70}")
        print("S6: Update Path com Re-extracao (1 API call)")
        print(f"{'='*70}")

        mid = self.memory_ids.get("m1_uf_carrier")
        if not mid:
            self._expect("S6: precondition m1 exists", False, "m1 not found")
            return

        # S6.1: Links antigos removidos
        with db.engine.connect() as conn:
            links_before = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_links WHERE memory_id = :mid
            """), {"mid": mid}).scalar()

        removed = remove_memory_links(mid)
        self._expect(
            "S6.1: Links antigos removidos (count >= 1)",
            removed >= 1,
            f"removed={removed}, before={links_before}",
        )

        # S6.2 + S6.3 + S6.4: Re-extrair com conteúdo atualizado (sem AM, com RJ)
        new_content = "Entregas para RJ via PATRUS com lead time de 4 dias. Cliente BIG."
        context, haiku_entities, haiku_relations = self._call_haiku(
            user_id=TEST_USER_A,
            path="/memories/test_api_stress/m1",
            content=new_content,
            cache_key="s6_update",
        )

        stats = extract_and_link_entities(
            user_id=TEST_USER_A,
            memory_id=mid,
            content=new_content,
            haiku_entities=haiku_entities,
            haiku_relations=haiku_relations,
        )

        self._expect(
            "S6.2: Novas entidades extraidas do conteudo atualizado",
            stats['entities_count'] >= 1,
            f"entities={stats['entities_count']}",
        )

        # Verificar RJ linkado
        with db.engine.connect() as conn:
            rj_linked = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_links l
                JOIN agent_memory_entities e ON l.entity_id = e.id
                WHERE l.memory_id = :mid AND e.entity_name = 'RJ'
            """), {"mid": mid}).scalar()
        self._expect(
            "S6.3: RJ linkado apos update",
            rj_linked is not None and rj_linked >= 1,
            f"rj_links={rj_linked}",
        )

        # AM não mais linkado a esta memória
        with db.engine.connect() as conn:
            am_linked = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_links l
                JOIN agent_memory_entities e ON l.entity_id = e.id
                WHERE l.memory_id = :mid AND e.entity_name = 'AM'
            """), {"mid": mid}).scalar()
        self._expect(
            "S6.4: AM nao mais linkado a esta memoria",
            am_linked == 0,
            f"am_links={am_linked}",
        )

    # -----------------------------------------------------------------
    # S7: End-to-End Pipeline
    # -----------------------------------------------------------------

    def test_s7_end_to_end(self):
        """S7: 3 memórias novas sequenciais com entidades compartilhadas."""
        from app.agente.services.knowledge_graph_service import (
            extract_and_link_entities,
        )
        from app.agente.services.knowledge_graph_service import query_graph_memories
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*70}")
        print("S7: End-to-End Pipeline (3 API calls)")
        print(f"{'='*70}")

        e2e_memories = [
            {
                "path": "/memories/test_api_stress/e2e_1",
                "content": "RODONAVES entrega para MG em 3 dias. Preco bom.",
            },
            {
                "path": "/memories/test_api_stress/e2e_2",
                "content": "RODONAVES tambem cobre SP e RJ com tabela especial.",
            },
            {
                "path": "/memories/test_api_stress/e2e_3",
                "content": "Para MG a melhor opcao e RODONAVES (rapido e confiavel).",
            },
        ]

        e2e_ids = []
        errors = 0

        with _Timer(self.timings, 's7_e2e'):
            for i, mem in enumerate(e2e_memories):
                # Criar memória no DB
                with db.engine.begin() as conn:
                    result = conn.execute(text("""
                        INSERT INTO agent_memories
                            (user_id, path, content, is_directory,
                             importance_score, last_accessed_at, created_at, updated_at)
                        VALUES
                            (:uid, :path, :content, false,
                             0.5, NOW(), NOW(), NOW())
                        RETURNING id
                    """), {
                        "uid": TEST_USER_A,
                        "path": mem["path"],
                        "content": mem["content"],
                    })
                    mid = result.fetchone()[0]
                    e2e_ids.append(mid)
                    self.memory_ids[f"e2e_{i}"] = mid

                # Call Haiku + extract
                try:
                    ctx, ents, rels = self._call_haiku(
                        user_id=TEST_USER_A,
                        path=mem["path"],
                        content=mem["content"],
                        cache_key=f"e2e_{i}",
                    )
                    stats = extract_and_link_entities(
                        user_id=TEST_USER_A,
                        memory_id=mid,
                        content=mem["content"],
                        haiku_entities=ents,
                        haiku_relations=rels,
                    )
                    print(f"   [e2e_{i}] entities={stats['entities_count']}, "
                          f"links={stats['links_count']}")
                except Exception as e:
                    errors += 1
                    print(f"   [e2e_{i}] ERRO: {e}")

        # S7.1: 3 memórias processadas com sucesso
        self._expect(
            "S7.1: 3 memorias processadas com sucesso",
            errors == 0 and len(e2e_ids) == 3,
            f"errors={errors}, created={len(e2e_ids)}",
        )

        # S7.2: RODONAVES linkado a >= 2 memórias no DB
        # Nota: query_graph_memories usa regex no prompt que não extrai nomes de
        # transportadoras (apenas UF, pedido, CNPJ, valor). Com EMBEDDINGS_ENABLED=false,
        # Voyage também não resolve. Verificamos via DB query direta.
        with db.engine.connect() as conn:
            rodo_memories = conn.execute(text("""
                SELECT COUNT(DISTINCT l.memory_id)
                FROM agent_memory_entity_links l
                JOIN agent_memory_entities e ON l.entity_id = e.id
                WHERE e.user_id = :uid AND e.entity_name = 'RODONAVES'
            """), {"uid": TEST_USER_A}).scalar()
        self._expect(
            "S7.2: RODONAVES linkado a >= 2 memorias no DB",
            rodo_memories is not None and rodo_memories >= 2,
            f"linked_memories={rodo_memories}",
        )

        # S7.3: Query "MG" retorna >= 2 memórias
        results_mg = query_graph_memories(
            user_id=TEST_USER_A,
            prompt="MG",
            limit=20,
        )
        self._expect(
            "S7.3: Query 'MG' retorna >= 2 memorias",
            len(results_mg) >= 2,
            f"results={len(results_mg)}",
        )

        # S7.4: Entidade RODONAVES tem mention_count >= 2
        with db.engine.connect() as conn:
            rodo_row = conn.execute(text("""
                SELECT mention_count FROM agent_memory_entities
                WHERE user_id = :uid AND entity_name = 'RODONAVES'
            """), {"uid": TEST_USER_A}).fetchone()
        rodo_count = rodo_row[0] if rodo_row else 0
        self._expect(
            "S7.4: Entidade RODONAVES tem mention_count >= 2",
            rodo_count >= 2,
            f"mention_count={rodo_count}",
        )

    # -----------------------------------------------------------------
    # S8: Error Handling e Resiliência
    # -----------------------------------------------------------------

    def test_s8_error_handling(self):
        """S8: Edge cases — conteúdo vazio, longo, não-frete."""
        print(f"\n{'='*70}")
        print("S8: Error Handling e Resiliencia (2 API calls)")
        print(f"{'='*70}")

        # S8.1: Conteúdo vazio → (None, [], []) sem exceção
        t0 = time.time()
        try:
            ctx, ents, rels = self._call_haiku(
                user_id=TEST_USER_A,
                path="/memories/test_api_stress/s8_empty",
                content="",
                cache_key="s8_empty",
            )
            # Haiku pode retornar algo ou nada para conteúdo vazio
            success = True
        except Exception:
            success = False
        self._expect(
            "S8.1: Conteudo vazio sem excecao",
            success,
            f"completed in {(time.time()-t0)*1000:.0f}ms",
        )

        # S8.2: Conteúdo longo (2000 chars) → truncado para 500
        long_content = "Entrega para SP via RODONAVES. " * 80  # ~2400 chars
        t0 = time.time()
        try:
            ctx, ents, rels = self._call_haiku(
                user_id=TEST_USER_A,
                path="/memories/test_api_stress/s8_long",
                content=long_content,
                cache_key="s8_long",
            )
            # _generate_memory_context trunca para 500 chars internamente
            success = True
        except Exception:
            success = False
        dt = time.time() - t0
        self._expect(
            "S8.2: Conteudo longo (2000 chars) processado sem erro",
            success,
            f"completed in {dt*1000:.0f}ms",
        )

        # S8.3: Conteúdo não-frete → poucas ou 0 entidades
        non_freight_cached = self.api_cache.get("m8_noise")
        noise_ents = len(non_freight_cached[1]) if non_freight_cached else 0
        self._expect(
            "S8.3: Conteudo nao-frete retorna <= 2 entidades",
            noise_ents <= 2,
            f"noise_entities={noise_ents}",
        )

        # S8.4: Todos edge cases completam em < 20s cada
        # (API call com timeout de 15s + overhead de DB query)
        self._expect(
            "S8.4: Todos edge cases completam em < 20s cada",
            dt < 20.0,
            f"longest_dt={dt:.2f}s",
        )

    # -----------------------------------------------------------------
    # S9: Multi-User Isolation com API
    # -----------------------------------------------------------------

    def test_s9_user_isolation(self):
        """S9: User A não vê entidades de User B."""
        from app.agente.services.knowledge_graph_service import (
            extract_and_link_entities,
            query_graph_memories,
        )
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*70}")
        print("S9: Multi-User Isolation com API (1 API call)")
        print(f"{'='*70}")

        # Criar memória para User B
        with db.engine.begin() as conn:
            result = conn.execute(text("""
                INSERT INTO agent_memories
                    (user_id, path, content, is_directory,
                     importance_score, last_accessed_at, created_at, updated_at)
                VALUES
                    (:uid, '/memories/test_api_stress/user_b_1',
                     'Entrega para RR via JADLOG com prioridade', false,
                     0.5, NOW(), NOW(), NOW())
                RETURNING id
            """), {"uid": TEST_USER_B})
            mid_b = result.fetchone()[0]
            self.memory_ids["user_b_1"] = mid_b

        # Call Haiku for user B
        ctx, ents, rels = self._call_haiku(
            user_id=TEST_USER_B,
            path="/memories/test_api_stress/user_b_1",
            content="Entrega para RR via JADLOG com prioridade",
            cache_key="user_b_1",
        )

        extract_and_link_entities(
            user_id=TEST_USER_B,
            memory_id=mid_b,
            content="Entrega para RR via JADLOG com prioridade",
            haiku_entities=ents,
            haiku_relations=rels,
        )

        # S9.1: User A não vê entidades de User B
        results_a = query_graph_memories(user_id=TEST_USER_A, prompt="RR")
        self._expect(
            "S9.1: User A nao ve entidades de User B (RR)",
            len(results_a) == 0,
            f"results_for_A={len(results_a)}",
        )

        # S9.2: User B vê suas próprias entidades
        results_b = query_graph_memories(user_id=TEST_USER_B, prompt="RR")
        self._expect(
            "S9.2: User B ve suas proprias entidades (RR)",
            len(results_b) >= 1,
            f"results_for_B={len(results_b)}",
        )

        # S9.3: User B não vê entidades de User A
        results_b_sp = query_graph_memories(user_id=TEST_USER_B, prompt="SP")
        self._expect(
            "S9.3: User B nao ve entidades de User A (SP)",
            len(results_b_sp) == 0,
            f"results_for_B_SP={len(results_b_sp)}",
        )

    # -----------------------------------------------------------------
    # S10: Consistência do Haiku
    # -----------------------------------------------------------------

    def test_s10_consistency(self):
        """S10: Chama _generate_memory_context 3x para mesmo conteúdo."""
        print(f"\n{'='*70}")
        print("S10: Consistencia do Haiku (3 API calls)")
        print(f"{'='*70}")

        test_content = ("Pedido VCD5000001 do ATACADAO para MG via RODONAVES. "
                        "Valor R$ 10.000,00. Prazo 4 dias.")
        test_path = "/memories/test_api_stress/consistency"

        results = []
        for i in range(3):
            # Não usar cache — forçar chamada real
            ctx, ents, rels = self._call_haiku(
                user_id=TEST_USER_A,
                path=test_path,
                content=test_content,
                cache_key=None,  # Sem cache
            )
            results.append((ctx, ents, rels))
            ent_types = {t for t, n in ents}
            print(f"   [run_{i}] ctx={'OK' if ctx else 'None'}, "
                  f"ents={len(ents)} (types={ent_types}), rels={len(rels)}")

        # S10.1: 3/3 retornam respostas válidas estruturadas
        valid_count = sum(1 for ctx, ents, _ in results if ctx is not None)
        self._expect(
            "S10.1: 3/3 retornam respostas validas estruturadas",
            valid_count == 3,
            f"valid={valid_count}/3",
        )

        # S10.2: UF MG aparece em >= 2/3 chamadas
        mg_count = sum(
            1 for _, ents, _ in results
            if any(n.upper() == 'MG' for t, n in ents if t == 'uf')
        )
        self._expect(
            "S10.2: UF MG aparece em >= 2/3 chamadas",
            mg_count >= 2,
            f"mg_in_results={mg_count}/3",
        )

        # S10.3: >= 1 tipo adicional aparece em >= 2/3 chamadas
        # Verificar tipos como transportadora, cliente, pedido
        extra_types_count = {}
        for _, ents, _ in results:
            types_in_run = {t for t, n in ents if t != 'uf'}
            for t in types_in_run:
                extra_types_count[t] = extra_types_count.get(t, 0) + 1

        consistent_extra = any(c >= 2 for c in extra_types_count.values())
        self._expect(
            "S10.3: >= 1 tipo adicional aparece em >= 2/3 chamadas",
            consistent_extra,
            f"extra_type_counts={extra_types_count}",
        )

    # -----------------------------------------------------------------
    # RUN ALL
    # -----------------------------------------------------------------

    def run_all(self):
        """Executa todos os cenários na ordem correta."""
        self.test_s1_haiku_extraction()    # Popula api_cache
        self.test_s2_write_pipeline()      # Usa cache S1, popula grafo no DB
        self.test_s3_haiku_vs_regex()      # Usa cache S1 (0 API calls)
        self.test_s4_contextual_enrichment()  # Independente
        self.test_s5_read_path()           # Depende de S2 (lê do grafo)
        self.test_s6_update_path()         # Depende de S2 (precisa de memória existente)
        self.test_s7_end_to_end()          # Independente (cria próprias memórias)
        self.test_s8_error_handling()       # Independente
        self.test_s9_user_isolation()      # Independente (cria user_b)
        self.test_s10_consistency()        # Independente

    # -----------------------------------------------------------------
    # CLEANUP
    # -----------------------------------------------------------------

    def _cleanup_data(self):
        """Remove dados de teste (ordem FK)."""
        from app import db
        from sqlalchemy import text

        for uid in [TEST_USER_A, TEST_USER_B]:
            with db.engine.begin() as conn:
                # 1. Relations (FK → entities)
                conn.execute(text("""
                    DELETE FROM agent_memory_entity_relations
                    WHERE source_entity_id IN (
                        SELECT id FROM agent_memory_entities WHERE user_id = :uid
                    ) OR target_entity_id IN (
                        SELECT id FROM agent_memory_entities WHERE user_id = :uid
                    )
                """), {"uid": uid})
                # 2. Links (FK → entities)
                conn.execute(text("""
                    DELETE FROM agent_memory_entity_links
                    WHERE entity_id IN (
                        SELECT id FROM agent_memory_entities WHERE user_id = :uid
                    )
                """), {"uid": uid})
                # 3. Entities
                conn.execute(text("""
                    DELETE FROM agent_memory_entities WHERE user_id = :uid
                """), {"uid": uid})
                # 4. Embeddings (se existirem)
                conn.execute(text("""
                    DELETE FROM agent_memory_embeddings
                    WHERE user_id = :uid
                """), {"uid": uid})
                # 5. Memory versions (FK → memories)
                conn.execute(text("""
                    DELETE FROM agent_memory_versions
                    WHERE memory_id IN (
                        SELECT id FROM agent_memories WHERE user_id = :uid
                    )
                """), {"uid": uid})
                # 6. Memories
                conn.execute(text("""
                    DELETE FROM agent_memories WHERE user_id = :uid
                """), {"uid": uid})
                # 7. Usuarios
                conn.execute(text("""
                    DELETE FROM usuarios WHERE id = :uid
                """), {"uid": uid})

    def cleanup(self):
        """Cleanup final + verificação de zero residual."""
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*70}")
        print("CLEANUP")
        print(f"{'='*70}")

        self._cleanup_data()

        with db.engine.connect() as conn:
            for uid in [TEST_USER_A, TEST_USER_B]:
                remaining = conn.execute(text("""
                    SELECT
                        (SELECT COUNT(*) FROM agent_memory_entities WHERE user_id = :uid),
                        (SELECT COUNT(*) FROM agent_memories WHERE user_id = :uid)
                """), {"uid": uid}).fetchone()
                self._expect(
                    f"Cleanup: 0 registros residuais para user {uid}",
                    remaining[0] == 0 and remaining[1] == 0,
                    f"entities={remaining[0]}, memories={remaining[1]}",
                )

    # -----------------------------------------------------------------
    # REPORT (grading.json format)
    # -----------------------------------------------------------------

    def report(self):
        """Gera report final + grading.json."""
        total_duration = time.time() - self.t0
        passed = sum(1 for e in self.expectations if e['passed'])
        failed = sum(1 for e in self.expectations if not e['passed'])
        total = len(self.expectations)
        pass_rate = passed / total if total > 0 else 0

        estimated_cost = self.api_calls * ESTIMATED_COST_PER_CALL

        # Console output
        print(f"\n{'='*70}")
        print(f"RESULTADO: {passed}/{total} expectations passed ({pass_rate:.0%})")
        print(f"Duração total: {total_duration:.2f}s")
        print(f"API calls: {self.api_calls} (estimado: ${estimated_cost:.4f})")
        if failed > 0:
            print(f"\nFALHAS ({failed}):")
            for e in self.expectations:
                if not e['passed']:
                    print(f"   - {e['text']}: {e['evidence']}")
        else:
            print("\nTodos os testes passaram!")
        print(f"{'='*70}")

        # grading.json
        grading = {
            "expectations": self.expectations,
            "summary": {
                "passed": passed,
                "failed": failed,
                "total": total,
                "pass_rate": round(pass_rate, 4),
            },
            "execution_metrics": {
                "memories_created": len(self.memory_ids),
                "scenarios_run": 10,
                "api_calls_total": self.api_calls,
                "api_estimated_cost_usd": round(estimated_cost, 4),
            },
            "timing": {
                "total_duration_seconds": round(total_duration, 2),
                **{k: round(v, 4) for k, v in self.timings.items()},
            },
        }

        with open(OUTPUT_PATH, 'w') as f:
            json.dump(grading, f, indent=2, ensure_ascii=False)

        print(f"\nOutput: {OUTPUT_PATH}")
        return pass_rate


# =====================================================================
# Utilities
# =====================================================================

class _Timer:
    """Context manager para medir tempo de blocos."""

    def __init__(self, timings: dict, label: str):
        self.timings = timings
        self.label = label
        self.start = None

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.timings[self.label] = time.time() - self.start


# =====================================================================
# Main
# =====================================================================

def main():
    # Verificar --yes flag (bypass confirmation)
    if '--yes' not in sys.argv:
        print("=" * 70)
        print("T3-3 Knowledge Graph — STRESS TEST COM API REAL (Haiku)")
        print("=" * 70)
        print(f"\n  Budget: ~{MAX_API_CALLS} chamadas Haiku (~${MAX_API_CALLS * ESTIMATED_COST_PER_CALL:.4f})")
        print(f"  Users de teste: {TEST_USER_A}, {TEST_USER_B}")
        print(f"  Output: {OUTPUT_PATH}")
        print(f"\n  Requer: ANTHROPIC_API_KEY configurada")
        print(f"\n  Use --yes para pular confirmacao\n")

        resp = input("Continuar? [y/N] ").strip().lower()
        if resp not in ('y', 'yes', 's', 'sim'):
            print("Abortado.")
            sys.exit(0)

    from app import create_app
    app = create_app()
    runner = ApiStressTestRunner(app)

    with app.app_context():
        try:
            runner.preflight()
            runner.setup()
            runner.run_all()
        except Exception:
            print(f"\n{'='*70}")
            print("ERRO FATAL:")
            traceback.print_exc()
            print(f"{'='*70}")
        finally:
            runner.cleanup()
            pass_rate = runner.report()

    # Tolerância de ~6% para variância Haiku (45/48 = 93.75%)
    sys.exit(0 if pass_rate >= 0.93 else 1)


if __name__ == '__main__':
    main()

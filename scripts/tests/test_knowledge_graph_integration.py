#!/usr/bin/env python
"""
Integration Test — Knowledge Graph (T3-3)

Script standalone que testa o pipeline completo do Knowledge Graph:
  Write Path: extract_and_link_entities (regex + haiku)
  Read Path: query_graph_memories
  Delete Path: remove_memory_links + cleanup_orphan_entities
  Stats: get_graph_stats
  Isolamento de usuario + Idempotencia

Execucao:
    source .venv/bin/activate
    python scripts/tests/test_knowledge_graph_integration.py

Seguranca:
    - Usa TEST_USER_ID = 99999 (nao existe em producao)
    - Cleanup final remove TUDO com user_id = 99999
    - Cria usuario temporario (removido ao final)
"""

import os
import sys
import traceback

# Setup path para imports do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

TEST_USER_ID = 99999
TEST_USER_ID_2 = 88888  # Para teste de isolamento

# Desabilitar Layer 2 (Voyage) nos testes — sem API key configurada
os.environ.setdefault('EMBEDDINGS_ENABLED', 'false')


def main():
    """Entry point do script de integracao."""
    from app import create_app

    app = create_app()
    runner = IntegrationTestRunner(app)

    with app.app_context():
        try:
            runner.setup()
            runner.run_all_tests()
        except Exception:
            print(f"\n{'='*60}")
            print("ERRO FATAL durante execucao dos testes:")
            traceback.print_exc()
            print(f"{'='*60}")
        finally:
            runner.cleanup()
            runner.report()

    sys.exit(0 if runner.failed == 0 else 1)


class IntegrationTestRunner:
    """Executa testes de integracao do Knowledge Graph."""

    def __init__(self, app):
        self.app = app
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.memory_ids = {}  # key → memory_id mapping

    # =================================================================
    # SETUP
    # =================================================================

    def setup(self):
        """Cria tabelas KG (idempotente), usuario e memorias de teste."""
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*60}")
        print("T3-3 Knowledge Graph — Integration Tests")
        print(f"{'='*60}")

        # 1. Executar migration (idempotente)
        print("\n--- Setup: Migration ---")
        try:
            from scripts.migrations.criar_tabelas_knowledge_graph import migrate
            migrate()
        except Exception as e:
            print(f"   Migration (pode ja existir): {e}")

        # 2. Cleanup preventivo (caso execucao anterior tenha falhado)
        print("\n--- Setup: Cleanup preventivo ---")
        self._cleanup_test_data()

        # 3. Criar usuario temporario
        print("\n--- Setup: Criando usuario de teste ---")
        with db.engine.begin() as conn:
            # Usuario principal de teste
            conn.execute(text("""
                INSERT INTO usuarios (id, nome, email, senha_hash, perfil, status, criado_em)
                VALUES (:id, :nome, :email, :hash, 'administrador', 'ativo', NOW())
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": TEST_USER_ID,
                "nome": "TEST_KG_USER",
                "email": f"test_kg_{TEST_USER_ID}@test.local",
                "hash": "not_a_real_hash_test_only",
            })

            # Usuario 2 para teste de isolamento
            conn.execute(text("""
                INSERT INTO usuarios (id, nome, email, senha_hash, perfil, status, criado_em)
                VALUES (:id, :nome, :email, :hash, 'administrador', 'ativo', NOW())
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": TEST_USER_ID_2,
                "nome": "TEST_KG_ISOLATION",
                "email": f"test_kg_{TEST_USER_ID_2}@test.local",
                "hash": "not_a_real_hash_test_only",
            })

        print(f"   Usuarios {TEST_USER_ID} e {TEST_USER_ID_2}: OK")

        # 4. Criar memorias de teste
        print("\n--- Setup: Criando memorias de teste ---")
        memories = {
            "mem1": {
                "path": "/memories/test_kg/mem1",
                "content": "Transportadora RODONAVES sempre atrasa para AM e PA",
            },
            "mem2": {
                "path": "/memories/test_kg/mem2",
                "content": "Cliente ATACADAO pediu VCD1234567 com urgencia para SP",
            },
            "mem3": {
                "path": "/memories/test_kg/mem3",
                "content": "VCD1234567 embarcou para SP via RODONAVES com atraso",
            },
        }

        with db.engine.begin() as conn:
            for key, mem in memories.items():
                result = conn.execute(text("""
                    INSERT INTO agent_memories
                        (user_id, path, content, is_directory, importance_score,
                         last_accessed_at, created_at, updated_at)
                    VALUES
                        (:uid, :path, :content, false, 0.5,
                         NOW(), NOW(), NOW())
                    RETURNING id
                """), {
                    "uid": TEST_USER_ID,
                    "path": mem["path"],
                    "content": mem["content"],
                })
                row = result.fetchone()
                self.memory_ids[key] = row[0]
                print(f"   {key}: id={row[0]} — {mem['content'][:50]}...")

        print(f"\n   Memorias criadas: {self.memory_ids}")

    # =================================================================
    # TESTS
    # =================================================================

    def run_all_tests(self):
        """Executa todos os cenarios de teste."""
        self._test_extract_regex()
        self._test_haiku_entities()
        self._test_query_graph()
        self._test_remove_links()
        self._test_stats()
        self._test_user_isolation()
        self._test_idempotency()

    def _assert(self, condition, msg):
        """Assert com tracking de resultado."""
        if condition:
            self.passed += 1
            print(f"   PASS: {msg}")
        else:
            self.failed += 1
            self.errors.append(msg)
            print(f"   FAIL: {msg}")

    # -----------------------------------------------------------------
    # 2.2 Extract + Link (Write Path)
    # -----------------------------------------------------------------

    def _test_extract_regex(self):
        """Testa Layer 1 (regex) de extracao de entidades."""
        from app.agente.services.knowledge_graph_service import (
            extract_and_link_entities,
        )
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*60}")
        print("Test 2.2: Extract + Link (Write Path)")
        print(f"{'='*60}")

        # Memoria 1: "Transportadora RODONAVES sempre atrasa para AM e PA"
        stats1 = extract_and_link_entities(
            user_id=TEST_USER_ID,
            memory_id=self.memory_ids["mem1"],
            content="Transportadora RODONAVES sempre atrasa para AM e PA",
        )
        print(f"\n   Mem1 stats: {stats1}")
        self._assert(
            stats1['entities_count'] >= 2,
            f"Mem1 deve ter >= 2 entidades (AM, PA), got {stats1['entities_count']}"
        )
        self._assert(
            stats1['links_count'] >= 2,
            f"Mem1 deve ter >= 2 links, got {stats1['links_count']}"
        )

        # Memoria 2: "Cliente ATACADAO pediu VCD1234567 com urgencia para SP"
        stats2 = extract_and_link_entities(
            user_id=TEST_USER_ID,
            memory_id=self.memory_ids["mem2"],
            content="Cliente ATACADAO pediu VCD1234567 com urgencia para SP",
        )
        print(f"   Mem2 stats: {stats2}")
        self._assert(
            stats2['entities_count'] >= 2,
            f"Mem2 deve ter >= 2 entidades (SP, VCD1234567), got {stats2['entities_count']}"
        )

        # Memoria 3: "VCD1234567 embarcou para SP via RODONAVES com atraso"
        stats3 = extract_and_link_entities(
            user_id=TEST_USER_ID,
            memory_id=self.memory_ids["mem3"],
            content="VCD1234567 embarcou para SP via RODONAVES com atraso",
        )
        print(f"   Mem3 stats: {stats3}")
        self._assert(
            stats3['entities_count'] >= 2,
            f"Mem3 deve ter >= 2 entidades (SP, VCD1234567), got {stats3['entities_count']}"
        )

        # Verificacoes SQL
        print("\n   --- Verificacoes SQL ---")
        with db.engine.connect() as conn:
            # Total entidades criadas
            entity_count = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entities
                WHERE user_id = :uid
            """), {"uid": TEST_USER_ID}).scalar()
            self._assert(
                entity_count >= 3,
                f"Deve ter >= 3 entidades no total (AM, PA, SP, VCD1234567...), got {entity_count}"
            )

            # Total links criados
            link_count = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_links
                WHERE entity_id IN (
                    SELECT id FROM agent_memory_entities WHERE user_id = :uid
                )
            """), {"uid": TEST_USER_ID}).scalar()
            self._assert(
                link_count >= 6,
                f"Deve ter >= 6 links (3 memorias × 2+ entidades cada), got {link_count}"
            )

            # mention_count incrementou para SP (aparece em mem2 e mem3)
            sp_mention = conn.execute(text("""
                SELECT mention_count FROM agent_memory_entities
                WHERE user_id = :uid AND entity_type = 'uf' AND entity_name = 'SP'
            """), {"uid": TEST_USER_ID}).scalar()
            self._assert(
                sp_mention is not None and sp_mention >= 2,
                f"SP deve ter mention_count >= 2 (mem2+mem3), got {sp_mention}"
            )

            # entity_key preenchido para UFs
            uf_keys = conn.execute(text("""
                SELECT entity_name, entity_key FROM agent_memory_entities
                WHERE user_id = :uid AND entity_type = 'uf'
            """), {"uid": TEST_USER_ID}).fetchall()
            for uf_name, uf_key in uf_keys:
                self._assert(
                    uf_key == uf_name,
                    f"UF {uf_name} deve ter entity_key = {uf_name}, got {uf_key}"
                )

            # Co-occur relations (AM↔PA da mem1)
            co_occur_count = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_relations
                WHERE relation_type = 'co_occurs'
                  AND source_entity_id IN (
                      SELECT id FROM agent_memory_entities WHERE user_id = :uid
                  )
            """), {"uid": TEST_USER_ID}).scalar()
            self._assert(
                co_occur_count >= 1,
                f"Deve ter >= 1 relacao co_occurs, got {co_occur_count}"
            )

    # -----------------------------------------------------------------
    # 2.3 Haiku Entities (Write Path com Layer 3)
    # -----------------------------------------------------------------

    def _test_haiku_entities(self):
        """Testa Layer 3 (Haiku entities + relations)."""
        from app.agente.services.knowledge_graph_service import (
            extract_and_link_entities,
        )
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*60}")
        print("Test 2.3: Haiku Entities (Layer 3)")
        print(f"{'='*60}")

        # Re-processar mem1 com entidades Haiku
        stats = extract_and_link_entities(
            user_id=TEST_USER_ID,
            memory_id=self.memory_ids["mem1"],
            content="Transportadora RODONAVES sempre atrasa para AM e PA",
            haiku_entities=[
                ("transportadora", "RODONAVES"),
                ("uf", "AM"),
            ],
            haiku_relations=[
                ("RODONAVES", "atrasa_para", "AM"),
            ],
        )
        print(f"   Stats com Haiku: {stats}")

        self._assert(
            stats['relations_count'] >= 1,
            f"Deve ter >= 1 relacao do Haiku (atrasa_para), got {stats['relations_count']}"
        )

        # Verificar relacao no banco
        with db.engine.connect() as conn:
            haiku_rel = conn.execute(text("""
                SELECT r.relation_type, s.entity_name AS source_name, t.entity_name AS target_name
                FROM agent_memory_entity_relations r
                JOIN agent_memory_entities s ON r.source_entity_id = s.id
                JOIN agent_memory_entities t ON r.target_entity_id = t.id
                WHERE s.user_id = :uid
                  AND r.relation_type = 'atrasa_para'
            """), {"uid": TEST_USER_ID}).fetchall()

            self._assert(
                len(haiku_rel) >= 1,
                f"Relacao atrasa_para deve existir no banco, found {len(haiku_rel)}"
            )

            if haiku_rel:
                rel = haiku_rel[0]
                self._assert(
                    rel[0] == 'atrasa_para',
                    f"relation_type deve ser 'atrasa_para', got '{rel[0]}'"
                )

            # Verificar que entidades Haiku mergearam (nao duplicaram)
            am_count = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entities
                WHERE user_id = :uid AND entity_type = 'uf' AND entity_name = 'AM'
            """), {"uid": TEST_USER_ID}).scalar()
            self._assert(
                am_count == 1,
                f"UF AM nao deve estar duplicada (UNIQUE constraint), count={am_count}"
            )

    # -----------------------------------------------------------------
    # 2.4 Query Graph (Read Path)
    # -----------------------------------------------------------------

    def _test_query_graph(self):
        """Testa busca de memorias via knowledge graph."""
        from app.agente.services.knowledge_graph_service import (
            query_graph_memories,
        )

        print(f"\n{'='*60}")
        print("Test 2.4: Query Graph (Read Path)")
        print(f"{'='*60}")

        # Query 1: "entregas para AM" → deve retornar mem1 (tem AM)
        results_am = query_graph_memories(
            user_id=TEST_USER_ID,
            prompt="entregas para AM",
        )
        print(f"   Query 'AM': {len(results_am)} resultados")
        result_mids_am = {r['memory_id'] for r in results_am}
        self._assert(
            self.memory_ids["mem1"] in result_mids_am,
            f"Query AM deve retornar mem1 (id={self.memory_ids['mem1']})"
        )
        self._assert(
            self.memory_ids["mem2"] not in result_mids_am,
            f"Query AM NAO deve retornar mem2 (id={self.memory_ids['mem2']})"
        )

        # Query 2: "pedido VCD1234567" → deve retornar mem2 e mem3
        results_vcd = query_graph_memories(
            user_id=TEST_USER_ID,
            prompt="pedido VCD1234567",
        )
        print(f"   Query 'VCD1234567': {len(results_vcd)} resultados")
        result_mids_vcd = {r['memory_id'] for r in results_vcd}
        self._assert(
            self.memory_ids["mem2"] in result_mids_vcd,
            f"Query VCD deve retornar mem2 (id={self.memory_ids['mem2']})"
        )
        self._assert(
            self.memory_ids["mem3"] in result_mids_vcd,
            f"Query VCD deve retornar mem3 (id={self.memory_ids['mem3']})"
        )

        # Query 3: com exclude
        results_excl = query_graph_memories(
            user_id=TEST_USER_ID,
            prompt="entregas para SP",
            exclude_memory_ids={self.memory_ids["mem2"]},
        )
        print(f"   Query 'SP' (excluindo mem2): {len(results_excl)} resultados")
        result_mids_excl = {r['memory_id'] for r in results_excl}
        self._assert(
            self.memory_ids["mem2"] not in result_mids_excl,
            f"Query SP com exclude nao deve retornar mem2 (id={self.memory_ids['mem2']})"
        )
        self._assert(
            self.memory_ids["mem3"] in result_mids_excl,
            f"Query SP com exclude deve retornar mem3 (id={self.memory_ids['mem3']})"
        )

        # Verificar source = 'graph' em todos resultados
        for r in results_am + results_vcd + results_excl:
            self._assert(
                r.get('source') == 'graph',
                f"Resultado deve ter source='graph', got '{r.get('source')}'"
            )
            break  # Verifica apenas 1 para nao poluir output

    # -----------------------------------------------------------------
    # 2.5 Remove Links (Delete Path)
    # -----------------------------------------------------------------

    def _test_remove_links(self):
        """Testa remocao de links e cleanup de orfaos."""
        from app.agente.services.knowledge_graph_service import (
            cleanup_orphan_entities,
            remove_memory_links,
        )
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*60}")
        print("Test 2.5: Remove Links (Delete Path)")
        print(f"{'='*60}")

        # Contar links antes
        with db.engine.connect() as conn:
            links_before = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_links
                WHERE memory_id = :mid
            """), {"mid": self.memory_ids["mem1"]}).scalar()

        print(f"   Links de mem1 antes: {links_before}")

        # Remover links de mem1
        removed = remove_memory_links(self.memory_ids["mem1"])
        print(f"   Links removidos: {removed}")

        self._assert(
            removed >= 1,
            f"Deve ter removido >= 1 link de mem1, got {removed}"
        )

        # Verificar 0 links para mem1
        with db.engine.connect() as conn:
            links_after = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_links
                WHERE memory_id = :mid
            """), {"mid": self.memory_ids["mem1"]}).scalar()

        self._assert(
            links_after == 0,
            f"Deve ter 0 links para mem1 apos remocao, got {links_after}"
        )

        # Entidades AM e PA ainda existem (sem CASCADE para entities)
        with db.engine.connect() as conn:
            am_exists = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entities
                WHERE user_id = :uid AND entity_type = 'uf' AND entity_name = 'AM'
            """), {"uid": TEST_USER_ID}).scalar()
        self._assert(
            am_exists >= 1,
            f"Entidade AM deve ainda existir apos remover links, count={am_exists}"
        )

        # Memorias 2 e 3 nao afetadas
        with db.engine.connect() as conn:
            mem2_links = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_links
                WHERE memory_id = :mid
            """), {"mid": self.memory_ids["mem2"]}).scalar()
            mem3_links = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_links
                WHERE memory_id = :mid
            """), {"mid": self.memory_ids["mem3"]}).scalar()

        self._assert(
            mem2_links >= 1,
            f"mem2 deve manter seus links, got {mem2_links}"
        )
        self._assert(
            mem3_links >= 1,
            f"mem3 deve manter seus links, got {mem3_links}"
        )

        # Cleanup orfaos — PA pode ser orfao se so tinha link em mem1
        orphans_removed = cleanup_orphan_entities(user_id=TEST_USER_ID)
        print(f"   Orfaos removidos: {orphans_removed}")
        # Nao assert no valor exato — depende de quantas entidades
        # eram exclusivas de mem1

    # -----------------------------------------------------------------
    # 2.6 Stats
    # -----------------------------------------------------------------

    def _test_stats(self):
        """Testa get_graph_stats."""
        from app.agente.services.knowledge_graph_service import get_graph_stats

        print(f"\n{'='*60}")
        print("Test 2.6: Stats")
        print(f"{'='*60}")

        stats = get_graph_stats(user_id=TEST_USER_ID)
        print(f"   Stats: {stats}")

        self._assert(
            stats['total_entities'] >= 1,
            f"total_entities deve ser >= 1, got {stats['total_entities']}"
        )
        self._assert(
            stats['total_links'] >= 1,
            f"total_links deve ser >= 1 (mem2+mem3 links), got {stats['total_links']}"
        )
        self._assert(
            isinstance(stats['entities_by_type'], dict),
            f"entities_by_type deve ser dict, got {type(stats['entities_by_type'])}"
        )
        self._assert(
            isinstance(stats['top_entities'], list),
            f"top_entities deve ser list, got {type(stats['top_entities'])}"
        )

        # entities_by_type deve ter pelo menos 'uf' ou 'pedido'
        known_types = {'uf', 'pedido', 'transportadora', 'cnpj', 'valor', 'regra'}
        has_known_type = bool(set(stats['entities_by_type'].keys()) & known_types)
        self._assert(
            has_known_type,
            f"entities_by_type deve ter tipos conhecidos, got {stats['entities_by_type']}"
        )

        # top_entities deve ter formato correto
        if stats['top_entities']:
            first = stats['top_entities'][0]
            self._assert(
                all(k in first for k in ['type', 'name', 'mentions']),
                f"top_entities item deve ter type/name/mentions, got {first}"
            )

    # -----------------------------------------------------------------
    # 2.7 Isolamento de usuario
    # -----------------------------------------------------------------

    def _test_user_isolation(self):
        """Testa que usuario diferente nao ve dados do outro."""
        from app.agente.services.knowledge_graph_service import (
            query_graph_memories,
        )

        print(f"\n{'='*60}")
        print("Test 2.7: Isolamento de Usuario")
        print(f"{'='*60}")

        # User 88888 buscando por AM — nao deve encontrar nada
        results = query_graph_memories(
            user_id=TEST_USER_ID_2,
            prompt="entregas para AM",
        )
        self._assert(
            len(results) == 0,
            f"User {TEST_USER_ID_2} nao deve ver dados de {TEST_USER_ID}, got {len(results)} resultados"
        )

    # -----------------------------------------------------------------
    # 2.8 Idempotencia
    # -----------------------------------------------------------------

    def _test_idempotency(self):
        """Testa que chamadas duplicadas nao geram duplicatas."""
        from app.agente.services.knowledge_graph_service import (
            extract_and_link_entities,
        )
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*60}")
        print("Test 2.8: Idempotencia")
        print(f"{'='*60}")

        # Capturar mention_count de SP antes
        with db.engine.connect() as conn:
            sp_before = conn.execute(text("""
                SELECT mention_count FROM agent_memory_entities
                WHERE user_id = :uid AND entity_type = 'uf' AND entity_name = 'SP'
            """), {"uid": TEST_USER_ID}).scalar() or 0

        # Chamar extract novamente para mem2 (mesmo conteudo)
        extract_and_link_entities(
            user_id=TEST_USER_ID,
            memory_id=self.memory_ids["mem2"],
            content="Cliente ATACADAO pediu VCD1234567 com urgencia para SP",
        )

        with db.engine.connect() as conn:
            # SP nao deve duplicar (UNIQUE constraint)
            sp_count = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entities
                WHERE user_id = :uid AND entity_type = 'uf' AND entity_name = 'SP'
            """), {"uid": TEST_USER_ID}).scalar()
            self._assert(
                sp_count == 1,
                f"SP nao deve duplicar (UNIQUE), count={sp_count}"
            )

            # mention_count deve ter incrementado
            sp_after = conn.execute(text("""
                SELECT mention_count FROM agent_memory_entities
                WHERE user_id = :uid AND entity_type = 'uf' AND entity_name = 'SP'
            """), {"uid": TEST_USER_ID}).scalar() or 0
            self._assert(
                sp_after > sp_before,
                f"SP mention_count deve incrementar: before={sp_before}, after={sp_after}"
            )

            # Links nao devem duplicar (UNIQUE constraint em entity_memory_link)
            link_count = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_links l
                JOIN agent_memory_entities e ON l.entity_id = e.id
                WHERE e.user_id = :uid
                  AND e.entity_name = 'SP'
                  AND l.memory_id = :mid
            """), {"uid": TEST_USER_ID, "mid": self.memory_ids["mem2"]}).scalar()
            self._assert(
                link_count == 1,
                f"Link SP→mem2 nao deve duplicar, count={link_count}"
            )

    # =================================================================
    # CLEANUP
    # =================================================================

    def _cleanup_test_data(self):
        """Remove TODOS os dados de teste (user_id = 99999 e 88888)."""
        from app import db
        from sqlalchemy import text

        for uid in [TEST_USER_ID, TEST_USER_ID_2]:
            with db.engine.begin() as conn:
                # 1. Relations (FK para entities)
                conn.execute(text("""
                    DELETE FROM agent_memory_entity_relations
                    WHERE source_entity_id IN (
                        SELECT id FROM agent_memory_entities WHERE user_id = :uid
                    )
                    OR target_entity_id IN (
                        SELECT id FROM agent_memory_entities WHERE user_id = :uid
                    )
                """), {"uid": uid})

                # 2. Links (FK para entities e memories)
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

                # 4. Memory versions (FK para memories)
                conn.execute(text("""
                    DELETE FROM agent_memory_versions
                    WHERE memory_id IN (
                        SELECT id FROM agent_memories WHERE user_id = :uid
                    )
                """), {"uid": uid})

                # 5. Memories
                conn.execute(text("""
                    DELETE FROM agent_memories WHERE user_id = :uid
                """), {"uid": uid})

                # 6. Usuario de teste
                conn.execute(text("""
                    DELETE FROM usuarios WHERE id = :uid
                """), {"uid": uid})

    def cleanup(self):
        """Cleanup final completo."""
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*60}")
        print("Cleanup Final")
        print(f"{'='*60}")

        try:
            self._cleanup_test_data()

            # Verificar que nao restou nada
            with db.engine.connect() as conn:
                for uid in [TEST_USER_ID, TEST_USER_ID_2]:
                    remaining = conn.execute(text("""
                        SELECT
                            (SELECT COUNT(*) FROM agent_memory_entities WHERE user_id = :uid) AS entities,
                            (SELECT COUNT(*) FROM agent_memories WHERE user_id = :uid) AS memories
                    """), {"uid": uid}).fetchone()

                    print(f"   User {uid}: entities={remaining[0]}, memories={remaining[1]}")

                    if remaining[0] > 0 or remaining[1] > 0:
                        print(f"   AVISO: Dados residuais para user_id={uid}!")

        except Exception as e:
            print(f"   ERRO no cleanup: {e}")
            traceback.print_exc()

    # =================================================================
    # REPORT
    # =================================================================

    def report(self):
        """Imprime resultado final."""
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"RESULTADO: {self.passed}/{total} testes passaram")
        if self.failed > 0:
            print(f"\nFALHAS ({self.failed}):")
            for err in self.errors:
                print(f"   - {err}")
        else:
            print("\nTodos os testes passaram!")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    main()

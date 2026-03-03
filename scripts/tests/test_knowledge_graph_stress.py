#!/usr/bin/env python
"""
Stress Test — Knowledge Graph (T3-3)

Valida que o KG é corretamente utilizado no pipeline real:
  1. WRITE: save_memory → extract_and_link_entities (3 layers)
  2. READ:  _load_user_memories_for_context → query_graph_memories (Tier 2b)
  3. UPDATE: remove_memory_links → re-extract
  4. DELETE: remove_memory_links → cleanup_orphan_entities
  5. STATS:  get_graph_stats

Padrão de output: grading.json (compatível com skill-creator eval viewer)

Execução:
    source .venv/bin/activate
    python scripts/tests/test_knowledge_graph_stress.py

Segurança:
    - TEST_USER_IDs = 99998, 99997 (não existem em produção)
    - Cleanup final remove TUDO
    - Output JSON em /tmp/kg_stress_results.json

Cenários:
    S1: Bulk Extraction (60 memórias, 3 layers)
    S2: Entity Deduplication + mention_count
    S3: Co-occurrence Cap (>10 entities → max 10 pares)
    S4: Query Performance + Precision
    S5: Exclude Set (simula Tier 2b real)
    S6: Update Path (remove + re-extract)
    S7: Delete + Orphan Cleanup
    S8: Multi-User Isolation
    S9: Feature Flag Toggle
    S10: Stats Accuracy
    S11: Haiku Entity Merge (Layer 3 pipeline)
    S12: Parse Contextual Response Stress
"""

import json
import os
import sys
import time
import traceback

# Setup path para imports do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Desabilitar Voyage Layer 2 — sem API key em teste
os.environ.setdefault('EMBEDDINGS_ENABLED', 'false')

TEST_USER_A = 99998
TEST_USER_B = 99997
OUTPUT_PATH = '/tmp/kg_stress_results.json'

# =====================================================================
# Dados de teste realistas (domínio logístico)
# =====================================================================

_UFS = ['SP', 'RJ', 'MG', 'AM', 'PA', 'BA', 'CE', 'PR', 'RS', 'SC',
        'GO', 'MT', 'MS', 'PE', 'MA', 'ES', 'DF', 'RN', 'PB', 'AL']

_PEDIDOS = [f'VCD{i}' for i in range(1000001, 1000031)]  # 30 pedidos

_CNPJS_FORMATADOS = [
    '12.345.678/0001-99', '98.765.432/0001-55', '11.222.333/0001-44',
    '55.666.777/0001-88', '99.888.777/0001-11',
]

_CARRIERS = ['RODONAVES', 'TAC', 'TRANSMERC', 'PATRUS', 'FL BRASIL',
             'JADLOG', 'BRASPRESS', 'TNT MERCURIO']

_CLIENTS = ['ATACADAO', 'SENDAS', 'ASSAI', 'CARREFOUR', 'BIG']


def _generate_memories():
    """Gera 60 memórias com conteúdos variados para stress test."""
    memories = []

    # 10 memórias UF-focused (1 entidade principal cada)
    for i, uf in enumerate(_UFS[:10]):
        carrier = _CARRIERS[i % len(_CARRIERS)]
        memories.append({
            "key": f"uf_{i}",
            "path": f"/memories/test_stress/uf_{i}",
            "content": f"Entregas para {uf} tem lead time de {3 + i} dias via {carrier}",
            "expected_ufs": {uf},
        })

    # 10 memórias pedido-focused (UF + pedido)
    for i in range(10):
        uf = _UFS[i % len(_UFS)]
        pedido = _PEDIDOS[i]
        client = _CLIENTS[i % len(_CLIENTS)]
        memories.append({
            "key": f"ped_{i}",
            "path": f"/memories/test_stress/ped_{i}",
            "content": f"Pedido {pedido} do {client} para {uf} com urgencia",
            "expected_pedidos": {pedido},
        })

    # 5 memórias CNPJ
    for i, cnpj in enumerate(_CNPJS_FORMATADOS):
        memories.append({
            "key": f"cnpj_{i}",
            "path": f"/memories/test_stress/cnpj_{i}",
            "content": f"CNPJ {cnpj} deve ser faturado pela filial FB",
        })

    # 5 memórias valor
    for i in range(5):
        uf = _UFS[i]
        valor = f"R$ {(i + 1) * 1000},{i}0"
        memories.append({
            "key": f"val_{i}",
            "path": f"/memories/test_stress/val_{i}",
            "content": f"Frete de {valor} para {uf} via {_CARRIERS[i % len(_CARRIERS)]}",
        })

    # 10 memórias mixed (todos os tipos)
    for i in range(10):
        uf = _UFS[i]
        pedido = _PEDIDOS[10 + i]
        cnpj = _CNPJS_FORMATADOS[i % len(_CNPJS_FORMATADOS)]
        valor = f"R$ {(i + 5) * 500},00"
        memories.append({
            "key": f"mix_{i}",
            "path": f"/memories/test_stress/mix_{i}",
            "content": (
                f"Pedido {pedido} do CNPJ {cnpj} para {uf} "
                f"no valor de {valor} via {_CARRIERS[i % len(_CARRIERS)]}"
            ),
        })

    # 10 memórias sobre SP (para testar dedup + mention_count alto)
    for i in range(10):
        memories.append({
            "key": f"sp_{i}",
            "path": f"/memories/test_stress/sp_{i}",
            "content": f"Entrega #{i + 1} para SP via {_CARRIERS[i % len(_CARRIERS)]} com prioridade",
        })

    # 5 memórias noise (sem entidades extraíveis)
    noise_texts = [
        "Verificar programacao da proxima semana",
        "Reuniao com equipe sobre processos internos",
        "Lembrar de atualizar planilha de controle",
        "Novo procedimento de conferencia no almoxarifado",
        "Treinamento da equipe sobre sistema novo",
    ]
    for i, txt in enumerate(noise_texts):
        memories.append({
            "key": f"noise_{i}",
            "path": f"/memories/test_stress/noise_{i}",
            "content": txt,
        })

    # 5 memórias com >10 entidades (para testar co-occurrence cap)
    for i in range(5):
        # 12 UFs distintas em uma memória
        ufs_bulk = ' '.join(_UFS[i:i + 12])
        memories.append({
            "key": f"bulk_{i}",
            "path": f"/memories/test_stress/bulk_{i}",
            "content": f"Rota multi-estado: {ufs_bulk} via {_CARRIERS[i % len(_CARRIERS)]}",
            "entity_count_min": 10,  # pelo menos 10 UFs
        })

    return memories


# =====================================================================
# Runner
# =====================================================================

class StressTestRunner:
    """Executa stress test do Knowledge Graph com output estruturado."""

    def __init__(self, app):
        self.app = app
        self.expectations = []
        self.memory_ids = {}  # key → memory_id
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
    # SETUP
    # -----------------------------------------------------------------

    def setup(self):
        """Cria tabelas, usuarios e 60 memorias de teste."""
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*70}")
        print("T3-3 Knowledge Graph — STRESS TEST")
        print(f"{'='*70}")

        # Cleanup preventivo
        self._cleanup_data()

        # Usuarios de teste
        for uid, name in [(TEST_USER_A, 'STRESS_A'), (TEST_USER_B, 'STRESS_B')]:
            with db.engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO usuarios (id, nome, email, senha_hash, perfil, status, criado_em)
                    VALUES (:id, :nome, :email, 'test_hash', 'administrador', 'ativo', NOW())
                    ON CONFLICT (id) DO NOTHING
                """), {
                    "id": uid,
                    "nome": f"TEST_{name}",
                    "email": f"test_stress_{uid}@test.local",
                })

        # Criar memorias
        memories = _generate_memories()
        print(f"\n   Criando {len(memories)} memorias...")

        with _Timer(self.timings, 'setup_memories'):
            with db.engine.begin() as conn:
                for mem in memories:
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
    # S1: Bulk Extraction
    # -----------------------------------------------------------------

    def test_s1_bulk_extraction(self):
        """S1: Extrair entidades de 60 memórias em sequência."""
        from app.agente.services.knowledge_graph_service import (
            extract_and_link_entities,
        )

        print(f"\n{'='*70}")
        print("S1: Bulk Extraction (60 memorias)")
        print(f"{'='*70}")

        memories = _generate_memories()
        total_entities = 0
        total_links = 0
        total_relations = 0
        errors = 0

        with _Timer(self.timings, 's1_bulk_extract'):
            for mem in memories:
                mid = self.memory_ids.get(mem["key"])
                if not mid:
                    errors += 1
                    continue
                try:
                    stats = extract_and_link_entities(
                        user_id=TEST_USER_A,
                        memory_id=mid,
                        content=mem["content"],
                    )
                    total_entities += stats['entities_count']
                    total_links += stats['links_count']
                    total_relations += stats['relations_count']
                except Exception as e:
                    errors += 1

        duration = self.timings['s1_bulk_extract']
        avg_ms = (duration / len(memories)) * 1000

        print(f"   Total: {total_entities} entities, {total_links} links, "
              f"{total_relations} relations em {duration:.2f}s ({avg_ms:.1f}ms/mem)")

        self._expect(
            "S1.1: Todas 60 memorias processadas sem erro",
            errors == 0,
            f"errors={errors}",
        )
        self._expect(
            "S1.2: Entidades extraidas (>= 30 UFs+pedidos+CNPJs)",
            total_entities >= 30,
            f"total_entities={total_entities}",
        )
        self._expect(
            "S1.3: Links criados (>= 30)",
            total_links >= 30,
            f"total_links={total_links}",
        )
        self._expect(
            "S1.4: Performance media < 100ms/memoria (regex Layer 1)",
            avg_ms < 100,
            f"avg={avg_ms:.1f}ms/mem",
        )

    # -----------------------------------------------------------------
    # S2: Deduplication + mention_count
    # -----------------------------------------------------------------

    def test_s2_deduplication(self):
        """S2: SP aparece em 10+ memorias → 1 entidade, mention_count alto."""
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*70}")
        print("S2: Entity Deduplication + mention_count")
        print(f"{'='*70}")

        with db.engine.connect() as conn:
            sp_row = conn.execute(text("""
                SELECT entity_name, mention_count
                FROM agent_memory_entities
                WHERE user_id = :uid AND entity_type = 'uf' AND entity_name = 'SP'
            """), {"uid": TEST_USER_A}).fetchone()

            sp_count = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entities
                WHERE user_id = :uid AND entity_type = 'uf' AND entity_name = 'SP'
            """), {"uid": TEST_USER_A}).scalar()

            total_ufs = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entities
                WHERE user_id = :uid AND entity_type = 'uf'
            """), {"uid": TEST_USER_A}).scalar()

        self._expect(
            "S2.1: SP existe como entidade unica (UNIQUE constraint)",
            sp_count == 1,
            f"count_rows_SP={sp_count}",
        )
        self._expect(
            "S2.2: SP mention_count >= 10 (10 memorias sp_*)",
            sp_row is not None and sp_row[1] >= 10,
            f"mention_count={sp_row[1] if sp_row else 'NULL'}",
        )
        self._expect(
            "S2.3: Pelo menos 10 UFs distintas no grafo",
            total_ufs is not None and total_ufs >= 10,
            f"total_ufs={total_ufs}",
        )

    # -----------------------------------------------------------------
    # S3: Co-occurrence Cap
    # -----------------------------------------------------------------

    def test_s3_co_occurrence_cap(self):
        """S3: Memoria com 12 UFs → max 10 geram co-occurs = 45 pares."""
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*70}")
        print("S3: Co-occurrence Cap (MAX_CO_OCCURS_ENTITIES=10)")
        print(f"{'='*70}")

        # bulk_0 tem 12 UFs. Co-occurs devem ser capped em 10 → max 45 pares
        bulk_mid = self.memory_ids.get("bulk_0")
        if not bulk_mid:
            self._expect("S3: memoria bulk_0 existe", False, "memory_id=None")
            return

        with db.engine.connect() as conn:
            co_occur_count = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_relations
                WHERE relation_type = 'co_occurs' AND memory_id = :mid
            """), {"mid": bulk_mid}).scalar()

        # Com 10 entities capped: C(10,2) = 45 pares
        # Com 12 entities sem cap: C(12,2) = 66 pares
        self._expect(
            "S3.1: Co-occurs da bulk_0 <= 45 (cap em 10 entities → C(10,2)=45)",
            co_occur_count is not None and co_occur_count <= 45,
            f"co_occurs={co_occur_count}",
        )
        self._expect(
            "S3.2: Co-occurs da bulk_0 >= 1 (entidades coocorrem)",
            co_occur_count is not None and co_occur_count >= 1,
            f"co_occurs={co_occur_count}",
        )

    # -----------------------------------------------------------------
    # S4: Query Performance + Precision
    # -----------------------------------------------------------------

    def test_s4_query_performance(self):
        """S4: Query graph e verifica precisão + latência."""
        from app.agente.services.knowledge_graph_service import query_graph_memories

        print(f"\n{'='*70}")
        print("S4: Query Performance + Precision")
        print(f"{'='*70}")

        queries = [
            ("AM", "uf", True),
            ("VCD1000001", "pedido", True),
            ("SP", "uf", True),
            ("XYZINEXISTENTE", "nada", False),
            ("", "vazio", False),
        ]

        latencies = []
        for prompt, label, expect_results in queries:
            t0 = time.time()
            results = query_graph_memories(
                user_id=TEST_USER_A,
                prompt=prompt,
                limit=20,
            )
            dt_ms = (time.time() - t0) * 1000
            latencies.append(dt_ms)

            if expect_results:
                self._expect(
                    f"S4: Query '{prompt}' retorna resultados ({label})",
                    len(results) >= 1,
                    f"count={len(results)}, latency={dt_ms:.1f}ms",
                )
            else:
                self._expect(
                    f"S4: Query '{prompt}' retorna vazio ({label})",
                    len(results) == 0,
                    f"count={len(results)}, latency={dt_ms:.1f}ms",
                )

        avg_latency = sum(latencies) / len(latencies)
        self._expect(
            "S4: Latencia media de query < 50ms",
            avg_latency < 50,
            f"avg_latency={avg_latency:.1f}ms",
        )

    # -----------------------------------------------------------------
    # S5: Exclude Set (simula Tier 2b real)
    # -----------------------------------------------------------------

    def test_s5_exclude_set(self):
        """S5: Simula Tier 2b — semantic já encontrou N, KG complementa."""
        from app.agente.services.knowledge_graph_service import query_graph_memories

        print(f"\n{'='*70}")
        print("S5: Exclude Set (Tier 2b simulation)")
        print(f"{'='*70}")

        # Primeiro, buscar tudo para SP
        all_sp = query_graph_memories(
            user_id=TEST_USER_A,
            prompt="entrega para SP",
            limit=50,
        )
        all_sp_ids = {r['memory_id'] for r in all_sp}

        # Simular semantic_ids (metade dos resultados já encontrados)
        if len(all_sp_ids) >= 2:
            exclude_half = set(list(all_sp_ids)[:len(all_sp_ids) // 2])
            remaining = query_graph_memories(
                user_id=TEST_USER_A,
                prompt="entrega para SP",
                exclude_memory_ids=exclude_half,
                limit=50,
            )
            remaining_ids = {r['memory_id'] for r in remaining}

            overlap = exclude_half & remaining_ids
            self._expect(
                "S5.1: Exclude set funciona — 0 overlap com IDs excluídos",
                len(overlap) == 0,
                f"overlap={overlap}",
            )
            self._expect(
                "S5.2: Resultados complementares existem",
                len(remaining_ids) >= 1,
                f"remaining={len(remaining_ids)}, excluded={len(exclude_half)}",
            )
        else:
            self._expect(
                "S5: Pré-condição (>= 2 resultados para SP)",
                False,
                f"all_sp count={len(all_sp_ids)}, esperava >= 2",
            )

        # Todos resultados devem ter source='graph'
        for r in all_sp:
            if r.get('source') != 'graph':
                self._expect("S5.3: source='graph' em todos resultados", False,
                             f"found source='{r.get('source')}'")
                break
        else:
            self._expect("S5.3: source='graph' em todos resultados", True,
                         f"count={len(all_sp)}")

    # -----------------------------------------------------------------
    # S6: Update Path (remove + re-extract)
    # -----------------------------------------------------------------

    def test_s6_update_path(self):
        """S6: Simula update_memory → remove_links + re-extract."""
        from app.agente.services.knowledge_graph_service import (
            extract_and_link_entities,
            remove_memory_links,
        )
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*70}")
        print("S6: Update Path (remove + re-extract)")
        print(f"{'='*70}")

        mid = self.memory_ids["uf_0"]
        old_content = f"Entregas para {_UFS[0]} tem lead time de 3 dias via {_CARRIERS[0]}"
        new_content = f"Entregas para RJ tem lead time de 5 dias via {_CARRIERS[1]}"

        # Links antes do update
        with db.engine.connect() as conn:
            links_before = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_links WHERE memory_id = :mid
            """), {"mid": mid}).scalar()

        # STEP 1: Remove old links (como memory_mcp_tool faz)
        removed = remove_memory_links(mid)
        self._expect(
            "S6.1: Links antigos removidos",
            removed >= 1,
            f"removed={removed}, before={links_before}",
        )

        # STEP 2: Re-extract com novo conteudo
        stats = extract_and_link_entities(
            user_id=TEST_USER_A,
            memory_id=mid,
            content=new_content,
        )
        self._expect(
            "S6.2: Novas entidades extraidas apos update",
            stats['entities_count'] >= 1,
            f"entities={stats['entities_count']}",
        )

        # Verificar que RJ agora está linkado a essa memória
        with db.engine.connect() as conn:
            rj_linked = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_links l
                JOIN agent_memory_entities e ON l.entity_id = e.id
                WHERE l.memory_id = :mid AND e.entity_name = 'RJ'
            """), {"mid": mid}).scalar()

        self._expect(
            "S6.3: RJ agora está linkado à memória atualizada",
            rj_linked is not None and rj_linked >= 1,
            f"rj_links={rj_linked}",
        )

    # -----------------------------------------------------------------
    # S7: Delete + Orphan Cleanup
    # -----------------------------------------------------------------

    def test_s7_delete_cleanup(self):
        """S7: Deletar memorias noise e limpar orfaos."""
        from app.agente.services.knowledge_graph_service import (
            cleanup_orphan_entities,
            remove_memory_links,
        )
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*70}")
        print("S7: Delete + Orphan Cleanup")
        print(f"{'='*70}")

        # Contar entidades antes
        with db.engine.connect() as conn:
            entities_before = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entities WHERE user_id = :uid
            """), {"uid": TEST_USER_A}).scalar()

        # Remover links de 5 memorias noise (não devem ter entidades)
        noise_removed = 0
        for i in range(5):
            mid = self.memory_ids.get(f"noise_{i}")
            if mid:
                noise_removed += remove_memory_links(mid)

        self._expect(
            "S7.1: Memorias noise têm 0 links (sem entidades extraíveis)",
            noise_removed == 0,
            f"links_from_noise={noise_removed}",
        )

        # Remover links de uf_1 (SP aparece em muitas, mas uf_1 é única)
        mid_uf1 = self.memory_ids.get("uf_1")
        if mid_uf1:
            removed = remove_memory_links(mid_uf1)
            self._expect(
                "S7.2: Links de uf_1 removidos",
                removed >= 1,
                f"removed={removed}",
            )

        # Cleanup orfaos
        orphans = cleanup_orphan_entities(user_id=TEST_USER_A)
        print(f"   Orfaos removidos: {orphans}")

        # Entidades compartilhadas NÃO devem ser removidas
        with db.engine.connect() as conn:
            sp_exists = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entities
                WHERE user_id = :uid AND entity_name = 'SP'
            """), {"uid": TEST_USER_A}).scalar()

        self._expect(
            "S7.3: SP (compartilhada) sobrevive ao cleanup",
            sp_exists is not None and sp_exists >= 1,
            f"sp_exists={sp_exists}",
        )

    # -----------------------------------------------------------------
    # S8: Multi-User Isolation
    # -----------------------------------------------------------------

    def test_s8_user_isolation(self):
        """S8: User B não vê dados do User A."""
        from app.agente.services.knowledge_graph_service import (
            extract_and_link_entities,
            get_graph_stats,
            query_graph_memories,
        )
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*70}")
        print("S8: Multi-User Isolation")
        print(f"{'='*70}")

        # Criar 1 memória para User B
        with db.engine.begin() as conn:
            result = conn.execute(text("""
                INSERT INTO agent_memories
                    (user_id, path, content, is_directory,
                     importance_score, last_accessed_at, created_at, updated_at)
                VALUES (:uid, '/memories/test_b/mem1',
                        'Entrega para RR via JADLOG', false, 0.5, NOW(), NOW(), NOW())
                RETURNING id
            """), {"uid": TEST_USER_B})
            mid_b = result.fetchone()[0]

        extract_and_link_entities(
            user_id=TEST_USER_B,
            memory_id=mid_b,
            content="Entrega para RR via JADLOG",
        )

        # User A busca RR → NÃO deve encontrar
        results_a = query_graph_memories(user_id=TEST_USER_A, prompt="RR")
        self._expect(
            "S8.1: User A não vê RR (pertence a User B)",
            len(results_a) == 0,
            f"results_for_A={len(results_a)}",
        )

        # User B busca SP → NÃO deve encontrar (pertence a User A)
        results_b = query_graph_memories(user_id=TEST_USER_B, prompt="SP")
        self._expect(
            "S8.2: User B não vê SP (pertence a User A)",
            len(results_b) == 0,
            f"results_for_B={len(results_b)}",
        )

        # User B busca RR → deve encontrar
        results_b_rr = query_graph_memories(user_id=TEST_USER_B, prompt="RR")
        self._expect(
            "S8.3: User B vê seus proprios dados (RR)",
            len(results_b_rr) >= 1,
            f"results_for_B_RR={len(results_b_rr)}",
        )

        # Stats isolados
        stats_a = get_graph_stats(user_id=TEST_USER_A)
        stats_b = get_graph_stats(user_id=TEST_USER_B)
        self._expect(
            "S8.4: Stats de User A >> Stats de User B",
            stats_a['total_entities'] > stats_b['total_entities'],
            f"A_entities={stats_a['total_entities']}, B_entities={stats_b['total_entities']}",
        )

    # -----------------------------------------------------------------
    # S9: Feature Flag Toggle
    # -----------------------------------------------------------------

    def test_s9_feature_flag(self):
        """S9: Desabilitar flag → operações retornam vazio."""
        from unittest.mock import patch

        print(f"\n{'='*70}")
        print("S9: Feature Flag Toggle")
        print(f"{'='*70}")

        # Desabilitar flag
        with patch('app.embeddings.config.MEMORY_KNOWLEDGE_GRAPH', False):
            from app.agente.services.knowledge_graph_service import (
                extract_and_link_entities,
                query_graph_memories,
            )

            result_extract = extract_and_link_entities(
                user_id=TEST_USER_A,
                memory_id=1,
                content="Teste SP AM VCD1234567 R$ 1.000,00",
            )
            result_query = query_graph_memories(
                user_id=TEST_USER_A,
                prompt="SP",
            )

        self._expect(
            "S9.1: Flag=False → extract retorna zeros",
            result_extract == {'entities_count': 0, 'links_count': 0, 'relations_count': 0},
            f"result={result_extract}",
        )
        self._expect(
            "S9.2: Flag=False → query retorna []",
            result_query == [],
            f"result={result_query}",
        )

    # -----------------------------------------------------------------
    # S10: Stats Accuracy
    # -----------------------------------------------------------------

    def test_s10_stats(self):
        """S10: Stats refletem estado real do grafo."""
        from app.agente.services.knowledge_graph_service import get_graph_stats
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*70}")
        print("S10: Stats Accuracy")
        print(f"{'='*70}")

        stats = get_graph_stats(user_id=TEST_USER_A)

        # Verificar contra contagem direta no banco
        with db.engine.connect() as conn:
            real_entities = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entities WHERE user_id = :uid
            """), {"uid": TEST_USER_A}).scalar()
            real_links = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_links l
                JOIN agent_memory_entities e ON l.entity_id = e.id
                WHERE e.user_id = :uid
            """), {"uid": TEST_USER_A}).scalar()
            real_relations = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_relations r
                JOIN agent_memory_entities e ON r.source_entity_id = e.id
                WHERE e.user_id = :uid
            """), {"uid": TEST_USER_A}).scalar()

        self._expect(
            "S10.1: total_entities matches DB",
            stats['total_entities'] == real_entities,
            f"stats={stats['total_entities']}, db={real_entities}",
        )
        self._expect(
            "S10.2: total_links matches DB",
            stats['total_links'] == real_links,
            f"stats={stats['total_links']}, db={real_links}",
        )
        self._expect(
            "S10.3: total_relations matches DB",
            stats['total_relations'] == real_relations,
            f"stats={stats['total_relations']}, db={real_relations}",
        )
        self._expect(
            "S10.4: entities_by_type soma = total_entities",
            sum(stats['entities_by_type'].values()) == stats['total_entities'],
            f"sum_by_type={sum(stats['entities_by_type'].values())}, total={stats['total_entities']}",
        )
        self._expect(
            "S10.5: top_entities ordenado por mention_count DESC",
            _is_sorted_desc(stats['top_entities'], 'mentions'),
            f"top_entities={[e['mentions'] for e in stats['top_entities'][:5]]}",
        )

    # -----------------------------------------------------------------
    # S11: Haiku Entity Merge (Layer 3 pipeline)
    # -----------------------------------------------------------------

    def test_s11_haiku_merge(self):
        """S11: Entidades Haiku mergeam com regex sem duplicar."""
        from app.agente.services.knowledge_graph_service import (
            extract_and_link_entities,
        )
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*70}")
        print("S11: Haiku Entity Merge (Layer 3)")
        print(f"{'='*70}")

        mid = self.memory_ids["ped_0"]
        content = f"Pedido {_PEDIDOS[0]} do {_CLIENTS[0]} para {_UFS[0]} com urgencia"

        # Re-extract com haiku_entities que OVERLAP com regex
        stats = extract_and_link_entities(
            user_id=TEST_USER_A,
            memory_id=mid,
            content=content,
            haiku_entities=[
                ("uf", _UFS[0]),  # já extraída por regex
                ("cliente", _CLIENTS[0]),  # nova, só haiku
                ("transportadora", "RODONAVES"),  # nova, só haiku
            ],
            haiku_relations=[
                (_CLIENTS[0], "pediu_para", _UFS[0]),
            ],
        )

        self._expect(
            "S11.1: Haiku merge gera entidades (regex + haiku)",
            stats['entities_count'] >= 3,
            f"entities={stats['entities_count']}",
        )

        # Verificar que UF não duplicou
        with db.engine.connect() as conn:
            uf_count = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entities
                WHERE user_id = :uid AND entity_type = 'uf'
                  AND entity_name = :name
            """), {"uid": TEST_USER_A, "name": _UFS[0]}).scalar()

        self._expect(
            f"S11.2: UF {_UFS[0]} não duplicou (UNIQUE constraint)",
            uf_count == 1,
            f"count={uf_count}",
        )

        # Verificar relação semântica criada
        with db.engine.connect() as conn:
            haiku_rel = conn.execute(text("""
                SELECT COUNT(*) FROM agent_memory_entity_relations
                WHERE relation_type = 'pediu_para'
                  AND source_entity_id IN (
                      SELECT id FROM agent_memory_entities WHERE user_id = :uid
                  )
            """), {"uid": TEST_USER_A}).scalar()

        self._expect(
            "S11.3: Relação Haiku 'pediu_para' criada",
            haiku_rel is not None and haiku_rel >= 1,
            f"count={haiku_rel}",
        )

    # -----------------------------------------------------------------
    # S12: Parse Contextual Response Stress
    # -----------------------------------------------------------------

    def test_s12_parse_stress(self):
        """S12: parse_contextual_response com inputs variados em massa."""
        from app.agente.services.knowledge_graph_service import (
            parse_contextual_response,
        )

        print(f"\n{'='*70}")
        print("S12: Parse Contextual Response Stress")
        print(f"{'='*70}")

        test_cases = [
            # Formato completo
            (
                "CONTEXTO: Memoria sobre frete\n"
                "ENTIDADES: uf:SP|pedido:VCD123|cnpj:12345678\n"
                "RELACOES: VCD123>destino>SP",
                3, 1,
            ),
            # Muitas entidades (20)
            (
                "CONTEXTO: Rota complexa\n"
                "ENTIDADES: " + "|".join(f"uf:{uf}" for uf in _UFS) + "\n"
                "RELACOES: nenhuma",
                20, 0,
            ),
            # Muitas relações (10)
            (
                "CONTEXTO: Rede\n"
                "ENTIDADES: transportadora:TAC|" + "|".join(f"uf:{uf}" for uf in _UFS[:10]) + "\n"
                "RELACOES: " + "|".join(f"TAC>entrega>{uf}" for uf in _UFS[:10]),
                11, 10,
            ),
            # Nenhuma
            (
                "CONTEXTO: Genérico\nENTIDADES: nenhuma\nRELACOES: nenhuma",
                0, 0,
            ),
            # Fallback (sem formato)
            ("Esta memória não segue o formato estruturado", 0, 0),
            # Vazio
            ("", 0, 0),
            # None
            (None, 0, 0),
            # Com acento em RELAÇÕES
            (
                "CONTEXTO: Teste\n"
                "ENTIDADES: uf:SP\n"
                "RELAÇÕES: SP>capital>BRASIL",
                1, 1,
            ),
        ]

        errors = 0
        with _Timer(self.timings, 's12_parse'):
            for text_input, exp_entities, exp_relations in test_cases:
                try:
                    ctx, ents, rels = parse_contextual_response(text_input)
                    if len(ents) != exp_entities:
                        errors += 1
                    if len(rels) != exp_relations:
                        errors += 1
                except Exception:
                    errors += 1

        self._expect(
            f"S12.1: {len(test_cases)} parse cases sem erro de lógica",
            errors == 0,
            f"errors={errors}/{len(test_cases)}",
        )
        self._expect(
            "S12.2: Parse performance < 1ms total",
            self.timings['s12_parse'] < 0.001,
            f"duration={self.timings['s12_parse']*1000:.2f}ms",
        )

    # -----------------------------------------------------------------
    # RUN ALL
    # -----------------------------------------------------------------

    def run_all(self):
        """Executa todos os cenários."""
        self.test_s1_bulk_extraction()
        self.test_s2_deduplication()
        self.test_s3_co_occurrence_cap()
        self.test_s4_query_performance()
        self.test_s5_exclude_set()
        self.test_s6_update_path()
        self.test_s7_delete_cleanup()
        self.test_s8_user_isolation()
        self.test_s9_feature_flag()
        self.test_s10_stats()
        self.test_s11_haiku_merge()
        self.test_s12_parse_stress()

    # -----------------------------------------------------------------
    # CLEANUP
    # -----------------------------------------------------------------

    def _cleanup_data(self):
        """Remove dados de teste."""
        from app import db
        from sqlalchemy import text

        for uid in [TEST_USER_A, TEST_USER_B]:
            with db.engine.begin() as conn:
                conn.execute(text("""
                    DELETE FROM agent_memory_entity_relations
                    WHERE source_entity_id IN (
                        SELECT id FROM agent_memory_entities WHERE user_id = :uid
                    ) OR target_entity_id IN (
                        SELECT id FROM agent_memory_entities WHERE user_id = :uid
                    )
                """), {"uid": uid})
                conn.execute(text("""
                    DELETE FROM agent_memory_entity_links
                    WHERE entity_id IN (
                        SELECT id FROM agent_memory_entities WHERE user_id = :uid
                    )
                """), {"uid": uid})
                conn.execute(text("""
                    DELETE FROM agent_memory_entities WHERE user_id = :uid
                """), {"uid": uid})
                conn.execute(text("""
                    DELETE FROM agent_memory_versions
                    WHERE memory_id IN (
                        SELECT id FROM agent_memories WHERE user_id = :uid
                    )
                """), {"uid": uid})
                conn.execute(text("""
                    DELETE FROM agent_memories WHERE user_id = :uid
                """), {"uid": uid})
                conn.execute(text("""
                    DELETE FROM usuarios WHERE id = :uid
                """), {"uid": uid})

    def cleanup(self):
        """Cleanup final + verificação de zero residual."""
        from app import db
        from sqlalchemy import text

        print(f"\n{'='*70}")
        print("Cleanup")
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

        # Console output
        print(f"\n{'='*70}")
        print(f"RESULTADO: {passed}/{total} expectations passed ({pass_rate:.0%})")
        print(f"Duração total: {total_duration:.2f}s")
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
                "scenarios_run": 12,
                "users_tested": 2,
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


def _is_sorted_desc(items: list, key: str) -> bool:
    """Verifica se lista está ordenada DESC por key."""
    if len(items) <= 1:
        return True
    values = [item.get(key, 0) for item in items]
    return all(values[i] >= values[i + 1] for i in range(len(values) - 1))


# =====================================================================
# Main
# =====================================================================

def main():
    from app import create_app
    app = create_app()
    runner = StressTestRunner(app)

    with app.app_context():
        try:
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

    sys.exit(0 if pass_rate == 1.0 else 1)


if __name__ == '__main__':
    main()

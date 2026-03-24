"""
Migration: Normalizar Knowledge Graph - relações e entidades (auditoria 2026-03-23)

Contexto:
- Auditoria revelou 100+ tipos de relação sem vocabulário controlado
- 72% das entidades são tipo 'regra' (catch-all genérico)
- 80% das relações são co_occurs (automáticas)

Ações:
1. Mapear tipos de relação existentes para vocabulário controlado (15 tipos)
2. Remover relações singleton não mapeáveis
3. Mudar entidades tipo 'regra' para 'conceito'
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Mapeamento de tipos antigos para tipos canônicos
RELATION_MAP = {
    # Já canônicos (manter)
    'co_occurs': 'co_occurs',
    'pertence_a': 'pertence_a',
    'depende_de': 'depende_de',
    'substitui': 'substitui',
    'conflita_com': 'conflita_com',
    'precede': 'precede',
    'bloqueia': 'bloqueia',
    'usa': 'usa',
    'produz': 'produz',
    'fornece': 'fornece',
    'consome': 'consome',
    'localizado_em': 'localizado_em',
    'responsavel_por': 'responsavel_por',
    'corrige': 'corrige',
    'requer': 'requer',
    'complementa': 'complementa',
    'atrasa_para': 'atrasa_para',
    # Sinônimos → canônicos
    'pertence': 'pertence_a', 'parte_de': 'pertence_a', 'faz_parte_de': 'pertence_a',
    'pertence_ao': 'pertence_a', 'pertence_ao_setor': 'pertence_a',
    'atua_em': 'responsavel_por', 'trabalha_em': 'responsavel_por',
    'executa': 'responsavel_por', 'realiza': 'responsavel_por',
    'opera': 'responsavel_por', 'opera_em': 'responsavel_por',
    'opera_com': 'responsavel_por', 'realiza_operacao': 'responsavel_por',
    'executa_diariamente': 'responsavel_por',
    'gera': 'produz', 'origina': 'produz', 'dispara': 'produz',
    'confirmacao_gera': 'produz', 'nao_gera': None,  # negação -> descartar
    'antecede': 'precede', 'transiciona_para': 'precede', 'transita_para': 'precede',
    'transita': 'precede', 'sequencia': 'precede', 'evolui_para': 'precede',
    'transiciona_de': 'precede', 'transita_de': 'precede',
    'vincula': 'complementa', 'vincula_a': 'complementa', 'relaciona_com': 'complementa',
    'integra': 'complementa', 'associada_a': 'complementa', 'relaciona': 'complementa',
    'relacionado_a': 'complementa', 'corresponde_a': 'complementa',
    'possui': 'complementa', 'contem': 'complementa', 'agrupa': 'complementa',
    'define': 'complementa',
    'corrigido_de': 'corrige', 'resolve': 'corrige', 'reverte': 'corrige',
    'afeta': 'depende_de', 'causa': 'depende_de', 'propaga': 'depende_de',
    'condiciona': 'depende_de', 'sujeito_a': 'depende_de',
    'bloqueia_sem': 'bloqueia', 'dificulta': 'bloqueia',
    'exige': 'requer', 'exige_correspondencia': 'requer', 'requer_campo': 'requer',
    'obrigatorio_para': 'requer',
    'identifica': 'complementa', 'identificada_por': 'complementa',
    'identificado_por': 'complementa', 'identificado_com': 'complementa',
    'consultavel_por': 'usa', 'consulta': 'usa', 'referencia': 'usa',
    'le_de': 'usa', 'usa_formato': 'usa', 'utiliza_formato': 'usa',
    'presente_em': 'localizado_em', 'localiza_em': 'localizado_em',
    'entrega_em': 'fornece',
    'responsavel': 'responsavel_por',
    'tem_status': 'complementa', 'possui_id': 'complementa',
    'possui_acesso': 'complementa', 'possui_estilo': 'complementa',
    'possui_regra': 'complementa', 'possui_pedido': 'complementa',
}


def run():
    from app import create_app, db
    from sqlalchemy import text as sql_text

    app = create_app()
    with app.app_context():
        # ── BEFORE ──
        stats_before = db.session.execute(sql_text("""
            SELECT
                COUNT(DISTINCT relation_type) as tipos_unicos,
                COUNT(*) as total_relacoes,
                COUNT(*) FILTER (WHERE relation_type = 'co_occurs') as co_occurs
            FROM agent_memory_entity_relations
        """)).mappings().first()

        entity_before = db.session.execute(sql_text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE entity_type = 'regra') as tipo_regra
            FROM agent_memory_entities
        """)).mappings().first()

        print(f"=== ANTES ===")
        print(f"  Tipos de relação únicos: {stats_before['tipos_unicos']}")
        print(f"  Total relações: {stats_before['total_relacoes']}")
        print(f"  co_occurs: {stats_before['co_occurs']}")
        print(f"  Entidades 'regra': {entity_before['tipo_regra']}/{entity_before['total']}")

        # ── PARTE 1: Normalizar tipos de relação ──
        # Obter todos os tipos existentes
        existing_types = db.session.execute(sql_text("""
            SELECT relation_type, COUNT(*) as cnt
            FROM agent_memory_entity_relations
            WHERE relation_type != 'co_occurs'
            GROUP BY relation_type
            ORDER BY cnt DESC
        """)).mappings().all()

        mapped = 0
        discarded = 0
        for row in existing_types:
            old_type = row['relation_type']
            new_type = RELATION_MAP.get(old_type)

            if new_type == old_type:
                continue  # Já canônico
            elif new_type is not None:
                # Tentar UPDATE, mas pode dar conflito de unique constraint
                # (mesmo source_id, target_id, novo relation_type já existe)
                # Nesses casos, deletar a relação antiga (merge implícito via weight)
                try:
                    db.session.execute(sql_text("""
                        UPDATE agent_memory_entity_relations
                        SET relation_type = :new_type
                        WHERE relation_type = :old_type
                        AND NOT EXISTS (
                            SELECT 1 FROM agent_memory_entity_relations r2
                            WHERE r2.source_entity_id = agent_memory_entity_relations.source_entity_id
                            AND r2.target_entity_id = agent_memory_entity_relations.target_entity_id
                            AND r2.relation_type = :new_type
                        )
                    """), {"old_type": old_type, "new_type": new_type})

                    # Deletar restantes (que teriam conflito unique)
                    db.session.execute(sql_text("""
                        DELETE FROM agent_memory_entity_relations
                        WHERE relation_type = :old_type
                    """), {"old_type": old_type})

                    mapped += row['cnt']
                    print(f"  [{row['cnt']:3d}] {old_type} → {new_type}")
                except Exception as e:
                    print(f"  ERRO ao mapear {old_type}: {e}")
            else:
                # Não mapeável → descartar
                db.session.execute(sql_text("""
                    DELETE FROM agent_memory_entity_relations
                    WHERE relation_type = :old_type
                """), {"old_type": old_type})
                discarded += row['cnt']
                print(f"  [{row['cnt']:3d}] {old_type} → DESCARTADO")

        print(f"\n  Mapeadas: {mapped} relações")
        print(f"  Descartadas: {discarded} relações")

        # ── PARTE 2: Mudar entidades 'regra' para 'conceito' ──
        result = db.session.execute(sql_text("""
            UPDATE agent_memory_entities
            SET entity_type = 'conceito'
            WHERE entity_type = 'regra'
        """))
        renamed = result.rowcount
        print(f"\n  Entidades 'regra' → 'conceito': {renamed}")

        db.session.commit()

        # ── AFTER ──
        stats_after = db.session.execute(sql_text("""
            SELECT
                COUNT(DISTINCT relation_type) as tipos_unicos,
                COUNT(*) as total_relacoes
            FROM agent_memory_entity_relations
        """)).mappings().first()

        print(f"\n=== APOS ===")
        print(f"  Tipos de relação únicos: {stats_after['tipos_unicos']}")
        print(f"  Total relações: {stats_after['total_relacoes']}")
        print(f"\nMigration concluída com sucesso.")


if __name__ == '__main__':
    run()

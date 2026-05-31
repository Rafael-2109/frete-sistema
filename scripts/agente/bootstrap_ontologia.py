#!/usr/bin/env python3
"""
Bootstrap de ontologia canônica no Knowledge Graph.

Cria nós canônicos de negócio (produto/transportadora/cliente) com user_id=0
(escopo empresa) a partir das tabelas-mestre do sistema de fretes.

CUSTO: ZERO de API — INSERT idempotente via ON CONFLICT, sem Voyage.
FLAG: exige AGENT_ONTOLOGY=true OU --force para escrita real.
      --dry-run é sempre permitido (conta, NÃO escreve).

Uso:
    source .venv/bin/activate

    # Preview — o que seria inserido (não escreve):
    python scripts/agente/bootstrap_ontologia.py --dry-run

    # Escrita real via variável de ambiente:
    AGENT_ONTOLOGY=true python scripts/agente/bootstrap_ontologia.py

    # Escrita real forçada (ignora flag):
    python scripts/agente/bootstrap_ontologia.py --force

    # Tipo específico:
    python scripts/agente/bootstrap_ontologia.py --entity-type produto --dry-run

    # Smoke-test com limite de rows:
    python scripts/agente/bootstrap_ontologia.py --limit 10 --dry-run

NOTA de DEPLOY:
    Este script deve rodar no DEPLOY (pós-migração, pré-flag ON).
    Dados locais são TESTE — não refletem PROD.
    Antes de rodar em PROD para clientes, confirmar volume:
        SELECT COUNT(DISTINCT substring(regexp_replace(cnpj_cpf, '\\D', '', 'g') FROM 1 FOR 8))
        FROM carteira_principal
        WHERE cnpj_cpf IS NOT NULL;
    Volume esperado: ~2K-8K CNPJ raiz (trivial — sem risco de rate-limit).
"""
import argparse
import os
import sys

# Setup sys.path para imports do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Bootstrap ontologia canônica no KG (nós empresa user_id=0).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Conta entidades a inserir, NÃO escreve no DB. Sempre permitido.",
    )
    parser.add_argument(
        "--entity-type",
        choices=["cliente", "produto", "transportadora"],
        default=None,
        help="Tipo específico a bootstrapar (default: todos os 3 tipos).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita o número de rows por tabela (útil para smoke-test).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Força escrita mesmo sem AGENT_ONTOLOGY=true (bypass da flag).",
    )
    return parser.parse_args()


def main():
    args = _parse_args()

    # --- Guard: exige flag ou --force para escrita real ---
    use_ontology = os.getenv("AGENT_ONTOLOGY", "false").lower() == "true"
    write_allowed = args.dry_run or use_ontology or args.force

    if not write_allowed:
        print(
            "ERROR: Escrita bloqueada. Use --dry-run para preview, "
            "--force para forçar, ou defina AGENT_ONTOLOGY=true.",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Imports do app (após sys.path) ---
    from app import create_app, db
    from app.agente.services.ontology_bootstrap import (
        _ENTITY_SOURCE_MAP,
        _read_tabela,
        bootstrap_entities,
    )

    app = create_app()
    with app.app_context():
        engine = db.engine

        types_to_run = (
            [args.entity_type] if args.entity_type
            else list(_ENTITY_SOURCE_MAP.keys())
        )

        total = 0
        with engine.connect() as conn:
            for entity_type in types_to_run:
                print(f"\n[{entity_type}] Lendo tabela-mestre...", end=" ", flush=True)
                rows = _read_tabela(entity_type, conn, limit=args.limit)
                print(f"{len(rows)} rows encontradas.")

                if args.dry_run:
                    # Contar sem escrever
                    cfg = _ENTITY_SOURCE_MAP[entity_type]
                    key_f = cfg["key_field"]
                    name_f = cfg["name_field"]
                    will_insert = sum(
                        1 for r in rows
                        if r.get(key_f) and r.get(name_f)
                           and str(r[key_f]).strip() and str(r[name_f]).strip()
                    )
                    print(f"  [DRY-RUN] Seriam inseridas/atualizadas: {will_insert} entidades (user_id=0)")
                    total += will_insert
                else:
                    n = bootstrap_entities(entity_type, rows, conn)
                    print(f"  [OK] {n} entidades inseridas/atualizadas (user_id=0)")
                    total += n

            if not args.dry_run:
                conn.commit()

        mode = "DRY-RUN" if args.dry_run else "REAL"
        print(f"\n=== Bootstrap {mode} concluído — total: {total} entidades ===")


if __name__ == "__main__":
    main()

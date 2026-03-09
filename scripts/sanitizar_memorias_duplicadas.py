"""
Script one-shot: sanitiza memórias empresa duplicadas identificadas pelo Agent SDK.

Uso:
    python scripts/sanitizar_memorias_duplicadas.py              # dry-run (padrão)
    python scripts/sanitizar_memorias_duplicadas.py --execute    # executa deleção

Contexto:
    Após fix de dedup (Bugs 1-3 do save_memory), o Agent SDK identificou
    memórias empresa redundantes que já existem com conteúdo melhor em outros paths.
    Este script remove as duplicatas conhecidas.
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Paths empresa redundantes a deletar (identificados pelo Agent SDK em produção)
PATHS_TO_DELETE = [
    '/memories/empresa/termos/preset-do-claude-code.xml',
    '/memories/empresa/termos/agent-sdk.xml',
    '/memories/empresa/regras/o-agente-em-producao-render-nao-deve-a.xml',
    '/memories/empresa/regras/quando-o-agente-encontrar-um-problema-em.xml',
    '/memories/empresa/correcoes/o-agente-em-producao-eh-o-agent-sdk-ele.xml',
    '/memories/empresa/regras/a-rede-assai-opera-com-multiplas-lojas-p.xml',
    '/memories/empresa/correcoes/gilberto-nao-existe-foi-um-exemplo-inv.xml',
]


def main():
    parser = argparse.ArgumentParser(
        description='Sanitiza memórias empresa duplicadas'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Executa a deleção (padrão: dry-run)',
    )
    args = parser.parse_args()

    from app import create_app, db
    app = create_app()

    with app.app_context():
        from app.agente.models import AgentMemory

        deleted = []
        not_found = []
        errors = []

        for path in PATHS_TO_DELETE:
            try:
                mem = AgentMemory.get_by_path(0, path)  # user_id=0 = empresa
                if not mem:
                    not_found.append(path)
                    continue

                if args.execute:
                    # Cleanup embedding
                    try:
                        from sqlalchemy import text as sql_text
                        db.session.execute(sql_text("""
                            DELETE FROM agent_memory_embeddings
                            WHERE memory_id = :mid
                        """), {"mid": mem.id})
                    except Exception:
                        pass  # Embedding pode não existir

                    # Cleanup KG
                    try:
                        from app.agente.services.knowledge_graph_service import remove_memory_links
                        remove_memory_links(mem.id)
                    except Exception:
                        pass  # KG pode não existir

                    db.session.delete(mem)
                    deleted.append(path)
                else:
                    # Dry-run: apenas reportar
                    preview = (mem.content or '')[:80]
                    print(f"  [DELETAR] {path}")
                    print(f"            preview: {preview}...")
                    deleted.append(path)

            except Exception as e:
                errors.append((path, str(e)))

        if args.execute:
            db.session.commit()

        # Resumo
        mode = "EXECUTE" if args.execute else "DRY-RUN"
        print(f"\n{'='*60}")
        print(f"Sanitização de memórias duplicadas [{mode}]")
        print(f"{'='*60}")
        print(f"  Deletadas:       {len(deleted)}")
        print(f"  Não encontradas: {len(not_found)}")
        print(f"  Erros:           {len(errors)}")

        if not_found:
            print(f"\nPaths não encontrados (já deletados?):")
            for p in not_found:
                print(f"  - {p}")

        if errors:
            print(f"\nErros:")
            for p, e in errors:
                print(f"  - {p}: {e}")

        if not args.execute and deleted:
            print(f"\n⚠️  Modo dry-run. Execute com --execute para aplicar.")


if __name__ == '__main__':
    main()

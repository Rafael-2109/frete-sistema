"""
Limpeza de memorias residuais do auto_haiku (subagente Haiku deprecado).

O MemoryAgent foi removido em 2026-03-12. As memorias criadas por ele
permanecem no banco e sao injetadas no contexto do Agent web, causando
citacoes de "<source>auto_haiku</source>" para o usuario.

Auditoria (2026-03-12):
- 16 memorias em 6 usuarios (IDs: 1, 5, 18, 27, 36, 46)
- 0 tem conteudo misto (100% auto_haiku, nenhuma contribuicao MCP)
- 38 entradas auto_haiku no total

Acao: DELETE direto (sem rollback necessario — conteudo de baixa qualidade).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app import create_app, db
from app.agente.models import AgentMemory

# IDs auditados via MCP Render em 2026-03-12
TARGET_IDS = [9, 10, 14, 16, 17, 20, 22, 24, 25, 28, 31, 34, 35, 39, 40, 249]


def main():
    app = create_app()

    with app.app_context():
        # Verificacao pre-delete
        memories = AgentMemory.query.filter(AgentMemory.id.in_(TARGET_IDS)).all()

        print(f"Encontradas {len(memories)}/{len(TARGET_IDS)} memorias para remover:\n")

        for m in memories:
            has_auto_haiku = 'auto_haiku' in (m.content or '')
            status = 'OK' if has_auto_haiku else 'SKIP (sem auto_haiku!)'
            print(f"  [{status}] id={m.id} user={m.user_id} path={m.path}")

        # Confirmar
        to_delete = [m for m in memories if 'auto_haiku' in (m.content or '')]
        skipped = [m for m in memories if 'auto_haiku' not in (m.content or '')]

        if skipped:
            print(f"\n⚠ {len(skipped)} memorias NAO contem 'auto_haiku' — serao PRESERVADAS")

        if not to_delete:
            print("\nNenhuma memoria para deletar.")
            return

        print(f"\n{len(to_delete)} memorias serao deletadas.")

        if '--dry-run' in sys.argv:
            print("(dry-run — nenhuma alteracao feita)")
            return

        if '--confirm' not in sys.argv:
            print("Use --confirm para executar ou --dry-run para simular.")
            return

        # Delete
        for m in to_delete:
            db.session.delete(m)

        db.session.commit()
        print(f"\n{len(to_delete)} memorias removidas com sucesso.")


if __name__ == '__main__':
    main()

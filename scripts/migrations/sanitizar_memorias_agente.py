"""
Sanitização de memórias do agente — produção.

Aplica a mesma lógica de memory_mcp_tool.py:
1. Anti-injection (_sanitize_content)
2. Dedup por overlap coefficient (_text_overlap_check)
3. Remoção de memórias subset (info já coberta por memória mais completa)

Ações:
- REMOVE 4 memórias duplicadas/subset (empresa, user_id=0)
- VERIFICA injection em todas as memórias

Executar: python scripts/migrations/sanitizar_memorias_agente.py [--dry-run]
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app import create_app
from app import db
from app.agente.models import AgentMemory

# === Memórias para remoção (por path + user_id, independente de ID) ===
# Cada entrada: (user_id, path_to_remove, motivo, canonical_path)
MEMORIAS_REMOVER = [
    # Grupo 1: Teams processing — operadores-do-teams-bot é superset
    (0, "/memories/empresa/regras/pedidos-de-separacao-feitos-via-teams-de.xml",
     "subset: 'processados imediatamente via Teams' já coberto por operadores-do-teams-bot",
     "/memories/empresa/regras/operadores-do-teams-bot-possuem-user-id.xml"),

    (0, "/memories/empresa/regras/elaine-possui-dois-cadastros-no-sistema.xml",
     "subset: 'Elaine dois cadastros' já mencionado em operadores-do-teams-bot",
     "/memories/empresa/regras/operadores-do-teams-bot-possuem-user-id.xml"),

    # Grupo 2: One-shot vs recorrente — avaliar-se-o-comando é a melhor formulação
    (0, "/memories/empresa/correcoes/a-instancia-e-especifica-mas-a-necessid.xml",
     "duplicata: mesma correção com exemplos específicos, coberta por avaliar-se-o-comando",
     "/memories/empresa/correcoes/avaliar-se-o-comando-representa-um-proce.xml"),

    (0, "/memories/empresa/regras/uma-necessidade-operacional-pode-se-repe.xml",
     "duplicata: mesma lição expressa como regra, coberta por avaliar-se-o-comando",
     "/memories/empresa/correcoes/avaliar-se-o-comando-representa-um-proce.xml"),
]


def main():
    dry_run = '--dry-run' in sys.argv

    app = create_app()
    with app.app_context():
        print("=" * 60)
        print(f"SANITIZAÇÃO DE MEMÓRIAS DO AGENTE {'(DRY-RUN)' if dry_run else '(PRODUÇÃO)'}")
        print("=" * 60)

        # === 1. Verificar injection em TODAS as memórias ===
        import re
        DANGEROUS_PATTERNS = [
            re.compile(r'(?i)ignore\s+(all\s+)?previous\s+instructions'),
            re.compile(r'(?i)ignore\s+rules?\s+(P\d|R\d)'),
            re.compile(r'(?i)you\s+(must|should|are)\s+now'),
            re.compile(r'(?i)new\s+instructions?:'),
            re.compile(r'(?i)system\s*prompt'),
            re.compile(r'(?i)override\s+rules?'),
            re.compile(r'(?i)act\s+as\s+if'),
            re.compile(r'(?i)disregard\s+(all\s+)?prior'),
            re.compile(r'(?i)forget\s+(everything|all|prior)'),
        ]

        # Paths com "system prompt" como conteúdo legítimo (falsos positivos)
        FALSE_POSITIVE_PATHS = {
            '/memories/user.xml',  # Perfil do Rafael menciona system prompt como parte do trabalho
        }

        all_memories = AgentMemory.query.filter_by(is_directory=False).all()
        print(f"\n📋 Total de memórias: {len(all_memories)}")

        print("\n📛 Verificação de prompt injection:")
        injection_count = 0
        for mem in all_memories:
            if not mem.content:
                continue
            if mem.path in FALSE_POSITIVE_PATHS:
                continue
            for pattern in DANGEROUS_PATTERNS:
                if pattern.search(mem.content):
                    injection_count += 1
                    print(f"  ⚠️  ID={mem.id} user={mem.user_id} path={mem.path}")
                    print(f"      Padrão: {pattern.pattern}")
                    break

        if injection_count == 0:
            print("  ✅ Nenhum padrão de injection detectado")
        else:
            print(f"  ⚠️  {injection_count} memória(s) com padrão suspeito (revisar manualmente)")

        # === 2. Verificar que as memórias canônicas existem ===
        print("\n🔒 Verificação de memórias canônicas:")
        canonical_paths = set(item[3] for item in MEMORIAS_REMOVER)
        for cpath in canonical_paths:
            canonical = AgentMemory.query.filter_by(
                user_id=0, path=cpath, is_directory=False
            ).first()
            if canonical:
                print(f"  ✅ {cpath} (ID={canonical.id})")
            else:
                print(f"  ❌ {cpath} NÃO EXISTE — abortando!")
                sys.exit(1)

        # === 3. Remover duplicatas ===
        print(f"\n🗑️  Remoção de {len(MEMORIAS_REMOVER)} memórias duplicadas/subset:")
        removed = 0
        for user_id, path_remove, motivo, canonical_path in MEMORIAS_REMOVER:
            mem = AgentMemory.query.filter_by(
                user_id=user_id, path=path_remove, is_directory=False
            ).first()

            if not mem:
                print(f"  ⚠️  {path_remove} já não existe (skip)")
                continue

            print(f"  {'[DRY-RUN] ' if dry_run else ''}Removendo ID={mem.id}")
            print(f"    Path: {mem.path}")
            print(f"    Motivo: {motivo}")

            if not dry_run:
                db.session.delete(mem)
                removed += 1

        if not dry_run and removed > 0:
            db.session.commit()
            print(f"\n✅ {removed} memórias removidas com sucesso")
        elif dry_run:
            print(f"\n📊 DRY-RUN: {len(MEMORIAS_REMOVER)} memórias seriam removidas")
        else:
            print("\n✅ Nenhuma ação necessária")

        # === 4. Resumo final ===
        remaining = AgentMemory.query.filter_by(is_directory=False).count()
        print(f"\n📋 Memórias restantes: {remaining}")
        print("\nResumo por user_id:")
        from sqlalchemy import func
        stats = db.session.query(
            AgentMemory.user_id,
            func.count(AgentMemory.id)
        ).filter_by(is_directory=False).group_by(AgentMemory.user_id).all()
        for uid, count in sorted(stats):
            print(f"  user_id={uid}: {count} memórias")


if __name__ == '__main__':
    main()

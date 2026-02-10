"""
Diagnóstico: Tags não exibindo em lista_pedidos.html
Data: 2026-02-10
Descrição: Verifica se a VIEW pedidos tem a coluna tags_pedido
           e se a tabela separacao tem dados preenchidos.

Executar:
    source .venv/bin/activate
    python scripts/diagnostico_tags_lista_pedidos.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def diagnosticar():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("DIAGNÓSTICO: Tags em lista_pedidos.html")
        print("=" * 60)

        # 1. Verificar se VIEW pedidos tem coluna tags_pedido
        print("\n📋 1. Verificando coluna tags_pedido na VIEW pedidos...")
        try:
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'pedidos'
                AND column_name = 'tags_pedido'
            """))
            row = result.fetchone()
            if row:
                print("   ✅ VIEW pedidos TEM a coluna tags_pedido")
                view_ok = True
            else:
                print("   ❌ VIEW pedidos NÃO tem a coluna tags_pedido")
                print("   ➡️  Ação: Executar scripts/migrations/add_tags_pedido_view_pedidos.sql")
                view_ok = False
        except Exception as e:
            print(f"   ❌ Erro ao verificar VIEW: {e}")
            view_ok = False

        # 2. Verificar separações com tags_pedido preenchido
        print("\n📋 2. Verificando separacao.tags_pedido...")
        try:
            result = db.session.execute(text("""
                SELECT
                    count(*) AS total,
                    count(tags_pedido) AS com_tags,
                    count(*) - count(tags_pedido) AS sem_tags
                FROM separacao
            """))
            row = result.fetchone()
            total, com_tags, sem_tags = row[0], row[1], row[2]
            print(f"   Total de separações: {total}")
            print(f"   Com tags_pedido:     {com_tags}")
            print(f"   Sem tags_pedido:     {sem_tags}")
            if com_tags == 0:
                print("   ❌ Nenhuma separação tem tags_pedido preenchido")
                print("   ➡️  Ação: Executar scripts/migrations/atualizar_tags_separacoes_existentes.py")
                sep_ok = False
            elif sem_tags > 0:
                print(f"   ⚠️  {sem_tags} separações ainda sem tags (podem não ter tags na carteira)")
                sep_ok = True
            else:
                print("   ✅ Todas as separações têm tags_pedido")
                sep_ok = True
        except Exception as e:
            print(f"   ❌ Erro ao verificar separações: {e}")
            sep_ok = False

        # 3. Verificar CarteiraPrincipal com tags
        print("\n📋 3. Verificando carteira_principal.tags_pedido...")
        try:
            result = db.session.execute(text("""
                SELECT
                    count(*) AS total,
                    count(tags_pedido) AS com_tags,
                    count(DISTINCT CASE WHEN tags_pedido IS NOT NULL THEN num_pedido END) AS pedidos_com_tags
                FROM carteira_principal
            """))
            row = result.fetchone()
            total, com_tags, pedidos_com_tags = row[0], row[1], row[2]
            print(f"   Total de registros:       {total}")
            print(f"   Com tags_pedido:          {com_tags}")
            print(f"   Pedidos únicos com tags:  {pedidos_com_tags}")
        except Exception as e:
            print(f"   ❌ Erro ao verificar carteira: {e}")

        # 4. Se VIEW OK, verificar se dados aparecem
        if view_ok:
            print("\n📋 4. Verificando dados na VIEW pedidos...")
            try:
                result = db.session.execute(text("""
                    SELECT
                        count(*) AS total,
                        count(tags_pedido) AS com_tags
                    FROM pedidos
                """))
                row = result.fetchone()
                total, com_tags = row[0], row[1]
                print(f"   Total na VIEW:      {total}")
                print(f"   Com tags na VIEW:   {com_tags}")
                if com_tags > 0:
                    print("   ✅ Tags aparecem na VIEW pedidos!")
                else:
                    print("   ⚠️  VIEW existe mas nenhum pedido com tags")
                    print("   ➡️  Ação: Executar backfill em separacoes primeiro")
            except Exception as e:
                print(f"   ❌ Erro ao consultar VIEW: {e}")

        # 5. Amostra de tags
        if view_ok:
            print("\n📋 5. Amostra de pedidos com tags na VIEW...")
            try:
                result = db.session.execute(text("""
                    SELECT num_pedido, tags_pedido
                    FROM pedidos
                    WHERE tags_pedido IS NOT NULL
                    LIMIT 5
                """))
                rows = result.fetchall()
                if rows:
                    for r in rows:
                        print(f"   Pedido {r[0]}: {r[1]}")
                else:
                    print("   (nenhum pedido com tags encontrado)")
            except Exception as e:
                print(f"   ❌ Erro: {e}")

        # Resumo
        print("\n" + "=" * 60)
        print("RESUMO DO DIAGNÓSTICO")
        print("=" * 60)
        if view_ok and sep_ok:
            print("✅ Tudo OK! Tags devem aparecer em lista_pedidos.html")
        else:
            print("❌ Ações necessárias:")
            if not view_ok:
                print("   1. Aplicar migration da VIEW:")
                print("      psql $DATABASE_URL < scripts/migrations/add_tags_pedido_view_pedidos.sql")
            if not sep_ok:
                print("   2. Executar backfill de separações:")
                print("      python scripts/migrations/atualizar_tags_separacoes_existentes.py")
        print("=" * 60)


if __name__ == '__main__':
    diagnosticar()

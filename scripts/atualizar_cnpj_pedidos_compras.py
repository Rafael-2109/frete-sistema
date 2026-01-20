"""
Script para atualizar CNPJ dos Pedidos de Compra existentes.

Problema identificado:
- 4.259 registros em pedido_compras têm raz_social mas CNPJ vazio
- O campo cnpj_fornecedor não estava sendo preenchido na sincronização anterior

Solução:
1. Buscar todos os partner_id únicos dos POs no Odoo
2. Buscar CNPJ de cada parceiro no Odoo
3. Atualizar registros locais com o CNPJ

Executar: python scripts/atualizar_cnpj_pedidos_compras.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.odoo.utils.connection import get_odoo_connection
from sqlalchemy import text


def buscar_partner_ids_sem_cnpj():
    """
    Busca registros sem CNPJ e agrupa por raz_social para identificar fornecedores.
    """
    result = db.session.execute(text("""
        SELECT DISTINCT raz_social
        FROM pedido_compras
        WHERE cnpj_fornecedor IS NULL
          AND raz_social IS NOT NULL
    """))

    return [row[0] for row in result]


def buscar_cnpj_por_nome_no_odoo(connection, nomes_fornecedores):
    """
    Busca CNPJ dos fornecedores pelo nome no Odoo.

    Retorna: Dict {raz_social: cnpj}
    """
    print(f"\n🔍 Buscando {len(nomes_fornecedores)} fornecedores no Odoo...")

    resultado = {}

    # Buscar em batches de 50 para não sobrecarregar
    batch_size = 50
    for i in range(0, len(nomes_fornecedores), batch_size):
        batch = nomes_fornecedores[i:i + batch_size]

        # Buscar parceiros pelo nome exato
        partners = connection.search_read(
            'res.partner',
            [('name', 'in', batch)],
            ['id', 'name', 'l10n_br_cnpj']
        )

        for p in partners:
            if p.get('l10n_br_cnpj'):
                resultado[p['name']] = p['l10n_br_cnpj']

        print(f"   Batch {i // batch_size + 1}: {len(partners)} encontrados")

    return resultado


def atualizar_pedidos(mapa_cnpj):
    """
    Atualiza os pedidos com o CNPJ encontrado.

    Args:
        mapa_cnpj: Dict {raz_social: cnpj}
    """
    print(f"\n📝 Atualizando pedidos com {len(mapa_cnpj)} CNPJs encontrados...")

    total_atualizado = 0

    for raz_social, cnpj in mapa_cnpj.items():
        result = db.session.execute(
            text("""
                UPDATE pedido_compras
                SET cnpj_fornecedor = :cnpj,
                    atualizado_em = NOW()
                WHERE raz_social = :raz_social
                  AND cnpj_fornecedor IS NULL
            """),
            {'cnpj': cnpj, 'raz_social': raz_social}
        )

        count = result.rowcount
        if count > 0:
            total_atualizado += count
            print(f"   ✅ {raz_social[:40]}... -> {cnpj} ({count} registros)")

    db.session.commit()
    return total_atualizado


def main():
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("ATUALIZAÇÃO DE CNPJ DOS PEDIDOS DE COMPRA")
        print("=" * 60)

        # Passo 1: Verificar situação atual
        result = db.session.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(cnpj_fornecedor) as com_cnpj,
                COUNT(*) - COUNT(cnpj_fornecedor) as sem_cnpj
            FROM pedido_compras
        """))
        row = result.fetchone()
        print(f"\n📊 Situação atual:")
        print(f"   Total de registros: {row[0]}")
        print(f"   Com CNPJ: {row[1]}")
        print(f"   Sem CNPJ: {row[2]}")

        if row[2] == 0:
            print("\n✅ Todos os registros já têm CNPJ!")
            return

        # Passo 2: Buscar fornecedores sem CNPJ
        nomes_fornecedores = buscar_partner_ids_sem_cnpj()
        print(f"\n🔍 Fornecedores únicos sem CNPJ: {len(nomes_fornecedores)}")

        if not nomes_fornecedores:
            print("   Nenhum fornecedor para atualizar.")
            return

        # Passo 3: Conectar ao Odoo usando get_odoo_connection()
        connection = get_odoo_connection()
        if not connection.authenticate():
            print("❌ Falha ao autenticar no Odoo")
            return

        print("✅ Autenticado no Odoo")

        # Passo 4: Buscar CNPJs no Odoo
        mapa_cnpj = buscar_cnpj_por_nome_no_odoo(connection, nomes_fornecedores)

        print(f"\n📋 CNPJs encontrados: {len(mapa_cnpj)}")
        print(f"   Fornecedores sem CNPJ no Odoo: {len(nomes_fornecedores) - len(mapa_cnpj)}")

        if not mapa_cnpj:
            print("\n⚠️ Nenhum CNPJ encontrado no Odoo!")
            return

        # Passo 5: Atualizar pedidos
        total_atualizado = atualizar_pedidos(mapa_cnpj)

        # Passo 6: Verificar resultado
        result = db.session.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(cnpj_fornecedor) as com_cnpj,
                COUNT(*) - COUNT(cnpj_fornecedor) as sem_cnpj
            FROM pedido_compras
        """))
        row = result.fetchone()

        print("\n" + "=" * 60)
        print("RESULTADO FINAL")
        print("=" * 60)
        print(f"   Total de registros: {row[0]}")
        print(f"   Com CNPJ: {row[1]}")
        print(f"   Sem CNPJ: {row[2]}")
        print(f"   Atualizados nesta execução: {total_atualizado}")


if __name__ == '__main__':
    main()

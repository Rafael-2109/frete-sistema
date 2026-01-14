"""
Migration: Limpar registros de CNPJs do grupo e CTe
===================================================

Remove registros importados indevidamente das tabelas:
- cadastro_primeira_compra
- divergencia_fiscal
- validacao_fiscal_dfe

Criterios de exclusao:
- CNPJs do grupo: 61.724.241 (Nacom) e 18.467.441 (Goya)
- CTe (Knowledge de Transporte)

Execute:
    source .venv/bin/activate && python scripts/migrations/limpar_registros_grupo.py

SQL para Render Shell (caso prefira executar manualmente):
    -- Remover registros de CNPJs do grupo
    DELETE FROM cadastro_primeira_compra WHERE cnpj_fornecedor LIKE '61724241%' OR cnpj_fornecedor LIKE '18467441%';
    DELETE FROM divergencia_fiscal WHERE cnpj_fornecedor LIKE '61724241%' OR cnpj_fornecedor LIKE '18467441%';
    DELETE FROM validacao_fiscal_dfe WHERE cnpj_fornecedor LIKE '61724241%' OR cnpj_fornecedor LIKE '18467441%';
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

# CNPJs do grupo a serem removidos (prefixos)
CNPJS_GRUPO = [
    '61724241',  # Nacom
    '18467441',  # Goya
]


def limpar_tabela(tabela: str, campo_cnpj: str = 'cnpj_fornecedor'):
    """Remove registros de CNPJs do grupo de uma tabela"""
    print(f"\n📋 Processando tabela: {tabela}")

    total_removidos = 0

    for prefixo in CNPJS_GRUPO:
        # Contar antes
        count_result = db.session.execute(text(f"""
            SELECT COUNT(*) FROM {tabela}
            WHERE {campo_cnpj} LIKE :prefixo
        """), {'prefixo': f'{prefixo}%'})
        count = count_result.scalar()

        if count > 0:
            # Deletar
            result = db.session.execute(text(f"""
                DELETE FROM {tabela}
                WHERE {campo_cnpj} LIKE :prefixo
            """), {'prefixo': f'{prefixo}%'})

            print(f"   - Removidos {count} registros com CNPJ {prefixo}%")
            total_removidos += count

    if total_removidos == 0:
        print(f"   ✓ Nenhum registro do grupo encontrado")

    return total_removidos


def verificar_cte_na_base():
    """Verifica se existem CTe na base (consultando Odoo)"""
    from app.odoo.utils.connection import get_odoo_connection

    print("\n📋 Verificando CTe na base...")

    # Buscar odoo_dfe_ids das tabelas locais
    result = db.session.execute(text("""
        SELECT DISTINCT odoo_dfe_id FROM cadastro_primeira_compra WHERE odoo_dfe_id IS NOT NULL
        UNION
        SELECT DISTINCT odoo_dfe_id FROM divergencia_fiscal WHERE odoo_dfe_id IS NOT NULL
    """))
    dfe_ids = [int(row[0]) for row in result.fetchall() if row[0]]

    if not dfe_ids:
        print("   ✓ Nenhum DFE encontrado nas tabelas locais")
        return []

    print(f"   Encontrados {len(dfe_ids)} DFE IDs distintos")

    # Conectar ao Odoo e verificar quais sao CTe
    odoo = get_odoo_connection()
    if not odoo.authenticate():
        print("   ❌ Falha na autenticacao com Odoo")
        return []

    # Buscar DFEs que sao CTe (is_cte=True)
    dfes_cte = odoo.search_read(
        'l10n_br_ciel_it_account.dfe',
        [
            ['id', 'in', dfe_ids],
            ['is_cte', '=', True]  # CTe (Conhecimento de Transporte)
        ],
        fields=['id', 'name', 'nfe_infnfe_emit_cnpj', 'nfe_infnfe_emit_xnome']
    )

    return dfes_cte


def limpar_cte(dfe_ids: list):
    """Remove registros de CTe das tabelas locais"""
    if not dfe_ids:
        return 0

    print(f"\n📋 Removendo CTe ({len(dfe_ids)} DFEs)...")

    total_removidos = 0

    # Converter para strings para comparacao
    dfe_ids_str = [str(dfe_id) for dfe_id in dfe_ids]

    for tabela in ['cadastro_primeira_compra', 'divergencia_fiscal', 'validacao_fiscal_dfe']:
        # Contar antes
        placeholders = ','.join([f':id{i}' for i in range(len(dfe_ids_str))])
        params = {f'id{i}': dfe_id for i, dfe_id in enumerate(dfe_ids_str)}

        count_result = db.session.execute(text(f"""
            SELECT COUNT(*) FROM {tabela}
            WHERE odoo_dfe_id IN ({placeholders})
        """), params)
        count = count_result.scalar()

        if count > 0:
            # Deletar
            db.session.execute(text(f"""
                DELETE FROM {tabela}
                WHERE odoo_dfe_id IN ({placeholders})
            """), params)

            print(f"   - {tabela}: {count} registros removidos")
            total_removidos += count

    return total_removidos


def executar_limpeza():
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("LIMPEZA: Remover registros de CNPJs do grupo e CTe")
            print("=" * 60)

            # 1. Limpar CNPJs do grupo
            print("\n[1/3] Limpando registros de CNPJs do grupo...")

            total_cnpj = 0
            total_cnpj += limpar_tabela('cadastro_primeira_compra')
            total_cnpj += limpar_tabela('divergencia_fiscal')
            total_cnpj += limpar_tabela('validacao_fiscal_dfe')

            db.session.commit()

            # 2. Verificar CTe
            print("\n[2/3] Verificando CTe no Odoo...")
            dfes_cte = verificar_cte_na_base()

            total_cte = 0
            if dfes_cte:
                print(f"   Encontrados {len(dfes_cte)} CTe:")
                for dfe in dfes_cte:
                    print(f"      - ID {dfe['id']}: {dfe['name']} ({dfe.get('nfe_infnfe_emit_xnome', 'N/A')})")

                # 3. Limpar CTe
                print("\n[3/3] Removendo CTe das tabelas...")
                dfe_ids = [dfe['id'] for dfe in dfes_cte]
                total_cte = limpar_cte(dfe_ids)

                db.session.commit()
            else:
                print("   ✓ Nenhum CTe encontrado")
                print("\n[3/3] Nada a remover")

            print("\n" + "=" * 60)
            print("✅ LIMPEZA CONCLUIDA!")
            print(f"   - CNPJs do grupo: {total_cnpj} registros removidos")
            print(f"   - CTe: {total_cte} registros removidos")
            print(f"   - TOTAL: {total_cnpj + total_cte} registros")
            print("=" * 60)

            # Verificacao final
            print("\n📋 Verificacao final - registros restantes:")

            for tabela in ['cadastro_primeira_compra', 'divergencia_fiscal']:
                result = db.session.execute(text(f"""
                    SELECT status, COUNT(*) as total
                    FROM {tabela}
                    GROUP BY status
                    ORDER BY total DESC
                """))
                print(f"\n   {tabela}:")
                for row in result.fetchall():
                    print(f"      - {row[0]}: {row[1]} registros")

        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_limpeza()

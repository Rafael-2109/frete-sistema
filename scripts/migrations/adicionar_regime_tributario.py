"""
Migration: Adicionar e popular campo regime_tributario
======================================================

Adiciona o campo regime_tributario (CRT da NF-e) nas tabelas:
- cadastro_primeira_compra
- divergencia_fiscal

Valores do CRT:
- 1 = Simples Nacional
- 2 = Simples Nacional - excesso sublimite
- 3 = Regime Normal (Lucro Real ou Presumido)

Execute:
    source .venv/bin/activate && python scripts/migrations/adicionar_regime_tributario.py

SQL para Render Shell:
    ALTER TABLE cadastro_primeira_compra ADD COLUMN IF NOT EXISTS regime_tributario VARCHAR(1);
    ALTER TABLE divergencia_fiscal ADD COLUMN IF NOT EXISTS regime_tributario VARCHAR(1);
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text
from app.odoo.utils.connection import get_odoo_connection


def buscar_crt_odoo(odoo, dfe_ids: list) -> dict:
    """
    Busca o CRT (Código de Regime Tributário) do Odoo para uma lista de DFE IDs.

    Modelo: l10n_br_ciel_it_account.dfe
    Campo: nfe_infnfe_emit_crt

    Returns:
        Dict[dfe_id -> regime_tributario (str)]
    """
    if not dfe_ids:
        return {}

    # Buscar DFEs no Odoo
    dfe_data = odoo.search_read(
        'l10n_br_ciel_it_account.dfe',
        [('id', 'in', dfe_ids)],
        ['id', 'nfe_infnfe_emit_crt']
    )

    resultado = {}
    for dfe in dfe_data:
        crt = dfe.get('nfe_infnfe_emit_crt')
        # Odoo retorna False quando vazio
        if crt and crt is not False:
            resultado[dfe['id']] = str(crt)

    return resultado


def popular_regime_tabela(tabela: str, odoo, db_session):
    """Popula regime_tributario para uma tabela específica"""
    print(f"\n📋 Processando tabela: {tabela}")

    # 1. Buscar IDs únicos de DFE que precisam de atualização
    result = db_session.execute(text(f"""
        SELECT DISTINCT odoo_dfe_id
        FROM {tabela}
        WHERE regime_tributario IS NULL
        AND odoo_dfe_id IS NOT NULL
    """))
    dfe_ids = [int(row[0]) for row in result.fetchall() if row[0]]

    if not dfe_ids:
        print(f"   ✓ Nenhum registro para atualizar")
        return 0

    print(f"   Encontrados {len(dfe_ids)} DFE IDs para buscar no Odoo")

    # 2. Buscar dados do Odoo
    dados_odoo = buscar_crt_odoo(odoo, dfe_ids)
    print(f"   Dados obtidos do Odoo: {len(dados_odoo)} DFEs com CRT")

    # 3. Atualizar registros no banco
    atualizados = 0
    for dfe_id, regime in dados_odoo.items():
        result = db_session.execute(text(f"""
            UPDATE {tabela}
            SET regime_tributario = :regime
            WHERE odoo_dfe_id = :dfe_id
            AND regime_tributario IS NULL
        """), {
            'regime': regime,
            'dfe_id': str(dfe_id)
        })
        atualizados += result.rowcount

    print(f"   ✓ {atualizados} registros atualizados")
    return atualizados


def executar_migration():
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRATION: Adicionar e popular regime_tributario")
            print("=" * 60)

            # 1. Adicionar coluna nas tabelas
            print("\n[1/4] Adicionando coluna regime_tributario...")

            db.session.execute(text("""
                ALTER TABLE cadastro_primeira_compra
                ADD COLUMN IF NOT EXISTS regime_tributario VARCHAR(1)
            """))
            print("   ✓ cadastro_primeira_compra")

            db.session.execute(text("""
                ALTER TABLE divergencia_fiscal
                ADD COLUMN IF NOT EXISTS regime_tributario VARCHAR(1)
            """))
            print("   ✓ divergencia_fiscal")

            db.session.commit()

            # 2. Conectar ao Odoo
            print("\n[2/4] Conectando ao Odoo...")
            odoo = get_odoo_connection()
            if not odoo.authenticate():
                print("   ❌ Falha na autenticação com Odoo")
                return
            print("   ✓ Conectado ao Odoo")

            # 3. Popular cadastro_primeira_compra
            print("\n[3/4] Processando cadastro_primeira_compra...")
            total_pc = popular_regime_tabela('cadastro_primeira_compra', odoo, db.session)

            # 4. Popular divergencia_fiscal
            print("\n[4/4] Processando divergencia_fiscal...")
            total_div = popular_regime_tabela('divergencia_fiscal', odoo, db.session)

            # Commit
            db.session.commit()

            print("\n" + "=" * 60)
            print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
            print(f"   - Primeira Compra: {total_pc} registros atualizados")
            print(f"   - Divergências: {total_div} registros atualizados")
            print("=" * 60)

            # Verificação final
            print("\n📋 Verificação - distribuição de regimes:")
            result = db.session.execute(text("""
                SELECT
                    regime_tributario,
                    CASE regime_tributario
                        WHEN '1' THEN 'Simples Nacional'
                        WHEN '2' THEN 'Simples Nacional (excesso)'
                        WHEN '3' THEN 'Regime Normal'
                        ELSE 'Não informado'
                    END as descricao,
                    COUNT(*) as total
                FROM cadastro_primeira_compra
                GROUP BY regime_tributario
                ORDER BY total DESC
            """))
            for row in result.fetchall():
                print(f"   {row[1]}: {row[2]} registros")

        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()

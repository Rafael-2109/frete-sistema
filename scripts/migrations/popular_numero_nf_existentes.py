"""
Migration: Popular campos numero_nf, serie_nf, uf_fornecedor em registros existentes
====================================================================================

Os registros existentes estão com numero_nf, serie_nf e uf_fornecedor vazios.
Esta migration busca os dados do Odoo (l10n_br_ciel_it_account.dfe) e popula os campos.

Execute:
    source .venv/bin/activate && python scripts/migrations/popular_numero_nf_existentes.py

SQL para verificar depois:
    SELECT id, odoo_dfe_id, numero_nf, serie_nf, uf_fornecedor FROM cadastro_primeira_compra LIMIT 10;
    SELECT id, odoo_dfe_id, numero_nf, serie_nf, uf_fornecedor FROM divergencia_fiscal LIMIT 10;
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text
from app.odoo.utils.connection import get_odoo_connection


def buscar_dados_nf_odoo(odoo, dfe_ids: list) -> dict:
    """
    Busca numero_nf, serie_nf e uf_fornecedor do Odoo para uma lista de DFE IDs.

    Modelo: l10n_br_ciel_it_account.dfe (DFE = Documento Fiscal Eletrônico)

    Returns:
        Dict[dfe_id -> {'numero_nf': str, 'serie_nf': str, 'uf_fornecedor': str}]
    """
    if not dfe_ids:
        return {}

    # Buscar DFEs no Odoo - MODELO CORRETO: l10n_br_ciel_it_account.dfe
    dfe_data = odoo.search_read(
        'l10n_br_ciel_it_account.dfe',
        [('id', 'in', dfe_ids)],
        ['id', 'nfe_infnfe_ide_nnf', 'nfe_infnfe_ide_serie', 'nfe_infnfe_emit_uf', 'partner_id']
    )

    resultado = {}
    partner_ids = []

    for dfe in dfe_data:
        resultado[dfe['id']] = {
            'numero_nf': str(dfe.get('nfe_infnfe_ide_nnf') or '') if dfe.get('nfe_infnfe_ide_nnf') else None,
            'serie_nf': str(dfe.get('nfe_infnfe_ide_serie') or '') if dfe.get('nfe_infnfe_ide_serie') else None,
            'uf_fornecedor': str(dfe.get('nfe_infnfe_emit_uf') or '') if dfe.get('nfe_infnfe_emit_uf') else None,
            'cidade_fornecedor': None,  # Será buscado do partner
            'partner_id': dfe.get('partner_id')[0] if dfe.get('partner_id') else None
        }
        if dfe.get('partner_id'):
            partner_ids.append(dfe['partner_id'][0])

    # Buscar cidade dos partners (campo brasileiro l10n_br_municipio_id)
    if partner_ids:
        partners = odoo.search_read(
            'res.partner',
            [('id', 'in', list(set(partner_ids)))],
            ['id', 'l10n_br_municipio_id']
        )
        # l10n_br_municipio_id retorna [id, "Nome (UF)"] - Ex: [5570, "Brasília (DF)"]
        partner_city_map = {}
        for p in partners:
            municipio = p.get('l10n_br_municipio_id')
            if municipio and isinstance(municipio, (list, tuple)) and len(municipio) > 1:
                nome = municipio[1].split('(')[0].strip() if '(' in municipio[1] else municipio[1]
                partner_city_map[p['id']] = nome
            else:
                partner_city_map[p['id']] = None

        # Atribuir cidade aos DFEs
        for _, dados in resultado.items():
            partner_id = dados.pop('partner_id', None)
            if partner_id and partner_id in partner_city_map:
                dados['cidade_fornecedor'] = partner_city_map.get(partner_id)

    return resultado


def popular_tabela(tabela: str, odoo, db_session):
    """Popula numero_nf, serie_nf, uf_fornecedor e cidade_fornecedor para uma tabela específica"""
    print(f"\n📋 Processando tabela: {tabela}")

    # 1. Buscar IDs únicos de DFE que precisam de atualização
    result = db_session.execute(text(f"""
        SELECT DISTINCT odoo_dfe_id
        FROM {tabela}
        WHERE (numero_nf IS NULL OR uf_fornecedor IS NULL)
        AND odoo_dfe_id IS NOT NULL
    """))
    dfe_ids = [row[0] for row in result.fetchall()]

    if not dfe_ids:
        print(f"   ✓ Nenhum registro para atualizar")
        return 0

    print(f"   Encontrados {len(dfe_ids)} DFE IDs para buscar no Odoo")

    # 2. Buscar dados do Odoo
    dados_odoo = buscar_dados_nf_odoo(odoo, dfe_ids)
    print(f"   Dados obtidos do Odoo: {len(dados_odoo)} DFEs")

    # 3. Atualizar registros no banco
    atualizados = 0
    for dfe_id, dados in dados_odoo.items():
        numero_nf = dados.get('numero_nf')
        serie_nf = dados.get('serie_nf')
        uf_fornecedor = dados.get('uf_fornecedor')
        cidade_fornecedor = dados.get('cidade_fornecedor')

        # Tratar cidade_fornecedor = False (Odoo retorna False quando vazio)
        if cidade_fornecedor is False:
            cidade_fornecedor = None

        if numero_nf or uf_fornecedor:
            result = db_session.execute(text(f"""
                UPDATE {tabela}
                SET numero_nf = COALESCE(:numero_nf, numero_nf),
                    serie_nf = COALESCE(:serie_nf, serie_nf),
                    uf_fornecedor = COALESCE(:uf_fornecedor, uf_fornecedor),
                    cidade_fornecedor = COALESCE(:cidade_fornecedor, cidade_fornecedor)
                WHERE odoo_dfe_id = :dfe_id
                AND (numero_nf IS NULL OR uf_fornecedor IS NULL)
            """), {
                'numero_nf': numero_nf,
                'serie_nf': serie_nf,
                'uf_fornecedor': uf_fornecedor,
                'cidade_fornecedor': cidade_fornecedor,
                'dfe_id': str(dfe_id)  # Converter para string (campo é VARCHAR)
            })
            atualizados += result.rowcount

    print(f"   ✓ {atualizados} registros atualizados")
    return atualizados


def executar_migration():
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRATION: Popular numero_nf e serie_nf nas tabelas de validação")
            print("=" * 60)

            # Conectar ao Odoo
            print("\n[1/3] Conectando ao Odoo...")
            odoo = get_odoo_connection()
            if not odoo.authenticate():
                print("   ❌ Falha na autenticação com Odoo")
                return
            print("   ✓ Conectado ao Odoo")

            # Popular cadastro_primeira_compra
            print("\n[2/3] Processando cadastro_primeira_compra...")
            total_pc = popular_tabela('cadastro_primeira_compra', odoo, db.session)

            # Popular divergencia_fiscal
            print("\n[3/3] Processando divergencia_fiscal...")
            total_div = popular_tabela('divergencia_fiscal', odoo, db.session)

            # Commit
            db.session.commit()

            print("\n" + "=" * 60)
            print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
            print(f"   - Primeira Compra: {total_pc} registros atualizados")
            print(f"   - Divergências: {total_div} registros atualizados")
            print("=" * 60)

            # Verificação final
            print("\n📋 Verificação final - cadastro_primeira_compra:")
            result = db.session.execute(text("""
                SELECT odoo_dfe_id, numero_nf, serie_nf, COUNT(*) as total
                FROM cadastro_primeira_compra
                GROUP BY odoo_dfe_id, numero_nf, serie_nf
                ORDER BY odoo_dfe_id
                LIMIT 10
            """))
            for row in result.fetchall():
                print(f"   DFE {row[0]}: NF {row[1]} Série {row[2]} ({row[3]} itens)")

        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()

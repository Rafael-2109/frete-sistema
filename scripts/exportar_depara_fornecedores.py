"""
Exportar De-Para de Fornecedores (product.supplierinfo) do Odoo
===============================================================

Gera arquivo Excel com todos os registros de De-Para de fornecedores,
separados em duas abas:
- COM_CODIGO: Registros com código do fornecedor preenchido
- SEM_CODIGO: Registros sem código do fornecedor (pendentes)

Execute:
    source .venv/bin/activate && python scripts/exportar_depara_fornecedores.py

Saída:
    exports/depara_fornecedores_YYYYMMDD_HHMMSS.xlsx
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from app import create_app
from app.odoo.utils.connection import get_odoo_connection


def buscar_cnpjs_fornecedores(odoo, partner_ids: list) -> dict:
    """Busca CNPJs dos fornecedores em lote"""
    if not partner_ids:
        return {}

    partners = odoo.search_read(
        'res.partner',
        [['id', 'in', list(set(partner_ids))]],
        ['id', 'l10n_br_cnpj'],
        limit=10000
    )

    return {p['id']: p.get('l10n_br_cnpj') or '' for p in partners}


def buscar_codigos_produtos(odoo, product_tmpl_ids: list) -> dict:
    """Busca códigos internos dos produtos em lote"""
    if not product_tmpl_ids:
        return {}

    produtos = odoo.search_read(
        'product.template',
        [['id', 'in', list(set(product_tmpl_ids))]],
        ['id', 'default_code', 'name'],
        limit=10000
    )

    return {
        p['id']: {
            'default_code': p.get('default_code') or '',
            'name': p.get('name') or ''
        }
        for p in produtos
    }


def exportar_depara():
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("EXPORTAR DE-PARA DE FORNECEDORES")
            print("=" * 60)

            # 1. Conectar ao Odoo
            print("\n[1/5] Conectando ao Odoo...")
            odoo = get_odoo_connection()
            if not odoo.authenticate():
                print("   ❌ Falha na autenticação com Odoo")
                return

            print("   ✓ Conectado ao Odoo")

            # 2. Buscar todos os registros de product.supplierinfo
            print("\n[2/5] Buscando registros de product.supplierinfo...")
            campos = [
                'id', 'partner_id', 'product_tmpl_id', 'product_id',
                'product_code', 'product_name', 'product_uom',
                'fator_un', 'price', 'delay', 'min_qty', 'codigo_barras'
            ]

            registros = odoo.search_read(
                'product.supplierinfo',
                [],
                campos,
                limit=15000
            )

            print(f"   ✓ Encontrados {len(registros)} registros")

            # 3. Buscar dados complementares em lote
            print("\n[3/5] Buscando dados complementares...")

            # Coletar IDs
            partner_ids = [r['partner_id'][0] for r in registros if r.get('partner_id')]
            product_tmpl_ids = [r['product_tmpl_id'][0] for r in registros if r.get('product_tmpl_id')]

            # Buscar em lote
            cnpjs = buscar_cnpjs_fornecedores(odoo, partner_ids)
            print(f"   ✓ CNPJs: {len(cnpjs)} fornecedores")

            codigos_produtos = buscar_codigos_produtos(odoo, product_tmpl_ids)
            print(f"   ✓ Códigos: {len(codigos_produtos)} produtos")

            # 4. Processar e separar dados
            print("\n[4/5] Processando dados...")

            com_codigo = []
            sem_codigo = []

            for r in registros:
                # Extrair dados do registro
                partner_id = r['partner_id'][0] if r.get('partner_id') else None
                partner_nome = r['partner_id'][1] if r.get('partner_id') else ''
                partner_cnpj = cnpjs.get(partner_id, '') if partner_id else ''

                product_tmpl_id = r['product_tmpl_id'][0] if r.get('product_tmpl_id') else None
                produto_info = codigos_produtos.get(product_tmpl_id, {}) if product_tmpl_id else {}
                nosso_codigo = produto_info.get('default_code', '')
                nosso_produto = produto_info.get('name', '')

                # Tratar product_tmpl_id que pode conter nome junto
                if r.get('product_tmpl_id') and isinstance(r['product_tmpl_id'], (list, tuple)) and len(r['product_tmpl_id']) > 1:
                    if not nosso_produto:
                        nosso_produto = r['product_tmpl_id'][1]

                um_fornecedor = r['product_uom'][1] if r.get('product_uom') else ''
                fator_un = r.get('fator_un', 1.0)
                preco = r.get('price', 0)
                lead_time = r.get('delay', 0)
                min_qty = r.get('min_qty', 0)
                codigo_barras = r.get('codigo_barras') or ''

                codigo_fornecedor = r.get('product_code') or ''
                descricao_fornecedor = r.get('product_name') or ''

                # Tratar False do Odoo
                if codigo_fornecedor is False:
                    codigo_fornecedor = ''
                if descricao_fornecedor is False:
                    descricao_fornecedor = ''

                linha = {
                    'Fornecedor ID': partner_id,
                    'Fornecedor Nome': partner_nome,
                    'Fornecedor CNPJ': partner_cnpj,
                    'Código Fornecedor': codigo_fornecedor,
                    'Descrição Fornecedor': descricao_fornecedor,
                    'Nosso Código': nosso_codigo,
                    'Nosso Produto': nosso_produto,
                    'UM Fornecedor': um_fornecedor,
                    'Fator Conversão': fator_un,
                    'Preço': preco,
                    'Lead Time (dias)': lead_time,
                    'Qtd Mínima': min_qty,
                    'Código Barras': codigo_barras
                }

                if codigo_fornecedor:
                    com_codigo.append(linha)
                else:
                    sem_codigo.append(linha)

            print(f"   ✓ COM código: {len(com_codigo)} registros")
            print(f"   ✓ SEM código: {len(sem_codigo)} registros")

            # 5. Gerar Excel
            print("\n[5/5] Gerando arquivo Excel...")

            # Criar diretório exports se não existir
            exports_dir = os.path.join(os.path.dirname(__file__), '..', 'exports')
            os.makedirs(exports_dir, exist_ok=True)

            # Nome do arquivo com timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            arquivo = os.path.join(exports_dir, f'depara_fornecedores_{timestamp}.xlsx')

            # Criar DataFrames
            df_com_codigo = pd.DataFrame(com_codigo)
            df_sem_codigo = pd.DataFrame(sem_codigo)

            # Ordenar por fornecedor e produto
            if not df_com_codigo.empty:
                df_com_codigo = df_com_codigo.sort_values(['Fornecedor Nome', 'Nosso Código'])

            if not df_sem_codigo.empty:
                df_sem_codigo = df_sem_codigo.sort_values(['Fornecedor Nome', 'Nosso Código'])

            # Salvar Excel com duas abas
            with pd.ExcelWriter(arquivo, engine='openpyxl') as writer:
                df_com_codigo.to_excel(writer, sheet_name='COM_CODIGO', index=False)
                df_sem_codigo.to_excel(writer, sheet_name='SEM_CODIGO', index=False)

            print(f"   ✓ Arquivo salvo: {arquivo}")

            print("\n" + "=" * 60)
            print("✅ EXPORTAÇÃO CONCLUÍDA!")
            print(f"   - COM código: {len(com_codigo)} registros")
            print(f"   - SEM código: {len(sem_codigo)} registros")
            print(f"   - TOTAL: {len(registros)} registros")
            print(f"\n📁 Arquivo: {arquivo}")
            print("=" * 60)

            return arquivo

        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == '__main__':
    exportar_depara()

"""
Script de Teste - product.product no Odoo
==========================================

Objetivo: Identificar campos que indicam produtos relacionados à produção
para filtrar importações de requisições/pedidos/recebimentos.

Autor: Sistema de Fretes
Data: 31/10/2025
"""

import sys
import os
import json
from datetime import datetime

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.odoo.utils.connection import get_odoo_connection
from app.producao.models import CadastroPalletizacao
from app import create_app

def formatar_json(data):
    """Formata JSON de forma legível"""
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)

def testar_campos_product_product(conn):
    """
    Testa campos disponíveis em product.product
    """
    print("=" * 80)
    print("🔍 TESTANDO CAMPOS DE product.product")
    print("=" * 80)

    try:
        # Buscar 1 produto de exemplo
        print("\n📦 Buscando 1 produto de exemplo...")

        produtos = conn.search_read(
            'product.product',
            [],
            fields=[
                'id', 'name', 'default_code',
                'type', 'categ_id', 'active',
                'purchase_ok', 'sale_ok',
                'detailed_type'
            ],
            limit=5
        )

        if produtos:
            print(f"\n✅ Encontrados {len(produtos)} produtos:")
            for prod in produtos:
                print(f"\n   ID: {prod['id']}")
                print(f"   Name: {prod.get('name', 'N/A')}")
                print(f"   Default Code: {prod.get('default_code', 'N/A')}")
                print(f"   Type: {prod.get('type', 'N/A')}")
                print(f"   Detailed Type: {prod.get('detailed_type', 'N/A')}")
                print(f"   Category: {prod.get('categ_id', 'N/A')}")
                print(f"   Purchase OK: {prod.get('purchase_ok', 'N/A')}")
                print(f"   Sale OK: {prod.get('sale_ok', 'N/A')}")
                print("   " + "-" * 70)

            return produtos

        return None

    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return None

def testar_filtro_purchase_ok(conn):
    """
    Testa filtro purchase_ok=True (produtos compráveis)
    """
    print("\n" + "=" * 80)
    print("🛒 TESTANDO FILTRO purchase_ok=True")
    print("=" * 80)

    try:
        print("\n📦 Buscando produtos com purchase_ok=True...")

        produtos = conn.search_read(
            'product.product',
            [['purchase_ok', '=', True]],
            fields=['id', 'name', 'default_code', 'type', 'purchase_ok'],
            limit=10
        )

        if produtos:
            print(f"\n✅ Encontrados {len(produtos)} produtos compráveis:")
            for prod in produtos:
                print(f"   [{prod.get('default_code', 'N/A')}] {prod.get('name', 'N/A')}")

            return len(produtos)

        return 0

    except Exception as e:
        print(f"❌ ERRO: {e}")
        return 0

def testar_categorias_produto(conn):
    """
    Testa categorias de produtos (product.category)
    """
    print("\n" + "=" * 80)
    print("📂 TESTANDO product.category")
    print("=" * 80)

    try:
        print("\n📦 Buscando categorias de produtos...")

        categorias = conn.search_read(
            'product.category',
            [],
            fields=['id', 'name', 'parent_id', 'complete_name'],
            limit=20
        )

        if categorias:
            print(f"\n✅ Encontradas {len(categorias)} categorias:")
            for cat in categorias:
                print(f"   ID {cat['id']}: {cat.get('complete_name', cat.get('name', 'N/A'))}")

            return categorias

        return None

    except Exception as e:
        print(f"❌ ERRO: {e}")
        return None

def verificar_cadastro_palletizacao():
    """
    Verifica produtos cadastrados localmente com produto_comprado=True
    """
    print("\n" + "=" * 80)
    print("🗄️  VERIFICANDO CADASTRO LOCAL (produto_comprado=True)")
    print("=" * 80)

    app = create_app()

    with app.app_context():
        try:
            # Contar produtos comprados
            total_comprados = CadastroPalletizacao.query.filter_by(
                produto_comprado=True,
                ativo=True
            ).count()

            print(f"\n✅ Total de produtos com produto_comprado=True: {total_comprados}")

            # Buscar 5 exemplos
            produtos = CadastroPalletizacao.query.filter_by(
                produto_comprado=True,
                ativo=True
            ).limit(5).all()

            if produtos:
                print("\n📦 Exemplos de produtos comprados cadastrados localmente:")
                for prod in produtos:
                    print(f"   [{prod.cod_produto}] {prod.nome_produto}")

            return total_comprados

        except Exception as e:
            print(f"❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            return 0

def testar_busca_com_default_code(conn, cod_produto_exemplo):
    """
    Testa busca de produto específico usando default_code
    """
    print("\n" + "=" * 80)
    print(f"🔎 TESTANDO BUSCA POR default_code: {cod_produto_exemplo}")
    print("=" * 80)

    try:
        print(f"\n📦 Buscando produto com default_code='{cod_produto_exemplo}'...")

        produtos = conn.search_read(
            'product.product',
            [['default_code', '=', cod_produto_exemplo]],
            fields=[
                'id', 'name', 'default_code', 'type',
                'categ_id', 'purchase_ok', 'sale_ok',
                'active', 'detailed_type'
            ]
        )

        if produtos:
            print(f"\n✅ Produto encontrado:")
            prod = produtos[0]
            print(formatar_json(prod))
            return prod
        else:
            print(f"\n⚠️  Produto com default_code='{cod_produto_exemplo}' NÃO encontrado no Odoo")
            return None

    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return None

def analisar_estrategias_filtro(conn):
    """
    Analisa estratégias possíveis para filtrar produtos de produção
    """
    print("\n" + "=" * 80)
    print("🎯 ANÁLISE DE ESTRATÉGIAS DE FILTRO")
    print("=" * 80)

    print("\n📋 ESTRATÉGIAS POSSÍVEIS:\n")

    print("1️⃣  FILTRO POR purchase_ok=True (no Odoo)")
    print("   PRO: Filtra no Odoo, menos dados trafegados")
    print("   CONTRA: Pode incluir produtos não relacionados à produção")
    print("   QUERY: [['purchase_ok', '=', True]]")

    print("\n2️⃣  FILTRO POR CATEGORIA (no Odoo)")
    print("   PRO: Pode separar matérias-primas de outros produtos")
    print("   CONTRA: Precisa identificar categorias certas no Odoo")
    print("   QUERY: [['categ_id', 'in', [lista_categorias]]]")

    print("\n3️⃣  IMPORTAR TUDO + FILTRO LOCAL (CadastroPalletizacao.produto_comprado=True)")
    print("   PRO: Controle total no sistema local")
    print("   CONTRA: Importa dados desnecessários do Odoo")
    print("   LÓGICA: Verificar se default_code existe localmente com produto_comprado=True")

    print("\n4️⃣  HÍBRIDO: Filtro Odoo + Validação Local")
    print("   PRO: Otimização no Odoo + validação local")
    print("   CONTRA: Lógica mais complexa")
    print("   LÓGICA: purchase_ok=True no Odoo + produto_comprado=True local")

    print("\n" + "=" * 80)
    print("💡 RECOMENDAÇÃO INICIAL:")
    print("=" * 80)
    print("""
Usar ESTRATÉGIA 3 (Importar + Filtro Local):
1. Importar requisições/pedidos/recebimentos do Odoo SEM filtro de produto
2. Para cada linha, extrair default_code
3. Verificar se existe em CadastroPalletizacao com produto_comprado=True
4. SE NÃO EXISTIR: IGNORAR linha (não importar)
5. SE EXISTIR: Importar normalmente

VANTAGENS:
- Controle total no cadastro local
- Flexibilidade para mudar critérios sem tocar no Odoo
- Menos complexidade nas queries Odoo

DESVANTAGENS:
- Mais dados trafegados do Odoo (mas queries já são limitadas)
- Validação em tempo de importação
    """)

def main():
    """Função principal"""
    print("\n" + "=" * 80)
    print("🧪 TESTE DE product.product - IDENTIFICAÇÃO DE PRODUTOS DE PRODUÇÃO")
    print("=" * 80)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)

    # Conectar ao Odoo
    conn = get_odoo_connection()
    result = conn.test_connection()

    if not result['success']:
        print("\n❌ Não foi possível conectar ao Odoo. Abortando.")
        return

    print("✅ Conectado ao Odoo com sucesso\n")

    # Executar testes
    produtos_exemplo = testar_campos_product_product(conn)

    total_purchase_ok = testar_filtro_purchase_ok(conn)

    categorias = testar_categorias_produto(conn)

    total_local = verificar_cadastro_palletizacao()

    # Testar busca com default_code de exemplo (se temos produtos locais)
    if total_local > 0:
        # Pegar código de um produto local
        app = create_app()
        with app.app_context():
            exemplo = CadastroPalletizacao.query.filter_by(
                produto_comprado=True,
                ativo=True
            ).first()

            if exemplo:
                produto_odoo = testar_busca_com_default_code(conn, exemplo.cod_produto)

    # Analisar estratégias
    analisar_estrategias_filtro(conn)

    # Salvar resultados
    print("\n" + "=" * 80)
    print("💾 SALVANDO ANÁLISE")
    print("=" * 80)

    resultado = {
        "metadata": {
            "data_execucao": datetime.now().isoformat(),
            "total_produtos_purchase_ok_odoo": total_purchase_ok,
            "total_produtos_comprados_local": total_local
        },
        "produtos_exemplo_odoo": produtos_exemplo,
        "categorias_odoo": categorias
    }

    output_path = os.path.join(
        os.path.dirname(__file__),
        '../app/odoo/services/ANALISE_FILTRO_PRODUTOS.json'
    )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(formatar_json(resultado))

    print(f"✅ Análise salva em: {output_path}")
    print("\n✅ Teste concluído!")

if __name__ == '__main__':
    main()

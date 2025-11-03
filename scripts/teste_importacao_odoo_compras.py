"""
Script de Teste de Importação Odoo - Compras e Estoque
=======================================================

Testa importação real de 1 registro de cada tipo:
- Fase 1: purchase.requisition
- Fase 2: purchase.order + purchase.order.line
- Fase 3: stock.picking + stock.move

Documenta dados extraídos vs campos propostos.

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

def formatar_json(data):
    """Formata JSON de forma legível"""
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)

def testar_conexao():
    """Testa conexão com Odoo"""
    print("=" * 80)
    print("🔌 TESTANDO CONEXÃO COM ODOO")
    print("=" * 80)

    try:
        conn = get_odoo_connection()
        result = conn.test_connection()

        if result['success']:
            print("✅ CONEXÃO BEM-SUCEDIDA\n")
            print(f"Versão Odoo: {result['data'].get('version', 'N/A')}")
            print(f"Database: {result['data'].get('database', 'N/A')}")
            print(f"Usuário: {result['data'].get('user', {}).get('name', 'N/A')}")
            print(f"UID: {result['data'].get('uid', 'N/A')}")
            return conn
        else:
            print(f"❌ FALHA NA CONEXÃO: {result.get('message', 'Erro desconhecido')}")
            return None
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return None

def fase1_testar_purchase_requisition(conn):
    """
    FASE 1: Testar importação de purchase.requisition
    """
    print("\n" + "=" * 80)
    print("📋 FASE 1: TESTANDO purchase.request")
    print("=" * 80)

    try:
        # Buscar 1 requisição ativa
        print("\n🔍 Buscando requisições ativas no Odoo...")

        requisicoes = conn.search_read(
            'purchase.request',
            [['state', 'in', ['approved', 'done']]],
            fields=[
                'id', 'name', 'state', 'date_start', 'create_date',
                'requested_by', 'assigned_to', 'description',
                'line_ids', 'origin', 'company_id'
            ],
            limit=1
        )

        if not requisicoes:
            print("⚠️  Nenhuma requisição encontrada com state in ['approved', 'done']")
            print("\n🔍 Tentando buscar QUALQUER requisição...")
            requisicoes = conn.search_read(
                'purchase.request',
                [],
                fields=['id', 'name', 'state'],
                limit=5
            )
            if requisicoes:
                print(f"✅ Encontradas {len(requisicoes)} requisições:")
                for req in requisicoes:
                    print(f"   - ID: {req['id']}, Name: {req['name']}, State: {req['state']}")
            return None

        requisicao = requisicoes[0]
        print(f"✅ Encontrada requisição: {requisicao.get('name', 'N/A')}")
        print(f"   State: {requisicao.get('state', 'N/A')}")

        # Buscar linhas da requisição se existirem
        if requisicao.get('line_ids'):
            print(f"\n🔍 Buscando {len(requisicao['line_ids'])} linhas da requisição...")
            linhas = conn.read(
                'purchase.request.line',
                requisicao['line_ids'],
                fields=[
                    'id', 'request_id', 'product_id', 'name',
                    'product_qty', 'product_uom_id', 'date_required',
                    'estimated_cost', 'description'
                ]
            )
            requisicao['linhas_detalhadas'] = linhas
            print(f"✅ {len(linhas)} linhas carregadas")

        return requisicao

    except Exception as e:
        print(f"❌ ERRO na Fase 1: {e}")
        import traceback
        traceback.print_exc()
        return None

def fase2_testar_purchase_order(conn):
    """
    FASE 2: Testar importação de purchase.order + purchase.order.line
    """
    print("\n" + "=" * 80)
    print("📦 FASE 2: TESTANDO purchase.order + purchase.order.line")
    print("=" * 80)

    try:
        # Buscar 1 pedido confirmado
        print("\n🔍 Buscando pedidos de compra confirmados no Odoo...")

        pedidos = conn.search_read(
            'purchase.order',
            [['state', 'in', ['purchase', 'done']]],
            fields=[
                'id', 'name', 'state', 'date_order', 'date_approve',
                'date_planned', 'partner_id', 'user_id', 'origin',
                'amount_total', 'currency_id', 'order_line',
                'picking_ids', 'invoice_ids'
            ],
            limit=1
        )

        if not pedidos:
            print("⚠️  Nenhum pedido encontrado com state in ['purchase', 'done']")
            print("\n🔍 Tentando buscar QUALQUER pedido...")
            pedidos = conn.search_read(
                'purchase.order',
                [],
                fields=['id', 'name', 'state'],
                limit=5
            )
            if pedidos:
                print(f"✅ Encontrados {len(pedidos)} pedidos:")
                for ped in pedidos:
                    print(f"   - ID: {ped['id']}, Name: {ped['name']}, State: {ped['state']}")
            return None

        pedido = pedidos[0]
        print(f"✅ Encontrado pedido: {pedido.get('name', 'N/A')}")
        print(f"   State: {pedido.get('state', 'N/A')}")
        print(f"   Fornecedor: {pedido.get('partner_id', ['N/A'])[1] if pedido.get('partner_id') else 'N/A'}")

        # Buscar linhas do pedido
        if pedido.get('order_line'):
            print(f"\n🔍 Buscando {len(pedido['order_line'])} linhas do pedido...")
            linhas = conn.read(
                'purchase.order.line',
                pedido['order_line'],
                fields=[
                    'id', 'order_id', 'product_id', 'name',
                    'product_qty', 'qty_received', 'qty_invoiced',
                    'price_unit', 'price_subtotal', 'price_tax',
                    'taxes_id', 'product_uom', 'date_planned'
                ]
            )
            pedido['linhas_detalhadas'] = linhas
            print(f"✅ {len(linhas)} linhas carregadas")

        return pedido

    except Exception as e:
        print(f"❌ ERRO na Fase 2: {e}")
        import traceback
        traceback.print_exc()
        return None

def fase3_testar_stock_picking(conn):
    """
    FASE 3: Testar importação de stock.picking + stock.move
    """
    print("\n" + "=" * 80)
    print("🚚 FASE 3: TESTANDO stock.picking + stock.move")
    print("=" * 80)

    try:
        # Buscar 1 recebimento concluído
        print("\n🔍 Buscando recebimentos concluídos no Odoo...")

        recebimentos = conn.search_read(
            'stock.picking',
            [
                ['picking_type_id.code', '=', 'incoming'],
                ['state', '=', 'done']
            ],
            fields=[
                'id', 'name', 'state', 'scheduled_date', 'date_done',
                'origin', 'partner_id', 'purchase_id', 'location_dest_id',
                'move_ids_without_package', 'picking_type_id'
            ],
            limit=1
        )

        if not recebimentos:
            print("⚠️  Nenhum recebimento encontrado com picking_type_id.code='incoming' e state='done'")
            print("\n🔍 Tentando buscar QUALQUER stock.picking...")
            recebimentos = conn.search_read(
                'stock.picking',
                [['picking_type_id.code', '=', 'incoming']],
                fields=['id', 'name', 'state', 'picking_type_id'],
                limit=5
            )
            if recebimentos:
                print(f"✅ Encontrados {len(recebimentos)} recebimentos:")
                for rec in recebimentos:
                    print(f"   - ID: {rec['id']}, Name: {rec['name']}, State: {rec['state']}")
            return None

        recebimento = recebimentos[0]
        print(f"✅ Encontrado recebimento: {recebimento.get('name', 'N/A')}")
        print(f"   State: {recebimento.get('state', 'N/A')}")
        print(f"   Origem: {recebimento.get('origin', 'N/A')}")

        # Buscar movimentos do recebimento
        if recebimento.get('move_ids_without_package'):
            print(f"\n🔍 Buscando {len(recebimento['move_ids_without_package'])} movimentos...")
            movimentos = conn.read(
                'stock.move',
                recebimento['move_ids_without_package'],
                fields=[
                    'id', 'picking_id', 'product_id', 'name',
                    'product_uom_qty', 'quantity', 'product_uom',
                    'date', 'state', 'origin',
                    'purchase_line_id', 'location_id', 'location_dest_id'
                ]
            )
            recebimento['movimentos_detalhados'] = movimentos
            print(f"✅ {len(movimentos)} movimentos carregados")

        return recebimento

    except Exception as e:
        print(f"❌ ERRO na Fase 3: {e}")
        import traceback
        traceback.print_exc()
        return None

def salvar_documentacao(conn, fase1_data, fase2_data, fase3_data):
    """
    Salva documentação com os dados extraídos
    """
    print("\n" + "=" * 80)
    print("💾 SALVANDO DOCUMENTAÇÃO")
    print("=" * 80)

    doc = {
        "metadata": {
            "data_execucao": datetime.now().isoformat(),
            "odoo_url": "https://odoo.nacomgoya.com.br",
            "database": "odoo-17-ee-nacomgoya-prd",
        },
        "fase1_purchase_request": {
            "status": "sucesso" if fase1_data else "falha",
            "dados_extraidos": fase1_data,
            "campos_propostos_sistema": [
                "num_requisicao (name)",
                "data_requisicao_criacao (create_date)",
                "data_inicio (date_start)",
                "usuario_requisicao (requested_by)",
                "responsavel (assigned_to)",
                "descricao (description)",
                "origem (origin)",
                "cod_produto (line_ids/product_id/default_code)",
                "nome_produto (line_ids/product_id/name)",
                "qtd_produto_requisicao (line_ids/product_qty)",
                "data_necessidade (line_ids/date_required)",
                "custo_estimado (line_ids/estimated_cost)",
                "status (state)",
                "odoo_id (id)"
            ]
        },
        "fase2_purchase_order": {
            "status": "sucesso" if fase2_data else "falha",
            "dados_extraidos": fase2_data,
            "campos_propostos_sistema": [
                "num_pedido (name)",
                "cnpj_fornecedor (partner_id/l10n_br_cnpj)",
                "raz_social (partner_id/name)",
                "numero_nf (invoice_ids/name)",
                "data_pedido_criacao (date_order)",
                "data_pedido_entrega (date_approve)",
                "data_pedido_previsao (date_planned)",
                "cod_produto (order_line/product_id/default_code)",
                "nome_produto (order_line/product_id/name)",
                "qtd_produto_pedido (order_line/product_qty)",
                "preco_produto_pedido (order_line/price_unit)",
                "confirmacao_pedido (state=purchase)",
                "odoo_id (id)"
            ]
        },
        "fase3_stock_picking": {
            "status": "sucesso" if fase3_data else "falha",
            "dados_extraidos": fase3_data,
            "campos_propostos_sistema": [
                "numero_recebimento (name)",
                "data_programada (scheduled_date)",
                "data_efetiva (date_done)",
                "origem_documento (origin)",
                "fornecedor (partner_id/name)",
                "pedido_compra_vinculado (purchase_id)",
                "cod_produto (move_ids/product_id/default_code)",
                "nome_produto (move_ids/product_id/name)",
                "qtd_recebida (move_ids/quantity)",
                "data_movimento (move_ids/date)"
            ]
        }
    }

    # Salvar JSON
    output_path = os.path.join(
        os.path.dirname(__file__),
        '../app/odoo/services/TESTE_IMPORTACAO_RESULTADO.json'
    )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(formatar_json(doc))

    print(f"✅ JSON salvo em: {output_path}")

    # Criar documento markdown resumido
    md_path = os.path.join(
        os.path.dirname(__file__),
        '../app/odoo/services/TESTE_IMPORTACAO_ANALISE.md'
    )

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(gerar_markdown_analise(doc))

    print(f"✅ Análise Markdown salva em: {md_path}")

    return output_path, md_path

def gerar_markdown_analise(doc):
    """Gera documento markdown com análise"""
    md = f"""# 🧪 Resultado do Teste de Importação Odoo - Compras e Estoque

**Data de Execução**: {doc['metadata']['data_execucao']}
**Odoo URL**: {doc['metadata']['odoo_url']}
**Database**: {doc['metadata']['database']}

---

## 📋 FASE 1: purchase.request (Requisições de Compras)

**Status**: {doc['fase1_purchase_request']['status'].upper()}

### Campos Propostos no Sistema:
```
"""
    for campo in doc['fase1_purchase_request']['campos_propostos_sistema']:
        md += f"- {campo}\n"

    md += "```\n\n### Dados Extraídos do Odoo:\n\n"

    if doc['fase1_purchase_request']['dados_extraidos']:
        md += "```json\n"
        md += formatar_json(doc['fase1_purchase_request']['dados_extraidos'])
        md += "\n```\n"
    else:
        md += "❌ Nenhum dado extraído (veja erros no JSON completo)\n"

    md += "\n### ✅ Análise:\n\n"
    if doc['fase1_purchase_request']['status'] == 'sucesso':
        md += "- [ ] Verificar se campos existem conforme esperado\n"
        md += "- [ ] Validar mapeamento de campos relacionais (user_id, product_id)\n"
        md += "- [ ] Confirmar formato de datas\n"
        md += "- [ ] Analisar estrutura de line_ids\n"
    else:
        md += "⚠️ Importação falhou - analisar logs de erro\n"

    md += "\n---\n\n"
    md += "## 📦 FASE 2: purchase.order + purchase.order.line (Pedidos de Compras)\n\n"
    md += f"**Status**: {doc['fase2_purchase_order']['status'].upper()}\n\n"

    md += "### Campos Propostos no Sistema:\n```\n"
    for campo in doc['fase2_purchase_order']['campos_propostos_sistema']:
        md += f"- {campo}\n"

    md += "```\n\n### Dados Extraídos do Odoo:\n\n"

    if doc['fase2_purchase_order']['dados_extraidos']:
        md += "```json\n"
        md += formatar_json(doc['fase2_purchase_order']['dados_extraidos'])
        md += "\n```\n"
    else:
        md += "❌ Nenhum dado extraído (veja erros no JSON completo)\n"

    md += "\n### ✅ Análise:\n\n"
    if doc['fase2_purchase_order']['status'] == 'sucesso':
        md += "- [ ] Verificar se partner_id contém l10n_br_cnpj\n"
        md += "- [ ] Validar campos de quantidade (product_qty, qty_received)\n"
        md += "- [ ] Confirmar campos de preço e impostos\n"
        md += "- [ ] Analisar estrutura de order_line\n"
    else:
        md += "⚠️ Importação falhou - analisar logs de erro\n"

    md += "\n---\n\n"
    md += "## 🚚 FASE 3: stock.picking + stock.move (Recebimentos)\n\n"
    md += f"**Status**: {doc['fase3_stock_picking']['status'].upper()}\n\n"

    md += "### Campos Propostos no Sistema:\n```\n"
    for campo in doc['fase3_stock_picking']['campos_propostos_sistema']:
        md += f"- {campo}\n"

    md += "```\n\n### Dados Extraídos do Odoo:\n\n"

    if doc['fase3_stock_picking']['dados_extraidos']:
        md += "```json\n"
        md += formatar_json(doc['fase3_stock_picking']['dados_extraidos'])
        md += "\n```\n"
    else:
        md += "❌ Nenhum dado extraído (veja erros no JSON completo)\n"

    md += "\n### ✅ Análise:\n\n"
    if doc['fase3_stock_picking']['status'] == 'sucesso':
        md += "- [ ] Verificar se picking_type_id.code='incoming' funciona como filtro\n"
        md += "- [ ] Validar campos de quantidade (product_uom_qty vs quantity)\n"
        md += "- [ ] Confirmar vínculo com purchase_id\n"
        md += "- [ ] Analisar estrutura de move_ids_without_package\n"
    else:
        md += "⚠️ Importação falhou - analisar logs de erro\n"

    md += "\n---\n\n## 🎯 PRÓXIMOS PASSOS\n\n"
    md += "1. **Revisar JSON completo** em `TESTE_IMPORTACAO_RESULTADO.json`\n"
    md += "2. **Validar campos faltantes** ou diferentes do esperado\n"
    md += "3. **Ajustar mapeamentos** em `manufatura_mapper.py` se necessário\n"
    md += "4. **Confirmar filtros** de importação (states, dates, etc.)\n"
    md += "5. **Testar campos relacionais** (partner_id/l10n_br_cnpj, product_id/default_code)\n"
    md += "6. **Implementar importação real** após validação\n\n"

    md += "---\n\n"
    md += "**Autor**: Sistema de Fretes  \n"
    md += "**Script**: `scripts/teste_importacao_odoo_compras.py`\n"

    return md

def main():
    """Função principal"""
    print("\n" + "=" * 80)
    print("🧪 TESTE DE IMPORTAÇÃO ODOO - COMPRAS E ESTOQUE")
    print("=" * 80)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)

    # Testar conexão
    conn = testar_conexao()
    if not conn:
        print("\n❌ Não foi possível conectar ao Odoo. Abortando.")
        return

    # Executar testes
    fase1_data = fase1_testar_purchase_requisition(conn)
    fase2_data = fase2_testar_purchase_order(conn)
    fase3_data = fase3_testar_stock_picking(conn)

    # Salvar documentação
    json_path, md_path = salvar_documentacao(conn, fase1_data, fase2_data, fase3_data)

    # Resumo final
    print("\n" + "=" * 80)
    print("📊 RESUMO DOS TESTES")
    print("=" * 80)
    print(f"Fase 1 (purchase.requisition):    {'✅ SUCESSO' if fase1_data else '❌ FALHA'}")
    print(f"Fase 2 (purchase.order):          {'✅ SUCESSO' if fase2_data else '❌ FALHA'}")
    print(f"Fase 3 (stock.picking):           {'✅ SUCESSO' if fase3_data else '❌ FALHA'}")
    print("=" * 80)
    print(f"\n📄 Documentação gerada:")
    print(f"   - JSON: {json_path}")
    print(f"   - Análise: {md_path}")
    print("\n✅ Teste concluído!")

if __name__ == '__main__':
    main()

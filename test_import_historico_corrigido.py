#!/usr/bin/env python3
"""
Script CORRIGIDO para testar importação de 5 registros do HistoricoPedidos
Mostra todos os campos importados para validação
"""

from app import create_app, db
from app.odoo.utils.connection import get_odoo_connection
from app.manufatura.models import HistoricoPedidos
from datetime import datetime
from decimal import Decimal

def limpar_historico():
    """Limpa todos os registros de HistoricoPedidos"""
    count = HistoricoPedidos.query.count()
    if count > 0:
        print(f"⚠️  Limpando {count} registros existentes...")
        HistoricoPedidos.query.delete()
        db.session.commit()
        print("✅ Tabela limpa")
    else:
        print("✅ Tabela já está vazia")

def importar_teste():
    """Importa apenas 5 registros para teste"""
    print("\n🔄 Iniciando importação de teste (máximo 5 registros)...")
    
    # Obter conexão configurada
    connection = get_odoo_connection()
    
    # Conectar ao Odoo
    uid = connection.authenticate()
    if not uid:
        print("❌ Falha na autenticação com Odoo")
        return False
    
    print("✅ Conectado ao Odoo")
    
    # Buscar apenas 2 pedidos para ter ~5 linhas
    print("📥 Buscando 2 pedidos do Odoo...")
    pedidos = connection.search_read(
        'sale.order',
        [['state', 'in', ['sale', 'done']]],
        ['name', 'partner_id', 'date_order', 'user_id', 'team_id'],
        limit=2
    )
    
    print(f"📦 {len(pedidos)} pedidos encontrados")
    
    registros_importados = []
    total_linhas = 0
    
    for ped_odoo in pedidos:
        # Buscar linhas do pedido
        linhas = connection.search_read(
            'sale.order.line',
            [['order_id', '=', ped_odoo['id']]],
            ['product_id', 'product_uom_qty', 'price_unit', 'price_total']
        )
        
        print(f"  📋 Pedido {ped_odoo['name']}: {len(linhas)} linhas")
        
        # Buscar dados dos produtos para obter default_code (CORREÇÃO CRÍTICA)
        product_ids = [l['product_id'][0] for l in linhas if l.get('product_id')]
        produtos_dict = {}
        if product_ids:
            produtos = connection.search_read(
                'product.product',
                [['id', 'in', product_ids]],
                ['id', 'default_code', 'name']
            )
            produtos_dict = {p['id']: p for p in produtos}
            print(f"  📦 {len(produtos)} produtos buscados com default_code")
        
        for linha in linhas[:3]:  # Máximo 3 linhas por pedido
            if total_linhas >= 5:
                break
                
            product_id = linha['product_id'][0] if linha.get('product_id') else None
            produto_info = produtos_dict.get(product_id, {})
            
            # USAR DEFAULT_CODE COMO COD_PRODUTO (CORREÇÃO PRINCIPAL)
            cod_produto_real = produto_info.get('default_code', '')
            
            # Dados do registro
            dados = {
                'num_pedido': ped_odoo.get('name'),
                'data_pedido': ped_odoo.get('date_order', '').split(' ')[0] if ped_odoo.get('date_order') else None,
                'cnpj_cliente': str(ped_odoo['partner_id'][0]) if ped_odoo.get('partner_id') else None,
                'nome_cliente': ped_odoo['partner_id'][1] if ped_odoo.get('partner_id') else None,
                'vendedor': ped_odoo['user_id'][1] if ped_odoo.get('user_id') else None,
                'equipe_vendas': ped_odoo['team_id'][1] if ped_odoo.get('team_id') else None,
                'cod_produto': cod_produto_real,  # USANDO DEFAULT_CODE
                'product_id_odoo': product_id,  # Para comparação
                'nome_produto_original': produto_info.get('name', ''),
                'nome_produto_limpo': produto_info.get('name', '').split(']', 1)[-1].strip() if ']' in produto_info.get('name', '') else produto_info.get('name', ''),
                'qtd_produto_pedido': linha.get('product_uom_qty', 0),
                'preco_produto_pedido': linha.get('price_unit', 0),
                'valor_produto_pedido': linha.get('price_total', 0)
            }
            
            # Criar registro no banco
            try:
                # Processar data
                data_pedido = None
                if ped_odoo.get('date_order'):
                    try:
                        data_pedido = datetime.strptime(
                            ped_odoo['date_order'], '%Y-%m-%d %H:%M:%S'
                        ).date()
                    except:
                        pass
                
                historico = HistoricoPedidos(
                    num_pedido=dados['num_pedido'],
                    data_pedido=data_pedido,
                    cnpj_cliente=dados['cnpj_cliente'],
                    raz_social_red=dados['nome_cliente'],
                    vendedor=dados['vendedor'],
                    equipe_vendas=dados['equipe_vendas'],
                    cod_produto=cod_produto_real,  # USANDO DEFAULT_CODE
                    nome_produto=dados['nome_produto_limpo'],
                    qtd_produto_pedido=Decimal(str(dados['qtd_produto_pedido'])),
                    preco_produto_pedido=Decimal(str(dados['preco_produto_pedido'])),
                    valor_produto_pedido=Decimal(str(dados['valor_produto_pedido']))
                )
                
                db.session.add(historico)
                registros_importados.append(dados)
                total_linhas += 1
                print(f"    ✅ Linha {total_linhas}: Produto {cod_produto_real} importado")
                
            except Exception as e:
                print(f"    ❌ Erro ao importar linha: {e}")
        
        if total_linhas >= 5:
            break
    
    # Commit
    if registros_importados:
        db.session.commit()
        print(f"\n✅ {len(registros_importados)} registros importados com sucesso")
    
    return registros_importados

def mostrar_dados_completos():
    """Mostra todos os dados dos registros importados"""
    print("\n" + "="*80)
    print("📊 DADOS COMPLETOS DOS REGISTROS IMPORTADOS")
    print("="*80)
    
    registros = HistoricoPedidos.query.limit(5).all()
    
    for i, r in enumerate(registros, 1):
        print(f"\n{'='*40}")
        print(f"📦 REGISTRO {i}")
        print(f"{'='*40}")
        print(f"  ID no banco:           {r.id}")
        print(f"  Número Pedido:         {r.num_pedido}")
        print(f"  Data Pedido:           {r.data_pedido}")
        print(f"  CNPJ Cliente:          {r.cnpj_cliente}")
        print(f"  Nome Cliente:          {r.raz_social_red}")
        print(f"  Vendedor:              {r.vendedor}")
        print(f"  Equipe Vendas:         {r.equipe_vendas}")
        print(f"  ⭐ COD_PRODUTO:        {r.cod_produto}")
        print(f"  Nome Produto:          {r.nome_produto}")
        print(f"  Qtd Pedido:            {r.qtd_produto_pedido}")
        print(f"  Preço Unitário:        {r.preco_produto_pedido}")
        print(f"  Valor Total:           {r.valor_produto_pedido}")
        print(f"  Nome Grupo:            {r.nome_grupo}")
        print(f"  Importado em:          {r.importado_em}")
    
    print(f"\n{'='*80}")
    print("✅ VALIDAÇÃO DO COD_PRODUTO:")
    print("="*80)
    
    for r in registros:
        # Verificar se o código é numérico (correto) ou ID do Odoo (errado)
        if r.cod_produto:
            # Códigos corretos geralmente têm 7-10 dígitos
            # IDs do Odoo geralmente têm 4-5 dígitos
            if r.cod_produto.isdigit():
                if len(r.cod_produto) >= 6:
                    print(f"✅ Pedido {r.num_pedido}: cod_produto '{r.cod_produto}' parece ser o código correto (default_code)")
                else:
                    print(f"❌ Pedido {r.num_pedido}: cod_produto '{r.cod_produto}' parece ser ID do Odoo (ERRADO)")
            else:
                print(f"✅ Pedido {r.num_pedido}: cod_produto '{r.cod_produto}' é alfanumérico (default_code)")
        else:
            print(f"⚠️  Pedido {r.num_pedido}: cod_produto está VAZIO")

def main():
    app = create_app()
    
    with app.app_context():
        # 1. Limpar tabela
        limpar_historico()
        
        # 2. Importar 5 registros de teste
        registros = importar_teste()
        
        if registros:
            # 3. Mostrar dados importados (preview)
            print("\n📋 PREVIEW DOS DADOS IMPORTADOS:")
            print("-" * 80)
            for i, r in enumerate(registros, 1):
                print(f"\n{i}. Pedido: {r['num_pedido']}")
                print(f"   Cliente: {r['cnpj_cliente']} - {r['nome_cliente']}")
                print(f"   Produto Original: {r['nome_produto_original']}")
                print(f"   Produto Limpo: {r['nome_produto_limpo']}")
                print(f"   ⭐ COD_PRODUTO (default_code): {r['cod_produto']}")
                print(f"   🔴 ID Odoo (errado):           {r['product_id_odoo']}")
                print(f"   Quantidade: {r['qtd_produto_pedido']}")
            
            # 4. Mostrar dados completos do banco
            mostrar_dados_completos()
            
            print("\n" + "="*80)
            print("🎯 RESUMO DA IMPORTAÇÃO DE TESTE")
            print("="*80)
            print(f"✅ {len(registros)} registros importados com sucesso")
            print("\n⚠️  IMPORTANTE: Verifique se o campo COD_PRODUTO está correto!")
            print("   - ✅ DEVE conter o default_code do produto (ex: 4350114, PD-001)")
            print("   - ❌ NÃO deve conter o ID do Odoo (ex: 29758, 35898)")
            print("\n💡 Se estiver correto, você pode aprovar a limpeza total e reimportação")
        else:
            print("❌ Nenhum registro foi importado")

if __name__ == "__main__":
    main()
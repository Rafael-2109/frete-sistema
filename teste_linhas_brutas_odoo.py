"""
Teste para investigar linhas brutas do account.move.line do Odoo
================================================================

Este teste busca diretamente as linhas de uma NF específica no Odoo
para verificar se as linhas vazias vêm do próprio Odoo ou são criadas
durante o processamento.
"""

import logging
from app.odoo.utils.connection import get_odoo_connection

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def investigar_linhas_brutas_nf(numero_nf="137275"):
    """
    Investiga as linhas brutas que vêm diretamente do Odoo
    para uma NF específica
    """
    print(f"\n🔍 INVESTIGANDO LINHAS BRUTAS DA NF {numero_nf}")
    print("=" * 80)
    
    try:
        # Conectar ao Odoo
        connection = get_odoo_connection()
        if not connection:
            print("❌ Erro: Não foi possível conectar ao Odoo")
            return
        
        print("✅ Conectado ao Odoo com sucesso")
        
        # 1️⃣ BUSCAR FATURA PELO NÚMERO
        print(f"\n1️⃣ Buscando fatura {numero_nf}...")
        
        faturas = connection.search_read(
            'account.move',
            [('l10n_br_numero_nota_fiscal', '=', numero_nf)],
            ['id', 'name', 'l10n_br_numero_nota_fiscal', 'state']
        )
        
        if not faturas:
            print(f"❌ NF {numero_nf} não encontrada")
            return
        
        fatura = faturas[0]
        move_id = fatura['id']
        
        print(f"✅ Fatura encontrada:")
        print(f"   • ID: {move_id}")
        print(f"   • Nome: {fatura['name']}")
        print(f"   • Status: {fatura['state']}")
        
        # 2️⃣ BUSCAR TODAS AS LINHAS DA FATURA
        print(f"\n2️⃣ Buscando TODAS as linhas da fatura {move_id}...")
        
        campos_linha = [
            'id', 'move_id', 'partner_id', 'product_id', 
            'quantity', 'price_unit', 'price_total', 'price_subtotal',
            'name', 'account_id', 'display_type'
        ]
        
        linhas_brutas = connection.search_read(
            'account.move.line',
            [('move_id', '=', move_id)],
            campos_linha
        )
        
        print(f"📊 Total de linhas encontradas: {len(linhas_brutas)}")
        
        # 3️⃣ ANALISAR CADA LINHA
        print(f"\n3️⃣ ANÁLISE DETALHADA DAS LINHAS:")
        print("-" * 80)
        
        linhas_com_produto = 0
        linhas_sem_produto = 0
        linhas_quantidade_zero = 0
        linhas_impostos = 0
        linhas_outros = 0
        
        for i, linha in enumerate(linhas_brutas, 1):
            product_id = linha.get('product_id')
            quantity = linha.get('quantity', 0)
            display_type = linha.get('display_type')
            name = linha.get('name', '')
            account_id = linha.get('account_id')
            
            # Classificar tipo de linha
            tipo_linha = "PRODUTO"
            if not product_id:
                if display_type:
                    tipo_linha = f"DISPLAY ({display_type})"
                elif any(palavra in name.lower() for palavra in ['imposto', 'tax', 'icms', 'ipi', 'pis', 'cofins']):
                    tipo_linha = "IMPOSTO"
                    linhas_impostos += 1
                elif any(palavra in name.lower() for palavra in ['desconto', 'discount', 'frete']):
                    tipo_linha = "AJUSTE"
                else:
                    tipo_linha = "OUTROS"
                    linhas_outros += 1
                linhas_sem_produto += 1
            else:
                linhas_com_produto += 1
                if quantity == 0:
                    linhas_quantidade_zero += 1
            
            print(f"LINHA {i:2d}: {tipo_linha}")
            print(f"         • Product ID: {product_id}")
            print(f"         • Quantidade: {quantity}")
            print(f"         • Nome: {name[:60]}{'...' if len(name) > 60 else ''}")
            print(f"         • Display Type: {display_type}")
            if account_id:
                print(f"         • Account: {account_id}")
            print()
        
        # 4️⃣ RESUMO ESTATÍSTICO
        print("4️⃣ RESUMO ESTATÍSTICO:")
        print("=" * 40)
        print(f"📦 Linhas com produto:     {linhas_com_produto}")
        print(f"❌ Linhas sem produto:     {linhas_sem_produto}")
        print(f"⚠️  Quantidade zero:       {linhas_quantidade_zero}")
        print(f"💰 Linhas de impostos:     {linhas_impostos}")
        print(f"🔧 Outros tipos:           {linhas_outros}")
        print(f"📊 TOTAL:                  {len(linhas_brutas)}")
        
        # 5️⃣ FILTRAR APENAS LINHAS DE PRODUTO
        print(f"\n5️⃣ LINHAS DE PRODUTO VÁLIDAS:")
        print("-" * 40)
        
        linhas_produto_validas = [
            linha for linha in linhas_brutas 
            if linha.get('product_id') and linha.get('quantity', 0) > 0
        ]
        
        print(f"✅ Linhas de produto válidas: {len(linhas_produto_validas)}")
        
        for i, linha in enumerate(linhas_produto_validas, 1):
            product_info = linha.get('product_id', ['N/A', 'N/A'])
            print(f"   {i:2d}. Produto ID: {product_info[0] if isinstance(product_info, list) else product_info}")
            print(f"       Quantidade: {linha.get('quantity', 0)}")
            print(f"       Valor: R$ {linha.get('price_total', 0):,.2f}")
        
        # 6️⃣ CONCLUSÃO
        print(f"\n6️⃣ CONCLUSÃO:")
        print("=" * 40)
        
        taxa_produtos = (linhas_com_produto / len(linhas_brutas)) * 100 if linhas_brutas else 0
        taxa_validos = (len(linhas_produto_validas) / len(linhas_brutas)) * 100 if linhas_brutas else 0
        
        print(f"• Das {len(linhas_brutas)} linhas totais:")
        print(f"  - {linhas_com_produto} têm product_id ({taxa_produtos:.1f}%)")
        print(f"  - {len(linhas_produto_validas)} são produtos válidos ({taxa_validos:.1f}%)")
        print(f"  - {linhas_sem_produto} são linhas de ajuste/impostos ({100-taxa_produtos:.1f}%)")
        
        if taxa_validos < 20:
            print(f"\n⚠️  ATENÇÃO: Taxa de produtos válidos muito baixa ({taxa_validos:.1f}%)")
            print("   Isso confirma que o Odoo inclui muitas linhas de impostos/ajustes")
            print("   entre as linhas de produtos, sendo NORMAL esta proporção.")
        
        return {
            'total_linhas': len(linhas_brutas),
            'linhas_com_produto': linhas_com_produto,
            'linhas_produto_validas': len(linhas_produto_validas),
            'linhas_sem_produto': linhas_sem_produto,
            'taxa_produtos_validos': taxa_validos
        }
        
    except Exception as e:
        print(f"❌ Erro na investigação: {e}")
        return None

if __name__ == "__main__":
    resultado = investigar_linhas_brutas_nf("137275")
    
    if resultado:
        print(f"\n🎯 RESULTADO FINAL:")
        print(f"Taxa de produtos válidos: {resultado['taxa_produtos_validos']:.1f}%")
        print(f"Isso explica por que vemos apenas 11 produtos em 100 linhas!") 
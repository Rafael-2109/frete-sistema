#!/usr/bin/env python3
"""
Script de teste para verificar as melhorias no saldo de estoque
- Nova coluna Carteira
- Nova coluna Produção
- Novo critério de Status
"""

import os
import sys
from datetime import datetime, timedelta

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.estoque.routes import converter_projecao_para_resumo
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from app.carteira.models import CarteiraPrincipal
from app.producao.models import ProgramacaoProducao

def testar_melhorias():
    """Testa as melhorias implementadas"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*70)
        print("TESTE DAS MELHORIAS NO SALDO DE ESTOQUE")
        print("="*70)
        
        # Buscar um produto de exemplo
        cod_produto = '4310164'  # Produto de teste
        
        print(f"\n📦 Testando produto: {cod_produto}")
        print("-"*70)
        
        # 1. Testar busca na carteira
        print("\n1️⃣ TESTANDO COLUNA CARTEIRA:")
        qtd_carteira = db.session.query(
            db.func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido)
        ).filter(
            CarteiraPrincipal.cod_produto == str(cod_produto)
        ).scalar()
        
        if qtd_carteira:
            print(f"   ✅ Quantidade na carteira: {qtd_carteira:,.0f}")
        else:
            print(f"   ⚠️ Sem pedidos na carteira")
        
        # 2. Testar busca na produção
        print("\n2️⃣ TESTANDO COLUNA PRODUÇÃO:")
        hoje = datetime.now().date()
        qtd_producao = db.session.query(
            db.func.sum(ProgramacaoProducao.qtd_programada)
        ).filter(
            ProgramacaoProducao.cod_produto == str(cod_produto),
            ProgramacaoProducao.data_programacao >= hoje
        ).scalar()
        
        if qtd_producao:
            print(f"   ✅ Quantidade programada na produção: {qtd_producao:,.0f}")
        else:
            print(f"   ⚠️ Sem programação de produção")
        
        # 3. Testar projeção completa
        print("\n3️⃣ TESTANDO PROJEÇÃO COMPLETA:")
        projecao = ServicoEstoqueTempoReal.get_projecao_completa(cod_produto, dias=7)
        
        if projecao:
            resumo = converter_projecao_para_resumo(projecao)
            
            print(f"   📊 Estoque atual: {resumo['estoque_atual']:,.0f}")
            print(f"   📉 Ruptura 7d: {resumo['menor_estoque_d7']:,.0f}")
            
            # Disponibilidade
            if resumo['qtd_disponivel'] and resumo['qtd_disponivel'] > 0:
                print(f"   📅 Disponível: {resumo['qtd_disponivel']:,.0f} unidades")
                if resumo['dias_disponivel'] is not None:
                    print(f"   📅 Em D+{resumo['dias_disponivel']}")
            else:
                print(f"   ⚠️ Sem disponibilidade futura")
            
            # Carteira e Produção
            print(f"   🛒 Carteira: {resumo['qtd_total_carteira']:,.0f}")
            print(f"   🏭 Produção: {resumo['qtd_total_producao']:,.0f}")
            
            # 4. Testar novo critério de status
            print("\n4️⃣ TESTANDO NOVO CRITÉRIO DE STATUS:")
            print(f"   Status calculado: {resumo['status_ruptura']}")
            
            # Explicar o critério
            if resumo['menor_estoque_d7'] > 0:
                print(f"   ✅ Ruptura 7d > 0 → Status = OK")
            elif resumo['dias_disponivel'] is not None and resumo['dias_disponivel'] <= 7:
                print(f"   🟡 Disponível em até D+7 → Status = ATENÇÃO")
            else:
                print(f"   🔴 Sem disponibilidade em D+7 → Status = CRÍTICO")
        else:
            print("   ❌ Erro ao obter projeção")
        
        print("\n" + "="*70)
        print("TESTE CONCLUÍDO!")
        print("="*70)
        
        # Teste adicional com outros produtos
        print("\n📊 TESTANDO OUTROS PRODUTOS:")
        print("-"*70)
        
        produtos_teste = ['4080177', '4320162', '4729098']
        
        for cod in produtos_teste:
            projecao = ServicoEstoqueTempoReal.get_projecao_completa(cod, dias=7)
            if projecao:
                resumo = converter_projecao_para_resumo(projecao)
                print(f"\nProduto {cod}:")
                print(f"  Estoque: {resumo['estoque_atual']:,.0f} | "
                      f"Ruptura 7d: {resumo['menor_estoque_d7']:,.0f} | "
                      f"Carteira: {resumo['qtd_total_carteira']:,.0f} | "
                      f"Produção: {resumo['qtd_total_producao']:,.0f} | "
                      f"Status: {resumo['status_ruptura']}")

if __name__ == "__main__":
    testar_melhorias()
#!/usr/bin/env python3
"""
Script de debug detalhado para rastrear onde o produto 4159301 está sendo bloqueado
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text, and_, or_, func, exists
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def debug_produto():
    """Debug completo do produto 4159301"""
    
    app = create_app()
    cod_produto = '4159301'
    
    with app.app_context():
        print("=" * 80)
        print(f"DEBUG COMPLETO DO PRODUTO {cod_produto}")
        print("=" * 80)
        
        # ========== PARTE 1: VERIFICAÇÃO BÁSICA ==========
        print("\n📋 PARTE 1: VERIFICAÇÃO NAS TABELAS PRINCIPAIS")
        print("-" * 60)
        
        # 1.1 CarteiraPrincipal
        from app.carteira.models import CarteiraPrincipal
        
        # Query direta
        result = db.session.execute(
            text("SELECT COUNT(*) FROM carteira_principal WHERE cod_produto = :cod"),
            {"cod": cod_produto}
        )
        count_sql = result.scalar()
        print(f"\n1.1 CarteiraPrincipal (SQL direto): {count_sql} registros")
        
        # Query via ORM
        count_orm = CarteiraPrincipal.query.filter_by(cod_produto=cod_produto).count()
        print(f"1.1 CarteiraPrincipal (ORM): {count_orm} registros")
        
        # Detalhes
        itens = CarteiraPrincipal.query.filter_by(cod_produto=cod_produto).all()
        if itens:
            print("\nDetalhes dos registros encontrados:")
            for item in itens[:3]:
                print(f"  - Pedido: {item.num_pedido}")
                print(f"    Nome: {item.nome_produto}")
                print(f"    Qtd Saldo: {item.qtd_saldo_produto_pedido}")
                print(f"    Ativo: {item.ativo}")
                print(f"    Created: {item.created_at}")
                print()
        
        # 1.2 CadastroPalletizacao
        from app.producao.models import CadastroPalletizacao
        
        print("\n1.2 CadastroPalletizacao:")
        cadastro = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        if cadastro:
            print(f"  ✅ EXISTE - Nome: {cadastro.nome_produto}")
            print(f"     Palletização: {cadastro.palletizacao}")
            print(f"     Peso: {cadastro.peso_bruto}")
            print(f"     Ativo: {cadastro.ativo}")
        else:
            print(f"  ❌ NÃO EXISTE - ESTE É O PROBLEMA!")
        
        # ========== PARTE 2: TESTE DA QUERY DO AGRUPAMENTO ==========
        print("\n📊 PARTE 2: TESTE DA QUERY DE AGRUPAMENTO")
        print("-" * 60)
        
        from app.carteira.models import SaldoStandby
        
        # 2.1 Verificar se há pedidos do produto em standby
        pedidos_produto = [item.num_pedido for item in itens]
        if pedidos_produto:
            standby_count = SaldoStandby.query.filter(
                SaldoStandby.num_pedido.in_(pedidos_produto),
                SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
            ).count()
            
            print(f"\n2.1 Pedidos em Standby: {standby_count}")
            if standby_count > 0:
                print("  ⚠️ PEDIDOS BLOQUEADOS POR STANDBY!")
        
        # 2.2 Simular query exata do AgrupamentoService
        print("\n2.2 Simulando query do AgrupamentoService:")
        
        # Query que busca pedidos com o produto
        query_pedidos = db.session.query(
            CarteiraPrincipal.num_pedido,
            func.count(CarteiraPrincipal.id).label('total_itens'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('qtd_total')
        ).filter(
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.ativo == True,
            ~exists().where(
                and_(
                    SaldoStandby.num_pedido == CarteiraPrincipal.num_pedido,
                    SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
                )
            )
        ).group_by(
            CarteiraPrincipal.num_pedido
        ).all()
        
        print(f"  Pedidos encontrados na query agrupada: {len(query_pedidos)}")
        for pedido in query_pedidos:
            print(f"    - {pedido.num_pedido}: {pedido.total_itens} itens, qtd_total: {pedido.qtd_total}")
        
        # 2.3 Teste com LEFT JOIN do CadastroPalletizacao
        print("\n2.3 Teste com LEFT JOIN (como no AgrupamentoService):")
        
        query_com_join = db.session.query(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
            CarteiraPrincipal.qtd_saldo_produto_pedido,
            CadastroPalletizacao.palletizacao,
            CadastroPalletizacao.peso_bruto
        ).outerjoin(
            CadastroPalletizacao,
            and_(
                CarteiraPrincipal.cod_produto == CadastroPalletizacao.cod_produto,
                CadastroPalletizacao.ativo == True
            )
        ).filter(
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.ativo == True
        ).all()
        
        print(f"  Registros com LEFT JOIN: {len(query_com_join)}")
        for reg in query_com_join[:3]:
            print(f"    - Pedido: {reg.num_pedido}")
            print(f"      Produto: {reg.cod_produto} - {reg.nome_produto}")
            print(f"      Qtd: {reg.qtd_saldo_produto_pedido}")
            print(f"      Palletização: {reg.palletizacao or 'NULL (SEM CADASTRO)'}")
            print(f"      Peso: {reg.peso_bruto or 'NULL (SEM CADASTRO)'}")
        
        # ========== PARTE 3: VERIFICAR FILTROS ADICIONAIS ==========
        print("\n🔍 PARTE 3: VERIFICAÇÃO DE FILTROS")
        print("-" * 60)
        
        # 3.1 Verificar se pedidos são Odoo
        print("\n3.1 Verificando prefixos dos pedidos:")
        for pedido in pedidos_produto[:5]:
            is_odoo = pedido.startswith(('VSC', 'VCD', 'VFB'))
            print(f"  {pedido}: {'✅ Odoo' if is_odoo else '❌ Não-Odoo'}")
        
        # 3.2 Verificar se há algum filtro por data
        from datetime import datetime, timedelta
        hoje = datetime.now().date()
        
        itens_com_expedicao_futura = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.expedicao > hoje
        ).count()
        
        print(f"\n3.2 Itens com expedição futura: {itens_com_expedicao_futura}")
        
        # ========== PARTE 4: DIAGNÓSTICO FINAL ==========
        print("\n" + "=" * 80)
        print("DIAGNÓSTICO FINAL:")
        print("=" * 80)
        
        problemas = []
        
        if count_orm == 0:
            problemas.append("❌ Produto NÃO existe na CarteiraPrincipal")
        elif not all(item.ativo for item in itens):
            problemas.append("⚠️ Alguns registros estão INATIVOS")
        
        if not cadastro:
            problemas.append("❌ Produto NÃO existe no CadastroPalletizacao")
        elif cadastro and not cadastro.ativo:
            problemas.append("⚠️ CadastroPalletizacao está INATIVO")
        
        if standby_count > 0:
            problemas.append("⚠️ Pedidos bloqueados por STANDBY")
        
        if problemas:
            print("\n🔴 PROBLEMAS ENCONTRADOS:")
            for problema in problemas:
                print(f"  {problema}")
            
            print("\n🔧 SOLUÇÕES:")
            if not cadastro:
                print("  1. Criar registro no CadastroPalletizacao:")
                print("     python debug_produto_4159301.py --fix")
            if standby_count > 0:
                print("  2. Verificar/remover pedidos do standby")
        else:
            print("\n✅ Nenhum problema óbvio encontrado.")
            print("   O produto deveria aparecer normalmente.")
            print("\n💡 Verificações adicionais:")
            print("  - Reiniciar o servidor Flask")
            print("  - Verificar cache do navegador")
            print("  - Verificar logs do servidor")
        
        return len(problemas) == 0

def corrigir_cadastro():
    """Cria CadastroPalletizacao para o produto"""
    
    app = create_app()
    cod_produto = '4159301'
    
    with app.app_context():
        from app.producao.models import CadastroPalletizacao
        from app.carteira.models import CarteiraPrincipal
        
        print("\n🔧 CORREÇÃO AUTOMÁTICA")
        print("-" * 60)
        
        # Verificar se já existe
        existe = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        if existe:
            if not existe.ativo:
                print("⚠️ Produto existe mas está INATIVO. Ativando...")
                existe.ativo = True
                db.session.commit()
                print("✅ Produto ativado!")
            else:
                print("ℹ️ Produto já existe e está ativo no CadastroPalletizacao")
            return
        
        # Buscar dados na CarteiraPrincipal
        item = CarteiraPrincipal.query.filter_by(cod_produto=cod_produto).first()
        if not item:
            print("❌ Produto não encontrado na CarteiraPrincipal")
            return
        
        # Criar cadastro
        novo = CadastroPalletizacao(
            cod_produto=cod_produto,
            nome_produto=item.nome_produto or f'Produto {cod_produto}',
            palletizacao=1.0,
            peso_bruto=1.0,
            ativo=True,
            created_by='DebugScript',
            updated_by='DebugScript'
        )
        
        db.session.add(novo)
        db.session.commit()
        
        print(f"✅ CadastroPalletizacao criado com sucesso!")
        print(f"   Código: {novo.cod_produto}")
        print(f"   Nome: {novo.nome_produto}")
        print(f"   Palletização: {novo.palletizacao}")
        print(f"   Peso: {novo.peso_bruto}")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--fix':
        corrigir_cadastro()
    else:
        sucesso = debug_produto()
        if not sucesso:
            print("\n💡 Execute com --fix para corrigir automaticamente:")
            print("   python debug_produto_4159301.py --fix")
        sys.exit(0 if sucesso else 1)
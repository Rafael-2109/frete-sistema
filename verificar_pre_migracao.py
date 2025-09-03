#!/usr/bin/env python3
"""
Script de Verificação Pré-Migração
Data: 2025-01-29

Verifica se o sistema está pronto para a migração Pedido → VIEW
"""

import os
import sys
from datetime import datetime

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.faturamento.models import FaturamentoProduto
from sqlalchemy import func, and_

def verificar_integridade():
    """
    Verifica a integridade dos dados antes da migração
    """
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("VERIFICAÇÃO PRÉ-MIGRAÇÃO")
        print("=" * 60)
        
        problemas = []
        avisos = []
        
        # 1. Verificar pedidos sem lote
        print("\n📊 Verificando Pedidos...")
        
        pedidos_sem_lote = Pedido.query.filter(
            Pedido.separacao_lote_id.is_(None)
        ).count()
        
        if pedidos_sem_lote > 0:
            avisos.append(f"⚠️ {pedidos_sem_lote} pedidos sem separacao_lote_id (serão ignorados na VIEW)")
        
        # 2. Verificar pedidos com lote mas sem separação
        pedidos_com_lote = db.session.query(
            Pedido.separacao_lote_id,
            Pedido.num_pedido,
            Pedido.nf
        ).filter(
            Pedido.separacao_lote_id.isnot(None)
        ).all()
        
        print(f"   Total de pedidos com lote: {len(pedidos_com_lote)}")
        
        pedidos_sem_separacao = []
        for pedido in pedidos_com_lote:
            sep_existe = Separacao.query.filter_by(
                separacao_lote_id=pedido.separacao_lote_id
            ).first()
            
            if not sep_existe:
                pedidos_sem_separacao.append(pedido)
        
        if pedidos_sem_separacao:
            problemas.append(f"❌ {len(pedidos_sem_separacao)} pedidos com lote mas SEM separação correspondente!")
            print("\n   Pedidos sem separação (primeiros 10):")
            for p in pedidos_sem_separacao[:10]:
                print(f"      - Lote: {p.separacao_lote_id}, Pedido: {p.num_pedido}, NF: {p.nf}")
        
        # 3. Verificar separações órfãs
        print("\n📊 Verificando Separações...")
        
        lotes_separacao = db.session.query(
            func.distinct(Separacao.separacao_lote_id)
        ).filter(
            Separacao.separacao_lote_id.isnot(None)
        ).all()
        
        print(f"   Total de lotes em Separacao: {len(lotes_separacao)}")
        
        separacoes_orfas = []
        for lote in lotes_separacao:
            pedido_existe = Pedido.query.filter_by(
                separacao_lote_id=lote[0]
            ).first()
            
            if not pedido_existe:
                separacoes_orfas.append(lote[0])
        
        if separacoes_orfas:
            avisos.append(f"⚠️ {len(separacoes_orfas)} lotes em Separacao sem Pedido correspondente")
        
        # 4. Verificar pedidos com NF mas sem produtos no faturamento
        print("\n📊 Verificando Faturamento...")
        
        pedidos_com_nf = Pedido.query.filter(
            and_(
                Pedido.nf.isnot(None),
                Pedido.nf != ''
            )
        ).all()
        
        print(f"   Total de pedidos com NF: {len(pedidos_com_nf)}")
        
        nfs_sem_produtos = []
        for pedido in pedidos_com_nf:
            produtos = FaturamentoProduto.query.filter_by(
                numero_nf=pedido.nf
            ).first()
            
            if not produtos:
                nfs_sem_produtos.append(pedido.nf)
        
        if nfs_sem_produtos:
            avisos.append(f"⚠️ {len(nfs_sem_produtos)} NFs sem produtos em FaturamentoProduto")
            if len(nfs_sem_produtos) <= 10:
                print(f"   NFs sem produtos: {', '.join(nfs_sem_produtos)}")
        
        # 5. Verificar duplicação de lotes
        print("\n📊 Verificando duplicações...")
        
        lotes_duplicados = db.session.query(
            Pedido.separacao_lote_id,
            func.count(Pedido.id)
        ).filter(
            Pedido.separacao_lote_id.isnot(None)
        ).group_by(
            Pedido.separacao_lote_id
        ).having(
            func.count(Pedido.id) > 1
        ).all()
        
        if lotes_duplicados:
            problemas.append(f"❌ {len(lotes_duplicados)} lotes duplicados em Pedido!")
            for lote, count in lotes_duplicados[:5]:
                print(f"      - Lote {lote}: {count} pedidos")
        
        # 6. Verificar campos críticos
        print("\n📊 Verificando campos críticos...")
        
        # Verificar se campos novos existem
        try:
            # Testar acesso aos campos novos
            test_sep = Separacao.query.first()
            if test_sep:
                _ = test_sep.status
                _ = test_sep.cotacao_id
                print("   ✅ Campos novos em Separacao parecem OK")
        except AttributeError as e:
            problemas.append(f"❌ Campos novos não encontrados em Separacao: {e}")
        
        # RESUMO
        print("\n" + "=" * 60)
        print("RESUMO DA VERIFICAÇÃO")
        print("=" * 60)
        
        if problemas:
            print("\n❌ PROBLEMAS CRÍTICOS ENCONTRADOS:")
            for p in problemas:
                print(f"   {p}")
            print("\n⚠️ RESOLVA OS PROBLEMAS ANTES DE MIGRAR!")
            print("\n💡 SUGESTÃO: Execute primeiro:")
            print("   python recompor_separacoes_perdidas.py")
            return False
        
        if avisos:
            print("\n⚠️ AVISOS (não impedem migração):")
            for a in avisos:
                print(f"   {a}")
        
        if not problemas:
            print("\n✅ SISTEMA PRONTO PARA MIGRAÇÃO!")
            print("\n📋 Estatísticas:")
            print(f"   - Pedidos com lote: {len(pedidos_com_lote)}")
            print(f"   - Lotes em Separacao: {len(lotes_separacao)}")
            print(f"   - Pedidos com NF: {len(pedidos_com_nf)}")
            return True
        
        return False

if __name__ == "__main__":
    if verificar_integridade():
        sys.exit(0)  # Sucesso
    else:
        sys.exit(1)  # Falha
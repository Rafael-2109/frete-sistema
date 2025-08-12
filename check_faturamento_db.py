#!/usr/bin/env python3
"""
Script para verificar o estado do faturamento no banco
"""

import sys
import os
sys.path.insert(0, '.')
os.environ['FLASK_ENV'] = 'development'

from app import create_app, db
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from datetime import datetime, timedelta

app = create_app()
with app.app_context():
    print("=" * 60)
    print("VERIFICAÇÃO DO FATURAMENTO NO BANCO")
    print("=" * 60)
    
    # 1. Verificar FaturamentoProduto
    print("\n1. FaturamentoProduto:")
    print("-" * 40)
    
    total_fat = db.session.query(FaturamentoProduto).count()
    print(f"Total de registros: {total_fat}")
    
    # Últimos 5 registros
    ultimos_fat = db.session.query(FaturamentoProduto).order_by(
        FaturamentoProduto.created_at.desc()
    ).limit(5).all()
    
    if ultimos_fat:
        print("\nÚltimos 5 registros FaturamentoProduto:")
        for item in ultimos_fat:
            print(f"  NF: {item.numero_nf} | Produto: {item.cod_produto} | "
                  f"Cliente: {item.nome_cliente} | Status: {item.status_nf} | "
                  f"Criado: {item.created_at}")
    
    # 2. Verificar RelatorioFaturamentoImportado
    print("\n2. RelatorioFaturamentoImportado:")
    print("-" * 40)
    
    total_rel = db.session.query(RelatorioFaturamentoImportado).count()
    print(f"Total de registros: {total_rel}")
    
    # Últimos 5 registros
    ultimos_rel = db.session.query(RelatorioFaturamentoImportado).order_by(
        RelatorioFaturamentoImportado.criado_em.desc()
    ).limit(5).all()
    
    if ultimos_rel:
        print("\nÚltimos 5 registros RelatorioFaturamentoImportado:")
        for rel in ultimos_rel:
            print(f"  NF: {rel.numero_nf} | Cliente: {rel.nome_cliente} | "
                  f"Valor: R$ {rel.valor_total:.2f if rel.valor_total else 0} | "
                  f"Criado: {rel.criado_em}")
    else:
        print("⚠️ NENHUM registro em RelatorioFaturamentoImportado!")
    
    # 3. Verificar registros de hoje
    print("\n3. Registros criados HOJE:")
    print("-" * 40)
    
    hoje = datetime.now().date()
    inicio_dia = datetime.combine(hoje, datetime.min.time())
    
    fat_hoje = db.session.query(FaturamentoProduto).filter(
        FaturamentoProduto.created_at >= inicio_dia
    ).count()
    
    rel_hoje = db.session.query(RelatorioFaturamentoImportado).filter(
        RelatorioFaturamentoImportado.criado_em >= inicio_dia
    ).count()
    
    print(f"FaturamentoProduto criados hoje: {fat_hoje}")
    print(f"RelatorioFaturamentoImportado criados hoje: {rel_hoje}")
    
    # 4. Verificar data da última sincronização
    print("\n4. Última Sincronização:")
    print("-" * 40)
    
    ultima_nf = db.session.query(RelatorioFaturamentoImportado).order_by(
        RelatorioFaturamentoImportado.criado_em.desc()
    ).first()
    
    if ultima_nf:
        print(f"✅ Última sincronização: {ultima_nf.criado_em.strftime('%d/%m/%Y %H:%M')}")
        print(f"   NF: {ultima_nf.numero_nf} - {ultima_nf.nome_cliente}")
    else:
        print("❌ Nenhuma sincronização encontrada em RelatorioFaturamentoImportado")
    
    print("\n" + "=" * 60)
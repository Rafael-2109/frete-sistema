#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para verificar como o Odoo está enviando NFs canceladas
Analisa a NF 137713 como exemplo
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from app.estoque.models import MovimentacaoEstoque
from sqlalchemy import text
import json

def verificar_nf_137713():
    """Verifica o status da NF 137713 no banco"""
    print("\n=== VERIFICANDO NF 137713 ===\n")
    
    # 1. Buscar em FaturamentoProduto
    print("1. Buscando em FaturamentoProduto...")
    itens_faturamento = FaturamentoProduto.query.filter_by(numero_nf='137713').all()
    
    if itens_faturamento:
        print(f"✓ Encontrados {len(itens_faturamento)} itens")
        for item in itens_faturamento:
            print(f"  - Produto: {item.cod_produto}")
            print(f"    Status: '{item.status_nf}'")
            print(f"    Created by: {item.created_by}")
            print(f"    Data: {item.data_fatura}")
            print(f"    Cliente: {item.cnpj_cliente} - {item.nome_cliente}")
            print()
    else:
        print("✗ NF não encontrada em FaturamentoProduto")
    
    # 2. Buscar em RelatorioFaturamentoImportado
    print("\n2. Buscando em RelatorioFaturamentoImportado...")
    relatorio = RelatorioFaturamentoImportado.query.filter_by(numero_nf='137713').first()
    
    if relatorio:
        print("✓ Encontrado no relatório consolidado")
        print(f"  Ativo: {relatorio.ativo}")
        print(f"  Data: {relatorio.data_fatura}")
        print(f"  Valor: R$ {relatorio.valor_total}")
        if not relatorio.ativo:
            print(f"  Inativado em: {relatorio.inativado_em}")
            print(f"  Inativado por: {relatorio.inativado_por}")
    else:
        print("✗ NF não encontrada em RelatorioFaturamentoImportado")
    
    # 3. Buscar movimentações de estoque
    print("\n3. Buscando movimentações de estoque...")
    movimentacoes = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.observacao.like('%137713%')
    ).all()
    
    if movimentacoes:
        print(f"⚠️ ENCONTRADAS {len(movimentacoes)} movimentações!")
        for mov in movimentacoes:
            print(f"  - Produto: {mov.cod_produto}")
            print(f"    Quantidade: {mov.qtd_movimentacao}")
            print(f"    Data: {mov.data_movimentacao}")
            print(f"    Observação: {mov.observacao}")
            print()
    else:
        print("✓ Nenhuma movimentação encontrada (correto se cancelada)")
    
    return itens_faturamento

def buscar_nfs_odoo_com_status():
    """Busca exemplos de NFs do Odoo com diferentes status"""
    print("\n=== ANALISANDO STATUS DE NFs DO ODOO ===\n")
    
    # Query para ver diferentes valores de status_nf
    query = text("""
        SELECT DISTINCT status_nf, COUNT(*) as qtd
        FROM faturamento_produto
        WHERE created_by IN ('Sistema Odoo', 'ImportOdoo', 'ImportTagPlus')
        GROUP BY status_nf
        ORDER BY qtd DESC
    """)
    
    resultados = db.session.execute(query).fetchall()
    
    print("Status encontrados no banco:")
    for row in resultados:
        print(f"  '{row.status_nf}': {row.qtd} registros")
    
    # Buscar exemplos de cada status
    print("\n\nExemplos de NFs por status:")
    
    for status, _ in resultados[:5]:  # Top 5 status
        exemplo = FaturamentoProduto.query.filter_by(
            status_nf=status
        ).filter(
            FaturamentoProduto.created_by.in_(['Sistema Odoo', 'ImportOdoo'])
        ).first()
        
        if exemplo:
            print(f"\nStatus '{status}':")
            print(f"  NF: {exemplo.numero_nf}")
            print(f"  Data: {exemplo.data_fatura}")
            print(f"  Created by: {exemplo.created_by}")

def verificar_mapeamento_status():
    """Verifica como o status está sendo mapeado do Odoo"""
    print("\n=== VERIFICANDO MAPEAMENTO DE STATUS ===\n")
    
    # Simular o mapeamento que está no código
    status_map = {
        'draft': 'RASCUNHO',
        'posted': 'ATIVO', 
        'cancel': 'CANCELADO',
        'sale': 'ATIVO',
        'done': 'ATIVO',
        'sent': 'ATIVO'
    }
    
    print("Mapeamento atual no código:")
    for odoo_status, sistema_status in status_map.items():
        print(f"  '{odoo_status}' -> '{sistema_status}'")
    
    print("\n⚠️ IMPORTANTE:")
    print("  - Odoo envia 'cancel' que é mapeado para 'CANCELADO'")
    print("  - Mas o código está verificando se status_odoo == 'CANCELADO'")
    print("  - DEVERIA verificar se status_odoo == 'cancel' (antes do mapeamento)")
    print("    OU verificar se status_mapeado == 'CANCELADO' (após mapeamento)")

def buscar_dados_odoo_brutos():
    """Tenta buscar dados brutos do Odoo para ver o formato real"""
    print("\n=== BUSCANDO DADOS BRUTOS DO ODOO ===\n")
    
    try:
        from app.odoo.services.odoo_service import OdooService
        
        odoo_service = OdooService()
        
        # Tentar buscar a NF 137713 diretamente do Odoo
        print("Tentando buscar NF 137713 do Odoo...")
        
        # Buscar faturas com número específico
        domain = [['name', '=', '137713']]
        fields = ['name', 'state', 'date', 'partner_id', 'amount_total']
        
        faturas = odoo_service.search_read('account.move', domain, fields, limit=1)
        
        if faturas:
            print("✓ NF encontrada no Odoo!")
            fatura = faturas[0]
            print(f"  Dados brutos:")
            print(json.dumps(fatura, indent=2, default=str))
            print(f"\n  ⚠️ Estado no Odoo: '{fatura.get('state')}'")
            
            if fatura.get('state') == 'cancel':
                print("  ✅ A NF está CANCELADA no Odoo (state='cancel')")
            else:
                print(f"  ❌ A NF não está cancelada. Estado: {fatura.get('state')}")
        else:
            print("✗ NF 137713 não encontrada no Odoo")
            
    except Exception as e:
        print(f"Erro ao buscar do Odoo: {e}")
        print("Continuando análise com dados locais...")

def main():
    print("="*60)
    print("ANÁLISE DE NF CANCELADA - 137713")
    print("="*60)
    
    # 1. Verificar NF específica
    itens = verificar_nf_137713()
    
    # 2. Analisar status no banco
    buscar_nfs_odoo_com_status()
    
    # 3. Verificar mapeamento
    verificar_mapeamento_status()
    
    # 4. Tentar buscar dados brutos
    buscar_dados_odoo_brutos()
    
    # 5. Diagnóstico
    print("\n" + "="*60)
    print("DIAGNÓSTICO FINAL")
    print("="*60)
    
    if itens and itens[0].status_nf != 'CANCELADO':
        print("\n❌ PROBLEMA IDENTIFICADO:")
        print(f"  A NF 137713 tem status '{itens[0].status_nf}' no banco")
        print("  Mas deveria ter status 'CANCELADO' se está cancelada no Odoo")
        print("\n  POSSÍVEIS CAUSAS:")
        print("  1. O mapeamento de status não está sendo aplicado corretamente")
        print("  2. A verificação está sendo feita no momento errado")
        print("  3. O status 'cancel' do Odoo não está sendo detectado")
        print("\n  SOLUÇÃO:")
        print("  Verificar se status_odoo == 'cancel' ANTES do mapeamento")
        print("  OU verificar o campo já mapeado após UPDATE")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        main()
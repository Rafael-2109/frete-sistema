#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para testar a detecção de NFs canceladas após correção
Verifica se a NF 137713 será detectada como cancelada
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
from app.estoque.models import MovimentacaoEstoque
from app.odoo.services.faturamento_service import FaturamentoService
from datetime import datetime, timedelta

def verificar_estado_inicial():
    """Verifica o estado inicial da NF 137713"""
    print("\n=== ESTADO INICIAL DA NF 137713 ===\n")
    
    # Buscar NF
    nf_items = FaturamentoProduto.query.filter_by(numero_nf='137713').all()
    
    if nf_items:
        print(f"✓ NF encontrada com {len(nf_items)} itens")
        print(f"  Status atual: '{nf_items[0].status_nf}'")
    else:
        print("✗ NF não encontrada")
        return False
    
    # Buscar movimentações
    movs = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.observacao.like('%137713%')
    ).all()
    
    print(f"\nMovimentações de estoque: {len(movs)} encontradas")
    
    return True

def simular_sincronizacao():
    """Simula a sincronização com Odoo para testar detecção de cancelamento"""
    print("\n=== SIMULANDO SINCRONIZAÇÃO COM ODOO ===\n")
    
    try:
        # Criar serviço
        service = FaturamentoService()
        
        # Data de hoje e 30 dias atrás para incluir a NF
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=90)  # Buscar últimos 90 dias
        
        print(f"Sincronizando período: {data_inicio.date()} até {data_fim.date()}")
        print("NOTA: Verificando se NF 137713 está cancelada no Odoo...")
        print("      Se estiver com state='cancel', deve processar cancelamento\n")
        
        # Executar sincronização
        # O método sincronizar_faturamento_incremental usa um filtro de data fixo interno
        # Vamos chamar direto, ele busca últimos 30 dias automaticamente
        resultado = service.sincronizar_faturamento_incremental()
        
        if resultado['sucesso']:
            print("✅ Sincronização concluída com sucesso!")
            print(f"\nEstatísticas:")
            stats = resultado.get('estatisticas', {})
            print(f"  - Novos registros: {stats.get('novos', 0)}")
            print(f"  - Atualizados: {stats.get('atualizados', 0)}")
            print(f"  - NFs canceladas processadas: {stats.get('nfs_canceladas_processadas', 0)}")
            print(f"  - Movimentações removidas: {stats.get('movimentacoes_removidas', 0)}")
            
            # Verificar se NF 137713 foi processada
            if stats.get('nfs_canceladas_processadas', 0) > 0:
                print("\n🎉 SUCESSO: Cancelamentos foram detectados e processados!")
            else:
                print("\n⚠️ Nenhum cancelamento detectado")
        else:
            print(f"❌ Erro na sincronização: {resultado.get('erro')}")
            
    except Exception as e:
        print(f"❌ Erro ao executar sincronização: {e}")
        import traceback
        traceback.print_exc()

def verificar_estado_final():
    """Verifica o estado após sincronização"""
    print("\n=== ESTADO FINAL DA NF 137713 ===\n")
    
    # Buscar NF
    nf_items = FaturamentoProduto.query.filter_by(numero_nf='137713').all()
    
    if nf_items:
        print(f"✓ NF encontrada com {len(nf_items)} itens")
        status = nf_items[0].status_nf
        print(f"  Status: '{status}'")
        
        if status == 'CANCELADO':
            print("  ✅ Status corretamente atualizado para CANCELADO")
        else:
            print(f"  ⚠️ Status ainda é '{status}' (esperado: CANCELADO)")
    
    # Buscar movimentações
    movs = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.observacao.like('%137713%')
    ).all()
    
    print(f"\nMovimentações de estoque: {len(movs)}")
    if len(movs) == 0:
        print("  ✅ Movimentações removidas corretamente")
    else:
        print(f"  ⚠️ Ainda existem {len(movs)} movimentações")
        for mov in movs[:3]:  # Mostrar até 3
            print(f"    - {mov.cod_produto}: {mov.qtd_movimentacao}")

def main():
    print("="*60)
    print("TESTE DE DETECÇÃO DE NF CANCELADA")
    print("="*60)
    
    # 1. Verificar estado inicial
    if not verificar_estado_inicial():
        print("\n⚠️ NF 137713 não encontrada. Executando sincronização mesmo assim...")
    
    # 2. Executar sincronização
    simular_sincronizacao()
    
    # 3. Verificar estado final
    verificar_estado_final()
    
    print("\n" + "="*60)
    print("TESTE CONCLUÍDO")
    print("="*60)
    
    print("\n💡 DICA: Se o cancelamento não foi detectado:")
    print("  1. Verifique se a NF está realmente cancelada no Odoo")
    print("  2. Verifique se o campo 'state' está vindo como 'cancel'")
    print("  3. Verifique os logs para mensagens com '🚨'")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        main()
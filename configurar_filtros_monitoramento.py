#!/usr/bin/env python3
"""
🔧 CONFIGURAR FILTROS DE MONITORAMENTO

Este script demonstra e permite configurar os filtros que controlam quais NFs
vão para o monitoramento de entregas.

Filtros disponíveis:
1. 🚫 NFs FOB (ATIVO por padrão) - Não monitora NFs com frete por conta do cliente
2. 🚫 NFs em embarques FOB (SEMPRE ATIVO) - Não monitora NFs já em embarques FOB
3. 🚫 Todas NFs em embarques (INATIVO por padrão) - Não monitora NFs já em qualquer embarque

Uso: python configurar_filtros_monitoramento.py [--ativar-todos] [--desativar-fob]
"""

import sys
import os
import argparse

# Adiciona o diretório pai ao Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.faturamento.models import RelatorioFaturamentoImportado  
from app.monitoramento.models import EntregaMonitorada
from app.embarques.models import EmbarqueItem, Embarque

def analisar_impacto():
    """Analisa o impacto de cada filtro no monitoramento"""
    
    print("📊 ANÁLISE DE IMPACTO DOS FILTROS")
    print("=" * 60)
    
    # Dados básicos
    total_faturamento = RelatorioFaturamentoImportado.query.filter_by(ativo=True).count()
    total_monitoramento = EntregaMonitorada.query.count()
    
    print(f"\n📋 SITUAÇÃO ATUAL:")
    print(f"   • Total NFs ativas no faturamento: {total_faturamento}")
    print(f"   • Total NFs no monitoramento: {total_monitoramento}")
    
    # FILTRO 1: NFs FOB
    nfs_fob = RelatorioFaturamentoImportado.query.filter(
        RelatorioFaturamentoImportado.incoterm.ilike('%FOB%'),
        RelatorioFaturamentoImportado.ativo == True
    ).count()
    
    nfs_fob_monitoradas = (
        db.session.query(EntregaMonitorada)
        .join(RelatorioFaturamentoImportado, EntregaMonitorada.numero_nf == RelatorioFaturamentoImportado.numero_nf)
        .filter(RelatorioFaturamentoImportado.incoterm.ilike('%FOB%'))
        .count()
    )
    
    print(f"\n🚫 FILTRO 1 - NFs FOB:")
    print(f"   • Total NFs FOB: {nfs_fob}")
    print(f"   • NFs FOB atualmente no monitoramento: {nfs_fob_monitoradas}")
    if total_monitoramento > 0:
        perc_fob = (nfs_fob_monitoradas / total_monitoramento) * 100
        print(f"   • Impacto: {perc_fob:.1f}% do monitoramento atual")
    
    # FILTRO 2: NFs em embarques FOB
    nfs_embarque_fob = (
        db.session.query(EmbarqueItem.nota_fiscal)
        .join(Embarque, Embarque.id == EmbarqueItem.embarque_id)
        .filter(Embarque.tipo_carga == 'FOB')
        .distinct()
        .count()
    )
    
    nfs_embarque_fob_monitoradas = (
        db.session.query(EntregaMonitorada)
        .join(EmbarqueItem, EntregaMonitorada.numero_nf == EmbarqueItem.nota_fiscal)
        .join(Embarque, Embarque.id == EmbarqueItem.embarque_id)
        .filter(Embarque.tipo_carga == 'FOB')
        .count()
    )
    
    print(f"\n🚫 FILTRO 2 - NFs em embarques FOB:")
    print(f"   • Total NFs em embarques FOB: {nfs_embarque_fob}")
    print(f"   • NFs de embarques FOB atualmente no monitoramento: {nfs_embarque_fob_monitoradas}")
    
    # FILTRO 3: REMOVIDO - Não filtramos mais TODAS as NFs em embarques
    # Apenas embarques FOB são filtrados (FILTRO 2)
    print(f"\n✅ FILTRO 3 - REMOVIDO:")
    print(f"   • NFs em embarques não-FOB DEVEM estar no monitoramento")
    print(f"   • Apenas NFs FOB são filtradas automaticamente")
    
    # Resumo combinado
    print(f"\n📊 RESUMO DOS IMPACTOS:")
    total_impacto = nfs_fob_monitoradas + nfs_embarque_fob_monitoradas
    if total_monitoramento > 0:
        perc_total = (total_impacto / total_monitoramento) * 100
        print(f"   • Impacto total dos filtros: {total_impacto} NFs ({perc_total:.1f}%)")
    print(f"   • Apenas NFs FOB são filtradas do monitoramento")
    
    return {
        'nfs_fob': nfs_fob_monitoradas,
        'nfs_embarque_fob': nfs_embarque_fob_monitoradas, 
        'total_monitoramento': total_monitoramento
    }

def mostrar_configuracao_atual():
    """Mostra a configuração atual dos filtros"""
    from flask import current_app
    
    print("\n⚙️ CONFIGURAÇÃO ATUAL DOS FILTROS:")
    print("-" * 40)
    
    filtrar_fob = getattr(current_app.config, 'FILTRAR_FOB_MONITORAMENTO', True)
    filtrar_embarques = getattr(current_app.config, 'FILTRAR_EMBARQUES_MONITORAMENTO', False)
    
    status_fob = "🟢 ATIVO" if filtrar_fob else "🔴 INATIVO"
    status_embarques = "🟢 ATIVO" if filtrar_embarques else "🔴 INATIVO"
    
    print(f"   1. Filtrar NFs FOB: {status_fob}")
    print(f"   2. Filtrar NFs em embarques FOB: 🟢 SEMPRE ATIVO")
    print(f"   3. Filtrar TODAS NFs em embarques: {status_embarques}")

def exemplo_configuracao():
    """Mostra exemplos de como configurar os filtros"""
    
    print("\n🔧 COMO CONFIGURAR OS FILTROS:")
    print("-" * 40)
    print("   Para ATIVAR filtro de NFs FOB (padrão):")
    print("   ➤ Variável: FILTRAR_FOB_MONITORAMENTO=True")
    print("   ➤ Ou não configure (ativo por padrão)")
    
    print("\n   Para DESATIVAR filtro de NFs FOB:")
    print("   ➤ Variável: FILTRAR_FOB_MONITORAMENTO=False")
    
    print("\n   Para ATIVAR filtro de TODAS NFs em embarques:")
    print("   ➤ Variável: FILTRAR_EMBARQUES_MONITORAMENTO=True")
    print("   ➤ ATENÇÃO: Isso pode impactar significativamente o monitoramento!")
    
    print("\n💡 RECOMENDAÇÕES:")
    print("   ✅ Manter filtro FOB ativo (economia de ~4-5%)")
    print("   ⚠️ Avaliar cuidadosamente filtro de todos embarques")
    print("   🔒 Filtro de embarques FOB sempre ativo (crítico)")

def main():
    parser = argparse.ArgumentParser(description='Configurar filtros de monitoramento')
    parser.add_argument('--stats-only', action='store_true', help='Apenas mostra estatísticas')
    
    args = parser.parse_args()
    
    app = create_app()
    
    with app.app_context():
        print("🔧 CONFIGURADOR DE FILTROS DE MONITORAMENTO")
        print("=" * 60)
        
        # Análise de impacto
        stats = analisar_impacto()
        
        # Configuração atual
        mostrar_configuracao_atual()
        
        if not args.stats_only:
            # Exemplos de configuração
            exemplo_configuracao()
        
        print("\n" + "=" * 60)
        print("✅ ANÁLISE CONCLUÍDA!")
        
        if stats['nfs_fob'] > 0:
            print(f"\n💡 DICA: {stats['nfs_fob']} NFs FOB podem ser removidas do monitoramento")
            print("   Execute: python testar_filtros_monitoramento.py para testar")

if __name__ == "__main__":
    main() 
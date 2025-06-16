#!/usr/bin/env python3
"""
🧪 TESTE DOS FILTROS DE MONITORAMENTO

Este script testa os novos filtros que impedem certas NFs de irem para o monitoramento:
1. NFs com Incoterm "FOB"
2. NFs que já estão em embarques FOB

Uso: python testar_filtros_monitoramento.py
"""

import sys
import os

# Adiciona o diretório pai ao Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.faturamento.models import RelatorioFaturamentoImportado  
from app.monitoramento.models import EntregaMonitorada
from app.embarques.models import EmbarqueItem, Embarque
from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf

def main():
    app = create_app()
    
    with app.app_context():
        print("🧪 TESTANDO FILTROS DE MONITORAMENTO")
        print("=" * 60)
        
        # 1. NFs FOB
        print("\n📋 NFs COM INCOTERM FOB:")
        nfs_fob = RelatorioFaturamentoImportado.query.filter(
            RelatorioFaturamentoImportado.incoterm.ilike('%FOB%')
        ).all()
        
        if nfs_fob:
            print(f"   Encontradas {len(nfs_fob)} NFs FOB:")
            for nf in nfs_fob[:5]:  # Primeiras 5
                # Verifica se está no monitoramento
                monitorada = EntregaMonitorada.query.filter_by(numero_nf=nf.numero_nf).first()
                status = "❌ No monitoramento" if monitorada else "✅ Não monitorada"
                print(f"   • NF {nf.numero_nf} - {nf.nome_cliente[:30]}... - Incoterm: {nf.incoterm} - {status}")
        else:
            print("   Nenhuma NF FOB encontrada")
        
        # 2. NFs em embarques FOB
        print("\n🚚 NFs EM EMBARQUES FOB:")
        nfs_embarque_fob = (
            db.session.query(EmbarqueItem)
            .join(Embarque, Embarque.id == EmbarqueItem.embarque_id)
            .filter(Embarque.tipo_carga == 'FOB')
            .limit(5)
            .all()
        )
        
        if nfs_embarque_fob:
            print(f"   Encontradas {len(nfs_embarque_fob)} NFs em embarques FOB:")
            for item in nfs_embarque_fob:
                # Verifica se está no monitoramento
                monitorada = EntregaMonitorada.query.filter_by(numero_nf=item.nota_fiscal).first()
                status = "❌ No monitoramento" if monitorada else "✅ Não monitorada"
                print(f"   • NF {item.nota_fiscal} - Embarque #{item.embarque.numero} - {status}")
        else:
            print("   Nenhuma NF em embarque FOB encontrada")
        
        # 3. Teste de sincronização
        print("\n🔄 TESTANDO SINCRONIZAÇÃO:")
        
        # Testa FOB
        if nfs_fob:
            nf_teste_fob = nfs_fob[0]
            print(f"\n   📝 Testando NF FOB: {nf_teste_fob.numero_nf}")
            
            antes = EntregaMonitorada.query.filter_by(numero_nf=nf_teste_fob.numero_nf).first()
            print(f"   • Antes: {'Está no monitoramento' if antes else 'Não está no monitoramento'}")
            
            # Executa sincronização
            sincronizar_entrega_por_nf(nf_teste_fob.numero_nf)
            
            depois = EntregaMonitorada.query.filter_by(numero_nf=nf_teste_fob.numero_nf).first()
            print(f"   • Depois: {'Está no monitoramento' if depois else 'Não está no monitoramento'}")
            
            if antes and not depois:
                print(f"   ✅ SUCESSO: NF FOB removida do monitoramento!")
            elif not antes and not depois:
                print(f"   ✅ SUCESSO: NF FOB não foi adicionada ao monitoramento!")
            else:
                print(f"   ❌ FALHA: NF FOB ainda está no monitoramento!")
        
        # Testa embarque FOB
        if nfs_embarque_fob:
            item_teste = nfs_embarque_fob[0]
            print(f"\n   📝 Testando NF em embarque FOB: {item_teste.nota_fiscal}")
            
            antes = EntregaMonitorada.query.filter_by(numero_nf=item_teste.nota_fiscal).first()
            print(f"   • Antes: {'Está no monitoramento' if antes else 'Não está no monitoramento'}")
            
            # Executa sincronização
            sincronizar_entrega_por_nf(item_teste.nota_fiscal)
            
            depois = EntregaMonitorada.query.filter_by(numero_nf=item_teste.nota_fiscal).first()
            print(f"   • Depois: {'Está no monitoramento' if depois else 'Não está no monitoramento'}")
            
            if antes and not depois:
                print(f"   ✅ SUCESSO: NF de embarque FOB removida do monitoramento!")
            elif not antes and not depois:
                print(f"   ✅ SUCESSO: NF de embarque FOB não foi adicionada ao monitoramento!")
            else:
                print(f"   ❌ FALHA: NF de embarque FOB ainda está no monitoramento!")
        
        # 4. Estatísticas finais
        print("\n📊 ESTATÍSTICAS:")
        total_faturamento = RelatorioFaturamentoImportado.query.filter_by(ativo=True).count()
        total_monitoramento = EntregaMonitorada.query.count()
        total_fob = RelatorioFaturamentoImportado.query.filter(
            RelatorioFaturamentoImportado.incoterm.ilike('%FOB%'),
            RelatorioFaturamentoImportado.ativo == True
        ).count()
        
        nfs_embarque_fob_count = (
            db.session.query(EmbarqueItem.nota_fiscal)
            .join(Embarque, Embarque.id == EmbarqueItem.embarque_id)
            .filter(Embarque.tipo_carga == 'FOB')
            .distinct()
            .count()
        )
        
        nfs_embarque_nao_fob_count = (
            db.session.query(EmbarqueItem.nota_fiscal)
            .join(Embarque, Embarque.id == EmbarqueItem.embarque_id)
            .filter(Embarque.tipo_carga != 'FOB')
            .distinct()
            .count()
        )
        
        print(f"   • Total NFs ativas no faturamento: {total_faturamento}")
        print(f"   • Total NFs no monitoramento: {total_monitoramento}")
        print(f"   • Total NFs FOB: {total_fob}")
        print(f"   • Total NFs em embarques FOB: {nfs_embarque_fob_count}")
        print(f"   • Total NFs em embarques NÃO-FOB: {nfs_embarque_nao_fob_count}")
        
        potencial_reducao = total_fob + nfs_embarque_fob_count
        print(f"   • NFs filtradas do monitoramento: {potencial_reducao} NFs")
        
        if total_monitoramento > 0:
            percentual = (potencial_reducao / total_monitoramento) * 100
            print(f"   • Isso representa {percentual:.1f}% do monitoramento atual")
        
        print("\n" + "=" * 60)
        print("✅ TESTE CONCLUÍDO!")
        print("\n💡 EXPLICAÇÃO DOS FILTROS:")
        print("   🚫 NFs FOB: Frete por conta do cliente, não precisam ser monitoradas")
        print("   🚫 NFs em embarques FOB: Já têm logística definida, não precisam monitoramento")
        print("   ✅ NFs em embarques NÃO-FOB: DEVEM estar no monitoramento")
        print("   ✅ Sistema agora filtra automaticamente apenas NFs FOB!")

if __name__ == "__main__":
    main() 
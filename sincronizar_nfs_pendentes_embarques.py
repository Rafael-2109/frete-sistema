#!/usr/bin/env python3
"""
Script para sincronizar NFs pendentes entre Embarques e Monitoramento

Este script identifica e sincroniza NFs que:
1. Estão em embarques ativos
2. Têm dados no faturamento  
3. MAS não estão no monitoramento de entregas

Casos de uso:
- NF foi adicionada ao embarque ANTES de ser importada no faturamento
- Problema na sincronização automática durante importação
- Correção de inconsistências no monitoramento

Uso: python sincronizar_nfs_pendentes_embarques.py
"""

import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app import create_app, db
from app.monitoramento.models import EntregaMonitorada
from app.faturamento.models import RelatorioFaturamentoImportado
from app.embarques.models import EmbarqueItem, Embarque
from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf

def sincronizar_nfs_pendentes_completo():
    """Executa sincronização completa de NFs pendentes"""
    
    app = create_app()
    
    with app.app_context():
        print("🔄 SINCRONIZAÇÃO DE NFs PENDENTES - EMBARQUES → MONITORAMENTO")
        print("=" * 80)
        
        # 1. Diagnóstico inicial
        print("\n📊 DIAGNÓSTICO INICIAL:")
        
        # Busca TODAS as NFs que estão em embarques ativos
        nfs_em_embarques = db.session.query(EmbarqueItem.nota_fiscal).filter(
            EmbarqueItem.nota_fiscal.isnot(None),
            EmbarqueItem.nota_fiscal != '',
            EmbarqueItem.status == 'ativo'
        ).join(Embarque).filter(
            Embarque.status == 'ativo'
        ).distinct().all()
        
        nfs_em_embarques_set = {nf[0] for nf in nfs_em_embarques}
        print(f"📦 NFs em embarques ativos: {len(nfs_em_embarques_set)}")
        
        # Busca NFs que JÁ estão no monitoramento
        nfs_no_monitoramento = db.session.query(EntregaMonitorada.numero_nf).distinct().all()
        nfs_no_monitoramento_set = {nf[0] for nf in nfs_no_monitoramento}
        print(f"📊 NFs no monitoramento: {len(nfs_no_monitoramento_set)}")
        
        # Calcula NFs pendentes
        nfs_pendentes_sincronizacao = nfs_em_embarques_set - nfs_no_monitoramento_set
        print(f"⚠️ NFs pendentes de sincronização: {len(nfs_pendentes_sincronizacao)}")
        
        if not nfs_pendentes_sincronizacao:
            print("\n✅ RESULTADO: Todas as NFs de embarques já estão sincronizadas!")
            print("   Não há ação necessária.")
            return
        
        # 2. Analisa quais têm faturamento
        print(f"\n🔍 ANÁLISE DETALHADA DAS {len(nfs_pendentes_sincronizacao)} NFs PENDENTES:")
        
        nfs_com_faturamento = []
        nfs_sem_faturamento = []
        
        for nf in nfs_pendentes_sincronizacao:
            fat = RelatorioFaturamentoImportado.query.filter_by(numero_nf=nf).first()
            if fat:
                nfs_com_faturamento.append(nf)
            else:
                nfs_sem_faturamento.append(nf)
        
        print(f"✅ Com faturamento (podem ser sincronizadas): {len(nfs_com_faturamento)}")
        print(f"❌ Sem faturamento (precisam ser importadas): {len(nfs_sem_faturamento)}")
        
        # 3. Mostra exemplos
        if nfs_com_faturamento:
            print(f"\n📋 PRIMEIRAS 10 NFs COM FATURAMENTO (serão sincronizadas):")
            for i, nf in enumerate(sorted(nfs_com_faturamento)[:10]):
                print(f"   {i+1:2d}. NF {nf}")
        
        if nfs_sem_faturamento:
            print(f"\n📋 PRIMEIRAS 10 NFs SEM FATURAMENTO (precisam importação):")
            for i, nf in enumerate(sorted(nfs_sem_faturamento)[:10]):
                print(f"   {i+1:2d}. NF {nf}")
        
        # 4. Executa sincronização
        if nfs_com_faturamento:
            print(f"\n🚀 INICIANDO SINCRONIZAÇÃO DE {len(nfs_com_faturamento)} NFs...")
            
            contador_sucesso = 0
            contador_erro = 0
            
            for i, nf in enumerate(nfs_com_faturamento, 1):
                try:
                    print(f"[{i:3d}/{len(nfs_com_faturamento)}] Sincronizando NF {nf}...", end=" ")
                    sincronizar_entrega_por_nf(nf)
                    contador_sucesso += 1
                    print("✅")
                    
                    # Commit a cada 20 NFs
                    if i % 20 == 0:
                        db.session.commit()
                        print(f"    💾 Progresso salvo: {i} NFs processadas")
                        
                except Exception as e:
                    contador_erro += 1
                    print(f"❌ Erro: {str(e)}")
            
            # Commit final
            db.session.commit()
            
            print(f"\n📈 RESULTADOS DA SINCRONIZAÇÃO:")
            print(f"✅ Sincronizadas com sucesso: {contador_sucesso}")
            print(f"❌ Erros: {contador_erro}")
            
            if contador_sucesso > 0:
                print(f"\n🎉 SUCESSO! {contador_sucesso} NFs foram sincronizadas para o monitoramento!")
        
        # 5. Orientações finais
        if nfs_sem_faturamento:
            print(f"\n💡 PRÓXIMOS PASSOS PARA AS {len(nfs_sem_faturamento)} NFs RESTANTES:")
            print(f"   1. Importar essas NFs no módulo de Faturamento")
            print(f"   2. Executar este script novamente")
            print(f"   3. Ou aguardar a sincronização automática na próxima importação")
        
        print(f"\n✅ PROCESSO CONCLUÍDO!")

def listar_nfs_pendentes():
    """Lista NFs pendentes sem executar sincronização"""
    
    app = create_app()
    
    with app.app_context():
        print("📋 RELATÓRIO: NFs PENDENTES DE SINCRONIZAÇÃO")
        print("=" * 60)
        
        # Busca dados
        nfs_em_embarques = db.session.query(EmbarqueItem.nota_fiscal).filter(
            EmbarqueItem.nota_fiscal.isnot(None),
            EmbarqueItem.nota_fiscal != '',
            EmbarqueItem.status == 'ativo'
        ).join(Embarque).filter(
            Embarque.status == 'ativo'
        ).distinct().all()
        
        nfs_no_monitoramento = db.session.query(EntregaMonitorada.numero_nf).distinct().all()
        
        nfs_em_embarques_set = {nf[0] for nf in nfs_em_embarques}
        nfs_no_monitoramento_set = {nf[0] for nf in nfs_no_monitoramento}
        nfs_pendentes = nfs_em_embarques_set - nfs_no_monitoramento_set
        
        print(f"📊 Estatísticas:")
        print(f"   NFs em embarques: {len(nfs_em_embarques_set)}")
        print(f"   NFs no monitoramento: {len(nfs_no_monitoramento_set)}")
        print(f"   NFs pendentes: {len(nfs_pendentes)}")
        
        if nfs_pendentes:
            print(f"\n📋 Lista das NFs pendentes:")
            for i, nf in enumerate(sorted(nfs_pendentes), 1):
                fat = RelatorioFaturamentoImportado.query.filter_by(numero_nf=nf).first()
                status = "✅ Faturada" if fat else "❌ Não faturada"
                print(f"   {i:3d}. NF {nf} - {status}")
        else:
            print("\n✅ Nenhuma NF pendente encontrada!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--listar':
        listar_nfs_pendentes()
    else:
        sincronizar_nfs_pendentes_completo()
        
    print(f"\n💡 DICAS:")
    print(f"   - Execute 'python {sys.argv[0]} --listar' para apenas ver relatório")
    print(f"   - Execute 'python {sys.argv[0]}' para sincronizar")
    print(f"   - Monitore os logs para verificar se tudo funcionou corretamente") 
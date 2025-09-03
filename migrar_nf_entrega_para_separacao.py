#!/usr/bin/env python3
"""
Script para migrar numero_nf de EntregaMonitorada para Separacao
usando separacao_lote_id como chave de ligação

Autor: Claude AI Assistant
Data: 2025
"""

from app import create_app, db
from app.monitoramento.models import EntregaMonitorada
from app.separacao.models import Separacao
from sqlalchemy import func
from datetime import datetime

def migrar_nf_entrega_para_separacao():
    """
    Migra numero_nf de EntregaMonitorada para Separacao
    baseado no separacao_lote_id
    """
    
    print("=" * 80)
    print("MIGRAÇÃO DE NF: EntregaMonitorada → Separacao")
    print("=" * 80)
    print(f"\nIniciando em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Contadores
    total_entregas = 0
    entregas_com_lote = 0
    entregas_sem_lote = 0
    separacoes_atualizadas = 0
    separacoes_ja_tinham_nf = 0
    erros = 0
    
    try:
        # 1. Busca todas as EntregaMonitorada com numero_nf e separacao_lote_id
        print("📊 FASE 1: Analisando EntregaMonitorada...")
        
        entregas = EntregaMonitorada.query.filter(
            EntregaMonitorada.numero_nf.isnot(None),
            EntregaMonitorada.numero_nf != ''
        ).all()
        
        total_entregas = len(entregas)
        print(f"   • Total de entregas com NF: {total_entregas}")
        
        # Agrupa por separacao_lote_id para otimizar
        entregas_por_lote = {}
        for entrega in entregas:
            if entrega.separacao_lote_id:
                entregas_com_lote += 1
                if entrega.separacao_lote_id not in entregas_por_lote:
                    entregas_por_lote[entrega.separacao_lote_id] = []
                entregas_por_lote[entrega.separacao_lote_id].append(entrega)
            else:
                entregas_sem_lote += 1
        
        print(f"   • Entregas com separacao_lote_id: {entregas_com_lote}")
        print(f"   • Entregas sem separacao_lote_id: {entregas_sem_lote}")
        print(f"   • Lotes únicos identificados: {len(entregas_por_lote)}")
        
        # 2. Atualiza Separacao para cada lote
        print("\n📝 FASE 2: Atualizando Separacao...")
        
        for lote_id, entregas_lote in entregas_por_lote.items():
            try:
                # Busca todas as separações deste lote
                separacoes = Separacao.query.filter_by(
                    separacao_lote_id=lote_id
                ).all()
                
                if separacoes:
                    # Pega a primeira NF encontrada (todas devem ser iguais para o mesmo lote)
                    numero_nf = entregas_lote[0].numero_nf
                    
                    for sep in separacoes:
                        if not sep.numero_nf or sep.numero_nf == '':
                            sep.numero_nf = numero_nf
                            sep.sincronizado_nf = True  # Marca como sincronizado
                            separacoes_atualizadas += 1
                        else:
                            separacoes_ja_tinham_nf += 1
                    
                    # Commit a cada lote para evitar problemas de memória
                    db.session.commit()
                    
                    if separacoes_atualizadas % 100 == 0:
                        print(f"   ✅ {separacoes_atualizadas} separações atualizadas...")
                
            except Exception as e:
                erros += 1
                print(f"   ❌ Erro ao processar lote {lote_id}: {str(e)}")
                db.session.rollback()
                continue
        
        # Commit final
        db.session.commit()
        
        print(f"\n✅ FASE 2 CONCLUÍDA:")
        print(f"   • Separações atualizadas com NF: {separacoes_atualizadas}")
        print(f"   • Separações que já tinham NF: {separacoes_ja_tinham_nf}")
        print(f"   • Erros durante atualização: {erros}")
        
        # 3. Verifica quantas Separacao ficaram sem NF
        print("\n📈 FASE 3: Estatísticas finais...")
        
        # Total de separações
        total_separacoes = Separacao.query.count()
        
        # Separações sem NF
        separacoes_sem_nf = Separacao.query.filter(
            (Separacao.numero_nf.is_(None)) | (Separacao.numero_nf == '')
        ).count()
        
        # Separações com NF
        separacoes_com_nf = total_separacoes - separacoes_sem_nf
        
        # Separações sem NF por status
        print("\n📊 SEPARAÇÕES SEM NF POR STATUS:")
        status_counts = db.session.query(
            Separacao.status,
            func.count(Separacao.id)
        ).filter(
            (Separacao.numero_nf.is_(None)) | (Separacao.numero_nf == '')
        ).group_by(
            Separacao.status
        ).all()
        
        for status, count in status_counts:
            percentual = (count / separacoes_sem_nf * 100) if separacoes_sem_nf > 0 else 0
            print(f"   • {status or 'SEM STATUS'}: {count} ({percentual:.1f}%)")
        
        # Top 10 lotes sem NF
        print("\n🔝 TOP 10 LOTES SEM NF (maior quantidade de itens):")
        lotes_sem_nf = db.session.query(
            Separacao.separacao_lote_id,
            func.count(Separacao.id).label('qtd_itens'),
            func.min(Separacao.expedicao).label('data_exp')
        ).filter(
            (Separacao.numero_nf.is_(None)) | (Separacao.numero_nf == ''),
            Separacao.separacao_lote_id.isnot(None)
        ).group_by(
            Separacao.separacao_lote_id
        ).order_by(
            func.count(Separacao.id).desc()
        ).limit(10).all()
        
        for lote_id, qtd, data_exp in lotes_sem_nf:
            data_str = data_exp.strftime('%d/%m/%Y') if data_exp else 'SEM DATA'
            print(f"   • Lote {lote_id}: {qtd} itens (Expedição: {data_str})")
        
        # Resumo final
        print("\n" + "=" * 80)
        print("📊 RESUMO FINAL DA MIGRAÇÃO:")
        print("=" * 80)
        print(f"\n✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!\n")
        print(f"📈 ESTATÍSTICAS GERAIS:")
        print(f"   • Total de Entregas processadas: {total_entregas}")
        print(f"   • Entregas com lote_id: {entregas_com_lote}")
        print(f"   • Entregas sem lote_id: {entregas_sem_lote}")
        print(f"   • Separações atualizadas: {separacoes_atualizadas}")
        print(f"   • Erros encontrados: {erros}")
        
        print(f"\n📊 SITUAÇÃO ATUAL DA TABELA SEPARACAO:")
        print(f"   • Total de registros: {total_separacoes}")
        print(f"   • COM número_nf: {separacoes_com_nf} ({separacoes_com_nf/total_separacoes*100:.1f}%)")
        print(f"   • SEM número_nf: {separacoes_sem_nf} ({separacoes_sem_nf/total_separacoes*100:.1f}%)")
        
        if separacoes_sem_nf > 0:
            print(f"\n⚠️  ATENÇÃO: {separacoes_sem_nf} registros de Separacao ainda estão sem NF!")
            print("   Possíveis motivos:")
            print("   1. Pedidos ainda não faturados")
            print("   2. EntregaMonitorada sem separacao_lote_id")
            print("   3. Separações com status='PREVISAO' (pré-separações)")
        
        print(f"\nFinalizado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {str(e)}")
        db.session.rollback()
        raise

if __name__ == "__main__":
    # Cria a aplicação Flask
    app = create_app()
    
    with app.app_context():
        # Executa a migração
        migrar_nf_entrega_para_separacao()
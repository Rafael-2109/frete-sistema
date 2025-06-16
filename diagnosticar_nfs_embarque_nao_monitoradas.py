#!/usr/bin/env python3
"""
🔍 DIAGNÓSTICO: NFs em Embarques Não Monitoradas

Este script identifica NFs que estão em embarques (EmbarqueItem) mas não foram 
sincronizadas para o monitoramento de entregas.

PROBLEMA RELATADO:
- NFs existem em EmbarqueItem 
- Mas não foram criadas em EntregaMonitorada durante a importação do faturamento
- Isso pode indicar problema na sincronização ou filtros inadequados

ANÁLISE:
1. Busca todas as NFs em embarques ativos
2. Verifica se existem no faturamento
3. Verifica se foram sincronizadas para o monitoramento
4. Identifica possíveis causas da não sincronização

Uso: python diagnosticar_nfs_embarque_nao_monitoradas.py [--corrigir] [--embarque=NUMERO]
"""

import sys
import os
import argparse
from datetime import datetime, timedelta

# Adiciona o diretório pai ao Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.embarques.models import EmbarqueItem, Embarque
from app.faturamento.models import RelatorioFaturamentoImportado
from app.monitoramento.models import EntregaMonitorada
from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf

def diagnosticar_nfs_embarque_nao_monitoradas(embarque_especifico=None, corrigir=False):
    """
    Diagnostica NFs em embarques que não estão no monitoramento
    """
    app = create_app()
    
    with app.app_context():
        print("🔍 DIAGNÓSTICO: NFs em Embarques Não Monitoradas")
        print("=" * 60)
        
        # Filtro por embarque específico se fornecido
        query_embarques = Embarque.query.filter_by(status='ativo')
        if embarque_especifico:
            query_embarques = query_embarques.filter_by(numero=embarque_especifico)
        
        embarques = query_embarques.all()
        print(f"\n📊 EMBARQUES ANALISADOS: {len(embarques)}")
        
        if embarque_especifico:
            print(f"   • Embarque específico: #{embarque_especifico}")
        else:
            print(f"   • Todos os embarques ativos")
        
        # Estatísticas gerais
        stats = {
            'total_nfs_embarques': 0,
            'nfs_com_faturamento': 0,
            'nfs_sem_faturamento': 0,
            'nfs_monitoradas': 0,
            'nfs_nao_monitoradas': 0,
            'nfs_fob_filtradas': 0,
            'nfs_inativas_filtradas': 0,
            'nfs_corrigidas': 0
        }
        
        # Lista para armazenar problemas encontrados
        problemas = {
            'sem_faturamento': [],
            'nao_monitoradas': [],
            'fob_nao_filtradas': [],
            'inativas_nao_filtradas': []
        }
        
        print(f"\n🔍 ANALISANDO NFs POR EMBARQUE...")
        
        for embarque in embarques:
            print(f"\n📦 Embarque #{embarque.numero} ({embarque.tipo_carga}) - {len(embarque.itens)} itens")
            
            for item in embarque.itens:
                if item.status != 'ativo' or not item.nota_fiscal:
                    continue
                
                nf = item.nota_fiscal
                stats['total_nfs_embarques'] += 1
                
                # Verifica se existe no faturamento
                nf_faturamento = RelatorioFaturamentoImportado.query.filter_by(numero_nf=nf).first()
                
                if not nf_faturamento:
                    print(f"   ❌ NF {nf} - NÃO encontrada no faturamento")
                    stats['nfs_sem_faturamento'] += 1
                    problemas['sem_faturamento'].append({
                        'nf': nf,
                        'embarque': embarque.numero,
                        'cliente': item.cliente
                    })
                    continue
                
                stats['nfs_com_faturamento'] += 1
                
                # Verifica se está no monitoramento
                entrega = EntregaMonitorada.query.filter_by(numero_nf=nf).first()
                
                if entrega:
                    stats['nfs_monitoradas'] += 1
                    print(f"   ✅ NF {nf} - Monitorada: {entrega.cliente[:30]}...")
                else:
                    stats['nfs_nao_monitoradas'] += 1
                    print(f"   ⚠️  NF {nf} - NÃO monitorada: {nf_faturamento.nome_cliente[:30]}...")
                    
                    # Analisa possíveis causas
                    causas = []
                    
                    # 1. NF inativa no faturamento
                    if not nf_faturamento.ativo:
                        causas.append("NF inativa no faturamento")
                        stats['nfs_inativas_filtradas'] += 1
                        problemas['inativas_nao_filtradas'].append({
                            'nf': nf,
                            'embarque': embarque.numero,
                            'cliente': nf_faturamento.nome_cliente,
                            'incoterm': nf_faturamento.incoterm
                        })
                    
                    # 2. NF FOB
                    elif nf_faturamento.incoterm and 'FOB' in nf_faturamento.incoterm.upper():
                        causas.append(f"NF FOB ({nf_faturamento.incoterm})")
                        stats['nfs_fob_filtradas'] += 1
                        
                        # Se embarque não é FOB, pode ser problema
                        if embarque.tipo_carga != 'FOB':
                            problemas['fob_nao_filtradas'].append({
                                'nf': nf,
                                'embarque': embarque.numero,
                                'embarque_tipo': embarque.tipo_carga,
                                'cliente': nf_faturamento.nome_cliente,
                                'incoterm': nf_faturamento.incoterm
                            })
                    
                    # 3. Problema de sincronização
                    else:
                        causas.append("Problema de sincronização")
                        problemas['nao_monitoradas'].append({
                            'nf': nf,
                            'embarque': embarque.numero,
                            'embarque_tipo': embarque.tipo_carga,
                            'cliente': nf_faturamento.nome_cliente,
                            'incoterm': nf_faturamento.incoterm,
                            'ativo': nf_faturamento.ativo
                        })
                        
                        # Tenta corrigir se solicitado
                        if corrigir:
                            try:
                                print(f"      🔄 Tentando sincronizar...")
                                sincronizar_entrega_por_nf(nf)
                                
                                # Verifica se foi criada
                                entrega_nova = EntregaMonitorada.query.filter_by(numero_nf=nf).first()
                                if entrega_nova:
                                    print(f"      ✅ Sincronizada com sucesso!")
                                    stats['nfs_corrigidas'] += 1
                                else:
                                    print(f"      ❌ Falha na sincronização")
                            except Exception as e:
                                print(f"      ❌ Erro na sincronização: {e}")
                    
                    if causas:
                        print(f"      💡 Possíveis causas: {', '.join(causas)}")
        
        # Relatório de problemas por categoria
        print(f"\n📋 ANÁLISE DETALHADA DOS PROBLEMAS:")
        
        # 1. NFs sem faturamento
        if problemas['sem_faturamento']:
            print(f"\n❌ NFs SEM FATURAMENTO ({len(problemas['sem_faturamento'])}):")
            print(f"   Problema: NFs estão em embarques mas não foram importadas no faturamento")
            for item in problemas['sem_faturamento'][:5]:
                print(f"   • NF {item['nf']} - Embarque #{item['embarque']} - {item['cliente'][:30]}...")
        
        # 2. NFs FOB em embarques não-FOB
        if problemas['fob_nao_filtradas']:
            print(f"\n🚫 NFs FOB em EMBARQUES NÃO-FOB ({len(problemas['fob_nao_filtradas'])}):")
            print(f"   Problema: NFs FOB em embarques que não são tipo FOB")
            for item in problemas['fob_nao_filtradas'][:5]:
                print(f"   • NF {item['nf']} - Embarque #{item['embarque']} ({item['embarque_tipo']}) - {item['incoterm']}")
        
        # 3. NFs inativas não filtradas adequadamente
        if problemas['inativas_nao_filtradas']:
            print(f"\n⚠️  NFs INATIVAS EM EMBARQUES ({len(problemas['inativas_nao_filtradas'])}):")
            print(f"   Problema: NFs inativas no faturamento mas ainda em embarques ativos")
            for item in problemas['inativas_nao_filtradas'][:5]:
                print(f"   • NF {item['nf']} - Embarque #{item['embarque']} - {item['cliente'][:30]}...")
        
        # 4. Problemas de sincronização
        if problemas['nao_monitoradas']:
            print(f"\n🔄 PROBLEMAS DE SINCRONIZAÇÃO ({len(problemas['nao_monitoradas'])}):")
            print(f"   Problema: NFs válidas que deveriam estar no monitoramento")
            for item in problemas['nao_monitoradas'][:10]:
                print(f"   • NF {item['nf']} - Embarque #{item['embarque']} ({item['embarque_tipo']}) - {item['incoterm'] or 'Sem incoterm'}")
        
        # Estatísticas finais
        print(f"\n📊 ESTATÍSTICAS FINAIS:")
        print(f"   • Total NFs em embarques: {stats['total_nfs_embarques']}")
        print(f"   • NFs com faturamento: {stats['nfs_com_faturamento']}")
        print(f"   • NFs sem faturamento: {stats['nfs_sem_faturamento']}")
        print(f"   • NFs monitoradas: {stats['nfs_monitoradas']}")
        print(f"   • NFs não monitoradas: {stats['nfs_nao_monitoradas']}")
        print(f"   • NFs FOB filtradas: {stats['nfs_fob_filtradas']}")
        print(f"   • NFs inativas filtradas: {stats['nfs_inativas_filtradas']}")
        
        if corrigir:
            print(f"   • NFs corrigidas: {stats['nfs_corrigidas']}")
        
        # Taxa de sincronização
        if stats['nfs_com_faturamento'] > 0:
            taxa_sincronizacao = (stats['nfs_monitoradas'] / stats['nfs_com_faturamento']) * 100
            print(f"   • Taxa de sincronização: {taxa_sincronizacao:.1f}%")
        
        # Ações recomendadas
        print(f"\n💡 AÇÕES RECOMENDADAS:")
        
        if problemas['sem_faturamento']:
            print(f"   • {len(problemas['sem_faturamento'])} NFs sem faturamento: Importar faturamento ou remover dos embarques")
        
        if problemas['fob_nao_filtradas']:
            print(f"   • {len(problemas['fob_nao_filtradas'])} NFs FOB em embarques não-FOB: Revisar classificação dos embarques")
        
        if problemas['inativas_nao_filtradas']:
            print(f"   • {len(problemas['inativas_nao_filtradas'])} NFs inativas em embarques: Revisar status das NFs ou embarques")
        
        if problemas['nao_monitoradas']:
            print(f"   • {len(problemas['nao_monitoradas'])} problemas de sincronização: Execute com --corrigir para tentar resolver")
        
        if not corrigir and problemas['nao_monitoradas']:
            print(f"\n🔧 Para tentar corrigir automaticamente:")
            print(f"   python {sys.argv[0]} --corrigir")

def main():
    parser = argparse.ArgumentParser(description='Diagnosticar NFs em embarques não monitoradas')
    parser.add_argument('--corrigir', action='store_true', help='Tenta corrigir problemas de sincronização')
    parser.add_argument('--embarque', type=int, help='Analisa apenas um embarque específico')
    
    args = parser.parse_args()
    
    diagnosticar_nfs_embarque_nao_monitoradas(
        embarque_especifico=args.embarque,
        corrigir=args.corrigir
    )

if __name__ == '__main__':
    main() 
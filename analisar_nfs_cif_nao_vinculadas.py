#!/usr/bin/env python3
"""
🔍 ANÁLISE DE NFs CIF NÃO VINCULADAS AO MONITORAMENTO

Este script identifica NFs com incoterm CIF que não foram vinculadas 
ao monitoramento de entregas e analisa os possíveis motivos.

NFs CIF (Cost, Insurance and Freight) = Frete por nossa conta
- Devem ser monitoradas pela logística
- Se não estão no monitoramento, pode indicar problema

Possíveis motivos para não vinculação:
1. NF inativa no faturamento
2. NF já está em embarque
3. Problema na sincronização
4. Filtros ativos impedindo vinculação

Uso: python analisar_nfs_cif_nao_vinculadas.py [--detalhado] [--recentes=30]
"""

import sys
import os
import argparse
from datetime import datetime, timedelta

# Adiciona o diretório pai ao Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.faturamento.models import RelatorioFaturamentoImportado
from app.monitoramento.models import EntregaMonitorada
from app.embarques.models import EmbarqueItem, Embarque

def analisar_nfs_cif_nao_vinculadas(detalhado=False, dias_recentes=30):
    """
    Analisa NFs CIF que não estão no monitoramento
    """
    app = create_app()
    
    with app.app_context():
        print("🔍 ANÁLISE DE NFs CIF NÃO VINCULADAS")
        print("=" * 60)
        
        # Data limite para NFs recentes
        data_limite = datetime.now().date() - timedelta(days=dias_recentes)
        
        # Busca NFs CIF ativas
        query_cif = RelatorioFaturamentoImportado.query.filter(
            RelatorioFaturamentoImportado.incoterm.ilike('%CIF%'),
            RelatorioFaturamentoImportado.ativo == True
        )
        
        if dias_recentes:
            query_cif = query_cif.filter(
                RelatorioFaturamentoImportado.data_fatura >= data_limite
            )
        
        nfs_cif = query_cif.all()
        
        print(f"\n📊 ESTATÍSTICAS GERAIS:")
        print(f"   • Período analisado: {f'Últimos {dias_recentes} dias' if dias_recentes else 'Todas as NFs'}")
        print(f"   • NFs CIF ativas encontradas: {len(nfs_cif)}")
        
        if not nfs_cif:
            print("✅ Nenhuma NF CIF encontrada no período!")
            return
        
        # Análise das NFs CIF
        nfs_vinculadas = []
        nfs_nao_vinculadas = []
        
        for nf in nfs_cif:
            entrega = EntregaMonitorada.query.filter_by(numero_nf=nf.numero_nf).first()
            if entrega:
                nfs_vinculadas.append((nf, entrega))
            else:
                nfs_nao_vinculadas.append(nf)
        
        print(f"   • NFs CIF vinculadas ao monitoramento: {len(nfs_vinculadas)}")
        print(f"   • NFs CIF NÃO vinculadas: {len(nfs_nao_vinculadas)}")
        
        if len(nfs_cif) > 0:
            perc_vinculadas = (len(nfs_vinculadas) / len(nfs_cif)) * 100
            print(f"   • Taxa de vinculação: {perc_vinculadas:.1f}%")
        
        if not nfs_nao_vinculadas:
            print("✅ Todas as NFs CIF estão vinculadas ao monitoramento!")
            return
        
        # Análise detalhada das não vinculadas
        print(f"\n🔍 ANÁLISE DAS NFs CIF NÃO VINCULADAS:")
        
        # Categoriza os motivos
        motivos = {
            'em_embarque': [],
            'em_embarque_fob': [],
            'sem_embarque': [],
            'dados_incompletos': []
        }
        
        for nf in nfs_nao_vinculadas:
            # Verifica se está em embarque
            item_embarque = EmbarqueItem.query.filter_by(nota_fiscal=nf.numero_nf).first()
            
            if item_embarque:
                embarque = Embarque.query.get(item_embarque.embarque_id)
                if embarque and embarque.tipo_carga == 'FOB':
                    motivos['em_embarque_fob'].append((nf, item_embarque, embarque))
                else:
                    motivos['em_embarque'].append((nf, item_embarque, embarque))
            else:
                # Verifica se tem dados mínimos
                if not nf.nome_cliente or not nf.cnpj_cliente:
                    motivos['dados_incompletos'].append(nf)
                else:
                    motivos['sem_embarque'].append(nf)
        
        # Relatório por categoria
        print(f"\n📋 CATEGORIZAÇÃO DOS MOTIVOS:")
        
        # 1. Em embarque FOB
        if motivos['em_embarque_fob']:
            print(f"\n🚫 NFs em embarques FOB ({len(motivos['em_embarque_fob'])}):")
            print(f"   Motivo: Filtro automático remove NFs de embarques FOB")
            for nf, item, embarque in motivos['em_embarque_fob'][:5]:  # Primeiras 5
                data_fatura = nf.data_fatura.strftime('%d/%m/%Y') if nf.data_fatura else 'N/A'
                print(f"   • NF {nf.numero_nf} - {nf.nome_cliente[:30]}... - {data_fatura} - Embarque #{embarque.numero}")
        
        # 2. Em embarque normal
        if motivos['em_embarque']:
            print(f"\n🚚 NFs em embarques normais ({len(motivos['em_embarque'])}):")
            print(f"   Motivo: Pode ser filtro de embarques ativo ou problema de sincronização")
            for nf, item, embarque in motivos['em_embarque'][:5]:  # Primeiras 5
                data_fatura = nf.data_fatura.strftime('%d/%m/%Y') if nf.data_fatura else 'N/A'
                tipo_embarque = embarque.tipo_carga if embarque else 'N/A'
                print(f"   • NF {nf.numero_nf} - {nf.nome_cliente[:30]}... - {data_fatura} - Embarque #{embarque.numero} ({tipo_embarque})")
        
        # 3. Sem embarque
        if motivos['sem_embarque']:
            print(f"\n❓ NFs sem embarque ({len(motivos['sem_embarque'])}):")
            print(f"   Motivo: NFs que deveriam estar no monitoramento mas não estão")
            for nf in motivos['sem_embarque'][:10]:  # Primeiras 10
                data_fatura = nf.data_fatura.strftime('%d/%m/%Y') if nf.data_fatura else 'N/A'
                print(f"   • NF {nf.numero_nf} - {nf.nome_cliente[:30]}... - {data_fatura}")
        
        # 4. Dados incompletos
        if motivos['dados_incompletos']:
            print(f"\n⚠️  NFs com dados incompletos ({len(motivos['dados_incompletos'])}):")
            print(f"   Motivo: Faltam dados básicos (cliente, CNPJ)")
            for nf in motivos['dados_incompletos'][:5]:  # Primeiras 5
                data_fatura = nf.data_fatura.strftime('%d/%m/%Y') if nf.data_fatura else 'N/A'
                cliente = nf.nome_cliente[:30] + '...' if nf.nome_cliente else 'SEM CLIENTE'
                cnpj = nf.cnpj_cliente or 'SEM CNPJ'
                print(f"   • NF {nf.numero_nf} - {cliente} - CNPJ: {cnpj} - {data_fatura}")
        
        # Resumo de ações sugeridas
        print(f"\n💡 AÇÕES SUGERIDAS:")
        
        if motivos['em_embarque_fob']:
            print(f"   • {len(motivos['em_embarque_fob'])} NFs em embarques FOB: ✅ Comportamento correto (filtro ativo)")
        
        if motivos['em_embarque']:
            print(f"   • {len(motivos['em_embarque'])} NFs em embarques normais: ⚠️  Verificar configuração FILTRAR_EMBARQUES_MONITORAMENTO")
        
        if motivos['sem_embarque']:
            print(f"   • {len(motivos['sem_embarque'])} NFs sem embarque: 🔄 Executar sincronização manual")
            print(f"     Comando: python -c \"from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf; [sincronizar_entrega_por_nf('{nf.numero_nf}') for nf in nfs]\"")
        
        if motivos['dados_incompletos']:
            print(f"   • {len(motivos['dados_incompletos'])} NFs com dados incompletos: 🔧 Revisar dados no faturamento")
        
        # Detalhamento se solicitado
        if detalhado and motivos['sem_embarque']:
            print(f"\n📄 DETALHAMENTO DAS NFs SEM EMBARQUE:")
            for nf in motivos['sem_embarque']:
                print(f"\n   NF: {nf.numero_nf}")
                print(f"   Cliente: {nf.nome_cliente}")
                print(f"   CNPJ: {nf.cnpj_cliente}")
                print(f"   Município: {nf.municipio} - {nf.estado}")
                print(f"   Valor: R$ {nf.valor_total:.2f}" if nf.valor_total else "   Valor: N/A")
                print(f"   Data Fatura: {nf.data_fatura}" if nf.data_fatura else "   Data Fatura: N/A")
                print(f"   Incoterm: {nf.incoterm}")
                print(f"   ---")

def main():
    parser = argparse.ArgumentParser(description='Analisar NFs CIF não vinculadas ao monitoramento')
    parser.add_argument('--detalhado', action='store_true', help='Mostra detalhes das NFs sem embarque')
    parser.add_argument('--recentes', type=int, default=30, help='Analisa apenas NFs dos últimos N dias (0 = todas)')
    
    args = parser.parse_args()
    
    dias = args.recentes if args.recentes > 0 else None
    
    analisar_nfs_cif_nao_vinculadas(detalhado=args.detalhado, dias_recentes=dias)

if __name__ == '__main__':
    main() 
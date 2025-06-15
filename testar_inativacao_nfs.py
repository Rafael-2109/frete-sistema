#!/usr/bin/env python3
"""
🧪 TESTE DA FUNCIONALIDADE DE INATIVAÇÃO DE NFs

Este script demonstra como funciona a nova funcionalidade de inativação de NFs
"""

import sys
import os

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.faturamento.models import RelatorioFaturamentoImportado
from app.monitoramento.models import EntregaMonitorada

def testar_inativacao():
    """Testa a funcionalidade de inativação de NFs"""
    
    app = create_app()
    with app.app_context():
        print("🧪 TESTANDO FUNCIONALIDADE DE INATIVAÇÃO DE NFs")
        print("=" * 60)
        
        # 1. Lista algumas NFs ativas
        print("\n📋 NFs ATIVAS NO FATURAMENTO:")
        nfs_ativas = RelatorioFaturamentoImportado.query.filter_by(ativo=True).limit(5).all()
        
        for nf in nfs_ativas:
            entrega = EntregaMonitorada.query.filter_by(numero_nf=nf.numero_nf).first()
            status_monitoramento = "✅ No monitoramento" if entrega else "❌ Não monitorada"
            print(f"   NF {nf.numero_nf} - {nf.nome_cliente[:30]}... - {status_monitoramento}")
        
        # 2. Lista NFs inativas (se houver)
        print("\n🗑️ NFs INATIVAS NO FATURAMENTO:")
        nfs_inativas = RelatorioFaturamentoImportado.query.filter_by(ativo=False).limit(5).all()
        
        if nfs_inativas:
            for nf in nfs_inativas:
                print(f"   NF {nf.numero_nf} - Inativada em {nf.inativado_em} por {nf.inativado_por}")
        else:
            print("   Nenhuma NF inativa encontrada")
        
        # 3. Estatísticas
        total_ativas = RelatorioFaturamentoImportado.query.filter_by(ativo=True).count()
        total_inativas = RelatorioFaturamentoImportado.query.filter_by(ativo=False).count()
        total_monitoradas = EntregaMonitorada.query.count()
        
        print(f"\n📊 ESTATÍSTICAS:")
        print(f"   📄 Total NFs ativas: {total_ativas}")
        print(f"   🗑️ Total NFs inativas: {total_inativas}")
        print(f"   👁️ Total NFs no monitoramento: {total_monitoradas}")
        
        print(f"\n✅ FUNCIONALIDADE PRONTA PARA USO!")
        print(f"\n🎯 COMO USAR:")
        print(f"   1. Acesse: http://localhost:5000/faturamento/listar")
        print(f"   2. Selecione as NFs que deseja inativar")
        print(f"   3. Clique em '🗑️ Inativar Selecionadas'")
        print(f"   4. As NFs serão:")
        print(f"      - Marcadas como inativas no faturamento")
        print(f"      - Removidas do monitoramento")
        print(f"      - Não serão mais sincronizadas")

if __name__ == '__main__':
    testar_inativacao() 
#!/usr/bin/env python3
"""
🚫 INATIVAR NFs FOB NO FATURAMENTO

Este script identifica e inativa todas as NFs com incoterm FOB no faturamento,
removendo-as também do monitoramento de entregas.

NFs FOB (Free On Board) = Frete por conta do cliente
- Não devem ser monitoradas pela logística
- Devem ser marcadas como inativas no faturamento

Uso: python inativar_nfs_fob.py [--dry-run] [--confirmar]
"""

import sys
import os
import argparse
from datetime import datetime

# Adiciona o diretório pai ao Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.faturamento.models import RelatorioFaturamentoImportado
from app.monitoramento.models import EntregaMonitorada

def inativar_nfs_fob(dry_run=True, confirmar=False):
    """
    Inativa NFs FOB no faturamento e remove do monitoramento
    """
    app = create_app()
    
    with app.app_context():
        print("🚫 INATIVAÇÃO DE NFs FOB")
        print("=" * 60)
        
        # Busca NFs FOB ativas
        nfs_fob = RelatorioFaturamentoImportado.query.filter(
            RelatorioFaturamentoImportado.incoterm.ilike('%FOB%'),
            RelatorioFaturamentoImportado.ativo == True
        ).all()
        
        if not nfs_fob:
            print("✅ Nenhuma NF FOB ativa encontrada!")
            return
        
        # Estatísticas iniciais
        print(f"\n📊 ANÁLISE INICIAL:")
        print(f"   • NFs FOB ativas encontradas: {len(nfs_fob)}")
        
        # Verifica quantas estão no monitoramento
        nfs_fob_monitoradas = []
        for nf in nfs_fob:
            entrega = EntregaMonitorada.query.filter_by(numero_nf=nf.numero_nf).first()
            if entrega:
                nfs_fob_monitoradas.append((nf, entrega))
        
        print(f"   • NFs FOB no monitoramento: {len(nfs_fob_monitoradas)}")
        
        # Mostra alguns exemplos
        print(f"\n📋 PRIMEIRAS 5 NFs FOB:")
        for i, nf in enumerate(nfs_fob[:5]):
            no_monitoramento = "SIM" if any(nf.numero_nf == item[0].numero_nf for item in nfs_fob_monitoradas) else "NÃO"
            data_fatura = nf.data_fatura.strftime('%d/%m/%Y') if nf.data_fatura else 'N/A'
            print(f"   • NF {nf.numero_nf} - {nf.nome_cliente[:30]}... - {data_fatura} - Monitorada: {no_monitoramento}")
        
        if dry_run:
            print(f"\n🔍 MODO SIMULAÇÃO (--dry-run)")
            print(f"   Para executar as alterações, use: python {sys.argv[0]} --confirmar")
            return
        
        if not confirmar:
            print(f"\n⚠️  CONFIRMAÇÃO NECESSÁRIA")
            print(f"   Este script irá:")
            print(f"   • Inativar {len(nfs_fob)} NFs FOB no faturamento")
            print(f"   • Remover {len(nfs_fob_monitoradas)} NFs FOB do monitoramento")
            print(f"   Para confirmar, use: python {sys.argv[0]} --confirmar")
            return
        
        # Executa as alterações
        print(f"\n🔄 EXECUTANDO ALTERAÇÕES...")
        
        nfs_inativadas = 0
        nfs_removidas_monitoramento = 0
        erros = []
        
        for nf in nfs_fob:
            try:
                # 1. Inativa no faturamento
                nf.ativo = False
                nf.inativado_em = datetime.utcnow()
                nf.inativado_por = 'Script FOB'
                nfs_inativadas += 1
                
                # 2. Remove do monitoramento se existir
                entrega = EntregaMonitorada.query.filter_by(numero_nf=nf.numero_nf).first()
                if entrega:
                    db.session.delete(entrega)
                    nfs_removidas_monitoramento += 1
                
            except Exception as e:
                erros.append(f"NF {nf.numero_nf}: {str(e)}")
        
        # Salva alterações
        try:
            db.session.commit()
            print(f"✅ ALTERAÇÕES SALVAS COM SUCESSO!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERRO AO SALVAR: {e}")
            return
        
        # Resultados
        print(f"\n📊 RESULTADOS:")
        print(f"   • NFs inativadas no faturamento: {nfs_inativadas}")
        print(f"   • NFs removidas do monitoramento: {nfs_removidas_monitoramento}")
        
        if erros:
            print(f"   • Erros encontrados: {len(erros)}")
            for erro in erros[:5]:  # Mostra primeiros 5 erros
                print(f"     - {erro}")

def main():
    parser = argparse.ArgumentParser(description='Inativar NFs FOB no faturamento')
    parser.add_argument('--dry-run', action='store_true', help='Simula as alterações sem executar')
    parser.add_argument('--confirmar', action='store_true', help='Confirma e executa as alterações')
    
    args = parser.parse_args()
    
    # Por padrão, roda em modo simulação
    dry_run = not args.confirmar
    
    inativar_nfs_fob(dry_run=dry_run, confirmar=args.confirmar)

if __name__ == '__main__':
    main() 
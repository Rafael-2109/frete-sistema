"""
Script para Sincronizar NFs FOB Existentes - Retroativo
========================================================

Este script cria EntregaMonitorada para todas as NFs FOB que:
- Estão em RelatorioFaturamentoImportado com incoterm='FOB'
- Ainda NÃO possuem EntregaMonitorada
- Possuem EmbarqueItem (para pegar data_embarque)

ATENÇÃO: Este script deve ser rodado APÓS modificar app/utils/sincronizar_entregas.py

Data: 13/10/2025
"""

import sys
import os

# Adiciona o diretório raiz ao path para importar módulos do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.faturamento.models import RelatorioFaturamentoImportado
from app.monitoramento.models import EntregaMonitorada
from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf
from sqlalchemy import text

def sincronizar_fob_retroativo():
    """
    Sincroniza retroativamente todas as NFs FOB que não têm EntregaMonitorada
    """
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🚀 SCRIPT DE SINCRONIZAÇÃO RETROATIVA - NFs FOB")
            print("=" * 80)
            print()

            # 1. Buscar todas as NFs FOB que estão ativas
            print("📋 Etapa 1: Buscando NFs FOB ativas no faturamento...")
            nfs_fob = RelatorioFaturamentoImportado.query.filter(
                RelatorioFaturamentoImportado.ativo == True,
                RelatorioFaturamentoImportado.incoterm.ilike('%FOB%')
            ).all()

            print(f"   ✅ Encontradas {len(nfs_fob)} NFs FOB ativas")
            print()

            if not nfs_fob:
                print("⚠️ Nenhuma NF FOB encontrada. Script finalizado.")
                return

            # 2. Filtrar apenas as que NÃO têm EntregaMonitorada
            print("📋 Etapa 2: Identificando NFs FOB sem EntregaMonitorada...")
            nfs_para_sincronizar = []

            for nf_fob in nfs_fob:
                entrega_existe = EntregaMonitorada.query.filter_by(
                    numero_nf=nf_fob.numero_nf
                ).first()

                if not entrega_existe:
                    nfs_para_sincronizar.append(nf_fob.numero_nf)

            print(f"   ✅ Encontradas {len(nfs_para_sincronizar)} NFs FOB sem EntregaMonitorada")
            print()

            if not nfs_para_sincronizar:
                print("✅ Todas as NFs FOB já possuem EntregaMonitorada. Script finalizado.")
                return

            # 3. Listar as NFs que serão processadas
            print("📦 NFs FOB que serão sincronizadas:")
            for idx, numero_nf in enumerate(nfs_para_sincronizar, 1):
                nf_info = next((nf for nf in nfs_fob if nf.numero_nf == numero_nf), None)
                if nf_info:
                    print(f"   {idx:3d}. NF {numero_nf:15s} | {nf_info.nome_cliente[:50]:50s} | R$ {nf_info.valor_total:,.2f}")
            print()

            # 4. Confirmação do usuário
            confirma = input("⚠️  CONFIRMA a sincronização retroativa destas NFs? (sim/não): ").strip().lower()

            if confirma not in ['sim', 's', 'yes', 'y']:
                print("❌ Sincronização cancelada pelo usuário.")
                return

            print()
            print("=" * 80)
            print("🔄 INICIANDO SINCRONIZAÇÃO...")
            print("=" * 80)
            print()

            # 5. Sincronizar cada NF FOB
            sucesso = 0
            erros = 0
            detalhes_erros = []

            for idx, numero_nf in enumerate(nfs_para_sincronizar, 1):
                try:
                    print(f"[{idx}/{len(nfs_para_sincronizar)}] Processando NF {numero_nf}...", end=" ")

                    # Usar a função existente de sincronização
                    sincronizar_entrega_por_nf(numero_nf)

                    # Verificar se foi criada
                    entrega_criada = EntregaMonitorada.query.filter_by(numero_nf=numero_nf).first()

                    if entrega_criada:
                        status_entrega = "ENTREGUE" if entrega_criada.entregue else "PENDENTE"
                        print(f"✅ Criada | Status: {status_entrega}")
                        sucesso += 1
                    else:
                        print(f"⚠️ Não foi criada (possível NF sem embarque)")
                        erros += 1
                        detalhes_erros.append(f"NF {numero_nf}: Não foi criada EntregaMonitorada")

                except Exception as e:
                    print(f"❌ ERRO: {str(e)}")
                    erros += 1
                    detalhes_erros.append(f"NF {numero_nf}: {str(e)}")
                    db.session.rollback()

            # 6. Relatório final
            print()
            print("=" * 80)
            print("📊 RELATÓRIO FINAL")
            print("=" * 80)
            print(f"✅ NFs sincronizadas com sucesso: {sucesso}")
            print(f"❌ NFs com erro/não sincronizadas: {erros}")
            print()

            if detalhes_erros:
                print("⚠️ DETALHES DOS ERROS:")
                for erro in detalhes_erros:
                    print(f"   - {erro}")
                print()

            # 7. Verificação final
            print("📋 Verificação final:")
            total_entregas_fob = db.session.execute(text("""
                SELECT COUNT(*)
                FROM entregas_monitoradas em
                JOIN relatorio_faturamento_importado rfi ON rfi.numero_nf = em.numero_nf
                WHERE rfi.incoterm ILIKE '%FOB%'
            """)).scalar()

            print(f"   📈 Total de EntregaMonitorada com incoterm FOB: {total_entregas_fob}")
            print()

            print("✅ Script finalizado com sucesso!")
            print("=" * 80)

        except Exception as e:
            print(f"\n❌ ERRO CRÍTICO: {str(e)}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    sincronizar_fob_retroativo()

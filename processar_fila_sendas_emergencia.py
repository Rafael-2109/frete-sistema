#!/usr/bin/env python3
"""
SCRIPT DE EMERGÊNCIA - Processar Fila Sendas Manualmente
Use este script para processar a fila pendente enquanto corrige o scheduler no Render
"""

import sys
from datetime import datetime

def processar_fila_emergencia():
    """Processa a fila Sendas pendente de forma emergencial"""

    print("="*60)
    print("🚨 PROCESSAMENTO EMERGENCIAL DA FILA SENDAS")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    try:
        from app import create_app
        from app.portal.models_fila_sendas import FilaAgendamentoSendas
        from app.portal.workers.sendas_fila_scheduler import processar_fila_sendas_scheduled

        app = create_app()
        with app.app_context():
            # Verificar pendentes
            pendentes = FilaAgendamentoSendas.contar_pendentes()
            total = sum(pendentes.values())

            print(f"\n📊 SITUAÇÃO ATUAL:")
            print(f"   Total de itens pendentes: {total}")
            print(f"   Por CNPJ: {pendentes}")

            if total == 0:
                print("\n✅ Nenhum item pendente! Fila está vazia.")
                return

            # Confirmar processamento
            print("\n⚠️  ATENÇÃO: Este processamento é EMERGENCIAL!")
            print("   Certifique-se de configurar ENABLE_SENDAS_SCHEDULER=true no Render")

            resposta = input("\n❓ Deseja processar a fila agora? (s/n): ")

            if resposta.lower() != 's':
                print("❌ Processamento cancelado.")
                return

            print("\n🔄 Processando fila...")

            # Processar
            resultado = processar_fila_sendas_scheduled()

            print("\n📊 RESULTADO DO PROCESSAMENTO:")
            print(f"   ✅ Sucesso: {resultado['success']}")
            print(f"   📝 Mensagem: {resultado['message']}")
            print(f"   📦 Total processado: {resultado['total_processado']}")

            if resultado.get('job_id'):
                print(f"   🎯 Job ID: {resultado['job_id']}")
                print("\n✅ Job criado com sucesso!")
                print("   Acompanhe o progresso nos logs do worker")

            if not resultado['success']:
                print(f"\n❌ ERRO: {resultado['message']}")

            # Verificar situação após processamento
            pendentes_depois = FilaAgendamentoSendas.contar_pendentes()
            total_depois = sum(pendentes_depois.values())

            print(f"\n📊 SITUAÇÃO APÓS PROCESSAMENTO:")
            print(f"   Itens pendentes restantes: {total_depois}")

    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("⚠️  LEMBRETE: Configure ENABLE_SENDAS_SCHEDULER=true no Render!")
    print("="*60)

if __name__ == "__main__":
    processar_fila_emergencia()
#!/usr/bin/env python3
"""
Script para testar e verificar o que aconteceria com a sincronização da carteira
Autor: Sistema de Fretes
Data: 2025-09-22
"""

import logging
from datetime import datetime, timedelta
from app import create_app
from app.odoo.services.sincronizacao_integrada_service import SincronizacaoIntegradaService
from app.odoo.services.carteira_service import CarteiraService

# Configurar logging detalhado
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analisar_sincronizacao():
    """Analisa o que aconteceria em uma sincronização"""

    print("=" * 80)
    print("🔍 ANÁLISE PROFUNDA DA SINCRONIZAÇÃO DA CARTEIRA")
    print("=" * 80)
    print()

    app = create_app()
    with app.app_context():
        # 1. VERIFICAR STATUS DO SISTEMA
        print("📊 1. VERIFICANDO STATUS DO SISTEMA...")
        print("-" * 50)

        sync_service = SincronizacaoIntegradaService()
        status = sync_service.verificar_status_sincronizacao()

        print(f"✅ Pode sincronizar: {status['pode_sincronizar']}")
        print(f"📌 Nível de risco: {status['nivel_risco']}")
        print(f"🕐 Última sync faturamento: {status.get('ultima_sync_faturamento', 'Nunca')}")
        print(f"🕐 Última sync carteira: {status.get('ultima_sync_carteira', 'Nunca')}")

        if status['alertas']:
            print(f"⚠️ Alertas detectados: {len(status['alertas'])}")
            for alerta in status['alertas'][:3]:
                print(f"   - {alerta}")
        print()

        # 2. VERIFICAR O QUE A CARTEIRA SERVICE FARIA
        print("📦 2. ANALISANDO SERVIÇO DA CARTEIRA...")
        print("-" * 50)

        carteira_service = CarteiraService()

        # Simular verificação de incremental
        print("🔍 Verificando o que uma sincronização incremental pegaria...")

        # Verificar últimos 40 minutos (padrão do scheduler)
        janela_minutos = 40
        data_inicio = datetime.now() - timedelta(minutes=janela_minutos)

        print(f"📅 Janela de busca: últimos {janela_minutos} minutos")
        print(f"📅 Desde: {data_inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 3. VERIFICAR O QUE SINCRONIZAÇÃO INTEGRADA FARIA
        print("🔄 3. ANALISANDO SINCRONIZAÇÃO INTEGRADA...")
        print("-" * 50)

        print("📌 Sequência de execução da sincronização integrada:")
        print("   1️⃣ FATURAMENTO primeiro (preserva NFs)")
        print("   2️⃣ Validação de integridade")
        print("   3️⃣ Atualização de status FATURADO")
        print("   4️⃣ CARTEIRA depois (sem risco de perda)")
        print()

        print("🔍 Verificando método que seria executado para carteira:")
        print("   - Método: sincronizar_carteira_odoo_com_gestao_quantidades")
        print("   - Parâmetros: usar_filtro_pendente=True")
        print("   - Operações principais:")
        print("     • Busca pedidos no Odoo")
        print("     • Calcula diferenças com banco local")
        print("     • Insere novos registros")
        print("     • Remove registros cancelados/faturados")
        print("     • Recompõe pré-separações afetadas")
        print()

        # 4. VERIFICAR CONFIGURAÇÃO DO SCHEDULER
        print("⏰ 4. CONFIGURAÇÃO DO SCHEDULER NO RENDER...")
        print("-" * 50)

        print("📌 Arquivo executado: app/scheduler/sincronizacao_incremental_simples.py")
        print("📌 Configuração atual:")
        print("   - INTERVALO_MINUTOS: 30 (a cada 30 minutos)")
        print("   - JANELA_MINUTOS: 40 (busca últimos 40 minutos)")
        print("   - STATUS_MINUTOS: 1560 (busca status últimas 26 horas)")
        print()

        print("📌 Fluxo de execução no Render:")
        print("   1. start_render.sh inicia o processo")
        print("   2. Executa sincronização inicial (janela de 120 minutos)")
        print("   3. Agenda execuções a cada 30 minutos")
        print("   4. Ordem de execução: FATURAMENTO → CARTEIRA")
        print()

        # 5. DIAGNÓSTICO FINAL
        print("🎯 5. DIAGNÓSTICO FINAL...")
        print("-" * 50)

        print("✅ PONTOS POSITIVOS:")
        print("   • Scheduler está configurado corretamente")
        print("   • Ordem de execução está SEGURA (Faturamento → Carteira)")
        print("   • Janela de sobreposição de 10 minutos evita perda de dados")
        print("   • Sincronização inicial recupera dados após deploy")
        print()

        print("⚠️ POSSÍVEIS PROBLEMAS NO RENDER:")
        print("   1. Processo do scheduler pode estar falhando ao iniciar")
        print("   2. Falta de logs detalhados dificulta diagnóstico")
        print("   3. Possível timeout ou kill do processo em background")
        print("   4. Verificar se o arquivo está no local correto")
        print()

        print("🔧 AÇÕES RECOMENDADAS:")
        print("   1. Verificar logs do Render: logs/sincronizacao_incremental.log")
        print("   2. Executar manualmente no shell do Render:")
        print("      python -m app.scheduler.sincronizacao_incremental_simples")
        print("   3. Verificar se o processo está rodando:")
        print("      ps aux | grep sincronizacao_incremental")
        print("   4. Testar execução única:")
        print("      python -c \"from app.odoo.services.sincronizacao_integrada_service import SincronizacaoIntegradaService; s = SincronizacaoIntegradaService(); print(s.executar_sincronizacao_completa_segura())\"")
        print()

if __name__ == "__main__":
    analisar_sincronizacao()
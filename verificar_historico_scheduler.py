#!/usr/bin/env python3
"""
Script para verificar histórico completo de execuções do scheduler
Mostra todos os horários de sincronização de Faturamento e Carteira
Autor: Sistema de Fretes
Data: 2025-09-22
"""

import os
from datetime import datetime, timedelta
from app import create_app, db
from sqlalchemy import text

def verificar_historico_scheduler():
    """Verifica todo o histórico de sincronizações"""

    print("=" * 80)
    print("🔍 ANÁLISE COMPLETA DO HISTÓRICO DO SCHEDULER")
    print("=" * 80)
    print()

    app = create_app()
    with app.app_context():

        # 1. VERIFICAR LOGS DO SCHEDULER (se existirem)
        print("📋 1. VERIFICANDO LOGS DO SCHEDULER...")
        print("-" * 50)

        log_file = "logs/sincronizacao_incremental.log"
        if os.path.exists(log_file):
            print(f"✅ Arquivo de log encontrado: {log_file}")

            # Ler últimas linhas do log
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()

                print(f"📊 Total de linhas no log: {len(lines)}")

                # Procurar por execuções do scheduler
                execucoes_faturamento = []
                execucoes_carteira = []
                execucoes_scheduler = []

                for line in lines:
                    if "SINCRONIZAÇÃO INCREMENTAL" in line or "INICIANDO SCHEDULER" in line:
                        execucoes_scheduler.append(line.strip())
                    if "Sincronizando Faturamento" in line or "Faturamento sincronizado" in line:
                        execucoes_faturamento.append(line.strip())
                    if "Sincronizando Carteira" in line or "Carteira sincronizada" in line:
                        execucoes_carteira.append(line.strip())

                print(f"\n📊 Execuções encontradas no log:")
                print(f"   • Inicializações do scheduler: {len(execucoes_scheduler)}")
                print(f"   • Sincronizações de faturamento: {len(execucoes_faturamento)}")
                print(f"   • Sincronizações de carteira: {len(execucoes_carteira)}")

                if execucoes_scheduler:
                    print("\n🕐 Últimas 5 inicializações do scheduler:")
                    for exec_log in execucoes_scheduler[-5:]:
                        print(f"   {exec_log[:100]}...")

                if execucoes_faturamento:
                    print("\n💰 Últimas 5 sincronizações de FATURAMENTO:")
                    for exec_log in execucoes_faturamento[-5:]:
                        print(f"   {exec_log[:100]}...")

                if execucoes_carteira:
                    print("\n📦 Últimas 5 sincronizações de CARTEIRA:")
                    for exec_log in execucoes_carteira[-5:]:
                        print(f"   {exec_log[:100]}...")

            except Exception as e:
                print(f"❌ Erro ao ler log: {e}")
        else:
            print(f"❌ Arquivo de log NÃO encontrado: {log_file}")
            print("   Isso indica que o scheduler NUNCA executou ou logs estão em outro local")

        print()

        # 2. VERIFICAR ÚLTIMA ATUALIZAÇÃO NO BANCO - FATURAMENTO
        print("💰 2. HISTÓRICO DE FATURAMENTO NO BANCO...")
        print("-" * 50)

        try:
            # Verificar registros mais recentes de faturamento
            query_fat = text("""
                SELECT
                    MIN(created_at) as primeira_sync,
                    MAX(created_at) as ultima_sync,
                    COUNT(DISTINCT DATE(created_at)) as dias_com_sync,
                    COUNT(*) as total_registros
                FROM faturamento_produto
                WHERE created_at IS NOT NULL
            """)

            resultado_fat = db.session.execute(query_fat).fetchone()

            if resultado_fat and resultado_fat[0]:
                print(f"✅ Primeira sincronização: {resultado_fat[0]}")
                print(f"✅ Última sincronização: {resultado_fat[1]}")
                print(f"📊 Dias com sincronização: {resultado_fat[2]}")
                print(f"📊 Total de registros: {resultado_fat[3]}")

                # Verificar últimas 24 horas
                query_24h = text("""
                    SELECT
                        DATE_TRUNC('hour', created_at) as hora,
                        COUNT(*) as registros
                    FROM faturamento_produto
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY hora
                    ORDER BY hora DESC
                    LIMIT 10
                """)

                resultados_24h = db.session.execute(query_24h).fetchall()

                if resultados_24h:
                    print("\n🕐 Sincronizações nas últimas 24 horas:")
                    for hora, qtd in resultados_24h:
                        print(f"   {hora}: {qtd} registros")
                else:
                    print("\n⚠️ Nenhuma sincronização de faturamento nas últimas 24 horas")

            else:
                print("❌ Nenhum registro de faturamento encontrado")

        except Exception as e:
            print(f"❌ Erro ao verificar faturamento: {e}")

        print()

        # 3. VERIFICAR ÚLTIMA ATUALIZAÇÃO NO BANCO - CARTEIRA
        print("📦 3. HISTÓRICO DE CARTEIRA NO BANCO...")
        print("-" * 50)

        try:
            # Verificar registros mais recentes da carteira
            query_cart = text("""
                SELECT
                    MIN(created_at) as primeira_sync,
                    MAX(created_at) as ultima_sync,
                    COUNT(DISTINCT DATE(created_at)) as dias_com_sync,
                    COUNT(*) as total_registros
                FROM carteira_principal
                WHERE created_at IS NOT NULL
            """)

            resultado_cart = db.session.execute(query_cart).fetchone()

            if resultado_cart and resultado_cart[0]:
                print(f"✅ Primeira sincronização: {resultado_cart[0]}")
                print(f"✅ Última sincronização: {resultado_cart[1]}")
                print(f"📊 Dias com sincronização: {resultado_cart[2]}")
                print(f"📊 Total de registros: {resultado_cart[3]}")

                # Verificar últimas 48 horas (mais amplo para carteira)
                query_48h = text("""
                    SELECT
                        DATE_TRUNC('hour', created_at) as hora,
                        COUNT(*) as registros
                    FROM carteira_principal
                    WHERE created_at >= NOW() - INTERVAL '48 hours'
                    GROUP BY hora
                    ORDER BY hora DESC
                    LIMIT 20
                """)

                resultados_48h = db.session.execute(query_48h).fetchall()

                if resultados_48h:
                    print("\n🕐 Sincronizações nas últimas 48 horas:")
                    for hora, qtd in resultados_48h[:10]:  # Mostrar só as 10 mais recentes
                        print(f"   {hora}: {qtd} registros")

                    # Verificar se houve sincronização hoje
                    hoje = datetime.now().date()
                    sync_hoje = any(hora.date() == hoje for hora, _ in resultados_48h)

                    if not sync_hoje:
                        print(f"\n⚠️ ALERTA: Nenhuma sincronização de carteira HOJE ({hoje})")
                else:
                    print("\n❌ Nenhuma sincronização de carteira nas últimas 48 horas!")

            else:
                print("❌ Nenhum registro de carteira encontrado")

        except Exception as e:
            print(f"❌ Erro ao verificar carteira: {e}")

        print()

        # 4. VERIFICAR TABELA DE JOBS DO SCHEDULER (se existir)
        print("⏰ 4. VERIFICANDO TABELA DE JOBS DO APSCHEDULER...")
        print("-" * 50)

        try:
            # Verificar se existe tabela de jobs do APScheduler
            query_jobs = text("""
                SELECT
                    id,
                    next_run_time,
                    job_state
                FROM apscheduler_jobs
                WHERE id LIKE '%sincronizacao%' OR id LIKE '%incremental%'
                ORDER BY next_run_time DESC
            """)

            jobs = db.session.execute(query_jobs).fetchall()

            if jobs:
                print(f"✅ {len(jobs)} jobs encontrados no scheduler:")
                for job_id, next_run, state in jobs:
                    print(f"   • ID: {job_id}")
                    print(f"     Próxima execução: {next_run}")
                    if state:
                        print(f"     Estado: {len(state)} bytes")
            else:
                print("⚠️ Nenhum job de sincronização encontrado na tabela do scheduler")

        except Exception as e:
            if "does not exist" in str(e) or "no such table" in str(e):
                print("ℹ️ Tabela do APScheduler não existe (scheduler pode não estar configurado)")
            else:
                print(f"❌ Erro ao verificar jobs: {e}")

        print()

        # 5. ANÁLISE FINAL
        print("🎯 5. ANÁLISE FINAL DO HISTÓRICO...")
        print("-" * 50)

        # Calcular diferença de tempo desde última sincronização
        if resultado_cart and resultado_cart[1]:
            ultima_cart = resultado_cart[1]
            if hasattr(ultima_cart, 'replace'):
                # É um datetime, calcular diferença
                diff_cart = datetime.now() - ultima_cart.replace(tzinfo=None)
                horas_sem_sync_cart = diff_cart.total_seconds() / 3600

                if horas_sem_sync_cart > 2:
                    print(f"🔴 PROBLEMA: Carteira sem sincronização há {horas_sem_sync_cart:.1f} horas!")
                else:
                    print(f"✅ Carteira sincronizada há {horas_sem_sync_cart:.1f} horas")

        if resultado_fat and resultado_fat[1]:
            ultima_fat = resultado_fat[1]
            if hasattr(ultima_fat, 'replace'):
                # É um datetime, calcular diferença
                diff_fat = datetime.now() - ultima_fat.replace(tzinfo=None)
                horas_sem_sync_fat = diff_fat.total_seconds() / 3600

                if horas_sem_sync_fat > 2:
                    print(f"⚠️ Faturamento sem sincronização há {horas_sem_sync_fat:.1f} horas")
                else:
                    print(f"✅ Faturamento sincronizado há {horas_sem_sync_fat:.1f} horas")

        print()
        print("📌 CONCLUSÃO:")

        # Verificar se o scheduler está funcionando
        scheduler_funciona = False

        if os.path.exists(log_file):
            try:
                # Verificar se o arquivo foi modificado recentemente
                mod_time = os.path.getmtime(log_file)
                mod_datetime = datetime.fromtimestamp(mod_time)
                diff_log = datetime.now() - mod_datetime

                if diff_log.total_seconds() < 3600:  # Modificado na última hora
                    scheduler_funciona = True
                    print(f"✅ Log do scheduler atualizado há {diff_log.total_seconds()/60:.1f} minutos")
                else:
                    print(f"❌ Log do scheduler sem atualização há {diff_log.total_seconds()/3600:.1f} horas")
            except:
                pass
        else:
            print("❌ Scheduler aparentemente NUNCA executou (sem arquivo de log)")

        if not scheduler_funciona:
            print("\n🔴 SCHEDULER NÃO ESTÁ FUNCIONANDO!")
            print("   Execute manualmente no shell do Render:")
            print("   python -m app.scheduler.sincronizacao_incremental_simples")


if __name__ == "__main__":
    verificar_historico_scheduler()
#!/usr/bin/env python3
"""
Script de Teste do Scheduler - Diagnóstico Completo
=====================================================

Este script verifica TODAS as premissas para o scheduler funcionar.
Use no Render para diagnosticar problemas.

Autor: Sistema
Data: 21/09/2025
"""

import os
import sys
import json
from datetime import datetime

print("=" * 80)
print("🔍 TESTE DO SCHEDULER - DIAGNÓSTICO COMPLETO")
print("=" * 80)
print(f"📅 Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"🖥️ Python: {sys.version}")
print(f"📂 Diretório: {os.getcwd()}")
print()

# 1. VERIFICAR VARIÁVEIS DE AMBIENTE
print("1️⃣ VARIÁVEIS DE AMBIENTE ODOO:")
print("-" * 40)
env_vars = {
    'ODOO_URL': os.environ.get('ODOO_URL', '❌ NÃO DEFINIDO'),
    'ODOO_DB': os.environ.get('ODOO_DB', '❌ NÃO DEFINIDO'),
    'ODOO_USERNAME': os.environ.get('ODOO_USERNAME', '❌ NÃO DEFINIDO'),
    'ODOO_PASSWORD': '***' if os.environ.get('ODOO_PASSWORD') else '❌ NÃO DEFINIDO'
}

for key, value in env_vars.items():
    status = "✅" if value != '❌ NÃO DEFINIDO' else "❌"
    print(f"{status} {key}: {value}")

all_env_ok = all(v != '❌ NÃO DEFINIDO' for v in env_vars.values())
print(f"\n{'✅' if all_env_ok else '❌'} Todas variáveis Odoo configuradas: {all_env_ok}")
print()

# 2. VERIFICAR IMPORTS NECESSÁRIOS
print("2️⃣ VERIFICAÇÃO DE DEPENDÊNCIAS:")
print("-" * 40)

dependencies = {
    'APScheduler': 'apscheduler',
    'Flask': 'flask',
    'SQLAlchemy': 'sqlalchemy',
    'psycopg2': 'psycopg2',
    'pytz': 'pytz',
    'pandas': 'pandas',
    'requests': 'requests'
}

missing_deps = []
for name, module in dependencies.items():
    try:
        __import__(module)
        print(f"✅ {name}: Instalado")
    except ImportError:
        print(f"❌ {name}: NÃO INSTALADO")
        missing_deps.append(name)

if missing_deps:
    print(f"\n❌ ERRO: Dependências faltando: {', '.join(missing_deps)}")
else:
    print(f"\n✅ Todas dependências instaladas")
print()

# 3. TESTAR IMPORTS DO APP
print("3️⃣ TESTE DE IMPORTS DO APLICATIVO:")
print("-" * 40)

try:
    from app import create_app
    print("✅ app.create_app importado")

    from app.odoo.services.carteira_service import CarteiraService
    print("✅ CarteiraService importado")

    from app.odoo.services.faturamento_service import FaturamentoService
    print("✅ FaturamentoService importado")

    from apscheduler.schedulers.blocking import BlockingScheduler
    print("✅ BlockingScheduler importado")

    imports_ok = True
except Exception as e:
    print(f"❌ ERRO ao importar: {e}")
    imports_ok = False
print()

# 4. TESTAR CONEXÃO COM ODOO
if all_env_ok and imports_ok:
    print("4️⃣ TESTE DE CONEXÃO COM ODOO:")
    print("-" * 40)

    try:
        from app.odoo.utils.connection import OdooConnection

        conn = OdooConnection()
        common, uid, models = conn.connect()

        if uid:
            print(f"✅ Conectado ao Odoo com sucesso! UID: {uid}")

            # Testar busca simples
            test_result = models.execute_kw(
                conn.db, uid, conn.password,
                'sale.order', 'search_count',
                [[('state', '=', 'sale')]]
            )
            print(f"✅ Teste de query: {test_result} pedidos em 'sale'")
            odoo_ok = True
        else:
            print("❌ Falha na autenticação Odoo")
            odoo_ok = False

    except Exception as e:
        print(f"❌ ERRO ao conectar Odoo: {e}")
        odoo_ok = False
else:
    print("4️⃣ TESTE DE CONEXÃO COM ODOO:")
    print("-" * 40)
    print("⚠️ Pulando teste (dependências não satisfeitas)")
    odoo_ok = False
print()

# 5. VERIFICAR PROCESSO DO SCHEDULER
print("5️⃣ VERIFICAÇÃO DE PROCESSOS:")
print("-" * 40)

import subprocess
try:
    result = subprocess.run(
        ['ps', 'aux'],
        capture_output=True,
        text=True,
        timeout=5
    )

    scheduler_running = False
    for line in result.stdout.split('\n'):
        if 'sincronizacao_incremental' in line and 'grep' not in line:
            print(f"✅ Scheduler rodando: {line[:100]}...")
            scheduler_running = True
            break

    if not scheduler_running:
        print("❌ Scheduler NÃO está rodando")

except Exception as e:
    print(f"⚠️ Não foi possível verificar processos: {e}")
print()

# 6. VERIFICAR ARQUIVO DE LOG
print("6️⃣ VERIFICAÇÃO DE LOGS:")
print("-" * 40)

log_file = 'logs/sincronizacao_incremental.log'
if os.path.exists(log_file):
    try:
        size = os.path.getsize(log_file)
        modified = datetime.fromtimestamp(os.path.getmtime(log_file))

        print(f"✅ Arquivo de log existe")
        print(f"   - Tamanho: {size:,} bytes")
        print(f"   - Última modificação: {modified.strftime('%Y-%m-%d %H:%M:%S')}")

        # Mostrar últimas linhas
        with open(log_file, 'r') as f:
            lines = f.readlines()
            if lines:
                print(f"   - Total de linhas: {len(lines)}")
                print("\n   📋 Últimas 5 linhas do log:")
                for line in lines[-5:]:
                    print(f"      {line.strip()}")
            else:
                print("   ⚠️ Log vazio")
    except Exception as e:
        print(f"❌ Erro ao ler log: {e}")
else:
    print(f"❌ Arquivo de log não existe: {log_file}")
print()

# 7. TESTE DE EXECUÇÃO SIMPLES
if all_env_ok and imports_ok and odoo_ok:
    print("7️⃣ TESTE DE EXECUÇÃO DO SCHEDULER:")
    print("-" * 40)
    print("⚠️ Tentando executar uma sincronização de teste...")

    try:
        app = create_app()
        with app.app_context():
            # Testar só Faturamento (mais rápido)
            faturamento_service = FaturamentoService()
            resultado = faturamento_service.sincronizar_faturamento_incremental(
                minutos_janela=60,
                primeira_execucao=False,
                minutos_status=60
            )

            if resultado.get("sucesso"):
                print(f"✅ Sincronização teste executada com sucesso!")
                print(f"   - Novos: {resultado.get('registros_novos', 0)}")
                print(f"   - Atualizados: {resultado.get('registros_atualizados', 0)}")
            else:
                print(f"❌ Erro na sincronização: {resultado.get('erro')}")

    except Exception as e:
        print(f"❌ ERRO ao executar teste: {e}")
        import traceback
        print("\nTraceback:")
        traceback.print_exc()
else:
    print("7️⃣ TESTE DE EXECUÇÃO DO SCHEDULER:")
    print("-" * 40)
    print("⚠️ Pulando teste de execução (premissas não satisfeitas)")
print()

# RESULTADO FINAL
print("=" * 80)
print("📊 RESULTADO FINAL DO DIAGNÓSTICO:")
print("=" * 80)

results = {
    'Variáveis Odoo': all_env_ok,
    'Dependências': not missing_deps,
    'Imports App': imports_ok,
    'Conexão Odoo': odoo_ok,
    'Log existe': os.path.exists(log_file)
}

all_ok = all(results.values())

for test, passed in results.items():
    print(f"{'✅' if passed else '❌'} {test}: {'OK' if passed else 'FALHOU'}")

print()
if all_ok:
    print("✅ TODOS OS TESTES PASSARAM - Scheduler deveria funcionar!")
    print("\nPara iniciar o scheduler manualmente:")
    print("  python -m app.scheduler.sincronizacao_incremental_simples")
else:
    print("❌ PROBLEMAS DETECTADOS - Corrija os itens acima")

    if not all_env_ok:
        print("\n🔧 CORREÇÃO: Configure as variáveis de ambiente do Odoo")
    if missing_deps:
        print("\n🔧 CORREÇÃO: Instale as dependências com: pip install -r requirements.txt")
    if not imports_ok:
        print("\n🔧 CORREÇÃO: Verifique se está no diretório correto do projeto")

print("\n" + "=" * 80)
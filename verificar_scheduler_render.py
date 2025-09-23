#!/usr/bin/env python3
"""
Script para verificar se o scheduler está rodando no Render
===========================================================

Este script oferece várias formas de confirmar se o scheduler
de sincronização incremental está funcionando corretamente.

Uso:
    python verificar_scheduler_render.py

Autor: Sistema de Fretes
Data: 2025-09-22
"""

import os
import sys
import subprocess
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verificar_processo_local():
    """Verifica se o processo do scheduler está rodando localmente"""
    print("\n🔍 VERIFICAÇÃO 1: Processo Local")
    print("-" * 50)

    try:
        # Procurar pelo processo usando ps
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            check=False
        )

        linhas_scheduler = []
        for linha in result.stdout.split('\n'):
            if 'sincronizacao_incremental' in linha and 'python' in linha:
                linhas_scheduler.append(linha)

        if linhas_scheduler:
            print("✅ Scheduler encontrado rodando:")
            for linha in linhas_scheduler:
                # Extrair PID
                parts = linha.split()
                if len(parts) > 1:
                    pid = parts[1]
                    print(f"   PID: {pid}")
                    print(f"   Comando: {' '.join(parts[10:])[:100]}...")
            return True
        else:
            print("❌ Processo do scheduler NÃO encontrado")
            print("   Pode estar parado ou rodando em outro servidor")
            return False

    except Exception as e:
        print(f"⚠️ Erro ao verificar processo: {e}")
        return False


def verificar_logs():
    """Verifica os logs do scheduler"""
    print("\n📋 VERIFICAÇÃO 2: Logs do Scheduler")
    print("-" * 50)

    log_path = Path("logs/sincronizacao_incremental.log")

    if not log_path.exists():
        print(f"❌ Arquivo de log não encontrado: {log_path}")
        print("   O scheduler pode não ter sido iniciado ainda")
        return False

    try:
        # Ler últimas linhas do log
        with open(log_path, 'r') as f:
            linhas = f.readlines()

        if not linhas:
            print("⚠️ Log existe mas está vazio")
            return False

        print(f"📄 Log encontrado com {len(linhas)} linhas")

        # Procurar última execução
        ultima_execucao = None
        for linha in reversed(linhas):
            if "SINCRONIZAÇÃO DEFINITIVA" in linha or "Sincronização completa" in linha:
                # Tentar extrair timestamp
                try:
                    # Formato: 2025-09-22 10:30:45,123 - ...
                    timestamp_str = linha.split(' - ')[0]
                    ultima_execucao = datetime.strptime(
                        timestamp_str.split(',')[0],
                        "%Y-%m-%d %H:%M:%S"
                    )
                    break
                except Exception as e:
                    print(f"❌ Erro ao extrair timestamp: {e}")
                    pass

        if ultima_execucao:
            diferenca = datetime.now() - ultima_execucao
            minutos = int(diferenca.total_seconds() / 60)

            print(f"⏰ Última execução: {ultima_execucao.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   ({minutos} minutos atrás)")

            if minutos < 35:  # Considerando intervalo de 30 min + margem
                print("✅ Scheduler está ATIVO (execução recente)")
                return True
            elif minutos < 70:
                print("⚠️ Scheduler pode estar com atraso")
                return True
            else:
                print("❌ Scheduler parece INATIVO (última execução há muito tempo)")
                return False
        else:
            print("⚠️ Não foi possível determinar última execução")

        # Mostrar últimas 5 linhas
        print("\n📜 Últimas 5 linhas do log:")
        for linha in linhas[-5:]:
            print(f"   {linha.strip()[:120]}...")

        return True

    except Exception as e:
        print(f"❌ Erro ao ler logs: {e}")
        return False


def verificar_banco_dados():
    """Verifica evidências de sincronização no banco"""
    print("\n💾 VERIFICAÇÃO 3: Evidências no Banco de Dados")
    print("-" * 50)

    try:
        from app import create_app, db
        from app.faturamento.models import FaturamentoProduto
        from app.carteira.models import CarteiraPrincipal
        from sqlalchemy import func, desc

        app = create_app()

        with app.app_context():
            # Verificar últimos registros de faturamento
            ultimo_faturamento = db.session.query(
                FaturamentoProduto.created_at
            ).order_by(
                desc(FaturamentoProduto.created_at)
            ).first()

            if ultimo_faturamento and ultimo_faturamento[0]:
                diferenca = datetime.now() - ultimo_faturamento[0]
                horas = int(diferenca.total_seconds() / 3600)
                print(f"📦 Último faturamento criado: {ultimo_faturamento[0].strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   ({horas} horas atrás)")

                if horas < 4:
                    print("   ✅ Sincronização de faturamento RECENTE")
                else:
                    print("   ⚠️ Sincronização de faturamento pode estar atrasada")

            # Verificar últimas atualizações na carteira
            ultima_carteira = db.session.query(
                CarteiraPrincipal.updated_at
            ).order_by(
                desc(CarteiraPrincipal.updated_at)
            ).first()

            if ultima_carteira and ultima_carteira[0]:
                diferenca = datetime.now() - ultima_carteira[0]
                minutos = int(diferenca.total_seconds() / 60)
                print(f"📋 Última atualização carteira: {ultima_carteira[0].strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   ({minutos} minutos atrás)")

                if minutos < 60:
                    print("   ✅ Sincronização de carteira ATIVA")
                else:
                    print("   ⚠️ Sincronização de carteira pode estar parada")

            # Contar registros recentes
            uma_hora_atras = datetime.now() - timedelta(hours=1)

            novos_faturamentos = db.session.query(
                func.count(FaturamentoProduto.id)
            ).filter(
                FaturamentoProduto.created_at >= uma_hora_atras
            ).scalar()

            print(f"\n📊 Estatísticas última hora:")
            print(f"   - Novos faturamentos: {novos_faturamentos}")

            return True

    except Exception as e:
        print(f"❌ Erro ao verificar banco: {e}")
        return False


def criar_endpoint_verificacao():
    """Cria código para endpoint de verificação no servidor"""
    print("\n🌐 VERIFICAÇÃO 4: Endpoint HTTP (código para adicionar)")
    print("-" * 50)

    codigo = '''
# Adicionar este código em app/api/routes.py ou criar novo arquivo

@api_bp.route('/scheduler/status', methods=['GET'])
def scheduler_status():
    """Endpoint para verificar status do scheduler"""
    import subprocess
    from datetime import datetime
    from pathlib import Path

    status = {
        'timestamp': datetime.now().isoformat(),
        'processo_ativo': False,
        'ultima_execucao': None,
        'proxima_execucao': None,
        'logs_disponiveis': False
    }

    # Verificar processo
    try:
        result = subprocess.run(
            ["pgrep", "-f", "sincronizacao_incremental"],
            capture_output=True,
            text=True,
            check=False
        )
        status['processo_ativo'] = bool(result.stdout.strip())
        if result.stdout.strip():
            status['pid'] = result.stdout.strip()
    except Exception as e:
        print(f"❌ Erro ao verificar processo: {e}")
        pass

    # Verificar logs
    log_path = Path("logs/sincronizacao_incremental.log")
    if log_path.exists():
        status['logs_disponiveis'] = True
        try:
            with open(log_path, 'r') as f:
                # Pegar última linha com timestamp
                for linha in reversed(f.readlines()[-100:]):
                    if "SINCRONIZAÇÃO" in linha:
                        # Extrair timestamp
                        status['ultima_execucao'] = linha[:19]
                        break
        except Exception as e:
            print(f"❌ Erro ao ler logs: {e}")
            pass

    # Calcular próxima execução (30 minutos após última)
    if status['ultima_execucao']:
        try:
            ultima = datetime.fromisoformat(status['ultima_execucao'])
            proxima = ultima + timedelta(minutes=30)
            status['proxima_execucao'] = proxima.isoformat()
        except Exception as e:
            print(f"❌ Erro ao calcular próxima execução: {e}")
            pass

    return jsonify(status)
'''

    print("📝 Código para adicionar endpoint de verificação:")
    print(codigo)
    print("\n💡 Depois de adicionar, acesse: https://seu-app.onrender.com/api/scheduler/status")

    return True


def verificar_render_api():
    """Verifica via API do Render (necessita API key)"""
    print("\n🚀 VERIFICAÇÃO 5: Render API")
    print("-" * 50)

    api_key = os.environ.get('RENDER_API_KEY')
    service_id = os.environ.get('RENDER_SERVICE_ID')

    if not api_key:
        print("⚠️ RENDER_API_KEY não configurada")
        print("   Para usar esta verificação:")
        print("   1. Acesse: https://dashboard.render.com/account/api-keys")
        print("   2. Crie uma API key")
        print("   3. Configure: export RENDER_API_KEY='sua-key'")
        return False

    if not service_id:
        print("⚠️ RENDER_SERVICE_ID não configurado")
        print("   Pegue o ID do serviço na URL do dashboard do Render")
        return False

    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/json'
        }

        # Buscar logs do serviço
        url = f'https://api.render.com/v1/services/{service_id}/logs'
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            logs = response.text

            if 'sincronizacao_incremental' in logs:
                print("✅ Scheduler mencionado nos logs do Render")

                # Procurar evidências de execução
                if 'Sincronização completa' in logs:
                    print("   ✅ Evidência de execução encontrada")
                if 'ERRO' in logs and 'scheduler' in logs.lower():
                    print("   ⚠️ Possíveis erros detectados")

                return True
            else:
                print("❌ Scheduler não encontrado nos logs do Render")
                return False

        else:
            print(f"❌ Erro ao acessar API do Render: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Erro ao verificar via API: {e}")
        return False


def main():
    """Executa todas as verificações"""
    print("=" * 60)
    print("🔍 VERIFICADOR DE SCHEDULER NO RENDER")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    resultados = []

    # Executar verificações
    resultados.append(("Processo Local", verificar_processo_local()))
    resultados.append(("Logs", verificar_logs()))
    resultados.append(("Banco de Dados", verificar_banco_dados()))
    criar_endpoint_verificacao()
    resultados.append(("Render API", verificar_render_api()))

    # Resumo
    print("\n" + "=" * 60)
    print("📊 RESUMO DAS VERIFICAÇÕES")
    print("=" * 60)

    total_ok = sum(1 for _, status in resultados if status)
    total = len(resultados)

    for nome, status in resultados:
        simbolo = "✅" if status else "❌"
        print(f"{simbolo} {nome}: {'OK' if status else 'FALHOU'}")

    print(f"\nResultado: {total_ok}/{total} verificações passaram")

    if total_ok >= 2:
        print("✅ Scheduler provavelmente está ATIVO")
    else:
        print("❌ Scheduler pode estar com PROBLEMAS")

    print("\n💡 DICAS PARA MONITORAMENTO CONTÍNUO:")
    print("1. Configure alertas no Render para falhas")
    print("2. Use o endpoint /api/scheduler/status após adicionar")
    print("3. Configure RENDER_API_KEY para monitoramento via API")
    print("4. Verifique logs regularmente: tail -f logs/sincronizacao_incremental.log")
    print("5. No Render Dashboard, veja os logs em tempo real")


if __name__ == "__main__":
    main()
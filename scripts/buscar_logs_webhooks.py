#!/usr/bin/env python3
"""
Script para buscar logs de webhooks TagPlus no Render

Uso:
    python scripts/buscar_logs_webhooks.py --horas 24
    python scripts/buscar_logs_webhooks.py --tipo nfe --horas 48
    python scripts/buscar_logs_webhooks.py --rejeitados
    python scripts/buscar_logs_webhooks.py --nfe 12345
"""

import requests
import json
import argparse
from datetime import datetime, timedelta
import os
import re
from typing import List, Dict
from collections import defaultdict
from pathlib import Path

# Carregar variáveis do .env
def carregar_env():
    """Carrega variáveis do arquivo .env"""
    env_path = Path(__file__).parent.parent / '.env'

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = value

# Carregar .env antes de ler as variáveis
carregar_env()

# Configuração
RENDER_API_KEY = os.getenv('RENDER_API_KEY', '')
SERVICE_ID = os.getenv('RENDER_SERVICE_ID', '')

class BuscadorLogsWebhook:
    """Busca e analisa logs de webhooks TagPlus"""

    def __init__(self, api_key: str, service_id: str):
        self.api_key = api_key
        self.service_id = service_id
        self.base_url = 'https://api.render.com/v1'
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/json'
        }

    def buscar_logs(self, horas: int = 24, limit: int = 10000) -> List[str]:
        """Busca logs do Render das últimas N horas"""

        if not self.api_key or not self.service_id:
            print("❌ Configure RENDER_API_KEY e RENDER_SERVICE_ID")
            print("\nObtenha no Render Dashboard:")
            print("1. API Key: Account Settings > API Keys")
            print("2. Service ID: URL do serviço (srv-xxxxx)")
            return []

        print(f"🔍 Buscando logs das últimas {horas}h...")

        url = f'{self.base_url}/services/{self.service_id}/logs'

        since_time = (datetime.utcnow() - timedelta(hours=horas)).isoformat() + 'Z'

        params = {
            'since': since_time,
            'limit': limit
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            logs = response.json()

            # Render retorna array de objetos com 'message' e 'timestamp'
            if isinstance(logs, list):
                return [log.get('message', str(log)) for log in logs]

            return []

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao buscar logs: {e}")
            return []

    def filtrar_webhooks(self, logs: List[str], tipo: str = None, rejeitados: bool = False) -> List[Dict]:
        """Filtra logs relacionados a webhooks"""

        webhooks = []

        # Padrões de busca baseados no código real
        padroes = {
            'recebido': r'🔔 WEBHOOK RECEBIDO.*Endpoint: (/webhook/tagplus/\w+).*IP: ([\d.]+)',
            'validado': r'✅ WEBHOOK VALIDADO',
            'rejeitado': r'🚫 WEBHOOK REJEITADO.*Motivo: (.+?) \|',
            'nfe': r'📦 WEBHOOK NFE.*Event Type: (\w+).*NFe ID: (\d+)',
            'cliente': r'📦 WEBHOOK CLIENTE.*Event Type: (\w+).*Cliente ID: (\d+)',
            'payload': r'🔍 Payload completo recebido: ({.+})',
            'erro': r'Erro no webhook.*: (.+)',
            'processado': r'NF (\d+) processada via webhook com (\d+) itens'
        }

        for log in logs:
            webhook_info = {}

            # Verifica se é log de webhook
            if 'WEBHOOK' not in log and '🔔' not in log and '📦' not in log:
                continue

            # Filtra por rejeitados se solicitado
            if rejeitados and 'REJEITADO' not in log:
                continue

            # Filtra por tipo se solicitado
            if tipo:
                if tipo == 'nfe' and '/nfe' not in log and 'WEBHOOK NFE' not in log:
                    continue
                elif tipo == 'cliente' and '/cliente' not in log and 'WEBHOOK CLIENTE' not in log:
                    continue

            # Extrai timestamp do log (geralmente no início)
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})', log)
            if timestamp_match:
                webhook_info['timestamp'] = timestamp_match.group(1)

            # Extrai informações estruturadas
            webhook_info['log_completo'] = log

            for nome, padrao in padroes.items():
                match = re.search(padrao, log)
                if match:
                    webhook_info['tipo'] = nome
                    webhook_info['detalhes'] = match.groups()
                    break

            if webhook_info:
                webhooks.append(webhook_info)

        return webhooks

    def buscar_por_nfe(self, logs: List[str], numero_nfe: str) -> List[str]:
        """Busca todos os logs relacionados a uma NFe específica"""

        logs_nfe = []

        for log in logs:
            # Busca por número da NFe em diversos formatos
            if (f'NFe ID: {numero_nfe}' in log or
                f'NF {numero_nfe}' in log or
                f'numero.*{numero_nfe}' in log.lower()):
                logs_nfe.append(log)

        return logs_nfe

    def gerar_relatorio(self, webhooks: List[Dict]) -> Dict:
        """Gera relatório estatístico dos webhooks"""

        stats = {
            'total': len(webhooks),
            'por_tipo': defaultdict(int),
            'por_endpoint': defaultdict(int),
            'rejeitados': 0,
            'validados': 0,
            'nfes_processadas': [],
            'ips_origem': defaultdict(int)
        }

        for webhook in webhooks:
            tipo = webhook.get('tipo', 'desconhecido')
            stats['por_tipo'][tipo] += 1

            if tipo == 'recebido' and webhook.get('detalhes'):
                endpoint, ip = webhook['detalhes']
                stats['por_endpoint'][endpoint] += 1
                stats['ips_origem'][ip] += 1

            if tipo == 'rejeitado':
                stats['rejeitados'] += 1

            if tipo == 'validado':
                stats['validados'] += 1

            if tipo == 'processado' and webhook.get('detalhes'):
                nfe_num = webhook['detalhes'][0]
                stats['nfes_processadas'].append(nfe_num)

        return stats

    def exibir_webhooks(self, webhooks: List[Dict], verbose: bool = False):
        """Exibe webhooks de forma formatada"""

        if not webhooks:
            print("❌ Nenhum webhook encontrado")
            return

        print(f"\n✅ {len(webhooks)} webhooks encontrados\n")
        print("=" * 100)

        for i, webhook in enumerate(webhooks, 1):
            timestamp = webhook.get('timestamp', 'N/A')
            tipo = webhook.get('tipo', 'desconhecido')

            print(f"\n[{i}] {timestamp} | Tipo: {tipo.upper()}")

            if verbose:
                print(f"    Log: {webhook['log_completo'][:200]}...")
            else:
                # Exibir apenas informações chave
                if tipo == 'recebido' and webhook.get('detalhes'):
                    endpoint, ip = webhook['detalhes']
                    print(f"    Endpoint: {endpoint}")
                    print(f"    IP: {ip}")

                elif tipo == 'nfe' and webhook.get('detalhes'):
                    event_type, nfe_id = webhook['detalhes']
                    print(f"    Event: {event_type}")
                    print(f"    NFe ID: {nfe_id}")

                elif tipo == 'rejeitado' and webhook.get('detalhes'):
                    motivo = webhook['detalhes'][0]
                    print(f"    ⚠️  Motivo: {motivo}")

                elif tipo == 'processado' and webhook.get('detalhes'):
                    nfe_num, itens = webhook['detalhes']
                    print(f"    ✅ NF {nfe_num} processada com {itens} itens")

            print("-" * 100)


def main():
    parser = argparse.ArgumentParser(
        description='Busca logs de webhooks TagPlus no Render',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s --horas 24                    # Últimas 24 horas
  %(prog)s --tipo nfe --horas 48         # Apenas webhooks de NFe
  %(prog)s --rejeitados                  # Apenas rejeitados
  %(prog)s --nfe 12345                   # Logs de uma NFe específica
  %(prog)s --verbose                     # Exibir log completo
  %(prog)s --stats                       # Exibir estatísticas
        """
    )

    parser.add_argument('--horas', type=int, default=24,
                       help='Buscar logs das últimas N horas (padrão: 24)')

    parser.add_argument('--tipo', choices=['nfe', 'cliente'],
                       help='Filtrar por tipo de webhook')

    parser.add_argument('--rejeitados', action='store_true',
                       help='Mostrar apenas webhooks rejeitados')

    parser.add_argument('--nfe', type=str,
                       help='Buscar logs de uma NFe específica')

    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Exibir log completo')

    parser.add_argument('--stats', action='store_true',
                       help='Exibir estatísticas')

    parser.add_argument('--exportar', type=str,
                       help='Exportar para arquivo JSON')

    args = parser.parse_args()

    # Criar buscador
    buscador = BuscadorLogsWebhook(RENDER_API_KEY, SERVICE_ID)

    # Buscar logs
    logs = buscador.buscar_logs(horas=args.horas)

    if not logs:
        print("❌ Nenhum log encontrado")
        return

    print(f"📊 {len(logs)} logs encontrados no total")

    # Filtrar webhooks
    if args.nfe:
        # Busca específica por NFe
        logs_filtrados = buscador.buscar_por_nfe(logs, args.nfe)
        print(f"\n🔍 Buscando NFe {args.nfe}...")
        print(f"✅ {len(logs_filtrados)} logs encontrados\n")

        for log in logs_filtrados:
            print(log)
            print("-" * 100)

    else:
        # Busca geral de webhooks
        webhooks = buscador.filtrar_webhooks(
            logs,
            tipo=args.tipo,
            rejeitados=args.rejeitados
        )

        # Exibir webhooks
        buscador.exibir_webhooks(webhooks, verbose=args.verbose)

        # Estatísticas
        if args.stats or len(webhooks) > 10:
            stats = buscador.gerar_relatorio(webhooks)

            print("\n" + "=" * 100)
            print("📊 ESTATÍSTICAS")
            print("=" * 100)
            print(f"Total de webhooks: {stats['total']}")
            print(f"Validados: {stats['validados']}")
            print(f"Rejeitados: {stats['rejeitados']}")

            if stats['por_endpoint']:
                print("\n🔗 Por endpoint:")
                for endpoint, count in stats['por_endpoint'].items():
                    print(f"  {endpoint}: {count}")

            if stats['ips_origem']:
                print("\n🌐 IPs de origem:")
                for ip, count in stats['ips_origem'].items():
                    print(f"  {ip}: {count}")

            if stats['nfes_processadas']:
                print(f"\n✅ NFes processadas: {len(stats['nfes_processadas'])}")
                if len(stats['nfes_processadas']) <= 10:
                    print(f"  {', '.join(stats['nfes_processadas'])}")

        # Exportar
        if args.exportar:
            with open(args.exportar, 'w') as f:
                json.dump(webhooks, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Logs exportados para: {args.exportar}")


if __name__ == '__main__':
    main()
